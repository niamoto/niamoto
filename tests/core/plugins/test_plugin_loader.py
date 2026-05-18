"""Tests for PluginLoader adapter methods."""

from __future__ import annotations

from types import SimpleNamespace

from niamoto.core.plugins.base import Plugin, PluginType
from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.core.plugins.registry import PluginRegistry


class AdapterPlugin(Plugin):
    type = PluginType.TRANSFORMER
    name = "adapter_plugin"


def test_register_plugin_uses_registry_argument_order(monkeypatch):
    PluginRegistry.clear()
    module = SimpleNamespace(AdapterPlugin=AdapterPlugin)
    monkeypatch.setattr(
        "niamoto.core.plugins.plugin_loader.importlib.import_module",
        lambda module_name: module,
    )

    loader = PluginLoader()
    loader.register_plugin("fake_plugin_module", "AdapterPlugin", "transformer")

    assert PluginRegistry.has_plugin("adapter_plugin", PluginType.TRANSFORMER)
    assert (
        PluginRegistry.get_plugin("adapter_plugin", PluginType.TRANSFORMER)
        is AdapterPlugin
    )
    assert "fake_plugin_module" in loader.loaded_plugins

    PluginRegistry.clear()
