"""
Extractor de Resúmenes Bancarios → Excel
Aplicación local Flask para procesar PDFs bancarios
"""

import os
import re
import json
import pdfplumber
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
from extractor import extraer_movimientos

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/procesar', methods=['POST'])
def procesar():
    if 'archivo' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo'}), 400

    archivo = request.files['archivo']
    if archivo.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    banco = request.form.get('banco', 'generico')

    nombre = secure_filename(archivo.filename)
    ruta_pdf = os.path.join(app.config['UPLOAD_FOLDER'], nombre)
    archivo.save(ruta_pdf)

    try:
        resultado = extraer_movimientos(ruta_pdf, banco)

        if not resultado['movimientos']:
            return jsonify({
                'error': 'No se encontraron movimientos. Intentá con banco "Genérico" o revisá el PDF.',
                'texto_muestra': resultado.get('texto_muestra', '')
            }), 422

        # Guardar Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_excel = f"extracto_{timestamp}.xlsx"
        ruta_excel = os.path.join(app.config['OUTPUT_FOLDER'], nombre_excel)
        guardar_excel(resultado, ruta_excel)

        return jsonify({
            'ok': True,
            'archivo': nombre_excel,
            'total': len(resultado['movimientos']),
            'info': resultado.get('info', {}),
            'preview': resultado['movimientos'][:10]
        })

    except Exception as e:
        return jsonify({'error': f'Error procesando PDF: {str(e)}'}), 500


@app.route('/descargar/<nombre>')
def descargar(nombre):
    ruta = os.path.join(app.config['OUTPUT_FOLDER'], secure_filename(nombre))
    if not os.path.exists(ruta):
        return jsonify({'error': 'Archivo no encontrado'}), 404
    return send_file(ruta, as_attachment=True)


@app.route('/preview_texto', methods=['POST'])
def preview_texto():
    """Muestra el texto crudo del PDF para debugging"""
    if 'archivo' not in request.files:
        return jsonify({'error': 'Sin archivo'}), 400
    archivo = request.files['archivo']
    nombre = secure_filename(archivo.filename)
    ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre)
    archivo.save(ruta)
    try:
        texto = []
        with pdfplumber.open(ruta) as pdf:
            for i, page in enumerate(pdf.pages[:3]):  # primeras 3 páginas
                texto.append(f"=== PÁGINA {i+1} ===\n{page.extract_text() or '(sin texto)'}")
        return jsonify({'texto': '\n\n'.join(texto)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def guardar_excel(resultado, ruta):
    movs = resultado['movimientos']
    info = resultado.get('info', {})

    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        # Hoja principal de movimientos
        df = pd.DataFrame(movs)

        # Orden de columnas preferido
        cols_preferidas = ['fecha', 'descripcion', 'referencia', 'debito', 'credito', 'saldo', 'tipo', 'raw']
        cols_existentes = [c for c in cols_preferidas if c in df.columns]
        otras = [c for c in df.columns if c not in cols_preferidas]
        df = df[cols_existentes + otras]

        df.to_excel(writer, sheet_name='Movimientos', index=False)

        # Hoja de resumen
        resumen_data = {
            'Campo': ['Banco detectado', 'Total movimientos', 'Fecha extracción',
                      'Débitos (suma)', 'Créditos (suma)'],
            'Valor': [
                info.get('banco', 'Desconocido'),
                len(movs),
                datetime.now().strftime('%d/%m/%Y %H:%M'),
                sum(float(m.get('debito') or 0) for m in movs),
                sum(float(m.get('credito') or 0) for m in movs),
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
    print("  Extractor Bancario PDF → Excel")
    print("  Abrí http://localhost:5000 en tu navegador")
    print("=" * 50)
    app.run(debug=True, port=5000)
