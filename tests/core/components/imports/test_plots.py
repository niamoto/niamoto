"""
Tests for the PlotImporter class.
"""

from unittest.mock import patch, MagicMock
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point

from niamoto.core.components.imports.plots import PlotImporter
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
)
from tests.common.base_test import NiamotoTestCase


class TestPlotImporter(NiamotoTestCase):
    """Test case for the PlotImporter class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Use MagicMock directly instead of create_mock to avoid spec_set restrictions
        self.mock_db = MagicMock()
        # Set attributes that are accessed in the code
        self.mock_db.db_path = "mock_db_path"
        self.mock_db.engine = MagicMock()
        self.importer = PlotImporter(self.mock_db)
        # Add db_path attribute to match other importers
        self.importer.db_path = "mock_db_path"

    def test_init(self):
        """Test initialization of PlotImporter."""
        self.assertEqual(self.importer.db, self.mock_db)
        self.assertEqual(self.importer.db_path, "mock_db_path")

    @patch("geopandas.read_file")
    @patch("pathlib.Path.exists")
    def test_import_from_gpkg(self, mock_exists, mock_read_file):
        """Test import_from_gpkg method."""
        # Setup mocks
        mock_exists.return_value = True

        # Create a mock GeoDataFrame with the required columns
        geometry = [Point(1, 1), Point(2, 2), Point(3, 3)]
        mock_df = gpd.GeoDataFrame(
            {
                "id": [1, 2, 3],
                "locality": ["Loc1", "Loc2", "Loc3"],
                "location": ["Loc1", "Loc2", "Loc3"],
                "geometry": geometry,
            }
        )
        mock_read_file.return_value = mock_df

        # Mock the internal methods
        with patch.object(
            self.importer, "_process_plots_data", return_value=3
        ) as mock_process:
            # Mock Path.resolve to return the original path
            with patch("pathlib.Path.resolve", return_value=Path("test.gpkg")):
                # Call the method
                result = self.importer.import_from_gpkg("test.gpkg", "id", "location")

                # Verify results
                self.assertEqual(
                    result,
                    "3 plots imported from test.gpkg. 0 occurrences linked to plots.",
                )
                mock_read_file.assert_called_once_with("test.gpkg")
                mock_process.assert_called_once()

    @patch("geopandas.read_file")
    @patch("pathlib.Path.exists")
    def test_import_from_gpkg_file_not_found(self, mock_exists, mock_read_file):
        """Test import_from_gpkg method with file not found."""
        # Setup mocks
        mock_exists.return_value = False

        # Call the method and expect exception
        with self.assertRaises(FileReadError):
            self.importer.import_from_gpkg("nonexistent.gpkg", "id", "location")

        # Verify read_file was not called
        mock_read_file.assert_not_called()

    @patch("geopandas.read_file")
    @patch("pathlib.Path.exists")
    def test_import_from_gpkg_invalid_file(self, mock_exists, mock_read_file):
        """Test import_from_gpkg method with invalid file."""
        # Setup mocks
        mock_exists.return_value = True
        mock_read_file.side_effect = Exception("Invalid file")

        # Call the method and expect exception
        with self.assertRaises(FileReadError):
            self.importer.import_from_gpkg("invalid.gpkg", "id", "location")

    @patch("geopandas.read_file")
    @patch("pathlib.Path.exists")
    def test_import_from_gpkg_missing_columns(self, mock_exists, mock_read_file):
        """Test import_from_gpkg method with missing columns."""
        # Setup mocks
        mock_exists.return_value = True

        # Create a mock GeoDataFrame with missing required columns
        geometry = [Point(1, 1), Point(2, 2), Point(3, 3)]
        mock_df = gpd.GeoDataFrame(
            {
                "id": [1, 2, 3],
                # Missing 'locality' column
                "geometry": geometry,
            }
        )
        mock_read_file.return_value = mock_df

        # Call the method and expect exception
        with self.assertRaises(DataValidationError):
            self.importer.import_from_gpkg("test.gpkg", "id", "location")

    @patch("sqlalchemy.orm.Session")
    def test_process_plots_data(self, mock_session):
        """Test _process_plots_data method."""
        # Create a mock GeoDataFrame with the required columns
        geometry = [Point(1, 1), Point(2, 2)]
        plots_data = gpd.GeoDataFrame(
            {
                "id": [1, 2],
                "locality": ["Loc1", "Loc2"],
                "location": ["Loc1", "Loc2"],
                "geometry": geometry,
            }
        )

        # Mock session context manager
        mock_session_context = MagicMock()
        self.mock_db.session.return_value.__enter__.return_value = mock_session_context

        # Mock _import_plot to return True (successful import)
        with patch.object(
            self.importer, "_import_plot", return_value=True
        ) as mock_import:
            # Call the method
            result = self.importer._process_plots_data(plots_data, "id", "location")

            # Verify results
            self.assertEqual(result, 2)
            self.assertEqual(mock_import.call_count, 2)
            mock_session_context.commit.assert_called_once()

    def test_import_plot(self):
        """Test _import_plot method."""
        # Create a mock session
        mock_session = MagicMock()

        # Create a mock row with required data
        geometry = Point(1, 1)
        row = pd.Series({"id": 1, "locality": "Loc1", "geometry": geometry})

        # Mock query to return None (no existing plot)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value.first.return_value = None

        # Mock validate_geometry to do nothing
        with patch.object(self.importer, "validate_geometry") as mock_validate:
            # Call the method
            result = self.importer._import_plot(mock_session, row, "id")

            # Verify results
            self.assertTrue(result)
            mock_validate.assert_called_once()
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_import_plot_existing(self):
        """Test _import_plot method with existing plot."""
        # Create a mock session
        mock_session = MagicMock()

        # Create a mock row with required data
        geometry = Point(1, 1)
        row = pd.Series({"id": 1, "locality": "Loc1", "geometry": geometry})

        # Mock query to return an existing plot
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value.first.return_value = MagicMock()

        # Mock validate_geometry to do nothing
        with patch.object(self.importer, "validate_geometry") as mock_validate:
            # Call the method
            result = self.importer._import_plot(mock_session, row, "id")

            # Verify results
            self.assertFalse(result)
            mock_validate.assert_called_once()
            mock_session.add.assert_not_called()

    def test_import_plot_invalid_geometry(self):
        """Test _import_plot method with invalid geometry."""
        # Create a mock session
        mock_session = MagicMock()

        # Create a mock row with invalid geometry
        row = pd.Series({"id": 1, "locality": "Loc1", "geometry": None})

        # Call the method and expect exception
        with self.assertRaises(DataValidationError):
            self.importer._import_plot(mock_session, row, "id")

    def test_import_plot_invalid_id(self):
        """Test _import_plot method with invalid ID."""
        # Create a mock session
        mock_session = MagicMock()

        # Create a mock row with invalid ID
        geometry = Point(1, 1)
        row = pd.Series({"id": None, "locality": "Loc1", "geometry": geometry})

        # Call the method and expect exception
        with self.assertRaises(DataValidationError):
            self.importer._import_plot(mock_session, row, "id")

    def test_import_plot_invalid_locality(self):
        """Test _import_plot method with invalid locality."""
        # Create a mock session
        mock_session = MagicMock()

        # Create a mock row with invalid locality
        geometry = Point(1, 1)
        row = pd.Series({"id": 1, "locality": None, "geometry": geometry})

        # Call the method and expect exception
        with self.assertRaises(DataValidationError):
            self.importer._import_plot(mock_session, row, "id")

    def test_validate_geometry_valid(self):
        """Test validate_geometry method with valid geometry."""
        # Call the method with valid WKT
        valid_wkt = "POINT(1 1)"
        PlotImporter.validate_geometry(valid_wkt)
        # If no exception is raised, the test passes

    def test_validate_geometry_empty(self):
        """Test validate_geometry method with empty geometry."""
        # Call the method with empty WKT
        with self.assertRaises(DataValidationError):
            PlotImporter.validate_geometry("")

    @patch("shapely.wkt.loads")
    def test_validate_geometry_invalid(self, mock_loads):
        """Test validate_geometry method with invalid geometry."""
        # Mock loads to return an invalid geometry
        mock_geom = MagicMock()
        mock_geom.is_valid = False
        mock_loads.return_value = mock_geom

        # Call the method and expect exception
        with self.assertRaises(DataValidationError):
            PlotImporter.validate_geometry("INVALID")
