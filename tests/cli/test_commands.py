"""
test_commands.py

This module contains tests for the command-line interface (CLI) commands defined in commands.py of the Niamoto application.
These tests verify that each CLI command behaves as expected when invoked from the command line.
The Click library is used to create a test CLI runner that simulates command line calls within the test environment.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from typing import Any
from niamoto.cli.commands import cli, import_data


@pytest.fixture  # type: ignore
def runner() -> Any:
    """Fixture that returns a Click CLI runner to invoke CLI commands."""
    return CliRunner()


def test_cli_group(runner: Any) -> Any:
    """
    Test the CLI group for existence and its response to invocation.

    Ensures that the main CLI command group can be invoked without errors.
    """
    result = runner.invoke(cli)
    assert result.exit_code == 0


def test_init_command_without_reset():
    """
    Test the 'init' command without the reset option.

    This test checks if the 'init' command completes successfully and
    performs the expected actions such as creating the configuration file
    and initializing the database.
    """
    runner = CliRunner()
    os.chdir(os.path.join(os.getcwd(), "tests", "test_data"))

    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0


def test_init_command_with_reset(runner):
    """
    Test the 'init' command with the --reset option.

    This test checks if the 'init' command with the --reset flag successfully resets the environment.
    It verifies that the command completes successfully and performs the expected actions such as
    deleting and recreating the configuration file and resetting the database and other resources.
    """
    # Setup: Create an initial environment that the reset command will modify
    # This could include creating a dummy configuration file, database file, etc.
    # Example:
    runner = CliRunner()

    # Run the init command with the --reset option
    result = runner.invoke(cli, ["init", "--reset"])
    assert result.exit_code == 0

    # Check if the reset effects have taken place
    # Example checks (modify these to suit your application's behavior):
    # Check if the configuration file has been recreated
    expected_config_path = "config/niamoto_config.toml"
    assert os.path.exists(expected_config_path)

    # Check if the database has been reset (if applicable)
    db_path = "data/db/niamoto.db"
    assert os.path.exists(db_path)


@patch("niamoto.cli.commands.ConfigManager")
@patch("niamoto.cli.commands.import_csv_data")
def test_import_data(mock_import_csv_data, mock_config_manager):
    # Créez une instance mock pour ConfigManager
    mock_config_manager_instance = MagicMock()
    mock_config_manager.return_value = mock_config_manager_instance
    mock_config_manager_instance.get.return_value = "mock_db_path"

    # Définissez les arguments à passer à la fonction
    mock_csvfile = "mock_csvfile"
    mock_table_name = "mock_table_name"

    # Créez un objet CliRunner
    runner = CliRunner()

    # Appellez la fonction avec les arguments mock
    result = runner.invoke(import_data, [mock_csvfile, mock_table_name])

    # Vérifiez si get a été appelé sur l'instance de ConfigManager
    mock_config_manager_instance.get.assert_called_once_with("database", "path")

    # Vérifiez si import_csv_data a été appelé avec les bons arguments
    mock_import_csv_data.assert_called_once_with(
        mock_csvfile, mock_table_name, "mock_db_path"
    )

    # Vérifiez que la commande s'est terminée sans erreur
    assert result.exit_code == 0


# Note: If this test suite grows, consider adding more granular tests for edge cases and error handling.
