# Arquitectura del Proyecto

## 📋 Visión General

Bank Extractor es una aplicación local de escritorio que automatiza la extracción de datos de resúmenes bancarios en PDF y los convierte en planillas Excel estructuradas para conciliación bancaria.

**Stack:** Python 3.8+ | Flask | pdfplumber | Pandas | openpyxl

---

## 🏗️ Estructura del Proyecto

```
bank_extractor/
├── app.py                 # Servidor Flask + rutas HTTP
├── extractor.py           # Motor de extracción (lógica principal)
├── lanzar.py              # Script de inicio automático
├── requirements.txt       # Dependencias Python
├── templates/
│   └── index.html         # UI interactiva
├── uploads/               # PDFs subidos por usuario (temporal)
└── outputs/               # Excels generados (descargables)
```

---

## 🔄 Flujo de Datos

```
PDF Bancario (subido por usuario)
        ↓
    app.py@/procesar
        ↓
extractor.py (3 métodos de extracción)
    ├─ 1. Extracción por tablas (pdfplumber.extract_tables)
    ├─ 2. Extracción por regex (patrones por banco)
    └─ 3. Extracción genérica agresiva (fallback)
        ↓
    Diccionario de movimientos [{fecha, descripcion, ...}]
        ↓
    app.py@guardar_excel
        ↓
    Excel con 2 hojas: "Movimientos" + "Resumen"
        ↓
    Usuario descarga (app.py@/descargar)
```

---

## 📦 Componentes Principales

### 1. **app.py** (Flask Server)
Responsabilidades:
- Servir la interfaz web
- Recibir archivos PDF del navegador
- Coordinar la extracción via `extractor.py`
- Generar Excel via `guardar_excel()`
- Servir descargas

**Rutas:**
| Ruta | Método | Función |
|------|--------|---------|
| `/` | GET | Sirve `index.html` |
| `/procesar` | POST | Extrae movimientos del PDF |
| `/descargar/<nombre>` | GET | Descarga Excel generado |
| `/preview_texto` | POST | Debug: muestra texto crudo del PDF |

**Límites:**
- Max file size: 50 MB
- Carpetas de trabajo: `uploads/`, `outputs/`

---

### 2. **extractor.py** (Motor de Extracción)
Responsabilidades:
- Leer PDFs via pdfplumber
- Detectar banco automáticamente
- Aplicar 3 estrategias de extracción progresivas
- Normalizar fechas y montos

**Funciones Clave:**

#### `extraer_movimientos(ruta_pdf, banco)` → dict
- Entry point principal
- Devuelve: `{movimientos: [...], info: {...}, texto_muestra: str}`

#### `detectar_banco(texto)` → str
- Busca keywords: "Galicia", "Santander", "BBVA", "Macro", etc.
- Devuelve nombre de banco o "generico"

#### `extraer_de_tablas(tablas, banco)` → list
- Busca tablas estructuradas en el PDF
- Mapea columnas por nombre (fecha, descripción, débito, crédito)
- Parsea cada fila como movimiento

#### `extraer_de_texto(texto, banco)` → list
- Aplica regex específico del banco
- Soporta: Galicia, Santander, BBVA, Macro, Nación, HSBC
- Clasifica montos como débito/crédito por palabras clave

#### `extraccion_generica(texto)` → list
- Fallback agresivo (sin banco específico)
- Busca líneas con: `fecha + descripcion + números`
- No requiere banco configurado

#### Utilidades:
- `limpiar_monto(valor)` — Convierte "1.234,56" → 1234.56
- `normalizar_fecha(fecha_str)` — Normaliza a DD/MM/YYYY
- `clasificar_monto(str, num, desc)` — Determina débito vs crédito

**Patrones por Banco:**

```python
PATRONES = {
    'galicia': {
        'movimiento': r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)',
        'fecha_fmt': '%d/%m/%Y',
    },
    'santander': {
        'movimiento': r'(\d{2}-\d{2}-\d{4})\s+(.+?)\s+([\d.,]+[-]?)\s+([\d.,]+)',
        'fecha_fmt': '%d-%m-%Y',
    },
    # ...
}
```

---

### 3. **lanzar.py** (Launcher Automático)
Responsabilidades:
- Detectar e instalar dependencias faltantes
- Arrancar Flask en background
- Abrir navegador automáticamente

**Flujo:**
1. Verifica qué módulos Python faltan
2. Instala vía `pip install` si necesario
3. Importa y ejecuta `app.py` en thread separado
4. Abre `http://localhost:5000` cuando esté listo

---

### 4. **index.html** (UI Frontend)
**Features:**
- Drag & drop de PDFs
- Selector de banco (con auto-detección)
- Botón "Ver texto crudo" (debug)
- Preview de primeros 10 movimientos
- Descarga de Excel

**Tecnología:** HTML5 + CSS puro (sin frameworks)

---

## 🎯 Decisiones de Diseño

### ✅ **Aplicación Local (No Cloud)**
**Por qué:** 
- Privacidad: PDFs nunca salen del equipo
- Sin dependencia de internet (excepto primera instalación)
- Sin costos de hosting
- Control total del usuario

### ✅ **3 Estrategias de Extracción (Fallback Progresivo)**
**Por qué:**
- Los PDFs bancarios tienen formatos diversos
- Tablas estructuradas: más confiables (si existen)
- Regex por banco: rápido y específico
- Fallback genérico: funciona incluso con PDFs no estandarizados

### ✅ **Detección Automática de Banco**
**Por qué:**
- UX: usuario no necesita saber qué patrones usar
- Fallback graceful: si falla, pasa a genérico
- Extensible: agregar más keywords es trivial

### ✅ **Normalización de Montos (Formato Argentino)**
**Por qué:**
- PDFs argentinos usan: punto (miles), coma (decimal)
- El sistema auto-detecta formato y convierte a float
- Previene errores de cálculo

---

## 🔌 Dependencias

| Librería | Versión | Uso |
|----------|---------|-----|
| Flask | ≥2.3.0 | Servidor web + rutas |
| pdfplumber | ≥0.10.0 | Lectura y extracción de PDFs |
| Pandas | ≥2.0.0 | Manipulación de datos |
| openpyxl | ≥3.1.0 | Escritura de Excel (.xlsx) |
| werkzeug | ≥2.3.0 | Validación de filenames (secure_filename) |

**Instalación:**
```bash
pip install -r requirements.txt
```

---

## 🚀 Flujo de Inicio

```
Usuario ejecuta: Iniciar_Windows.bat / Iniciar_Mac.command
        ↓
lanzar.py
        ↓
    instalar_si_falta()
        ↓
    Thread: abrir_navegador() (espera puerto 5000)
        ↓
    app.run(debug=False, port=5000)
        ↓
    http://localhost:5000 se abre automáticamente
```

---

## 📊 Formato del Excel Generado

### Hoja "Movimientos"
| Columna | Tipo | Ejemplo |
|---------|------|---------|
| fecha | text | 15/07/2024 |
| descripcion | text | TRANSFERENCIA RECIBIDA |
| referencia | text | OP-123456 |
| debito | number | 1500.00 |
| credito | number | 2500.50 |
| saldo | number | 50000.00 |
| tipo | text | D o C |

### Hoja "Resumen"
| Campo | Valor |
|-------|-------|
| Banco detectado | Galicia |
| Total movimientos | 47 |
| Fecha extracción | 15/07/2024 18:30 |
| Débitos (suma) | 25000.00 |
| Créditos (suma) | 18500.00 |

---

## 🔮 Limitaciones Conocidas

1. **PDFs Escaneados (imagen):** Requeriría OCR adicional (no implementado)
2. **PDFs Protegidos:** pdfplumber no puede acceder
3. **Formato de Fecha Incompleto:** "15/07" sin año se asume año actual
4. **Tablas Complejas:** Si columnas no tienen headers claros, fallback a regex
5. **Montos en Columnas Separadas:** Algunos bancos separan débito/crédito en 2 columnas - se detectan automáticamente

---

## 🛠️ Extensibilidad

### Agregar soporte para nuevo banco:
1. Editar `extractor.py`
2. Agregar entrada en `PATRONES`:
```python
'nuevo_banco': {
    'movimiento': re.compile(r'(regex_pattern)'),
    'fecha_fmt': '%d/%m/%Y',
    'tiene_fecha_valor': False,  # si aplica
},
```
3. Agregar keywords en `detectar_banco()`

### Agregar validación CUIT/CBU:
- Crear `validators.py`
- Implementar validaciones argentinas
- Invocar desde `extraer_de_texto()`

---

## 🔐 Seguridad

**Consideraciones:**
- `secure_filename()` previene path traversal en descargas
- PDFs se almacenan en carpeta aislada `uploads/`
- Sin validación de usuario/auth (aplicación local)
- Sin logs de datos sensibles (usuario puede audit)

**Para producción:**
- Agregar Auth (sessions)
- HTTPS (si se expone en red)
- Rate limiting en `/procesar`
- Cleanup automático de uploads/outputs antiguos

---

## 📈 Potenciales Mejoras

- [ ] OCR para PDFs escaneados (pytesseract + Tesseract)
- [ ] Exportar a formatos: CSV, ODS, JSON
- [ ] Base de datos para histórico de extracciones
- [ ] Validación CUIT/CBU argentina
- [ ] Conciliación automática (matchear con banco anterior)
- [ ] Interfaz modo oscuro
- [ ] API REST (no solo web)
- [ ] Tests automatizados
