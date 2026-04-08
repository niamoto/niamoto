from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Polygon

from niamoto.core.utils.column_detector import GeoPackageAnalyzer


def test_analyze_gpkg_detects_shapes_with_string_dtype_name_fields(tmp_path):
    gpkg_path = tmp_path / "provinces.gpkg"
    gdf = gpd.GeoDataFrame(
        {
            "nom": ["PROVINCE NORD", "PROVINCE SUD"],
            "code_com": ["98827", "98828"],
        },
        geometry=[
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(2, 0), (3, 0), (3, 1), (2, 1)]),
        ],
        crs="EPSG:4326",
    )
    gdf.to_file(gpkg_path, driver="GPKG")

    analysis = GeoPackageAnalyzer.analyze_gpkg(gpkg_path)

    assert analysis["classification"] == "shapes"
    assert "nom" in analysis["name_field_candidates"]
    assert "code_com" not in analysis["name_field_candidates"]
