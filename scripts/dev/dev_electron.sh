#!/bin/bash
# Script to launch the experimental Electron desktop shell in development mode.
# Starts or reuses the Vite dev server, then boots the Electron shell which
# launches the Python sidecar itself.
#
# Usage:
#   ./scripts/dev/dev_electron.sh [instance_path]
#
# Examples:
#   ./scripts/dev/dev_electron.sh test-instance/niamoto-nc
#   ./scripts/dev/dev_electron.sh /absolute/path/to/instance

set -e

VITE_PORT="${NIAMOTO_DESKTOP_VITE_PORT:-5173}"
API_PORT="${NIAMOTO_DESKTOP_API_PORT:-8080}"
VITE_HOST="${NIAMOTO_DESKTOP_VITE_HOST:-127.0.0.1}"
VITE_URL="http://${VITE_HOST}:${VITE_PORT}"
VITE_VERSION_MODULE_URL="${VITE_URL}/src/shared/desktop/updater/useAppUpdater.ts"
STARTED_VITE=0
VITE_PID=""
INSTANCE_ARG=""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_usage() {
    echo "Usage: $0 [instance_path]"
    echo ""
    echo "Examples:"
    echo "  $0 test-instance/niamoto-nc"
    echo "  $0 /absolute/path/to/instance"
}

echo -e "${BLUE}⚛️  Starting Niamoto Electron shell in dev mode...${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
ELECTRON_DIR="$PROJECT_ROOT/electron"

while [[ $# -gt 0 ]]; do
    case "$1" in
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

cd "$PROJECT_ROOT"

if [[ ! -d "$ELECTRON_DIR/node_modules" ]]; then
    echo -e "${RED}❌ Electron dependencies are missing in $ELECTRON_DIR/node_modules${NC}"
    echo -e "${YELLOW}Run: pnpm install --dir electron${NC}"
    exit 1
fi

CURRENT_APP_VERSION="$(python3 - <<'PY'
import json
from pathlib import Path

print(json.loads(Path("src-tauri/tauri.conf.json").read_text())["version"])
PY
)"

if [[ -n "$INSTANCE_ARG" ]]; then
    INSTANCE_PATH="$INSTANCE_ARG"
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
    echo -e "${YELLOW}⚠️  No instance specified. The Electron shell will use the shared desktop config or open in welcome mode.${NC}"
fi

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

stop_api_on_port() {
    local pids
    pids="$(lsof -ti tcp:"$API_PORT" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
        echo -e "${YELLOW}Stopping existing backend on port ${API_PORT}: ${pids}${NC}"
        kill $pids 2>/dev/null || true
        sleep 1
    fi
}

echo -e "${BLUE}⚛️  Step 1: Checking Vite dev server...${NC}"
cd src/niamoto/gui/ui

REUSE_VITE=0
if curl -sf "$VITE_URL" > /dev/null; then
    RUNNING_VITE_VERSION="$(detect_running_vite_version)"
    if [[ -n "$RUNNING_VITE_VERSION" && "$RUNNING_VITE_VERSION" == "$CURRENT_APP_VERSION" ]]; then
        REUSE_VITE=1
        echo -e "${GREEN}✓ Reusing existing Vite on $VITE_URL (version $RUNNING_VITE_VERSION)${NC}"
    else
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
fi

stop_api_on_port

echo ""
echo -e "${BLUE}🖥️  Step 2: Launching Electron shell...${NC}"
cd "$PROJECT_ROOT"

export NIAMOTO_DESKTOP_API_PORT="$API_PORT"
export NIAMOTO_ELECTRON_RENDERER_URL="$VITE_URL"

pnpm --dir electron exec electron .
