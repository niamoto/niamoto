from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from niamoto.core.imports.config_models import GenericImportConfig
from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.core.services.importer import ImporterService
from niamoto.gui.api import context
from niamoto.gui.api.services.templates.suggestion_service import (
    generate_navigation_suggestion,
    get_class_object_suggestions,
    get_entity_map_suggestions,
    get_reference_field_suggestions,
)


INSTANCE_DIR = Path(__file__).parents[5] / "test-instance" / "niamoto-subset"


def _stage_subset_project(
    instance_dir: Path, tmp_path: Path, rel_paths: list[str]
) -> Path:
    for rel_path in rel_paths:
        source = instance_dir / rel_path
        destination = tmp_path / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return tmp_path


@pytest.fixture(scope="module")
def imported_subset_project(tmp_path_factory: pytest.TempPathFactory):
    project_dir = tmp_path_factory.mktemp("niamoto_subset_benchmark")
    _stage_subset_project(
        INSTANCE_DIR,
        project_dir,
        [
            "config/config.yml",
            "config/import.yml",
            "config/transform.yml",
            "imports/occurrences.csv",
            "imports/plots.csv",
            "imports/holdridge_zones.gpkg",
            "imports/mines.gpkg",
            "imports/raw_plot_stats.csv",
            "imports/raw_shape_stats.csv",
        ],
    )
    (project_dir / "db").mkdir(exist_ok=True)

    with open(project_dir / "config" / "import.yml", "r", encoding="utf-8") as f:
        config = GenericImportConfig.from_dict(yaml.safe_load(f) or {})

    service = ImporterService(str(project_dir / "db" / "niamoto.duckdb"))
    try:
        service.import_all(config)
    finally:
        service.close()

    return project_dir


@pytest.fixture(scope="module", autouse=True)
def _ensure_plugins_loaded():
    PluginLoader().load_plugins_with_cascade()


@pytest.mark.integration
def test_subset_instance_suggestions_cover_navigation_maps_and_widgets(
    imported_subset_project: Path,
):
    with patch.object(context, "_working_directory", imported_subset_project):
        navigation = generate_navigation_suggestion("taxons")
        plot_maps = get_entity_map_suggestions("plots")
        shape_maps = get_entity_map_suggestions("shapes")
        plot_reference_widgets = get_reference_field_suggestions("plots")
        plot_class_widgets = get_class_object_suggestions("plots")
        shape_class_widgets = get_class_object_suggestions("shapes")

    assert navigation is not None
    assert navigation["plugin"] == "hierarchical_nav_widget"
    assert navigation["config"]["lft_field"] == "lft"
    assert navigation["config"]["rght_field"] == "rght"

    assert {s["template_id"] for s in plot_maps} >= {
        "plots_geo_pt_entity_map",
        "plots_geo_pt_all_map",
    }
    assert {s["template_id"] for s in shape_maps} >= {
        "shapes_location_entity_map",
        "shapes_location_all_map",
    }

    assert any(
        suggestion["template_id"] == "basal_area_binned_distribution_bar_plot"
        for suggestion in plot_reference_widgets
    )
    assert any(
        suggestion["template_id"] == "dbh_series_extractor_bar_plot"
        for suggestion in plot_class_widgets
    )
    assert any(
        suggestion["template_id"] == "cover_forest_binary_aggregator_donut_chart"
        for suggestion in shape_class_widgets
    )
