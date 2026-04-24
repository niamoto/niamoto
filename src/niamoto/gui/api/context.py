"""Shared context for GUI API endpoints.

This module provides utilities to access the Niamoto working directory
and database path in a consistent way across all API endpoints.
"""

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
from typing import Literal, Optional
import yaml

logger = logging.getLogger(__name__)

NIAMOTO_HOME_ENV = "NIAMOTO_HOME"

# Store the working directory set at GUI startup
_working_directory: Optional[Path] = None

ReloadProjectState = Literal["loaded", "welcome", "invalid-project"]


@dataclass(frozen=True)
class DesktopProjectReloadResult:
    """Result of reloading the desktop project from the Tauri config."""

    state: ReloadProjectState
    project_path: Optional[Path]
    message: Optional[str] = None


def set_working_directory(path: Path) -> None:
    """Set the working directory for the GUI session.

    This should be called once when the GUI starts, from the CLI command.

    Args:
        path: Path to the Niamoto project directory
    """
    global _working_directory
    _working_directory = path
    logger.info(f"GUI working directory set to: {path}")


def get_working_directory() -> Path:
    """Get the current working directory for the GUI.

    Determines the working directory in the following order:
    1. Directory set via set_working_directory() (when launched via 'niamoto gui')
    2. NIAMOTO_HOME environment variable (for development mode)
    3. Current working directory (fallback)

    Returns:
        Path to the Niamoto project directory
    """
    if _working_directory is not None:
        return _working_directory

    # Check NIAMOTO_HOME environment variable
    niamoto_home = os.environ.get("NIAMOTO_HOME")
    if niamoto_home:
        path = Path(niamoto_home)
        logger.info(f"Using NIAMOTO_HOME: {path}")
        return path

    # Fallback to current working directory
    cwd = Path.cwd()
    logger.warning(f"Working directory not set, using current directory: {cwd}")
    return cwd


def get_optional_working_directory() -> Optional[Path]:
    """Return the explicit GUI working directory when one is configured.

    Desktop startup can legitimately begin without any selected project.
    In that case, returning ``None`` lets the API stay in welcome mode
    instead of implicitly treating the process cwd as a project root.
    """
    if _working_directory is not None:
        return _working_directory

    niamoto_home = os.environ.get("NIAMOTO_HOME")
    if niamoto_home:
        path = Path(niamoto_home)
        logger.info(f"Using explicit NIAMOTO_HOME: {path}")
        return path

    return None


def resolve_explicit_working_directory(path: Optional[str]) -> Optional[Path]:
    """Return a normalized project path only when it is a valid project."""
    if not path:
        return None

    resolved = Path(path).expanduser().resolve()
    if _is_valid_desktop_project_path(resolved):
        return resolved

    logger.warning(f"Ignoring invalid explicit working directory: {resolved}")
    return None


def _sync_niamoto_home_env(project_path: Optional[Path]) -> None:
    """Keep NIAMOTO_HOME aligned with the active desktop project."""
    if project_path is None:
        os.environ.pop(NIAMOTO_HOME_ENV, None)
        return

    os.environ[NIAMOTO_HOME_ENV] = str(project_path)


def get_valid_optional_working_directory() -> Optional[Path]:
    """Return the configured working directory only when it is still valid."""
    work_dir = get_optional_working_directory()
    if work_dir is None:
        return None

    if _is_valid_desktop_project_path(work_dir):
        return work_dir

    logger.warning(f"Ignoring invalid configured working directory: {work_dir}")
    return None


def get_database_path() -> Optional[Path]:
    """Return the analytics database path (DuckDB by default).

    Search order:
    1. Path specified in config/config.yml (defaults to db/niamoto.duckdb)
    2. db/niamoto.duckdb
    3. niamoto.duckdb
    4. data/niamoto.duckdb
    5. Legacy SQLite fallbacks (db/niamoto.db, niamoto.db, data/niamoto.db)
    """
    work_dir = get_working_directory()

    # First check config for database path
    config_path = work_dir / "config" / "config.yml"

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                db_path_str = config.get("database", {}).get(
                    "path", "db/niamoto.duckdb"
                )
                db_path = work_dir / db_path_str
                if db_path.exists():
                    logger.debug(f"Database found from config: {db_path}")
                    return db_path
        except Exception as e:
            logger.warning(f"Error reading config: {e}")

    # Fallback to common locations
    common_paths = [
        work_dir / "db" / "niamoto.duckdb",
        work_dir / "niamoto.duckdb",
        work_dir / "data" / "niamoto.duckdb",
        work_dir / "db" / "niamoto.db",
        work_dir / "niamoto.db",
        work_dir / "data" / "niamoto.db",
    ]

    for db_path in common_paths:
        if db_path.exists():
            logger.debug(f"Database found at: {db_path}")
            return db_path

    logger.error(f"Database not found in {work_dir}")
    logger.error(f"Searched in: {[str(p) for p in common_paths]}")
    return None


def get_config_path(config_file: str) -> Path:
    """Get path to a configuration file.

    Args:
        config_file: Name of the config file (e.g., "transform.yml" or "config/transform.yml")

    Returns:
        Path to the configuration file
    """
    work_dir = get_working_directory()

    # If the path already starts with "config/", use it as-is
    if config_file.startswith("config/"):
        return work_dir / config_file

    # Otherwise, prepend "config/"
    return work_dir / "config" / config_file


def _is_valid_desktop_project_path(path: Path) -> bool:
    """Return whether a desktop project path matches the minimal project shape."""
    return (
        path.exists()
        and path.is_dir()
        and path.joinpath("db").is_dir()
        and path.joinpath("config").is_dir()
        and path.joinpath("config", "config.yml").is_file()
    )


def _resolve_desktop_config_path() -> Path:
    """Return the desktop config path, preferring the native platform location."""
    configured_path = os.environ.get("NIAMOTO_DESKTOP_CONFIG")
    if configured_path:
        return Path(configured_path).expanduser()

    legacy_home = Path.home() / ".niamoto" / "desktop-config.json"
    return legacy_home


def reload_project_from_desktop_config() -> DesktopProjectReloadResult:
    """Reload the current project from the desktop shell config.

    This reads the shared desktop config file written by the active shell to get the current project
    and updates the global working directory.

    Returns:
        A structured result describing the resulting desktop state.
    """
    global _working_directory

    desktop_config_path = _resolve_desktop_config_path()
    _working_directory = None
    _sync_niamoto_home_env(None)

    if not desktop_config_path.exists():
        logger.debug(f"Desktop config not found at {desktop_config_path}")
        return DesktopProjectReloadResult(
            state="welcome",
            project_path=None,
            message=None,
        )

    try:
        with open(desktop_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        current_project = config.get("current_project")
        if not current_project:
            logger.debug("No current_project in desktop config")
            return DesktopProjectReloadResult(
                state="welcome",
                project_path=None,
                message=None,
            )

        project_path = Path(current_project)
        if not _is_valid_desktop_project_path(project_path):
            logger.error(f"Project path is invalid: {project_path}")
            return DesktopProjectReloadResult(
                state="invalid-project",
                project_path=None,
                message=(
                    "The selected desktop project is no longer available. "
                    "Open another project or remove it from the recent list."
                ),
            )

        # Update the global working directory
        _working_directory = project_path
        _sync_niamoto_home_env(project_path)
        logger.info(f"Reloaded project from desktop config: {project_path}")
        return DesktopProjectReloadResult(
            state="loaded",
            project_path=project_path,
            message=None,
        )

    except Exception as e:
        logger.error(f"Error reading desktop config: {e}")
        return DesktopProjectReloadResult(
            state="invalid-project",
            project_path=None,
            message="Failed to read the desktop project configuration.",
        )
