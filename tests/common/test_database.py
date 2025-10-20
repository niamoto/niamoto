"""Regression tests for the lightweight Database wrapper."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.sql import text

from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseQueryError, TransactionError


@pytest.fixture
def test_database() -> Any:
    db = Database(db_path=":memory:")
    yield db
    # Properly cleanup database resources
    try:
        db.close_db_session()
    except Exception:
        pass
    finally:
        # Dispose of the engine to close all connections
        if hasattr(db, "engine") and db.engine:
            db.engine.dispose()


@pytest.fixture
def duckdb_database(tmp_path):
    db_path = tmp_path / "test.duckdb"
    db = Database(db_path=str(db_path))
    yield db
    try:
        db.close_db_session()
    except Exception:
        pass
    finally:
        if hasattr(db, "engine") and db.engine:
            db.engine.dispose()


@pytest.fixture
def session(test_database: Any):
    session = test_database.get_new_session()
    yield session
    session.rollback()
    session.close()


def test_database_initialisation(test_database: Any) -> None:
    assert test_database.engine is not None
    assert test_database.session is not None


def test_create_and_query_table(test_database: Any) -> None:
    test_database.execute_sql("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
    test_database.execute_sql(
        "INSERT INTO sample (id, name) VALUES (:id, :name)",
        {"id": 1, "name": "alpha"},
    )
    rows = test_database.execute_sql(
        "SELECT name FROM sample WHERE id = :id", {"id": 1}, fetch_all=True
    )
    assert len(rows) > 0, "Expected the sample query to return at least one row"
    assert rows[0][0] == "alpha"


def test_transaction_helpers(test_database: Any) -> None:
    test_database.begin_transaction()
    test_database.execute_sql("CREATE TABLE tx_test (id INTEGER)")
    test_database.execute_sql("INSERT INTO tx_test VALUES (1)")
    test_database.commit_transaction()

    rows = test_database.execute_sql("SELECT COUNT(*) FROM tx_test", fetch=True)
    assert rows[0] == 1


def test_double_begin_transaction_raises(test_database: Any) -> None:
    test_database.begin_transaction()
    try:
        with pytest.raises(TransactionError):
            test_database.begin_transaction()
    finally:
        test_database.rollback_transaction()


def test_has_table(test_database: Any) -> None:
    test_database.execute_sql("CREATE TABLE lookup (id INTEGER)")
    assert test_database.has_table("lookup")
    assert not test_database.has_table("missing")


def test_execute_select_errors(test_database: Any) -> None:
    with pytest.raises(DatabaseQueryError):
        test_database.execute_select("SELECT * FROM non_existing_table")


def test_close_session(test_database: Any) -> None:
    session = test_database.get_new_session()
    first_session = session()
    second_session = None
    try:
        test_database.close_db_session()
        second_session = session()

        # The scoped session should return a brand new Session instance
        assert first_session is not second_session

        result = session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
    finally:
        # Ensure sessions are closed even if assertions fail
        if first_session and first_session.is_active:
            first_session.close()
        if second_session and second_session.is_active:
            second_session.close()


def test_duckdb_skips_index_creation(duckdb_database: Any, monkeypatch) -> None:
    duckdb_database.execute_sql(
        "CREATE TABLE duck_test (id INTEGER, foreign_id INTEGER)"
    )

    def fail(*_args, **_kwargs):  # pragma: no cover - defensive guard
        raise AssertionError("DuckDB path should not inspect indexes")

    monkeypatch.setattr(duckdb_database, "get_table_columns", fail)

    duckdb_database.create_indexes_for_table("duck_test")
    # Internal helper should also no-op without raising
    duckdb_database._create_missing_indexes()


def test_duckdb_database_stats(duckdb_database: Any) -> None:
    duckdb_database.execute_sql("CREATE TABLE stats_test (id INTEGER)")
    stats = duckdb_database.get_database_stats()

    assert stats["index_count"] is None
    assert "table_count" in stats
