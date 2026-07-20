@echo off
REM Script para ejecutar tests en Windows

echo.
echo 🧪 Ejecutando tests de Bank Extractor...
echo.

REM Instalar pytest si no está
python -m pip install pytest pytest-cov -q 2>nul

REM Ejecutar tests con cobertura
python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

echo.
echo ✅ Tests completados
echo 📊 Reporte HTML: htmlcov/index.html
echo.
pause
