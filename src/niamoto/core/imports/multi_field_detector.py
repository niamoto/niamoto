"""
Multi-field pattern detector for combined widget suggestions.

This module detects patterns across multiple columns that could form
meaningful combined visualizations (e.g., phenology from month + flower + fruit).

The detector analyzes selected fields and suggests appropriate transformers
and widgets that combine them intelligently.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)

logger = logging.getLogger(__name__)


class MultiFieldPatternType(str, Enum):
    """Types of multi-field patterns that can be detected."""

    PHENOLOGY = "phenology"  # temporal + boolean states (flower, fruit)
    ALLOMETRY = "allometry"  # numeric dimensions (dbh, height)
    TEMPORAL_SERIES = "temporal_series"  # temporal + numeric measurements
    CATEGORICAL_COMPARISON = "categorical_comparison"  # multiple categoricals
    BOOLEAN_COMPARISON = "boolean_comparison"  # multiple booleans
    NUMERIC_CORRELATION = "numeric_correlation"  # 2 numeric fields
    TRAIT_COMPARISON = "trait_comparison"  # functional traits (leaf, wood, bark)


@dataclass
class MultiFieldPattern:
    """A detected multi-field pattern with suggested widget configuration."""

    pattern_type: MultiFieldPatternType
    name: str
    description: str
    fields: List[str]
    field_roles: Dict[str, str]  # field_name -> role (time_axis, series, x, y, etc.)
    confidence: float
    transformer_plugin: str
    transformer_params: Dict[str, Any]
    widget_plugin: str
    widget_params: Dict[str, Any]
    is_recommended: bool = False


# Keywords for detecting semantic field groups
PHENOLOGY_KEYWORDS = {
    "temporal": ["month", "mois", "date", "period", "saison", "season"],
    # States must be exact field names or very specific patterns
    # Avoid generic words like "leaf" which could match "leaf_area"
    "states": [
        "flower",
        "fruit",
        "fleur",
        "fertile",
        "sterile",
    ],
}

DIMENSION_KEYWORDS = [
    "dbh",
    "height",
    "diameter",
    "width",
    "length",
    "hauteur",
    "diametre",
    "largeur",
    "longueur",
    "circumference",
    "circonference",
]

TRAIT_KEYWORDS = [
    "leaf_area",
    "leaf_sla",
    "leaf_ldmc",
    "leaf_thickness",
    "wood_density",
    "bark_thickness",
]


class MultiFieldPatternDetector:
    """
    Detects patterns across multiple columns for combined widgets.

    Usage:
        detector = MultiFieldPatternDetector()

        # From user selection
        suggestions = detector.suggest_for_selection(selected_profiles)

        # Proactive detection across all columns
        groups = detector.detect_semantic_groups(all_profiles)
    """

    def __init__(self):
        self.pattern_detectors = [
            self._detect_phenology_pattern,
            self._detect_allometry_pattern,
            self._detect_trait_comparison_pattern,
            self._detect_temporal_series_pattern,
            self._detect_boolean_comparison_pattern,
            self._detect_numeric_correlation_pattern,
        ]

    def suggest_for_selection(
        self,
        selected_profiles: List[EnrichedColumnProfile],
        source_name: str = "occurrences",
    ) -> List[MultiFieldPattern]:
        """
        Generate widget suggestions for a user-selected set of fields.

        Args:
            selected_profiles: List of column profiles selected by user
            source_name: Name of the data source

        Returns:
            List of possible combined widget patterns, sorted by relevance
        """
        if len(selected_profiles) < 2:
            return []

        suggestions = []

        # Try each pattern detector
        for detector in self.pattern_detectors:
            try:
                pattern = detector(selected_profiles, source_name)
                if pattern:
                    suggestions.append(pattern)
            except Exception as e:
                logger.warning(f"Pattern detector failed: {e}")

        # Sort by confidence (highest first)
        suggestions.sort(key=lambda p: -p.confidence)

        # Mark the best one as recommended
        if suggestions:
            suggestions[0].is_recommended = True

        return suggestions

    def detect_semantic_groups(
        self,
        all_profiles: List[EnrichedColumnProfile],
    ) -> List[Dict[str, Any]]:
        """
        Proactively detect semantic groups that could form combined widgets.

        This is used to suggest "These fields could be combined" in the UI.

        Args:
            all_profiles: All column profiles from the entity

        Returns:
            List of detected groups with their suggested patterns
        """
        groups = []

        # Detect phenology group
        phenology_group = self._find_phenology_group(all_profiles)
        if phenology_group:
            groups.append(phenology_group)

        # Detect dimension/allometry group
        dimension_group = self._find_dimension_group(all_profiles)
        if dimension_group:
            groups.append(dimension_group)

        # Detect leaf traits group
        trait_group = self._find_trait_group(all_profiles)
        if trait_group:
            groups.append(trait_group)

        return groups

    # =========================================================================
    # Pattern Detectors
    # =========================================================================

    def _detect_phenology_pattern(
        self,
        profiles: List[EnrichedColumnProfile],
        source_name: str,
    ) -> Optional[MultiFieldPattern]:
        """
        Detect phenology pattern: temporal field + boolean/categorical states.

        Example: month_obs + flower + fruit
        """
        # Find temporal field
        temporal_fields = [
            p
            for p in profiles
            if p.data_category == DataCategory.TEMPORAL
            or any(kw in p.name.lower() for kw in PHENOLOGY_KEYWORDS["temporal"])
        ]

        # Find phenology state fields (boolean or categorical with phenology keywords)
        state_fields = [
            p
            for p in profiles
            if (
                p.data_category == DataCategory.BOOLEAN
                or any(kw in p.name.lower() for kw in PHENOLOGY_KEYWORDS["states"])
            )
            and p not in temporal_fields
        ]

        if not temporal_fields or len(state_fields) < 1:
            return None

        temporal = temporal_fields[0]
        states = state_fields[:4]  # Max 4 series for readability

        # Build field mapping for time_series_analysis
        fields_mapping = {s.name: s.name for s in states}

        # Generate colors for each state
        color_palette = ["#FFB74D", "#81C784", "#64B5F6", "#BA68C8"]
        color_map = {
            s.name: color_palette[i % len(color_palette)] for i, s in enumerate(states)
        }

        return MultiFieldPattern(
            pattern_type=MultiFieldPatternType.PHENOLOGY,
            name="Phénologie",
            description=f"Distribution temporelle de {', '.join(s.name for s in states)} par {temporal.name}",
            fields=[temporal.name] + [s.name for s in states],
            field_roles={
                temporal.name: "time_axis",
                **{s.name: "series" for s in states},
            },
            confidence=0.90 if len(states) >= 2 else 0.75,
            transformer_plugin="time_series_analysis",
            transformer_params={
                "source": source_name,
                "fields": fields_mapping,
                "time_field": temporal.name,
                "labels": [
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                ],
            },
            widget_plugin="bar_plot",
            widget_params={
                "title": "Phénologie",
                "description": f"Distribution temporelle par {temporal.name}",
                "transform": "monthly_data",
                "transform_params": {
                    "data_field": "month_data",
                    "labels_field": "labels",
                    "melt": True,
                },
                "x_axis": "labels",
                "y_axis": "value",
                "color_field": "series",
                "barmode": "group",
                "orientation": "v",
                "labels": {
                    "x_axis": "Mois",
                    "y_axis": "Fréquence",
                    "color_field": "État",
                },
                "color_discrete_map": color_map,
            },
        )

    def _detect_allometry_pattern(
        self,
        profiles: List[EnrichedColumnProfile],
        source_name: str,
    ) -> Optional[MultiFieldPattern]:
        """
        Detect allometry pattern: two numeric dimension fields.

        Example: dbh + height for allometric relationships
        """
        # Find dimension fields
        dimension_fields = [
            p
            for p in profiles
            if p.data_category
            in (DataCategory.NUMERIC_CONTINUOUS, DataCategory.NUMERIC_DISCRETE)
            and any(kw in p.name.lower() for kw in DIMENSION_KEYWORDS)
        ]

        if len(dimension_fields) < 2:
            return None

        x_field = dimension_fields[0]
        y_field = dimension_fields[1]

        return MultiFieldPattern(
            pattern_type=MultiFieldPatternType.ALLOMETRY,
            name="Relation allométrique",
            description=f"Relation entre {x_field.name} et {y_field.name}",
            fields=[x_field.name, y_field.name],
            field_roles={
                x_field.name: "x_axis",
                y_field.name: "y_axis",
            },
            confidence=0.85,
            transformer_plugin="scatter_analysis",
            transformer_params={
                "source": source_name,
                "x_field": x_field.name,
                "y_field": y_field.name,
            },
            widget_plugin="scatter_plot",
            widget_params={
                "title": f"Relation {x_field.name} - {y_field.name}",
                "description": "Relation allométrique",
                "x_axis": x_field.name,
                "y_axis": y_field.name,
                "labels": {
                    "x_axis": x_field.name.upper(),
                    "y_axis": y_field.name.capitalize(),
                },
            },
        )

    def _detect_trait_comparison_pattern(
        self,
        profiles: List[EnrichedColumnProfile],
        source_name: str,
    ) -> Optional[MultiFieldPattern]:
        """
        Detect functional trait comparison: multiple trait fields.

        Example: leaf_sla + leaf_area + leaf_ldmc for trait analysis
        """
        # Find trait fields by keyword matching
        trait_fields = [
            p
            for p in profiles
            if p.data_category
            in (DataCategory.NUMERIC_CONTINUOUS, DataCategory.NUMERIC_DISCRETE)
            and any(kw in p.name.lower() for kw in TRAIT_KEYWORDS)
        ]

        # Also accept any numeric fields if user selected them together
        # (they might be traits without standard naming)
        if len(trait_fields) < 2:
            # Fall back to any numeric fields
            numeric_fields = [
                p
                for p in profiles
                if p.data_category
                in (DataCategory.NUMERIC_CONTINUOUS, DataCategory.NUMERIC_DISCRETE)
            ]
            # Only use fallback if at least one has a trait keyword
            if any(
                any(kw in p.name.lower() for kw in TRAIT_KEYWORDS)
                for p in numeric_fields
            ):
                trait_fields = numeric_fields

        if len(trait_fields) < 2:
            return None

        fields = trait_fields[:6]  # Max 6 traits for readability

        # Build field configs for field_aggregator with stats transformation
        field_configs = [
            {
                "source": source_name,
                "field": f.name,
                "target": f.name,
                "transformation": "stats",
            }
            for f in fields
        ]

        # Build widget items for info_grid with stats format
        widget_items = [
            {
                "label": f.name.replace("_", " ").title(),
                "source": f"{f.name}.value",
                "format": "stats",
            }
            for f in fields
        ]

        return MultiFieldPattern(
            pattern_type=MultiFieldPatternType.TRAIT_COMPARISON,
            name="Comparaison de traits",
            description=f"Comparaison des traits: {', '.join(f.name for f in fields)}",
            fields=[f.name for f in fields],
            field_roles={f.name: "trait" for f in fields},
            confidence=0.85 if len(fields) >= 3 else 0.75,
            transformer_plugin="field_aggregator",
            transformer_params={
                "fields": field_configs,
            },
            widget_plugin="info_grid",
            widget_params={
                "title": "Traits fonctionnels",
                "description": f"Statistiques des traits: {', '.join(f.name for f in fields)}",
                "items": widget_items,
                "grid_columns": min(len(fields), 3),
            },
        )

    def _detect_temporal_series_pattern(
        self,
        profiles: List[EnrichedColumnProfile],
        source_name: str,
    ) -> Optional[MultiFieldPattern]:
        """
        Detect temporal series: temporal field + numeric measurements.

        Example: date + elevation measurements over time
        """
        temporal_fields = [
            p
            for p in profiles
            if p.data_category == DataCategory.TEMPORAL
            or any(kw in p.name.lower() for kw in ["date", "time", "year", "month"])
        ]

        numeric_fields = [
            p
            for p in profiles
            if p.data_category
            in (DataCategory.NUMERIC_CONTINUOUS, DataCategory.NUMERIC_DISCRETE)
            and p.field_purpose == FieldPurpose.MEASUREMENT
            and p not in temporal_fields
        ]

        if not temporal_fields or not numeric_fields:
            return None

        temporal = temporal_fields[0]
        measurements = numeric_fields[:3]

        return MultiFieldPattern(
            pattern_type=MultiFieldPatternType.TEMPORAL_SERIES,
            name="Série temporelle",
            description=f"Évolution de {', '.join(m.name for m in measurements)} dans le temps",
            fields=[temporal.name] + [m.name for m in measurements],
            field_roles={
                temporal.name: "time_axis",
                **{m.name: "measurement" for m in measurements},
            },
            confidence=0.80,
            transformer_plugin="time_series_analysis",
            transformer_params={
                "source": source_name,
                "time_field": temporal.name,
                "value_fields": [m.name for m in measurements],
            },
            widget_plugin="bar_plot",
            widget_params={
                "title": "Évolution temporelle",
                "x_axis": temporal.name,
                "y_axis": "value",
                "barmode": "group",
            },
        )

    def _detect_boolean_comparison_pattern(
        self,
        profiles: List[EnrichedColumnProfile],
        source_name: str,
    ) -> Optional[MultiFieldPattern]:
        """
        Detect boolean comparison: multiple boolean fields.

        Example: endemic + threatened + protected
        """
        boolean_fields = [
            p for p in profiles if p.data_category == DataCategory.BOOLEAN
        ]

        if len(boolean_fields) < 2:
            return None

        fields = boolean_fields[:4]

        return MultiFieldPattern(
            pattern_type=MultiFieldPatternType.BOOLEAN_COMPARISON,
            name="Comparaison d'états",
            description=f"Comparaison de {', '.join(f.name for f in fields)}",
            fields=[f.name for f in fields],
            field_roles={f.name: "category" for f in fields},
            confidence=0.70,
            transformer_plugin="boolean_comparison",
            transformer_params={
                "source": source_name,
                "fields": [f.name for f in fields],
            },
            widget_plugin="bar_plot",
            widget_params={
                "title": "Comparaison d'états",
                "orientation": "h",
                "barmode": "group",
            },
        )

    def _detect_numeric_correlation_pattern(
        self,
        profiles: List[EnrichedColumnProfile],
        source_name: str,
    ) -> Optional[MultiFieldPattern]:
        """
        Detect numeric correlation: two or more numeric fields.

        Example: elevation + rainfall correlation
        """
        numeric_fields = [
            p
            for p in profiles
            if p.data_category
            in (DataCategory.NUMERIC_CONTINUOUS, DataCategory.NUMERIC_DISCRETE)
            and p.field_purpose == FieldPurpose.MEASUREMENT
        ]

        if len(numeric_fields) < 2:
            return None

        x_field = numeric_fields[0]
        y_field = numeric_fields[1]

        return MultiFieldPattern(
            pattern_type=MultiFieldPatternType.NUMERIC_CORRELATION,
            name="Corrélation",
            description=f"Corrélation entre {x_field.name} et {y_field.name}",
            fields=[x_field.name, y_field.name],
            field_roles={
                x_field.name: "x_axis",
                y_field.name: "y_axis",
            },
            confidence=0.75,
            transformer_plugin="correlation_analysis",
            transformer_params={
                "source": source_name,
                "x_field": x_field.name,
                "y_field": y_field.name,
            },
            widget_plugin="scatter_plot",
            widget_params={
                "title": f"Corrélation {x_field.name} - {y_field.name}",
                "x_axis": x_field.name,
                "y_axis": y_field.name,
            },
        )

    # =========================================================================
    # Semantic Group Finders (Proactive Detection)
    # =========================================================================

    def _find_phenology_group(
        self,
        profiles: List[EnrichedColumnProfile],
    ) -> Optional[Dict[str, Any]]:
        """Find fields that could form a phenology widget."""
        temporal = None
        states = []

        for p in profiles:
            if any(kw in p.name.lower() for kw in PHENOLOGY_KEYWORDS["temporal"]):
                temporal = p
            elif any(kw in p.name.lower() for kw in PHENOLOGY_KEYWORDS["states"]):
                states.append(p)

        if temporal and len(states) >= 2:
            return {
                "group_name": "phenology",
                "display_name": "Phénologie",
                "description": "Ces champs pourraient former un widget de phénologie",
                "fields": [temporal.name] + [s.name for s in states],
                "pattern_type": MultiFieldPatternType.PHENOLOGY,
            }
        return None

    def _find_dimension_group(
        self,
        profiles: List[EnrichedColumnProfile],
    ) -> Optional[Dict[str, Any]]:
        """Find fields that could form an allometry widget."""
        dimensions = [
            p
            for p in profiles
            if any(kw in p.name.lower() for kw in DIMENSION_KEYWORDS)
        ]

        if len(dimensions) >= 2:
            return {
                "group_name": "dimensions",
                "display_name": "Dimensions",
                "description": "Ces champs pourraient montrer des relations allométriques",
                "fields": [d.name for d in dimensions],
                "pattern_type": MultiFieldPatternType.ALLOMETRY,
            }
        return None

    def _find_trait_group(
        self,
        profiles: List[EnrichedColumnProfile],
    ) -> Optional[Dict[str, Any]]:
        """Find fields that could form a traits comparison widget."""
        traits = [
            p for p in profiles if any(kw in p.name.lower() for kw in TRAIT_KEYWORDS)
        ]

        if len(traits) >= 2:
            return {
                "group_name": "functional_traits",
                "display_name": "Traits fonctionnels",
                "description": "Ces champs pourraient être comparés ensemble",
                "fields": [t.name for t in traits],
                "pattern_type": MultiFieldPatternType.TRAIT_COMPARISON,
            }
        return None


def suggest_combined_widgets(
    selected_field_names: List[str],
    all_profiles: List[EnrichedColumnProfile],
    source_name: str = "occurrences",
) -> List[MultiFieldPattern]:
    """
    Convenience function to get combined widget suggestions for selected fields.

    Args:
        selected_field_names: Names of fields selected by user
        all_profiles: All available column profiles
        source_name: Name of the data source

    Returns:
        List of suggested combined widget patterns
    """
    # Filter profiles to selected fields
    selected_profiles = [p for p in all_profiles if p.name in selected_field_names]

    if len(selected_profiles) < 2:
        return []

    detector = MultiFieldPatternDetector()
    return detector.suggest_for_selection(selected_profiles, source_name)


def detect_all_groups(
    all_profiles: List[EnrichedColumnProfile],
) -> List[Dict[str, Any]]:
    """
    Convenience function to detect all semantic groups proactively.

    Args:
        all_profiles: All available column profiles

    Returns:
        List of detected semantic groups
    """
    detector = MultiFieldPatternDetector()
    return detector.detect_semantic_groups(all_profiles)
