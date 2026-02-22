"""Plotly bundle resolver — selects the right JS bundle for each widget.

Three bundle tiers:
- ``"core"``  — scatter, bar, pie, heatmap, indicator, sunburst, table, barpolar (~1 MB)
- ``"maps"``  — core + scattermap, choroplethmap (~2.5 MB)
- ``"none"``  — no Plotly at all (info_grid, hierarchical_nav, etc.)
"""

from typing import Literal, Optional

BundleTier = Literal["core", "maps", "none"]

# Widget plugins that need the maps bundle.
MAP_WIDGET_PLUGINS: frozenset[str] = frozenset({"interactive_map"})

# Widget plugins that need no Plotly at all.
NO_PLOTLY_PLUGINS: frozenset[str] = frozenset({
    "info_grid",
    "hierarchical_nav_widget",
    "table_view",
    "raw_data_widget",
    "summary_stats",
})

# Template ID suffixes that imply a map widget.
MAP_TEMPLATE_SUFFIXES = ("_entity_map", "_all_map")

# Bundle paths (served via /api/site/assets/…).
_BUNDLE_PATHS: dict[BundleTier, str] = {
    "core": "/api/site/assets/js/vendor/plotly/plotly-niamoto-core.min.js",
    "maps": "/api/site/assets/js/vendor/plotly/plotly-niamoto-maps.min.js",
}


def resolve_bundle(
    widget_plugin: Optional[str] = None,
    template_id: Optional[str] = None,
) -> BundleTier:
    """Determine the lightest Plotly bundle sufficient for a given widget.

    Args:
        widget_plugin: The widget plugin name (e.g. ``"bar_plot"``).
        template_id: The template ID if known (used for suffix-based heuristic).

    Returns:
        ``"core"``, ``"maps"``, or ``"none"``.
    """
    # Explicit widget plugin match takes precedence.
    if widget_plugin:
        if widget_plugin in NO_PLOTLY_PLUGINS:
            return "none"
        if widget_plugin in MAP_WIDGET_PLUGINS:
            return "maps"

    # Template-id suffix heuristic.
    if template_id:
        for suffix in MAP_TEMPLATE_SUFFIXES:
            if template_id.endswith(suffix):
                return "maps"

    # Default to core (covers bar_plot, donut_chart, radial_gauge, etc.).
    return "core"


def get_plotly_script_tag(bundle: BundleTier) -> str:
    """Return the ``<script>`` tag for *bundle*, or ``""`` for ``"none"``."""
    path = _BUNDLE_PATHS.get(bundle)
    if not path:
        return ""
    return f'    <script src="{path}"></script>'
