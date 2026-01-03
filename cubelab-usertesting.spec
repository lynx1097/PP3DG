# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, get_package_paths, collect_submodules

APP_NAME = "CubeLab-UserTesting"
ENTRY_SCRIPT = "User-Testing.py"
BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

all_datas, all_binaries, all_hiddenimports = [], [], []

# ============================================
# FIX 1: Properly collect PyQt6 with all DLLs
# ============================================
try:
    qt_path = get_package_paths('PyQt6')[1]
    
    # Collect Qt6 plugins
    qt_plugins = os.path.join(qt_path, 'Qt6', 'plugins')
    if os.path.exists(qt_plugins):
        all_datas.append((qt_plugins, 'PyQt6/Qt6/plugins'))
    
    # Collect Qt6 bin directory (contains core DLLs - CRITICAL FOR WINDOWS)
    qt_bin = os.path.join(qt_path, 'Qt6', 'bin')
    if os.path.exists(qt_bin):
        for dll in os.listdir(qt_bin):
            if dll.endswith('.dll'):
                all_binaries.append((os.path.join(qt_bin, dll), '.'))
    
    # Collect Qt6 lib directory (some DLLs may be here too)
    qt_lib = os.path.join(qt_path, 'Qt6', 'lib')
    if os.path.exists(qt_lib):
        for dll in os.listdir(qt_lib):
            if dll.endswith('.dll'):
                all_binaries.append((os.path.join(qt_lib, dll), '.'))
                
except Exception as e:
    print(f"Warning: Could not collect PyQt6 paths: {e}")

# ============================================
# FIX 2: Use collect_all for all packages including PyQt6
# ============================================
packages = [
    'PyQt6',           # Added PyQt6 to collect_all
    'PyQt6.sip',       # Required for PyQt6
    'vtkmodules',
    'pyvista',
    'pyvistaqt',
    'pypore3d',
    'pydantic',
]

for pkg in packages:
    try:
        d, b, h = collect_all(pkg)
        all_datas += d
        all_binaries += b
        all_hiddenimports += h
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# ============================================
# FIX 3: Comprehensive hidden imports
# ============================================
hidden_imports = list(set([
    # Your app modules
    'GUI', 'IDE', 'VoxelRenderer', 'Client', 'DiagnosticModule',
    
    # PyQt6 core modules
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.Qsci',
    'PyQt6.sip',
    
    # PyQt6 additional modules (often missing)
    'PyQt6.QtOpenGL',
    'PyQt6.QtOpenGLWidgets',
    'PyQt6.QtSvg',
    'PyQt6.QtSvgWidgets',
    'PyQt6.QtNetwork',
    'PyQt6.QtPrintSupport',
    
    # Other dependencies
    'numpy',
    'PIL',
    'PIL._tkinter_finder',  # Prevents PIL import issues
    'google.genai',
    'pypore3d',
    
    # VTK/PyVista related
    'vtkmodules.all',
    'vtkmodules.util.numpy_support',
    'vtkmodules.numpy_interface',
    'vtkmodules.qt.QVTKRenderWindowInteractor',
] + all_hiddenimports))

# ============================================
# FIX 4: Collect PyQt6 submodules explicitly
# ============================================
try:
    hidden_imports += collect_submodules('PyQt6')
except Exception:
    pass

# ============================================
# Data files
# ============================================
datas = [
    (str(SRC_DIR / '.env'), '.'),
    (str(SRC_DIR / 'context.txt'), '.'),
    (str(SRC_DIR / 'pypore3d_function_reference.json'), '.'),
    (str(SRC_DIR / 'visual_context.json'), '.'),
    (str(SRC_DIR / 'resources'), 'resources'),
] + all_datas

# ============================================
# Analysis
# ============================================
a = Analysis(
    [str(SRC_DIR / ENTRY_SCRIPT)],
    pathex=[str(SRC_DIR)],
    binaries=all_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 
        'matplotlib', 
        'pandas', 
        'IPython', 
        'jupyter', 
        'pytest',
        '_tkinter',
    ],
    noarchive=False,
    optimize=0,
)

# ============================================
# FIX 5: Remove duplicate binaries (can cause issues)
# ============================================
seen = set()
a.binaries = [x for x in a.binaries if not (x[0] in seen or seen.add(x[0]))]

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Keep UPX disabled - it can corrupt Qt DLLs
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(SRC_DIR / 'resources' / 'images' / 'Icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,  # Keep UPX disabled
    upx_exclude=[],
    name=APP_NAME,
)