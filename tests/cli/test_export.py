"""Test export commands."""

import pytest
from click.testing import CliRunner
from unittest import mock

from niamoto.cli.commands.export import generate_commands
from niamoto.common.exceptions import (
    TemplateError,
    GenerationError,
)


@pytest.fixture
def mock_config():
    """Mock Config class."""
    with mock.patch("niamoto.cli.commands.export.Config") as mock_config:
        yield mock_config


@pytest.fixture
def mock_exporter():
    """Mock ExporterService class."""
    with mock.patch("niamoto.cli.commands.export.ExporterService") as mock_exporter:
        yield mock_exporter


def test_export_pages_no_group(mock_config, mock_exporter):
    """Test export pages without group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages"])

    assert result.exit_code == 0
    mock_exporter.assert_called_once_with(mock_config_instance)
    # When no group is specified, export_data is called with None
    mock_exporter.return_value.export_data.assert_called_once_with(None)


def test_export_pages_with_group(mock_config, mock_exporter):
    """Test export pages with specific group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages", "--group", "taxon"])

    assert result.exit_code == 0
    mock_exporter.assert_called_once_with(mock_config_instance)
    mock_exporter.return_value.export_data.assert_called_once_with("taxon")


def test_export_pages_invalid_group(mock_config):
    """Test export pages with invalid group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages", "--group", "invalid"])

    # With the error_handler decorator, this will exit with code 1 instead of raising
    assert result.exit_code == 1


def test_export_pages_missing_config(mock_config):
    """Test export pages with missing config."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = None

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages"])

    # In test environment, we're not exiting but raising the exception
    assert result.exit_code == 0


def test_export_pages_template_error(mock_config, mock_exporter):
    """Test export pages with template error."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}
    mock_exporter_instance = mock_exporter.return_value
    mock_exporter_instance.export_data.side_effect = TemplateError(
        template_name="test.html",
        message="Template error",
    )

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages"])

    # With the error_handler decorator, this will exit with code 1 instead of raising
    assert result.exit_code == 1


def test_export_pages_generation_error(mock_config, mock_exporter):
    """Test export pages with generation error."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}
    mock_exporter_instance = mock_exporter.return_value
    mock_exporter_instance.export_data.side_effect = GenerationError(
        message="Test error",
    )

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages"])

    # With the error_handler decorator, this will exit with code 1 instead of raising
    assert result.exit_code == 1


def test_export_default_command(mock_config, mock_exporter):
    """Test export default command."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands)

    assert result.exit_code == 0
    mock_exporter.assert_called_once_with(mock_config_instance)
    # When no group is specified, export_data is called with None
    mock_exporter.return_value.export_data.assert_called_once_with(None)
