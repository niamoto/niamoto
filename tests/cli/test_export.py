"""Test export commands."""

import pytest
from click.testing import CliRunner
from unittest import mock

from niamoto.cli.commands.export import generate_commands
from niamoto.common.exceptions import (
    TemplateError,
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
    mock_exporter.return_value.generate_content.assert_has_calls(
        [mock.call("taxon"), mock.call("plot"), mock.call("shape")]
    )


def test_export_pages_with_group(mock_config, mock_exporter):
    """Test export pages with specific group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages", "--group", "taxon"])

    assert result.exit_code == 0
    mock_exporter.assert_called_once_with(mock_config_instance)
    mock_exporter.return_value.generate_content.assert_called_once_with("taxon")


def test_export_pages_invalid_group(mock_config):
    """Test export pages with invalid group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages", "--group", "invalid"])

    assert result.exit_code == 1
    assert "Invalid group specified" in str(result.exception)


def test_export_pages_missing_config(mock_config):
    """Test export pages with missing config."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = None

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages"])

    assert result.exit_code == 1
    assert "Missing or empty transforms configuration" in str(result.exception)


def test_export_pages_template_error(mock_config, mock_exporter):
    """Test export pages with template error."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}
    mock_exporter_instance = mock_exporter.return_value
    mock_exporter_instance.generate_content.side_effect = TemplateError(
        template_name="test.html",
        message="Template error",
        details={"error": "Test error"},
    )

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages"])

    assert result.exit_code == 1
    assert "Template processing failed" in str(result.exception)


def test_export_pages_generation_error(mock_config, mock_exporter):
    """Test export pages with generation error."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}
    mock_exporter_instance = mock_exporter.return_value
    mock_exporter_instance.generate_content.side_effect = Exception("Test error")

    runner = CliRunner()
    result = runner.invoke(generate_commands, ["pages"])

    assert result.exit_code == 1
    assert "Content generation failed" in str(result.exception)


def test_export_default_command(mock_config, mock_exporter):
    """Test export default command."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(generate_commands)

    assert result.exit_code == 0
    mock_exporter.assert_called_once_with(mock_config_instance)
    mock_exporter.return_value.generate_content.assert_has_calls(
        [mock.call("taxon"), mock.call("plot"), mock.call("shape")]
    )
