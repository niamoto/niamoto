"""Regression tests for database introspection routes on DuckDB projects."""

import inspect
import sqlite3

import duckdb
from fastapi.testclient import TestClient
import pytest
import yaml

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import database as database_router
from niamoto.gui.api.utils.database import open_database


def test_table_stats_route_is_sync_for_threadpool_execution():
    assert not inspect.iscoroutinefunction(database_router.get_table_stats)


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


def test_table_preview_uses_read_only_duckdb_connection(
    gui_duckdb_client: TestClient,
    gui_duckdb_project,
    monkeypatch,
):
    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    read_only_values = []

    def recording_open_database(path, *, read_only=False):
        read_only_values.append(read_only)
        return open_database(path, read_only=read_only)

    monkeypatch.setattr(database_router, "open_database", recording_open_database)

    with open_database(db_path, read_only=True):
        response = gui_duckdb_client.get(
            "/api/database/tables/dataset_occurrences/preview"
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["table_name"] == "dataset_occurrences"
    assert payload["total_rows"] == 3
    assert [row["id"] for row in payload["rows"]] == [1, 2, 3]
    assert read_only_values == [True]


def test_table_preview_does_not_create_sqlite_indexes_in_read_only_mode(
    tmp_path,
    monkeypatch,
):
    project_dir = tmp_path / "sqlite-project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir()
    db_path = db_dir / "niamoto.db"
    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.db"}}),
        encoding="utf-8",
    )

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE parent (id INTEGER PRIMARY KEY);
            CREATE TABLE child (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER,
                label TEXT,
                FOREIGN KEY (parent_id) REFERENCES parent(id)
            );
            INSERT INTO parent VALUES (1);
            INSERT INTO child VALUES (1, 1, 'A');
            """
        )
        conn.commit()
        before_indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    finally:
        conn.close()

    monkeypatch.setattr(database_router, "get_working_directory", lambda: project_dir)

    response = TestClient(create_app()).get("/api/database/tables/child/preview")

    assert response.status_code == 200, response.text
    conn = sqlite3.connect(db_path)
    try:
        after_indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    finally:
        conn.close()
    assert after_indexes == before_indexes == []
    assert not db_path.with_suffix(".db-wal").exists()


def test_table_preview_paginates_with_stable_default_order(
    gui_duckdb_client: TestClient,
    gui_duckdb_project,
):
    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE unordered_preview (
                id INTEGER,
                label VARCHAR
            )
            """
        )
        conn.execute(
            """
            INSERT INTO unordered_preview VALUES
                (3, 'third'),
                (1, 'first'),
                (2, 'second')
            """
        )
    finally:
        conn.close()

    response = gui_duckdb_client.get(
        "/api/database/tables/unordered_preview/preview",
        params={"limit": 1, "offset": 1},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["rows"] == [{"id": 2, "label": "second"}]


def test_table_stats_reports_counts_for_duckdb_table(gui_duckdb_client: TestClient):
    response = gui_duckdb_client.get("/api/database/tables/dataset_occurrences/stats")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["table_name"] == "dataset_occurrences"
    assert payload["row_count"] == 3
    assert payload["column_count"] == 4
    assert payload["null_counts"] == {
        "id": 0,
        "taxon_id": 0,
        "count": 0,
        "locality": 0,
    }
    assert payload["unique_counts"]["taxon_id"] == 2
    assert set(payload["data_types"]) == {"id", "taxon_id", "count", "locality"}


def test_table_stats_uses_read_only_duckdb_connection(
    gui_duckdb_client: TestClient,
    gui_duckdb_project,
    monkeypatch,
):
    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    read_only_values = []

    def recording_open_database(path, *, read_only=False):
        read_only_values.append(read_only)
        return open_database(path, read_only=read_only)

    monkeypatch.setattr(database_router, "open_database", recording_open_database)

    with open_database(db_path, read_only=True):
        response = gui_duckdb_client.get(
            "/api/database/tables/dataset_occurrences/stats"
        )

    assert response.status_code == 200, response.text
    assert response.json()["table_name"] == "dataset_occurrences"
    assert read_only_values == [True]


def test_table_stats_reports_nulls_and_duplicates(
    gui_duckdb_client: TestClient,
    gui_duckdb_project,
):
    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE stats_fixture (
                id INTEGER,
                name VARCHAR,
                score INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO stats_fixture VALUES
                (1, 'A', 10),
                (2, 'A', NULL),
                (3, NULL, 10)
            """
        )
    finally:
        conn.close()

    response = gui_duckdb_client.get("/api/database/tables/stats_fixture/stats")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["row_count"] == 3
    assert payload["column_count"] == 3
    assert payload["null_counts"] == {"id": 0, "name": 1, "score": 1}
    assert payload["unique_counts"]["name"] == 1
    assert payload["unique_counts"]["score"] == 1


def test_table_stats_returns_404_for_missing_table(gui_duckdb_client: TestClient):
    response = gui_duckdb_client.get("/api/database/tables/missing_table/stats")

    assert response.status_code == 404
    assert response.json()["detail"] == "Table 'missing_table' not found"


def test_query_endpoint_enforces_limit_over_user_sql_limit(
    gui_duckdb_client: TestClient,
):
    response = gui_duckdb_client.get(
        "/api/database/query",
        params={
            "query": "SELECT * FROM dataset_occurrences ORDER BY id LIMIT 5000",
            "limit": 2,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["row_count"] == 2
    assert [row["id"] for row in payload["rows"]] == [1, 2]


@pytest.mark.parametrize(
    ("query", "expected_row"),
    [
        ("SELECT 1 AS created_at", {"created_at": 1}),
        ("SELECT 1 AS updated_count", {"updated_count": 1}),
        ("SELECT 'drop' AS label", {"label": "drop"}),
    ],
)
def test_query_endpoint_allows_safe_identifiers_and_literals_with_keyword_substrings(
    gui_duckdb_client: TestClient,
    query,
    expected_row,
):
    response = gui_duckdb_client.get(
        "/api/database/query", params={"query": query, "limit": 1}
    )

    assert response.status_code == 200, response.text
    assert response.json()["rows"] == [expected_row]


@pytest.mark.parametrize(
    ("query", "expected_detail"),
    [
        ("DROP TABLE dataset_occurrences", "Only SELECT queries are allowed"),
        ("UPDATE dataset_occurrences SET count = 0", "Only SELECT queries are allowed"),
        (
            "INSERT INTO dataset_occurrences VALUES (99, 1, 1, 'bad')",
            "Only SELECT queries are allowed",
        ),
        (
            "SELECT * FROM dataset_occurrences; DROP TABLE dataset_occurrences",
            "Multiple statements are not allowed",
        ),
        (
            "SELECT * FROM dataset_occurrences -- hidden mutation",
            "Multiple statements are not allowed",
        ),
        (
            "SELECT * FROM dataset_occurrences /* hidden mutation */",
            "Multiple statements are not allowed",
        ),
        (
            "SELECT * FROM dataset_occurrences UNION SELECT * FROM drop",
            "Query contains forbidden keyword: drop",
        ),
        (
            "SELECT * FROM read_csv_auto('/tmp/secret.csv')",
            "Query contains forbidden function: read_csv_auto",
        ),
    ],
)
def test_query_endpoint_rejects_mutation_and_multistatement_sql_before_opening_db(
    gui_duckdb_client: TestClient,
    monkeypatch,
    query,
    expected_detail,
):
    opened_database = False

    def fail_if_opened(*_args, **_kwargs):
        nonlocal opened_database
        opened_database = True
        raise AssertionError("Rejected SQL should not open the database")

    monkeypatch.setattr(database_router, "open_database", fail_if_opened)

    response = gui_duckdb_client.get(
        "/api/database/query", params={"query": query, "limit": 1}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail
    assert opened_database is False


def test_query_endpoint_uses_read_only_duckdb_connection(
    gui_duckdb_client: TestClient,
    gui_duckdb_project,
    monkeypatch,
):
    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    read_only_values = []

    def recording_open_database(path, *, read_only=False):
        read_only_values.append(read_only)
        return open_database(path, read_only=read_only)

    monkeypatch.setattr(database_router, "open_database", recording_open_database)

    with open_database(db_path, read_only=True):
        response = gui_duckdb_client.get(
            "/api/database/query",
            params={"query": "SELECT 1 AS value", "limit": 1},
        )

    assert response.status_code == 200, response.text
    assert response.json()["rows"] == [{"value": 1}]
    assert read_only_values == [True]
