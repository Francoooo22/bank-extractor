"""
Tests para el módulo app.py
Verifica rutas y funcionalidades Flask
"""

import pytest
import os
import tempfile
from app import app, validar_pdf, limpiar_archivos_antiguos
from datetime import datetime, timedelta


@pytest.fixture
def client():
    """Fixture: cliente Flask para testing"""
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    app.config['OUTPUT_FOLDER'] = tempfile.mkdtemp()

    with app.test_client() as client:
        yield client

    # Cleanup
    import shutil
    shutil.rmtree(app.config['UPLOAD_FOLDER'], ignore_errors=True)
    shutil.rmtree(app.config['OUTPUT_FOLDER'], ignore_errors=True)


class TestValidarPdf:
    """Tests para la función validar_pdf"""

    def test_pdf_válido(self):
        """Validar PDF correcto"""
        valido, error = validar_pdf("documento.pdf")
        assert valido is True
        assert error is None

    def test_extension_no_permitida(self):
        """Rechazar extensiones no permitidas"""
        valido, error = validar_pdf("documento.txt")
        assert valido is False
        assert "no permitida" in error.lower()

        valido, error = validar_pdf("documento.xlsx")
        assert valido is False

    def test_sin_extension(self):
        """Rechazar archivos sin extensión"""
        valido, error = validar_pdf("documento")
        assert valido is False

    def test_nombre_vacío(self):
        """Rechazar nombre vacío"""
        valido, error = validar_pdf("")
        assert valido is False


class TestRutas:
    """Tests para las rutas Flask"""

    def test_index(self, client):
        """GET / debe devolver HTML"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'html' in response.data.lower() or b'PDF' in response.data

    def test_procesar_sin_archivo(self, client):
        """POST /procesar sin archivo"""
        response = client.post('/procesar', data={})
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_procesar_extension_no_permitida(self, client):
        """POST /procesar con archivo no-PDF"""
        data = {
            'archivo': (b'contenido', 'test.txt'),
            'banco': 'generico'
        }
        response = client.post(
            '/procesar',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    def test_descargar_no_existe(self, client):
        """GET /descargar/<nombre> archivo no existe"""
        response = client.get('/descargar/no_existe.xlsx')
        assert response.status_code == 404

    def test_preview_texto_sin_archivo(self, client):
        """POST /preview_texto sin archivo"""
        response = client.post('/preview_texto', data={})
        assert response.status_code == 400


class TestLimpiezaArchivos:
    """Tests para la función limpiar_archivos_antiguos"""

    def test_cleanup_no_falla_si_carpeta_vacía(self):
        """No debe fallar si no hay archivos"""
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        app.config['OUTPUT_FOLDER'] = tempfile.mkdtemp()
        try:
            limpiar_archivos_antiguos()  # No debe lanzar excepción
        finally:
            import shutil
            shutil.rmtree(app.config['UPLOAD_FOLDER'], ignore_errors=True)
            shutil.rmtree(app.config['OUTPUT_FOLDER'], ignore_errors=True)

    def test_cleanup_elimina_archivos_antiguos(self):
        """Debe eliminar archivos más viejos que CLEANUP_HOURS"""
        app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        app.config['CLEANUP_HOURS'] = 1

        # Crear archivo antiguo
        archivo_antiguo = os.path.join(app.config['UPLOAD_FOLDER'], 'viejo.txt')
        with open(archivo_antiguo, 'w') as f:
            f.write('test')

        # Simular que es antiguo
        tiempo_antiguo = (datetime.now() - timedelta(hours=2)).timestamp()
        os.utime(archivo_antiguo, (tiempo_antiguo, tiempo_antiguo))

        # Limpiar
        limpiar_archivos_antiguos()

        # Verificar que se eliminó
        assert not os.path.exists(archivo_antiguo)

        # Cleanup
        import shutil
        shutil.rmtree(app.config['UPLOAD_FOLDER'], ignore_errors=True)


# ─────────────────────────────────────────────
#  Tests de Configuración
# ─────────────────────────────────────────────

class TestConfiguracion:
    """Tests para verificar configuración"""

    def test_carpetas_existen(self, client):
        """Verificar que se crean las carpetas necesarias"""
        assert os.path.isdir(app.config['UPLOAD_FOLDER'])
        assert os.path.isdir(app.config['OUTPUT_FOLDER'])

    def test_max_content_length(self):
        """Verificar límite de tamaño"""
        assert app.config['MAX_CONTENT_LENGTH'] == 50 * 1024 * 1024

    def test_allowed_extensions(self):
        """Verificar extensiones permitidas"""
        assert 'pdf' in app.config['ALLOWED_EXTENSIONS']
