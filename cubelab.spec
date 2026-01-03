# -*- mode: python ; coding: utf-8 -*-
"""
CubeLab - Standalone Package
============================
Creates a fully self-contained executable with ALL dependencies bundled.
"""

import sys
import os
from pathlib import Path

# =====================================================
# CONFIGURATION
# =====================================================

APP_NAME = "CubeLab"
APP_VERSION = "1.0.0"
ENTRY_SCRIPT = "GUI.py"

IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"

# =====================================================
# COLLECT ALL HIDDEN IMPORTS
# =====================================================

hidden_imports = [
    # PyQt6 - ALL modules needed
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'PyQt6.Qsci',
    'PyQt6.sip',
    
    # PyVista / VTK - Complete
    'pyvista',
    'pyvistaqt',
    'pyvistaqt.plotting',
    'vtk',
    'vtkmodules',
    'vtkmodules.all',
    'vtkmodules.util',
    'vtkmodules.util.numpy_support',
    'vtkmodules.util.vtkAlgorithm',
    'vtkmodules.numpy_interface',
    'vtkmodules.numpy_interface.dataset_adapter',
    'vtkmodules.numpy_interface.algorithms',
    
    # NumPy internals
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.core._dtype_ctypes',
    'numpy.lib',
    'numpy.lib.format',
    'numpy.random',
    'numpy.fft',
    'numpy.linalg',
    
    # PIL/Pillow
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    
    # Google GenAI
    'google',
    'google.genai',
    'google.genai.types',
    'google.auth',
    'google.auth.transport',
    'google.protobuf',
    
    # Pydantic
    'pydantic',
    'pydantic.fields',
    'pydantic.main',
    'pydantic_core',
    'pydantic_core._pydantic_core',
    
    # System utilities
    'psutil',
    'dotenv',
    'json',
    'uuid',
    'tempfile',
    'traceback',
    'ast',
    're',
    'datetime',
    'platform',
    'subprocess',
    'shutil',
    'pathlib',
    
    # Telemetry
    'newrelic_telemetry_sdk',
    
    # pypore3d - ALL modules
    'pypore3d',
    'pypore3d.p3dFiltPy',
    'pypore3d.p3dFiltPy_16',
    'pypore3d.p3dBlobPy',
    'pypore3d.p3dSkelPy',
    'pypore3d.p3dFilt',
    'pypore3d.p3dBlob', 
    'pypore3d.p3dSkel',
    'pypore3d.p3d_common_lib',
    'pypore3d._p3dFilt',
    'pypore3d._p3dBlob',
    'pypore3d._p3dSkel',
    
    # Application modules
    'IDE',
    'VoxelRenderer', 
    'Client',
    'DiagnosticModule',
    'GUI',
]

# =====================================================
# DATA FILES - Bundle everything
# =====================================================

datas = [
    # .env with API keys
    (str(SRC_DIR / '.env'), '.'),
    
    # Config files
    (str(SRC_DIR / 'context.txt'), '.'),
    (str(SRC_DIR / 'pypore3d_function_reference.json'), '.'),
    (str(SRC_DIR / 'visual_context.json'), '.'),
    
    # Resources
    (str(SRC_DIR / 'resources'), 'resources'),
]

# =====================================================
# BINARIES
# =====================================================

binaries = []

# =====================================================
# EXCLUDES - Remove unnecessary bloat
# =====================================================

excludes = [
    'tkinter',
    '_tkinter',
    'matplotlib',
    'scipy',
    'pandas',
    'IPython',
    'jupyter',
    'notebook',
    'pytest',
    'sphinx',
    'docutils',
    'setuptools',
    'pip',
    'wheel',
    'pkg_resources',
    'test',
    'tests',
    'unittest',
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
# COLLECT ALL VTK MODULES
# =====================================================

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# VTK - Complete collection
try:
    vtk_datas, vtk_binaries, vtk_hiddenimports = collect_all('vtkmodules')
    a.datas.extend(vtk_datas)
    a.binaries.extend(vtk_binaries)
    a.hiddenimports.extend(vtk_hiddenimports)
except Exception as e:
    print(f"VTK collection warning: {e}")

# PyVista
try:
    pv_datas, pv_binaries, pv_hiddenimports = collect_all('pyvista')
    a.datas.extend(pv_datas)
    a.binaries.extend(pv_binaries)
    a.hiddenimports.extend(pv_hiddenimports)
except Exception as e:
    print(f"PyVista collection warning: {e}")

# pyvistaqt
try:
    pvqt_datas, pvqt_binaries, pvqt_hiddenimports = collect_all('pyvistaqt')
    a.datas.extend(pvqt_datas)
    a.binaries.extend(pvqt_binaries) 
    a.hiddenimports.extend(pvqt_hiddenimports)
except Exception as e:
    print(f"pyvistaqt collection warning: {e}")

# pypore3d - Complete collection including SWIG binaries
try:
    p3d_datas, p3d_binaries, p3d_hiddenimports = collect_all('pypore3d')
    a.datas.extend(p3d_datas)
    a.binaries.extend(p3d_binaries)
    a.hiddenimports.extend(p3d_hiddenimports)
    print(f"pypore3d collected: {len(p3d_binaries)} binaries")
except Exception as e:
    print(f"pypore3d collection warning: {e}")

# Google GenAI
try:
    genai_datas, genai_binaries, genai_hiddenimports = collect_all('google.genai')
    a.datas.extend(genai_datas)
    a.binaries.extend(genai_binaries)
    a.hiddenimports.extend(genai_hiddenimports)
except Exception:
    pass

# Pydantic
try:
    pyd_datas, pyd_binaries, pyd_hiddenimports = collect_all('pydantic')
    a.datas.extend(pyd_datas)
    a.binaries.extend(pyd_binaries)
    a.hiddenimports.extend(pyd_hiddenimports)
except Exception:
    pass

# =====================================================
# PYZ ARCHIVE
# =====================================================

pyz = PYZ(a.pure, a.zipped_data)

# =====================================================
# EXECUTABLE
# =====================================================

exe_options = {
    'name': APP_NAME,
    'debug': False,
    'bootloader_ignore_signals': False,
    'strip': False,
    'upx': True,
    'upx_exclude': [],
    'console': False,  # No console window
    'disable_windowed_traceback': False,
    'argv_emulation': False,
    'target_arch': None,
    'codesign_identity': None,
    'entitlements_file': None,
}

# Platform-specific icon
if IS_WINDOWS:
    icon_path = SRC_DIR / 'resources' / 'images' / 'Icon.ico'
    if icon_path.exists():
        exe_options['icon'] = str(icon_path)
elif IS_MACOS:
    icon_path = SRC_DIR / 'resources' / 'images' / 'Icon.icns'
    if icon_path.exists():
        exe_options['icon'] = str(icon_path)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    **exe_options,
)

# =====================================================
# COLLECT INTO FOLDER
# =====================================================

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

# =====================================================
# macOS APP BUNDLE
# =====================================================

if IS_MACOS:
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=str(SRC_DIR / 'resources' / 'images' / 'Icon.icns') if (SRC_DIR / 'resources' / 'images' / 'Icon.icns').exists() else None,
        bundle_identifier='com.cubelab.app',
        version=APP_VERSION,
        info_plist={
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': 'Cube Lab',
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleExecutable': APP_NAME,
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': 'CUBE',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
            'LSMinimumSystemVersion': '10.15',
            'NSOpenGLEnabled': True,
            'LSApplicationCategoryType': 'public.app-category.developer-tools',
        },
    )
