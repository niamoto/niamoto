"""
Error handling utilities for Niamoto.
"""

import logging
import sys
import os
import traceback
from functools import wraps
from typing import Any, Callable, TypeVar, Optional

from rich.console import Console

from niamoto.common.exceptions import (
    NiamotoError,
    DatabaseError,
    FileError,
    DataImportError,
    DatabaseWriteError,
    DatabaseQueryError,
    CommandError,
    ArgumentError,
    ProcessError,
    CLIError,
    ValidationError,
    TemplateError,
    OutputError,
    CSVError,
    LoggingError,
    DataTransformError,
)

console = Console()
T = TypeVar("T")


def get_error_details(error: Exception) -> dict:
    """
    Extract error details from an exception.

    Args:
        error: The exception to process

    Returns:
        Dictionary containing error details
    """
    details = {"error_type": type(error).__name__, "traceback": traceback.format_exc()}

    if isinstance(error, NiamotoError):
        details.update(error.details or {})

        # Add specific error attributes based on error type
        if isinstance(error, FileError):
            details["file_path"] = error.file_path
        elif isinstance(error, DatabaseError):
            if isinstance(error, DatabaseWriteError):
                details["table_name"] = error.table_name
            elif isinstance(error, DatabaseQueryError):
                details["query"] = error.query
        elif isinstance(error, ValidationError):
            details["field"] = error.field
        elif isinstance(error, TemplateError):
            details["template_name"] = error.template_name
        elif isinstance(error, OutputError):
            details["output_path"] = error.output_path
        elif isinstance(error, CLIError):
            if isinstance(error, CommandError):
                details["command"] = error.command
            elif isinstance(error, ArgumentError):
                details["argument"] = error.argument

    return details


def format_error_message(error: Exception) -> str:
    """
    Format an error message for display.

    Args:
        error: The exception to format

    Returns:
        Formatted error message
    """
    if isinstance(error, FileError):
        return f"File error on {error.file_path}: {str(error)}"
    elif isinstance(error, DatabaseError):
        if isinstance(error, DatabaseWriteError):
            return f"Database write error on table {error.table_name}: {str(error)}"
        elif isinstance(error, DatabaseQueryError):
            return f"Database query error: {str(error)}"
        return f"Database error: {str(error)}"
    elif isinstance(error, ValidationError):
        return f"Validation error for {error.field}: {str(error)}"
    elif isinstance(error, TemplateError):
        return f"Template error in {error.template_name}: {str(error)}"
    elif isinstance(error, OutputError):
        return f"Output error for {error.output_path}: {str(error)}"
    elif isinstance(error, CLIError):
        if isinstance(error, CommandError):
            return f"Command error ({error.command}): {str(error)}"
        elif isinstance(error, ArgumentError):
            return f"Argument error ({error.argument}): {str(error)}"
        return f"CLI error: {str(error)}"
    elif isinstance(error, DataImportError):
        return f"Import error: {str(error)}"
    elif isinstance(error, ProcessError):
        return f"Statistics error: {str(error)}"
    elif isinstance(error, CSVError):
        return f"CSV error in {error.file_path}: {str(error)}"
    elif isinstance(error, LoggingError):
        return f"Logging error: {str(error)}"

    return f"Error ({type(error).__name__}): {str(error)}"


def handle_error(
    error: Exception,
    log: bool = True,
    raise_error: bool = True,
    console_output: bool = True,
) -> None:
    """
    Central error handler for standardized error processing.

    Args:
        error: The exception to handle
        log: Whether to log the error
        raise_error: Whether to re-raise the error
        console_output: Whether to output to console
    """
    # Check if this error has already been handled (to avoid duplicate output)
    if hasattr(error, "_handled") and error._handled:
        if raise_error:
            raise error
        return

    # Mark error as handled
    error._handled = True

    # Get error message - use get_user_message if available
    if hasattr(error, "get_user_message") and callable(
        getattr(error, "get_user_message")
    ):
        error_message = error.get_user_message()
    else:
        error_message = str(error)

    # Log error if requested
    if log:
        # Only log full traceback for unexpected errors
        if isinstance(error, NiamotoError):
            logging.error("Error: %s", error_message)
        else:
            logging.error("Unexpected error: %s", error_message, exc_info=True)

    # Console output if requested
    if console_output:
        # For DataTransformError, use a more contextual message
        if isinstance(error, DataTransformError):
            console.print(f"[yellow]⚠ {error_message}[/yellow]")
        else:
            console.print(f"[red]✗ {error_message}[/red]")

    # Re-raise if requested, but avoid cascade
    if raise_error:
        # If we're in a CLI context, we might want to exit the program
        # But for library code and tests, we should just raise the exception

        is_test_environment = "PYTEST_CURRENT_TEST" in os.environ

        if isinstance(error, NiamotoError) and not is_test_environment:
            # Only exit in CLI context, not during tests
            # sys.exit(1)
            raise error
        elif isinstance(error, NiamotoError):
            # In test environment, just re-raise the original error
            raise error
        else:
            # For non-NiamotoError, wrap it in a ProcessError
            raise ProcessError(str(error), details={"original_error": str(error)})


def error_handler(
    *, log: bool = True, raise_error: bool = True, console_output: bool = True
) -> Callable:
    """
    Decorator for standardized error handling.

    Keyword Arguments:
        log (bool): Whether to log errors. Defaults to True.
        raise_error (bool): Whether to re-raise errors. Defaults to True.
        console_output (bool): Whether to output to console. Defaults to True.

    Returns:
        Callable: Decorator function that wraps the target function with error handling.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        """
        Decorator function
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            """
            Wrapped function
            """
            try:
                return func(*args, **kwargs)
            except (NiamotoError, ValueError, OSError) as e:
                handle_error(
                    e, log=log, raise_error=raise_error, console_output=console_output
                )
                return None if not raise_error else None

        return wrapper

    return decorator


def setup_global_exception_handler() -> None:
    """
    Set up global exception handler for unhandled exceptions.
    """

    def global_exception_handler(
        exc_type: type, exc_value: Exception, exc_traceback: Any
    ) -> None:
        """
        Global exception handler for unhandled exceptions.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Call the default handler for keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        handle_error(exc_value, log=True, raise_error=False, console_output=True)

    # Set the custom handler as the default
    sys.excepthook = global_exception_handler
