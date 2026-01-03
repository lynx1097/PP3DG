# -*- mode: python ; coding: utf-8 -*-
"""
CubeLab-UserTesting - SUS Testing Package
"""

import sys
from pathlib import Path

APP_NAME = "CubeLab-UserTesting"
APP_VERSION = "1.0.0"
ENTRY_SCRIPT = "User-Testing.py"

IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

# =====================================================
# COLLECT DEPENDENCIES BEFORE ANALYSIS
# =====================================================

from PyInstaller.utils.hooks import collect_all, collect_submodules

all_datas = []
all_binaries = []
all_hiddenimports = []

# Added 'PyQt6' here to force collection of all Qt DLLs and plugins
for pkg in ['PyQt6', 'vtkmodules', 'pyvista', 'pyvistaqt', 'pypore3d', 'pydantic']:
    try:
        d, b, h = collect_all(pkg)
        all_datas += d
        all_binaries += b
        all_hiddenimports += h
        print(f"Collected {pkg}")
    except Exception as e:
        print(f"Skip {pkg}: {e}")

# =====================================================
# HIDDEN IMPORTS
# =====================================================

hidden_imports = list(set([
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.Qsci',
    'numpy', 'numpy.core._methods', 'numpy.lib.format',
    'PIL', 'PIL.Image',
    'google.genai', 'google.genai.types',
    'pydantic', 'pydantic_core',
    'psutil', 'dotenv', 'newrelic_telemetry_sdk',
    'pypore3d', 'pypore3d.p3dFiltPy', 'pypore3d.p3dFiltPy_16',
    'pypore3d.p3dBlobPy', 'pypore3d.p3dSkelPy',
    'GUI', 'IDE', 'VoxelRenderer', 'Client', 'DiagnosticModule',
    'time', 'datetime', 'platform', 'functools', 'uuid',
] + all_hiddenimports))

# =====================================================
# DATA FILES
# =====================================================

datas = [
    (str(SRC_DIR / '.env'), '.'),
    (str(SRC_DIR / 'context.txt'), '.'),
    (str(SRC_DIR / 'pypore3d_function_reference.json'), '.'),
    (str(SRC_DIR / 'visual_context.json'), '.'),
    (str(SRC_DIR / 'resources'), 'resources'),
] + all_datas

binaries = all_binaries

excludes = ['tkinter', 'matplotlib', 'scipy', 'pandas', 'IPython', 'jupyter', 'pytest']

# =====================================================
# ANALYSIS
# =====================================================

a = Analysis(
    [str(SRC_DIR / ENTRY_SCRIPT)],
    pathex=[str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    # Pointed to your 'hooks' directory
    hookspath=['hooks'],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe_kwargs = {'name': APP_NAME, 'debug': False, 'strip': False, 'upx': True, 'console': False}

if IS_WINDOWS and (SRC_DIR / 'resources' / 'images' / 'Icon.ico').exists():
    exe_kwargs['icon'] = str(SRC_DIR / 'resources' / 'images' / 'Icon.ico')
elif IS_MACOS and (SRC_DIR / 'resources' / 'images' / 'Icon.icns').exists():
    exe_kwargs['icon'] = str(SRC_DIR / 'resources' / 'images' / 'Icon.icns')

exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_kwargs)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name=APP_NAME)

if IS_MACOS:
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=str(SRC_DIR / 'resources' / 'images' / 'Icon.icns') if (SRC_DIR / 'resources' / 'images' / 'Icon.icns').exists() else None,
        bundle_identifier='com.cubelab.usertesting',
        version=APP_VERSION,
        info_plist={'CFBundleName': APP_NAME, 'NSHighResolutionCapable': True},
    )