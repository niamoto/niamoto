from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import config as config_router


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
    assert payload["source"]["general_info"]["name"]["value"] == (
        "Araucaria columnaris"
    )


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
