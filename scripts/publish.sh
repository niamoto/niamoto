#!/bin/bash
# script publish.sh
# Publishes the package to PyPI with GUI included in wheel
# This script builds wheel and sdist separately to handle GUI files properly

# Get version from pyproject.toml
VERSION=$(grep -o 'version = "[^"]*"' pyproject.toml | cut -d'"' -f2)
echo "Publishing Niamoto version $VERSION"

# Build GUI if not already built
GUI_DIST_DIR="src/niamoto/gui/ui/dist"
if [ ! -f "$GUI_DIST_DIR/index.html" ]; then
    echo "GUI not built. Building now..."
    if [ -f "scripts/build_gui.sh" ]; then
        bash scripts/build_gui.sh
    else
        echo "Error: GUI build script not found and GUI not built"
        exit 1
    fi
else
    echo "GUI already built, using existing files"
fi

# Clean previous builds
rm -rf dist/

# Temporarily enable GUI inclusion in pyproject.toml for wheel build
echo "Configuring build for GUI inclusion..."
sed -i.bak 's/# "src\/niamoto\/gui\/ui\/dist"/"src\/niamoto\/gui\/ui\/dist"/' pyproject.toml

# Build wheel directly (includes GUI files)
echo "Building wheel with GUI..."
uv build --wheel

# Restore pyproject.toml
mv pyproject.toml.bak pyproject.toml

# Now temporarily remove GUI files for sdist
echo "Building source distribution without GUI..."
BACKUP_DIR="/tmp/niamoto_gui_backup_$$"
if [ -d "$GUI_DIST_DIR" ]; then
    # Move GUI files to temp location
    mv "$GUI_DIST_DIR" "$BACKUP_DIR"
    # Create placeholder
    mkdir -p "$GUI_DIST_DIR"
    echo "# Placeholder for CI/CD" > "$GUI_DIST_DIR/.gitkeep"
fi

# Build sdist without GUI files
uv build --sdist

# Restore GUI files
if [ -d "$BACKUP_DIR" ]; then
    rm -rf "$GUI_DIST_DIR"
    mv "$BACKUP_DIR" "$GUI_DIST_DIR"
fi

echo ""
echo "Build complete! Files in dist/:"
ls -lh dist/

# Check for .env file and load it if exists
ENV_FILE="$(dirname "$0")/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading PyPI token from .env file"
    source "$ENV_FILE"
fi

# Check if PYPI_TOKEN is set in environment or passed directly
if [ -z "$PYPI_TOKEN" ]; then
    echo ""
    echo "PYPI_TOKEN not found. You can set it using one of these methods:"
    echo "1. Create a .env file in the scripts directory: echo 'PYPI_TOKEN=your-token' > scripts/.env"
    echo "2. Pass it directly: PYPI_TOKEN=your-token bash scripts/publish.sh"
    echo "3. Continue with manual authentication below"
    echo ""
    echo "Do you want to publish to PyPI now? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Continuing with interactive authentication..."
        echo "When prompted, enter '__token__' as username and your PyPI token as password"
        uv publish
    else
        echo "Skipping publication. You can publish later with: uv publish"
    fi
else
    echo "Using PyPI token for authentication"
    echo "Publishing to PyPI..."
    # Use token authentication
    UV_PUBLISH_USERNAME=__token__ UV_PUBLISH_PASSWORD=$PYPI_TOKEN uv publish
fi
