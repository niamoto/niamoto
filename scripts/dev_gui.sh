#!/bin/bash
#
# Development script to run Niamoto GUI with hot reload
#
# This script starts both the FastAPI backend and Vite frontend development servers
# in parallel, allowing for hot reload on both React components and Python code.
#
# Usage:
#   ./scripts/dev_gui.sh [instance-path]
#
# Examples:
#   ./scripts/dev_gui.sh test-instance/niamoto-nc
#   ./scripts/dev_gui.sh /absolute/path/to/instance
#   ./scripts/dev_gui.sh  # Uses current directory or NIAMOTO_HOME
#
# Requirements:
#   - Python with niamoto installed
#   - Node.js and npm
#   - Frontend dependencies installed (cd src/niamoto/gui/ui && npm install)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

# Cleanup function to kill both servers on exit
cleanup() {
    print_info "Stopping development servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    print_success "Servers stopped"
    exit 0
}

# Set up cleanup trap
trap cleanup INT TERM EXIT

# Parse instance path argument
INSTANCE_PATH=""
if [ ! -z "$1" ]; then
    INSTANCE_PATH="$1"
    print_info "Using instance from argument: $INSTANCE_PATH"
elif [ ! -z "$NIAMOTO_HOME" ]; then
    INSTANCE_PATH="$NIAMOTO_HOME"
    print_info "Using instance from NIAMOTO_HOME: $INSTANCE_PATH"
else
    INSTANCE_PATH="$(pwd)"
    print_warning "No instance specified, using current directory: $INSTANCE_PATH"
fi

# Convert to absolute path if relative
if [[ "$INSTANCE_PATH" != /* ]]; then
    INSTANCE_PATH="$REPO_ROOT/$INSTANCE_PATH"
fi

# Validate instance directory
if [ ! -d "$INSTANCE_PATH" ]; then
    print_error "Instance directory does not exist: $INSTANCE_PATH"
    exit 1
fi

print_success "Instance directory: $INSTANCE_PATH"

# Check if config directory exists (warning only)
if [ ! -d "$INSTANCE_PATH/config" ]; then
    print_warning "No config directory found in instance"
    print_warning "This might not be a valid Niamoto instance"
fi

# Check if frontend dependencies are installed
UI_DIR="$REPO_ROOT/src/niamoto/gui/ui"
if [ ! -d "$UI_DIR/node_modules" ]; then
    print_warning "Frontend dependencies not found"
    print_info "Installing npm dependencies..."
    cd "$UI_DIR"
    npm install
    cd "$REPO_ROOT"
    print_success "Dependencies installed"
fi

# Print header
clear
print_header "🚀 NIAMOTO GUI DEVELOPMENT MODE"
echo ""
print_info "Instance: $INSTANCE_PATH"
print_info "Backend:  http://127.0.0.1:8080/api (FastAPI with auto-reload)"
print_info "Frontend: http://127.0.0.1:5173 (Vite dev server with HMR)"
print_info "API Docs: http://127.0.0.1:8080/api/docs"
echo ""
print_warning "Use the Frontend URL for development (hot reload enabled)"
print_warning "Press Ctrl+C to stop both servers"
echo ""
print_header "STARTING SERVERS"
echo ""

# Start backend (FastAPI)
print_info "Starting FastAPI backend on port 8080..."
python "$SCRIPT_DIR/dev_api.py" --instance "$INSTANCE_PATH" --port 8080 > /tmp/niamoto-backend.log 2>&1 &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 2

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    print_error "Backend failed to start. Check logs:"
    cat /tmp/niamoto-backend.log
    exit 1
fi

print_success "Backend started (PID: $BACKEND_PID)"

# Start frontend (Vite)
print_info "Starting Vite frontend development server..."
cd "$UI_DIR"
npm run dev > /tmp/niamoto-frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait a bit for frontend to start
sleep 2

# Check if frontend is running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    print_error "Frontend failed to start. Check logs:"
    cat /tmp/niamoto-frontend.log
    exit 1
fi

print_success "Frontend started (PID: $FRONTEND_PID)"

echo ""
print_header "✨ READY FOR DEVELOPMENT"
echo ""
print_success "Open http://127.0.0.1:5173 in your browser"
print_info "Backend logs: tail -f /tmp/niamoto-backend.log"
print_info "Frontend logs: tail -f /tmp/niamoto-frontend.log"
echo ""
print_warning "Press Ctrl+C to stop both servers"
echo ""

# Wait for both processes
wait
