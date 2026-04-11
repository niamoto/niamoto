"""
Transformer suggester for automatic configuration generation.

This module matches enriched column profiles with appropriate transformers
and generates pre-filled configurations ready for user validation.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)

logger = logging.getLogger(__name__)


@dataclass
class TransformerSuggestion:
    """
    Suggestion for a compatible transformer with pre-filled config.

    Attributes:
        transformer_name: Name of the transformer plugin
        confidence: Confidence score (0.0 to 1.0)
        reason: Human-readable explanation of why this transformer was suggested
        pre_filled_config: Complete configuration ready to use
        column_name: Name of the column this suggestion applies to
    """

    transformer_name: str
    confidence: float
    reason: str
    pre_filled_config: Dict[str, Any]
    column_name: str


class TransformerSuggester:
    """
    Suggests transformers based on enriched column profiles.

    The suggester uses a mapping from data categories to appropriate transformers,
    then generates pre-filled configurations based on column metadata.
    """

    # Mapping from data category to compatible transformers
    # Ordered by typical priority (most common/useful first)
    CATEGORY_TO_TRANSFORMERS = {
        DataCategory.NUMERIC_CONTINUOUS: [
            "binned_distribution",
            "statistical_summary",
        ],
        DataCategory.NUMERIC_DISCRETE: [
            "binned_distribution",
            "statistical_summary",
        ],
        DataCategory.CATEGORICAL: [
            "categorical_distribution",
            "top_ranking",
        ],
        DataCategory.CATEGORICAL_HIGH_CARD: [
            "top_ranking",
        ],
        DataCategory.BOOLEAN: [
            "binary_counter",
        ],
        DataCategory.GEOGRAPHIC: [
            "geospatial_extractor",
        ],
        DataCategory.TEMPORAL: [
            "time_series_analysis",
        ],
        DataCategory.IDENTIFIER: [
            "top_ranking",  # Useful for foreign keys (e.g., id_taxonref -> species ranking)
        ],
        DataCategory.TEXT: [],  # No transformers for text descriptions
    }

    def __init__(self):
        """Initialize TransformerSuggester."""
        pass

    def suggest_for_dataset(
        self,
        enriched_profiles: List[EnrichedColumnProfile],
        source_entity: str,
    ) -> Dict[str, List[TransformerSuggestion]]:
        """
        Suggest transformers for all columns in a dataset.

        Args:
            enriched_profiles: List of enriched column profiles
            source_entity: Name of the source entity (e.g., "occurrences")

        Returns:
            Dict mapping column names to lists of transformer suggestions
        """
        suggestions_by_column = {}

        for profile in enriched_profiles:
            suggestions = self.suggest_transformers(profile, source_entity)
            if suggestions:
                suggestions_by_column[profile.name] = suggestions
                logger.info(
                    f"Generated {len(suggestions)} suggestions for column '{profile.name}'"
                )

        return suggestions_by_column

    def suggest_transformers(
        self,
        profile: EnrichedColumnProfile,
        source_entity: str,
    ) -> List[TransformerSuggestion]:
        """
        Suggest transformers for a single column.

        Args:
            profile: Enriched column profile
            source_entity: Name of the source entity

        Returns:
            List of transformer suggestions sorted by confidence
        """
        suggestions = []

        # Get applicable transformers for this data category
        transformer_names = self.CATEGORY_TO_TRANSFORMERS.get(profile.data_category, [])

        if not transformer_names:
            logger.debug(
                f"No transformers available for category {profile.data_category}"
            )
            return suggestions

        # Generate suggestion for each applicable transformer
        for transformer_name in transformer_names:
            if self._should_skip_measurement_transformer(transformer_name, profile):
                logger.debug(
                    "Skipping %s for identifier-like column %s",
                    transformer_name,
                    profile.name,
                )
                continue

            config = self._generate_config(transformer_name, profile, source_entity)

            if config is None:
                logger.debug(
                    f"Could not generate config for {transformer_name} on {profile.name}"
                )
                continue

            confidence = self._calculate_confidence(transformer_name, profile)
            reason = self._generate_reason(transformer_name, profile)

            suggestions.append(
                TransformerSuggestion(
                    transformer_name=transformer_name,
                    confidence=confidence,
                    reason=reason,
                    pre_filled_config=config,
                    column_name=profile.name,
                )
            )

        # Sort by confidence (descending)
        suggestions.sort(key=lambda x: -x.confidence)

        return suggestions

    def _should_skip_measurement_transformer(
        self, transformer_name: str, profile: EnrichedColumnProfile
    ) -> bool:
        """Block measurement widgets on identifier-like columns."""
        if transformer_name not in {"binned_distribution", "statistical_summary"}:
            return False

        semantic = (profile.semantic_type or "").lower()
        name = profile.name.lower()
        is_identifier_name = (
            name == "id"
            or name.endswith("_id")
            or name.startswith("id_")
            or (name.startswith("id") and any(ch in name[2:] for ch in "_0123456789"))
            or "uuid" in name
            or "identifier" in name
            or name in {"pk", "oid", "rowid", "index"}
        )

        return (
            profile.data_category == DataCategory.IDENTIFIER
            or profile.field_purpose
            in {  # Defensive against stale semantic profiles in metadata
                FieldPurpose.PRIMARY_KEY,
                FieldPurpose.FOREIGN_KEY,
            }
            or semantic.startswith("identifier")
            or is_identifier_name
        )

    def _generate_config(
        self,
        transformer_name: str,
        profile: EnrichedColumnProfile,
        source_entity: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate pre-filled configuration for a transformer.

        Args:
            transformer_name: Name of the transformer
            profile: Enriched column profile
            source_entity: Name of source entity

        Returns:
            Configuration dict or None if cannot generate
        """
        # Dispatch table for config generators
        config_generators = {
            "binned_distribution": self._config_binned_distribution,
            "statistical_summary": self._config_statistical_summary,
            "categorical_distribution": self._config_categorical_distribution,
            "top_ranking": self._config_top_ranking,
            "binary_counter": self._config_binary_counter,
            "geospatial_extractor": self._config_geospatial_extractor,
            "time_series_analysis": self._config_time_series_analysis,
        }

        generator = config_generators.get(transformer_name)
        if generator is None:
            logger.warning(f"Unknown transformer: {transformer_name}")
            return None

        return generator(profile, source_entity)

    def _config_binned_distribution(
        self, profile: EnrichedColumnProfile, source_entity: str
    ) -> Optional[Dict[str, Any]]:
        """Generate config for binned_distribution.

        Returns None if no valid bins are available.
        """
        # Need at least 2 bin edges to create meaningful bins
        if not profile.suggested_bins or len(profile.suggested_bins) < 2:
            return None

        return {
            "plugin": "binned_distribution",
            "params": {
                "source": source_entity,
                "field": profile.name,
                "bins": profile.suggested_bins,
                "labels": None,
                "include_percentages": False,
            },
        }

    def _config_statistical_summary(
        self, profile: EnrichedColumnProfile, source_entity: str
    ) -> Dict[str, Any]:
        """Generate config for statistical_summary."""
        # Infer units from semantic type or name
        units = self._infer_units(profile)

        # Determine max_value for gauge display
        max_value = 100  # Default
        if profile.value_range:
            max_value = (
                int(profile.value_range[1]) if profile.value_range[1] > 0 else 100
            )

        return {
            "plugin": "statistical_summary",
            "params": {
                "source": source_entity,
                "field": profile.name,
                "stats": ["min", "mean", "max", "median", "std"],
                "units": units,
                "max_value": max_value,
            },
        }

    def _config_categorical_distribution(
        self, profile: EnrichedColumnProfile, source_entity: str
    ) -> Dict[str, Any]:
        """Generate config for categorical_distribution."""
        return {
            "plugin": "categorical_distribution",
            "params": {
                "source": source_entity,
                "field": profile.name,
                "categories": [],  # Auto-detect
                "labels": profile.suggested_labels or [],
            },
        }

    def _config_top_ranking(
        self, profile: EnrichedColumnProfile, source_entity: str
    ) -> Dict[str, Any]:
        """Generate config for top_ranking."""
        # Determine count based on cardinality
        # Target ~10% of unique values, minimum 5, maximum 10
        # But never more than actual cardinality
        target_count = max(5, profile.cardinality // 10)
        count = min(10, target_count, profile.cardinality)

        return {
            "plugin": "top_ranking",
            "params": {
                "source": source_entity,
                "field": profile.name,
                "count": count,
                "mode": "direct",
                "aggregate_function": "count",
            },
        }

    def _config_binary_counter(
        self, profile: EnrichedColumnProfile, source_entity: str
    ) -> Dict[str, Any]:
        """Generate config for binary_counter."""
        return {
            "plugin": "binary_counter",
            "params": {
                "source": source_entity,
                "field": profile.name,
            },
        }

    def _config_geospatial_extractor(
        self, profile: EnrichedColumnProfile, source_entity: str
    ) -> Dict[str, Any]:
        """Generate config for geospatial_extractor."""
        return {
            "plugin": "geospatial_extractor",
            "params": {
                "source": source_entity,
                "field": profile.name,
                "format": "geojson",
                "properties": [],
            },
        }

    def _config_time_series_analysis(
        self, profile: EnrichedColumnProfile, source_entity: str
    ) -> Dict[str, Any]:
        """Generate config for time_series_analysis."""
        return {
            "plugin": "time_series_analysis",
            "params": {
                "source": source_entity,
                "field": profile.name,
                "period": "month",
            },
        }

    def _infer_units(self, profile: EnrichedColumnProfile) -> str:
        """
        Infer measurement units from semantic type or field name.

        Args:
            profile: Enriched column profile

        Returns:
            Unit string (e.g., "m", "cm", "mm")
        """
        name_lower = profile.name.lower()
        semantic = profile.semantic_type or ""

        # From semantic type
        if "elevation" in semantic or "altitude" in semantic or "height" in semantic:
            return "m"
        elif "diameter" in semantic or "dbh" in name_lower:
            return "cm"
        elif "rainfall" in semantic or "precipitation" in semantic:
            return "mm"
        elif "temperature" in semantic:
            return "°C"

        # From field name
        if any(
            pattern in name_lower for pattern in ["elevation", "altitude", "height"]
        ):
            return "m"
        elif "dbh" in name_lower or "diameter" in name_lower:
            return "cm"
        elif "rain" in name_lower:
            return "mm"

        return ""  # No unit

    def _calculate_confidence(
        self, transformer_name: str, profile: EnrichedColumnProfile
    ) -> float:
        """
        Calculate confidence score for a suggestion.

        Args:
            transformer_name: Name of the transformer
            profile: Enriched column profile

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Start with base confidence from ML detection
        base_confidence = profile.confidence

        # Quality factor based on null ratio
        quality_factor = 1.0 - (profile.null_ratio * 0.3)

        # Category match boost
        category_match_boost = 0.0
        expected_transformers = self.CATEGORY_TO_TRANSFORMERS.get(
            profile.data_category, []
        )
        if transformer_name in expected_transformers:
            category_match_boost = 0.2

        # Specific boosts
        if transformer_name == "binned_distribution":
            if profile.suggested_bins and len(profile.suggested_bins) >= 3:
                category_match_boost += 0.1

        if transformer_name == "categorical_distribution":
            if profile.cardinality > 2 and profile.cardinality < 50:
                category_match_boost += 0.1

        if transformer_name == "top_ranking":
            if profile.cardinality > 10:
                category_match_boost += 0.1

        # Combine factors
        confidence = min(1.0, base_confidence * quality_factor + category_match_boost)

        return round(confidence, 2)

    def _generate_reason(
        self, transformer_name: str, profile: EnrichedColumnProfile
    ) -> str:
        """
        Generate human-readable reason for suggestion.

        Args:
            transformer_name: Name of the transformer
            profile: Enriched column profile

        Returns:
            Reason string
        """
        parts = []

        # Data category
        parts.append(f"Type: {profile.data_category.value}")

        # Semantic type
        if profile.semantic_type:
            parts.append(f"Sémantique: {profile.semantic_type}")

        # Specific reasons
        if transformer_name == "binned_distribution":
            if profile.suggested_bins:
                parts.append(f"{len(profile.suggested_bins)} bins suggérés")

        if transformer_name == "categorical_distribution":
            parts.append(f"{profile.cardinality} catégories")

        if transformer_name == "top_ranking":
            parts.append(f"Top N des {profile.cardinality} valeurs")

        if transformer_name == "statistical_summary":
            parts.append("Statistiques descriptives")

        return " | ".join(parts)
