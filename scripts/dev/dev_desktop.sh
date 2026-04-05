#!/bin/bash
# Script to launch Niamoto Desktop in development mode
# Starts both Vite dev server and Tauri app
#
# Usage:
#   ./scripts/dev/dev_desktop.sh [--reset-user-config] [instance_path]
#
# Examples:
#   ./scripts/dev/dev_desktop.sh test-instance/niamoto-nc
#   ./scripts/dev/dev_desktop.sh --reset-user-config test-instance/niamoto-nc
#   ./scripts/dev/dev_desktop.sh /absolute/path/to/instance

set -e

VITE_PORT="${NIAMOTO_DESKTOP_VITE_PORT:-5173}"
API_PORT="${NIAMOTO_DESKTOP_API_PORT:-8080}"
VITE_HOST="${NIAMOTO_DESKTOP_VITE_HOST:-127.0.0.1}"
VITE_URL="http://${VITE_HOST}:${VITE_PORT}"
VITE_VERSION_MODULE_URL="${VITE_URL}/src/shared/desktop/updater/useAppUpdater.ts"
STARTED_VITE=0
VITE_PID=""
RESET_USER_CONFIG=0
INSTANCE_ARG=""
DESKTOP_CONFIG_PATH="$HOME/.niamoto/desktop-config.json"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Niamoto Desktop in dev mode...${NC}"
echo ""

print_usage() {
    echo "Usage: $0 [--reset-user-config] [instance_path]"
    echo ""
    echo "Options:"
    echo "  --reset-user-config  Remove ~/.niamoto/desktop-config.json before launch"
    echo "                       to simulate a fresh desktop install."
    echo "  -h, --help           Show this help message"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reset-user-config)
            RESET_USER_CONFIG=1
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        --*)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo ""
            print_usage
            exit 1
            ;;
        *)
            if [[ -n "$INSTANCE_ARG" ]]; then
                echo -e "${RED}❌ Multiple instance paths provided${NC}"
                echo ""
                print_usage
                exit 1
            fi
            INSTANCE_ARG="$1"
            shift
            ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

CURRENT_APP_VERSION="$(python3 - <<'PY'
import json
from pathlib import Path

print(json.loads(Path("src-tauri/tauri.conf.json").read_text())["version"])
PY
)"

# Optionally remove persisted desktop selection to simulate a fresh install
if [[ "$RESET_USER_CONFIG" -eq 1 ]]; then
    echo -e "${BLUE}🧹 Resetting desktop user config...${NC}"
    if [[ -f "$DESKTOP_CONFIG_PATH" ]]; then
        rm -f "$DESKTOP_CONFIG_PATH"
        echo -e "${GREEN}✓ Removed $DESKTOP_CONFIG_PATH${NC}"
    else
        echo -e "${YELLOW}ℹ️  No desktop config found at $DESKTOP_CONFIG_PATH${NC}"
    fi
    echo ""
fi

# Handle instance path argument
if [[ -n "$INSTANCE_ARG" ]]; then
    INSTANCE_PATH="$INSTANCE_ARG"
    # Convert to absolute path if relative
    if [[ ! "$INSTANCE_PATH" = /* ]]; then
        INSTANCE_PATH="$PROJECT_ROOT/$INSTANCE_PATH"
    fi

    if [[ ! -d "$INSTANCE_PATH" ]]; then
        echo -e "${RED}❌ Instance directory not found: $INSTANCE_PATH${NC}"
        exit 1
    fi

    export NIAMOTO_HOME="$INSTANCE_PATH"
    echo -e "${GREEN}✓ Instance: $NIAMOTO_HOME${NC}"
else
    echo -e "${YELLOW}⚠️  No instance specified. Use: $0 <instance_path>${NC}"
    echo -e "${YELLOW}   Example: $0 test-instance/niamoto-nc${NC}"
    echo ""
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}⚠️  Stopping services...${NC}"
    if [[ "$STARTED_VITE" -eq 1 && -n "$VITE_PID" ]]; then
        kill "$VITE_PID" 2>/dev/null || true
    fi
    exit
}

trap cleanup INT TERM

detect_running_vite_version() {
    curl -fsS "$VITE_VERSION_MODULE_URL" 2>/dev/null \
        | sed -n 's/.*const APP_VERSION = "\([^"]*\)".*/\1/p' \
        | head -n 1
}

stop_vite_on_port() {
    local pids
    pids="$(lsof -ti tcp:"$VITE_PORT" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
        echo -e "${YELLOW}Stopping existing server on port ${VITE_PORT}: ${pids}${NC}"
        kill $pids 2>/dev/null || true
        sleep 1
    fi
}

# Step 1: Start or reuse Vite dev server for frontend HMR
echo ""
echo -e "${BLUE}⚛️  Step 1: Checking Vite dev server...${NC}"
cd src/niamoto/gui/ui

REUSE_VITE=0
if curl -sf "$VITE_URL" > /dev/null; then
    RUNNING_VITE_VERSION="$(detect_running_vite_version)"
    if [[ -n "$RUNNING_VITE_VERSION" && "$RUNNING_VITE_VERSION" == "$CURRENT_APP_VERSION" ]]; then
        REUSE_VITE=1
        echo -e "${GREEN}✓ Reusing existing Vite on $VITE_URL (version $RUNNING_VITE_VERSION)${NC}"
    else
        if [[ -n "$RUNNING_VITE_VERSION" ]]; then
            echo -e "${YELLOW}⚠️  Running Vite serves version $RUNNING_VITE_VERSION but tauri.conf.json is $CURRENT_APP_VERSION${NC}"
        else
            echo -e "${YELLOW}⚠️  Running Vite detected on $VITE_URL but its injected app version could not be verified${NC}"
        fi
        stop_vite_on_port
    fi
fi

if [[ "$REUSE_VITE" -eq 0 ]]; then
    NIAMOTO_DESKTOP_API_PORT="$API_PORT" pnpm exec vite --host "$VITE_HOST" --strictPort --port "$VITE_PORT" &
    VITE_PID=$!
    STARTED_VITE=1

    echo -e "${YELLOW}Waiting for Vite to start on $VITE_URL (version $CURRENT_APP_VERSION)...${NC}"

    for _ in {1..30}; do
        if curl -sf "$VITE_URL" > /dev/null; then
            break
        fi
        sleep 1
    done

    if ! curl -sf "$VITE_URL" > /dev/null; then
        echo -e "${RED}❌ Vite failed to start on $VITE_URL${NC}"
        if [[ -n "$VITE_PID" ]]; then
            kill "$VITE_PID" 2>/dev/null || true
        fi
        exit 1
    fi

    echo -e "${GREEN}✓ Vite is ready on $VITE_URL (version $CURRENT_APP_VERSION)${NC}"
fi

echo -e "${YELLOW}ℹ️  Frontend changes hot-reload through Vite HMR.${NC}"
echo -e "${YELLOW}ℹ️  Backend API stays on http://127.0.0.1:${API_PORT} and is proxied by Vite.${NC}"

# Step 2: Start Tauri
cd "$PROJECT_ROOT"
echo ""
echo -e "${BLUE}🦀 Step 2: Starting Tauri...${NC}"
echo -e "${YELLOW}This will open the Niamoto Desktop window${NC}"
echo -e "${YELLOW}ℹ️  cargo tauri dev will rebuild Rust changes under src-tauri.${NC}"
echo ""

NIAMOTO_TAURI_DEV_UI=1 NIAMOTO_DESKTOP_API_PORT="$API_PORT" cargo tauri dev

# This line is reached when Tauri exits
cleanup
