"""Tests for the plot importer module."""

import pytest
import geopandas as gpd
from shapely.geometry import Point
from unittest import mock
from sqlalchemy.exc import SQLAlchemyError

from niamoto.core.components.imports.plots import PlotImporter
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
    DatabaseError,
)
from niamoto.core.models import PlotRef


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary directory for test data."""
    return tmp_path


@pytest.fixture
def valid_gpkg(test_data_dir):
    """Create a valid GeoPackage file for testing."""
    # Create sample data with valid geometries
    data = {
        "id": [1, 2, 3],
        "locality": ["Site A", "Site B", "Site C"],
        "geometry": [
            Point(166.5, -22.1),  # Valid coordinates for New Caledonia
            Point(166.6, -22.2),
            Point(166.7, -22.3),
        ],
    }
    gdf = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:4326")

    # Save to GeoPackage
    file_path = test_data_dir / "valid_plots.gpkg"
    gdf.to_file(file_path, driver="GPKG")
    return str(file_path)


@pytest.fixture
def mock_db():
    """Create a mock database."""
    with mock.patch("niamoto.common.database.Database") as mock_db:
        mock_session = mock.MagicMock()
        # Ensure the session can be used as a context manager
        mock_session.__enter__.return_value = mock_session

        # Configure the query chain: each call to query() returns a new MagicMock
        def fake_query(*args, **kwargs):
            mock_query = mock.MagicMock()
            # For every call to filter_by().first(), force a return of None.
            mock_query.filter_by.return_value.first.return_value = None
            return mock_query

        mock_session.query.side_effect = fake_query

        # Make session() return our configured mock_session
        mock_db.return_value.session.return_value = mock_session
        yield mock_db.return_value


class TestPlotImporter:
    """Test cases for PlotImporter class."""

    def test_import_valid_file(self, mock_db, valid_gpkg):
        """Test importing a valid GeoPackage file."""
        importer = PlotImporter(mock_db)
        result = importer.import_from_gpkg(valid_gpkg, "id", "geometry")

        assert "3 plots imported" in result
        assert mock_db.session.return_value.commit.called

    def test_file_not_found(self, mock_db):
        """Test error when file doesn't exist."""
        importer = PlotImporter(mock_db)
        with pytest.raises(FileReadError) as exc_info:
            importer.import_from_gpkg("nonexistent.gpkg", "id", "geometry")

        assert "GeoPackage file not found" in str(exc_info.value)

    def test_invalid_format(self, test_data_dir, mock_db):
        """Test error when file format is invalid."""
        # Create an invalid file
        invalid_file = test_data_dir / "invalid.gpkg"
        with open(invalid_file, "w") as f:
            f.write("Not a GeoPackage file")

        importer = PlotImporter(mock_db)
        with pytest.raises(FileReadError) as exc_info:
            importer.import_from_gpkg(str(invalid_file), "id", "geometry")

        assert "Failed to read GeoPackage file" in str(exc_info.value)

    def test_missing_columns(self, test_data_dir, mock_db):
        """Test error when required columns are missing."""
        # Create GeoPackage without required columns
        data = {
            "geometry": [Point(166.5, -22.1)]  # Only geometry, missing id and locality
        }
        gdf = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:4326")
        file_path = test_data_dir / "missing_columns.gpkg"
        gdf.to_file(file_path, driver="GPKG")

        importer = PlotImporter(mock_db)
        with pytest.raises(DataValidationError) as exc_info:
            importer.import_from_gpkg(str(file_path), "id", "geometry")

        assert "Missing required columns" in str(exc_info.value)

    def test_empty_geometry(self, test_data_dir, mock_db):
        """Test error when geometry is empty."""
        # Create GeoPackage with empty geometry
        data = {"id": [1], "locality": ["Site A"], "geometry": [None]}
        gdf = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:4326")
        file_path = test_data_dir / "empty_geometry.gpkg"
        gdf.to_file(file_path, driver="GPKG")

        importer = PlotImporter(mock_db)
        with pytest.raises(DataValidationError) as exc_info:
            importer.import_from_gpkg(str(file_path), "id", "geometry")

        assert "Missing geometry" in str(exc_info.value)

    def test_duplicate_plot(self, mock_db, valid_gpkg):
        """Test handling of duplicate plots."""
        # Configure mock to return an existing plot
        mock_db.session.return_value.query.return_value.filter_by.return_value.scalar.return_value = PlotRef(
            id_locality=1, locality="Site A", geometry="POINT(166.5 -22.1)"
        )

        importer = PlotImporter(mock_db)
        result = importer.import_from_gpkg(valid_gpkg, "id", "geometry")

        # Should skip existing plots but continue processing
        assert "plots imported" in result
        assert mock_db.session.return_value.commit.called

    def test_invalid_locality(self, test_data_dir, mock_db):
        """Test error when locality is invalid."""
        # Create GeoPackage with invalid locality (None)
        data = {"id": [1], "locality": [None], "geometry": [Point(166.5, -22.1)]}
        gdf = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:4326")
        file_path = test_data_dir / "invalid_locality.gpkg"
        gdf.to_file(file_path, driver="GPKG")

        importer = PlotImporter(mock_db)
        with pytest.raises(DataValidationError) as exc_info:
            importer.import_from_gpkg(str(file_path), "id", "geometry")

        assert "Invalid locality" in str(exc_info.value)

    def test_database_error(self, mock_db, valid_gpkg):
        """Test handling of database errors."""
        # Configure mock to raise SQLAlchemy error
        mock_session = mock_db.session.return_value
        mock_session.__enter__.return_value = mock_session
        mock_session.commit.side_effect = SQLAlchemyError("Database error")

        importer = PlotImporter(mock_db)
        with pytest.raises(DatabaseError) as exc_info:
            importer.import_from_gpkg(valid_gpkg, "id", "geometry")

        assert "Database error" in str(exc_info.value)
        assert mock_session.rollback.called  # Should rollback on error
