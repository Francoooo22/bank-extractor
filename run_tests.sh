#!/bin/bash
# Script para ejecutar tests con cobertura

echo "🧪 Ejecutando tests de Bank Extractor..."
echo ""

# Instalar pytest si no está
python -m pip install pytest pytest-cov -q 2>/dev/null

# Ejecutar tests con cobertura
python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

echo ""
echo "✅ Tests completados"
echo "📊 Reporte HTML: htmlcov/index.html"
