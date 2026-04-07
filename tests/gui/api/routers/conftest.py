"""Shared fixtures for GUI router tests backed by a real DuckDB project."""

from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api import context
from niamoto.gui.api.app import create_app


@pytest.fixture
def gui_duckdb_project(tmp_path: Path) -> Path:
    """Create a minimal Niamoto project with a DuckDB database for GUI API tests."""

    work_dir = tmp_path / "gui-duckdb-project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "connector": {"type": "csv"},
                        }
                    },
                    "references": {
                        "taxons": {
                            "kind": "hierarchical",
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE dataset_occurrences (
                id INTEGER,
                taxon_id INTEGER,
                count INTEGER,
                locality VARCHAR
            )
            """
        )
        conn.execute(
            """
            INSERT INTO dataset_occurrences VALUES
                (1, 101, 3, 'Aoupinié'),
                (2, 101, 5, 'Aoupinié'),
                (3, 202, 1, 'Tiwaka')
            """
        )

        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id INTEGER,
                full_name VARCHAR,
                parent_id INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (101, 'Araucaria columnaris', NULL),
                (202, 'Niaouli test', 101)
            """
        )

        conn.execute(
            """
            CREATE VIEW occurrences_by_taxon AS
            SELECT taxon_id, SUM(count) AS total_count
            FROM dataset_occurrences
            GROUP BY taxon_id
            """
        )
    finally:
        conn.close()

    return work_dir


@pytest.fixture
def gui_duckdb_context(gui_duckdb_project: Path):
    """Point GUI API context to the temporary DuckDB project."""

    with patch.object(context, "_working_directory", gui_duckdb_project):
        yield gui_duckdb_project


@pytest.fixture
def gui_duckdb_client(gui_duckdb_context: Path) -> TestClient:
    """Create a TestClient bound to the temporary DuckDB project."""

    return TestClient(create_app())
