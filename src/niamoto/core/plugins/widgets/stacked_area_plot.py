import logging
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import plotly.express as px
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

logger = logging.getLogger(__name__)


# Pydantic model for Stacked Area Plot parameters validation
class StackedAreaPlotParams(BaseModel):
    title: Optional[str] = Field(None, description="Optional title for the plot.")
    x_axis: str = Field(..., description="Field name for the X-axis (often time).")
    y_axis: str = Field(..., description="Field name for the Y-axis (values).")
    color_field: str = Field(..., description="Field name used to segment areas.")
    line_group: Optional[str] = Field(
        None, description="Field name to group lines within areas (optional)."
    )
    hover_name: Optional[str] = Field(
        None, description="Field to display as the main label on hover."
    )
    hover_data: Optional[List[str]] = Field(
        None, description="List of additional fields to display on hover."
    )
    labels: Optional[dict] = Field(
        None, description="Dictionary to override axis/legend labels."
    )
    color_discrete_map: Optional[dict] = Field(
        None, description="Explicit color mapping for discrete colors."
    )


@register("stacked_area_plot", PluginType.WIDGET)
class StackedAreaPlotWidget(WidgetPlugin):
    """Widget to display a stacked area plot using Plotly Express."""

    param_schema = StackedAreaPlotParams

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

    def render(self, data: Optional[Any], params: StackedAreaPlotParams) -> str:
        """Generate the HTML for the stacked area plot."""
        # Debug info
        print("\n" + "=" * 80)
        print(
            f"DEBUG STACKED_AREA_PLOT - data_source: {getattr(params, 'data_source', 'unknown')}"
        )
        print(
            f"DEBUG STACKED_AREA_PLOT - x_axis: {params.x_axis}, y_axis: {params.y_axis}, color_field: {params.color_field}"
        )
        print(f"DEBUG STACKED_AREA_PLOT - data type: {type(data)}")

        if isinstance(data, dict):
            print(f"DEBUG STACKED_AREA_PLOT - Dict top level keys: {list(data.keys())}")

            # Handle nested data and convert dictionary to DataFrame
            processed_data = None

            # Structure attendue: {'altitudes': [...], 'type1': [...], 'type2': [...], ...}
            # Où les types sont des catégories de forêts et les valeurs sont des séries temporelles pour chaque altitude

            altitude_key = "altitudes"
            if altitude_key in data:
                print(
                    "DEBUG STACKED_AREA_PLOT - Detected altitude-forest_type structure"
                )
                altitudes = data[altitude_key]

                # Identifie toutes les clés représentant les types de forêts (toutes les clés sauf 'altitudes')
                forest_type_keys = [key for key in data.keys() if key != altitude_key]
                print(
                    "DEBUG STACKED_AREA_PLOT - Forest type keys: {}".format(
                        forest_type_keys
                    )
                )

                if forest_type_keys and len(altitudes) > 0:
                    # Créer un DataFrame au format long pour le graphique empilé
                    rows = []

                    for altitude_idx, altitude in enumerate(altitudes):
                        for forest_type in forest_type_keys:
                            if forest_type in data and altitude_idx < len(
                                data[forest_type]
                            ):
                                # Extraire la valeur pour ce type de forêt à cette altitude
                                value = data[forest_type][altitude_idx]

                                rows.append(
                                    {
                                        "altitude": altitude,
                                        "forest_type": forest_type,
                                        "value": value,
                                    }
                                )

                    if rows:
                        processed_data = pd.DataFrame(rows)
                        # Renommer les colonnes pour correspondre aux paramètres attendus
                        column_mapping = {
                            "altitude": params.x_axis,
                            "forest_type": params.color_field,
                            "value": params.y_axis,
                        }
                        processed_data.rename(columns=column_mapping, inplace=True)
                        print(
                            "DEBUG STACKED_AREA_PLOT - Successfully created DataFrame with shape:",
                            processed_data.shape,
                        )
            # If we've successfully processed the data, use it instead of the original
            if processed_data is not None:
                data = processed_data
                print(
                    "DEBUG STACKED_AREA_PLOT - Processed data to DataFrame with shape: {}".format(
                        data.shape
                    )
                )
            else:
                print(
                    "DEBUG STACKED_AREA_PLOT - Could not process dictionary data to DataFrame"
                )

        # Check if data is a non-empty DataFrame
        if not isinstance(data, pd.DataFrame) or data.empty:
            logger.warning(
                "No data or invalid data type provided to StackedAreaPlotWidget "
                "(expected non-empty DataFrame)."
            )
            # Print data for debugging
            if data is not None:
                print(f"DEBUG STACKED_AREA_PLOT - Input data: {data}")
            return "<p class='info'>No valid data available for stacked area plot.</p>"

        # Validate required columns
        required_cols = {params.x_axis, params.y_axis, params.color_field}
        if params.line_group:
            required_cols.add(params.line_group)
        if params.hover_name:
            required_cols.add(params.hover_name)
        if params.hover_data:
            hover_data_list = (
                params.hover_data
                if isinstance(params.hover_data, list)
                else [params.hover_data]
            )
            required_cols.update(hover_data_list)

        missing_cols = required_cols - set(data.columns)
        if missing_cols:
            logger.error(
                f"Missing required columns for StackedAreaPlotWidget: {missing_cols}"
            )
            print(
                f"DEBUG STACKED_AREA_PLOT - Available columns: {data.columns.tolist()}"
            )
            return f"<p class='error'>Configuration Error: Missing columns {missing_cols}.</p>"

        # Attempt to convert Y-axis to numeric if it's not already
        if not pd.api.types.is_numeric_dtype(data[params.y_axis]):
            try:
                data[params.y_axis] = pd.to_numeric(
                    data[params.y_axis], errors="coerce"
                )
                if data[params.y_axis].isnull().any():
                    logger.warning(
                        f"Column '{params.y_axis}' used for Y-axis contains non-numeric values or NaNs after conversion. Plot might be affected."
                    )
                    # Optionally drop rows with NaN y-values, or return error
                    # data.dropna(subset=[params.y_axis], inplace=True)
                    # For now, let Plotly handle potential issues
            except Exception as e:
                logger.error(
                    f"Failed to convert Y-axis column '{params.y_axis}' to numeric: {e}"
                )
                return f"<p class='error'>Data Error: Could not process numeric Y-axis column '{params.y_axis}'.</p>"

        # Attempt to convert X-axis to datetime if it looks like one, Plotly often handles this
        # but explicit conversion can be safer
        try:
            # Basic check if it's not already datetime or numeric (which Plotly can handle)
            if not pd.api.types.is_datetime64_any_dtype(
                data[params.x_axis]
            ) and not pd.api.types.is_numeric_dtype(data[params.x_axis]):
                data[params.x_axis] = pd.to_datetime(
                    data[params.x_axis], errors="coerce"
                )
                if data[params.x_axis].isnull().any():
                    logger.warning(
                        f"Column '{params.x_axis}' used for X-axis contains values that could not be converted to datetime. Plot might be affected."
                    )
                    # data.dropna(subset=[params.x_axis], inplace=True)
        except Exception as e:
            logger.warning(
                f"Could not convert X-axis column '{params.x_axis}' to datetime: {e}. Plotly will attempt to interpret it."
            )

        try:
            # Prepare arguments for px.area, filtering out None values
            plot_args = {
                "data_frame": data,
                "x": params.x_axis,
                "y": params.y_axis,
                "color": params.color_field,
                "line_group": params.line_group,
                "hover_name": params.hover_name,
                "hover_data": params.hover_data,
                "labels": params.labels or {},
                "title": params.title or "",  # Use Widget title
                "color_discrete_map": params.color_discrete_map,
            }
            plot_args = {k: v for k, v in plot_args.items() if v is not None}

            fig = px.area(**plot_args)

            # Layout updates
            fig.update_layout(
                margin={"r": 10, "t": 30 if params.title else 10, "l": 10, "b": 10},
                yaxis_title=params.labels.get(params.y_axis, params.y_axis)
                if params.labels
                else params.y_axis,
                xaxis_title=params.labels.get(params.x_axis, params.x_axis)
                if params.labels
                else params.x_axis,
                legend_title_text=params.labels.get(
                    params.color_field, params.color_field
                )
                if params.labels
                else params.color_field,
            )

            # Render figure to HTML
            html_content = fig.to_html(full_html=False, include_plotlyjs="cdn")
            return html_content

        except Exception as e:
            logger.exception(f"Error rendering StackedAreaPlotWidget: {e}")
            return f"<p class='error'>Error generating stacked area plot: {e}</p>"
