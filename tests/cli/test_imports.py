"""Tests for the import commands in the Niamoto CLI."""

from unittest import mock
import pytest
from click.testing import CliRunner

from niamoto.cli.commands.imports import import_taxonomy


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestImportTaxonomy:
    """Tests for the import_taxonomy command."""

    def test_import_with_file_and_ranks(self, runner):
        """Test importing taxonomy with explicit file and ranks."""
        with runner.isolated_filesystem():
            # Create a temporary CSV file with realistic test data
            with open("taxonomy.csv", "w") as f:
                f.write("family,genus,species,author\n")
                f.write("Fabaceae,Acacia,Acacia mangium,Willd.\n")
                f.write("Fabaceae,Acacia,Acacia auriculiformis,A.Cunn. ex Benth.\n")
                f.write("Myrtaceae,Syzygium,Syzygium jambos,(L.) Alston\n")

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer,
                mock.patch("niamoto.cli.commands.imports.reset_table") as mock_reset,
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                # Ensure the config has the proper structure for taxonomy import
                config.imports = {
                    "taxonomy": {
                        "path": "taxonomy.csv",
                        "ranks": "family,genus,species",
                        # No API enrichment settings, so api_config will be None
                    }
                }
                mock_importer.return_value.import_taxonomy.return_value = (
                    "Successfully imported 3 taxa"
                )

                result = runner.invoke(
                    import_taxonomy, ["taxonomy.csv", "--ranks", "family,genus,species"]
                )

                assert result.exit_code == 0
                assert "Successfully imported 3 taxa" in result.output
                mock_reset.assert_called_once_with("/path/to/db.sqlite", "taxon_ref")
                mock_importer.return_value.import_taxonomy.assert_called_once_with(
                    "taxonomy.csv", ("family", "genus", "species"), None
                )

    def test_import_from_config(self, runner):
        """Test importing taxonomy using configuration."""
        with runner.isolated_filesystem():
            # Create a temporary CSV file
            with open("taxonomy.csv", "w") as f:
                f.write("family,genus,species,author\n")
                f.write("Fabaceae,Acacia,Acacia mangium,Willd.\n")

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer,
                mock.patch("niamoto.cli.commands.imports.reset_table") as mock_reset,
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {
                    "taxonomy": {
                        "path": "taxonomy.csv",
                        "ranks": "family,genus,species",
                        # No API enrichment settings, so api_config will be None
                    }
                }
                mock_importer.return_value.import_taxonomy.return_value = (
                    "Successfully imported 1 taxon"
                )

                result = runner.invoke(import_taxonomy, [])

                assert result.exit_code == 0
                assert "Successfully imported 1 taxon" in result.output
                mock_reset.assert_called_once_with("/path/to/db.sqlite", "taxon_ref")
                mock_importer.return_value.import_taxonomy.assert_called_once_with(
                    "taxonomy.csv", ("family", "genus", "species"), None
                )

    def test_file_not_found(self, runner):
        """Test error when file doesn't exist."""
        with runner.isolated_filesystem():
            with mock.patch("niamoto.cli.commands.imports.Config") as mock_config:
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"

                result = runner.invoke(
                    import_taxonomy,
                    ["nonexistent.csv", "--ranks", "family,genus,species"],
                )

                assert result.exit_code == 1
                assert "File not found" in result.output

    def test_missing_ranks(self, runner):
        """Test error when ranks are missing."""
        with runner.isolated_filesystem():
            # Create a temporary CSV file
            with open("taxonomy.csv", "w") as f:
                f.write("family,genus,species,author\n")
                f.write("Fabaceae,Acacia,Acacia mangium,Willd.\n")

            with mock.patch("niamoto.cli.commands.imports.Config") as mock_config:
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {"taxonomy": {"path": "taxonomy.csv"}}

                result = runner.invoke(import_taxonomy, ["taxonomy.csv"])

                assert result.exit_code == 1
                assert "Missing required fields: ranks" in result.output
