"""Tests para categorizador.py"""

from categorizador import categorizar, CATEGORIAS


class TestCategorizar:
    def test_transferencia_recibida(self):
        assert categorizar("TRANSFERENCIA RECIBIDA DE JUAN PEREZ", "C") == "Transferencias recibidas"

    def test_transferencia_emitida(self):
        assert categorizar("TRANSFERENCIA A TERCEROS", "D") == "Transferencias emitidas"

    def test_gastos_bancarios(self):
        assert categorizar("COMISION MANTENIMIENTO DE CUENTA", "D") == "Gastos bancarios / aranceles"
        assert categorizar("ARANCEL POR SERVICIO", "D") == "Gastos bancarios / aranceles"

    def test_impuestos(self):
        assert categorizar("IMPUESTO LEY 25413 DEBITOS", "D") == "Impuestos"
        assert categorizar("PERCEPCION IVA RG 2408", "D") == "Impuestos"

    def test_pagos_de_servicios(self):
        assert categorizar("DEBITO AUTOMATICO EDENOR", "D") == "Pagos de servicios"
        assert categorizar("PAGO SERV. TELECOM", "D") == "Pagos de servicios"

    def test_extracciones_depositos_efectivo(self):
        assert categorizar("EXTRACCION CAJERO AUTOMATICO", "D") == "Extracciones / Depósitos efectivo"
        assert categorizar("DEPOSITO EFECTIVO SUCURSAL", "C") == "Extracciones / Depósitos efectivo"

    def test_otros_debitos_fallback(self):
        assert categorizar("CONCEPTO SIN CLASIFICAR RARO", "D") == "Otros débitos"

    def test_otros_creditos_fallback(self):
        assert categorizar("CONCEPTO SIN CLASIFICAR RARO", "C") == "Otros créditos"

    def test_case_insensitive_y_sin_acentos(self):
        assert categorizar("transferencia recibida", "C") == "Transferencias recibidas"
        assert categorizar("IMPUESTO", "D") == "Impuestos"

    def test_tipo_vacio_usa_fallback_debito(self):
        assert categorizar("CONCEPTO CUALQUIERA", "") == "Otros débitos"


def test_categorias_orden_fijo():
    assert CATEGORIAS == [
        "Transferencias recibidas",
        "Transferencias emitidas",
        "Gastos bancarios / aranceles",
        "Impuestos",
        "Pagos de servicios",
        "Extracciones / Depósitos efectivo",
        "Otros débitos",
        "Otros créditos",
    ]
