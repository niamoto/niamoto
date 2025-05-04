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
        """Generate the HTML for the info grid."""
        # Data IS used now if item.source is specified
        if not params.items:
            logger.warning("No items provided to InfoGridWidget.")
            return "<p class='info'>No information items configured for this grid.</p>"

        # Check if data is needed but not provided
        if data is None and any(item.source for item in params.items):
            logger.warning(
                "InfoGridWidget has items requiring a data source, but no data was provided."
            )
            # Optionally return an error, or just render items without sourced values

        # Determine column class (assuming Bootstrap-like grid)
        col_class = "col"
        if params.grid_columns:
            if 1 <= params.grid_columns <= 12:
                # Simple mapping, e.g., 2 -> col-md-6, 3 -> col-md-4, 4 -> col-md-3
                span = max(1, 12 // params.grid_columns)
                col_class = f"col-md-{span}"
            else:
                logger.warning(
                    f"Invalid grid_columns value: {params.grid_columns}. Using auto columns."
                )

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
                    numeric_value = int(value_to_format)
                    display_value = f"{numeric_value:,}".replace(
                        ",", " "
                    )  # French style thousands separator
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not format value '{value_to_format}' as number for item '{item.label}'."
                    )

            # --- HTML Generation --- #
            icon_html = f'<i class="{item.icon} mr-2"></i>' if item.icon else ""
            unit_html = f'<span class="unit">{item.unit}</span>' if item.unit else ""
            description_html = (
                f' title="{item.description}"' if item.description else ""
            )

            item_html = f'''
            <div class="{col_class} mb-3 info-grid-item" {description_html}>
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">{icon_html}{item.label}</h5>
                        <p class="card-text display-5">{display_value}{unit_html}</p>
                        </div>
                </div>
            </div>
            '''
            item_html_parts.append(item_html)

        # Wrap items in a row
        output_html = f'<div class="row">{" ".join(item_html_parts)}</div>'

        return output_html
