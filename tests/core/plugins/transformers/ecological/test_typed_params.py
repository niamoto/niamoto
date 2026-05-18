"""Regression tests for ecological transformers with typed params."""

from unittest.mock import MagicMock

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Polygon

from niamoto.core.plugins.transformers.ecological import forest_holdridge
from niamoto.core.plugins.transformers.ecological.forest_elevation import (
    ForestElevationAnalysis,
)
from niamoto.core.plugins.transformers.ecological.forest_holdridge import (
    ForestHoldridgeAnalysis,
)
from niamoto.core.plugins.transformers.ecological.land_use import LandUseAnalysis


@pytest.fixture
def simple_area():
    polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    return gpd.GeoDataFrame({"id": [1]}, geometry=[polygon], crs="EPSG:3857")


def test_forest_elevation_accepts_typed_params(simple_area, tmp_path):
    plugin = ForestElevationAnalysis(db=MagicMock())
    plugin.logger = MagicMock()
    plugin._get_base_directory = MagicMock(return_value=str(tmp_path))
    config = {
        "params": {
            "forest_types_path": "forest.shp",
            "dem_path": "dem.tif",
            "elevation_bins": [0, 100, 200],
            "forest_types": ["Core forest"],
        }
    }

    validated = plugin.validate_config(config)
    result = plugin.transform(simple_area, config)

    assert validated.params.forest_types_path == "forest.shp"
    assert result["elevation_bins"] == [0, 100, 200]
    assert result["forest_core_forest"] == [0.0, 0.0]


def test_land_use_transform_accepts_typed_params(simple_area, tmp_path):
    plugin = LandUseAnalysis(db=MagicMock())
    plugin.logger = MagicMock()
    plugin._get_base_directory = MagicMock(return_value=str(tmp_path))
    config = {
        "params": {
            "layers": [
                {
                    "path": "missing-layer.shp",
                    "field": "type",
                    "categories": ["Reserve"],
                }
            ],
            "area_unit": "ha",
        }
    }

    result = plugin.transform(simple_area, config)

    assert result["categories"] == ["Reserve"]
    assert result["areas"] == [0.0]
    assert result["area_unit"] == "ha"


def test_forest_holdridge_transform_accepts_typed_params(monkeypatch, simple_area):
    class FakeRaster:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_mask(src, geometries, crop, nodata):
        return np.array([[[nodata, nodata]]]), object()

    monkeypatch.setattr(forest_holdridge.rasterio, "open", lambda path: FakeRaster())
    monkeypatch.setattr(forest_holdridge, "mask", fake_mask)

    plugin = ForestHoldridgeAnalysis(db=MagicMock())
    config = {
        "params": {
            "forest_path": "forest.shp",
            "holdridge_path": "holdridge.tif",
            "holdridge_values": {1: "Dry"},
            "nodata": -9999,
        }
    }

    result = plugin.transform(simple_area, config)

    assert result["error"] == "No valid Holdridge data found in the shape"
    assert result["forest"] == {"dry": 0.0, "humid": 0.0, "very_humid": 0.0}
