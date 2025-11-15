"""Shared context for GUI API endpoints.

This module provides utilities to access the Niamoto working directory
and database path in a consistent way across all API endpoints.
"""

import logging
import os
from pathlib import Path
from typing import Optional
import yaml

logger = logging.getLogger(__name__)

# Store the working directory set at GUI startup
_working_directory: Optional[Path] = None


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


def get_database_path() -> Optional[Path]:
    """Get the path to the SQLite database.

    Searches for the database in the following order:
    1. Path specified in config/config.yml
    2. db/niamoto.db in working directory
    3. niamoto.db in working directory
    4. data/niamoto.db in working directory

    Returns:
        Path to the database file, or None if not found
    """
    work_dir = get_working_directory()

    # First check config for database path
    config_path = work_dir / "config" / "config.yml"

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
                db_path_str = config.get("database", {}).get("path", "db/niamoto.db")
                db_path = work_dir / db_path_str
                if db_path.exists():
                    logger.debug(f"Database found from config: {db_path}")
                    return db_path
        except Exception as e:
            logger.warning(f"Error reading config: {e}")

    # Fallback to common locations
    common_paths = [
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
