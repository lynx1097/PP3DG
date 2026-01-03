# -*- mode: python ; coding: utf-8 -*-
"""
CubeLab-UserTesting - BULLETPROOF PyInstaller Spec
===================================================
"""

import sys
import os
from pathlib import Path

APP_NAME = "CubeLab-UserTesting"
ENTRY_SCRIPT = "User-Testing.py"
BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

# ============================================
# STEP 1: Import PyInstaller hooks SAFELY
# ============================================
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# ============================================
# STEP 2: Collect packages ONE BY ONE with error handling
# ============================================
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
# STEP 3: Collect PyQt6 MANUALLY (most reliable)
# ============================================
try:
    from PyInstaller.utils.hooks import get_package_paths
    _, qt_path = get_package_paths('PyQt6')
    
    # Collect Qt6 plugins directory
    qt_plugins = os.path.join(qt_path, 'Qt6', 'plugins')
    if os.path.isdir(qt_plugins):
        all_datas.append((qt_plugins, os.path.join('PyQt6', 'Qt6', 'plugins')))
        print(f"[OK] Added Qt6 plugins from {qt_plugins}")
    
    # Collect ALL DLLs from Qt6/bin
    qt_bin = os.path.join(qt_path, 'Qt6', 'bin')
    if os.path.isdir(qt_bin):
        for f in os.listdir(qt_bin):
            if f.endswith('.dll'):
                src = os.path.join(qt_bin, f)
                all_binaries.append((src, '.'))
        print(f"[OK] Added Qt6 DLLs from {qt_bin}")
        
except Exception as e:
    print(f"[WARN] PyQt6 manual collection failed: {e}")

# Also use collect_all for PyQt6 as backup
d, b, h = safe_collect('PyQt6')
all_datas += d
all_binaries += b
all_hiddenimports += h

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
    'google.generativeai',
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
    'time',
    'datetime',
    'platform',
    'functools',
    'uuid',
    
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

# ============================================
# STEP 6: Analysis
# ============================================
a = Analysis(
    [str(SRC_DIR / ENTRY_SCRIPT)],
    pathex=[str(SRC_DIR)],
    binaries=all_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', '_tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'IPython', 'jupyter', 'notebook',
        'pytest',
        'trame', 'trame_vtk', 'trame_vuetify', 'trame_client', 'trame_server',
    ],
    noarchive=False,
    optimize=0,
)

# ============================================
# STEP 7: Remove duplicate binaries
# ============================================
seen_binaries = set()
unique_binaries = []
for item in a.binaries:
    name = item[0]
    if name not in seen_binaries:
        seen_binaries.add(name)
        unique_binaries.append(item)
a.binaries = unique_binaries

# ============================================
# STEP 8: Build
# ============================================
pyz = PYZ(a.pure, a.zipped_data)

# Check if icon exists
icon_path = SRC_DIR / 'resources' / 'images' / 'Icon.ico'
exe_icon = str(icon_path) if icon_path.exists() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
