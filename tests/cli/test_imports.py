"""Tests for the import commands in the Niamoto CLI."""

import unittest.mock as mock

import pytest
from click.testing import CliRunner

from niamoto.cli.commands.imports import (
    import_all,
    import_run,
    import_reference,
    import_dataset,
    import_list,
)


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestImportRun:
    """Tests for the import_run command."""

    def test_import_run_success(self, runner):
        """Test successful import run."""
        with (
            mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
            mock.patch("niamoto.cli.commands.imports.ImporterService") as mock_importer,
            mock.patch("niamoto.cli.commands.imports.set_progress_mode"),
        ):
            # Configure mocks
            config = mock_config.return_value
            config.database_path = "/path/to/db.duckdb"
            mock_imports_config = mock.MagicMock()
            config.get_imports_config = mock_imports_config

            importer_instance = mock_importer.return_value
            importer_instance.import_all.return_value = (
                "Successfully imported all entities"
            )

            result = runner.invoke(import_run, [])

            assert result.exit_code == 0
            assert "Successfully imported all entities" in result.output

    def test_import_run_with_reset(self, runner):
        """Test import run with reset table option."""
        with (
            mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
            mock.patch("niamoto.cli.commands.imports.ImporterService") as mock_importer,
            mock.patch("niamoto.cli.commands.imports.set_progress_mode"),
        ):
            # Configure mocks
            config = mock_config.return_value
            config.database_path = "/path/to/db.duckdb"
            mock_imports_config = mock.MagicMock()
            config.get_imports_config = mock_imports_config

            importer_instance = mock_importer.return_value
            importer_instance.import_all.return_value = (
                "Successfully imported all entities"
            )

            result = runner.invoke(import_run, ["--reset-table"])

            assert result.exit_code == 0
            # Verify reset_table=True was passed
            importer_instance.import_all.assert_called_once()
            call_kwargs = importer_instance.import_all.call_args[1]
            assert call_kwargs.get("reset_table") is True


class TestImportReference:
    """Tests for the import_reference command."""

    def test_import_reference_success(self, runner):
        """Test successful reference import."""
        with (
            mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
            mock.patch("niamoto.cli.commands.imports.ImporterService") as mock_importer,
            mock.patch("niamoto.cli.commands.imports.set_progress_mode"),
        ):
            # Configure mocks
            config = mock_config.return_value
            config.database_path = "/path/to/db.duckdb"

            # Mock the entities configuration
            mock_entities = mock.MagicMock()
            mock_entities.references = {"species": mock.MagicMock()}

            mock_imports_config = mock.MagicMock()
            mock_imports_config.entities = mock_entities
            config.get_imports_config = mock_imports_config

            importer_instance = mock_importer.return_value
            importer_instance.import_reference.return_value = (
                "Successfully imported reference: species"
            )

            result = runner.invoke(import_reference, ["species"])

            assert result.exit_code == 0
            assert "Successfully imported reference: species" in result.output

    def test_import_reference_not_found(self, runner):
        """Test error when reference not found."""
        with (
            mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
            mock.patch("niamoto.cli.commands.imports.set_progress_mode"),
        ):
            # Configure mocks
            config = mock_config.return_value
            config.database_path = "/path/to/db.duckdb"

            # Mock empty entities configuration
            mock_entities = mock.MagicMock()
            mock_entities.references = {}

            mock_imports_config = mock.MagicMock()
            mock_imports_config.entities = mock_entities
            config.get_imports_config = mock_imports_config

            result = runner.invoke(import_reference, ["nonexistent"])

            assert result.exit_code == 1
            assert "Failed to import reference 'nonexistent'" in result.output


class TestImportDataset:
    """Tests for the import_dataset command."""

    def test_import_dataset_success(self, runner):
        """Test successful dataset import."""
        with (
            mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
            mock.patch("niamoto.cli.commands.imports.ImporterService") as mock_importer,
            mock.patch("niamoto.cli.commands.imports.set_progress_mode"),
        ):
            # Configure mocks
            config = mock_config.return_value
            config.database_path = "/path/to/db.duckdb"

            # Mock the entities configuration
            mock_entities = mock.MagicMock()
            mock_entities.datasets = {"observations": mock.MagicMock()}

            mock_imports_config = mock.MagicMock()
            mock_imports_config.entities = mock_entities
            config.get_imports_config = mock_imports_config

            importer_instance = mock_importer.return_value
            importer_instance.import_dataset.return_value = (
                "Successfully imported dataset: observations"
            )

            result = runner.invoke(import_dataset, ["observations"])

            assert result.exit_code == 0
            assert "Successfully imported dataset: observations" in result.output


class TestImportList:
    """Tests for the import_list command."""

    def test_import_list_with_entities(self, runner):
        """Test listing entities."""
        with (
            mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
        ):
            # Configure mocks
            config = mock_config.return_value

            # Mock entities
            mock_ref = mock.MagicMock()
            mock_ref.kind = "taxonomy"
            mock_ref.connector = mock.MagicMock()
            mock_ref.connector.path = "data/species.csv"

            mock_ds = mock.MagicMock()
            mock_ds.connector = mock.MagicMock()
            mock_ds.connector.path = "data/observations.csv"
            mock_ds.links = []

            mock_entities = mock.MagicMock()
            mock_entities.references = {"species": mock_ref}
            mock_entities.datasets = {"observations": mock_ds}

            mock_imports_config = mock.MagicMock()
            mock_imports_config.entities = mock_entities
            config.get_imports_config = mock_imports_config

            result = runner.invoke(import_list, [])

            assert result.exit_code == 0
            assert "References:" in result.output
            assert "Datasets:" in result.output

    def test_import_list_no_entities(self, runner):
        """Test listing when no entities configured."""
        with (
            mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
        ):
            # Configure mocks
            config = mock_config.return_value

            mock_imports_config = mock.MagicMock()
            mock_imports_config.entities = None
            config.get_imports_config = mock_imports_config

            result = runner.invoke(import_list, [])

            assert result.exit_code == 0
            assert "No entities configured" in result.output


class TestImportAll:
    """Tests for the import_all command (deprecated alias)."""

    def test_import_all_invokes_import_run(self, runner):
        """Test that import_all invokes import_run."""
        with (
            mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
            mock.patch("niamoto.cli.commands.imports.ImporterService") as mock_importer,
            mock.patch("niamoto.cli.commands.imports.set_progress_mode"),
        ):
            # Configure mocks
            config = mock_config.return_value
            config.database_path = "/path/to/db.duckdb"
            mock_imports_config = mock.MagicMock()
            config.get_imports_config = mock_imports_config

            importer_instance = mock_importer.return_value
            importer_instance.import_all.return_value = (
                "Successfully imported all entities"
            )

            result = runner.invoke(import_all, [])

            assert result.exit_code == 0
            assert "Successfully imported all entities" in result.output
