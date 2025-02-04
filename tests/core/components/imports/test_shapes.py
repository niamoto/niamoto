"""Tests for the ShapeImporter class."""

from unittest import mock

import pytest
import geopandas as gpd
from shapely.geometry import Point, Polygon
from sqlalchemy.exc import SQLAlchemyError

from niamoto.core.components.imports.shapes import ShapeImporter
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
    DatabaseError,
    ConfigurationError,
)


class TestShapeImporter:
    """Test cases for ShapeImporter class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        with mock.patch("niamoto.common.database.Database") as mock_db:
            # Configure the mock
            mock_session = mock.MagicMock()
            mock_db.return_value.session = mock_session
            # Configure query to return None by default (no existing shapes)
            mock_session.query.return_value.filter_by.return_value.scalar.return_value = None
            yield mock_db.return_value

    @pytest.fixture
    def importer(self, mock_db):
        """ShapeImporter fixture."""
        return ShapeImporter(mock_db)

    @pytest.fixture
    def valid_geojson(self, tmp_path):
        """Create a valid GeoJSON file for testing."""
        # Create a simple polygon
        polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(
            {"name": ["Test Shape"], "geometry": [polygon]}, crs="EPSG:4326"
        )

        # Save to temporary file
        file_path = tmp_path / "test_shape.geojson"
        gdf.to_file(file_path, driver="GeoJSON")
        return str(file_path)

    @pytest.fixture
    def valid_config(self, valid_geojson):
        """Create a valid shape configuration."""
        return [
            {
                "category": "test_category",
                "label": "Test Shape",
                "path": valid_geojson,
                "name_field": "name",
            }
        ]

    def test_import_valid_file(self, importer, valid_config):
        """Test importing a valid shape file."""
        result = importer.import_from_config(valid_config)
        assert "1 shapes imported" in result
        assert "1 new" in result
        assert "0 updated" in result

    def test_file_not_found(self, importer, valid_config):
        """Test handling of non-existent file."""
        valid_config[0]["path"] = "/nonexistent/path.geojson"
        with pytest.raises(FileReadError) as exc_info:
            importer.import_from_config(valid_config)
        assert "Shape file not found" in str(exc_info.value)

    def test_invalid_format(self, importer, tmp_path):
        """Test handling of invalid file format."""
        # Create an invalid file
        invalid_file = tmp_path / "invalid.geojson"
        invalid_file.write_text("invalid content")

        config = [
            {
                "category": "test_category",
                "label": "Test Shape",
                "path": str(invalid_file),
                "name_field": "name",
            }
        ]

        with pytest.raises(DataValidationError) as exc_info:
            importer.import_from_config(config)
        assert "Invalid shape file format" in str(exc_info.value)

    def test_missing_columns(self, importer, tmp_path):
        """Test handling of missing required columns."""
        # Create GeoJSON without required field
        point = Point(0, 0)
        gdf = gpd.GeoDataFrame(
            {"other_field": ["Test"], "geometry": [point]}, crs="EPSG:4326"
        )

        file_path = tmp_path / "missing_columns.geojson"
        gdf.to_file(file_path, driver="GeoJSON")

        config = [
            {
                "category": "test_category",
                "label": "Test Shape",
                "path": str(file_path),
                "name_field": "name",  # This field doesn't exist in the file
            }
        ]

        result = importer.import_from_config(config)
        assert "0 shapes imported" in result
        assert "skipped" in str(result)

    def test_invalid_geometry(self, importer, tmp_path):
        """Test handling of invalid geometry."""
        # Create an invalid polygon (self-intersecting)
        invalid_polygon = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
        gdf = gpd.GeoDataFrame(
            {"name": ["Invalid Shape"], "geometry": [invalid_polygon]}, crs="EPSG:4326"
        )

        file_path = tmp_path / "invalid_geometry.geojson"
        gdf.to_file(file_path, driver="GeoJSON")

        config = [
            {
                "category": "test_category",
                "label": "Test Shape",
                "path": str(file_path),
                "name_field": "name",
            }
        ]

        result = importer.import_from_config(config)
        assert "1 shapes imported" in result  # Should auto-fix the geometry

    def test_duplicate_shape(self, importer, valid_config):
        """Test handling of duplicate shapes."""
        # Configure mock to return an existing shape
        mock_shape = mock.MagicMock()
        importer.db.session.query.return_value.filter_by.return_value.scalar.return_value = mock_shape

        result = importer.import_from_config(valid_config)
        assert "1 shapes imported" in result
        assert "0 new" in result
        assert "1 updated" in result

    def test_invalid_config(self, importer):
        """Test handling of invalid configuration."""
        invalid_configs = [
            # Empty config
            [],
            # Missing required fields
            [{"category": "test"}],
            # Empty category
            [
                {
                    "category": "",
                    "label": "Test",
                    "path": "test.geojson",
                    "name_field": "name",
                }
            ],
        ]

        for config in invalid_configs:
            with pytest.raises(ConfigurationError):
                importer.import_from_config(config)

    def test_database_error(self, importer, valid_config):
        """Test handling of database errors."""
        # Mock SQLAlchemy to raise an error
        importer.db.session.commit.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            importer.import_from_config(valid_config)
        assert "Database error" in str(exc_info.value)
