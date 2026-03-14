"""Fonctions de rendu pour les widgets class_object.

Extraites de templates.py pour être partagées entre le routeur templates
et le moteur de preview (engine.py).
"""

import html
import json
import logging
from typing import Any

from niamoto.common.database import Database
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Extraction de class_objects depuis les paramètres transformer
# ---------------------------------------------------------------------------


def _extract_class_objects_from_params(params: dict[str, Any]) -> list[str]:
    """Extract class_object names from transformer parameters.

    Different transformers store class_objects in different param structures:
    - field_aggregator: params.fields[].class_object
    - binary_aggregator: params.groups[].field
    - series_extractor: params.class_object
    - categories_extractor: params.class_object
    """
    class_objects: list[str] = []
    seen: set[str] = set()

    def add_class_object(value: Any) -> None:
        """Normalize class_object values (string or list) into a unique list."""
        if isinstance(value, str):
            if value and value not in seen:
                seen.add(value)
                class_objects.append(value)
        elif isinstance(value, list):
            for item in value:
                add_class_object(item)

    # Single class_object
    add_class_object(params.get("class_object"))

    # List of fields with class_object
    for field in params.get("fields", []):
        if isinstance(field, dict):
            add_class_object(field.get("class_object"))

    # List of groups with field (binary_aggregator)
    for group in params.get("groups", []):
        if isinstance(group, dict):
            add_class_object(group.get("field"))

    # Series config list
    for series in params.get("series", []):
        if isinstance(series, dict):
            add_class_object(series.get("class_object"))

    # Distributions (ratio aggregator)
    for dist in params.get("distributions", {}).values():
        if isinstance(dist, dict):
            add_class_object(dist.get("total"))
            add_class_object(dist.get("subset"))

    # Categories mapper
    for category in params.get("categories", {}).values():
        if isinstance(category, dict):
            add_class_object(category.get("class_object"))

    # Series by axis extractor
    for class_object in params.get("types", {}).values():
        add_class_object(class_object)

    return class_objects


# ---------------------------------------------------------------------------
# Exécution de transformers class_object
# ---------------------------------------------------------------------------


def _execute_configured_transformer(
    transformer_plugin: str,
    params: dict[str, Any],
    class_object_data: dict[str, dict[str, Any]],
    group_by: str,
) -> dict[str, Any] | None:
    """Execute a class_object transformer with loaded CSV data.

    This mimics what happens during the actual transform phase,
    but uses the preview data we loaded.
    """
    try:
        # For binary_aggregator, we need to compute ratios
        # Output format: {"tops": [...], "counts": [...]} for bar_plot compatibility
        if transformer_plugin == "class_object_binary_aggregator":
            groups = params.get("groups", [])
            all_labels = []
            all_counts = []

            for group in groups:
                field = group.get("field", "")

                if field not in class_object_data:
                    continue

                # co_data is already in {"tops": [...], "counts": [...]} format
                co_data = class_object_data[field]
                group_tops = co_data.get("tops", [])
                group_counts = co_data.get("counts", [])

                # Add tops and counts for this group
                all_labels.extend(group_tops)
                all_counts.extend(group_counts)

            return {"tops": all_labels, "counts": all_counts}

        # For field_aggregator, collect scalar values
        elif transformer_plugin == "class_object_field_aggregator":
            fields = params.get("fields", [])
            result: dict[str, Any] = {}

            for field_config in fields:
                co_name = field_config.get("class_object")
                target = field_config.get("target", "value")
                units = field_config.get("units", "")
                field_format = field_config.get("format")

                value: Any = None
                if isinstance(co_name, list):
                    values: list[Any] = []
                    for name in co_name:
                        co_data = class_object_data.get(name, {})
                        counts = co_data.get("counts", [])
                        values.append(counts[0] if counts else None)

                    if field_format == "range" and len(values) >= 2:
                        value = {"min": values[0], "max": values[1]}
                    else:
                        value = values
                elif isinstance(co_name, str):
                    co_data = class_object_data.get(co_name, {})
                    counts = co_data.get("counts", [])
                    value = counts[0] if counts else None

                field_result: dict[str, Any] = {"value": value}
                if units:
                    field_result["units"] = units
                result[target] = field_result

            return result

        # For series_extractor, extract size distribution
        elif transformer_plugin == "class_object_series_extractor":
            co_name = params.get("class_object", "")
            if co_name not in class_object_data:
                return None

            # co_data is in {"tops": [...], "counts": [...]} format
            co_data = class_object_data[co_name]
            tops = co_data.get("tops", [])
            counts = co_data.get("counts", [])

            # Sort by value descending (like top_ranking)
            if tops and counts:
                paired = sorted(zip(tops, counts), key=lambda x: -x[1])
                # Apply count limit if specified
                count_limit = params.get("count")
                if count_limit and len(paired) > count_limit:
                    paired = paired[:count_limit]
                tops, counts = zip(*paired) if paired else ([], [])

            # Use output field names from config (e.g. "bins"/"counts")
            # to match what the real pipeline produces
            size_key = (params.get("size_field") or {}).get("output", "tops")
            value_key = (params.get("value_field") or {}).get("output", "counts")
            return {size_key: list(tops), value_key: list(counts)}

        # For categories_extractor, extract categories
        elif transformer_plugin == "class_object_categories_extractor":
            co_name = params.get("class_object", "")
            if co_name not in class_object_data:
                return None

            # co_data is in {"tops": [...], "counts": [...]} format
            co_data = class_object_data[co_name]
            tops = co_data.get("tops", [])
            counts = co_data.get("counts", [])

            return {"tops": tops, "counts": counts}

        # Default: return the raw data
        return {"data": class_object_data}

    except Exception as e:
        logger.warning(f"Error executing transformer {transformer_plugin}: {e}")
        return None


# ---------------------------------------------------------------------------
# Helpers internes pour le rendu widget
# ---------------------------------------------------------------------------


def _summarize_info_list(values: list[Any], max_items: int = 5) -> str:
    """Summarize list values into a compact preview string."""
    preview = ", ".join(str(v) for v in values[:max_items])
    if len(values) > max_items:
        preview += ", ..."
    return preview


def _coerce_info_value(value: Any) -> bool | str | int | float:
    """Convert arbitrary values to an InfoGrid-compatible scalar."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    if isinstance(value, list):
        return _summarize_info_list(value)
    if isinstance(value, dict):
        if "min" in value and "max" in value:
            return f"{value.get('min')} - {value.get('max')}"
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _build_info_grid_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a safe InfoGrid `items` config from transformer output."""
    items: list[dict[str, Any]] = []

    if not isinstance(data, dict):
        return items

    # Legacy structured output used by earlier preview helpers.
    if isinstance(data.get("fields"), list):
        for field in data["fields"]:
            if not isinstance(field, dict):
                continue
            label = str(field.get("label") or field.get("name") or "Value")
            item: dict[str, Any] = {"label": label}
            if "value" in field:
                item["value"] = _coerce_info_value(field["value"])
            elif "source" in field:
                item["source"] = str(field["source"])
            if field.get("units"):
                item["unit"] = str(field["units"])
            items.append(item)
        if items:
            return items

    for key, value in data.items():
        label = str(key).replace("_", " ").title()

        if isinstance(value, dict):
            if "value" in value:
                item: dict[str, Any] = {"label": label, "source": f"{key}.value"}
                if value.get("units"):
                    item["unit"] = str(value["units"])
                items.append(item)
                continue

            scalar_items = [
                (sub_key, sub_value)
                for sub_key, sub_value in value.items()
                if isinstance(sub_value, (str, int, float, bool))
            ]
            if scalar_items:
                for sub_key, sub_value in scalar_items[:8]:
                    sub_label = str(sub_key).replace("_", " ").title()
                    items.append(
                        {
                            "label": f"{label} - {sub_label}",
                            "value": _coerce_info_value(sub_value),
                        }
                    )
            else:
                items.append({"label": label, "value": _coerce_info_value(value)})
            continue

        if isinstance(value, list):
            items.append({"label": label, "value": _coerce_info_value(value)})
            continue

        if value is not None:
            items.append({"label": label, "value": _coerce_info_value(value)})

    return items


# ---------------------------------------------------------------------------
# Construction des paramètres widget
# ---------------------------------------------------------------------------


def _build_widget_params_for_configured(
    transformer: str,
    widget: str,
    data: dict[str, Any],
    title: str,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build widget parameters for configured widgets.

    Maps transformer output to widget input based on known patterns.
    """
    params = {"title": title}

    # Apply extra params from export.yml first (they can be overridden by defaults)
    if extra_params:
        params.update(extra_params)

    if widget == "bar_plot":
        # For binary_aggregator, data has groups with values
        if transformer == "class_object_binary_aggregator":
            # Set params for bar_plot
            params.setdefault("x_axis", "labels")
            params.setdefault("y_axis", "counts")
            params.setdefault("orientation", "v")
            params.setdefault("gradient_color", "#10b981")

        # For series extractors — data is {"tops": [...], "counts": [...]}
        elif transformer in ("class_object_series_extractor", "series_extractor"):
            params.setdefault("x_axis", "counts")
            params.setdefault("y_axis", "tops")
            params.setdefault("orientation", "h")
            params.setdefault("sort_order", "descending")
            params.setdefault("auto_color", True)

        # For categories extractors
        elif transformer in (
            "class_object_categories_extractor",
            "categories_extractor",
        ):
            params.setdefault("x_axis", "labels")
            params.setdefault("y_axis", "counts")
            params.setdefault("orientation", "h")
            params.setdefault("sort_order", "descending")

        # Fallback for other bar_plot transformers
        else:
            params.setdefault("x_axis", "labels")
            params.setdefault("y_axis", "counts")
            params.setdefault("orientation", "v")

    elif widget == "donut_chart":
        params.setdefault("values_field", "counts")
        params.setdefault("labels_field", "labels")

    elif widget == "info_grid":
        params.setdefault("items", _build_info_grid_items(data))
        params.setdefault("grid_columns", 2)

    elif widget == "radial_gauge":
        params.setdefault("auto_range", True)

    return params


def _build_widget_params_for_class_object(
    extractor: str, widget: str, data: dict[str, Any], title: str
) -> dict[str, Any]:
    """Build widget parameters for class_object data.

    Class_object data format: {"tops": [...], "counts": [...], "source": "...", "class_object": "..."}

    Widget params depend on the widget type:
    - bar_plot: horizontal with y_axis="tops", x_axis="counts" (like top_ranking)
    - donut_chart: values_field="counts", labels_field="tops"
    - radial_gauge: value_field (uses first value), max_value
    """
    if widget == "bar_plot":
        # Check if data is numeric (distribution) or categorical (ranking)
        is_numeric = data.get("_is_numeric", False)

        if is_numeric:
            # Numeric bins (like dbh) -> vertical bar chart with gradient
            # Detect if values are percentages (sum ~ 100)
            counts = data.get("counts", [])
            total = sum(counts) if counts else 0
            is_percentage = 95 <= total <= 105  # Allow some tolerance

            # Get class_object name for x-axis label
            class_object_name = data.get("class_object", "").upper()
            x_label = class_object_name if class_object_name else "Classe"
            y_label = "%" if is_percentage else "Effectif"

            return {
                "x_axis": "tops",  # bins on x-axis
                "y_axis": "counts",
                "title": title,
                "orientation": "v",
                "sort_order": "descending",
                "gradient_color": "#8B4513",
                "gradient_mode": "luminance",
                "show_legend": False,  # no legend for distributions
                "labels": {
                    "tops": x_label,
                    "counts": y_label,
                },  # Applied from x_label/y_label
            }
        else:
            # Categorical (like top_ranking) -> horizontal bar chart with auto_color
            return {
                "x_axis": "counts",
                "y_axis": "tops",
                "title": title,
                "orientation": "h",
                "sort_order": "descending",
                "auto_color": True,
            }

    elif widget == "donut_chart":
        return {
            "values_field": "counts",
            "labels_field": "tops",
            "title": title,
        }

    elif widget == "radial_gauge":
        # For scalar values, use the first (and usually only) value
        max_value = 100
        actual_value: float | None = None
        counts = data.get("counts", [])
        if counts:
            try:
                actual_value = float(counts[0])
            except (TypeError, ValueError):
                actual_value = None
        elif "value" in data:
            try:
                actual_value = float(data.get("value"))
            except (TypeError, ValueError):
                actual_value = None

        if actual_value is not None and actual_value > 0:
            # Round to a "nice" upper bound above the value
            magnitude = 10 ** max(1, len(str(int(actual_value))))
            max_value = int(((actual_value // magnitude) + 1) * magnitude)

        unit_value = data.get("units") or data.get("unit")

        params = {
            "value_field": "value",  # We'll need to adjust data structure
            "max_value": max_value,
            "title": title,
        }
        if isinstance(unit_value, str) and unit_value:
            params["unit"] = unit_value
        return params

    elif widget == "info_grid":
        return {
            "title": title,
            "columns": 2,
        }

    # Default fallback
    return {"title": title}


# ---------------------------------------------------------------------------
# Rendu de widgets configurés (transform.yml)
# ---------------------------------------------------------------------------


def _render_widget_for_configured(
    db: Database | None,
    widget_name: str,
    data: dict[str, Any],
    transformer: str,
    title: str,
    extra_params: dict[str, Any] | None = None,
) -> str:
    """Render a widget for a configured widget from transform.yml.

    This handles widgets created via the wizard that have custom configurations.

    Args:
        db: Database connection (can be None)
        widget_name: Name of the widget plugin (e.g., 'bar_plot')
        data: Transformer output data
        transformer: Name of the transformer plugin
        title: Title for the widget
        extra_params: Additional widget params from export.yml

    Returns:
        HTML content of the rendered widget
    """
    try:
        plugin_class = PluginRegistry.get_plugin(widget_name, PluginType.WIDGET)
        plugin_instance = plugin_class(db=db)

        # Build widget params based on transformer and widget type
        widget_params = _build_widget_params_for_configured(
            transformer, widget_name, data, title, extra_params
        )

        # Validate params if the plugin has a param_schema
        if hasattr(plugin_instance, "param_schema") and plugin_instance.param_schema:
            validated_params = plugin_instance.param_schema.model_validate(
                widget_params
            )
        else:
            validated_params = widget_params

        return plugin_instance.render(data, validated_params)
    except Exception as e:
        logger.exception(f"Error rendering configured widget '{widget_name}': {e}")
        return f"<p class='error'>Widget render error: {html.escape(str(e))}</p>"


# ---------------------------------------------------------------------------
# Rendu de widgets class_object (CSV)
# ---------------------------------------------------------------------------


def _render_widget_for_class_object(
    db: Database | None,
    widget_name: str,
    data: dict[str, Any],
    extractor: str,
    title: str,
) -> str:
    """Render a widget for class_object data (pre-calculated CSV).

    Args:
        db: Database connection (can be None for class_object widgets)
        widget_name: Name of the widget plugin (e.g., 'bar_plot', 'donut_chart')
        data: Class object data with 'labels' and 'counts'
        extractor: Name of the class_object extractor (e.g., 'series_extractor')
        title: Title for the widget

    Returns:
        HTML content of the rendered widget
    """
    try:
        plugin_class = PluginRegistry.get_plugin(widget_name, PluginType.WIDGET)
        plugin_instance = plugin_class(db=db)

        # For bar_plot, handle data based on type (numeric vs categorical)
        render_data = data
        if widget_name == "bar_plot":
            tops = data.get("tops", [])
            counts = data.get("counts", [])
            if tops and counts:
                # Check if data is numeric (distribution bins like dbh)
                is_numeric = all(
                    isinstance(t, (int, float))
                    or (
                        isinstance(t, str)
                        and t.replace(".", "").replace("-", "").isdigit()
                    )
                    for t in tops[:5]  # Check first 5 items
                )

                if is_numeric:
                    # Numeric bins: sort by bin value descending (largest bins first)
                    paired = sorted(
                        zip(tops, counts),
                        key=lambda x: (
                            float(x[0])
                            if isinstance(x[0], (int, float))
                            or x[0].replace(".", "").replace("-", "").isdigit()
                            else 0
                        ),
                        reverse=True,
                    )
                    tops, counts = zip(*paired) if paired else ([], [])
                elif len(tops) > 10:
                    # Categorical: sort by value descending and take top 10
                    paired = sorted(zip(tops, counts), key=lambda x: -x[1])[:10]
                    tops, counts = zip(*paired) if paired else ([], [])

                render_data = {
                    **data,
                    "tops": list(tops),
                    "counts": list(counts),
                    "_is_numeric": is_numeric,
                }

        # class_object_field_aggregator outputs a dict keyed by target fields:
        # {"elevation_max": {"value": 1234, "units": "m"}}.
        # radial_gauge expects a flat structure with a direct numeric value.
        if (
            extractor == "class_object_field_aggregator"
            and widget_name == "radial_gauge"
            and isinstance(render_data, dict)
            and "value" not in render_data
        ):
            scalar_value: Any = None
            scalar_units: str | None = None

            counts = render_data.get("counts")
            if isinstance(counts, list) and counts:
                scalar_value = counts[0]
            else:
                for field_payload in render_data.values():
                    if isinstance(field_payload, dict):
                        candidate = field_payload.get("value")
                        if candidate is not None:
                            scalar_value = candidate
                            units = field_payload.get("units")
                            if isinstance(units, str) and units:
                                scalar_units = units
                            break

            if scalar_value is not None:
                render_data = {"value": scalar_value}
                if scalar_units:
                    render_data["units"] = scalar_units

        # Build widget params based on extractor type
        widget_params = _build_widget_params_for_class_object(
            extractor, widget_name, render_data, title
        )

        # Validate params if the plugin has a param_schema
        if hasattr(plugin_instance, "param_schema") and plugin_instance.param_schema:
            validated_params = plugin_instance.param_schema.model_validate(
                widget_params
            )
        else:
            validated_params = widget_params

        return plugin_instance.render(render_data, validated_params)
    except Exception as e:
        logger.exception(f"Error rendering class_object widget '{widget_name}': {e}")
        return f"<p class='error'>Widget render error: {html.escape(str(e))}</p>"
