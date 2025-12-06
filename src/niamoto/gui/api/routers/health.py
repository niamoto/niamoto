"""Health check endpoint for Tauri desktop app."""

import os
from fastapi import APIRouter, HTTPException

from niamoto.gui.api.context import (
    reload_project_from_desktop_config,
    get_working_directory,
    get_database_path,
)

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check():
    """
    Simple health check endpoint.

    Used by the Tauri desktop app to verify the FastAPI server is ready.
    """
    return {"status": "ok", "message": "Niamoto API is running"}


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
async def reload_project():
    """
    Reload the current project from Tauri desktop config.

    This endpoint is called after switching projects in the Tauri app.
    It reads ~/.niamoto/desktop-config.json and updates the FastAPI server's
    working directory without restarting the entire application.

    Returns:
        - project: The newly loaded project path
        - success: Whether the reload was successful

    Raises:
        HTTPException: If the project cannot be reloaded
    """
    project_path = reload_project_from_desktop_config()

    if project_path is None:
        raise HTTPException(
            status_code=500, detail="Failed to reload project from desktop config"
        )

    return {
        "success": True,
        "project": str(project_path),
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
