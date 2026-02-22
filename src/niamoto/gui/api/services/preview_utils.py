"""Shared preview utility functions.

Module-level functions extracted from PreviewService for use by
engine.py, routers, and any code that needs preview HTML wrapping,
transformer execution, or widget rendering without pulling in the
full PreviewService class.
"""

import html
import logging
from typing import Any, Dict, Optional, Union

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
# Transformer execution
# ---------------------------------------------------------------------------


def execute_transformer(
    db: Optional[Database],
    plugin_name: str,
    params: Dict[str, Any],
    data: Union[pd.DataFrame, Dict[str, Any]],
) -> Dict[str, Any]:
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
    db: Optional[Database],
    plugin_name: str,
    data: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
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

        widget_params: Dict[str, Any] = {"title": title}
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
