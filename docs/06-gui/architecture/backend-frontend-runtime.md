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
python scripts/dev_api.py --instance test-instance/niamoto-nc
cd src/niamoto/gui/ui && pnpm dev
```

## Packaged mode

In packaged or end-user mode:

- the frontend is pre-built into static assets
- FastAPI serves both the API and the frontend bundle
- Node.js is not required for end users

The build output used for this mode is:

- [src/niamoto/gui/ui/dist](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/dist)

## Desktop runtime

When running through Tauri:

- the same frontend is embedded inside the desktop application
- some behavior changes based on runtime detection
- local fonts are loaded from `public/fonts` instead of Google Fonts
- the welcome screen and project selection flow are especially relevant

## Practical implication

When documenting or changing GUI behavior, it is important to distinguish:

- backend API concerns
- frontend state and routing concerns
- runtime-specific behavior for desktop mode

These three layers share one product surface, but they are not the same implementation layer.
