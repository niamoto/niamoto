"""
Class Object Widget Suggester

Generates widget suggestions based on class_objects detected in pre-calculated CSV files.
Maps class_object patterns to appropriate transformer+widget combinations.

This is fully generic - it works with ANY CSV following the class_object format:
- class_object: type of metric
- class_name: category or bin value
- class_value: numeric value

Widget selection is based on data characteristics, not hardcoded names:
- Cardinality 0 (scalar) → radial_gauge
- Cardinality 2 (binary) → donut_chart
- Cardinality 3-5 (small categorical) → donut_chart
- Cardinality >5 (large categorical) → bar_plot horizontal
- Numeric class_names → bar_plot (distribution)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from niamoto.core.imports.class_object_analyzer import (
    ClassObjectAnalyzer,
    ClassObjectStats,
)


@dataclass
class ClassObjectWidgetSuggestion:
    """A widget suggestion based on a class_object."""

    template_id: str
    name: str
    description: str
    transformer_plugin: str
    widget_plugin: str
    category: str
    icon: str
    confidence: float
    source_name: str
    class_object: str
    config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "plugin": self.transformer_plugin,
            "category": self.category,
            "icon": self.icon,
            "confidence": self.confidence,
            "source": "class_object",
            "source_name": self.source_name,
            "matched_column": self.class_object,
            "match_reason": f"Source: {self.source_name}",
            "is_recommended": self.confidence >= 0.8,
            "config": self.config,
            "alternatives": [],
        }


def _humanize_name(name: str) -> str:
    """Convert any class_object name to a human-readable label.

    Examples:
        'top10_family' → 'Top10 family'
        'cover_forest' → 'Cover forest'
        'forest_elevation_distribution' → 'Forest elevation distribution'
        'nb_species' → 'Nb species'
    """
    # Replace underscores with spaces and capitalize first letter
    label = name.replace("_", " ")
    return label.capitalize()


def _get_widget_icon(widget: str) -> str:
    """Get icon name for widget type."""
    return {
        "bar_plot": "bar-chart",
        "donut_chart": "pie-chart",
        "radial_gauge": "gauge",
        "info_grid": "grid",
        "interactive_map": "map",
    }.get(widget, "chart")


def _get_widget_category(widget: str) -> str:
    """Get category for widget type."""
    return {
        "bar_plot": "chart",
        "donut_chart": "donut",
        "radial_gauge": "gauge",
        "info_grid": "info",
        "interactive_map": "map",
    }.get(widget, "chart")


class ClassObjectWidgetSuggester:
    """Generates widget suggestions from class_object analysis.

    This class is fully generic - it works with ANY class_object data.
    Widget selection is based on data characteristics:
    - Cardinality (number of distinct class_names)
    - Value type (numeric vs categorical class_names)
    """

    def suggest_for_class_object(
        self,
        co: ClassObjectStats,
        source_name: str,
        reference_name: str,
    ) -> Optional[ClassObjectWidgetSuggestion]:
        """Generate a widget suggestion for a single class_object.

        Args:
            co: Class object statistics from analyzer
            source_name: Name of the CSV source
            reference_name: Name of the reference group (for config)

        Returns:
            Widget suggestion or None if no suitable widget
        """
        plugin = co.suggested_plugin
        if not plugin:
            return None

        # Determine widget based on transformer and characteristics
        widget, config = self._build_widget_config(co, plugin, source_name)
        if not widget:
            return None

        label = _humanize_name(co.name)
        template_id = f"{co.name}_{plugin}_{widget}"

        return ClassObjectWidgetSuggestion(
            template_id=template_id,
            name=label,
            description=f"{label} (source: {source_name})",
            transformer_plugin=plugin,
            widget_plugin=widget,
            category=_get_widget_category(widget),
            icon=_get_widget_icon(widget),
            confidence=co.confidence,
            source_name=source_name,
            class_object=co.name,
            config=config,
        )

    def _build_widget_config(
        self, co: ClassObjectStats, plugin: str, source_name: str
    ) -> tuple[Optional[str], dict[str, Any]]:
        """Build widget type and transformer config for a class_object.

        Widget selection logic (generic, based on data not names):
        - series_extractor (numeric bins) → bar_plot
        - binary_aggregator (exactly 2 categories) → donut_chart
        - categories_extractor (3-5 categories) → donut_chart
        - categories_extractor (>5 categories) → bar_plot horizontal
        - field_aggregator (scalar) → radial_gauge
        """
        base_config = {
            "source": source_name,
            "class_object": co.name,
        }

        # Series (numeric distribution) → bar_plot vertical
        if plugin == "series_extractor":
            return "bar_plot", {
                **base_config,
                "output_field": f"{co.name}_distribution",
                "orientation": "v",
            }

        # Binary (exactly 2 categories) → donut_chart
        if plugin == "binary_aggregator":
            # Use actual class_names from data if available
            labels = co.class_names[:2] if len(co.class_names) >= 2 else ["A", "B"]
            return "donut_chart", {
                **base_config,
                "true_label": labels[0],
                "false_label": labels[1] if len(labels) > 1 else "Other",
            }

        # Categories → donut (small) or bar (large)
        if plugin == "categories_extractor":
            if co.cardinality <= 5:
                # Small categorical → donut chart
                return "donut_chart", {
                    **base_config,
                    "output_field": f"{co.name}_distribution",
                }
            else:
                # Large categorical → horizontal bar chart
                # Limit to top 10 for readability
                return "bar_plot", {
                    **base_config,
                    "orientation": "h",
                    "limit": min(co.cardinality, 10),
                }

        # Scalar (field_aggregator) → radial_gauge
        if plugin == "field_aggregator":
            # Use sample values to estimate max_value if available
            max_value = self._estimate_max_value(co)
            return "radial_gauge", {
                **base_config,
                "output_field": co.name,
                "max_value": max_value,
            }

        return None, {}

    def _estimate_max_value(self, co: ClassObjectStats) -> float:
        """Estimate appropriate max_value for gauge from actual data.

        Uses sample values if available, otherwise returns a safe default.
        """
        if co.sample_values:
            # Use max of sample values * 1.2 for headroom
            max_sample = max(co.sample_values)
            if max_sample > 0:
                # Round to nice number
                magnitude = 10 ** len(str(int(max_sample)))
                return round(max_sample * 1.2 / magnitude) * magnitude

        # Safe default
        return 100

    def suggest_from_source(
        self,
        csv_path: Path,
        source_name: str,
        reference_name: str,
    ) -> list[ClassObjectWidgetSuggestion]:
        """Generate all widget suggestions from a CSV source file.

        Args:
            csv_path: Path to the CSV file
            source_name: Name to identify this source
            reference_name: Name of the reference group

        Returns:
            List of widget suggestions, sorted by confidence
        """
        analyzer = ClassObjectAnalyzer(csv_path)
        analysis = analyzer.analyze()

        if not analysis.is_valid:
            return []

        suggestions = []
        for co in analysis.class_objects:
            suggestion = self.suggest_for_class_object(co, source_name, reference_name)
            if suggestion:
                suggestions.append(suggestion)

        # Sort by confidence (highest first)
        suggestions.sort(key=lambda s: -s.confidence)

        return suggestions


def suggest_widgets_for_source(
    csv_path: str | Path,
    source_name: str,
    reference_name: str,
) -> list[dict[str, Any]]:
    """Convenience function to get widget suggestions as dicts.

    Args:
        csv_path: Path to the CSV file
        source_name: Name to identify this source
        reference_name: Name of the reference group

    Returns:
        List of suggestion dicts ready for API response
    """
    analyzer = ClassObjectAnalyzer(Path(csv_path))
    analysis = analyzer.analyze()

    if not analysis.is_valid:
        return []

    suggester = ClassObjectWidgetSuggester()
    suggestions = suggester.suggest_from_source(
        Path(csv_path), source_name, reference_name
    )

    return [s.to_dict() for s in suggestions]
