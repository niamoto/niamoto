"""
Focused regression tests for WidgetGenerator and scatter plot integration.
"""


# ── Phase 2.3: Fix "um" bug + labels from data ────────────────────────────


class TestUmBugFix:
    """Verify the um substring bug is fixed."""

    def test_maximum_not_detected_as_um(self):
        """'maximum_height' should NOT produce UM/NUM labels."""
        from niamoto.core.imports.widget_generator import WidgetGenerator

        gen = WidgetGenerator()
        labels = gen._guess_binary_labels("maximum_height", values={"low", "high"})
        assert labels != ("UM", "NUM"), f"maximum_height got labels {labels}"
        assert "UM" not in labels

    def test_medium_not_detected_as_um(self):
        """'medium_size' should NOT produce UM/NUM labels."""
        from niamoto.core.imports.widget_generator import WidgetGenerator

        gen = WidgetGenerator()
        labels = gen._guess_binary_labels("medium_size", values={"small", "large"})
        assert labels != ("UM", "NUM")

    def test_museum_not_detected_as_um(self):
        """'museum_id' should NOT produce UM/NUM labels."""
        from niamoto.core.imports.widget_generator import WidgetGenerator

        gen = WidgetGenerator()
        labels = gen._guess_binary_labels("museum_id", values={"A", "B"})
        assert labels != ("UM", "NUM")

    def test_binary_labels_from_data(self):
        """Labels should be derived from actual column values."""
        from niamoto.core.imports.widget_generator import WidgetGenerator

        gen = WidgetGenerator()
        labels = gen._guess_binary_labels("status", values={"active", "inactive"})
        assert labels == ("active", "inactive")

    def test_binary_labels_default(self):
        """Without values, default to True/False."""
        from niamoto.core.imports.widget_generator import WidgetGenerator

        gen = WidgetGenerator()
        labels = gen._guess_binary_labels("unknown_col")
        assert labels == ("True", "False")


# ── Phase 2.7: scatter_plot compatible_structures + mapping config ─────────


class TestScatterPlotActivation:
    """Verify scatter_plot has compatible_structures and config mapping."""

    def test_scatter_plot_has_compatible_structures(self):
        """ScatterPlotWidget should declare compatible_structures."""
        from niamoto.core.plugins.widgets.scatter_plot import ScatterPlotWidget

        assert hasattr(ScatterPlotWidget, "compatible_structures")
        assert ScatterPlotWidget.compatible_structures is not None
        assert len(ScatterPlotWidget.compatible_structures) > 0

    def test_scatter_analysis_config_mapping(self):
        """scatter_analysis→scatter_plot should produce a config with x_axis."""
        from niamoto.core.imports.widget_generator import WidgetGenerator
        from niamoto.core.imports.data_analyzer import (
            EnrichedColumnProfile,
            DataCategory,
            FieldPurpose,
        )

        gen = WidgetGenerator()
        profile = EnrichedColumnProfile(
            name="dbh",
            dtype="float64",
            semantic_type=None,
            unique_ratio=0.8,
            null_ratio=0.0,
            sample_values=[10.0, 20.0, 30.0],
            confidence=0.5,
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            cardinality=100,
            value_range=[0.0, 100.0],
            suggested_bins=None,
            suggested_labels=None,
        )
        config = gen._generate_widget_params(
            profile, "scatter_analysis", "scatter_plot"
        )
        assert config, "scatter_analysis→scatter_plot should produce config"
        assert "x_axis" in config
