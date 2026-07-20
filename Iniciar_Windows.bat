@echo off
title Extractor Bancario
cd /d "%~dp0"

:: Verificar que Python esté instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python no encontrado.
    echo  Instalalo desde https://www.python.org/downloads/
    echo  Asegurate de marcar "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b 1
)

python lanzar.py
pause
