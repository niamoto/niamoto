import logging
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import plotly.graph_objects as go
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

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


@register("radial_gauge", PluginType.WIDGET)
class RadialGaugeWidget(WidgetPlugin):
    """Widget to display a radial gauge using Plotly."""

    param_schema = RadialGaugeParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Plotly is handled centrally."""
        return set()

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
            return "<p class='info'>No value available for gauge.</p>"

        try:
            numeric_value = pd.to_numeric(value, errors="coerce")
            if pd.isna(numeric_value):
                logger.warning(f"Value '{value}' is not numeric.")
                return "<p class='info'>Gauge value is not numeric.</p>"

        except Exception as e:
            logger.error(f"Error converting value '{value}' to numeric: {e}")
            return f"<p class='error'>Error processing gauge value: {e}</p>"

        gauge_args = {
            "mode": "gauge+number",
            "value": numeric_value,
            "title": {"text": params.description or ""},
            "number": {"suffix": params.unit if params.unit else ""},
            "gauge": {
                "axis": {"range": [params.min_value, params.max_value]},
                "bar": {"color": params.bar_color},
                "bgcolor": params.background_color,
                "shape": params.gauge_shape,
            },
        }
        if params.steps:
            gauge_args["gauge"]["steps"] = params.steps
        if params.threshold:
            gauge_args["gauge"]["threshold"] = params.threshold

        try:
            fig = go.Figure(go.Indicator(**gauge_args))

            fig.update_layout(margin={"r": 10, "t": 10, "l": 10, "b": 10}, height=250)

            html_content = fig.to_html(full_html=False, include_plotlyjs="cdn")
            return html_content

        except Exception as e:
            logger.exception(f"Error rendering RadialGaugeWidget: {e}")
            return f"<p class='error'>Error generating gauge: {e}</p>"
