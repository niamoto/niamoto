"""Health and desktop runtime endpoints."""

import os
import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from niamoto.gui.api.context import (
    reload_project_from_desktop_config,
    get_working_directory,
    get_database_path,
)
from niamoto.gui.api.services.enrichment_service import (
    cancel_enrichment_for_project_change,
)
from niamoto.gui.api.services.job_store_runtime import resolve_job_store
from niamoto.gui.api.services.preview_engine.engine import reset_preview_engine
from niamoto.gui.startup_logging import log_desktop_startup

router = APIRouter(prefix="/api/health", tags=["health"])
_first_health_logged = False
DESKTOP_SHELL_ENV = "NIAMOTO_DESKTOP_SHELL"
DESKTOP_TOKEN_HEADER = "x-niamoto-desktop-token"


@router.get("")
async def health_check(request: Request):
    """
    Simple health check endpoint.

    Used by desktop shells to verify the FastAPI server is ready.
    """
    global _first_health_logged
    if not _first_health_logged:
        log_desktop_startup("health endpoint returned first successful response")
        _first_health_logged = True

    response = JSONResponse({"status": "ok", "message": "Niamoto API is running"})

    return response


@router.get("/runtime-mode")
async def get_runtime_mode():
    """
    Detect the runtime mode and active desktop shell.

    Returns:
        - mode: "desktop" when running behind a native desktop shell, "web" otherwise
        - shell: "tauri", "electron", or null
        - project: Current NIAMOTO_HOME if set, None otherwise

    Desktop shells set NIAMOTO_RUNTIME_MODE=desktop when launching the server.
    """
    runtime_mode = os.environ.get("NIAMOTO_RUNTIME_MODE", "web")
    shell_name = os.environ.get(DESKTOP_SHELL_ENV)
    niamoto_home = os.environ.get("NIAMOTO_HOME")

    return {
        "mode": runtime_mode,
        "shell": shell_name if shell_name in {"tauri", "electron"} else None,
        "project": niamoto_home,
        "features": {
            "project_switching": runtime_mode == "desktop",
        },
    }


@router.post("/reload-project")
async def reload_project(request: Request):
    """
    Reload the current project from the shared desktop config.

    This endpoint is called after switching projects in a native shell.
    It reads the shared desktop config file written by the active shell and updates the FastAPI server's
    working directory without restarting the entire application.

    Returns:
        - project: The newly loaded project path (null if no project selected)
        - success: Whether the reload was successful
    """
    _require_desktop_auth(request, require_configured=True)

    reload_result = reload_project_from_desktop_config()
    cancel_enrichment_for_project_change(reload_result.project_path)
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


def _require_desktop_auth(
    request: Request, *, require_configured: bool = False
) -> None:
    expected_token = os.environ.get("NIAMOTO_DESKTOP_AUTH_TOKEN")
    if not expected_token:
        if require_configured:
            raise HTTPException(
                status_code=401, detail="Desktop auth token is not configured."
            )
        return

    provided_token = request.headers.get(DESKTOP_TOKEN_HEADER)
    if provided_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid desktop auth token.")


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
async def get_diagnostic(request: Request):
    """
    Get diagnostic information about the Niamoto GUI context.

    This endpoint returns information about the working directory,
    database path, and configuration files.
    """
    _require_desktop_auth(request, require_configured=True)

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
        engine = None
        try:
            from sqlalchemy import create_engine, inspect

            engine = create_engine(f"sqlite:///{db_path}")
            inspector = inspect(engine)
            db_tables = inspector.get_table_names()
        except Exception as e:
            db_tables = [f"Error reading tables: {str(e)}"]
        finally:
            if engine is not None:
                engine.dispose()

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
    if os.environ.get("NIAMOTO_ENABLE_DEBUG_ROUTES") != "1":
        raise HTTPException(status_code=404, detail="Not found")

    raise HTTPException(
        status_code=500,
        detail="Intentional test 500 for bug report CTA validation.",
    )
