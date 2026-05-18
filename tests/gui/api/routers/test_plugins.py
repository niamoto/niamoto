"""Tests for plugin registry API routes."""

from fastapi.testclient import TestClient

from niamoto.core.plugins.base import PluginType, WidgetPlugin
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import plugins as plugins_router


class DummyWidget(WidgetPlugin):
    """Dummy widget used for plugin route tests."""

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
