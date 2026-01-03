# -*- mode: python ; coding: utf-8 -*-
"""
CubeLab - Standalone Package
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

APP_NAME = "CubeLab"
APP_VERSION = "1.0.0"
ENTRY_SCRIPT = "GUI.py"

IS_WINDOWS = sys.platform == 'win32'
BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

# =====================================================
# 1. FORCE COLLECTION OF ALL DLLS
# =====================================================
all_datas = []
all_binaries = []
all_hiddenimports = []

# We explicitly collect PyQt6 here to fix the "DLL load failed" error
# We also collect vtkmodules and pyvistaqt because they are complex
packages_to_collect = ['PyQt6', 'vtkmodules', 'pyvista', 'pyvistaqt', 'pypore3d', 'pydantic']

for pkg in packages_to_collect:
    try:
        d, b, h = collect_all(pkg)
        all_datas += d
        all_binaries += b
        all_hiddenimports += h
        print(f"Collected full package: {pkg}")
    except Exception as e:
        print(f"Warning: Could not collect {pkg}: {e}")

# =====================================================
# 2. HIDDEN IMPORTS
# =====================================================
hidden_imports = list(set([
    'GUI', 'IDE', 'VoxelRenderer', 'Client', 'DiagnosticModule',
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.Qsci',
    'numpy', 'PIL', 'google.genai', 'pypore3d', 'scipy.spatial.transform._rotation_groups'
] + all_hiddenimports))

# =====================================================
# 3. DATA FILES
# =====================================================
datas = [
    (str(SRC_DIR / '.env'), '.'),
    (str(SRC_DIR / 'context.txt'), '.'),
    (str(SRC_DIR / 'pypore3d_function_reference.json'), '.'),
    (str(SRC_DIR / 'visual_context.json'), '.'),
    (str(SRC_DIR / 'resources'), 'resources'),
] + all_datas

# =====================================================
# 4. ANALYSIS
# =====================================================
a = Analysis(
    [str(SRC_DIR / ENTRY_SCRIPT)],
    pathex=[str(SRC_DIR)],
    binaries=all_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    
    # CRITICAL FIX: Point to your 'hooks' folder so VTK/PyVista hooks are found
    hookspath=['hooks'], 
    
    excludes=['tkinter', 'matplotlib', 'pandas', 'IPython', 'jupyter', 'pytest'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(SRC_DIR / 'resources' / 'images' / 'Icon.ico')
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name=APP_NAME)