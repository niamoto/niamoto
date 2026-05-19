import asyncio
from copy import deepcopy
import threading
import time
from unittest.mock import Mock

import pytest
import yaml
from fastapi import HTTPException
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import config as config_router


def test_list_export_widgets_reads_groups_under_params(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
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
                                            "params": {"geometry_field": "geo_pt"},
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

    response = gui_duckdb_client.get("/api/config/export/plots/widgets")

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "plugin": "interactive_map",
            "data_source": "plot_map",
            "params": {"geometry_field": "geo_pt"},
        }
    ]


def test_get_index_generator_reads_groups_under_params(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    index_generator = {
        "enabled": True,
        "template": "group_index.html",
        "page_config": {"title": {"fr": "Placettes", "en": "Plots"}},
        "display_fields": [{"field": "plot_name", "label": "Plot"}],
    }
    export_path.write_text(
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
                                    "index_generator": index_generator,
                                    "widgets": [],
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

    response = gui_duckdb_client.get("/api/config/export/plots/index-generator")

    assert response.status_code == 200, response.text
    assert response.json() == index_generator


def test_update_export_widget_preserves_layout_and_accepts_localized_metadata(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "exporter": "html_page_exporter",
                        "groups": [
                            {
                                "group_by": "taxons",
                                "widgets": [
                                    {
                                        "plugin": "bar_plot",
                                        "data_source": "richness",
                                        "title": "Richness",
                                        "params": {"x_axis": "name"},
                                        "layout": {"order": 3, "colspan": 2},
                                        "template": "custom.html",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.put(
        "/api/config/export/taxons/widgets/richness",
        json={
            "plugin": "donut_chart",
            "data_source": "richness",
            "title": {"fr": "Richesse", "en": "Richness"},
            "description": {"fr": "Description", "en": "Description"},
            "params": {"value_field": "count"},
        },
    )

    assert response.status_code == 200, response.text

    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    widget = saved["exports"][0]["groups"][0]["widgets"][0]
    assert widget["plugin"] == "donut_chart"
    assert widget["title"] == {"fr": "Richesse", "en": "Richness"}
    assert widget["description"] == {"fr": "Description", "en": "Description"}
    assert widget["params"] == {"value_field": "count"}
    assert widget["layout"] == {"order": 3, "colspan": 2}
    assert widget["template"] == "custom.html"


def test_update_export_widget_rejects_mismatched_data_source(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    original_config = {
        "exports": [
            {
                "name": "web_pages",
                "exporter": "html_page_exporter",
                "groups": [
                    {
                        "group_by": "taxons",
                        "widgets": [
                            {
                                "plugin": "bar_plot",
                                "data_source": "richness",
                                "params": {"x_axis": "name"},
                            }
                        ],
                    }
                ],
            }
        ]
    }
    export_path.write_text(
        yaml.safe_dump(original_config, sort_keys=False),
        encoding="utf-8",
    )

    response = gui_duckdb_client.put(
        "/api/config/export/taxons/widgets/richness_copy",
        json={
            "plugin": "bar_plot",
            "data_source": "richness",
            "params": {"x_axis": "name"},
        },
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == (
        "Widget data_source must match the widget_id path parameter"
    )
    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    assert saved == original_config


def test_update_export_widget_can_clear_metadata(gui_duckdb_client, gui_duckdb_context):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "exporter": "html_page_exporter",
                        "groups": [
                            {
                                "group_by": "taxons",
                                "widgets": [
                                    {
                                        "plugin": "bar_plot",
                                        "data_source": "richness",
                                        "title": {"fr": "Richesse", "en": "Richness"},
                                        "description": {
                                            "fr": "Description",
                                            "en": "Description",
                                        },
                                        "params": {"x_axis": "name"},
                                        "layout": {"order": 3, "colspan": 2},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.put(
        "/api/config/export/taxons/widgets/richness",
        json={
            "plugin": "bar_plot",
            "data_source": "richness",
            "params": {"x_axis": "name"},
        },
    )

    assert response.status_code == 200, response.text
    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    widget = saved["exports"][0]["groups"][0]["widgets"][0]
    assert widget["title"] == {"fr": "Richesse", "en": "Richness"}
    assert widget["description"] == {"fr": "Description", "en": "Description"}

    response = gui_duckdb_client.put(
        "/api/config/export/taxons/widgets/richness",
        json={
            "plugin": "bar_plot",
            "data_source": "richness",
            "title": None,
            "description": None,
            "params": {"x_axis": "name"},
        },
    )

    assert response.status_code == 200, response.text
    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    widget = saved["exports"][0]["groups"][0]["widgets"][0]
    assert "title" not in widget
    assert "description" not in widget
    assert widget["layout"] == {"order": 3, "colspan": 2}


def test_update_export_widget_auto_creates_valid_web_export(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "json_api",
                        "exporter": "json_api_exporter",
                        "params": {
                            "output_dir": "exports/json_api",
                            "detail_output_pattern": "{group}/{id}.json",
                            "index_output_pattern": "{group}/index.json",
                        },
                        "groups": [],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.put(
        "/api/config/export/taxons/widgets/richness",
        json={
            "plugin": "bar_plot",
            "data_source": "richness",
            "params": {"x_axis": "name"},
        },
    )

    assert response.status_code == 200, response.text
    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    web_export = next(
        export for export in saved["exports"] if export["name"] == "web_pages"
    )
    assert web_export["exporter"] == "html_page_exporter"
    assert web_export["params"] == {
        "template_dir": "templates/",
        "output_dir": "exports/web",
    }
    assert web_export["static_pages"] == []
    assert web_export["groups"][0]["group_by"] == "taxons"
    assert web_export["groups"][0]["widgets"][0]["data_source"] == "richness"


def test_api_export_suggestions_route_serializes_response(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "json_api",
                    "exporter": "json_api_exporter",
                    "groups": [],
                }
            ]
        },
    )

    async def fake_suggest_index_fields(group_by: str):
        assert group_by == "taxons"
        return config_router.IndexFieldSuggestions(
            display_fields=[],
            filters=[],
            total_entities=12,
        )

    monkeypatch.setattr(
        config_router, "suggest_index_fields", fake_suggest_index_fields
    )

    client = TestClient(create_app())
    response = client.get(
        "/api/config/export/api-targets/json_api/groups/taxons/suggestions"
    )

    assert response.status_code == 200
    assert response.json() == {
        "display_fields": [],
        "filters": [],
        "total_entities": 12,
        "available_fields": [],
    }


def test_list_api_export_targets_route_summarizes_groups(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "json_api",
                    "enabled": False,
                    "exporter": "json_api_exporter",
                    "params": {"output_dir": "exports/json_api"},
                    "groups": [
                        {"group_by": "plots", "enabled": True},
                        {"group_by": "taxons", "enabled": False},
                    ],
                },
                {"name": "web_pages", "exporter": "html_page_exporter"},
            ]
        },
    )

    client = TestClient(create_app())
    response = client.get("/api/config/export/api-targets")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "json_api",
            "enabled": False,
            "exporter": "json_api_exporter",
            "group_names": ["plots", "taxons"],
            "groups": [
                {"group_by": "plots", "enabled": True},
                {"group_by": "taxons", "enabled": False},
            ],
            "params": {"output_dir": "exports/json_api"},
        }
    ]


def test_create_api_export_target_route_adds_simple_target(monkeypatch):
    export_config = {"exports": []}
    saved = Mock()

    monkeypatch.setattr(config_router, "_load_export_config", lambda: export_config)
    monkeypatch.setattr(config_router, "_validate_export_config_or_raise", Mock())
    monkeypatch.setattr(config_router, "_save_export_config", saved)

    client = TestClient(create_app())
    response = client.post(
        "/api/config/export/api-targets",
        json={
            "name": "public_json",
            "template": "simple",
            "params": {"base_path": "/data"},
        },
    )

    assert response.status_code == 200
    assert response.json()["params"] == {
        "output_dir": "exports/public_json",
        "detail_output_pattern": "{group}/{id}.json",
        "index_output_pattern": "all_{group}.json",
        "base_path": "/data",
    }
    assert export_config["exports"][0]["name"] == "public_json"
    saved.assert_called_once_with(export_config)


def test_create_api_export_target_route_rejects_duplicate(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {"name": "json_api", "exporter": "json_api_exporter", "groups": []}
            ]
        },
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/config/export/api-targets",
        json={"name": "json_api", "template": "simple"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Target 'json_api' already exists"


def test_create_api_export_target_serializes_concurrent_writes(monkeypatch):
    current_export_config = {"exports": []}
    config_lock = threading.Lock()
    first_save_entered = threading.Event()
    release_first_save = threading.Event()
    errors: list[BaseException] = []

    def load_export_config():
        with config_lock:
            return deepcopy(current_export_config)

    def save_export_config(export_config):
        nonlocal current_export_config
        exports = export_config.get("exports", [])
        if len(exports) == 1 and exports[0].get("name") == "api_one":
            first_save_entered.set()
            release_first_save.wait(timeout=2)
        with config_lock:
            current_export_config = deepcopy(export_config)

    monkeypatch.setattr(config_router, "_load_export_config", load_export_config)
    monkeypatch.setattr(config_router, "_validate_export_config_or_raise", Mock())
    monkeypatch.setattr(config_router, "_save_export_config", save_export_config)

    def create_target(name: str):
        try:
            asyncio.run(
                config_router.create_api_export_target(
                    config_router.ApiExportTargetCreate(
                        name=name,
                        template="simple",
                    )
                )
            )
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(target=create_target, args=("api_one",))
    second = threading.Thread(target=create_target, args=("api_two",))

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
    assert {target["name"] for target in current_export_config["exports"]} == {
        "api_one",
        "api_two",
    }


def test_update_api_export_target_settings_persists_params(monkeypatch):
    export_config = {
        "exports": [
            {
                "name": "json_api",
                "exporter": "json_api_exporter",
                "enabled": True,
                "params": {"output_dir": "exports/json_api"},
                "groups": [],
            }
        ]
    }
    saved = Mock()

    monkeypatch.setattr(config_router, "_load_export_config", lambda: export_config)
    monkeypatch.setattr(config_router, "_validate_export_config_or_raise", Mock())
    monkeypatch.setattr(config_router, "_save_export_config", saved)

    client = TestClient(create_app())
    response = client.put(
        "/api/config/export/api-targets/json_api/settings",
        json={"enabled": False, "params": {"output_dir": "exports/public"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "name": "json_api",
        "enabled": False,
        "params": {"output_dir": "exports/public"},
    }
    assert export_config["exports"][0]["enabled"] is False
    saved.assert_called_once_with(export_config)


@pytest.mark.parametrize(
    ("params", "expected_detail"),
    [
        (
            {"output_dir": "../outside"},
            "output_dir must not contain parent directory segments",
        ),
        (
            {"output_dir": "/tmp/niamoto-export"},
            "output_dir must be relative to the project directory",
        ),
        (
            {"output_dir": "tmp/json_api"},
            "output_dir must stay within the exports directory",
        ),
        (
            {
                "output_dir": "exports/json_api",
                "detail_output_pattern": "../{group}/{id}.json",
            },
            "detail_output_pattern must not contain parent directory segments",
        ),
        (
            {
                "output_dir": "exports/json_api",
                "index_output_pattern": "/{group}/index.json",
            },
            "index_output_pattern must be relative to the project directory",
        ),
    ],
)
def test_update_api_export_target_settings_rejects_unsafe_paths(
    monkeypatch, params, expected_detail
):
    export_config = {
        "exports": [
            {
                "name": "json_api",
                "exporter": "json_api_exporter",
                "enabled": True,
                "params": {"output_dir": "exports/json_api"},
                "groups": [],
            }
        ]
    }
    saved = Mock()

    monkeypatch.setattr(config_router, "_load_export_config", lambda: export_config)
    monkeypatch.setattr(config_router, "_validate_export_config_or_raise", Mock())
    monkeypatch.setattr(config_router, "_save_export_config", saved)

    client = TestClient(create_app())
    response = client.put(
        "/api/config/export/api-targets/json_api/settings",
        json={"enabled": False, "params": params},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail
    assert export_config["exports"][0]["enabled"] is True
    assert export_config["exports"][0]["params"] == {"output_dir": "exports/json_api"}
    saved.assert_not_called()


def test_create_api_export_target_rejects_unsafe_output_dir(monkeypatch):
    saved = Mock()

    monkeypatch.setattr(config_router, "_load_export_config", lambda: {"exports": []})
    monkeypatch.setattr(config_router, "_validate_export_config_or_raise", Mock())
    monkeypatch.setattr(config_router, "_save_export_config", saved)

    client = TestClient(create_app())
    response = client.post(
        "/api/config/export/api-targets",
        json={
            "name": "json_api",
            "template": "simple",
            "params": {"output_dir": "../outside"},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "output_dir must not contain parent directory segments"
    )
    saved.assert_not_called()


def test_update_api_export_group_config_disables_missing_group(monkeypatch):
    export_config = {
        "exports": [
            {
                "name": "json_api",
                "exporter": "json_api_exporter",
                "groups": [],
            }
        ]
    }

    monkeypatch.setattr(config_router, "_load_export_config", lambda: export_config)
    monkeypatch.setattr(config_router, "_validate_export_config_or_raise", Mock())
    monkeypatch.setattr(config_router, "_save_export_config", Mock())

    client = TestClient(create_app())
    response = client.put(
        "/api/config/export/api-targets/json_api/groups/plots",
        json={"enabled": False},
    )

    assert response.status_code == 200
    assert response.json() == {"group_by": "plots", "enabled": False}
    assert export_config["exports"][0]["groups"] == [
        {"group_by": "plots", "enabled": False}
    ]


def test_update_api_export_group_config_inherits_dwc_sibling_defaults(monkeypatch):
    export_config = {
        "exports": [
            {
                "name": "dwc_occurrence_json",
                "exporter": "json_api_exporter",
                "groups": [
                    {
                        "group_by": "taxons",
                        "transformer_plugin": "niamoto_to_dwc_occurrence",
                    }
                ],
            }
        ]
    }

    monkeypatch.setattr(config_router, "_load_export_config", lambda: export_config)
    monkeypatch.setattr(config_router, "_validate_export_config_or_raise", Mock())
    monkeypatch.setattr(config_router, "_save_export_config", Mock())

    client = TestClient(create_app())
    response = client.put(
        "/api/config/export/api-targets/dwc_occurrence_json/groups/plots",
        json={"enabled": True, "detail": {"pass_through": True}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["transformer_plugin"] == "niamoto_to_dwc_occurrence"
    assert payload["transformer_params"]["taxonomy_entity"] == "plots"


def test_update_api_export_group_config_applies_dwc_defaults_for_empty_target(
    monkeypatch,
):
    export_config = {
        "exports": [
            {
                "name": "occurrence_json",
                "exporter": "json_api_exporter",
                "params": {
                    "detail_output_pattern": "{group}/{id}_dwc.json",
                    "index_output_pattern": "all_{group}_dwc.json",
                },
                "groups": [],
            }
        ]
    }

    monkeypatch.setattr(config_router, "_load_export_config", lambda: export_config)
    monkeypatch.setattr(config_router, "_validate_export_config_or_raise", Mock())
    monkeypatch.setattr(config_router, "_save_export_config", Mock())

    client = TestClient(create_app())
    response = client.put(
        "/api/config/export/api-targets/occurrence_json/groups/plots",
        json={"enabled": True, "detail": {"pass_through": True}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transformer_plugin"] == "niamoto_to_dwc_occurrence"
    assert payload["transformer_params"]["taxonomy_entity"] == "plots"


def test_update_api_export_group_config_preserves_omitted_existing_fields(monkeypatch):
    export_config = {
        "exports": [
            {
                "name": "json_api",
                "exporter": "json_api_exporter",
                "groups": [
                    {
                        "group_by": "taxons",
                        "data_source": "taxon_stats",
                        "detail": {"pass_through": False, "fields": ["name"]},
                        "index": {"fields": ["id"]},
                        "json_options": {"indent": 2},
                        "transformer_plugin": "custom_transformer",
                        "transformer_params": {"custom": True},
                    }
                ],
            }
        ]
    }

    monkeypatch.setattr(config_router, "_load_export_config", lambda: export_config)
    monkeypatch.setattr(config_router, "_validate_export_config_or_raise", Mock())
    monkeypatch.setattr(config_router, "_save_export_config", Mock())

    client = TestClient(create_app())
    response = client.put(
        "/api/config/export/api-targets/json_api/groups/taxons",
        json={"enabled": True, "index": {"fields": ["id", "full_name"]}},
    )

    assert response.status_code == 200
    saved_group = export_config["exports"][0]["groups"][0]
    assert saved_group["data_source"] == "taxon_stats"
    assert saved_group["detail"] == {"pass_through": False, "fields": ["name"]}
    assert saved_group["index"] == {"fields": ["id", "full_name"]}
    assert saved_group["json_options"] == {"indent": 2}
    assert saved_group["transformer_plugin"] == "custom_transformer"
    assert saved_group["transformer_params"] == {"custom": True}


def test_api_export_auto_config_route_returns_read_only_simple_proposal(monkeypatch):
    export_config = {
        "exports": [
            {
                "name": "json_api",
                "exporter": "json_api_exporter",
                "params": {"json_options": {"indent": 2}},
                "groups": [
                    {
                        "group_by": "taxons",
                        "detail": {
                            "pass_through": False,
                            "fields": [{"custom_name": "general_info.name.value"}],
                        },
                        "index": {"fields": [{"custom_id": "id"}]},
                    }
                ],
            }
        ]
    }

    monkeypatch.setattr(config_router, "_load_export_config", lambda: export_config)

    def fail_if_saved(_config):
        raise AssertionError("auto-config proposal must not save export.yml")

    monkeypatch.setattr(config_router, "_save_export_config", fail_if_saved)

    async def fake_suggest_index_fields(group_by: str):
        assert group_by == "taxons"
        return config_router.IndexFieldSuggestions(
            display_fields=[
                config_router.SuggestedDisplayField(
                    name="name",
                    source="general_info.name.value",
                    type="text",
                    label="Name",
                    priority="high",
                )
            ],
            filters=[],
            total_entities=12,
        )

    monkeypatch.setattr(
        config_router, "suggest_index_fields", fake_suggest_index_fields
    )

    client = TestClient(create_app())
    response = client.get(
        "/api/config/export/api-targets/json_api/groups/taxons/auto-config"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["export_name"] == "json_api"
    assert payload["group_by"] == "taxons"
    assert payload["total_entities"] == 12
    assert payload["proposal"]["detail"]["pass_through"] is False
    assert payload["proposal"]["detail"]["fields"] == [
        {"name": "general_info.name.value"}
    ]
    assert payload["proposal"]["index"]["fields"] == [
        {
            "detail_url": {
                "generator": "endpoint_url",
                "params": {"base_path": "/api"},
            }
        },
        {"name": "general_info.name.value"},
    ]
    assert payload["sections"]["index"]["config"]["fields"][0] == {
        "detail_url": {
            "generator": "endpoint_url",
            "params": {"base_path": "/api"},
        }
    }
    assert payload["sections"]["json_options"]["config"] == {"indent": 2}
    assert payload["sections"]["index"]["confidence"] == "high"


def test_api_export_group_config_exposes_detail_url_index_field(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "json_api",
                    "exporter": "json_api_exporter",
                    "params": {"output_dir": "exports/json_api"},
                    "groups": [
                        {
                            "group_by": "plots",
                            "detail": {"pass_through": True},
                            "index": {"fields": [{"plot_name": "general_info.name"}]},
                        }
                    ],
                }
            ]
        },
    )

    client = TestClient(create_app())
    response = client.get("/api/config/export/api-targets/json_api/groups/plots")

    assert response.status_code == 200
    payload = response.json()
    assert payload["index"]["fields"] == [
        {
            "detail_url": {
                "generator": "endpoint_url",
                "params": {"base_path": "/api"},
            }
        },
        {"plot_name": "general_info.name"},
    ]


def test_api_export_group_config_keeps_detail_url_when_other_endpoint_url_exists(
    monkeypatch,
):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "json_api",
                    "exporter": "json_api_exporter",
                    "params": {"output_dir": "exports/json_api"},
                    "groups": [
                        {
                            "group_by": "plots",
                            "detail": {"pass_through": True},
                            "index": {
                                "fields": [
                                    {
                                        "url": {
                                            "generator": "endpoint_url",
                                            "params": {"base_path": "/api"},
                                        }
                                    }
                                ]
                            },
                        }
                    ],
                }
            ]
        },
    )

    client = TestClient(create_app())
    response = client.get("/api/config/export/api-targets/json_api/groups/plots")

    assert response.status_code == 200
    payload = response.json()
    assert payload["index"]["fields"] == [
        {
            "detail_url": {
                "generator": "endpoint_url",
                "params": {"base_path": "/api"},
            }
        },
        {"url": {"generator": "endpoint_url", "params": {"base_path": "/api"}}},
    ]


def test_api_export_auto_config_route_marks_dwc_mapping_unresolved(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "dwc_api",
                    "exporter": "json_api_exporter",
                    "groups": [
                        {
                            "group_by": "taxons",
                            "transformer_plugin": "niamoto_to_dwc_occurrence",
                        }
                    ],
                }
            ]
        },
    )

    async def fake_suggest_index_fields(group_by: str):
        assert group_by == "taxons"
        return config_router.IndexFieldSuggestions(
            display_fields=[],
            filters=[],
            total_entities=3,
        )

    monkeypatch.setattr(
        config_router, "suggest_index_fields", fake_suggest_index_fields
    )

    client = TestClient(create_app())
    response = client.get(
        "/api/config/export/api-targets/dwc_api/groups/taxons/auto-config"
    )

    assert response.status_code == 200
    payload = response.json()
    transformer_params = payload["proposal"]["transformer_params"]
    assert payload["proposal"]["transformer_plugin"] == "niamoto_to_dwc_occurrence"
    assert transformer_params["taxonomy_entity"] == "taxons"
    assert transformer_params["mapping"]["occurrenceID"]["generator"] == (
        "unique_occurrence_id"
    )
    assert "decimalLatitude" in payload["sections"]["dwc_mapping"]["unresolved"]


def test_api_export_preview_route_maps_representative_index_data(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "json_api",
                    "exporter": "json_api_exporter",
                    "params": {"output_dir": "exports/json_api"},
                    "groups": [],
                }
            ]
        },
    )

    def fake_load_preview_item(group_by, data_source, paths=None):
        assert group_by == "taxons"
        assert data_source is None
        assert paths == ["general_info.name.value"]
        return {
            "id": 42,
            "general_info": {"name": {"value": "Araucaria columnaris"}},
        }

    monkeypatch.setattr(
        config_router, "_load_api_export_preview_item", fake_load_preview_item
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/config/export/api-targets/json_api/groups/taxons/preview",
        json={
            "enabled": True,
            "section": "index",
            "detail": {"pass_through": True},
            "index": {"fields": [{"name": "general_info.name.value"}]},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["export_name"] == "json_api"
    assert payload["group_by"] == "taxons"
    assert payload["section"] == "index"
    assert payload["item_id"] == 42
    assert payload["preview"] == {
        "name": "Araucaria columnaris",
        "detail_url": "/api/taxons/42.json",
    }
    assert payload["metadata"] == {
        "sample_basis": "representative_record",
        "rows_sampled": 1,
        "source": "taxons",
        "source_record_id": 42,
        "illustrative": True,
    }
    assert payload["warnings"] == []
    assert payload["errors"] == []
    assert payload["source"]["general_info"]["name"]["value"] == (
        "Araucaria columnaris"
    )


def test_api_export_preview_get_route_uses_saved_group_config(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "json_api",
                    "exporter": "json_api_exporter",
                    "params": {"output_dir": "exports/json_api"},
                    "groups": [
                        {
                            "group_by": "plots",
                            "detail": {"pass_through": True},
                            "index": {
                                "fields": [{"plot_name": "general_info.name.value"}]
                            },
                        }
                    ],
                }
            ]
        },
    )

    def fake_load_preview_item(group_by, data_source, paths=None):
        assert group_by == "plots"
        assert data_source is None
        assert paths == ["general_info.name.value"]
        return {
            "id": 7,
            "general_info": {"name": {"value": "Plot A"}},
        }

    monkeypatch.setattr(
        config_router, "_load_api_export_preview_item", fake_load_preview_item
    )

    client = TestClient(create_app())
    response = client.get(
        "/api/config/export/api-targets/json_api/groups/plots/preview"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["section"] == "index"
    assert payload["item_id"] == 7
    assert payload["preview"] == {
        "plot_name": "Plot A",
        "detail_url": "/api/plots/7.json",
    }
    assert payload["metadata"]["rows_sampled"] == 1
    assert payload["metadata"]["source_record_id"] == 7


def test_api_export_preview_route_applies_dwc_transformer_for_detail(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "dwc_occurrence_json",
                    "exporter": "json_api_exporter",
                    "params": {"output_dir": "exports/dwc_occurrence_json"},
                    "groups": [
                        {
                            "group_by": "taxons",
                            "transformer_plugin": "niamoto_to_dwc_occurrence",
                            "transformer_params": {
                                "occurrence_list_source": "occurrences",
                                "mapping": {
                                    "occurrenceID": {
                                        "generator": "unique_occurrence_id"
                                    }
                                },
                            },
                        }
                    ],
                }
            ]
        },
    )

    candidates = [
        {"id": 1, "general_info": {"name": {"value": "Empty taxon"}}},
        {"id": 2, "general_info": {"name": {"value": "Araucaria columnaris"}}},
    ]

    def fake_load_preview_items(group_by, data_source, paths=None):
        assert group_by == "taxons"
        assert data_source is None
        assert paths == []
        return candidates

    def fake_apply_transformer(group_config, items):
        assert group_config.transformer_plugin == "niamoto_to_dwc_occurrence"
        assert items == candidates
        return candidates[1], [
            {
                "occurrenceID": "taxons-2-occurrence-1",
                "scientificName": "Araucaria columnaris",
            }
        ]

    monkeypatch.setattr(
        config_router, "_load_api_export_preview_items", fake_load_preview_items
    )
    monkeypatch.setattr(
        config_router,
        "_apply_api_export_preview_transformer",
        fake_apply_transformer,
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/config/export/api-targets/dwc_occurrence_json/groups/taxons/preview",
        json={
            "enabled": True,
            "section": "detail",
            "transformer_plugin": "niamoto_to_dwc_occurrence",
            "transformer_params": {
                "occurrence_list_source": "occurrences",
                "mapping": {
                    "occurrenceID": {"generator": "unique_occurrence_id"},
                    "scientificName": {"source": "@taxon.general_info.name.value"},
                },
            },
            "detail": {"pass_through": True},
            "index": {"fields": []},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["export_name"] == "dwc_occurrence_json"
    assert payload["section"] == "detail"
    assert payload["item_id"] == 2
    assert payload["preview"] == [
        {
            "occurrenceID": "taxons-2-occurrence-1",
            "scientificName": "Araucaria columnaris",
        }
    ]
    assert payload["metadata"]["rows_sampled"] == 2
    assert payload["metadata"]["illustrative"] is True
    assert payload["source"]["general_info"]["name"]["value"] == (
        "Araucaria columnaris"
    )


def test_api_export_preview_route_allows_draft_to_clear_saved_transformer(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "dwc_occurrence_json",
                    "exporter": "json_api_exporter",
                    "params": {"output_dir": "exports/dwc_occurrence_json"},
                    "groups": [
                        {
                            "group_by": "taxons",
                            "transformer_plugin": "niamoto_to_dwc_occurrence",
                            "transformer_params": {
                                "occurrence_list_source": "occurrences",
                                "mapping": {
                                    "occurrenceID": {
                                        "generator": "unique_occurrence_id"
                                    }
                                },
                            },
                        }
                    ],
                }
            ]
        },
    )

    def fake_load_preview_item(group_by, data_source, paths=None):
        assert group_by == "taxons"
        assert data_source is None
        assert paths == []
        return {"id": 3, "general_info": {"name": {"value": "Draft taxon"}}}

    def fail_apply_transformer(group_config, items):
        pytest.fail("Draft cleared transformer_plugin but transformer was applied")

    monkeypatch.setattr(
        config_router, "_load_api_export_preview_item", fake_load_preview_item
    )
    monkeypatch.setattr(
        config_router,
        "_apply_api_export_preview_transformer",
        fail_apply_transformer,
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/config/export/api-targets/dwc_occurrence_json/groups/taxons/preview",
        json={
            "section": "detail",
            "transformer_plugin": None,
            "detail": {"pass_through": True},
            "index": {"fields": []},
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["item_id"] == 3
    assert payload["preview"] == {
        "id": 3,
        "general_info": {"name": {"value": "Draft taxon"}},
    }


def test_api_export_preview_route_returns_empty_dwc_output_without_mapping(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_export_config",
        lambda: {
            "exports": [
                {
                    "name": "dwc_occurrence_json",
                    "exporter": "json_api_exporter",
                    "params": {"output_dir": "exports/dwc_occurrence_json"},
                    "groups": [
                        {
                            "group_by": "plots",
                            "transformer_plugin": "niamoto_to_dwc_occurrence",
                            "transformer_params": {
                                "occurrence_list_source": "occurrences",
                                "mapping": {},
                            },
                        }
                    ],
                }
            ]
        },
    )

    def fake_load_preview_items(group_by, data_source, paths=None):
        assert group_by == "plots"
        assert data_source is None
        assert paths == []
        return [
            {
                "plots_id": 2,
                "general_info": {"name": {"value": "Aoupinié"}},
            }
        ]

    monkeypatch.setattr(
        config_router, "_load_api_export_preview_items", fake_load_preview_items
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/config/export/api-targets/dwc_occurrence_json/groups/plots/preview",
        json={
            "enabled": True,
            "section": "detail",
            "transformer_plugin": "niamoto_to_dwc_occurrence",
            "transformer_params": {
                "occurrence_list_source": "occurrences",
                "mapping": {},
            },
            "detail": {"pass_through": True},
            "index": {"fields": []},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["item_id"] == 2
    assert payload["preview"] == []
    assert payload["source"]["general_info"]["name"]["value"] == "Aoupinié"


def test_api_export_preview_helpers_parse_paths_and_score_items():
    assert config_router._parse_api_export_preview_value(3) == 3
    assert config_router._parse_api_export_preview_value("plain") == "plain"
    assert config_router._parse_api_export_preview_value('{"name":"Plot A"}') == {
        "name": "Plot A"
    }
    assert config_router._parse_api_export_preview_value("{invalid") == "{invalid"
    assert config_router._normalize_api_export_preview_item(
        {"general_info": '{"name":{"value":"Plot A"}}'}
    ) == {"general_info": {"name": {"value": "Plot A"}}}

    paths = config_router._extract_api_export_mapping_paths(
        [
            "label: general_info.name.value",
            {"raw": "@source.id"},
            {"rainfall": {"source": "general_info.rainfall.value"}},
            {"elevation": {"field": "general_info.elevation.value"}},
            {"flat": "id"},
            {"duplicate": "general_info.name.value"},
        ]
    )
    assert paths == [
        "general_info.name.value",
        "general_info.rainfall.value",
        "general_info.elevation.value",
    ]
    assert config_router._api_export_preview_value_is_populated("  ") is False
    assert config_router._api_export_preview_value_is_populated([]) is False
    assert config_router._api_export_preview_value_is_populated(0) is True
    assert (
        config_router._score_api_export_preview_item(
            {"general_info": {"name": {"value": "Plot A"}, "rainfall": {}}},
            ["general_info.name.value", "general_info.rainfall.value"],
        )
        == 1
    )


def test_load_api_export_preview_items_uses_data_source_and_sorts(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "db" / "niamoto.duckdb"
    db_path.parent.mkdir()
    db_path.touch()

    class FakeRows:
        def all(self):
            return [
                {"plots_id": 1, "general_info": '{"name":{"value":""}}'},
                {"plots_id": 2, "general_info": '{"name":{"value":"Plot B"}}'},
            ]

    class FakeResult:
        def mappings(self):
            return FakeRows()

    class FakeSession:
        def execute(self, query):
            assert "plot_stats" in str(query)
            return FakeResult()

    class FakeDatabase:
        def __init__(self, path, read_only=False):
            assert path == str(db_path)
            assert read_only is True
            self.session = FakeSession()
            self.closed = False

        def has_table(self, table_name):
            return table_name == "plot_stats"

        def close_db_session(self):
            self.closed = True

    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr("niamoto.common.database.Database", FakeDatabase)
    monkeypatch.setattr(
        "niamoto.common.table_resolver.quote_identifier",
        lambda _db, table_name: f'"{table_name}"',
    )

    items = config_router._load_api_export_preview_items(
        "plots", "plot_stats", ["general_info.name.value"]
    )

    assert [item["plots_id"] for item in items] == [2, 1]
    assert items[0]["general_info"]["name"]["value"] == "Plot B"


def test_load_api_export_preview_items_falls_back_to_legacy_data_table(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "db" / "niamoto.duckdb"
    db_path.parent.mkdir()
    db_path.touch()
    checked_tables: list[str] = []

    class FakeRows:
        def all(self):
            return [{"plots_id": 3, "general_info": '{"name":{"value":"Plot C"}}'}]

    class FakeResult:
        def mappings(self):
            return FakeRows()

    class FakeSession:
        def execute(self, query):
            assert '"plots_data"' in str(query)
            return FakeResult()

    class FakeDatabase:
        def __init__(self, path, read_only=False):
            assert path == str(db_path)
            assert read_only is True
            self.session = FakeSession()

        def has_table(self, table_name):
            checked_tables.append(table_name)
            return table_name == "plots_data"

        def close_db_session(self):
            pass

    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr("niamoto.common.database.Database", FakeDatabase)
    monkeypatch.setattr(
        "niamoto.common.table_resolver.quote_identifier",
        lambda _db, table_name: f'"{table_name}"',
    )

    items = config_router._load_api_export_preview_items(
        "plots", None, ["general_info.name.value"]
    )

    assert checked_tables == ["plots", "plots_stats", "plots_data"]
    assert items[0]["plots_id"] == 3


def test_load_api_export_preview_items_requires_database(monkeypatch, tmp_path):
    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        config_router._load_api_export_preview_items("plots", None)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Database not found"


def test_apply_api_export_preview_transformer_uses_first_populated_result(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "db" / "niamoto.duckdb"
    db_path.parent.mkdir()
    db_path.touch()

    class FakeDatabase:
        def __init__(self, path, read_only=False):
            assert path == str(db_path)
            assert read_only is True

        def close_db_session(self):
            pass

    class FakeExporter:
        def __init__(self, db):
            self.db = db

        def _prepare_transformer_batch(self, items, group_config):
            assert [item["id"] for item in items] == [1, 2]
            assert group_config.group_by == "taxons"

        def _apply_transformer(self, item, group_config):
            return [] if item["id"] == 1 else [{"occurrenceID": "taxon-2"}]

    group_config = config_router.JsonApiGroupConfig.model_validate(
        {
            "group_by": "taxons",
            "transformer_plugin": "niamoto_to_dwc_occurrence",
            "transformer_params": {
                "occurrence_list_source": "occurrences",
                "mapping": {"occurrenceID": "@source.id"},
            },
        }
    )

    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr("niamoto.common.database.Database", FakeDatabase)
    monkeypatch.setattr(config_router, "JsonApiExporter", FakeExporter)

    item, preview = config_router._apply_api_export_preview_transformer(
        group_config, [{"id": 1}, {"id": 2}]
    )

    assert item == {"id": 2}
    assert preview == [{"occurrenceID": "taxon-2"}]


def test_build_api_export_preview_maps_curated_detail(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_api_export_preview_item",
        lambda group_by, data_source, paths=None: {
            "id": 4,
            "general_info": {"name": {"value": "Plot D"}},
        },
    )

    response = config_router._build_api_export_preview(
        "json_api",
        {"name": "json_api", "params": {"output_dir": "exports/json_api"}},
        "plots",
        config_router.ApiExportPreviewRequest.model_validate(
            {
                "section": "detail",
                "detail": {
                    "pass_through": False,
                    "fields": [{"name": "general_info.name.value"}],
                },
                "index": {"fields": []},
            }
        ),
    )

    assert response.item_id == 4
    assert response.preview == {"name": "Plot D"}


def test_api_export_auto_config_helpers_cover_low_confidence_and_dwc_detection():
    suggestions = config_router.IndexFieldSuggestions(
        display_fields=[],
        available_fields=[
            config_router.SuggestedDisplayField(
                name="name",
                source="general_info.name.value",
                type="text",
                label="Name",
                priority="low",
            )
        ],
        filters=[],
        total_entities=5,
    )
    assert config_router._api_export_mapping_from_suggestions(
        suggestions, "taxons", limit=1
    ) == [{"name": "general_info.name.value"}]

    export_target = {
        "params": {"json_options": {"indent": 2}},
        "groups": [
            {
                "group_by": "taxons",
                "transformer_plugin": "niamoto_to_dwc_occurrence",
            }
        ],
    }
    assert config_router._api_export_target_uses_dwc(export_target, "plots") is True

    empty_dwc_target = {
        "name": "occurrence_json",
        "params": {
            "detail_output_pattern": "{group}/{id}_dwc.json",
            "index_output_pattern": "all_{group}_dwc.json",
        },
        "groups": [],
    }
    assert config_router._api_export_target_uses_dwc(empty_dwc_target, "plots") is True

    dwc_proposal = config_router._build_api_export_auto_config_proposal(
        "occurrence_json",
        empty_dwc_target,
        "plots",
        config_router.IndexFieldSuggestions(
            display_fields=[],
            available_fields=[],
            filters=[],
            total_entities=0,
        ),
    )
    assert dwc_proposal.proposal["transformer_plugin"] == ("niamoto_to_dwc_occurrence")
    assert dwc_proposal.proposal["transformer_params"]["taxonomy_entity"] == "plots"

    empty_proposal = config_router._build_api_export_auto_config_proposal(
        "json_api",
        {"params": {}, "groups": []},
        "plots",
        config_router.IndexFieldSuggestions(
            display_fields=[],
            available_fields=[],
            filters=[],
            total_entities=0,
        ),
    )
    assert empty_proposal.sections["index"].confidence == "low"
    assert empty_proposal.sections["detail"].confidence == "low"


def test_api_export_auto_config_uses_populated_transformed_fields():
    suggestions = config_router.IndexFieldSuggestions(
        display_fields=[
            config_router.SuggestedDisplayField(
                name="class",
                source="extra_data.api_enrichment.sources.source-3.data.taxonomy.class",
                type="text",
                label="Class",
                priority="high",
            ),
            config_router.SuggestedDisplayField(
                name="match_type",
                source=(
                    "extra_data.api_enrichment.sources.source-3.data.name_resolution."
                    "match_type"
                ),
                type="text",
                label="Match Type",
                priority="high",
            ),
        ],
        available_fields=[
            config_router.SuggestedDisplayField(
                name="name",
                source="general_info.name.value",
                type="text",
                label="Name",
                priority="high",
                is_title=True,
            ),
            config_router.SuggestedDisplayField(
                name="rank",
                source="general_info.rank.value",
                type="select",
                label="Rank",
                priority="high",
            ),
            config_router.SuggestedDisplayField(
                name="occurrences_count",
                source="general_info.occurrences_count.value",
                type="number",
                label="Occurrences Count",
                priority="high",
            ),
            config_router.SuggestedDisplayField(
                name="units",
                source="height.units",
                type="select",
                label="Units",
                priority="low",
            ),
        ],
        filters=[],
        total_entities=2,
    )
    preview_items = [
        {
            "taxons_id": 1,
            "general_info": {
                "name": {"value": "Araucaria columnaris"},
                "rank": {"value": "species"},
                "occurrences_count": {"value": 12},
            },
            "height": {"units": "m"},
        }
    ]

    proposal = config_router._build_api_export_auto_config_proposal(
        "json_api",
        {"params": {}, "groups": []},
        "taxons",
        suggestions,
        preview_items,
    )

    assert proposal.proposal["index"]["fields"] == [
        {
            "detail_url": {
                "generator": "endpoint_url",
                "params": {"base_path": "/api"},
            }
        },
        {"name": "general_info.name.value"},
        {"rank": "general_info.rank.value"},
        {"occurrences_count": "general_info.occurrences_count.value"},
    ]
    assert proposal.proposal["detail"]["fields"] == [
        {"name": "general_info.name.value"},
        {"rank": "general_info.rank.value"},
        {"occurrences_count": "general_info.occurrences_count.value"},
    ]
