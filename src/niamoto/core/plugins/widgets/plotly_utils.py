"""
Utility functions for Plotly-based widgets.

This module provides common functionality for all Plotly widgets,
including consistent configuration and styling.
"""

import colorsys
import json
from typing import Any, Dict, List, Set

# Plotly bundle paths for the exported site.
# Core bundle — all chart types except maps (~1.3 MB).
PLOTLY_CORE_URL = "/assets/js/vendor/plotly/plotly-niamoto-core.min.js"
# Maps bundle — core + scattermap/choroplethmap (~2.2 MB).
PLOTLY_MAPS_URL = "/assets/js/vendor/plotly/plotly-niamoto-maps.min.js"

# Shared palette for automatically generated chart colors. The hues stay varied,
# but avoid the highly saturated default Plotly/HTML named colors.
MUTED_CHART_COLORS = [
    "#4f8068",
    "#6d8796",
    "#b07f4f",
    "#8b6f9b",
    "#b76f63",
    "#6c8f45",
    "#9a8d58",
    "#5f7f88",
    "#a36f82",
    "#7f7f72",
]


def escape_json_for_html_script(json_text: str) -> str:
    """Escape JSON text before embedding it in an inline script block."""
    return json_text.replace("</", "<\\/")


def json_dumps_for_html_script(value: Any) -> str:
    """Serialize a value as JSON safe for inline script embedding."""
    return escape_json_for_html_script(json.dumps(value))


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex."""
    return f"#{r:02x}{g:02x}{b:02x}"


def _mix_hex_colors(hex_color: str, target_color: str, ratio: float) -> str:
    """Mix a hex color with a target color."""
    ratio = max(0.0, min(1.0, ratio))
    source_rgb = hex_to_rgb(hex_color)
    target_rgb = hex_to_rgb(target_color)
    mixed_rgb = [
        round(source * (1 - ratio) + target * ratio)
        for source, target in zip(source_rgb, target_rgb)
    ]
    return rgb_to_hex(*mixed_rgb)


def _soften_hex_color(hex_color: str) -> str:
    """Reduce saturation while keeping the original hue recognizable."""
    r, g, b = [channel / 255 for channel in hex_to_rgb(hex_color)]
    h, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    saturation *= 0.68
    if lightness < 0.5:
        lightness += (0.5 - lightness) * 0.18
    softened = colorsys.hls_to_rgb(h, lightness, saturation)
    return rgb_to_hex(*(round(channel * 255) for channel in softened))


def _derive_muted_color(hex_color: str, index: int, cycle: int) -> str:
    """Create a muted color variation without collapsing to repeated shades."""
    r, g, b = [channel / 255 for channel in hex_to_rgb(hex_color)]
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)

    hue = (hue + (0.061 * cycle) + (0.013 * index)) % 1.0
    lightness_offsets = [-0.12, 0.1, -0.06, 0.06, -0.02, 0.14]
    lightness = max(0.34, min(0.72, lightness + lightness_offsets[cycle % 6]))
    saturation = max(0.18, min(0.44, saturation * (0.72 + 0.04 * (cycle % 4))))

    derived = colorsys.hls_to_rgb(hue, lightness, saturation)
    return rgb_to_hex(*(round(channel * 255) for channel in derived))


def _make_unique_color(color: str, seen_colors: Set[str]) -> str:
    """Return a nearby muted color that has not already been emitted."""
    if color not in seen_colors:
        return color

    r, g, b = [channel / 255 for channel in hex_to_rgb(color)]
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    for attempt in range(1, 512):
        next_hue = (hue + 0.017 * attempt) % 1.0
        next_lightness = max(0.34, min(0.72, lightness + 0.015 * ((attempt % 9) - 4)))
        adjusted = colorsys.hls_to_rgb(next_hue, next_lightness, saturation)
        candidate = rgb_to_hex(*(round(channel * 255) for channel in adjusted))
        if candidate not in seen_colors:
            return candidate

    raise ValueError("Unable to generate a unique muted color")


def generate_muted_gradient_colors(
    base_color: str, count: int, mode: str = "luminance"
) -> List[str]:
    """Generate a restrained gradient based on a base color."""
    if count <= 0:
        return []

    if count == 1:
        return [base_color]

    muted_base = _soften_hex_color(base_color)
    colors = []

    if mode == "luminance":
        for i in range(count):
            factor = 0.35 + (0.65 * i / (count - 1))
            colors.append(_mix_hex_colors("#f7f5f0", muted_base, factor))
    elif mode == "saturation":
        neutral = "#8f8b84"
        for i in range(count):
            factor = 0.92 - (0.52 * i / (count - 1))
            colors.append(_mix_hex_colors(neutral, muted_base, factor))

    return colors


def generate_muted_discrete_colors(count: int) -> List[str]:
    """Generate varied, low-saturation colors for automatic chart coloring."""
    if count <= 0:
        return []

    colors = []
    seen_colors: Set[str] = set()
    palette_size = len(MUTED_CHART_COLORS)
    for i in range(count):
        base_color = MUTED_CHART_COLORS[i % palette_size]
        cycle = i // palette_size
        if cycle == 0:
            colors.append(base_color)
            seen_colors.add(base_color)
            continue

        color = _derive_muted_color(base_color, i % palette_size, cycle)
        color = _make_unique_color(color, seen_colors)
        colors.append(color)
        seen_colors.add(color)

    return colors


def get_plotly_config() -> Dict[str, Any]:
    """
    Get standard Plotly configuration for all widgets.

    Returns:
        Dictionary with Plotly config options
    """
    return {
        "displayModeBar": True,
        "displaylogo": False,  # Remove Plotly logo
        "modeBarButtonsToRemove": ["sendDataToCloud"],  # Remove cloud button
        "toImageButtonOptions": {
            "format": "png",
            "filename": "niamoto_chart",
            "height": 500,
            "width": 700,
        },
    }


def get_plotly_layout_defaults() -> Dict[str, Any]:
    """
    Get default layout options for all Plotly charts.

    Returns:
        Dictionary with layout defaults including watermark removal
    """
    return {
        "annotations": [],  # Remove "Produced with Plotly" watermark
        "colorway": MUTED_CHART_COLORS,
        "margin": {"r": 10, "t": 30, "l": 10, "b": 10},
    }


def apply_plotly_defaults(fig, additional_layout: Dict[str, Any] = None):
    """
    Apply standard Plotly defaults to a figure.

    Args:
        fig: Plotly figure object
        additional_layout: Additional layout options to merge with defaults

    Returns:
        Modified figure object
    """
    layout_updates = get_plotly_layout_defaults()

    if additional_layout:
        layout_updates.update(additional_layout)

    fig.update_layout(**layout_updates)
    return fig


def get_plotly_dependencies() -> Set[str]:
    """
    Get the standard Plotly core dependency (no maps).

    Returns:
        Set containing the Plotly core bundle URL
    """
    return {PLOTLY_CORE_URL}


def get_plotly_map_dependencies() -> Set[str]:
    """
    Get Plotly dependencies including map support.

    Returns:
        Set containing the Plotly maps bundle URL
    """
    return {PLOTLY_MAPS_URL}


def get_map_tile_fallback_script(div_id: str) -> str:
    """
    Generate a JavaScript snippet that detects tile loading failures
    and falls back to white-bg map style with an offline notice.

    This is used by map widgets to gracefully handle offline scenarios
    where map tile servers are unreachable.

    Args:
        div_id: The Plotly div ID for the map

    Returns:
        HTML script tag with tile fallback logic
    """
    return f'''
    <script type="text/javascript">
    (function() {{
        var divId = "{div_id}";
        var tileErrors = 0;
        var tileFallbackApplied = false;
        var tileCheckTimeout = null;

        function applyWhiteBgFallback() {{
            if (tileFallbackApplied) return;
            tileFallbackApplied = true;

            try {{
                var gd = document.getElementById(divId);
                if (gd && typeof Plotly !== 'undefined') {{
                    Plotly.relayout(gd, {{
                        'map.style': 'white-bg',
                        'map.layers': []
                    }});

                    // Add offline notice
                    var notice = document.createElement('div');
                    notice.className = 'tile-offline-notice';
                    notice.style.cssText = 'position:absolute;bottom:4px;left:4px;' +
                        'background:rgba(0,0,0,0.6);color:#fff;padding:2px 8px;' +
                        'border-radius:3px;font-size:11px;z-index:100;pointer-events:none;';
                    notice.textContent = 'Map tiles unavailable offline';
                    var container = gd.closest('.map-container') || gd.parentElement;
                    if (container) {{
                        container.style.position = 'relative';
                        container.appendChild(notice);
                    }}
                }}
            }} catch(e) {{
                console.warn('Tile fallback error:', e);
            }}
        }}

        // Monitor for tile loading errors via MutationObserver on img elements
        function startTileMonitor() {{
            var gd = document.getElementById(divId);
            if (!gd) return;

            // Set a 5s timeout: if map tiles haven't loaded, apply fallback
            tileCheckTimeout = setTimeout(function() {{
                if (tileErrors > 0 && !tileFallbackApplied) {{
                    applyWhiteBgFallback();
                }}
            }}, 5000);

            // Listen for image errors within the plotly container (tile images)
            gd.addEventListener('error', function(e) {{
                if (e.target && e.target.tagName === 'IMG') {{
                    tileErrors++;
                    if (tileErrors >= 3 && !tileFallbackApplied) {{
                        clearTimeout(tileCheckTimeout);
                        applyWhiteBgFallback();
                    }}
                }}
            }}, true);
        }}

        // Start monitoring after Plotly renders
        if (typeof Plotly !== 'undefined') {{
            setTimeout(startTileMonitor, 500);
        }} else {{
            var check = setInterval(function() {{
                if (typeof Plotly !== 'undefined') {{
                    clearInterval(check);
                    setTimeout(startTileMonitor, 500);
                }}
            }}, 200);
        }}
    }})();
    </script>
    '''


def render_plotly_figure(
    fig, config: Dict[str, Any] = None, is_map: bool = False
) -> str:
    """
    Render a Plotly figure to HTML with standard configuration.

    Important: This assumes Plotly JS is loaded centrally through the dependency system.
    All Plotly widgets should include the dependency from get_plotly_dependencies().

    Args:
        fig: Plotly figure object
        config: Optional custom config (defaults will be applied)
        is_map: If True, adds tile fallback script for offline map support

    Returns:
        HTML string (without embedded Plotly JS)
    """
    plotly_config = get_plotly_config()

    if config:
        plotly_config.update(config)

    # Generate the HTML with a div placeholder
    # We need to get the div_id to wrap our JS code properly
    import uuid

    div_id = str(uuid.uuid4())

    fig_json = escape_json_for_html_script(fig.to_json())
    config_json = json_dumps_for_html_script(plotly_config)

    # Create HTML that waits for Plotly to be loaded
    is_map_js = "true" if is_map else "false"
    html = f'''
    <div id="{div_id}" class="plotly-graph-div" style="height:100%; width:100%;"></div>
    <script type="text/javascript">
        (function() {{
            var isPreview = !!window.__NIAMOTO_PREVIEW__;
            var isMap = {is_map_js};
            var hasRendered = false;
            var figure = {fig_json};
            var plotConfig = {config_json};

            // Preview mode: keep rendering cheap and stable.
            if (isPreview) {{
                plotConfig.displayModeBar = false;
                plotConfig.responsive = false;
                figure.layout = figure.layout || {{}};
                figure.layout.showlegend = false;
                // Keep maps in their native autosize path, but freeze non-map
                // charts to avoid heavy redraw loops in tiny iframes.
                if (!isMap) {{
                    plotConfig.staticPlot = true;
                    // Avoid autosize/automargin feedback loops in tiny preview iframes.
                    figure.layout.autosize = false;
                    if (typeof figure.layout.width !== 'number') {{
                        figure.layout.width = 400;
                    }}
                    if (typeof figure.layout.height !== 'number') {{
                        figure.layout.height = 300;
                    }}
                }}
            }}

            var plotlyReady = function() {{
                if (hasRendered) return;
                hasRendered = true;
                Plotly.newPlot(
                    "{div_id}",
                    figure.data || [],
                    figure.layout || {{}},
                    plotConfig
                ).then(function(gd) {{
                    // Keep one post-render resize in non-preview contexts.
                    // For preview maps, run a delayed resize to ensure markers
                    // are positioned correctly after iframe layout settles.
                    if (!isPreview && gd) {{
                        requestAnimationFrame(function() {{
                            Plotly.Plots.resize(gd);
                        }});
                    }} else if (isPreview && isMap && gd) {{
                        requestAnimationFrame(function() {{
                            Plotly.Plots.resize(gd);
                        }});
                        setTimeout(function() {{
                            Plotly.Plots.resize(gd);
                        }}, 120);
                    }}
                }});
            }};

            if (typeof Plotly !== 'undefined') {{
                plotlyReady();
            }} else {{
                // Wait for Plotly to load
                var attempts = 0;
                var checkPlotly = setInterval(function() {{
                    attempts++;
                    if (typeof Plotly !== 'undefined') {{
                        clearInterval(checkPlotly);
                        plotlyReady();
                    }} else if (attempts > 100) {{
                        clearInterval(checkPlotly);
                    }}
                }}, 100);
            }}

            // Resize only when the host window actually resizes (non-preview).
            if (!isPreview) {{
                var resizeRaf = null;
                window.addEventListener('resize', function() {{
                    if (resizeRaf !== null) {{
                        cancelAnimationFrame(resizeRaf);
                    }}
                    resizeRaf = requestAnimationFrame(function() {{
                        var gd = document.getElementById("{div_id}");
                        if (gd && typeof Plotly !== 'undefined') {{
                            Plotly.Plots.resize(gd);
                        }}
                        resizeRaf = null;
                    }});
                }});
            }}
        }})();
    </script>
    '''

    # Add tile fallback script for map widgets
    if is_map:
        html += get_map_tile_fallback_script(div_id)

    return html
