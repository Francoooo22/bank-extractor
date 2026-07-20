#!/bin/bash
# Iniciar_Mac.command
# Doble clic para abrir la app en Mac

cd "$(dirname "$0")"

# Verificar Python
if ! command -v python3 &>/dev/null; then
    osascript -e 'display alert "Python no encontrado" message "Instalá Python desde https://www.python.org/downloads/" as critical'
    exit 1
fi

python3 lanzar.py
