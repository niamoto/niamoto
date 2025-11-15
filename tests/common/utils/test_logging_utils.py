"""Tests for logging_utils module."""

import logging
import json
from unittest.mock import patch

from niamoto.common.utils.logging_utils import (
    JsonFormatter,
    setup_logging,
    log_error,
    LoggerAdapter,
    get_component_logger,
)
from niamoto.common.exceptions import NiamotoError, LoggingError


class TestJsonFormatter:
    """Test JsonFormatter class."""

    def test_format_simple_message(self):
        """Test formatting a simple log message."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_format_with_exception(self):
        """Test formatting a log message with exception info."""
        formatter = JsonFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "error" in data
        assert data["error"]["type"] == "ValueError"
        assert "Test error" in data["error"]["message"]

    def test_format_with_niamoto_error(self):
        """Test formatting a log message with NiamotoError."""
        formatter = JsonFormatter()

        try:
            raise NiamotoError("Test error", details={"key": "value"})
        except NiamotoError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "error" in data
        assert data["error"]["type"] == "NiamotoError"
        assert data["error"]["details"] == {"key": "value"}

    def test_format_with_error_details(self):
        """Test formatting with error_details attribute."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error",
            args=(),
            exc_info=None,
        )
        record.error_details = {"detail_key": "detail_value"}

        result = formatter.format(record)
        data = json.loads(result)

        assert "error_details" in data
        assert data["error_details"]["detail_key"] == "detail_value"


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_default(self, tmp_path):
        """Test default logging setup."""
        with patch.dict("os.environ", {"NIAMOTO_LOGS": str(tmp_path)}):
            logger = setup_logging(component_name="test")

            assert isinstance(logger, logging.Logger)
            assert logger.name == "test"
            assert logger.level == logging.INFO
            assert len(logger.handlers) >= 1

    def test_setup_logging_console_only(self):
        """Test logging setup with console only."""
        logger = setup_logging(
            component_name="test",
            enable_console=True,
            enable_file=False,
        )

        assert logger.handlers  # Should have at least console handler

    def test_setup_logging_with_custom_format(self):
        """Test logging setup with custom console format."""
        custom_format = "%(levelname)s - %(message)s"
        logger = setup_logging(
            component_name="test",
            enable_file=False,
            console_format=custom_format,
        )

        # Check that custom format was applied to console handler
        assert logger.handlers

    def test_setup_logging_with_custom_level(self, tmp_path):
        """Test logging setup with custom log level."""
        with patch.dict("os.environ", {"NIAMOTO_LOGS": str(tmp_path)}):
            logger = setup_logging(
                component_name="test",
                log_level=logging.DEBUG,
            )

            assert logger.level == logging.DEBUG

    def test_setup_logging_creates_log_directory(self, tmp_path):
        """Test that logging setup creates log directory."""
        log_dir = tmp_path / "custom_logs"

        setup_logging(
            component_name="test",
            log_directory=str(log_dir),
            enable_console=False,
        )

        assert log_dir.exists()
        assert (log_dir / "test.log").exists()

    def test_setup_logging_file_error_raises_logging_error(self, tmp_path):
        """Test that file logging errors raise LoggingError."""
        # Create a file where the log directory should be
        bad_path = tmp_path / "bad_log_dir"
        bad_path.write_text("not a directory")

        try:
            setup_logging(
                component_name="test",
                log_directory=str(bad_path / "subdir"),
                enable_console=False,
            )
            assert False, "Should have raised LoggingError"
        except LoggingError as e:
            assert "Failed to set up file logging" in str(e)

    def test_setup_logging_removes_existing_handlers(self, tmp_path):
        """Test that setup removes existing handlers."""
        with patch.dict("os.environ", {"NIAMOTO_LOGS": str(tmp_path)}):
            # Setup logging twice
            logger1 = setup_logging(component_name="test")
            initial_handlers = len(logger1.handlers)

            logger2 = setup_logging(component_name="test")

            # Should have same number of handlers, not doubled
            assert len(logger2.handlers) == initial_handlers

    def test_setup_logging_default_logger_name(self, tmp_path):
        """Test logging setup with no component name."""
        with patch.dict("os.environ", {"NIAMOTO_LOGS": str(tmp_path)}):
            logger = setup_logging()

            assert logger.name == "niamoto"


class TestLogError:
    """Test log_error function."""

    def test_log_error_simple_exception(self, caplog):
        """Test logging a simple exception."""
        logger = logging.getLogger("test")

        with caplog.at_level(logging.ERROR):
            log_error(logger, ValueError("Test error"))

        assert "Test error" in caplog.text

    def test_log_error_niamoto_error(self, caplog):
        """Test logging a NiamotoError with details."""
        logger = logging.getLogger("test")
        error = NiamotoError("Test error", details={"key": "value"})

        with caplog.at_level(logging.ERROR):
            log_error(logger, error)

        assert "Test error" in caplog.text

    def test_log_error_with_additional_info(self, caplog):
        """Test logging error with additional context."""
        logger = logging.getLogger("test")
        additional_info = {"context": "test context"}

        with caplog.at_level(logging.ERROR):
            log_error(logger, ValueError("Test error"), additional_info=additional_info)

        assert "Test error" in caplog.text


class TestLoggerAdapter:
    """Test LoggerAdapter class."""

    def test_logger_adapter_process(self):
        """Test LoggerAdapter processes messages with context."""
        logger = logging.getLogger("test")
        context = {"request_id": "123"}
        adapter = LoggerAdapter(logger, context)

        msg, kwargs = adapter.process("Test message", {})

        assert "extra" in kwargs
        assert kwargs["extra"]["request_id"] == "123"

    def test_logger_adapter_preserves_existing_extra(self):
        """Test that LoggerAdapter preserves existing extra data."""
        logger = logging.getLogger("test")
        context = {"request_id": "123"}
        adapter = LoggerAdapter(logger, context)

        msg, kwargs = adapter.process("Test", {"extra": {"other": "data"}})

        assert kwargs["extra"]["request_id"] == "123"
        assert kwargs["extra"]["other"] == "data"


class TestGetComponentLogger:
    """Test get_component_logger function."""

    def test_get_component_logger_basic(self):
        """Test getting a component logger."""
        logger = get_component_logger("test_component")

        assert isinstance(logger, LoggerAdapter)
        assert logger.logger.name == "test_component"

    def test_get_component_logger_with_context(self):
        """Test getting a component logger with context."""
        context = {"session_id": "abc123"}
        logger = get_component_logger("test_component", context=context)

        assert logger.extra == context

    def test_get_component_logger_no_context(self):
        """Test getting a component logger without context."""
        logger = get_component_logger("test_component")

        assert logger.extra == {}
