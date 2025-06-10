import logging
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.core.plugins.widgets.plotly_utils import (
    apply_plotly_defaults,
    get_plotly_dependencies,
    render_plotly_figure,
)

logger = logging.getLogger(__name__)


# Pydantic model for Donut Chart parameters validation
class SubplotConfig(BaseModel):
    name: str  # Title for the subplot
    data_key: str  # Key in the main data dictionary to find this subplot's data
    labels: Optional[List[str]] = (
        None  # Specific labels for this subplot (overrides common_labels)
    )
    colors: Optional[List[str]] = None  # Specific colors for this subplot


class DonutChartParams(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    labels_field: Optional[str] = None  # Now optional
    values_field: Optional[str] = None  # Now optional
    label_mapping: Optional[Dict[str, str]] = None  # Still useful for flat dict case
    color_discrete_sequence: Optional[List[str]] = (
        None  # Default colors if not in subplot
    )
    hole_size: float = Field(0.3, ge=0, lt=1)  # Renamed
    text_info: Optional[str] = (
        "percent+label"  # e.g., 'percent', 'label', 'value', 'percent+label'
    )
    legend_orientation: Optional[str] = Field(
        None, pattern=r"^(h|v)$"
    )  # Horizontal or Vertical

    # New fields for multi-donut subplot feature
    subplots: Optional[List[SubplotConfig]] = None
    common_labels: Optional[List[str]] = (
        None  # Labels shared across subplots if not specified per subplot
    )

    # Hovertemplate fields (keep as is)
    hover_name: Optional[str] = None
    hover_data: Optional[List[str]] = None
    hovertemplate: Optional[str] = None


@register("donut_chart", PluginType.WIDGET)
class DonutChartWidget(WidgetPlugin):
    """Widget to display a donut chart using Plotly."""

    param_schema = DonutChartParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Plotly is handled centrally."""
        return get_plotly_dependencies()

    # get_container_html is inherited from WidgetPlugin

    def render(self, data: Optional[Any], params: DonutChartParams) -> str:
        """Generate the HTML for the donut chart or subplots."""

        df_plot = None
        fig = None  # Initialize fig

        # --- Data Processing --- #

        # === NEW: Subplot Logic ===
        if params.subplots and isinstance(data, dict):
            logger.debug(
                f"Processing dict input for multi-donut subplots using {len(params.subplots)} configurations."
            )
            num_subplots = len(params.subplots)
            if num_subplots == 0:
                return "<p class='info'>No subplots configured.</p>"

            # Create subplots (e.g., 1 row, N cols) - adjust layout as needed
            specs = [
                [{"type": "domain"}] * num_subplots
            ]  # 'domain' type is for Pie charts
            subplot_titles = [sp.name for sp in params.subplots]
            try:
                fig = go.Figure(data=[go.Pie()], layout=go.Layout(title=params.title))
                fig = make_subplots(
                    rows=1,
                    cols=num_subplots,
                    specs=specs,
                    subplot_titles=subplot_titles,
                )
            except Exception as e:
                logger.error(f"Error creating subplots: {e}", exc_info=True)
                return f"<p class='error'>Error setting up subplots: {e}</p>"

            default_colors = params.color_discrete_sequence or [
                "blue",
                "green",
                "red",
                "yellow",
                "orange",
                "purple",
                "pink",
                "brown",
                "gray",
                "black",
            ]
            traces_added = 0

            for i, subplot_conf in enumerate(params.subplots):
                subplot_data = data.get(subplot_conf.data_key)
                if not isinstance(subplot_data, dict) or not subplot_data:
                    logger.warning(
                        f"Could not find valid data for subplot '{subplot_conf.name}' using key '{subplot_conf.data_key}'. Skipping."
                    )
                    continue

                # Determine labels and values
                try:
                    values = [float(v) for v in subplot_data.values()]  # Ensure numeric
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Non-numeric values found in subplot '{subplot_conf.name}' data: {e}. Skipping."
                    )
                    continue

                # Prioritize subplot labels, then common labels, then data keys
                labels = (
                    subplot_conf.labels
                    or params.common_labels
                    or list(subplot_data.keys())
                )

                # Ensure labels and values match length (simple check)
                if len(labels) != len(values):
                    logger.warning(
                        f"Label/Value length mismatch for subplot '{subplot_conf.name}'. Labels ({len(labels)}): {labels}, Values ({len(values)}): {values}. Skipping."
                    )
                    continue

                # Determine colors
                colors = subplot_conf.colors or default_colors

                # Add Pie trace to the subplot
                try:
                    fig.add_trace(
                        go.Pie(
                            labels=labels,
                            values=values,
                            name=subplot_conf.name,  # Name for hover/legend if needed
                            hole=params.hole_size,
                            marker_colors=colors,
                            textinfo=params.text_info,
                            hoverinfo="label+percent+name",  # Example hover info
                            hovertemplate=params.hovertemplate,  # Use if provided
                            # insidetextorientation='radial' # Example styling
                        ),
                        row=1,
                        col=i + 1,
                    )
                    traces_added += 1
                except Exception as e:
                    logger.error(
                        f"Error adding trace for subplot '{subplot_conf.name}': {e}",
                        exc_info=True,
                    )
                    # Continue trying to add other subplots

            if traces_added == 0:  # Check if any traces were actually added
                return "<p class='info'>No valid data found for any configured subplot.</p>"

            # Update overall layout
            layout_updates = {
                "title_text": params.title,
                "showlegend": False,  # Usually hide legend for multiple side-by-side donuts
                "margin": dict(l=20, r=20, t=50, b=20),  # Adjust margins as needed
            }
            apply_plotly_defaults(fig, layout_updates)

        # === EXISTING Logic (if not subplots) ===
        elif not fig:  # Only run if subplot logic didn't create a figure
            effective_labels_field = None
            effective_values_field = None

            # 1. DataFrame Input
            if isinstance(data, pd.DataFrame):
                logger.debug("Processing DataFrame input for DonutChartWidget.")
                if not params.values_field or not params.labels_field:
                    logger.error(
                        "Config Error: 'values_field' and 'labels_field' required for DataFrame."
                    )
                    return "<p class='error'>Config Error: Missing fields for DataFrame.</p>"

                required_cols = {params.values_field, params.labels_field}
                # Add hover fields if they are specified
                if params.hover_name:
                    required_cols.add(params.hover_name)
                if params.hover_data:
                    required_cols.update(params.hover_data)

                missing_cols = required_cols - set(data.columns)
                if missing_cols:
                    logger.error(f"DataFrame missing required columns: {missing_cols}")
                    return f"<p class='error'>DataFrame missing columns: {missing_cols}</p>"

                try:
                    # ... (aggregation, type conversion)
                    df_agg = data.copy()  # Placeholder for actual aggregation
                    df_agg[params.values_field] = pd.to_numeric(
                        df_agg[params.values_field], errors="coerce"
                    )
                    df_agg = df_agg.dropna(subset=[params.values_field])

                    if df_agg.empty:
                        logger.warning("DataFrame empty after processing.")
                    else:
                        df_plot = df_agg
                        effective_labels_field = params.labels_field
                        effective_values_field = params.values_field
                except Exception as e:
                    logger.error(f"Error processing DataFrame: {e}", exc_info=True)
                    return f"<p class='error'>Error preparing DataFrame data: {e}</p>"

            # 2. Dictionary Input (Non-subplot cases)
            elif isinstance(data, dict):
                # 2a. Dict with lists, using labels_field/values_field
                if params.labels_field and params.values_field:
                    logger.debug("Processing dict using labels/values fields.")
                    if (
                        params.labels_field in data
                        and params.values_field in data
                        and isinstance(data[params.labels_field], list)
                        and isinstance(data[params.values_field], list)
                    ):
                        if len(data[params.labels_field]) == len(
                            data[params.values_field]
                        ):
                            try:
                                df_temp = pd.DataFrame(
                                    {
                                        params.labels_field: data[params.labels_field],
                                        params.values_field: data[params.values_field],
                                    }
                                )
                                df_temp[params.values_field] = pd.to_numeric(
                                    df_temp[params.values_field], errors="coerce"
                                )
                                df_temp = df_temp.dropna(subset=[params.values_field])
                                if not df_temp.empty:
                                    df_plot = df_temp
                                    effective_labels_field = params.labels_field
                                    effective_values_field = params.values_field
                                    logger.debug(
                                        f"Created DF from dict lists: {list(df_plot.columns)}"
                                    )
                                else:
                                    logger.warning(
                                        "Dict lists resulted in empty data after cleaning."
                                    )
                            except Exception as e:
                                logger.error(f"Error creating DF from dict lists: {e}")
                        else:
                            logger.error("List lengths mismatch in dict for fields.")
                    else:
                        logger.error(
                            f"Missing keys '{params.labels_field}' or '{params.values_field}' or not lists in dict."
                        )

                # 2b. Dict with _percent keys and label_mapping (fallback)
                elif not df_plot:  # Only try if 2a failed/inapplicable
                    logger.debug("Processing dict using _percent keys and mapping.")
                    plot_labels = []
                    plot_values = []
                    label_map = params.label_mapping or {}
                    percent_keys = sorted(
                        [
                            k
                            for k in data
                            if isinstance(k, str) and k.endswith("_percent")
                        ]
                    )

                    if not percent_keys:
                        logger.warning("No _percent keys and no labels/values fields.")
                    else:
                        for pk in percent_keys:
                            base_key = pk.replace("_percent", "")
                            value = data.get(pk)
                            label = label_map.get(base_key, base_key)
                            if isinstance(value, (int, float)):
                                plot_labels.append(label)
                                plot_values.append(value)
                            else:
                                logger.warning(f"Non-numeric value for key '{pk}'.")

                        if plot_labels and plot_values:
                            df_plot = pd.DataFrame(
                                {
                                    "labels": plot_labels,  # Use default names
                                    "values": plot_values,
                                }
                            )
                            effective_labels_field = "labels"
                            effective_values_field = "values"
                            logger.debug(
                                f"Created DF from dict _percent keys: {list(df_plot.columns)}"
                            )
                        else:
                            logger.warning(
                                "Could not extract valid labels/values from _percent keys."
                            )

            # 3. Invalid Input Type or None
            else:
                if data is None:
                    logger.warning("No data provided.")
                else:
                    logger.error(
                        f"Unsupported data type for DonutChartWidget: {type(data)}"
                    )
                    return f"<p class='error'>Unsupported data type: {type(data)}</p>"

            # --- Final Plot Generation (if not subplot) --- #
            if df_plot is not None and not df_plot.empty:
                # Check if all values are zero or null (no meaningful data)
                if effective_values_field and effective_values_field in df_plot.columns:
                    y_values = df_plot[effective_values_field]
                    if pd.isna(y_values).all() or (y_values == 0).all():
                        return "<p class='info'>No data available.</p>"
                try:
                    fig_single = go.Figure(
                        data=[
                            go.Pie(
                                labels=df_plot[effective_labels_field],
                                values=df_plot[effective_values_field],
                                hole=params.hole_size,
                                textinfo=params.text_info,
                                hoverinfo="label+percent+value",
                                marker_colors=params.color_discrete_sequence,
                                sort=True,
                            )
                        ]
                    )

                    # Layout updates
                    layout_updates = {
                        "title": params.title,
                        "showlegend": True,
                        "legend_orientation": params.legend_orientation,
                        "uniformtext_minsize": 12,
                        "uniformtext_mode": "hide",
                        "margin": dict(l=20, r=20, t=30, b=20),  # Adjust margins
                    }
                    apply_plotly_defaults(fig_single, layout_updates)

                    fig = fig_single  # Assign the single figure
                except Exception as e:
                    logger.error(
                        f"Error creating single donut chart: {e}", exc_info=True
                    )
                    return f"<p class='error'>Error generating chart: {e}</p>"
            elif (
                not isinstance(data, dict) or not params.subplots
            ):  # Avoid error if subplot logic was intended
                logger.warning("No plottable data found after processing.")
                return "<p class='info'>No data available for the donut chart.</p>"

        # --- HTML Output --- #
        if fig:
            try:
                # Render using utility function
                html_output = render_plotly_figure(fig)
                # Wrap in a div with class for potential CSS styling
                return f"<div class='plotly-chart-widget donut-chart-widget'>{html_output}</div>"
            except Exception as e:
                logger.error(
                    f"Error converting Plotly figure to HTML: {e}", exc_info=True
                )
                return f"<p class='error'>Error displaying chart: {e}</p>"
        else:
            # This case should be covered by earlier returns, but as a fallback:
            logger.error(
                "Figure object was not created, and no error message returned."
            )
            return "<p class='error'>Failed to generate chart figure due to an unexpected issue.</p>"
