# Bank Extractor — Contexto para Agentes

## Resumen
Proyecto dual: extractor de resúmenes bancarios + extractor de pólizas de seguro PDF → Excel.

## Estructura
- `extractor.py` — Motor de extracción bancaria (pdfplumber, 3 estrategias, 10+ bancos)
- `extractor_seguros.py` — Motor de extracción de pólizas de seguro (regex sobre texto plano)
- `app.py` — Flask web server (rutas `/` bancario, `/seguros` seguro)
- `lanzar.py` — Lanzador con detección automática (`--seguros` para modo CLI)
- `templates/` — `index.html` (bancario), `seguros.html` (seguros)
- `tests/` — 60 tests (40 bancario + 20 seguros)

## PDFs de prueba (en Windows)
- `/mnt/c/Users/pc_wolf_05/Downloads/RESUMEN DE CUENTA 1.pdf` (5906 pólizas)
- `/mnt/c/Users/pc_wolf_05/Downloads/RESUMEN DE CUENTA 2.pdf` (2352 pólizas)

## Cómo usar
```bash
source venv/bin/activate
python lanzar.py                          # web app (bancario + seguros)
python lanzar.py --seguros archivo.pdf    # CLI directo seguros
python -m pytest tests/ -v                # todos los tests
```

## Formato de datos extraídos (seguros)
Columnas: POLIZA, VIGENCIA_DESDE, VIGENCIA_HASTA, SALDO, TP, VENCIMIENTO, INTERES, FACTURA, ASEGURADO_OBJETO

El campo ASEGURADO_OBJETO contiene artefactos numéricos del PDF (ej: "bel1e5n49" → "belen"). Usar `limpiar_texto_asegurado()` para limpiar.

## Branch actual
`feature/extractor-seguros` — commit e65ea9b
