"""
Tests for TransformerSuggester module.
"""

import pytest

from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)
from niamoto.core.imports.transformer_suggester import (
    TransformerSuggester,
)


@pytest.fixture
def suggester():
    """Create a TransformerSuggester instance."""
    return TransformerSuggester()


@pytest.fixture
def elevation_profile():
    """Profile for elevation (numeric continuous)."""
    return EnrichedColumnProfile(
        name="elevation",
        dtype="float64",
        semantic_type="measurement.elevation",
        unique_ratio=0.85,
        null_ratio=0.02,
        sample_values=[150.5, 250.0, 350.2],
        confidence=0.90,
        data_category=DataCategory.NUMERIC_CONTINUOUS,
        field_purpose=FieldPurpose.MEASUREMENT,
        suggested_bins=[0, 250, 500, 750, 1000],
        cardinality=850,
        value_range=(5.0, 1650.0),
    )


@pytest.fixture
def species_profile():
    """Profile for species (categorical)."""
    return EnrichedColumnProfile(
        name="species",
        dtype="object",
        semantic_type="taxonomy.species",
        unique_ratio=0.15,
        null_ratio=0.01,
        sample_values=["Species A", "Species B"],
        confidence=0.85,
        data_category=DataCategory.CATEGORICAL,
        field_purpose=FieldPurpose.CLASSIFICATION,
        suggested_labels=["Species A", "Species B", "Species C"],
        cardinality=25,
        value_range=None,
    )


@pytest.fixture
def id_profile():
    """Profile for ID (identifier)."""
    return EnrichedColumnProfile(
        name="id_occurrence",
        dtype="int64",
        semantic_type="identifier",
        unique_ratio=1.0,
        null_ratio=0.0,
        sample_values=[1, 2, 3],
        confidence=0.95,
        data_category=DataCategory.IDENTIFIER,
        field_purpose=FieldPurpose.PRIMARY_KEY,
        cardinality=1250,
        value_range=(1, 1250),
    )


class TestCategoryMapping:
    """Tests for category to transformer mapping."""

    def test_numeric_continuous_mapping(self, suggester, elevation_profile):
        """Test mapping for numeric continuous data."""
        suggestions = suggester.suggest_transformers(elevation_profile, "occurrences")

        assert len(suggestions) == 2
        transformer_names = [s.transformer_name for s in suggestions]
        assert "binned_distribution" in transformer_names
        assert "statistical_summary" in transformer_names

    def test_categorical_mapping(self, suggester, species_profile):
        """Test mapping for categorical data."""
        suggestions = suggester.suggest_transformers(species_profile, "occurrences")

        assert len(suggestions) == 2
        transformer_names = [s.transformer_name for s in suggestions]
        assert "categorical_distribution" in transformer_names
        assert "top_ranking" in transformer_names

    def test_numeric_discrete_mapping(self, suggester):
        """Numeric discrete category should stay mapped to binned_distribution."""
        discrete_transformers = suggester.CATEGORY_TO_TRANSFORMERS.get(
            DataCategory.NUMERIC_DISCRETE, []
        )
        assert "binned_distribution" in discrete_transformers

    def test_identifier_gets_top_ranking(self, suggester, id_profile):
        """Test that identifiers with high cardinality get top_ranking suggestion."""
        suggestions = suggester.suggest_transformers(id_profile, "occurrences")
        # Identifiers with high cardinality can get top_ranking to show most frequent values
        assert len(suggestions) == 1
        assert suggestions[0].transformer_name == "top_ranking"

    def test_identifier_like_numeric_profile_skips_measurement_widgets(self, suggester):
        """Legacy identifier names should not get measurement-oriented transformers."""
        profile = EnrichedColumnProfile(
            name="idrb_n",
            dtype="float64",
            semantic_type="identifier.record",
            unique_ratio=0.35,
            null_ratio=0.1,
            sample_values=["ngoila003", "ngoila004"],
            confidence=0.85,
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.FOREIGN_KEY,
            suggested_bins=[0, 10, 20],
            cardinality=120,
            value_range=(0.0, 20.0),
        )

        suggestions = suggester.suggest_transformers(profile, "occurrences")

        assert all(
            suggestion.transformer_name
            not in {"binned_distribution", "statistical_summary"}
            for suggestion in suggestions
        )

    def test_boolean_mapping(self, suggester):
        """Test mapping for boolean data."""
        profile = EnrichedColumnProfile(
            name="is_endemic",
            dtype="int64",
            semantic_type=None,
            unique_ratio=0.02,
            null_ratio=0.0,
            sample_values=[0, 1],
            confidence=0.80,
            data_category=DataCategory.BOOLEAN,
            field_purpose=FieldPurpose.METADATA,
            cardinality=2,
            value_range=(0, 1),
        )

        suggestions = suggester.suggest_transformers(profile, "occurrences")

        assert len(suggestions) == 1
        assert suggestions[0].transformer_name == "binary_counter"

    def test_geographic_mapping(self, suggester):
        """Test mapping for geographic data."""
        profile = EnrichedColumnProfile(
            name="geo_pt",
            dtype="object",
            semantic_type="geometry",
            unique_ratio=0.95,
            null_ratio=0.0,
            sample_values=[],
            confidence=0.90,
            data_category=DataCategory.GEOGRAPHIC,
            field_purpose=FieldPurpose.LOCATION,
            cardinality=1200,
            value_range=None,
        )

        suggestions = suggester.suggest_transformers(profile, "occurrences")

        assert len(suggestions) == 1
        assert suggestions[0].transformer_name == "geospatial_extractor"


class TestConfigGeneration:
    """Tests for configuration generation."""

    def test_binned_distribution_config(self, suggester, elevation_profile):
        """Test config generation for binned_distribution."""
        suggestions = suggester.suggest_transformers(elevation_profile, "occurrences")

        binned_suggestion = next(
            s for s in suggestions if s.transformer_name == "binned_distribution"
        )

        config = binned_suggestion.pre_filled_config
        assert config["plugin"] == "binned_distribution"
        assert config["params"]["source"] == "occurrences"
        assert config["params"]["field"] == "elevation"
        assert config["params"]["bins"] == [0, 250, 500, 750, 1000]
        assert "include_percentages" in config["params"]

    def test_statistical_summary_config(self, suggester, elevation_profile):
        """Test config generation for statistical_summary."""
        suggestions = suggester.suggest_transformers(elevation_profile, "occurrences")

        stats_suggestion = next(
            s for s in suggestions if s.transformer_name == "statistical_summary"
        )

        config = stats_suggestion.pre_filled_config
        assert config["plugin"] == "statistical_summary"
        assert config["params"]["source"] == "occurrences"
        assert config["params"]["field"] == "elevation"
        assert config["params"]["units"] == "m"  # Inferred from semantic type
        assert config["params"]["max_value"] == 1650  # From value_range
        assert "stats" in config["params"]

    def test_categorical_distribution_config(self, suggester, species_profile):
        """Test config generation for categorical_distribution."""
        suggestions = suggester.suggest_transformers(species_profile, "occurrences")

        cat_suggestion = next(
            s for s in suggestions if s.transformer_name == "categorical_distribution"
        )

        config = cat_suggestion.pre_filled_config
        assert config["plugin"] == "categorical_distribution"
        assert config["params"]["source"] == "occurrences"
        assert config["params"]["field"] == "species"
        assert config["params"]["categories"] == []  # Auto-detect
        assert config["params"]["labels"] == ["Species A", "Species B", "Species C"]

    def test_top_ranking_config(self, suggester, species_profile):
        """Test config generation for top_ranking."""
        suggestions = suggester.suggest_transformers(species_profile, "occurrences")

        top_suggestion = next(
            s for s in suggestions if s.transformer_name == "top_ranking"
        )

        config = top_suggestion.pre_filled_config
        assert config["plugin"] == "top_ranking"
        assert config["params"]["source"] == "occurrences"
        assert config["params"]["field"] == "species"
        assert config["params"]["count"] > 0
        assert config["params"]["mode"] == "direct"


class TestUnitsInference:
    """Tests for units inference."""

    def test_elevation_units(self, suggester, elevation_profile):
        """Test units inference for elevation."""
        units = suggester._infer_units(elevation_profile)
        assert units == "m"

    def test_dbh_units(self, suggester):
        """Test units inference for DBH."""
        profile = EnrichedColumnProfile(
            name="dbh",
            dtype="float64",
            semantic_type="measurement.diameter",
            unique_ratio=0.80,
            null_ratio=0.0,
            sample_values=[10.5, 20.3],
            confidence=0.85,
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            cardinality=300,
            value_range=(5.0, 80.0),
        )

        units = suggester._infer_units(profile)
        assert units == "cm"

    def test_no_units(self, suggester):
        """Test units inference for generic numeric field."""
        profile = EnrichedColumnProfile(
            name="value",
            dtype="float64",
            semantic_type=None,
            unique_ratio=0.90,
            null_ratio=0.0,
            sample_values=[1.0, 2.0],
            confidence=0.60,
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.METADATA,
            cardinality=500,
            value_range=(0.0, 100.0),
        )

        units = suggester._infer_units(profile)
        assert units == ""


class TestConfidenceCalculation:
    """Tests for confidence score calculation."""

    def test_high_confidence(self, suggester, elevation_profile):
        """Test high confidence calculation."""
        suggestions = suggester.suggest_transformers(elevation_profile, "occurrences")

        # All suggestions should have high confidence due to:
        # - High base confidence (0.90)
        # - Low null ratio (0.02)
        # - Category match
        for suggestion in suggestions:
            assert suggestion.confidence >= 0.80

    def test_low_confidence_high_nulls(self, suggester):
        """Test lower confidence with high null ratio."""
        profile = EnrichedColumnProfile(
            name="incomplete_field",
            dtype="float64",
            semantic_type=None,
            unique_ratio=0.50,
            null_ratio=0.40,  # 40% nulls
            sample_values=[1.0, 2.0],
            confidence=0.60,
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.METADATA,
            cardinality=100,
            value_range=(0.0, 10.0),
        )

        suggestions = suggester.suggest_transformers(profile, "occurrences")

        # Confidence should be penalized by null_ratio
        for suggestion in suggestions:
            assert suggestion.confidence < 0.80

    def test_confidence_ordering(self, suggester, elevation_profile):
        """Test that suggestions are ordered by confidence."""
        suggestions = suggester.suggest_transformers(elevation_profile, "occurrences")

        # Check that suggestions are sorted descending
        confidences = [s.confidence for s in suggestions]
        assert confidences == sorted(confidences, reverse=True)


class TestReasonGeneration:
    """Tests for reason string generation."""

    def test_reason_includes_category(self, suggester, elevation_profile):
        """Test that reason includes data category."""
        suggestions = suggester.suggest_transformers(elevation_profile, "occurrences")

        for suggestion in suggestions:
            assert "numeric_continuous" in suggestion.reason

    def test_reason_includes_semantic_type(self, suggester, elevation_profile):
        """Test that reason includes semantic type."""
        suggestions = suggester.suggest_transformers(elevation_profile, "occurrences")

        for suggestion in suggestions:
            assert "measurement.elevation" in suggestion.reason

    def test_reason_specific_details(self, suggester, elevation_profile):
        """Test that reason includes transformer-specific details."""
        suggestions = suggester.suggest_transformers(elevation_profile, "occurrences")

        binned_suggestion = next(
            s for s in suggestions if s.transformer_name == "binned_distribution"
        )
        assert "bins suggérés" in binned_suggestion.reason

        stats_suggestion = next(
            s for s in suggestions if s.transformer_name == "statistical_summary"
        )
        assert "Statistiques descriptives" in stats_suggestion.reason


class TestDatasetSuggestions:
    """Tests for dataset-level suggestions."""

    def test_suggest_for_dataset(self, suggester, elevation_profile, species_profile):
        """Test generating suggestions for multiple columns."""
        profiles = [elevation_profile, species_profile]

        suggestions_by_column = suggester.suggest_for_dataset(profiles, "occurrences")

        assert len(suggestions_by_column) == 2
        assert "elevation" in suggestions_by_column
        assert "species" in suggestions_by_column

        # Each column should have suggestions
        assert len(suggestions_by_column["elevation"]) > 0
        assert len(suggestions_by_column["species"]) > 0

    def test_suggest_for_dataset_includes_all_columns(
        self, suggester, elevation_profile, id_profile
    ):
        """Test that all columns with suggestions are included in dataset suggestions."""
        profiles = [elevation_profile, id_profile]

        suggestions_by_column = suggester.suggest_for_dataset(profiles, "occurrences")

        # Both elevation and id_occurrence should have suggestions
        # (identifiers can get top_ranking for high cardinality columns)
        assert len(suggestions_by_column) == 2
        assert "elevation" in suggestions_by_column
        assert "id_occurrence" in suggestions_by_column
        # Verify id_occurrence gets top_ranking
        assert (
            suggestions_by_column["id_occurrence"][0].transformer_name == "top_ranking"
        )


class TestTransformerSuggestion:
    """Tests for TransformerSuggestion dataclass."""

    def test_suggestion_structure(self, suggester, elevation_profile):
        """Test that suggestion has all required fields."""
        suggestions = suggester.suggest_transformers(elevation_profile, "occurrences")

        for suggestion in suggestions:
            assert hasattr(suggestion, "transformer_name")
            assert hasattr(suggestion, "confidence")
            assert hasattr(suggestion, "reason")
            assert hasattr(suggestion, "pre_filled_config")
            assert hasattr(suggestion, "column_name")

            # Check types
            assert isinstance(suggestion.transformer_name, str)
            assert isinstance(suggestion.confidence, float)
            assert isinstance(suggestion.reason, str)
            assert isinstance(suggestion.pre_filled_config, dict)
            assert isinstance(suggestion.column_name, str)

            # Check value ranges
            assert 0.0 <= suggestion.confidence <= 1.0
            assert len(suggestion.reason) > 0
