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

## Versión portable (offline)
- Build local Linux: `./build_linux.sh` → `dist/BankExtractor/`. Windows: `build_windows.bat` (en Windows) o el workflow de Actions `Build Windows portable` (`gh workflow run build-windows.yml`, luego `gh run download <id> -n BankExtractor-windows`).
- `BankExtractor.spec` es la config de PyInstaller; entrada = `lanzar.py`. `python-magic` no se usa en el código y está excluido.
- Modo empaquetado: `sys.frozen` → datos junto al exe, recursos en `sys._MEIPASS` (ver `app.py`).
- ZIP Windows entregado en `C:\Users\pc_wolf_05\Downloads\BankExtractor-windows.zip` (`/mnt/c/Users/pc_wolf_05/Downloads/`).
- Pendiente opcional: fijar actions por SHA y dependencias de pip con versión en el workflow.

## Branch actual
`main` (seguros ya mergeado; `feature/extractor-seguros` quedó como rama vieja)
