# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files, copy_metadata

BASE_DIR = Path(SPECPATH)
SRC_DIR = BASE_DIR / "src"


# 1. THE "GRAB EVERYTHING" FUNCTION

all_datas = []
all_binaries = []
all_hiddenimports = [
    h for h in all_hiddenimports 
    if not h.startswith('vtkmodules.web')
]

def safe_collect(package_name):
    """Run collect_all on a package to get absolutely everything."""
    try:
        datas, binaries, hiddenimports = collect_all(package_name)
        print(f"[OK] Full Collect: {package_name}")
        return datas, binaries, hiddenimports
    except Exception as e:
        print(f"[SKIP] {package_name}: {e}")
        return [], [], []

packages = [
    'vtkmodules',   
    'pyvista',        
    'pyvistaqt',      
    'pypore3d',       
    'pydantic',
    'setuptools'
]

for pkg in packages:
    d, b, h = safe_collect(pkg)
    all_datas += d
    all_binaries += b
    all_hiddenimports += h
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

# 5. HIDDEN IMPORTS (STRICT LIST)

strict_imports = [
    # Application
    'GUI', 'IDE', 'VoxelRenderer', 'Client', 'DiagnosticModule',
    
    # PyQt6
    'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
    'PyQt6.Qsci', 'PyQt6.sip',
    'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets',
    'PyQt6.QtSvg', 'PyQt6.QtNetwork', 'PyQt6.QtPrintSupport',
    
    # Core packages
    'numpy.core._methods', 'numpy.core._dtype_ctypes',
    'PIL', 'PIL.Image',
    'google.genai',
    'pydantic', 'pydantic_core',
    'psutil', 'cryptography', 'tempfile', 'json', 'pathlib',
    'newrelic_telemetry_sdk',
    
    # pypore3d
    'pypore3d', 'pypore3d.p3dFiltPy', 'pypore3d.p3dFiltPy_16',
    'pypore3d.p3dBlobPy', 'pypore3d.p3dSkelPy',


    'vtkmodules',
    'vtkmodules.all',
    'vtkmodules.util.numpy_support',
    'vtkmodules.qt.QVTKRenderWindowInteractor',

    'pkg_resources',


]

strict_imports = list(set(strict_imports + all_hiddenimports))


# 4. DATA FILES & METADATA

datas = [
    (str(SRC_DIR / 'context.txt'), '.'),
    (str(SRC_DIR / 'pypore3d_function_reference.json'), '.'),
    (str(SRC_DIR / 'visual_context.json'), '.'),
    (str(SRC_DIR / 'resources'), 'resources'),
    ('_key.bin', '.'),
    ('_secrets.bin', '.')
] + all_datas


my_binaries = all_binaries

# Define the build settings ONCE
build_args = dict(
    pathex=[str(SRC_DIR)],
    binaries=[# Use the system compatibility DLLs if SDK is missing
        ('C:\\Windows\\System32\\ucrtbase.dll', '.'),
    ]+ all_binaries,
    datas=datas,
    hiddenimports=strict_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[    
            # GUI Frameworks
            'tkinter', '_tkinter', 'tcl', 'tk',
            'PySide2', 'PySide6', 'wx', 'Gtk', 'GTK3',
            
            # Scientific / Bloat 
            'scipy', 'pandas', 'notebook', 'jupyter', 'IPython',
            'sklearn', 'tensorflow', 'torch',
            
            # Testing
            'pytest', 'unittest', 'nose', 'numpy.tests', 
            
            # Qt Extras
            'PyQt6.QtWebEngine', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
            'PyQt6.QtBluetooth', 'PyQt6.QtNfc', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
            'PyQt6.QtDesigner', 'PyQt6.QtHelp', 'PyQt6.QtTest', 'PyQt6.QtPositioning',
            'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
            'PyQt6.QtQuick', 'PyQt6.QtQuickWidgets', 'PyQt6.QtQml',
            'PyQt6.QtSql', 'PyQt6.QtDBus', 'PyQt6.uic',
                
            # Trame
            'trame', 'trame_vtk', 'trame_vuetify', 'trame_client', 'trame_server',
            'vtkmodules.web', 'vtkmodules.vtkWebCore', 'vtkmodules.vtkWebGLExporter',
            
            'curses', 'pydoc', 'doctest',

            'vtkmodules.web', 'vtkmodules.vtkWebCore', 'vtkmodules.vtkWebGLExporter',
            'vtkmodules.vtkIOSQL', 'vtkmodules.vtkIOAMR',
            'vtkmodules.vtkIOEnSight', 'vtkmodules.vtkIOExodus',
            'vtkmodules.vtkIONetCDF', 'vtkmodules.vtkIOVideo', 'vtkmodules.vtkIOFFMPEG',
            'vtkmodules.vtkRenderingMatplotlib','vtkmodules.vtkDomainsChemistry', 
            'vtkmodules.vtkDomainsChemistryOpenGL2', 'vtkmodules.vtkGeovisCore',
        ], 
    noarchive=False,
    optimize=0,
)

# --- Analysis 1: Main GUI ---
a1 = Analysis(['src/GUI.py'], **build_args)

# --- Analysis 2: User Testing ---
#a2 = Analysis(['src/User-Testing.py'], **build_args)

# --- Deduplicate Binaries (Crucial to prevent crashes) ---
def dedup(bin_list):
    seen = set(); unique = []
    for item in bin_list:
        if item[0] not in seen:
            seen.add(item[0]); unique.append(item)
    return unique

a1.binaries = dedup(a1.binaries)
#a2.binaries = dedup(a2.binaries)

# --- PYZ ---
pyz1 = PYZ(a1.pure, a1.zipped_data)
#pyz2 = PYZ(a2.pure, a2.zipped_data)

# --- EXEs ---
icon_path = SRC_DIR / 'resources' / 'images' / 'Icon.ico'
exe_icon = str(icon_path) if icon_path.exists() else None

exe1 = EXE(pyz1, a1.scripts, [], exclude_binaries=True, name='PP3DG', 
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, icon=exe_icon, disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None)

#exe2 = EXE(pyz2, a2.scripts, [], exclude_binaries=True, name='PP3DG-UserTesting', 
#          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, icon=exe_icon, disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None)

# --- COLLECT ---
coll = COLLECT(
    exe1, a1.binaries, a1.datas,
#    exe2, a2.binaries, a2.datas,
    strip=False, upx=False, upx_exclude=[],
    name='PP3DG',
)