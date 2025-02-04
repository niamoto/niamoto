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
    # Mock the setup_logging function
    with mock.patch("niamoto.main.setup_logging") as mock_setup_logging:
        # Mock the create_cli function
        with mock.patch("niamoto.main.create_cli") as mock_cli:
            # Mock the CLI to raise SystemExit(0) when called
            mock_cli.return_value = mock.MagicMock(side_effect=SystemExit(0))

            # Call the main function
            with pytest.raises(SystemExit) as excinfo:
                main()

            assert excinfo.value.code == 0  # Verify that the exit code is 0 (success)

            # Assert that cli function was called exactly once
            mock_cli.assert_called_once()

            # Assert that setup_logging was called
            mock_setup_logging.assert_called_once()

    # Verify that no 'logs' directory was created in the project root
    assert not os.path.exists(os.path.join(os.getcwd(), "logs"))
