"""
Phase 2: Semantic corrections and label fixes.

Tests for: DwC patterns, um bug fix, labels from data, French→English, NULL columns,
NUMERIC_DISCRETE alignment, scatter_plot, DataAnalyzer consolidation.
"""

import pandas as pd

from niamoto.core.imports.profiler import DataProfiler


# ── Phase 2.1: Darwin Core patterns ───────────────────────────────────────


class TestDarwinCorePatterns:
    """Verify DwC field names are detected semantically."""

    def test_scientific_name_detected(self, tmp_path):
        """scientificName should be detected as taxonomy."""
        csv_path = tmp_path / "dwc.csv"
        df = pd.DataFrame(
            {
                "scientificName": [
                    "Araucaria columnaris",
                    "Podocarpus sp.",
                    "Nothofagus",
                ],
            }
        )
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(csv_path)

        col = profile.columns[0]
        assert col.semantic_type is not None
        assert "taxonomy" in col.semantic_type, (
            f"scientificName got semantic_type={col.semantic_type}"
        )

    def test_decimal_latitude_detected(self, tmp_path):
        """decimalLatitude should be detected as location."""
        csv_path = tmp_path / "dwc.csv"
        df = pd.DataFrame({"decimalLatitude": [-22.1, -22.2, -22.3]})
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(csv_path)

        col = profile.columns[0]
        assert col.semantic_type is not None
        assert "location" in col.semantic_type, (
            f"decimalLatitude got semantic_type={col.semantic_type}"
        )

    def test_decimal_longitude_detected(self, tmp_path):
        """decimalLongitude should be detected as location."""
        csv_path = tmp_path / "dwc.csv"
        df = pd.DataFrame({"decimalLongitude": [166.4, 166.5, 166.6]})
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(csv_path)

        col = profile.columns[0]
        assert col.semantic_type is not None
        assert "location" in col.semantic_type

    def test_kingdom_detected(self, tmp_path):
        """kingdom should be detected as taxonomy."""
        csv_path = tmp_path / "dwc.csv"
        df = pd.DataFrame({"kingdom": ["Plantae", "Animalia", "Fungi"]})
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(csv_path)

        col = profile.columns[0]
        assert col.semantic_type is not None
        assert "taxonomy" in col.semantic_type

    def test_event_date_detected(self, tmp_path):
        """eventDate should be detected as temporal."""
        csv_path = tmp_path / "dwc.csv"
        df = pd.DataFrame({"eventDate": ["2024-01-15", "2024-02-20", "2024-03-10"]})
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(csv_path)

        col = profile.columns[0]
        assert col.semantic_type is not None
        assert "temporal" in col.semantic_type


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


# ── Phase 2.4: French labels → English ────────────────────────────────────


class TestFrenchLabelsRemoved:
    """Verify French strings are replaced with English."""

    def test_labels_are_english(self):
        """Generated labels should not contain French accented characters."""
        from niamoto.core.imports.widget_generator import WidgetGenerator
        from niamoto.core.imports.data_analyzer import (
            EnrichedColumnProfile,
            DataCategory,
            FieldPurpose,
        )

        gen = WidgetGenerator()
        profile = EnrichedColumnProfile(
            name="height",
            dtype="float64",
            semantic_type=None,
            unique_ratio=0.8,
            null_ratio=0.0,
            sample_values=[10.0, 20.0, 30.0],
            confidence=0.5,
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            cardinality=100,
            value_range=[0.0, 50.0],
            suggested_bins=None,
            suggested_labels=None,
        )

        # Check all transformer labels
        for transformer in [
            "binned_distribution",
            "statistical_summary",
            "categorical_distribution",
            "top_ranking",
            "binary_counter",
            "geospatial_extractor",
            "time_series_analysis",
        ]:
            name, desc = gen._generate_labels(profile, transformer, "bar_plot")
            # No French accented characters
            french_chars = set("éèêëàâùûôîïçÉÈÊËÀÂÙÛÔÎÏÇ")
            assert not any(c in french_chars for c in name), (
                f"Label '{name}' for {transformer} contains French chars"
            )
            assert not any(c in french_chars for c in desc), (
                f"Description '{desc}' for {transformer} contains French chars"
            )


# ── Phase 2.6: Align NUMERIC_DISCRETE ─────────────────────────────────────


# ── Phase 2.5: NULL columns → no suggestion ───────────────────────────────


class TestNullColumnsSkipped:
    """Verify columns with 100% NULL produce no suggestions."""

    def test_null_column_produces_no_suggestions(self):
        """A column with null_ratio=1.0 should produce zero suggestions."""
        from niamoto.core.imports.widget_generator import WidgetGenerator
        from niamoto.core.imports.data_analyzer import (
            EnrichedColumnProfile,
            DataCategory,
            FieldPurpose,
        )

        gen = WidgetGenerator()
        profile = EnrichedColumnProfile(
            name="empty_col",
            dtype="float64",
            semantic_type=None,
            unique_ratio=0.0,
            null_ratio=1.0,  # 100% NULL
            sample_values=[],
            confidence=0.0,
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            cardinality=0,
            value_range=None,
            suggested_bins=None,
            suggested_labels=None,
        )
        suggestions = gen.generate_for_columns([profile])
        assert len(suggestions) == 0, (
            f"Expected 0 suggestions for 100% NULL column, got {len(suggestions)}"
        )


# ── Phase 2.6: Align NUMERIC_DISCRETE ─────────────────────────────────────


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
        config = gen._generate_widget_config(
            profile, "scatter_analysis", "scatter_plot"
        )
        assert config, "scatter_analysis→scatter_plot should produce config"
        assert "x_axis" in config


# ── Phase 2.6: Align NUMERIC_DISCRETE ─────────────────────────────────────


class TestNumericDiscreteAlignment:
    """Verify NUMERIC_DISCRETE mapping is aligned between components."""

    def test_transformer_suggester_numeric_discrete(self):
        """TransformerSuggester should suggest binned_distribution for NUMERIC_DISCRETE."""
        from niamoto.core.imports.transformer_suggester import TransformerSuggester
        from niamoto.core.imports.data_analyzer import DataCategory

        ts = TransformerSuggester()
        mapping = ts.CATEGORY_TO_TRANSFORMERS
        discrete_transformers = mapping.get(DataCategory.NUMERIC_DISCRETE, [])
        assert "binned_distribution" in discrete_transformers, (
            f"NUMERIC_DISCRETE transformers: {discrete_transformers}"
        )
