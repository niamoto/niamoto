"""Tests for plugin registry API routes."""

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import PluginType, WidgetPlugin
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import plugins as plugins_router


class DummyWidget(WidgetPlugin):
    """Dummy widget used for plugin route tests."""

    class Params(BaseModel):
        title: str = "Demo"

    param_schema = Params

    def render(self, data, params):
        return "<div></div>"


class RequiredParamWidget(WidgetPlugin):
    """Widget with a required parameter for compatibility checks."""

    class Params(BaseModel):
        title: str

    param_schema = Params

    def render(self, data, params):
        return "<div></div>"


class ConfigModelWidget(WidgetPlugin):
    """Widget exposing only a config_model schema."""

    class ConfigModel(BaseModel):
        enabled: bool = True

    param_schema = None
    config_model = ConfigModel

    def render(self, data, params):
        return "<div></div>"


class NoParamWidget(WidgetPlugin):
    """Widget without configurable parameters."""

    param_schema = None
    config_model = None

    def render(self, data, params):
        return "<div></div>"


class MislabeledWidget(WidgetPlugin):
    """Widget whose class metadata disagrees with registry metadata."""

    type = PluginType.TRANSFORMER

    def render(self, data, params):
        return "<div></div>"


class CategorizedWidget(WidgetPlugin):
    """Widget whose module path maps to the visualization category."""

    __module__ = "niamoto.core.plugins.widgets.categorized_widget"

    def render(self, data, params):
        return "<div></div>"


class UiMetadataWidget(WidgetPlugin):
    """Widget exposing UI metadata through Pydantic json_schema_extra."""

    class Params(BaseModel):
        field: str = Field(
            default="height",
            json_schema_extra={"ui:widget": "field-select"},
        )

    param_schema = Params

    def render(self, data, params):
        return "<div></div>"


def test_check_compatibility_rejects_unknown_plugin(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        client = TestClient(create_app())

        response = client.post(
            "/api/plugins/check-compatibility",
            json={"plugin_id": "missing_plugin", "source_data": {"type": "dataframe"}},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Plugin 'missing_plugin' not found"
    finally:
        PluginRegistry.clear()


def test_check_compatibility_accepts_known_plugin(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin("dummy_widget", DummyWidget, PluginType.WIDGET)
        client = TestClient(create_app())

        response = client.post(
            "/api/plugins/check-compatibility",
            json={"plugin_id": "dummy_widget", "source_data": {"type": "dataframe"}},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["compatible"] is True
        assert (
            payload["reason"]
            == "Plugin 'dummy_widget' accepts the provided source data."
        )
    finally:
        PluginRegistry.clear()


def test_check_compatibility_rejects_invalid_plugin_config(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin(
            "required_param_widget", RequiredParamWidget, PluginType.WIDGET
        )
        client = TestClient(create_app())

        response = client.post(
            "/api/plugins/check-compatibility",
            json={
                "plugin_id": "required_param_widget",
                "source_data": {"type": "dataframe"},
                "config": {},
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["compatible"] is False
        assert "Plugin config is invalid" in payload["reason"]
        assert "title" in payload["reason"]
    finally:
        PluginRegistry.clear()


def test_check_compatibility_rejects_missing_source_type(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin("dummy_widget", DummyWidget, PluginType.WIDGET)
        client = TestClient(create_app())

        response = client.post(
            "/api/plugins/check-compatibility",
            json={"plugin_id": "dummy_widget", "source_data": {}},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["compatible"] is False
        assert "source_data.type is required" in payload["reason"]
    finally:
        PluginRegistry.clear()


def test_get_plugin_uses_registry_type_when_class_type_disagrees(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin(
            "mislabeled_widget", MislabeledWidget, PluginType.WIDGET
        )
        client = TestClient(create_app())

        response = client.get("/api/plugins/mislabeled_widget")

        assert response.status_code == 200
        payload = response.json()
        assert payload["type"] == "widget"
        assert payload["output_format"] == "html"
    finally:
        PluginRegistry.clear()


def test_list_plugins_uses_registry_type_when_class_type_disagrees(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin(
            "mislabeled_widget", MislabeledWidget, PluginType.WIDGET
        )
        client = TestClient(create_app())

        response = client.get("/api/plugins/")

        assert response.status_code == 200
        payload = response.json()
        plugin = next(item for item in payload if item["id"] == "mislabeled_widget")
        assert plugin["type"] == "widget"
        assert plugin["output_format"] == "html"
    finally:
        PluginRegistry.clear()


def test_list_plugins_uses_top_level_ui_widget_metadata(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin(
            "ui_metadata_widget", UiMetadataWidget, PluginType.WIDGET
        )
        client = TestClient(create_app())

        response = client.get("/api/plugins/")

        assert response.status_code == 200
        payload = response.json()
        plugin = next(item for item in payload if item["id"] == "ui_metadata_widget")
        field_param = next(
            item for item in plugin["parameters_schema"] if item["name"] == "field"
        )
        assert field_param["type"] == "field-select"
    finally:
        PluginRegistry.clear()


def test_list_categories_returns_registered_plugin_categories(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin(
            "categorized_widget", CategorizedWidget, PluginType.WIDGET
        )
        response = TestClient(create_app()).get("/api/plugins/categories/list")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["categories"] == ["visualization"]
        assert payload["count"] == 1
    finally:
        PluginRegistry.clear()


def test_list_categories_returns_empty_registry(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        response = TestClient(create_app()).get("/api/plugins/categories/list")

        assert response.status_code == 200, response.text
        assert response.json() == {"categories": [], "count": 0}
    finally:
        PluginRegistry.clear()


def test_list_plugin_types_route_is_not_shadowed(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        response = TestClient(create_app()).get("/api/plugins/types/list")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["types"] == [plugin_type.value for plugin_type in PluginType]
        assert payload["count"] == len(PluginType)
    finally:
        PluginRegistry.clear()


def test_get_plugin_json_schema_returns_registered_plugin_schema(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin("dummy_widget", DummyWidget, PluginType.WIDGET)
        response = TestClient(create_app()).get("/api/plugins/dummy_widget/schema")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["plugin_id"] == "dummy_widget"
        assert payload["plugin_type"] == "widget"
        assert payload["has_params"] is True
        assert "schema" in payload
    finally:
        PluginRegistry.clear()


def test_get_plugin_json_schema_uses_config_model_fallback(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin(
            "config_model_widget", ConfigModelWidget, PluginType.WIDGET
        )
        response = TestClient(create_app()).get(
            "/api/plugins/config_model_widget/schema"
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["plugin_id"] == "config_model_widget"
        assert payload["plugin_type"] == "widget"
        assert payload["has_params"] is True
        assert "enabled" in payload["schema"]["properties"]
    finally:
        PluginRegistry.clear()


def test_get_plugin_json_schema_reports_plugin_without_params(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        PluginRegistry.register_plugin(
            "no_param_widget", NoParamWidget, PluginType.WIDGET
        )
        response = TestClient(create_app()).get("/api/plugins/no_param_widget/schema")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["plugin_id"] == "no_param_widget"
        assert payload["plugin_type"] == "widget"
        assert payload["has_params"] is False
        assert payload["message"] == "This plugin does not have configurable parameters"
    finally:
        PluginRegistry.clear()


def test_get_plugin_json_schema_rejects_unknown_plugin(monkeypatch):
    monkeypatch.setattr(plugins_router, "load_all_plugins", lambda: None)
    PluginRegistry.clear()
    try:
        response = TestClient(create_app()).get("/api/plugins/missing/schema")

        assert response.status_code == 404
        assert response.json()["detail"] == "Plugin 'missing' not found"
    finally:
        PluginRegistry.clear()
