#!/usr/bin/env bash
# Genera dist/BankExtractor/ (carpeta portable). Internet solo para construir.
set -e
cd "$(dirname "$0")"
python3 -m venv .buildenv
source .buildenv/bin/activate
pip install --quiet flask pdfplumber pandas openpyxl pyinstaller
pyinstaller BankExtractor.spec --noconfirm
echo "Listo: dist/BankExtractor/BankExtractor"
