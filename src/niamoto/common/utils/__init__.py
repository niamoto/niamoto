"""
Common utilities for Niamoto.
"""

from .error_handler import (
    error_handler,
    handle_error,
    setup_global_exception_handler,
    get_error_details,
    format_error_message,
)

__all__ = [
    "error_handler",
    "handle_error",
    "setup_global_exception_handler",
    "get_error_details",
    "format_error_message",
]
