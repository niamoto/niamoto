"""Plotly bundle resolver — selects the right JS bundle for each widget.

Three bundle tiers:
- ``"core"``  — scatter, bar, pie, heatmap, indicator, sunburst, table, barpolar (~1 MB)
- ``"maps"``  — core + scattermap, choroplethmap (~2.5 MB)
- ``"none"``  — no Plotly at all (info_grid, hierarchical_nav, etc.)
"""

from typing import Literal

BundleTier = Literal["core", "maps", "none"]

# Widget plugins that need the maps bundle.
MAP_WIDGET_PLUGINS: frozenset[str] = frozenset({"interactive_map"})

# Widget plugins that need no Plotly at all.
NO_PLOTLY_PLUGINS: frozenset[str] = frozenset(
    {
        "info_grid",
        "enrichment_panel",
        "hierarchical_nav_widget",
        "table_view",
        "raw_data_widget",
        "summary_stats",
    }
)

# Template ID suffixes that imply a map widget.
MAP_TEMPLATE_SUFFIXES = ("_entity_map", "_all_map")

# Bundle paths (served via /api/site/assets/…).
_BUNDLE_PATHS: dict[BundleTier, str] = {
    "core": "/api/site/assets/js/vendor/plotly/plotly-niamoto-core.min.js",
    "maps": "/api/site/assets/js/vendor/plotly/plotly-niamoto-maps.min.js",
}

# Extra scripts required alongside map bundles (topojson for client-side conversion).
_MAP_EXTRA_SCRIPTS: list[str] = [
    "/api/site/assets/js/vendor/topojson/3.1.0_topojson.js",
]


def resolve_bundle(
    widget_plugin: str | None = None,
    template_id: str | None = None,
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
    """Return the ``<script>`` tag(s) for *bundle*, or ``""`` for ``"none"``.

    For the ``"maps"`` bundle this also loads the TopoJSON client library
    required for client-side TopoJSON → GeoJSON conversion.
    """
    path = _BUNDLE_PATHS.get(bundle)
    if not path:
        return ""
    # Polyfill `global` — le bundle custom esbuild référence `global`
    # qui n'existe pas dans les navigateurs (seulement Node.js).
    parts = [
        "    <script>var global = globalThis;</script>",
        f'    <script src="{path}" crossorigin="anonymous"></script>',
    ]
    if bundle == "maps":
        for extra in _MAP_EXTRA_SCRIPTS:
            parts.append(f'    <script src="{extra}" crossorigin="anonymous"></script>')
    return "\n".join(parts)
