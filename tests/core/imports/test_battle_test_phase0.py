"""
Phase 0: Guard rails and characterization tests for the battle-test plan.

These tests establish baselines and safety nets BEFORE modifying the pipeline.
"""

import pytest
import pandas as pd

from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.plugin_loader import PluginLoader


# ── Phase 0.1: Smoke test plugin registry ──────────────────────────────────


class TestPluginRegistrySmoke:
    """Verify that plugins are loaded and discoverable."""

    @pytest.fixture(autouse=True, scope="class")
    @classmethod
    def ensure_plugins_loaded(cls):
        """Ensure core plugins are loaded before testing."""
        loader = PluginLoader()
        loader.load_plugins_with_cascade()

    def test_widgets_are_registered(self):
        """At least 5 widget plugins should be registered."""
        widgets = PluginRegistry.get_plugins_by_type(PluginType.WIDGET)
        assert len(widgets) >= 5, (
            f"Expected >= 5 widgets, got {len(widgets)}: {list(widgets.keys())}"
        )

    def test_transformers_are_registered(self):
        """At least 5 transformer plugins should be registered."""
        transformers = PluginRegistry.get_plugins_by_type(PluginType.TRANSFORMER)
        assert len(transformers) >= 5, (
            f"Expected >= 5 transformers, got {len(transformers)}: {list(transformers.keys())}"
        )

    def test_key_widgets_present(self):
        """Critical widgets for suggestions must be registered."""
        widgets = PluginRegistry.get_plugins_by_type(PluginType.WIDGET)
        expected = ["bar_plot", "donut_chart", "interactive_map", "radial_gauge"]
        for name in expected:
            assert name in widgets, f"Widget '{name}' not found in registry"

    def test_key_transformers_present(self):
        """Critical transformers for suggestions must be registered."""
        transformers = PluginRegistry.get_plugins_by_type(PluginType.TRANSFORMER)
        expected = [
            "binned_distribution",
            "statistical_summary",
            "categorical_distribution",
            "binary_counter",
            "geospatial_extractor",
        ]
        for name in expected:
            assert name in transformers, f"Transformer '{name}' not found in registry"


# ── Phase 0.2: Clarify ML detector behavior ───────────────────────────────


class TestMLDetectorBehavior:
    """Clarify how ml_detector=None behaves in DataProfiler."""

    def test_profiler_with_ml_none_loads_default(self):
        """DataProfiler(ml_detector=None) tries to load the default model."""
        from niamoto.core.imports.profiler import DataProfiler

        profiler = DataProfiler(ml_detector=None)
        # The profiler should either have loaded the model or gracefully have None
        # This documents the ACTUAL behavior
        if profiler.ml_detector is not None:
            assert profiler.ml_detector.is_trained
        # Either way, no crash

    def test_profiler_with_explicit_disable(self):
        """DataProfiler(ml_detector=False) should disable ML."""
        from niamoto.core.imports.profiler import DataProfiler

        # Using False as a sentinel to explicitly disable
        profiler = DataProfiler(ml_detector=False)
        assert profiler.ml_detector is False or profiler.ml_detector is None

    def test_profile_works_without_ml(self, tmp_path):
        """Profiling a CSV works even without ML detector."""
        from niamoto.core.imports.profiler import DataProfiler

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "species": ["Araucaria", "Podocarpus", "Nothofagus"],
                "height": [15.2, 8.5, 12.0],
                "latitude": [-22.1, -22.2, -22.3],
            }
        )
        df.to_csv(csv_path, index=False)

        profiler = DataProfiler(ml_detector=None)
        profile = profiler.profile(csv_path)

        assert profile is not None
        assert profile.record_count == 3
        assert len(profile.columns) == 3


# ── Phase 0.3: Characterization tests for WidgetGenerator ─────────────────


class TestWidgetGeneratorCharacterization:
    """Baseline tests documenting current WidgetGenerator behavior.

    These tests snapshot the current behavior BEFORE modifications.
    If they fail during Phase 2, we know exactly what changed.
    """

    @pytest.fixture
    def generator(self):
        from niamoto.core.imports.widget_generator import WidgetGenerator

        return WidgetGenerator()

    @pytest.fixture
    def make_profile(self):
        """Factory for creating EnrichedColumnProfile test objects."""
        from niamoto.core.imports.data_analyzer import (
            EnrichedColumnProfile,
            DataCategory,
            FieldPurpose,
        )

        def _make(
            name="test_col",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            cardinality=100,
            null_ratio=0.0,
            value_range=None,
            suggested_bins=None,
            suggested_labels=None,
            dtype="float64",
            semantic_type=None,
            unique_ratio=0.8,
            sample_values=None,
            confidence=0.5,
        ):
            return EnrichedColumnProfile(
                name=name,
                dtype=dtype,
                semantic_type=semantic_type,
                unique_ratio=unique_ratio,
                null_ratio=null_ratio,
                sample_values=sample_values or [1.0, 2.0, 3.0],
                confidence=confidence,
                data_category=data_category,
                field_purpose=field_purpose,
                cardinality=cardinality,
                value_range=value_range or [0.0, 100.0],
                suggested_bins=suggested_bins,
                suggested_labels=suggested_labels,
            )

        return _make

    def test_numeric_continuous_produces_suggestions(self, generator, make_profile):
        """A numeric continuous column should produce at least 1 suggestion."""
        from niamoto.core.imports.data_analyzer import (
            DataCategory,
            FieldPurpose,
        )

        profile = make_profile(
            name="dbh",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
        )
        suggestions = generator.generate_for_columns([profile])
        assert len(suggestions) >= 1, "Numeric continuous should produce suggestions"

    def test_categorical_produces_suggestions(self, generator, make_profile):
        """A categorical column should produce at least 1 suggestion."""
        from niamoto.core.imports.data_analyzer import (
            DataCategory,
            FieldPurpose,
        )

        profile = make_profile(
            name="habitat",
            data_category=DataCategory.CATEGORICAL,
            field_purpose=FieldPurpose.CLASSIFICATION,
            cardinality=5,
            dtype="object",
            sample_values=["forest", "savanna", "wetland"],
        )
        suggestions = generator.generate_for_columns([profile])
        assert len(suggestions) >= 1, "Categorical should produce suggestions"

    def test_binary_column_labels_from_data(self, generator):
        """Labels are now derived from data values, not hardcoded NC patterns."""
        labels = generator._guess_binary_labels("substrat_um", values={"UM", "NUM"})
        # Post Phase 2.3: labels come from data values
        assert labels == ("NUM", "UM"), (
            f"Labels for 'substrat_um' with values: {labels}"
        )

    def test_high_cardinality_column_behavior(self, generator, make_profile):
        """Document how high-cardinality (ID-like) columns are handled."""
        from niamoto.core.imports.data_analyzer import (
            DataCategory,
            FieldPurpose,
        )

        profile = make_profile(
            name="record_id",
            data_category=DataCategory.CATEGORICAL_HIGH_CARD,
            field_purpose=FieldPurpose.PRIMARY_KEY,
            cardinality=10000,
            dtype="object",
            sample_values=["ID001", "ID002", "ID003"],
        )
        suggestions = generator.generate_for_columns([profile])
        # Document: high-card columns may or may not produce suggestions currently
        # This baseline helps us verify Phase 2.5 (skip identifiers)
        assert isinstance(suggestions, list)

    def test_generate_widget_config_known_pair(self, generator, make_profile):
        """Known transformer→widget pair produces non-empty config."""
        profile = make_profile(name="test")
        config = generator._generate_widget_config(
            profile, "binned_distribution", "bar_plot"
        )
        assert config, "binned_distribution→bar_plot should produce config"
        assert "x_axis" in config

    def test_generate_widget_config_unknown_pair(self, generator, make_profile):
        """Unknown transformer→widget pair returns empty dict."""
        profile = make_profile(name="test")
        config = generator._generate_widget_config(
            profile, "unknown_transformer", "unknown_widget"
        )
        assert config == {}, "Unknown pair should return {}"


# ── Phase 0.4: Observability fields in semantic_profile ────────────────────


class TestSemanticProfileObservability:
    """Verify schema_version, profiling_status, column_diagnostics in semantic_profile."""

    def test_analyze_for_transformers_has_schema_version(self, tmp_path):
        """semantic_profile must contain schema_version >= 2."""
        from niamoto.core.imports.engine import GenericImporter

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "species": ["Araucaria", "Podocarpus", "Nothofagus"],
                "height": [15.2, 8.5, 12.0],
            }
        )
        df.to_csv(csv_path, index=False)

        engine = GenericImporter.__new__(GenericImporter)
        engine.data_analyzer = _make_data_analyzer()
        engine.transformer_suggester = _make_transformer_suggester()

        profile = engine._analyze_for_transformers(
            df=df, csv_path=csv_path, entity_name="test"
        )

        assert "schema_version" in profile
        assert profile["schema_version"] >= 2

    def test_analyze_has_profiling_status(self, tmp_path):
        """semantic_profile must contain profiling_status."""
        from niamoto.core.imports.engine import GenericImporter

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "species": ["A", "B", "C"],
                "value": [1.0, 2.0, 3.0],
            }
        )
        df.to_csv(csv_path, index=False)

        engine = GenericImporter.__new__(GenericImporter)
        engine.data_analyzer = _make_data_analyzer()
        engine.transformer_suggester = _make_transformer_suggester()

        profile = engine._analyze_for_transformers(
            df=df, csv_path=csv_path, entity_name="test"
        )

        assert "profiling_status" in profile
        assert profile["profiling_status"] in ("complete", "partial", "failed")

    def test_analyze_has_column_diagnostics(self, tmp_path):
        """semantic_profile must contain column_diagnostics with status per column."""
        from niamoto.core.imports.engine import GenericImporter

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "species": ["A", "B", "C"],
                "value": [1.0, 2.0, 3.0],
            }
        )
        df.to_csv(csv_path, index=False)

        engine = GenericImporter.__new__(GenericImporter)
        engine.data_analyzer = _make_data_analyzer()
        engine.transformer_suggester = _make_transformer_suggester()

        profile = engine._analyze_for_transformers(
            df=df, csv_path=csv_path, entity_name="test"
        )

        assert "column_diagnostics" in profile
        diagnostics = profile["column_diagnostics"]
        assert len(diagnostics) > 0

        for col_name, diag in diagnostics.items():
            assert "status" in diag
            assert diag["status"] in ("analyzed", "skipped", "error")
            if diag["status"] == "analyzed":
                assert "suggestions" in diag


def _make_data_analyzer():
    """Create a real DataAnalyzer for testing."""
    from niamoto.core.imports.data_analyzer import DataAnalyzer

    return DataAnalyzer()


def _make_transformer_suggester():
    """Create a real TransformerSuggester for testing."""
    from niamoto.core.imports.transformer_suggester import TransformerSuggester

    return TransformerSuggester()
