# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [1.4.1] - 2026-10-01

### Corregido
- 🐛 **Parser Santander** — el parser leía el resumen de cuenta en el orden equivocado. Reescrito para reagrupar las líneas del PDF en filas lógicas antes de interpretarlas, porque la columna **Fecha** va en un bloque x distinto y queda desalineada del resto de la fila: en el texto plano aparece suelta, *después* de la línea principal. Antes se procesaba línea por línea y eso rompía tres cosas:
  - **Todos los débitos se clasificaban como créditos.** Santander imprime el importe *sin signo* en las columnas Débito y Crédito, así que el código solo miraba el signo del número (siempre vacío) y caía en "sin signo = crédito". Ahora la dirección se deriva del **delta del saldo que imprime el banco** (`saldo_actual = saldo_anterior ± importe`), igual que el parser Nación. Hace falta porque la descripción miente: `"Impuesto ley 25.413 credito 0,6%"` es un débito cuando el saldo baja, y `"Echeq clearing recibido 48hs"` también es un débito.
  - **"Saldo Inicial" se emitía como un movimiento más** con tipo `C`, inflando el total de créditos y rompiendo la conciliación. Ahora es el saldo de apertura de la cuenta (y la hoja Resumen lo reporta bien).
  - **Se perdían movimientos de las primeras filas.** El filtro de ruido descartaba por palabra clave `'comision'`, `'iva 21%'`, `'regimen de recaudacion'` y `'resp:'` — que son justamente los conceptos de los primeros movimientos (`Comision transf otros bcos canales`, `Iva 21% reg de transfisc ley27743`, `Regimen de recaudacion sircreb c`) y de todas las filas `Impuesto ley 25.413`. El filtro se reemplazó por un criterio estructural: una línea es fila solo si tiene **dos montos o más** (último = saldo, penúltimo = importe), lo que además descarta como movimiento las trampas que tienen un único monto disfrazado de importe (`Resp:... 0,10% sobre $1.203.371,18`, `Total Retención ... SIRCREB $ 1.203,37`) y deja de colarse texto legal al final del PDF.
  - Las líneas sin importe (`Pago de anahi lilian roman / 30674222`, `Cta orig: ... base impo. usd 2.040,00`) ahora se anexan a la descripción del movimiento al que pertenecen, en vez de perderse o generar filas sueltas.
- 🐛 **Parser Santander**: el "Saldo Inicial" negativo (`-$ 38.126.749,24`) se leía sin signo, así que en los resúmenes con saldo en contra la cadena de saldos arrancaba corrida y no cerraba ni un solo movimiento.

### Agregado
- 🧪 10 tests de regresión del parser Santander (`TestSantander`), con una corrida contigua real de un resumen de ago-2026: saldo inicial que no es movimiento, primeras filas con la fecha desalineada, débitos que no se leen como créditos, contradicciones entre descripción y saldo, cierre de la cadena de saldos y descripciones con continuaciones.

### Verificado
- Los 8 resúmenes Santander de 2026 de Aramendi (ene-ago) reconcilian **al centavo**: `saldo inicial + débitos - créditos == saldo final impreso` en los 2063 movimientos, 0 discrepancias, y el saldo final de cada mes es exactamente el saldo inicial del mes siguiente.

---

## [1.4.0] - 2026-09-29

### Agregado
- ✨ **Versión portable offline** (PyInstaller): carpeta `BankExtractor/` con `.exe` para Windows (y binario Linux), sin instalar Python ni necesitar internet. Ver README → "Versión portable".
- ✨ `BankExtractor.spec`, `build_windows.bat` y `build_linux.sh` para construir el paquete.
- ✨ Workflow de GitHub Actions `Build Windows portable` (`.github/workflows/build-windows.yml`): construye el `.exe` en `windows-latest`, disparable a mano (Actions → Run workflow) o con tags `v*`; deja la carpeta como artefacto `BankExtractor-windows`.

### Cambiado
- Fuentes DM Sans / DM Mono embebidas en `static/` (antes se cargaban de Google Fonts).
- `app.py`: en modo empaquetado, `uploads/`, `outputs/` y `bank_extractor.log` van junto al ejecutable; templates y static dentro del bundle.
- `lanzar.py`: no ejecuta `pip` si está empaquetado y busca el primer puerto libre desde 5000 (antes fallaba o abría otra app si el 5000 estaba ocupado).

---

## [1.3.0] - 2026-09-23

### Agregado
- ✨ Vista `/analisis` — combina varios Excels ya procesados, categoriza movimientos (transferencias, gastos bancarios, impuestos, servicios, efectivo) con gráfico de composición, modal de detalle por categoría con recategorización manual, y exporta un Excel con una hoja por categoría.

---

## [1.2.2] - 2026-09-03

### Corregido
- 🐛 **Parser Nación**: se perdía el movimiento "DB PM/TOT RESUMEN TCORP" (y cualquier otro que incluya la palabra "resumen" en su descripción, p.ej. variantes de "PM/TOT RESUMEN") porque el filtro de líneas de ruido descartaba cualquier línea que contuviera "resumen", pensado para encabezados/pies de página ("RESUMEN DE CUENTA", "FIN DE RESUMEN"). Esas líneas ya se filtran solas por no empezar con fecha, así que se sacó "resumen" del filtro de ruido — mismo tipo de bug que el fix anterior de "banco"/"nacion". Caso real: resumen Copparoni 08/2026, confirmado 199/199 filas contra el Excel corregido a mano.

---

## [1.2.0] - 2026-07-29

### Agregado
- ✨ **Parser BBVA** — parser dedicado para resúmenes de cuenta BBVA
- ✨ **Parser Macro** — parser dedicado para resúmenes Banco Macro (múltiples cuentas)
- ✨ Clasificación débito/crédito por signo del importe (BBVA) y por delta de saldo (Macro)
- ✨ Columna `cuenta` en el Excel de salida para identificar cuenta de origen
- ✨ Detección automática de banco para BBVA y Macro
- ✨ Exclusión de sección de inversiones en PDFs de BBVA

### Cobertura de Formatos Soportados
- 🏦 BBVA: resúmenes "Cuenta Pyme Persona Jurídica" (formato FECHA ORIGEN CONCEPTO DEBITO CREDITO SALDO)
- 🏦 Macro: resúmenes con múltiples cuentas (CC Pesos, CC Dólares, CC Bancaria)
- 🏦 Macro: extracción de titular y CUIT del titular

---

## [1.1.0] - 2026-07-29

### Agregado
- ✨ **Extractor de Seguros** — nuevo módulo `extractor_seguros.py`
- ✨ Conversión de resúmenes de deuda de pólizas de seguro (PDF → Excel)
- ✨ Extracción de 11 columnas: PÓLIZA, VIGENCIA, SALDO, TP, VENCIMIENTO, INTERÉS, FACTURA, ASEGURADO, OBJETO
- ✨ Interfaz web en `/seguros` con drag & drop
- ✨ Modo CLI: `python lanzar.py --seguros archivo.pdf`
- ✨ Exportación a Excel con 2 hojas: "Pólizas" + "Resumen"
- ✨ 20 tests unitarios y de integración para `extractor_seguros.py`
- ✨ Limpieza automática de artefactos numéricos del PDF
- ✨ Captura de metadatos del resumen (fecha, cliente, productor)

### Cobertura de Formatos Soportados
- 🏦 Resúmenes de deuda de aseguradoras (formato "RESUMEN DE DEUDA")
- 🛡️ Pólizas de seguro de vida, accidentes personales, RC
- 📄 Múltiples hojas (100+ páginas detectadas correctamente)

---

## [1.0.0] - 2024-07-20

### Agregado
- ✨ Interfaz web Flask con drag & drop
- ✨ Extracción de PDFs bancarios con 3 métodos (tablas, regex, genérico)
- ✨ Auto-detección de banco (Galicia, Santander, BBVA, Macro, Nación, HSBC)
- ✨ Generación de Excel con hojas "Movimientos" y "Resumen"
- ✨ Launcher automático (Iniciar_Windows.bat, Iniciar_Mac.command)
- ✨ Instalación automática de dependencias
- ✨ Vista previa de texto crudo para debugging
- ✨ Soporte para múltiples formatos de fecha (DD/MM/YYYY, DD-MM-YYYY, DD/MM)
- ✨ Normalización de montos (formato argentino: 1.234,56)
- ✨ Clasificación automática de débito/crédito
- 📚 Documentación completa (README, ARCHITECTURE, CONTRIBUTING)
- 🔒 Validación de filenames (prevención de path traversal)
- 🔒 Límite de tamaño de archivo (50 MB)

### Características Soportadas
- 🏦 Banco Galicia
- 🏦 Santander / Banco Río
- 🏦 BBVA / Banco Francés
- 🏦 Banco Macro
- 🏦 Banco de la Nación Argentina (BNA)
- 🏦 HSBC
- 🏦 ICBC (detección genérica)
- 🏦 Banco Provincia (detección genérica)
- 🏦 Supervielle (detección genérica)
- 🏦 Otros bancos (fallback genérico)

### Tecnología
- Python 3.8+
- Flask 2.3+
- pdfplumber 0.10+
- Pandas 2.0+
- openpyxl 3.1+

---

## [0.5.0] - 2024-04-11

### Versión Inicial (Pre-release)
- Motor de extracción básico con regex
- Interfaz HTML simple
- Soporte para bancos principales
- Lanzador manual

---

## Roadmap Futuro

### v2.0
- [ ] Exportar a CSV, ODS, JSON
- [ ] Conciliación automática
- [ ] Base de datos de históricos
- [ ] Modo oscuro en UI
- [ ] API REST
- [x] ~~Extractor de seguros~~ (implementado en v1.1.0)

### v3.0
- [ ] OCR para PDFs escaneados
- [ ] Validación CUIT/CBU
- [ ] Multi-lenguaje
- [ ] Aplicación desktop (Electron/PyQt)

---

## Convenciones de Versioning

Este proyecto sigue [Semantic Versioning](https://semver.org/):
- MAJOR.MINOR.PATCH
- Ejemplo: v1.0.0

---

## Cómo Reportar Cambios

Para proponer nuevos cambios en futuros releases:
1. Abre un [Issue](https://github.com/Francoooo22/bank-extractor/issues) con tag `enhancement`
2. O haz un [PR](CONTRIBUTING.md)
