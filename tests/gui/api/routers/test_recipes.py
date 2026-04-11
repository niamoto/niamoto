"""Regression tests for recipe routes on DuckDB projects."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from niamoto.gui.api.routers import recipes
from niamoto.gui.api.routers.recipes import SourceInfo


def test_recipes_sources_use_read_only_duckdb_connections(
    gui_duckdb_client: TestClient,
):
    """Recipe source listing should not open DuckDB in write mode."""

    with patch(
        "niamoto.gui.api.routers.recipes.open_database",
        wraps=recipes.open_database,
    ) as open_database_mock:
        response = gui_duckdb_client.get("/api/recipes/sources/taxons")

    assert response.status_code == 200, response.text
    assert open_database_mock.call_args is not None
    assert open_database_mock.call_args.kwargs.get("read_only") is True


def test_recipes_source_columns_use_read_only_duckdb_connections(
    gui_duckdb_client: TestClient,
):
    """Recipe source column inspection should not open DuckDB in write mode."""

    with (
        patch(
            "niamoto.gui.api.routers.recipes.open_database",
            wraps=recipes.open_database,
        ) as open_database_mock,
        patch(
            "niamoto.gui.api.routers.recipes._get_all_sources",
            return_value=[
                SourceInfo(
                    type="dataset",
                    name="plot_stats",
                    table_name="dataset_occurrences",
                    columns=["id", "count"],
                    transformers=[],
                )
            ],
        ),
        patch(
            "niamoto.gui.api.routers.recipes._build_column_tree",
            return_value=[],
        ),
    ):
        response = gui_duckdb_client.get(
            "/api/recipes/sources/taxons/plot_stats/columns"
        )

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["source_name"] == "plot_stats"
    assert payload["table_name"] == "dataset_occurrences"
    assert open_database_mock.call_args is not None
    assert open_database_mock.call_args.kwargs.get("read_only") is True


def test_recipes_source_columns_fall_back_to_registry_source_outside_group(
    gui_duckdb_client: TestClient,
):
    """Column lookup should still work for valid registry sources outside transform.yml."""

    with (
        patch(
            "niamoto.gui.api.routers.recipes._get_all_sources",
            return_value=[],
        ),
        patch(
            "niamoto.gui.api.routers.recipes._get_registry_source",
            return_value=SourceInfo(
                type="dataset",
                name="occurrences",
                table_name="dataset_occurrences",
                columns=["id", "count", "locality"],
                transformers=[],
            ),
        ),
        patch(
            "niamoto.gui.api.routers.recipes._build_column_tree",
            return_value=[],
        ),
    ):
        response = gui_duckdb_client.get(
            "/api/recipes/sources/shapes/occurrences/columns"
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source_name"] == "occurrences"
    assert payload["table_name"] == "dataset_occurrences"
