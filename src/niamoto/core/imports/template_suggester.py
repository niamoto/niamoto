"""
Template-based suggester for widget configurations.

This module provides a hybrid suggestion system that combines:
1. Dynamic generation based on column data types (primary)
2. Domain-specific templates as optional enhancements (secondary)

Usage:
    suggester = TemplateSuggester()
    suggestions = suggester.suggest_for_entity(
        column_profiles=profiles,
        reference_name="my_reference",
        source_name="occurrences"
    )
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from niamoto.core.imports.data_analyzer import EnrichedColumnProfile
from niamoto.core.imports.widget_generator import WidgetGenerator, WidgetSuggestion

logger = logging.getLogger(__name__)


@dataclass
class TemplateSuggestion:
    """A suggested template with confidence and match information."""

    template_id: str
    name: str
    description: str
    plugin: str
    category: str
    icon: str
    confidence: float
    source: str  # "auto" | "template" | "generic"
    source_name: str  # Actual source dataset name (from import.yml)
    matched_column: Optional[str] = None
    match_reason: Optional[str] = None
    is_recommended: bool = False
    config: Dict[str, Any] = None
    alternatives: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "plugin": self.plugin,
            "category": self.category,
            "icon": self.icon,
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "source_name": self.source_name,
            "matched_column": self.matched_column,
            "match_reason": self.match_reason,
            "is_recommended": self.is_recommended,
            "config": self.config or {},
            "alternatives": self.alternatives or [],
        }


class TemplateSuggester:
    """
    Suggests widget templates based on column profiles.

    Uses a dynamic generation approach:
    1. Analyze each column's data type
    2. Generate compatible widgets (distribution, stats, map, etc.)
    3. Link alternatives together (same column, different visualization)
    4. Score based on data quality

    Confidence scoring:
    - Primary widget for data type: 0.85
    - Alternative widgets: 0.65
    - Penalty for null ratio: -0.2 * null_ratio
    """

    # Essential widgets that should always be suggested if data allows
    # Note: general_info is now generated dynamically in templates.py with auto-detected fields
    ESSENTIAL_WIDGETS: list = []

    # Minimum confidence to include in suggestions
    MIN_CONFIDENCE = 0.4

    def __init__(self):
        """Initialize the template suggester."""
        self.generator = WidgetGenerator()

    def suggest_for_entity(
        self,
        column_profiles: List[EnrichedColumnProfile],
        reference_name: str,
        source_name: str = "occurrences",
        max_suggestions: int = 30,
    ) -> List[TemplateSuggestion]:
        """
        Generate template suggestions for any reference entity.

        This is a generic method that works with any reference from import.yml.
        No hardcoded entity names - the reference_name and source_name are
        passed dynamically from the API.

        Args:
            column_profiles: Enriched column profiles from data analysis
            reference_name: Name of the reference entity (group_by target)
            source_name: Name of the source dataset (e.g., 'occurrences')
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of TemplateSuggestion sorted by confidence (descending).
            All alternatives are included even if beyond max_suggestions.
        """
        # 1. Generate dynamic suggestions from WidgetGenerator
        widget_suggestions = self.generator.generate_for_columns(
            column_profiles, source_table=source_name
        )

        # 2. Convert to TemplateSuggestion format
        suggestions = [self._convert_widget_suggestion(ws) for ws in widget_suggestions]

        # 3. Filter by minimum confidence
        suggestions = [s for s in suggestions if s.confidence >= self.MIN_CONFIDENCE]

        # 5. Sort by confidence (primary first), then by name
        suggestions.sort(key=lambda s: (-s.confidence, not s.is_recommended, s.name))

        # 6. Apply max_suggestions limit, but ensure all alternatives are included
        # First, get the top suggestions up to max_suggestions
        top_suggestions = suggestions[:max_suggestions]

        # Collect all alternative IDs that need to be included
        needed_alternatives = set()
        for s in top_suggestions:
            if s.alternatives:
                needed_alternatives.update(s.alternatives)

        # Add any alternatives that are in the full list but not in top_suggestions
        top_ids = {s.template_id for s in top_suggestions}
        missing_alternatives = needed_alternatives - top_ids

        if missing_alternatives:
            # Find and add missing alternatives from the full list
            for s in suggestions[max_suggestions:]:
                if s.template_id in missing_alternatives:
                    top_suggestions.append(s)
                    missing_alternatives.remove(s.template_id)
                    if not missing_alternatives:
                        break

        return top_suggestions

    def _convert_widget_suggestion(self, ws: WidgetSuggestion) -> TemplateSuggestion:
        """Convert WidgetSuggestion to TemplateSuggestion."""
        return TemplateSuggestion(
            template_id=ws.id,
            name=ws.name,
            description=ws.description,
            plugin=ws.plugin,
            category=ws.category,
            icon=ws.icon,
            confidence=ws.confidence,
            source="auto",
            source_name=ws.source_name,
            matched_column=ws.column,
            match_reason=f"Colonne '{ws.column}' ({ws.widget_type})",
            is_recommended=ws.is_primary,
            config=ws.config,
            alternatives=ws.alternatives,
        )

    def _create_general_info_suggestion(
        self, reference_name: str, source_name: str
    ) -> TemplateSuggestion:
        """Create the general info widget suggestion.

        The config is generic - specific field names should be configured
        by the user in the UI based on their schema.

        Args:
            reference_name: Name of the reference entity (group_by target)
            source_name: Name of the source dataset
        """
        return TemplateSuggestion(
            template_id="general_info",
            name="Informations générales",
            description=f"Informations de base et statistiques pour {reference_name}",
            plugin="field_aggregator",
            category="info",
            icon="Info",
            confidence=0.9,
            source="template",
            source_name=source_name,
            matched_column=reference_name,
            match_reason=f"Widget essentiel pour {reference_name}",
            is_recommended=True,
            config={
                # Generic config - user should configure specific fields in UI
                "fields": [
                    {
                        "source": reference_name,
                        "field": "name",  # Generic - user configures actual field
                        "target": "name",
                    },
                    {
                        "source": source_name,
                        "field": "id",
                        "target": "count",
                        "transformation": "count",
                    },
                ]
            },
            alternatives=[],
        )

    def get_available_widget_types(self) -> List[Dict[str, Any]]:
        """
        Get list of available widget types with their categories.

        Returns:
            List of widget type info dicts
        """
        return [
            {
                "type": "distribution",
                "name": "Distribution (Histogramme)",
                "category": "chart",
                "data_types": ["numeric_continuous", "numeric_discrete"],
                "plugin": "binned_distribution",
            },
            {
                "type": "max",
                "name": "Valeur maximale (Jauge)",
                "category": "gauge",
                "data_types": ["numeric_continuous", "numeric_discrete"],
                "plugin": "statistical_summary",
            },
            {
                "type": "mean",
                "name": "Valeur moyenne (Jauge)",
                "category": "gauge",
                "data_types": ["numeric_continuous", "numeric_discrete"],
                "plugin": "statistical_summary",
            },
            {
                "type": "min",
                "name": "Valeur minimale (Jauge)",
                "category": "gauge",
                "data_types": ["numeric_continuous", "numeric_discrete"],
                "plugin": "statistical_summary",
            },
            {
                "type": "categorical_distribution",
                "name": "Distribution catégorielle",
                "category": "chart",
                "data_types": ["categorical", "categorical_high_card"],
                "plugin": "categorical_distribution",
            },
            {
                "type": "top_ranking",
                "name": "Classement Top N",
                "category": "chart",
                "data_types": ["categorical", "categorical_high_card"],
                "plugin": "top_ranking",
            },
            {
                "type": "binary",
                "name": "Distribution binaire (Donut)",
                "category": "donut",
                "data_types": ["boolean"],
                "plugin": "binary_counter",
            },
            {
                "type": "map",
                "name": "Distribution map",
                "category": "map",
                "data_types": ["geographic"],
                "plugin": "geospatial_extractor",
            },
        ]

    def generate_transform_config(
        self,
        selected_suggestions: List[TemplateSuggestion],
    ) -> Dict[str, Any]:
        """
        Generate transform.yml widgets_data section from selected suggestions.

        Args:
            selected_suggestions: List of selected suggestions

        Returns:
            Dict suitable for transform.yml widgets_data section
        """
        widgets_data = {}

        for suggestion in selected_suggestions:
            widgets_data[suggestion.template_id] = {
                "plugin": suggestion.plugin,
                "params": suggestion.config,
            }

        return widgets_data
