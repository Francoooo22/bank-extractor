"""
Tests para el módulo extractor.py
Verifica funciones de normalización y clasificación
"""

import pytest
from extractor import (
    limpiar_monto,
    normalizar_fecha,
    clasificar_monto,
    detectar_banco,
)


class TestLimpiarMonto:
    """Tests para la función limpiar_monto"""

    def test_formato_argentino(self):
        """Formato: 1.234,56 (punto miles, coma decimal)"""
        assert limpiar_monto("1.234,56") == 1234.56
        assert limpiar_monto("1.000,00") == 1000.0
        assert limpiar_monto("10.000,99") == 10000.99

    def test_formato_anglosajón(self):
        """Formato: 1,234.56 (coma miles, punto decimal)"""
        assert limpiar_monto("1,234.56") == 1234.56
        assert limpiar_monto("1,000.00") == 1000.0

    def test_numeros_simples(self):
        """Números sin separadores"""
        assert limpiar_monto("100") == 100.0
        assert limpiar_monto("99.99") == 99.99

    def test_valores_negativos(self):
        """Números con signo negativo"""
        assert limpiar_monto("-1500") == -1500.0
        assert limpiar_monto("-1.234,56") == -1234.56
        # Nota: formato (1500) se interpreta como 1500 (sin signo)
        # Para formato "entre paréntesis negativo" usar "-1500"

    def test_valores_invalidos(self):
        """Valores que no se pueden convertir"""
        assert limpiar_monto(None) is None
        assert limpiar_monto("") is None
        assert limpiar_monto("-") is None
        assert limpiar_monto("abc") is None

    def test_espacios_en_blanco(self):
        """Valores con espacios"""
        assert limpiar_monto("  1500  ") == 1500.0
        assert limpiar_monto("1 234,56") == 1234.56


class TestNormalizarFecha:
    """Tests para la función normalizar_fecha"""

    def test_formato_dd_mm_yyyy(self):
        """Formato: DD/MM/YYYY"""
        assert normalizar_fecha("15/07/2024") == "15/07/2024"
        assert normalizar_fecha("01/01/2024") == "01/01/2024"

    def test_formato_dd_mm_yy(self):
        """Formato: DD/MM/YY (2 dígitos)"""
        resultado = normalizar_fecha("15/07/24")
        assert "15/07/" in resultado  # año completo

    def test_formato_guión(self):
        """Formato: DD-MM-YYYY"""
        assert normalizar_fecha("15-07-2024") == "15/07/2024"

    def test_formato_iso(self):
        """Formato: YYYY-MM-DD"""
        assert normalizar_fecha("2024-07-15") == "15/07/2024"

    def test_sin_año(self):
        """Formato: DD/MM (sin año)"""
        resultado = normalizar_fecha("15/07")
        assert "/07/" in resultado  # tiene algo en medio

    def test_valor_vacio(self):
        """Valores vacíos"""
        assert normalizar_fecha("") == ""
        assert normalizar_fecha(None) is None


class TestClasificarMonto:
    """Tests para la función clasificar_monto"""

    def test_débito_por_signo(self):
        """Clasificar como débito por signo negativo"""
        debito, credito = clasificar_monto("-1500", -1500, "COMPRA")
        assert debito == 1500
        assert credito is None

    def test_crédito_por_defecto(self):
        """Sin signos, clasificar como crédito"""
        debito, credito = clasificar_monto("1500", 1500, "TRANSFERENCIA")
        assert debito is None
        assert credito == 1500

    def test_débito_por_palabras_clave(self):
        """Clasificar como débito por descripción"""
        debito, credito = clasificar_monto("1500", 1500, "PAGO FACTURA")
        assert debito == 1500
        assert credito is None

        debito, credito = clasificar_monto("1500", 1500, "COMPRA ONLINE")
        assert debito == 1500

        debito, credito = clasificar_monto("1500", 1500, "RETIRO CAJERO")
        assert debito == 1500

    def test_crédito_por_palabras_clave(self):
        """Clasificar como crédito por descripción"""
        debito, credito = clasificar_monto("1500", 1500, "DEPÓSITO")
        assert debito is None
        assert credito == 1500

        debito, credito = clasificar_monto("1500", 1500, "ACREDITACIÓN SALARIO")
        assert debito is None
        assert credito == 1500

        debito, credito = clasificar_monto("1500", 1500, "TRANSFERENCIA RECIBIDA")
        assert debito is None
        assert credito == 1500

    def test_none_value(self):
        """Valor None"""
        debito, credito = clasificar_monto("abc", None, "TRANSFERENCIA")
        assert debito is None
        assert credito is None


class TestDetectarBanco:
    """Tests para la función detectar_banco"""

    def test_detectar_galicia(self):
        """Detectar Banco Galicia"""
        assert detectar_banco("Banco Galicia - Estado de Cuenta") == "galicia"
        assert detectar_banco("GALICIA") == "galicia"

    def test_detectar_santander(self):
        """Detectar Santander"""
        assert detectar_banco("Banco Santander Río") == "santander"
        assert detectar_banco("SANTANDER") == "santander"

    def test_detectar_bbva(self):
        """Detectar BBVA"""
        assert detectar_banco("BBVA Banco Francés") == "bbva"
        assert detectar_banco("FRANCES") == "bbva"

    def test_detectar_macro(self):
        """Detectar Macro"""
        assert detectar_banco("Banco Macro S.A.") == "macro"

    def test_detectar_nacion(self):
        """Detectar Banco Nación"""
        assert detectar_banco("Banco de la nacion") == "nacion"
        assert detectar_banco("BNA") == "nacion"
        assert detectar_banco("nacion argentina") == "nacion"

    def test_detectar_generico(self):
        """Si no detecta, devuelve genérico"""
        assert detectar_banco("Documento de pago") == "generico"
        assert detectar_banco("") == "generico"

    def test_case_insensitive(self):
        """Detección case-insensitive"""
        assert detectar_banco("banco galicia") == "galicia"
        assert detectar_banco("GALICIA") == "galicia"


# ─────────────────────────────────────────────
#  Tests de Integración
# ─────────────────────────────────────────────

class TestIntegracion:
    """Tests que verifican flujos completos"""

    def test_flujo_normalización(self):
        """Verificar flujo: monto → limpiar → clasificar"""
        monto = limpiar_monto("1.234,56")
        assert monto == 1234.56

        debito, credito = clasificar_monto("1.234,56", monto, "PAGO TARJETA")
        assert debito == 1234.56

    def test_flujo_fecha_y_monto(self):
        """Verificar flujo: procesar fecha y monto"""
        fecha = normalizar_fecha("15/07/24")
        monto = limpiar_monto("10.000,50")

        assert "/2024" in fecha or "/24" in fecha
        assert monto == 10000.50
