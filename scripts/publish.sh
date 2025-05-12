#!/bin/bash
# script publish.sh
# Publishes the package to PyPI using API token authentication

# Get version from pyproject.toml
VERSION=$(grep -o 'version = "[^"]*"' pyproject.toml | cut -d'"' -f2)
echo "Publishing Niamoto version $VERSION"

# Clean and build distribution files
rm -rf dist/
uv build

# Check for .env file and load it if exists
ENV_FILE="$(dirname "$0")/.env"
if [ -f "$ENV_FILE" ]; then
  echo "Loading PyPI token from .env file"
  source "$ENV_FILE"
fi

# Check if PYPI_TOKEN is set in environment or passed directly
if [ -z "$PYPI_TOKEN" ]; then
  echo "PYPI_TOKEN not found. You can set it using one of these methods:"
  echo "1. Create a .env file in the scripts directory: echo 'PYPI_TOKEN=your-token' > scripts/.env"
  echo "2. Pass it directly: PYPI_TOKEN=your-token bash scripts/publish.sh"
  echo "3. Continue with manual authentication below"

  # Standard interactive authentication
  echo "Continuing with interactive authentication..."
  echo "When prompted, enter '__token__' as username and your PyPI token as password"
  uv publish
else
  echo "Using PyPI token for authentication"
  # Use token authentication
  UV_PYPI_USER=__token__ UV_PYPI_PASSWORD=$PYPI_TOKEN uv publish
fi
