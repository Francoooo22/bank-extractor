# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller BankExtractor.spec --noconfirm
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static')]
binaries, hiddenimports = [], []
for pkg in ('pdfplumber', 'pdfminer', 'openpyxl'):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

a = Analysis(
    ['lanzar.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=['pytest', 'gunicorn', 'magic', 'tkinter', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='BankExtractor',
    console=True,   # ventana visible: cerrarla detiene la app
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name='BankExtractor')
