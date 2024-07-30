"""
This module contains utility functions for setting up logging for the application.
"""
import logging
import os
import sys
from logging import LogRecord
from typing import Optional


class CustomFilter(logging.Filter):
    """
    A custom logging filter that suppresses specific warnings.
    """

    def filter(self, record: LogRecord) -> bool:
        """
        Filter log records based on specific messages.
        Args:
            record (LogRecord): The log record to filter.

        Returns:
            bool: True if the record should be logged, False otherwise.

        """
        return not any(
            msg in record.getMessage()
            for msg in [
                "Empty GeoDataFrame",
                "No data found within the shape",
                "does not overlap with raster",
                "Expecting property name enclosed in double quotes",
            ]
        )


def setup_logging(
    log_directory: str = "logs", component_name: Optional[str] = None
) -> logging.Logger:
    """
    Set up the custom logging filter to suppress specific warnings and configure file logging.

    Args:
        log_directory (str): The directory where log files will be stored.
        component_name (str): The name of the component (e.g., 'shapes', 'plots', 'occurrences', 'taxonomy').

    Returns:
        logging.Logger: A logger configured for the specified component.
    """
    # Ensure the log directory exists
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Define the log file path
    log_file_name = f"{component_name}.log" if component_name else "application.log"
    log_file_path = os.path.join(log_directory, log_file_name)

    # Create a logger for the component
    logger = (
        logging.getLogger(component_name) if component_name else logging.getLogger()
    )
    logger.setLevel(logging.INFO)

    # Create a file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )

    # Add the custom filter to the logger
    logger.addFilter(CustomFilter())

    # Add the file handler to the logger
    logger.addHandler(file_handler)

    # Configure root logger to capture all logs
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers from the root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add the file handler to the root logger
    root_logger.addHandler(file_handler)

    # Optionally, add a StreamHandler for console output of errors
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Suppress specific warnings (keep your existing code for this)
    fiona_logger = logging.getLogger("fiona")
    fiona_logger.setLevel(logging.WARNING)
    fiona_logger.addFilter(CustomFilter())

    return logger
