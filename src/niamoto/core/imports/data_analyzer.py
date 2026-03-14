"""
Data analyzer for enriching column profiles with semantic metadata.

This module extends the ColumnProfile from DataProfiler with additional
metadata oriented towards transformer matching and configuration generation.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

import pandas as pd

from niamoto.core.imports.profiler import ColumnProfile

logger = logging.getLogger(__name__)


class DataCategory(str, Enum):
    """
    Data category for transformer matching.

    Categories are used to match columns with appropriate transformers
    based on the nature of the data.
    """

    NUMERIC_CONTINUOUS = "numeric_continuous"  # elevation, height, dbh
    NUMERIC_DISCRETE = "numeric_discrete"  # count, age (integer)
    CATEGORICAL = "categorical"  # species, family, status
    CATEGORICAL_HIGH_CARD = "categorical_high_card"  # IDs (many unique values)
    BOOLEAN = "boolean"  # true/false
    TEMPORAL = "temporal"  # dates
    GEOGRAPHIC = "geographic"  # lat/lon, geometry
    TEXT = "text"  # descriptions
    IDENTIFIER = "identifier"  # primary keys


class FieldPurpose(str, Enum):
    """
    Typical usage purpose of the field.

    Purpose helps determine which transformers are most relevant
    for the field's role in the dataset.
    """

    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    MEASUREMENT = "measurement"
    CLASSIFICATION = "classification"
    LOCATION = "location"
    DESCRIPTION = "description"
    METADATA = "metadata"


@dataclass
class EnrichedColumnProfile:
    """
    Extension of ColumnProfile with metadata for transformer matching.

    Attributes:
        name: Column name
        dtype: Pandas dtype (int64, float64, object...)
        semantic_type: Semantic type from profiler (taxonomy.genus, location.latitude...)
        unique_ratio: Ratio of unique values (0.0 to 1.0)
        null_ratio: Ratio of null values (0.0 to 1.0)
        sample_values: Sample values from the column
        confidence: ML detection confidence (0.0 to 1.0)
        data_category: High-level data category for matching
        field_purpose: Typical usage purpose
        suggested_bins: Suggested bins for numeric continuous data
        suggested_labels: Suggested labels for categorical data
        cardinality: Number of unique values
        value_range: Min/max range for numeric data
    """

    # Inherited from ColumnProfile
    name: str
    dtype: str
    semantic_type: Optional[str]
    unique_ratio: float
    null_ratio: float
    sample_values: List
    confidence: float

    # New enrichments
    data_category: DataCategory
    field_purpose: FieldPurpose
    suggested_bins: Optional[List[float]] = None
    suggested_labels: Optional[List[str]] = None
    cardinality: int = 0
    value_range: Optional[Tuple[float, float]] = None


class DataAnalyzer:
    """
    Analyzer to enrich ColumnProfile with transformer-oriented metadata.

    The analyzer takes profiles from DataProfiler and adds:
    - Data category (continuous, categorical, geographic...)
    - Field purpose (measurement, classification, location...)
    - Suggested bins for numeric data
    - Suggested labels for categorical data
    - Value statistics (cardinality, range)
    """

    def enrich_profile(
        self, col_profile: ColumnProfile, series: pd.Series
    ) -> EnrichedColumnProfile:
        """
        Enrich a ColumnProfile with additional metadata.

        Args:
            col_profile: Profile from DataProfiler
            series: Pandas series of the column data

        Returns:
            EnrichedColumnProfile with all metadata
        """
        # Pre-compute common stats once to avoid redundant column scans
        clean = series.dropna()
        cardinality = clean.nunique() if not clean.empty else 0

        # Detect data category
        data_category = self._detect_data_category(col_profile, series)

        # Detect field purpose
        field_purpose = self._detect_field_purpose(col_profile, series)

        # Get value range for numeric data (reuse pre-computed clean series)
        value_range = None
        if pd.api.types.is_numeric_dtype(series) and not clean.empty:
            value_range = (float(clean.min()), float(clean.max()))

        # Suggest bins if numeric continuous
        suggested_bins = None
        if data_category == DataCategory.NUMERIC_CONTINUOUS:
            suggested_bins = self._suggest_bins(series)

        # Suggest labels if categorical
        suggested_labels = None
        if data_category in (
            DataCategory.CATEGORICAL,
            DataCategory.CATEGORICAL_HIGH_CARD,
        ):
            suggested_labels = self._suggest_labels(series)

        return EnrichedColumnProfile(
            name=col_profile.name,
            dtype=col_profile.dtype,
            semantic_type=col_profile.semantic_type,
            unique_ratio=col_profile.unique_ratio,
            null_ratio=col_profile.null_ratio,
            sample_values=col_profile.sample_values,
            confidence=col_profile.confidence,
            data_category=data_category,
            field_purpose=field_purpose,
            suggested_bins=suggested_bins,
            suggested_labels=suggested_labels,
            cardinality=cardinality,
            value_range=value_range,
        )

    def _detect_data_category(
        self, col_profile: ColumnProfile, series: pd.Series
    ) -> DataCategory:
        """
        Detect high-level data category.

        Args:
            col_profile: Column profile from DataProfiler
            series: Pandas series

        Returns:
            DataCategory enum value
        """
        # Identifier detection (highest priority - skip useless fields)
        # Hybrid approach: name patterns + statistics + sequential detection
        if self._is_likely_identifier(col_profile, series):
            return DataCategory.IDENTIFIER

        # Geographic (high priority due to special handling)
        # Only treat actual geometry or coordinate types as geographic
        # NOT reference types like location.plot or location.locality (which are just names)
        if col_profile.semantic_type in ["geometry", "location.coordinates"]:
            return DataCategory.GEOGRAPHIC
        if col_profile.semantic_type in ["location.latitude", "location.longitude"]:
            return DataCategory.GEOGRAPHIC

        # Temporal
        if "datetime" in col_profile.dtype or "date" in col_profile.dtype.lower():
            return DataCategory.TEMPORAL

        # Numeric types
        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if clean.empty:
                return DataCategory.NUMERIC_CONTINUOUS

            # Boolean disguised as 0/1 (must have exactly 2 unique values)
            unique_values = set(clean.unique())
            if unique_values == {0, 1} or unique_values == {0} or unique_values == {1}:
                return DataCategory.BOOLEAN

            # Check if all values are integers
            is_integer = (clean % 1 == 0).all()

            if is_integer:
                # High cardinality integers are likely IDs
                if col_profile.unique_ratio > 0.8:
                    return DataCategory.CATEGORICAL_HIGH_CARD

                # Check if column name or semantic type suggests a count/measurement
                name_lower = col_profile.name.lower()
                semantic = (col_profile.semantic_type or "").lower()
                is_count_like = (
                    any(
                        term in name_lower
                        for term in ["count", "total", "sum", "number", "nb_", "num_"]
                    )
                    or "count" in semantic
                    or "statistic" in semantic
                )

                # Very few unique values (≤ 10) = likely categorical codes
                # UNLESS the name/semantic suggests it's a count/measurement
                unique_count = len(unique_values)
                if unique_count <= 10 and not is_count_like:
                    return DataCategory.CATEGORICAL

                # Low cardinality integers are discrete numeric
                return DataCategory.NUMERIC_DISCRETE

            # Float = continuous
            return DataCategory.NUMERIC_CONTINUOUS

        # Non-numeric types
        # Check for identifiers (high unique ratio)
        if col_profile.unique_ratio > 0.95:
            return DataCategory.IDENTIFIER

        # Low unique ratio = categorical
        if col_profile.unique_ratio < 0.5:
            return DataCategory.CATEGORICAL

        # Medium unique ratio with high cardinality
        if col_profile.unique_ratio >= 0.5:
            return DataCategory.CATEGORICAL_HIGH_CARD

        # Default to text
        return DataCategory.TEXT

    def _detect_field_purpose(
        self, col_profile: ColumnProfile, series: pd.Series
    ) -> FieldPurpose:
        """
        Detect the typical usage purpose of the field.

        Args:
            col_profile: Column profile
            series: Pandas series

        Returns:
            FieldPurpose enum value
        """
        name_lower = col_profile.name.lower()
        semantic = col_profile.semantic_type or ""

        # Location (check semantic type first to avoid confusion with _id suffix)
        if "location" in semantic or any(
            pattern in name_lower
            for pattern in ["lat", "lon", "coord", "geo", "location", "plot"]
        ):
            return FieldPurpose.LOCATION

        # Primary/Foreign keys (based on name patterns)
        if any(pattern in name_lower for pattern in ["_id", "id_", "identifier"]):
            if col_profile.unique_ratio > 0.95:
                return FieldPurpose.PRIMARY_KEY
            return FieldPurpose.FOREIGN_KEY

        # Measurement (from semantic type)
        if "measurement" in semantic:
            return FieldPurpose.MEASUREMENT

        # Check for measurement-like names
        if any(
            pattern in name_lower
            for pattern in [
                "height",
                "dbh",
                "diameter",
                "elevation",
                "altitude",
                "depth",
                "width",
                "length",
                "area",
                "volume",
                "weight",
                "temperature",
                "rainfall",
            ]
        ):
            return FieldPurpose.MEASUREMENT

        # Classification
        if "taxonomy" in semantic or any(
            pattern in name_lower
            for pattern in [
                "species",
                "genus",
                "family",
                "taxon",
                "class",
                "order",
                "status",
                "category",
                "type",
            ]
        ):
            return FieldPurpose.CLASSIFICATION

        # Description (long text fields)
        if pd.api.types.is_string_dtype(series):
            clean = series.dropna()
            if not clean.empty:
                avg_length = clean.astype(str).str.len().mean()
                if avg_length > 50:  # Arbitrary threshold for descriptions
                    return FieldPurpose.DESCRIPTION

        # Default to metadata
        return FieldPurpose.METADATA

    def _is_likely_identifier(
        self, col_profile: ColumnProfile, series: pd.Series
    ) -> bool:
        """
        Detect if a column is likely an identifier (ID, UUID, etc.).

        Uses a hybrid approach combining:
        1. Column name patterns + high unique ratio
        2. Very high unique ratio alone (>= 0.99)
        3. Sequential integer pattern detection

        Args:
            col_profile: Column profile
            series: Pandas series

        Returns:
            True if the column is likely an identifier
        """
        name_lower = col_profile.name.lower()
        unique_ratio = col_profile.unique_ratio

        # 1. Column name patterns suggesting identifier
        is_identifier_name = (
            name_lower == "id"
            or name_lower.endswith("_id")
            or name_lower.startswith("id_")
            or "uuid" in name_lower
            or "identifier" in name_lower
            or name_lower in ("pk", "oid", "rowid", "index")
        )

        # Name pattern + moderately high unique ratio
        if is_identifier_name and unique_ratio > 0.8:
            return True

        # 2. Very high unique ratio alone (almost all values unique)
        if unique_ratio >= 0.99:
            return True

        # 3. Sequential integer pattern detection
        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if not clean.empty and len(clean) > 10:
                # Check if all values are integers
                is_integer = (clean % 1 == 0).all()
                if is_integer:
                    min_val = int(clean.min())
                    max_val = int(clean.max())
                    count = len(clean)

                    # Sequential pattern: min is 0 or 1, max is close to count
                    if min_val in (0, 1) and abs(max_val - count) <= count * 0.1:
                        return True

                    # Perfect sequential: exactly count unique values in range
                    if clean.nunique() == count and max_val - min_val + 1 == count:
                        return True

        return False

    def _suggest_bins(self, series: pd.Series) -> Optional[List[float]]:
        """
        Suggest bins for numeric continuous data using quantiles.

        Args:
            series: Pandas series with numeric data

        Returns:
            List of bin edges or None if not applicable
        """
        clean = series.dropna()
        if clean.empty:
            return None

        # Check if data has enough variation
        if clean.std() == 0:
            return None

        # Use quantiles for better distribution
        # 5 bins = 4 splits + min and max
        quantiles = [0, 0.25, 0.5, 0.75, 1.0]
        bins = [float(clean.quantile(q)) for q in quantiles]

        # Remove duplicates (can happen if data is heavily skewed)
        bins = sorted(list(set(bins)))

        # Need at least 2 bins
        if len(bins) < 2:
            return [float(clean.min()), float(clean.max())]

        return bins

    def _suggest_labels(self, series: pd.Series) -> Optional[List[str]]:
        """
        Suggest labels for categorical data (top categories).

        Args:
            series: Pandas series with categorical data

        Returns:
            List of category labels (top 20) or None
        """
        clean = series.dropna()
        if clean.empty:
            return None

        # Get value counts
        value_counts = clean.value_counts()

        # Return top 20 categories
        top_categories = value_counts.head(20).index.tolist()

        # Convert to strings
        return [str(cat) for cat in top_categories]
