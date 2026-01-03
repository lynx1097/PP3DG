"""
PyInstaller hook for pyvista
=============================
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

hiddenimports = [
    'pyvista',
    'pyvista.core',
    'pyvista.plotting',
    'pyvista.utilities',
]

datas = []
binaries = []

try:
    hiddenimports.extend(collect_submodules('pyvista'))
except Exception:
    pass

try:
    pv_datas, pv_binaries, pv_hiddenimports = collect_all('pyvista')
    datas.extend(pv_datas)
    binaries.extend(pv_binaries)
    hiddenimports.extend(pv_hiddenimports)
except Exception:
    pass

hiddenimports = list(set(hiddenimports))
