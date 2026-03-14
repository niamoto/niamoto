"""Unit tests for data explorer query helpers."""

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine

from niamoto.gui.api.routers.data_explorer import _build_where_clause


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
