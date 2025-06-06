import logging
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import plotly.graph_objects as go
from pydantic import BaseModel, Field

from niamoto.common.utils.data_access import convert_to_dataframe, transform_data
from niamoto.core.plugins.base import PluginType, WidgetPlugin, register
from niamoto.core.plugins.widgets.plotly_utils import (
    apply_plotly_defaults,
    get_plotly_dependencies,
    render_plotly_figure,
)

logger = logging.getLogger(__name__)


class StackedAreaPlotParams(BaseModel):
    """Parameters for the Stacked Area Plot widget."""

    title: Optional[str] = None
    description: Optional[str] = None
    x_field: str = Field(
        ..., description="Field name for the X-axis (usually dates/categories)."
    )
    y_fields: List[str] = Field(
        ..., description="List of field names for each area series."
    )
    colors: Optional[List[str]] = Field(
        None, description="Colors for each series (must match y_fields length)."
    )
    fill_type: str = Field(
        "tonexty", description="Fill type for areas: 'tonexty', 'tozeroy', etc."
    )
    axis_titles: Optional[Dict[str, str]] = Field(
        None, description="Custom axis titles {'x': 'X Label', 'y': 'Y Label'}"
    )
    hover_template: Optional[str] = Field(
        None, description="Custom hover template (Plotly format)."
    )
    log_x: Optional[bool] = Field(
        False, description="Use logarithmic scale for X-axis."
    )
    log_y: Optional[bool] = Field(
        False, description="Use logarithmic scale for Y-axis."
    )
    # New fields for data transformation
    transform: Optional[str] = Field(
        None,
        description="Type of transformation to apply to data: 'extract_series', 'unpivot', 'pivot', etc.",
    )
    transform_params: Optional[Dict[str, Any]] = Field(
        None, description="Parameters for the transformation"
    )
    # Fields for field mappings
    field_mapping: Optional[Dict[str, str]] = Field(
        None, description="Mapping from data fields to expected column names"
    )


@register("stacked_area_plot", PluginType.WIDGET)
class StackedAreaPlotWidget(WidgetPlugin):
    """Widget to display a stacked area chart using Plotly."""

    param_schema = StackedAreaPlotParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies."""
        return get_plotly_dependencies()

    def render(self, data: Optional[Any], params: StackedAreaPlotParams) -> str:
        """Generate the HTML for the stacked area plot."""

        # --- Data Processing --- #

        # 1. Apply transformation if specified
        if params.transform:
            data = transform_data(data, params.transform, params.transform_params)

        # 2. Create a DataFrame if needed
        df = None

        # If already a DataFrame, use it
        if isinstance(data, pd.DataFrame):
            df = data.copy()

        # Process dictionary data based on the specified transformation
        elif isinstance(data, dict):
            # Case: Extract series from a structure with x_field and multiple y-series
            if params.transform == "extract_series" and params.transform_params:
                # The transform_params should specify where to find the x values and y series
                x_values = None
                series_dict = None

                # Get the x values
                if params.x_field in data:
                    x_values = data[params.x_field]

                # Get the series data (could be nested)
                series_field = params.transform_params.get("series_field")
                if (
                    series_field
                    and series_field in data
                    and isinstance(data[series_field], dict)
                ):
                    series_dict = data[series_field]

                # Create DataFrame if we have both components
                if x_values is not None and series_dict is not None:
                    df = pd.DataFrame({params.x_field: x_values})

                    # Add each series as a column
                    for y_field in params.y_fields:
                        if y_field in series_dict:
                            df[y_field] = series_dict[y_field]

            # Generic approach - use our utility
            else:
                # For stacked area plots, we need to try each y_field
                # First see if we can create a base DataFrame with x_field
                base_df = None
                for y_field in params.y_fields:
                    temp_df = convert_to_dataframe(
                        data=data,
                        x_field=params.x_field,
                        y_field=y_field,
                        mapping=params.field_mapping,
                    )

                    if temp_df is not None:
                        if base_df is None:
                            base_df = temp_df[[params.x_field, y_field]]
                        else:
                            # Add this y_field column to the base DataFrame
                            base_df[y_field] = temp_df[y_field]

                df = base_df

        # --- Data Validation --- #
        if df is None or df.empty:
            logger.warning("No valid data available for StackedAreaPlotWidget.")
            return "<p class='info'>No data available for the stacked area plot.</p>"

        # Check that all required columns are present
        required_cols = {params.x_field} | set(params.y_fields)
        missing_cols = required_cols - set(df.columns)

        if missing_cols:
            missing_y_fields = set(params.y_fields) & missing_cols
            if missing_y_fields:
                # If we're missing some y_fields, we'll continue with those we have
                available_y_fields = [y for y in params.y_fields if y in df.columns]
                if not available_y_fields:
                    logger.error(f"All y_fields are missing: {params.y_fields}")
                    return "<p class='error'>No series data available. Missing all specified y_fields.</p>"

                logger.warning(
                    f"Some y_fields are missing: {missing_y_fields}. Continuing with: {available_y_fields}"
                )
                params.y_fields = available_y_fields

            # If x_field is missing, it's a critical error
            if params.x_field in missing_cols:
                logger.error(f"Missing critical x_field: {params.x_field}")
                return f"<p class='error'>Missing x-axis field: {params.x_field}</p>"

        # --- Generate Plot --- #
        try:
            fig = go.Figure()

            # Add traces for each series
            colors = params.colors or None
            for i, y_field in enumerate(params.y_fields):
                color = colors[i] if colors and i < len(colors) else None

                # Create the trace
                trace_args = {
                    "x": df[params.x_field],
                    "y": df[y_field],
                    "name": y_field,
                    "fill": params.fill_type,
                    "stackgroup": "one",  # Stack traces on top of each other
                }

                if params.hover_template:
                    trace_args["hovertemplate"] = params.hover_template

                # Apply color to both line and fill
                if color:
                    trace_args["line"] = dict(color=color, width=0)  # No line border
                    trace_args["fillcolor"] = color

                fig.add_trace(go.Scatter(**trace_args))

            # Update layout
            layout_updates = {
                "title": None,  # Handled by container
                "xaxis_title": params.axis_titles.get("x")
                if params.axis_titles
                else params.x_field,
                "yaxis_title": params.axis_titles.get("y")
                if params.axis_titles
                else None,
                "legend_title_text": "Series",
            }

            # Apply logarithmic scales if requested
            if params.log_x:
                layout_updates["xaxis_type"] = "log"
            if params.log_y:
                layout_updates["yaxis_type"] = "log"

            apply_plotly_defaults(fig, layout_updates)

            # Render figure to HTML
            return render_plotly_figure(fig)

        except Exception as e:
            logger.exception(f"Error rendering StackedAreaPlotWidget: {e}")
            return f"<p class='error'>Error generating stacked area plot: {str(e)}</p>"
