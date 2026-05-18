"""
Main CLI package for Niamoto.
"""

import os
import sys

from .commands import create_cli


def _clean_exception_hook(exc_type, exc_value, exc_traceback):
    """
    Custom exception hook that suppresses traceback chains for handled errors.
    Unexpected errors still get a concise fallback message.
    """
    # Allow KeyboardInterrupt to work normally
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Errors routed through error_handler.py have already been displayed.
    if getattr(exc_value, "_handled", False):
        return

    print(f"Error ({exc_type.__name__}): {exc_value}", file=sys.stderr)


# Create the CLI instance that will be used as the entry point
cli = create_cli()

# Suppress tracebacks by default unless DEBUG is explicitly enabled
# Users can enable with: export NIAMOTO_DEBUG=1
if os.environ.get("NIAMOTO_DEBUG") != "1":
    sys.excepthook = _clean_exception_hook

__all__ = ["cli"]
