from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from niamoto.core.imports.config_models import GenericImportConfig
from niamoto.core.services.importer import ImporterService


def _stage_subset_project(
    instance_dir: Path, tmp_path: Path, rel_paths: list[str]
) -> Path:
    for rel_path in rel_paths:
        source = instance_dir / rel_path
        destination = tmp_path / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return tmp_path


@pytest.mark.slow
@pytest.mark.integration
def test_importer_subset_instance_populates_registry_and_semantic_profiles(
    tmp_path: Path,
    niamoto_subset_instance_dir: Path,
):
    project_dir = _stage_subset_project(
        niamoto_subset_instance_dir,
        tmp_path,
        [
            "config/config.yml",
            "config/import.yml",
            "imports/occurrences.csv",
            "imports/plots.csv",
            "imports/holdridge_zones.gpkg",
            "imports/mines.gpkg",
        ],
    )
    (project_dir / "db").mkdir(exist_ok=True)

    with open(project_dir / "config" / "import.yml", "r", encoding="utf-8") as f:
        config = GenericImportConfig.from_dict(yaml.safe_load(f) or {})

    service = ImporterService(str(project_dir / "db" / "niamoto.duckdb"))
    try:
        result = service.import_all(config)

        assert "Import completed successfully" in result
        assert service.db.has_table("dataset_occurrences")
        assert service.db.has_table("entity_taxons")
        assert service.db.has_table("entity_plots")
        assert service.db.has_table("entity_shapes")

        occurrences = service.registry.get("occurrences")
        taxons = service.registry.get("taxons")
        plots = service.registry.get("plots")
        shapes = service.registry.get("shapes")

        assert occurrences.config["semantic_profile"]["profiling_status"] == "complete"
        assert "column_diagnostics" in occurrences.config["semantic_profile"]
        assert plots.config["semantic_profile"]["profiling_status"] == "complete"
        assert taxons.config["derived"]["source_entity"] == "occurrences"
        assert plots.config["schema"]["id_field"] == "id_plot"
        assert shapes.table_name == "entity_shapes"
    finally:
        service.close()
