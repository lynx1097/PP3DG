# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

# =========================================================
# 1. CONFIGURATION & DEBLOATING
# =========================================================
block_cipher = None

all_datas = []
all_binaries = []
all_hiddenimports = []

def safe_collect(package_name):
    """Safely collect a package, return empty lists on failure."""
    try:
        datas, binaries, hiddenimports = collect_all(package_name)
        print(f"[OK] Collected {package_name}: {len(datas)} datas, {len(binaries)} binaries")
        return datas, binaries, hiddenimports
    except Exception as e:
        print(f"[SKIP] {package_name}: {e}")
        return [], [], []


# Collect VTK first (largest)
d, b, h = safe_collect('vtkmodules')
all_datas += d
all_binaries += b
all_hiddenimports += h

# Collect PyVista
d, b, h = safe_collect('pyvista')
all_datas += d
all_binaries += b
all_hiddenimports += h

# Collect pyvistaqt
d, b, h = safe_collect('pyvistaqt')
all_datas += d
all_binaries += b
all_hiddenimports += h

# Collect pypore3d (may not exist)
d, b, h = safe_collect('pypore3d')
all_datas += d
all_binaries += b
all_hiddenimports += h

# Collect pydantic
d, b, h = safe_collect('pydantic')
all_datas += d
all_binaries += b
all_hiddenimports += h

# ============================================
# STEP 3: Collect PyQt6 (Platform Specific)
# ============================================

# 1. Windows: Manual collection (Required for stability)
if sys.platform == 'win32':
    try:
        from PyInstaller.utils.hooks import get_package_paths
        _, qt_path = get_package_paths('PyQt6')
        
        # Collect Qt6 plugins directory
        qt_plugins = os.path.join(qt_path, 'Qt6', 'plugins')
        if os.path.isdir(qt_plugins):
            all_datas.append((qt_plugins, os.path.join('PyQt6', 'Qt6', 'plugins')))
        
        # Collect ALL DLLs from Qt6/bin
        qt_bin = os.path.join(qt_path, 'Qt6', 'bin')
        if os.path.isdir(qt_bin):
            for f in os.listdir(qt_bin):
                if f.endswith('.dll'):
                    src = os.path.join(qt_bin, f)
                    all_binaries.append((src, '.'))
    except Exception as e:
        print(f"[WARN] PyQt6 manual collection failed: {e}")
else:
    print("[INFO] Skipping manual PyQt6 collection for macOS/Linux to prevent symlink errors.")
  

# Binaries: Define Windows system DLLs only if on Windows
my_binaries = []
if sys.platform == 'win32':
    my_binaries = [
        ('C:\\Windows\\System32\\downlevel\\api-ms-win-crt-*.dll', '.'),
        ('C:\\Windows\\System32\\ucrtbase.dll', '.'),
    ]

# Excludes: Aggressive cleanup to save space safely
safe_excludes = [
    # GUI Frameworks we don't use
    'tkinter', '_tkinter', 'tcl', 'tk',
    'PySide2', 'PySide6', 'wx', 'Gtk', 'GTK3',
    
    # Heavy SciPy/Pandas if not used (remove if you need them!)
    'scipy', 'pandas', 'notebook', 'jupyter', 'IPython',
    'matplotlib.tests', 'numpy.tests',
    
    # Qt Bloatware (Safe to remove if not using Web/NFC/Bluetooth)
    'PyQt6.QtWebEngine', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtBluetooth', 'PyQt6.QtNfc', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
    'PyQt6.QtDesigner', 'PyQt6.QtHelp', 'PyQt6.QtTest', 'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets', 'PyQt6.QtQuick', 'PyQt6.QtQuickWidgets',
    'PyQt6.QtQml', 'PyQt6.uic',
    
    # Standard Lib Bloat
    'trame', 'trame_vtk', 'trame_vuetify', 'trame_client', 'trame_server',

    'curses', 'html', 'unittest', 'pydoc', 'xml.dom.domreg',
]
# ============================================
# STEP 4: Define ALL hidden imports explicitly
# ============================================
hidden_imports = [
    # Application modules
    'GUI', 'IDE', 'VoxelRenderer', 'Client', 'DiagnosticModule',
    
    # PyQt6 - EVERY module
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.Qsci',
    'PyQt6.sip',
    'PyQt6.QtOpenGL',
    'PyQt6.QtOpenGLWidgets',
    'PyQt6.QtSvg',
    'PyQt6.QtNetwork',
    'PyQt6.QtPrintSupport',
    
    # NumPy
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.core._dtype_ctypes',
    'numpy.lib.format',
    
    # PIL
    'PIL',
    'PIL.Image',
    
    # Google
    'google.genai',
    
    # Pydantic
    'pydantic',
    'pydantic_core',
    
    # System
    'psutil',
    'dotenv',
    'json',
    'tempfile',
    'pathlib',
    
    # Telemetry
    'newrelic_telemetry_sdk',
    
    # pypore3d
    'pypore3d',
    'pypore3d.p3dFiltPy',
    'pypore3d.p3dFiltPy_16',
    'pypore3d.p3dBlobPy',
    'pypore3d.p3dSkelPy',
    
    # VTK
    'vtkmodules',
    'vtkmodules.all',
    'vtkmodules.util.numpy_support',
    'vtkmodules.qt.QVTKRenderWindowInteractor',
]

# Add collected hiddenimports
hidden_imports = list(set(hidden_imports + all_hiddenimports))

# ============================================
# STEP 5: Data files
# ============================================
datas = [
    (str(SRC_DIR / '.env'), '.'),
    (str(SRC_DIR / 'context.txt'), '.'),
    (str(SRC_DIR / 'pypore3d_function_reference.json'), '.'),
    (str(SRC_DIR / 'visual_context.json'), '.'),
    (str(SRC_DIR / 'resources'), 'resources'),
] + all_datas

# =========================================================
# 2. ANALYSIS (Process both scripts)
# =========================================================

# --- Analysis 1: Main GUI ---
a1 = Analysis(
    ['src/GUI.py'],  # Main Entry Point
    pathex=[str(SRC_DIR)],
    binaries=my_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=safe_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --- Analysis 2: User Testing ---
a2 = Analysis(
    ['src/User-Testing.py'],  # Second Entry Point
    pathex=[str(SRC_DIR)],
    binaries=my_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=safe_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
# ============================================
# STEP 7: Remove duplicate binaries
# ============================================
seen_binaries1 = set()
seen_binaries2 = set()
unique_binaries1 = []
unique_binaries2 = []
for item in a1.binaries:
    name = item[0]
    if name not in seen_binaries1:
        seen_binaries1.add(name)
        unique_binaries1.append(item)
a1.binaries = 

for item in a2.binaries:
    name = item[0]
    if name not in seen_binaries2:
        seen_binaries2.add(name)
        unique_binaries2.append(item)
a2.binaries = unique_binaries2

# =========================================================
# 3. MERGE & BUILD (Deduplication happens here)
# =========================================================

# Create PYZ archives (Python bytecode)
pyz1 = PYZ(a1.pure, a1.zipped_data, cipher=block_cipher)
pyz2 = PYZ(a2.pure, a2.zipped_data, cipher=block_cipher)
# Check if icon exists
icon_path = SRC_DIR / 'resources' / 'images' / 'Icon.ico'
exe_icon = str(icon_path) if icon_path.exists() else None

# Create EXE 1 (CubeLab)
exe1 = EXE(
    pyz1,
    a1.scripts,
    [],
    exclude_binaries=True,
    name='CubeLab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip symbols to save space
    upx=False,
    console=False, # Set to True if you want a terminal window for debugging
    icon=exe_icon,
)

# Create EXE 2 (UserTesting)
exe2 = EXE(
    pyz2,
    a2.scripts,
    [],
    exclude_binaries=True,
    name='CubeLab-UserTesting',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
    icon=exe_icon,
)

# COLLECT: Bundles both EXEs into ONE folder with shared libraries
coll = COLLECT(
    exe1,
    a1.binaries, a1.datas,
    
    exe2,
    # Note: We don't need a2.binaries/datas here if they are identical, 
    # but passing them ensures unique deps from the second script are included.
    # COLLECT automatically removes duplicates.
    a2.binaries, a2.datas,
    
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CubeLab_Suite', # Name of the output folder
)