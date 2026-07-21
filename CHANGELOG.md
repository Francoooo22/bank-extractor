# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

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
