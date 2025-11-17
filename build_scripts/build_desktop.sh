#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    echo -e "${YELLOW}⚠ PyInstaller not found. Installing...${NC}"
    if command -v uv &> /dev/null; then
        uv pip install pyinstaller
    else
        python3 -m pip install pyinstaller
    fi
fi
echo -e "${GREEN}✓ PyInstaller found${NC}"

# Check Node/npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found. Please install Node.js.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npm found${NC}"

# Check Rust/Cargo
if ! command -v cargo &> /dev/null; then
    echo -e "${RED}❌ Cargo not found. Please install Rust from https://rustup.rs/${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Rust/Cargo found${NC}"

echo ""

# Step 2: Build Python bundle with PyInstaller
echo -e "${BLUE}🐍 Step 2: Building Python bundle with PyInstaller...${NC}"
echo "This may take several minutes..."

pyinstaller build_scripts/niamoto.spec --clean --noconfirm

if [ ! -f "dist/niamoto" ] && [ ! -f "dist/niamoto.exe" ]; then
    echo -e "${RED}❌ PyInstaller build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python bundle created${NC}"
echo ""

# Step 3: Copy Python bundle to Tauri bin directory
echo -e "${BLUE}📦 Step 3: Copying Python bundle to Tauri...${NC}"

mkdir -p src-tauri/bin

# Determine target triple for Tauri externalBin
if [ "$OS" == "windows" ]; then
    TARGET="x86_64-pc-windows-msvc"
    cp dist/niamoto.exe src-tauri/bin/niamoto-${TARGET}.exe
    echo -e "${GREEN}✓ Copied niamoto-${TARGET}.exe${NC}"
elif [ "$OS" == "linux" ]; then
    TARGET="x86_64-unknown-linux-gnu"
    cp dist/niamoto src-tauri/bin/niamoto-${TARGET}
    chmod +x src-tauri/bin/niamoto-${TARGET}
    echo -e "${GREEN}✓ Copied niamoto-${TARGET}${NC}"
else
    # macOS - detect architecture
    ARCH=$(uname -m)
    if [ "$ARCH" == "arm64" ]; then
        TARGET="aarch64-apple-darwin"
    else
        TARGET="x86_64-apple-darwin"
    fi
    cp dist/niamoto src-tauri/bin/niamoto-${TARGET}
    chmod +x src-tauri/bin/niamoto-${TARGET}
    echo -e "${GREEN}✓ Copied niamoto-${TARGET}${NC}"
fi

echo ""

# Step 4: Build React frontend
echo -e "${BLUE}⚛️  Step 4: Building React frontend...${NC}"

cd src/niamoto/gui/ui

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Build
npm run build

if [ ! -d "dist" ]; then
    echo -e "${RED}❌ React build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ React build created${NC}"

cd ../../../..
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
