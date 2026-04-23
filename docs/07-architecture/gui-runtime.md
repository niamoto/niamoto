# Backend / Frontend Runtime Model

Niamoto GUI runs in two main modes.

## Development mode

In development:

- the React app runs through the Vite dev server
- the FastAPI backend runs separately
- Vite proxies `/api/*` calls to FastAPI

This gives:

- hot module replacement on the frontend
- backend auto-reload during Python development
- a clear separation between UI assets and API behavior

Typical workflow:

```bash
./scripts/dev/dev_web.sh test-instance/niamoto-nc
```

Or manually:

```bash
uv run python scripts/dev/dev_api.py --instance test-instance/niamoto-nc
cd src/niamoto/gui/ui && pnpm dev
```

## Packaged mode

In packaged or end-user mode:

- the frontend is pre-built into static assets
- FastAPI serves both the API and the frontend bundle
- Node.js is not required for end users

The build output used for this mode is:

- `src/niamoto/gui/ui/dist`

## Desktop runtime

When running through a desktop shell:

- the same frontend is embedded inside the native application window
- packaged desktop mode loads the UI from the loopback FastAPI server on `127.0.0.1`
- the shell waits for an authenticated `/api/health` probe before navigating to that loopback origin
- runtime metadata exposes both `mode` (`web` or `desktop`) and `shell` (`tauri`, `electron`, or `null`)
- local fonts are loaded from `public/fonts` instead of Google Fonts
- the welcome screen and project selection flow are especially relevant

Current shells:

- Tauri remains the production desktop shell
- Electron exists as a parallel experimental shell under `electron/`

The shell-neutral desktop contract now includes:

- a shared renderer bridge for project selection, settings, external URLs, and desktop-only helpers
- a Tauri-native application menu that emits shell actions back into the renderer for command palette, settings, documentation, and sidebar toggling
- a small shared shell action layer in the renderer so menu actions and non-native keyboard bindings reuse the same command paths
- a shared project-selection config path through `NIAMOTO_DESKTOP_CONFIG`
- shell-specific settings, logs, and application identifiers kept separate

Development entry points:

```bash
./scripts/dev/dev_desktop.sh test-instance/niamoto-nc
./scripts/dev/dev_electron.sh test-instance/niamoto-nc
```

Both shells follow the same high-level startup model:

1. show a lightweight native loading state
2. launch the Python sidecar on loopback
3. wait for the authenticated health probe to return the expected desktop token
4. navigate the window to Vite in hot-reload mode, or to the packaged FastAPI loopback origin otherwise

## What to separate when you document or change the GUI

Keep these layers distinct:

- backend API concerns
- frontend state and routing concerns
- runtime-specific behavior for desktop mode

Users see one product. The code does not live in one layer.
