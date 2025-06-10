# Installing Niamoto

This guide walks you through installing Niamoto on your system.

## Prerequisites

### Operating System
- Linux (Ubuntu 20.04+, Debian 10+)
- macOS (10.15+)
- Windows 10+ (WSL2 recommended)

### Required Software
- Python 3.9 or higher
- pip or uv (Python package manager)
- Git (for cloning examples)
- SQLite 3.35+ (usually included with Python)

### Optional but Recommended
- GDAL/OGR (for advanced geospatial features)
- QGIS (for visualizing spatial data)

## Installation via pip

### 1. Simple Installation

```bash
pip install niamoto
```

### 2. Installation with All Dependencies

```bash
pip install niamoto[all]
```

### 3. Development Installation

```bash
git clone https://github.com/niamoto/niamoto.git
cd niamoto
pip install -e ".[dev]"
```

## Installation via uv (recommended)

[uv](https://github.com/astral-sh/uv) is a modern and fast Python package manager.

### 1. Install uv

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install Niamoto with uv

```bash
uv pip install niamoto
```

### 3. Development Installation with uv

```bash
git clone https://github.com/niamoto/niamoto.git
cd niamoto
uv pip install -e ".[dev]"
```

## Verify Installation

### 1. Check Version

```bash
niamoto --version
```

You should see something like:
```
niamoto, version 0.5.3
```

### 2. Display Help

```bash
niamoto --help
```

This will show all available commands:
```
Usage: niamoto [OPTIONS] COMMAND [ARGS]...

  Niamoto CLI - Ecological data platform

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  init       Initialize a new Niamoto project
  import     Import data from CSV/GIS files
  transform  Run data transformations
  export     Export to static site
  run        Run entire pipeline
  stats      Display database statistics
  deploy     Deploy to web server
  plugins    Manage plugins
```

### 3. Quick Test

Create a test project:

```bash
# Create a folder for testing
mkdir test-niamoto
cd test-niamoto

# Initialize a project
niamoto init

# Check the created structure
ls -la
```

You should see:
```
.
├── config/
│   ├── config.yml
│   ├── import.yml
│   ├── transform.yml
│   └── export.yml
├── imports/
├── exports/
├── plugins/
├── templates/
└── logs/
```

## Installing Geospatial Dependencies

### On Ubuntu/Debian

```bash
# Install GDAL and dependencies
sudo apt-get update
sudo apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    libspatialite-dev

# Verify installation
gdalinfo --version
```

### On macOS

```bash
# With Homebrew
brew install gdal
brew install spatialite-tools

# Verify installation
gdalinfo --version
```

### On Windows

1. Download and install [OSGeo4W](https://trac.osgeo.org/osgeo4w/)
2. Select GDAL and SQLite/Spatialite packages
3. Add installation path to system PATH

## Environment Configuration

### Optional Environment Variables

```bash
# Set default path for Niamoto projects
export NIAMOTO_HOME=$HOME/.niamoto

# Enable detailed logging
export NIAMOTO_LOG_LEVEL=DEBUG

# Set locale (important for special characters)
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
```

### Git Configuration (for contributors)

```bash
# Clone repository with examples
git clone https://github.com/niamoto/niamoto.git
cd niamoto

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

## Common Installation Issues

### Error: "command not found: niamoto"

The binary is not in your PATH. Solutions:

```bash
# Check where pip installs scripts
python -m site --user-base

# Add to PATH (Linux/macOS)
export PATH="$HOME/.local/bin:$PATH"

# Or use python -m
python -m niamoto --version
```

### Error: "No module named 'gdal'"

Python bindings for GDAL are not installed:

```bash
# Install with pip
pip install GDAL==$(gdal-config --version)

# Or with conda
conda install -c conda-forge gdal
```

### Permission Error

If you get permission errors during installation:

```bash
# Install in user space
pip install --user niamoto

# Or use a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
pip install niamoto
```

## Next Steps

Once Niamoto is successfully installed:

1. Follow the [Quick Start Guide](quickstart.md) to create your first project
2. Explore [Core Concepts](concepts.md) to understand the architecture
3. Download [example data](https://github.com/niamoto/niamoto-example-data) for testing

## Support

If you encounter issues:

1. Check the [FAQ](../faq/general.md)
2. Look at [GitHub issues](https://github.com/niamoto/niamoto/issues)
3. Join the community on [Discussions](https://github.com/niamoto/niamoto/discussions)
