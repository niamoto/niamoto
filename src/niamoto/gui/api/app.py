"""FastAPI application for Niamoto GUI."""

import os
from pathlib import Path
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from niamoto.gui.startup_logging import log_desktop_startup

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
    preview,
    pipeline,
)
from .context import get_optional_working_directory
from .services.job_store_runtime import resolve_job_store

APP_IMPORT_STARTED = time.perf_counter()
log_desktop_startup("app.py import started")

# Get the path to the built React app
# Works in both source and frozen (PyInstaller) modes
UI_BUILD_DIR = Path(__file__).parent.parent / "ui" / "dist"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    create_app_started = time.perf_counter()
    log_desktop_startup("create_app() started")

    app = FastAPI(
        title="Niamoto GUI API",
        description="API for Niamoto visual configuration interface",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    configured_origins = os.getenv("NIAMOTO_CORS_ORIGINS")
    if configured_origins:
        allow_origins = [
            origin.strip() for origin in configured_origins.split(",") if origin.strip()
        ]
    else:
        # Safe defaults for local development + Tauri desktop runtime.
        allow_origins = [
            "http://localhost",
            "http://127.0.0.1",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "tauri://localhost",
            "http://tauri.localhost",
        ]

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _log_startup_event() -> None:
        log_desktop_startup("FastAPI startup event fired")

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
    app.include_router(preview.router, prefix="/api")  # Unified preview engine (new)
    app.include_router(
        templates.router, prefix="/api"
    )  # Templates API for Smart Setup V2
    app.include_router(sources.router, prefix="/api")  # Pre-calculated sources API
    app.include_router(layout.router, prefix="/api")  # Layout editor API
    app.include_router(recipes.router, prefix="/api")  # Widget recipes API
    app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])

    work_dir = get_optional_working_directory()
    if work_dir is not None:
        resolve_job_store(app)
    else:
        app.state.job_store = None
        app.state.job_store_work_dir = None

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

    log_desktop_startup(
        f"create_app() completed in {time.perf_counter() - create_app_started:.3f}s"
    )
    return app


# Create the app instance
app = create_app()
log_desktop_startup(
    f"module-level FastAPI app created in {time.perf_counter() - APP_IMPORT_STARTED:.3f}s"
)
