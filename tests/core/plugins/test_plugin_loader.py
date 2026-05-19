"""Tests for PluginLoader adapter methods."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from niamoto.core.plugins.exceptions import PluginLoadError
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


def test_load_plugin_module_removes_failed_import_from_sys_modules(tmp_path):
    plugin_file = tmp_path / "bad_plugin.py"
    plugin_file.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    module_name = "plugins.bad_plugin_failure"
    sys.modules.pop(module_name, None)

    loader = PluginLoader()

    with pytest.raises(PluginLoadError):
        loader._load_plugin_module(plugin_file, module_name)

    assert module_name not in sys.modules
