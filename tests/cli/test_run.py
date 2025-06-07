"""
Tests for the run command module.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

from niamoto.cli.commands.run import run_pipeline
# Imports d'exceptions supprimés - tests supprimés


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
    assert "--no-reset" in result.output


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_all_phases(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running all phases of the pipeline."""
    mock_get_config_dir.return_value = "/mock/config"

    result = runner.invoke(run_pipeline)

    assert result.exit_code == 0
    assert "Starting Niamoto pipeline..." in result.output
    assert "Phase 0: Reset Environment" in result.output
    assert "Phase 1: Import" in result.output
    assert "Phase 2: Transform" in result.output
    assert "Phase 3: Export" in result.output
    assert "Pipeline completed successfully!" in result.output

    # Verify all commands were invoked
    mock_reset_env.assert_called_once_with("/mock/config")
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_no_reset(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running pipeline with --no-reset option."""
    result = runner.invoke(run_pipeline, ["--no-reset"])

    assert result.exit_code == 0
    assert "Starting Niamoto pipeline..." in result.output
    assert "Skipping environment reset" in result.output
    assert "Phase 1: Import" in result.output
    assert "Phase 2: Transform" in result.output
    assert "Phase 3: Export" in result.output
    assert "Pipeline completed successfully!" in result.output

    # Verify reset was not called
    mock_reset_env.assert_not_called()
    mock_get_config_dir.assert_not_called()

    # Verify other commands were invoked
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_skip_import(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running pipeline with import phase skipped."""
    mock_get_config_dir.return_value = "/mock/config"

    result = runner.invoke(run_pipeline, ["--skip-import"])

    assert result.exit_code == 0
    assert "Skipping import phase" in result.output
    assert "Phase 2: Transform" in result.output
    assert "Phase 3: Export" in result.output

    # Verify reset was called but import was not
    mock_reset_env.assert_called_once_with("/mock/config")
    mock_import.assert_not_called()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_skip_transform(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running pipeline with transform phase skipped."""
    mock_get_config_dir.return_value = "/mock/config"

    result = runner.invoke(run_pipeline, ["--skip-transform"])

    assert result.exit_code == 0
    assert "Phase 1: Import" in result.output
    assert "Skipping transform phase" in result.output
    assert "Phase 3: Export" in result.output

    # Verify only import and export were called
    mock_import.assert_called_once()
    mock_transform.assert_not_called()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_skip_export(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running pipeline with export phase skipped."""
    mock_get_config_dir.return_value = "/mock/config"

    result = runner.invoke(run_pipeline, ["--skip-export"])

    assert result.exit_code == 0
    assert "Phase 1: Import" in result.output
    assert "Phase 2: Transform" in result.output
    assert "Skipping export phase" in result.output

    # Verify only import and transform were called
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_not_called()


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_all_phases_skipped(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running pipeline with all phases skipped."""
    mock_get_config_dir.return_value = "/mock/config"

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
    # Reset should still be called even when all phases are skipped
    mock_reset_env.assert_called_once_with("/mock/config")


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_with_group_option(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running pipeline with group option."""
    mock_get_config_dir.return_value = "/mock/config"

    result = runner.invoke(run_pipeline, ["--group", "taxon"])

    assert result.exit_code == 0

    # Verify transform and export were called with group parameter
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()

    # Check that ctx.invoke was called with the group parameter
    # This is harder to test directly, but we can verify the command ran successfully


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_with_target_option(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running pipeline with target option."""
    mock_get_config_dir.return_value = "/mock/config"

    result = runner.invoke(run_pipeline, ["--target", "my_site"])

    assert result.exit_code == 0

    # Verify all commands were called
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_with_verbose_option(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running pipeline with verbose option."""
    mock_get_config_dir.return_value = "/mock/config"

    result = runner.invoke(run_pipeline, ["--verbose"])

    assert result.exit_code == 0

    # Verify all commands were called
    mock_import.assert_called_once()
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


# Test supprimé - créait des répertoires indésirables (db/, logs/)


# Test supprimé - créait des répertoires indésirables (db/, logs/)


# Test supprimé - créait des répertoires indésirables (db/, logs/)


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_mixed_options(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test running pipeline with multiple options combined."""
    mock_get_config_dir.return_value = "/mock/config"

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
    # Reset should still be called
    mock_reset_env.assert_called_once_with("/mock/config")


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
        "no_reset",
    }

    assert expected_params.issubset(params)


# Test supprimé - créait des répertoires indésirables (db/, logs/)


@patch("niamoto.cli.commands.run.reset_environment")
@patch("niamoto.cli.commands.run.get_config_dir")
@patch("niamoto.cli.commands.run.import_all")
@patch("niamoto.cli.commands.run.process_transformations")
@patch("niamoto.cli.commands.run.export_pages")
def test_run_pipeline_error_continues_to_next_phase_when_phase_skipped(
    mock_export,
    mock_transform,
    mock_import,
    mock_get_config_dir,
    mock_reset_env,
    runner,
):
    """Test that errors in skipped phases don't affect the pipeline."""
    mock_get_config_dir.return_value = "/mock/config"

    # Even if import would fail, it should be skipped and not affect the pipeline
    mock_import.side_effect = Exception("This should not run")

    result = runner.invoke(run_pipeline, ["--skip-import"])

    assert result.exit_code == 0
    assert "Skipping import phase" in result.output
    assert "Pipeline completed successfully!" in result.output

    # Verify import was not called due to skip
    mock_import.assert_not_called()
    mock_reset_env.assert_called_once_with("/mock/config")
    mock_transform.assert_called_once()
    mock_export.assert_called_once()


# Tests d'intégration supprimés - créaient des répertoires indésirables (db/, logs/)
