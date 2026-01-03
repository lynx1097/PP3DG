"""
PyInstaller hook for pypore3d
=============================
Ensures all pypore3d modules AND SWIG-compiled binaries are bundled.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files, get_package_paths
import os
import glob

# Get package path
try:
    pkg_base, pkg_dir = get_package_paths('pypore3d')
except Exception:
    pkg_base = pkg_dir = None

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

# Try to collect submodules dynamically
try:
    hiddenimports.extend(collect_submodules('pypore3d'))
except Exception:
    pass

# Collect data files
datas = []
try:
    datas = collect_data_files('pypore3d')
except Exception:
    pass

# Collect ALL binaries (SWIG .pyd/.so files)
binaries = []

if pkg_dir:
    # Find all compiled extensions
    for ext in ['*.pyd', '*.so', '*.dll', '_*.pyd', '_*.so']:
        pattern = os.path.join(pkg_dir, '**', ext)
        for filepath in glob.glob(pattern, recursive=True):
            rel_path = os.path.relpath(os.path.dirname(filepath), pkg_dir)
            if rel_path == '.':
                dest = 'pypore3d'
            else:
                dest = os.path.join('pypore3d', rel_path)
            binaries.append((filepath, dest))

# Also try collect_all as fallback
try:
    all_datas, all_binaries, all_hiddenimports = collect_all('pypore3d')
    datas.extend(all_datas)
    binaries.extend(all_binaries)
    hiddenimports.extend(all_hiddenimports)
except Exception as e:
    print(f"pypore3d collect_all warning: {e}")

# Remove duplicates
hiddenimports = list(set(hiddenimports))
