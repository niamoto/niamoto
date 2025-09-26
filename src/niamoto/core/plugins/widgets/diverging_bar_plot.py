import logging
from typing import Any, List, Optional, Set

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


# Pydantic model for Diverging Bar Plot parameters validation
class DivergingBarPlotParams(BasePluginParams):
    """Parameters for diverging bar plot widget."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Create diverging bar charts with positive/negative color coding",
            "examples": [
                {
                    "x_axis": "category",
                    "y_axis": "value",
                    "threshold": 0.0,
                    "color_positive": "#2ca02c",
                    "color_negative": "#d62728",
                }
            ],
        }
    )

    title: Optional[str] = Field(
        default=None, description="Chart title", json_schema_extra={"ui:widget": "text"}
    )
    description: Optional[str] = Field(
        default=None,
        description="Chart description",
        json_schema_extra={"ui:widget": "textarea"},
    )
    x_axis: str = Field(
        ...,
        description="Field name for the category axis (Y in horizontal bar plot)",
        json_schema_extra={"ui:widget": "field-select"},
    )
    y_axis: str = Field(
        ...,
        description="Field name for the value axis (X in horizontal bar plot)",
        json_schema_extra={"ui:widget": "field-select"},
    )
    color_positive: str = Field(
        default="#2ca02c",
        description="Hex color for positive bars",
        json_schema_extra={"ui:widget": "color"},
    )
    color_negative: str = Field(
        default="#d62728",
        description="Hex color for negative bars",
        json_schema_extra={"ui:widget": "color"},
    )
    threshold: float = Field(
        default=0.0,
        description="Value threshold to determine positive/negative",
        json_schema_extra={"ui:widget": "number", "ui:step": 0.1},
    )
    orientation: Optional[str] = Field(
        default="h",
        description="Bar orientation",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": [
                {"value": "h", "label": "Horizontal"},
                {"value": "v", "label": "Vertical"},
            ],
        },
    )
    hover_name: Optional[str] = Field(
        default=None,
        description="Field name for hover text",
        json_schema_extra={"ui:widget": "field-select"},
    )
    hover_data: Optional[List[str]] = Field(
        default=None,
        description="Additional fields for hover tooltip",
        json_schema_extra={"ui:widget": "array", "ui:item-widget": "field-select"},
    )
    xaxis_title: Optional[str] = Field(
        default=None,
        description="X-axis title",
        json_schema_extra={"ui:widget": "text"},
    )
    yaxis_title: Optional[str] = Field(
        default=None,
        description="Y-axis title",
        json_schema_extra={"ui:widget": "text"},
    )
    sort_values: Optional[bool] = Field(
        default=True,
        description="Whether to sort bars by value",
        json_schema_extra={"ui:widget": "checkbox"},
    )


@register("diverging_bar_plot", PluginType.WIDGET)
class DivergingBarPlotWidget(WidgetPlugin):
    """Widget to display a diverging bar plot (horizontal or vertical) using Plotly."""

    param_schema = DivergingBarPlotParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Plotly is handled centrally."""
        return get_plotly_dependencies()

    def render(self, data: Optional[Any], params: DivergingBarPlotParams) -> str:
        """Generate the HTML for the diverging bar plot."""
        if data is None or not isinstance(data, pd.DataFrame) or data.empty:
            logger.warning(
                "No data or invalid data type provided to DivergingBarPlotWidget (expected non-empty DataFrame)."
            )
            return "<p class='info'>No data available for the diverging bar plot.</p>"

        # Validate required columns exist
        required_cols = {params.x_axis, params.y_axis}
        if params.hover_name:
            required_cols.add(params.hover_name)
        if params.hover_data:
            required_cols.update(params.hover_data)

        missing_cols = required_cols - set(data.columns)
        if missing_cols:
            logger.error(
                f"Missing required columns for DivergingBarPlotWidget: {missing_cols}"
            )
            return f"<p class='error'>Configuration Error: Missing columns {missing_cols}.</p>"

        # Prepare data (sorting)
        df_plot = data.copy()

        # Check if all y-axis values are zero or null (no meaningful data)
        y_values = df_plot[params.y_axis]
        if pd.isna(y_values).all() or (y_values == 0).all():
            return "<p class='info'>Pas de données disponibles.</p>"

        if params.sort_values:
            try:
                df_plot = df_plot.sort_values(by=params.y_axis, ascending=True)
            except KeyError:
                logger.error(f"Sort column '{params.y_axis}' not found.")
                # Proceed without sorting
            except Exception as e:
                logger.error(f"Error sorting data: {e}")
                # Proceed without sorting

        try:
            # Determine colors based on threshold
            colors = [
                params.color_positive
                if x >= params.threshold
                else params.color_negative
                for x in df_plot[params.y_axis]
            ]

            fig = go.Figure()

            hover_text = None
            if params.hover_name:
                hover_text = df_plot[params.hover_name]
            custom_data = None
            hover_template_parts = []
            if params.hover_data:
                custom_data = df_plot[params.hover_data].values
                for i, col in enumerate(params.hover_data):
                    hover_template_parts.append(
                        f"<b>{col}</b>: %{{customdata[{i}]}}<br>"
                    )
            # Always include X and Y axis values
            if params.orientation == "h":
                hover_template_parts.insert(
                    0, f"<b>{params.yaxis_title or params.y_axis}</b>: %{{x}}<br>"
                )
                hover_template_parts.insert(
                    0, f"<b>{params.xaxis_title or params.x_axis}</b>: %{{y}}<br>"
                )
            else:  # Vertical
                hover_template_parts.insert(
                    0, f"<b>{params.yaxis_title or params.y_axis}</b>: %{{y}}<br>"
                )
                hover_template_parts.insert(
                    0, f"<b>{params.xaxis_title or params.x_axis}</b>: %{{x}}<br>"
                )

            hover_template = (
                "".join(hover_template_parts) + "<extra></extra>"
            )  # <extra></extra> removes the trace info box

            fig.add_trace(
                go.Bar(
                    x=df_plot[params.y_axis]
                    if params.orientation == "h"
                    else df_plot[params.x_axis],
                    y=df_plot[params.x_axis]
                    if params.orientation == "h"
                    else df_plot[params.y_axis],
                    orientation=params.orientation,
                    marker_color=colors,
                    text=df_plot[
                        params.y_axis
                    ],  # Show value on bar (optional, maybe make configurable)
                    textposition="auto",
                    name="",  # Avoid default legend entry
                    hovertext=hover_text,
                    customdata=custom_data,
                    hovertemplate=hover_template,
                )
            )

            # Layout updates
            layout_updates = {
                "title": None,  # Title handled by container
                "xaxis_title": params.yaxis_title
                if params.orientation == "h"
                else params.xaxis_title,
                "yaxis_title": params.xaxis_title
                if params.orientation == "h"
                else params.yaxis_title,
                "bargap": 0.15,
                "showlegend": False,  # Typically not needed for single trace
            }
            # Add zero line for clarity
            if params.orientation == "h":
                layout_updates["xaxis_zeroline"] = True
                layout_updates["xaxis_zerolinecolor"] = "grey"
                layout_updates["xaxis_zerolinewidth"] = 1
            else:
                layout_updates["yaxis_zeroline"] = True
                layout_updates["yaxis_zerolinecolor"] = "grey"
                layout_updates["yaxis_zerolinewidth"] = 1

            apply_plotly_defaults(fig, layout_updates)

            # Render figure to HTML
            return render_plotly_figure(fig)

        except Exception as e:
            logger.exception(f"Error rendering DivergingBarPlotWidget: {e}")
            return f"<p class='error'>Error generating diverging bar plot: {e}</p>"
