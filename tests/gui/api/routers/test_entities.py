"""Regression tests for entity routes on DuckDB projects."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

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
