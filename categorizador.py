"""Categorización de movimientos bancarios por tipo de concepto."""

import unicodedata

CATEGORIAS = [
    "Transferencias recibidas",
    "Transferencias emitidas",
    "Gastos bancarios / aranceles",
    "Impuestos",
    "Pagos de servicios",
    "Extracciones / Depósitos efectivo",
    "Otros débitos",
    "Otros créditos",
]

_KEYWORDS_GASTOS = ["comision", "arancel", "mantenimiento", "gasto banc"]
_KEYWORDS_IMPUESTOS = ["iva", "impuesto", "ley 25413", "percepcion", "retencion"]
_KEYWORDS_SERVICIOS = ["debito automatico", "pago serv", "factura"]
_KEYWORDS_EFECTIVO = ["extraccion", "cajero", "atm", "deposito efectivo"]


def _normalizar(texto):
    """Minúsculas y sin acentos, para matchear keywords de forma robusta."""
    texto = (texto or "").lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def categorizar(descripcion, tipo):
    """Clasifica un movimiento en una de las CATEGORIAS según su descripción y tipo (D/C).

    Si `tipo` no es 'D' ni 'C' (dato faltante), se asume débito por defecto.
    """
    desc = _normalizar(descripcion)
    es_credito = tipo == "C"

    if "transfer" in desc:
        return "Transferencias recibidas" if es_credito else "Transferencias emitidas"
    if any(k in desc for k in _KEYWORDS_GASTOS):
        return "Gastos bancarios / aranceles"
    if any(k in desc for k in _KEYWORDS_IMPUESTOS):
        return "Impuestos"
    if any(k in desc for k in _KEYWORDS_SERVICIOS):
        return "Pagos de servicios"
    if any(k in desc for k in _KEYWORDS_EFECTIVO):
        return "Extracciones / Depósitos efectivo"

    return "Otros créditos" if es_credito else "Otros débitos"
