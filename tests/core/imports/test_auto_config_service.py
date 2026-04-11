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

    config, warning = service._build_derived_hierarchy_reference(
        "occurrences",
        {
            "columns": ["id_taxonref", "taxaname", "family", "genus", "species"],
            "name_columns": ["taxaname"],
            "ml_predictions": [],
            "hierarchy": {
                "levels": ["family", "genus", "species"],
                "column_mapping": {
                    "family": "family",
                    "genus": "genus",
                    "species": "species",
                },
                "hierarchy_type": "taxonomic",
            },
        },
    )

    assert warning is None
    assert config["schema"]["id_field"] == "id"
    assert config["schema"]["name_field"] == "full_name"
    assert config["connector"]["extraction"]["name_column"] == "taxaname"


def test_build_derived_hierarchy_reference_uses_detected_relation(tmp_path: Path):
    service = AutoConfigService(tmp_path)

    config, warning = service._build_derived_hierarchy_reference(
        "plots",
        {
            "columns": ["id_liste_plots", "country", "plot_name"],
            "name_columns": ["plot_name"],
            "ml_predictions": [],
            "hierarchy": {
                "levels": ["country", "plot_name"],
                "column_mapping": {
                    "country": "country",
                    "plot_name": "plot_name",
                },
                "hierarchy_type": "geographic",
            },
        },
        relation_info=[
            {
                "from": "occurrences",
                "field": "id_table_liste_plots_n",
                "target_field": "id_liste_plots",
                "confidence": 0.98,
            }
        ],
        decision_summary={"occurrences": {"final_entity_type": "dataset"}},
        reference_name="plots_hierarchy",
    )

    assert warning is None
    assert config["connector"]["extraction"]["id_column"] == "id_liste_plots"
    assert config["relation"] == {
        "dataset": "occurrences",
        "foreign_key": "id_table_liste_plots_n",
        "reference_key": "plots_hierarchy_id",
    }


def test_build_derived_hierarchy_reference_prefers_taxonomic_semantics(tmp_path: Path):
    service = AutoConfigService(tmp_path)

    config, warning = service._build_derived_hierarchy_reference(
        "occurrences",
        {
            "columns": [
                "id_n",
                "idtax_individual_f",
                "plot_name",
                "locality_name",
                "tax_fam",
                "tax_gen",
                "tax_sp_level",
            ],
            "name_columns": ["plot_name", "locality_name", "tax_sp_level"],
            "ml_predictions": [
                {
                    "column": "plot_name",
                    "concept": "location.locality",
                    "confidence": 1.0,
                },
                {
                    "column": "locality_name",
                    "concept": "location.locality",
                    "confidence": 1.0,
                },
                {
                    "column": "id_n",
                    "concept": "identifier.record",
                    "confidence": 0.938,
                },
                {
                    "column": "idtax_individual_f",
                    "concept": "identifier.taxon",
                    "confidence": 1.0,
                },
                {
                    "column": "tax_fam",
                    "concept": "taxonomy.family",
                    "confidence": 1.0,
                },
                {
                    "column": "tax_gen",
                    "concept": "taxonomy.genus",
                    "confidence": 1.0,
                },
                {
                    "column": "tax_sp_level",
                    "concept": "taxonomy.species",
                    "confidence": 1.0,
                },
            ],
            "hierarchy": {
                "levels": ["family", "genus", "species"],
                "column_mapping": {
                    "family": "tax_fam",
                    "genus": "tax_gen",
                    "species": "tax_sp_level",
                },
                "hierarchy_type": "taxonomic",
            },
        },
        relation_info=[
            {
                "from": "plots",
                "field": "plot_name",
                "target_field": "plot_name",
                "confidence": 0.8,
            }
        ],
        decision_summary={"plots": {"final_entity_type": "dataset"}},
        reference_name="taxons",
    )

    assert warning is None
    assert config["connector"]["extraction"]["id_column"] == "idtax_individual_f"
    assert config["connector"]["extraction"]["name_column"] == "tax_sp_level"
    assert config["relation"] == {
        "dataset": "occurrences",
        "foreign_key": "idtax_individual_f",
        "reference_key": "taxons_id",
    }


def test_build_derived_hierarchy_reference_warns_when_taxonomic_id_is_missing(
    tmp_path: Path,
):
    service = AutoConfigService(tmp_path)

    config, warning = service._build_derived_hierarchy_reference(
        "occurrences",
        {
            "columns": ["plot_name", "locality_name", "tax_fam", "tax_gen"],
            "name_columns": ["plot_name", "locality_name"],
            "ml_predictions": [
                {
                    "column": "plot_name",
                    "concept": "location.locality",
                    "confidence": 1.0,
                },
                {
                    "column": "locality_name",
                    "concept": "location.locality",
                    "confidence": 1.0,
                },
                {
                    "column": "tax_fam",
                    "concept": "taxonomy.family",
                    "confidence": 1.0,
                },
                {
                    "column": "tax_gen",
                    "concept": "taxonomy.genus",
                    "confidence": 1.0,
                },
            ],
            "hierarchy": {
                "levels": ["family", "genus"],
                "column_mapping": {
                    "family": "tax_fam",
                    "genus": "tax_gen",
                },
                "hierarchy_type": "taxonomic",
            },
        },
        relation_info=[
            {
                "from": "plots",
                "field": "plot_name",
                "target_field": "plot_name",
                "confidence": 0.8,
            }
        ],
        decision_summary={"plots": {"final_entity_type": "dataset"}},
        reference_name="taxons",
    )

    assert "relation" not in config
    assert config["connector"]["extraction"]["id_column"] is None
    assert config["connector"]["extraction"]["name_column"] == "tax_gen"
    assert warning is not None
    assert "taxon identifier compatible" in warning
