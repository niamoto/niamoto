#!/bin/bash
# Script to prepare Niamoto binaries for Tauri bundling
# This script copies the niamoto binary to the platform-specific location
# that Tauri expects for bundling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TAURI_BIN_DIR="$PROJECT_ROOT/src-tauri/bin"

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        TARGET="aarch64-apple-darwin"
    else
        TARGET="x86_64-apple-darwin"
    fi
    EXE_NAME="niamoto"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    ARCH=$(uname -m)
    if [[ "$ARCH" == "x86_64" ]]; then
        TARGET="x86_64-unknown-linux-gnu"
    elif [[ "$ARCH" == "aarch64" ]]; then
        TARGET="aarch64-unknown-linux-gnu"
    fi
    EXE_NAME="niamoto"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    TARGET="x86_64-pc-windows-msvc"
    EXE_NAME="niamoto.exe"
else
    echo "Unknown platform: $OSTYPE"
    exit 1
fi

echo "Platform: $TARGET"

# Create bin directory if it doesn't exist
mkdir -p "$TAURI_BIN_DIR"

# For development: create a placeholder
# For production: copy the real niamoto binary
PLACEHOLDER="$TAURI_BIN_DIR/niamoto-$TARGET"

if [[ -f "$PROJECT_ROOT/.venv/bin/niamoto" ]]; then
    echo "Copying niamoto from .venv..."
    cp "$PROJECT_ROOT/.venv/bin/niamoto" "$PLACEHOLDER"
    chmod +x "$PLACEHOLDER"
    echo "✓ Copied niamoto to $PLACEHOLDER"
elif [[ -f "/usr/local/bin/niamoto" ]]; then
    echo "Copying niamoto from /usr/local/bin..."
    cp "/usr/local/bin/niamoto" "$PLACEHOLDER"
    chmod +x "$PLACEHOLDER"
    echo "✓ Copied niamoto to $PLACEHOLDER"
else
    echo "Warning: niamoto binary not found. Creating placeholder..."
    echo "For development, this is OK. For production build, ensure niamoto is installed."
    cat > "$PLACEHOLDER" << 'EOF'
#!/bin/bash
# Placeholder niamoto binary for development
# In production, this should be replaced with the actual niamoto binary

echo "Warning: Using placeholder niamoto binary"
echo "For production, run: build_scripts/prepare_tauri_bins.sh"

# Try to find and execute the real niamoto
if [[ -f ".venv/bin/niamoto" ]]; then
    exec .venv/bin/niamoto "$@"
elif command -v niamoto &> /dev/null; then
    exec niamoto "$@"
else
    echo "Error: niamoto binary not found"
    exit 1
fi
EOF
    chmod +x "$PLACEHOLDER"
    echo "✓ Created placeholder at $PLACEHOLDER"
fi

echo ""
echo "Tauri binary preparation complete!"
echo "Location: $PLACEHOLDER"
