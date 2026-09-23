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
from extractor_seguros import extraer_resumen_seguros, exportar_excel
from categorizador import categorizar, CATEGORIAS

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


# ─────────────────────────────────────────────
#  RUTAS: EXTRACTOR DE SEGUROS
# ─────────────────────────────────────────────

@app.route('/seguros')
def seguros_index():
    return render_template('seguros.html')


@app.route('/seguros/procesar', methods=['POST'])
def seguros_procesar():
    limpiar_archivos_antiguos()

    if 'archivo' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo'}), 400

    archivo = request.files['archivo']
    if archivo.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    valido, msg_error = validar_pdf(archivo.filename)
    if not valido:
        return jsonify({'error': msg_error}), 400

    nombre = secure_filename(archivo.filename)
    ruta_pdf = os.path.join(app.config['UPLOAD_FOLDER'], nombre)

    try:
        archivo.save(ruta_pdf)
        resultado = extraer_resumen_seguros(ruta_pdf)
        logger.info(f"📄 Seguros - PDF procesado: {nombre} ({resultado['total_polizas']} pólizas)")

        if not resultado['polizas']:
            return jsonify({'error': 'No se encontraron pólizas en el PDF'}), 422

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_excel = f"seguros_{timestamp}.xlsx"
        ruta_excel = os.path.join(app.config['OUTPUT_FOLDER'], nombre_excel)
        exportar_excel(resultado, ruta_excel)

        return jsonify({
            'ok': True,
            'archivo': nombre_excel,
            'total': resultado['total_polizas'],
            'info': resultado.get('info', {}),
            'preview': resultado['polizas'][:10]
        })

    except Exception as e:
        logger.error(f"❌ Error procesando PDF seguros: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error procesando PDF: {str(e)}'}), 500


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


@app.route('/analisis')
def analisis_index():
    return render_template('analisis.html')


@app.route('/analisis/combinar', methods=['POST'])
def analisis_combinar():
    archivos = request.files.getlist('archivos')
    if not archivos:
        logger.warning("❌ POST /analisis/combinar: sin archivos")
        return jsonify({'error': 'No se recibió ningún archivo'}), 400

    movimientos, resumen, errores_archivos = combinar_excels(archivos)

    if not movimientos:
        logger.warning(f"⚠️  /analisis/combinar sin movimientos válidos: {errores_archivos}")
        return jsonify({
            'error': 'No se encontraron movimientos en los archivos subidos',
            'errores_archivos': errores_archivos
        }), 422

    logger.info(f"📊 /analisis/combinar: {len(movimientos)} movimientos de {len(archivos)} archivo(s)")
    return jsonify({
        'movimientos': movimientos,
        'resumen': resumen,
        'errores_archivos': errores_archivos
    })


def guardar_excel(resultado, ruta):
    movs = resultado['movimientos']
    info = resultado.get('info', {})

    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        # Hoja principal de movimientos
        df = pd.DataFrame(movs)

        # Orden de columnas preferido. 'documento' (nombre del PDF de origen)
        # va siempre al final, a la derecha de todo lo demás, para poder
        # identificar de qué resumen salió cada fila si se combinan varios.
        cols_preferidas = ['fecha', 'descripcion', 'referencia', 'importe', 'saldo', 'moneda', 'tipo', 'titular', 'cuenta', 'raw']
        cols_existentes = [c for c in cols_preferidas if c in df.columns]
        otras = [c for c in df.columns if c not in cols_preferidas and c != 'documento']
        orden_columnas = cols_existentes + otras
        if 'documento' in df.columns:
            orden_columnas.append('documento')
        df = df[orden_columnas]

        df.to_excel(writer, sheet_name='Movimientos', index=False)

        # Hoja de resumen
        importes = [float(m.get('importe') or 0) for m in movs]
        total_debitos = sum(i for i in importes if i < 0)
        total_creditos = sum(i for i in importes if i > 0)
        campos = ['Banco detectado', 'Titular', 'Total movimientos', 'Fecha extracción',
                  'Débitos (suma)', 'Créditos (suma)']
        valores = [
            info.get('banco', 'Desconocido'),
            info.get('titular', ''),
            len(movs),
            datetime.now().strftime('%d/%m/%Y %H:%M'),
            total_debitos,
            total_creditos,
        ]

        saldos = info.get('saldos', [])
        if len(saldos) == 1:
            campos += ['Saldo inicial', 'Saldo final']
            valores += [saldos[0]['saldo_inicial'], saldos[0]['saldo_final']]
        else:
            for i, grupo in enumerate(saldos, start=1):
                identificador = grupo.get('cuenta') or grupo.get('moneda') or ''
                etiqueta = f"Cuenta {i}" + (f" - {identificador}" if identificador else "")
                campos.append(f"Saldo inicial ({etiqueta})")
                valores.append(grupo['saldo_inicial'])
                campos.append(f"Saldo final ({etiqueta})")
                valores.append(grupo['saldo_final'])

        resumen_data = {'Campo': campos, 'Valor': valores}
        pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)

        # Formatear columnas en Movimientos
        ws = writer.sheets['Movimientos']
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)


COLUMNAS_REQUERIDAS_ANALISIS = {'fecha', 'descripcion', 'importe', 'tipo'}


def combinar_excels(archivos):
    """Lee la hoja 'Movimientos' de cada archivo .xlsx, concatena y categoriza.

    Devuelve (movimientos, resumen, errores_archivos). Un archivo inválido
    no aborta el resto: se agrega su motivo a errores_archivos y se sigue.
    """
    dataframes = []
    errores_archivos = []

    for archivo in archivos:
        try:
            df = pd.read_excel(archivo, sheet_name='Movimientos')
        except Exception:
            errores_archivos.append(f"'{archivo.filename}': no es un Excel válido generado por esta app")
            continue

        faltantes = COLUMNAS_REQUERIDAS_ANALISIS - set(df.columns)
        if faltantes:
            errores_archivos.append(f"'{archivo.filename}': faltan columnas {', '.join(sorted(faltantes))}")
            continue

        dataframes.append(df)

    if not dataframes:
        return [], {}, errores_archivos

    combinado = pd.concat(dataframes, ignore_index=True, sort=False)
    combinado['categoria'] = combinado.apply(
        lambda fila: categorizar(fila.get('descripcion', ''), fila.get('tipo', '')),
        axis=1
    )

    resumen_df = combinado.groupby('categoria')['importe'].agg(['count', 'sum'])
    resumen = {
        categoria: {'cantidad': int(fila['count']), 'total': float(fila['sum'])}
        for categoria, fila in resumen_df.iterrows()
    }

    combinado = combinado.astype(object).where(pd.notnull(combinado), None)
    movimientos = combinado.to_dict('records')

    return movimientos, resumen, errores_archivos


NOMBRES_HOJA = {
    'Transferencias recibidas': 'Transferencias recibidas',
    'Transferencias emitidas': 'Transferencias emitidas',
    'Gastos bancarios / aranceles': 'Gastos bancarios',
    'Impuestos': 'Impuestos',
    'Pagos de servicios': 'Pagos de servicios',
    'Extracciones / Depósitos efectivo': 'Extracciones-Depositos',
    'Otros débitos': 'Otros debitos',
    'Otros créditos': 'Otros creditos',
}

COLUMNAS_HOJA_CATEGORIA = ['fecha', 'descripcion', 'referencia', 'importe', 'saldo',
                            'moneda', 'tipo', 'titular', 'cuenta', 'documento']


def exportar_analisis_excel(movimientos, ruta):
    """Genera el Excel de análisis: hoja Resumen + una hoja por categoría con movimientos."""
    df = pd.DataFrame(movimientos)

    resumen_filas = []
    total_general = 0.0
    for categoria in CATEGORIAS:
        subset = df[df['categoria'] == categoria] if 'categoria' in df.columns else df.iloc[0:0]
        cantidad = len(subset)
        total = float(subset['importe'].sum()) if cantidad else 0.0
        resumen_filas.append({'Categoría': categoria, 'Cantidad': cantidad, 'Total': total})
        total_general += total
    resumen_filas.append({'Categoría': 'TOTAL GENERAL', 'Cantidad': len(df), 'Total': total_general})

    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        pd.DataFrame(resumen_filas).to_excel(writer, sheet_name='Resumen', index=False)

        for categoria in CATEGORIAS:
            subset = df[df['categoria'] == categoria] if 'categoria' in df.columns else df.iloc[0:0]
            if subset.empty:
                continue
            columnas = [c for c in COLUMNAS_HOJA_CATEGORIA if c in subset.columns]
            subset[columnas].to_excel(writer, sheet_name=NOMBRES_HOJA[categoria], index=False)


@app.route('/analisis/exportar', methods=['POST'])
def analisis_exportar():
    data = request.get_json(silent=True) or {}
    movimientos = data.get('movimientos')

    if not movimientos:
        logger.warning("❌ POST /analisis/exportar: sin movimientos")
        return jsonify({'error': 'No se recibieron movimientos para exportar'}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_excel = f"analisis_{timestamp}.xlsx"
    ruta_excel = os.path.join(app.config['OUTPUT_FOLDER'], nombre_excel)
    exportar_analisis_excel(movimientos, ruta_excel)

    logger.info(f"📊 Excel de análisis generado: {nombre_excel} ({len(movimientos)} movimientos)")
    return jsonify({'ok': True, 'archivo': nombre_excel})


if __name__ == '__main__':
    print("=" * 50)
    print("  🏦 Extractor Bancario PDF → Excel v1.0")
    print("  Abrí http://localhost:5000 en tu navegador")
    print("=" * 50)
    logger.info("🚀 Flask server iniciando en puerto 5000...")
    app.run(debug=False, host='0.0.0.0', port=5001)
