"""
Emoji utilities for cross-platform compatibility.

This module provides a centralized way to handle emoji/Unicode characters
that may not be supported on all platforms (e.g., Windows CP1252 encoding).
"""

import sys
import os

# Auto-detect: disable emojis on Windows by default, enable on macOS/Linux
# Can be overridden with NIAMOTO_USE_EMOJIS environment variable
USE_EMOJIS = (
    os.getenv(
        "NIAMOTO_USE_EMOJIS", "true" if sys.platform != "win32" else "false"
    ).lower()
    == "true"
)


def emoji(unicode_char: str, fallback: str) -> str:
    """
    Return emoji or fallback based on platform support.

    Args:
        unicode_char: The Unicode emoji/symbol (e.g., "🚀", "✓")
        fallback: ASCII-safe fallback (e.g., ">>", "[OK]")

    Returns:
        str: Unicode character if supported, fallback otherwise

    Examples:
        >>> emoji("🚀", ">>")  # Returns "🚀" on macOS/Linux, ">>" on Windows
        >>> emoji("✓", "[OK]")  # Returns "✓" on macOS/Linux, "[OK]" on Windows
    """
    return unicode_char if USE_EMOJIS else fallback
