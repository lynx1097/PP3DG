# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

# =========================================================
# 1. CONFIGURATION & DEBLOATING
# =========================================================
block_cipher = None

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
    'curses', 'email', 'html', 'http', 'unittest', 'pydoc', 'xml.dom.domreg',
]

# =========================================================
# 2. ANALYSIS (Process both scripts)
# =========================================================

# --- Analysis 1: Main GUI ---
a1 = Analysis(
    ['src/GUI.py'],  # Main Entry Point
    pathex=[],
    binaries=my_binaries,
    datas=[('src/resources', 'resources')], # Shared resources
    hiddenimports=['vtkmodules.all', 'pyvistaqt'],
    hookspath=[],
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
    pathex=[],
    binaries=my_binaries,
    datas=[('src/resources', 'resources')],
    hiddenimports=['vtkmodules.all', 'pyvistaqt'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=safe_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# =========================================================
# 3. MERGE & BUILD (Deduplication happens here)
# =========================================================

# Create PYZ archives (Python bytecode)
pyz1 = PYZ(a1.pure, a1.zipped_data, cipher=block_cipher)
pyz2 = PYZ(a2.pure, a2.zipped_data, cipher=block_cipher)

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
)

# COLLECT: Bundles both EXEs into ONE folder with shared libraries
coll = COLLECT(
    exe1,
    a1.binaries, a1.zipfiles, a1.datas,
    
    exe2,
    # Note: We don't need a2.binaries/datas here if they are identical, 
    # but passing them ensures unique deps from the second script are included.
    # COLLECT automatically removes duplicates.
    a2.binaries, a2.zipfiles, a2.datas,
    
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CubeLab_Suite', # Name of the output folder
)