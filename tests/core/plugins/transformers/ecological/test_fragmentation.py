# Contents for test_fragmentation.py

import pytest
import geopandas as gpd
from shapely.geometry import Polygon
from unittest.mock import patch, MagicMock

from niamoto.core.plugins.transformers.ecological.fragmentation import (
    FragmentationAnalysis,
    FragmentationConfig,
)
from niamoto.common.exceptions import DataTransformError

# --- Test Data ---


# Sample GeoDataFrame for the area of interest (input 'data' to transform)
@pytest.fixture
def area_of_interest():
    # 10km x 10km square polygon (area = 100 km^2 = 10,000 ha)
    poly = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    gdf = gpd.GeoDataFrame(
        [1], geometry=[poly], crs="EPSG:3857"
    )  # Use a projected CRS (meters)
    return gdf


# Sample GeoDataFrame representing forest patches (mock return value for gpd.read_file)
@pytest.fixture
def mock_forest_data():
    # Create some forest patches within the 10km x 10km area
    # Patch areas in m^2:
    # patch1: 2000m * 2000m = 4,000,000 m^2 = 400 ha
    # patch2: 1000m * 1000m = 1,000,000 m^2 = 100 ha
    # patch3: 500m * 500m   =   250,000 m^2 =  25 ha
    patch1 = Polygon([(1000, 1000), (3000, 1000), (3000, 3000), (1000, 3000)])
    patch2 = Polygon([(5000, 5000), (6000, 5000), (6000, 6000), (5000, 6000)])
    patch3 = Polygon([(8000, 8000), (8500, 8000), (8500, 8500), (8000, 8500)])
    # Patch outside the area_of_interest, should be ignored
    patch_outside = Polygon(
        [(11000, 1000), (12000, 1000), (12000, 2000), (11000, 2000)]
    )

    gdf = gpd.GeoDataFrame(
        {"id": [1, 2, 3, 4]},
        geometry=[patch1, patch2, patch3, patch_outside],
        crs="EPSG:3857",  # Must match area_of_interest CRS
    )
    return gdf


# --- Test Class ---


class TestFragmentationAnalysis:
    """Tests for the FragmentationAnalysis plugin."""

    @pytest.fixture(autouse=True)
    def setup_plugin(self):
        """Initialize the plugin for each test."""
        # Mock the database dependency
        self.plugin = FragmentationAnalysis(db=MagicMock())
        # Mock the base directory getter to avoid filesystem dependency
        self.plugin._get_base_directory = MagicMock(return_value="/fake/base/dir")

    # --- Configuration Validation Tests ---

    def test_valid_config_minimal(self):
        """Test minimal valid configuration."""
        config = {"params": {"forest_path": "dummy/forest.shp"}}
        # Use the plugin's validation method, not direct instantiation
        validated = self.plugin.validate_config(config)
        # Assertions need to access attributes of the validated config object
        assert validated.params["forest_path"] == "dummy/forest.shp"
        # Default values inside the 'params' factory are NOT merged when 'params' is provided.
        # We only need to ensure the mandatory 'forest_path' is validated.
        # The transform method uses .get() to handle defaults for other params like 'metrics'.

    def test_valid_config_full(self):
        """Test full valid configuration with custom metrics and units."""
        config = {
            "params": {
                "forest_path": "forests.gpkg",
                "shape_field": "geom",
                "metrics": ["meff", "edge_density"],
                "area_unit": "km2",
                "edge_width": 50,
                "size_classes": [10, 100, 1000, float("inf")],
            }
        }
        validated = FragmentationConfig(**config)
        assert validated.params["forest_path"] == "forests.gpkg"
        assert validated.params["metrics"] == ["meff", "edge_density"]
        assert validated.params["area_unit"] == "km2"
        assert validated.params["edge_width"] == 50

    def test_invalid_config_missing_forest_path(self):
        """Test config validation fails if forest_path is missing."""
        config = {
            "plugin": "fragmentation_analysis",
            "params": {},
        }  # Missing forest_path
        # The plugin's validate_config wraps Pydantic/custom checks
        with pytest.raises(
            DataTransformError, match="path to the forest layer is required"
        ):
            self.plugin.validate_config(config)

    def test_invalid_config_bad_metric(self):
        """Test config validation fails with an invalid metric name."""
        config = {
            "params": {"forest_path": "f.shp", "metrics": ["patch_count", "bad_metric"]}
        }
        # Pydantic validator in FragmentationConfig catches this
        with pytest.raises(ValueError, match="Unsupported metric: bad_metric"):
            FragmentationConfig(**config)

    def test_invalid_config_bad_area_unit(self):
        """Test config validation fails with an invalid area unit."""
        config = {"params": {"forest_path": "f.shp", "area_unit": "acres"}}
        # Pydantic validator in FragmentationConfig catches this
        with pytest.raises(ValueError, match="Invalid area unit: acres"):
            FragmentationConfig(**config)

    # --- Transformation Logic Tests (Initial) ---

    @patch("geopandas.read_file")
    def test_transform_basic_patch_count(
        self, mock_read_file, area_of_interest, mock_forest_data
    ):
        """Test basic transformation calculating only patch count and area."""
        mock_read_file.return_value = mock_forest_data
        config = {
            "params": {
                "forest_path": "dummy/forest.shp",  # Path doesn't matter due to mock
                "metrics": ["patch_count"],  # Only request patch count related metrics
                "area_unit": "ha",  # Explicitly set for clarity, matches default
            }
        }

        # Pass the GeoDataFrame fixture directly
        result = self.plugin.transform(area_of_interest, config)

        # Expectations based on mock_forest_data and area_of_interest:
        # - 3 patches from mock_forest_data intersect the 10k x 10k area_of_interest.
        # - Total area = 400ha + 100ha + 25ha = 525ha
        assert result["patch_count"] == 3
        assert result["total_forest_area"] == pytest.approx(525.0)
        assert result["area_unit"] == "ha"
        # patch_sizes are calculated internally and should match
        assert sorted([round(p, 2) for p in result["patch_sizes"]]) == sorted(
            [400.0, 100.0, 25.0]
        )

        # Verify the mock was called correctly with the full path
        expected_path = "/fake/base/dir/dummy/forest.shp"
        mock_read_file.assert_called_once_with(expected_path)

    @patch("geopandas.read_file")
    def test_transform_no_intersecting_forest(self, mock_read_file, area_of_interest):
        """Test transformation returns empty results when no forest patches intersect the area."""
        # Mock returns forest data completely outside the AOI
        patch_far_outside = Polygon([(20000, 20000), (21000, 20000), (21000, 21000)])
        mock_forest_outside = gpd.GeoDataFrame(
            [1], geometry=[patch_far_outside], crs="EPSG:3857"
        )
        mock_read_file.return_value = mock_forest_outside

        config = {
            "params": {
                "forest_path": "dummy/outside.shp",
                "metrics": [
                    "patch_count",
                    "meff",
                    "edge_density",
                ],  # Request several metrics
                "area_unit": "km2",  # Use a different unit
            }
        }
        # Pass the GeoDataFrame fixture directly
        result = self.plugin.transform(area_of_interest, config)

        # Expect the structure from _empty_results
        assert result["patch_count"] == 0
        assert result["patch_sizes"] == []
        assert result["total_forest_area"] == 0.0
        assert result["area_unit"] == "km2"
        assert result["meff"] == 0.0
        assert result["meff_unit"] == "km2"  # Expect 'km2' as per the code logic
        assert result["edge_length"] == 0.0
        assert result["edge_density"] == 0.0
        assert result["edge_unit"] == "m/km2"  # Density unit depends on area_unit

        # Verify the mock was called correctly with the full path
        expected_path = "/fake/base/dir/dummy/outside.shp"
        mock_read_file.assert_called_once_with(expected_path)

    # --- TODO: Add more specific tests ---
    # - Test each metric individually (meff, lpi, edge_density, core_area, connectivity, size_dist)
    #   with known geometries to verify calculations.
    # - Test different area_units (km2, m2) and check if calculations/results scale correctly.
    # - Test error handling (e.g., file not found if mock is not used, invalid geometry in input data).
    # - Test edge cases (e.g., single large patch, many tiny patches).
