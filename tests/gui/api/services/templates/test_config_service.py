"""Tests for transform/export config service helpers."""

from __future__ import annotations

from datetime import datetime

import pytest
import yaml

from niamoto.gui.api.services.templates import config_service


def test_load_transform_config_returns_empty_when_file_is_missing(tmp_path):
    assert config_service.load_transform_config(tmp_path) == []


def test_load_transform_config_rejects_non_list_yaml(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "transform.yml").write_text("group_by: plots\n", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        config_service.load_transform_config(tmp_path)

    assert "transform.yml must be a list of groups" in str(exc_info.value)


def test_save_and_load_transform_config_round_trip(tmp_path):
    config = [
        {
            "group_by": "plots",
            "sources": [],
            "widgets_data": {},
        }
    ]

    config_service.save_transform_config(tmp_path, config)

    assert config_service.load_transform_config(tmp_path) == config


@pytest.mark.parametrize(
    ("filename", "save_config", "payload", "original"),
    [
        (
            "transform.yml",
            config_service.save_transform_config,
            [{"group_by": "plots", "sources": [], "widgets_data": {}}],
            "- group_by: old\n  sources: []\n  widgets_data: {}\n",
        ),
        (
            "import.yml",
            config_service.save_import_config,
            {"entities": {"references": {}, "datasets": {"old": {}}}},
            "entities:\n  datasets:\n    old: {}\n  references: {}\n",
        ),
        (
            "export.yml",
            config_service.save_export_config,
            {"exports": [{"name": "web", "exporter": "html_page_exporter"}]},
            "exports:\n- name: old\n  exporter: html_page_exporter\n",
        ),
    ],
)
def test_save_config_preserves_existing_file_when_yaml_dump_fails(
    monkeypatch, tmp_path, filename, save_config, payload, original
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    config_path = config_dir / filename
    config_path.write_text(original, encoding="utf-8")

    def fail_dump(_payload, stream, *args, **kwargs):
        stream.write("partial: true\n")
        raise RuntimeError("dump boom")

    monkeypatch.setattr(config_service.yaml, "dump", fail_dump)

    with pytest.raises(RuntimeError, match="dump boom"):
        save_config(tmp_path, payload)

    assert config_path.read_text(encoding="utf-8") == original
    assert not list(config_dir.glob("*.tmp"))


def test_create_backup_file_preserves_rapid_successive_backups(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "transform.yml"
    config_path.write_text("first\n", encoding="utf-8")

    class FixedDatetime:
        @classmethod
        def now(cls):
            return datetime(2026, 5, 18, 17, 15, 0, 123456)

    monkeypatch.setattr(config_service, "datetime", FixedDatetime)

    config_service._create_backup_file(config_path)
    config_path.write_text("second\n", encoding="utf-8")
    config_service._create_backup_file(config_path)

    backups = sorted((config_dir / "backups").glob("transform_*.yml"))
    assert len(backups) == 2
    assert backups[0].read_text(encoding="utf-8") == "first\n"
    assert backups[1].read_text(encoding="utf-8") == "second\n"


def test_save_transform_and_export_configs_rolls_back_both_files_on_write_failure(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    transform_path = config_dir / "transform.yml"
    export_path = config_dir / "export.yml"
    transform_path.write_text(
        "- group_by: old\n  sources: []\n  widgets_data: {}\n",
        encoding="utf-8",
    )
    export_path.write_text("exports: []\n", encoding="utf-8")
    original_write = config_service._write_yaml_atomic

    def fail_export_write(path, payload):
        if path.name == "export.yml":
            raise RuntimeError("export boom")
        original_write(path, payload)

    monkeypatch.setattr(config_service, "_write_yaml_atomic", fail_export_write)

    with pytest.raises(RuntimeError, match="export boom"):
        config_service.save_transform_and_export_configs(
            tmp_path,
            [{"group_by": "new", "sources": [], "widgets_data": {}}],
            {"exports": [{"name": "web_pages", "exporter": "html_page_exporter"}]},
            create_backup=True,
        )

    assert transform_path.read_text(encoding="utf-8") == (
        "- group_by: old\n  sources: []\n  widgets_data: {}\n"
    )
    assert export_path.read_text(encoding="utf-8") == "exports: []\n"
    assert not (config_dir / ".transform_export_write_pending.yml").exists()


def test_recover_pending_transaction_rejects_paths_outside_project(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    outside_file = tmp_path.parent / "outside-config.yml"
    outside_file.write_text("keep me\n", encoding="utf-8")
    outside_dir = tmp_path.parent / "outside-transaction"
    outside_dir.mkdir(exist_ok=True)
    (outside_dir / "snapshot.yml").write_text("snapshot\n", encoding="utf-8")

    (config_dir / config_service.TRANSFORM_EXPORT_TRANSACTION_MARKER).write_text(
        yaml.safe_dump(
            {
                "operation": "transform_export_write",
                "transaction_dir": str(outside_dir),
                "targets": [
                    {
                        "path": str(outside_file),
                        "existed": False,
                        "rollback_path": str(outside_dir / "snapshot.yml"),
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    config_service.recover_pending_config_transaction(tmp_path)

    assert outside_file.read_text(encoding="utf-8") == "keep me\n"
    assert outside_dir.exists()
    assert not (
        config_dir / config_service.TRANSFORM_EXPORT_TRANSACTION_MARKER
    ).exists()


def test_recover_pending_transaction_preserves_marker_when_restore_fails(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    transaction_dir = config_dir / ".transactions" / "transform_export_interrupted"
    transaction_dir.mkdir(parents=True)
    transform_path = config_dir / "transform.yml"
    transform_snapshot = transaction_dir / "transform.yml.rollback"
    transform_path.write_text(
        "- group_by: partial\n  sources: []\n  widgets_data: {}\n",
        encoding="utf-8",
    )
    transform_snapshot.write_text(
        "- group_by: old\n  sources: []\n  widgets_data: {}\n",
        encoding="utf-8",
    )
    marker_path = config_dir / config_service.TRANSFORM_EXPORT_TRANSACTION_MARKER
    marker_path.write_text(
        yaml.safe_dump(
            {
                "operation": "transform_export_write",
                "transaction_dir": "config/.transactions/transform_export_interrupted",
                "targets": [
                    {
                        "path": "config/transform.yml",
                        "existed": True,
                        "rollback_path": (
                            "config/.transactions/transform_export_interrupted/"
                            "transform.yml.rollback"
                        ),
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def fail_restore(_source, _target):
        raise RuntimeError("restore boom")

    monkeypatch.setattr(config_service, "_copy_file_atomic", fail_restore)

    with pytest.raises(RuntimeError, match="restore boom"):
        config_service.recover_pending_config_transaction(tmp_path)

    assert marker_path.exists()
    assert transaction_dir.exists()
    assert transform_path.read_text(encoding="utf-8") == (
        "- group_by: partial\n  sources: []\n  widgets_data: {}\n"
    )


def test_load_transform_config_recovers_interrupted_transform_export_write(tmp_path):
    config_dir = tmp_path / "config"
    transaction_dir = config_dir / ".transactions" / "transform_export_interrupted"
    transaction_dir.mkdir(parents=True)
    transform_path = config_dir / "transform.yml"
    export_path = config_dir / "export.yml"
    transform_snapshot = transaction_dir / "transform.yml.rollback"
    export_snapshot = transaction_dir / "export.yml.rollback"
    transform_snapshot.write_text(
        "- group_by: old\n  sources: []\n  widgets_data: {}\n",
        encoding="utf-8",
    )
    export_snapshot.write_text("exports: []\n", encoding="utf-8")
    transform_path.write_text(
        "- group_by: new\n  sources: []\n  widgets_data: {}\n",
        encoding="utf-8",
    )
    export_path.write_text(
        "exports:\n- name: partial\n  exporter: html_page_exporter\n",
        encoding="utf-8",
    )
    (config_dir / config_service.TRANSFORM_EXPORT_TRANSACTION_MARKER).write_text(
        yaml.safe_dump(
            {
                "operation": "transform_export_write",
                "transaction_dir": "config/.transactions/transform_export_interrupted",
                "targets": [
                    {
                        "path": "config/transform.yml",
                        "existed": True,
                        "rollback_path": (
                            "config/.transactions/transform_export_interrupted/"
                            "transform.yml.rollback"
                        ),
                    },
                    {
                        "path": "config/export.yml",
                        "existed": True,
                        "rollback_path": (
                            "config/.transactions/transform_export_interrupted/"
                            "export.yml.rollback"
                        ),
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    loaded = config_service.load_transform_config(tmp_path)

    assert loaded == [{"group_by": "old", "sources": [], "widgets_data": {}}]
    assert export_path.read_text(encoding="utf-8") == "exports: []\n"
    assert not (
        config_dir / config_service.TRANSFORM_EXPORT_TRANSACTION_MARKER
    ).exists()
    assert not transaction_dir.exists()


def test_load_export_config_recovers_interrupted_transform_export_write(tmp_path):
    config_dir = tmp_path / "config"
    transaction_dir = config_dir / ".transactions" / "transform_export_interrupted"
    transaction_dir.mkdir(parents=True)
    transform_path = config_dir / "transform.yml"
    export_path = config_dir / "export.yml"
    transform_snapshot = transaction_dir / "transform.yml.rollback"
    export_snapshot = transaction_dir / "export.yml.rollback"
    transform_snapshot.write_text(
        "- group_by: old\n  sources: []\n  widgets_data: {}\n",
        encoding="utf-8",
    )
    export_snapshot.write_text("exports: []\n", encoding="utf-8")
    transform_path.write_text(
        "- group_by: partial\n  sources: []\n  widgets_data: {}\n",
        encoding="utf-8",
    )
    export_path.write_text(
        "exports:\n- name: partial\n  exporter: html_page_exporter\n",
        encoding="utf-8",
    )
    (config_dir / config_service.TRANSFORM_EXPORT_TRANSACTION_MARKER).write_text(
        yaml.safe_dump(
            {
                "operation": "transform_export_write",
                "transaction_dir": "config/.transactions/transform_export_interrupted",
                "targets": [
                    {
                        "path": "config/transform.yml",
                        "existed": True,
                        "rollback_path": (
                            "config/.transactions/transform_export_interrupted/"
                            "transform.yml.rollback"
                        ),
                    },
                    {
                        "path": "config/export.yml",
                        "existed": True,
                        "rollback_path": (
                            "config/.transactions/transform_export_interrupted/"
                            "export.yml.rollback"
                        ),
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    loaded = config_service.load_export_config(tmp_path)

    assert loaded == {"exports": []}
    assert transform_path.read_text(encoding="utf-8") == (
        "- group_by: old\n  sources: []\n  widgets_data: {}\n"
    )
    assert not (
        config_dir / config_service.TRANSFORM_EXPORT_TRANSACTION_MARKER
    ).exists()
    assert not transaction_dir.exists()


def test_load_import_config_defaults_missing_entities(tmp_path):
    assert config_service.load_import_config(tmp_path) == {
        "entities": {"references": {}, "datasets": {}}
    }

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text("metadata:\n  collections: {}\n")

    loaded = config_service.load_import_config(tmp_path)

    assert loaded == {
        "metadata": {"collections": {}},
        "entities": {"references": {}, "datasets": {}},
    }


def test_save_and_load_import_config_round_trip(tmp_path):
    config = {
        "entities": {"references": {"taxons": {}}, "datasets": {}},
        "metadata": {
            "collections": {
                "taxons": {
                    "label": "Taxons",
                    "review_status": "accepted",
                }
            }
        },
    }

    config_service.save_import_config(tmp_path, config)

    assert config_service.load_import_config(tmp_path) == config


def test_load_export_config_normalizes_missing_or_invalid_payloads(tmp_path):
    assert config_service.load_export_config(tmp_path) == {"exports": []}

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "export.yml").write_text("- invalid\n", encoding="utf-8")

    assert config_service.load_export_config(tmp_path) == {"exports": []}


def test_find_and_create_helpers_reuse_existing_groups():
    groups = [{"group_by": "plots", "sources": [], "widgets_data": {}}]
    export_config = {
        "exports": [
            {
                "name": "web_pages",
                "groups": [{"group_by": "plots", "widgets": []}],
            }
        ]
    }

    existing = config_service.find_or_create_transform_group(groups, "plots")
    created = config_service.find_or_create_transform_group(groups, "taxons")

    assert existing is groups[0]
    assert created == {"group_by": "taxons", "sources": [], "widgets_data": {}}
    assert config_service.find_transform_group(groups, "taxons") is created
    assert config_service.find_export_group(export_config, "plots") == {
        "group_by": "plots",
        "widgets": [],
    }
