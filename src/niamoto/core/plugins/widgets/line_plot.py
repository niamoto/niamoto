import logging
from typing import Any, Dict, List, Optional, Set, Union

import pandas as pd
import plotly.express as px
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.core.plugins.widgets.plotly_utils import (
    apply_plotly_defaults,
    get_plotly_dependencies,
    render_plotly_figure,
)

logger = logging.getLogger(__name__)


# Pydantic model for Line Plot parameters validation
class LinePlotParams(BaseModel):
    title: Optional[str] = Field(
        None, description="Optional title for the widget container."
    )
    description: Optional[str] = Field(
        None, description="Optional description for the widget container."
    )
    x_axis: str = Field(
        ..., description="Field name for the X-axis (often time or a sequence)."
    )
    y_axis: Union[str, List[str]] = Field(
        ..., description="Field name(s) for the Y-axis (values)."
    )
    color_field: Optional[str] = Field(
        None, description="Field name for color grouping (creates multiple lines)."
    )
    line_group: Optional[str] = Field(
        None, description="Field to group data points into lines without coloring."
    )
    markers: Union[bool, str] = Field(
        False,
        description="Show markers on lines (True, False, or field name for marker symbols).",
    )
    line_shape: Optional[str] = Field(
        "linear",
        description="Shape of lines: 'linear', 'spline', 'hv', 'vh', 'hvh', 'vhv'.",
    )
    hover_name: Optional[str] = Field(
        None, description="Field for primary hover label."
    )
    hover_data: Optional[List[str]] = Field(
        None, description="Additional fields for hover tooltip."
    )
    color_discrete_map: Optional[Any] = Field(
        None, description="Mapping for discrete colors."
    )
    color_continuous_scale: Optional[str] = Field(
        None, description="Plotly color scale name (if color_field is numeric)."
    )
    range_y: Optional[List[float]] = Field(None, description="Y-axis range [min, max].")
    labels: Optional[Any] = Field(
        None, description="Mapping for axis/legend labels {'x_axis': 'X Label', ...}"
    )
    log_y: bool = Field(False, description="Use logarithmic scale for Y-axis.")


@register("line_plot", PluginType.WIDGET)
class LinePlotWidget(WidgetPlugin):
    """Widget to display a line plot using Plotly."""

    param_schema = LinePlotParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Plotly is handled centrally."""
        return get_plotly_dependencies()

    def _get_nested_data(self, data: Dict, key_path: str) -> Any:
        """Access nested dictionary data using dot notation.

        Args:
            data: The dictionary to access
            key_path: Path to the data using dot notation (e.g., 'elevation.classes')

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

    def render(self, data: Optional[Any], params: LinePlotParams) -> str:
        """Generate the HTML for the line plot."""

        # Process dictionary data
        if isinstance(data, dict):
            # Handle specific case for fragmentation_distribution data
            processed_data = None

            # Case 1: Dictionary with direct keys for x and y axes
            if params.x_axis in data and params.y_axis in data:
                x_values = data[params.x_axis]
                y_values = (
                    data[params.y_axis]
                    if isinstance(params.y_axis, str)
                    else data[params.y_axis[0]]
                )

                if (
                    isinstance(x_values, list)
                    and isinstance(y_values, list)
                    and len(x_values) == len(y_values)
                ):
                    # Create dataframe from the lists
                    processed_data = pd.DataFrame(
                        {
                            params.x_axis: x_values,
                            params.y_axis
                            if isinstance(params.y_axis, str)
                            else params.y_axis[0]: y_values,
                        }
                    )

                    # Add color field if available
                    if params.color_field and params.color_field in data:
                        color_values = data[params.color_field]
                        if isinstance(color_values, list) and len(color_values) == len(
                            x_values
                        ):
                            processed_data[params.color_field] = color_values

            # Case 2: Dictionary with 'sizes' and 'areas'/'cumulative' structure for fragmentation_distribution
            elif "sizes" in data and (
                "areas" in data or "cumulative" in data or "values" in data
            ):
                x_values = data["sizes"]

                # Determine which field to use for y-axis values
                y_key = None
                if "values" in data:
                    y_key = "values"
                elif "cumulative" in data:
                    y_key = "cumulative"
                elif "areas" in data:
                    y_key = "areas"

                if (
                    y_key
                    and isinstance(data[y_key], list)
                    and len(data[y_key]) == len(x_values)
                ):
                    processed_data = pd.DataFrame(
                        {
                            params.x_axis: x_values,
                            params.y_axis
                            if isinstance(params.y_axis, str)
                            else params.y_axis[0]: data[y_key],
                        }
                    )

            # Case 3: Try using dot notation to access nested data
            elif "." in params.x_axis or "." in params.y_axis:
                x_data = self._get_nested_data(data, params.x_axis)
                y_data = self._get_nested_data(
                    data,
                    params.y_axis
                    if isinstance(params.y_axis, str)
                    else params.y_axis[0],
                )

                if (
                    x_data is not None
                    and y_data is not None
                    and len(x_data) == len(y_data)
                ):
                    processed_data = pd.DataFrame(
                        {
                            params.x_axis: x_data,
                            params.y_axis
                            if isinstance(params.y_axis, str)
                            else params.y_axis[0]: y_data,
                        }
                    )

            # If we've processed data successfully, use it
            if processed_data is not None:
                data = processed_data
            else:
                logger.warning(
                    "DEBUG LINE_PLOT - Could not process dictionary to DataFrame"
                )
                logger.warning("DEBUG LINE_PLOT - Input data: {}".format(data))

        # Continue with DataFrame validation and plotting
        if data is None or not isinstance(data, pd.DataFrame) or data.empty:
            logger.warning(
                "No data or invalid data type provided to LinePlotWidget (expected non-empty DataFrame)."
            )
            return "<p class='info'>No data available for the line plot.</p>"

        # Validate required columns
        required_cols = {params.x_axis}
        if isinstance(params.y_axis, str):
            required_cols.add(params.y_axis)
        else:
            required_cols.update(params.y_axis)

        if params.color_field:
            required_cols.add(params.color_field)
        if params.line_group:
            required_cols.add(params.line_group)
        if params.hover_name:
            required_cols.add(params.hover_name)
        if params.hover_data:
            required_cols.update(params.hover_data)
        if isinstance(params.markers, str):
            required_cols.add(params.markers)

        missing_cols = required_cols - set(data.columns)
        if missing_cols:
            logger.error(
                "Missing required columns for LinePlotWidget: {}".format(missing_cols)
            )
            return (
                "<p class='error'>Configuration Error: Missing columns {}.</p>".format(
                    missing_cols
                )
            )

        # Attempt to convert x_axis to datetime if it looks like one
        df_plot = data.copy()
        try:
            if df_plot[params.x_axis].dtype == "object":
                df_plot[params.x_axis] = pd.to_datetime(
                    df_plot[params.x_axis], errors="ignore"
                )
        except Exception as e:
            logger.warning(
                "Could not convert x-axis '{}' to datetime: {}".format(params.x_axis, e)
            )

        # Sort by x-axis to ensure lines are drawn correctly, especially for time series
        if pd.api.types.is_datetime64_any_dtype(
            df_plot[params.x_axis]
        ) or pd.api.types.is_numeric_dtype(df_plot[params.x_axis]):
            try:
                df_plot = df_plot.sort_values(by=params.x_axis)
            except Exception as e:
                logger.error(
                    "Error sorting by x-axis '{}': {}".format(params.x_axis, e)
                )
        else:
            logger.info(
                "X-axis '{}' is not numeric or datetime, skipping sort.".format(
                    params.x_axis
                )
            )

        try:
            # Create a dictionary of parameters for px.line(), filtering out None values
            line_args = {
                "data_frame": df_plot,
                "x": params.x_axis,
                "y": params.y_axis,
                "color": params.color_field,
                "line_group": params.line_group,
                "markers": params.markers,
                "line_shape": params.line_shape,
                "hover_name": params.hover_name,
                "hover_data": params.hover_data,
                "color_discrete_map": params.color_discrete_map,
                "labels": params.labels,
                "log_y": params.log_y,
                "title": None,
            }

            # Remove None values and unsupported parameters
            # color_continuous_scale is not supported by px.line()
            line_args = {
                k: v
                for k, v in line_args.items()
                if v is not None and k != "color_continuous_scale"
            }

            fig = px.line(**line_args)

            layout_updates = {
                "xaxis_title": params.labels.get(params.x_axis)
                if params.labels
                else params.x_axis,
                "yaxis_title": params.labels.get(
                    params.y_axis if isinstance(params.y_axis, str) else "value"
                )
                if params.labels
                else (params.y_axis if isinstance(params.y_axis, str) else "Value"),
                "legend_title_text": params.labels.get(params.color_field)
                if params.labels and params.color_field
                else params.color_field,
            }

            apply_plotly_defaults(fig, layout_updates)

            # Handle logarithmic x-axis if specified in params
            if hasattr(params, "xaxis_type") and params.xaxis_type == "logarithmic":
                fig.update_xaxes(type="log")

            return render_plotly_figure(fig)

        except Exception as e:
            logger.exception("Error rendering LinePlotWidget: {}".format(e))
            return "<p class='error'>Error generating line plot: {}</p>".format(e)
