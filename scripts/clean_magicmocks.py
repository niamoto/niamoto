#!/usr/bin/env python
"""
Clean up MagicMock files and directories created during tests.

This script removes any files or directories that match MagicMock patterns
which may have been created during test runs.
"""

import os
import re
import shutil
from pathlib import Path


def is_magicmock(name):
    """Check if a file or directory name matches MagicMock patterns."""
    patterns = [
        r"^<MagicMock.*>$",
        r"^MagicMock$",
        r".*MagicMock.*",
        r"^\d+$",  # ID directories inside MagicMock directories
    ]

    return any(re.match(pattern, name) for pattern in patterns)


def clean_magicmocks(directory):
    """
    Recursively clean MagicMock files and directories from the given directory.

    Args:
        directory (str): Path to the directory to clean

    Returns:
        int: Number of items removed
    """
    count = 0
    root_path = Path(directory)

    # First pass: identify items to remove
    to_remove = []

    for item in root_path.glob("**/*"):
        rel_path = item.relative_to(root_path)

        # Skip .git and other hidden directories
        if any(part.startswith(".") for part in rel_path.parts):
            continue

        if is_magicmock(item.name):
            to_remove.append(item)
            count += 1

    # Second pass: remove identified items (deepest first to avoid dependency issues)
    for item in sorted(to_remove, key=lambda x: len(str(x)), reverse=True):
        try:
            if item.is_file():
                print(f"Removing file: {item}")
                item.unlink()
            elif item.is_dir():
                print(f"Removing directory: {item}")
                shutil.rmtree(item)
        except Exception as e:
            print(f"Error removing {item}: {e}")

    return count


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    removed = clean_magicmocks(project_root)
    print(f"Cleaned up {removed} MagicMock files and directories")
