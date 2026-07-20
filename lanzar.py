"""
lanzar.py · Lanzador automático del Extractor Bancario
- Instala dependencias si faltan
- Arranca Flask en segundo plano
- Abre el navegador automáticamente
"""

import sys
import subprocess
import importlib
import threading
import time
import webbrowser
import socket

DEPENDENCIAS = [
    ('flask',      'flask>=2.3.0'),
    ('pdfplumber', 'pdfplumber>=0.10.0'),
    ('pandas',     'pandas>=2.0.0'),
    ('openpyxl',   'openpyxl>=3.1.0'),
    ('werkzeug',   'werkzeug>=2.3.0'),
]

PUERTO = 5000


# ── 1. Instalar dependencias faltantes ──────────────────────────────────────

def instalar_si_falta():
    faltantes = []
    for modulo, paquete in DEPENDENCIAS:
        try:
            importlib.import_module(modulo)
        except ImportError:
            faltantes.append(paquete)

    if faltantes:
        print(f"\n📦 Instalando dependencias: {', '.join(faltantes)}\n")
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '--quiet'] + faltantes
        )
        print("✅ Dependencias instaladas.\n")


# ── 2. Esperar que Flask esté listo ─────────────────────────────────────────

def esperar_puerto(puerto, timeout=15):
    """Intenta conectarse al puerto hasta que responda."""
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            with socket.create_connection(('127.0.0.1', puerto), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


# ── 3. Abrir navegador cuando Flask esté listo ──────────────────────────────

def abrir_navegador(puerto):
    if esperar_puerto(puerto):
        webbrowser.open(f'http://localhost:{puerto}')
    else:
        print("⚠️  No se pudo confirmar que Flask arrancó. Abrí http://localhost:5000 manualmente.")


# ── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 52)
    print("  🏦  Extractor Bancario PDF → Excel")
    print("=" * 52)

    # Instalar deps
    instalar_si_falta()

    # Importar la app Flask (después de instalar)
    from app import app

    # Hilo que abre el navegador en cuanto Flask responda
    t = threading.Thread(target=abrir_navegador, args=(PUERTO,), daemon=True)
    t.start()

    print(f"\n🚀 Servidor corriendo en http://localhost:{PUERTO}")
    print("   Cerrá esta ventana para detener la aplicación.\n")

    # Arrancar Flask (bloquea hasta que se cierre la ventana)
    app.run(debug=False, port=PUERTO, use_reloader=False)
