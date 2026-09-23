"""Tests para las rutas de análisis de resúmenes (/analisis/*)"""

import io
import tempfile
import pandas as pd
import pytest
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    app.config['OUTPUT_FOLDER'] = tempfile.mkdtemp()
    with app.test_client() as client:
        yield client
    import shutil
    shutil.rmtree(app.config['UPLOAD_FOLDER'], ignore_errors=True)
    shutil.rmtree(app.config['OUTPUT_FOLDER'], ignore_errors=True)


def _excel_bytes(movimientos):
    """Genera un .xlsx en memoria con una hoja 'Movimientos', igual al formato que ya produce la app."""
    buffer = io.BytesIO()
    df = pd.DataFrame(movimientos)
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Movimientos', index=False)
    buffer.seek(0)
    return buffer.read()


MOVS_ENERO = [
    {"fecha": "05/01/2026", "descripcion": "TRANSFERENCIA RECIBIDA JUAN", "importe": 1000.0, "tipo": "C"},
    {"fecha": "10/01/2026", "descripcion": "COMISION MANTENIMIENTO", "importe": -50.0, "tipo": "D"},
]

MOVS_FEBRERO = [
    {"fecha": "03/02/2026", "descripcion": "IMPUESTO LEY 25413", "importe": -20.0, "tipo": "D"},
    {"fecha": "15/02/2026", "descripcion": "TRANSFERENCIA A PROVEEDOR", "importe": -500.0, "tipo": "D"},
]


class TestAnalisisCombinar:
    def test_sin_archivos(self, client):
        response = client.post('/analisis/combinar', data={}, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_combina_dos_excels_y_categoriza(self, client):
        data = {
            'archivos': [
                (io.BytesIO(_excel_bytes(MOVS_ENERO)), 'enero.xlsx'),
                (io.BytesIO(_excel_bytes(MOVS_FEBRERO)), 'febrero.xlsx'),
            ]
        }
        response = client.post('/analisis/combinar', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        body = response.get_json()

        assert len(body['movimientos']) == 4
        categorias = {m['descripcion']: m['categoria'] for m in body['movimientos']}
        assert categorias["TRANSFERENCIA RECIBIDA JUAN"] == "Transferencias recibidas"
        assert categorias["COMISION MANTENIMIENTO"] == "Gastos bancarios / aranceles"
        assert categorias["IMPUESTO LEY 25413"] == "Impuestos"
        assert categorias["TRANSFERENCIA A PROVEEDOR"] == "Transferencias emitidas"

        assert body['resumen']['Transferencias recibidas']['cantidad'] == 1
        assert body['resumen']['Transferencias recibidas']['total'] == 1000.0
        assert body['errores_archivos'] == []

    def test_archivo_sin_columnas_esperadas_no_aborta_los_demas(self, client):
        buffer = io.BytesIO()
        pd.DataFrame({"columna_random": [1, 2]}).to_excel(buffer, sheet_name='Movimientos', index=False)
        buffer.seek(0)

        data = {
            'archivos': [
                (io.BytesIO(_excel_bytes(MOVS_ENERO)), 'enero.xlsx'),
                (buffer, 'invalido.xlsx'),
            ]
        }
        response = client.post('/analisis/combinar', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        body = response.get_json()

        assert len(body['movimientos']) == 2  # solo enero.xlsx
        assert len(body['errores_archivos']) == 1
        assert 'invalido.xlsx' in body['errores_archivos'][0]

    def test_archivo_no_es_excel_no_aborta_los_demas(self, client):
        data = {
            'archivos': [
                (io.BytesIO(_excel_bytes(MOVS_ENERO)), 'enero.xlsx'),
                (io.BytesIO(b"not an excel file"), 'roto.xlsx'),
            ]
        }
        response = client.post('/analisis/combinar', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        body = response.get_json()

        assert len(body['movimientos']) == 2  # solo enero.xlsx
        assert len(body['errores_archivos']) == 1
        assert 'roto.xlsx' in body['errores_archivos'][0]

    def test_ningun_archivo_valido_devuelve_422(self, client):
        buffer = io.BytesIO()
        pd.DataFrame({"columna_random": [1, 2]}).to_excel(buffer, sheet_name='Movimientos', index=False)
        buffer.seek(0)

        data = {'archivos': [(buffer, 'invalido.xlsx')]}
        response = client.post('/analisis/combinar', data=data, content_type='multipart/form-data')
        assert response.status_code == 422
