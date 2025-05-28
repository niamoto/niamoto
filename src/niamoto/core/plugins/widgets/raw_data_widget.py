# src/niamoto/core/plugins/widgets/raw_data_widget.py

"""
A simple widget plugin that displays the raw data it receives.
"""

import logging
from typing import List, Optional, Set

import pandas as pd
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

logger = logging.getLogger(__name__)


# Pydantic model for Raw Data Widget parameters validation
class RawDataWidgetParams(BaseModel):
    title: Optional[str] = Field(None, description="Optional title for the widget.")
    max_rows: int = Field(100, description="Maximum number of rows to display.")
    columns: Optional[List[str]] = Field(
        None, description="List of specific columns to display. Displays all if None."
    )
    sort_by: Optional[str] = Field(None, description="Column name to sort by.")
    ascending: bool = Field(
        True, description="Sort direction (True for ascending, False for descending)."
    )


@register("raw_data_widget", PluginType.WIDGET)
class RawDataWidget(WidgetPlugin):
    """Widget to display raw data in an HTML table."""

    param_schema = RawDataWidgetParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Minimal for raw HTML table."""
        # Potentially add CSS for table styling later
        return set()

    def render(self, data: Optional[pd.DataFrame], params: RawDataWidgetParams) -> str:
        """Generate the HTML table for the raw data."""
        if data is None or data.empty:
            logger.info("No data provided to RawDataWidget.")
            return "<p class='info'>No data available to display.</p>"

        df_display = data.copy()

        # Select columns if specified
        if params.columns:
            missing_cols = set(params.columns) - set(df_display.columns)
            if missing_cols:
                logger.warning(
                    f"Specified columns not found in data: {missing_cols}. Displaying available columns."
                )
                # Filter to only existing columns among the requested ones
                available_cols = [
                    col for col in params.columns if col in df_display.columns
                ]
                if not available_cols:
                    logger.error(
                        "None of the specified columns are available in the data."
                    )
                    return f"<p class='error'>Configuration Error: None of the specified columns {params.columns} found.</p>"
                df_display = df_display[available_cols]
            else:
                df_display = df_display[params.columns]

        # Sort if specified
        if params.sort_by:
            if params.sort_by in df_display.columns:
                df_display = df_display.sort_values(
                    by=params.sort_by, ascending=params.ascending
                )
            else:
                logger.warning(
                    f"Column '{params.sort_by}' specified for sorting not found. Skipping sorting."
                )

        # Limit rows
        df_display = df_display.head(params.max_rows)

        try:
            # Generate HTML table
            # Adding some basic Bootstrap classes for styling, assuming Bootstrap might be available
            html_table = df_display.to_html(
                classes="table table-striped table-hover table-sm",
                index=False,
                border=0,
                escape=True,
            )
            return html_table
        except Exception as e:
            logger.exception(f"Error generating HTML table for RawDataWidget: {e}")
            return f"<p class='error'>Error displaying data: {e}</p>"
