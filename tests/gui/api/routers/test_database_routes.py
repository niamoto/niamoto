"""Regression tests for database introspection routes on DuckDB projects."""

from fastapi.testclient import TestClient
import yaml

from niamoto.gui.api.routers import database as database_router


def test_database_router_path_expands_configured_home_path(tmp_path, monkeypatch):
    """Router-local database lookup should expand ~/ paths from config.yml."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    db_file = home_dir / "custom.duckdb"
    db_file.write_text("fake db")

    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "config.yml").write_text(
        yaml.dump({"database": {"path": "~/custom.duckdb"}})
    )

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(database_router, "get_working_directory", lambda: project_dir)

    assert database_router.get_database_path() == db_file


def test_database_router_missing_configured_path_falls_back(
    tmp_path, monkeypatch, caplog
):
    """Router-local database lookup should fall back when config points nowhere."""
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "config.yml").write_text(
        yaml.dump({"database": {"path": "missing/custom.duckdb"}})
    )

    fallback_db = project_dir / "db" / "niamoto.duckdb"
    fallback_db.parent.mkdir()
    fallback_db.write_text("fake db")

    monkeypatch.setattr(database_router, "get_working_directory", lambda: project_dir)

    assert database_router.get_database_path() == fallback_db
    assert "Configured database path not found" in caplog.text


def test_database_schema_uses_duckdb_fixture_without_reflection_errors(
    gui_duckdb_client: TestClient,
):
    """Schema endpoint should avoid SQLAlchemy reflection paths that break on DuckDB."""

    response = gui_duckdb_client.get("/api/database/schema")

    assert response.status_code == 200, response.text
    payload = response.json()

    tables = {table["name"]: table for table in payload["tables"]}
    views = {view["name"]: view for view in payload["views"]}

    assert payload["total_size"] is not None
    assert tables["dataset_occurrences"]["row_count"] == 3
    assert [column["name"] for column in tables["dataset_occurrences"]["columns"]] == [
        "id",
        "taxon_id",
        "count",
        "locality",
    ]
    assert tables["entity_taxons"]["row_count"] == 2
    assert views["occurrences_by_taxon"]["is_view"] is True
