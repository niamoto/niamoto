"""Unit tests for data explorer query helpers."""

from pathlib import Path
from unittest.mock import patch

import duckdb
from fastapi.testclient import TestClient
from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine

from niamoto.gui.api import context
from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers.data_explorer import (
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
