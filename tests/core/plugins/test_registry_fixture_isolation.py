"""Regression tests for plugin registry test fixtures."""

from niamoto.core.plugins.base import Plugin, PluginType
from niamoto.core.plugins.registry import PluginRegistry


LEAK_PLUGIN_NAME = "fixture_metadata_leak_probe"


class FixtureMetadataProbePlugin(Plugin):
    """Tiny plugin class used to probe fixture metadata isolation."""

    type = PluginType.TRANSFORMER

    def validate_config(self, config):
        return config


def test_clear_registry_fixture_restores_metadata_after_test(clear_registry):
    PluginRegistry.register_plugin(
        LEAK_PLUGIN_NAME,
        FixtureMetadataProbePlugin,
        metadata={"source": "clear_registry_fixture_test"},
    )

    assert PluginRegistry.get_plugin_metadata(LEAK_PLUGIN_NAME) == {
        "source": "clear_registry_fixture_test"
    }


def test_clear_registry_fixture_does_not_leak_registered_metadata():
    assert PluginRegistry.get_plugin_metadata(LEAK_PLUGIN_NAME) == {}
