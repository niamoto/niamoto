"""Targeted tests for auto-config reference naming."""

from __future__ import annotations

from pathlib import Path
import yaml

from niamoto.core.imports.auto_config_service import AutoConfigService
from niamoto.core.utils.column_detector import ColumnDetector


def _write_delayed_plot_relation_files(tmp_path: Path) -> None:
    imports_dir = tmp_path / "imports"
    imports_dir.mkdir()

    plot_rows = [
        (
            f"{index},Plot {index:03d},Country {index // 50},"
            f"Locality {index // 10},POINT (0 {index}),survey,2024,"
            f"provider,{index},0.{index % 10},extra"
        )
        for index in range(1, 102)
    ]
    (imports_dir / "plots.csv").write_text(
        "\n".join(
            [
                (
                    "id_liste_plots,plot_name,country,locality_name,geo_pt,"
                    "method,date_y,data_provider,nbe_stem,prop_det,notes"
                ),
                *plot_rows,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (imports_dir / "occurrences.csv").write_text(
        "\n".join(
            [
                "id,plot_name,id_table_liste_plots_n,stem_diameter,observed_at",
                *[
                    f"{1000 + index},Plot 101,101,{8 + (index % 20) / 2},2024-01-01"
                    for index in range(1, 1200)
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_build_collection_candidates_exposes_reviewable_reference_metadata(
    tmp_path: Path,
):
    service = AutoConfigService(tmp_path)

    candidates = service._build_collection_candidates(
        {
            "references": {
                "taxons": {
                    "kind": "hierarchical",
                    "description": "Taxonomic hierarchy",
                    "schema": {"fields": [{"name": "species", "type": "string"}]},
                }
            },
            "datasets": {
                "occurrences": {
                    "schema": {"fields": [{"name": "taxon_id", "type": "integer"}]}
                }
            },
        }
    )

    assert candidates == [
        {
            "name": "taxons",
            "label": "taxons",
            "source_type": "reference",
            "source_name": "taxons",
            "grain": "taxon",
            "roles": ["site", "api"],
            "visible": True,
            "review_status": "pending",
            "confidence": 0.85,
            "description": "Taxonomic hierarchy",
            "evidence": [
                {
                    "kind": "import_reference",
                    "message": "Declared reference entity 'taxons' in import.yml",
                    "confidence": 0.85,
                    "details": {"kind": "hierarchical"},
                }
            ],
        }
    ]


def test_auxiliary_stats_csv_skips_semantic_ml(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "raw_plot_stats.csv"
    csv_path.write_text(
        "id,class_object,class_name,class_value,class_index,plot_id\n"
        "1,plot,elevation,120,1,plot-a\n",
        encoding="utf-8",
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("semantic ML should be skipped for stats sources")

    monkeypatch.setattr(
        ColumnDetector, "_detect_semantic_columns", classmethod(fail_if_called)
    )

    analysis = AutoConfigService(tmp_path)._analyze_csv_file(
        csv_path, include_sample_rows=False
    )

    assert analysis["ml_predictions"] == []
    assert AutoConfigService(tmp_path)._is_auxiliary_stats_candidate(analysis)


def test_existing_auxiliary_stats_source_is_reused_when_reimported_alone(
    tmp_path: Path,
):
    config_dir = tmp_path / "config"
    imports_dir = tmp_path / "imports"
    config_dir.mkdir()
    imports_dir.mkdir()
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "entities": {
                    "datasets": {},
                    "references": {
                        "sites": {
                            "connector": {
                                "type": "file",
                                "path": "imports/sites.csv",
                            }
                        }
                    },
                },
                "auxiliary_sources": [
                    {
                        "name": "site_metrics",
                        "data": "imports/raw_site_metrics.csv",
                        "grouping": "sites",
                        "relation": {
                            "plugin": "stats_loader",
                            "key": "id",
                            "ref_field": "site_code",
                            "match_field": "site_id",
                        },
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (imports_dir / "raw_site_metrics.csv").write_text(
        "site_id,class_object,class_name,class_value\ns1,canopy,closed,12\n",
        encoding="utf-8",
    )

    result = AutoConfigService(tmp_path).auto_configure(
        ["imports/raw_site_metrics.csv"]
    )

    assert result["entities"]["datasets"] == {}
    assert result["entities"]["references"] == {}
    assert result["decision_summary"]["raw_site_metrics"]["final_entity_type"] == (
        "auxiliary_source"
    )
    assert result["auxiliary_sources"] == [
        {
            "name": "site_metrics",
            "data": "imports/raw_site_metrics.csv",
            "grouping": "sites",
            "relation": {
                "plugin": "stats_loader",
                "key": "id",
                "ref_field": "site_code",
                "match_field": "site_id",
            },
            "source_entity": "raw_site_metrics",
        }
    ]


def test_existing_auxiliary_stats_source_is_not_reused_when_match_field_is_missing(
    tmp_path: Path,
):
    config_dir = tmp_path / "config"
    imports_dir = tmp_path / "imports"
    config_dir.mkdir()
    imports_dir.mkdir()
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "entities": {"datasets": {}, "references": {}},
                "auxiliary_sources": [
                    {
                        "name": "site_metrics",
                        "data": "imports/raw_site_metrics.csv",
                        "grouping": "sites",
                        "relation": {
                            "plugin": "stats_loader",
                            "key": "id",
                            "ref_field": "site_code",
                            "match_field": "site_id",
                        },
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (imports_dir / "raw_site_metrics.csv").write_text(
        "station_id,class_object,class_name,class_value\ns1,canopy,closed,12\n",
        encoding="utf-8",
    )

    result = AutoConfigService(tmp_path).auto_configure(
        ["imports/raw_site_metrics.csv"]
    )

    assert result["auxiliary_sources"] == []
    assert result["decision_summary"]["raw_site_metrics"]["review_required"] is True


def test_existing_transform_stats_source_is_reused_when_reimported_alone(
    tmp_path: Path,
):
    config_dir = tmp_path / "config"
    imports_dir = tmp_path / "imports"
    config_dir.mkdir()
    imports_dir.mkdir()
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "entities": {
                    "datasets": {},
                    "references": {
                        "sites": {
                            "connector": {
                                "type": "file",
                                "path": "imports/sites.csv",
                            }
                        }
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "sites",
                    "sources": [
                        {
                            "name": "site_metrics",
                            "data": "imports/raw_site_metrics.csv",
                            "grouping": "sites",
                            "relation": {
                                "plugin": "stats_loader",
                                "key": "id",
                                "ref_field": "site_code",
                                "match_field": "site_id",
                            },
                        }
                    ],
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (imports_dir / "raw_site_metrics.csv").write_text(
        "site_id,class_object,class_name,class_value\ns1,canopy,closed,12\n",
        encoding="utf-8",
    )

    result = AutoConfigService(tmp_path).auto_configure(
        ["imports/raw_site_metrics.csv"]
    )

    assert result["entities"]["datasets"] == {}
    assert result["entities"]["references"] == {}
    assert result["decision_summary"]["raw_site_metrics"]["final_entity_type"] == (
        "auxiliary_source"
    )
    assert result["auxiliary_sources"] == [
        {
            "name": "site_metrics",
            "data": "imports/raw_site_metrics.csv",
            "grouping": "sites",
            "relation": {
                "plugin": "stats_loader",
                "key": "id",
                "ref_field": "site_code",
                "match_field": "site_id",
            },
            "source_entity": "raw_site_metrics",
        }
    ]


def test_existing_auxiliary_source_reuse_prefers_exact_path_over_same_basename(
    tmp_path: Path,
):
    config_dir = tmp_path / "config"
    imports_a_dir = tmp_path / "imports" / "a"
    imports_b_dir = tmp_path / "imports" / "b"
    config_dir.mkdir()
    imports_a_dir.mkdir(parents=True)
    imports_b_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "entities": {"datasets": {}, "references": {}},
                "auxiliary_sources": [
                    {
                        "name": "alpha_metrics",
                        "data": "imports/a/raw_metrics.csv",
                        "grouping": "alpha_sites",
                        "relation": {
                            "plugin": "stats_loader",
                            "key": "id",
                            "ref_field": "alpha_code",
                            "match_field": "site_id",
                        },
                    },
                    {
                        "name": "beta_metrics",
                        "data": "imports/b/raw_metrics.csv",
                        "grouping": "beta_sites",
                        "relation": {
                            "plugin": "stats_loader",
                            "key": "id",
                            "ref_field": "beta_code",
                            "match_field": "site_id",
                        },
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (imports_b_dir / "raw_metrics.csv").write_text(
        "site_id,class_object,class_name,class_value\nb1,canopy,closed,12\n",
        encoding="utf-8",
    )

    result = AutoConfigService(tmp_path).auto_configure(["imports/b/raw_metrics.csv"])

    assert result["auxiliary_sources"] == [
        {
            "name": "beta_metrics",
            "data": "imports/b/raw_metrics.csv",
            "grouping": "beta_sites",
            "relation": {
                "plugin": "stats_loader",
                "key": "id",
                "ref_field": "beta_code",
                "match_field": "site_id",
            },
            "source_entity": "raw_metrics",
        }
    ]


def test_existing_auxiliary_source_reuse_skips_same_entity_for_different_path(
    tmp_path: Path,
):
    config_dir = tmp_path / "config"
    imports_a_dir = tmp_path / "imports" / "a"
    imports_b_dir = tmp_path / "imports" / "b"
    config_dir.mkdir()
    imports_a_dir.mkdir(parents=True)
    imports_b_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "entities": {"datasets": {}, "references": {}},
                "auxiliary_sources": [
                    {
                        "name": "raw_metrics",
                        "data": "imports/a/raw_metrics.csv",
                        "grouping": "alpha_sites",
                        "relation": {
                            "plugin": "stats_loader",
                            "key": "id",
                            "ref_field": "alpha_code",
                            "match_field": "site_id",
                        },
                        "source_entity": "raw_metrics",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (imports_b_dir / "raw_metrics.csv").write_text(
        "site_id,class_object,class_name,class_value\nb1,canopy,closed,12\n",
        encoding="utf-8",
    )

    result = AutoConfigService(tmp_path).auto_configure(["imports/b/raw_metrics.csv"])

    assert result["auxiliary_sources"] == []
    assert result["decision_summary"]["raw_metrics"]["final_entity_type"] == (
        "auxiliary_source"
    )
    assert result["decision_summary"]["raw_metrics"]["review_required"] is True
    assert result["warnings"] == [
        'Review "raw_metrics": auxiliary source target is unresolved.',
        "No references detected. Add taxonomy or lookup tables.",
    ]


def test_unmatched_class_object_csv_is_not_promoted_to_reference(tmp_path: Path):
    imports_dir = tmp_path / "imports"
    imports_dir.mkdir()
    (imports_dir / "raw_metrics.csv").write_text(
        "entity_id,class_object,class_name,class_value\n1,canopy,closed,12\n",
        encoding="utf-8",
    )

    result = AutoConfigService(tmp_path).auto_configure(["imports/raw_metrics.csv"])

    assert result["entities"]["datasets"] == {}
    assert result["entities"]["references"] == {}
    assert result["decision_summary"]["raw_metrics"]["final_entity_type"] == (
        "auxiliary_source"
    )
    assert result["decision_summary"]["raw_metrics"]["review_required"] is True
    assert result["warnings"] == [
        'Review "raw_metrics": auxiliary source target is unresolved.',
        "No references detected. Add taxonomy or lookup tables.",
    ]
    assert result["auxiliary_sources"] == []


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


def test_auto_configure_detects_derived_hierarchy_relation_beyond_analysis_sample(
    tmp_path: Path,
):
    _write_delayed_plot_relation_files(tmp_path)

    result = AutoConfigService(tmp_path).auto_configure(
        ["imports/occurrences.csv", "imports/plots.csv"]
    )

    references = result["entities"]["references"]
    datasets = result["entities"]["datasets"]

    assert "plots" in references
    assert "plots_hierarchy" not in references
    assert "plots_source" in datasets
    assert references["plots"]["connector"]["source"] == "plots_source"
    assert references["plots"]["relation"] == {
        "dataset": "occurrences",
        "foreign_key": "id_table_liste_plots_n",
        "reference_key": "plots_id",
    }
    collection_names = {
        candidate["name"] for candidate in result["collection_candidates"]
    }
    assert "plots" in collection_names
    assert "plots_hierarchy" not in collection_names
    assert "plots_source" not in collection_names
    assert not any("plots" in warning for warning in result["warnings"])


def test_auxiliary_stats_follow_promoted_hierarchical_reference(tmp_path: Path):
    _write_delayed_plot_relation_files(tmp_path)
    (tmp_path / "imports" / "raw_plot_stats.csv").write_text(
        "id,class_object,class_name,class_value,plot_id\n1,plot,elevation,120,101\n",
        encoding="utf-8",
    )

    result = AutoConfigService(tmp_path).auto_configure(
        [
            "imports/occurrences.csv",
            "imports/plots.csv",
            "imports/raw_plot_stats.csv",
        ]
    )

    assert result["auxiliary_sources"] == [
        {
            "name": "plot_stats",
            "data": "imports/raw_plot_stats.csv",
            "grouping": "plots",
            "relation": {
                "plugin": "stats_loader",
                "key": "id",
                "ref_field": "plots_id",
                "match_field": "plot_id",
            },
            "source_entity": "raw_plot_stats",
        }
    ]


def test_stale_auxiliary_grouping_is_not_reused_after_reference_promotion(
    tmp_path: Path,
):
    _write_delayed_plot_relation_files(tmp_path)
    (tmp_path / "imports" / "raw_plot_stats.csv").write_text(
        "id,class_object,class_name,class_value,plot_id\n1,plot,elevation,120,101\n",
        encoding="utf-8",
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "entities": {
                    "datasets": {},
                    "references": {
                        "plots_hierarchy": {"kind": "hierarchical"},
                    },
                },
                "auxiliary_sources": [
                    {
                        "name": "plot_stats",
                        "data": "imports/raw_plot_stats.csv",
                        "grouping": "plots_hierarchy",
                        "relation": {
                            "plugin": "stats_loader",
                            "key": "id",
                            "ref_field": "plots_hierarchy_id",
                            "match_field": "plot_id",
                        },
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = AutoConfigService(tmp_path).auto_configure(
        [
            "imports/occurrences.csv",
            "imports/plots.csv",
            "imports/raw_plot_stats.csv",
        ]
    )

    assert result["auxiliary_sources"][0]["grouping"] == "plots"
    assert result["auxiliary_sources"][0]["relation"]["ref_field"] == "plots_id"


def test_detect_relationships_uses_relation_sample_beyond_analysis_sample(
    tmp_path: Path,
):
    _write_delayed_plot_relation_files(tmp_path)

    result = AutoConfigService(tmp_path).detect_relationships(
        "imports/occurrences.csv",
        ["imports/plots.csv"],
    )

    assert any(
        relationship["source_field"] == "id_table_liste_plots_n"
        and relationship["target_field"] == "id_liste_plots"
        for relationship in result["relationships"]
    )


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
