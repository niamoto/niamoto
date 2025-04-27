"""
This test module contains the unit test for the main entry point of the Niamoto application.

The test verifies that the main function properly invokes the CLI interface when
the application is executed directly, ensuring the integration between the main entry point
and the command-line interface is functioning as expected.
"""

import os
from unittest import mock
import pytest

from niamoto.main import main


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
