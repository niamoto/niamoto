"""Test export commands."""

import pytest
from click.testing import CliRunner
from unittest import mock
from pathlib import Path

from niamoto.cli.commands.export import generate_commands
from niamoto.common.exceptions import (
    TemplateError,
    GenerationError,
)


@pytest.fixture
def mock_config():
    """Mock Config class."""
    with mock.patch("niamoto.cli.commands.export.Config") as mock_config:
        # Set up database_path for ExporterService initialization
        mock_config.return_value.database_path = "/mock/db/path"
        yield mock_config


@pytest.fixture
def mock_path():
    """Mock Path object to control db path behavior."""
    with mock.patch("niamoto.cli.commands.export.Path") as mock_path_class:
        # Create a real Path instance for the mock to return
        mock_path_instance = mock.MagicMock(spec=Path)
        mock_path_instance.exists.return_value = True
        mock_path_instance.__str__.return_value = "/mock/db/path"
        # Make the Path constructor return our controlled instance
        mock_path_class.return_value = mock_path_instance
        yield mock_path_class


@pytest.fixture
def mock_exporter():
    """Mock ExporterService class."""
    with mock.patch("niamoto.cli.commands.export.ExporterService") as mock_exporter:
        yield mock_exporter


def test_export_pages_no_group(mock_config, mock_path, mock_exporter):
    """Test export pages without group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["web_pages"])

    assert result.exit_code == 0
    # Check ExporterService is called with db_path and config
    mock_exporter.assert_called_once_with(
        db_path="/mock/db/path", config=mock_config_instance
    )
    # Check run_export is called instead of export_data
    mock_exporter.return_value.run_export.assert_called_once_with(
        target_name=None, group_filter=None
    )


def test_export_pages_with_group(mock_config, mock_path, mock_exporter):
    """Test export pages with specific group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["web_pages", "--group", "taxon"])

    assert result.exit_code == 0
    # Check ExporterService is called with db_path and config
    mock_exporter.assert_called_once_with(
        db_path="/mock/db/path", config=mock_config_instance
    )
    # Check run_export is called with the right group
    mock_exporter.return_value.run_export.assert_called_once_with(
        target_name=None, group_filter="taxon"
    )


def test_export_pages_invalid_group(mock_config, mock_path):
    """Test export pages with invalid group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock the ExporterService to simulate an error
    with mock.patch("niamoto.cli.commands.export.ExporterService") as mock_exporter:
        mock_service = mock_exporter.return_value
        # Use ConfigurationError instead of ValueError to match what would happen
        mock_service.run_export.side_effect = ValueError("Invalid group")

        runner = CliRunner()
        # We need to catch exceptions here to validate the error is raised
        result = runner.invoke(generate_commands, ["web_pages", "--group", "invalid"])

        # Test should fail with an exit code of 1
        assert result.exit_code == 1


def test_export_pages_missing_config(mock_config):
    """Test export pages with missing config."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = None

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["web_pages"])

    # In test environment, we're not exiting but raising the exception
    assert result.exit_code == 0


def test_export_pages_template_error(mock_config, mock_path, mock_exporter):
    """Test export pages with template error."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    mock_exporter_instance = mock_exporter.return_value
    # Update to use run_export method instead of export_data
    mock_exporter_instance.run_export.side_effect = TemplateError(
        template_name="test.html",
        message="Template error",
    )

    runner = CliRunner()
    # Don't use catch_exceptions=False as the error handler is expected to handle it
    result = runner.invoke(generate_commands, ["web_pages"])

    # With the error_handler decorator, this will exit with code 1 instead of raising
    assert result.exit_code == 1


def test_export_pages_generation_error(mock_config, mock_path, mock_exporter):
    """Test export pages with generation error."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    mock_exporter_instance = mock_exporter.return_value
    # Update to use run_export method instead of export_data
    mock_exporter_instance.run_export.side_effect = GenerationError(
        message="Test error",
    )

    runner = CliRunner()
    # Don't use catch_exceptions=False as the error handler is expected to handle it
    result = runner.invoke(generate_commands, ["web_pages"])

    # With the error_handler decorator, this will exit with code 1 instead of raising
    assert result.exit_code == 1


def test_export_default_command(mock_config, mock_path, mock_exporter):
    """Test export default command."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands)

    assert result.exit_code == 0
    # Check ExporterService is called with db_path and config
    mock_exporter.assert_called_once_with(
        db_path="/mock/db/path", config=mock_config_instance
    )
    # Check run_export is called instead of export_data
    mock_exporter.return_value.run_export.assert_called_once_with(
        target_name=None, group_filter=None
    )
