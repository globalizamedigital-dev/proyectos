# leadhunter.spec — PyInstaller spec para generar ejecutable Windows .exe
#
# Uso:
#   pip install pyinstaller
#   pyinstaller leadhunter.spec
#
# El ejecutable se genera en dist/LeadHunterPro/LeadHunterPro.exe
# Para un solo archivo: cambiar onefile=True (más lento al iniciar)

import sys
from pathlib import Path

# Directorio raíz del proyecto
ROOT = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'gui')],
    binaries=[],
    datas=[
        # Incluir mappings, templates y scripts en el bundle
        (str(ROOT / 'mappings'), 'mappings'),
        (str(ROOT / 'templates'), 'templates'),
        (str(ROOT / 'scripts'), 'scripts'),
        (str(ROOT / 'gui'), 'gui'),
    ],
    hiddenimports=[
        # Módulos que PyInstaller puede no detectar automáticamente
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        'sqlite3',
        'smtplib',
        'email.mime.multipart',
        'email.mime.text',
        'urllib.robotparser',
        'xml.etree.ElementTree',
        'unicodedata',
        'hashlib',
        'queue',
        'threading',
        'concurrent.futures',
        # Scripts propios
        '_common',
        'borme',
        'ddg',
        'domain_resolver',
        'osm',
        'placsp',
        'aepd',
        'infosubvenciones',
        'cartociudad',
        'dirce',
        'infoempresa',
        'person_finder',
        'web_contact',
        'email_finder',
        'lead_scorer',
        'outreach',
        'discover',
        'analyze',
        'cross',
        # GUI
        'gui.app',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir módulos pesados no necesarios
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LeadHunterPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # Sin ventana de consola (solo GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,            # Añadir ruta a .ico si se tiene: icon='assets/icon.ico'
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LeadHunterPro',
)

# Para ejecutable de un solo archivo (más lento en inicio, sin carpeta):
# Descomentar y comentar el bloque COLLECT de arriba
#
# exe_onefile = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.datas,
#     [],
#     name='LeadHunterPro',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     runtime_tmpdir=None,
#     console=False,
#     icon=None,
#     onefile=True,
# )
