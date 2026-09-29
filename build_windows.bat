@echo off
:: Genera dist\BankExtractor\ (carpeta portable). Requiere Python 3.10+ en Windows, con internet SOLO para construir.
pushd "%~dp0"
python -m venv .buildenv || goto :err
call .buildenv\Scripts\activate.bat
python -m pip install --quiet flask pdfplumber pandas openpyxl pyinstaller || goto :err
pyinstaller BankExtractor.spec --noconfirm || goto :err
echo.
echo  Listo: dist\BankExtractor\BankExtractor.exe
echo  Comprimi la carpeta dist\BankExtractor en un ZIP para compartirla.
popd
pause
exit /b 0
:err
echo  ERROR en el build.
popd
pause
exit /b 1
