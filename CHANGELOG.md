# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [1.2.0] - 2026-07-23

### Agregado
- ✨ **Parser dedicado ICBC** (`extraer_icbc`) — Formato `DD-MM CONCEPTO [COMPROBANTE] [ORIGEN] [CANAL] MONTO[-] [SALDO[-]]`.
  - El propio banco imprime el signo en cada importe (termina en `-` = débito), así que no adivina por texto ni por prefijo.
  - El saldo no viene en todas las filas (solo al cierre de cada agrupación/día): se arrastra un saldo corriente y se valida contra el impreso cuando aparece.
  - El año no viene en la fecha (`DD-MM`): se infiere del `PERIODO DD-MM-YYYY AL DD-MM-YYYY` del encabezado.
  - Soporta múltiples cuentas/monedas dentro de un mismo PDF (cuenta corriente en pesos, caja de ahorro, cuenta en dólares): cada `SALDO ULTIMO EXTRACTO`/`SALDO ANTERIOR` nuevo reinicia el arrastre y puede cambiar de moneda.
  - Detección de banco por nombre completo (`bankofchina`, sin espacios por artefacto de extracción del PDF) o CUIT propio de ICBC (`30-70944784-6`), ya que el resumen nunca imprime la sigla "ICBC".
- ✨ **Columna `documento`** — Nombre del PDF de origen (sin extensión), agregada al final de todas las columnas para cualquier banco. Permite identificar de qué resumen salió cada fila al combinar varios Excels.

### Corregido (Banco Nación)
- 🐛 **Débito/crédito invertidos** — `extraer_nacion` clasificaba por prefijo de texto (ej. "DEBIN" = siempre débito), pero una misma descripción puede ser débito o crédito según de quién sea el CUIT asociado (ej. "DEBIN <CUIT del propio titular>" es cobranza = crédito; "DEBIN <CUIT de un tercero>" es débito). Esto invertía **2532 movimientos** de un solo resumen mensual. Ahora se clasifica comparando el delta real de saldo (`saldo_actual = saldo_anterior ± monto`) contra el monto impreso; el prefijo queda solo como respaldo si no hay saldo previo confiable. Validado contra un resumen completo de 11.333 movimientos con 0 errores de consistencia encadenada.
- 🐛 **Movimientos descartados** — El filtro de ruido tenía la palabra suelta `"banco"`, que matcheaba por accidente dentro de descripciones reales ("48HS. **BANCO**S", "COMIS. CANJE O/**BANCO**S") y las descartaba como si fueran encabezado. Se quitó esa palabra del filtro (el requisito de fecha al inicio de línea ya alcanza para filtrar los encabezados reales).
- 🐛 **Signo de saldo negativo perdido** — El regex de montos no capturaba el guion final de saldos negativos (`304.019,41-`), así que el signo se perdía antes de llegar a `limpiar_monto`. Se agregó el guion opcional al regex.

### Corregido (general)
- 🐛 `extraer_titular` — La estrategia de fallback (línea en mayúsculas, 2+ palabras) no toleraba razones sociales con conectores de una letra ("Y", "DE"), ej. "ARAMENDI Y ASOCIADOS SA" quedaba sin matchear y se devolvía un dato menos relevante (ej. "SUCURSAL MENDOZA"). Se relajó el largo mínimo de las palabras siguientes a 1 letra.

---

## [1.1.0] - 2026-07-21

### Agregado
- ✨ **Parser dedicado Santander** — Extrae comprobantes, soporte USD, sección pesos/dólares
- ✨ **Parser dedicado Nación** — Clasifica débito/crédito por prefijo (CR/DEBIN/GRAVAMEN)
- ✨ **Columna `titular`** — Identifica el cliente titular de cada PDF (multi-tenant)
- ✨ **Columna `importe` unificada** — Una sola columna: positivo = crédito, negativo = débito
- ✨ **Columna `moneda`** — ARS o USD para cada movimiento
- ✨ **Formato homogéneo** — Mismas 8 columnas para todos los bancos
- ✨ **Extracción de comprobantes** — Número de comprobante/operación en columna `referencia`

### Corregido
- 🐛 Detección de banco Nación — keyword `rio` matcheaba dentro de `periodo`
- 🐛 Frontend `index.html` — URLs relativas para funcionar detrás de Tailscale Funnel

### Cambiado
- 🔄 Columna `importe` reemplaza a `debito`/`credito` separados
- 🔄 Orden de columnas Excel: `fecha | descripcion | referencia | importe | saldo | moneda | tipo | titular`
- 🔄 Resumen Excel incluye titular y suma de débitos/créditos

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
