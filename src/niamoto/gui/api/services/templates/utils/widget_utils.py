"""
Widget utility functions for templates API.

Functions for mapping transformers to widgets, generating widget titles,
parsing template IDs, and loading configured widgets.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from niamoto.gui.api.context import get_working_directory

logger = logging.getLogger(__name__)


# Class_object extractors (not real transformer plugins, but used for preview)
CLASS_OBJECT_EXTRACTORS = {
    "series_extractor",
    "binary_aggregator",
    "categories_extractor",
    "class_object_field_aggregator",
}


def map_transformer_to_widget(transformer_plugin: str, widget_id: str) -> str:
    """Map a transformer plugin to its corresponding widget plugin."""
    # Navigation widget passes through
    if transformer_plugin == "hierarchical_nav_widget":
        return "hierarchical_nav_widget"

    # Determine widget type from widget_id suffix
    if widget_id.endswith("_bar_plot"):
        return "bar_plot"
    elif widget_id.endswith("_donut_chart"):
        return "donut_chart"
    elif widget_id.endswith("_radial_gauge"):
        return "radial_gauge"
    elif widget_id.endswith("_interactive_map"):
        return "interactive_map"
    elif widget_id.endswith("_info_grid"):
        return "info_grid"

    # Default mappings based on transformer
    transformer_to_widget = {
        "top_ranking": "bar_plot",
        "categorical_distribution": "bar_plot",
        "binned_distribution": "bar_plot",
        "binary_counter": "donut_chart",
        "statistical_summary": "info_grid",
        "geospatial_extractor": "interactive_map",
        "field_aggregator": "info_grid",
        "class_object_field_aggregator": "info_grid",
    }
    return transformer_to_widget.get(transformer_plugin, "info_grid")


def generate_widget_title(widget_id: str, plugin: str, params: Dict[str, Any]) -> str:
    """Generate a user-friendly title for a widget."""
    # Get field name from params
    field = params.get("field", "")

    # Clean up field name for title
    if field:
        title = field.replace("_", " ").title()
    else:
        # Extract from widget_id
        parts = widget_id.split("_")
        # Remove suffix like bar_plot, donut_chart
        if len(parts) >= 2:
            title = " ".join(parts[:-2]).replace("_", " ").title()
        else:
            title = widget_id.replace("_", " ").title()

    # Add context based on transformer
    if plugin == "top_ranking":
        count = params.get("count", 10)
        return f"Top {count} - {title}"
    elif plugin == "binned_distribution":
        return f"Distribution - {title}"
    elif plugin == "categorical_distribution":
        return f"Répartition - {title}"
    elif plugin == "binary_counter":
        return f"{title}"
    elif plugin == "geospatial_extractor":
        return "Distribution géographique"
    elif plugin == "hierarchical_nav_widget":
        ref = params.get("referential_data", "")
        return f"Navigation - {ref.title()}"

    return title


def generate_widget_params(
    widget_plugin: str, transformer_plugin: str, transformer_params: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate widget-specific params based on transformer."""
    params: Dict[str, Any] = {}

    if widget_plugin == "bar_plot":
        if transformer_plugin == "top_ranking":
            params = {
                "orientation": "h",
                "x_axis": "counts",
                "y_axis": "tops",
                "sort_order": "ascending",
                "auto_color": True,
            }
        elif transformer_plugin in ("binned_distribution", "categorical_distribution"):
            params = {
                "orientation": "v",
                "x_axis": "labels",
                "y_axis": "counts",
                "gradient_color": "#10b981",
                "gradient_mode": "luminance",
                "show_legend": False,  # Hide legend - values shown on bars
            }
            if transformer_plugin == "binned_distribution":
                params["transform"] = "bins_to_df"
                params["transform_params"] = {
                    "bin_field": "bins",
                    "count_field": "counts",
                    "use_percentages": True,
                    "percentage_field": "percentages",
                    "x_field": "bin",
                    "y_field": "count",
                }
                # After transform, columns are "bin" and "count"
                params["x_axis"] = "bin"
                params["y_axis"] = "count"
                # Use axis labels from transformer config if available
                x_label = transformer_params.get("x_label")
                y_label = transformer_params.get("y_label")
                if x_label or y_label:
                    params["labels"] = {
                        "bin": x_label or "Classe",
                        "count": y_label or "%",
                    }

    elif widget_plugin == "donut_chart":
        params = {
            "labels_field": "labels",
            "values_field": "counts",
        }

    elif widget_plugin == "radial_gauge":
        if transformer_plugin == "statistical_summary":
            # Use new stat_to_display param for statistical_summary data
            params = {
                "stat_to_display": "mean",  # Display mean by default
                "show_range": True,  # Show min/max as visual markers
                "auto_range": True,  # Use max_value from data
            }
        else:
            # Generic gauge - try to auto-detect value field
            params = {
                "auto_range": True,
            }

    elif widget_plugin == "interactive_map":
        params = {
            "map_style": "carto-voyager",
            "zoom": 7,
            "layers": [
                {
                    "id": "occurrences",
                    "source": "coordinates",
                    "type": "circle_markers",
                    "style": {
                        "color": "#1fb99d",
                        "weight": 1,
                        "fillColor": "#00716b",
                        "fillOpacity": 0.5,
                        "radius": 8,
                    },
                }
            ],
        }

    elif widget_plugin == "hierarchical_nav_widget":
        # Pass through the navigation params
        params = {
            "referential_data": transformer_params.get("referential_data", ""),
            "id_field": transformer_params.get("id_field", "id"),
            "name_field": transformer_params.get("name_field", "name"),
            "base_url": transformer_params.get("base_url", ""),
            "show_search": transformer_params.get("show_search", True),
        }
        # Add hierarchy fields if present
        if transformer_params.get("lft_field"):
            params["lft_field"] = transformer_params["lft_field"]
        if transformer_params.get("rght_field"):
            params["rght_field"] = transformer_params["rght_field"]
        if transformer_params.get("level_field"):
            params["level_field"] = transformer_params["level_field"]
        if transformer_params.get("parent_id_field"):
            params["parent_id_field"] = transformer_params["parent_id_field"]

    return params


def is_class_object_template(transformer: str) -> bool:
    """Check if a transformer name is a class_object extractor."""
    return transformer in CLASS_OBJECT_EXTRACTORS


def find_widget_for_transformer(transformer_name: str) -> Optional[str]:
    """Use SmartMatcher to find a compatible widget for a transformer.

    Returns the name of the best compatible widget, or None if no match found.
    """
    try:
        from niamoto.core.plugins import PluginRegistry, PluginType
        from niamoto.gui.api.services.matcher import SmartMatcher

        transformer_class = PluginRegistry.get_plugin(
            transformer_name, PluginType.TRANSFORMER
        )
        matcher = SmartMatcher()
        suggestions = matcher.find_compatible_widgets(transformer_class)

        if suggestions:
            # Return the best match (highest score)
            return suggestions[0].widget_name
        return None
    except Exception as e:
        logger.warning(
            f"Error finding widget for transformer '{transformer_name}': {e}"
        )
        return None


def parse_dynamic_template_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Parse a dynamic template ID into column, transformer, and widget.

    Dynamic template IDs have the format: {column}_{transformer}_{widget}
    Examples:
        - height_binned_distribution_bar_plot
        - geo_pt_geospatial_extractor_interactive_map
        - species_categorical_distribution_donut_chart
        - dbh_series_extractor_bar_plot (class_object)

    Returns dict with 'column', 'transformer', 'widget' or None if not parseable.
    """
    # Known widget names (from PluginRegistry)
    widget_names = [
        "bar_plot",
        "donut_chart",
        "interactive_map",
        "radial_gauge",
        "info_grid",
    ]

    # Known transformer names (real transformers + class_object extractors)
    transformer_names = [
        # Real transformer plugins
        "binned_distribution",
        "categorical_distribution",
        "statistical_summary",
        "top_ranking",
        "binary_counter",
        "field_aggregator",
        "geospatial_extractor",
        "time_series_analysis",
        # Class_object extractors (for pre-calculated CSV data)
        "series_extractor",
        "binary_aggregator",
        "categories_extractor",
    ]

    # Try to match widget from the end
    matched_widget = None
    for widget in widget_names:
        if template_id.endswith(f"_{widget}"):
            matched_widget = widget
            break

    if not matched_widget:
        return None

    # Remove widget suffix
    remaining = template_id[: -(len(matched_widget) + 1)]

    # Try to match transformer
    matched_transformer = None
    for transformer in transformer_names:
        if remaining.endswith(f"_{transformer}"):
            matched_transformer = transformer
            break

    if not matched_transformer:
        return None

    # Extract column name
    column = remaining[: -(len(matched_transformer) + 1)]
    if not column:
        return None

    return {
        "column": column,
        "transformer": matched_transformer,
        "widget": matched_widget,
    }


def find_widget_group(widget_id: str) -> Optional[str]:
    """Find which group contains a widget by searching transform.yml.

    Args:
        widget_id: The widget identifier to search for

    Returns:
        The group_by value if found, None otherwise
    """
    work_dir = get_working_directory()
    if not work_dir:
        return None

    work_dir = Path(work_dir)
    transform_path = work_dir / "config" / "transform.yml"

    if not transform_path.exists():
        return None

    try:
        with open(transform_path, "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        # Search all groups for the widget_id
        if isinstance(transform_config, list):
            for group in transform_config:
                if isinstance(group, dict):
                    group_by = group.get("group_by")
                    widgets_data = group.get("widgets_data", {})
                    if widget_id in widgets_data:
                        return group_by
        elif isinstance(transform_config, dict):
            groups = transform_config.get("groups", {})
            if isinstance(groups, dict):
                for group_by, group_config in groups.items():
                    if isinstance(group_config, dict):
                        widgets_data = group_config.get("widgets_data", {})
                        if widget_id in widgets_data:
                            return group_by

        return None
    except Exception:
        return None


def load_configured_widget(widget_id: str, group_by: str) -> Optional[Dict[str, Any]]:
    """Load a configured widget from transform.yml and export.yml.

    This is used for previewing widgets created via the wizard, which have
    simple IDs like 'agregateur_binaire_1' rather than dynamic template IDs.

    Args:
        widget_id: The widget identifier (key in widgets_data)
        group_by: Reference name (group_by value in transform.yml)

    Returns:
        Dict with transformer plugin, params, widget plugin, and widget params
        or None if not found.
    """
    work_dir = get_working_directory()
    if not work_dir:
        return None

    work_dir = Path(work_dir)
    transform_path = work_dir / "config" / "transform.yml"
    export_path = work_dir / "config" / "export.yml"

    if not transform_path.exists():
        return None

    try:
        # Load transform.yml
        with open(transform_path, "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        # Find the group config
        group_config = None
        if isinstance(transform_config, list):
            for group in transform_config:
                if isinstance(group, dict) and group.get("group_by") == group_by:
                    group_config = group
                    break
        elif isinstance(transform_config, dict):
            groups = transform_config.get("groups", {})
            if isinstance(groups, dict) and group_by in groups:
                group_config = groups[group_by]

        if not group_config:
            return None

        # Get widget config from widgets_data
        widgets_data = group_config.get("widgets_data", {})
        if widget_id not in widgets_data:
            return None

        widget_config = widgets_data[widget_id]
        transformer_plugin = widget_config.get("plugin")
        raw_params = widget_config.get("params") or {}

        if not transformer_plugin:
            return None

        # Handle nested format where params contains transformer/widget sub-dicts:
        #   params:
        #     transformer: {plugin: ..., params: {source: plots, field: biomass}}
        #     widget: {plugin: radial_gauge, params: {...}}
        #     title: "..."
        # vs flat format where params are directly the transformer params:
        #   params: {source: plots, field: biomass, ...}
        transformer_params = raw_params
        nested_widget_plugin = None
        nested_widget_params = None
        nested_title = None

        if "transformer" in raw_params and isinstance(raw_params["transformer"], dict):
            nested_transformer = raw_params["transformer"]
            transformer_params = nested_transformer.get("params", {})
            if nested_transformer.get("plugin"):
                transformer_plugin = nested_transformer["plugin"]

            if "widget" in raw_params and isinstance(raw_params["widget"], dict):
                nested_widget = raw_params["widget"]
                nested_widget_plugin = nested_widget.get("plugin")
                nested_widget_params = nested_widget.get("params", {})

            if "title" in raw_params:
                nested_title = raw_params["title"]

        # Try to load export.yml for widget display info
        widget_plugin = nested_widget_plugin or "info_grid"
        widget_params = nested_widget_params or {}
        widget_title = nested_title or widget_id.replace("_", " ").title()

        if export_path.exists():
            with open(export_path, "r", encoding="utf-8") as f:
                export_config = yaml.safe_load(f) or {}

            # Find export config for this group
            # export.yml structure: exports: [{groups: [{group_by: ..., widgets: [...]}]}]
            group_export = None

            # Handle exports wrapper
            exports = export_config.get("exports", [])
            if isinstance(exports, list):
                for export_entry in exports:
                    if isinstance(export_entry, dict):
                        groups = export_entry.get("groups", [])
                        if isinstance(groups, list):
                            for item in groups:
                                if (
                                    isinstance(item, dict)
                                    and item.get("group_by") == group_by
                                ):
                                    group_export = item
                                    break
                    if group_export:
                        break

            # Also check legacy formats
            if not group_export:
                if isinstance(export_config, list):
                    for item in export_config:
                        if isinstance(item, dict) and item.get("group_by") == group_by:
                            group_export = item
                            break
                elif isinstance(export_config, dict):
                    groups = export_config.get("groups", [])
                    if isinstance(groups, list):
                        for item in groups:
                            if (
                                isinstance(item, dict)
                                and item.get("group_by") == group_by
                            ):
                                group_export = item
                                break

            if group_export:
                widgets_export = group_export.get("widgets", [])
                for w in widgets_export:
                    if w.get("data_source") == widget_id:
                        widget_plugin = w.get("plugin", "info_grid")
                        widget_params = w.get("params", {})
                        widget_title = w.get("title", widget_title)
                        break

        return {
            "transformer_plugin": transformer_plugin,
            "transformer_params": transformer_params,
            "widget_plugin": widget_plugin,
            "widget_params": widget_params,
            "widget_title": widget_title,
            "widget_id": widget_id,
        }

    except Exception as e:
        logger.warning(f"Error loading configured widget '{widget_id}': {e}")
        return None


def load_widget_params_from_export(
    data_source: str, group_by: str
) -> Optional[Dict[str, Any]]:
    """Load widget params from export.yml for a given data_source.

    This is useful for previewing dynamic templates with custom widget params
    (like custom_tiles_url for interactive maps).

    Args:
        data_source: The data_source value in export.yml (matches template_id)
        group_by: Reference name (group_by value)

    Returns:
        Dict with widget params or None if not found.
    """
    work_dir = get_working_directory()
    if not work_dir:
        return None

    work_dir = Path(work_dir)
    export_path = work_dir / "config" / "export.yml"

    if not export_path.exists():
        return None

    try:
        with open(export_path, "r", encoding="utf-8") as f:
            export_config = yaml.safe_load(f) or {}

        # Find export config for this group
        group_export = None

        # Handle exports wrapper
        exports = export_config.get("exports", [])
        if isinstance(exports, list):
            for export_entry in exports:
                if isinstance(export_entry, dict):
                    groups = export_entry.get("groups", [])
                    if isinstance(groups, list):
                        for item in groups:
                            if (
                                isinstance(item, dict)
                                and item.get("group_by") == group_by
                            ):
                                group_export = item
                                break
                if group_export:
                    break

        # Also check legacy formats
        if not group_export:
            if isinstance(export_config, list):
                for item in export_config:
                    if isinstance(item, dict) and item.get("group_by") == group_by:
                        group_export = item
                        break
            elif isinstance(export_config, dict):
                groups = export_config.get("groups", [])
                if isinstance(groups, list):
                    for item in groups:
                        if isinstance(item, dict) and item.get("group_by") == group_by:
                            group_export = item
                            break

        if group_export:
            widgets_export = group_export.get("widgets", [])
            for w in widgets_export:
                if w.get("data_source") == data_source:
                    return w.get("params", {})

        return None

    except Exception as e:
        logger.warning(
            f"Error loading widget params from export.yml for '{data_source}': {e}"
        )
        return None
