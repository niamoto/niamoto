"""Targeted tests for auto-config reference naming."""

from __future__ import annotations

from pathlib import Path

from niamoto.core.imports.auto_config_service import AutoConfigService


def test_build_simple_reference_config_sets_schema_name_field(tmp_path: Path):
    service = AutoConfigService(tmp_path)

    config = service._build_simple_reference_config(
        "imports/plots.csv",
        {
            "columns": ["id_plot", "plot", "geo_pt"],
            "id_columns": ["id_plot"],
            "name_columns": ["id_plot", "plot"],
            "geometry_columns": ["geo_pt"],
        },
        relation_info=[
            {
                "from": "occurrences",
                "field": "plot_name",
                "target_field": "plot",
                "confidence": 0.9,
            }
        ],
        decision_summary={"occurrences": {"final_entity_type": "dataset"}},
    )

    assert config["schema"]["id_field"] == "id_plot"
    assert config["schema"]["name_field"] == "plot"
    assert config["relation"]["reference_key"] == "plot"


def test_pick_display_name_column_ignores_id_like_name_candidates(tmp_path: Path):
    service = AutoConfigService(tmp_path)

    picked = service._pick_display_name_column(
        {
            "columns": ["id_plot", "plot", "geo_pt"],
            "name_columns": ["id_plot", "plot"],
        },
        id_field="id_plot",
        entity_name="plots",
    )

    assert picked == "plot"


def test_build_shapes_reference_sets_schema_name_field(tmp_path: Path):
    service = AutoConfigService(tmp_path)

    config = service._build_shapes_reference(
        [{"name": "Communes", "path": "imports/communes.gpkg", "name_field": "nom"}]
    )

    assert config["schema"]["name_field"] == "name"


def test_build_derived_hierarchy_reference_sets_full_name_field(tmp_path: Path):
    service = AutoConfigService(tmp_path)

    config = service._build_derived_hierarchy_reference(
        "occurrences",
        {
            "columns": ["id_taxonref", "taxaname", "family", "genus", "species"],
            "name_columns": ["taxaname"],
            "hierarchy": {
                "levels": ["family", "genus", "species"],
                "column_mapping": {
                    "family": "family",
                    "genus": "genus",
                    "species": "species",
                },
            },
        },
    )

    assert config["schema"]["id_field"] == "id"
    assert config["schema"]["name_field"] == "full_name"
    assert config["connector"]["extraction"]["name_column"] == "taxaname"
