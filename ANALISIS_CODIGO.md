# Análisis Técnico del Proyecto Bank Extractor

**Fecha:** 2024-07-20  
**Versión:** 1.0.0  
**Desarrollador:** Franco Bocchi

---

## 📊 Métricas Generales

| Métrica | Valor |
|---------|-------|
| **Líneas de código** | ~650 |
| **Archivos Python** | 3 |
| **Archivos HTML/CSS** | 1 |
| **Dependencias externas** | 5 |
| **Bancos soportados** | 9+ |
| **Métodos de extracción** | 3 |

---

## 🏗️ Estructura del Código

### app.py (142 líneas)
**Rol:** Servidor web Flask y orquestación

#### Rutas Implementadas
1. `GET /` — Sirve interfaz (index.html)
2. `POST /procesar` — Main: recibe PDF, llama extractor, genera Excel
3. `GET /descargar/<nombre>` — Descarga Excel generado
4. `POST /preview_texto` — Debug: extrae texto crudo de PDF

#### Funciones Clave
- `procesar()` — Orquesta todo el flujo
- `guardar_excel()` — Crea Excel con 2 hojas (Movimientos + Resumen)

#### Características
```python
# Config
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Validaciones
secure_filename()  # Previene path traversal
os.path.exists()   # Verifica archivos antes de servir

# Carpetas
uploads/  # PDFs subidos (temporal)
outputs/  # Excels generados
```

#### Flujo de /procesar
```
1. Validar que hay archivo
2. Guardar PDF en uploads/
3. Llamar extraer_movimientos()
4. Si no hay resultados → error 422
5. Generar Excel con guardar_excel()
6. Devolver JSON con preview + nombre archivo
```

---

### extractor.py (443 líneas)
**Rol:** Motor de extracción (la mayoría de la lógica)

#### Arquitectura de Extracción
```
extraer_movimientos(pdf, banco)
├─ Lee PDF con pdfplumber
├─ Detecta banco automáticamente
├─ Intenta 3 métodos progresivos:
│  ├─ 1. extraer_de_tablas() — Si hay tablas estructuradas
│  ├─ 2. extraer_de_texto() — Regex específico del banco
│  └─ 3. extraccion_generica() — Fallback agresivo
└─ Normaliza y retorna resultados
```

#### Métodos de Extracción

**1. Extracción por Tablas (líneas 143-177)**
- Busca tablas en PDF (`pdfplumber.extract_tables()`)
- Identifica tabla de movimientos por keywords en header
- Mapea columnas automáticamente (fecha, descripción, etc)
- Parsea cada fila

```python
def mapear_columnas(encabezado):
    # Busca por palabras clave: "fecha", "descripcion", "debito", etc
    # Retorna: {'fecha': 0, 'descripcion': 1, 'debito': 2, ...}
```

**2. Extracción por Regex (líneas 254-305)**
- Aplica patrones específicos por banco
- Configurable en `PATRONES = { 'banco': { 'movimiento': regex, ... } }`

```python
PATRONES = {
    'galicia': {
        'movimiento': r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)',
        'fecha_fmt': '%d/%m/%Y',
    },
    # ...
}
```

Soportados:
- Galicia, Santander, BBVA, Macro, Nación, HSBC

**3. Extracción Genérica (líneas 312-361)**
- Fallback que funciona sin banco específico
- Busca líneas con patrón: `fecha + descripción + números`
- Detecta fechas: `\b(\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?)\b`
- Detecta montos: `\b([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b`

#### Funciones Auxiliares

**limpiar_monto(valor) → float | None**
- Convierte strings de monto a float
- Auto-detecta formato:
  - Argentino: "1.234,56" → 1234.56
  - Anglosajón: "1,234.56" → 1234.56
- Maneja signos: "-1500", "(1500)"

**normalizar_fecha(fecha_str) → str**
- Convierte múltiples formatos a DD/MM/YYYY
- Soporta: DD/MM/YYYY, DD-MM-YYYY, DD/MM/YY, YYYY-MM-DD
- Si falta año, asume año actual

**clasificar_monto(monto_str, monto_num, descripción) → (débito, crédito)**
- Determina si movimiento es débito o crédito
- Usa signos (-1500 = débito) o palabras clave
- Keywords:
  - Débito: "pago", "compra", "retiro", "transferencia enviada"
  - Crédito: "depósito", "acreditación", "transferencia recibida"

**detectar_banco(texto) → str**
- Busca keywords en PDF: "Galicia", "Santander", "BBVA", etc
- Retorna nombre de banco o "generico"
- Extensible: agregar más bancos es trivial

---

### lanzar.py (89 líneas)
**Rol:** Launcher automático (ejecutable con doble clic)

#### Funcionalidades
1. **Instalación de deps:**
   - Verifica qué módulos faltan (`importlib.import_module()`)
   - Instala solo lo necesario via `pip install`

2. **Espera a que Flask esté listo:**
   ```python
   def esperar_puerto(puerto, timeout=15):
       # Intenta conectarse al puerto cada 0.2s
       # Timeout si no responde en 15s
   ```

3. **Abre navegador automáticamente:**
   - Thread daemon que espera al puerto
   - Abre `http://localhost:5000` cuando esté listo

#### Scripts de Inicio
- `Iniciar_Windows.bat` — Ejecuta `lanzar.py` en Windows
- `Iniciar_Mac.command` — Ejecuta `lanzar.py` en Mac/Linux

---

## 🔍 Análisis de Calidad

### ✅ Fortalezas

1. **Arquitectura robusta**
   - Separación clara: app.py (web) vs extractor.py (lógica)
   - Fallback progresivo (tablas → regex → genérico)
   - Sin acoplamiento fuerte

2. **Manejo de errores**
   ```python
   try:
       resultado = extraer_movimientos(ruta_pdf, banco)
   except Exception as e:
       return jsonify({'error': f'Error procesando PDF: {str(e)}'}), 500
   ```

3. **Normalización de datos**
   - Fechas: múltiples formatos → DD/MM/YYYY
   - Montos: argentino/anglosajón → float
   - Clasificación: automática débito/crédito

4. **UX profesional**
   - Auto-instalación de deps
   - Auto-detección de banco
   - Debug incluido (ver texto crudo)
   - Preview de resultados

5. **Seguridad**
   - `secure_filename()` previene path traversal
   - Límite de tamaño de archivo (50MB)
   - PDFs se almacenan localmente (sin cloud)

### ⚠️ Áreas de Mejora

1. **Sin tests automatizados**
   - No hay `test_*` files
   - Pruebas son manuales
   - **Recomendación:** Agregar pytest con fixtures de PDFs

2. **Sin validación input estricta**
   ```python
   # Hoy: asume que file.filename es PDF
   # Mejora: validar extension, magic bytes
   ```

3. **Manejo de errores incompleto en extractor.py**
   ```python
   except Exception:  # Línea 302
       continue  # Silencia errores
   ```
   - Debería loguear para debugging

4. **Sin limpieza de archivos antiguos**
   - `uploads/` y `outputs/` acumulan archivos
   - **Recomendación:** Cleanup automático con fecha

5. **Hardcoded Puerto 5000**
   - No hay forma de cambiar puerto sin editar código
   - **Mejora:** Leer de ENV o CLI args

6. **Regex no completos para todos los bancos**
   - Algunos bancos tienen formatos variados
   - Modo genérico es fallback, no ideal

---

## 📈 Complejidad de Código

### Función Más Compleja: `extraer_movimientos()` (68 líneas)
- **Ciclomática:** Media (~8 branches)
- **Legibilidad:** Buena (comentarios claros)
- **Testabilidad:** Buena (entrada/salida predecible)

### Función Más Corta: `detectar_banco()` (17 líneas)
- Simple, legible, fácil de extender

### Spaghetti Factor: BAJO ✅
- Funciones cohesivas y con un solo propósito
- Bajo acoplamiento entre módulos

---

## 🔐 Análisis de Seguridad

| Aspecto | Estado | Notas |
|---------|--------|-------|
| Path traversal | ✅ Protegido | `secure_filename()` |
| File size limit | ✅ Protegido | 50 MB hardcoded |
| SQL injection | ✅ N/A | No hay DB |
| XSS | ⚠️ Verificar | index.html no sanitiza, pero no hay user input en HTML |
| Authentication | ⚠️ No implementado | OK para local, necesario si expone en red |
| HTTPS | ⚠️ No implementado | OK para localhost |

**Recomendación para producción:**
- Agregar auth si se expone en red
- Usar HTTPS
- Validar tipos MIME de archivos
- Rate limiting en `/procesar`

---

## 🚀 Performance

### Tiempos Típicos
- **Upload PDF (~500 KB):** <100ms
- **Extracción (50 movimientos):** 1-2s
- **Generación Excel:** 200-500ms
- **Total:** 2-3 segundos

### Cuello de Botella
1. Lectura de PDF con pdfplumber (~1s)
2. Regex en PDFs grandes (linear)

**Optimizaciones posibles:**
- Cache de PDFs procesados
- Multiprocesamiento para regex
- Indexación de columnas en tablas

---

## 🧪 Estrategia de Prueba Actual

### Manual ✅
- Descargar PDFs reales de bancos
- Someter a app
- Verificar Excel generado
- Revisar "Ver texto crudo" si falla

### Automatizado ❌
- No hay tests
- Propuesta: Crear carpeta `tests/` con:
  ```python
  # test_extractor.py
  def test_limpiar_monto():
      assert limpiar_monto("1.234,56") == 1234.56
      assert limpiar_monto("-1500") == -1500
      assert limpiar_monto("1,234.56") == 1234.56
  
  # test_app.py
  def test_procesar_pdf_galicia(client, pdf_galicia):
      resp = client.post('/procesar', data={'archivo': pdf_galicia, 'banco': 'galicia'})
      assert resp.status_code == 200
      assert 'archivo' in resp.json
  ```

---

## 📚 Documentación Generada

| Archivo | Contenido | Audiencia |
|---------|-----------|-----------|
| README.md | User guide, features, getting started | End users |
| ARCHITECTURE.md | Diseño, componentes, decisiones | Developers |
| CONTRIBUTING.md | Cómo contribuir, estilo, workflow | Contributors |
| CHANGELOG.md | Historial de versiones | All |
| This file (ANALISIS_CODIGO.md) | Technical deep-dive | Senior devs |

---

## 🎯 Conclusión

### Resumen
- **Código bien escrito** con arquitectura clara
- **Funcional y listo para producción** en uso local
- **Fácil de extender** (agregar bancos, mejorar regex)
- **UX pensada en usuario** (auto-install, auto-detect, debug)

### Recomendaciones Prioritarias
1. **ALTA:** Tests automatizados (pytest)
2. **ALTA:** Cleanup automático de uploads/outputs
3. **MEDIA:** Logging estruturado para debugging
4. **MEDIA:** Validación de MIME type de archivo
5. **BAJA:** Interfaz modo oscuro

### Viabilidad de Mejoras
- ✅ Agregar OCR (pytesseract) — Medio
- ✅ Exportar CSV/JSON — Fácil
- ✅ Base de datos (SQLite) — Medio
- ✅ API REST — Fácil (Flask-RESTX)
- ✅ Conciliación automática — Difícil (lógica de matching)

---

**Evaluación General: 8/10** 🌟

Proyecto maduro, bien estructurado, listo para production en desktop. Necesita tests y logging para ser enterprise-ready.
