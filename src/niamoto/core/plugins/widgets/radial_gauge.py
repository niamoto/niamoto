import logging
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import plotly.graph_objects as go
from pydantic import Field, ConfigDict

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.core.plugins.models import BasePluginParams
from niamoto.core.plugins.widgets.plotly_utils import (
    apply_plotly_defaults,
    get_plotly_dependencies,
    render_plotly_figure,
)

logger = logging.getLogger(__name__)


# Pydantic model for Radial Gauge parameters validation
class RadialGaugeParams(BasePluginParams):
    """Parameters for radial gauge widget."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Create interactive radial gauge displays with customizable styling",
            "examples": [
                {
                    "value_field": "meff.value",
                    "max_value": 100,
                    "unit": "%",
                    "title": "Progress Gauge",
                },
                {
                    "stat_to_display": "mean",
                    "show_range": True,
                    "auto_range": True,
                    "title": "DBH Statistics",
                },
            ],
        }
    )

    title: Optional[str] = Field(
        default=None,
        description="Optional title for the gauge",
        json_schema_extra={"ui:widget": "text"},
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description or subtitle",
        json_schema_extra={"ui:widget": "textarea"},
    )
    stat_to_display: Optional[str] = Field(
        default=None,
        description="Statistic to display (for statistical_summary data). Overrides value_field.",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": [
                {"value": "", "label": "-- Use value_field --"},
                {"value": "mean", "label": "Mean (Average)"},
                {"value": "max", "label": "Maximum"},
                {"value": "min", "label": "Minimum"},
                {"value": "median", "label": "Median"},
            ],
        },
    )
    value_field: Optional[str] = Field(
        default=None,
        description="Field name containing the current value (supports dot notation). Use stat_to_display for statistical_summary data.",
        json_schema_extra={"ui:widget": "field-select"},
    )
    show_range: Optional[bool] = Field(
        default=False,
        description="Show min/max values as reference markers on the gauge (requires statistical_summary data)",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    auto_range: Optional[bool] = Field(
        default=False,
        description="Auto-detect gauge max from data's max_value field (for statistical_summary)",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    min_value: Optional[float] = Field(
        default=0,
        description="Minimum value of the gauge range",
        json_schema_extra={"ui:widget": "number"},
    )
    max_value: Optional[float] = Field(
        default=None,
        description="Maximum value of the gauge range (or use auto_range)",
        json_schema_extra={"ui:widget": "number"},
    )
    unit: Optional[str] = Field(
        default=None,
        description="Unit symbol (e.g., '%') to display next to the value",
        json_schema_extra={"ui:widget": "text"},
    )
    steps: Optional[List[dict]] = Field(
        default=None,
        description="List of dicts defining color steps, e.g., [{'range': [0, 50], 'color': 'red'}, ...]",
        json_schema_extra={"ui:widget": "json"},
    )
    threshold: Optional[dict] = Field(
        default=None,
        description="Dict defining a threshold line, e.g., {'line': {'color': 'red', 'width': 4}, 'thickness': 0.75, 'value': 90}",
        json_schema_extra={"ui:widget": "json"},
    )
    bar_color: Optional[str] = Field(
        default="cornflowerblue",
        description="Color of the gauge's value bar",
        json_schema_extra={"ui:widget": "color"},
    )
    background_color: Optional[str] = Field(
        default="white",
        description="Background color of the gauge area",
        json_schema_extra={"ui:widget": "color"},
    )
    gauge_shape: str = Field(
        default="angular",
        description="Shape of the gauge",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": [
                {"value": "angular", "label": "Angular (arc)"},
                {"value": "bullet", "label": "Bullet (horizontal)"},
            ],
        },
    )
    style_mode: Optional[str] = Field(
        default="classic",
        description="Style mode for the gauge appearance",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": [
                {"value": "classic", "label": "Classic (with steps)"},
                {"value": "minimal", "label": "Minimal (simple)"},
                {"value": "gradient", "label": "Gradient"},
                {"value": "contextual", "label": "Contextual (color based on value)"},
            ],
        },
    )
    show_axis: Optional[bool] = Field(
        default=True,
        description="Show axis labels and ticks",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    value_format: Optional[str] = Field(
        default=None,
        description="Format string for the value (e.g., '.1f' for 1 decimal, '.0%' for percentage)",
        json_schema_extra={"ui:widget": "text"},
    )
    units: Optional[str] = Field(
        default=None,
        description="Deprecated: use 'unit' instead",
        json_schema_extra={"ui:widget": "text"},
    )


@register("radial_gauge", PluginType.WIDGET)
class RadialGaugeWidget(WidgetPlugin):
    """Widget to display a radial gauge using Plotly."""

    param_schema = RadialGaugeParams

    # Pattern matching: Declare compatible input data structures
    compatible_structures = [
        {
            "min": "float",
            "mean": "float",
            "max": "float",
            "units": "str",
            "max_value": "float",
        },  # statistical_summary (full)
        {
            "max": "float",
            "units": "str",
            "max_value": "float",
        },  # statistical_summary (partial - only max)
        {
            "mean": "float",
            "units": "str",
            "max_value": "float",
        },  # statistical_summary (partial - only mean)
        {"value": "float"},  # Simple value structure
        {
            "meff": "dict",
            "value": "float",
        },  # Nested value (e.g., fragmentation.meff.value)
    ]

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
        # Determine effective value_field
        effective_field = (
            params.stat_to_display if params.stat_to_display else params.value_field
        )

        # Auto-detect field if none specified and data is dict with stats
        if not effective_field and isinstance(data, dict):
            # Try common stat fields in order of preference
            for field in ["mean", "max", "value", "min", "median"]:
                if field in data and data[field] is not None:
                    effective_field = field
                    break

        if not effective_field:
            logger.error("No value_field or stat_to_display specified")
            return "<p class='error'>Configuration Error: No field specified for gauge value.</p>"

        # Extract reference stats for show_range feature
        stat_min = None
        stat_max = None
        data_max_value = None
        data_unit = None

        if isinstance(data, dict):
            stat_min = data.get("min")
            stat_max = data.get("max")
            data_max_value = data.get("max_value")
            data_unit = data.get("units") or data.get("unit")

        # Handle auto_range: use max_value from data if available
        gauge_max = params.max_value
        if params.auto_range and data_max_value is not None:
            gauge_max = float(data_max_value)
        elif gauge_max is None:
            # Fallback: use stat_max * 1.2 or default to 100
            if stat_max is not None:
                gauge_max = float(stat_max) * 1.2
            else:
                gauge_max = 100

        # Handle auto unit from data
        unit = params.unit
        if not unit and data_unit:
            unit = data_unit

        value = None
        if isinstance(data, pd.DataFrame):
            if data.empty:
                logger.warning("Empty DataFrame provided to RadialGaugeWidget.")
                return "<p class='info'>No data for gauge.</p>"
            if effective_field not in data.columns:
                logger.error(f"Value field '{effective_field}' not found in DataFrame.")
                return f"<p class='error'>Configuration Error: Value field '{effective_field}' missing.</p>"
            value = data[effective_field].iloc[0]
        elif isinstance(data, pd.Series):
            if data.empty:
                logger.warning("Empty Series provided to RadialGaugeWidget.")
                return "<p class='info'>No data for gauge.</p>"
            value = data.iloc[0]
        elif isinstance(data, dict):
            # Check if we need to access a nested field using dot notation
            if "." in effective_field:
                value = self._get_nested_data(data, effective_field)
                if value is None:
                    # Return empty string to not display the widget when no data
                    return ""
            elif effective_field not in data:
                # Return empty string to not display the widget when no data
                return ""
            else:
                value = data[effective_field]
        elif isinstance(data, (int, float)):
            value = data
        else:
            logger.warning(
                f"Unsupported data type for RadialGaugeWidget: {type(data)}. Expected DataFrame, Series, dict, or number."
            )
            return "<p class='info'>Invalid data type for gauge.</p>"

        if value is None:
            # Return empty string to not display the widget when no data
            return ""

        try:
            numeric_value = pd.to_numeric(value, errors="coerce")
            if pd.isna(numeric_value):
                logger.warning(f"Value '{value}' is not numeric.")
                return "<p class='info'>Gauge value is not numeric.</p>"

        except Exception as e:
            logger.error(f"Error converting value '{value}' to numeric: {e}")
            return f"<p class='error'>Error processing gauge value: {e}</p>"

        # Handle deprecated units parameter
        if params.units and not unit:
            unit = params.units

        # Apply value formatting if specified
        number_config = {"suffix": unit if unit else ""}
        if params.value_format:
            number_config["valueformat"] = params.value_format

        # Configure style based on style_mode
        bar_color = params.bar_color
        bar_thickness = None  # Default thickness
        min_value = params.min_value or 0

        if params.style_mode == "contextual":
            # Determine color based on value position in range
            value_ratio = (numeric_value - min_value) / (gauge_max - min_value)
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
                    "range": [min_value, gauge_max],
                    "visible": params.show_axis,
                },
                "bar": {"color": bar_color},
                "bgcolor": params.background_color,
                "shape": params.gauge_shape,
            },
        }

        # Add range markers (min/max) if show_range is enabled
        if params.show_range and isinstance(data, dict):
            steps = []
            # Get numeric min/max values
            range_min = None
            range_max = None

            if stat_min is not None and effective_field != "min":
                try:
                    range_min = float(stat_min)
                except (TypeError, ValueError):
                    pass

            if stat_max is not None and effective_field != "max":
                try:
                    range_max = float(stat_max)
                except (TypeError, ValueError):
                    pass

            # Add visual markers for min/max as subtle colored zones
            if range_min is not None or range_max is not None:
                # Create steps showing the data range
                if range_min is not None and range_max is not None:
                    # Show the full range as a highlighted zone
                    steps = [
                        {
                            "range": [min_value, range_min],
                            "color": "#f0f0f0",
                        },  # Below min
                        {
                            "range": [range_min, range_max],
                            "color": "#e3f2fd",
                        },  # Data range
                        {
                            "range": [range_max, gauge_max],
                            "color": "#f0f0f0",
                        },  # Above max
                    ]
                elif range_min is not None:
                    steps = [
                        {"range": [min_value, range_min], "color": "#f0f0f0"},
                        {"range": [range_min, gauge_max], "color": "#e3f2fd"},
                    ]
                elif range_max is not None:
                    steps = [
                        {"range": [min_value, range_max], "color": "#e3f2fd"},
                        {"range": [range_max, gauge_max], "color": "#f0f0f0"},
                    ]

                if steps:
                    gauge_args["gauge"]["steps"] = steps

                # Add threshold marker for the max value
                if range_max is not None and effective_field != "max":
                    gauge_args["gauge"]["threshold"] = {
                        "line": {"color": "#1976d2", "width": 2},
                        "thickness": 0.75,
                        "value": range_max,
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
