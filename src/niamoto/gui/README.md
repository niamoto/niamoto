# Niamoto GUI

The `src/niamoto/gui` package contains the full graphical interface layer for Niamoto:

- a Python backend built with FastAPI
- a React/TypeScript frontend built with Vite

This README is the high-level entry point for the GUI as a whole.
For frontend-specific architecture, conventions, and assets, see:

- [ui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/README.md)

## Directory overview

- [api](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/api): FastAPI app, routers, services, request models
- [ui](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui): React frontend application

## End-user mode

When Niamoto is installed via pip, the GUI is served as a pre-built frontend bundle behind the Python backend. End users do not need Node.js or pnpm.

Run:

```bash
niamoto gui
```

Useful options:

```bash
niamoto gui --port 8081
niamoto gui --no-browser
niamoto gui --reload
```

What this does:
- starts the FastAPI GUI backend
- serves the built frontend from the UI build output
- opens the browser unless disabled

## Developer workflow

If you are developing the GUI, you need both Python and Node.js tooling.

### Recommended setup

From the repository root:

```bash
cd src/niamoto/gui/ui
pnpm install
cd ../../../..
./scripts/dev_gui.sh test-instance/niamoto-nc
```

This starts:
- the FastAPI backend with reload
- the Vite dev server with HMR

Default frontend URL:

```text
http://127.0.0.1:5173
```

### Manual dual-server setup

Backend:

```bash
uv run python scripts/dev/dev_api.py --instance test-instance/niamoto-nc
```

Frontend:

```bash
cd src/niamoto/gui/ui
pnpm dev
```

The Vite dev server proxies `/api/*` to the backend.

## Instance context

The GUI needs a Niamoto instance path. Resolution order:

1. CLI argument: `--instance /path/to/instance`
2. Environment variable: `NIAMOTO_HOME=/path/to/instance`
3. Current working directory

## Build and distribution

To build the frontend bundle used by the Python GUI server:

```bash
bash scripts/build_gui.sh
```

Or through the build script:

```bash
bash scripts/build/build_gui.sh
```

This generates the frontend build in:

- [ui/dist](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/dist)

That build output is what the Python backend serves in packaged/distribution mode.

## Architecture

### Development mode

- Vite dev server serves the React app with HMR
- FastAPI serves the backend API
- Vite proxies `/api/*` to FastAPI

### Production/distribution mode

- the frontend is pre-built into static assets
- FastAPI serves both the API and the built frontend
- Node.js is not required for end users

## Backend responsibilities

The GUI backend is responsible for:

- instance resolution and context management
- serving configuration and data APIs
- file operations and import orchestration
- serving the built frontend in packaged mode

Main entry points:

- [api/app.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/api/app.py)
- [api/context.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/api/context.py)

## Frontend responsibilities

The frontend is responsible for:

- interactive import and review flows
- dashboard and navigation
- group configuration
- site configuration
- publish workflows
- desktop onboarding UX

The frontend now follows a feature-oriented structure centered on:

- `src/app`
- `src/features`
- `src/shared`

See the detailed frontend README:

- [ui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/README.md)

## Troubleshooting

### Port already in use

```bash
lsof -ti:8080 | xargs kill
lsof -ti:5173 | xargs kill
```

### Frontend cannot reach backend

Check backend:

```bash
curl http://127.0.0.1:8080/api/docs
```

Check frontend:

```bash
curl http://127.0.0.1:5173
```

### Invalid instance path

Check that the target instance contains the expected directories, typically:

```bash
config/
db/
exports/
```

## Environment variables

- `NIAMOTO_HOME`: path to the active instance
- `VITE_API_BASE_URL`: override frontend API base URL when needed
- `NIAMOTO_DESKTOP_CONFIG`: override the desktop config path used by the Tauri shell and FastAPI sidecar
- `NIAMOTO_DESKTOP_LOG_DIR`: override the native desktop startup log directory
