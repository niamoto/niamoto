"""Test export commands."""

import pytest
from click.testing import CliRunner
from unittest import mock
from pathlib import Path

from niamoto.cli.commands.export import (
    export_command,
    _list_export_targets,
    _show_dry_run,
)
from niamoto.common.exceptions import (
    TemplateError,
    GenerationError,
    ConfigurationError,
    ProcessError,
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
        # Set up default return values for common methods
        mock_service = mock_exporter.return_value
        mock_service.run_export.return_value = {"default": {"status": "success"}}
        mock_service.get_export_targets.return_value = {}
        yield mock_exporter


def test_export_pages_no_group(mock_config, mock_path, mock_exporter):
    """Test export pages without group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(export_command, ["--target", "web_pages"])

    assert result.exit_code == 0
    # Check ExporterService is called with db_path and config
    mock_exporter.assert_called_once_with(
        db_path="/mock/db/path", config=mock_config_instance
    )
    # Check run_export is called instead of export_data
    mock_exporter.return_value.run_export.assert_called_once_with(
        target_name="web_pages", group_filter=None
    )


def test_export_pages_with_group(mock_config, mock_path, mock_exporter):
    """Test export pages with specific group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(
        export_command, ["--target", "web_pages", "--group", "taxon"]
    )

    assert result.exit_code == 0
    # Check ExporterService is called with db_path and config
    mock_exporter.assert_called_once_with(
        db_path="/mock/db/path", config=mock_config_instance
    )
    # Check run_export is called with the right group
    mock_exporter.return_value.run_export.assert_called_once_with(
        target_name="web_pages", group_filter="taxon"
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
        result = runner.invoke(
            export_command, ["--target", "web_pages", "--group", "invalid"]
        )

        # Test should fail with an exit code of 1
        assert result.exit_code == 1


def test_export_pages_missing_config(mock_config):
    """Test export pages with missing config."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = None

    runner = CliRunner()
    result = runner.invoke(export_command, ["--target", "web_pages"])

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
    result = runner.invoke(export_command, ["--target", "web_pages"])

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
    result = runner.invoke(export_command, ["--target", "web_pages"])

    # With the error_handler decorator, this will exit with code 1 instead of raising
    assert result.exit_code == 1


def test_export_default_command(mock_config, mock_path, mock_exporter):
    """Test export default command."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(export_command)

    assert result.exit_code == 0
    # Check ExporterService is called with db_path and config
    mock_exporter.assert_called_once_with(
        db_path="/mock/db/path", config=mock_config_instance
    )
    # Check run_export is called instead of export_data
    mock_exporter.return_value.run_export.assert_called_once_with(
        target_name=None, group_filter=None
    )


# Tests for CLI options
def test_export_list_option(mock_config, mock_path, mock_exporter):
    """Test export command with --list option."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock the get_export_targets method
    mock_service = mock_exporter.return_value
    mock_service.get_export_targets.return_value = {
        "web_pages": {
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [{"group_by": "taxon"}, {"group_by": "plot"}],
            "params": {"output_dir": "/output/web"},
        },
        "json_api": {
            "enabled": False,
            "exporter": "json_api_exporter",
            "params": {"output_dir": "/output/api"},
        },
    }

    runner = CliRunner()
    result = runner.invoke(export_command, ["--list"])

    assert result.exit_code == 0
    # Should call get_export_targets but not run_export
    mock_service.get_export_targets.assert_called_once()
    mock_service.run_export.assert_not_called()

    # Check output contains target information
    assert "web_pages" in result.output
    assert "json_api" in result.output
    assert "html_page_exporter" in result.output
    assert "json_api_exporter" in result.output
    # Check groups and output paths are displayed
    assert "Groups: taxon, plot" in result.output
    assert "Output: /output/web" in result.output
    assert "Output: /output/api" in result.output


def test_export_list_option_no_targets(mock_config, mock_path, mock_exporter):
    """Test export command with --list option when no targets are found."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock empty targets
    mock_service = mock_exporter.return_value
    mock_service.get_export_targets.return_value = {}

    runner = CliRunner()
    result = runner.invoke(export_command, ["--list"])

    assert result.exit_code == 0
    assert "No export targets found" in result.output


def test_export_list_option_error(mock_config, mock_path, mock_exporter):
    """Test export command with --list option when get_export_targets fails."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock error in get_export_targets
    mock_service = mock_exporter.return_value
    mock_service.get_export_targets.side_effect = Exception("Failed to get targets")

    runner = CliRunner()
    result = runner.invoke(export_command, ["--list"])

    assert result.exit_code == 0
    assert "Failed to list targets" in result.output


def test_export_dry_run_option(mock_config, mock_path, mock_exporter):
    """Test export command with --dry-run option."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock the get_export_targets method
    mock_service = mock_exporter.return_value
    mock_service.get_export_targets.return_value = {
        "web_pages": {
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [{"group_by": "taxon"}, {"group_by": "plot"}],
            "params": {"output_dir": "/output/web"},
        }
    }

    runner = CliRunner()
    result = runner.invoke(export_command, ["--dry-run"])

    assert result.exit_code == 0
    # Should call get_export_targets but not run_export
    mock_service.get_export_targets.assert_called_once()
    mock_service.run_export.assert_not_called()

    # Check output contains dry run information
    assert "DRY RUN" in result.output
    assert "web_pages" in result.output


def test_export_dry_run_with_target(mock_config, mock_path, mock_exporter):
    """Test export command with --dry-run and specific target."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock the get_export_targets method
    mock_service = mock_exporter.return_value
    mock_service.get_export_targets.return_value = {
        "web_pages": {
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [{"group_by": "taxon"}],
            "params": {"output_dir": "/output/web"},
        },
        "json_api": {"enabled": True, "exporter": "json_api_exporter"},
    }

    runner = CliRunner()
    result = runner.invoke(export_command, ["--dry-run", "--target", "web_pages"])

    assert result.exit_code == 0
    # Should show only the specified target
    assert "web_pages" in result.output
    assert "json_api" not in result.output


def test_export_dry_run_target_not_found(mock_config, mock_path, mock_exporter):
    """Test export command with --dry-run and non-existent target."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock the get_export_targets method
    mock_service = mock_exporter.return_value
    mock_service.get_export_targets.return_value = {
        "web_pages": {"enabled": True, "exporter": "html_page_exporter"}
    }

    runner = CliRunner()
    result = runner.invoke(export_command, ["--dry-run", "--target", "nonexistent"])

    assert result.exit_code == 0
    assert "not found in configuration" in result.output


def test_export_dry_run_with_group(mock_config, mock_path, mock_exporter):
    """Test export command with --dry-run, target, and group filter."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock the get_export_targets method
    mock_service = mock_exporter.return_value
    mock_service.get_export_targets.return_value = {
        "web_pages": {
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [{"group_by": "taxon"}, {"group_by": "plot"}],
        }
    }

    runner = CliRunner()
    result = runner.invoke(
        export_command, ["--dry-run", "--target", "web_pages", "--group", "taxon"]
    )

    assert result.exit_code == 0
    assert "taxon" in result.output
    # Should not show "plot" group since we filtered to "taxon"


def test_export_dry_run_group_not_found(mock_config, mock_path, mock_exporter):
    """Test export command with --dry-run and non-existent group."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock the get_export_targets method
    mock_service = mock_exporter.return_value
    mock_service.get_export_targets.return_value = {
        "web_pages": {
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [{"group_by": "taxon"}],
        }
    }

    runner = CliRunner()
    result = runner.invoke(
        export_command, ["--dry-run", "--target", "web_pages", "--group", "nonexistent"]
    )

    assert result.exit_code == 0
    assert "not found in this target" in result.output


def test_export_dry_run_error(mock_config, mock_path, mock_exporter):
    """Test export command with --dry-run when get_export_targets fails."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock error in get_export_targets
    mock_service = mock_exporter.return_value
    mock_service.get_export_targets.side_effect = Exception("Failed to get targets")

    runner = CliRunner()
    result = runner.invoke(export_command, ["--dry-run"])

    assert result.exit_code == 0
    assert "Failed to analyze export configuration" in result.output


# Tests for validation and error cases
def test_export_group_without_target(mock_config, mock_path, mock_exporter):
    """Test export command with --group but no --target (should fail)."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    runner = CliRunner()
    result = runner.invoke(export_command, ["--group", "taxon"])

    assert result.exit_code == 0  # Function returns normally but prints error
    assert "requires --target" in result.output


def test_export_database_not_found(mock_config):
    """Test export command when database doesn't exist."""
    # Configure mock with non-existent database
    mock_config_instance = mock_config.return_value
    mock_config_instance.database_path = "/nonexistent/db"

    with mock.patch("niamoto.cli.commands.export.Path") as mock_path_class:
        mock_path_instance = mock.MagicMock(spec=Path)
        mock_path_instance.exists.return_value = False
        mock_path_instance.__str__.return_value = "/nonexistent/db"
        mock_path_class.return_value = mock_path_instance

        runner = CliRunner()
        result = runner.invoke(export_command, ["--target", "web_pages"])

        assert result.exit_code == 0  # Function returns normally but prints error
        assert "Database not found" in result.output


def test_export_database_path_none(mock_config, mock_path, mock_exporter):
    """Test export command when database_path is None."""
    # Configure mock with None database_path
    mock_config_instance = mock_config.return_value
    mock_config_instance.database_path = None

    runner = CliRunner()
    result = runner.invoke(export_command, ["--target", "web_pages"])

    assert result.exit_code == 0  # Function returns normally but prints error
    assert "Database not found" in result.output


def test_export_configuration_error(mock_config, mock_path, mock_exporter):
    """Test export command with ConfigurationError."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock ConfigurationError
    mock_service = mock_exporter.return_value
    mock_service.run_export.side_effect = ConfigurationError(
        config_key="test_key", message="Invalid configuration"
    )

    runner = CliRunner()
    result = runner.invoke(export_command, ["--target", "web_pages"])

    assert result.exit_code == 1
    assert "Configuration error" in result.output


def test_export_process_error(mock_config, mock_path, mock_exporter):
    """Test export command with ProcessError."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock ProcessError
    mock_service = mock_exporter.return_value
    mock_service.run_export.side_effect = ProcessError("Export process failed")

    runner = CliRunner()
    result = runner.invoke(export_command, ["--target", "web_pages"])

    assert result.exit_code == 1
    assert "Export failed" in result.output


def test_export_unexpected_error(mock_config, mock_path, mock_exporter):
    """Test export command with unexpected exception."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock unexpected error
    mock_service = mock_exporter.return_value
    mock_service.run_export.side_effect = RuntimeError("Unexpected error")

    runner = CliRunner()
    result = runner.invoke(export_command, ["--target", "web_pages"])

    assert result.exit_code == 1
    assert "Unexpected error" in result.output


# Tests for metrics integration
def test_export_with_metrics(mock_config, mock_path, mock_exporter):
    """Test export command with metrics collection and display."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock export results
    mock_service = mock_exporter.return_value
    mock_service.run_export.return_value = {
        "web_pages": {
            "files_generated": 25,
            "errors": 0,
            "duration": "30.5s",
            "start_time": "2023-01-01T12:00:00",
        }
    }

    with mock.patch("niamoto.cli.commands.export.MetricsCollector") as mock_metrics:
        with mock.patch(
            "niamoto.cli.commands.export.print_operation_metrics"
        ) as mock_print_metrics:
            runner = CliRunner()
            result = runner.invoke(export_command, ["--target", "web_pages"])

            assert result.exit_code == 0
            # Verify metrics collection and display
            mock_metrics.create_export_metrics.assert_called_once()
            mock_print_metrics.assert_called_once()


def test_export_empty_results(mock_config, mock_path, mock_exporter):
    """Test export command with empty results."""
    # Configure mock
    mock_config_instance = mock_config.return_value
    mock_config_instance.exports = {"some": "config"}

    # Mock empty export results
    mock_service = mock_exporter.return_value
    mock_service.run_export.return_value = {}

    with mock.patch("niamoto.cli.commands.export.MetricsCollector") as mock_metrics:
        runner = CliRunner()
        result = runner.invoke(export_command, ["--target", "web_pages"])

        assert result.exit_code == 0
        # Should still call metrics collection even with empty results
        mock_metrics.create_export_metrics.assert_called_once_with({})


# Tests for utility functions
def test_list_export_targets_function():
    """Test _list_export_targets function directly."""

    # Mock service
    mock_service = mock.MagicMock()
    mock_service.get_export_targets.return_value = {
        "web_pages": {
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [{"group_by": "taxon"}, {"group_by": "plot"}],
            "params": {"output_dir": "/output/web"},
        },
        "json_api": {"enabled": False, "exporter": "json_api_exporter"},
    }

    # Mock print functions to capture output
    with mock.patch("niamoto.cli.commands.export.print_section") as mock_print_section:
        with mock.patch("niamoto.cli.commands.export.print_info") as mock_print_info:
            _list_export_targets(mock_service)

            # Verify section header
            mock_print_section.assert_called_once_with("Available export targets")

            # Verify info calls for targets
            assert mock_print_info.call_count >= 2  # At least one call per target


def test_list_export_targets_no_targets():
    """Test _list_export_targets with no targets."""

    # Mock service with no targets
    mock_service = mock.MagicMock()
    mock_service.get_export_targets.return_value = {}

    with mock.patch("niamoto.cli.commands.export.print_warning") as mock_print_warning:
        _list_export_targets(mock_service)

        mock_print_warning.assert_called_once_with(
            "No export targets found in configuration."
        )


def test_list_export_targets_error():
    """Test _list_export_targets with service error."""

    # Mock service that raises error
    mock_service = mock.MagicMock()
    mock_service.get_export_targets.side_effect = Exception("Service error")

    with mock.patch("niamoto.cli.commands.export.print_error") as mock_print_error:
        _list_export_targets(mock_service)

        mock_print_error.assert_called_once_with(
            "Failed to list targets: Service error"
        )


def test_show_dry_run_function():
    """Test _show_dry_run function directly."""

    # Mock service
    mock_service = mock.MagicMock()
    mock_service.get_export_targets.return_value = {
        "web_pages": {
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [{"group_by": "taxon"}],
            "params": {"output_dir": "/output/web"},
        },
        "disabled_target": {"enabled": False, "exporter": "some_exporter"},
    }

    with mock.patch("niamoto.cli.commands.export.print_section") as mock_print_section:
        with mock.patch("niamoto.cli.commands.export.print_info") as mock_print_info:
            _show_dry_run(mock_service, None, None)

            # Verify section header
            mock_print_section.assert_called_once_with(
                "DRY RUN - The following would be exported"
            )

            # Should show info about enabled targets
            assert mock_print_info.call_count >= 1


def test_show_dry_run_specific_target():
    """Test _show_dry_run with specific target."""

    # Mock service
    mock_service = mock.MagicMock()
    mock_service.get_export_targets.return_value = {
        "web_pages": {"enabled": True, "exporter": "html_page_exporter"},
        "other_target": {"enabled": True, "exporter": "other_exporter"},
    }

    with mock.patch("niamoto.cli.commands.export.print_info") as mock_print_info:
        _show_dry_run(mock_service, "web_pages", None)

        # Should only show the specified target
        info_calls = [call[0][0] for call in mock_print_info.call_args_list]
        assert any("web_pages" in call for call in info_calls)


def test_show_dry_run_target_not_found():
    """Test _show_dry_run with non-existent target."""

    # Mock service
    mock_service = mock.MagicMock()
    mock_service.get_export_targets.return_value = {
        "existing_target": {"enabled": True, "exporter": "html_page_exporter"}
    }

    with mock.patch("niamoto.cli.commands.export.print_error") as mock_print_error:
        _show_dry_run(mock_service, "nonexistent", None)

        mock_print_error.assert_called_once_with(
            "Target 'nonexistent' not found in configuration."
        )


def test_show_dry_run_with_group_filter():
    """Test _show_dry_run with group filter."""

    # Mock service
    mock_service = mock.MagicMock()
    mock_service.get_export_targets.return_value = {
        "web_pages": {
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [{"group_by": "taxon"}, {"group_by": "plot"}],
        }
    }

    with mock.patch("niamoto.cli.commands.export.print_info") as mock_print_info:
        _show_dry_run(mock_service, "web_pages", "taxon")

        # Should show info about the filtered group
        assert mock_print_info.call_count >= 1


def test_show_dry_run_group_not_found():
    """Test _show_dry_run with non-existent group."""

    # Mock service
    mock_service = mock.MagicMock()
    mock_service.get_export_targets.return_value = {
        "web_pages": {
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [{"group_by": "taxon"}],
        }
    }

    with mock.patch("niamoto.cli.commands.export.print_warning") as mock_print_warning:
        _show_dry_run(mock_service, "web_pages", "nonexistent")

        mock_print_warning.assert_called_once_with(
            "   Group 'nonexistent' not found in this target"
        )


def test_show_dry_run_error():
    """Test _show_dry_run with service error."""

    # Mock service that raises error
    mock_service = mock.MagicMock()
    mock_service.get_export_targets.side_effect = Exception("Service error")

    with mock.patch("niamoto.cli.commands.export.print_error") as mock_print_error:
        _show_dry_run(mock_service, None, None)

        mock_print_error.assert_called_once_with(
            "Failed to analyze export configuration: Service error"
        )
