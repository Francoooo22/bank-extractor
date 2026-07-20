# 🏦 Bank Extractor

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Flask 2.3+](https://img.shields.io/badge/Flask-2.3%2B-green)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Extractor bancario profesional que convierte resúmenes PDF a planillas Excel para conciliación.**

Herramienta local 100% privada que procesa PDFs de cualquier banco argentino (Galicia, Santander, BBVA, Macro, Nación, HSBC, etc.) y genera Excel estructurado listo para contabilidad.

---

## ✨ Features

- ✅ **Interfaz visual intuitiva** — Drag & drop, no necesitas terminal
- ✅ **Auto-detección de banco** — Funciona con cualquier banco argentino
- ✅ **3 métodos de extracción** — Tablas, regex específico, fallback genérico
- ✅ **100% Local** — PDFs nunca salen de tu computadora
- ✅ **Sin dependencias externas** — Solo Python + librerías
- ✅ **Inicio automático** — Doble clic y listo
- ✅ **Excel profesional** — 2 hojas: Movimientos + Resumen
- ✅ **Debug incluido** — Ver texto crudo del PDF para diagnosticar problemas

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

El lanzador:
- ✓ Instala dependencias automáticamente
- ✓ Arranca el servidor Flask
- ✓ Abre el navegador en `http://localhost:5000`

### 3. Usar
1. Sube tu PDF bancario (drag & drop o click)
2. Selecciona banco (o deja auto-detección)
3. Espera extracción (~2 segundos)
4. Descarga Excel

**¡Listo!** Usa el Excel para conciliación o importa a tu software contable.

---

## 📊 Qué Extrae

Cada movimiento incluye:

| Campo | Ejemplo | Uso |
|-------|---------|-----|
| **Fecha** | 15/07/2024 | Correlacionar con registros |
| **Descripción** | TRANSFERENCIA RECIBIDA | Identificar tipo de operación |
| **Débito** | 1500.00 | Egresos (pagos, retiros) |
| **Crédito** | 2500.50 | Ingresos (depósitos) |
| **Saldo** | 50000.00 | Verificar cierre de día |
| **Referencia** | OP-123456 | Número de comprobante |
| **Tipo** | D/C | Débito o Crédito |

**Generas un Excel con:**
- 📑 Hoja "Movimientos" — Todos los registros
- 📑 Hoja "Resumen" — Totales y metadata

---

## 🏦 Bancos Soportados

| Banco | Estado | Notas |
|-------|--------|-------|
| Banco Galicia | ✅ Completo | Muy confiable |
| Santander / Río | ✅ Completo | Funciona bien |
| BBVA / Francés | ✅ Completo | Detecta 2 fechas |
| Banco Macro | ✅ Completo | Fecha sin año |
| Banco Nación (BNA) | ✅ Completo | Estándar |
| HSBC | ✅ Completo | Funciona bien |
| ICBC | ✅ Automático | Via detección genérica |
| Banco Provincia | ✅ Automático | Via detección genérica |
| Supervielle | ✅ Automático | Via detección genérica |
| **Cualquier otro** | ✅ Modo Genérico | Fallback automático |

No aparece tu banco? **[Abre un Issue](https://github.com/Francoooo22/bank-extractor/issues)** con un PDF de ejemplo (anónimo).

---

## 🛠️ Agregar Soporte Nuevo Banco

¿Necesitas un banco no listado? Fácil:

1. Descarga un extracto PDF del banco
2. Abre `extractor.py`
3. Busca `PATRONES = {`
4. Agrega entrada nueva:
   ```python
   'mi_banco': {
       'movimiento': re.compile(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+)'),
       'fecha_fmt': '%d/%m/%Y',
   },
   ```
5. Agrega palabra clave en `detectar_banco()`:
   ```python
   'mi_banco': ['mi banco', 'mibanc'],
   ```
6. [Haz un PR](CONTRIBUTING.md) para compartir 🎉

Ver **[ARCHITECTURE.md](ARCHITECTURE.md)** para detalles técnicos.

---

## 🐛 Problemas Comunes

### "No se encontraron movimientos"
- ✓ Probá seleccionar **"Genérico"** manualmente
- ✓ Click **"Ver texto crudo"** para diagnosticar
- ✓ ¿PDF descargado de home banking? (no escaneado)
- ✓ ¿Fecha visible? (algunos PDFs no tienen fechas)

### "Los números no coinciden"
- ✓ Algunos bancos usan formato regional (1.234,56)
- ✓ El sistema auto-convierte; verifica en Excel

### "Python no encontrado" (Windows)
- ✓ Instala desde https://www.python.org/downloads/
- ✓ **Importante:** Marca la casilla **"Add Python to PATH"**

### "Port 5000 en uso"
- ✓ Cierra otras apps que usen ese puerto
- ✓ O edita `lanzar.py` línea 24: `PUERTO = 5001`

---

## 🔒 Privacidad & Seguridad

✅ **100% local**
- PDFs nunca se suben a internet
- Sin servidores remotos
- Control total

✅ **Sin datos guardados**
- Archivos se borran después de descargar
- Modo "set it and forget it"

✅ **Código abierto**
- Revisa todo en GitHub
- Sin código oculto

---

## 📚 Documentación Técnica

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Diseño y componentes
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Cómo contribuir
- **[CHANGELOG.md](CHANGELOG.md)** — Historial de cambios

---

## 🚦 Para Desarrolladores

### Setup
```bash
git clone https://github.com/Francoooo22/bank-extractor.git
cd bank-extractor
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Ejecutar en desarrollo
```bash
python app.py  # Va a http://localhost:5000
```

### Hacer cambios
1. Edita el código
2. Flask se recarga automáticamente (debug=True)
3. Prueba en navegador

### Testing
```bash
# Prueba extracción con PDF específico
python -c "
from extractor import extraer_movimientos
r = extraer_movimientos('path/to/pdf.pdf', 'galicia')
for mov in r['movimientos']:
    print(mov)
"
```

---

## 📦 Dependencias

| Paquete | Versión | Uso |
|---------|---------|-----|
| Flask | ≥2.3.0 | Servidor web |
| pdfplumber | ≥0.10.0 | Lectura de PDFs |
| Pandas | ≥2.0.0 | Manipulación de datos |
| openpyxl | ≥3.1.0 | Escritura de Excel |
| werkzeug | ≥2.3.0 | Validación |

Instaladas automáticamente via `pip install -r requirements.txt`

---

## 📈 Roadmap

### v2.0 (próximas)
- [ ] Exportar a CSV, ODS, JSON
- [ ] Conciliación automática (comparar con mes anterior)
- [ ] Base de datos de históricos
- [ ] Interfaz modo oscuro
- [ ] API REST

### Futuro
- [ ] OCR para PDFs escaneados
- [ ] Validación CUIT/CBU
- [ ] Multi-idioma

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

1. **Reportar bugs:** [Issues](https://github.com/Francoooo22/bank-extractor/issues)
2. **Sugerir mejoras:** [Discussions](https://github.com/Francoooo22/bank-extractor/discussions)
3. **Hacer PRs:** Ver [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 Licencia

[MIT License](LICENSE) — Usa libremente en proyectos personales y comerciales.

---

## 👤 Autor

**Franco Bocchi**  
- 🌐 [GitHub](https://github.com/Francoooo22)
- 📧 bfproductosyservicios@gmail.com

---

## ❤️ Agradecimientos

- PDFPlumber por la librería de extracción PDF
- Flask por el framework web simple
- Pandas por manipulación de datos
- Todos los que reportan bugs y sugieren mejoras

---

**¿Preguntas?** Abre un [Issue](https://github.com/Francoooo22/bank-extractor/issues) o [Discussion](https://github.com/Francoooo22/bank-extractor/discussions) 🚀
