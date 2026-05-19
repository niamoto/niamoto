"""Regression tests for entity routes on DuckDB projects."""

from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
from unittest.mock import patch

import duckdb
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


def test_entities_available_rejects_invalid_kind(gui_duckdb_client: TestClient):
    response = gui_duckdb_client.get("/api/entities/available?kind=invalid")

    assert response.status_code == 422


def test_entities_available_filters_by_dataset_kind(
    gui_duckdb_client: TestClient,
    gui_duckdb_project: Path,
):
    class FakeRegistry:
        def __init__(self, _db):
            pass

        def list_entities(self):
            return [
                SimpleNamespace(
                    table_name="dataset_occurrences",
                    kind=SimpleNamespace(value="dataset"),
                ),
                SimpleNamespace(
                    table_name="entity_taxons",
                    kind=SimpleNamespace(value="reference"),
                ),
            ]

    with (
        patch("niamoto.gui.api.routers.entities.Config") as config_mock,
        patch("niamoto.gui.api.routers.entities.EntityRegistry", FakeRegistry),
    ):
        config_mock.return_value.database_path = (
            gui_duckdb_project / "db" / "niamoto.duckdb"
        )
        response = gui_duckdb_client.get("/api/entities/available?kind=dataset")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["datasets"] == ["dataset_occurrences"]
    assert payload["references"] == []
    assert {entity["kind"] for entity in payload["all"]} == {"dataset", "reference"}


def test_entities_available_filters_by_reference_kind(
    gui_duckdb_client: TestClient,
    gui_duckdb_project: Path,
):
    class FakeRegistry:
        def __init__(self, _db):
            pass

        def list_entities(self):
            return [
                SimpleNamespace(
                    table_name="dataset_occurrences",
                    kind=SimpleNamespace(value="dataset"),
                ),
                SimpleNamespace(
                    table_name="entity_taxons",
                    kind=SimpleNamespace(value="reference"),
                ),
            ]

    with (
        patch("niamoto.gui.api.routers.entities.Config") as config_mock,
        patch("niamoto.gui.api.routers.entities.EntityRegistry", FakeRegistry),
    ):
        config_mock.return_value.database_path = (
            gui_duckdb_project / "db" / "niamoto.duckdb"
        )
        response = gui_duckdb_client.get("/api/entities/available?kind=reference")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["datasets"] == []
    assert payload["references"] == ["entity_taxons"]
    assert {entity["kind"] for entity in payload["all"]} == {"dataset", "reference"}


def test_list_entities_uses_read_only_duckdb_connections(
    gui_duckdb_client: TestClient,
    gui_duckdb_project: Path,
):
    """Entity list reads should not open DuckDB in write mode."""

    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE taxons (
                taxons_id INTEGER,
                general_info JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO taxons VALUES (
                101,
                '{"name": {"value": "Araucaria columnaris"}}'
            )
            """
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.entities.open_database",
        wraps=entities.open_database,
    ) as open_database_mock:
        response = gui_duckdb_client.get("/api/entities/entities/taxons")

    assert response.status_code == 200, response.text
    assert response.json()[0]["id"] == "101"
    assert open_database_mock.call_args is not None
    assert open_database_mock.call_args.kwargs.get("read_only") is True


def test_entity_detail_uses_read_only_duckdb_connections(
    gui_duckdb_client: TestClient,
    gui_duckdb_project: Path,
):
    """Entity detail reads should not open DuckDB in write mode."""

    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE taxons (
                taxons_id INTEGER,
                general_info JSON,
                widgets_data JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO taxons VALUES (
                101,
                '{"name": {"value": "Araucaria columnaris"}}',
                '{"count": 3}'
            )
            """
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.entities.open_database",
        wraps=entities.open_database,
    ) as open_database_mock:
        response = gui_duckdb_client.get("/api/entities/entity/taxons/101")

    assert response.status_code == 200, response.text
    assert response.json()["id"] == "101"
    assert open_database_mock.call_args is not None
    assert open_database_mock.call_args.kwargs.get("read_only") is True


def test_list_entities_rejects_malformed_group_by(gui_duckdb_client: TestClient):
    response = gui_duckdb_client.get(
        "/api/entities/entities/taxon%3Bdrop%20table%20taxon"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Entity table not found"


def test_entity_detail_rejects_malformed_group_by(gui_duckdb_client: TestClient):
    response = gui_duckdb_client.get(
        "/api/entities/entity/taxon%29%3Bdrop%20table%20taxon/1"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Entity table not found"


def test_entity_routes_quote_dynamic_table_and_id_names(
    gui_duckdb_client: TestClient,
    gui_duckdb_project: Path,
):
    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE "plots-special" (
                "plots-special_id" INTEGER,
                general_info JSON,
                metrics JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO "plots-special" VALUES (
                7,
                '{"name": {"value": "Plot Seven"}}',
                '{"count": 42}'
            )
            """
        )
    finally:
        conn.close()

    list_response = gui_duckdb_client.get("/api/entities/entities/plots-special")
    assert list_response.status_code == 200, list_response.text
    assert list_response.json() == [
        {"id": "7", "name": "Plot Seven", "display_name": "Plot Seven"}
    ]

    detail_response = gui_duckdb_client.get("/api/entities/entity/plots-special/7")
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["id"] == "7"
    assert detail["name"] == "Plot Seven"
    assert detail["group_by"] == "plots-special"
    assert detail["widgets_data"]["metrics"] == {"count": 42}


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


def test_render_widget_rejects_unsafe_plugin_dependencies(monkeypatch, tmp_path):
    work_dir = tmp_path
    config_dir = work_dir / "config"
    config_dir.mkdir()
    db_path = tmp_path / "niamoto.duckdb"
    db_path.write_text("", encoding="utf-8")
    (config_dir / "export.yml").write_text(
        """
exports:
  - groups:
      - group_by: taxon
        widgets:
          - plugin: unsafe_widget
            data_source: richness
            params: {}
""".lstrip(),
        encoding="utf-8",
    )

    class FakeDbContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    class UnsafeWidget:
        def __init__(self, db):
            self.db = db

        def render(self, _data, _params):
            return "<div>Widget</div>"

        def get_dependencies(self):
            return {'/assets/vendor.js" onerror="alert(1)'}

    async def fake_get_entity_detail(group_by: str, entity_id: str):
        return SimpleNamespace(widgets_data={"richness": {"value": 1}})

    monkeypatch.setattr(entities, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(entities, "get_database_path", lambda: db_path)
    monkeypatch.setattr(entities, "get_entity_detail", fake_get_entity_detail)
    monkeypatch.setattr(entities, "open_database", lambda _db_path: FakeDbContext())
    monkeypatch.setattr(
        entities.PluginRegistry,
        "get_plugin",
        staticmethod(lambda _plugin_id, _plugin_type: UnsafeWidget),
    )

    client = TestClient(create_app())
    response = client.get("/api/entities/render-widget/taxon/1/richness")

    assert response.status_code == 200
    assert "Unsafe widget dependency" in response.text
    assert 'onerror="alert(1)' not in response.text
    assert "<script" not in response.text
