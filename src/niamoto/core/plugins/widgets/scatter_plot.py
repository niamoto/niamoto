import logging
from typing import Dict, List, Optional, Set

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


# Pydantic model for Scatter Plot parameters validation
class ScatterPlotParams(BaseModel):
    title: Optional[str] = Field(None, description="Optional title for the plot.")
    x_axis: str = Field(..., description="Field name for the X-axis.")
    y_axis: str = Field(..., description="Field name for the Y-axis.")
    color_field: Optional[str] = Field(
        None, description="Field to use for coloring points."
    )
    size_field: Optional[str] = Field(
        None, description="Field to use for sizing points."
    )
    symbol_field: Optional[str] = Field(
        None, description="Field to use for different point symbols."
    )
    hover_name: Optional[str] = Field(
        None, description="Field to display as the main label on hover."
    )
    hover_data: Optional[List[str]] = Field(
        None, description="List of additional fields to display on hover."
    )
    trendline: Optional[str] = Field(
        None, description="Type of trendline to add (e.g., 'ols', 'lowess')."
    )
    facet_col: Optional[str] = Field(
        None, description="Field to create faceted columns."
    )
    facet_row: Optional[str] = Field(None, description="Field to create faceted rows.")
    log_x: bool = Field(False, description="Use a logarithmic scale for the X-axis.")
    log_y: bool = Field(False, description="Use a logarithmic scale for the Y-axis.")
    labels: Optional[Dict[str, str]] = Field(
        None, description="Dictionary to override axis/legend labels."
    )
    # Add other relevant plotly express scatter arguments as needed
    color_discrete_map: Optional[Dict[str, str]] = Field(
        None, description="Explicit color mapping for discrete colors."
    )
    size_max: Optional[int] = Field(None, description="Maximum size of the markers.")


@register("scatter_plot", PluginType.WIDGET)
class ScatterPlotWidget(WidgetPlugin):
    """Widget to display a scatter plot using Plotly Express."""

    param_schema = ScatterPlotParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Plotly is handled centrally."""
        return get_plotly_dependencies()

    # get_container_html is inherited from WidgetPlugin

    def render(self, data: Optional[pd.DataFrame], params: ScatterPlotParams) -> str:
        """Generate the HTML for the scatter plot."""
        if data is None or data.empty:
            logger.info("No data provided to ScatterPlotWidget.")
            return "<p class='info'>No data available for scatter plot.</p>"

        # Validate required columns
        required_cols = {params.x_axis, params.y_axis}
        if params.color_field:
            required_cols.add(params.color_field)
        if params.size_field:
            required_cols.add(params.size_field)
        if params.symbol_field:
            required_cols.add(params.symbol_field)
        if params.hover_name:
            required_cols.add(params.hover_name)
        if params.facet_col:
            required_cols.add(params.facet_col)
        if params.facet_row:
            required_cols.add(params.facet_row)
        if params.hover_data:
            # Ensure hover_data is a list even if provided as a single string initially
            hover_data_list = (
                params.hover_data
                if isinstance(params.hover_data, list)
                else [params.hover_data]
            )
            required_cols.update(hover_data_list)

        missing_cols = required_cols - set(data.columns)
        if missing_cols:
            logger.error(
                f"Missing required columns for ScatterPlotWidget: {missing_cols}"
            )
            return f"<p class='error'>Configuration Error: Missing columns {missing_cols}.</p>"

        # Check data types for numeric axes/size
        numeric_cols = {params.x_axis, params.y_axis}
        if params.size_field:
            numeric_cols.add(params.size_field)

        for col in numeric_cols:
            if not pd.api.types.is_numeric_dtype(data[col]):
                try:
                    # Attempt conversion
                    data[col] = pd.to_numeric(data[col], errors="coerce")
                    if data[col].isnull().any():
                        logger.warning(
                            f"Column '{col}' used for numeric axis/size contains non-numeric values or NaNs after conversion."
                        )
                        # Decide whether to dropna or return error. Returning error for now.
                        return f"<p class='error'>Data Error: Column '{col}' contains non-numeric values.</p>"
                except Exception as e:
                    logger.error(f"Failed to convert column '{col}' to numeric: {e}")
                    return f"<p class='error'>Data Error: Could not process numeric column '{col}'.</p>"

        try:
            # Prepare arguments for px.scatter, filtering out None values
            plot_args = {
                "data_frame": data,
                "x": params.x_axis,
                "y": params.y_axis,
                "color": params.color_field,
                "size": params.size_field,
                "symbol": params.symbol_field,
                "hover_name": params.hover_name,
                "hover_data": params.hover_data,
                "trendline": params.trendline,
                "facet_col": params.facet_col,
                "facet_row": params.facet_row,
                "log_x": params.log_x,
                "log_y": params.log_y,
                "labels": params.labels or {},
                "title": params.title or "",  # Use Widget title, px title adds space
                "color_discrete_map": params.color_discrete_map,
                "size_max": params.size_max,
            }
            # Filter out keys with None values
            plot_args = {k: v for k, v in plot_args.items() if v is not None}

            fig = px.scatter(**plot_args)

            # Layout updates
            layout_updates = {
                "margin": {
                    "r": 10,
                    "t": 30 if params.title else 10,
                    "l": 10,
                    "b": 10,
                },  # Adjust top margin if title exists
            }

            apply_plotly_defaults(fig, layout_updates)

            # Render figure to HTML
            return render_plotly_figure(fig)

        except Exception as e:
            logger.exception(f"Error rendering ScatterPlotWidget: {e}")
            return f"<p class='error'>Error generating scatter plot: {e}</p>"
