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


def test_forest_elevation_typed_params_drive_valid_data_path(
    monkeypatch, simple_area, tmp_path
):
    class FakeRaster:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_mask(src, geometries, crop, nodata):
        return np.array([[[50, 150]]]), object()

    forest_layer = gpd.GeoDataFrame(
        {"type": ["Core forest"]},
        geometry=[Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])],
        crs=simple_area.crs,
    )

    monkeypatch.setattr(
        "niamoto.core.plugins.transformers.ecological.forest_elevation.rasterio.open",
        lambda path: FakeRaster(),
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.transformers.ecological.forest_elevation.mask",
        fake_mask,
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.transformers.ecological.forest_elevation.gpd.read_file",
        lambda path, engine=None: forest_layer,
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.transformers.ecological.forest_elevation.rasterio.features.rasterize",
        lambda *args, **kwargs: np.array([[1, 0]], dtype=np.uint8),
    )

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

    result = plugin.transform(simple_area, config)

    assert result["forest_core_forest"] == [100.0, 0.0]
    assert result["forest_total"] == [100.0, 0.0]


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


def test_land_use_typed_params_drive_valid_layer_processing(
    monkeypatch, simple_area, tmp_path
):
    reserve_layer = gpd.GeoDataFrame(
        {"type": ["Reserve"]},
        geometry=[Polygon([(0, 0), (50, 0), (50, 100), (0, 100)])],
        crs=simple_area.crs,
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.transformers.ecological.land_use.gpd.read_file",
        lambda path, engine=None: reserve_layer,
    )

    plugin = LandUseAnalysis(db=MagicMock())
    plugin.logger = MagicMock()
    plugin._get_base_directory = MagicMock(return_value=str(tmp_path))
    config = {
        "params": {
            "layers": [
                {
                    "path": "reserve.shp",
                    "field": "type",
                    "categories": ["Reserve"],
                }
            ],
            "area_unit": "ha",
        }
    }

    result = plugin.transform(simple_area, config)

    assert result["categories"] == ["Reserve"]
    assert result["areas"] == [0.5]
    assert result["total_area"] == 1.0


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


def test_forest_holdridge_typed_params_drive_valid_raster_and_forest_path(
    monkeypatch, simple_area
):
    class FakeRaster:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_mask(src, geometries, crop, nodata):
        return np.array([[[1, 2]]]), object()

    forest_layer = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])],
        crs=simple_area.crs,
    )

    monkeypatch.setattr(forest_holdridge.rasterio, "open", lambda path: FakeRaster())
    monkeypatch.setattr(forest_holdridge, "mask", fake_mask)
    monkeypatch.setattr(
        forest_holdridge.gpd,
        "read_file",
        lambda path, engine=None: forest_layer,
    )
    monkeypatch.setattr(
        forest_holdridge.rasterio.features,
        "rasterize",
        lambda *args, **kwargs: np.array([[1, 0]], dtype=np.uint8),
    )

    plugin = ForestHoldridgeAnalysis(db=MagicMock())
    config = {
        "params": {
            "forest_path": "forest.shp",
            "holdridge_path": "holdridge.tif",
            "holdridge_values": {1: "Dry", 2: "Humid"},
            "nodata": -9999,
        }
    }

    result = plugin.transform(simple_area, config)

    assert result["forest"]["dry"] == 0.5
    assert result["forest"]["humid"] == 0.0
    assert result["non_forest"]["dry"] == 0.0
    assert result["non_forest"]["humid"] == 0.5
