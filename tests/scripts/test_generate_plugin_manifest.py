"""Tests for scripts/generate-plugin-manifest.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate-plugin-manifest.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("plugin_manifest", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["plugin_manifest"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_plugins_tree(tmp_path: Path) -> Path:
    """Create a minimal plugins tree with two registered classes."""
    root = tmp_path / "plugins"
    (root / "widgets").mkdir(parents=True)
    (root / "transformers").mkdir(parents=True)

    (root / "widgets" / "bar_plot.py").write_text(
        '''
from niamoto.core.plugins.base import PluginType, register, WidgetPlugin


@register("bar_plot", PluginType.WIDGET)
class BarPlotWidget(WidgetPlugin):
    """Widget to display a bar plot using Plotly.

    This second paragraph is ignored by the extractor.
    """
    pass
'''.lstrip()
    )

    (root / "transformers" / "top_ranking.py").write_text(
        '''
from niamoto.core.plugins.base import PluginType, register


@register("top_ranking", PluginType.TRANSFORMER)
class TopRanking:
    """Rank the top N values of a field."""
    pass
'''.lstrip()
    )

    # A file without any @register decorator — should be skipped silently.
    (root / "widgets" / "_helpers.py").write_text("def helper():\n    return 1\n")

    return root


def test_extracts_two_plugins(fake_plugins_tree: Path):
    module = _load_module()
    plugins = module.extract_plugins(fake_plugins_tree)

    assert len(plugins) == 2
    names = {p["name"] for p in plugins}
    assert names == {"bar_plot", "top_ranking"}


def test_output_shape(fake_plugins_tree: Path):
    module = _load_module()
    plugins = module.extract_plugins(fake_plugins_tree)

    bar_plot = next(p for p in plugins if p["name"] == "bar_plot")
    assert bar_plot == {
        "name": "bar_plot",
        "type": "widget",
        "body": "Widget to display a bar plot using Plotly.",
    }


def test_sorted_by_type_then_name(fake_plugins_tree: Path):
    module = _load_module()
    plugins = module.extract_plugins(fake_plugins_tree)

    # transformer comes before widget alphabetically
    assert [p["type"] for p in plugins] == ["transformer", "widget"]


def test_handles_missing_docstring(tmp_path: Path):
    root = tmp_path / "plugins"
    root.mkdir()
    (root / "nodoc.py").write_text(
        """
from niamoto.core.plugins.base import PluginType, register


@register("nodoc", PluginType.LOADER)
class NoDocLoader:
    pass
""".lstrip()
    )

    module = _load_module()
    plugins = module.extract_plugins(root)
    assert plugins == [{"name": "nodoc", "type": "loader", "body": ""}]


def test_type_fallback_from_class_attr(tmp_path: Path):
    """If @register is called without a type, fall back on the `type` class attr."""
    root = tmp_path / "plugins"
    root.mkdir()
    (root / "implicit.py").write_text(
        '''
from niamoto.core.plugins.base import PluginType, register


@register("implicit")
class ImplicitExporter:
    """An exporter declaring its type via class attribute."""
    type = PluginType.EXPORTER
'''.lstrip()
    )

    module = _load_module()
    plugins = module.extract_plugins(root)
    assert plugins[0]["type"] == "exporter"


def test_type_fallback_from_base_class(tmp_path: Path):
    """If neither @register nor class body specifies type, infer from base class name."""
    root = tmp_path / "plugins"
    root.mkdir()
    (root / "vercel.py").write_text(
        '''
from niamoto.core.plugins.base import DeployerPlugin, register


@register("vercel")
class VercelDeployer(DeployerPlugin):
    """Deploy static sites to Vercel via the Deployments API."""
    pass
'''.lstrip()
    )

    module = _load_module()
    plugins = module.extract_plugins(root)
    assert plugins == [
        {
            "name": "vercel",
            "type": "deployer",
            "body": "Deploy static sites to Vercel via the Deployments API.",
        }
    ]
