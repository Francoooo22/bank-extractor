"""
Extractor de Resúmenes Bancarios → Excel
Aplicación local Flask para procesar PDFs bancarios
"""

import os
import re
import json
import logging
import pdfplumber
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from extractor import extraer_movimientos

# ─────────────────────────────────────────────
#  CONFIGURACIÓN DE LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bank_extractor.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['CLEANUP_HOURS'] = 24  # Limpiar archivos de +24h

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

logger.info("✅ Bank Extractor iniciado")


# ─────────────────────────────────────────────
#  FUNCIONES AUXILIARES
# ─────────────────────────────────────────────

def validar_pdf(filename):
    """Valida que el archivo sea PDF válido"""
    if not filename or '.' not in filename:
        return False, "Nombre de archivo inválido"

    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in app.config['ALLOWED_EXTENSIONS']:
        return False, f"Extensión no permitida: {ext}. Solo PDF."

    return True, None


def limpiar_archivos_antiguos():
    """Elimina archivos de más de CLEANUP_HOURS horas"""
    hora_limite = datetime.now() - timedelta(hours=app.config['CLEANUP_HOURS'])

    for carpeta in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
        if not os.path.exists(carpeta):
            continue

        for archivo in os.listdir(carpeta):
            ruta = os.path.join(carpeta, archivo)
            if os.path.isfile(ruta):
                mtime = datetime.fromtimestamp(os.path.getmtime(ruta))
                if mtime < hora_limite:
                    try:
                        os.remove(ruta)
                        logger.info(f"🗑️  Limpiado: {archivo}")
                    except Exception as e:
                        logger.warning(f"⚠️  No se pudo limpiar {archivo}: {e}")


# ─────────────────────────────────────────────
#  RUTAS
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/procesar', methods=['POST'])
def procesar():
    # Limpiar archivos antiguos (background)
    limpiar_archivos_antiguos()

    if 'archivo' not in request.files:
        logger.warning("❌ POST /procesar: sin archivo")
        return jsonify({'error': 'No se recibió ningún archivo'}), 400

    archivo = request.files['archivo']
    if archivo.filename == '':
        logger.warning("❌ POST /procesar: nombre de archivo vacío")
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    # Validar PDF
    valido, msg_error = validar_pdf(archivo.filename)
    if not valido:
        logger.warning(f"❌ POST /procesar: {msg_error} - {archivo.filename}")
        return jsonify({'error': msg_error}), 400

    banco = request.form.get('banco', 'generico').lower().strip()
    nombre = secure_filename(archivo.filename)
    ruta_pdf = os.path.join(app.config['UPLOAD_FOLDER'], nombre)

    try:
        archivo.save(ruta_pdf)
        logger.info(f"📁 PDF guardado: {nombre} (banco: {banco})")

        resultado = extraer_movimientos(ruta_pdf, banco)
        logger.info(f"✅ Extracción completada: {len(resultado['movimientos'])} movimientos")

        if not resultado['movimientos']:
            logger.warning(f"⚠️  No se encontraron movimientos en {nombre}")
            return jsonify({
                'error': 'No se encontraron movimientos. Intentá con banco "Genérico" o revisá el PDF.',
                'texto_muestra': resultado.get('texto_muestra', '')
            }), 422

        # Guardar Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_excel = f"extracto_{timestamp}.xlsx"
        ruta_excel = os.path.join(app.config['OUTPUT_FOLDER'], nombre_excel)
        guardar_excel(resultado, ruta_excel)

        logger.info(f"📊 Excel generado: {nombre_excel}")
        return jsonify({
            'ok': True,
            'archivo': nombre_excel,
            'total': len(resultado['movimientos']),
            'info': resultado.get('info', {}),
            'preview': resultado['movimientos'][:10]
        })

    except Exception as e:
        logger.error(f"❌ Error procesando PDF: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error procesando PDF: {str(e)}'}), 500


@app.route('/descargar/<nombre>')
def descargar(nombre):
    nombre_seguro = secure_filename(nombre)
    ruta = os.path.join(app.config['OUTPUT_FOLDER'], nombre_seguro)
    if not os.path.exists(ruta):
        logger.warning(f"❌ Intento de descargar archivo no existente: {nombre}")
        return jsonify({'error': 'Archivo no encontrado'}), 404
    logger.info(f"⬇️  Descargando: {nombre}")
    return send_file(ruta, as_attachment=True)


@app.route('/preview_texto', methods=['POST'])
def preview_texto():
    """Muestra el texto crudo del PDF para debugging"""
    if 'archivo' not in request.files:
        logger.warning("❌ POST /preview_texto: sin archivo")
        return jsonify({'error': 'Sin archivo'}), 400
    archivo = request.files['archivo']
    nombre = secure_filename(archivo.filename)
    ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre)
    archivo.save(ruta)
    try:
        logger.info(f"🔍 Preview de texto: {nombre}")
        texto = []
        with pdfplumber.open(ruta) as pdf:
            for i, page in enumerate(pdf.pages[:3]):
                texto.append(f"=== PÁGINA {i+1} ===\n{page.extract_text() or '(sin texto)'}")
        return jsonify({'texto': '\n\n'.join(texto)})
    except Exception as e:
        logger.error(f"❌ Error en preview: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def guardar_excel(resultado, ruta):
    movs = resultado['movimientos']
    info = resultado.get('info', {})

    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        # Hoja principal de movimientos
        df = pd.DataFrame(movs)

        # Orden de columnas preferido
        cols_preferidas = ['fecha', 'descripcion', 'referencia', 'importe', 'saldo', 'moneda', 'tipo', 'titular', 'raw']
        cols_existentes = [c for c in cols_preferidas if c in df.columns]
        otras = [c for c in df.columns if c not in cols_preferidas]
        df = df[cols_existentes + otras]

        df.to_excel(writer, sheet_name='Movimientos', index=False)

        # Hoja de resumen
        importes = [float(m.get('importe') or 0) for m in movs]
        total_debitos = sum(i for i in importes if i < 0)
        total_creditos = sum(i for i in importes if i > 0)
        resumen_data = {
            'Campo': ['Banco detectado', 'Titular', 'Total movimientos', 'Fecha extracción',
                      'Débitos (suma)', 'Créditos (suma)'],
            'Valor': [
                info.get('banco', 'Desconocido'),
                info.get('titular', ''),
                len(movs),
                datetime.now().strftime('%d/%m/%Y %H:%M'),
                total_debitos,
                total_creditos,
            ]
        }
        pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)

        # Formatear columnas en Movimientos
        ws = writer.sheets['Movimientos']
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)


if __name__ == '__main__':
    print("=" * 50)
    print("  🏦 Extractor Bancario PDF → Excel v1.0")
    print("  Abrí http://localhost:5000 en tu navegador")
    print("=" * 50)
    logger.info("🚀 Flask server iniciando en puerto 5000...")
    app.run(debug=False, host='0.0.0.0', port=5001)
