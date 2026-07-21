"""
Motor de extracción de resúmenes bancarios
Soporta: Galicia, Santander, BBVA, Macro, HSBC, Banco Nación, Genérico
"""

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

    with pdfplumber.open(ruta_pdf) as pdf:
        paginas_texto = []
        todas_tablas = []

        for page in pdf.pages:
            texto = page.extract_text() or ''
            paginas_texto.append(texto)

            # Intentar extracción por tablas
            tablas = page.extract_tables()
            if tablas:
                todas_tablas.extend(tablas)

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

    # Si no hubo éxito con tablas, usar regex sobre texto
    if not movimientos:
        movimientos = extraer_de_texto(texto_completo, banco_detectado)

    # Si aún sin resultados, usar extracción genérica agresiva
    if not movimientos:
        movimientos = extraccion_generica(texto_completo)

    # Agregar titular y unificar importe
    for mov in movimientos:
        if titular:
            mov['titular'] = titular
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
        },
        'texto_muestra': texto_completo[:2000]
    }


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
        'icbc': ['icbc'],
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
    Parser dedicado para resúmenes Santander.
    Cada línea con montos es un movimiento independiente.
    Formato: [DD/MM/YY] [comprobante] Descripción $ monto $ saldo
    Negativos: -$ monto. USD: U$S monto.
    """
    movimientos = []
    lineas = texto.split('\n')

    pat_fecha = re.compile(r'^(\d{2}/\d{2}/\d{2})\s')
    pat_monto_pesos = re.compile(r'(-?)[$]\s*([\d.,]+)')
    pat_monto_usd = re.compile(r'(-?)U[$]S\s*([\d.,]+)')

    en_seccion_pesos = True
    fecha_actual = None

    for linea in lineas:
        linea = linea.strip()
        if not linea or len(linea) < 5:
            continue

        linea_lower = linea.lower()

        if 'movimientos en dólares' in linea_lower or 'movimientos en dolares' in linea_lower:
            en_seccion_pesos = False
            continue

        if any(kw in linea_lower for kw in [
            'detalle impositivo', 'tarjeta de débito', 'tarjeta de debito',
            'tipo de impuesto', 'totales de retencion', 'así usaste tu dinero',
            'compras en el período', 'pagos en el período', 'pagos totales',
            'monto total', 'total en pesos', 'total en dólares',
            'fecha comprobante movimiento', 'caja de ahorro',
            'cuenta corriente', 'saldo en cuenta', 'saldo total',
            'período', 'desde:', 'hasta:', 'mi resumen',
            'tarjetas', 'superclub', 'banco santander',
            'consumidor final', 'cbu:', 'cuit:', 'cuenta ',
            'importes en', 'impuesto ley', 'iva 21%',
            'comision', 'regimen de recaudacion',
            'pago interes', 'seguro de vida',
            'resp:', 'débito',
        ]):
            continue

        # Elegir patrón según sección
        pat_monto = pat_monto_pesos if en_seccion_pesos else pat_monto_usd
        montos_matches = list(pat_monto.finditer(linea))

        if not montos_matches:
            continue

        # Detectar fecha
        match_fecha = pat_fecha.match(linea)
        if match_fecha:
            fecha_actual = match_fecha.group(1)
            resto = linea[match_fecha.end():]
            montos_matches = list(pat_monto.finditer(resto))
            primer_monto = montos_matches[0] if montos_matches else None
            if primer_monto:
                desc_raw = resto[:primer_monto.start()].strip()
            else:
                desc_raw = resto.strip()
        else:
            desc_raw = linea
            for m in reversed(montos_matches):
                desc_raw = desc_raw[:m.start()]
            desc_raw = desc_raw.strip()

        # Extraer comprobante (número al inicio de desc_raw)
        comprobante = ''
        match_comprob = re.match(r'^(\d+)\s', desc_raw)
        if match_comprob:
            comprobante = match_comprob.group(1)

        desc_limpia = re.sub(r'^\d+\s+', '', desc_raw).strip()

        saldo = None
        monto_num = None
        es_debito = False

        if len(montos_matches) >= 2:
            saldo = limpiar_monto(montos_matches[-1].group(2))
            monto_str = montos_matches[-2].group(2)
            es_debito = montos_matches[-2].group(1) == '-'
        elif len(montos_matches) == 1:
            monto_str = montos_matches[0].group(2)
            es_debito = montos_matches[0].group(1) == '-'

        monto_num = limpiar_monto(monto_str) if monto_str else None

        if monto_num is not None:
            debito = abs(monto_num) if es_debito else None
            credito = monto_num if not es_debito else None
        else:
            debito = None
            credito = None

        moneda = 'USD' if not en_seccion_pesos else 'ARS'

        # Filtrar ruido: sin fecha y monto muy pequeño (< 100) o sin descripción
        if not fecha_actual:
            continue
        if monto_num is not None and abs(monto_num) < 100 and not desc_limpia:
            continue

        movimientos.append({
            'fecha': normalizar_fecha(fecha_actual) if fecha_actual else '',
            'descripcion': desc_limpia,
            'referencia': comprobante,
            'debito': debito,
            'credito': credito,
            'saldo': saldo,
            'moneda': moneda,
            'tipo': 'D' if debito else ('C' if credito else ''),
        })

    return movimientos


# ─────────────────────────────────────────────
#  EXTRACCIÓN NACIÓN (DEDICADA)
# ─────────────────────────────────────────────

def extraer_nacion(texto):
    """
    Parser dedicado para resúmenes Banco Nación.
    Formato: [____] DD/MM/YY DESCRIPCION COMPROBANTE MONTO SALDO

    Clasificación débito/crédito por prefijo de descripción:
    - CR ... = crédito
    - DEBIN, DEB, GRAVAMEN, REG.REC.SIRCREB, COMIS., I.V.A., RETEN., CAM.FED = débito
    - TRANSF. INTERBANCARIAS = débito
    """
    movimientos = []
    lineas = texto.split('\n')

    pat_num = re.compile(r'(\d{1,3}(?:\.\d{3})*,\d{2})')
    pat_num_entero = re.compile(r'(\d{4,})')
    pat_fecha = re.compile(r'^(\d{2}/\d{2}/\d{2})\s')

    # Prefijos de crédito (todo lo demás es débito)
    prefijos_credito = re.compile(
        r'^CR\s|'
        r'^LIQ\s|'
        r'^ACREDIT|'
        r'^DEPOSITO|'
        r'^DEP\.'
    , re.IGNORECASE)

    # Líneas a saltar
    saltar_re = re.compile(
        r'transporte|saldo\s+anterior|fecha|movimientos|'
        r'comprob|debitos|creditos|saldo\s*$|'
        r'hoja:|cuit|sucursal|banco|nacion|cuenta|'
        r'resumen|cbu|clave|suc:|iva|'
        r'pagina|siguiente|clav', re.IGNORECASE
    )

    for linea in lineas:
        linea = linea.strip()
        if not linea or len(linea) < 10:
            continue

        linea_lower = linea.lower()

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

        # Clasificar débito/crédito por prefijo
        es_credito = bool(prefijos_credito.match(desc_limpia))

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
    # (solo mayúsculas, letras, espacios, al menos 2 palabras)
    excluir = ['banco', 'nacion', 'santander', 'resumen', 'cuenta', 'periodo']
    for linea in lineas[:15]:
        if re.match(r'^[A-ZÁÉÍÓÚÜ]{2,}(\s+[A-ZÁÉÍÓÚÜ]{2,})+$', linea):
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
