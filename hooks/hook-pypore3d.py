"""
PyInstaller hook for pypore3d
=============================
Ensures all pypore3d modules AND SWIG-compiled binaries are bundled.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all submodules
hiddenimports = [
    'pypore3d',
    'pypore3d.p3dFiltPy',
    'pypore3d.p3dFiltPy_16',
    'pypore3d.p3dBlobPy',
    'pypore3d.p3dSkelPy',
    'pypore3d.p3dFilt',
    'pypore3d.p3dBlob',
    'pypore3d.p3dSkel',
    'pypore3d.p3d_common_lib',
    'pypore3d.p3dSITKPy',
    'pypore3d.p3dSITKPy_16',
]

# Initialize empty lists
datas = []
binaries = []

# Try to collect submodules dynamically
try:
    hiddenimports.extend(collect_submodules('pypore3d'))
except Exception:
    pass

# Use collect_all which returns properly formatted tuples
try:
    all_datas, all_binaries, all_hiddenimports = collect_all('pypore3d')
    datas = all_datas
    binaries = all_binaries
    hiddenimports.extend(all_hiddenimports)
except Exception as e:
    print(f"pypore3d collect_all warning: {e}")

# Remove duplicates from hiddenimports
hiddenimports = list(set(hiddenimports))
