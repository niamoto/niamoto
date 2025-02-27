"""
Tests for error handling utilities.
"""

import pytest
from unittest.mock import patch
from niamoto.common.utils.error_handler import (
    error_handler,
    handle_error,
    get_error_details,
    format_error_message,
)
from niamoto.common.exceptions import (
    FileError,
    DatabaseError,
    ValidationError,
    CommandError,
)


def test_error_handler_decorator_with_logging():
    """Test error_handler decorator with logging enabled."""

    @error_handler(log=True, raise_error=False)
    def failing_function():
        raise ValueError("Test error")

    with patch("logging.error") as mock_log:
        failing_function()
        mock_log.assert_called_once()


def test_error_handler_decorator_with_raise():
    """Test error_handler decorator with raise_error enabled."""

    @error_handler(log=False, raise_error=True)
    def failing_function():
        raise ValueError("Test error")

    # ValueError will be wrapped in Exception
    with pytest.raises(Exception):
        failing_function()


def test_error_handler_decorator_without_raise():
    """Test error_handler decorator with raise_error disabled."""

    @error_handler(log=False, raise_error=False)
    def failing_function():
        raise ValueError("Test error")
        return True

    result = failing_function()
    assert result is None


def test_get_error_details_niamoto_error():
    """Test get_error_details with NiamotoError."""
    error = FileError("/test/path", "Test error", {"extra": "info"})
    details = get_error_details(error)

    assert details["error_type"] == "FileError"
    assert "traceback" in details
    assert details["file_path"] == "/test/path"
    assert details["extra"] == "info"


def test_get_error_details_standard_error():
    """Test get_error_details with standard Python error."""
    error = ValueError("Test error")
    details = get_error_details(error)

    assert details["error_type"] == "ValueError"
    assert "traceback" in details


def test_format_error_message():
    """Test format_error_message for different error types."""
    # Test FileError
    error = FileError("/test/path", "Test error")
    assert "File error on /test/path" in format_error_message(error)

    # Test DatabaseError
    error = DatabaseError("Test error")
    assert "Database error: Test error" in format_error_message(error)

    # Test ValidationError
    error = ValidationError("test_field", "Test error")
    assert "Validation error for test_field" in format_error_message(error)

    # Test standard error
    error = ValueError("Test error")
    assert "Error (ValueError): Test error" in format_error_message(error)


def test_handle_error_with_console():
    """Test handle_error with console output."""
    error = ValidationError("test_field", "Test error", {"detail": "value"})

    with patch("rich.console.Console.print") as mock_print:
        handle_error(error, log=False, raise_error=False, console_output=True)
        assert mock_print.call_count >= 1


@patch("logging.error")
def test_handle_error_with_logging(mock_log):
    """Test handle_error with logging."""
    error = DatabaseError("Test error")
    handle_error(error, log=True, raise_error=False, console_output=False)
    mock_log.assert_called_once()


def test_handle_error_with_raise():
    """Test handle_error with raise_error enabled."""
    error = CommandError("test_cmd", "Test error")

    # NiamotoError will be re-raised in test environment
    with pytest.raises(CommandError):
        handle_error(error, log=False, raise_error=True, console_output=False)


def test_error_handler_decorator_return_value():
    """Test error_handler decorator preserves return value."""

    @error_handler(log=False, raise_error=False)
    def successful_function():
        return "success"

    result = successful_function()
    assert result == "success"


def test_error_handler_decorator_with_args():
    """Test error_handler decorator with function arguments."""

    @error_handler(log=False, raise_error=False)
    def function_with_args(arg1, arg2=None):
        if arg2 is None:
            raise ValueError("arg2 is required")
        return f"{arg1}-{arg2}"

    # Test successful case
    result = function_with_args("test", arg2="value")
    assert result == "test-value"

    # Test error case
    result = function_with_args("test")
    assert result is None
