"""
Utility functions for Plotly-based widgets.

This module provides common functionality for all Plotly widgets,
including consistent configuration and styling.
"""

from typing import Dict, Any, Set

# Plotly bundle paths for the exported site.
# Core bundle — all chart types except maps (~1.3 MB).
PLOTLY_CORE_URL = "/assets/js/vendor/plotly/plotly-niamoto-core.min.js"
# Maps bundle — core + scattermap/choroplethmap (~2.2 MB).
PLOTLY_MAPS_URL = "/assets/js/vendor/plotly/plotly-niamoto-maps.min.js"


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

    # Get the JSON representation of the figure
    import json

    fig_json = fig.to_json()
    config_json = json.dumps(plotly_config)

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
