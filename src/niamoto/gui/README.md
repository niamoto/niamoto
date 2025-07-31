# Niamoto GUI

A modern web interface for configuring Niamoto data pipelines, built with React, TypeScript, and shadcn/ui.

## Features

- **Visual Configuration Builder**: Create and edit Niamoto pipeline configurations through an intuitive interface
- **Multi-step Workflow**: Organized sections for Import, Transform, Export, and Visualize
- **File Upload**: Drag-and-drop support for CSV, Excel, JSON, GeoJSON, and Shapefile formats
- **Real-time Validation**: Instant feedback on configuration validity
- **Modern UI**: Built with React and shadcn/ui for a clean, responsive interface

## Development

### Prerequisites

- Node.js 18+ and npm
- Python 3.10+ with Niamoto installed

### Setup

1. Navigate to the UI directory:
   ```bash
   cd src/niamoto/gui/ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

### Building for Production

To build the UI for production:

```bash
npm run build
```

This creates optimized files in the `dist/` directory.

## Usage

After building the UI, run the Niamoto GUI command:

```bash
niamoto gui
```

This will:
- Start a local web server (default port 8080)
- Open your browser automatically
- Serve the configuration interface

### Command Options

- `--port`: Specify a different port (default: 8080)
- `--host`: Specify the host to bind to (default: 127.0.0.1)
- `--no-browser`: Don't open the browser automatically

## Architecture

The GUI consists of:

- **Frontend**: React + TypeScript application with shadcn/ui components
- **Build System**: Vite for fast development and optimized production builds
- **Styling**: Tailwind CSS v4 with custom theme configuration
- **Routing**: React Router for navigation between sections

The interface is served as static files by a simple HTTP server, making it lightweight and easy to deploy.
