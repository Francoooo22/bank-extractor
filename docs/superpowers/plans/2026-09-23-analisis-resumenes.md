# Análisis de resúmenes bancarios — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar una vista `/analisis` a Bank Extractor donde el usuario suelta varios `.xlsx` ya generados por la app, ve la composición de movimientos por categoría (transferencias, gastos bancarios, impuestos, etc.) en un gráfico, puede auditar/recategorizar el detalle de cada categoría en un modal, y exporta un Excel final con una hoja por categoría.

**Architecture:** Backend Flask sin estado (dos endpoints nuevos: combinar y exportar, ninguno guarda nada en el servidor). Todo el estado combinado y las recategorizaciones manuales viven en una variable JS global del browser hasta que el usuario pide exportar. Gráfico con Chart.js vendorizado localmente (sin CDN en runtime).

**Tech Stack:** Flask, pandas, openpyxl (ya en el proyecto) + Chart.js 4.4.4 (nuevo, vendorizado en `static/vendor/`). Sin frameworks JS nuevos — JS vanilla como el resto de la app.

**Spec:** `docs/superpowers/specs/2026-09-23-analisis-resumenes-design.md`

## Global Constraints

- Sin base de datos ni sesión de servidor — el estado combinado vive solo en el browser (spec, sección "No objetivos").
- Sin CDN externo para Chart.js — se vendoriza en `static/vendor/chart.umd.min.js`, versión pinneada 4.4.4 (spec, "Vendorizado de Chart.js").
- Solo se aceptan `.xlsx` ya generados por esta app en `/analisis/combinar` — no PDFs.
- Modal de detalle es **por categoría únicamente** — no hay modal general "ver todo sin filtrar" (decisión explícita del usuario).
- Un archivo individual que falla al combinar **no aborta el resto** — se reporta en `errores_archivos` y se sigue con los demás (spec, "Manejo de errores").
- Nombres de hoja de Excel ≤31 caracteres (límite de Excel) — usar el mapeo `NOMBRES_HOJA` definido en Task 4, no los nombres de categoría completos.

---

## Mapa de archivos

- Crear `categorizador.py` — función `categorizar()` y lista `CATEGORIAS`.
- Crear `tests/test_categorizador.py` — tests de `categorizar()`.
- Modificar `app.py` — helpers `combinar_excels()`, `exportar_analisis_excel()`, y rutas `/analisis`, `/analisis/combinar`, `/analisis/exportar`.
- Crear `tests/test_analisis.py` — tests de los dos endpoints nuevos.
- Crear `templates/analisis.html` — vista nueva (drop multi-archivo, gráfico, tabla, modal).
- Crear `static/vendor/chart.umd.min.js` — Chart.js vendorizado (binario, se descarga, no se escribe a mano).

---

### Task 1: Vendorizar Chart.js

**Files:**
- Create: `static/vendor/chart.umd.min.js`

**Interfaces:**
- Produces: variable global `Chart` disponible en el browser al incluir `<script src="/static/vendor/chart.umd.min.js"></script>` (usada por Task 5).

- [ ] **Step 1: Crear la carpeta y descargar el archivo**

```bash
mkdir -p static/vendor
curl -sf https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js -o static/vendor/chart.umd.min.js
```

- [ ] **Step 2: Verificar que se descargó completo**

Run: `wc -c static/vendor/chart.umd.min.js`
Expected: un número cercano a 205749 (bytes). Si el comando `curl` falló (archivo vacío o `curl` devolvió error), no seguir — revisar conectividad antes de continuar.

- [ ] **Step 3: Commit**

```bash
git add static/vendor/chart.umd.min.js
git commit -m "chore: vendorizar Chart.js 4.4.4 para la vista de análisis"
```

---

### Task 2: Módulo `categorizador.py`

**Files:**
- Create: `categorizador.py`
- Test: `tests/test_categorizador.py`

**Interfaces:**
- Produces: `categorizar(descripcion: str, tipo: str) -> str` y `CATEGORIAS: list[str]` (8 categorías, en el orden fijo del spec). Usado por Task 3 (`combinar_excels`) y Task 4 (`exportar_analisis_excel`).

- [ ] **Step 1: Escribir los tests (deben fallar porque el módulo no existe)**

Crear `tests/test_categorizador.py`:

```python
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
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `python -m pytest tests/test_categorizador.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'categorizador'`

- [ ] **Step 3: Implementar `categorizador.py`**

```python
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
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `python -m pytest tests/test_categorizador.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add categorizador.py tests/test_categorizador.py
git commit -m "feat: módulo categorizador con reglas de clasificación por concepto"
```

---

### Task 3: Endpoint `POST /analisis/combinar`

**Files:**
- Modify: `app.py` (agregar import de `categorizador`, función `combinar_excels`, ruta `analisis_combinar`, ruta `analisis_index`)
- Test: `tests/test_analisis.py` (nuevo)

**Interfaces:**
- Consumes: `categorizar(descripcion, tipo) -> str` de `categorizador.py` (Task 2).
- Produces: `combinar_excels(archivos: list[FileStorage]) -> tuple[list[dict], dict, list[str]]` — `(movimientos, resumen, errores_archivos)`. Usado por la ruta en este mismo task; `movimientos` (lista de dicts con clave `'categoria'`) es el formato que consume Task 6 (frontend) y Task 4 (export, vía JSON del browser).
- Ruta `GET /analisis` sirve `templates/analisis.html` (creado en Task 5 — hasta entonces el test de esta ruta no se agrega).

- [ ] **Step 1: Escribir los tests (deben fallar — la ruta no existe)**

Crear `tests/test_analisis.py`:

```python
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

    def test_ningun_archivo_valido_devuelve_422(self, client):
        buffer = io.BytesIO()
        pd.DataFrame({"columna_random": [1, 2]}).to_excel(buffer, sheet_name='Movimientos', index=False)
        buffer.seek(0)

        data = {'archivos': [(buffer, 'invalido.xlsx')]}
        response = client.post('/analisis/combinar', data=data, content_type='multipart/form-data')
        assert response.status_code == 422
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `python -m pytest tests/test_analisis.py -v`
Expected: FAIL (404, la ruta `/analisis/combinar` no existe todavía)

- [ ] **Step 3: Implementar en `app.py`**

Agregar el import al bloque de imports existente (cerca de `from extractor import extraer_movimientos`):

```python
from categorizador import categorizar
```

Agregar estas constantes y función después de `guardar_excel` (o en cualquier punto a nivel de módulo antes de las rutas que las usan):

```python
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
```

Agregar las rutas (junto a las demás rutas de `app.py`, por ejemplo después de `preview_texto`):

```python
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
```

Nota: `templates/analisis.html` todavía no existe (se crea en Task 5) — `GET /analisis` va a devolver un error de `TemplateNotFound` hasta entonces. Eso es esperado y no lo cubre ningún test de este task.

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `python -m pytest tests/test_analisis.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_analisis.py
git commit -m "feat: endpoint /analisis/combinar para combinar y categorizar Excels"
```

---

### Task 4: Endpoint `POST /analisis/exportar`

**Files:**
- Modify: `app.py` (agregar `NOMBRES_HOJA`, `COLUMNAS_HOJA_CATEGORIA`, función `exportar_analisis_excel`, ruta `analisis_exportar`)
- Modify: `tests/test_analisis.py` (agregar clase de tests)

**Interfaces:**
- Consumes: `CATEGORIAS` de `categorizador.py` (Task 2).
- Produces: `exportar_analisis_excel(movimientos: list[dict], ruta: str) -> None` — escribe el `.xlsx` en disco. Usado solo por la ruta de este task.

- [ ] **Step 1: Agregar los tests (deben fallar — la ruta no existe)**

Agregar a `tests/test_analisis.py`:

```python
import os
from openpyxl import load_workbook


class TestAnalisisExportar:
    def test_sin_movimientos(self, client):
        response = client.post('/analisis/exportar', json={'movimientos': []})
        assert response.status_code == 400

    def test_exporta_una_hoja_por_categoria_no_vacia(self, client):
        movimientos = [
            {"fecha": "05/01/2026", "descripcion": "TRANSFERENCIA RECIBIDA JUAN",
             "importe": 1000.0, "tipo": "C", "categoria": "Transferencias recibidas"},
            {"fecha": "10/01/2026", "descripcion": "COMISION MANTENIMIENTO",
             "importe": -50.0, "tipo": "D", "categoria": "Gastos bancarios / aranceles"},
        ]
        response = client.post('/analisis/exportar', json={'movimientos': movimientos})
        assert response.status_code == 200
        body = response.get_json()
        assert body['ok'] is True

        ruta = os.path.join(app.config['OUTPUT_FOLDER'], body['archivo'])
        assert os.path.exists(ruta)

        wb = load_workbook(ruta)
        assert 'Resumen' in wb.sheetnames
        assert 'Transferencias recibidas' in wb.sheetnames
        assert 'Gastos bancarios' in wb.sheetnames  # nombre corto por límite de 31 chars
        # Categorías sin movimientos no deben generar hoja:
        assert 'Impuestos' not in wb.sheetnames
        assert 'Otros debitos' not in wb.sheetnames
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `python -m pytest tests/test_analisis.py::TestAnalisisExportar -v`
Expected: FAIL (404, la ruta `/analisis/exportar` no existe todavía)

- [ ] **Step 3: Implementar en `app.py`**

Agregar el import de `CATEGORIAS` (modificar la línea del import de `categorizador` agregada en Task 3):

```python
from categorizador import categorizar, CATEGORIAS
```

Agregar estas constantes y función (junto a `combinar_excels`):

```python
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
```

Agregar la ruta:

```python
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
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `python -m pytest tests/test_analisis.py -v`
Expected: PASS (todos, incluyendo los de Task 3)

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_analisis.py
git commit -m "feat: endpoint /analisis/exportar genera Excel multi-hoja por categoría"
```

---

### Task 5: Vista `analisis.html` — drop, combinar, gráfico

**Files:**
- Create: `templates/analisis.html`

**Interfaces:**
- Consumes: `POST /analisis/combinar` (Task 3) → `{movimientos, resumen, errores_archivos}`; `/static/vendor/chart.umd.min.js` (Task 1).
- Produces: variable JS global `let movimientos = []` y función `renderizarGrafico()` que Task 6 va a extender (para abrir el modal al click) y Task 7 va a leer (para exportar).

No hay tests automatizados de JS en este proyecto (no hay npm/framework de testing frontend) — este task se verifica manualmente contra el servidor de desarrollo, siguiendo el mismo criterio que ya usa el resto de la app.

- [ ] **Step 1: Leer el `<style>` base de una vista existente**

Abrir `templates/index.html` líneas 9-560 (bloque `<style>`) para reusar las variables de color, tipografía y la clase `.drop-zone` ya existentes — copiarlas tal cual como punto de partida del `<style>` de la nueva página, para que `/analisis` se vea consistente con `/` y `/seguros`.

- [ ] **Step 2: Crear `templates/analisis.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Análisis de Resúmenes — Bank Extractor</title>
  <style>
    /* Pegar aquí el bloque de estilos base copiado de templates/index.html:9-560
       (variables de color, tipografía, .drop-zone, .drag-over, botones, etc.) */

    .grafico-container {
      max-width: 480px;
      margin: 2rem auto;
    }

    .tabla-resumen {
      width: 100%;
      max-width: 700px;
      margin: 1.5rem auto;
      border-collapse: collapse;
    }

    .tabla-resumen th, .tabla-resumen td {
      padding: 0.6rem 1rem;
      text-align: left;
      border-bottom: 1px solid rgba(255,255,255,0.1);
    }

    .tabla-resumen tr {
      cursor: pointer;
    }

    .tabla-resumen tr:hover {
      background: rgba(255,255,255,0.05);
    }

    .errores-archivos {
      max-width: 700px;
      margin: 1rem auto;
      padding: 0.8rem 1rem;
      border-radius: 8px;
      background: rgba(220,50,50,0.15);
      border: 1px solid rgba(220,50,50,0.4);
      font-size: 0.9rem;
    }

    #export-btn {
      display: none;
    }
  </style>
</head>
<body>
  <h1>📊 Análisis de resúmenes bancarios</h1>
  <p><a href="/">← Volver al extractor</a></p>

  <div class="drop-zone" id="drop-zone" onclick="document.getElementById('archivos').click()">
    <p>Arrastrá acá los Excels ya procesados (podés soltar varios a la vez)</p>
    <input type="file" id="archivos" accept=".xlsx" multiple style="display:none">
  </div>

  <div id="errores-archivos" class="errores-archivos" style="display:none"></div>

  <button id="export-btn" onclick="exportarExcel()">⬇️ Exportar Excel</button>

  <div class="grafico-container">
    <canvas id="grafico-categorias"></canvas>
  </div>

  <table class="tabla-resumen" id="tabla-resumen">
    <thead>
      <tr><th>Categoría</th><th>Cantidad</th><th>Total</th></tr>
    </thead>
    <tbody id="tabla-resumen-body"></tbody>
  </table>

  <script src="/static/vendor/chart.umd.min.js"></script>
  <script>
    let movimientos = [];
    let resumen = {};
    let grafico = null;

    const dropZone = document.getElementById('drop-zone');
    const inputArchivos = document.getElementById('archivos');

    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', e => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      combinarArchivos(e.dataTransfer.files);
    });
    inputArchivos.addEventListener('change', e => combinarArchivos(e.target.files));

    async function combinarArchivos(archivos) {
      const formData = new FormData();
      for (const archivo of archivos) {
        formData.append('archivos', archivo);
      }

      const resp = await fetch('/analisis/combinar', { method: 'POST', body: formData });
      const body = await resp.json();

      if (!resp.ok) {
        alert(body.error || 'Error al combinar los archivos');
        return;
      }

      movimientos = body.movimientos;
      resumen = body.resumen;
      mostrarErroresArchivos(body.errores_archivos || []);
      renderizarGrafico();
      document.getElementById('export-btn').style.display = 'inline-block';
    }

    function mostrarErroresArchivos(errores) {
      const div = document.getElementById('errores-archivos');
      if (!errores.length) {
        div.style.display = 'none';
        return;
      }
      div.style.display = 'block';
      div.innerHTML = '<strong>No se pudieron procesar:</strong><ul>' +
        errores.map(e => `<li>${e}</li>`).join('') + '</ul>';
    }

    function renderizarGrafico() {
      // Recalcular resumen desde `movimientos` (por si hubo recategorización manual)
      resumen = {};
      for (const mov of movimientos) {
        const cat = mov.categoria;
        if (!resumen[cat]) resumen[cat] = { cantidad: 0, total: 0 };
        resumen[cat].cantidad += 1;
        resumen[cat].total += mov.importe;
      }

      const categorias = Object.keys(resumen);
      const cantidades = categorias.map(c => resumen[c].cantidad);

      const ctx = document.getElementById('grafico-categorias');
      if (grafico) grafico.destroy();
      grafico = new Chart(ctx, {
        type: 'pie',
        data: {
          labels: categorias,
          datasets: [{ data: cantidades }]
        },
        options: {
          onClick: (evt, elementos) => {
            if (elementos.length > 0) {
              const categoria = categorias[elementos[0].index];
              abrirModalCategoria(categoria);
            }
          }
        }
      });

      const tbody = document.getElementById('tabla-resumen-body');
      tbody.innerHTML = '';
      for (const cat of categorias) {
        const fila = document.createElement('tr');
        fila.innerHTML = `<td>${cat}</td><td>${resumen[cat].cantidad}</td><td>${resumen[cat].total.toFixed(2)}</td>`;
        fila.onclick = () => abrirModalCategoria(cat);
        tbody.appendChild(fila);
      }
    }

    async function exportarExcel() {
      const resp = await fetch('/analisis/exportar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ movimientos })
      });
      const body = await resp.json();
      if (!resp.ok) {
        alert(body.error || 'Error al exportar');
        return;
      }
      window.location.href = `/descargar/${body.archivo}`;
    }
  </script>
</body>
</html>
```

- [ ] **Step 3: Probar manualmente contra el servidor de desarrollo**

```bash
source venv/bin/activate
python app.py
```

En el browser: abrir `http://localhost:5001/analisis`, y con dos o más `.xlsx` generados previamente por `/procesar` (usar los que ya tenés de pruebas anteriores, o generar uno nuevo subiendo un PDF de prueba en `/`), soltarlos en la zona de drop. Confirmar:
- Aparece el gráfico de torta con las categorías.
- La tabla debajo lista las mismas categorías con cantidad y total.
- Si subís un archivo que no es un Excel de esta app, aparece el bloque de "No se pudieron procesar" sin romper el resto.

- [ ] **Step 4: Commit**

```bash
git add templates/analisis.html
git commit -m "feat: vista /analisis con drop múltiple y gráfico de composición"
```

---

### Task 6: Modal de detalle por categoría con recategorización

**Files:**
- Modify: `templates/analisis.html`

**Interfaces:**
- Consumes: `movimientos` (variable global de Task 5), `renderizarGrafico()` (Task 5).
- Produces: función `abrirModalCategoria(categoria)` (ya referenciada desde Task 5, implementada acá).

- [ ] **Step 1: Agregar el HTML del modal**

Agregar antes de `</body>` en `templates/analisis.html`:

```html
<div id="modal-categoria" class="modal-overlay" style="display:none">
  <div class="modal-contenido">
    <button class="modal-cerrar" onclick="cerrarModal()">✕</button>
    <h2 id="modal-titulo"></h2>
    <table class="tabla-modal">
      <thead>
        <tr><th>Fecha</th><th>Descripción</th><th>Importe</th><th>Documento</th><th>Categoría</th></tr>
      </thead>
      <tbody id="modal-tabla-body"></tbody>
    </table>
    <p id="modal-total"></p>
  </div>
</div>
```

Agregar al `<style>`:

```css
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-contenido {
  background: #1e1e1e;
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 900px;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
}

.modal-cerrar {
  position: absolute;
  top: 1rem; right: 1rem;
  background: none;
  border: none;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
}

.tabla-modal {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.tabla-modal th, .tabla-modal td {
  padding: 0.5rem 0.8rem;
  text-align: left;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  font-size: 0.9rem;
}
```

- [ ] **Step 2: Implementar `abrirModalCategoria`, `cerrarModal` y el cambio de categoría por fila**

Agregar al `<script>` de `templates/analisis.html`, después de `renderizarGrafico`:

```javascript
let categoriaModalActual = null;

function abrirModalCategoria(categoria) {
  categoriaModalActual = categoria;
  document.getElementById('modal-titulo').textContent = categoria;
  document.getElementById('modal-categoria').style.display = 'flex';
  renderizarTablaModal();
}

function renderizarTablaModal() {
  const filtrados = movimientos.filter(m => m.categoria === categoriaModalActual);
  const tbody = document.getElementById('modal-tabla-body');
  tbody.innerHTML = '';

  let total = 0;
  filtrados.forEach((mov) => {
    total += mov.importe;
    const idx = movimientos.indexOf(mov);

    const fila = document.createElement('tr');
    fila.innerHTML = `
      <td>${mov.fecha ?? ''}</td>
      <td>${mov.descripcion ?? ''}</td>
      <td>${mov.importe.toFixed(2)}</td>
      <td>${mov.documento ?? ''}</td>
      <td>
        <select onchange="recategorizar(${idx}, this.value)">
          ${CATEGORIAS_JS.map(c => `<option value="${c}" ${c === mov.categoria ? 'selected' : ''}>${c}</option>`).join('')}
        </select>
      </td>`;
    tbody.appendChild(fila);
  });

  document.getElementById('modal-total').textContent = `Total: ${total.toFixed(2)} (${filtrados.length} movimientos)`;
}

function recategorizar(indexMovimiento, nuevaCategoria) {
  movimientos[indexMovimiento].categoria = nuevaCategoria;
  renderizarTablaModal();
}

function cerrarModal() {
  document.getElementById('modal-categoria').style.display = 'none';
  renderizarGrafico();
}
```

Agregar, antes de `let movimientos = [];`, la lista de categorías que necesita el `<select>` (mismo orden que `CATEGORIAS` en `categorizador.py` — si se edita esa lista en Python, hay que reflejar el cambio acá también):

```javascript
const CATEGORIAS_JS = [
  'Transferencias recibidas',
  'Transferencias emitidas',
  'Gastos bancarios / aranceles',
  'Impuestos',
  'Pagos de servicios',
  'Extracciones / Depósitos efectivo',
  'Otros débitos',
  'Otros créditos',
];
```

- [ ] **Step 3: Probar manualmente**

Con el servidor corriendo (`python app.py`) y datos ya combinados en `/analisis`:
- Click en una porción del gráfico o una fila de la tabla resumen → se abre el modal con solo esos movimientos y el total correcto al pie.
- Cambiar la categoría de un movimiento desde el `<select>` → la fila se mueve de categoría en la tabla del modal al instante.
- Cerrar el modal (✕) → el gráfico y la tabla resumen reflejan el cambio (la categoría editada bajó/subió su cantidad y total).

- [ ] **Step 4: Commit**

```bash
git add templates/analisis.html
git commit -m "feat: modal de detalle por categoría con recategorización manual"
```

---

### Task 7: Exportar Excel end-to-end

**Files:**
- (ya implementado en Task 4 backend y Task 5 frontend — `exportarExcel()` ya está escrita) — este task es de verificación end-to-end, sin cambios de código nuevos salvo lo que surja de la prueba.

**Interfaces:**
- Consumes: `POST /analisis/exportar` (Task 4), `exportarExcel()` (Task 5), `GET /descargar/<nombre>` (endpoint ya existente en `app.py`).

- [ ] **Step 1: Prueba manual end-to-end completa**

Con el servidor corriendo:
1. Ir a `/analisis`.
2. Soltar 2-3 `.xlsx` de prueba (generados con `/procesar` a partir de PDFs reales, o los mismos usados en Task 5).
3. Verificar gráfico y tabla resumen.
4. Abrir el modal de al menos una categoría y recategorizar un movimiento a otra categoría.
5. Cerrar el modal, confirmar que el gráfico se actualizó.
6. Click en "⬇️ Exportar Excel".
7. Confirmar que se descarga un archivo `analisis_<timestamp>.xlsx`.
8. Abrir el Excel descargado y verificar:
   - Hoja `Resumen` con cantidad y total por categoría + fila `TOTAL GENERAL`.
   - Una hoja por cada categoría con movimientos (los nombres cortos: "Gastos bancarios", "Extracciones-Depositos", "Otros debitos", "Otros creditos").
   - El movimiento recategorizado en el paso 4 aparece en la hoja de su **nueva** categoría, no la original.
   - Categorías sin movimientos no tienen hoja.

- [ ] **Step 2: Correr toda la suite de tests una última vez**

Run: `python -m pytest tests/ -v`
Expected: PASS (todos — los 60 existentes + los nuevos de `test_categorizador.py` y `test_analisis.py`)

- [ ] **Step 3: Actualizar CHANGELOG.md**

Agregar entrada nueva arriba de la más reciente en `CHANGELOG.md`, siguiendo el formato existente del archivo (buscar la sección `## [Unreleased]` o la versión más reciente y agregar debajo del encabezado correspondiente):

```markdown
### Agregado
- ✨ Vista `/analisis` — combina varios Excels ya procesados, categoriza movimientos (transferencias, gastos bancarios, impuestos, servicios, efectivo) con gráfico de composición, modal de detalle por categoría con recategorización manual, y exporta un Excel con una hoja por categoría.
```

- [ ] **Step 4: Commit final**

```bash
git add CHANGELOG.md
git commit -m "docs: documentar vista de análisis de resúmenes en CHANGELOG"
```
