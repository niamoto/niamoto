"""Unit tests for data explorer query helpers."""

import asyncio
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import duckdb
from fastapi.testclient import TestClient
from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine

from niamoto.gui.api import context
from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import data_explorer as data_explorer_router
from niamoto.gui.api.routers.data_explorer import (
    MAX_QUERY_LIMIT,
    _build_where_clause,
    _get_default_order_column,
)


class _DummyDB:
    """Minimal DB stub exposing SQLAlchemy engine for identifier quoting."""

    def __init__(self):
        self.engine = create_engine("sqlite://")


@pytest.fixture
def dummy_db() -> _DummyDB:
    return _DummyDB()


def test_build_where_clause_supports_or_parentheses_and_in(dummy_db: _DummyDB):
    clause, params = _build_where_clause(
        "(name = 'A' OR name = 'B') AND id IN (1, 2, 3)",
        {"name", "id"},
        dummy_db,
    )

    assert clause.startswith(" WHERE ")
    assert " OR " in clause
    assert " IN (" in clause
    assert len(params) == 5
    assert set(params.values()) == {"A", "B", 1, 2, 3}


def test_build_where_clause_supports_not_in(dummy_db: _DummyDB):
    clause, params = _build_where_clause(
        "status NOT IN ('draft', 'archived')",
        {"status"},
        dummy_db,
    )

    assert "NOT IN" in clause
    assert len(params) == 2
    assert set(params.values()) == {"draft", "archived"}


def test_build_where_clause_supports_double_quoted_strings(dummy_db: _DummyDB):
    clause, params = _build_where_clause(
        'rank_name = "species" OR full_name LIKE "%Araucaria%"',
        {"rank_name", "full_name"},
        dummy_db,
    )

    assert clause.startswith(" WHERE ")
    assert " OR " in clause
    assert params == {"w_0": "species", "w_1": "%Araucaria%"}


def test_build_where_clause_supports_is_not_null_and_or(dummy_db: _DummyDB):
    clause, params = _build_where_clause(
        "extra_data IS NOT NULL OR active = true",
        {"extra_data", "active"},
        dummy_db,
    )

    assert "IS NOT NULL" in clause
    assert " OR " in clause
    assert params == {"w_0": True}


def test_build_where_clause_rejects_unknown_column(dummy_db: _DummyDB):
    with pytest.raises(HTTPException):
        _build_where_clause("unknown = 1", {"id"}, dummy_db)


def test_build_where_clause_rejects_invalid_syntax(dummy_db: _DummyDB):
    with pytest.raises(HTTPException):
        _build_where_clause("1 = 1", {"id"}, dummy_db)


def test_build_where_clause_supports_unary_not_on_group(dummy_db: _DummyDB):
    clause, params = _build_where_clause(
        "NOT (active = true OR status = 'archived')",
        {"active", "status"},
        dummy_db,
    )

    assert "NOT" in clause
    assert " OR " in clause
    assert params["w_0"] is True
    assert params["w_1"] == "archived"


def test_build_where_clause_supports_between_and_not_between(dummy_db: _DummyDB):
    clause, params = _build_where_clause(
        "score BETWEEN 10 AND 20 OR age NOT BETWEEN 18 AND 65",
        {"score", "age"},
        dummy_db,
    )

    assert "BETWEEN" in clause
    assert "NOT BETWEEN" in clause
    assert params == {"w_0": 10, "w_1": 20, "w_2": 18, "w_3": 65}


def test_get_default_order_column_prefers_nested_set_left_boundary():
    column = _get_default_order_column(
        "taxons",
        [
            {"name": "taxons_id", "type": "BIGINT"},
            {"name": "lft", "type": "INTEGER"},
            {"name": "extra_data", "type": "JSON"},
        ],
    )

    assert column == "lft"


def test_get_default_order_column_falls_back_to_entity_identifier():
    column = _get_default_order_column(
        "taxons",
        [
            {"name": "general_info", "type": "JSON"},
            {"name": "taxons_id", "type": "BIGINT"},
        ],
    )

    assert column == "taxons_id"


def test_list_tables_uses_duckdb_fixture_without_reflection_errors(
    gui_duckdb_client: TestClient,
):
    """Data explorer should list DuckDB tables via backend-safe introspection."""

    response = gui_duckdb_client.get("/api/data/tables")

    assert response.status_code == 200, response.text
    payload = response.json()

    table_names = [table["name"] for table in payload]
    assert table_names == ["dataset_occurrences", "entity_taxons"]
    assert payload[0]["count"] == 3
    assert payload[0]["columns"] == ["id", "taxon_id", "count", "locality"]


def test_get_table_columns_uses_duckdb_fixture_without_reflection_errors(
    gui_duckdb_client: TestClient,
):
    """Column metadata endpoint should read DuckDB schema through the safe helper."""

    response = gui_duckdb_client.get("/api/data/tables/dataset_occurrences/columns")

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["table"] == "dataset_occurrences"
    assert [column["name"] for column in payload["columns"]] == [
        "id",
        "taxon_id",
        "count",
        "locality",
    ]


def test_get_table_columns_returns_404_when_table_is_missing(
    gui_duckdb_client: TestClient,
):
    response = gui_duckdb_client.get("/api/data/tables/dataset_missing/columns")

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Table 'dataset_missing' not found"


def test_query_table_applies_default_order_by_when_none_provided(
    gui_duckdb_project: Path,
):
    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"

    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("DELETE FROM entity_taxons")
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (202, 'Niaouli test', 101),
                (101, 'Araucaria columnaris', NULL)
            """
        )
    finally:
        conn.close()

    with patch.object(context, "_working_directory", gui_duckdb_project):
        client = TestClient(create_app())
        response = client.post(
            "/api/data/query",
            json={"table": "entity_taxons", "limit": 10, "offset": 0},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [row["id"] for row in payload["rows"]] == [101, 202]


def test_query_table_rejects_oversized_limit(gui_duckdb_client: TestClient):
    response = gui_duckdb_client.post(
        "/api/data/query",
        json={"table": "entity_taxons", "limit": MAX_QUERY_LIMIT + 1, "offset": 0},
    )

    assert response.status_code == 422, response.text
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "limit"]
    assert error["type"] == "less_than_equal"


def test_query_table_opens_database_in_read_only_mode(
    monkeypatch, gui_duckdb_project: Path
):
    captured: dict[str, object] = {}

    class DummyDB:
        def get_table_names(self):
            return ["entity_taxons"]

        def get_columns(self, _table):
            return [
                {"name": "id", "type": "INTEGER"},
                {"name": "full_name", "type": "VARCHAR"},
            ]

        @property
        def engine(self):
            return create_engine("sqlite://")

        def session(self):
            class DummySessionContext:
                def __enter__(self_nonlocal):
                    class DummySession:
                        def execute(self, query, _params=None):
                            query_text = str(query)

                            class DummyResult:
                                def __init__(self, query_text):
                                    self.query_text = query_text

                                def scalar(self):
                                    return 1

                                def keys(self):
                                    return ["id", "full_name"]

                                def __iter__(self):
                                    if "COUNT(*)" in self.query_text:
                                        return iter([])
                                    return iter([(1, "Araucaria columnaris")])

                            return DummyResult(query_text)

                    return DummySession()

                def __exit__(self_nonlocal, exc_type, exc, tb):
                    return False

            return DummySessionContext()

    @contextmanager
    def fake_open_database(_path, *, read_only=False):
        captured["read_only"] = read_only
        yield DummyDB()

    monkeypatch.setattr(
        "niamoto.gui.api.routers.data_explorer.open_database",
        fake_open_database,
    )

    with patch.object(context, "_working_directory", gui_duckdb_project):
        client = TestClient(create_app())
        response = client.post(
            "/api/data/query",
            json={"table": "entity_taxons", "limit": 10, "offset": 0},
        )

    assert response.status_code == 200, response.text
    assert captured["read_only"] is True


def test_preview_enrichment_runs_loader_in_threadpool(monkeypatch, tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "import.yml").write_text(
        """
taxonomy:
  api_enrichment:
    plugin: api_taxonomy_enricher
    api_url: https://example.test/taxon
    query_field: full_name
    query_param_name: q
    response_mapping: {}
""",
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    async def fake_run_in_threadpool(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"api_enrichment": {"status": "previewed"}}

    monkeypatch.setattr(
        data_explorer_router,
        "get_working_directory",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        data_explorer_router,
        "run_in_threadpool",
        fake_run_in_threadpool,
    )

    response = asyncio.run(
        data_explorer_router.preview_enrichment(
            data_explorer_router.EnrichmentPreviewRequest(
                taxon_name="Araucaria columnaris"
            )
        )
    )

    assert captured["func"].__name__ == "load_data"
    assert captured["args"] == (
        {"full_name": "Araucaria columnaris"},
        {
            "plugin": "api_taxonomy_enricher",
            "params": {
                "api_url": "https://example.test/taxon",
                "query_field": "full_name",
                "query_param_name": "q",
                "response_mapping": {},
                "rate_limit": 1.0,
                "cache_results": False,
                "auth_method": "none",
                "auth_params": {},
                "query_params": {},
                "chained_endpoints": [],
            },
        },
    )
    assert captured["kwargs"] == {}
    assert response["success"] is True
    assert response["api_enrichment"] == {"status": "previewed"}


def test_preview_enrichment_route_reads_config_and_returns_preview(
    monkeypatch,
    tmp_path: Path,
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "import.yml").write_text(
        """
taxonomy:
  api_enrichment:
    plugin: api_taxonomy_enricher
    api_url: https://example.test/taxon
    query_field: full_name
    query_param_name: q
    response_mapping: {}
""",
        encoding="utf-8",
    )

    async def fake_run_in_threadpool(func, *args, **kwargs):
        assert func.__name__ == "load_data"
        assert args[0] == {"full_name": "Araucaria columnaris"}
        return {"api_enrichment": {"canonical_name": "Araucaria columnaris"}}

    monkeypatch.setattr(
        data_explorer_router,
        "get_working_directory",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        data_explorer_router,
        "run_in_threadpool",
        fake_run_in_threadpool,
    )

    response = TestClient(create_app()).post(
        "/api/data/enrichment/preview",
        json={"taxon_name": "Araucaria columnaris"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "success": True,
        "taxon_name": "Araucaria columnaris",
        "api_enrichment": {"canonical_name": "Araucaria columnaris"},
        "config_used": {
            "api_url": "https://example.test/taxon",
            "query_field": "full_name",
        },
    }
