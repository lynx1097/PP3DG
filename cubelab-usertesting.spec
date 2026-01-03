# -*- mode: python ; coding: utf-8 -*-
"""
CubeLab-UserTesting - SUS Testing Package
==========================================
Creates a fully self-contained executable with ALL dependencies bundled.
"""

import sys
import os
from pathlib import Path

# =====================================================
# CONFIGURATION
# =====================================================

APP_NAME = "CubeLab-UserTesting"
APP_VERSION = "1.0.0"
ENTRY_SCRIPT = "User-Testing.py"

IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

# =====================================================
# COLLECT ALL HIDDEN IMPORTS
# =====================================================

hidden_imports = [
    # PyQt6 - ALL modules
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'PyQt6.Qsci',
    'PyQt6.sip',
    
    # PyVista / VTK
    'pyvista',
    'pyvistaqt',
    'pyvistaqt.plotting',
    'vtk',
    'vtkmodules',
    'vtkmodules.all',
    'vtkmodules.util',
    'vtkmodules.util.numpy_support',
    'vtkmodules.numpy_interface',
    'vtkmodules.numpy_interface.dataset_adapter',
    
    # NumPy
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.core._dtype_ctypes',
    'numpy.lib',
    'numpy.lib.format',
    
    # PIL
    'PIL',
    'PIL.Image',
    
    # Google GenAI
    'google',
    'google.genai',
    'google.genai.types',
    
    # Pydantic
    'pydantic',
    'pydantic.fields',
    'pydantic_core',
    
    # System
    'psutil',
    'dotenv',
    'json',
    'uuid',
    'tempfile',
    'traceback',
    'ast',
    're',
    'time',
    'datetime',
    'platform',
    'functools',
    
    # Telemetry
    'newrelic_telemetry_sdk',
    
    # pypore3d
    'pypore3d',
    'pypore3d.p3dFiltPy',
    'pypore3d.p3dFiltPy_16',
    'pypore3d.p3dBlobPy',
    'pypore3d.p3dSkelPy',
    'pypore3d._p3dFilt',
    'pypore3d._p3dBlob',
    'pypore3d._p3dSkel',
    
    # Application modules
    'GUI',
    'IDE',
    'VoxelRenderer', 
    'Client',
    'DiagnosticModule',
]

# =====================================================
# DATA FILES
# =====================================================

datas = [
    (str(SRC_DIR / '.env'), '.'),
    (str(SRC_DIR / 'context.txt'), '.'),
    (str(SRC_DIR / 'pypore3d_function_reference.json'), '.'),
    (str(SRC_DIR / 'visual_context.json'), '.'),
    (str(SRC_DIR / 'resources'), 'resources'),
]

binaries = []

excludes = [
    'tkinter', '_tkinter', 'matplotlib', 'scipy', 'pandas',
    'IPython', 'jupyter', 'notebook', 'pytest', 'sphinx',
    'setuptools', 'pip', 'wheel', 'test', 'tests',
]

# =====================================================
# ANALYSIS
# =====================================================

a = Analysis(
    [str(SRC_DIR / ENTRY_SCRIPT)],
    pathex=[str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],  # Use PyInstaller's built-in hooks only
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

# =====================================================
# COLLECT DEPENDENCIES
# =====================================================

from PyInstaller.utils.hooks import collect_all

for pkg in ['vtkmodules', 'pyvista', 'pyvistaqt', 'pypore3d', 'pydantic']:
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
        a.datas.extend(pkg_datas)
        a.binaries.extend(pkg_binaries)
        a.hiddenimports.extend(pkg_hiddenimports)
    except Exception as e:
        print(f"{pkg} collection: {e}")

# =====================================================
# BUILD
# =====================================================

pyz = PYZ(a.pure, a.zipped_data)

exe_options = {
    'name': APP_NAME,
    'debug': False,
    'strip': False,
    'upx': True,
    'console': False,
}

if IS_WINDOWS:
    icon_path = SRC_DIR / 'resources' / 'images' / 'Icon.ico'
    if icon_path.exists():
        exe_options['icon'] = str(icon_path)
elif IS_MACOS:
    icon_path = SRC_DIR / 'resources' / 'images' / 'Icon.icns'
    if icon_path.exists():
        exe_options['icon'] = str(icon_path)

exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_options)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name=APP_NAME)

if IS_MACOS:
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=str(SRC_DIR / 'resources' / 'images' / 'Icon.icns') if (SRC_DIR / 'resources' / 'images' / 'Icon.icns').exists() else None,
        bundle_identifier='com.cubelab.usertesting',
        version=APP_VERSION,
        info_plist={
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': 'Cube Lab - User Testing',
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15',
        },
    )
