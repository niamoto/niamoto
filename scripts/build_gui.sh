#!/bin/bash
# Build the GUI for distribution
# This script should be run before publishing to PyPI

set -e  # Exit on error

echo "Building Niamoto GUI for distribution..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GUI_DIR="$PROJECT_ROOT/src/niamoto/gui/ui"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed. Please install npm first."
    exit 1
fi

# Navigate to GUI directory
cd "$GUI_DIR"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing GUI dependencies..."
    npm install
fi

# Build the GUI
echo "Building GUI..."
npm run build

# Check if build was successful
if [ -d "dist" ]; then
    echo "✅ GUI built successfully!"
    echo "Build output: $GUI_DIR/dist"

    # Count files
    FILE_COUNT=$(find dist -type f | wc -l)
    echo "Generated $FILE_COUNT files"
else
    echo "❌ GUI build failed!"
    exit 1
fi

echo ""
echo "Next steps:"
echo "1. Commit the built files if needed"
echo "2. Run 'bash scripts/publish.sh' to publish to PyPI"
