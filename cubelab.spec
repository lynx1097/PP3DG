# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, get_package_paths

APP_NAME = "CubeLab"
ENTRY_SCRIPT = "GUI.py"
BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

# 1. Collect dependencies
all_datas, all_binaries, all_hiddenimports = [], [], []

# Collect PyQt6 separately to ensure plugins are included
# This provides the necessary 'qwindows.dll' platform plugin
qt_path = get_package_paths('PyQt6')[1]
qt_plugins = os.path.join(qt_path, 'Qt6', 'plugins')
if os.path.exists(qt_plugins):
    all_datas.append((qt_plugins, 'PyQt6/Qt6/plugins'))

# Force collection for other complex modules
packages = ['vtkmodules', 'pyvista', 'pyvistaqt', 'pypore3d', 'pydantic']
for pkg in packages:
    try:
        d, b, h = collect_all(pkg)
        all_datas += d
        all_binaries += b
        all_hiddenimports += h
    except Exception as e:
        print(f"Warning: {pkg} collection issue: {e}")

hidden_imports = list(set([
    'GUI', 'IDE', 'VoxelRenderer', 'Client', 'DiagnosticModule',
    'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.Qsci',
    'numpy', 'PIL', 'google.genai', 'pypore3d', 'scipy.spatial.transform._rotation_groups'
] + all_hiddenimports))

datas = [
    (str(SRC_DIR / '.env'), '.'),
    (str(SRC_DIR / 'context.txt'), '.'),
    (str(SRC_DIR / 'pypore3d_function_reference.json'), '.'),
    (str(SRC_DIR / 'visual_context.json'), '.'),
    (str(SRC_DIR / 'resources'), 'resources'),
] + all_datas

a = Analysis(
    [str(SRC_DIR / ENTRY_SCRIPT)],
    pathex=[str(SRC_DIR)],
    binaries=all_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=['hooks'], # Keep using your custom hooks [cite: 193]
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
    upx=False,  # CRITICAL: Disable UPX [cite: 193]
    console=False,
    icon=str(SRC_DIR / 'resources' / 'images' / 'Icon.ico')
)

coll = COLLECT(
    exe, a.binaries, a.datas, 
    strip=False, 
    upx=False,  # CRITICAL: Disable UPX [cite: 193]
    name=APP_NAME
)