import logging
from typing import Any, Dict, List, Optional, Set, Union

import pandas as pd
import plotly.express as px
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

logger = logging.getLogger(__name__)


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


@register("bar_plot", PluginType.WIDGET)
class BarPlotWidget(WidgetPlugin):
    """Widget to display a bar plot using Plotly."""

    param_schema = BarPlotParams  # Correct name for validation

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Plotly is handled centrally."""
        return set()

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

    def render(self, data: Optional[Any], params: BarPlotParams) -> str:
        """Generate the HTML for the bar plot."""

        # DEBUG: Print data structure and requested parameters
        print("\n" + "=" * 80)
        print(
            f"DEBUG BAR_PLOT - data_source: {getattr(params, 'data_source', 'unknown')}"
        )
        print(f"DEBUG BAR_PLOT - x_axis: {params.x_axis}, y_axis: {params.y_axis}")
        print("DEBUG BAR_PLOT - data type: {}".format(type(data)))

        if isinstance(data, dict):
            print("DEBUG BAR_PLOT - Dict top level keys: {}".format(list(data.keys())))

            # Print specific structures based on known patterns
            if "elevation" in data and isinstance(data["elevation"], dict):
                print(
                    "DEBUG BAR_PLOT - Elevation structure: {}".format(
                        list(data["elevation"].keys())
                    )
                )
                print(
                    "DEBUG BAR_PLOT - First few classes: {}".format(
                        data["elevation"]["classes"][:5]
                    )
                )
                print(
                    "DEBUG BAR_PLOT - First few subset values: {}".format(
                        data["elevation"]["subset"][:5]
                    )
                )

            if "forest" in data and "non_forest" in data:
                print("DEBUG BAR_PLOT - Holdridge structure:")
                print(
                    "DEBUG BAR_PLOT - Forest keys: {}".format(
                        list(data["forest"].keys())
                    )
                )
                print(
                    "DEBUG BAR_PLOT - Non-forest keys: {}".format(
                        list(data["non_forest"].keys())
                    )
                )

            if "class_name" in data and "series" in data:
                print("DEBUG BAR_PLOT - Forest cover structure:")
                print(
                    "DEBUG BAR_PLOT - Series keys: {}".format(
                        list(data["series"].keys())
                    )
                )

        # --- Data Structure Handling --- #
        processed_data = None

        if isinstance(data, pd.DataFrame):
            # Handle pandas DataFrame directly
            processed_data = data

        elif isinstance(data, dict):
            # Handle nested data structures with dot notation
            x_data = None
            y_data = None

            # 1. Try to handle nested paths with dot notation (elevation.classes, etc.)
            if "." in params.x_axis or "." in params.y_axis:
                x_data = self._get_nested_data(data, params.x_axis)
                y_data = self._get_nested_data(data, params.y_axis)

                if x_data is not None and y_data is not None:
                    # Create a DataFrame from the extracted nested data
                    processed_data = pd.DataFrame(
                        {params.x_axis: x_data, params.y_axis: y_data}
                    )

            # 2. Handle special case for 'elevation_distribution' pattern
            elif (
                "elevation" in data
                and isinstance(data["elevation"], dict)
                and "classes" in data["elevation"]
                and "subset" in data["elevation"]
            ):
                if (
                    params.x_axis == "elevation.subset"
                    or params.x_axis == "forest_um_values"
                ):
                    processed_data = pd.DataFrame(
                        {
                            "class_name": data["elevation"]["classes"],
                            "values": data["elevation"]["subset"],
                        }
                    )
                    # Rename columns to match expected param names
                    processed_data.rename(
                        columns={
                            "class_name": params.y_axis
                            if params.orientation == "h"
                            else params.x_axis,
                            "values": params.x_axis
                            if params.orientation == "h"
                            else params.y_axis,
                        },
                        inplace=True,
                    )

            # 3. Handle special case for 'forest_cover_by_elevation' pattern
            elif (
                "class_name" in data
                and "series" in data
                and isinstance(data["series"], dict)
            ):
                if (
                    params.x_axis.startswith("series.")
                    or params.x_axis == "forest_um_values"
                    or params.x_axis == "values"
                ):
                    # Extract the actual series key if using dot notation
                    series_key = (
                        params.x_axis.split(".")[-1]
                        if "." in params.x_axis
                        else "forest_um"
                    )

                    # If x_axis is "values", default to forest_um key
                    if params.x_axis == "values":
                        series_key = "forest_um"

                    if series_key in data["series"]:
                        processed_data = pd.DataFrame(
                            {
                                "class_name": data["class_name"],
                                "values": data["series"][series_key],
                            }
                        )
                        # Rename columns to match expected param names
                        processed_data.rename(
                            columns={
                                "class_name": params.y_axis
                                if params.orientation == "h"
                                else params.x_axis,
                                "values": params.x_axis
                                if params.orientation == "h"
                                else params.y_axis,
                            },
                            inplace=True,
                        )

            # 4. Handle special case for 'holdridge' pattern with nested forest/non_forest structure
            elif (
                "forest" in data
                and "non_forest" in data
                and isinstance(data["forest"], dict)
                and isinstance(data["non_forest"], dict)
            ):
                # Convert the nested structure to a format suitable for a bar plot
                categories = []
                values = []
                types = []

                # Extract from forest dict
                for category, value in data["forest"].items():
                    categories.append(category)
                    values.append(value)
                    types.append("Forêt (%)")

                # Extract from non_forest dict
                for category, value in data["non_forest"].items():
                    categories.append(category)
                    values.append(value)
                    types.append("Hors-Forêt (%)")

                processed_data = pd.DataFrame(
                    {"category": categories, "value": values, "type": types}
                )

                # Map to the expected columns
                column_mapping = {"category": params.x_axis, "value": params.y_axis}
                if params.color_field:
                    column_mapping["type"] = params.color_field
                processed_data.rename(columns=column_mapping, inplace=True)

            # 5. Default case - handle simple dict with direct keys
            elif params.x_axis in data and params.y_axis in data:
                x_values = data[params.x_axis]
                y_values = data[params.y_axis]

                # Create a basic DataFrame
                processed_data = pd.DataFrame(
                    {params.x_axis: x_values, params.y_axis: y_values}
                )

                # Add color field if specified and available
                if params.color_field and params.color_field in data:
                    processed_data[params.color_field] = data[params.color_field]

            # 6. Handle categories/values pattern (seen in debug output)
            elif "categories" in data and "values" in data:
                processed_data = pd.DataFrame(
                    {"categories": data["categories"], "values": data["values"]}
                )
                # Rename to match expected columns
                processed_data.rename(
                    columns={"categories": params.x_axis, "values": params.y_axis},
                    inplace=True,
                )

        # If we couldn't process the data with any of the methods above
        if processed_data is None:
            if isinstance(data, dict):
                logger.error(
                    f"Dict input missing required keys '{params.x_axis}' or '{params.y_axis}'."
                )
                print(data)  # Print the actual data structure
                return f"<p class='error'>Input dict structure not recognized or keys ('{params.x_axis}', '{params.y_axis}') missing/invalid type. Cannot create DataFrame.</p>"
            else:
                return "<p class='error'>Unsupported data type. Expected dict or DataFrame.</p>"

        # --- Data Validation (operates on processed_data) --- #
        if (
            processed_data is None
            or not isinstance(processed_data, pd.DataFrame)
            or processed_data.empty
        ):
            logger.warning(
                "No valid DataFrame available for BarPlotWidget after processing input."
            )
            print(f"Input data: {data}")
            return "<p class='info'>No data available for the bar plot.</p>"

        # --- Validate required columns (operates on processed_data) --- #
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
                f"Data structure causing validation failure:\n{processed_data}"
            )  # Log the structure
            logger.error(
                f"Missing required columns in processed data for BarPlotWidget: {missing_cols}. Required: {required_cols}. Available: {set(processed_data.columns)}"
            )
            print(f"Input data: {data}")
            return f"<p class='error'>Configuration Error: Processed data missing required columns {missing_cols}. Check data source and widget params.</p>"

        # --- Plotting logic (operates on processed_data) --- #
        df_plot = processed_data.copy()

        # Apply sorting if specified
        if params.sort_order:
            ascending = params.sort_order == "ascending"
            try:
                # Sort by y_axis value
                df_plot = df_plot.sort_values(by=params.y_axis, ascending=ascending)
                # If horizontal, sorting by value means sorting the categories on the y-axis
                # If vertical, we need to ensure the x-axis categories respect this order
                if params.orientation == "v":
                    df_plot[params.x_axis] = pd.Categorical(
                        df_plot[params.x_axis],
                        categories=df_plot[params.x_axis].unique(),
                        ordered=True,
                    )
            except KeyError:
                logger.warning(
                    f"Cannot sort by column '{params.y_axis}' as it might be missing after potential aggregation or wrong name."
                )
            except Exception as e:
                logger.error(f"Error applying sorting: {e}")

        try:
            fig = px.bar(
                df_plot,
                x=params.x_axis,
                y=params.y_axis,
                color=params.color_field,
                barmode=params.barmode,
                orientation=params.orientation,
                text_auto=params.text_auto,
                hover_name=params.hover_name,
                hover_data=params.hover_data,
                color_discrete_map=params.color_discrete_map,
                color_continuous_scale=params.color_continuous_scale,
                range_y=params.range_y,
                labels=params.labels,
                title=None,  # Title handled by container
            )

            # Additional layout updates if needed (e.g., axis titles if not covered by labels)
            fig.update_layout(
                margin={"r": 10, "t": 30, "l": 10, "b": 10},  # Adjust margins
                xaxis_title=params.labels.get(params.x_axis)
                if params.labels
                else params.x_axis,
                yaxis_title=params.labels.get(params.y_axis)
                if params.labels
                else params.y_axis,
                legend_title_text=params.labels.get(params.color_field)
                if params.labels and params.color_field
                else params.color_field,
            )

            # Render figure to HTML
            html_content = fig.to_html(full_html=False, include_plotlyjs="cdn")
            return html_content

        except Exception as e:
            logger.exception(f"Error rendering BarPlotWidget: {e}")
            return f"<p class='error'>Error generating bar plot: {e}</p>"
