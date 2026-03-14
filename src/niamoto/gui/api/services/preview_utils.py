"""Shared preview utility functions.

Module-level functions extracted from PreviewService for use by
engine.py, routers, and any code that needs preview HTML wrapping,
transformer execution, or widget rendering without pulling in the
full PreviewService class.
"""

import html
import logging
import re
from typing import Any, Optional

import pandas as pd

from niamoto.common.database import Database
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def error_html(message: str) -> str:
    """Render a safe error paragraph for iframe previews."""
    return f"<p class='error'>{html.escape(message)}</p>"


def wrap_html_response(
    content: str,
    title: str = "Preview",
    plotly_bundle: str = "core",
    *,
    thumbnail: bool = False,
) -> str:
    """Wrap widget HTML in a complete HTML document for iframe display.

    Args:
        content: The widget HTML content.
        title: Page title.
        plotly_bundle: Which Plotly bundle to load — ``"core"``, ``"maps"``,
            or ``"none"``.  Defaults to ``"core"``.
        thumbnail: If ``True``, inject a script that disables Plotly
            interactivity for lightweight thumbnail rendering.

    Returns:
        Complete HTML document string.
    """
    from niamoto.gui.api.services.preview_engine.plotly_bundle_resolver import (
        get_plotly_script_tag,
    )

    safe_title = html.escape(title, quote=True)
    plotly_script = get_plotly_script_tag(plotly_bundle)
    thumbnail_js = ""
    if thumbnail:
        thumbnail_js = """
    <script>
        // Mode thumbnail : désactiver l'interactivité Plotly
        window.__NIAMOTO_THUMBNAIL__ = true;
    </script>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_title}</title>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: system-ui, -apple-system, sans-serif;
            background: transparent;
        }}
        .plotly-graph-div {{
            width: 100% !important;
            height: 100% !important;
        }}
        .error {{
            color: #ef4444;
            padding: 1rem;
            text-align: center;
        }}
        .info {{
            color: #6b7280;
            padding: 1rem;
            text-align: center;
        }}
        /* MapLibre GL attribution — discret et intégré */
        .maplibregl-ctrl-attrib {{
            font-size: 10px !important;
            color: rgba(0, 0, 0, 0.45) !important;
            background: rgba(255, 255, 255, 0.6) !important;
            padding: 2px 6px !important;
            border-radius: 3px 0 0 0 !important;
        }}
        .maplibregl-ctrl-attrib a {{
            color: rgba(0, 0, 0, 0.55) !important;
            text-decoration: none !important;
        }}
        .maplibregl-ctrl-attrib a:hover {{
            text-decoration: underline !important;
        }}
        .maplibregl-ctrl-bottom-right {{
            bottom: 0 !important;
            right: 0 !important;
        }}
    </style>
    <script>
        window.__NIAMOTO_PREVIEW__ = true;
    </script>{thumbnail_js}
{plotly_script}
</head>
<body>
{content}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Transformer → Widget data adaptation
# ---------------------------------------------------------------------------


def preprocess_data_for_widget(data: Any, transformer: str, widget: str) -> Any:
    """Adapt transformer output to the format expected by a widget.

    This is the single place for all transformer→widget format conversions.
    Called after transformer execution and before widget rendering.
    """
    if not isinstance(data, dict):
        return data

    # binned_distribution → donut_chart: convert bin edges to labels
    if transformer == "binned_distribution" and widget == "donut_chart":
        bins = data.get("bins", [])
        counts = data.get("counts", [])
        if len(bins) == len(counts) + 1:
            labels = [f"{int(bins[i])}-{int(bins[i + 1])}" for i in range(len(counts))]
            result: dict[str, Any] = {"labels": labels, "counts": counts}
            percentages = data.get("percentages", [])
            if percentages and len(percentages) == len(labels):
                result["percentages"] = percentages
            return result

    # statistical_summary → radial_gauge: extract the stat to display as value.
    # statistical_summary returns {min, mean, max, units, max_value}.
    # radial_gauge needs {value, unit, max_value, min, max}.
    if transformer == "statistical_summary" and widget == "radial_gauge":
        stat = data.get("mean", data.get("max"))
        if stat is not None:
            return {
                "value": stat,
                "unit": data.get("units", ""),
                "max_value": data.get("max_value", data.get("max")),
                "min": data.get("min"),
                "max": data.get("max"),
            }

    # field_aggregator / class_object_field_aggregator → radial_gauge:
    # flatten nested payload to a simple {value, unit} dict.
    if (
        transformer in ("field_aggregator", "class_object_field_aggregator")
        and widget == "radial_gauge"
    ):
        if "value" in data:
            return data

        # Try counts list first (class_object scalars)
        counts = data.get("counts")
        if isinstance(counts, list) and counts:
            return {"value": counts[0]}

        # Scan nested field payloads
        scalar_value: Any = None
        scalar_unit: str | None = None
        for field_payload in data.values():
            if not isinstance(field_payload, dict):
                continue
            candidate = field_payload.get("value")
            if candidate is None:
                continue
            scalar_value = candidate
            units = field_payload.get("units") or field_payload.get("unit")
            if isinstance(units, str) and units:
                scalar_unit = units
            break

        if scalar_value is not None:
            flattened: dict[str, Any] = {"value": scalar_value}
            if scalar_unit:
                flattened["unit"] = scalar_unit
            return flattened

    return data


# ---------------------------------------------------------------------------
# Transformer execution
# ---------------------------------------------------------------------------


def execute_transformer(
    db: Database | None,
    plugin_name: str,
    params: dict[str, Any],
    data: pd.DataFrame | dict[str, Any],
) -> dict[str, Any]:
    """Execute a transformer plugin on data.

    Args:
        db: Database instance (can be None for some transformers).
        plugin_name: Name of the transformer plugin.
        params: Transformer parameters.
        data: Input data (DataFrame or dict for class_object transformers).

    Returns:
        Transformed data dictionary.

    Raises:
        ValueError: If transformer execution fails.
    """
    try:
        plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.TRANSFORMER)
        plugin_instance = plugin_class(db=db)

        transform_config = {
            "plugin": plugin_name,
            "params": params,
        }

        return plugin_instance.transform(data, transform_config)
    except Exception as e:
        logger.exception("Error executing transformer '%s': %s", plugin_name, e)
        raise ValueError(f"Transformer error: {e}")


# ---------------------------------------------------------------------------
# Widget rendering
# ---------------------------------------------------------------------------


def render_widget(
    db: Database | None,
    plugin_name: str,
    data: dict[str, Any],
    params: dict[str, Any] | None = None,
    title: str = "Widget",
) -> str:
    """Render a widget with the given data.

    Args:
        db: Database instance (can be None).
        plugin_name: Name of the widget plugin.
        data: Data to render.
        params: Widget parameters.
        title: Widget title.

    Returns:
        HTML string of rendered widget.
    """
    try:
        plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.WIDGET)
        plugin_instance = plugin_class(db=db)

        widget_params: dict[str, Any] = {"title": title}
        if params:
            widget_params.update(params)

        if hasattr(plugin_instance, "param_schema") and plugin_instance.param_schema:
            validated_params = plugin_instance.param_schema.model_validate(
                widget_params
            )
        else:
            validated_params = widget_params

        return plugin_instance.render(data, validated_params)
    except Exception as e:
        logger.exception("Error rendering widget '%s': %s", plugin_name, e)
        return error_html(f"Widget render error: {e}")


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def parse_wkt_to_geojson(wkt: str) -> Optional[dict[str, Any]]:
    """Parse WKT geometry string to GeoJSON geometry object.

    Handles POINT, POLYGON, MULTIPOLYGON with optional Z coordinates.
    """
    if not wkt or wkt in ("None", "nan", ""):
        return None

    wkt = wkt.strip()

    if wkt.startswith("POINT"):
        match = re.search(r"POINT\s*Z?\s*\(\s*([^)]+)\s*\)", wkt)
        if match:
            parts = match.group(1).strip().split()
            if len(parts) >= 2:
                return {
                    "type": "Point",
                    "coordinates": [float(parts[0]), float(parts[1])],
                }
        return None

    if wkt.startswith("MULTIPOLYGON"):
        polygons: list[Any] = []
        polygon_pattern = r"\(\(([^()]+(?:\([^()]+\)[^()]*)*)\)\)"
        for poly_coords in re.findall(polygon_pattern, wkt):
            ring_coords = []
            for coord_pair in poly_coords.split(","):
                parts = coord_pair.strip().split()
                if len(parts) >= 2:
                    ring_coords.append([float(parts[0]), float(parts[1])])
            if ring_coords:
                polygons.append([ring_coords])
        if polygons:
            return {"type": "MultiPolygon", "coordinates": polygons}
        return None

    if wkt.startswith("POLYGON"):
        match = re.search(r"POLYGON\s*Z?\s*\(\(([^)]+)\)\)", wkt)
        if match:
            coords = []
            for coord_pair in match.group(1).split(","):
                parts = coord_pair.strip().split()
                if len(parts) >= 2:
                    coords.append([float(parts[0]), float(parts[1])])
            if coords:
                return {"type": "Polygon", "coordinates": [coords]}
        return None

    return None
