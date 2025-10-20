import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
from unittest.mock import MagicMock, patch
from shapely.geometry import Point

from niamoto.core.plugins.transformers.extraction.geospatial_extractor import (
    GeospatialExtractor,
)
from niamoto.core.imports.registry import EntityMetadata, EntityKind


@pytest.fixture(scope="function")
def geospatial_extractor_plugin():
    """Fixture for GeospatialExtractor plugin instance."""
    # Mock database interaction
    mock_db = MagicMock()
    mock_db.has_table = MagicMock(return_value=False)
    mock_db.engine = MagicMock()

    # Create mock config
    mock_config_instance = MagicMock()
    mock_config_instance.config_dir = "/mock/config"

    # Create a MagicMock for the registry
    mock_registry = MagicMock()

    # Create plugin WITHOUT the dependencies first (so we can inject mocks)
    # We'll manually create the plugin and inject mocks
    plugin = object.__new__(GeospatialExtractor)
    plugin.db = mock_db
    plugin.registry = mock_registry
    plugin.config = mock_config_instance
    plugin.config_model = GeospatialExtractor.config_model

    # Store references for test access
    plugin._test_mock_db = mock_db
    plugin._test_mock_registry = plugin.registry

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
        with pytest.raises(ValueError, match="Field required"):
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
        with pytest.raises(ValueError, match="Field required"):
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
        with pytest.raises(ValueError, match="Input should be 'geojson'"):
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
        assert validated_config.params.format == "geojson"
        assert validated_config.params.properties == []
        assert not validated_config.params.group_by_coordinates


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
        """Test getting data from a CSV import via connector."""
        # Setup: Create EntityMetadata with CSV connector config
        metadata = EntityMetadata(
            name="test_csv",
            kind=EntityKind.DATASET,
            table_name="test_csv_table",
            config={
                "connector": {
                    "type": "csv",
                    "path": "data/test.csv",
                    "identifier": "id",
                }
            },
        )

        # Mock registry to return this metadata
        geospatial_extractor_plugin._test_mock_registry.get.return_value = metadata
        geospatial_extractor_plugin._test_mock_db.has_table.return_value = False

        # Mock CSV file reading
        expected_df = pd.DataFrame({"id": [1, 2], "value": ["a", "b"]})
        with patch("pandas.read_csv", return_value=expected_df) as mock_read_csv:
            # Execute: Call the method we're testing
            result = geospatial_extractor_plugin._get_data_from_source("test_csv")

        # Verify: pandas.read_csv was called with correct path
        mock_read_csv.assert_called_once()
        called_path = mock_read_csv.call_args[0][0]
        assert called_path.endswith("data/test.csv")

        # Verify: Result matches expected data
        pd.testing.assert_frame_equal(result, expected_df)

    def test_get_data_from_vector_import(self, geospatial_extractor_plugin):
        """Test getting data from a vector import via connector."""
        # Setup: Create EntityMetadata with vector connector config
        metadata = EntityMetadata(
            name="test_vector",
            kind=EntityKind.DATASET,
            table_name="test_vector_table",
            config={
                "connector": {
                    "type": "vector",
                    "path": "data/test.geojson",
                    "identifier": "id",
                }
            },
        )

        # Mock registry to return this metadata
        geospatial_extractor_plugin._test_mock_registry.get.return_value = metadata
        geospatial_extractor_plugin._test_mock_db.has_table.return_value = False

        # Mock GeoJSON file reading
        expected_gdf = gpd.GeoDataFrame(
            {"id": [1, 2], "geometry": [Point(1, 1), Point(2, 2)]}
        )
        with patch("geopandas.read_file", return_value=expected_gdf) as mock_read_file:
            # Execute: Call the method we're testing
            result = geospatial_extractor_plugin._get_data_from_source("test_vector")

        # Verify: geopandas.read_file was called with correct path
        mock_read_file.assert_called_once()
        called_path = mock_read_file.call_args[0][0]
        assert called_path.endswith("data/test.geojson")

        # Verify: Result is a GeoDataFrame with correct data
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 2

    def test_get_data_from_registry_table(self, geospatial_extractor_plugin):
        """Test getting data from a database table via registry."""
        # Setup: Create EntityMetadata for a database table (no connector)
        metadata = EntityMetadata(
            name="db_table",
            kind=EntityKind.DATASET,
            table_name="db_table",
            config={},
        )

        # Mock registry and database
        geospatial_extractor_plugin._test_mock_registry.get.return_value = metadata
        geospatial_extractor_plugin._test_mock_db.has_table.return_value = True

        # Mock SQL query execution
        expected_df = pd.DataFrame({"id": [1], "value": ["a"]})
        with patch("pandas.read_sql", return_value=expected_df) as mock_read_sql:
            # Execute: Call with id filter
            result = geospatial_extractor_plugin._get_data_from_source(
                "db_table", id_value=5
            )

        # Verify: SQL query was called correctly
        mock_read_sql.assert_called_once()
        query, engine = mock_read_sql.call_args[0][:2]
        params = mock_read_sql.call_args.kwargs.get("params")
        assert "FROM db_table" in query
        assert "WHERE id = :id" in query
        assert params == {"id": 5}
        assert isinstance(result, pd.DataFrame)

    def test_get_data_from_registry_connector_csv(self, geospatial_extractor_plugin):
        """Test getting data from CSV connector with id filtering."""
        # Setup: Create EntityMetadata with CSV connector
        metadata = EntityMetadata(
            name="custom",
            kind=EntityKind.DATASET,
            table_name="missing_table",
            config={
                "connector": {
                    "type": "csv",
                    "path": "data/custom.csv",
                    "identifier": "id",
                }
            },
        )

        # Mock registry and database (table doesn't exist, fallback to connector)
        geospatial_extractor_plugin._test_mock_registry.get.return_value = metadata
        geospatial_extractor_plugin._test_mock_db.has_table.return_value = False

        # Mock CSV reading
        full_df = pd.DataFrame({"id": [1, 2], "value": ["x", "y"]})
        with patch("pandas.read_csv", return_value=full_df) as mock_read_csv:
            # Execute: Call with id filter - should filter the dataframe
            result = geospatial_extractor_plugin._get_data_from_source(
                "custom", id_value=1
            )

        # Verify: CSV was read and filtered correctly
        mock_read_csv.assert_called_once()
        called_path = mock_read_csv.call_args[0][0]
        assert called_path.endswith("data/custom.csv")

        # Verify: Result is filtered to only id=1
        expected_filtered = full_df[full_df["id"] == 1]
        pd.testing.assert_frame_equal(result, expected_filtered)

    def test_get_data_from_database(self, geospatial_extractor_plugin):
        """Test getting data from a database table without id filter."""
        # Setup: Create EntityMetadata for a database table
        metadata = EntityMetadata(
            name="db_table",
            kind=EntityKind.DATASET,
            table_name="db_table",
            config={},
        )

        # Mock registry and database
        geospatial_extractor_plugin._test_mock_registry.get.return_value = metadata
        geospatial_extractor_plugin._test_mock_db.has_table.return_value = True

        # Mock SQL query execution
        expected_df = pd.DataFrame({"id": [1, 2], "value": ["a", "b"]})
        with patch("pandas.read_sql", return_value=expected_df) as mock_read_sql:
            # Execute: Call without id filter
            result = geospatial_extractor_plugin._get_data_from_source("db_table")

        # Verify: SQL query was called correctly (no WHERE clause)
        mock_read_sql.assert_called_once()
        query = mock_read_sql.call_args[0][0]
        params = mock_read_sql.call_args.kwargs.get("params")
        assert "FROM db_table" in query
        assert "WHERE" not in query  # No filter when id_value is None
        assert params is None
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["id", "value"]


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
