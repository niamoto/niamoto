# Niamoto Desktop Application

This document describes the architecture and implementation of the Niamoto Desktop application built with Tauri.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Multi-Project Support](#multi-project-support)
- [Runtime Mode Detection](#runtime-mode-detection)
- [Plugin Resolution Cascade](#plugin-resolution-cascade)
- [Building the Desktop App](#building-the-desktop-app)
- [Development](#development)

## Overview

Niamoto Desktop is a cross-platform desktop application that wraps the Niamoto web interface in a native application using Tauri. It provides:

- **Native desktop experience** - Runs as a native app on macOS, Windows, and Linux
- **Multi-project support** - Switch between different Niamoto projects without restarting
- **Persistent configuration** - Remembers recent projects and current selection
- **Plugin cascade resolution** - Unified plugin loading from system, user, and project locations

## Architecture

### Tech Stack

**Backend (Rust/Tauri)**:
- **Tauri 2.x** - Native desktop framework
- **serde** - Serialization/deserialization
- **dirs** - Cross-platform directory paths
- **chrono** - Timestamp management

**Frontend (React/TypeScript)**:
- **React 19** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS v4** - Styling
- **shadcn/ui** - Component library

**Python Backend**:
- **FastAPI** - REST API server
- **DuckDB** - Database engine

### Application Flow

```
┌─────────────────────────────────────────────┐
│          Tauri Desktop App (Rust)           │
│  ┌───────────────────────────────────────┐  │
│  │  1. Load config from                  │  │
│  │     ~/.niamoto/desktop-config.json    │  │
│  │                                       │  │
│  │  2. Launch FastAPI server with:      │  │
│  │     - NIAMOTO_RUNTIME_MODE=desktop   │  │
│  │     - NIAMOTO_HOME=/path/to/project  │  │
│  │                                       │  │
│  │  3. Display React UI in webview      │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│     FastAPI Server (Python/niamoto)         │
│  ┌───────────────────────────────────────┐  │
│  │  - Detects runtime mode via env var  │  │
│  │  - Loads plugins with cascade         │  │
│  │  - Serves /api/health/runtime-mode    │  │
│  │  - Serves React UI static files       │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         React Frontend (TypeScript)         │
│  ┌───────────────────────────────────────┐  │
│  │  - Fetches runtime mode on mount      │  │
│  │  - Shows ProjectSwitcher if desktop   │  │
│  │  - Calls Tauri commands for switching │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Multi-Project Support

### Configuration Storage

Project configuration is stored in `~/.niamoto/desktop-config.json`:

```json
{
  "current_project": "/Users/user/projects/niamoto-nc",
  "recent_projects": [
    {
      "path": "/Users/user/projects/niamoto-nc",
      "name": "niamoto-nc",
      "last_accessed": "2025-11-16T17:00:00Z"
    },
    {
      "path": "/Users/user/projects/niamoto-test",
      "name": "niamoto-test",
      "last_accessed": "2025-11-15T10:30:00Z"
    }
  ],
  "last_updated": "2025-11-16T17:00:00Z"
}
```

### Rust Backend Files

**src-tauri/src/config.rs**
- `AppConfig` struct for configuration management
- Load/save operations for desktop-config.json
- Project validation (checks for `db/` directory)
- Recent projects management (max 10, ordered by last access)

**src-tauri/src/commands.rs**
- Tauri commands exposed to frontend:
  - `get_current_project()` - Get active project path
  - `get_recent_projects()` - Get list of recent projects
  - `set_current_project(path)` - Switch to a different project
  - `remove_recent_project(path)` - Remove from recents
  - `validate_project(path)` - Check if path is valid

**src-tauri/src/lib.rs**
- Main application setup
- Launches FastAPI server with environment variables
- Manages server process lifecycle
- Handles window events and cleanup

### React Frontend Components

**src/niamoto/gui/ui/src/hooks/useRuntimeMode.ts**
```typescript
const { isDesktop, features } = useRuntimeMode();
// features.project_switching = true in desktop mode
```

**src/niamoto/gui/ui/src/hooks/useProjectSwitcher.ts**
```typescript
const {
  currentProject,
  recentProjects,
  switchProject,
  removeProject
} = useProjectSwitcher();
```

**src/niamoto/gui/ui/src/components/project-switcher.tsx**
- Dropdown menu showing recent projects
- Switch between projects
- Remove projects from history

### Project Switching Flow

1. User clicks project in ProjectSwitcher dropdown
2. Frontend calls `window.__TAURI__.core.invoke('set_current_project', { path })`
3. Rust updates `~/.niamoto/desktop-config.json`
4. Frontend reloads: `window.location.reload()`
5. Tauri detects new config on reload
6. Tauri kills old FastAPI server
7. Tauri launches new FastAPI server with new `NIAMOTO_HOME`
8. React UI loads with new project context

## Runtime Mode Detection

### API Endpoint

**GET /api/health/runtime-mode**

Response in web mode:
```json
{
  "mode": "web",
  "project": null,
  "features": {
    "project_switching": false
  }
}
```

Response in desktop mode:
```json
{
  "mode": "desktop",
  "project": "/Users/user/projects/niamoto-nc",
  "features": {
    "project_switching": true
  }
}
```

### Environment Variables

- `NIAMOTO_RUNTIME_MODE` - Set to "desktop" by Tauri
- `NIAMOTO_HOME` - Project path (set by Tauri if project selected)

### Frontend Usage

```typescript
import { useRuntimeMode } from '@/hooks/useRuntimeMode';

export function MyComponent() {
  const { isDesktop, features } = useRuntimeMode();

  return (
    <>
      {features.project_switching && <ProjectSwitcher />}
    </>
  );
}
```

## Plugin Resolution Cascade

Niamoto uses a three-tier plugin resolution system that works identically in CLI and Desktop modes:

### Resolution Order (by priority)

1. **Project plugins** (priority 100) - `{project}/plugins/`
2. **User plugins** (priority 50) - `~/.niamoto/plugins/`
3. **System plugins** (priority 10) - `src/niamoto/core/plugins/`

### Conflict Resolution

When multiple plugins have the same name:
- Higher priority wins (project > user > system)
- Conflict logged with details of all locations
- Only the winning plugin is loaded

### Example

```
Project: /Users/user/niamoto-nc/plugins/my_transformer.py (priority 100) ✓
User:    ~/.niamoto/plugins/my_transformer.py              (priority 50)  ✗
System:  src/niamoto/core/plugins/my_transformer.py        (priority 10)  ✗

→ Loads project version, logs conflict
```

### CLI Command

```bash
niamoto plugins list
# Shows all plugins with their scope (project/user/system) and priority
```

## Building the Desktop App

### Prerequisites

1. **Rust** - Install from https://rustup.rs/
2. **Node.js** - Install from https://nodejs.org/
3. **Niamoto** - Install or build from source

### Build Steps

#### 1. Prepare Niamoto Binary

```bash
# Build and copy the niamoto binary for bundling
./build_scripts/prepare_tauri_bins.sh
```

This script:
- Detects your platform (macOS ARM64/x86_64, Linux, Windows)
- Copies `niamoto` binary to `src-tauri/bin/niamoto-{platform}`
- Required before building the Tauri app

#### 2. Build React Frontend

```bash
cd src/niamoto/gui/ui
npm install
npm run build
```

Outputs to: `src/niamoto/gui/ui/dist/`

#### 3. Build Tauri Application

```bash
# Development build (faster, larger)
cargo tauri build --debug

# Production build (optimized)
cargo tauri build
```

Output location:
- macOS: `src-tauri/target/release/bundle/dmg/`
- Windows: `src-tauri/target/release/bundle/msi/`
- Linux: `src-tauri/target/release/bundle/deb/` or `appimage/`

### Platform-Specific Notes

**macOS**:
- Requires code signing for distribution
- Use `--target` to build for specific arch: `--target aarch64-apple-darwin`

**Windows**:
- Requires WiX Toolset for MSI installer
- Set icon in `src-tauri/tauri.conf.json`

**Linux**:
- Multiple formats available: AppImage, deb, rpm
- AppImage is most portable

## Development

### Running in Development Mode

**Option 1: Full Tauri Dev Mode**
```bash
# Start both React dev server and Tauri
cd src-tauri
cargo tauri dev
```

**Option 2: Separate Frontend/Backend**
```bash
# Terminal 1: React dev server
cd src/niamoto/gui/ui
npm run dev

# Terminal 2: Tauri app pointing to dev server
cd src-tauri
cargo tauri dev
```

### Project Structure

```
Niamoto/
├── src-tauri/                      # Tauri Rust application
│   ├── src/
│   │   ├── config.rs              # Config management
│   │   ├── commands.rs            # Tauri commands
│   │   ├── lib.rs                 # Main app logic
│   │   └── main.rs                # Entry point
│   ├── bin/                        # Bundled niamoto binary
│   │   └── niamoto-{platform}
│   ├── Cargo.toml                  # Rust dependencies
│   └── tauri.conf.json            # Tauri configuration
│
├── src/niamoto/
│   ├── common/
│   │   └── resource_paths.py      # Plugin cascade resolution
│   ├── core/
│   │   └── plugins/
│   │       └── plugin_loader.py   # Unified plugin loading
│   └── gui/
│       ├── api/
│       │   ├── app.py
│       │   └── routers/
│       │       └── health.py      # Runtime mode endpoint
│       └── ui/                     # React frontend
│           └── src/
│               ├── components/
│               │   ├── project-switcher.tsx
│               │   └── layout/
│               │       └── TopBar.tsx
│               └── hooks/
│                   ├── useRuntimeMode.ts
│                   └── useProjectSwitcher.ts
│
├── build_scripts/
│   └── prepare_tauri_bins.sh      # Binary preparation
│
└── ~/.niamoto/                     # User directory
    ├── desktop-config.json         # Desktop app config
    ├── plugins/                    # User plugins (priority 50)
    └── templates/                  # User templates
```

### Debugging

**Rust Console Logs**:
```bash
cargo tauri dev
# Logs appear in terminal
```

**React Console Logs**:
- Open DevTools in the Tauri window: `Cmd+Option+I` (macOS) or `Ctrl+Shift+I` (Windows/Linux)

**Network Requests**:
- DevTools Network tab shows API calls to FastAPI server

### Common Issues

**Issue**: `resource path 'bin/niamoto-{platform}' doesn't exist`
**Solution**: Run `./build_scripts/prepare_tauri_bins.sh`

**Issue**: React build not found
**Solution**: `cd src/niamoto/gui/ui && npm run build`

**Issue**: Server fails to start
**Solution**: Check that niamoto binary is executable and in PATH or bundled correctly

**Issue**: Project switching doesn't work
**Solution**: Verify Tauri commands are registered in `lib.rs` invoke_handler

## Testing

### Test Runtime Mode Detection

```bash
# Start in web mode
cd test-instance/niamoto-test
niamoto gui --port 8765

# Check endpoint
curl http://127.0.0.1:8765/api/health/runtime-mode
# Should return {"mode": "web", ...}
```

### Test Desktop Mode

```bash
# Build and run Tauri app
cd src-tauri
cargo tauri dev

# In DevTools console:
fetch('/api/health/runtime-mode').then(r => r.json()).then(console.log)
# Should return {"mode": "desktop", ...}
```

### Test Plugin Cascade

```bash
# Create test plugins at different levels
echo "print('Project plugin')" > test-instance/niamoto-test/plugins/test.py
echo "print('User plugin')" > ~/.niamoto/plugins/test.py

# List plugins
niamoto plugins list

# Project version should win (priority 100)
```

## Distribution

### Code Signing (macOS)

```bash
# Set environment variables
export APPLE_CERTIFICATE=...
export APPLE_CERTIFICATE_PASSWORD=...
export APPLE_ID=...
export APPLE_PASSWORD=...

# Build with signing
cargo tauri build
```

### Windows Installer

- MSI installer created automatically
- Requires WiX Toolset
- Configure in `tauri.conf.json` under `bundle.windows`

### Linux AppImage

```bash
# Build AppImage
cargo tauri build --bundles appimage

# Portable executable - no installation needed
./target/release/bundle/appimage/niamoto_0.7.4_amd64.AppImage
```

## Future Enhancements

- [ ] Folder browser dialog for selecting projects
- [ ] Project creation wizard within desktop app
- [ ] Auto-update mechanism
- [ ] System tray integration
- [ ] Multiple window support for comparing projects
- [ ] Background task notifications
- [ ] Project templates management UI

## References

- [Tauri Documentation](https://tauri.app/v2/)
- [Niamoto Plugin System](./PLUGINS.md)
- [Resource Cascade Architecture](./ARCHITECTURE_MULTI_PROJETS.md)
