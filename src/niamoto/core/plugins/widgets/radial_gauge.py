import logging
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import plotly.graph_objects as go
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.core.plugins.widgets.plotly_utils import (
    apply_plotly_defaults,
    get_plotly_dependencies,
    render_plotly_figure,
)

logger = logging.getLogger(__name__)


# Pydantic model for Radial Gauge parameters validation
class RadialGaugeParams(BaseModel):
    title: Optional[str] = Field(None, description="Optional title for the gauge.")
    description: Optional[str] = Field(
        None, description="Optional description or subtitle."
    )
    value_field: str = Field(
        ..., description="Field name containing the current value."
    )
    min_value: Optional[float] = Field(
        0, description="Minimum value of the gauge range."
    )
    max_value: float = Field(..., description="Maximum value of the gauge range.")
    unit: Optional[str] = Field(
        None, description="Unit symbol (e.g., '%') to display next to the value."
    )
    steps: Optional[List[dict]] = Field(
        None,
        description="List of dicts defining color steps, e.g., [{'range': [0, 50], 'color': 'red'}, ...]",
    )
    threshold: Optional[dict] = Field(
        None,
        description="Dict defining a threshold line, e.g., {'line': {'color': 'red', 'width': 4}, 'thickness': 0.75, 'value': 90}",
    )
    bar_color: Optional[str] = Field(
        "cornflowerblue", description="Color of the gauge's value bar."
    )
    background_color: Optional[str] = Field(
        "white", description="Background color of the gauge area."
    )
    gauge_shape: str = Field(
        "angular", description="Shape of the gauge ('angular' or 'bullet')."
    )
    style_mode: Optional[str] = Field(
        "classic",
        description="Style mode: 'classic' (with steps), 'minimal' (simple), 'gradient', or 'contextual'",
    )
    show_axis: Optional[bool] = Field(True, description="Show axis labels and ticks")
    value_format: Optional[str] = Field(
        None,
        description="Format string for the value (e.g., '.1f' for 1 decimal, '.0%' for percentage)",
    )
    units: Optional[str] = Field(None, description="Deprecated: use 'unit' instead")


@register("radial_gauge", PluginType.WIDGET)
class RadialGaugeWidget(WidgetPlugin):
    """Widget to display a radial gauge using Plotly."""

    param_schema = RadialGaugeParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Plotly is handled centrally."""
        return get_plotly_dependencies()

    def _get_nested_data(self, data: Dict, key_path: str) -> Any:
        """Access nested dictionary data using dot notation.

        Args:
            data: The dictionary to access
            key_path: Path to the data using dot notation (e.g., 'meff.value')

        Returns:
            The value at the specified path or None if not found
        """
        if not key_path or not isinstance(data, dict):
            return None

        parts = key_path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def render(self, data: Optional[Any], params: RadialGaugeParams) -> str:
        """Generate the HTML for the radial gauge."""
        value = None
        if isinstance(data, pd.DataFrame):
            if data.empty:
                logger.warning("Empty DataFrame provided to RadialGaugeWidget.")
                return "<p class='info'>No data for gauge.</p>"
            if params.value_field not in data.columns:
                logger.error(
                    f"Value field '{params.value_field}' not found in DataFrame."
                )
                return f"<p class='error'>Configuration Error: Value field '{params.value_field}' missing.</p>"
            value = data[params.value_field].iloc[0]
        elif isinstance(data, pd.Series):
            if data.empty:
                logger.warning("Empty Series provided to RadialGaugeWidget.")
                return "<p class='info'>No data for gauge.</p>"
            value = data.iloc[0]
        elif isinstance(data, dict):
            # Check if we need to access a nested field using dot notation
            if "." in params.value_field:
                value = self._get_nested_data(data, params.value_field)
                if value is None:
                    logger.error(
                        f"Nested value field '{params.value_field}' not found in dict."
                    )
                    return f"<p class='error'>Configuration Error: Nested value field '{params.value_field}' missing.</p>"
            elif params.value_field not in data:
                logger.error(f"Value field '{params.value_field}' not found in dict.")
                return f"<p class='error'>Configuration Error: Value field '{params.value_field}' missing.</p>"
            else:
                value = data[params.value_field]
        elif isinstance(data, (int, float)):
            value = data
        else:
            logger.warning(
                f"Unsupported data type for RadialGaugeWidget: {type(data)}. Expected DataFrame, Series, dict, or number."
            )
            return "<p class='info'>Invalid data type for gauge.</p>"

        if value is None:
            return "<p class='info'>No value available.</p>"

        try:
            numeric_value = pd.to_numeric(value, errors="coerce")
            if pd.isna(numeric_value):
                logger.warning(f"Value '{value}' is not numeric.")
                return "<p class='info'>Gauge value is not numeric.</p>"

        except Exception as e:
            logger.error(f"Error converting value '{value}' to numeric: {e}")
            return f"<p class='error'>Error processing gauge value: {e}</p>"

        # Handle deprecated units parameter
        if params.units and not params.unit:
            params.unit = params.units

        # Apply value formatting if specified
        number_config = {"suffix": params.unit if params.unit else ""}
        if params.value_format:
            number_config["valueformat"] = params.value_format

        # Configure style based on style_mode
        bar_color = params.bar_color
        bar_thickness = None  # Default thickness

        if params.style_mode == "contextual":
            # Determine color based on value position in range
            value_ratio = (numeric_value - params.min_value) / (
                params.max_value - params.min_value
            )
            if value_ratio < 0.33:
                bar_color = "#f02828"  # Red for low values
            elif value_ratio < 0.66:
                bar_color = "#fe6a00"  # Orange for medium values
            else:
                bar_color = "#049f50"  # Green for high values
            # Use same thickness as minimal style
            bar_thickness = 0.8

        gauge_args = {
            "mode": "gauge+number",
            "value": numeric_value,
            "title": {"text": params.description or ""},
            "number": number_config,
            "gauge": {
                "axis": {
                    "range": [params.min_value, params.max_value],
                    "visible": params.show_axis,
                },
                "bar": {"color": bar_color},
                "bgcolor": params.background_color,
                "shape": params.gauge_shape,
            },
        }

        # Apply bar thickness if specified
        if bar_thickness is not None:
            gauge_args["gauge"]["bar"]["thickness"] = bar_thickness

        # Apply style-specific configurations
        if params.style_mode == "minimal":
            # Minimal style: no steps, clean look
            gauge_args["gauge"]["bgcolor"] = "#f5f5f5"  # Light gray background
            gauge_args["gauge"]["borderwidth"] = 0
            gauge_args["gauge"]["bar"]["thickness"] = 0.8

        elif params.style_mode == "contextual":
            # Contextual style: same clean look as minimal but with dynamic colors
            gauge_args["gauge"]["bgcolor"] = "#f5f5f5"  # Light gray background
            gauge_args["gauge"]["borderwidth"] = 0
            # Bar thickness already set above

        elif params.style_mode == "gradient":
            # For gradient style, we'll use a single color bar but with a gradient background
            # This creates a cleaner look
            gauge_args["gauge"]["bgcolor"] = (
                "#e8f5f3"  # Very light version of the bar color
            )
            gauge_args["gauge"]["borderwidth"] = 0
            gauge_args["gauge"]["bar"]["thickness"] = 0.75

            # If bar_color contains RGB, extract it for gradient
            if params.bar_color:
                # Use the bar color as is
                gauge_args["gauge"]["bar"]["color"] = params.bar_color
            else:
                # Default gradient color
                gauge_args["gauge"]["bar"]["color"] = "#1fb99d"

        elif params.style_mode == "classic" and params.steps:
            # Classic style with defined color steps
            gauge_args["gauge"]["steps"] = params.steps

        if params.threshold:
            gauge_args["gauge"]["threshold"] = params.threshold

        try:
            fig = go.Figure(go.Indicator(**gauge_args))

            # Apply Plotly defaults with custom layout
            layout_updates = {"height": 250}
            apply_plotly_defaults(fig, layout_updates)

            # Render with standard config
            return render_plotly_figure(fig)

        except Exception as e:
            logger.exception(f"Error rendering RadialGaugeWidget: {e}")
            return f"<p class='error'>Error generating gauge: {e}</p>"
