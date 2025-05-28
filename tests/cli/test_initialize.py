"""Tests for the initialize commands in the Niamoto CLI."""

import os
from unittest import mock
import pytest
from click.testing import CliRunner

from niamoto.cli.commands.initialize import init_environment
from niamoto.common.exceptions import (
    EnvironmentSetupError,
)


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


def test_successful_init(runner):
    """Test successful environment initialization."""
    with runner.isolated_filesystem():
        with mock.patch("niamoto.cli.commands.initialize.Config") as mock_config:
            # Mock Config.get_niamoto_home to return current directory
            mock_config.get_niamoto_home.return_value = os.getcwd()

            # Mock Environment to avoid actual initialization
            with mock.patch("niamoto.cli.commands.initialize.Environment") as mock_env:
                mock_env.return_value.initialize.return_value = None

                result = runner.invoke(init_environment, [])

                assert result.exit_code == 0
                assert "Environment initialized successfully" in result.output
                mock_env.return_value.initialize.assert_called_once()


def test_config_dir_error(runner):
    """Test error when accessing config directory."""
    with runner.isolated_filesystem():
        with mock.patch("niamoto.cli.commands.initialize.Config") as mock_config:
            mock_config.get_niamoto_home.side_effect = EnvironmentSetupError(
                message="Failed to get config directory",
                details={"error": "Permission denied"},
            )

            result = runner.invoke(init_environment, [])

            assert result.exit_code == 1
            assert "Failed to get config directory" in result.output


def test_init_environment_error(runner):
    """Test error during environment initialization."""
    with runner.isolated_filesystem():
        with mock.patch("niamoto.cli.commands.initialize.Config") as mock_config:
            mock_config.get_niamoto_home.return_value = os.getcwd()

            with mock.patch("niamoto.cli.commands.initialize.Environment") as mock_env:
                mock_env.return_value.initialize.side_effect = EnvironmentSetupError(
                    message="Failed to initialize environment",
                    details={"error": "Database error"},
                )

                result = runner.invoke(init_environment, [])

                assert result.exit_code == 1
                assert "Failed to initialize environment" in result.output


def test_reset_cancelled(runner):
    """Test cancelling reset operation."""
    with runner.isolated_filesystem():
        # Create config directory to simulate existing environment
        os.makedirs("config")

        with mock.patch("niamoto.cli.commands.initialize.Config") as mock_config:
            mock_config.get_niamoto_home.return_value = os.getcwd()

            # Simulate user input 'n' to cancel reset
            result = runner.invoke(init_environment, ["--reset"], input="n\n")

            assert result.exit_code == 0
            assert "Environment reset cancelled by user" in result.output
