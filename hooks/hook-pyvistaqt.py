"""
PyInstaller hook for pyvistaqt
===============================
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

hiddenimports = [
    'pyvistaqt',
    'pyvistaqt.plotting',
    'pyvistaqt.dialog',
    'pyvistaqt.counter',
    'pyvistaqt.window',
]

datas = []
binaries = []

try:
    hiddenimports.extend(collect_submodules('pyvistaqt'))
except Exception:
    pass

# Use collect_all which returns properly formatted tuples
try:
    pvqt_datas, pvqt_binaries, pvqt_hiddenimports = collect_all('pyvistaqt')
    datas = pvqt_datas
    binaries = pvqt_binaries
    hiddenimports.extend(pvqt_hiddenimports)
except Exception:
    pass

hiddenimports = list(set(hiddenimports))
