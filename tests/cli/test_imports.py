"""Tests for the import commands in the Niamoto CLI."""

from pathlib import Path
import unittest.mock as mock

import pytest
from click.testing import CliRunner

from niamoto.cli.commands.imports import (
    import_all,
    import_occurrences,
    import_plots,
    import_shapes,
    import_taxonomy,
    validate_source_config,
    get_source_path,
)
from niamoto.common.exceptions import ConfigurationError, FileError, ValidationError


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


class TestImportAll:
    """Tests for the import_all command."""

    def test_import_all_missing_occurrence_columns(self, runner):
        """Test error when taxonomy source is occurrence but occurrence_columns is missing."""
        with runner.isolated_filesystem():
            with mock.patch("niamoto.cli.commands.imports.Config") as mock_config:
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {
                    "taxonomy": {
                        "source": "occurrence",
                        "path": "dummy_taxonomy.csv",  # Add dummy path
                        "ranks": "dummy_rank",  # Add dummy ranks
                        # Missing 'occurrence_columns'
                    },
                    # Add minimal valid config for other potential imports if needed
                    # to avoid unrelated validation errors
                    "occurrence": {"path": "dummy_occurrence.csv"},
                    "plot": {"path": "dummy_plot.csv"},
                    "shapes": {"path": "dummy_shape.geojson"},
                }
                # Mock ImporterService and reset_table, although they might not be called
                # before the validation error
                with (
                    mock.patch("niamoto.cli.commands.imports.ImporterService"),
                    mock.patch("niamoto.cli.commands.imports.reset_table"),
                ):
                    result = runner.invoke(import_all, [])

                    assert result.exit_code == 1
                    # The specific ConfigurationError message isn't printed directly,
                    # the command outputs a generic failure message.
                    assert "Full import failed" in result.output
                    # We could potentially also check result.exception here if needed,
                    # but checking the output and exit code is often sufficient for CLI tests.

    def test_import_all_taxonomy_from_file(self, runner):
        """Test import_all successfully imports taxonomy from file by default."""
        with runner.isolated_filesystem() as temp_dir:
            temp_path = Path(temp_dir)
            taxonomy_file = temp_path / "taxonomy.csv"
            occurrences_file = temp_path / "occurrences.csv"
            plots_file = temp_path / "plots.csv"
            shapes_file = temp_path / "shapes.geojson"

            # Create dummy files mentioned in config
            with open(taxonomy_file, "w") as f:
                f.write("col1,col2\n")
                f.write("val1,val2\n")
            with open(occurrences_file, "w") as f:
                f.write("id,loc\n")
                f.write("1,A\n")
            with open(plots_file, "w") as f:
                f.write("id,geom\n")
                f.write("1,POINT(1 1)\n")
            with open(shapes_file, "w") as f:
                f.write('{"type": "FeatureCollection", "features": []}\n')

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer_service,
                mock.patch("niamoto.cli.commands.imports.reset_table") as mock_reset,
            ):
                # Create a mock instance to configure
                mock_config_instance = mock.MagicMock()

                # Configure the mock instance attributes
                mock_config_instance.database_path = (
                    temp_path / "db.sqlite"
                )  # Use temp dir for db too
                mock_config_instance.imports = {
                    "taxonomy": {
                        "path": str(taxonomy_file),  # Use absolute path
                        "ranks": "family,genus",
                        # 'source' is implicitly 'file'
                    },
                    "occurrences": {
                        "path": str(occurrences_file),  # Use absolute path
                        "identifier": "id",
                        "location_field": "loc",
                        "locality_field": "locality",  # Add dummy locality field
                    },
                    "plots": {
                        "path": str(plots_file),  # Use absolute path
                        "identifier": "id",
                        "geometry_field": "geom",
                        "location_field": "loc",  # Add dummy field
                        "locality_field": "locality",  # Add dummy field
                    },
                    "shapes": [
                        {  # Wrap the dict in a list
                            "path": str(shapes_file),  # Use absolute path
                            "identifier": "id",
                        }
                    ],
                }

                # Make the mock Config class return our configured instance when called
                mock_config.return_value = mock_config_instance

                importer_instance = mock_importer_service.return_value
                importer_instance.import_taxonomy.return_value = "Taxonomy import OK"
                # Mock other import methods called by import_all
                importer_instance.import_occurrences.return_value = "Occurrences OK"
                importer_instance.import_plots.return_value = "Plots OK"
                importer_instance.import_shapes.return_value = "Shapes OK"

                result = runner.invoke(import_all, [])

                assert result.exit_code == 0
                assert "Starting full data import..." in result.output
                assert "Importing taxonomy..." in result.output
                assert "Taxonomy import OK" in result.output
                assert "Importing occurrences..." in result.output
                assert "Occurrences OK" in result.output
                # ... add assertions for plots and shapes if desired ...
                assert "[>] Data import completed" in result.output

                # Verify reset was called for taxonomy
                mock_reset.assert_any_call(
                    mock_config_instance.database_path, "taxon_ref"
                )

                # Verify import_taxonomy was called correctly
                importer_instance.import_taxonomy.assert_called_once_with(
                    str(taxonomy_file),
                    ("family", "genus"),
                    None,  # api_config is None
                )
                # Verify other import methods were called
                importer_instance.import_occurrences.assert_called_once()
                importer_instance.import_plots.assert_called_once()
                importer_instance.import_shapes.assert_called_once()

    def test_import_all_missing_config(self, runner):
        """Test error when imports configuration is missing."""
        with runner.isolated_filesystem():
            with mock.patch("niamoto.cli.commands.imports.Config") as mock_config:
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {}  # Empty config, missing imports

                # Make sure import_taxonomy is called first, which will fail
                with mock.patch(
                    "niamoto.cli.commands.imports.import_taxonomy"
                ) as mock_import_taxonomy:
                    mock_import_taxonomy.side_effect = ConfigurationError(
                        config_key="taxonomy",
                        message="Source 'taxonomy' not found in configuration",
                        details={},
                    )

                    result = runner.invoke(import_all, [])

                    assert result.exit_code == 1
                    assert (
                        "Source 'taxonomy' not found in configuration" in result.output
                    )
                    assert "Full import failed" in result.output

    def test_import_all_service_init_error(self, runner):
        """Test error when ImporterService initialization fails."""
        with runner.isolated_filesystem():
            # Create a mock taxonomy.csv file so the file existence check passes
            with open("taxonomy.csv", "w") as f:
                f.write("family,genus,species\n")
                f.write("Fabaceae,Acacia,Acacia mangium\n")

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch("niamoto.cli.commands.imports.validate_source_config"),
                mock.patch(
                    "niamoto.cli.commands.imports.get_source_path",
                    return_value="taxonomy.csv",
                ),
                mock.patch("os.path.exists", return_value=True),
                # Force an error during ImporterService initialization
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService",
                    side_effect=Exception("Cannot initialize ImporterService"),
                ),
            ):
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {
                    "taxonomy": {
                        "path": "taxonomy.csv",
                        "ranks": "family,genus,species",
                    }
                }

                # Call import_all with standard exception handling
                result = runner.invoke(import_all, [])

                assert result.exit_code == 1
                assert "Full import failed" in result.output


class TestImportPlots:
    """Tests for the import_plots command."""

    def test_import_plots_with_file_and_fields(self, runner):
        """Test importing plots with explicit file and fields."""
        with runner.isolated_filesystem():
            # Create a temporary CSV file with test data
            with open("plots.csv", "w") as f:
                f.write("id,location,locality\n")
                f.write("1,POINT(1 1),New Caledonia\n")

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer_cls,
                mock.patch("niamoto.cli.commands.imports.reset_table"),
                mock.patch("os.path.exists", return_value=True),
                # Patch validate_source_config so it doesn't raise exceptions
                mock.patch(
                    "niamoto.cli.commands.imports.validate_source_config"
                ) as mock_validate,
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"

                # Set up the source config
                source_config = {
                    "path": "plots.csv",
                    "identifier": "id",
                    "location_field": "location",
                    "locality_field": "locality",
                }
                mock_validate.return_value = source_config

                # Set up the importer mock
                importer_instance = mock.MagicMock()
                mock_importer_cls.return_value = importer_instance
                importer_instance.import_plots.return_value = (
                    "Successfully imported 1 plot"
                )

                # Call the CLI command
                result = runner.invoke(
                    import_plots,
                    [
                        "plots.csv",
                        "--id-field",
                        "id",
                        "--location-field",
                        "location",
                        "--locality-field",
                        "locality",
                    ],
                )

                assert result.exit_code == 0
                assert "Successfully imported 1 plot" in result.output
                mock_importer_cls.assert_called_once_with("/path/to/db.sqlite")
                importer_instance.import_plots.assert_called_once_with(
                    "plots.csv",
                    "id",
                    "location",
                    "locality",
                    link_field=None,
                    occurrence_link_field=None,
                    hierarchy_config=None,
                )

    def test_import_plots_with_link_fields(self, runner):
        """Test importing plots with link fields for occurrence relationships."""
        with runner.isolated_filesystem():
            # Create a temporary CSV file with test data
            with open("plots_with_links.csv", "w") as f:
                f.write("plot_id,geometry,region,taxon_id\n")
                f.write("1,POINT(1 1),Test1,001\n")
                f.write("2,POINT(2 2),Test2,002\n")

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer_cls,
                mock.patch("niamoto.cli.commands.imports.reset_table"),
                mock.patch("os.path.exists", return_value=True),
                # Patch validate_source_config so it doesn't raise exceptions
                mock.patch(
                    "niamoto.cli.commands.imports.validate_source_config"
                ) as mock_validate,
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"

                # Set up the source config
                source_config = {
                    "path": "plots_with_links.csv",
                    "identifier": "plot_id",
                    "location_field": "geometry",
                    "locality_field": "region",
                    "link_field": "taxon_id",
                    "occurrence_link_field": "taxon_id",
                }
                mock_validate.return_value = source_config

                # Set up the importer mock
                importer_instance = mock.MagicMock()
                mock_importer_cls.return_value = importer_instance
                importer_instance.import_plots.return_value = (
                    "Successfully imported 2 plots with taxon links"
                )

                # Call the CLI command
                result = runner.invoke(
                    import_plots,
                    [
                        "plots_with_links.csv",
                        "--id-field",
                        "plot_id",
                        "--location-field",
                        "geometry",
                        "--locality-field",
                        "region",
                        "--link-field",
                        "taxon_id",
                        "--occurrence-link-field",
                        "taxon_id",
                    ],
                )

                assert result.exit_code == 0
                assert "Successfully imported 2 plots with taxon links" in result.output
                mock_importer_cls.assert_called_once_with("/path/to/db.sqlite")
                importer_instance.import_plots.assert_called_once_with(
                    "plots_with_links.csv",
                    "plot_id",
                    "geometry",
                    "region",
                    link_field="taxon_id",
                    occurrence_link_field="taxon_id",
                    hierarchy_config=None,
                )

    def test_import_plots_from_config(self, runner):
        """Test importing plots using configuration."""
        with runner.isolated_filesystem():
            # Create a temporary CSV file
            with open("plots.csv", "w") as f:
                f.write("id,location,locality\n")
                f.write("1,POINT(1 1),New Caledonia\n")

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer_cls,
                mock.patch("niamoto.cli.commands.imports.reset_table"),
                mock.patch("os.path.exists", return_value=True),
                mock.patch(
                    "niamoto.cli.commands.imports.get_source_path",
                    return_value="plots.csv",
                ) as mock_get_source_path,
                # Patch validate_source_config so it doesn't raise exceptions
                mock.patch(
                    "niamoto.cli.commands.imports.validate_source_config"
                ) as mock_validate,
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"

                # Set up the source config
                source_config = {
                    "path": "plots.csv",
                    "identifier": "id",
                    "location_field": "location",
                    "locality_field": "locality",
                }
                mock_validate.return_value = source_config

                # Set up the importer mock
                importer_instance = mock.MagicMock()
                mock_importer_cls.return_value = importer_instance
                importer_instance.import_plots.return_value = (
                    "Successfully imported 1 plot"
                )

                # Call the CLI command
                result = runner.invoke(import_plots, [])

                assert result.exit_code == 0
                assert "Successfully imported 1 plot" in result.output
                mock_get_source_path.assert_called_once_with(config, "plots")
                mock_importer_cls.assert_called_once_with("/path/to/db.sqlite")
                importer_instance.import_plots.assert_called_once_with(
                    "plots.csv",
                    "id",
                    "location",
                    "locality",
                    link_field=None,
                    occurrence_link_field=None,
                    hierarchy_config=None,
                )

    def test_import_plots_missing_required_fields(self, runner):
        """Test error when required fields are missing."""
        with runner.isolated_filesystem():
            with mock.patch("niamoto.cli.commands.imports.Config") as mock_config:
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {
                    "plots": {
                        "path": "plots.csv",
                        # Missing id_field and location_field
                    }
                }

                # Mock the validation function to raise the appropriate error
                with mock.patch(
                    "niamoto.cli.commands.imports.validate_source_config"
                ) as mock_validate:
                    mock_validate.side_effect = ValidationError(
                        field="plots",
                        message="Missing required fields: identifier, location_field, locality_field",
                        details={
                            "missing": [
                                "identifier",
                                "location_field",
                                "locality_field",
                            ]
                        },
                    )

                    result = runner.invoke(import_plots, [])

                    assert result.exit_code == 1
                    assert "Missing required fields" in result.output

    def test_import_plots_file_not_found(self, runner):
        """Test error when plot file doesn't exist."""
        with runner.isolated_filesystem():
            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                # Patch validate_source_config first to return a config
                mock.patch(
                    "niamoto.cli.commands.imports.validate_source_config",
                    return_value={
                        "path": "nonexistent.csv",
                        "identifier": "id",
                        "location_field": "geom",
                        "locality_field": "local",
                    },
                ),
                # Then mock get_source_path to raise FileError
                mock.patch(
                    "niamoto.cli.commands.imports.get_source_path"
                ) as mock_get_source_path,
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {
                    "plots": {
                        "path": "nonexistent.csv",
                        "identifier": "id",
                        "location_field": "geom",
                        "locality_field": "local",
                    }
                }

                # Make get_source_path raise FileError
                mock_get_source_path.side_effect = FileError(
                    file_path="nonexistent.csv", message="File not found", details={}
                )

                result = runner.invoke(import_plots, [])

                assert result.exit_code == 1
                assert "File not found" in result.output


class TestImportOccurrences:
    """Tests for the import_occurrences command."""

    def test_import_occurrences_with_file_and_fields(self, runner):
        """Test importing occurrences with explicit file and fields."""
        with runner.isolated_filesystem():
            # Create a temporary CSV file with test data
            with open("occurrences.csv", "w") as f:
                f.write("taxon_id,location,date\n")
                f.write("1,POINT(1 1),2023-01-01\n")
                f.write("2,POINT(2 2),2023-01-02\n")

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer_cls,
                mock.patch("niamoto.cli.commands.imports.reset_table"),
                mock.patch("os.path.exists", return_value=True),
                # Patch validate_source_config so it doesn't raise exceptions
                mock.patch(
                    "niamoto.cli.commands.imports.validate_source_config"
                ) as mock_validate,
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {
                    "occurrences": {
                        "path": "occurrences.csv",
                        "identifier": "taxon_id",
                        "location_field": "location",
                    }
                }

                # Set up validation mock
                mock_validate.return_value = config.imports["occurrences"]

                # Setup the importer mock
                importer_instance = mock.MagicMock()
                mock_importer_cls.return_value = importer_instance
                importer_instance.import_occurrences.return_value = (
                    "Successfully imported 2 occurrences"
                )

                result = runner.invoke(
                    import_occurrences,
                    [
                        "occurrences.csv",
                        "--taxon-id",
                        "taxon_id",
                        "--location-field",
                        "location",
                    ],
                )

                assert result.exit_code == 0
                assert "Successfully imported 2 occurrences" in result.output
                importer_instance.import_occurrences.assert_called_once_with(
                    "occurrences.csv", "taxon_id", "location"
                )

    def test_import_occurrences_from_config(self, runner):
        """Test importing occurrences using configuration."""
        with runner.isolated_filesystem():
            # Create a temporary CSV file
            with open("occurrences.csv", "w") as f:
                f.write("taxon_id,location,date\n")
                f.write("1,POINT(1 1),2023-01-01\n")

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer_cls,
                mock.patch("niamoto.cli.commands.imports.reset_table"),
                mock.patch("os.path.exists", return_value=True),
                mock.patch(
                    "niamoto.cli.commands.imports.get_source_path",
                    return_value="occurrences.csv",
                ),
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {
                    "occurrences": {
                        "path": "occurrences.csv",
                        "identifier": "taxon_id",
                        "location_field": "location",
                    }
                }

                # Setup the importer mock
                importer_instance = mock.MagicMock()
                mock_importer_cls.return_value = importer_instance
                importer_instance.import_occurrences.return_value = (
                    "Successfully imported 1 occurrence"
                )

                result = runner.invoke(import_occurrences, [])

                assert result.exit_code == 0
                assert "Successfully imported 1 occurrence" in result.output
                importer_instance.import_occurrences.assert_called_once_with(
                    "occurrences.csv", "taxon_id", "location"
                )

    def test_import_occurrences_missing_required_fields(self, runner):
        """Test error when required fields are missing."""
        with runner.isolated_filesystem():
            with mock.patch("niamoto.cli.commands.imports.Config") as mock_config:
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {
                    "occurrences": {
                        "path": "occurrences.csv",
                        # Missing identifier and location_field
                    }
                }

                # Mock the validation function to raise the appropriate error
                with mock.patch(
                    "niamoto.cli.commands.imports.validate_source_config"
                ) as mock_validate:
                    mock_validate.side_effect = ValidationError(
                        field="occurrences",
                        message="Missing required fields: identifier, location_field",
                        details={"missing": ["identifier", "location_field"]},
                    )

                    result = runner.invoke(import_occurrences, [])

                    assert result.exit_code == 1
                    assert "Missing required fields" in result.output

    def test_import_occurrences_import_error(self, runner):
        """Test handling of import errors."""
        with runner.isolated_filesystem():
            # Create a temporary CSV file
            with open("occurrences.csv", "w") as f:
                f.write("taxon_id,location,date\n")
                f.write("1,POINT(1 1),2023-01-01\n")

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer_cls,
                mock.patch("niamoto.cli.commands.imports.reset_table"),
                mock.patch("os.path.exists", return_value=True),
                mock.patch(
                    "niamoto.cli.commands.imports.get_source_path",
                    return_value="occurrences.csv",
                ),
                # Patch validate_source_config so it doesn't raise exceptions
                mock.patch(
                    "niamoto.cli.commands.imports.validate_source_config"
                ) as mock_validate,
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"

                # Set up the source config
                source_config = {
                    "path": "occurrences.csv",
                    "identifier": "taxon_id",
                    "location_field": "location",
                }
                mock_validate.return_value = source_config

                # Setup the importer mock and make it fail
                error_message = "Invalid data format"
                importer_instance = mock.MagicMock()
                importer_instance.import_occurrences.side_effect = Exception(
                    error_message
                )
                mock_importer_cls.return_value = importer_instance

                result = runner.invoke(import_occurrences, [])

                assert result.exit_code == 1
                assert "Occurrences import failed" in result.output


class TestImportShapes:
    """Tests for the import_shapes command."""

    def test_import_shapes(self, runner):
        """Test importing shapes."""
        with runner.isolated_filesystem():
            # Create a temporary GeoJSON file
            with open("shapes.geojson", "w") as f:
                f.write('{"type": "FeatureCollection", "features": []}')

            with (
                mock.patch("niamoto.cli.commands.imports.Config") as mock_config,
                mock.patch(
                    "niamoto.cli.commands.imports.ImporterService"
                ) as mock_importer,
            ):
                # Configure mocks
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                shapes_config = [
                    {
                        "path": "shapes.geojson",
                        "category": "protected_areas",
                        "identifier": "id",
                    }
                ]
                config.imports = {"shapes": shapes_config}

                mock_importer.return_value.import_shapes.return_value = (
                    "Successfully imported 1 shape category"
                )

                result = runner.invoke(import_shapes)

                assert result.exit_code == 0
                assert "Successfully imported 1 shape category" in result.output
                mock_importer.return_value.import_shapes.assert_called_once_with(
                    shapes_config
                )

    def test_import_shapes_no_config(self, runner):
        """Test error when shapes configuration is missing."""
        with runner.isolated_filesystem():
            with mock.patch("niamoto.cli.commands.imports.Config") as mock_config:
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {}  # Empty config, missing shapes

                result = runner.invoke(import_shapes)

                assert result.exit_code == 1
                assert "No shapes configuration found" in result.output

    def test_import_shapes_invalid_config(self, runner):
        """Test error when shapes configuration is invalid."""
        with runner.isolated_filesystem():
            with mock.patch("niamoto.cli.commands.imports.Config") as mock_config:
                config = mock_config.return_value
                config.database_path = "/path/to/db.sqlite"
                config.imports = {
                    "shapes": "not_a_list"
                }  # Invalid config, should be a list

                result = runner.invoke(import_shapes)

                assert result.exit_code == 1
                assert "invalid format" in result.output


class TestUtilityFunctions:
    """Tests for utility functions in imports.py."""

    def test_validate_source_config_valid(self):
        """Test validate_source_config with valid configuration."""
        sources = {
            "taxonomy": {"path": "taxonomy.csv", "ranks": "family,genus,species"}
        }
        required_fields = ["path", "ranks"]

        # Mock the error_handler decorator to call the function directly
        with mock.patch(
            "niamoto.common.utils.error_handler", lambda **kwargs: lambda func: func
        ):
            result = validate_source_config(sources, "taxonomy", required_fields)
            assert result == sources["taxonomy"]

    def test_validate_source_config_missing_source(self):
        """Test validate_source_config with missing source."""
        sources = {}
        required_fields = ["path", "ranks"]

        # Mock the error_handler decorator to call the function directly
        with mock.patch(
            "niamoto.common.utils.error_handler", lambda **kwargs: lambda func: func
        ):
            with pytest.raises(ConfigurationError) as excinfo:
                validate_source_config(sources, "taxonomy", required_fields)

            assert "Source 'taxonomy' not found in configuration" in str(excinfo.value)

    def test_validate_source_config_missing_fields(self):
        """Test validate_source_config with missing required fields."""
        sources = {
            "taxonomy": {
                "path": "taxonomy.csv",
                # Missing ranks field
            }
        }
        required_fields = ["path", "ranks"]

        # Mock the error_handler decorator to call the function directly
        with mock.patch(
            "niamoto.common.utils.error_handler", lambda **kwargs: lambda func: func
        ):
            with pytest.raises(ValidationError) as excinfo:
                validate_source_config(sources, "taxonomy", required_fields)

            assert "Missing required fields" in str(excinfo.value)
            assert "ranks" in str(excinfo.value)

    def test_get_source_path_valid(self):
        """Test get_source_path with valid configuration."""
        with (
            mock.patch("os.path.isabs", return_value=True),
            mock.patch("os.path.exists", return_value=True),
            # Mock the error_handler decorator to call the function directly
            mock.patch(
                "niamoto.common.utils.error_handler", lambda **kwargs: lambda func: func
            ),
        ):
            config = mock.MagicMock()
            config.imports = {"taxonomy": {"path": "/path/to/taxonomy.csv"}}

            result = get_source_path(config, "taxonomy")

            assert result == "/path/to/taxonomy.csv"

    def test_get_source_path_relative(self):
        """Test get_source_path with relative path."""
        with (
            mock.patch("os.path.isabs", return_value=False),
            mock.patch("os.path.exists", return_value=True),
            mock.patch(
                "os.path.join", return_value="/niamoto_home/imports/taxonomy.csv"
            ),
            # Mock the error_handler decorator to call the function directly
            mock.patch(
                "niamoto.common.utils.error_handler", lambda **kwargs: lambda func: func
            ),
        ):
            config = mock.MagicMock()
            config.imports = {"taxonomy": {"path": "imports/taxonomy.csv"}}
            config.get_niamoto_home.return_value = "/niamoto_home"

            result = get_source_path(config, "taxonomy")

            assert result == "/niamoto_home/imports/taxonomy.csv"

    def test_get_source_path_missing(self):
        """Test get_source_path with missing path."""
        config = mock.MagicMock()
        config.imports = {
            "taxonomy": {}  # Missing path
        }

        with pytest.raises(ConfigurationError):
            get_source_path(config, "taxonomy")

    def test_get_source_path_not_found(self):
        """Test get_source_path with non-existent file."""
        with (
            mock.patch("os.path.isabs", return_value=True),
            mock.patch("os.path.exists", return_value=False),
        ):
            config = mock.MagicMock()
            config.imports = {"taxonomy": {"path": "/path/to/nonexistent.csv"}}

            with pytest.raises(ConfigurationError):
                get_source_path(config, "taxonomy")
