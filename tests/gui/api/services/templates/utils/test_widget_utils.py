from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.gui.api.services.templates.utils import widget_utils


def test_parse_dynamic_template_id_supports_regular_transformers():
    widget_utils._transformer_names = None
    widget_utils._widget_names = None
    PluginLoader().load_plugins_with_cascade()

    assert "binned_distribution" in widget_utils._get_transformer_names()
    assert widget_utils.parse_dynamic_template_id(
        "basal_area_binned_distribution_bar_plot"
    ) == {
        "column": "basal_area",
        "transformer": "binned_distribution",
        "widget": "bar_plot",
    }
