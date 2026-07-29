"""
Tests para el módulo extractor_seguros.py
Verifica extracción de pólizas de seguro y limpieza de texto
"""

import pytest
import os
import tempfile
from extractor_seguros import (
    ROW_PATTERN,
    HEADER_PATTERNS,
    limpiar_header,
    limpiar_texto_asegurado,
    extraer_resumen_seguros,
)


class TestRowPattern:
    """Tests para el patrón de extracción de filas"""

    def test_linea_valida_completa(self):
        línea = "144,467/00001/06/2026 31/12/2026 $ 52.423,70 T 01/07/2026 0.00 325,807Guiñazu Yohana bel1e5n49 Colegio Rivadavia"
        m = ROW_PATTERN.match(línea)
        assert m is not None
        assert m.group(1) == "144,467/000"
        assert m.group(2) == "01/06/2026"
        assert m.group(3) == "31/12/2026"
        assert m.group(4) == "52.423,70"
        assert m.group(5) == "T"
        assert m.group(6) == "01/07/2026"
        assert m.group(7) == "0.00"
        assert m.group(8) == "325,807"
        assert "Guiñazu" in m.group(9)
        assert "Colegio Rivadavia" in m.group(9)

    def test_linea_con_factura_grande(self):
        línea = "151,218/00005/06/2026 31/12/2028 $ 206.801,29 T 05/07/2026 0.00 332,610DANIELA CAROLIN1A5 G49IRAUDVIta Brigada Aerea N"
        m = ROW_PATTERN.match(línea)
        assert m is not None
        assert m.group(1) == "151,218/000"
        assert m.group(4) == "206.801,29"
        assert m.group(8) == "332,610"

    def test_linea_saldo_menor(self):
        línea = "152,920/00009/06/2026 01/10/2026 $ 37.821,60 T 09/07/2026 0.00 334,420ERICA PATRICIA FA1B5R48ONI NUES"
        m = ROW_PATTERN.match(línea)
        assert m is not None
        assert m.group(4) == "37.821,60"
        assert m.group(8) == "334,420"

    def test_linea_con_tipo_s(self):
        """TP puede ser 'S' también"""
        línea = "151,218/00005/06/2026 31/12/2028 $ 119.886,72 S 05/07/2026 0.00 332,610DANIELA CAROLINA"
        m = ROW_PATTERN.match(línea)
        assert m is not None
        assert m.group(5) == "S"

    def test_linea_invalida(self):
        """Líneas sin formato de póliza no deben matchear"""
        assert ROW_PATTERN.match("RESUMEN DE DEUDA AL 08/06/2026") is None
        assert ROW_PATTERN.match("CLIENTE 15364 WOLF TRAVEL") is None
        assert ROW_PATTERN.match("") is None
        assert ROW_PATTERN.match("POLIZA/EN V I G E N C I A MON S A L D O") is None


class TestHeaderPatterns:
    """Tests para los patrones de header"""

    def test_fecha_resumen(self):
        m = HEADER_PATTERNS['fecha_resumen'].match("RESUMEN DE DEUDA AL 08/06/2026")
        assert m is not None
        assert m.group(1) == "08/06/2026"

    def test_cliente(self):
        m = HEADER_PATTERNS['cliente'].match("CLIENTE 1 5 ,364 WOLF TRAVEL")
        assert m is not None
        assert "WOLF" in m.group(1)

    def test_productor(self):
        m = HEADER_PATTERNS['productor'].match("PRODUCTOR: 476 DI SANTO RAUL MATIAS AGENCIA 1")
        assert m is not None
        assert "476" in m.group(1)

    def test_no_match(self):
        assert HEADER_PATTERNS['fecha_resumen'].match("OTRA COSA") is None


class TestLimpiarHeader:
    """Tests para limpiar_header"""

    def test_une_numeros_separados(self):
        assert limpiar_header("CLIENTE 1 5 ,364") == "CLIENTE 15,364"

    def test_sin_cambios(self):
        assert limpiar_header("WOLF TRAVEL") == "WOLF TRAVEL"

    def test_vacio(self):
        assert limpiar_header("") == ""


class TestLimpiarTextoAsegurado:
    """Tests para limpiar_texto_asegurado"""

    def test_remueve_digitos_espurios(self):
        assert limpiar_texto_asegurado("bel1e5n49") == "belen"

    def test_con_espacios(self):
        assert limpiar_texto_asegurado("CAROLIN1A5 G49IRAUDVI") == "CAROLINA GIRAUDVI"

    def test_vacio(self):
        assert limpiar_texto_asegurado("") == ""
        assert limpiar_texto_asegurado(None) is None

    def test_sin_artefactos(self):
        assert limpiar_texto_asegurado("Juan Perez") == "Juan Perez"


class TestExtraerResumenSeguros:
    """Tests de integración con PDF real (si existe)"""

    def test_pdf_no_existe(self):
        with pytest.raises(Exception):
            extraer_resumen_seguros("/ruta/inexistente.pdf")

    def test_procesar_pdf_real(self):
        pdf_test = "/mnt/c/Users/pc_wolf_05/Downloads/RESUMEN DE CUENTA 1.pdf"
        if not os.path.exists(pdf_test):
            pytest.skip("PDF de prueba no encontrado")

        resultado = extraer_resumen_seguros(pdf_test)
        assert resultado['total_polizas'] > 0
        assert len(resultado['polizas']) == resultado['total_polizas']
        assert 'fecha_resumen' in resultado['info']
        assert 'poliza' in resultado['polizas'][0]
        assert 'vigencia_desde' in resultado['polizas'][0]
        assert 'saldo' in resultado['polizas'][0]

    def test_procesar_pdf_real_2(self):
        pdf_test = "/mnt/c/Users/pc_wolf_05/Downloads/RESUMEN DE CUENTA 2.pdf"
        if not os.path.exists(pdf_test):
            pytest.skip("PDF de prueba no encontrado")

        resultado = extraer_resumen_seguros(pdf_test)
        assert resultado['total_polizas'] > 0
        assert 'cliente' in resultado['info']

    def test_exportar_excel(self):
        from extractor_seguros import exportar_excel
        pdf_test = "/mnt/c/Users/pc_wolf_05/Downloads/RESUMEN DE CUENTA 1.pdf"
        if not os.path.exists(pdf_test):
            pytest.skip("PDF de prueba no encontrado")

        resultado = extraer_resumen_seguros(pdf_test)
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            ruta = f.name
        try:
            exportar_excel(resultado, ruta)
            assert os.path.exists(ruta)
            assert os.path.getsize(ruta) > 0
        finally:
            if os.path.exists(ruta):
                os.unlink(ruta)
