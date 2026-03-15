"""Tests for declarative widget registries and preprocessing adapters."""

import pytest

from niamoto.core.imports.data_analyzer import DataCategory, EnrichedColumnProfile
from niamoto.core.imports.widget_generator import WidgetGenerator
from niamoto.gui.api.services.preview_utils import (
    preprocess_data_for_widget,
)


# ---------------------------------------------------------------------------
# WIDGET_CONFIG_MAP
# ---------------------------------------------------------------------------


class TestWidgetConfigMap:
    """Validate WidgetGenerator.WIDGET_CONFIG_MAP completeness."""

    def test_all_entries_are_non_empty(self):
        for key, config in WidgetGenerator.WIDGET_CONFIG_MAP.items():
            assert isinstance(config, dict), f"{key} should be a dict"
            assert config, f"{key} should not be empty"

    def test_binned_distribution_bar_plot(self):
        cfg = WidgetGenerator.WIDGET_CONFIG_MAP[("binned_distribution", "bar_plot")]
        assert cfg["x_axis"] == "bin"
        assert cfg["y_axis"] == "count"
        assert "transform" in cfg
        assert "field_mapping" in cfg

    def test_statistical_summary_radial_gauge(self):
        cfg = WidgetGenerator.WIDGET_CONFIG_MAP[("statistical_summary", "radial_gauge")]
        assert cfg["value_field"] == "mean"

    def test_top_ranking_bar_plot(self):
        cfg = WidgetGenerator.WIDGET_CONFIG_MAP[("top_ranking", "bar_plot")]
        assert cfg["x_axis"] == "counts"
        assert cfg["y_axis"] == "tops"
        assert cfg["orientation"] == "h"

    def test_binary_counter_donut_chart(self):
        cfg = WidgetGenerator.WIDGET_CONFIG_MAP[("binary_counter", "donut_chart")]
        assert "labels_field" in cfg
        assert "values_field" in cfg

    def test_all_donut_entries_have_label_value_fields(self):
        for (transformer, widget), cfg in WidgetGenerator.WIDGET_CONFIG_MAP.items():
            if widget == "donut_chart":
                assert "labels_field" in cfg, (
                    f"({transformer}, {widget}) missing labels_field"
                )
                assert "values_field" in cfg, (
                    f"({transformer}, {widget}) missing values_field"
                )

    def test_all_bar_plot_entries_have_axes(self):
        for (transformer, widget), cfg in WidgetGenerator.WIDGET_CONFIG_MAP.items():
            if widget == "bar_plot":
                assert "x_axis" in cfg, f"({transformer}, {widget}) missing x_axis"
                assert "y_axis" in cfg, f"({transformer}, {widget}) missing y_axis"

    def test_generate_widget_params_returns_map_entry(self):
        gen = WidgetGenerator()
        result = gen._generate_widget_params(None, "binned_distribution", "bar_plot")
        assert result["x_axis"] == "bin"
        assert result["y_axis"] == "count"

    def test_generate_widget_params_unknown_pair_returns_empty(self):
        gen = WidgetGenerator()
        result = gen._generate_widget_params(
            None, "unknown_transformer", "unknown_widget"
        )
        assert result == {}


# ---------------------------------------------------------------------------
# _PREPROCESSING_ADAPTERS
# ---------------------------------------------------------------------------


class TestPreprocessingAdapters:
    """Validate preprocessing adapter functions."""

    def test_adapt_bins_to_donut_normal(self):
        data = {"bins": [0, 10, 20, 30], "counts": [5, 10, 15]}
        result = preprocess_data_for_widget(data, "binned_distribution", "donut_chart")
        assert result["labels"] == ["0-10", "10-20", "20-30"]
        assert result["counts"] == [5, 10, 15]

    def test_adapt_bins_to_donut_empty(self):
        data = {"bins": [], "counts": []}
        result = preprocess_data_for_widget(data, "binned_distribution", "donut_chart")
        # Should return data unchanged when bins/counts are empty
        assert "bins" in result or "labels" in result

    def test_adapt_bins_to_donut_preserves_percentages(self):
        data = {"bins": [0, 10, 20], "counts": [5, 15], "percentages": [25.0, 75.0]}
        result = preprocess_data_for_widget(data, "binned_distribution", "donut_chart")
        assert result["percentages"] == [25.0, 75.0]

    def test_adapt_aggregator_to_gauge_passthrough(self):
        data = {"value": 42}
        result = preprocess_data_for_widget(data, "field_aggregator", "radial_gauge")
        assert result == {"value": 42}

    def test_adapt_aggregator_to_gauge_nested(self):
        data = {"some_field": {"value": 42, "units": "mm"}}
        result = preprocess_data_for_widget(data, "field_aggregator", "radial_gauge")
        assert result["value"] == 42
        assert result["unit"] == "mm"

    def test_adapt_aggregator_to_gauge_counts_list(self):
        data = {"counts": [42]}
        result = preprocess_data_for_widget(data, "field_aggregator", "radial_gauge")
        assert result["value"] == 42

    def test_non_dict_data_passthrough(self):
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2]})
        result = preprocess_data_for_widget(df, "binned_distribution", "bar_plot")
        assert isinstance(result, pd.DataFrame)

    def test_unknown_pair_passthrough(self):
        data = {"custom": "data"}
        result = preprocess_data_for_widget(data, "unknown", "unknown")
        assert result == {"custom": "data"}

    def test_class_object_field_aggregator_to_gauge(self):
        data = {"field": {"value": 99}}
        result = preprocess_data_for_widget(
            data, "class_object_field_aggregator", "radial_gauge"
        )
        assert result["value"] == 99


# ---------------------------------------------------------------------------
# High-cardinality filter
# ---------------------------------------------------------------------------


class TestHighCardinalityFilter:
    """Validate that high-cardinality categoricals get filtered."""

    @pytest.fixture(autouse=True)
    def _load_plugins(self):
        from niamoto.core.plugins.plugin_loader import PluginLoader

        PluginLoader().load_plugins_with_cascade()

    def _make_profile(self, cardinality, category=DataCategory.CATEGORICAL):
        from niamoto.core.imports.data_analyzer import FieldPurpose

        return EnrichedColumnProfile(
            name="test_col",
            dtype="object",
            semantic_type=None,
            unique_ratio=cardinality / 100,
            null_ratio=0.0,
            sample_values=["a", "b", "c"],
            confidence=0.9,
            data_category=category,
            field_purpose=FieldPurpose.CLASSIFICATION,
            cardinality=cardinality,
        )

    def test_low_cardinality_gets_categorical_distribution(self):
        profile = self._make_profile(5)
        gen = WidgetGenerator()
        suggestions = gen._generate_for_column(profile, "occurrences")
        transformers = {s.transformer_plugin for s in suggestions}
        assert "categorical_distribution" in transformers

    def test_high_cardinality_no_categorical_distribution(self):
        profile = self._make_profile(50)
        gen = WidgetGenerator()
        suggestions = gen._generate_for_column(profile, "occurrences")
        transformers = {s.transformer_plugin for s in suggestions}
        assert "categorical_distribution" not in transformers
        assert "top_ranking" in transformers

    def test_categorical_high_card_only_top_ranking(self):
        profile = self._make_profile(100, DataCategory.CATEGORICAL_HIGH_CARD)
        gen = WidgetGenerator()
        suggestions = gen._generate_for_column(profile, "occurrences")
        transformers = {s.transformer_plugin for s in suggestions}
        assert "categorical_distribution" not in transformers
        assert "top_ranking" in transformers
