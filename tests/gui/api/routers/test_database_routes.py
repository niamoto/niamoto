"""Regression tests for database introspection routes on DuckDB projects."""

from fastapi.testclient import TestClient


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
