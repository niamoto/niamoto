from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from niamoto.core.imports.auto_config_service import AutoConfigService


@pytest.mark.integration
def test_auto_config_subset_instance_tracks_validated_import_shape(
    niamoto_subset_instance_dir: Path,
):
    service = AutoConfigService(niamoto_subset_instance_dir)

    with open(
        niamoto_subset_instance_dir / "config" / "import.yml",
        "r",
        encoding="utf-8",
    ) as f:
        validated_import = yaml.safe_load(f) or {}

    result = service.auto_configure(
        [
            "imports/occurrences.csv",
            "imports/plots.csv",
            "imports/raw_plot_stats.csv",
            "imports/raw_shape_stats.csv",
            "imports/holdridge_zones.gpkg",
            "imports/mines.gpkg",
            "imports/amap_raster_holdridge_nc.tif",
            "imports/rainfall_epsg3163.tif",
        ]
    )

    datasets = result["entities"]["datasets"]
    references = result["entities"]["references"]
    summaries = result["decision_summary"]
    layer_names = {layer["name"] for layer in result["entities"]["metadata"]["layers"]}

    validated_datasets = set(validated_import["entities"]["datasets"])
    validated_references = set(validated_import["entities"]["references"])

    assert validated_datasets <= set(datasets)
    assert {"taxons", "shapes"} <= set(references)
    assert {"plots", "taxons", "shapes"} <= validated_references

    assert summaries["occurrences"]["final_entity_type"] == "dataset"
    assert summaries["occurrences"]["review_required"] is True

    assert summaries["plots"]["final_entity_type"] == "reference"
    assert summaries["plots"]["review_required"] is True

    assert summaries["raw_plot_stats"]["final_entity_type"] == "reference"
    assert summaries["raw_plot_stats"]["review_required"] is False

    assert "amap_raster_holdridge_nc" in layer_names
    assert "rainfall_epsg3163" in layer_names
