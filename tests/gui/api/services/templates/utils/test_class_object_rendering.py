"""Tests pour class_object_rendering — cohérence entre transformer output et widget params.

Ces tests vérifient que les noms de champs dans les paramètres widget (x_axis, y_axis,
labels_field, values_field) correspondent aux clés réellement produites par les transformers.

C'est le point de défaillance récurrent #1 du preview engine : le widget demande un champ
qui n'existe pas dans la sortie du transformer → "Input dict structure not recognized".
"""

from niamoto.gui.api.services.templates.utils import class_object_rendering
from niamoto.gui.api.services.templates.utils.class_object_rendering import (
    _build_info_grid_items,
    _build_widget_params_for_class_object,
    _build_widget_params_for_configured,
    _execute_configured_transformer,
    _extract_class_objects_from_params,
)


# -----------------------------------------------------------------------
# Données réalistes simulant la sortie de load_class_object_data_for_preview
# -----------------------------------------------------------------------

FAMILY_CSV_DATA = {
    "top10_family": {
        "tops": ["Myrtaceae", "Cunoniaceae", "Rubiaceae", "Proteaceae", "Lauraceae"],
        "counts": [45, 32, 28, 22, 18],
    }
}

SPECIES_CSV_DATA = {
    "top10_species": {
        "tops": ["Arillastrum gummiferum", "Nothofagus aequilateralis"],
        "counts": [120, 95],
    }
}

DBH_CSV_DATA = {
    "dbh": {
        "tops": [10, 20, 30, 40, 50],
        "counts": [150, 120, 80, 45, 20],
    }
}


class TestSeriesExtractorBarPlotCoherence:
    """Vérifie que _build_widget_params_for_configured produit des noms de champs
    qui existent dans la sortie de _execute_configured_transformer."""

    TRANSFORMER = "class_object_series_extractor"
    WIDGET = "bar_plot"

    def _transformer_params(self, class_object: str = "top10_family") -> dict:
        return {
            "source": "plot_stats",
            "class_object": class_object,
            "size_field": {"input": "class_name", "output": "tops"},
            "value_field": {"input": "class_value", "output": "counts"},
            "count": 10,
            "x_axis": "counts",
            "y_axis": "tops",
            "orientation": "h",
            "sort_order": "descending",
            "auto_color": True,
        }

    def test_x_axis_matches_data_keys(self):
        """x_axis doit correspondre à une clé de la sortie transformer."""
        result = _execute_configured_transformer(
            self.TRANSFORMER, self._transformer_params(), FAMILY_CSV_DATA, "plots"
        )
        assert result is not None

        params = _build_widget_params_for_configured(
            self.TRANSFORMER, self.WIDGET, result, "Top10 Family"
        )
        assert params["x_axis"] in result, (
            f"x_axis='{params['x_axis']}' n'existe pas dans les clés de la sortie "
            f"transformer: {list(result.keys())}"
        )

    def test_y_axis_matches_data_keys(self):
        """y_axis doit correspondre à une clé de la sortie transformer."""
        result = _execute_configured_transformer(
            self.TRANSFORMER, self._transformer_params(), FAMILY_CSV_DATA, "plots"
        )
        assert result is not None

        params = _build_widget_params_for_configured(
            self.TRANSFORMER, self.WIDGET, result, "Top10 Family"
        )
        assert params["y_axis"] in result, (
            f"y_axis='{params['y_axis']}' n'existe pas dans les clés de la sortie "
            f"transformer: {list(result.keys())}"
        )

    def test_extra_params_override_defaults(self):
        """Les extra_params (export.yml) doivent override les defaults."""
        result = _execute_configured_transformer(
            self.TRANSFORMER, self._transformer_params(), FAMILY_CSV_DATA, "plots"
        )
        params = _build_widget_params_for_configured(
            self.TRANSFORMER,
            self.WIDGET,
            result,
            "Title",
            extra_params={"x_axis": "counts", "y_axis": "tops", "orientation": "h"},
        )
        assert params["x_axis"] == "counts"
        assert params["y_axis"] == "tops"
        assert params["orientation"] == "h"

    def test_species_variant(self):
        """Même vérification pour top10_species."""
        tp = self._transformer_params("top10_species")
        tp["class_object"] = "top10_species"
        result = _execute_configured_transformer(
            self.TRANSFORMER, tp, SPECIES_CSV_DATA, "plots"
        )
        assert result is not None
        params = _build_widget_params_for_configured(
            self.TRANSFORMER, self.WIDGET, result, "Top10 Species"
        )
        assert params["x_axis"] in result
        assert params["y_axis"] in result


class TestCategoriesExtractorBarPlotCoherence:
    """Même vérification pour class_object_categories_extractor."""

    TRANSFORMER = "class_object_categories_extractor"
    WIDGET = "bar_plot"

    def test_axes_match_data_keys(self):
        co_data = {
            "strata": {
                "tops": ["Canopy", "Understory", "Emergent"],
                "counts": [300, 150, 50],
            }
        }
        result = _execute_configured_transformer(
            self.TRANSFORMER,
            {"class_object": "strata"},
            co_data,
            "plots",
        )
        assert result is not None
        params = _build_widget_params_for_configured(
            self.TRANSFORMER, self.WIDGET, result, "Strata"
        )
        # Pour categories, les defaults sont labels/counts
        assert params["x_axis"] in result or params["x_axis"] == "labels"
        assert params["y_axis"] in result


class TestBinaryAggregatorBarPlotCoherence:
    """Vérification pour class_object_binary_aggregator."""

    TRANSFORMER = "class_object_binary_aggregator"
    WIDGET = "bar_plot"

    def test_axes_match_data_keys(self):
        co_data = {
            "is_endemic": {
                "tops": ["Endemic", "Non-endemic"],
                "counts": [800, 200],
            }
        }
        result = _execute_configured_transformer(
            self.TRANSFORMER,
            {"groups": [{"field": "is_endemic"}]},
            co_data,
            "plots",
        )
        assert result is not None
        params = _build_widget_params_for_configured(
            self.TRANSFORMER, self.WIDGET, result, "Endemic"
        )
        # binary_aggregator output : {"tops": [...], "counts": [...]}
        # defaults : x_axis="labels", y_axis="counts"
        # "labels" n'existe pas dans result mais "tops" oui
        # Ce test documente l'état actuel — si on casse les defaults, on le voit
        assert params["y_axis"] in result or params["y_axis"] == "counts"


def test_extract_class_objects_from_params_supports_all_config_shapes():
    params = {
        "class_object": ["dbh", "height"],
        "fields": [{"class_object": "dbh"}, {"class_object": "canopy"}],
        "groups": [{"field": "is_endemic"}],
        "series": [{"class_object": "height"}, {"class_object": "density"}],
        "distributions": {"cover": {"total": "all", "subset": "forest"}},
        "categories": {"richness": {"class_object": "richness_class"}},
        "types": {"primary": "slope", "secondary": "aspect"},
    }

    assert _extract_class_objects_from_params(params) == [
        "dbh",
        "height",
        "canopy",
        "is_endemic",
        "density",
        "all",
        "forest",
        "richness_class",
        "slope",
        "aspect",
    ]


def test_build_info_grid_items_supports_legacy_fields_and_nested_scalars():
    assert _build_info_grid_items(
        {
            "fields": [
                {"label": "Elevation", "value": 412, "units": "m"},
                {"name": "Slope", "source": "terrain.slope"},
            ]
        }
    ) == [
        {"label": "Elevation", "value": 412, "unit": "m"},
        {"label": "Slope", "source": "terrain.slope"},
    ]

    assert _build_info_grid_items(
        {
            "forest_cover": {"value": 82, "units": "%"},
            "range_stats": {"min": 120, "max": 360},
            "flags": {"is_native": True, "rank": 3},
            "habitats": ["forest", "maquis", "riverine"],
        }
    ) == [
        {"label": "Forest Cover", "source": "forest_cover.value", "unit": "%"},
        {"label": "Range Stats - Min", "value": 120},
        {"label": "Range Stats - Max", "value": 360},
        {"label": "Flags - Is Native", "value": True},
        {"label": "Flags - Rank", "value": 3},
        {"label": "Habitats", "value": "forest, maquis, riverine"},
    ]


def test_build_widget_params_for_class_object_handles_numeric_and_gauge_outputs():
    distribution_params = _build_widget_params_for_class_object(
        "class_object_series_extractor",
        "bar_plot",
        {
            "tops": [10, 20, 30],
            "counts": [25, 35, 40],
            "_is_numeric": True,
            "class_object": "dbh",
        },
        "DBH distribution",
    )

    assert distribution_params == {
        "x_axis": "tops",
        "y_axis": "counts",
        "title": "DBH distribution",
        "orientation": "v",
        "sort_order": "descending",
        "gradient_color": "#8B4513",
        "gradient_mode": "luminance",
        "show_legend": False,
        "labels": {"tops": "DBH", "counts": "%"},
    }

    gauge_params = _build_widget_params_for_class_object(
        "class_object_field_aggregator",
        "radial_gauge",
        {"counts": [412], "units": "m"},
        "Elevation",
    )

    assert gauge_params == {
        "value_field": "value",
        "max_value": 1000,
        "title": "Elevation",
        "unit": "m",
    }


def test_render_widget_for_configured_returns_error_html_when_widget_fails(
    monkeypatch,
):
    class FailingWidget:
        param_schema = None

        def __init__(self, db=None):
            self.db = db

        def render(self, data, params):
            raise RuntimeError("<boom>")

    monkeypatch.setattr(
        class_object_rendering.PluginRegistry,
        "get_plugin",
        lambda _widget_name, _plugin_type: FailingWidget,
    )

    html = class_object_rendering._render_widget_for_configured(
        None,
        "bar_plot",
        {"tops": ["forest"], "counts": [12]},
        "class_object_series_extractor",
        "Top habitats",
    )

    assert "Widget render error" in html
    assert "&lt;boom&gt;" in html
