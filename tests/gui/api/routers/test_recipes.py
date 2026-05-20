"""Regression tests for recipe routes on DuckDB projects."""

from copy import deepcopy
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import BaseModel

from niamoto.core.plugins.base import PluginType, WidgetPlugin
from niamoto.core.plugins.registry import PluginRegistry
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


def test_recipes_source_columns_expands_json_keys_from_multiple_rows(
    gui_duckdb_client: TestClient, gui_duckdb_project
):
    import duckdb

    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("CREATE TABLE dataset_json_source (id INTEGER, extra_data JSON)")
        conn.execute(
            """
            INSERT INTO dataset_json_source VALUES
                (1, '{"alpha": 1}'::JSON),
                (2, '{"beta": 2}'::JSON)
            """
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.recipes._get_all_sources",
        return_value=[
            SourceInfo(
                type="dataset",
                name="json_source",
                table_name="dataset_json_source",
                columns=[],
                transformers=[],
            )
        ],
    ):
        response = gui_duckdb_client.get(
            "/api/recipes/sources/taxons/json_source/columns"
        )

    assert response.status_code == 200, response.text
    extra_data = next(
        column
        for column in response.json()["columns"]
        if column["name"] == "extra_data"
    )
    assert [child["name"] for child in extra_data["children"]] == ["alpha", "beta"]


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


def test_recipes_source_columns_returns_csv_columns_without_database(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    imports_dir = work_dir / "imports"
    config_dir.mkdir(parents=True)
    imports_dir.mkdir()
    (config_dir / "transform.yml").write_text(
        """
- group_by: taxons
  sources:
    - name: plot_stats
      data: imports/plot_stats.csv
      grouping: taxons
      relation:
        plugin: direct_reference
        key: taxon_id
""",
        encoding="utf-8",
    )
    (imports_dir / "plot_stats.csv").write_text(
        "taxon_id;class_object;class_name;class_value\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(recipes, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(recipes, "get_database_path", lambda: None)

    response = TestClient(create_app()).get(
        "/api/recipes/sources/taxons/plot_stats/columns"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source_name"] == "plot_stats"
    assert payload["table_name"] is None
    assert [column["name"] for column in payload["columns"]] == [
        "taxon_id",
        "class_object",
        "class_name",
        "class_value",
    ]


def test_recipes_widgets_lists_all_core_widget_modules():
    PluginRegistry.clear()
    client = TestClient(create_app())

    try:
        response = client.get("/api/recipes/widgets")
    finally:
        recipes._ensure_plugins_loaded()

    assert response.status_code == 200, response.text
    widget_names = {widget["name"] for widget in response.json()}
    assert {
        "diverging_bar_plot",
        "hierarchical_nav_widget",
        "raw_data_widget",
        "summary_stats",
        "table_view",
    }.issubset(widget_names)


def test_recipes_widget_schema_loads_discovered_widget_module():
    PluginRegistry.clear()
    client = TestClient(create_app())

    try:
        response = client.get("/api/recipes/widget-schema/table_view")
    finally:
        recipes._ensure_plugins_loaded()

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["name"] == "table_view"
    assert "columns" in payload["params"]
    assert "max_rows" in payload["params"]


def test_recipes_widget_schema_includes_arbitrary_dict_params_and_following_fields():
    class DictParamWidget(WidgetPlugin):
        class Params(BaseModel):
            options: dict[str, Any] = {}
            title: str = "Title"

        param_schema = Params

        def render(self, data, params):
            return "<div></div>"

    PluginRegistry.clear()
    PluginRegistry.register_plugin(
        "dict_param_widget", DictParamWidget, PluginType.WIDGET
    )
    client = TestClient(create_app())

    try:
        response = client.get("/api/recipes/widget-schema/dict_param_widget")
    finally:
        recipes._ensure_plugins_loaded()

    assert response.status_code == 200, response.text
    params = response.json()["params"]
    assert params["options"]["type"] == "object"
    assert params["options"]["additional_properties_type"] == "any"
    assert params["title"]["type"] == "string"


def test_recipes_list_transformers_returns_registered_plugins():
    PluginRegistry.clear()
    client = TestClient(create_app())

    try:
        response = client.get("/api/recipes/transformers")
    finally:
        recipes._ensure_plugins_loaded()

    assert response.status_code == 200, response.text
    transformer_names = set(response.json())
    assert {
        "field_aggregator",
        "time_series_analysis",
        "geospatial_extractor",
    }.issubset(transformer_names)


def test_recipes_list_transformers_reports_registry_failures(monkeypatch):
    client = TestClient(create_app())

    monkeypatch.setattr(recipes, "_ensure_plugins_loaded", lambda: None)

    def fail_get_plugins(_plugin_type):
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(PluginRegistry, "get_plugins_by_type", fail_get_plugins)

    response = client.get("/api/recipes/transformers")

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to list transformers"


def test_recipes_transformer_schema_route_returns_plugin_params():
    client = TestClient(create_app())

    response = client.get("/api/recipes/transformer-schema/time_series_analysis")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["name"] == "time_series_analysis"
    assert {"source", "field", "fields", "time_field", "labels"}.issubset(
        payload["params"]
    )


def test_recipes_transformer_schema_route_rejects_unknown_plugin():
    response = TestClient(create_app()).get(
        "/api/recipes/transformer-schema/unknown_transformer"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Transformer 'unknown_transformer' not found"


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


def test_validate_recipe_rejects_duplicate_export_widget_id(monkeypatch, tmp_path):
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
        lambda _work_dir: {
            "exports": [
                {
                    "name": "web_pages",
                    "exporter": "html_page_exporter",
                    "groups": [
                        {
                            "group_by": "taxons",
                            "widgets": [
                                {"plugin": "bar_plot", "data_source": "richness"}
                            ],
                        }
                    ],
                }
            ]
        },
    )

    response = TestClient(create_app()).post(
        "/api/recipes/validate",
        json={
            "group_by": "taxons",
            "recipe": {
                "widget_id": "richness",
                "transformer": {"plugin": "field_aggregator", "params": {}},
                "widget": {"plugin": "bar_plot", "params": {}},
            },
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["valid"] is False
    assert {
        "field": "widget_id",
        "message": "Widget ID 'richness' already exists",
    } in payload["errors"]


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


def test_save_recipe_rolls_back_export_when_transform_save_fails(monkeypatch, tmp_path):
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

    original_export_config = {"exports": []}
    saved_export_configs = []
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
        lambda _work_dir: original_export_config,
    )

    def save_export_config(_work_dir, config):
        saved_export_configs.append(config)

    def fail_save_transform_config(_work_dir, _config):
        raise OSError("simulated transform save failure")

    monkeypatch.setattr(recipes, "save_export_config", save_export_config)
    monkeypatch.setattr(recipes, "save_transform_config", fail_save_transform_config)

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
    assert len(saved_export_configs) == 2
    assert (
        saved_export_configs[0]["exports"][0]["groups"][0]["widgets"][0]["data_source"]
        == "richness"
    )
    assert saved_export_configs[1] == {"exports": []}


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


def test_delete_recipe_does_not_write_transform_when_export_save_fails(
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
            }
        ]
    }
    saved_transform_configs = []

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

    def fail_save_export_config(_work_dir, _config):
        raise OSError("simulated export save failure")

    monkeypatch.setattr(recipes, "save_export_config", fail_save_export_config)

    response = TestClient(create_app(), raise_server_exceptions=False).delete(
        "/api/recipes/taxons/alpha"
    )

    assert response.status_code == 500
    assert saved_transform_configs == []


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


def test_reorder_widgets_leaves_non_web_exporters_unchanged(monkeypatch, tmp_path):
    json_widgets = [
        {"plugin": "json_widget", "data_source": "alpha", "layout": {"order": 10}},
        {"plugin": "json_widget", "data_source": "beta", "layout": {"order": 11}},
    ]
    export_config = {
        "exports": [
            {
                "name": "web_pages",
                "exporter": "html_page_exporter",
                "groups": [
                    {
                        "group_by": "taxons",
                        "widgets": [
                            {"plugin": "chart_widget", "data_source": "alpha"},
                            {"plugin": "table_widget", "data_source": "beta"},
                        ],
                    }
                ],
            },
            {
                "name": "json_api",
                "exporter": "json_api_exporter",
                "groups": [{"group_by": "taxons", "widgets": deepcopy(json_widgets)}],
            },
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

    response = TestClient(create_app()).post(
        "/api/recipes/taxons/reorder",
        json={"widget_ids": ["beta", "alpha"]},
    )

    assert response.status_code == 200, response.text
    saved_exports = saved_configs[0]["exports"]
    assert [
        widget["data_source"] for widget in saved_exports[0]["groups"][0]["widgets"]
    ] == ["beta", "alpha"]
    assert saved_exports[1]["groups"][0]["widgets"] == json_widgets
