"""Tests for spatial matching helpers."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon

from niamoto.core.utils.column_detector import SpatialMatcher


def test_check_intersection_counts_distinct_points_with_overlapping_polygons(tmp_path):
    csv_path = tmp_path / "points.csv"
    gpkg_path = tmp_path / "areas.gpkg"

    pd.DataFrame(
        [{"id": 1, "geometry": Point(0, 0).wkt}],
    ).to_csv(csv_path, index=False)
    gpd.GeoDataFrame(
        {
            "name": ["first", "second"],
            "geometry": [
                Polygon([(-1, -1), (1, -1), (1, 1), (-1, 1)]),
                Polygon([(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]),
            ],
        },
        crs="EPSG:4326",
    ).to_file(gpkg_path, layer="areas", driver="GPKG", engine="pyogrio")

    result = SpatialMatcher.check_intersection(csv_path, "geometry", gpkg_path, "areas")

    assert result["has_intersection"] is True
    assert result["total_points"] == 1
    assert result["matched_points"] == 1
    assert result["coverage_percent"] == 100.0
