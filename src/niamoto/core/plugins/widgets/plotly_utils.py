"""
Utility functions for Plotly-based widgets.

This module provides common functionality for all Plotly widgets,
including consistent configuration and styling.
"""

from typing import Dict, Any, Set

# Define the centralized Plotly dependency
# Use local file instead of CDN
PLOTLY_CDN_URL = "/assets/js/vendor/plotly/3.0.1_plotly.min.js"


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
    Get the standard Plotly CDN dependency.

    Returns:
        Set containing the Plotly CDN URL
    """
    return {PLOTLY_CDN_URL}


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
                    notice.textContent = 'Fond de carte indisponible hors connexion';
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
    html = f'''
    <div id="{div_id}" class="plotly-graph-div" style="height:100%; width:100%;"></div>
    <script type="text/javascript">
        (function() {{
            var plotlyReady = function() {{
                Plotly.newPlot(
                    "{div_id}",
                    {fig_json},
                    {config_json}
                ).then(function() {{
                    // Resize after initial render to fix container sizing issues
                    setTimeout(function() {{
                        Plotly.Plots.resize("{div_id}");
                    }}, 100);
                }});
            }};

            if (typeof Plotly !== 'undefined') {{
                plotlyReady();
            }} else {{
                // Wait for Plotly to load
                var checkPlotly = setInterval(function() {{
                    if (typeof Plotly !== 'undefined') {{
                        clearInterval(checkPlotly);
                        plotlyReady();
                    }}
                }}, 100);
            }}

            // Also resize on window load to handle iframe sizing
            window.addEventListener('load', function() {{
                if (typeof Plotly !== 'undefined') {{
                    setTimeout(function() {{
                        Plotly.Plots.resize("{div_id}");
                    }}, 200);
                }}
            }});
        }})();
    </script>
    '''

    # Add tile fallback script for map widgets
    if is_map:
        html += get_map_tile_fallback_script(div_id)

    return html
