"""
Main CLI package for Niamoto.
"""

import sys
import os

from .commands import create_cli

# Suppress tracebacks by default unless DEBUG is explicitly enabled
# Users can enable with: export NIAMOTO_DEBUG=1
if os.environ.get("NIAMOTO_DEBUG") != "1":

    def _clean_exception_hook(exc_type, exc_value, exc_traceback):
        """
        Custom exception hook that suppresses traceback chains.
        Errors are already displayed by error_handler.py, so we suppress
        the default Python traceback output entirely.
        """
        # Allow KeyboardInterrupt to work normally
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # For all other exceptions, suppress output
        # (the error message has already been displayed by error_handler.py)
        pass

    sys.excepthook = _clean_exception_hook

# Create the CLI instance that will be used as the entry point
cli = create_cli()

__all__ = ["cli"]
