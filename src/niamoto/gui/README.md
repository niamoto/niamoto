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

### Setup

1. Install Node.js dependencies:
```bash
cd src/niamoto/gui/ui
npm install
```

2. Run development server:
```bash
npm run dev  # Frontend dev server (port 5173)
```

In another terminal:
```bash
niamoto gui --reload  # Backend with auto-reload
```

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

### Backend (`api/`)
- FastAPI application
- Provides REST APIs for configuration management
- Serves the built React application
- Handles file uploads and analysis

### Frontend (`ui/`)
- React 19 with TypeScript
- Vite for build tooling
- Tailwind CSS v4 for styling
- shadcn/ui components
- Internationalization (French/English)

## How It Works in Production

1. **Pre-built files**: The React app is built into static HTML/JS/CSS files
2. **Python serves static files**: FastAPI serves these files directly
3. **No Node.js required**: End users only need Python installed
4. **Single process**: Everything runs from `niamoto gui` command

## API Endpoints

- `/api/config` - Configuration management
- `/api/files` - File operations
- `/api/imports` - Import process management
- `/api/docs` - API documentation (Swagger UI)

## Development Workflow

1. Make changes to React code in `ui/src/`
2. Test with `npm run dev`
3. Build with `npm run build`
4. Test the built version with `niamoto gui`
5. Commit the built files before publishing
