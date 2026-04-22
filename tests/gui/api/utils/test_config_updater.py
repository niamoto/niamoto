"""Tests for GUI-driven import config updater."""

from __future__ import annotations

import yaml

from niamoto.gui.api.utils.config_updater import (
    clean_unused_config,
    update_import_config,
)


def test_clean_unused_config_removes_empty_sections(tmp_path):
    config_path = tmp_path / "import.yml"
    config_path.write_text(
        yaml.safe_dump({"plots": None, "shapes": [], "taxonomy": {"path": "ok"}}),
        encoding="utf-8",
    )

    clean_unused_config(config_path)

    assert yaml.safe_load(config_path.read_text(encoding="utf-8")) == {
        "taxonomy": {"path": "ok"}
    }


def test_update_import_config_writes_plots_without_advanced_options(tmp_path):
    config_path = tmp_path / "import.yml"

    update_import_config(
        config_path=config_path,
        import_type="plots",
        filename="plots.csv",
        field_mappings={
            "identifier": "id_plot",
            "locality": "plot_name",
            "location": "geo_pt",
        },
    )

    assert yaml.safe_load(config_path.read_text(encoding="utf-8")) == {
        "plots": {
            "type": "csv",
            "path": "imports/plots.csv",
            "identifier": "id_plot",
            "locality_field": "plot_name",
            "location_field": "geo_pt",
        }
    }


def test_update_import_config_adds_taxonomy_api_enrichment_defaults(tmp_path):
    config_path = tmp_path / "import.yml"

    update_import_config(
        config_path=config_path,
        import_type="taxonomy",
        filename="taxonomy.csv",
        field_mappings={"family": "fam", "species": "sp", "taxon_id": "taxon_id"},
        advanced_options={
            "apiEnrichment": {
                "enabled": True,
                "plugin": "custom_enricher",
                "endpoint": "https://example.test/api",
                "query_field": None,
            }
        },
    )

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert payload["taxonomy"]["api_enrichment"] == {
        "enabled": True,
        "plugin": "custom_enricher",
        "endpoint": "https://example.test/api",
        "query_field": "full_name",
        "rate_limit": 1.0,
        "cache_results": True,
    }


def test_update_import_config_shapes_replaces_duplicates_and_normalizes_properties(
    tmp_path,
):
    config_path = tmp_path / "import.yml"

    update_import_config(
        config_path=config_path,
        import_type="shapes",
        filename="communes.gpkg",
        field_mappings={"name": "nom", "type": "commune"},
        advanced_options={"properties": "code_insee, province", "is_first_shape": True},
    )
    update_import_config(
        config_path=config_path,
        import_type="shapes",
        filename="communes.gpkg",
        field_mappings={"name": "label", "type": "commune"},
        advanced_options={"properties": ["code_insee"], "is_first_shape": False},
    )

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "shapes": [
            {
                "type": "commune",
                "path": "imports/communes.gpkg",
                "name_field": "label",
                "properties": ["code_insee"],
            }
        ]
    }
