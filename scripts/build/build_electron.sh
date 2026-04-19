#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
PYINSTALLER_VERSION="${PYINSTALLER_VERSION:-6.19.0}"

if command -v uv &> /dev/null; then
    PYINSTALLER_CMD=(uv run pyinstaller)
else
    PYINSTALLER_CMD=(python3 -m PyInstaller)
fi

echo -e "${BLUE}⚡ Building the experimental Niamoto Electron shell...${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

CURRENT_APP_VERSION="$(python3 - <<'PY'
import json
from pathlib import Path

print(json.loads(Path("src-tauri/tauri.conf.json").read_text())["version"])
PY
)"

detect_target_triple() {
    case "$(uname -s)" in
        Darwin)
            if [[ "$(uname -m)" == "arm64" ]]; then
                echo "aarch64-apple-darwin"
            else
                echo "x86_64-apple-darwin"
            fi
            ;;
        Linux)
            if [[ "$(uname -m)" == "aarch64" ]]; then
                echo "aarch64-unknown-linux-gnu"
            else
                echo "x86_64-unknown-linux-gnu"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            if [[ "$(uname -m)" == "aarch64" ]]; then
                echo "aarch64-pc-windows-msvc"
            else
                echo "x86_64-pc-windows-msvc"
            fi
            ;;
        *)
            echo -e "${RED}❌ Unsupported host platform: $(uname -s)${NC}" >&2
            exit 1
            ;;
    esac
}

echo -e "${BLUE}🔍 Step 1: Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found.${NC}"
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    echo -e "${RED}❌ pnpm not found.${NC}"
    exit 1
fi

if [[ ! -d "electron/node_modules" ]]; then
    echo -e "${RED}❌ Electron dependencies are missing in electron/node_modules${NC}"
    echo -e "${YELLOW}Run: pnpm install --dir electron${NC}"
    exit 1
fi

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

echo -e "${GREEN}✓ Prerequisites ready${NC}"
echo ""

echo -e "${BLUE}⚛️  Step 2: Building the React frontend...${NC}"

if command -v uv &> /dev/null; then
    uv run python scripts/build/sync_app_docs.py
else
    python3 scripts/build/sync_app_docs.py
fi

cd src/niamoto/gui/ui
pnpm install --frozen-lockfile

export VITE_FEEDBACK_WORKER_URL="${VITE_FEEDBACK_WORKER_URL:-${FEEDBACK_WORKER_URL:-}}"
export VITE_FEEDBACK_API_KEY="${VITE_FEEDBACK_API_KEY:-${FEEDBACK_API_KEY:-}}"
if [ -z "$VITE_FEEDBACK_WORKER_URL" ] || [ -z "$VITE_FEEDBACK_API_KEY" ]; then
    echo -e "${YELLOW}⚠ Feedback worker env vars missing; desktop feedback will be disabled in this build.${NC}"
fi

pnpm run build
cd ../../../..

echo -e "${GREEN}✓ Frontend build complete${NC}"
echo ""

echo -e "${BLUE}🐍 Step 3: Building the Python sidecar...${NC}"
NIAMOTO_PYINSTALLER_MODE=onedir NIAMOTO_PYINSTALLER_CONSOLE=false "${PYINSTALLER_CMD[@]}" build_scripts/niamoto.spec --clean --noconfirm

if [ ! -d "dist/niamoto" ]; then
    echo -e "${RED}❌ PyInstaller onedir build failed${NC}"
    exit 1
fi

TARGET="$(detect_target_triple)"
RESOURCE_DIR="src-tauri/resources/sidecar/${TARGET}"
rm -rf "${RESOURCE_DIR}"
mkdir -p "${RESOURCE_DIR}"
cp -R dist/niamoto "${RESOURCE_DIR}/niamoto"

if [[ "$(uname -s)" != MINGW* && "$(uname -s)" != MSYS* && "$(uname -s)" != CYGWIN* ]]; then
    chmod +x "${RESOURCE_DIR}/niamoto/niamoto" 2>/dev/null || true
fi

echo -e "${GREEN}✓ Sidecar staged to ${RESOURCE_DIR}/niamoto${NC}"
echo ""

echo -e "${BLUE}🖥️  Step 4: Packaging the Electron shell...${NC}"
python3 - <<'PY'
import json
from pathlib import Path

root = Path.cwd()
electron_package = root / "electron" / "package.json"
tauri_conf = root / "src-tauri" / "tauri.conf.json"

package_data = json.loads(electron_package.read_text())
tauri_data = json.loads(tauri_conf.read_text())
package_data["version"] = tauri_data["version"]
electron_package.write_text(json.dumps(package_data, indent=2) + "\n")
PY
pnpm --dir electron run pack

echo ""
echo -e "${GREEN}✅ Electron shell build complete${NC}"
echo -e "${BLUE}Artifacts:${NC} electron/dist"
