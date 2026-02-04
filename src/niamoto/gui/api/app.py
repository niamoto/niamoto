"""FastAPI application for Niamoto GUI."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import (
    config,
    database,
    files,
    health,
    imports,
    layers,
    plugins,
    transform,
    export,
    data_explorer,
    entities,
    deploy,
    smart_config,
    site,
    stats,
    enrichment,
    transformer_suggestions,
    templates,
    sources,
    layout,
    recipes,
)
from .context import get_working_directory

# Get the path to the built React app
# Works in both source and frozen (PyInstaller) modes
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
    app.include_router(health.router)  # Health check endpoint for Tauri
    app.include_router(config.router, prefix="/api/config", tags=["config"])
    app.include_router(database.router, prefix="/api/database", tags=["database"])
    app.include_router(files.router, prefix="/api/files", tags=["files"])
    app.include_router(
        layers.router, prefix="/api", tags=["layers"]
    )  # Geographic layers API
    app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
    app.include_router(plugins.router, prefix="/api/plugins", tags=["plugins"])
    app.include_router(transform.router, prefix="/api/transform", tags=["transform"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])
    app.include_router(data_explorer.router, prefix="/api/data", tags=["data-explorer"])
    app.include_router(entities.router, prefix="/api/entities", tags=["entities"])
    app.include_router(deploy.router, prefix="/api/deploy", tags=["deploy"])
    app.include_router(smart_config.router, prefix="/api/smart", tags=["smart-config"])
    app.include_router(site.router, prefix="/api/site", tags=["site"])
    app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
    app.include_router(enrichment.router, prefix="/api/enrichment", tags=["enrichment"])
    app.include_router(
        transformer_suggestions.router
    )  # Already has /api/transformer-suggestions prefix
    app.include_router(
        templates.router, prefix="/api"
    )  # Templates API for Smart Setup V2
    app.include_router(sources.router, prefix="/api")  # Pre-calculated sources API
    app.include_router(layout.router, prefix="/api")  # Layout editor API
    app.include_router(recipes.router, prefix="/api")  # Widget recipes API

    # Serve exported site from exports/web/ directory
    work_dir = get_working_directory()
    if work_dir:
        exports_web_dir = work_dir / "exports" / "web"
        if exports_web_dir.exists():
            app.mount(
                "/preview",
                StaticFiles(directory=exports_web_dir, html=True),
                name="exported-site",
            )

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
