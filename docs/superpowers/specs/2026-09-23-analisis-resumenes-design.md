# Vista "Análisis de resúmenes bancarios" — Diseño

**Fecha**: 2026-09-23
**Estado**: Aprobado, pendiente de implementación

## Contexto y objetivo

Bank Extractor hoy convierte un PDF bancario a la vez en un Excel (`Movimientos` + `Resumen`). El usuario final (contador/estudio contable) frecuentemente necesita, después de tener varios de esos Excels ya generados (ej. los 12 meses de un cliente en un banco), un análisis agregado: composición de los movimientos por tipo de concepto (transferencias, gastos bancarios, impuestos, etc.), poder auditar el detalle de cada categoría, y exportar un Excel final organizado en una hoja por tipo de movimiento — útil para conciliación contable y presentación al cliente.

Esta feature agrega una nueva vista `/analisis` dentro de la misma app (mismo dominio/puerto), sin tocar el flujo existente de extracción PDF→Excel.

## No objetivos (fuera de alcance v1)

- No hay base de datos ni persistencia entre sesiones — si se recarga la página se pierde el trabajo de combinado/edición (decisión explícita del usuario).
- No hay deduplicación automática de movimientos si se sube el mismo archivo dos veces.
- No se soporta subir PDFs directamente en esta vista — solo los `.xlsx` que ya generó el flujo `/procesar` existente.
- No hay un modal "ver todos los movimientos sin filtrar" — solo modal por categoría (decisión explícita del usuario).
- No hay control de usuarios/login — mismo modelo de la app actual (herramienta local/interna, sin auth).

## Arquitectura

```
Browser (analisis.html)                     Flask (app.py)
┌──────────────────────────┐   POST /analisis/combinar   ┌─────────────────────────┐
│ Drop N .xlsx              │ ───────────────────────────▶│ Lee hoja "Movimientos"   │
│                            │                              │ de cada archivo,          │
│ Estado JS: array           │ ◀── JSON {movimientos,       │ concatena, categoriza     │
│ `movimientos` (mutable,    │      resumen} ───────────────│ (sin guardar estado)      │
│ incluye `categoria`)       │                              └─────────────────────────┘
│                            │
│ Gráfico (Chart.js local)   │
│ + tabla por categoría      │
│                            │
│ Click categoría → modal    │
│ con detalle + total,       │
│ <select> para recategorizar│
│ (edita el array en JS,     │
│ re-renderiza al cerrar)    │
│                            │   POST /analisis/exportar   ┌─────────────────────────┐
│ Botón "Exportar Excel"     │ ───────────────────────────▶│ Genera .xlsx multi-hoja  │
│                            │ ◀── {archivo: nombre.xlsx} ─│ (Resumen + 1 hoja/cat)   │
└──────────────────────────┘                              └─────────────────────────┘
                                                              descarga vía
                                                              GET /descargar/<nombre>
                                                              (endpoint ya existente)
```

Todo el estado post-combinado (incluidas las recategorizaciones manuales) vive en una variable JS global de la página — no hay sesión de servidor ni archivo temporal. El backend es puro request/response sin estado, igual que el resto de la app.

## Componentes

### 1. Backend: función `categorizar(descripcion, tipo)` (nuevo módulo o función en `extractor.py`)

Clasifica un movimiento en una de 8 categorías según keywords en `descripcion` (case-insensitive, sin acentos) y la señal `tipo` (`D`/`C`) ya calculada por el extractor:

| Categoría | Regla |
|---|---|
| Transferencias recibidas | contiene "transfer" y `tipo == 'C'` |
| Transferencias emitidas | contiene "transfer" y `tipo == 'D'` |
| Gastos bancarios / aranceles | contiene "comision", "arancel", "mantenimiento", "gasto banc" |
| Impuestos | contiene "iva", "impuesto", "ley 25413", "percepcion", "retencion" |
| Pagos de servicios | contiene "debito automatico", "pago serv", "factura" |
| Extracciones / Depósitos efectivo | contiene "extraccion", "cajero", "atm", "deposito efectivo" |
| Otros débitos | ninguna regla anterior matchea y `tipo == 'D'` |
| Otros créditos | ninguna regla anterior matchea y `tipo == 'C'` |

Orden de evaluación: transferencias → gastos → impuestos → servicios → efectivo → fallback por signo. Las reglas son keywords iniciales; se espera afinarlas con casos reales, mismo patrón que los fixes de clasificación D/C ya aplicados en Nación (commits `426326e`, `215baa1`).

### 2. Backend: endpoint `POST /analisis/combinar`

- Recibe N archivos `.xlsx` (`request.files.getlist(...)`).
- Por archivo: `pandas.read_excel(archivo, sheet_name='Movimientos')`.
- Valida columnas mínimas esperadas (`fecha, descripcion, importe, tipo`) — si faltan, error 400 con el nombre del archivo problemático.
- Concatena todos los DataFrames.
- Si el resultado está vacío → error 422.
- Aplica `categorizar()` fila a fila → agrega columna `categoria`.
- Devuelve JSON:
  ```json
  {
    "movimientos": [ {"fecha": "...", "descripcion": "...", "importe": -1500.0, "categoria": "Gastos bancarios / aranceles", "documento": "...", ...}, ... ],
    "resumen": { "Gastos bancarios / aranceles": {"cantidad": 12, "total": -18500.0}, ... }
  }
  ```

### 3. Backend: endpoint `POST /analisis/exportar`

- Recibe el mismo array `movimientos` (JSON, ya con `categoria` posiblemente editada a mano) en el body.
- Agrupa por `categoria`.
- Genera `.xlsx` en `outputs/analisis_<timestamp>.xlsx`:
  - Hoja `Resumen`: una fila por categoría (cantidad, total $) + fila de total general.
  - Una hoja por categoría con movimientos > 0 (se omiten las vacías), mismas columnas que la hoja `Movimientos` actual.
- Devuelve `{ok: true, archivo: "analisis_<timestamp>.xlsx"}`.
- Descarga vía el endpoint `GET /descargar/<nombre>` ya existente (no se crea uno nuevo).

### 4. Frontend: `templates/analisis.html` + ruta `GET /analisis`

- Mismo look & feel que `index.html`/`seguros.html` (reutilizar CSS existente).
- Zona de drop múltiple → `POST /analisis/combinar` → guarda la respuesta en `let movimientos = [...]` (variable global).
- Gráfico de torta con Chart.js (vendorizado en `/static/vendor/chart.umd.min.js`, sin CDN) mostrando `resumen` por categoría, más tabla resumen debajo.
- Click en categoría (porción del gráfico o fila de tabla) → abre modal con los movimientos de esa categoría filtrados client-side desde `movimientos`, total al pie, `<select>` por fila para recategorizar (muta el array global).
- Al cerrar el modal, re-renderiza gráfico y tabla desde el array actualizado.
- Botón "Exportar Excel" → `POST /analisis/exportar` con el array actual → redirige a `/descargar/<nombre>` de la respuesta.

## Manejo de errores

- Archivo no es `.xlsx` válido generado por esta app (faltan columnas) → 400, mensaje indica qué archivo.
- Ningún movimiento tras combinar → 422 ("No se encontraron movimientos en los archivos subidos").
- Errores de parseo de un archivo individual no abortan el resto — se reporta cuál archivo falló y se listan los demás que sí se procesaron (para que el usuario sepa cuál re-subir).

## Testing

Nuevos tests en `tests/` (proyecto ya tiene 60 con `pytest`):
- `categorizar()`: un caso por categoría + un caso de fallback a "Otros débitos"/"Otros créditos".
- `/analisis/combinar`: combinar 2 Excels de prueba (fixtures nuevos en `tests/fixtures/`) y verificar `resumen` agregado correctamente.
- `/analisis/combinar`: archivo con columnas faltantes → 400.
- `/analisis/exportar`: verificar que el `.xlsx` resultante tiene una hoja por categoría con movimientos y omite las vacías.

## Vendorizado de Chart.js

Descargar `chart.umd.min.js` (versión estable, ej. 4.x) y guardarlo en `static/vendor/`, servido por Flask como estático — sin request a ningún CDN externo, preservando el "100% local / sin dependencias externas" del README.
