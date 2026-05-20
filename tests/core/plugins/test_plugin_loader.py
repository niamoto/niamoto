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


def test_reload_plugin_keeps_previous_registration_when_import_fails(tmp_path):
    PluginRegistry.clear()
    plugin_file = tmp_path / "reloadable_plugin.py"
    plugin_file.write_text(
        "from niamoto.core.plugins.base import Plugin, PluginType, register\n"
        "@register('reloadable_plugin', PluginType.TRANSFORMER)\n"
        "class ReloadablePlugin(Plugin):\n"
        "    type = PluginType.TRANSFORMER\n",
        encoding="utf-8",
    )
    module_name = "reloadable_plugin_module"
    sys.modules.pop(module_name, None)

    loader = PluginLoader()
    loader._load_plugin_module(plugin_file, module_name)
    loader.loaded_plugins.add(module_name)
    loader.plugin_paths[module_name] = str(plugin_file)
    original_plugin = PluginRegistry.get_plugin(
        "reloadable_plugin", PluginType.TRANSFORMER
    )

    plugin_file.write_text("raise RuntimeError('broken reload')\n", encoding="utf-8")

    with pytest.raises(PluginLoadError):
        loader.reload_plugin(module_name)

    assert module_name in loader.loaded_plugins
    assert (
        PluginRegistry.get_plugin("reloadable_plugin", PluginType.TRANSFORMER)
        is original_plugin
    )

    PluginRegistry.clear()
    sys.modules.pop(module_name, None)


def test_reload_plugin_does_not_unregister_before_probe_succeeds(tmp_path, monkeypatch):
    PluginRegistry.clear()
    plugin_file = tmp_path / "reloadable_probe_plugin.py"
    plugin_file.write_text(
        "from niamoto.core.plugins.base import Plugin, PluginType, register\n"
        "@register('reloadable_probe_plugin', PluginType.TRANSFORMER)\n"
        "class ReloadableProbePlugin(Plugin):\n"
        "    type = PluginType.TRANSFORMER\n",
        encoding="utf-8",
    )
    module_name = "reloadable_probe_plugin_module"
    sys.modules.pop(module_name, None)

    loader = PluginLoader()
    loader._load_plugin_module(plugin_file, module_name)
    loader.loaded_plugins.add(module_name)
    loader.plugin_paths[module_name] = str(plugin_file)

    plugin_file.write_text("raise RuntimeError('broken probe')\n", encoding="utf-8")
    removed: list[tuple[str, PluginType]] = []
    original_remove_plugin = PluginRegistry.remove_plugin

    def track_remove_plugin(name, plugin_type):
        removed.append((name, plugin_type))
        return original_remove_plugin(name, plugin_type)

    monkeypatch.setattr(PluginRegistry, "remove_plugin", track_remove_plugin)

    with pytest.raises(PluginLoadError):
        loader.reload_plugin(module_name)

    assert removed == []
    assert PluginRegistry.has_plugin("reloadable_probe_plugin", PluginType.TRANSFORMER)

    PluginRegistry.clear()
    sys.modules.pop(module_name, None)


def test_discover_plugins_does_not_leave_decorated_plugin_registered(
    tmp_path, monkeypatch
):
    PluginRegistry.clear()
    plugin_root = tmp_path / "plugins"
    transformers_dir = plugin_root / "transformers"
    transformers_dir.mkdir(parents=True)
    (plugin_root / "__init__.py").write_text("", encoding="utf-8")
    (transformers_dir / "__init__.py").write_text("", encoding="utf-8")
    plugin_file = transformers_dir / "decorated_temp.py"
    plugin_file.write_text(
        "from niamoto.core.plugins.base import Plugin, PluginType, register\n"
        "@register('decorated_temp', PluginType.TRANSFORMER)\n"
        "class DecoratedTemp(Plugin):\n"
        "    type = PluginType.TRANSFORMER\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("plugins.transformers.decorated_temp", None)
    loader = PluginLoader()
    monkeypatch.setattr(
        loader,
        "_get_module_name",
        lambda _file, _is_core: "plugins.transformers.decorated_temp",
    )

    discovered = loader.discover_plugins(plugin_root)

    assert {
        "path": str(plugin_file),
        "module": "plugins.transformers.decorated_temp",
        "name": "decorated_temp",
        "type": "transformer",
    } in discovered
    assert not PluginRegistry.has_plugin("decorated_temp", PluginType.TRANSFORMER)
    assert "plugins.transformers.decorated_temp" not in sys.modules
