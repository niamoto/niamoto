"""Regression tests for recipe routes on DuckDB projects."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import BaseModel

from niamoto.core.plugins.base import PluginType
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


def test_recipes_widgets_lists_all_core_widget_modules():
    client = TestClient(create_app())

    response = client.get("/api/recipes/widgets")

    assert response.status_code == 200, response.text
    widget_names = {widget["name"] for widget in response.json()}
    assert {
        "diverging_bar_plot",
        "hierarchical_nav_widget",
        "raw_data_widget",
        "summary_stats",
        "table_view",
    }.issubset(widget_names)


def test_save_recipe_rejects_missing_required_plugin_params(monkeypatch, tmp_path):
    class RequiredTransformerParams(BaseModel):
        source: str

    class RequiredTransformer:
        param_schema = RequiredTransformerParams

    class RequiredWidgetParams(BaseModel):
        value_field: str

    class RequiredWidget:
        param_schema = RequiredWidgetParams

    def fake_get_plugin(name, plugin_type):
        if plugin_type == PluginType.TRANSFORMER and name == "required_transformer":
            return RequiredTransformer
        if plugin_type == PluginType.WIDGET and name == "required_widget":
            return RequiredWidget
        raise KeyError(name)

    saved_transform_configs = []
    saved_export_configs = []
    monkeypatch.setattr(
        recipes.PluginRegistry, "get_plugin", staticmethod(fake_get_plugin)
    )
    monkeypatch.setattr(recipes, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        recipes,
        "save_transform_config",
        lambda _work_dir, config: saved_transform_configs.append(config),
    )
    monkeypatch.setattr(
        recipes,
        "save_export_config",
        lambda _work_dir, config: saved_export_configs.append(config),
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/recipes/save",
        json={
            "group_by": "taxons",
            "recipe": {
                "widget_id": "bad_widget",
                "transformer": {"plugin": "required_transformer", "params": {}},
                "widget": {"plugin": "required_widget", "params": {}},
            },
        },
    )

    assert response.status_code == 400, response.text
    assert "transformer.params.source" in response.text
    assert "widget.params.value_field" in response.text
    assert saved_transform_configs == []
    assert saved_export_configs == []


def test_save_recipe_does_not_write_transform_when_export_save_fails(
    monkeypatch, tmp_path
):
    class RecipeTransformer:
        param_schema = None

    class RecipeWidget:
        param_schema = None

    def fake_get_plugin(name, plugin_type):
        if plugin_type == PluginType.TRANSFORMER and name == "field_aggregator":
            return RecipeTransformer
        if plugin_type == PluginType.WIDGET and name == "bar_plot":
            return RecipeWidget
        raise KeyError(name)

    saved_transform_configs = []
    monkeypatch.setattr(
        recipes.PluginRegistry, "get_plugin", staticmethod(fake_get_plugin)
    )
    monkeypatch.setattr(recipes, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        recipes,
        "load_transform_config",
        lambda _work_dir: [{"group_by": "taxons", "sources": [], "widgets_data": {}}],
    )
    monkeypatch.setattr(
        recipes,
        "load_export_config",
        lambda _work_dir: {"exports": []},
    )
    monkeypatch.setattr(
        recipes,
        "save_transform_config",
        lambda _work_dir, config: saved_transform_configs.append(config),
    )

    def fail_save_export_config(_work_dir, _config):
        raise OSError("simulated export save failure")

    monkeypatch.setattr(recipes, "save_export_config", fail_save_export_config)

    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.post(
        "/api/recipes/save",
        json={
            "group_by": "taxons",
            "recipe": {
                "widget_id": "richness",
                "transformer": {"plugin": "field_aggregator", "params": {}},
                "widget": {"plugin": "bar_plot", "params": {}},
            },
        },
    )

    assert response.status_code == 500
    assert saved_transform_configs == []


def test_delete_recipe_removes_widget_only_from_html_page_exporter(
    monkeypatch, tmp_path
):
    transform_config = [
        {"group_by": "taxons", "widgets_data": {"alpha": {"plugin": "stats"}}}
    ]
    export_config = {
        "exports": [
            {
                "name": "web_pages",
                "exporter": "html_page_exporter",
                "groups": [
                    {
                        "group_by": "taxons",
                        "widgets": [{"plugin": "chart_widget", "data_source": "alpha"}],
                    }
                ],
            },
            {
                "name": "json_api",
                "exporter": "json_api_exporter",
                "groups": [
                    {
                        "group_by": "taxons",
                        "widgets": [{"plugin": "json_widget", "data_source": "alpha"}],
                    }
                ],
            },
        ]
    }
    saved_transform_configs = []
    saved_export_configs = []

    monkeypatch.setattr(recipes, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        recipes, "load_transform_config", lambda _work_dir: transform_config
    )
    monkeypatch.setattr(recipes, "load_export_config", lambda _work_dir: export_config)
    monkeypatch.setattr(
        recipes,
        "save_transform_config",
        lambda _work_dir, config: saved_transform_configs.append(config),
    )
    monkeypatch.setattr(
        recipes,
        "save_export_config",
        lambda _work_dir, config: saved_export_configs.append(config),
    )

    client = TestClient(create_app())
    response = client.delete("/api/recipes/taxons/alpha")

    assert response.status_code == 200, response.text
    assert "alpha" not in saved_transform_configs[0][0]["widgets_data"]
    saved_exports = saved_export_configs[0]["exports"]
    assert saved_exports[0]["groups"][0]["widgets"] == []
    assert saved_exports[1]["groups"][0]["widgets"] == [
        {"plugin": "json_widget", "data_source": "alpha"}
    ]


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
