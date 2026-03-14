"""
Phase 3: WidgetGenerator tests + contract tests.

Tests for: DataCategory coverage, config validation, API shape, edge cases.
"""

import pytest
import pandas as pd

from niamoto.core.imports.widget_generator import WidgetGenerator
from niamoto.core.imports.data_analyzer import (
    EnrichedColumnProfile,
    DataCategory,
    FieldPurpose,
)
from niamoto.core.plugins.plugin_loader import PluginLoader


@pytest.fixture(autouse=True, scope="module")
def _ensure_plugins_loaded():
    """Ensure plugins are loaded so SmartMatcher can find them."""
    loader = PluginLoader()
    loader.load_plugins_with_cascade()


def make_profile(
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


# ── Phase 3.a: Tests by DataCategory ──────────────────────────────────────


class TestWidgetGeneratorByCategory:
    """Test WidgetGenerator.generate_for_columns for each DataCategory."""

    @pytest.fixture
    def gen(self):
        return WidgetGenerator()

    def test_numeric_continuous_suggests_distribution(self, gen):
        """NUMERIC_CONTINUOUS → at least 1 suggestion with binned_distribution."""
        profile = make_profile(
            name="dbh",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
        )
        suggestions = gen.generate_for_columns([profile])
        assert len(suggestions) >= 1
        transformers = {s.transformer_plugin for s in suggestions}
        assert "binned_distribution" in transformers, (
            f"Expected binned_distribution, got {transformers}"
        )

    def test_numeric_discrete_suggests_binned(self, gen):
        """NUMERIC_DISCRETE → suggests binned_distribution (aligned with TransformerSuggester)."""
        profile = make_profile(
            name="age",
            data_category=DataCategory.NUMERIC_DISCRETE,
            field_purpose=FieldPurpose.MEASUREMENT,
            dtype="int64",
            cardinality=20,
        )
        suggestions = gen.generate_for_columns([profile])
        assert len(suggestions) >= 1
        transformers = {s.transformer_plugin for s in suggestions}
        assert "binned_distribution" in transformers

    def test_categorical_suggests_distribution(self, gen):
        """CATEGORICAL → at least 1 suggestion with categorical_distribution."""
        profile = make_profile(
            name="habitat",
            data_category=DataCategory.CATEGORICAL,
            field_purpose=FieldPurpose.CLASSIFICATION,
            dtype="object",
            cardinality=8,
            sample_values=["forest", "savanna", "wetland"],
        )
        suggestions = gen.generate_for_columns([profile])
        assert len(suggestions) >= 1
        transformers = {s.transformer_plugin for s in suggestions}
        assert (
            "categorical_distribution" in transformers or "top_ranking" in transformers
        )

    def test_binary_suggests_binary_counter(self, gen):
        """BOOLEAN → binary_counter + donut_chart."""
        profile = make_profile(
            name="is_endemic",
            data_category=DataCategory.BOOLEAN,
            field_purpose=FieldPurpose.CLASSIFICATION,
            dtype="bool",
            cardinality=2,
            sample_values=[True, False],
        )
        suggestions = gen.generate_for_columns([profile])
        assert len(suggestions) >= 1
        transformers = {s.transformer_plugin for s in suggestions}
        assert "binary_counter" in transformers

    def test_geographic_suggests_map(self, gen):
        """GEOGRAPHIC → geospatial_extractor + interactive_map."""
        profile = make_profile(
            name="coordinates",
            data_category=DataCategory.GEOGRAPHIC,
            field_purpose=FieldPurpose.LOCATION,
            semantic_type="geometry",
        )
        suggestions = gen.generate_for_columns([profile])
        assert len(suggestions) >= 1
        transformers = {s.transformer_plugin for s in suggestions}
        assert "geospatial_extractor" in transformers

    def test_identifier_produces_no_suggestions(self, gen):
        """IDENTIFIER → no suggestions (intentionally skipped)."""
        profile = make_profile(
            name="gbifID",
            data_category=DataCategory.IDENTIFIER,
            field_purpose=FieldPurpose.PRIMARY_KEY,
            dtype="int64",
        )
        suggestions = gen.generate_for_columns([profile])
        assert len(suggestions) == 0

    def test_text_produces_no_suggestions(self, gen):
        """TEXT → no suggestions."""
        profile = make_profile(
            name="remarks",
            data_category=DataCategory.TEXT,
            field_purpose=FieldPurpose.DESCRIPTION,
            dtype="object",
        )
        suggestions = gen.generate_for_columns([profile])
        assert len(suggestions) == 0

    def test_null_column_skipped(self, gen):
        """100% NULL column → no suggestions."""
        profile = make_profile(
            name="empty",
            null_ratio=1.0,
            cardinality=0,
            sample_values=[],
        )
        suggestions = gen.generate_for_columns([profile])
        assert len(suggestions) == 0

    def test_multiple_columns_combined(self, gen):
        """Multiple columns produce combined suggestions sorted by confidence."""
        profiles = [
            make_profile(
                name="height",
                data_category=DataCategory.NUMERIC_CONTINUOUS,
                field_purpose=FieldPurpose.MEASUREMENT,
            ),
            make_profile(
                name="species",
                data_category=DataCategory.CATEGORICAL,
                field_purpose=FieldPurpose.CLASSIFICATION,
                dtype="object",
                cardinality=50,
                sample_values=["Araucaria", "Podocarpus"],
            ),
        ]
        suggestions = gen.generate_for_columns(profiles)
        assert len(suggestions) >= 2
        # Should be sorted by confidence descending
        confidences = [s.confidence for s in suggestions]
        assert confidences == sorted(confidences, reverse=True)


# ── Phase 3.b: Contract test — config validation ──────────────────────────


class TestConfigContract:
    """Verify generated configs are non-empty for known pairs."""

    KNOWN_PAIRS = [
        ("binned_distribution", "bar_plot"),
        ("categorical_distribution", "bar_plot"),
        ("statistical_summary", "radial_gauge"),
        ("binary_counter", "donut_chart"),
        ("geospatial_extractor", "interactive_map"),
        ("top_ranking", "bar_plot"),
        ("scatter_analysis", "scatter_plot"),
    ]

    @pytest.fixture
    def gen(self):
        return WidgetGenerator()

    @pytest.mark.parametrize("transformer,widget", KNOWN_PAIRS)
    def test_known_pair_produces_nonempty_config(self, gen, transformer, widget):
        """Each known transformer→widget pair must produce a non-empty config."""
        profile = make_profile(name="test_col")
        config = gen._generate_widget_config(profile, transformer, widget)
        assert config, f"{transformer}→{widget} returned empty config {config}"

    def test_unknown_pair_returns_empty(self, gen):
        """Unknown pair returns {} (documented behavior)."""
        profile = make_profile(name="test_col")
        config = gen._generate_widget_config(profile, "unknown_t", "unknown_w")
        assert config == {}


# ── Phase 3.c: Semantic profile shape contract ────────────────────────────


class TestSemanticProfileShape:
    """Verify semantic_profile structure is consistent."""

    def test_profile_has_required_fields(self, tmp_path):
        """semantic_profile from _analyze_for_transformers has all required fields."""
        from niamoto.core.imports.engine import GenericImporter
        from niamoto.core.imports.data_analyzer import DataAnalyzer
        from niamoto.core.imports.transformer_suggester import TransformerSuggester

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "species": ["Araucaria", "Podocarpus", "Nothofagus"],
                "height": [15.2, 8.5, 12.0],
                "latitude": [-22.1, -22.2, -22.3],
            }
        )
        df.to_csv(csv_path, index=False)

        engine = GenericImporter.__new__(GenericImporter)
        engine.data_analyzer = DataAnalyzer()
        engine.transformer_suggester = TransformerSuggester()

        profile = engine._analyze_for_transformers(
            df=df, csv_path=csv_path, entity_name="test"
        )

        # Required top-level keys
        required_keys = {
            "schema_version",
            "profiling_status",
            "analyzed_at",
            "column_diagnostics",
            "columns",
            "transformer_suggestions",
        }
        assert required_keys.issubset(profile.keys()), (
            f"Missing keys: {required_keys - profile.keys()}"
        )

        # schema_version >= 2
        assert profile["schema_version"] >= 2

        # profiling_status is valid
        assert profile["profiling_status"] in ("complete", "partial", "failed")

        # columns is a list of dicts
        assert isinstance(profile["columns"], list)
        for col in profile["columns"]:
            assert "name" in col
            assert "data_category" in col

        # column_diagnostics has entries
        assert isinstance(profile["column_diagnostics"], dict)
        for col_name, diag in profile["column_diagnostics"].items():
            assert "status" in diag

        # transformer_suggestions is a dict
        assert isinstance(profile["transformer_suggestions"], dict)

    def test_suggestion_has_required_fields(self, tmp_path):
        """Each suggestion in transformer_suggestions has required fields."""
        from niamoto.core.imports.engine import GenericImporter
        from niamoto.core.imports.data_analyzer import DataAnalyzer
        from niamoto.core.imports.transformer_suggester import TransformerSuggester

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "height": [15.2, 8.5, 12.0, 20.0, 5.0],
                "species": ["A", "B", "C", "D", "E"],
            }
        )
        df.to_csv(csv_path, index=False)

        engine = GenericImporter.__new__(GenericImporter)
        engine.data_analyzer = DataAnalyzer()
        engine.transformer_suggester = TransformerSuggester()

        profile = engine._analyze_for_transformers(
            df=df, csv_path=csv_path, entity_name="test"
        )

        for col_name, suggestions in profile["transformer_suggestions"].items():
            for s in suggestions:
                assert "transformer" in s, (
                    f"Missing 'transformer' in suggestion for {col_name}"
                )
                assert "confidence" in s, (
                    f"Missing 'confidence' in suggestion for {col_name}"
                )
                assert "reason" in s
                assert "config" in s
                assert 0 <= s["confidence"] <= 1.0
