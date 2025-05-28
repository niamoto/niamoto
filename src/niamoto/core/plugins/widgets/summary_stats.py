import logging
from typing import List, Optional, Set

import pandas as pd
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

logger = logging.getLogger(__name__)


# Pydantic model for Summary Stats Widget parameters validation
class SummaryStatsParams(BaseModel):
    title: Optional[str] = Field(None, description="Optional title for the widget.")
    description: Optional[str] = Field(
        None, description="Optional description for the widget."
    )
    numeric_columns: Optional[List[str]] = Field(
        None,
        description="List of numeric columns to compute stats for. If None, attempts all numeric columns.",
    )
    percentiles: List[float] = Field(
        [0.25, 0.5, 0.75], description="List of percentiles to compute."
    )
    include_stats: Optional[List[str]] = Field(
        None,
        description="Specific stats to include (e.g., ['mean', 'std']). Defaults to pandas describe() output.",
    )
    # Note: pandas describe() includes count, mean, std, min, 25%, 50%, 75%, max by default


@register("summary_stats", PluginType.WIDGET)
class SummaryStatsWidget(WidgetPlugin):
    """Widget to display summary statistics of numeric columns in a DataFrame."""

    param_schema = SummaryStatsParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Minimal for HTML table."""
        return set()

    # get_container_html is inherited from WidgetPlugin

    def render(self, data: Optional[pd.DataFrame], params: SummaryStatsParams) -> str:
        """Generate the HTML table for the summary statistics."""
        if data is None or data.empty:
            logger.info("No data provided to SummaryStatsWidget.")
            return "<p class='info'>No data available for summary statistics.</p>"

        if not isinstance(data, pd.DataFrame):
            logger.warning(
                f"Invalid data type for SummaryStatsWidget: {type(data)}. Expected DataFrame."
            )
            # Attempt conversion if possible, e.g., from list of dicts
            try:
                data = pd.DataFrame(data)
            except Exception:
                logger.error("Could not convert input data to DataFrame.")
                return (
                    "<p class='error'>Invalid data format for summary statistics.</p>"
                )

        # Select numeric columns
        if params.numeric_columns:
            cols_to_use = [col for col in params.numeric_columns if col in data.columns]
            if len(cols_to_use) != len(params.numeric_columns):
                missing = set(params.numeric_columns) - set(cols_to_use)
                logger.warning(
                    f"Specified numeric columns not found: {missing}. Using available ones: {cols_to_use}"
                )
            if not cols_to_use:
                logger.error(
                    "None of the specified numeric columns were found in the data."
                )
                return f"<p class='error'>Configuration Error: Columns {params.numeric_columns} not found.</p>"
            df_numeric = data[cols_to_use].select_dtypes(include="number")
        else:
            df_numeric = data.select_dtypes(include="number")

        if df_numeric.empty:
            logger.info("No numeric columns found or selected in the data.")
            return (
                "<p class='info'>No numeric data available for summary statistics.</p>"
            )

        try:
            # Calculate summary statistics using describe()
            summary = df_numeric.describe(
                percentiles=params.percentiles, include="number"
            )  # Ensure only numeric are processed

            # Filter specific stats if requested
            if params.include_stats:
                # Pandas describe index: count, mean, std, min, 25%, 50%, 75%, max
                # Ensure requested stats are valid describe() outputs or percentile labels
                valid_stats = list(summary.index)
                # Convert percentile numbers (like 0.5) to string format ('50%') if needed for matching
                percentile_strs = [f"{p * 100:.0f}%" for p in params.percentiles]
                stats_to_keep_final = []
                for stat in params.include_stats:
                    if stat in valid_stats:
                        stats_to_keep_final.append(stat)
                    elif f"{stat * 100:.0f}%" in percentile_strs:
                        stats_to_keep_final.append(
                            f"{stat * 100:.0f}%"
                        )  # Match the format from describe

                if not stats_to_keep_final:
                    logger.warning(
                        "None of the requested 'include_stats' were valid describe() outputs. Showing default stats."
                    )
                else:
                    summary = summary.loc[stats_to_keep_final]

            # Format for better readability (optional)
            # summary = summary.applymap(lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x)

            # Generate HTML table
            html_table = summary.to_html(
                classes="table table-striped table-hover table-sm", border=0
            )
            # Add title and description if provided (handled by container now)
            # title_html = f"<h5>{params.title}</h5>" if params.title else ""
            # desc_html = f"<p>{params.description}</p>" if params.description else ""
            # return title_html + desc_html + html_table
            return html_table

        except Exception as e:
            logger.exception(f"Error generating summary statistics table: {e}")
            return f"<p class='error'>Error calculating statistics: {e}</p>"
