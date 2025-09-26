# GUI Development Guide

This guide explains the architecture and development workflow for the Niamoto GUI.

## Architecture Overview

The Niamoto GUI uses a hybrid architecture with:
- **Frontend**: React with TypeScript, Vite, and shadcn/ui
- **Backend**: FastAPI serving both API endpoints and static files
- **Two modes**: Development (hot-reload) and Production (optimized)

## Development Mode

For active development with hot module replacement:

### 1. Start the API server
```bash
cd /path/to/niamoto
uv run python -m niamoto gui --no-browser
```
This starts FastAPI on http://localhost:8080

### 2. Start the Vite dev server
```bash
cd src/niamoto/gui/ui
npm install  # First time only
npm run dev
```
This starts Vite on http://localhost:5173

### Architecture in Development
- **Port 5173**: Vite dev server with React hot-reload
- **Port 8080**: FastAPI with API endpoints
- **Proxy**: Vite proxies `/api/*` requests to FastAPI

```
Browser → localhost:5173 → Vite Dev Server
                              ↓
                          React App
                              ↓
                        /api/* calls
                              ↓
                    Proxy to localhost:8080
                              ↓
                          FastAPI
```

## Production Mode

For testing the production build or end-user usage:

### 1. Build the React app
```bash
cd src/niamoto/gui/ui
npm run build
```
This creates optimized files in `dist/`

### 2. Run Niamoto GUI
```bash
niamoto gui
```
This starts everything on http://localhost:8080

### Architecture in Production
- **Single port (8080)**: FastAPI serves everything
- **Static files**: React build from `dist/`
- **API routes**: Same server, no proxy needed

```
Browser → localhost:8080 → FastAPI
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
               /api/* routes      Static files
                    ↓                   ↓
              API handlers        React app
```

## Key Differences

| Aspect | Development | Production |
|--------|------------|------------|
| Command | `npm run dev` + API | `niamoto gui` |
| Ports | 5173 (React) + 8080 (API) | 8080 only |
| React files | Source files with HMR | Compiled bundle |
| Performance | Slower (dev features) | Optimized |
| Use case | Active development | Testing/deployment |

## Common Issues

### "Method Not Allowed" errors
- **Cause**: Using old API server without new routes
- **Fix**: Restart the API server after adding new endpoints

### 404 on API calls from port 5173
- **Cause**: Missing proxy configuration
- **Fix**: Ensure `vite.config.ts` has proxy settings

### Changes not appearing
- **Development**: Check both servers are running
- **Production**: Rebuild with `npm run build`

## File Structure

```
src/niamoto/gui/
├── api/                 # FastAPI backend
│   ├── app.py          # Main application
│   └── routers/        # API endpoints
├── ui/                  # React frontend
│   ├── src/            # Source code
│   ├── dist/           # Production build
│   └── vite.config.ts  # Vite configuration
└── README.md           # Basic documentation
```

## Adding New Features

1. **API Endpoint**: Add router in `api/routers/`
2. **React Component**: Add in `ui/src/components/`
3. **Test in Development**: Use two-server setup
4. **Build for Production**: `npm run build`
5. **Test Production**: `niamoto gui`

## Debugging Tips

- **API Documentation**: http://localhost:8080/docs
- **React DevTools**: Works in development mode
- **Network Tab**: Check if API calls go to correct port
- **Console**: Check for CORS or proxy errors
