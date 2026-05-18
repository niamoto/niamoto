"""Regression tests for recipe routes on DuckDB projects."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
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


def test_recipes_sources_add_dataset_fallback_when_only_reference_exists(
    gui_duckdb_client: TestClient,
):
    """Reference-only source lists should still include dataset fallback sources."""

    with (
        patch(
            "niamoto.gui.api.routers.recipes._get_all_sources",
            return_value=[
                SourceInfo(
                    type="reference",
                    name="taxons",
                    table_name="entity_taxons",
                    columns=["id", "full_name"],
                    transformers=[],
                )
            ],
        ),
        patch(
            "niamoto.gui.api.routers.recipes._get_all_dataset_entities",
            return_value=[
                ("occurrences", "dataset_occurrences", ["id", "taxon_id", "count"])
            ],
        ),
    ):
        response = gui_duckdb_client.get("/api/recipes/sources/taxons")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [source["name"] for source in payload["sources"]] == [
        "taxons",
        "occurrences",
    ]
    assert [source["type"] for source in payload["sources"]] == [
        "reference",
        "dataset",
    ]


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


def test_recipes_source_columns_returns_all_database_columns(
    gui_duckdb_client: TestClient,
):
    with patch(
        "niamoto.gui.api.routers.recipes._get_all_sources",
        return_value=[
            SourceInfo(
                type="dataset",
                name="occurrences",
                table_name="dataset_occurrences",
                columns=[],
                transformers=[],
            )
        ],
    ):
        response = gui_duckdb_client.get(
            "/api/recipes/sources/taxons/occurrences/columns"
        )

    assert response.status_code == 200, response.text
    column_names = [column["name"] for column in response.json()["columns"]]
    assert "id" in column_names
    assert "taxon_id" in column_names
    assert "count" in column_names


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


def test_reorder_widgets_preserves_unresolved_widgets(monkeypatch, tmp_path):
    export_config = {
        "exports": [
            {
                "name": "web_pages",
                "groups": [
                    {
                        "group_by": "taxons",
                        "widgets": [
                            {
                                "plugin": "chart_widget",
                                "data_source": "alpha",
                                "layout": {"order": 0},
                            },
                            {
                                "plugin": "legacy_widget",
                                "title": "Unresolved legacy widget",
                                "layout": {"order": 1},
                            },
                            {
                                "plugin": "table_widget",
                                "data_source": "beta",
                                "layout": {"order": 2},
                            },
                        ],
                    }
                ],
            }
        ]
    }
    saved_configs = []

    monkeypatch.setattr(recipes, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(recipes, "load_export_config", lambda _work_dir: export_config)
    monkeypatch.setattr(
        recipes,
        "save_export_config",
        lambda _work_dir, config: saved_configs.append(config),
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/recipes/taxons/reorder",
        json={"widget_ids": ["beta", "alpha"]},
    )

    assert response.status_code == 200, response.text
    saved_widgets = saved_configs[0]["exports"][0]["groups"][0]["widgets"]
    assert [widget.get("data_source") for widget in saved_widgets] == [
        "beta",
        "alpha",
        None,
    ]
    assert saved_widgets[2]["plugin"] == "legacy_widget"
    assert [widget["layout"]["order"] for widget in saved_widgets] == [0, 1, 2]
