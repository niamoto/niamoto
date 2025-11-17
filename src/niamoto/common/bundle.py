"""
Utilities for handling file paths in PyInstaller bundles.

PyInstaller extracts files to a temporary directory (_MEIPASS).
This module provides helpers to access data files correctly whether
running from source or from a PyInstaller bundle.
"""

import sys
from pathlib import Path


def get_base_path() -> Path:
    """
    Get the base path for the application.

    When running from PyInstaller bundle, returns sys._MEIPASS.
    When running from source, returns the project root.

    Returns:
        Path: Base path for accessing application files

    Raises:
        AssertionError: If running from source and structure is invalid
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running in a PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # Running from source - go up from niamoto/common/ to project root
        base = Path(__file__).parent.parent.parent.parent

        # Quick sanity check (warning only, to allow test mocking)
        if not (base / "src" / "niamoto").exists():
            import warnings

            warnings.warn(
                f"Base path {base} doesn't contain expected src/niamoto/ directory. "
                f"This might cause issues loading resources.",
                RuntimeWarning,
                stacklevel=2,
            )

        return base


def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to a resource file.

    Works both in development and PyInstaller bundle.

    Args:
        relative_path: Path relative to the project root (e.g., "src/niamoto/data/config.yml")

    Returns:
        Path: Absolute path to the resource

    Example:
        >>> config_path = get_resource_path("src/niamoto/gui/templates/index.html")
        >>> with open(config_path) as f:
        ...     content = f.read()
    """
    base = get_base_path()
    return base / relative_path


def is_frozen() -> bool:
    """
    Check if running from PyInstaller bundle.

    Returns:
        bool: True if running from bundle, False if running from source
    """
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
