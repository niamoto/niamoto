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


def render_plotly_figure(fig, config: Dict[str, Any] = None) -> str:
    """
    Render a Plotly figure to HTML with standard configuration.

    Important: This assumes Plotly JS is loaded centrally through the dependency system.
    All Plotly widgets should include the dependency from get_plotly_dependencies().

    Args:
        fig: Plotly figure object
        config: Optional custom config (defaults will be applied)

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
                );
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
        }})();
    </script>
    '''

    return html
