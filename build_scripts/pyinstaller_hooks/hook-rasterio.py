"""Ensure rasterio is fully bundled in PyInstaller sidecar builds."""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

# rasterio imports pure-Python helpers such as rasterio.sample from its package
# __init__ at runtime. Without explicit submodule collection, frozen desktop
# builds can launch successfully and then crash during FastAPI app import.
hiddenimports = collect_submodules(
    "rasterio",
    filter=lambda name: not name.startswith("rasterio.tests"),
)

# Keep GDAL/PROJ auxiliary data shipped by rasterio wheels, and skip test data
# to avoid bloating the desktop sidecar.
datas = collect_data_files(
    "rasterio",
    excludes=[
        "**/tests",
        "**/tests/**/*",
        "**/__pycache__",
        "**/*.pyc",
    ],
) + copy_metadata("rasterio")

# Bundle rasterio native libraries explicitly for frozen desktop builds.
binaries = collect_dynamic_libs("rasterio")
