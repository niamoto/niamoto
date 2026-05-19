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
        assert validated.params.forest_path == "dummy/forest.shp"
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
        assert validated.params.forest_path == "forests.gpkg"
        assert validated.params.metrics == ["meff", "edge_density"]
        assert validated.params.area_unit == "km2"
        assert validated.params.edge_width == 50

    def test_invalid_config_missing_forest_path(self):
        """Test config validation fails if forest_path is missing."""
        config = {
            "plugin": "fragmentation_analysis",
            "params": {},
        }  # Missing forest_path
        # The plugin's validate_config wraps Pydantic/custom checks
        with pytest.raises(DataTransformError, match="Invalid configuration"):
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
        mock_read_file.assert_called_once_with(expected_path, engine="pyogrio")

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
        mock_read_file.assert_called_once_with(expected_path, engine="pyogrio")

    @pytest.mark.parametrize(
        ("area_unit", "expected_density", "expected_unit"),
        [
            ("ha", 1.4, "m/ha"),
            ("km2", 140.0, "m/km²"),
        ],
    )
    @patch("geopandas.read_file")
    def test_transform_edge_density_uses_requested_area_unit(
        self,
        mock_read_file,
        area_of_interest,
        mock_forest_data,
        area_unit,
        expected_density,
        expected_unit,
    ):
        """Test edge density is meters per converted area unit."""
        mock_read_file.return_value = mock_forest_data
        config = {
            "params": {
                "forest_path": "dummy/forest.shp",
                "metrics": ["edge_density"],
                "area_unit": area_unit,
            }
        }

        result = self.plugin.transform(area_of_interest, config)

        assert result["edge_length"] == pytest.approx(14000.0)
        assert result["edge_density"] == pytest.approx(expected_density)
        assert result["edge_unit"] == expected_unit

    @patch("geopandas.read_file")
    def test_transform_advanced_metrics_for_intersecting_forest(
        self, mock_read_file, area_of_interest, mock_forest_data
    ):
        """Test advanced metrics against deterministic non-empty forest patches."""
        mock_read_file.return_value = mock_forest_data
        config = {
            "params": {
                "forest_path": "dummy/forest.shp",
                "metrics": [
                    "patch_count",
                    "meff",
                    "edge_density",
                    "largest_patch_index",
                    "core_area",
                    "connectivity_index",
                    "size_distribution",
                ],
                "area_unit": "ha",
                "edge_width": 100,
            }
        }

        result = self.plugin.transform(area_of_interest, config)

        assert result["patch_count"] == 3
        assert result["patch_sizes"] == pytest.approx([400.0, 100.0, 25.0])
        assert result["total_forest_area"] == pytest.approx(525.0)
        assert result["landscape_area"] == pytest.approx(10000.0)
        assert result["meff"] == pytest.approx(17.0625)
        assert result["meff_unit"] == "ha"
        assert result["largest_patch"] == pytest.approx(400.0)
        assert result["largest_patch_index"] == pytest.approx(4.0)
        assert result["edge_length"] == pytest.approx(14000.0)
        assert result["edge_density"] == pytest.approx(1.4)
        assert result["edge_unit"] == "m/ha"
        assert result["core_areas"] == pytest.approx([324.0, 64.0, 9.0])
        assert result["total_core_area"] == pytest.approx(397.0)
        assert result["core_area_percentage"] == pytest.approx(397.0 / 525.0 * 100)
        assert result["connectivity_index"] == pytest.approx(
            (400.0**2 + 100.0**2 + 25.0**2) / 525.0**2
        )
        assert result["size_classes"] == {
            "labels": [
                "1-5",
                "5-10",
                "10-50",
                "50-100",
                "100-500",
                "500-1000",
                "> 1000",
            ],
            "counts": [0, 0, 1, 0, 2, 0, 0],
            "areas": [0.0, 0.0, 25.0, 0.0, 500.0, 0.0, 0.0],
            "percentages": [0.0, 0.0, 4.76, 0.0, 95.24, 0.0, 0.0],
        }

    @pytest.mark.parametrize(
        ("area_unit", "expected_patch_sizes", "expected_total_area", "expected_meff"),
        [
            ("ha", [400.0, 100.0, 25.0], 525.0, 17.0625),
            ("km2", [4.0, 1.0, 0.25], 5.25, 0.170625),
            ("m2", [4000000.0, 1000000.0, 250000.0], 5250000.0, 170625.0),
        ],
    )
    @patch("geopandas.read_file")
    def test_transform_metrics_scale_with_area_unit(
        self,
        mock_read_file,
        area_of_interest,
        mock_forest_data,
        area_unit,
        expected_patch_sizes,
        expected_total_area,
        expected_meff,
    ):
        """Test area-based metrics scale consistently for each supported unit."""
        mock_read_file.return_value = mock_forest_data
        config = {
            "params": {
                "forest_path": "dummy/forest.shp",
                "metrics": [
                    "patch_count",
                    "meff",
                    "largest_patch_index",
                ],
                "area_unit": area_unit,
            }
        }

        result = self.plugin.transform(area_of_interest, config)

        assert result["area_unit"] == area_unit
        assert result["patch_sizes"] == pytest.approx(expected_patch_sizes)
        assert result["total_forest_area"] == pytest.approx(expected_total_area)
        assert result["meff"] == pytest.approx(expected_meff)
        assert result["largest_patch_index"] == pytest.approx(4.0)
