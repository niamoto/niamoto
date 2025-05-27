import logging
from typing import Any, List, Optional, Set, Union, Dict

from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.common.utils.dict_utils import get_nested_value

logger = logging.getLogger(__name__)

# --- Pydantic Models for Validation ---


class InfoItem(BaseModel):
    """Model for a single item within the info grid."""

    label: str = Field(..., description="The label or title for the info item.")
    value: Optional[Union[str, int, float]] = Field(
        None, description="The value to display (if source is not used)."
    )
    source: Optional[str] = Field(
        None, description="Dot-notation key to fetch the value from the data source."
    )
    unit: Optional[str] = Field(
        None, description="Optional unit for the value (e.g., '%', 'USD')."
    )
    description: Optional[str] = Field(
        None, description="Optional description or tooltip for the item."
    )
    icon: Optional[str] = Field(
        None, description="Optional icon class (e.g., Font Awesome 'fas fa-users')."
    )
    format: Optional[str] = Field(
        None, description="Optional format for the value (e.g., 'map', 'number')."
    )
    mapping: Optional[Dict[str, str]] = Field(
        None, description="Optional mapping for the 'map' format."
    )


class InfoGridParams(BaseModel):
    """Parameters for configuring the InfoGridWidget."""

    title: Optional[str] = Field(
        None, description="Optional title for the widget container."
    )
    description: Optional[str] = Field(
        None, description="Optional description for the widget container."
    )
    items: List[InfoItem] = Field(
        ..., description="A list of info items to display in the grid."
    )
    grid_columns: Optional[int] = Field(
        None, description="Number of columns (e.g., 2, 3, 4). Auto-adjusts if None."
    )
    # Add styling options if needed, e.g., card_style: str = 'basic'


# --- Widget Implementation ---


@register("info_grid", PluginType.WIDGET)
class InfoGridWidget(WidgetPlugin):
    """Displays a grid of key information items (KPIs, stats, labels)."""

    param_schema = InfoGridParams

    def get_dependencies(self) -> Set[str]:
        """Return the set of CSS/JS dependencies. Currently relies on framework (e.g., Bootstrap)."""
        # If specific icons (like Font Awesome) are used via params.icon,
        # the framework should handle loading the icon library.
        return set()

    # get_container_html is inherited from WidgetPlugin

    def render(self, data: Optional[Any], params: InfoGridParams) -> str:
        """Generate the HTML for the info grid using Tailwind CSS."""
        # Data IS used now if item.source is specified
        if not params.items:
            logger.warning("No items provided to InfoGridWidget.")
            return "<p class='text-gray-500 italic p-4'>No information items configured for this grid.</p>"

        # Check if data is needed but not provided
        if data is None and any(item.source for item in params.items):
            logger.warning(
                "InfoGridWidget has items requiring a data source, but no data was provided."
            )
            # Optionally return an error, or just render items without sourced values

        # Determine grid columns for Tailwind
        grid_cols_class = "grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
        if params.grid_columns:
            if 1 <= params.grid_columns <= 6:
                # Map number of columns to Tailwind grid classes
                grid_cols_mapping = {
                    1: "grid-cols-1",
                    2: "grid-cols-1 md:grid-cols-2",
                    3: "grid-cols-1 md:grid-cols-3",
                    4: "grid-cols-1 md:grid-cols-2 lg:grid-cols-4",
                    5: "grid-cols-1 md:grid-cols-3 lg:grid-cols-5",
                    6: "grid-cols-1 md:grid-cols-3 lg:grid-cols-6",
                }
                grid_cols_class = grid_cols_mapping.get(
                    params.grid_columns, grid_cols_class
                )
            else:
                logger.warning(
                    f"Invalid grid_columns value: {params.grid_columns}. Using default responsive grid."
                )

        # Container for the whole widget with title if provided
        title_html = ""
        if params.title:
            title_html = f'<div class="mb-4"><h3 class="text-lg font-medium text-gray-900">{params.title}</h3></div>'

        description_html = ""
        if params.description:
            description_html = f'<div class="mb-4"><p class="text-sm text-gray-500">{params.description}</p></div>'

        item_html_parts = []
        for item in params.items:
            # --- Value Fetching --- #
            item_value = item.value  # Default to static value
            if item.source:
                if isinstance(data, dict):
                    # Fetch value from data using the source key (dot notation supported)
                    fetched_value = get_nested_value(data, item.source)
                    if fetched_value is not None:
                        item_value = fetched_value
                    else:
                        logger.debug(
                            f"Source '{item.source}' not found in data for InfoGrid item '{item.label}'. Using default value if set."
                        )
                        # Keep item_value as item.value or None if not set
                else:
                    logger.warning(
                        f"Cannot fetch source '{item.source}' for InfoGrid item '{item.label}' because data is not a dictionary or is None."
                    )

            # --- Value Formatting --- #
            # Skip item if no value could be determined (either static or fetched)
            if item_value is None:
                continue

            # Check if value is a dictionary with a 'value' key
            if isinstance(item_value, dict) and "value" in item_value:
                item_value = item_value["value"]

            # Default display value is the string representation
            display_value = str(item_value)

            # Apply formatting if specified
            if item.format == "map" and item.mapping:
                display_value = item.mapping.get(
                    str(item_value), display_value
                )  # Use str(item_value) for lookup
            elif item.format == "number":
                # Check if value is nested in a dict like {'value': 123}
                value_to_format = item_value
                if isinstance(item_value, dict) and "value" in item_value:
                    value_to_format = item_value["value"]

                try:
                    # Attempt conversion and formatting
                    numeric_value = float(
                        value_to_format
                    )  # Use float to handle decimal values
                    # Format integers without decimal places, otherwise use 2 decimal places
                    if numeric_value.is_integer():
                        display_value = f"{int(numeric_value):,}".replace(
                            ",", " "
                        )  # French style thousands separator
                    else:
                        display_value = f"{numeric_value:,.2f}".replace(
                            ",", " "
                        ).replace(".", ",")  # French style formatting
                except (ValueError, TypeError):
                    """ logger.warning(
                        f"Could not format value '{value_to_format}' as number for item '{item.label}'."
                    ) """

            # --- HTML Generation with Tailwind CSS --- #
            # Handle icons - support for Font Awesome and other icon libraries
            icon_html = ""
            if item.icon:
                if item.icon.startswith("fa"):
                    # Font Awesome icon
                    icon_html = f'<i class="{item.icon} mr-2"></i>'
                else:
                    # Assume it's a simple icon name and use Font Awesome solid as default
                    icon_html = f'<i class="fas fa-{item.icon} mr-2"></i>'

            unit_html = (
                f'<span class="text-gray-500 text-sm ml-1">{item.unit}</span>'
                if item.unit
                else ""
            )
            tooltip_attr = f'title="{item.description}"' if item.description else ""

            # Generate HTML for each item with Tailwind styling
            item_html = f"""
            <div class="info-grid-item p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200" {tooltip_attr}>
                <div class="flex flex-col h-full">
                    <div class="text-sm font-medium text-gray-500 mb-1">{icon_html}{item.label}</div>
                    <div class="text-2xl font-semibold text-gray-900">{display_value}{unit_html}</div>
                </div>
            </div>
            """
            item_html_parts.append(item_html)

        # If no items were rendered, show a message
        if not item_html_parts:
            return (
                "<p class='text-gray-500 italic p-4'>No data available for display.</p>"
            )

        # Wrap items in a responsive grid layout
        items_html = "\n".join(item_html_parts)
        output_html = f"""
        <div class="info-grid-widget">
            {title_html}
            {description_html}
            <div class="grid {grid_cols_class} gap-4">
                {items_html}
            </div>
        </div>
        """

        return output_html
