"""
Utility functions for Plotly-based widgets.

This module provides common functionality for all Plotly widgets,
including consistent configuration and styling.
"""

from typing import Dict, Any


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


def render_plotly_figure(fig, config: Dict[str, Any] = None) -> str:
    """
    Render a Plotly figure to HTML with standard configuration.

    Args:
        fig: Plotly figure object
        config: Optional custom config (defaults will be applied)

    Returns:
        HTML string
    """
    plotly_config = get_plotly_config()

    if config:
        plotly_config.update(config)

    return fig.to_html(full_html=False, include_plotlyjs="cdn", config=plotly_config)
