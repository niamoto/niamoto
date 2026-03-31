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
    }
