"""
This test module contains the unit test for the main entry point of the Niamoto application.

The test verifies that the main function properly invokes the CLI interface when
the application is executed directly, ensuring the integration between the main entry point
and the command-line interface is functioning as expected.
"""

from unittest import mock

from niamoto.main import main


def test_main_calls_cli() -> None:
    """Test to ensure the main entry point calls the CLI function.

    This test checks if the `main` function in the `main.py` module
    correctly calls the `cli` function from the `niamoto.cli.commands`
    module when executed.
    """
    with mock.patch("niamoto.main.cli") as mock_cli:
        # Call the main function which should in turn call the cli function
        main()
        # Assert that cli function was called exactly once
        mock_cli.assert_called_once()
