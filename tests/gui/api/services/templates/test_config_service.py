"""Tests for transform/export config service helpers."""

from __future__ import annotations

import pytest

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
