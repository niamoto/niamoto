#!/bin/bash
# Script to launch Niamoto Desktop in development mode
# Starts both Vite dev server and Tauri app

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Niamoto Desktop in dev mode...${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}⚠️  Stopping services...${NC}"
    kill $(jobs -p) 2>/dev/null || true
    exit
}

trap cleanup INT TERM

# Step 1: Prepare Tauri binaries
echo -e "${BLUE}📦 Step 1: Preparing Tauri binaries...${NC}"
./build_scripts/prepare_tauri_bins.sh

# Step 2: Start Vite dev server
echo ""
echo -e "${BLUE}⚛️  Step 2: Starting Vite dev server...${NC}"
cd src/niamoto/gui/ui
npm run dev &
VITE_PID=$!

# Wait for Vite to be ready
echo -e "${YELLOW}Waiting for Vite to start...${NC}"
sleep 5

# Check if Vite is running
if ! curl -s http://localhost:5173 > /dev/null; then
    echo -e "${RED}❌ Vite failed to start${NC}"
    kill $VITE_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✓ Vite is ready on http://localhost:5173${NC}"

# Step 3: Start Tauri
cd "$PROJECT_ROOT"
echo ""
echo -e "${BLUE}🦀 Step 3: Starting Tauri...${NC}"
echo -e "${YELLOW}This will open the Niamoto Desktop window${NC}"
echo ""

cargo tauri dev

# This line is reached when Tauri exits
cleanup
