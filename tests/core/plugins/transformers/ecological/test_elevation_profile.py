"""Tests for the ElevationProfile transformer plugin."""

import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import Polygon
from unittest.mock import patch, MagicMock
import tempfile
import os

from niamoto.core.plugins.transformers.ecological.elevation_profile import (
    ElevationProfile,
    ElevationProfileConfig,
)
from niamoto.common.exceptions import DataTransformError


# Fixtures for test data
@pytest.fixture
def simple_polygon():
    """Create a simple polygon for testing."""
    return Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])


@pytest.fixture
def simple_polygon_gdf(simple_polygon):
    """Create a simple GeoDataFrame with polygon."""
    return gpd.GeoDataFrame(
        {"id": [1], "name": ["test"]}, geometry=[simple_polygon], crs="EPSG:4326"
    )


@pytest.fixture
def temp_dem():
    """Create a temporary DEM (Digital Elevation Model) file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_dem.tif")

        # Create a DEM with elevation values from 0 to 999
        # 10x10 grid with gradual elevation increase
        elevation_data = np.arange(0, 1000, 10, dtype=np.float32).reshape(1, 10, 10)

        transform = from_bounds(0, 0, 1, 1, 10, 10)

        with rasterio.open(
            filepath,
            "w",
            driver="GTiff",
            height=10,
            width=10,
            count=1,
            dtype=elevation_data.dtype,
            crs="EPSG:4326",
            transform=transform,
            nodata=-9999,
        ) as dst:
            dst.write(elevation_data)

        yield filepath


@pytest.fixture
def temp_dem_with_nodata():
    """Create a DEM with nodata values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_dem_nodata.tif")

        # Create DEM with some nodata cells
        elevation_data = np.arange(0, 1000, 10, dtype=np.float32).reshape(1, 10, 10)
        elevation_data[0, 0:3, 0:3] = -9999  # Set some cells to nodata

        transform = from_bounds(0, 0, 1, 1, 10, 10)

        with rasterio.open(
            filepath,
            "w",
            driver="GTiff",
            height=10,
            width=10,
            count=1,
            dtype=elevation_data.dtype,
            crs="EPSG:4326",
            transform=transform,
            nodata=-9999,
        ) as dst:
            dst.write(elevation_data)

        yield filepath


@pytest.fixture
def temp_forest_layer(simple_polygon):
    """Create a temporary forest coverage shapefile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_forest.shp")

        # Create forest polygons (covering part of the area)
        forest_poly1 = Polygon([(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)])
        forest_poly2 = Polygon([(0.5, 0.5), (1, 0.5), (1, 1), (0.5, 1)])

        forest_gdf = gpd.GeoDataFrame(
            {"id": [1, 2], "type": ["primary", "secondary"]},
            geometry=[forest_poly1, forest_poly2],
            crs="EPSG:4326",
        )

        forest_gdf.to_file(filepath)
        yield filepath


@pytest.fixture
def plugin():
    """Create an ElevationProfile plugin instance."""
    mock_db = MagicMock()
    return ElevationProfile(db=mock_db)


# Configuration validation tests
class TestElevationProfileConfig:
    """Test ElevationProfileConfig validation."""

    def test_valid_config(self, temp_dem):
        """Test valid configuration."""
        config = ElevationProfileConfig(
            plugin="elevation_profile",
            params={"dem_path": temp_dem, "bins": 10, "area_unit": "ha"},
        )
        assert config.params["dem_path"] == temp_dem
        assert config.params["bins"] == 10

    def test_config_missing_dem_path(self):
        """Test validation fails when dem_path is missing."""
        with pytest.raises(ValueError) as exc_info:
            ElevationProfileConfig(plugin="elevation_profile", params={})
        assert "DEM is required" in str(exc_info.value)

    def test_config_invalid_bins(self, temp_dem):
        """Test validation fails when bins is not an integer."""
        with pytest.raises(ValueError) as exc_info:
            ElevationProfileConfig(
                plugin="elevation_profile",
                params={"dem_path": temp_dem, "bins": "ten"},
            )
        assert "must be an integer" in str(exc_info.value)

    def test_config_invalid_custom_bins(self, temp_dem):
        """Test validation fails for invalid custom_bins."""
        # Not a list
        with pytest.raises(ValueError):
            ElevationProfileConfig(
                plugin="elevation_profile",
                params={"dem_path": temp_dem, "custom_bins": 100},
            )

        # Too few values
        with pytest.raises(ValueError):
            ElevationProfileConfig(
                plugin="elevation_profile",
                params={"dem_path": temp_dem, "custom_bins": [100]},
            )

        # Not in ascending order
        with pytest.raises(ValueError) as exc_info:
            ElevationProfileConfig(
                plugin="elevation_profile",
                params={"dem_path": temp_dem, "custom_bins": [100, 50, 200]},
            )
        assert "ascending order" in str(exc_info.value)

    def test_config_overlay_forest_requires_path(self, temp_dem):
        """Test that overlay_forest requires forest_path."""
        with pytest.raises(ValueError) as exc_info:
            ElevationProfileConfig(
                plugin="elevation_profile",
                params={"dem_path": temp_dem, "overlay_forest": True},
            )
        assert "forest coverage layer is required" in str(exc_info.value)

    def test_config_invalid_area_unit(self, temp_dem):
        """Test validation fails for invalid area unit."""
        with pytest.raises(ValueError) as exc_info:
            ElevationProfileConfig(
                plugin="elevation_profile",
                params={"dem_path": temp_dem, "area_unit": "acres"},
            )
        assert "Invalid unit of area" in str(exc_info.value)

    def test_config_valid_custom_bins(self, temp_dem):
        """Test valid custom_bins configuration."""
        config = ElevationProfileConfig(
            plugin="elevation_profile",
            params={
                "dem_path": temp_dem,
                "custom_bins": [0, 100, 200, 500, 1000],
            },
        )
        assert config.params["custom_bins"] == [0, 100, 200, 500, 1000]


class TestElevationProfileBasics:
    """Test basic ElevationProfile functionality."""

    def test_validate_config_success(self, plugin, temp_dem):
        """Test successful config validation."""
        config = {
            "plugin": "elevation_profile",
            "params": {"dem_path": temp_dem, "bins": 5},
        }
        validated = plugin.validate_config(config)
        assert isinstance(validated, ElevationProfileConfig)

    def test_validate_config_error(self, plugin):
        """Test config validation error."""
        config = {"plugin": "elevation_profile", "params": {}}
        with pytest.raises(DataTransformError):
            plugin.validate_config(config)

    def test_get_base_directory(self, plugin):
        """Test base directory retrieval."""
        base_dir = plugin._get_base_directory()
        assert os.path.isabs(base_dir)


class TestTransformBasic:
    """Test basic transform functionality."""

    def test_transform_basic_elevation_profile(
        self, plugin, simple_polygon_gdf, temp_dem
    ):
        """Test basic elevation profile creation."""
        config = {
            "plugin": "elevation_profile",
            "params": {
                "dem_path": temp_dem,
                "bins": 5,
                "nodata": -9999,
                "area_unit": "ha",
            },
        }

        result = plugin.transform(simple_polygon_gdf, config)

        assert "class_name" in result
        assert "pixel_count" in result
        assert "area" in result
        assert "bin_edges" in result
        assert "area_unit" in result
        assert result["area_unit"] == "ha"
        assert len(result["class_name"]) == 5  # 5 bins

    def test_transform_with_custom_bins(self, plugin, simple_polygon_gdf, temp_dem):
        """Test elevation profile with custom bins."""
        config = {
            "plugin": "elevation_profile",
            "params": {
                "dem_path": temp_dem,
                "custom_bins": [0, 200, 400, 600, 800, 1000],
                "nodata": -9999,
            },
        }

        result = plugin.transform(simple_polygon_gdf, config)

        assert "class_name" in result
        assert len(result["class_name"]) == 5  # 5 classes from 6 bin edges
        assert result["bin_edges"] == [0, 200, 400, 600, 800, 1000]

    def test_transform_different_area_units(self, plugin, simple_polygon_gdf, temp_dem):
        """Test elevation profile with different area units."""
        # Test ha
        config_ha = {
            "plugin": "elevation_profile",
            "params": {
                "dem_path": temp_dem,
                "bins": 5,
                "area_unit": "ha",
                "nodata": -9999,
            },
        }
        result_ha = plugin.transform(simple_polygon_gdf, config_ha)

        # Test km2
        config_km2 = {
            "plugin": "elevation_profile",
            "params": {
                "dem_path": temp_dem,
                "bins": 5,
                "area_unit": "km2",
                "nodata": -9999,
            },
        }
        result_km2 = plugin.transform(simple_polygon_gdf, config_km2)

        # Test m2
        config_m2 = {
            "plugin": "elevation_profile",
            "params": {
                "dem_path": temp_dem,
                "bins": 5,
                "area_unit": "m2",
                "nodata": -9999,
            },
        }
        result_m2 = plugin.transform(simple_polygon_gdf, config_m2)

        # Check conversions
        assert result_ha["area_unit"] == "ha"
        assert result_km2["area_unit"] == "km2"
        assert result_m2["area_unit"] == "m2"

        # m2 should have largest values
        assert sum(result_m2["area"]) > sum(result_ha["area"])
        assert sum(result_m2["area"]) > sum(result_km2["area"])

    def test_transform_with_nodata_handling(
        self, plugin, simple_polygon_gdf, temp_dem_with_nodata
    ):
        """Test elevation profile with nodata values."""
        config = {
            "plugin": "elevation_profile",
            "params": {
                "dem_path": temp_dem_with_nodata,
                "bins": 5,
                "nodata": -9999,
            },
        }

        result = plugin.transform(simple_polygon_gdf, config)

        # Should have excluded nodata cells
        assert "class_name" in result
        assert sum(result["pixel_count"]) < 100  # Less than total 100 pixels

    def test_transform_all_nodata(self, plugin, simple_polygon_gdf):
        """Test elevation profile when all data is nodata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "all_nodata.tif")

            # Create DEM with all nodata
            elevation_data = np.full((1, 10, 10), -9999, dtype=np.float32)
            transform = from_bounds(0, 0, 1, 1, 10, 10)

            with rasterio.open(
                filepath,
                "w",
                driver="GTiff",
                height=10,
                width=10,
                count=1,
                dtype=elevation_data.dtype,
                crs="EPSG:4326",
                transform=transform,
                nodata=-9999,
            ) as dst:
                dst.write(elevation_data)

            config = {
                "plugin": "elevation_profile",
                "params": {"dem_path": filepath, "bins": 5, "nodata": -9999},
            }

            result = plugin.transform(simple_polygon_gdf, config)
            assert "error" in result
            assert "No valid elevation data" in result["error"]


class TestTransformInputValidation:
    """Test transform input validation."""

    def test_transform_not_geodataframe(self, plugin, temp_dem):
        """Test error when input is not a GeoDataFrame."""
        df = pd.DataFrame({"id": [1], "value": [10]})
        config = {
            "plugin": "elevation_profile",
            "params": {"dem_path": temp_dem, "bins": 5},
        }

        with pytest.raises(DataTransformError) as exc_info:
            plugin.transform(df, config)
        assert "must be a GeoDataFrame" in str(exc_info.value)

    def test_transform_empty_geometry(self, plugin, temp_dem):
        """Test error when geometry is empty."""
        empty_gdf = gpd.GeoDataFrame({"geometry": []}, crs="EPSG:4326")
        config = {
            "plugin": "elevation_profile",
            "params": {"dem_path": temp_dem, "bins": 5},
        }

        with pytest.raises(DataTransformError) as exc_info:
            plugin.transform(empty_gdf, config)
        assert "No geometry found" in str(exc_info.value)

    def test_transform_invalid_dem_path(self, plugin, simple_polygon_gdf):
        """Test error when DEM file doesn't exist."""
        config = {
            "plugin": "elevation_profile",
            "params": {"dem_path": "/nonexistent/dem.tif", "bins": 5},
        }

        with pytest.raises(DataTransformError) as exc_info:
            plugin.transform(simple_polygon_gdf, config)
        assert "Error opening the DEM" in str(exc_info.value)


class TestForestDistribution:
    """Test forest distribution overlay functionality."""

    def test_transform_with_forest_overlay(
        self, plugin, simple_polygon_gdf, temp_dem, temp_forest_layer
    ):
        """Test elevation profile with forest overlay."""
        config = {
            "plugin": "elevation_profile",
            "params": {
                "dem_path": temp_dem,
                "bins": 5,
                "nodata": -9999,
                "overlay_forest": True,
                "forest_path": temp_forest_layer,
                "area_unit": "ha",
            },
        }

        result = plugin.transform(simple_polygon_gdf, config)

        assert "forest_distribution" in result
        forest_dist = result["forest_distribution"]
        assert "forest_area" in forest_dist
        assert "forest_percentage" in forest_dist
        assert "forest_pixels" in forest_dist
        assert "total_pixels" in forest_dist
        assert len(forest_dist["forest_area"]) == 5  # 5 bins

    def test_calculate_forest_distribution_empty_forest(
        self, plugin, simple_polygon, temp_dem
    ):
        """Test forest distribution with empty forest layer."""
        # Create empty forest shapefile
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "empty_forest.shp")
            empty_forest = gpd.GeoDataFrame({"geometry": []}, crs="EPSG:4326")
            empty_forest.to_file(filepath)

            # Create elevation data
            elevation_data = np.arange(100, dtype=np.float32).reshape(10, 10)
            valid_mask = np.ones((10, 10), dtype=bool)
            bin_edges = np.array([0, 25, 50, 75, 100])
            transform = from_bounds(0, 0, 1, 1, 10, 10)

            result = plugin._calculate_forest_distribution(
                filepath,
                simple_polygon,
                "EPSG:4326",
                elevation_data,
                bin_edges,
                valid_mask,
                transform,
                1.0,  # pixel_area
                0.0001,  # area_factor for ha
            )

            assert result is not None
            assert all(area == 0 for area in result["forest_area"])
            assert all(pct == 0 for pct in result["forest_percentage"])

    def test_calculate_forest_distribution_crs_mismatch(
        self, plugin, simple_polygon, temp_forest_layer, temp_dem
    ):
        """Test forest distribution handles CRS mismatch."""
        # Create elevation data in EPSG:4326
        elevation_data = np.arange(100, dtype=np.float32).reshape(10, 10)
        valid_mask = np.ones((10, 10), dtype=bool)
        bin_edges = np.array([0, 25, 50, 75, 100])
        transform = from_bounds(0, 0, 1, 1, 10, 10)

        # Forest is in EPSG:4326, test with different CRS
        result = plugin._calculate_forest_distribution(
            temp_forest_layer,
            simple_polygon,
            "EPSG:3857",  # Different CRS
            elevation_data,
            bin_edges,
            valid_mask,
            transform,
            1.0,
            0.0001,
        )

        # Should handle reprojection
        assert result is not None

    def test_calculate_forest_distribution_no_overlap(
        self, plugin, simple_polygon, temp_dem
    ):
        """Test forest distribution when forest doesn't overlap area."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "far_forest.shp")

            # Create forest far from the test area
            far_forest_poly = Polygon([(10, 10), (11, 10), (11, 11), (10, 11)])
            far_forest = gpd.GeoDataFrame(
                {"id": [1]}, geometry=[far_forest_poly], crs="EPSG:4326"
            )
            far_forest.to_file(filepath)

            elevation_data = np.arange(100, dtype=np.float32).reshape(10, 10)
            valid_mask = np.ones((10, 10), dtype=bool)
            bin_edges = np.array([0, 25, 50, 75, 100])
            transform = from_bounds(0, 0, 1, 1, 10, 10)

            result = plugin._calculate_forest_distribution(
                filepath,
                simple_polygon,
                "EPSG:4326",
                elevation_data,
                bin_edges,
                valid_mask,
                transform,
                1.0,
                0.0001,
            )

            assert result is not None
            assert all(area == 0 for area in result["forest_area"])

    def test_calculate_forest_distribution_error_handling(self, plugin, simple_polygon):
        """Test forest distribution error handling."""
        elevation_data = np.arange(100, dtype=np.float32).reshape(10, 10)
        valid_mask = np.ones((10, 10), dtype=bool)
        bin_edges = np.array([0, 25, 50, 75, 100])
        transform = from_bounds(0, 0, 1, 1, 10, 10)

        # Use a relative path that doesn't exist
        with patch.object(plugin, "_get_base_directory", return_value="/tmp"):
            # Nonexistent forest file
            result = plugin._calculate_forest_distribution(
                "nonexistent_forest.shp",  # Relative path
                simple_polygon,
                "EPSG:4326",
                elevation_data,
                bin_edges,
                valid_mask,
                transform,
                1.0,
                0.0001,
            )

            assert result is None  # Should return None on error


class TestElevationClasses:
    """Test elevation class creation."""

    def test_automatic_bins_rounding(self, plugin, simple_polygon_gdf):
        """Test that automatic bins round to nearest 100."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_rounding.tif")

            # Create DEM with values 150-750 (should round to 100-800)
            elevation_data = np.linspace(150, 750, 100, dtype=np.float32).reshape(
                1, 10, 10
            )
            transform = from_bounds(0, 0, 1, 1, 10, 10)

            with rasterio.open(
                filepath,
                "w",
                driver="GTiff",
                height=10,
                width=10,
                count=1,
                dtype=elevation_data.dtype,
                crs="EPSG:4326",
                transform=transform,
            ) as dst:
                dst.write(elevation_data)

            config = {
                "plugin": "elevation_profile",
                "params": {"dem_path": filepath, "bins": 5, "nodata": -9999},
            }

            result = plugin.transform(simple_polygon_gdf, config)

            # First bin edge should be rounded down to nearest 100
            # Last bin edge should be rounded up to nearest 100
            assert result["bin_edges"][0] == 100.0
            assert result["bin_edges"][-1] == 800.0

    def test_class_name_formatting(self, plugin, simple_polygon_gdf, temp_dem):
        """Test that class names are properly formatted."""
        config = {
            "plugin": "elevation_profile",
            "params": {"dem_path": temp_dem, "bins": 3, "nodata": -9999},
        }

        result = plugin.transform(simple_polygon_gdf, config)

        # Class names should be in format "min-max"
        for class_name in result["class_name"]:
            assert "-" in class_name
            parts = class_name.split("-")
            assert len(parts) == 2
            # Should be parseable as integers
            assert int(parts[0]) < int(parts[1])


class TestRelativePathResolution:
    """Test relative path resolution."""

    def test_relative_dem_path_resolution(self, plugin, simple_polygon_gdf, temp_dem):
        """Test that relative DEM paths are resolved."""
        base_dir = os.path.dirname(temp_dem)
        filename = os.path.basename(temp_dem)

        with patch.object(plugin, "_get_base_directory", return_value=base_dir):
            config = {
                "plugin": "elevation_profile",
                "params": {
                    "dem_path": filename,
                    "bins": 5,
                    "nodata": -9999,
                },  # Relative path
            }

            result = plugin.transform(simple_polygon_gdf, config)
            assert "class_name" in result

    def test_relative_forest_path_resolution(
        self, plugin, simple_polygon_gdf, temp_dem, temp_forest_layer
    ):
        """Test that relative forest paths are resolved."""
        base_dir = os.path.dirname(temp_forest_layer)
        dem_filename = os.path.basename(temp_dem)
        forest_filename = os.path.basename(temp_forest_layer)

        # Copy DEM to same directory as forest
        import shutil

        dem_in_forest_dir = os.path.join(base_dir, dem_filename)
        shutil.copy(temp_dem, dem_in_forest_dir)

        with patch.object(plugin, "_get_base_directory", return_value=base_dir):
            config = {
                "plugin": "elevation_profile",
                "params": {
                    "dem_path": dem_filename,
                    "overlay_forest": True,
                    "forest_path": forest_filename,
                    "bins": 5,
                    "nodata": -9999,
                },
            }

            result = plugin.transform(simple_polygon_gdf, config)
            assert "forest_distribution" in result


class TestPixelAreaCalculation:
    """Test pixel area calculation."""

    def test_pixel_area_affects_results(self, plugin, simple_polygon_gdf):
        """Test that different pixel sizes affect area distribution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two DEMs with same elevation data but different pixel sizes

            # Small pixels (higher resolution)
            filepath_small = os.path.join(tmpdir, "small_pixels.tif")
            elevation_data = np.arange(100, dtype=np.float32).reshape(1, 10, 10)
            transform_small = from_bounds(0, 0, 1, 1, 10, 10)

            with rasterio.open(
                filepath_small,
                "w",
                driver="GTiff",
                height=10,
                width=10,
                count=1,
                dtype=elevation_data.dtype,
                crs="EPSG:4326",
                transform=transform_small,
            ) as dst:
                dst.write(elevation_data)

            # Large pixels (lower resolution)
            filepath_large = os.path.join(tmpdir, "large_pixels.tif")
            transform_large = from_bounds(0, 0, 10, 10, 10, 10)  # 10x larger

            with rasterio.open(
                filepath_large,
                "w",
                driver="GTiff",
                height=10,
                width=10,
                count=1,
                dtype=elevation_data.dtype,
                crs="EPSG:4326",
                transform=transform_large,
            ) as dst:
                dst.write(elevation_data)

            config_small = {
                "plugin": "elevation_profile",
                "params": {
                    "dem_path": filepath_small,
                    "bins": 5,
                    "area_unit": "m2",
                    "nodata": -9999,
                },
            }

            config_large = {
                "plugin": "elevation_profile",
                "params": {
                    "dem_path": filepath_large,
                    "bins": 5,
                    "area_unit": "m2",
                    "nodata": -9999,
                },
            }

            result_small = plugin.transform(simple_polygon_gdf, config_small)
            result_large = plugin.transform(simple_polygon_gdf, config_large)

            # Different pixel sizes should produce different area distributions
            # (even if total area is similar, the distribution across bins should differ)
            assert result_small["area"] != result_large["area"]
