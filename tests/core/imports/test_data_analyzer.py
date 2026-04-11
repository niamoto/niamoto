"""
Tests for DataAnalyzer module.
"""

import pandas as pd
import pytest

from niamoto.core.imports.data_analyzer import (
    DataAnalyzer,
    DataCategory,
    FieldPurpose,
)
from niamoto.core.imports.profiler import ColumnProfile


@pytest.fixture
def analyzer():
    """Create a DataAnalyzer instance."""
    return DataAnalyzer()


@pytest.fixture
def numeric_continuous_profile():
    """Profile for numeric continuous data (elevation)."""
    return ColumnProfile(
        name="elevation",
        dtype="float64",
        semantic_type="measurement.elevation",
        unique_ratio=0.85,
        null_ratio=0.02,
        sample_values=[150.5, 250.0, 350.2, 450.8, 550.3],
        confidence=0.90,
    )


@pytest.fixture
def elevation_series():
    """Sample elevation data."""
    return pd.Series(
        [150.5, 250.0, 350.2, 450.8, 550.3, 650.0, 750.5, 850.2, 950.0, 1050.5] * 10
    )


@pytest.fixture
def categorical_profile():
    """Profile for categorical data (species)."""
    return ColumnProfile(
        name="species",
        dtype="object",
        semantic_type="taxonomy.species",
        unique_ratio=0.15,
        null_ratio=0.01,
        sample_values=["Species A", "Species B", "Species C"],
        confidence=0.85,
    )


@pytest.fixture
def species_series():
    """Sample species data."""
    return pd.Series(["Species A"] * 50 + ["Species B"] * 30 + ["Species C"] * 20)


@pytest.fixture
def identifier_profile():
    """Profile for identifier data (ID column)."""
    return ColumnProfile(
        name="id_occurrence",
        dtype="int64",
        semantic_type="identifier",
        unique_ratio=1.0,
        null_ratio=0.0,
        sample_values=[1, 2, 3, 4, 5],
        confidence=0.95,
    )


@pytest.fixture
def id_series():
    """Sample ID data."""
    return pd.Series(range(1, 101))


class TestDataCategory:
    """Tests for data category detection."""

    def test_numeric_continuous_detection(
        self, analyzer, numeric_continuous_profile, elevation_series
    ):
        """Test detection of numeric continuous data."""
        enriched = analyzer.enrich_profile(numeric_continuous_profile, elevation_series)
        assert enriched.data_category == DataCategory.NUMERIC_CONTINUOUS

    def test_categorical_detection(self, analyzer, categorical_profile, species_series):
        """Test detection of categorical data."""
        enriched = analyzer.enrich_profile(categorical_profile, species_series)
        assert enriched.data_category == DataCategory.CATEGORICAL

    def test_identifier_detection(self, analyzer, identifier_profile, id_series):
        """Test detection of identifier data (sequential IDs with id_ prefix)."""
        enriched = analyzer.enrich_profile(identifier_profile, id_series)
        # id_occurrence with unique_ratio=1.0 should be detected as IDENTIFIER
        assert enriched.data_category == DataCategory.IDENTIFIER

    def test_identifier_semantic_detection_for_legacy_id_columns(self, analyzer):
        """Legacy identifier columns should stay identifiers even without id_ prefix."""
        profile = ColumnProfile(
            name="idrb_n",
            dtype="object",
            semantic_type="identifier.record",
            unique_ratio=0.25,
            null_ratio=0.0,
            sample_values=["ngoila003", "ngoila004", "ngoila005"],
            confidence=0.9,
        )
        series = pd.Series(["ngoila003", "ngoila003", "ngoila004", "ngoila005"])

        enriched = analyzer.enrich_profile(profile, series)

        assert enriched.data_category == DataCategory.IDENTIFIER

    def test_boolean_detection(self, analyzer):
        """Test detection of boolean data disguised as 0/1."""
        profile = ColumnProfile(
            name="is_endemic",
            dtype="int64",
            semantic_type=None,
            unique_ratio=0.02,
            null_ratio=0.0,
            sample_values=[0, 1, 0, 1, 0],
            confidence=0.5,
        )
        series = pd.Series([0, 1, 0, 1, 0, 1, 1, 0, 0, 1])

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.data_category == DataCategory.BOOLEAN

    def test_geographic_detection(self, analyzer):
        """Test detection of geographic data."""
        profile = ColumnProfile(
            name="latitude",
            dtype="float64",
            semantic_type="location.latitude",
            unique_ratio=0.95,
            null_ratio=0.0,
            sample_values=[-22.1, -22.2, -22.3],
            confidence=0.90,
        )
        series = pd.Series([-22.1, -22.2, -22.3, -22.4, -22.5])

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.data_category == DataCategory.GEOGRAPHIC

    def test_geographic_detection_for_coordinate_wkt_semantic_type(self, analyzer):
        """WKT coordinate semantics should stay geographic for map suggestions."""
        profile = ColumnProfile(
            name="geo_pt",
            dtype="object",
            semantic_type="location.coordinate",
            unique_ratio=0.66,
            null_ratio=0.01,
            sample_values=["POINT (166.45 -22.18)", "POINT (166.46 -22.19)"],
            confidence=1.0,
        )
        series = pd.Series(
            [
                "POINT (166.45 -22.18)",
                "POINT (166.46 -22.19)",
                "POINT (166.47 -22.20)",
            ]
        )

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.data_category == DataCategory.GEOGRAPHIC

    def test_temporal_detection(self, analyzer):
        """Test detection of temporal data."""
        profile = ColumnProfile(
            name="date_observation",
            dtype="datetime64[ns]",
            semantic_type=None,
            unique_ratio=0.80,
            null_ratio=0.0,
            sample_values=[],
            confidence=0.5,
        )
        series = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.data_category == DataCategory.TEMPORAL

    def test_discrete_numeric_detection(self, analyzer):
        """Test detection of discrete numeric data (counts)."""
        profile = ColumnProfile(
            name="count",
            dtype="int64",
            semantic_type="statistic.count",
            unique_ratio=0.15,
            null_ratio=0.0,
            sample_values=[1, 2, 3, 4, 5],
            confidence=0.70,
        )
        series = pd.Series([1, 2, 3, 4, 5, 1, 2, 3, 4, 5] * 5)

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.data_category == DataCategory.NUMERIC_DISCRETE


class TestFieldPurpose:
    """Tests for field purpose detection."""

    def test_measurement_purpose(
        self, analyzer, numeric_continuous_profile, elevation_series
    ):
        """Test detection of measurement purpose."""
        enriched = analyzer.enrich_profile(numeric_continuous_profile, elevation_series)
        assert enriched.field_purpose == FieldPurpose.MEASUREMENT

    def test_classification_purpose(
        self, analyzer, categorical_profile, species_series
    ):
        """Test detection of classification purpose."""
        enriched = analyzer.enrich_profile(categorical_profile, species_series)
        assert enriched.field_purpose == FieldPurpose.CLASSIFICATION

    def test_primary_key_purpose(self, analyzer, identifier_profile, id_series):
        """Test detection of primary key purpose."""
        enriched = analyzer.enrich_profile(identifier_profile, id_series)
        assert enriched.field_purpose == FieldPurpose.PRIMARY_KEY

    def test_foreign_key_purpose(self, analyzer):
        """Test detection of foreign key purpose."""
        profile = ColumnProfile(
            name="id_taxonref",
            dtype="int64",
            semantic_type="identifier.taxon",
            unique_ratio=0.15,
            null_ratio=0.0,
            sample_values=[12345, 12346, 12347],
            confidence=0.80,
        )
        series = pd.Series([12345, 12346, 12347] * 20)

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.field_purpose == FieldPurpose.FOREIGN_KEY

    def test_identifier_semantic_sets_foreign_key_purpose(self, analyzer):
        """Identifier semantics should mark repeated legacy IDs as foreign keys."""
        profile = ColumnProfile(
            name="idrb_n",
            dtype="object",
            semantic_type="identifier.record",
            unique_ratio=0.25,
            null_ratio=0.0,
            sample_values=["ngoila003", "ngoila004"],
            confidence=0.9,
        )
        series = pd.Series(["ngoila003", "ngoila003", "ngoila004", "ngoila005"])

        enriched = analyzer.enrich_profile(profile, series)

        assert enriched.field_purpose == FieldPurpose.FOREIGN_KEY

    def test_location_purpose(self, analyzer):
        """Test detection of location purpose."""
        profile = ColumnProfile(
            name="plot_id",
            dtype="object",
            semantic_type="location.plot",
            unique_ratio=0.10,
            null_ratio=0.0,
            sample_values=["PLOT_001", "PLOT_002"],
            confidence=0.75,
        )
        series = pd.Series(["PLOT_001", "PLOT_002"] * 50)

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.field_purpose == FieldPurpose.LOCATION

    def test_description_purpose(self, analyzer):
        """Test detection of description purpose (long text)."""
        profile = ColumnProfile(
            name="notes",
            dtype="object",
            semantic_type=None,
            unique_ratio=0.95,
            null_ratio=0.10,
            sample_values=["Long description about the observation..."],
            confidence=0.5,
        )
        series = pd.Series(
            ["This is a long description about the botanical observation in the field"]
            * 50
        )

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.field_purpose == FieldPurpose.DESCRIPTION


class TestBinsSuggestion:
    """Tests for bins suggestion."""

    def test_suggest_bins_quantiles(
        self, analyzer, numeric_continuous_profile, elevation_series
    ):
        """Test bins suggestion using quantiles."""
        enriched = analyzer.enrich_profile(numeric_continuous_profile, elevation_series)

        assert enriched.suggested_bins is not None
        assert len(enriched.suggested_bins) >= 2
        assert enriched.suggested_bins == sorted(enriched.suggested_bins)
        # Check min and max are included
        assert enriched.suggested_bins[0] == elevation_series.min()
        assert enriched.suggested_bins[-1] == elevation_series.max()

    def test_suggest_bins_no_variation(self, analyzer):
        """Test bins suggestion with no variation (constant values)."""
        profile = ColumnProfile(
            name="constant",
            dtype="float64",
            semantic_type=None,
            unique_ratio=0.01,
            null_ratio=0.0,
            sample_values=[100.0, 100.0, 100.0],
            confidence=0.5,
        )
        series = pd.Series([100.0] * 50)

        enriched = analyzer.enrich_profile(profile, series)
        # Should return None when no variation
        assert enriched.suggested_bins is None

    def test_suggest_bins_empty_series(self, analyzer):
        """Test bins suggestion with empty series."""
        profile = ColumnProfile(
            name="empty",
            dtype="float64",
            semantic_type=None,
            unique_ratio=0.0,
            null_ratio=1.0,
            sample_values=[],
            confidence=0.5,
        )
        series = pd.Series([], dtype=float)

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.suggested_bins is None


class TestLabelsSuggestion:
    """Tests for labels suggestion."""

    def test_suggest_labels_categorical(
        self, analyzer, categorical_profile, species_series
    ):
        """Test labels suggestion for categorical data."""
        enriched = analyzer.enrich_profile(categorical_profile, species_series)

        assert enriched.suggested_labels is not None
        assert len(enriched.suggested_labels) == 3
        assert "Species A" in enriched.suggested_labels
        assert "Species B" in enriched.suggested_labels
        assert "Species C" in enriched.suggested_labels

    def test_suggest_labels_top_20(self, analyzer):
        """Test labels suggestion returns max 20 categories."""
        profile = ColumnProfile(
            name="many_categories",
            dtype="object",
            semantic_type=None,
            unique_ratio=0.30,
            null_ratio=0.0,
            sample_values=[f"Cat_{i}" for i in range(30)],
            confidence=0.5,
        )
        # Create series with 30 categories
        categories = [f"Cat_{i}" for i in range(30)]
        series = pd.Series(categories * 10)

        enriched = analyzer.enrich_profile(profile, series)

        assert enriched.suggested_labels is not None
        assert len(enriched.suggested_labels) <= 20

    def test_suggest_labels_empty_series(self, analyzer):
        """Test labels suggestion with empty series."""
        profile = ColumnProfile(
            name="empty",
            dtype="object",
            semantic_type=None,
            unique_ratio=0.0,
            null_ratio=1.0,
            sample_values=[],
            confidence=0.5,
        )
        series = pd.Series([], dtype=object)

        enriched = analyzer.enrich_profile(profile, series)
        assert enriched.suggested_labels is None


class TestValueStatistics:
    """Tests for value statistics (cardinality, range)."""

    def test_cardinality(self, analyzer, categorical_profile, species_series):
        """Test cardinality calculation."""
        enriched = analyzer.enrich_profile(categorical_profile, species_series)
        assert enriched.cardinality == 3

    def test_value_range_numeric(
        self, analyzer, numeric_continuous_profile, elevation_series
    ):
        """Test value range for numeric data."""
        enriched = analyzer.enrich_profile(numeric_continuous_profile, elevation_series)

        assert enriched.value_range is not None
        assert enriched.value_range[0] == elevation_series.min()
        assert enriched.value_range[1] == elevation_series.max()

    def test_value_range_non_numeric(
        self, analyzer, categorical_profile, species_series
    ):
        """Test value range is None for non-numeric data."""
        enriched = analyzer.enrich_profile(categorical_profile, species_series)
        assert enriched.value_range is None


class TestEnrichedColumnProfile:
    """Tests for complete enriched profile."""

    def test_complete_enrichment(
        self, analyzer, numeric_continuous_profile, elevation_series
    ):
        """Test complete enrichment process."""
        enriched = analyzer.enrich_profile(numeric_continuous_profile, elevation_series)

        # Check all attributes are present
        assert enriched.name == "elevation"
        assert enriched.dtype == "float64"
        assert enriched.semantic_type == "measurement.elevation"
        assert enriched.data_category == DataCategory.NUMERIC_CONTINUOUS
        assert enriched.field_purpose == FieldPurpose.MEASUREMENT
        assert enriched.suggested_bins is not None
        assert enriched.cardinality > 0
        assert enriched.value_range is not None
        assert enriched.confidence == 0.90

    def test_enrichment_preserves_original(
        self, analyzer, numeric_continuous_profile, elevation_series
    ):
        """Test enrichment preserves original profile data."""
        enriched = analyzer.enrich_profile(numeric_continuous_profile, elevation_series)

        # Original attributes preserved
        assert enriched.name == numeric_continuous_profile.name
        assert enriched.dtype == numeric_continuous_profile.dtype
        assert enriched.semantic_type == numeric_continuous_profile.semantic_type
        assert enriched.unique_ratio == numeric_continuous_profile.unique_ratio
        assert enriched.null_ratio == numeric_continuous_profile.null_ratio
        assert enriched.confidence == numeric_continuous_profile.confidence
