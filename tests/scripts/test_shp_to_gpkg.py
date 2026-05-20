"""Tests for archived shapefile conversion helpers."""

from pathlib import Path

from scripts._archive import shp_to_gpkg


def test_merge_returns_empty_when_all_layers_fail(monkeypatch, tmp_path):
    def fail_read_file(_path):
        raise OSError("missing shapefile")

    monkeypatch.setattr(shp_to_gpkg.gpd, "read_file", fail_read_file)

    converted = shp_to_gpkg.convert_multiple_shapefiles(
        [Path("missing.shp")],
        output_dir=tmp_path,
        merge=True,
    )

    assert converted == []
