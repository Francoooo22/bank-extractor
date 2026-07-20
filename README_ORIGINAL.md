# 🏦 Extractor Bancario PDF → Excel

Herramienta local para convertir resúmenes bancarios en PDF a planillas Excel para conciliación.

## ⚡ Inicio rápido

### Requisitos
- Python 3.8 o superior (con `pip`)
- Conexión a internet la primera vez (para instalar dependencias)

### 1. Estructura de carpetas

```
bank_extractor/
├── app.py
├── extractor.py
├── lanzar.py
├── Iniciar_Windows.bat
├── Iniciar_Mac.command      # funciona también en Linux
├── requirements.txt
└── templates/
    └── index.html
```

### 2. Abrir la aplicación

| Sistema | Acción |
|---------|--------|
| **Windows** | Doble clic en `Iniciar_Windows.bat` |
| **Mac** | Doble clic en `Iniciar_Mac.command` ¹ |
| **Linux** | Doble clic en `Iniciar_Mac.command` ² |

> ¹ La primera vez en Mac: clic derecho → Abrir (el sistema pide confirmación por seguridad).  
> ² La primera vez en Linux, dar permisos desde terminal: `chmod +x Iniciar_Mac.command`

El lanzador se encarga de todo:
- Instala las dependencias automáticamente si faltan
- Arranca el servidor Flask
- Abre el navegador en `http://localhost:5000`

Para detener la aplicación, cerrá la ventana de consola.

---

## 🏦 Bancos soportados

| Banco | Estado |
|-------|--------|
| Banco Galicia | ✅ Soportado |
| Santander / Río | ✅ Soportado |
| BBVA / Francés | ✅ Soportado |
| Banco Macro | ✅ Soportado |
| Banco Nación (BNA) | ✅ Soportado |
| HSBC | ✅ Soportado |
| Cualquier otro | ✅ Modo genérico |

---

## 📊 Columnas del Excel generado

### Hoja "Movimientos"
| Columna | Descripción |
|---------|-------------|
| fecha | Fecha del movimiento |
| descripcion | Descripción o concepto |
| debito | Monto debitado (egreso) |
| credito | Monto acreditado (ingreso) |
| saldo | Saldo después del movimiento |
| referencia | Número de referencia/comprobante |
| tipo | D (débito) o C (crédito) |

### Hoja "Resumen"
Información general: banco, total de movimientos, fecha de extracción, totales de débitos y créditos.

---

## 💡 Consejos para mejores resultados

1. **Usá PDFs del home banking** — Los descargados directamente funcionan mejor que los escaneados
2. **Detección automática** — El sistema detecta el banco solo; podés seleccionarlo manualmente si hace falta
3. **Ver texto crudo** — Si hay problemas, usá el botón "Ver texto crudo" para diagnosticar qué ve el programa
4. **PDFs escaneados** — Si el PDF es una imagen escaneada los resultados serán limitados (requeriría OCR adicional)

---

## 🔧 Agregar soporte para más bancos

En `extractor.py`, dentro del diccionario `PATRONES`, agregá una entrada nueva:

```python
'mi_banco': {
    'movimiento': re.compile(
        r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)',
        re.IGNORECASE
    ),
    'fecha_fmt': '%d/%m/%Y',
},
```

---

## ❓ Problemas frecuentes

**"No se encontraron movimientos"**
- Probá seleccionar el banco correcto manualmente
- Usá "Ver texto crudo" para ver cómo se extrae el PDF
- Algunos PDFs están protegidos o son imágenes escaneadas

**Los montos no son correctos**
- Puede haber diferencias en el formato numérico del banco
- Revisá el texto crudo para ver cómo aparecen los números en ese PDF

**El Excel tiene filas vacías o incorrectas**
- Normal en modo genérico — filtrá las filas en Excel por la columna `fecha`

**Python no encontrado (Windows)**
- Instalalo desde https://www.python.org/downloads/
- Durante la instalación, marcá la opción **"Add Python to PATH"**
