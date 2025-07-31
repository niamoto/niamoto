"""
Tests for the PlotImporter class.
"""

from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.errors import GEOSException

from niamoto.core.components.imports.plots import PlotImporter
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
    DatabaseError,
)
from tests.common.base_test import NiamotoTestCase


class TestPlotImporter(NiamotoTestCase):
    """Test case for the PlotImporter class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = MagicMock()
        self.mock_db.db_path = "mock_db_path"
        self.mock_db.engine = MagicMock()
        self.importer = PlotImporter(self.mock_db)

    def test_init(self):
        """Test initialization of PlotImporter."""
        self.assertEqual(self.importer.db, self.mock_db)
        self.assertEqual(self.importer.db_path, "mock_db_path")
        self.assertEqual(self.importer.link_field, "locality")
        self.assertEqual(self.importer.occurrence_link_field, "plot_name")

    def test_set_link_field(self):
        """Test setting link field."""
        self.importer.set_link_field("custom_field")
        self.assertEqual(self.importer.link_field, "custom_field")

    def test_set_occurrence_link_field(self):
        """Test setting occurrence link field."""
        self.importer.set_occurrence_link_field("custom_occurrence_field")
        self.assertEqual(self.importer.occurrence_link_field, "custom_occurrence_field")

    # Tests for import_plots main entry point
    @patch("pathlib.Path.exists")
    def test_import_plots_file_not_found(self, mock_exists):
        """Test import_plots with non-existent file."""
        mock_exists.return_value = False

        with self.assertRaises(FileReadError) as context:
            self.importer.import_plots("nonexistent.gpkg", "id", "location", "locality")

        self.assertIn("File not found", str(context.exception))

    @patch("pathlib.Path.exists")
    def test_import_plots_unsupported_format(self, mock_exists):
        """Test import_plots with unsupported file format."""
        mock_exists.return_value = True

        with self.assertRaises(DataValidationError) as context:
            self.importer.import_plots("test.txt", "id", "location", "locality")

        self.assertIn("Unsupported file format", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch.object(PlotImporter, "import_from_gpkg")
    def test_import_plots_gpkg_delegation(self, mock_import_gpkg, mock_exists):
        """Test import_plots delegates to import_from_gpkg for .gpkg files."""
        mock_exists.return_value = True
        mock_import_gpkg.return_value = "Success message"

        result = self.importer.import_plots("test.gpkg", "id", "location", "locality")

        self.assertEqual(result, "Success message")
        mock_import_gpkg.assert_called_once()

    @patch("pathlib.Path.exists")
    @patch.object(PlotImporter, "import_from_csv")
    def test_import_plots_csv_delegation(self, mock_import_csv, mock_exists):
        """Test import_plots delegates to import_from_csv for .csv files."""
        mock_exists.return_value = True
        mock_import_csv.return_value = "Success message"

        result = self.importer.import_plots("test.csv", "id", "location", "locality")

        self.assertEqual(result, "Success message")
        mock_import_csv.assert_called_once()

    @patch("pathlib.Path.exists")
    @patch.object(PlotImporter, "import_from_gpkg")
    def test_import_plots_geometry_error_conversion(
        self, mock_import_gpkg, mock_exists
    ):
        """Test import_plots converts geometry errors to DataValidationError."""
        mock_exists.return_value = True
        mock_import_gpkg.side_effect = Exception("invalid geometry")

        with self.assertRaises(DataValidationError) as context:
            self.importer.import_plots("test.gpkg", "id", "location", "locality")

        self.assertIn("Invalid geometry", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch.object(PlotImporter, "import_from_gpkg")
    def test_import_plots_reraises_specific_errors(self, mock_import_gpkg, mock_exists):
        """Test import_plots re-raises specific error types."""
        mock_exists.return_value = True

        # Test FileReadError
        mock_import_gpkg.side_effect = FileReadError("test.gpkg", "Read error")
        with self.assertRaises(FileReadError):
            self.importer.import_plots("test.gpkg", "id", "location", "locality")

        # Test DataValidationError
        mock_import_gpkg.side_effect = DataValidationError("Validation error", [])
        with self.assertRaises(DataValidationError):
            self.importer.import_plots("test.gpkg", "id", "location", "locality")

    # Tests for GPKG import
    @patch("geopandas.read_file")
    @patch("pathlib.Path.exists")
    def test_import_from_gpkg_success(self, mock_exists, mock_read_file):
        """Test successful GPKG import."""
        mock_exists.return_value = True

        # Create mock GeoDataFrame
        geometry = [Point(165.5, -21.5), Point(166.0, -22.0)]
        mock_gdf = gpd.GeoDataFrame(
            {
                "plot_id": [1, 2],
                "locality": ["Site1", "Site2"],
                "location": ["Loc1", "Loc2"],
                "geometry": geometry,
            }
        )
        mock_read_file.return_value = mock_gdf

        with patch.object(self.importer, "_process_plots_data", return_value=2):
            with patch.object(
                self.importer, "link_occurrences_to_plots", return_value=5
            ):
                result = self.importer.import_from_gpkg(
                    "test.gpkg", "plot_id", "location", link_occurrences=True
                )

        self.assertIn("2 plots imported", result)
        self.assertIn("5 occurrences linked", result)

    @patch("geopandas.read_file")
    @patch("pathlib.Path.exists")
    def test_import_from_gpkg_missing_columns(self, mock_exists, mock_read_file):
        """Test GPKG import with missing required columns."""
        mock_exists.return_value = True

        # Missing 'locality' column
        geometry = [Point(165.5, -21.5)]
        mock_gdf = gpd.GeoDataFrame(
            {"plot_id": [1], "location": ["Loc1"], "geometry": geometry}
        )
        mock_read_file.return_value = mock_gdf

        with self.assertRaises(DataValidationError) as context:
            self.importer.import_from_gpkg("test.gpkg", "plot_id", "location")

        self.assertIn("Missing required columns", str(context.exception))

    @patch("geopandas.read_file")
    @patch("pathlib.Path.exists")
    def test_import_from_gpkg_read_error(self, mock_exists, mock_read_file):
        """Test GPKG import with file read error."""
        mock_exists.return_value = True
        mock_read_file.side_effect = Exception("Cannot read file")

        with self.assertRaises(FileReadError) as context:
            self.importer.import_from_gpkg("test.gpkg", "plot_id", "location")

        self.assertIn("Failed to read GeoPackage file", str(context.exception))

    @patch("geopandas.read_file")
    @patch("pathlib.Path.exists")
    def test_import_from_gpkg_geos_exception(self, mock_exists, mock_read_file):
        """Test GPKG import with GEOS geometry exception."""
        mock_exists.return_value = True
        mock_read_file.side_effect = GEOSException("LinearRing error")

        with self.assertRaises(DataValidationError) as context:
            self.importer.import_from_gpkg("test.gpkg", "plot_id", "location")

        self.assertIn("Invalid geometry", str(context.exception))

    @patch("geopandas.read_file")
    @patch("pathlib.Path.exists")
    def test_import_from_gpkg_invalid_geodataframe(self, mock_exists, mock_read_file):
        """Test GPKG import with invalid GeoDataFrame."""
        mock_exists.return_value = True
        mock_read_file.return_value = "not a geodataframe"

        with self.assertRaises(FileReadError) as context:
            self.importer.import_from_gpkg("test.gpkg", "plot_id", "location")

        self.assertIn("Failed to read GeoPackage file", str(context.exception))

    # Tests for CSV import
    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="id,locality,geometry\n1,Site1,POINT(165.5 -21.5)\n",
    )
    def test_import_from_csv_success(self, mock_file, mock_exists, mock_read_csv):
        """Test successful CSV import."""
        mock_exists.return_value = True

        # Mock CSV data
        mock_df = pd.DataFrame(
            {
                "id": [1, 2],
                "locality": ["Site1", "Site2"],
                "geometry": ["POINT(165.5 -21.5)", "POINT(166.0 -22.0)"],
            }
        )
        mock_read_csv.return_value = mock_df

        with patch.object(self.importer, "_process_plots_data", return_value=2):
            with patch.object(
                self.importer, "link_occurrences_to_plots", return_value=3
            ):
                result = self.importer.import_from_csv(
                    "test.csv", "id", "geometry", "locality", link_occurrences=True
                )

        self.assertIn("2 plots imported", result)
        self.assertIn("3 occurrences linked", result)

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="header\n")
    def test_import_from_csv_missing_columns(
        self, mock_file, mock_exists, mock_read_csv
    ):
        """Test CSV import with missing required columns."""
        mock_exists.return_value = True

        mock_df = pd.DataFrame(
            {
                "id": [1],
                # Missing 'locality' and 'geometry' columns
            }
        )
        mock_read_csv.return_value = mock_df

        with self.assertRaises(DataValidationError) as context:
            self.importer.import_from_csv("test.csv", "id", "geometry", "locality")

        self.assertIn("Missing required columns", str(context.exception))

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="header\n")
    def test_import_from_csv_geometry_parsing_error(
        self, mock_file, mock_exists, mock_read_csv
    ):
        """Test CSV import with geometry parsing errors."""
        mock_exists.return_value = True

        mock_df = pd.DataFrame(
            {
                "id": [1, 2],
                "locality": ["Site1", "Site2"],
                "geometry": ["INVALID_GEOMETRY", "POINT(166.0 -22.0)"],
            }
        )
        mock_read_csv.return_value = mock_df

        with self.assertRaises(DataValidationError) as context:
            self.importer.import_from_csv("test.csv", "id", "geometry", "locality")

        self.assertIn("Failed to parse geometries", str(context.exception))

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="header\n")
    def test_import_from_csv_wkb_geometry(self, mock_file, mock_exists, mock_read_csv):
        """Test CSV import with WKB geometry format."""
        mock_exists.return_value = True

        # Valid WKB hex string for POINT(1 1)
        wkb_hex = "0101000000000000000000F03F000000000000F03F"

        mock_df = pd.DataFrame(
            {"id": [1], "locality": ["Site1"], "geometry": [wkb_hex]}
        )
        mock_read_csv.return_value = mock_df

        with patch("shapely.wkt.loads", side_effect=Exception("Not WKT")):
            with patch("shapely.wkb.loads", return_value=Point(1, 1)):
                with patch.object(self.importer, "_process_plots_data", return_value=1):
                    result = self.importer.import_from_csv(
                        "test.csv", "id", "geometry", "locality"
                    )

        self.assertIn("1 plots imported", result)

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="header\n")
    def test_import_from_csv_delimiter_detection(
        self, mock_file, mock_exists, mock_read_csv
    ):
        """Test CSV import with delimiter detection."""
        mock_exists.return_value = True

        # Mock file content with semicolon delimiter
        mock_file.return_value.read.return_value = (
            "id;locality;geometry\n1;Site1;POINT(165.5 -21.5)\n"
        )

        mock_df = pd.DataFrame(
            {"id": [1], "locality": ["Site1"], "geometry": ["POINT(165.5 -21.5)"]}
        )
        mock_read_csv.return_value = mock_df

        with patch.object(self.importer, "_process_plots_data", return_value=1):
            self.importer.import_from_csv("test.csv", "id", "geometry", "locality")

        # Verify read_csv was called with detected delimiter
        mock_read_csv.assert_called_once()

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", side_effect=Exception("File read error"))
    def test_import_from_csv_file_read_error(
        self, mock_file, mock_exists, mock_read_csv
    ):
        """Test CSV import with file read error."""
        mock_exists.return_value = True

        with self.assertRaises(DataValidationError) as context:
            self.importer.import_from_csv("test.csv", "id", "geometry", "locality")

        self.assertIn("Failed to import plots from CSV", str(context.exception))

    # Tests for hierarchical import
    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="header\n")
    def test_import_from_csv_hierarchical(self, mock_file, mock_exists, mock_read_csv):
        """Test CSV import with hierarchical configuration."""
        mock_exists.return_value = True

        mock_df = pd.DataFrame(
            {
                "plot_name": ["P1", "P2"],
                "locality_name": ["Loc1", "Loc1"],
                "country": ["New Caledonia", "New Caledonia"],
                "geometry": ["POINT(165.5 -21.5)", "POINT(166.0 -22.0)"],
            }
        )
        mock_read_csv.return_value = mock_df

        hierarchy_config = {
            "enabled": True,
            "levels": ["plot_name", "locality_name", "country"],
            "aggregate_geometry": True,
        }

        with patch.object(
            self.importer, "_process_hierarchical_plots_data", return_value=2
        ):
            result = self.importer.import_from_csv(
                "test.csv",
                "plot_name",
                "geometry",
                "locality_name",
                hierarchy_config=hierarchy_config,
            )

        self.assertIn("2 plots imported", result)

    # Tests for _process_plots_data
    def test_process_plots_data_success(self):
        """Test successful plot data processing."""
        geometry = [Point(165.5, -21.5), Point(166.0, -22.0)]
        plots_data = gpd.GeoDataFrame(
            {"id": [1, 2], "locality": ["Site1", "Site2"], "geometry": geometry}
        )

        mock_session = MagicMock()
        self.mock_db.session.return_value.__enter__.return_value = mock_session

        with patch.object(self.importer, "_import_plot", return_value=True):
            result = self.importer._process_plots_data(plots_data, "id", "locality")

        self.assertEqual(result, 2)
        mock_session.commit.assert_called_once()

    def test_process_plots_data_database_error(self):
        """Test plot data processing with database error."""
        from sqlalchemy.exc import SQLAlchemyError

        geometry = [Point(165.5, -21.5)]
        plots_data = gpd.GeoDataFrame(
            {"id": [1], "locality": ["Site1"], "geometry": geometry}
        )

        mock_session = MagicMock()
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        self.mock_db.session.return_value.__enter__.return_value = mock_session

        with patch.object(self.importer, "_import_plot", return_value=True):
            with self.assertRaises(DatabaseError):
                self.importer._process_plots_data(plots_data, "id", "locality")

        mock_session.rollback.assert_called_once()

    # Tests for _import_plot
    def test_import_plot_success(self):
        """Test successful single plot import."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        geometry = Point(165.5, -21.5)
        row = pd.Series({"id": 1, "locality": "Site1", "geometry": geometry})

        with patch.object(PlotImporter, "validate_geometry"):
            result = self.importer._import_plot(mock_session, row, "id", "locality")

        self.assertTrue(result)
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_import_plot_existing_plot(self):
        """Test import of existing plot (should skip)."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            MagicMock()
        )

        geometry = Point(165.5, -21.5)
        row = pd.Series({"id": 1, "locality": "Site1", "geometry": geometry})

        with patch.object(PlotImporter, "validate_geometry"):
            result = self.importer._import_plot(mock_session, row, "id", "locality")

        self.assertFalse(result)
        mock_session.add.assert_not_called()

    def test_import_plot_missing_geometry(self):
        """Test import plot with missing geometry."""
        mock_session = MagicMock()

        row = pd.Series({"id": 1, "locality": "Site1", "geometry": None})

        with self.assertRaises(DataValidationError) as context:
            self.importer._import_plot(mock_session, row, "id", "locality")

        self.assertIn("Missing geometry", str(context.exception))

    def test_import_plot_empty_geometry(self):
        """Test import plot with empty geometry."""
        mock_session = MagicMock()

        empty_geom = MagicMock()
        empty_geom.is_empty = True
        row = pd.Series({"id": 1, "locality": "Site1", "geometry": empty_geom})

        with self.assertRaises(DataValidationError) as context:
            self.importer._import_plot(mock_session, row, "id", "locality")

        self.assertIn("Missing geometry", str(context.exception))

    def test_import_plot_invalid_id_type(self):
        """Test import plot with invalid ID type."""
        mock_session = MagicMock()

        geometry = Point(165.5, -21.5)
        row = pd.Series(
            {
                "id": "invalid_id",  # Cannot convert to int
                "locality": "Site1",
                "geometry": geometry,
            }
        )

        with self.assertRaises(DataValidationError) as context:
            self.importer._import_plot(mock_session, row, "id", "locality")

        self.assertIn("Invalid plot identifier value", str(context.exception))

    def test_import_plot_invalid_locality(self):
        """Test import plot with empty locality - should use fallback."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.add = MagicMock()
        mock_session.flush = MagicMock()

        geometry = Point(165.5, -21.5)
        row = pd.Series(
            {
                "id": 1,
                "locality": "",  # Empty locality
                "geometry": geometry,
            }
        )

        # Should not raise an error, but use fallback value "Plot_1"
        result = self.importer._import_plot(mock_session, row, "id", "locality")
        self.assertTrue(result)

        # Check that a plot was added with the fallback locality
        mock_session.add.assert_called_once()
        added_plot = mock_session.add.call_args[0][0]
        self.assertEqual(added_plot.locality, "Plot_1")

    def test_import_plot_none_locality(self):
        """Test import plot with 'None' string locality."""
        mock_session = MagicMock()

        geometry = Point(165.5, -21.5)
        row = pd.Series(
            {
                "id": 1,
                "locality": "None",  # String 'None'
                "geometry": geometry,
            }
        )

        with self.assertRaises(DataValidationError) as context:
            self.importer._import_plot(mock_session, row, "id", "locality")

        self.assertIn("Invalid locality", str(context.exception))

    def test_import_plot_invalid_geometry_validation(self):
        """Test import plot with geometry that fails validation."""
        mock_session = MagicMock()

        invalid_geom = MagicMock()
        invalid_geom.is_valid = False
        invalid_geom.is_empty = False
        row = pd.Series({"id": 1, "locality": "Site1", "geometry": invalid_geom})

        with patch(
            "niamoto.core.components.imports.plots.explain_validity",
            return_value="Self-intersection",
        ):
            with self.assertRaises(DataValidationError) as context:
                self.importer._import_plot(mock_session, row, "id", "locality")

        self.assertIn("Invalid geometry", str(context.exception))

    def test_import_plot_geometry_conversion_error(self):
        """Test import plot with geometry conversion error."""
        mock_session = MagicMock()

        geometry = MagicMock()
        geometry.is_valid = True
        geometry.is_empty = False  # Make sure it's not empty
        row = pd.Series({"id": 1, "locality": "Site1", "geometry": geometry})

        with patch("shapely.wkt.dumps", side_effect=GEOSException("Conversion error")):
            with self.assertRaises(DataValidationError) as context:
                self.importer._import_plot(mock_session, row, "id", "locality")

        self.assertIn("Invalid geometry in conversion", str(context.exception))

    def test_import_plot_fallback_locality_field(self):
        """Test import plot with fallback to identifier for locality."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        geometry = Point(165.5, -21.5)
        row = pd.Series(
            {
                "id": 1,
                "geometry": geometry,
                # No 'locality' field
            }
        )

        with patch.object(PlotImporter, "validate_geometry"):
            result = self.importer._import_plot(mock_session, row, "id")

        self.assertTrue(result)
        # Verify the plot was created with ID as locality
        added_plot = mock_session.add.call_args[0][0]
        self.assertEqual(added_plot.locality, "1")

    # Tests for validate_geometry static method
    def test_validate_geometry_valid_point(self):
        """Test validate_geometry with valid point WKT."""
        wkt = "POINT(165.5 -21.5)"
        # Should not raise exception
        PlotImporter.validate_geometry(wkt)

    def test_validate_geometry_valid_polygon(self):
        """Test validate_geometry with valid polygon WKT."""
        wkt = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
        # Should not raise exception
        PlotImporter.validate_geometry(wkt)

    def test_validate_geometry_empty_string(self):
        """Test validate_geometry with empty string."""
        with self.assertRaises(DataValidationError) as context:
            PlotImporter.validate_geometry("")

        self.assertIn("Empty geometry", str(context.exception))

    def test_validate_geometry_none(self):
        """Test validate_geometry with None."""
        with self.assertRaises(DataValidationError) as context:
            PlotImporter.validate_geometry(None)

        self.assertIn("Empty geometry", str(context.exception))

    def test_validate_geometry_invalid_wkt(self):
        """Test validate_geometry with invalid WKT."""
        with self.assertRaises(DataValidationError) as context:
            PlotImporter.validate_geometry("INVALID WKT")

        self.assertIn("Invalid geometry", str(context.exception))

    def test_validate_geometry_geos_exception(self):
        """Test validate_geometry handling GEOS exception."""
        from shapely.errors import GEOSException

        with patch(
            "niamoto.core.components.imports.plots.loads",
            side_effect=GEOSException("GEOS error"),
        ):
            with self.assertRaises(DataValidationError) as context:
                PlotImporter.validate_geometry("POINT(1 1)")

        self.assertIn("Invalid geometry", str(context.exception))

    def test_validate_geometry_empty_geometry_object(self):
        """Test validate_geometry with empty geometry object."""

        # Create a simple class that mimics an empty geometry
        class EmptyGeometry:
            @property
            def is_empty(self):
                return True

            @property
            def is_valid(self):
                return True  # Valid but empty

        empty_geom = EmptyGeometry()

        with patch(
            "niamoto.core.components.imports.plots.loads", return_value=empty_geom
        ):
            with patch(
                "niamoto.core.components.imports.plots.explain_validity"
            ):  # Mock this too
                with self.assertRaises(DataValidationError) as context:
                    PlotImporter.validate_geometry("POINT EMPTY")

        # The exception gets caught and re-wrapped as "Invalid geometry"
        self.assertIn("Invalid geometry", str(context.exception))

    def test_validate_geometry_invalid_geometry_object(self):
        """Test validate_geometry with invalid geometry object."""

        # Create a simple class that mimics an invalid geometry
        class InvalidGeometry:
            @property
            def is_empty(self):
                return False

            @property
            def is_valid(self):
                return False

        invalid_geom = InvalidGeometry()

        with patch(
            "niamoto.core.components.imports.plots.loads", return_value=invalid_geom
        ):
            with patch(
                "niamoto.core.components.imports.plots.explain_validity",
                return_value="Self-intersection",
            ):
                with self.assertRaises(DataValidationError) as context:
                    PlotImporter.validate_geometry("POLYGON((0 0, 1 1, 1 0, 0 1, 0 0))")

        self.assertIn("Failed to validate geometry", str(context.exception))

    # Tests for occurrence linking
    def test_link_occurrences_to_plots_success(self):
        """Test successful occurrence linking."""
        with patch.object(self.importer, "_ensure_plot_ref_id_column_exists"):
            with patch.object(
                self.importer, "_extract_count_from_result", return_value=1
            ):
                # Mock successful bulk update
                mock_result = MagicMock()
                mock_result.rowcount = 5
                self.mock_db.execute_sql.return_value = mock_result

                result = self.importer.link_occurrences_to_plots()

        self.assertEqual(result, 5)

    def test_link_occurrences_to_plots_missing_column(self):
        """Test occurrence linking with missing occurrence_link_field column."""
        with patch.object(self.importer, "_ensure_plot_ref_id_column_exists"):
            with patch.object(
                self.importer, "_extract_count_from_result", return_value=0
            ):
                with self.assertRaises(DatabaseError) as context:
                    self.importer.link_occurrences_to_plots()

        self.assertIn("does not exist in occurrences table", str(context.exception))

    def test_link_occurrences_to_plots_fallback_method(self):
        """Test occurrence linking fallback to individual updates."""
        with patch.object(self.importer, "_ensure_plot_ref_id_column_exists"):
            with patch.object(
                self.importer, "_extract_count_from_result", return_value=1
            ):
                # Mock column check
                column_check_result = 1
                # Mock bulk update failure, then individual success
                mock_result_bulk = MagicMock()
                mock_result_bulk.rowcount = 0

                mock_result_match = [(1, 10), (2, 20)]  # occurrence_id, plot_id pairs
                mock_result_individual = MagicMock()
                mock_result_individual.rowcount = 1

                self.mock_db.execute_sql.side_effect = [
                    column_check_result,  # Column exists check
                    mock_result_bulk,  # Bulk update result
                    mock_result_match,  # Match query result
                    mock_result_individual,  # First individual update
                    mock_result_individual,  # Second individual update
                ]

                result = self.importer.link_occurrences_to_plots()

        self.assertEqual(result, 2)

    def test_link_occurrences_to_plots_no_matches(self):
        """Test occurrence linking with no matches found."""
        with patch.object(self.importer, "_ensure_plot_ref_id_column_exists"):
            with patch.object(
                self.importer, "_extract_count_from_result", return_value=1
            ):
                # Mock column check
                column_check_result = 1
                # Mock bulk update returns 0, no matches found
                mock_result_bulk = MagicMock()
                mock_result_bulk.rowcount = 0

                self.mock_db.execute_sql.side_effect = [
                    column_check_result,  # Column exists check
                    mock_result_bulk,  # Bulk update result
                    [],  # No matches
                ]

                result = self.importer.link_occurrences_to_plots()

        self.assertEqual(result, 0)

    def test_link_occurrences_by_plot_name_success(self):
        """Test linking occurrences by specific plot name."""
        plot_link_value = "TestPlot"

        with patch.object(self.importer, "_ensure_plot_ref_id_column_exists"):
            with patch.object(
                self.importer, "_extract_count_from_result", return_value=1
            ):
                # Mock column check
                column_check_result = 1
                # Mock plot found
                plot_result = [123]  # plot_id
                # Mock matching occurrences
                match_result = [(1,), (2,), (3,)]  # occurrence_ids
                # Mock update result
                update_result = MagicMock()
                update_result.rowcount = 3

                self.mock_db.execute_sql.side_effect = [
                    column_check_result,  # Column exists check
                    plot_result,  # Plot query
                    match_result,  # Match query
                    update_result,  # Update query
                ]

                result = self.importer.link_occurrences_by_plot_name(plot_link_value)

        self.assertEqual(result, 3)

    def test_link_occurrences_by_plot_name_plot_not_found(self):
        """Test linking occurrences by plot name when plot not found."""
        plot_link_value = "NonexistentPlot"

        with patch.object(self.importer, "_ensure_plot_ref_id_column_exists"):
            with patch.object(
                self.importer, "_extract_count_from_result", return_value=1
            ):
                # Mock no plot found
                self.mock_db.execute_sql.return_value = []

                with self.assertRaises(DataValidationError) as context:
                    self.importer.link_occurrences_by_plot_name(plot_link_value)

        self.assertIn("Plot not found", str(context.exception))

    def test_ensure_plot_ref_id_column_exists_creates_column(self):
        """Test _ensure_plot_ref_id_column_exists creates missing column."""
        # Mock table exists but column doesn't
        table_result = [("occurrences",)]
        column_result = []

        with patch.object(self.importer, "_extract_count_from_result", side_effect=[0]):
            self.mock_db.execute_sql.side_effect = [table_result, column_result, None]

            self.importer._ensure_plot_ref_id_column_exists()

            # Verify ALTER TABLE was called
            calls = self.mock_db.execute_sql.call_args_list
            self.assertEqual(len(calls), 3)  # Check table, check column, create column

    def test_ensure_plot_ref_id_column_exists_table_missing(self):
        """Test _ensure_plot_ref_id_column_exists with missing occurrences table."""
        # Mock table doesn't exist
        self.mock_db.execute_sql.return_value = []

        with self.assertRaises(DatabaseError) as context:
            self.importer._ensure_plot_ref_id_column_exists()

        self.assertIn("Occurrences table does not exist", str(context.exception))

    def test_extract_count_from_result_various_formats(self):
        """Test _extract_count_from_result with various result formats."""
        # Test with integer
        self.assertEqual(self.importer._extract_count_from_result(5), 5)

        # Test with list
        self.assertEqual(self.importer._extract_count_from_result([3]), 3)

        # Test with nested list
        self.assertEqual(self.importer._extract_count_from_result([[7]]), 7)

        # Test with tuple
        self.assertEqual(self.importer._extract_count_from_result((2,)), 2)

        # Test with mock Row object
        mock_row = MagicMock()
        mock_row.__getitem__.return_value = 4
        mock_row.__iter__ = lambda x: iter([4])
        self.assertEqual(self.importer._extract_count_from_result(mock_row), 4)

        # Test with empty list
        self.assertEqual(self.importer._extract_count_from_result([]), 0)

        # Test with invalid data
        self.assertEqual(self.importer._extract_count_from_result("invalid"), 0)

    # Tests for hierarchical import methods
    def test_process_hierarchical_plots_data_success(self):
        """Test successful hierarchical plots data processing."""
        geometry = [Point(165.5, -21.5), Point(166.0, -22.0)]
        plots_data = gpd.GeoDataFrame(
            {
                "plot_name": ["P1", "P2"],
                "locality_name": ["Loc1", "Loc1"],
                "country": ["New Caledonia", "New Caledonia"],
                "geometry": geometry,
            }
        )

        hierarchy_config = {
            "levels": ["plot_name", "locality_name", "country"],
            "aggregate_geometry": True,
        }

        mock_session = MagicMock()
        self.mock_db.session.return_value.__enter__.return_value = mock_session

        with patch.object(self.importer, "_import_hierarchy_level", return_value=1):
            with patch.object(
                self.importer, "_import_plot_hierarchical", return_value=True
            ):
                with patch.object(self.importer, "_update_nested_set_values"):
                    result = self.importer._process_hierarchical_plots_data(
                        plots_data, "plot_name", "locality_name", hierarchy_config
                    )

        self.assertEqual(result, 2)

    def test_process_hierarchical_plots_data_missing_columns(self):
        """Test hierarchical processing with missing columns."""
        geometry = [Point(165.5, -21.5)]
        plots_data = gpd.GeoDataFrame(
            {
                "plot_name": ["P1"],
                # Missing 'locality_name' and 'country'
                "geometry": geometry,
            }
        )

        hierarchy_config = {"levels": ["plot_name", "locality_name", "country"]}

        with self.assertRaises(DataValidationError) as context:
            self.importer._process_hierarchical_plots_data(
                plots_data, "plot_name", "locality_name", hierarchy_config
            )

        self.assertIn("Missing hierarchy columns", str(context.exception))

    def test_import_hierarchy_level_new_entity(self):
        """Test importing new hierarchy level entity."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        geometry = [Point(165.5, -21.5), Point(166.0, -22.0)]
        data = gpd.GeoDataFrame(
            {
                "locality_name": ["Loc1", "Loc1"],
                "country": ["New Caledonia", "New Caledonia"],
                "geometry": geometry,
            }
        )

        with patch("shapely.ops.unary_union", return_value=Point(165.75, -21.75)):
            self.importer._import_hierarchy_level(
                mock_session, "Loc1", "locality", data, "locality_name", True
            )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_import_hierarchy_level_existing_entity(self):
        """Test importing existing hierarchy level entity."""
        mock_session = MagicMock()
        existing_entity = MagicMock()
        existing_entity.id = 123
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            existing_entity
        )

        data = gpd.GeoDataFrame()

        result = self.importer._import_hierarchy_level(
            mock_session, "Loc1", "locality", data, "locality_name", True
        )

        self.assertEqual(result, 123)
        mock_session.add.assert_not_called()

    def test_import_plot_hierarchical_success(self):
        """Test importing hierarchical plot successfully."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        geometry = Point(165.5, -21.5)
        row = pd.Series(
            {
                "plot_name": 1,  # Use numeric ID instead of string
                "locality_name": "Loc1",
                "geometry": geometry,
                "extra_field": "extra_value",
            }
        )

        result = self.importer._import_plot_hierarchical(
            mock_session, row, "plot_name", "locality_name", parent_id=123
        )

        self.assertTrue(result)
        mock_session.add.assert_called_once()

        # Verify extra data was included
        added_plot = mock_session.add.call_args[0][0]
        self.assertEqual(added_plot.parent_id, 123)
        self.assertIn("extra_field", added_plot.extra_data)

    def test_update_nested_set_values(self):
        """Test updating nested set values for hierarchy."""
        mock_session = MagicMock()

        # Mock root nodes
        root1 = MagicMock()
        root1.id = 1
        root2 = MagicMock()
        root2.id = 2
        mock_session.query.return_value.filter_by.return_value.all.return_value = [
            root1,
            root2,
        ]

        with patch.object(
            self.importer, "_assign_nested_set_values", side_effect=[5, 10]
        ):
            self.importer._update_nested_set_values(mock_session)

        # Verify reset query was called
        mock_session.query.return_value.update.assert_called_once()
        mock_session.flush.assert_called()

    def test_assign_nested_set_values_with_children(self):
        """Test assigning nested set values with children."""
        mock_session = MagicMock()

        # Mock node with children - create a real object to test attribute setting
        class MockNode:
            def __init__(self, node_id):
                self.id = node_id
                self.lft = None
                self.level = None
                self.rght = None

        parent_node = MockNode(1)
        child1 = MockNode(2)
        child2 = MockNode(3)

        # Mock children query to return different results based on parent_id
        def mock_filter_by(parent_id):
            mock_filter = MagicMock()
            if parent_id == 1:
                # Parent node has two children
                mock_filter.all.return_value = [child1, child2]
            else:
                # Children have no children (leaf nodes)
                mock_filter.all.return_value = []
            return mock_filter

        mock_session.query.return_value.filter_by.side_effect = mock_filter_by

        # Call the actual method without patching it (testing the real implementation)
        result = self.importer._assign_nested_set_values(
            mock_session, parent_node, 1, 0
        )

        # Verify parent node values were set correctly
        self.assertEqual(parent_node.lft, 1)
        self.assertEqual(parent_node.level, 0)
        self.assertEqual(parent_node.rght, 6)  # 1 + (2 children * 2) + 1
        self.assertEqual(result, 7)  # Final counter

        # Verify children values were set
        self.assertEqual(child1.lft, 2)
        self.assertEqual(child1.level, 1)
        self.assertEqual(child1.rght, 3)

        self.assertEqual(child2.lft, 4)
        self.assertEqual(child2.level, 1)
        self.assertEqual(child2.rght, 5)

    # Error handling tests
    def test_database_error_handling(self):
        """Test database error handling in occurrence linking."""
        from sqlalchemy.exc import SQLAlchemyError

        with patch.object(self.importer, "_ensure_plot_ref_id_column_exists"):
            self.mock_db.execute_sql.side_effect = SQLAlchemyError("DB error")

            with self.assertRaises(DatabaseError) as context:
                self.importer.link_occurrences_to_plots()

        self.assertIn(
            "Database error during occurrence linking", str(context.exception)
        )

    def test_generic_exception_propagation(self):
        """Test that non-specific exceptions are propagated."""
        with patch.object(
            self.importer,
            "_ensure_plot_ref_id_column_exists",
            side_effect=RuntimeError("Generic error"),
        ):
            with self.assertRaises(RuntimeError):
                self.importer.link_occurrences_to_plots()
