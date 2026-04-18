#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
PYINSTALLER_VERSION="${PYINSTALLER_VERSION:-6.19.0}"
if command -v uv &> /dev/null; then
    PYINSTALLER_CMD=(uv run pyinstaller)
else
    PYINSTALLER_CMD=(python3 -m PyInstaller)
fi

echo -e "${BLUE}🚀 Building Niamoto Desktop Application...${NC}"
echo ""

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo -e "${GREEN}📱 Detected OS: macOS${NC}"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo -e "${GREEN}📱 Detected OS: Linux${NC}"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
    echo -e "${GREEN}📱 Detected OS: Windows${NC}"
else
    echo -e "${RED}❌ Unsupported OS: $OSTYPE${NC}"
    exit 1
fi

echo ""

# Step 1: Check prerequisites
echo -e "${BLUE}🔍 Step 1: Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

# Check PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo -e "${YELLOW}⚠ PyInstaller ${PYINSTALLER_VERSION} not found. Installing...${NC}"
    if command -v uv &> /dev/null; then
        uv pip install "pyinstaller==${PYINSTALLER_VERSION}"
    else
        python3 -m pip install "pyinstaller==${PYINSTALLER_VERSION}"
    fi
elif [ "$(pyinstaller --version)" != "${PYINSTALLER_VERSION}" ]; then
    echo -e "${YELLOW}⚠ PyInstaller $(pyinstaller --version) detected. Installing pinned ${PYINSTALLER_VERSION}...${NC}"
    if command -v uv &> /dev/null; then
        uv pip install "pyinstaller==${PYINSTALLER_VERSION}"
    else
        python3 -m pip install "pyinstaller==${PYINSTALLER_VERSION}"
    fi
fi
echo -e "${GREEN}✓ PyInstaller ${PYINSTALLER_VERSION} ready${NC}"

# Check Node/pnpm
if ! command -v pnpm &> /dev/null; then
    echo -e "${RED}❌ pnpm not found. Please install pnpm.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ pnpm found${NC}"

# Check Rust/Cargo
if ! command -v cargo &> /dev/null; then
    echo -e "${RED}❌ Cargo not found. Please install Rust from https://rustup.rs/${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Rust/Cargo found${NC}"

echo ""

# Step 2: Build React frontend
echo -e "${BLUE}⚛️  Step 2: Building React frontend...${NC}"

echo "Syncing in-app documentation..."
if command -v uv &> /dev/null; then
    uv run python scripts/build/sync_app_docs.py
else
    python3 scripts/build/sync_app_docs.py
fi

cd src/niamoto/gui/ui

# Install dependencies from lockfile
echo "Installing pnpm dependencies..."
pnpm install --frozen-lockfile

# Forward feedback worker env vars to Vite builds.
export VITE_FEEDBACK_WORKER_URL="${VITE_FEEDBACK_WORKER_URL:-${FEEDBACK_WORKER_URL:-}}"
export VITE_FEEDBACK_API_KEY="${VITE_FEEDBACK_API_KEY:-${FEEDBACK_API_KEY:-}}"
if [ -z "$VITE_FEEDBACK_WORKER_URL" ] || [ -z "$VITE_FEEDBACK_API_KEY" ]; then
    echo -e "${YELLOW}⚠ Feedback worker env vars missing; desktop feedback will be disabled in this build.${NC}"
fi

# Build
pnpm run build

if [ ! -d "dist" ]; then
    echo -e "${RED}❌ React build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ React build created${NC}"

cd ../../../..
echo ""

# Step 3: Build Python sidecar bundle with PyInstaller onedir mode
echo -e "${BLUE}🐍 Step 3: Building Python sidecar bundle...${NC}"
echo "This may take several minutes..."

NIAMOTO_PYINSTALLER_MODE=onedir NIAMOTO_PYINSTALLER_CONSOLE=false "${PYINSTALLER_CMD[@]}" build_scripts/niamoto.spec --clean --noconfirm

if [ ! -d "dist/niamoto" ]; then
    echo -e "${RED}❌ PyInstaller onedir build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python sidecar directory created${NC}"
echo ""

# Step 4: Copy sidecar directory into Tauri resources
echo -e "${BLUE}📦 Step 4: Copying Python sidecar into Tauri resources...${NC}"

if [ "$OS" == "windows" ]; then
    TARGET="x86_64-pc-windows-msvc"
elif [ "$OS" == "linux" ]; then
    TARGET="x86_64-unknown-linux-gnu"
else
    ARCH=$(uname -m)
    if [ "$ARCH" == "arm64" ]; then
        TARGET="aarch64-apple-darwin"
    else
        TARGET="x86_64-apple-darwin"
    fi
fi

RESOURCE_DIR="src-tauri/resources/sidecar/${TARGET}"
rm -rf "${RESOURCE_DIR}"
mkdir -p "${RESOURCE_DIR}"
cp -R dist/niamoto "${RESOURCE_DIR}/niamoto"
if [ "$OS" != "windows" ]; then
    chmod +x "${RESOURCE_DIR}/niamoto/niamoto"
fi
echo -e "${GREEN}✓ Copied sidecar to ${RESOURCE_DIR}/niamoto${NC}"
echo ""

# Step 5: Build Tauri app
echo -e "${BLUE}🦀 Step 5: Building Tauri application...${NC}"
echo "This may take several minutes on first build..."

cd src-tauri

# Install Tauri CLI if needed
if ! cargo tauri --version &> /dev/null; then
    echo "Installing Tauri CLI..."
    cargo install tauri-cli
fi

# Build
cargo tauri build

cd ..

echo ""

# Step 6: Show results
echo ""
echo -e "${GREEN}✅ Build Complete!${NC}"
echo ""
echo -e "${BLUE}📦 Installers located in:${NC}"
echo -e "   ${YELLOW}src-tauri/target/release/bundle/${NC}"
echo ""

if [ "$OS" == "macos" ]; then
    echo -e "${GREEN}→ macOS:${NC}"
    if [ -d "src-tauri/target/release/bundle/dmg" ]; then
        ls -lh src-tauri/target/release/bundle/dmg/*.dmg 2>/dev/null || true
    fi
    if [ -d "src-tauri/target/release/bundle/macos" ]; then
        ls -d src-tauri/target/release/bundle/macos/*.app 2>/dev/null || true
    fi
elif [ "$OS" == "linux" ]; then
    echo -e "${GREEN}→ Linux:${NC}"
    if [ -d "src-tauri/target/release/bundle/deb" ]; then
        ls -lh src-tauri/target/release/bundle/deb/*.deb 2>/dev/null || true
    fi
    if [ -d "src-tauri/target/release/bundle/appimage" ]; then
        ls -lh src-tauri/target/release/bundle/appimage/*.AppImage 2>/dev/null || true
    fi
elif [ "$OS" == "windows" ]; then
    echo -e "${GREEN}→ Windows:${NC}"
    if [ -d "src-tauri/target/release/bundle/msi" ]; then
        ls -lh src-tauri/target/release/bundle/msi/*.msi 2>/dev/null || true
    fi
    if [ -d "src-tauri/target/release/bundle/nsis" ]; then
        ls -lh src-tauri/target/release/bundle/nsis/*.exe 2>/dev/null || true
    fi
fi

echo ""
echo -e "${BLUE}🎉 You can now distribute the installer!${NC}"
echo ""

# Optional: Open bundle directory
if [ "$OS" == "macos" ]; then
    echo -e "${YELLOW}Opening bundle directory...${NC}"
    open src-tauri/target/release/bundle/
elif [ "$OS" == "linux" ]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open src-tauri/target/release/bundle/
    fi
fi
