# 🏦 Bank Extractor

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Flask 2.3+](https://img.shields.io/badge/Flask-2.3%2B-green)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Extractor bancario profesional que convierte resúmenes PDF a planillas Excel para conciliación.**

Herramienta local 100% privada que procesa PDFs de cualquier banco argentino (Galicia, Santander, BBVA, Macro, Nación, HSBC, etc.) y genera Excel estructurado listo para contabilidad. Soporte multi-tenant: identifica automáticamente el titular de cada cuenta.

---

## ✨ Features

- ✅ **Interfaz visual intuitiva** — Drag & drop, no necesitas terminal
- ✅ **Auto-detección de banco** — Funciona con cualquier banco argentino
- ✅ **Parsers dedicados** — Santander y Nación con extracción precisa
- ✅ **Multi-tenant** — Extrae y columna el titular (cliente) de cada PDF
- ✅ **Formato homogéneo** — Mismas columnas para todos los bancos
- ✅ **100% Local** — PDFs nunca salen de tu computadora
- ✅ **Inicio automático** — Doble clic y listo
- ✅ **Excel profesional** — 2 hojas: Movimientos + Resumen
- ✅ **Debug incluido** — Ver texto crudo del PDF para diagnosticar

---

## 🚀 Inicio Rápido

### Requisitos
- **Python 3.8+** ([descargar](https://www.python.org/downloads/))
- **Windows, Mac o Linux**

### 1. Descargar
```bash
git clone https://github.com/Francoooo22/bank-extractor.git
cd bank-extractor
```

### 2. Ejecutar
| Sistema | Acción |
|---------|--------|
| **Windows** | Doble clic en `Iniciar_Windows.bat` |
| **Mac** | Doble clic en `Iniciar_Mac.command` (primera vez: clic derecho → Abrir) |
| **Linux** | `chmod +x Iniciar_Mac.command && ./Iniciar_Mac.command` |

### 3. Usar
1. Sube tu PDF bancario (drag & drop o click)
2. Selecciona banco (o deja auto-detección)
3. Espera extracción (~2 segundos)
4. Descarga Excel

---

## 📊 Formato de Salida

Cada movimiento se exporta con **las mismas columnas** para cualquier banco:

| Campo | Tipo | Ejemplo | Descripción |
|-------|------|---------|-------------|
| **fecha** | texto | 15/07/2026 | Fecha del movimiento |
| **descripcion** | texto | TRANSFERENCIA RECIBIDA | Descripción de la operación |
| **referencia** | texto | 27329529 | Número de comprobante |
| **importe** | número | -5000000 | Positivo = crédito, Negativo = débito |
| **saldo** | número | 1555229.94 | Saldo posterior al movimiento |
| **moneda** | texto | ARS | Moneda (ARS o USD) |
| **tipo** | texto | D | D = Débito, C = Crédito |
| **titular** | texto | COPPARONI SOCIEDAD ANONIMA | Cliente titular de la cuenta |

### Ejemplo en Excel
| fecha | descripcion | referencia | importe | saldo | moneda | tipo | titular |
|-------|-------------|-----------|---------|-------|--------|------|---------|
| 06/02/2026 | Transferencia realizada | 27329529 | -5000000 | 1555229.94 | ARS | D | CRISTIAN A. DE BENEDECTIS |
| 06/02/2026 | Deposito de efectivo | 3454 | 1916100 | 3471329.94 | ARS | C | CRISTIAN A. DE BENEDECTIS |

---

## 🏦 Bancos Soportados

| Banco | Parser | Notas |
|-------|--------|-------|
| Santander / Río | Dedicado | Extrae comprobante, USD, débitos/créditos |
| Banco Nación (BNA) | Dedicado | Clasifica por prefijo (CR/DEBIN/GRAVAMEN) |
| Banco Galicia | Genérico | Funciona bien |
| BBVA / Francés | Genérico | Detecta 2 fechas |
| Banco Macro | Genérico | Fecha sin año |
| HSBC | Genérico | Funciona bien |
| **Cualquier otro** | Genérico | Fallback automático |

---

## 🛠️ Agregar Soporte Nuevo Banco

1. Descarga un extracto PDF del banco
2. Analiza el formato (ver `extractor.py`)
3. Crear función `extraer_mi_banco(texto)` siguiendo el patrón de `extraer_santander()` o `extraer_nacion()`
4. Agregar detección en `detectar_banco()`
5. Integrar en `extraer_movimientos()`

Ver **[ARCHITECTURE.md](ARCHITECTURE.md)** para detalles técnicos.

---

## 🔒 Privacidad & Seguridad

✅ **100% local** — PDFs nunca se suben a internet
✅ **Auto-limpieza** — Archivos se eliminan después de 24h
✅ **Código abierto** — Revisa todo en GitHub

---

## 📚 Documentación

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Diseño y componentes
- **[DEPLOY.md](DEPLOY.md)** — Guía de despliegue (PM2, Nginx, Tailscale)
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Cómo contribuir
- **[CHANGELOG.md](CHANGELOG.md)** — Historial de cambios

---

## 📦 Dependencias

| Paquete | Versión | Uso |
|---------|---------|-----|
| Flask | ≥2.3.0 | Servidor web |
| pdfplumber | ≥0.10.0 | Lectura de PDFs |
| Pandas | ≥2.0.0 | Manipulación de datos |
| openpyxl | ≥3.1.0 | Escritura de Excel |

---

## 👤 Autor

**Franco Bocchi**
- 🌐 [GitHub](https://github.com/Francoooo22)
- 📧 bfproductosyservicios@gmail.com
