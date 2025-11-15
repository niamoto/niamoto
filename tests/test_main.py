"""
This test module contains the unit test for the main entry point of the Niamoto application.

The test verifies that the main function properly invokes the CLI interface when
the application is executed directly, ensuring the integration between the main entry point
and the command-line interface is functioning as expected.
"""

import os
import sys
from unittest import mock
import pytest

from niamoto.main import main, init_logging
from niamoto.common.exceptions import NiamotoError


def test_main_calls_cli(tmp_path):
    """Test to ensure the main entry point calls the CLI function."""
    # Mock the logging setup functions and the CLI creation
    with (
        mock.patch("niamoto.main.init_logging") as mock_init_logging,
        mock.patch("niamoto.main.setup_global_exception_handler") as mock_setup_handler,
        mock.patch("niamoto.main.create_cli") as mock_cli,
    ):
        # Mock the CLI to raise SystemExit(0) when called
        mock_cli.return_value = mock.MagicMock(side_effect=SystemExit(0))

        # Call the main function
        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 0  # Verify that the exit code is 0 (success)

        # Assert that logging and CLI functions were called exactly once
        mock_init_logging.assert_called_once()
        mock_setup_handler.assert_called_once()
        mock_cli.assert_called_once()

    # Verify that no 'logs' directory was created in the project root
    # (tmp_path is used implicitly by pytest for test isolation, checking cwd is sufficient here)
    assert not os.path.exists(os.path.join(os.getcwd(), "logs"))


def test_main_handles_niamoto_error_with_details():
    """Test main function handles NiamotoError with details."""
    with mock.patch("niamoto.main.init_logging"):
        with mock.patch("niamoto.main.setup_global_exception_handler"):
            with mock.patch("niamoto.main.create_cli") as mock_create_cli:
                with mock.patch("niamoto.main.console") as mock_console:
                    # Create an error with details
                    error = NiamotoError(
                        "Test error", details={"key1": "value1", "key2": "value2"}
                    )
                    mock_cli = mock.MagicMock()
                    mock_cli.side_effect = error
                    mock_create_cli.return_value = mock_cli

                    with pytest.raises(SystemExit) as excinfo:
                        main()

                    assert excinfo.value.code == 1
                    # Verify error message was printed
                    assert mock_console.print.called


def test_main_handles_niamoto_error_without_details():
    """Test main function handles NiamotoError without details."""
    with mock.patch("niamoto.main.init_logging"):
        with mock.patch("niamoto.main.setup_global_exception_handler"):
            with mock.patch("niamoto.main.create_cli") as mock_create_cli:
                with mock.patch("niamoto.main.console") as mock_console:
                    # Create an error without details
                    error = NiamotoError("Test error")
                    mock_cli = mock.MagicMock()
                    mock_cli.side_effect = error
                    mock_create_cli.return_value = mock_cli

                    with pytest.raises(SystemExit) as excinfo:
                        main()

                    assert excinfo.value.code == 1
                    assert mock_console.print.called


def test_main_handles_generic_exception():
    """Test main function handles generic exceptions."""
    with mock.patch("niamoto.main.init_logging"):
        with mock.patch("niamoto.main.setup_global_exception_handler"):
            with mock.patch("niamoto.main.create_cli") as mock_create_cli:
                with mock.patch("niamoto.main.console") as mock_console:
                    mock_cli = mock.MagicMock()
                    mock_cli.side_effect = RuntimeError("Generic error")
                    mock_create_cli.return_value = mock_cli

                    with pytest.raises(SystemExit) as excinfo:
                        main()

                    assert excinfo.value.code == 1
                    assert mock_console.print.called


def test_main_debug_mode_shows_traceback():
    """Test that debug mode shows full traceback."""
    with mock.patch("niamoto.main.init_logging"):
        with mock.patch("niamoto.main.setup_global_exception_handler"):
            with mock.patch("niamoto.main.create_cli") as mock_create_cli:
                with mock.patch("niamoto.main.console") as mock_console:
                    with mock.patch.object(sys, "argv", ["niamoto", "--debug"]):
                        mock_cli = mock.MagicMock()
                        mock_cli.side_effect = RuntimeError("Debug error")
                        mock_create_cli.return_value = mock_cli

                        with pytest.raises(SystemExit) as excinfo:
                            main()

                        assert excinfo.value.code == 1
                        # Verify print_exception was called in debug mode
                        mock_console.print_exception.assert_called_once()


def test_init_logging_success():
    """Test successful logging initialization."""
    with mock.patch("niamoto.main.setup_logging") as mock_setup:
        init_logging()
        mock_setup.assert_called_once()


def test_init_logging_handles_exception():
    """Test that init_logging handles exceptions gracefully."""
    with mock.patch("niamoto.main.setup_logging") as mock_setup:
        mock_setup.side_effect = Exception("Setup failed")
        # error_handler decorator should catch and handle the exception
        result = init_logging()
        # Due to error_handler(raise_error=False), it returns None
        assert result is None
