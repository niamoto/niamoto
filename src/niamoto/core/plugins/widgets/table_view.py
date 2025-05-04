import logging
from typing import List, Optional, Set

import pandas as pd
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

logger = logging.getLogger(__name__)


# Model for column configuration in the table view
class TableColumn(BaseModel):
    source: str  # Key in the data dictionary/DataFrame column name
    label: Optional[str] = None  # Display header (defaults to source)
    format: Optional[str] = (
        None  # Formatting hint ('number', 'currency', 'date', '.2f')
    )
    visible: bool = True  # Whether the column is initially visible
    searchable: bool = True  # If the column should be included in search
    sortable: bool = True  # If the column can be sorted
    width: Optional[str] = None  # CSS width (e.g., '100px', '10%')


# Pydantic model for Table View parameters validation
class TableViewParams(BaseModel):
    title: Optional[str] = Field(None, description="Optional title for the table.")
    description: Optional[str] = Field(
        None, description="Optional description for the table."
    )
    columns: Optional[List[str]] = Field(
        None, description="List of columns to display. If None, displays all."
    )
    sort_by: Optional[List[str]] = Field(
        None, description="List of columns to sort by."
    )
    ascending: Optional[List[bool]] = Field(
        None,
        description="List of sort directions (True/False) corresponding to sort_by columns.",
    )
    max_rows: int = Field(
        100, description="Maximum number of rows to display in the table."
    )
    # Configuration for pagination/scrolling could be added here
    index: bool = Field(False, description="Whether to display the DataFrame index.")
    table_classes: str = Field(
        "table table-striped table-hover table-sm",
        description="CSS classes for the HTML table.",
    )
    escape: bool = Field(
        True, description="Whether to escape HTML entities in the table cells."
    )
    border: Optional[int] = Field(0, description="Border attribute for the HTML table.")


@register("table_view", PluginType.WIDGET)
class TableViewWidget(WidgetPlugin):
    """Widget to display a pandas DataFrame as an HTML table."""

    param_schema = TableViewParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Minimal for HTML table."""
        # Dependencies for potential JS-based table enhancements (like DataTables) could be added
        return set()

    # get_container_html is inherited from WidgetPlugin

    def render(self, data: Optional[pd.DataFrame], params: TableViewParams) -> str:
        """Generate the HTML table from the DataFrame."""
        if data is None or data.empty:
            logger.info("No data provided to TableViewWidget.")
            return "<p class='info'>No data available to display in table.</p>"

        if not isinstance(data, pd.DataFrame):
            logger.warning(
                f"Invalid data type for TableViewWidget: {type(data)}. Expected DataFrame."
            )
            try:
                data = pd.DataFrame(data)
            except Exception as e:
                logger.error(f"Could not convert input data to DataFrame: {e}")
                return "<p class='error'>Invalid data format for table view.</p>"

        df_display = data.copy()

        # Select columns
        if params.columns:
            valid_cols = [col for col in params.columns if col in df_display.columns]
            if len(valid_cols) != len(params.columns):
                missing = set(params.columns) - set(valid_cols)
                logger.warning(
                    f"Specified columns not found: {missing}. Displaying available specified columns: {valid_cols}"
                )
            if not valid_cols:
                logger.error("None of the specified columns exist in the DataFrame.")
                return f"<p class='error'>Configuration Error: None of the specified columns found: {params.columns}</p>"
            df_display = df_display[valid_cols]

        # Sorting
        if params.sort_by:
            valid_sort_cols = [
                col for col in params.sort_by if col in df_display.columns
            ]
            if not valid_sort_cols:
                logger.warning(
                    f"None of the specified sort_by columns found: {params.sort_by}. Skipping sorting."
                )
            else:
                if len(valid_sort_cols) != len(params.sort_by):
                    missing_sort = set(params.sort_by) - set(valid_sort_cols)
                    logger.warning(
                        f"Sort columns not found: {missing_sort}. Sorting by available: {valid_sort_cols}"
                    )

                # Ensure ascending list matches valid sort columns length
                ascending_flags = params.ascending or [True] * len(
                    valid_sort_cols
                )  # Default to True
                if len(ascending_flags) < len(valid_sort_cols):
                    ascending_flags.extend(
                        [True] * (len(valid_sort_cols) - len(ascending_flags))
                    )
                elif len(ascending_flags) > len(valid_sort_cols):
                    ascending_flags = ascending_flags[: len(valid_sort_cols)]

                try:
                    df_display = df_display.sort_values(
                        by=valid_sort_cols, ascending=ascending_flags
                    )
                except Exception as e:
                    logger.error(f"Error during sorting by {valid_sort_cols}: {e}")
                    return f"<p class='error'>Error sorting data: {e}</p>"

        # Limit rows
        df_display = df_display.head(params.max_rows)

        try:
            # Generate HTML table using DataFrame.to_html
            html_table = df_display.to_html(
                classes=params.table_classes,
                index=params.index,
                escape=params.escape,
                border=params.border,
                na_rep="-",  # Represent NaNs nicely
                max_rows=None,  # Already handled by head()
            )
            return html_table
        except Exception as e:
            logger.exception(f"Error generating HTML table for TableViewWidget: {e}")
            return f"<p class='error'>Error displaying table: {e}</p>"
