# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files, copy_metadata

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

for pkg in ['pyvista', 'pyvistaqt', 'pypore3d', 'pydantic']:
    d, b, h = safe_collect(pkg)
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
        
        # CRITICAL: Only collect essential Qt plugins (not all)
        essential_plugins = ['platforms', 'styles']
        qt_plugins = os.path.join(qt_path, 'Qt6', 'plugins')
        
        if os.path.isdir(qt_plugins):
            for plugin in essential_plugins:
                plugin_dir = os.path.join(qt_plugins, plugin)
                if os.path.isdir(plugin_dir):
                    all_datas.append((plugin_dir, os.path.join('PyQt6', 'Qt6', 'plugins', plugin)))
        
        # OPTIMIZATION: Don't manually add Qt6 DLLs - let PyInstaller auto-detect
        # This is MUCH faster and prevents duplicate DLL searches
        
    except Exception as e:
        pass  

my_binaries = all_binaries

# Excludes: Aggressive cleanup to save space safely
safe_excludes = [
    # GUI Frameworks you DON'T use
    'tkinter', '_tkinter', 'tcl', 'tk',
    'PySide2', 'PySide6', 'wx', 'Gtk', 'GTK3',
    
    # Scientific packages you DON'T import
    'scipy', 'pandas', 'matplotlib',
    'notebook', 'jupyter', 'IPython',
    'sklearn', 'tensorflow', 'torch',
    
    # Test frameworks
    'pytest', 'unittest', 'nose',
    '*.tests', '*.test',
    
    # Qt modules you DON'T use (CRITICAL for size reduction)
    
    'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
    'PyQt6.QtHelp', 'PyQt6.QtTest', 'PyQt6.QtPositioning',
    'PyQt6.QtSql', 'PyQt6.QtDBus', 'PyQt6.uic',
    'PyQt6.QtWebEngine*',
    'PyQt6.QtBluetooth', 'PyQt6.QtNfc',
    'PyQt6.QtMultimedia*', 'PyQt6.QtQuick*',
    'PyQt6.QtQml', 'PyQt6.QtDesigner',
    
    # VTK extras
    'vtkmodules.vtkWeb*',
    'vtkmodules.vtkDomains*',
    'vtkmodules.vtkGeovisCore',
    'vtkmodules.vtkViewsInfovis', 'vtkmodules.vtkInfovisCore',
    'vtkmodules.vtkIOParallel', 'vtkmodules.vtkParallelCore',
    
    # Trame
    'trame*',

    
  
    
    # Standard library bloat
    'curses', 'pydoc', 'doctest',
    'xml.dom.domreg', 'xml.sax', 'html.parser',
]

# ============================================
# STEP 4: Define ALL hidden imports explicitly
# ============================================
hidden_imports = [
    # Your application modules
    'GUI', 'IDE', 'VoxelRenderer', 'Client', 'DiagnosticModule',
    
    # PyQt6 - ONLY modules you import
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
    
    # NumPy essentials
    'numpy.core._methods',
    'numpy.core._dtype_ctypes',
    
    # PIL
    'PIL.Image',
    
    # Google GenAI
    'google.genai',    
    # Pydantic
    'pydantic',
    'pydantic_core',
    
    # System
    'psutil',
    'dotenv',
    
    # Telemetry (if you actually use it)
    'newrelic_telemetry_sdk',
    
    # pypore3d
    'pypore3d',
    'pypore3d.p3dFiltPy',
    'pypore3d.p3dFiltPy_16',
    'pypore3d.p3dBlobPy',
    'pypore3d.p3dSkelPy',
    
    # --- 1. VTK ESSENTIALS (Replaces vtkmodules.all) ---
    # Core & Data
    'vtkmodules.vtkCommonCore',
    'vtkmodules.vtkCommonDataModel',
    'vtkmodules.vtkImagingCore',        # You specifically asked for this
    'vtkmodules.util.numpy_support',    # Critical for NumPy <-> VTK
    
    # Rendering Backend (REQUIRED for GUI to display anything)
    'vtkmodules.vtkRenderingOpenGL2',
    'vtkmodules.vtkInteractionStyle',
    'vtkmodules.vtkRenderingUI',
    'vtkmodules.qt.QVTKRenderWindowInteractor', # The widget for PyQt6
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
a1.binaries = unique_binaries1

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
    a2.binaries, a2.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CubeLab',
)