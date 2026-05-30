"""Tests for automatic transform/export scaffolding."""

from __future__ import annotations

import asyncio
import threading
import time

import yaml

from niamoto.gui.api.routers import config as config_router
from niamoto.gui.api.services.templates import config_scaffold
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


def test_build_relation_config_uses_schema_id_field_for_derived_ref_key():
    hierarchical = build_relation_config(
        "taxons",
        "hierarchical",
        {
            "connector": {
                "type": "derived",
                "extraction": {"id_column": "id_taxonref"},
            },
            "schema": {"id_field": "id_taxon"},
        },
    )

    assert hierarchical == {
        "plugin": "nested_set",
        "key": "id_taxonref",
        "ref_key": "id_taxon",
        "fields": {
            "parent": "parent_id",
            "left": "lft",
            "right": "rght",
        },
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


def test_scaffold_configs_reuses_export_groups_under_params(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {},
                    "references": {"plots": {"kind": "generic"}},
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [{"group_by": "plots", "sources": [], "widgets_data": {}}],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "export.yml").write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "exporter": "html_page_exporter",
                        "params": {
                            "groups": [
                                {
                                    "group_by": "plots",
                                    "widgets": [
                                        {
                                            "plugin": "interactive_map",
                                            "data_source": "plot_map",
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        config_scaffold, "find_stats_sources_for_reference", lambda *_args: []
    )

    changed, message = scaffold_configs(tmp_path)

    export_config = yaml.safe_load((config_dir / "export.yml").read_text())
    web_export = export_config["exports"][0]
    assert changed is False
    assert message == "Rien à ajouter"
    assert "groups" not in web_export
    assert web_export["params"]["groups"][0]["widgets"][0]["data_source"] == "plot_map"


def test_scaffold_configs_rolls_back_transform_when_export_save_fails(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    import_path = config_dir / "import.yml"
    transform_path = config_dir / "transform.yml"
    export_path = config_dir / "export.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {"occurrences": {}},
                    "references": {
                        "plots": {
                            "kind": "generic",
                            "relation": {
                                "dataset": "occurrences",
                                "foreign_key": "plot_id",
                            },
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        config_scaffold, "find_stats_sources_for_reference", lambda *_args: []
    )

    def fail_save_export_config(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(config_scaffold, "save_export_config", fail_save_export_config)

    try:
        scaffold_configs(tmp_path)
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("scaffold_configs should propagate export save failure")

    assert not transform_path.exists()
    assert not export_path.exists()


def test_scaffold_configs_shares_transform_write_lock_with_widget_updates(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {"occurrences": {}},
                    "references": {
                        "taxons": {"kind": "generic", "schema": {"id_field": "id"}},
                        "plots": {
                            "kind": "generic",
                            "relation": {
                                "dataset": "occurrences",
                                "foreign_key": "plot_id",
                                "reference_key": "id_plot",
                            },
                        },
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [{"group_by": "taxons", "sources": [], "widgets_data": {}}],
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        config_scaffold, "find_stats_sources_for_reference", lambda *_args: []
    )

    original_save_transform_config = config_scaffold.save_transform_config
    first_save_entered = threading.Event()
    release_first_save = threading.Event()
    errors: list[BaseException] = []

    def delayed_save_transform_config(work_dir, groups, create_backup=False):
        if any(group.get("group_by") == "plots" for group in groups):
            first_save_entered.set()
            release_first_save.wait(timeout=2)
        original_save_transform_config(work_dir, groups, create_backup=create_backup)

    monkeypatch.setattr(
        config_scaffold, "save_transform_config", delayed_save_transform_config
    )

    def run_scaffold():
        try:
            config_scaffold.scaffold_configs(tmp_path)
        except BaseException as exc:
            errors.append(exc)

    def update_widget():
        try:
            asyncio.run(
                config_router.update_transform_widget(
                    "taxons",
                    "summary_widget",
                    config_router.TransformWidgetUpdate(
                        plugin="field_aggregator",
                        params={"field": "id"},
                    ),
                )
            )
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(target=run_scaffold)
    second = threading.Thread(target=update_widget)

    first.start()
    assert first_save_entered.wait(timeout=2)
    second.start()
    time.sleep(0.05)
    release_first_save.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []

    transform_config = yaml.safe_load((config_dir / "transform.yml").read_text())
    groups = {group["group_by"]: group for group in transform_config}
    assert "plots" in groups
    assert "summary_widget" in groups["taxons"]["widgets_data"]


def test_scaffold_configs_shares_export_write_lock_with_export_updates(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {"occurrences": {}},
                    "references": {
                        "taxons": {"kind": "generic", "schema": {"id_field": "id"}},
                        "plots": {
                            "kind": "generic",
                            "relation": {
                                "dataset": "occurrences",
                                "foreign_key": "plot_id",
                                "reference_key": "id_plot",
                            },
                        },
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [{"group_by": "taxons", "sources": [], "widgets_data": {}}],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "export.yml").write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "exporter": "html_page_exporter",
                        "groups": [{"group_by": "taxons", "widgets": []}],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        config_scaffold, "find_stats_sources_for_reference", lambda *_args: []
    )

    original_save_export_config = config_scaffold.save_export_config
    first_save_entered = threading.Event()
    release_first_save = threading.Event()
    errors: list[BaseException] = []

    def delayed_save_export_config(work_dir, config, create_backup=False):
        groups = config["exports"][0]["groups"]
        if any(group.get("group_by") == "plots" for group in groups):
            first_save_entered.set()
            release_first_save.wait(timeout=2)
        original_save_export_config(work_dir, config, create_backup=create_backup)

    monkeypatch.setattr(
        config_scaffold, "save_export_config", delayed_save_export_config
    )

    def run_scaffold():
        try:
            config_scaffold.scaffold_configs(tmp_path)
        except BaseException as exc:
            errors.append(exc)

    def update_index_generator():
        try:
            asyncio.run(
                config_router.update_index_generator(
                    "taxons",
                    config_router.IndexGeneratorConfigUpdate(
                        page_config=config_router.IndexGeneratorPageConfigUpdate(
                            title="Taxons"
                        ),
                        display_fields=[
                            config_router.IndexGeneratorDisplayFieldUpdate(
                                name="name",
                                source="full_name",
                                type="text",
                            )
                        ],
                    ),
                )
            )
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(target=run_scaffold)
    second = threading.Thread(target=update_index_generator)

    first.start()
    assert first_save_entered.wait(timeout=2)
    second.start()
    time.sleep(0.05)
    release_first_save.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []

    export_config = yaml.safe_load((config_dir / "export.yml").read_text())
    groups = {
        group["group_by"]: group for group in export_config["exports"][0]["groups"]
    }
    assert "plots" in groups
    assert groups["taxons"]["index_generator"]["display_fields"][0]["name"] == "name"


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
