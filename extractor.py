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
    'santander': {
        'movimiento': re.compile(
            r'(\d{2}-\d{2}-\d{4})\s+(.+?)\s+([\d.,]+[-]?)\s+([\d.,]+)',
            re.IGNORECASE
        ),
        'fecha_fmt': '%d-%m-%Y',
    },
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

    # Intentar primero con tablas estructuradas
    movimientos = []
    if todas_tablas:
        movimientos = extraer_de_tablas(todas_tablas, banco_detectado)

    # Si no hubo éxito con tablas, usar regex sobre texto
    if not movimientos:
        movimientos = extraer_de_texto(texto_completo, banco_detectado)

    # Si aún sin resultados, usar extracción genérica agresiva
    if not movimientos:
        movimientos = extraccion_generica(texto_completo)

    return {
        'movimientos': movimientos,
        'info': {
            'banco': banco_detectado,
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
        'santander': ['santander', 'rio'],
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
                'debito': debito,
                'credito': credito,
                'saldo': saldo_num,
                'tipo': 'D' if debito else 'C',
                'raw': linea
            })
        except Exception:
            continue

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
            'raw': linea
        }

        if len(valores) >= 2:
            # Asumir penúltimo = movimiento, último = saldo
            mov['importe'] = valores[-2]
            mov['saldo'] = valores[-1]
        elif len(valores) == 1:
            mov['importe'] = valores[0]

        movimientos.append(mov)

    return movimientos


# ─────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────

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
