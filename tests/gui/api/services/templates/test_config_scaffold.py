"""Tests for automatic transform/export scaffolding."""

from __future__ import annotations

import yaml

from niamoto.gui.api.services.templates.config_scaffold import (
    build_relation_config,
    scaffold_configs,
)


def test_build_relation_config_supports_hierarchical_and_direct_references():
    hierarchical = build_relation_config(
        "taxons",
        "hierarchical",
        {
            "connector": {
                "type": "derived",
                "extraction": {"id_column": "id_taxonref"},
            }
        },
    )
    direct = build_relation_config(
        "plots",
        "generic",
        {
            "relation": {
                "foreign_key": "plot_id",
                "reference_key": "id_plot",
            }
        },
    )

    assert hierarchical == {
        "plugin": "nested_set",
        "key": "id_taxonref",
        "ref_key": "id",
        "fields": {
            "parent": "parent_id",
            "left": "lft",
            "right": "rght",
        },
    }
    assert direct == {
        "plugin": "direct_reference",
        "key": "plot_id",
        "ref_key": "id_plot",
    }


def test_build_relation_config_returns_none_without_safe_key():
    assert build_relation_config("plots", "generic", {"schema": {}}) is None
    assert build_relation_config("taxons", "hierarchical", {"connector": {}}) is None


def test_scaffold_configs_adds_missing_transform_and_export_groups(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "connector": {"type": "csv"},
                        }
                    },
                    "references": {
                        "plots": {
                            "kind": "generic",
                            "relation": {
                                "dataset": "occurrences",
                                "foreign_key": "plot_id",
                                "reference_key": "id_plot",
                            },
                        },
                        "taxons": {
                            "kind": "hierarchical",
                            "connector": {
                                "type": "derived",
                                "extraction": {"id_column": "id_taxonref"},
                            },
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.config_scaffold.find_stats_sources_for_reference",
        lambda work_dir, ref_name: [],
    )

    changed, message = scaffold_configs(tmp_path)
    second_changed, second_message = scaffold_configs(tmp_path)

    transform_config = yaml.safe_load((config_dir / "transform.yml").read_text())
    export_config = yaml.safe_load((config_dir / "export.yml").read_text())

    assert changed is True
    assert "transform:" in message
    assert "export:" in message
    assert {group["group_by"] for group in transform_config} == {"plots", "taxons"}
    assert export_config["exports"][0]["name"] == "web_pages"
    assert {group["group_by"] for group in export_config["exports"][0]["groups"]} == {
        "plots",
        "taxons",
    }
    assert second_changed is False
    assert second_message == "Rien à ajouter"


def test_scaffold_configs_returns_false_when_no_references_exist(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump({"entities": {"datasets": {"occurrences": {}}}}),
        encoding="utf-8",
    )

    changed, message = scaffold_configs(tmp_path)

    assert changed is False
    assert message == "Aucune référence dans import.yml"
