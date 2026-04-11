"""Health check endpoint for Tauri desktop app."""

import os
import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from niamoto.gui.api.context import (
    reload_project_from_desktop_config,
    get_working_directory,
    get_database_path,
)
from niamoto.gui.api.services.job_store_runtime import resolve_job_store
from niamoto.gui.api.services.preview_engine.engine import reset_preview_engine
from niamoto.gui.startup_logging import log_desktop_startup

router = APIRouter(prefix="/api/health", tags=["health"])
_first_health_logged = False
DESKTOP_PROBE_HEADER = "x-niamoto-desktop-probe"
DESKTOP_TOKEN_HEADER = "x-niamoto-desktop-token"


@router.get("")
async def health_check(request: Request):
    """
    Simple health check endpoint.

    Used by the Tauri desktop app to verify the FastAPI server is ready.
    """
    global _first_health_logged
    if not _first_health_logged:
        log_desktop_startup("health endpoint returned first successful response")
        _first_health_logged = True

    response = JSONResponse({"status": "ok", "message": "Niamoto API is running"})

    desktop_probe_requested = (
        request.headers.get(DESKTOP_PROBE_HEADER, "").strip() == "1"
    )
    desktop_auth_token = os.environ.get("NIAMOTO_DESKTOP_AUTH_TOKEN")
    if desktop_probe_requested and desktop_auth_token:
        response.headers[DESKTOP_TOKEN_HEADER] = desktop_auth_token

    return response


@router.get("/runtime-mode")
async def get_runtime_mode():
    """
    Detect the runtime mode (desktop vs web).

    Returns:
        - mode: "desktop" if running in Tauri app, "web" otherwise
        - project: Current NIAMOTO_HOME if set, None otherwise

    The Tauri application sets NIAMOTO_RUNTIME_MODE=desktop when launching the server.
    """
    runtime_mode = os.environ.get("NIAMOTO_RUNTIME_MODE", "web")
    niamoto_home = os.environ.get("NIAMOTO_HOME")

    return {
        "mode": runtime_mode,
        "project": niamoto_home,
        "features": {
            "project_switching": runtime_mode == "desktop",
        },
    }


@router.post("/reload-project")
async def reload_project(request: Request):
    """
    Reload the current project from Tauri desktop config.

    This endpoint is called after switching projects in the Tauri app.
    It reads the native desktop config file written by the Tauri shell and updates the FastAPI server's
    working directory without restarting the entire application.

    Returns:
        - project: The newly loaded project path (null if no project selected)
        - success: Whether the reload was successful
    """
    reload_result = reload_project_from_desktop_config()
    reset_preview_engine()

    if reload_result.state == "loaded":
        resolve_job_store(request.app)
    else:
        request.app.state.job_store = None
        request.app.state.job_store_work_dir = None

    return {
        "success": reload_result.state != "invalid-project",
        "state": reload_result.state,
        "project": (
            str(reload_result.project_path) if reload_result.project_path else None
        ),
        "message": reload_result.message,
    }


@router.get("/connectivity")
async def check_connectivity():
    """
    Check internet connectivity with a lightweight external request.

    Performs a HEAD request to a reliable external service with a 3-second timeout.
    Returns online status and latency.
    """
    import httpx

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.head("https://dns.google")
            latency_ms = round((time.monotonic() - start) * 1000)
            return {
                "online": response.status_code < 500,
                "latency_ms": latency_ms,
            }
    except Exception:
        latency_ms = round((time.monotonic() - start) * 1000)
        return {
            "online": False,
            "latency_ms": latency_ms,
        }


@router.get("/diagnostic")
async def get_diagnostic():
    """
    Get diagnostic information about the Niamoto GUI context.

    This endpoint returns information about the working directory,
    database path, and configuration files.
    """
    work_dir = get_working_directory()
    db_path = get_database_path()

    # Check for configuration files
    config_dir = work_dir / "config"
    config_files = {}
    for config_file in ["config.yml", "import.yml", "transform.yml", "export.yml"]:
        file_path = config_dir / config_file
        config_files[config_file] = {
            "exists": file_path.exists(),
            "path": str(file_path),
        }

    # Check database tables if database exists
    db_tables = []
    if db_path and db_path.exists():
        try:
            from sqlalchemy import create_engine, inspect

            engine = create_engine(f"sqlite:///{db_path}")
            inspector = inspect(engine)
            db_tables = inspector.get_table_names()
            engine.dispose()
        except Exception as e:
            db_tables = [f"Error reading tables: {str(e)}"]

    return {
        "working_directory": str(work_dir),
        "database": {
            "path": str(db_path) if db_path else None,
            "exists": db_path.exists() if db_path else False,
            "tables": db_tables,
        },
        "config_files": config_files,
    }


@router.get("/debug/test-500")
async def trigger_test_server_error():
    """Trigger a deliberate 500 response for manual feedback-flow testing."""

    raise HTTPException(
        status_code=500,
        detail="Intentional test 500 for bug report CTA validation.",
    )
