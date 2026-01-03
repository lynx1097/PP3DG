"""
PyInstaller hook for VTK/vtkmodules
====================================
Complete collection of VTK modules for 3D rendering.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Initialize
hiddenimports = []
datas = []
binaries = []

# Core VTK modules needed for 3D visualization
VTK_MODULES = [
    'vtkmodules',
    'vtkmodules.all',
    'vtkmodules.util',
    'vtkmodules.util.numpy_support',
    'vtkmodules.util.vtkAlgorithm',
    'vtkmodules.util.vtkConstants',
    'vtkmodules.util.misc',
    'vtkmodules.numpy_interface',
    'vtkmodules.numpy_interface.dataset_adapter',
    'vtkmodules.numpy_interface.algorithms',
    'vtkmodules.vtkCommonCore',
    'vtkmodules.vtkCommonDataModel',
    'vtkmodules.vtkCommonExecutionModel',
    'vtkmodules.vtkCommonMath',
    'vtkmodules.vtkCommonMisc',
    'vtkmodules.vtkCommonSystem',
    'vtkmodules.vtkCommonTransforms',
    'vtkmodules.vtkFiltersCore',
    'vtkmodules.vtkFiltersGeneral',
    'vtkmodules.vtkFiltersGeometry',
    'vtkmodules.vtkFiltersExtraction',
    'vtkmodules.vtkFiltersModeling',
    'vtkmodules.vtkFiltersSources',
    'vtkmodules.vtkFiltersHybrid',
    'vtkmodules.vtkImagingCore',
    'vtkmodules.vtkImagingGeneral',
    'vtkmodules.vtkImagingHybrid',
    'vtkmodules.vtkInteractionStyle',
    'vtkmodules.vtkInteractionWidgets',
    'vtkmodules.vtkIOCore',
    'vtkmodules.vtkIOImage',
    'vtkmodules.vtkIOLegacy',
    'vtkmodules.vtkIOXML',
    'vtkmodules.vtkRenderingAnnotation',
    'vtkmodules.vtkRenderingCore',
    'vtkmodules.vtkRenderingFreeType',
    'vtkmodules.vtkRenderingOpenGL2',
    'vtkmodules.vtkRenderingVolume',
    'vtkmodules.vtkRenderingVolumeOpenGL2',
    'vtkmodules.vtkRenderingUI',
    'vtkmodules.vtkRenderingContext2D',
    'vtkmodules.vtkRenderingContextOpenGL2',
]

hiddenimports.extend(VTK_MODULES)

# Dynamically collect all submodules
try:
    all_submodules = collect_submodules('vtkmodules')
    hiddenimports.extend(all_submodules)
except Exception as e:
    print(f"VTK submodule collection warning: {e}")

# Collect all data and binaries using collect_all (returns proper format)
try:
    vtk_datas, vtk_binaries, vtk_hiddenimports = collect_all('vtkmodules')
    datas = vtk_datas
    binaries = vtk_binaries
    hiddenimports.extend(vtk_hiddenimports)
except Exception as e:
    print(f"VTK collect_all warning: {e}")

# Remove duplicates
hiddenimports = list(set(hiddenimports))
