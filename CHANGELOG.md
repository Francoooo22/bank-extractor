# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

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
