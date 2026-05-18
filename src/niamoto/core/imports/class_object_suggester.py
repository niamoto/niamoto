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

import math
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
    widget_params: Optional[dict[str, Any]] = None

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
            "widget_plugin": self.widget_plugin,
            "widget_params": self.widget_params or {},
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
        widget, config, widget_params = self._build_widget_config(
            co, plugin, source_name
        )
        if not widget:
            return None

        label = _humanize_name(co.name)
        # Strip class_object_ prefix for template_id to match parser expectations
        short_plugin = plugin.replace("class_object_", "")
        template_id = f"{co.name}_{short_plugin}_{widget}"

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
            widget_params=widget_params,
        )

    def _build_widget_config(
        self, co: ClassObjectStats, plugin: str, source_name: str
    ) -> tuple[Optional[str], dict[str, Any], dict[str, Any]]:
        """Build widget type, transformer config, and widget params.

        Widget selection logic (generic, based on data not names):
        - series_extractor (all multi-value) → bar_plot with tops/counts
        - binary_aggregator (exactly 2 categories) → donut_chart
        - field_aggregator (scalar) → radial_gauge

        The config follows the reference format from niamoto-nc/config.
        """
        # Series extractor for all multi-value data (categorical and numeric)
        if plugin in ("series_extractor", "class_object_series_extractor"):
            is_numeric = co.value_type == "numeric"

            # Build transformer config matching reference format
            transformer_config = {
                "source": source_name,
                "class_object": co.name,
                "size_field": {
                    "input": "class_name",
                    "output": "tops",
                    "numeric": is_numeric,
                    "sort": is_numeric,  # Sort only for numeric bins
                },
                "value_field": {
                    "input": "class_value",
                    "output": "counts",
                    "numeric": True,
                },
            }

            # Choose widget based on value type and cardinality
            if co.cardinality <= 5 and not is_numeric:
                # Small categorical → donut chart
                return (
                    "donut_chart",
                    transformer_config,
                    {
                        "labels_field": "tops",
                        "values_field": "counts",
                        "show_legend": False,
                    },
                )

            if is_numeric:
                # Numeric bins (like dbh, elevation) → vertical bar chart with gradient
                # No count limit - show all bins for distribution
                # Detect if values are percentages (sum ≈ 100)
                total = sum(co.sample_values) if co.sample_values else 0
                is_percentage = 95 <= total <= 105

                return (
                    "bar_plot",
                    transformer_config,
                    {
                        "orientation": "v",
                        "x_axis": "tops",
                        "y_axis": "counts",
                        "sort_order": "descending",
                        "gradient_color": "#8B4513",
                        "gradient_mode": "luminance",
                        "show_legend": False,
                        "labels": {
                            "tops": co.name.upper(),
                            "counts": "%" if is_percentage else "Count",
                        },
                    },
                )
            else:
                # Categorical (like top10_family) → horizontal bar chart with auto_color
                # Add count limit for large datasets
                transformer_config["count"] = 10
                return (
                    "bar_plot",
                    transformer_config,
                    {
                        "orientation": "h",
                        "x_axis": "counts",
                        "y_axis": "tops",
                        "sort_order": "descending",
                        "auto_color": True,
                    },
                )

        # Binary (exactly 2 categories) → donut_chart
        if plugin in ("binary_aggregator", "class_object_binary_aggregator"):
            # Use actual class_names from data if available
            labels = co.class_names[:2] if len(co.class_names) >= 2 else ["A", "B"]
            normalized_labels = labels if len(labels) > 1 else [labels[0], "Other"]
            label = _humanize_name(co.name)
            return (
                "donut_chart",
                {
                    "source": source_name,
                    "groups": [
                        {
                            "label": co.name,
                            "field": co.name,
                            "classes": normalized_labels,
                            "class_mapping": {
                                class_name: class_name
                                for class_name in normalized_labels
                            },
                        }
                    ],
                },
                {
                    "subplots": [{"name": label, "data_key": co.name}],
                    "show_legend": False,
                },
            )

        # Scalar (field_aggregator) → radial_gauge
        if plugin in ("field_aggregator", "class_object_field_aggregator"):
            # Use sample values to estimate max_value if available
            max_value = self._estimate_max_value(co)
            return (
                "radial_gauge",
                {
                    "source": source_name,
                    "fields": [
                        {
                            "class_object": co.name,
                            "target": co.name,
                        }
                    ],
                },
                {
                    "value_field": f"{co.name}.value",
                    "max_value": max_value,
                },
            )

        return None, {}, {}

    def _estimate_max_value(self, co: ClassObjectStats) -> float:
        """Estimate appropriate max_value for gauge from actual data.

        Uses sample values if available, otherwise returns a safe default.
        """
        if co.sample_values:
            # Use max of sample values * 1.2 for headroom
            max_sample = max(co.sample_values)
            if max_sample > 0:
                # Round to nice number
                target = max_sample * 1.2
                magnitude = 10 ** math.floor(math.log10(target))
                return math.ceil(target / magnitude) * magnitude

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
