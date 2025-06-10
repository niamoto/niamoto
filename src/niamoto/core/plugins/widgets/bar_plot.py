import logging
from typing import Any, Dict, List, Optional, Union, Set

import pandas as pd
import plotly.express as px
from pydantic import BaseModel, Field

from niamoto.common.utils.data_access import convert_to_dataframe, transform_data
from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.core.plugins.widgets.plotly_utils import (
    apply_plotly_defaults,
    render_plotly_figure,
    get_plotly_dependencies,
)

logger = logging.getLogger(__name__)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex."""
    return f"#{r:02x}{g:02x}{b:02x}"


def generate_gradient_colors(
    base_color: str, count: int, mode: str = "luminance"
) -> List[str]:
    """Generate a gradient of colors based on a base color.

    Args:
        base_color: Base color in hex format (e.g., '#1fb99d')
        count: Number of colors to generate
        mode: Gradient mode - 'luminance' (light to dark) or 'saturation' (saturated to pale)

    Returns:
        List of hex color strings forming a gradient
    """
    if count <= 0:
        return []

    if count == 1:
        return [base_color]

    # Convert base color to RGB
    r, g, b = hex_to_rgb(base_color)

    colors = []

    if mode == "luminance":
        # Create gradient from lighter to darker
        for i in range(count):
            # Calculate factor: 0.3 (lightest) to 1.0 (original color)
            factor = 0.3 + (0.7 * i / (count - 1))

            # Apply factor to create gradient
            new_r = int(r * factor + 255 * (1 - factor))
            new_g = int(g * factor + 255 * (1 - factor))
            new_b = int(b * factor + 255 * (1 - factor))

            colors.append(rgb_to_hex(new_r, new_g, new_b))

    elif mode == "saturation":
        # Create gradient from saturated to pale
        for i in range(count):
            # Calculate factor: 1.0 (full saturation) to 0.3 (pale)
            factor = 1.0 - (0.7 * i / (count - 1))

            # Mix with gray to reduce saturation
            gray = 128
            new_r = int(r * factor + gray * (1 - factor))
            new_g = int(g * factor + gray * (1 - factor))
            new_b = int(b * factor + gray * (1 - factor))

            colors.append(rgb_to_hex(new_r, new_g, new_b))

    return colors


def generate_colors(count: int) -> List[str]:
    """Generate harmonious colors using HSL color space and golden ratio.

    Args:
        count: Number of colors to generate

    Returns:
        List of hex color strings
    """

    def hsl_to_rgb(h: float, s: float, lightness: float) -> tuple[int, int, int]:
        """Convert HSL to RGB."""
        if s == 0:
            r = g = b = lightness  # achromatic
        else:

            def hue_to_rgb(p: float, q: float, t: float) -> float:
                if t < 0:
                    t += 1
                if t > 1:
                    t -= 1
                if t < 1 / 6:
                    return p + (q - p) * 6 * t
                if t < 1 / 2:
                    return q
                if t < 2 / 3:
                    return p + (q - p) * (2 / 3 - t) * 6
                return p

            q = (
                lightness * (1 + s)
                if lightness < 0.5
                else lightness + s - lightness * s
            )
            p = 2 * lightness - q
            r = hue_to_rgb(p, q, h + 1 / 3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1 / 3)

        return (round(r * 255), round(g * 255), round(b * 255))

    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex."""
        return f"#{r:02x}{g:02x}{b:02x}"

    colors = []
    for i in range(count):
        # Use golden ratio to spread hues evenly
        hue = (i * 0.618033988749895) % 1

        # Vary saturation slightly
        saturation = 0.5 + (i % 3) * 0.1

        # Vary lightness to create contrast
        lightness = 0.4 + (i % 2) * 0.2

        r, g, b = hsl_to_rgb(hue, saturation, lightness)
        colors.append(rgb_to_hex(r, g, b))

    return colors


# Pydantic model for Bar Plot parameters validation
class BarPlotParams(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    x_axis: str = Field(..., description="Field name for the X-axis (categories).")
    y_axis: str = Field(..., description="Field name for the Y-axis (values).")
    color_field: Optional[str] = Field(
        None,
        description="Field name for color grouping (creates grouped/stacked bars).",
    )
    barmode: Optional[str] = Field(
        "group", description="'group', 'stack', or 'relative'."
    )
    orientation: Optional[str] = Field(
        "v", description="'v' (vertical) or 'h' (horizontal)."
    )
    text_auto: Union[bool, str] = Field(
        True,
        description="Display values on bars (True, False, or formatting string like '.2f').",
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
    sort_order: Optional[str] = Field(
        None, description="Sort bars: 'ascending', 'descending', or None."
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
    auto_color: bool = Field(
        False, description="Automatically generate harmonious colors for each bar"
    )
    gradient_color: Optional[str] = Field(
        None,
        description="Base color for gradient generation (e.g., '#1fb99d'). Overrides auto_color if set",
    )
    gradient_mode: Optional[str] = Field(
        "luminance",
        description="Gradient mode: 'luminance' (light to dark) or 'saturation' (saturated to pale)",
    )
    bar_width: Optional[float] = Field(
        None,
        description="Width of bars (0.0 to 1.0). If None, width is calculated automatically based on data count",
    )
    filter_zero_values: bool = Field(
        False, description="Remove bars with zero or null values from the plot"
    )
    show_legend: bool = Field(
        True, description="Show or hide the legend. Default is True to show the legend"
    )


@register("bar_plot", PluginType.WIDGET)
class BarPlotWidget(WidgetPlugin):
    """Widget to display a bar plot using Plotly."""

    param_schema = BarPlotParams  # Correct name for validation

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies."""
        return get_plotly_dependencies()

    def render(self, data: Optional[Any], params: BarPlotParams) -> str:
        """Generate the HTML for the bar plot."""

        # --- Data Processing --- #

        # 1. Apply transformation if specified
        if params.transform:
            data = transform_data(data, params.transform, params.transform_params or {})

        # 2. Convert data to DataFrame using our generic utility
        processed_data = convert_to_dataframe(
            data=data,
            x_field=params.x_axis,
            y_field=params.y_axis,
            color_field=params.color_field,
            mapping=params.field_mapping,
        )

        # If we couldn't process the data with the generic method
        if processed_data is None:
            if isinstance(data, dict):
                logger.error(
                    "Dict input could not be processed for bar plot. Please check configuration."
                )
                return "<p class='error'>Input dict structure not recognized. Check your configuration and ensure data_source points to the correct data.</p>"
            else:
                logger.error(
                    "Unsupported input type for BarPlotWidget: {}".format(type(data))
                )
                return "<p class='error'>Unsupported data type: {}. Expected dictionary or DataFrame.</p>".format(
                    type(data)
                )

        # --- Data Validation (operates on processed_data) --- #
        if (
            processed_data is None
            or not isinstance(processed_data, pd.DataFrame)
            or processed_data.empty
        ):
            return "<p class='info'>No data available for the bar plot.</p>"

        # Verify required columns are present in the processed DataFrame
        required_cols = {params.x_axis, params.y_axis}

        if params.color_field:
            required_cols.add(params.color_field)
        if params.hover_name:
            required_cols.add(params.hover_name)
        if params.hover_data:
            required_cols.update(params.hover_data)

        missing_cols = required_cols - set(processed_data.columns)
        if missing_cols:
            logger.debug(
                "Data structure causing validation failure:\n{}".format(processed_data)
            )  # Log the structure
            logger.error(
                "Missing required columns in processed data for BarPlotWidget: {}. Required: {}. Available: {}".format(
                    missing_cols, required_cols, set(processed_data.columns)
                )
            )
            return "<p class='error'>Configuration Error: Processed data missing required columns {}. Check data source and widget params.</p>".format(
                missing_cols
            )

        # Create a copy to avoid modifying the original
        df_plot = processed_data.copy()

        # Check if all values are zero or null (no meaningful data)
        # The value column depends on orientation
        if params.orientation == "h":
            # Horizontal bars: values are on x-axis
            value_column = params.x_axis
        else:
            # Vertical bars: values are on y-axis
            value_column = params.y_axis

        if value_column in df_plot.columns:
            values = df_plot[value_column]
            if pd.isna(values).all() or (values == 0).all():
                return "<p class='info'>No data available.</p>"

        # Filter zero values if requested
        if params.filter_zero_values:
            # Remove rows where y-axis value is 0 or null
            mask = pd.notna(df_plot[params.y_axis]) & (df_plot[params.y_axis] != 0)
            df_plot = df_plot[mask]
            logger.debug(
                f"Filtered {len(processed_data) - len(df_plot)} zero/null values from data"
            )

        # Apply sorting if specified
        if params.sort_order:
            ascending = params.sort_order == "ascending"
            try:
                # Sort by the values axis (depends on orientation)
                if params.orientation == "h":
                    # For horizontal bars, sort by x_axis (values)
                    sort_column = params.x_axis
                    df_plot = df_plot.sort_values(by=sort_column, ascending=ascending)
                    # Ensure y-axis categories (labels) respect this order
                    df_plot[params.y_axis] = pd.Categorical(
                        df_plot[params.y_axis],
                        categories=df_plot[params.y_axis].unique(),
                        ordered=True,
                    )
                else:
                    # For vertical bars, sort by y_axis (values)
                    sort_column = params.y_axis
                    df_plot = df_plot.sort_values(by=sort_column, ascending=ascending)
                    # Ensure x-axis categories (labels) respect this order
                    df_plot[params.x_axis] = pd.Categorical(
                        df_plot[params.x_axis],
                        categories=df_plot[params.x_axis].unique(),
                        ordered=True,
                    )
            except KeyError:
                logger.warning(
                    "Cannot sort by column '{}' as it might be missing after potential aggregation or wrong name.".format(
                        sort_column
                    )
                )
            except Exception as e:
                logger.error("Error applying sorting: {}".format(e))

        try:
            # Handle automatic coloring
            color_field = params.color_field
            color_discrete_sequence = None
            color_discrete_map = params.color_discrete_map

            # Check if gradient color is specified
            if params.gradient_color and not params.color_field:
                # For gradient coloring without grouping, we need to create a color field
                # that assigns each bar its own category
                if params.orientation == "h":
                    # For horizontal bars, each y-axis value gets its own color
                    category_field = params.y_axis
                else:
                    # For vertical bars, each x-axis value gets its own color
                    category_field = params.x_axis

                # Create a temporary color field that's just a copy of the category field
                df_plot["_gradient_color"] = df_plot[category_field].astype(str)
                color_field = "_gradient_color"

                # Generate gradient colors based on unique categories
                unique_categories = df_plot[category_field].unique()
                num_categories = len(unique_categories)
                generated_colors = generate_gradient_colors(
                    params.gradient_color, num_categories, params.gradient_mode
                )

                # Create a color mapping
                color_discrete_map = {
                    str(cat): color
                    for cat, color in zip(unique_categories, generated_colors)
                }

            elif params.auto_color and not params.color_field:
                # For auto-coloring without grouping, we need to create a color field
                # that assigns each bar its own category
                if params.orientation == "h":
                    # For horizontal bars, each y-axis value gets its own color
                    category_field = params.y_axis
                else:
                    # For vertical bars, each x-axis value gets its own color
                    category_field = params.x_axis

                # Create a temporary color field that's just a copy of the category field
                df_plot["_auto_color"] = df_plot[category_field].astype(str)
                color_field = "_auto_color"

                # Generate colors based on unique categories
                unique_categories = df_plot[category_field].unique()
                num_categories = len(unique_categories)
                generated_colors = generate_colors(num_categories)

                # Create a color mapping
                color_discrete_map = {
                    str(cat): color
                    for cat, color in zip(unique_categories, generated_colors)
                }

            fig = px.bar(
                df_plot,
                x=params.x_axis,
                y=params.y_axis,
                color=color_field,
                barmode=params.barmode,
                orientation=params.orientation,
                text_auto=params.text_auto,
                hover_name=params.hover_name,
                hover_data=params.hover_data,
                color_discrete_map=color_discrete_map,
                color_discrete_sequence=color_discrete_sequence,
                color_continuous_scale=params.color_continuous_scale,
                range_y=params.range_y,
                labels=params.labels,
                title=None,  # Title handled by container
            )

            # Additional layout updates if needed (e.g., axis titles if not covered by labels)
            layout_updates = {
                "xaxis_title": params.labels.get(params.x_axis)
                if params.labels
                else params.x_axis,
                "yaxis_title": params.labels.get(params.y_axis)
                if params.labels
                else params.y_axis,
            }

            # Handle legend visibility
            if not params.show_legend:
                # User explicitly wants to hide the legend
                layout_updates["showlegend"] = False
            elif params.auto_color and not params.color_field:
                # Hide legend when auto-coloring since it would duplicate the axis labels
                layout_updates["showlegend"] = False
            else:
                # Show legend with proper title for regular color fields
                layout_updates["showlegend"] = True
                layout_updates["legend_title_text"] = (
                    params.labels.get(params.color_field)
                    if params.labels and params.color_field
                    else params.color_field
                )

            # Apply Plotly defaults (includes watermark removal)
            apply_plotly_defaults(fig, layout_updates)

            # Calculate and set bar width for better visibility
            bar_width = params.bar_width
            if bar_width is None:
                # Auto-calculate width based on number of bars
                num_bars = len(df_plot)
                if num_bars <= 5:
                    bar_width = 0.8
                elif num_bars <= 10:
                    bar_width = 0.6
                elif num_bars <= 20:
                    bar_width = 0.4
                else:
                    bar_width = 0.3

            fig.update_traces(width=bar_width)

            # Render figure to HTML with standard config
            return render_plotly_figure(fig)

        except Exception as e:
            logger.exception("Error rendering BarPlotWidget: {}".format(e))
            return "<p class='error'>Error generating bar plot: {}</p>".format(e)
