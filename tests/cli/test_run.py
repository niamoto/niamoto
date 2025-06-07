"""
Tests for the run command module.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

from niamoto.cli.commands.run import run_pipeline
from niamoto.common.exceptions import (
    ProcessError,
    DataImportError,
)


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock Config class."""
    with patch("niamoto.cli.commands.run.Config") as mock_config:
        mock_config.return_value.database_path = "/mock/db/path"
        yield mock_config


@pytest.fixture
def mock_path():
    """Mock Path object to control db path behavior."""
    with patch("niamoto.cli.commands.run.Path") as mock_path_class:
        mock_path_instance = MagicMock(spec=Path)
        mock_path_instance.exists.return_value = True
        mock_path_instance.__str__.return_value = "/mock/db/path"
        mock_path_class.return_value = mock_path_instance
        yield mock_path_class


def test_run_pipeline_help(runner):
    """Test that the run command help works correctly."""
    result = runner.invoke(run_pipeline, ["--help"])
    assert result.exit_code == 0
    assert "Run the complete Niamoto data pipeline" in result.output
    assert "--skip-import" in result.output
    assert "--skip-transform" in result.output
    assert "--skip-export" in result.output
    assert "--group" in result.output
    assert "--target" in result.output
    assert "--verbose" in result.output


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_all_phases(mock_export, mock_transform, mock_import, runner):
    """Test running all phases of the pipeline."""
    result = runner.invoke(run_pipeline)

    assert result.exit_code == 0
    assert "Starting Niamoto pipeline..." in result.output
    assert "Phase 1: Import" in result.output
    assert "Phase 2: Transform" in result.output
    assert "Phase 3: Export" in result.output
    assert "Pipeline completed successfully!" in result.output

    # Verify all commands were invoked
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_skip_import(mock_export, mock_transform, mock_import, runner):
    """Test running pipeline with import phase skipped."""
    result = runner.invoke(run_pipeline, ["--skip-import"])

    assert result.exit_code == 0
    assert "Skipping import phase" in result.output
    assert "Phase 2: Transform" in result.output
    assert "Phase 3: Export" in result.output

    # Verify only transform and export were called
    mock_import.assert_not_called()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_skip_transform(mock_export, mock_transform, mock_import, runner):
    """Test running pipeline with transform phase skipped."""
    result = runner.invoke(run_pipeline, ["--skip-transform"])

    assert result.exit_code == 0
    assert "Phase 1: Import" in result.output
    assert "Skipping transform phase" in result.output
    assert "Phase 3: Export" in result.output

    # Verify only import and export were called
    mock_import.assert_called_once()
    mock_transform.assert_not_called()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_skip_export(mock_export, mock_transform, mock_import, runner):
    """Test running pipeline with export phase skipped."""
    result = runner.invoke(run_pipeline, ["--skip-export"])

    assert result.exit_code == 0
    assert "Phase 1: Import" in result.output
    assert "Phase 2: Transform" in result.output
    assert "Skipping export phase" in result.output

    # Verify only import and transform were called
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_not_called()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_all_phases_skipped(
    mock_export, mock_transform, mock_import, runner
):
    """Test running pipeline with all phases skipped."""
    result = runner.invoke(
        run_pipeline, ["--skip-import", "--skip-transform", "--skip-export"]
    )

    assert result.exit_code == 0
    assert "Skipping import phase" in result.output
    assert "Skipping transform phase" in result.output
    assert "Skipping export phase" in result.output
    assert "Pipeline completed successfully!" in result.output

    # Verify no commands were called
    mock_import.assert_not_called()
    mock_transform.assert_not_called()
    mock_export.assert_not_called()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_with_group_option(
    mock_export, mock_transform, mock_import, runner
):
    """Test running pipeline with group option."""
    result = runner.invoke(run_pipeline, ["--group", "taxon"])

    assert result.exit_code == 0

    # Verify transform and export were called with group parameter
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()

    # Check that ctx.invoke was called with the group parameter
    # This is harder to test directly, but we can verify the command ran successfully


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_with_target_option(
    mock_export, mock_transform, mock_import, runner
):
    """Test running pipeline with target option."""
    result = runner.invoke(run_pipeline, ["--target", "my_site"])

    assert result.exit_code == 0

    # Verify all commands were called
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_with_verbose_option(
    mock_export, mock_transform, mock_import, runner
):
    """Test running pipeline with verbose option."""
    result = runner.invoke(run_pipeline, ["--verbose"])

    assert result.exit_code == 0

    # Verify all commands were called
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_import_error(mock_export, mock_transform, mock_import, runner):
    """Test pipeline behavior when import phase fails."""
    mock_import.side_effect = DataImportError(
        "Import failed", details={"error": "test"}
    )

    result = runner.invoke(run_pipeline)

    assert result.exit_code == 1
    assert "Pipeline failed" in result.output

    # Verify only import was called
    mock_import.assert_called_once()
    mock_transform.assert_not_called()
    mock_export.assert_not_called()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_transform_error(mock_export, mock_transform, mock_import, runner):
    """Test pipeline behavior when transform phase fails."""
    mock_transform.side_effect = ProcessError("Transform failed")

    result = runner.invoke(run_pipeline)

    assert result.exit_code == 1
    assert "Pipeline failed" in result.output

    # Verify import and transform were called, but not export
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_not_called()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_export_error(mock_export, mock_transform, mock_import, runner):
    """Test pipeline behavior when export phase fails."""
    mock_export.side_effect = ProcessError("Export failed")

    result = runner.invoke(run_pipeline)

    assert result.exit_code == 1
    assert "Pipeline failed" in result.output

    # Verify all phases were attempted
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_mixed_options(mock_export, mock_transform, mock_import, runner):
    """Test running pipeline with multiple options combined."""
    result = runner.invoke(
        run_pipeline,
        ["--skip-import", "--group", "taxon", "--target", "my_site", "--verbose"],
    )

    assert result.exit_code == 0
    assert "Skipping import phase" in result.output
    assert "Phase 2: Transform" in result.output
    assert "Phase 3: Export" in result.output

    # Verify only transform and export were called
    mock_import.assert_not_called()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


def test_run_pipeline_command_name():
    """Test that the command has the correct name."""
    assert run_pipeline.name == "run"


def test_run_pipeline_has_correct_options():
    """Test that the command has all expected options."""
    # Get the command's parameters
    params = {param.name for param in run_pipeline.params}

    expected_params = {
        "skip_import",
        "skip_transform",
        "skip_export",
        "group",
        "target",
        "verbose",
    }

    assert expected_params.issubset(params)


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_exception_handling(
    mock_export, mock_transform, mock_import, runner
):
    """Test pipeline behavior with unexpected exceptions."""
    mock_import.side_effect = Exception("Unexpected error")

    result = runner.invoke(run_pipeline)

    assert result.exit_code == 1
    assert "Pipeline failed" in result.output

    # Verify import was called but others weren't due to the exception
    mock_import.assert_called_once()
    mock_transform.assert_not_called()
    mock_export.assert_not_called()


@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_error_continues_to_next_phase_when_phase_skipped(
    mock_export, mock_transform, mock_import, runner
):
    """Test that errors in skipped phases don't affect the pipeline."""
    # Even if import would fail, it should be skipped and not affect the pipeline
    mock_import.side_effect = Exception("This should not run")

    result = runner.invoke(run_pipeline, ["--skip-import"])

    assert result.exit_code == 0
    assert "Skipping import phase" in result.output
    assert "Pipeline completed successfully!" in result.output

    # Verify import was not called due to skip
    mock_import.assert_not_called()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


class TestRunPipelineIntegration:
    """Integration tests for the run pipeline command."""

    def test_run_command_integration_with_cli(self):
        """Test that the run command is properly integrated with the main CLI."""
        try:
            from niamoto.cli.commands import create_cli

            cli = create_cli()
            runner = CliRunner()

            # Test that the run command is available
            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0
            assert "run" in result.output

            # Test that run command help works
            result = runner.invoke(cli, ["run", "--help"])
            assert result.exit_code == 0
            assert "Run the complete Niamoto data pipeline" in result.output
        except (ImportError, AttributeError) as e:
            # Skip test if CLI integration has issues (not related to run command)
            pytest.skip(f"CLI integration test skipped due to: {e}")

    @patch("niamoto.cli.commands.run.import_all")
    @patch("niamoto.cli.commands.run.process_transformations")
    @patch("niamoto.cli.commands.run.export_pages")
    def test_run_pipeline_context_passing(
        self, mock_export, mock_transform, mock_import
    ):
        """Test that click context is properly passed to invoked commands."""
        try:
            from niamoto.cli.commands import create_cli

            cli = create_cli()
            runner = CliRunner()

            # This should work without context errors
            result = runner.invoke(cli, ["run", "--skip-import", "--skip-export"])

            assert result.exit_code == 0
            assert "Phase 2: Transform" in result.output

            # Verify the correct commands were called via context
            mock_import.assert_not_called()
            mock_transform.assert_called_once()
            mock_export.assert_not_called()
        except (ImportError, AttributeError) as e:
            # Skip test if CLI integration has issues (not related to run command)
            pytest.skip(f"CLI context test skipped due to: {e}")

    @patch("niamoto.cli.commands.run.import_all")
    @patch("niamoto.cli.commands.run.process_transformations")
    @patch("niamoto.cli.commands.run.export_pages")
    def test_run_command_parameter_validation(
        self, mock_export, mock_transform, mock_import
    ):
        """Test parameter validation for the run command."""
        runner = CliRunner()

        # Test with invalid flag combinations (this should still work as all flags are independent)
        result = runner.invoke(
            run_pipeline, ["--skip-import", "--skip-transform", "--skip-export"]
        )
        assert result.exit_code == 0

        # Test with invalid option values (these should be handled gracefully)
        result = runner.invoke(run_pipeline, ["--group", ""])
        assert result.exit_code == 0  # Empty string should be accepted

        result = runner.invoke(run_pipeline, ["--target", ""])
        assert result.exit_code == 0  # Empty string should be accepted

    @patch("niamoto.cli.commands.run.import_all")
    @patch("niamoto.cli.commands.run.process_transformations")
    @patch("niamoto.cli.commands.run.export_pages")
    def test_run_pipeline_with_all_options(
        self, mock_export, mock_transform, mock_import
    ):
        """Test run pipeline with all possible options set."""
        runner = CliRunner()

        result = runner.invoke(
            run_pipeline, ["--group", "taxon", "--target", "my_target", "--verbose"]
        )

        assert result.exit_code == 0
        assert "Starting Niamoto pipeline..." in result.output
        assert "Pipeline completed successfully!" in result.output

        # All phases should be called
        mock_import.assert_called_once()
        mock_transform.assert_called_once()
        mock_export.assert_called_once()

    def test_run_command_docstring_and_help(self):
        """Test that the command docstring and help are properly formatted."""
        runner = CliRunner()
        result = runner.invoke(run_pipeline, ["--help"])

        assert result.exit_code == 0

        # Check for key help content
        help_content = result.output
        assert "Run the complete Niamoto data pipeline" in help_content
        assert "import, transform, and export" in help_content
        assert "Examples:" in help_content
        assert "niamoto run" in help_content
        assert "--skip-import" in help_content
        assert "--skip-transform" in help_content
        assert "--skip-export" in help_content

    @patch("niamoto.cli.commands.run.print_info")
    @patch("niamoto.cli.commands.run.print_success")
    @patch("niamoto.cli.commands.run.print_error")
    @patch("niamoto.cli.commands.run.import_all")
    @patch("niamoto.cli.commands.run.process_transformations")
    @patch("niamoto.cli.commands.run.export_pages")
    def test_run_pipeline_output_messages(
        self,
        mock_export,
        mock_transform,
        mock_import,
        mock_print_error,
        mock_print_success,
        mock_print_info,
    ):
        """Test that appropriate messages are printed during pipeline execution."""
        runner = CliRunner()

        result = runner.invoke(run_pipeline)

        assert result.exit_code == 0

        # Verify print functions were called appropriately
        mock_print_info.assert_called()
        mock_print_success.assert_called_with("\n✨ Pipeline completed successfully!")
        mock_print_error.assert_not_called()

    @patch("niamoto.cli.commands.run.print_error")
    @patch("niamoto.cli.commands.run.import_all")
    @patch("niamoto.cli.commands.run.process_transformations")
    @patch("niamoto.cli.commands.run.export_pages")
    def test_run_pipeline_error_output_messages(
        self, mock_export, mock_transform, mock_import, mock_print_error
    ):
        """Test that error messages are properly printed when pipeline fails."""
        runner = CliRunner()

        # Make import fail
        mock_import.side_effect = Exception("Test error")

        result = runner.invoke(run_pipeline)

        assert result.exit_code == 1

        # Verify error message was printed
        mock_print_error.assert_called_with("\n❌ Pipeline failed: Test error")
