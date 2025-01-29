"""
Logging utilities for Niamoto application.
"""

import os
from pathlib import Path
import logging
from logging import LogRecord
import json
from typing import Optional, Dict, Any, Union
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install as install_rich_traceback

from niamoto.common.exceptions import LoggingError, NiamotoError
from niamoto.common.utils import error_handler

# Install rich traceback handler for better exception formatting
install_rich_traceback()


class JsonFormatter(logging.Formatter):
    """
    Formats log records as JSON strings with support for NiamotoError details.
    """

    def format(self, record: LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record: The log record to format

        Returns:
            Formatted JSON string
        """
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add error information if present
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            log_data["error"] = {"type": exc_type.__name__, "message": str(exc_value)}
            # Add extra details for NiamotoError
            if isinstance(exc_value, NiamotoError) and exc_value.details:
                log_data["error"]["details"] = exc_value.details

        # Add any extra fields
        if hasattr(record, "error_details"):
            log_data["error_details"] = record.error_details

        return json.dumps(log_data)


@error_handler(log=False)  # Don't log logging setup errors to avoid recursion
def setup_logging(
    component_name: Optional[str] = None,
    log_directory: Optional[str] = None,
    log_level: int = logging.INFO,
    enable_console: bool = True,
    enable_file: bool = True,
    console_format: Optional[str] = None,
) -> logging.Logger:
    """
    Set up logging configuration for a component.

    Args:
        component_name: Name of the component (affects log file name)
        log_directory: Directory for log files (defaults to NIAMOTO_LOGS or 'logs')
        log_level: Logging level to use
        enable_console: Whether to enable console output
        enable_file: Whether to enable file logging
        console_format: Optional format for console output

    Returns:
        Configured logger instance

    Raises:
        LoggingError: If there's an error setting up logging
    """
    try:
        # Get or create logger
        logger_name = component_name if component_name else "niamoto"
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)

        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        handlers = []

        # Configure console handler with Rich if enabled
        if enable_console:
            console_handler = RichHandler(
                rich_tracebacks=True,
                console=Console(stderr=True),
                show_time=True,
                show_path=True,
            )
            if console_format:
                console_handler.setFormatter(logging.Formatter(console_format))
            console_handler.setLevel(log_level)
            handlers.append(console_handler)

        # Configure file handler if enabled
        if enable_file:
            log_dir = log_directory or os.getenv("NIAMOTO_LOGS", "logs")
            try:
                log_path = Path(log_dir)
                log_path.mkdir(parents=True, exist_ok=True)

                file_path = log_path / f"{logger_name.lower()}.log"
                file_handler = logging.FileHandler(str(file_path))
                file_handler.setFormatter(JsonFormatter())
                file_handler.setLevel(log_level)
                handlers.append(file_handler)

            except OSError as e:
                raise LoggingError(
                    f"Failed to set up file logging in {log_dir}",
                    details={"error": str(e), "directory": log_dir},
                )

        # Add all handlers to logger
        for handler in handlers:
            logger.addHandler(handler)

        return logger

    except Exception as e:
        if isinstance(e, LoggingError):
            raise
        raise LoggingError(
            "Failed to setup logging",
            details={"error": str(e), "component": component_name},
        )


def log_error(
    logger: logging.Logger,
    error: Union[Exception, NiamotoError],
    additional_info: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an error with additional context information.

    Args:
        logger: Logger instance to use
        error: Exception to log
        additional_info: Additional context information

    This method ensures proper handling of NiamotoError details and
    additional context information.
    """
    error_info = {"error_type": type(error).__name__, "error_message": str(error)}

    # Add details from NiamotoError
    if isinstance(error, NiamotoError):
        error_info["details"] = error.details

    # Add any additional context
    if additional_info:
        error_info["additional_info"] = additional_info

    logger.error(str(error), extra={"error_details": error_info}, exc_info=True)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter that adds context information to log records.
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """
        Process the logging message and keywords arguments.

        Args:
            msg: Log message
            kwargs: Keyword arguments

        Returns:
            Tuple of processed message and kwargs
        """
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"].update(self.extra)
        return msg, kwargs


def get_component_logger(
    component_name: str, context: Optional[Dict[str, Any]] = None
) -> logging.LoggerAdapter:
    """
    Get a logger for a specific component with optional context information.

    Args:
        component_name: Name of the component
        context: Optional context information to add to all log messages

    Returns:
        Logger adapter instance

    This is the recommended way to get a logger for a component as it ensures
    proper context information is added to all log messages.
    """
    logger = logging.getLogger(component_name)
    return LoggerAdapter(logger, context or {})
