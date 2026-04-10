# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Niamoto Desktop
Bundles the entire Python application with all dependencies
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

# Base directories
# PyInstaller runs from project root, so paths are relative to that
# Note: __file__ is not available in spec files, use SPECPATH instead
import os
ROOT_DIR = Path(SPECPATH).parent  # SPECPATH is the directory containing this .spec file
SRC_DIR = ROOT_DIR / 'src'
NIAMOTO_SRC = SRC_DIR / 'niamoto'
BUILD_MODE = os.environ.get('NIAMOTO_PYINSTALLER_MODE', 'onefile').strip().lower()
CONSOLE_ENABLED = os.environ.get('NIAMOTO_PYINSTALLER_CONSOLE', 'true').strip().lower() not in {
    '0',
    'false',
    'no',
}

# Collect all Niamoto data files (YAML, templates, static files)
datas = []

# Patterns to include (exclude node_modules, build artifacts)
patterns = [
    '**/*.yml', '**/*.yaml', '**/*.json',
    '**/*.html', '**/*.css', '**/*.sql',
    '**/*.py',  # Include all Python files (plugins)
    '**/*.pkl',  # Include ML models
]

# Directories to exclude from globbing
exclude_dirs = {'node_modules', 'dist', '__pycache__', '.git', 'build', 'venv', '.venv'}

for pattern in patterns:
    for file in NIAMOTO_SRC.glob(pattern):
        # Skip if file is in an excluded directory
        if any(excluded in file.parts for excluded in exclude_dirs):
            continue
        relative_path = file.parent.relative_to(SRC_DIR)
        datas.append((str(file), str(relative_path)))

# CRITICAL: Also include models directory if it exists
models_dir = ROOT_DIR / 'models'
if models_dir.exists():
    print(f"[OK] Including ML models from {models_dir}")
    for file in models_dir.rglob('*'):
        if file.is_file():
            datas.append((str(file), 'models'))
else:
    print(f"[WARN] No models directory found at {models_dir}")

# Include wheel metadata required at runtime by some geo/scientific packages.
# PyInstaller does not always collect these dist-info directories automatically.
for package_name in [
    'shapely',
]:
    datas += copy_metadata(package_name)

# Include pyproj coordinate reference data (proj.db)
datas += collect_data_files('pyproj')
# Include pyogrio bundled GDAL/PROJ data required by geospatial imports.
datas += collect_data_files('pyogrio')

# CRITICAL: Include React build (src/niamoto/gui/ui/dist)
ui_dist = NIAMOTO_SRC / 'gui' / 'ui' / 'dist'
if ui_dist.exists():
    print(f"[OK] Including React build from {ui_dist}")
    for file in ui_dist.rglob('*'):
        if file.is_file():
            # Map to niamoto/gui/ui/dist/... for bundle.py to find
            relative_dest = file.relative_to(NIAMOTO_SRC / 'gui')
            dest_path = Path('niamoto/gui') / relative_dest
            datas.append((str(file), str(dest_path.parent)))
    print(f"  Added {len([d for d in datas if 'gui/ui/dist' in str(d[0])])} files from React build")
else:
    print(f"[WARN] React build not found at {ui_dist}")
    print("  Run 'cd src/niamoto/gui/ui && pnpm run build' before building with PyInstaller")

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    # Core Niamoto
    'niamoto',
    'niamoto.cli',
    'niamoto.core',
    'niamoto.gui',
    'niamoto.common',

    # Data processing
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs',
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
    'numpy.random',
    'numpy.random._common',
    'numpy.random._generator',

    # Geospatial (if used)
    'geopandas',
    'shapely',
    'shapely.geometry',
    'pyproj',

    # Database
    'duckdb',
    'duckdb_engine',
    'sqlalchemy',
    'sqlalchemy.ext',
    'sqlalchemy.ext.declarative',

    # API
    'fastapi',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'starlette',
    'starlette.routing',

    # Validation & Config
    'pydantic',
    'pydantic.fields',
    'pydantic_core',
    'yaml',

    # Templates
    'jinja2',
    'jinja2.ext',

    # HTTP
    'httpx',

    # CLI
    'click',

    # Machine Learning
    'sklearn',
    'sklearn.ensemble',
    'sklearn.preprocessing',
    'sklearn.linear_model',
    'sklearn.calibration',
    'sklearn.feature_extraction.text',
    'scipy',
    'scipy.sparse',
    'scipy.special',
    'scipy.stats',
    'joblib',

    # Required by scipy/numpy internals
    'unittest',
    'unittest.mock',
]

# Binaries - additional binary dependencies
binaries = collect_dynamic_libs('pyogrio')

# Collect pyogrio extension modules explicitly. Without them, frozen Linux builds
# can fail at runtime with missing native module errors such as pyogrio_geometry.
hiddenimports += collect_submodules(
    'pyogrio',
    filter=lambda name: not name.startswith('pyogrio.tests'),
)

# Analysis
a = Analysis(
    [str(NIAMOTO_SRC / '__main__.py')],
    pathex=[str(ROOT_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(ROOT_DIR / 'build_scripts' / 'pyinstaller_hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused packages
        'matplotlib',
        'fiona',
        # Typing-only tooling pulled by sqlalchemy[mypy] in dev.
        'mypy',
        'mypyc',
        'mypy_extensions',
        # Testing frameworks
        'pytest',
        'pytest_mock',
        'hypothesis',
        '_pytest',
        # Documentation
        'sphinx',
        'docutils',
        # Interactive Python
        'IPython',
        'ipykernel',
        'jupyter',
        'jupyter_client',
        'jupyter_core',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

common_exe_kwargs = dict(
    name='niamoto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Don't strip - causes issues with numpy/pandas on Linux and DLL issues on Windows
    upx=False,  # Disabled: UPX triggers antivirus false positives on Windows
    upx_exclude=[
        # Exclude Python DLL and critical libraries from UPX to avoid corruption
        'python*.dll',
        'vcruntime*.dll',
        'msvcp*.dll',
        'api-ms-win-*.dll',
    ],
    runtime_tmpdir=None if sys.platform != 'win32' else os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'niamoto'),
    console=CONSOLE_ENABLED,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if BUILD_MODE == 'onedir':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='niamoto',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=CONSOLE_ENABLED,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=common_exe_kwargs['upx_exclude'],
        name='niamoto',
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        **common_exe_kwargs,
    )
