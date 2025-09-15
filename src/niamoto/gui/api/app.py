"""FastAPI application for Niamoto GUI."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import config, database, files, imports, plugins, status

# Get the path to the built React app
UI_BUILD_DIR = Path(__file__).parent.parent / "ui" / "dist"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Niamoto GUI API",
        description="API for Niamoto visual configuration interface",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers FIRST (before static files)
    app.include_router(status.router, prefix="/api/status", tags=["status"])
    app.include_router(config.router, prefix="/api/config", tags=["config"])
    app.include_router(database.router, prefix="/api/database", tags=["database"])
    app.include_router(files.router, prefix="/api/files", tags=["files"])
    app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
    app.include_router(plugins.router, prefix="/api/plugins", tags=["plugins"])

    # Serve static files from the React build
    if UI_BUILD_DIR.exists():
        # Mount assets directory
        app.mount(
            "/assets", StaticFiles(directory=UI_BUILD_DIR / "assets"), name="assets"
        )

        # Mount the entire dist directory for all non-API routes
        # This will serve index.html for any route that doesn't match an API endpoint
        from fastapi.staticfiles import StaticFiles as HTMLStaticFiles

        class SPAStaticFiles(HTMLStaticFiles):
            """Static files handler that always serves index.html for HTML requests."""

            async def get_response(self, path: str, scope):
                try:
                    return await super().get_response(path, scope)
                except Exception:
                    # If file not found, serve index.html for client-side routing
                    return await super().get_response("index.html", scope)

        # Mount SPA handler last, so API routes take precedence
        app.mount("/", SPAStaticFiles(directory=UI_BUILD_DIR, html=True), name="spa")

    return app


# Create the app instance
app = create_app()
