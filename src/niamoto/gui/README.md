# Niamoto GUI

## Overview

The Niamoto GUI provides a web-based interface for configuring and managing Niamoto data pipelines. It consists of:

- **Backend**: FastAPI server (Python) that provides REST APIs
- **Frontend**: React application (TypeScript) built with Vite

## For End Users (pip install niamoto)

When you install Niamoto via pip, the GUI is included as pre-built static files. No Node.js or npm is required.

### Usage

Simply run:
```bash
niamoto gui
```

This will:
1. Start the FastAPI server on port 8080
2. Serve the pre-built React application
3. Open your browser automatically

### Options

```bash
niamoto gui --port 8081  # Use a different port
niamoto gui --no-browser  # Don't open browser automatically
niamoto gui --reload      # Enable auto-reload (development)
```

## For Developers

If you're developing the GUI, you'll need Node.js and npm installed.

### Quick Start (Recommended)

From the repository root:

```bash
# 1. Install frontend dependencies (first time only)
cd src/niamoto/gui/ui && npm install && cd ../../../..

# 2. Start development environment with hot reload
./scripts/dev_gui.sh test-instance/niamoto-nc

# 3. Open browser to http://127.0.0.1:5173
```

This launches both servers in parallel with full hot reload for both React and Python code.

### Manual Dual Server Setup

If you prefer to run servers separately:

**Terminal 1 - Backend:**
```bash
python scripts/dev_api.py --instance test-instance/niamoto-nc
```

**Terminal 2 - Frontend:**
```bash
cd src/niamoto/gui/ui
npm run dev
```

Access the frontend at `http://127.0.0.1:5173` (Vite will proxy `/api/*` requests to port 8080).

### Instance Context

The GUI needs to know which Niamoto instance to work with. Context is resolved in this order:

1. **CLI argument**: `--instance /path/to/instance`
2. **Environment variable**: `export NIAMOTO_HOME=/path/to/instance`
3. **Current directory**: Falls back to `pwd` (with warning)

### Development Workflow

1. Make changes to React code in `ui/src/` or Python code in `api/`
2. Changes are automatically reloaded (no manual rebuild needed)
3. Test in browser at `http://127.0.0.1:5173`
4. Before publishing, build with `npm run build` and test production mode

### Building for Distribution

Before publishing to PyPI, build the GUI:

```bash
# From project root
bash scripts/build_gui.sh
```

Or when publishing:
```bash
bash scripts/publish.sh --build-gui
```

This creates the `dist/` directory with optimized static files that will be included in the pip package.

## Architecture

```
Development Mode:
┌─────────────────────┐         ┌─────────────────────┐
│  Vite Dev Server    │         │  FastAPI Backend    │
│   (Port 5173)       │◄────────│   (Port 8080)       │
│                     │  Proxy  │                     │
│  - React HMR        │  /api/* │  - REST API         │
│  - Hot Reload       │         │  - Auto-reload      │
└─────────────────────┘         └─────────────────────┘

Production Mode:
┌───────────────────────────────────────┐
│         FastAPI Backend               │
│          (Port 8080)                  │
│                                       │
│  - REST API at /api/*                 │
│  - Serves static build from ui/dist/  │
└───────────────────────────────────────┘
```

### Backend (`api/`)
- FastAPI application
- Provides REST APIs for configuration management
- Instance context management via `context.py`
- Serves the built React application in production
- Handles file uploads and analysis

### Frontend (`ui/`)
- React 19 with TypeScript
- Vite for build tooling and dev server
- Tailwind CSS v4 for styling
- shadcn/ui components
- Internationalization (French/English)

## How It Works

### In Development Mode

1. Vite dev server runs on port 5173 with hot module replacement (HMR)
2. FastAPI backend runs on port 8080 with auto-reload
3. Vite proxies all `/api/*` requests to FastAPI (configured in `vite.config.ts`)
4. React changes hot reload instantly without rebuilding
5. Python changes auto-reload the FastAPI server

### In Production Mode

1. **Pre-built files**: The React app is built into static HTML/JS/CSS files
2. **Python serves static files**: FastAPI serves these files directly
3. **No Node.js required**: End users only need Python installed
4. **Single process**: Everything runs from `niamoto gui` command

## API Endpoints

- `/api/config/{config_name}` - Get/update configuration files
- `/api/database/schema` - Database introspection
- `/api/database/tables/{table}/preview` - Preview table data
- `/api/entities` - Entity registry management
- `/api/files/list` - File operations
- `/api/imports/detect-fields` - Field detection
- `/api/docs` - Interactive API documentation (Swagger UI)

## Troubleshooting

### Port already in use

If port 8080 or 5173 is already in use:

```bash
# Find and kill the process
lsof -ti:8080 | xargs kill
lsof -ti:5173 | xargs kill
```

### Frontend can't connect to backend

Make sure both servers are running:
```bash
# Check backend
curl http://127.0.0.1:8080/api/docs

# Check frontend
curl http://127.0.0.1:5173
```

### Instance not found

Ensure you're pointing to a valid Niamoto instance:
```bash
# Check instance structure
ls -la test-instance/niamoto-nc/
# Should contain: config/, db/, exports/ directories
```

## Environment Variables

- `NIAMOTO_HOME` - Path to the Niamoto instance directory
- `VITE_API_BASE_URL` - (Frontend only) Override API base URL (default: uses Vite proxy)
