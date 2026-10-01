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
    extraer_nacion,
    extraer_santander,
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

class TestExtraerNacion:
    """Tests para el parser dedicado de Banco Nación (extraer_nacion)"""

    def test_no_descarta_movimiento_con_resumen_en_la_descripcion(self):
        """
        Caso real (Copparoni, resumen 08/2026): el movimiento
        'DB PM/TOT RESUMEN TCORP' se perdía porque el filtro de ruido
        descartaba cualquier línea que contuviera la palabra suelta
        "resumen", pensado para encabezados como "RESUMEN DE CUENTA" o
        pies de página como "FIN DE RESUMEN" — pero esos nunca empiezan
        con fecha, así que el filtro por "resumen" era innecesario y
        además borraba movimientos reales que legítimamente incluyen esa
        palabra en su descripción.
        """
        texto = (
            "RESUMEN DE CUENTA\n"
            "SALDO ANTERIOR 8.885.389,76-\n"
            "20/08/26 DB PM/TOT RESUMEN TCORP 4572 3.353.911,53 12.239.301,29-\n"
            "000230476 <--- FIN DE RESUMEN\n"
        )

        movimientos = extraer_nacion(texto)

        assert len(movimientos) == 1
        mov = movimientos[0]
        assert mov['descripcion'] == 'DB PM/TOT RESUMEN TCORP'
        assert mov['referencia'] == '4572'
        assert mov['tipo'] == 'D'
        assert mov['debito'] == pytest.approx(3353911.53)
        assert mov['credito'] is None
        assert mov['saldo'] == pytest.approx(-12239301.29)


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


# ─────────────────────────────────────────────
#  SANTANDER: regresiones del parser dedicado
# ─────────────────────────────────────────────

# Corrida CONTIGUA taken del resumen Santander real de ago-2026 (ARAMENDI Y
# ASOCIADOS SA): desde "Saldo Inicial" hasta el último impuesto de la pág. 3.
# Replica los tres casos que reportaba el usuario: la columna Fecha se
# desalinea de la fila, el "Saldo Inicial" se emitía como movimiento, y los
# débitos (que Santander imprime SIN signo) se clasificaban como créditos.
TEXTO_SANTANDER = """Resumen de cuenta
Movimientos en pesos
Cuenta Corriente Nº 068-016143/3 CBU: 0720068720000001614336
Fecha Comprobante Movimiento Débito Crédito Saldo en cuenta
01/08/26 Saldo Inicial $ 610.096,43
31/07/26 13264 Comision transf otros bcos canales $ 864,00 $ 609.232,43
Comision transferencias
13264 Iva 21% reg de transfisc ley27743 $ 181,44 $ 609.050,99
31/07/26
Regimen de recaudacion sircreb c $ 1.203,37 $ 607.847,62
31/07/26
Resp:30709590657 / 0,10% sobre $1.203.371,18
01/08/26 32548957 Pago con transferencia qrpct $ 81.901,87 $ 689.749,49
Pago de anahi lilian roman / 30674222
37121843 Pago con transferencia qrpct $ 168.472,43 $ 858.221,92
01/08/26
Pago de omar eduardo mercado / 30987474
5420290 Pago con transferencia qrpct $ 94.032,00 $ 952.253,92
01/08/26
Pago de alejandra paola loyola / 29125029
14509032 Pago con transferencia qrpct $ 291.471,93 $ 1.243.725,85
01/08/26
Pago de noelia ester condori / 32490701
30382182 Transf recibida cvu dif titular $ 300.000,00 $ 1.543.725,85
01/08/26
De veronica noelia palazzett/ mercado pago /27313193530
97463028 Transf recibida cvu dif titular $ 300.000,00 $ 1.843.725,85
01/08/26
De veronica noelia palazzett/ mercado pago /27313193530
03/08/26 3522 Echeq clearing recibido 48hs $ 794.920,13 $ 1.048.805,72
81770757 Pago con transferencia qrpct $ 446.652,00 $ 1.495.457,72
03/08/26
Pago de leopoldo jose moreschi ro / 24398549
33162445 Pago con transferencia qrpct $ 216.273,60 $ 1.711.731,32
03/08/26
Pago de marcela alejandra antonel / 44436579
57938654 Transferencia inmediata $ 1.700.000,00 $ 11.731,32
03/08/26
A david antonio ojeda / - var / 20329679234
32356760 Pago con transferencia qrpct $ 235.664,47 $ 247.395,79
03/08/26
Pago de vanesa carolina rojas / 30818267
Pago tarjeta de credito visa $ 247.395,79 $ 0,00
03/08/26
Por deb:03/08/2026 part 000000001256477288

Cuenta Corriente Nº 068-016143/3 CBU: 0720068720000001614336
Fecha Comprobante Movimiento Débito Crédito Saldo en cuenta
03/08/26 Impuesto ley 25.413 credito 0,6% $ 12.806,80 -$ 12.806,80
Impuesto ley 25.413 debito 0,6% $ 16.467,38 -$ 29.274,18
03/08/26
Impuesto ley 25.413 credito 0,6% $ 18.277,20 -$ 47.551,38
03/08/26
Cta orig: 068-017995/7 - base impo. usd 2.040,00
Detalle impositivo
Total Retención Régimen de Recaudación SIRCREB $ 1.203,37
Saldo total $ 366.323,05
"""

SALDO_INICIAL_AGO = 610096.43
SALDO_FINAL_AGO = -47551.38
TOTAL_MOVS_AGO = 18


class TestSantander:
    """Regresiones del parser dedicado de Santander"""

    @pytest.fixture
    def movs(self):
        return extraer_santander(TEXTO_SANTANDER)

    def test_saldo_inicial_no_es_movimiento(self, movs):
        """'Saldo Inicial' es el saldo de apertura, no un movimiento"""
        assert movs
        assert not any('saldo inicial' in m['descripcion'].lower() for m in movs)
        # El saldo de apertura se deduce del primer movimiento, no de una fila.
        # 'debito' se guarda positivo, así que el saldo anterior es saldo + debito.
        primer = movs[0]
        assert primer['debito'] == pytest.approx(864.00)
        assert primer['saldo'] + primer['debito'] == pytest.approx(SALDO_INICIAL_AGO)

    def test_primeras_filas_del_31_07_se_leen(self, movs):
        """Las 3 filas del 31/07 con la fecha desalineada deben salir"""
        primeras = movs[:3]
        assert len(primeras) == 3
        assert [m['fecha'] for m in primeras] == ['31/07/2026'] * 3
        assert [m['debito'] for m in primeras] == [864.0, 181.44, 1203.37]
        assert [m['referencia'] for m in primeras] == ['13264', '13264', '']

    def test_debitos_no_se_clasifican_como_credito(self, movs):
        """Santander imprime el importe sin signo: el saldo define D/C"""
        debitos = [m for m in movs if m['debito'] is not None]
        creditos = [m for m in movs if m['credito'] is not None]
        assert debitos, "ningún movimiento clasificado como débito"
        assert creditos, "ningún movimiento clasificado como crédito"
        for m in debitos:
            assert m['tipo'] == 'D' and m['credito'] is None
        for m in creditos:
            assert m['tipo'] == 'C' and m['debito'] is None

    def test_descripcion_miente_about_el_signo(self, movs):
        """"Impuesto ley 25.413 credito 0,6%" es DÉBITO si el saldo baja"""
        trampa = [m for m in movs if 'credito 0,6%' in m['descripcion']]
        assert trampa
        assert trampa[0]['tipo'] == 'D'
        assert trampa[0]['debito'] == pytest.approx(12806.80)

    def test_cadena_de_saldos_cierra(self, movs):
        """Saldo inicial + débitos - créditos == último saldo impreso"""
        saldo = SALDO_INICIAL_AGO
        for m in movs:
            saldo = round(saldo + (m['credito'] or 0) - (m['debito'] or 0), 2)
            assert m['saldo'] == pytest.approx(saldo), m
        assert saldo == pytest.approx(SALDO_FINAL_AGO)

    def test_continuaciones_se_anexan_a_la_descripcion(self, movs):
        """Las líneas sin importe son detalle de la fila anterior"""
        assert 'Comision transferencias' in movs[0]['descripcion']
        # "0,10% sobre $1.203.371,18" es detalle del SIRCREB, NO un importe
        sircreb = [m for m in movs if 'sircreb' in m['descripcion'].lower()][0]
        assert sircreb['debito'] == pytest.approx(1203.37)
        assert '1.203.371,18' in sircreb['descripcion']

    def test_lineas_de_un_solo_monto_no_son_movimientos(self, movs):
        """'Total Retención ... SIRCREB $ 1.203,37' es un total, no un movimiento"""
        assert len(movs) == TOTAL_MOVS_AGO
        assert not any('Total Retención' in m['descripcion'] for m in movs)

    def test_texto_posterior_al_detalle_impositivo_se_ignora(self, movs):
        """Nada de lo que viene después del cierre entra como movimiento"""
        assert not any('Detalle' in m['descripcion'] for m in movs)
        assert all(m['saldo'] is not None for m in movs)

    def test_descripcion_contradice_al_saldo(self, movs):
        """'Echeq ... recibido 48hs' es DÉBITO: el saldo baja, no sube"""
        echeq = [m for m in movs if 'Echeq' in m['descripcion']][0]
        assert echeq['tipo'] == 'D'
        assert echeq['debito'] == pytest.approx(794920.13)
        # 1.843.725,85 - 794.920,13 = 1.048.805,72
        assert echeq['saldo'] == pytest.approx(1048805.72)

    def test_pago_tarjeta_es_debito(self, movs):
        """El pago de tarjeta que deja el saldo en 0 es débito"""
        visa = [m for m in movs if 'visa' in m['descripcion'].lower()][0]
        assert visa['tipo'] == 'D'
        assert visa['debito'] == pytest.approx(247395.79)
        assert visa['saldo'] == pytest.approx(0.0)

