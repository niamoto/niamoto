"""Regression tests for entity routes on DuckDB projects."""

from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
from unittest.mock import patch

from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import entities


def test_entities_available_use_read_only_duckdb_connections(
    gui_duckdb_client: TestClient,
    gui_duckdb_project: Path,
):
    """Entity listing should not open DuckDB in write mode."""

    with (
        patch(
            "niamoto.gui.api.routers.entities.open_database",
            wraps=entities.open_database,
        ) as open_database_mock,
        patch("niamoto.gui.api.routers.entities.Config") as config_mock,
    ):
        config_mock.return_value.database_path = (
            gui_duckdb_project / "db" / "niamoto.duckdb"
        )
        response = gui_duckdb_client.get("/api/entities/available")

    assert response.status_code == 200, response.text
    assert open_database_mock.call_args is not None
    assert open_database_mock.call_args.kwargs.get("read_only") is True


def test_list_entities_rejects_malformed_group_by(gui_duckdb_client: TestClient):
    response = gui_duckdb_client.get(
        "/api/entities/entities/taxon%3Bdrop%20table%20taxon"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid entity group"


def test_entity_detail_rejects_malformed_group_by(gui_duckdb_client: TestClient):
    response = gui_duckdb_client.get(
        "/api/entities/entity/taxon%29%3Bdrop%20table%20taxon/1"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid entity group"


def test_render_widget_escapes_missing_widget_transform_key(monkeypatch, tmp_path):
    work_dir = tmp_path
    config_dir = work_dir / "config"
    config_dir.mkdir()
    (config_dir / "export.yml").write_text(
        "exports:\n  - groups:\n      - group_by: taxon\n        widgets: []\n",
        encoding="utf-8",
    )
    transform_key = "<img src=x onerror=alert(1)>"

    async def fake_get_entity_detail(group_by: str, entity_id: str):
        return SimpleNamespace(widgets_data={transform_key: {"value": 1}})

    monkeypatch.setattr(entities, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(entities, "get_entity_detail", fake_get_entity_detail)

    client = TestClient(create_app())
    response = client.get(
        f"/api/entities/render-widget/taxon/1/{quote(transform_key, safe='')}",
    )

    assert response.status_code == 200
    assert "<img src=x onerror=alert(1)>" not in response.text
    assert "&lt;img src=x onerror=alert(1)&gt;" in response.text
