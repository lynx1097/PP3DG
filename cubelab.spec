# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ['CubeLab.py'],
    pathex=[],
    binaries=[],
    datas=collect_data_files('pyvista'),
    hiddenimports=[],
    excludes=[
        'vtk.qt',        # 🚫 avoid Qt plugin collision
        'PySide6',
        'PyQt5',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CubeLab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='CubeLab',
)
