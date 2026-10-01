"""
Motor de extracción de resúmenes bancarios
Soporta: Galicia, Santander, BBVA, Macro, HSBC, Banco Nación, ICBC, Genérico
"""

import os
import re
import pdfplumber
from datetime import datetime


# ─────────────────────────────────────────────
#  PATRONES POR BANCO
# ─────────────────────────────────────────────

PATRONES = {
    'galicia': {
        # Formato: DD/MM/YYYY  Descripción  Monto  Saldo
        'movimiento': re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)',
            re.IGNORECASE
        ),
        'fecha_fmt': '%d/%m/%Y',
    },
    'santander': None,  # Parser dedicado: extraer_santander()
    'bbva': {
        'movimiento': re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-]?[\d.,]+)\s+([\d.,]+)',
            re.IGNORECASE
        ),
        'fecha_fmt': '%d/%m/%Y',
        'tiene_fecha_valor': True,
    },
    'macro': {
        'movimiento': re.compile(
            r'(\d{2}/\d{2})\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)',
            re.IGNORECASE
        ),
        'fecha_fmt': '%d/%m',
    },
    'nacion': {
        'movimiento': re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)',
            re.IGNORECASE
        ),
        'fecha_fmt': '%d/%m/%Y',
    },
    'hsbc': {
        'movimiento': re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)',
            re.IGNORECASE
        ),
        'fecha_fmt': '%d/%m/%Y',
    },
    'icbc': None,  # Parser dedicado: extraer_icbc()
    'generico': None,  # Usa detección automática
}


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def extraer_movimientos(ruta_pdf: str, banco: str = 'generico') -> dict:
    """
    Extrae movimientos de un PDF bancario.
    Returns: { movimientos: [...], info: {...}, texto_muestra: str }
    """
    banco = banco.lower().strip()

    # Bancos con parser dedicado de texto: no necesitan extract_tables(),
    # que es muy costoso en RAM/CPU y en PDFs de cientos de páginas puede
    # tirar el proceso por OOM sin aportar nada (el parser de texto ya es
    # más preciso que la extracción por tablas para estos formatos).
    BANCOS_SIN_TABLAS = {'nacion', 'santander', 'icbc', 'bbva', 'macro'}

    with pdfplumber.open(ruta_pdf) as pdf:
        primer_texto = pdf.pages[0].extract_text() if pdf.pages else ''
        banco_preliminar = detectar_banco(primer_texto or '') if banco == 'generico' else banco
        usar_tablas = banco_preliminar not in BANCOS_SIN_TABLAS

        paginas_texto = []
        todas_tablas = []

        for page in pdf.pages:
            texto = page.extract_text() or ''
            paginas_texto.append(texto)

            if usar_tablas:
                tablas = page.extract_tables()
                if tablas:
                    todas_tablas.extend(tablas)

            # pdfplumber cachea los caracteres/objetos de cada página mientras
            # el PDF siga abierto; en documentos de cientos de páginas eso
            # acumula memoria indefinidamente. Liberarlo apenas terminamos con
            # la página evita que el proceso escale a gigabytes de RAM.
            page.flush_cache()

    texto_completo = '\n'.join(paginas_texto)
    banco_detectado = detectar_banco(texto_completo) if banco == 'generico' else banco
    titular = extraer_titular(paginas_texto[0] if paginas_texto else '')

    # Intentar primero con tablas estructuradas
    movimientos = []
    if todas_tablas:
        movimientos = extraer_de_tablas(todas_tablas, banco_detectado)

    # Parser dedicado para Santander
    if not movimientos and banco_detectado == 'santander':
        movimientos = extraer_santander(texto_completo)

    # Parser dedicado para Nación
    if not movimientos and banco_detectado == 'nacion':
        movimientos = extraer_nacion(texto_completo)

    # Parser dedicado para ICBC
    if not movimientos and banco_detectado == 'icbc':
        movimientos = extraer_icbc(texto_completo)

    # Parser dedicado para BBVA
    if not movimientos and banco_detectado == 'bbva':
        movimientos = extraer_bbva(texto_completo)

    # Parser dedicado para Macro
    if not movimientos and banco_detectado == 'macro':
        movimientos = extraer_macro(texto_completo)

    # Si no hubo éxito con tablas, usar regex sobre texto
    if not movimientos:
        movimientos = extraer_de_texto(texto_completo, banco_detectado)

    # Si aún sin resultados, usar extracción genérica agresiva
    if not movimientos:
        movimientos = extraccion_generica(texto_completo)

    # Agregar titular, documento de origen y unificar importe
    nombre_documento = os.path.splitext(os.path.basename(ruta_pdf))[0]
    for mov in movimientos:
        if titular:
            mov['titular'] = titular
        mov['documento'] = nombre_documento
        debito = mov.pop('debito', None)
        credito = mov.pop('credito', None)
        if debito is not None:
            mov['importe'] = -abs(debito)
        elif credito is not None:
            mov['importe'] = abs(credito)
        elif 'importe' not in mov:
            mov['importe'] = None
        mov['tipo'] = 'D' if mov.get('importe') is not None and mov['importe'] < 0 else ('C' if mov.get('importe') is not None and mov['importe'] > 0 else '')

    return {
        'movimientos': movimientos,
        'info': {
            'banco': banco_detectado,
            'titular': titular,
            'paginas': len(paginas_texto),
            'metodo': 'tabla' if todas_tablas and movimientos else 'texto',
            'saldos': calcular_saldos_por_cuenta(movimientos),
        },
        'texto_muestra': texto_completo[:2000]
    }


def calcular_saldos_por_cuenta(movimientos):
    """
    Identifica saldo inicial y final por cuenta a partir del campo 'saldo'
    (saldo corriente) que cada parser ya deja en los movimientos.

    Agrupa por 'cuenta' cuando el parser la distingue (BBVA, Macro); si no,
    por 'moneda' (separa ARS/USD en ICBC); si tampoco hay moneda, todo cae
    en un único grupo. El orden de los grupos es el de aparición en el PDF.

    saldo_inicial se despeja del primer movimiento con saldo e importe
    conocidos (saldo - importe = saldo anterior a ese movimiento), lo que
    coincide con el "SALDO ANTERIOR"/"SALDO ULTIMO EXTRACTO" que imprimen
    los bancos cuando el parser pudo leerlo. saldo_final es el saldo del
    último movimiento del grupo.
    """
    grupos = {}
    orden = []

    for mov in movimientos:
        clave = mov.get('cuenta') or mov.get('moneda') or ''
        if clave not in grupos:
            grupos[clave] = {
                'cuenta': mov.get('cuenta', ''),
                'moneda': mov.get('moneda', ''),
                'saldo_inicial': None,
                'saldo_final': None,
            }
            orden.append(clave)

        grupo = grupos[clave]
        saldo = mov.get('saldo')
        importe = mov.get('importe')

        if grupo['saldo_inicial'] is None and saldo is not None and importe is not None:
            grupo['saldo_inicial'] = round(saldo - importe, 2)
        if saldo is not None:
            grupo['saldo_final'] = saldo

    return [grupos[clave] for clave in orden]


# ─────────────────────────────────────────────
#  DETECCIÓN DE BANCO
# ─────────────────────────────────────────────

def detectar_banco(texto: str) -> str:
    texto_lower = texto.lower()
    bancos = {
        'galicia': ['galicia', 'banco galicia'],
        'santander': ['santander'],
        'bbva': ['bbva', 'frances'],
        'macro': ['banco macro', 'macro'],
        'nacion': ['banco de la nacion', 'bna', 'nacion'],
        'hsbc': ['hsbc'],
        # El PDF de ICBC nunca imprime la sigla "ICBC": dice el nombre
        # completo, y a veces pdfplumber lo extrae sin espacios
        # ("industrialandcommercialbankofchina") por el espaciado del PDF.
        'icbc': ['icbc', 'bankofchina', 'bank of china', '30-70944784-6'],
        'ciudad': ['banco ciudad'],
        'provincia': ['banco provincia', 'bapro'],
        'supervielle': ['supervielle'],
    }
    for banco, keywords in bancos.items():
        if any(kw in texto_lower for kw in keywords):
            return banco
    return 'generico'


# ─────────────────────────────────────────────
#  EXTRACCIÓN DESDE TABLAS
# ─────────────────────────────────────────────

def extraer_de_tablas(tablas, banco):
    """Intenta identificar y parsear tablas de movimientos"""
    movimientos = []

    for tabla in tablas:
        if not tabla or len(tabla) < 2:
            continue

        # Buscar fila de encabezado
        encabezado = tabla[0]
        if not encabezado:
            continue

        encabezado_str = ' '.join(str(c or '').lower() for c in encabezado)

        # Verificar que es tabla de movimientos
        es_movimientos = any(kw in encabezado_str for kw in [
            'fecha', 'movimiento', 'descripcion', 'importe',
            'debito', 'credito', 'saldo', 'concepto', 'operacion'
        ])
        if not es_movimientos:
            continue

        # Mapear columnas
        col_map = mapear_columnas(encabezado)

        for fila in tabla[1:]:
            if not fila or all(c is None or str(c).strip() == '' for c in fila):
                continue

            mov = parsear_fila_tabla(fila, col_map, encabezado)
            if mov:
                movimientos.append(mov)

    return movimientos


def mapear_columnas(encabezado):
    """Mapea columnas por nombre"""
    col_map = {}
    for i, col in enumerate(encabezado):
        if col is None:
            continue
        col_str = str(col).lower().strip()
        if any(k in col_str for k in ['fecha', 'date', 'dia']):
            col_map['fecha'] = i
        elif any(k in col_str for k in ['descripcion', 'concepto', 'detalle', 'movimiento', 'operacion', 'glosa']):
            col_map['descripcion'] = i
        elif any(k in col_str for k in ['debito', 'cargo', 'egreso', 'retiro', 'debe']):
            col_map['debito'] = i
        elif any(k in col_str for k in ['credito', 'abono', 'ingreso', 'deposito', 'haber']):
            col_map['credito'] = i
        elif any(k in col_str for k in ['saldo', 'balance']):
            col_map['saldo'] = i
        elif any(k in col_str for k in ['referencia', 'comprobante', 'nro', 'numero']):
            col_map['referencia'] = i
        elif any(k in col_str for k in ['importe', 'monto', 'valor', 'amount']):
            col_map['importe'] = i
    return col_map


def parsear_fila_tabla(fila, col_map, encabezado):
    """Parsea una fila de tabla en un dict de movimiento"""
    def get(key):
        idx = col_map.get(key)
        if idx is not None and idx < len(fila):
            return str(fila[idx] or '').strip()
        return ''

    fecha = get('fecha')
    descripcion = get('descripcion')

    # Validar que tiene al menos fecha o descripción significativa
    if not fecha and not descripcion:
        return None

    # Verificar que la fecha parece válida
    if fecha and not re.search(r'\d{1,2}[/\-]\d{1,2}', fecha):
        if not descripcion:
            return None

    debito = limpiar_monto(get('debito'))
    credito = limpiar_monto(get('credito'))
    saldo = limpiar_monto(get('saldo'))
    importe = limpiar_monto(get('importe'))

    # Si hay importe pero no débito/crédito, determinar por signo
    if importe is not None and debito is None and credito is None:
        if importe < 0:
            debito = abs(importe)
        else:
            credito = importe

    mov = {
        'fecha': normalizar_fecha(fecha),
        'descripcion': descripcion or ' '.join(str(c or '') for c in fila),
        'debito': debito,
        'credito': credito,
        'saldo': saldo,
        'referencia': get('referencia'),
        'tipo': 'D' if debito else ('C' if credito else ''),
        'moneda': 'ARS',
    }

    # Eliminar campos vacíos no esenciales
    return {k: v for k, v in mov.items() if v is not None and v != ''}


# ─────────────────────────────────────────────
#  EXTRACCIÓN DESDE TEXTO (REGEX)
# ─────────────────────────────────────────────

def extraer_de_texto(texto, banco):
    """Usa patrones regex según el banco"""
    movimientos = []
    lineas = texto.split('\n')

    patron_config = PATRONES.get(banco, PATRONES['generico'])
    if patron_config is None:
        return []

    patron = patron_config['movimiento']
    tiene_fecha_valor = patron_config.get('tiene_fecha_valor', False)

    for linea in lineas:
        linea = linea.strip()
        if len(linea) < 10:
            continue

        m = patron.search(linea)
        if not m:
            continue

        grupos = m.groups()
        try:
            if tiene_fecha_valor and len(grupos) >= 5:
                fecha, _fecha_valor, desc, monto, saldo = grupos[:5]
            elif len(grupos) >= 4:
                fecha, desc, monto, saldo = grupos[:4]
            elif len(grupos) >= 3:
                fecha, desc, monto = grupos[:3]
                saldo = None
            else:
                continue

            monto_num = limpiar_monto(monto)
            saldo_num = limpiar_monto(saldo) if saldo else None

            # Determinar débito/crédito por signo o contexto
            debito, credito = clasificar_monto(monto, monto_num, desc)

            movimientos.append({
                'fecha': normalizar_fecha(fecha),
                'descripcion': desc.strip(),
                'referencia': '',
                'debito': debito,
                'credito': credito,
                'saldo': saldo_num,
                'tipo': 'D' if debito else 'C',
                'moneda': 'ARS',
                'raw': linea
            })
        except Exception:
            continue

    return movimientos


# ─────────────────────────────────────────────
#  EXTRACCIÓN SANTANDER (DEDICADA)
# ─────────────────────────────────────────────

def extraer_santander(texto):
    """
    Parser dedicado para resúmenes Santander (Cuenta Corriente / Caja de Ahorro).

    El resumen imprime una tabla con columnas
    Fecha | Comprobante | Movimiento | Débito | Crédito | Saldo en cuenta,
    pero al extraer el texto la columna Fecha se desalinea del resto de la fila
    (va en un bloque x distinto y queda centrada verticalmente en las filas de
    dos o tres líneas), así que en el texto plano la fecha aparece:

      - en la misma línea de la fila (filas de una sola línea), o
      - en una línea suelta DESPUÉS de la línea principal de la fila,
        antes de su continuación de descripción.

    Además, las filas cuya descripción ocupa dos o tres líneas dejan la fecha
    y el comprobante en líneas separadas del resto. Por eso el parser no
    puede trabajar línea por línea: primero reagrupa las líneas en filas
    lógicas y recién después interpreta cada fila.

    Dos reglas sostienen la reagrupación:

      1. Una línea es "línea principal de fila" solo si tiene DOS montos o más.
         El último monto es el saldo en cuenta y el penúltimo el importe del
         movimiento. Las líneas de continuación nunca tienen dos montos, y las
         trampas más frecuentes son justamente las que tienen uno solo y lo
         presentan como si fuera un importe ("Resp:... / 0,10% sobre
         $1.203.371,18", "Cta orig: 068-017995/7 - base impo. usd 2.040,00",
         "Total Retención Régimen de Recaudación SIRCREB $ 1.203,37"), así que
         la regla las descarta como movimiento y las deja como continuación.

      2. "Saldo Inicial" no es un movimiento: es el saldo de apertura de la
         cuenta. Antes se emitía como una fila más con tipo 'C', lo que
         inflaba el total de créditos y rompía la conciliación. Ahora se usa
         como saldo de arrastre para clasificar el resto.

    Clasificación débito/crédito: se deriva del propio saldo informado por el
    banco (saldo_actual = saldo_anterior ± importe), nunca del texto de la
    descripción ni del signo del número. Santander imprime el importe sin
    signo en las columnas Débito y Crédito, así que el signo no sirve; y la
    descripción miente: "Impuesto ley 25.413 credito 0,6%" es un DÉBITO
    cuando el saldo baja. Solo si no se puede resolver por saldo (falta el
    saldo anterior o hay ambigüedad) se recurre al signo explícito y, en
    último caso, a las palabras clave de clasificar_monto().
    """
    EPS = 0.01

    movimientos = []
    lineas = texto.split('\n')

    # Encabezado de la tabla de movimientos: reaparece al inicio de cada página
    pat_encabezado = re.compile(
        r'fecha\s+comprobante\s+movimiento\s+d[eé]bito\s+cr[eé]dito\s+saldo',
        re.IGNORECASE
    )
    # "Movimientos en pesos" / "Movimientos en dólares": arranque de sección
    pat_seccion = re.compile(r'movimientos\s+en\s+(pesos|d[oó]lares)', re.IGNORECASE)
    # Pies de sección: lo que viene después ya no son movimientos
    pat_fin_seccion = re.compile(
        r'saldo\s+total|detalle\s+impositivo|'
        r'tasas\s+de\s+acuerdos|unidad\s+de\s+informaci|condici[oó]n\s+mipyme|'
        r'fondos\s+comunes|los\s+dep[oó]sitos\s+en\s+pesos|'
        r'salvo\s+error|^\s*\d{1,2}\s*-\s*\d{1,2}\s*$',
        re.IGNORECASE
    )
    pat_fecha = re.compile(r'^(\d{2}/\d{2}/\d{2})(?:\s+(.*))?$')
    pat_monto = re.compile(r'(-?)\$\s*([\d.,]+)')
    pat_saldo_inicial = re.compile(r'saldo\s+inicial', re.IGNORECASE)
    pat_comprobante = re.compile(r'^(\d{3,9})\s+(\S.*)$')
    pat_moneda = re.compile(r'^\s*U\s*\$?\s*S\b|^US\$', re.IGNORECASE)

    dentro = False
    moneda = 'ARS'
    saldo_anterior = None      # saldo de arrastre para clasificar débito/crédito
    fecha_anticipada = None    # fecha suelta que corresponde a la fila siguiente
    fila_actual = None         # última fila agregada, para anexarle continuaciones

    for linea_raw in lineas:
        linea = linea_raw.strip()
        if not linea:
            continue

        # ── Control de sección ──────────────────────────────────────
        m_seccion = pat_seccion.search(linea)
        if m_seccion:
            dentro = True
            moneda = 'USD' if 'd' in m_seccion.group(1).lower() else 'ARS'
            saldo_anterior = None
            fecha_anticipada = None
            fila_actual = None
            continue

        if pat_encabezado.search(linea):
            dentro = True
            continue

        if not dentro:
            continue

        if pat_fin_seccion.search(linea):
            dentro = False
            fila_actual = None
            continue

        # ── Saldo inicial: no es un movimiento ──────────────────────
        if pat_saldo_inicial.search(linea):
            montos_ini = pat_monto.findall(linea)
            if montos_ini:
                signo_ini, valor_ini = montos_ini[-1]
                saldo_anterior = limpiar_monto(valor_ini)
                # El saldo de apertura puede venir negativo ("Saldo Inicial
                # -$ 38.126.749,24"): sin el signo, la cadena de saldos
                # arranca corrida y no cierra ningún movimiento posterior.
                if saldo_anterior is not None and signo_ini == '-':
                    saldo_anterior = -abs(saldo_anterior)
            continue

        # ── Fecha al inicio de la línea (con o sin contenido) ───────
        m_fecha = pat_fecha.match(linea)
        fecha_linea = m_fecha.group(1) if m_fecha else None
        resto = (m_fecha.group(2) or '').strip() if m_fecha else linea

        montos = list(pat_monto.finditer(resto))

        # ── Línea principal de fila: al menos 2 montos ───────────────
        if len(montos) >= 2:
            m_saldo = montos[-1]
            m_mov = montos[-2]

            desc_raw = resto[:m_mov.start()].strip()

            saldo = limpiar_monto(m_saldo.group(2))
            if saldo is not None and m_saldo.group(1) == '-':
                saldo = -abs(saldo)

            monto = limpiar_monto(m_mov.group(2))
            if monto is not None and m_mov.group(1) == '-':
                monto = -abs(monto)
            signo_explicito = m_mov.group(1) == '-'

            if monto is None or not desc_raw:
                continue

            # Comprobante: número suelto al inicio de la descripción
            referencia = ''
            m_comp = pat_comprobante.match(desc_raw)
            if m_comp:
                referencia = m_comp.group(1)
                desc_raw = m_comp.group(2).strip()

            # La sección de dólares imprime "U$S" pegado a la descripción
            desc_raw = pat_moneda.sub('', desc_raw).strip()

            # ── Clasificación por delta de saldo ────────────────────
            es_credito = None
            if saldo_anterior is not None and saldo is not None:
                delta = round(saldo - saldo_anterior, 2)
                if abs(delta - abs(monto)) < EPS and abs(delta + abs(monto)) >= EPS:
                    es_credito = True
                elif abs(delta + abs(monto)) < EPS and abs(delta - abs(monto)) >= EPS:
                    es_credito = False

            if es_credito is None:
                if signo_explicito:
                    es_credito = False
                else:
                    _, c_fallback = clasificar_monto(m_mov.group(2), abs(monto), desc_raw)
                    es_credito = c_fallback is not None

            if saldo is not None:
                saldo_anterior = saldo

            fila_actual = {
                'fecha': normalizar_fecha(fecha_linea or fecha_anticipada or ''),
                'descripcion': desc_raw,
                'referencia': referencia,
                'debito': None if es_credito else abs(monto),
                'credito': abs(monto) if es_credito else None,
                'saldo': saldo,
                'moneda': moneda,
                'tipo': 'C' if es_credito else 'D',
            }
            movimientos.append(fila_actual)
            fecha_anticipada = None
            continue

        # ── Fecha suelta: pertenece a la fila abierta, si aún no tiene ──
        if fecha_linea:
            if fila_actual is not None and not fila_actual['fecha']:
                fila_actual['fecha'] = normalizar_fecha(fecha_linea)
            else:
                fecha_anticipada = fecha_linea
            continue

        # ── Continuación de la descripción ──────────────────────────
        if fila_actual is not None and resto:
            fila_actual['descripcion'] = (fila_actual['descripcion'] + ' ' + resto).strip()

    return movimientos


# ─────────────────────────────────────────────
#  EXTRACCIÓN NACIÓN (DEDICADA)
# ─────────────────────────────────────────────

def extraer_nacion(texto):
    """
    Parser dedicado para resúmenes Banco Nación.
    Formato: [____] DD/MM/YY DESCRIPCION COMPROBANTE MONTO SALDO

    Clasificación débito/crédito: se deriva del propio saldo informado por
    el banco (saldo_actual = saldo_anterior ± monto), no del texto de la
    descripción. Un mismo tipo de movimiento (p.ej. "DEBIN <cuit>") puede
    ser débito o crédito según de quién sea el CUIT asociado, así que
    adivinar por prefijo de texto clasifica mal una porción grande de
    movimientos (todo lo que aparece bajo el propio CUIT del titular).
    Si no se puede resolver por saldo (falta saldo anterior o hay
    ambigüedad), se usa como respaldo la clasificación por prefijo.
    """
    movimientos = []
    lineas = texto.split('\n')

    pat_num = re.compile(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?)')
    pat_fecha = re.compile(r'^(\d{2}/\d{2}/\d{2})\s')
    pat_saldo_anterior = re.compile(r'SALDO\s+ANTERIOR\s+([\d.,]+-?)', re.IGNORECASE)

    # Prefijos de crédito, usados solo como respaldo cuando no hay saldo para comparar
    prefijos_credito = re.compile(
        r'^CR\s|'
        r'^LIQ\s|'
        r'^ACREDIT|'
        r'^DEPOSITO|'
        r'^DEP\.'
    , re.IGNORECASE)

    # Líneas a saltar (encabezados/pie de página).
    # Nota: NO incluye "banco", "nacion" ni "resumen": esas palabras
    # aparecen también en movimientos reales ("48HS. BANCOS", "COMIS.
    # CANJE O/BANCOS", "DB PM/TOT RESUMEN TCORP") y los descartaba por
    # error. El propio requisito de fecha al inicio de línea ya filtra
    # los encabezados/pies de página donde SÍ aparecen esas palabras
    # ("BANCO DE LA NACION ARGENTINA", "RESUMEN DE CUENTA", "FIN DE
    # RESUMEN"): ninguno de ellos empieza con una fecha DD/MM/YY.
    saltar_re = re.compile(
        r'transporte|saldo\s+anterior|fecha|movimientos|'
        r'comprob|debitos|creditos|saldo\s*$|'
        r'hoja:|cuit|sucursal|cuenta|'
        r'cbu|clave|suc:|iva|'
        r'pagina|siguiente|clav', re.IGNORECASE
    )

    EPS = 0.01
    saldo_prev = None

    for linea in lineas:
        linea = linea.strip()
        if not linea or len(linea) < 10:
            continue

        linea_lower = linea.lower()

        # Actualizar saldo de referencia cuando el resumen declara uno nuevo
        # (inicio del resumen, o inicio de una nueva cuenta dentro del PDF)
        m_saldo_ant = pat_saldo_anterior.search(linea)
        if m_saldo_ant:
            saldo_prev = limpiar_monto(m_saldo_ant.group(1))
            continue

        # Saltar líneas de ruido
        if saltar_re.search(linea_lower):
            continue

        # Saltear líneas que son solo ____ o solo transporting
        if re.match(r'^_+$', linea):
            continue
        if re.match(r'^transporte\s', linea_lower):
            continue

        # Quitar prefijo ____ si existe
        if linea.startswith('____'):
            linea = linea.lstrip('_').strip()

        # Buscar fecha al inicio
        match_fecha = pat_fecha.match(linea)
        if not match_fecha:
            continue

        fecha = match_fecha.group(1)
        resto = linea[match_fecha.end():]

        # Buscar todos los montos en el resto
        montos = pat_num.findall(resto)
        if len(montos) < 2:
            continue

        # Último monto = saldo, penúltimo = monto del movimiento
        saldo_str = montos[-1]
        monto_str = montos[-2]

        saldo = limpiar_monto(saldo_str)
        monto = limpiar_monto(monto_str)

        # La descripción es todo antes del penúltimo monto
        # Encontrar la posición del penúltimo monto en el string
        idx_monto = resto.rfind(monto_str)
        desc_con_comprob = resto[:idx_monto].strip()

        # Extraer comprobante: buscar número standalone (4-8 dígitos) que aparece
        # DESPUÉS de la descripción textual y ANTES del monto.
        # ESTRATEGIA: encontrar todos los integers standalone y tomar el último
        # que esté inmediatamente antes del monto (no confundir con CUIT).
        comprobante_final = ''
        # Buscar integers standalone (no parte de texto alfanumérico)
        integers_standalone = list(re.finditer(r'(?<![A-Za-z0-9])(\d{4,8})(?![A-Za-z0-9])', desc_con_comprob))

        if integers_standalone:
            # El comprobante es el último integer standalone
            ultimo_int = integers_standalone[-1]
            comprobante_final = ultimo_int.group(1)
            desc_limpia = desc_con_comprob[:ultimo_int.start()].strip()
        else:
            desc_limpia = desc_con_comprob

        if monto is None:
            continue

        # Clasificar débito/crédito comparando contra el delta real de saldo
        es_credito = None
        if saldo_prev is not None and saldo is not None:
            delta = round(saldo - saldo_prev, 2)
            coincide_credito = abs(delta - monto) < EPS
            coincide_debito = abs(delta + monto) < EPS
            if coincide_credito and not coincide_debito:
                es_credito = True
            elif coincide_debito and not coincide_credito:
                es_credito = False

        if es_credito is None:
            # Respaldo: sin saldo previo confiable, clasificar por prefijo
            es_credito = bool(prefijos_credito.match(desc_limpia))

        if saldo is not None:
            saldo_prev = saldo

        movimientos.append({
            'fecha': normalizar_fecha(fecha),
            'descripcion': desc_limpia,
            'referencia': comprobante_final,
            'debito': monto if not es_credito else None,
            'credito': monto if es_credito else None,
            'saldo': saldo,
            'moneda': 'ARS',
            'tipo': 'C' if es_credito else 'D',
        })

    return movimientos


# ─────────────────────────────────────────────
#  EXTRACCIÓN ICBC (DEDICADA)
# ─────────────────────────────────────────────

def extraer_icbc(texto):
    """
    Parser dedicado para resúmenes ICBC (Industrial and Commercial Bank of China).
    Formato: DD-MM CONCEPTO [COMPROBANTE] [ORIGEN] [CANAL] MONTO[-] [SALDO[-]]

    A diferencia de Banco Nación, acá el importe ya viene con signo explícito
    en el propio número (termina en "-" = débito, sin "-" = crédito), así que
    no hace falta adivinar el tipo por texto ni por delta de saldo.

    Lo que sí hay que arrastrar es el saldo corriente: el banco no lo imprime
    en todas las filas, solo en el último movimiento de cada agrupación
    (normalmente por día). Cuando no viene impreso, se calcula sumando el
    monto con signo al último saldo conocido.

    El PDF puede traer más de una cuenta (corriente en pesos, caja de
    ahorro, cuenta en dólares) una atrás de otra: cada sección nueva reinicia
    el saldo de arrastre con su propio "SALDO ULTIMO EXTRACTO"/"SALDO
    ANTERIOR" y puede cambiar de moneda.
    """
    movimientos = []
    lineas = texto.split('\n')

    pat_fecha = re.compile(r'^(\d{2})-(\d{2})\s+(.*)$')
    pat_num = re.compile(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?)')
    pat_saldo_inicial = re.compile(r'SALDO\s+(?:ULTIMO\s+EXTRACTO|ANTERIOR)\b', re.IGNORECASE)
    pat_periodo = re.compile(
        r'PERIODO\s+(\d{2})-(\d{2})-(\d{4})\s+AL\s+(\d{2})-(\d{2})-(\d{4})', re.IGNORECASE
    )
    pat_cuenta = re.compile(
        r'(?:CUENTA\s+CORRIENTE|CAJA\s+DE\s+AHORROS?)\s+EN\s+(PESOS|D[OÓ]LARES)', re.IGNORECASE
    )

    mes_inicio = anio_inicio = mes_fin = anio_fin = None
    saldo_prev = None
    moneda_actual = 'ARS'

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        m_periodo = pat_periodo.search(linea)
        if m_periodo:
            mes_inicio, anio_inicio = m_periodo.group(2), m_periodo.group(3)
            mes_fin, anio_fin = m_periodo.group(5), m_periodo.group(6)
            continue

        m_cuenta = pat_cuenta.search(linea)
        if m_cuenta:
            moneda_actual = 'USD' if 'lar' in m_cuenta.group(1).lower() else 'ARS'
            continue

        if pat_saldo_inicial.search(linea):
            montos_ini = pat_num.findall(linea)
            if montos_ini:
                saldo_prev = limpiar_monto(montos_ini[-1])
            continue

        match_fecha = pat_fecha.match(linea)
        if not match_fecha:
            continue

        dia, mes, resto = match_fecha.groups()

        montos = pat_num.findall(resto)
        if not montos:
            continue

        # Si hay 2+ números, el último es el saldo de cierre (no siempre presente)
        if len(montos) >= 2:
            monto_str = montos[-2]
            saldo_impreso = limpiar_monto(montos[-1])
        else:
            monto_str = montos[-1]
            saldo_impreso = None

        monto = limpiar_monto(monto_str)
        if monto is None:
            continue

        # Descripción = todo antes del monto, sin los números sueltos
        # de comprobante/origen (se guardan juntos en 'referencia')
        idx_monto = resto.rfind(monto_str)
        desc_con_refs = resto[:idx_monto].strip()

        pat_referencia = re.compile(r'(?<![A-Za-z0-9])\d{3,}(?![A-Za-z0-9,])')
        referencia = ' '.join(pat_referencia.findall(desc_con_refs))
        desc_limpia = pat_referencia.sub('', desc_con_refs)
        desc_limpia = re.sub(r'\s+', ' ', desc_limpia).strip()

        # El año no viene en la fecha (DD-MM): se infiere del período del resumen
        anio = anio_fin
        if mes_inicio and mes == mes_inicio:
            anio = anio_inicio
        elif mes_fin and mes == mes_fin:
            anio = anio_fin
        if not anio:
            anio = str(datetime.now().year)

        es_debito = monto < 0

        if saldo_impreso is not None:
            saldo_prev = saldo_impreso
        elif saldo_prev is not None:
            saldo_prev = round(saldo_prev + monto, 2)
        saldo_final = saldo_prev

        movimientos.append({
            'fecha': normalizar_fecha(f'{dia}/{mes}/{anio}'),
            'descripcion': desc_limpia,
            'referencia': referencia,
            'debito': abs(monto) if es_debito else None,
            'credito': abs(monto) if not es_debito else None,
            'saldo': saldo_final,
            'moneda': moneda_actual,
            'tipo': 'D' if es_debito else 'C',
        })

    return movimientos


# ─────────────────────────────────────────────
#  EXTRACCIÓN GENÉRICA AGRESIVA
# ─────────────────────────────────────────────

def extraccion_generica(texto):
    """
    Detecta líneas con patrón: fecha + texto + números.
    Funciona con cualquier banco sin configuración.
    """
    movimientos = []
    lineas = texto.split('\n')

    # Patrones de fecha comunes
    pat_fecha = re.compile(r'\b(\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?)\b')
    pat_monto = re.compile(r'\b([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b')

    for linea in lineas:
        linea = linea.strip()
        if len(linea) < 15:
            continue

        fechas = pat_fecha.findall(linea)
        if not fechas:
            continue

        montos = pat_monto.findall(linea)
        if not montos:
            continue

        # Quitar la fecha del texto para obtener descripción
        descripcion = pat_fecha.sub('', linea).strip()
        descripcion = re.sub(r'\s+', ' ', descripcion)

        # Usar últimos 1-2 números como montos/saldo
        valores = [limpiar_monto(m) for m in montos[-3:] if limpiar_monto(m) is not None]
        if not valores:
            continue

        mov = {
            'fecha': normalizar_fecha(fechas[0]),
            'descripcion': descripcion[:120],
            'referencia': '',
            'debito': None,
            'credito': None,
            'saldo': None,
            'moneda': 'ARS',
            'tipo': '',
            'raw': linea
        }

        if len(valores) >= 2:
            mov['credito'] = valores[-2]
            mov['saldo'] = valores[-1]
        elif len(valores) == 1:
            mov['credito'] = valores[0]

        movimientos.append(mov)

    return movimientos


# ─────────────────────────────────────────────
#  EXTRACCIÓN BBVA (DEDICADA)
# ─────────────────────────────────────────────

def extraer_bbva(texto):
    """
    Parser dedicado para resúmenes BBVA.
    Formato: DD/MM [ORIGEN] CONCEPTO IMPORTE SALDO

    El importe ya viene con signo: positivo = crédito, negativo = débito.
    """
    movimientos = []
    lineas = texto.split('\n')

    pat_mov = re.compile(
        r'^(\d{2}/\d{2})\s+(.+?)\s+'
        r'(-?\d[\d\.]*,\d{2})\s+'
        r'(-?\d[\d\.]*,\d{2})$'
    )
    pat_saldo_ant = re.compile(r'SALDO\s+ANTERIOR\s+([\d\.]+,\d{2})', re.IGNORECASE)
    pat_cuenta = re.compile(r'CC\s+\$\s+([\d\-/]+)\s+\(([^)]+)\)', re.IGNORECASE)
    pat_cbu = re.compile(r'CBU\s+(\d[\d\s]+)')
    pat_sep = re.compile(r'^-+$')

    ruido = [
        'feecha origen', 'detalle', 'saldo al', 'total mov',
        'total cobrado', 'total dev', 'imp. neto',
        'sobre (', 'página', 'legales', 'importante',
        'usted puede', 'http', 'cuenta pyme', 'intervinientes',
        'mantenimiento', 'movimientos', 'bonificaciones',
        'consolidado', 'inversiones', 'transferencias',
        'débitos automáticos', 'realizados', 'recibidas',
        'saldos disponibles', 'operaciones realizadas',
        '3-91300005', 'orn', 'tiuc', 'otpircsni',
        'elbasnopser', 'avi', 'anitnegra', 'avbb', 'ocnab',
        '(cid:', 'fecha venc', 'cta. títulos',
        'fba renpeb', 'total saldos', 'total de inversion',
        'valorizadas', 'saldo consolidado',
    ]

    saldo_prev = None
    cuenta_actual = ''
    moneda_actual = 'ARS'
    year = None

    # Detectar año
    m_year = re.search(r'20\d{2}', texto[:2000])
    if m_year:
        year = m_year.group(0)

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        # Detectar cuenta
        m_cuenta = pat_cuenta.search(linea)
        if m_cuenta:
            cuenta_actual = m_cuenta.group(1)
            continue

        # Detectar moneda
        if 'DOLARES' in linea.upper():
            moneda_actual = 'USD'
        elif 'PESOS' in linea.upper() or 'CC $' in linea:
            moneda_actual = 'ARS'

        # Detectar CBU
        m_cbu = pat_cbu.search(linea)
        if m_cbu:
            continue

        # Saldo anterior
        m_sal = pat_saldo_ant.search(linea)
        if m_sal:
            saldo_prev = limpiar_monto(m_sal.group(1))
            continue

        # Saltar ruido
        linea_lower = linea.lower()
        if any(kw in linea_lower for kw in ruido):
            continue
        if pat_sep.match(linea):
            continue

        # Parsear movimiento
        m = pat_mov.match(linea)
        if not m:
            continue

        fecha_ddmm = m.group(1)
        concepto = m.group(2).strip()
        importe_str = m.group(3)
        saldo_str = m.group(4)

        importe = limpiar_monto(importe_str)
        saldo = limpiar_monto(saldo_str)

        if importe is None or saldo is None:
            continue

        fecha_completa = f"{fecha_ddmm}/{year}" if year else fecha_ddmm

        # Clasificar por signo del importe
        es_credito = importe >= 0

        movimientos.append({
            'fecha': normalizar_fecha(fecha_completa),
            'descripcion': concepto,
            'debito': abs(importe) if not es_credito else None,
            'credito': abs(importe) if es_credito else None,
            'saldo': saldo,
            'moneda': moneda_actual,
            'tipo': 'C' if es_credito else 'D',
            'cuenta': cuenta_actual,
        })

        saldo_prev = saldo

    return movimientos


# ─────────────────────────────────────────────
#  EXTRACCIÓN MACRO (DEDICADA)
# ─────────────────────────────────────────────

def extraer_macro(texto):
    """
    Parser dedicado para resúmenes Banco Macro.
    Formato: DD/MM/YY DESCRIPCION [REFERENCIA] MONTO SALDO

    Clasificación débito/crédito: por delta de saldo entre filas
    de la misma cuenta. El PDF puede tener múltiples cuentas.
    """
    movimientos = []
    lineas = texto.split('\n')

    pat_mov_2m = re.compile(
        r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+'
        r'(\d[\d\.]*,\d{2})\s+'
        r'(-?\d[\d\.]*,\d{2})$'
    )
    pat_mov_1m = re.compile(
        r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+'
        r'(-?\d[\d\.]*,\d{2})\s+'
        r'(-?\d[\d\.]*,\d{2})$'
    )
    pat_saldo_ant = re.compile(
        r'SALDO\s+(?:ULTIMO\s+EXTRACTO|ANTERIOR)\s+AL\s+\d{2}/\d{2}/\d{4}\s+([\d\.]+,\d{2})',
        re.IGNORECASE
    )
    pat_cuenta = re.compile(
        r'CUENTA\s+(?:CORRIENTE|CAJA)\s+(?:ESPECIAL\s+EN\s+)?(?:DOLARES|PESOS|BANCARIA)\s+NRO\.?:\s*([\d\-]+)',
        re.IGNORECASE
    )
    pat_moneda = re.compile(
        r'(?:CUENTA\s+CORRIENTE\s+(?:ESPECIAL\s+EN\s+)?)(DOLARES|PESOS)',
        re.IGNORECASE
    )
    pat_sep = re.compile(r'^-+$')

    ruido = [
        'sucursal', 'sr(es)', 'carril', 'rodriguez',
        'resumen', 'periodo', 'hoja', 'saldos consolidados',
        'saldo cuentas', 'informacion', 'clave bancaria',
        'tasa nom', 'tasa efc', 'detalle de movimiento',
        'total cobrado', 'estimado cliente', 'los depositos',
        'ley 24.485', 'd. 409/2018', 'cuenta corriente',
        'fecha descripcion', 'saldo final', 'cantidad',
        'imp.s/creds', 'transf. macronline',
    ]

    saldos_por_cuenta = {}
    cuenta_actual = ''
    moneda_actual = 'ARS'
    year = None

    # Detectar año
    m_year = re.search(r'Periodo del Extracto:.*?(\d{4})', texto[:2000])
    if m_year:
        year = m_year.group(1)
    else:
        m_year2 = re.search(r'20\d{2}', texto[:2000])
        if m_year2:
            year = m_year2.group(0)

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        # Detectar cuenta
        m_cuenta = pat_cuenta.search(linea)
        if m_cuenta:
            cuenta_actual = m_cuenta.group(1)
            continue

        # Detectar moneda
        m_mon = pat_moneda.search(linea)
        if m_mon:
            moneda_actual = 'USD' if 'DOLARES' in m_mon.group(1).upper() else 'ARS'
            continue

        # Saldo anterior
        m_sal = pat_saldo_ant.search(linea)
        if m_sal:
            saldo_prev = limpiar_monto(m_sal.group(1))
            if cuenta_actual:
                saldos_por_cuenta[cuenta_actual] = saldo_prev
            continue

        # Saltar ruido
        linea_lower = linea.lower()
        if any(kw in linea_lower for kw in ruido):
            continue
        if pat_sep.match(linea):
            continue
        if 'sin movimientos' in linea_lower:
            continue

        # Intentar con 2 montos (referencia + monto)
        m2 = pat_mov_2m.match(linea)
        if m2:
            fecha = m2.group(1)
            desc_completa = m2.group(2).strip()
            monto_str = m2.group(3)
            saldo_str = m2.group(4)

            monto = limpiar_monto(monto_str)
            saldo = limpiar_monto(saldo_str)

            if monto is not None and saldo is not None:
                ref_match = re.search(r'\s+(\d{5,})\s*$', desc_completa)
                referencia = ''
                if ref_match:
                    referencia = ref_match.group(1)
                    desc_limpia = desc_completa[:ref_match.start()].strip()
                else:
                    desc_limpia = desc_completa

                tipo = 'D'
                saldo_ant = saldos_por_cuenta.get(cuenta_actual)
                if saldo_ant is not None:
                    delta = round(saldo - saldo_ant, 2)
                    if abs(delta - monto) < 0.01:
                        tipo = 'C'
                    elif abs(delta + monto) < 0.01:
                        tipo = 'D'

                fecha_completa = fecha
                if year and '/' in fecha:
                    parts = fecha.split('/')
                    if len(parts) == 3 and len(parts[2]) == 2:
                        fecha_completa = f"{parts[0]}/{parts[1]}/{year}"

                movimientos.append({
                    'fecha': normalizar_fecha(fecha_completa),
                    'descripcion': desc_limpia,
                    'referencia': referencia,
                    'debito': monto if tipo == 'D' else None,
                    'credito': monto if tipo == 'C' else None,
                    'saldo': saldo,
                    'moneda': moneda_actual,
                    'tipo': tipo,
                    'cuenta': cuenta_actual,
                })
                saldos_por_cuenta[cuenta_actual] = saldo
            continue

        # Intentar con 1 monto
        m1 = pat_mov_1m.match(linea)
        if m1:
            fecha = m1.group(1)
            desc_completa = m1.group(2).strip()
            monto_str = m1.group(3)
            saldo_str = m1.group(4)

            monto = limpiar_monto(monto_str)
            saldo = limpiar_monto(saldo_str)

            if monto is not None and saldo is not None:
                ref_match = re.search(r'\s+(\d{5,})\s*$', desc_completa)
                referencia = ''
                if ref_match:
                    referencia = ref_match.group(1)
                    desc_limpia = desc_completa[:ref_match.start()].strip()
                else:
                    desc_limpia = desc_completa

                tipo = 'D'
                saldo_ant = saldos_por_cuenta.get(cuenta_actual)
                if saldo_ant is not None:
                    delta = round(saldo - saldo_ant, 2)
                    if abs(delta - monto) < 0.01:
                        tipo = 'C'
                    elif abs(delta + monto) < 0.01:
                        tipo = 'D'

                fecha_completa = fecha
                if year and '/' in fecha:
                    parts = fecha.split('/')
                    if len(parts) == 3 and len(parts[2]) == 2:
                        fecha_completa = f"{parts[0]}/{parts[1]}/{year}"

                movimientos.append({
                    'fecha': normalizar_fecha(fecha_completa),
                    'descripcion': desc_limpia,
                    'referencia': referencia,
                    'debito': monto if tipo == 'D' else None,
                    'credito': monto if tipo == 'C' else None,
                    'saldo': saldo,
                    'moneda': moneda_actual,
                    'tipo': tipo,
                    'cuenta': cuenta_actual,
                })
                saldos_por_cuenta[cuenta_actual] = saldo

    return movimientos


# ─────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────

def extraer_titular(texto: str) -> str:
    """
    Extrae el titular (nombre del cliente) del texto del PDF.
    Estrategias:
    1. Línea anterior a CUIT: contiene el nombre
    2. Santander: línea después de 'Período' o antes de 'Desde:'
    3. Nación: después de 'SUC:XXX' hay nombre del titular
    """
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]

    # Estrategia 1: Santander - buscar línea que contiene 'Desde:'
    for linea in lineas:
        if 'desde:' in linea.lower():
            # El nombre puede estar antes de 'Desde:' en la misma línea
            partes = re.split(r'\s*Desde:', linea, flags=re.IGNORECASE)
            if partes:
                candidato = partes[0].strip()
                if re.match(r'^[A-ZÁÉÍÓÚÜ\s\.]+$', candidato) and len(candidato) > 3:
                    return candidato
            # O en la línea anterior
            idx = lineas.index(linea)
            if idx > 0:
                candidato = lineas[idx - 1].strip()
                if re.match(r'^[A-ZÁÉÍÓÚÜ\s\.]+$', candidato) and len(candidato) > 3:
                    return candidato

    # Estrategia 2: Nación - después de 'SUC:XXX' viene el nombre
    pat_suc = re.compile(r'^SUC:\d+')
    for i, linea in enumerate(lineas):
        if pat_suc.match(linea) and i + 1 < len(lineas):
            candidato = lineas[i + 1].strip()
            if re.match(r'^[A-ZÁÉÍÓÚÜ\s\.]+$', candidato) and len(candidato) > 3:
                return candidato

    # Estrategia 3: buscar CUIT y tomar la línea anterior
    pat_cuit = re.compile(r'CUIT[:\s]*[\d]{2}-[\d]{8}-[\d]')
    for i, linea in enumerate(lineas):
        if pat_cuit.search(linea) and i > 0:
            candidato = lineas[i - 1].strip()
            if re.match(r'^[A-ZÁÉÍÓÚÜ\s\.]+$', candidato) and len(candidato) > 3:
                return candidato

    # Estrategia 4: buscar líneas que parezcan nombre de empresa/persona
    # (solo mayúsculas, letras, espacios, al menos 2 palabras). La primera
    # palabra debe tener 2+ letras (para no matchear headers con letras
    # sueltas separadas por espacios, ej. "M E N D O Z A"), pero las
    # siguientes admiten 1 letra para no descartar razones sociales con
    # conectores cortos ("Y", "DE"), ej. "ARAMENDI Y ASOCIADOS SA".
    excluir = ['banco', 'nacion', 'santander', 'resumen', 'cuenta', 'periodo', 'sucursal']
    for linea in lineas[:15]:
        if re.match(r'^[A-ZÁÉÍÓÚÜ]{2,}(\s+[A-ZÁÉÍÓÚÜ]{1,})+$', linea):
            if not any(p in linea.lower() for p in excluir):
                return linea

    return ''

def limpiar_monto(valor):
    """Convierte string de monto a float. Ej: '1.234,56' → 1234.56"""
    if valor is None:
        return None
    valor = str(valor).strip().replace(' ', '')
    if not valor or valor in ['-', '—', '']:
        return None

    # Detectar signo
    negativo = valor.startswith('-') or valor.endswith('-')
    valor = valor.replace('-', '').replace('(', '').replace(')', '')

    try:
        # Formato argentino: punto miles, coma decimal
        if re.match(r'^\d{1,3}(\.\d{3})*(,\d+)?$', valor):
            valor = valor.replace('.', '').replace(',', '.')
        # Formato anglosajón: coma miles, punto decimal
        elif re.match(r'^\d{1,3}(,\d{3})*(\.\d+)?$', valor):
            valor = valor.replace(',', '')
        # Solo dígitos y punto
        else:
            valor = valor.replace(',', '.')

        num = float(valor)
        return -num if negativo else num
    except ValueError:
        return None


def clasificar_monto(monto_str, monto_num, descripcion):
    """Determina si un monto es débito o crédito"""
    if monto_num is None:
        return None, None

    monto_str = str(monto_str)
    desc_lower = descripcion.lower()

    # Signos explícitos
    if monto_str.startswith('-') or monto_str.endswith('-') or '(' in monto_str:
        return abs(monto_num), None

    # Palabras clave en descripción
    palabras_debito = ['pago', 'compra', 'debito', 'débito', 'retiro', 'extraccion',
                       'transferencia enviada', 'egreso', 'cargo', 'comision']
    palabras_credito = ['deposito', 'depósito', 'acreditacion', 'acreditación',
                        'credito', 'crédito', 'transferencia recibida', 'ingreso', 'haberes']

    if any(p in desc_lower for p in palabras_debito):
        return monto_num, None
    if any(p in desc_lower for p in palabras_credito):
        return None, monto_num

    # Por defecto, asumir monto sin clasificar
    return None, monto_num


def normalizar_fecha(fecha_str):
    """Normaliza fecha a formato DD/MM/YYYY"""
    if not fecha_str:
        return fecha_str
    fecha_str = str(fecha_str).strip()

    formatos = ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d/%m',
                '%Y-%m-%d', '%d-%m-%y', '%d.%m.%Y']

    for fmt in formatos:
        try:
            dt = datetime.strptime(fecha_str, fmt)
            if dt.year == 1900:  # Fecha sin año
                dt = dt.replace(year=datetime.now().year)
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            continue

    return fecha_str  # Devolver tal cual si no se pudo parsear
