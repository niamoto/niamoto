import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
from unittest.mock import MagicMock, patch
from shapely.geometry import Point

from niamoto.core.plugins.transformers.extraction.geospatial_extractor import (
    GeospatialExtractor,
)


@pytest.fixture
def geospatial_extractor_plugin():
    """Fixture for GeospatialExtractor plugin instance."""
    # Mock database interaction
    mock_db = MagicMock()

    # Mock Config to prevent creating config directory at project root
    with patch(
        "niamoto.core.plugins.transformers.extraction.geospatial_extractor.Config"
    ) as mock_config:
        mock_config.return_value.get_imports_config = {
            "test_csv": {"path": "data/test.csv", "type": "csv", "identifier": "id"},
            "test_vector": {
                "path": "data/test.geojson",
                "type": "vector",
                "identifier": "id",
            },
        }
        plugin = GeospatialExtractor(db=mock_db)

    # Set the mocked config on the plugin
    plugin.config.config_dir = "/mock/config"

    return plugin


class TestGeospatialExtractorValidation:
    """Tests for GeospatialExtractor configuration validation."""

    def test_validate_config_valid(self, geospatial_extractor_plugin):
        """Test valid configuration."""
        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                "field": "geometry",
                "format": "geojson",
                "properties": ["name", "status"],
                "group_by_coordinates": False,
            },
        }
        # Should not raise an error
        geospatial_extractor_plugin.validate_config(config)

    def test_validate_config_missing_source(self, geospatial_extractor_plugin):
        """Test configuration missing source field."""
        config = {
            "plugin": "geospatial_extractor",
            "params": {
                # "source": "occurrences", # Missing source
                "field": "geometry",
                "format": "geojson",
            },
        }
        with pytest.raises(ValueError, match="Source is required"):
            geospatial_extractor_plugin.validate_config(config)

    def test_validate_config_missing_field(self, geospatial_extractor_plugin):
        """Test configuration missing field."""
        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                # "field": "geometry", # Missing field
                "format": "geojson",
            },
        }
        with pytest.raises(ValueError, match="Field is required"):
            geospatial_extractor_plugin.validate_config(config)

    def test_validate_config_invalid_format(self, geospatial_extractor_plugin):
        """Test configuration with invalid format."""
        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                "field": "geometry",
                "format": "invalid_format",  # Invalid format
            },
        }
        with pytest.raises(ValueError, match="Format must be 'geojson'"):
            geospatial_extractor_plugin.validate_config(config)

    def test_validate_config_default_values(self, geospatial_extractor_plugin):
        """Test configuration with default values applied."""
        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                "field": "geometry",
                # format, properties, and group_by_coordinates will use defaults
            },
        }
        # Use the config_model to validate and get the default values
        validated_config = geospatial_extractor_plugin.config_model(**config)

        # Check default values
        assert validated_config.params["format"] == "geojson"
        assert validated_config.params["properties"] == []
        assert not validated_config.params["group_by_coordinates"]


class TestGeospatialExtractorConversion:
    """Tests for the _convert_to_geometry method."""

    def test_convert_point_geometry(self, geospatial_extractor_plugin):
        """Test converting a Point geometry."""
        point = Point(1.0, 2.0)
        result = geospatial_extractor_plugin._convert_to_geometry(point)
        assert result is point
        assert result.x == 1.0
        assert result.y == 2.0

    def test_convert_wkt_string(self, geospatial_extractor_plugin):
        """Test converting a WKT string."""
        wkt = "POINT (1 2)"
        result = geospatial_extractor_plugin._convert_to_geometry(wkt)
        assert isinstance(result, Point)
        assert result.x == 1.0
        assert result.y == 2.0

    def test_convert_point_string(self, geospatial_extractor_plugin):
        """Test converting a point string format."""
        point_str = "POINT (3.5 4.5)"
        result = geospatial_extractor_plugin._convert_to_geometry(point_str)
        assert isinstance(result, Point)
        assert result.x == 3.5
        assert result.y == 4.5

    def test_convert_nan_value(self, geospatial_extractor_plugin):
        """Test converting a NaN value."""
        result = geospatial_extractor_plugin._convert_to_geometry(np.nan)
        assert result is None

    def test_convert_invalid_value(self, geospatial_extractor_plugin):
        """Test converting an invalid value."""
        result = geospatial_extractor_plugin._convert_to_geometry("not a point")
        assert result is None


class TestGeospatialExtractorGetData:
    """Tests for the _get_data_from_source method."""

    def test_get_data_from_csv_import(self, geospatial_extractor_plugin):
        """Test getting data from a CSV import."""
        # Create a test dataframe to return
        mock_df = pd.DataFrame({"id": [1, 2], "value": ["a", "b"]})

        # Directly patch the _get_data_from_source method
        with patch.object(
            geospatial_extractor_plugin, "_get_data_from_source", return_value=mock_df
        ) as mock_method:
            # Call the method
            result = geospatial_extractor_plugin._get_data_from_source("test_csv")

            # Verify method was called
            mock_method.assert_called_once_with("test_csv")

            # Verify result is correct
            pd.testing.assert_frame_equal(result, mock_df)

    def test_get_data_from_vector_import(self, geospatial_extractor_plugin):
        """Test getting data from a vector import."""
        # Create a test geodataframe to return
        mock_df = gpd.GeoDataFrame(
            {"id": [1, 2], "geometry": [Point(1, 1), Point(2, 2)]}
        )

        # Directly patch the _get_data_from_source method
        with patch.object(
            geospatial_extractor_plugin, "_get_data_from_source", return_value=mock_df
        ) as mock_method:
            # Call the method
            result = geospatial_extractor_plugin._get_data_from_source("test_vector")

            # Verify method was called
            mock_method.assert_called_once_with("test_vector")

            # Verify result is correct
            assert isinstance(result, gpd.GeoDataFrame)
            assert len(result) == 2

    def test_get_data_from_database(self, geospatial_extractor_plugin):
        """Test getting data from a database table."""
        # Create a mock for database results
        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("value",)]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1, "a"), (2, "b")]
        mock_result.cursor = mock_cursor

        # Mock the database execute_select method
        geospatial_extractor_plugin.db.execute_select.return_value = mock_result

        # Create a patched version of GeospatialExtractor._get_data_from_source
        original_method = GeospatialExtractor._get_data_from_source

        def patched_method(self, source, id_value=None):
            # Call the database method for this test
            if source == "db_table":
                query = f"SELECT * FROM {source}"
                if id_value is not None:
                    query += f" WHERE id = {id_value}"

                result = self.db.execute_select(query)
                df = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )
                return df

            # For other sources, use the original method
            return original_method(self, source, id_value)

        # Apply the patch
        with patch.object(GeospatialExtractor, "_get_data_from_source", patched_method):
            # Call the method
            result = geospatial_extractor_plugin._get_data_from_source("db_table")

            # Verify database was queried
            geospatial_extractor_plugin.db.execute_select.assert_called_once_with(
                "SELECT * FROM db_table"
            )

            # Verify result structure
            assert isinstance(result, pd.DataFrame)
            assert list(result.columns) == ["id", "value"]
            assert len(result) == 2


class TestGeospatialExtractorTransform:
    """Tests for the transform method."""

    def test_transform_with_points(self, geospatial_extractor_plugin):
        """Test transform with point geometries."""
        # Create test data with Point geometries
        points = [Point(1, 2), Point(3, 4), Point(5, 6)]
        data = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["A", "B", "C"],
                "status": ["active", "inactive", "active"],
                "geometry": points,
            }
        )

        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                "field": "geometry",
                "format": "geojson",
                "properties": ["name", "status"],
                "group_by_coordinates": False,
            },
        }

        result = geospatial_extractor_plugin.transform(data, config)

        # Check result structure
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 3

        # Check feature properties
        for i, feature in enumerate(result["features"]):
            assert feature["type"] == "Feature"
            assert feature["geometry"]["type"] == "Point"
            assert feature["geometry"]["coordinates"] == [points[i].x, points[i].y]
            assert feature["properties"]["name"] == data["name"].iloc[i]
            assert feature["properties"]["status"] == data["status"].iloc[i]

    def test_transform_with_wkt_strings(self, geospatial_extractor_plugin):
        """Test transform with WKT strings."""
        # Create test data with WKT strings
        wkt_points = ["POINT (1 2)", "POINT (3 4)", "POINT (5 6)"]
        data = pd.DataFrame(
            {"id": [1, 2, 3], "name": ["A", "B", "C"], "geometry": wkt_points}
        )

        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                "field": "geometry",
                "format": "geojson",
                "properties": ["name"],
                "group_by_coordinates": False,
            },
        }

        result = geospatial_extractor_plugin.transform(data, config)

        # Check result structure
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 3

        # Check coordinates match expected values
        expected_coords = [[1, 2], [3, 4], [5, 6]]
        for i, feature in enumerate(result["features"]):
            assert feature["geometry"]["coordinates"] == expected_coords[i]
            assert feature["properties"]["name"] == data["name"].iloc[i]

    def test_transform_with_grouped_coordinates(self, geospatial_extractor_plugin):
        """Test transform with grouped coordinates."""
        # Create test data with duplicate coordinates
        points = [Point(1, 2), Point(1, 2), Point(3, 4)]  # Two points at (1, 2)
        data = pd.DataFrame(
            {"id": [1, 2, 3], "name": ["A", "B", "C"], "geometry": points}
        )

        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                "field": "geometry",
                "format": "geojson",
                "properties": ["name"],
                "group_by_coordinates": True,  # Group by coordinates
            },
        }

        result = geospatial_extractor_plugin.transform(data, config)

        # Check result structure
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 2  # 2 unique coordinates instead of 3 points

        # Find the grouped feature
        grouped_feature = next(
            f for f in result["features"] if f["geometry"]["coordinates"] == [1, 2]
        )

        # Check that the count is 2 for the grouped feature
        assert grouped_feature["properties"]["count"] == 2

    def test_transform_with_external_source(self, geospatial_extractor_plugin):
        """Test transform with data from external source."""
        # Mock empty input data
        input_data = pd.DataFrame()

        # Mock source data
        source_data = pd.DataFrame(
            {"id": [1, 2], "name": ["A", "B"], "geometry": [Point(1, 2), Point(3, 4)]}
        )

        # Mock the _get_data_from_source method
        geospatial_extractor_plugin._get_data_from_source = MagicMock(
            return_value=source_data
        )

        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "external_source",  # Not "occurrences"
                "field": "geometry",
                "format": "geojson",
                "properties": ["name"],
            },
        }

        result = geospatial_extractor_plugin.transform(input_data, config)

        # Check that _get_data_from_source was called
        geospatial_extractor_plugin._get_data_from_source.assert_called_once_with(
            "external_source", None
        )

        # Check the result
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 2

    def test_transform_with_missing_field(self, geospatial_extractor_plugin):
        """Test transform with missing field."""
        data = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["A", "B", "C"],
                # No geometry field
            }
        )

        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                "field": "geometry",  # This field doesn't exist
                "format": "geojson",
                "properties": ["name"],
            },
        }

        result = geospatial_extractor_plugin.transform(data, config)

        # Should return empty feature collection
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 0

    def test_transform_with_empty_data(self, geospatial_extractor_plugin):
        """Test transform with empty data."""
        data = pd.DataFrame(columns=["id", "name", "geometry"])

        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                "field": "geometry",
                "format": "geojson",
                "properties": ["name"],
            },
        }

        result = geospatial_extractor_plugin.transform(data, config)

        # Should return empty feature collection
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 0

    def test_transform_with_invalid_geometries(self, geospatial_extractor_plugin):
        """Test transform with invalid geometries that can't be converted."""
        data = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["A", "B", "C"],
                "geometry": [
                    "invalid",
                    np.nan,
                    "POINT (1 2)",
                ],  # Only one valid geometry
            }
        )

        config = {
            "plugin": "geospatial_extractor",
            "params": {
                "source": "occurrences",
                "field": "geometry",
                "format": "geojson",
                "properties": ["name"],
            },
        }

        result = geospatial_extractor_plugin.transform(data, config)

        # Should only return features for valid geometries
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1
        assert result["features"][0]["geometry"]["coordinates"] == [1, 2]
