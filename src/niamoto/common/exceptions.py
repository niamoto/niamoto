"""
Custom exceptions for the Niamoto application.
"""

from typing import Optional, Any


class NiamotoError(Exception):
    """Base exception class for all Niamoto errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        """
        Initialize the base exception.

        Args:
            message: Main error message
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.details = details or {}

    def get_user_message(self) -> str:
        """Returns a user-friendly error message"""
        return str(self)


class CLIError(NiamotoError):
    """Base class for CLI related errors."""

    pass


class CommandError(CLIError):
    """Raised when a command fails to execute."""

    def __init__(self, command: str, message: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.command = command


class ArgumentError(CLIError):
    """Raised when command arguments are invalid."""

    def __init__(self, argument: str, message: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.argument = argument


class VersionError(CLIError):
    """Raised when version information cannot be retrieved."""

    pass


class LoggingError(NiamotoError):
    """Exception raised for logging configuration and handling errors."""

    pass


class InputError(NiamotoError):
    """Exception raised for errors in input data."""

    pass


class FileError(NiamotoError):
    """Base class for file related errors."""

    def __init__(self, file_path: str, message: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.file_path = file_path


class FileReadError(FileError):
    """Exception raised when there is an error reading a file."""

    pass


class FileWriteError(FileError):
    """Exception raised when there is an error writing a file."""

    pass


class FileFormatError(FileError):
    """Exception raised when file format is invalid."""

    pass


class CSVError(FileError):
    """Exception raised for CSV-specific errors."""

    pass


class DatabaseError(NiamotoError):
    """Base class for database related errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, details)


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""

    pass


class DatabaseWriteError(DatabaseError):
    """Exception raised when writing to database fails."""

    def __init__(self, table_name: str, message: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.table_name = table_name


class DatabaseQueryError(DatabaseError):
    """Exception raised when a database query fails."""

    def __init__(self, query: str, message: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.query = query


class TransactionError(DatabaseError):
    """Exception raised for transaction-related errors."""

    pass


class DataValidationError(NiamotoError):
    """Exception raised for data validation errors."""

    def __init__(self, message: str, validation_errors: list[dict[str, Any]]):
        super().__init__(message, {"validation_errors": validation_errors})
        self.validation_errors = validation_errors


class ConfigurationError(NiamotoError):
    """Exception raised for configuration errors."""

    def __init__(self, config_key: str, message: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.config_key = config_key

    def get_user_message(self) -> str:
        """Returns a user-friendly error message with details if available"""
        message = f"{str(self)} (configuration key: {self.config_key})"

        # Add help message if available
        if self.details and "help" in self.details:
            message += f"\n{self.details['help']}"
        # Add available groups if present
        elif self.details and "available_groups" in self.details:
            groups = ", ".join(self.details["available_groups"])
            message += f"\nAvailable groups: {groups}"

        return message


class EnvironmentSetupError(NiamotoError):
    """Exception raised for environment setup and configuration issues."""

    pass


class DataImportError(NiamotoError):
    """Base class for import related errors."""

    pass


class TaxonomyImportError(DataImportError):
    """Exception raised for taxonomy import errors."""

    pass


class OccurrenceImportError(DataImportError):
    """Exception raised for occurrence import errors."""

    pass


class PlotImportError(DataImportError):
    """Exception raised for plot import errors."""

    pass


class ShapeImportError(DataImportError):
    """Exception raised for shape import errors."""

    pass


class GenerationError(NiamotoError):
    """Base class for content generation errors."""

    pass


class TemplateError(GenerationError):
    """Exception raised for template processing errors."""

    def __init__(
        self, template_name: str, message: str, details: Optional[dict] = None
    ):
        super().__init__(message, details)
        self.template_name = template_name


class OutputError(GenerationError):
    """Exception raised for file generation and output errors."""

    def __init__(self, output_path: str, message: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.output_path = output_path


class ProcessError(NiamotoError):
    """Base class for transforms calculation errors."""

    def get_user_message(self) -> str:
        """Returns a user-friendly error message with details if available"""
        message = str(self)

        # If we have details, add them to the message
        if self.details:
            # Add original error if it's informative
            if "error" in self.details and isinstance(self.details["error"], str):
                original_error = self.details["error"]
                if "No configuration found for group" in original_error:
                    # Extract the group name from the original error
                    import re

                    match = re.search(r"group: (\w+)", original_error)
                    if match and match.group(1):
                        group_name = match.group(1)
                        message += f"\nGroup '{group_name}' not found."

            # Add available groups if present
            if "available_groups" in self.details:
                groups = self.details["available_groups"]
                message += f"\nAvailable groups: {', '.join(groups)}"

                # Add suggestion if we have a group name
                if "group" in self.details and groups:
                    group_name = self.details["group"]
                    import difflib

                    matches = difflib.get_close_matches(group_name, groups, n=1)
                    if matches:
                        message += f"\nDid you mean '{matches[0]}'?"

        return message


class CalculationError(ProcessError):
    """Exception raised for mathematical calculation errors."""

    pass


class DataTransformError(ProcessError):
    """Exception raised for errors during data processing for transforms."""

    pass


class CLIError(NiamotoError):
    """Base class for CLI related errors."""

    pass


class ValidationError(NiamotoError):
    """Exception raised for validation errors."""

    def __init__(self, field: str, message: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.field = field


class DataLoadError(NiamotoError):
    """Raised when there is an error loading data."""

    pass
