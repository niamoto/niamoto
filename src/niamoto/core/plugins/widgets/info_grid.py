import html
import logging
from typing import Any, List, Optional, Set, Union, Dict
import json

from pydantic import BaseModel, Field, ConfigDict

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.core.plugins.models import BasePluginParams
from niamoto.common.utils.dict_utils import get_nested_value

logger = logging.getLogger(__name__)

# --- Pydantic Models for Validation ---


class ImageMapping(BaseModel):
    """Model for configuring image field mappings."""

    url: str = Field(
        default="url",
        description="Field name for the full-size image URL",
        json_schema_extra={"ui:widget": "field-select"},
    )
    thumbnail: str = Field(
        default="small_thumb",
        description="Field name for the thumbnail URL",
        json_schema_extra={"ui:widget": "field-select"},
    )
    author: Optional[str] = Field(
        default=None,
        description="Field name for the image author/photographer",
        json_schema_extra={"ui:widget": "field-select"},
    )
    date: Optional[str] = Field(
        default=None,
        description="Field name for the image date",
        json_schema_extra={"ui:widget": "field-select"},
    )


class InfoItem(BaseModel):
    """Model for a single item within the info grid."""

    label: str = Field(
        ...,
        description="The label or title for the info item.",
        json_schema_extra={"ui:widget": "text"},
    )
    value: Optional[Union[str, int, float]] = Field(
        default=None,
        description="The value to display (if source is not used).",
        json_schema_extra={"ui:widget": "text"},
    )
    source: Optional[str] = Field(
        default=None,
        description="Dot-notation key to fetch the value from the data source.",
        json_schema_extra={"ui:widget": "field-select"},
    )
    unit: Optional[str] = Field(
        default=None,
        description="Optional unit for the value (e.g., '%', 'USD').",
        json_schema_extra={"ui:widget": "text"},
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description or tooltip for the item.",
        json_schema_extra={"ui:widget": "textarea"},
    )
    icon: Optional[str] = Field(
        default=None,
        description="Optional icon class (e.g., Font Awesome 'fas fa-users').",
        json_schema_extra={"ui:widget": "text"},
    )
    format: Optional[str] = Field(
        default=None,
        description="Optional format for the value (e.g., 'map', 'number', 'stats').",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": ["map", "number", "image", "stats"],
        },
    )
    mapping: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional mapping for the 'map' format.",
        json_schema_extra={"ui:widget": "json"},
    )
    image_mapping: Optional[ImageMapping] = Field(
        default=None,
        description="Optional image field mapping for the 'image' format.",
        json_schema_extra={"ui:widget": "json"},
    )


class InfoGridParams(BasePluginParams):
    """Parameters for configuring the InfoGridWidget."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Display a grid of key information items (KPIs, stats, labels)",
            "examples": [
                {
                    "items": [
                        {
                            "label": "Total Species",
                            "source": "species_count.value",
                            "format": "number",
                            "icon": "fas fa-leaf",
                        }
                    ],
                    "grid_columns": 3,
                }
            ],
        }
    )

    title: Optional[str] = Field(
        default=None,
        description="Optional title for the widget container.",
        json_schema_extra={"ui:widget": "text"},
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description for the widget container.",
        json_schema_extra={"ui:widget": "textarea"},
    )
    items: List[InfoItem] = Field(
        ...,
        description="A list of info items to display in the grid.",
        json_schema_extra={"ui:widget": "array"},
    )
    grid_columns: Optional[int] = Field(
        default=None,
        description="Number of columns (e.g., 2, 3, 4). Auto-adjusts if None.",
        json_schema_extra={"ui:widget": "number", "ui:min": 1, "ui:max": 6},
    )
    # Add styling options if needed, e.g., card_style: str = 'basic'


# --- Widget Implementation ---


@register("info_grid", PluginType.WIDGET)
class InfoGridWidget(WidgetPlugin):
    """Displays a grid of key information items (KPIs, stats, labels)."""

    param_schema = InfoGridParams

    # Pattern matching: Declare compatible input data structures
    compatible_structures = [
        {"*": "dict"},  # field_aggregator - dynamic keys with {value, units} structure
        {"name": "dict", "rank": "dict"},  # Partial field_aggregator structure
    ]

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
            title_html = f'<div class="mb-4"><h3 class="text-lg font-medium text-gray-900">{html.escape(str(params.title))}</h3></div>'

        description_html = ""
        if params.description:
            description_html = f'<div class="mb-4"><p class="text-sm text-gray-500">{html.escape(str(params.description))}</p></div>'

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

            # Skip item if the extracted value is None
            if item_value is None:
                continue

            # Default display value is the string representation (escaped for HTML safety)
            display_value = html.escape(str(item_value))

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
            elif item.format == "stats" and isinstance(item_value, dict):
                # Handle stats format (mean, min, max, std, count)
                display_value = self._render_stats(item_value)
            elif item.format == "image" and item.image_mapping:
                # Handle image gallery format
                # Debug log to see what we're getting
                logger.debug(
                    f"Image data type: {type(item_value)}, content: {str(item_value)[:200]}..."
                )
                display_value = self._render_image_gallery(
                    item_value, item.image_mapping, item.label
                )

            # --- HTML Generation with Tailwind CSS --- #
            # Handle icons - support for Font Awesome and other icon libraries
            icon_html = ""
            if item.icon:
                safe_icon = html.escape(str(item.icon), quote=True)
                if item.icon.startswith("fa"):
                    # Font Awesome icon
                    icon_html = f'<i class="{safe_icon} mr-2"></i>'
                else:
                    # Assume it's a simple icon name and use Font Awesome solid as default
                    icon_html = f'<i class="fas fa-{safe_icon} mr-2"></i>'

            unit_html = (
                f'<span class="text-gray-500 text-sm ml-1">{html.escape(str(item.unit))}</span>'
                if item.unit
                else ""
            )
            tooltip_attr = (
                f'title="{html.escape(str(item.description), quote=True)}"'
                if item.description
                else ""
            )

            # Generate HTML for each item with Tailwind + inline styles as fallback
            card_style = "padding: 1rem; background: white; border: 1px solid #e5e7eb; border-radius: 0.5rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05);"
            label_style = "font-size: 0.875rem; font-weight: 500; color: #6b7280; margin-bottom: 0.25rem;"
            value_style = "font-size: 1.5rem; font-weight: 600; color: #111827;"

            safe_label = html.escape(str(item.label))

            # Special handling for image format
            if item.format == "image":
                item_html = f"""
                <div class="info-grid-item p-4 bg-white border border-gray-200 rounded-lg shadow-sm" style="{card_style}" {tooltip_attr}>
                    <div style="display: flex; flex-direction: column; height: 100%;">
                        <div style="{label_style} margin-bottom: 0.75rem;">{icon_html}{safe_label}</div>
                        <div style="flex: 1;">{display_value}</div>
                    </div>
                </div>
                """
            elif item.format == "stats":
                # Stats format has its own styling from _render_stats
                item_html = f"""
                <div class="info-grid-item p-4 bg-white border border-gray-200 rounded-lg shadow-sm" style="{card_style}" {tooltip_attr}>
                    <div style="display: flex; flex-direction: column; height: 100%;">
                        <div style="{label_style}">{icon_html}{safe_label}</div>
                        <div>{display_value}</div>
                    </div>
                </div>
                """
            else:
                item_html = f"""
                <div class="info-grid-item p-4 bg-white border border-gray-200 rounded-lg shadow-sm" style="{card_style}" {tooltip_attr}>
                    <div style="display: flex; flex-direction: column; height: 100%;">
                        <div style="{label_style}">{icon_html}{safe_label}</div>
                        <div style="{value_style}">{display_value}{unit_html}</div>
                    </div>
                </div>
                """
            item_html_parts.append(item_html)

        # If no items were rendered, return empty string
        if not item_html_parts:
            return ""

        # Wrap items in a responsive grid layout with inline styles as fallback
        items_html = "\n".join(item_html_parts)

        # Calculate grid template based on columns
        grid_cols = params.grid_columns or 3
        output_html = f"""
        <div class="info-grid-widget" style="padding: 1rem;">
            {title_html}
            {description_html}
            <div class="grid {grid_cols_class} gap-4" style="display: grid; grid-template-columns: repeat({grid_cols}, minmax(0, 1fr)); gap: 1rem;">
                {items_html}
            </div>
        </div>
        """

        return output_html

    def _render_stats(self, stats_data: Dict[str, Any]) -> str:
        """Render statistics (mean, min, max, std, count) in a compact format."""
        if not stats_data:
            return '<span style="color: #9ca3af;">-</span>'

        parts = []

        # Format mean as the main value
        mean_val = stats_data.get("mean")
        if mean_val is not None:
            parts.append(
                f'<span style="font-size: 1.5rem; font-weight: 600; color: #111827;">{mean_val}</span>'
            )

        # Build secondary stats line
        secondary_parts = []
        min_val = stats_data.get("min")
        max_val = stats_data.get("max")
        if min_val is not None and max_val is not None:
            secondary_parts.append(
                f"<span style='color: #6b7280;'>{min_val} - {max_val}</span>"
            )

        std_val = stats_data.get("std")
        if std_val is not None:
            secondary_parts.append(f"<span style='color: #9ca3af;'>σ={std_val}</span>")

        count_val = stats_data.get("count")
        if count_val is not None:
            secondary_parts.append(
                f"<span style='color: #9ca3af;'>n={count_val}</span>"
            )

        if secondary_parts:
            secondary_html = " · ".join(secondary_parts)
            parts.append(
                f'<div style="font-size: 0.75rem; margin-top: 0.25rem;">{secondary_html}</div>'
            )

        return "".join(parts) if parts else '<span style="color: #9ca3af;">-</span>'

    def _render_image_gallery(
        self, image_data: Any, image_mapping: ImageMapping, label: str
    ) -> str:
        """Render an image gallery similar to the listView implementation."""
        if not image_data:
            return '<div class="text-center text-gray-400 text-sm py-4">Aucune image disponible</div>'

        # Handle the case where image_data might be a string representation of a list
        if isinstance(image_data, str):
            # If it's a URL starting with http, treat as single image
            if image_data.startswith("http"):
                image_data = [image_data]
            else:
                try:
                    image_data = json.loads(image_data)
                except (json.JSONDecodeError, TypeError):
                    image_data = [image_data]

        all_images = []
        display_images = []
        modal_images = []

        # Handle different data formats
        if isinstance(image_data, list):
            # Array of image objects or URLs
            for img in image_data:
                if isinstance(img, dict):
                    # Extract thumbnail URL for display
                    thumbnail_url = (
                        img.get(image_mapping.thumbnail)
                        or img.get("small_thumb")
                        or img.get(image_mapping.url)
                        or img.get("url", "")
                    )
                    if thumbnail_url:
                        all_images.append(thumbnail_url)

                    # Extract full-size URL for modal
                    modal_url = (
                        img.get("big_thumb")
                        or img.get(image_mapping.url)
                        or img.get("url", "")
                    )
                    if modal_url:
                        modal_images.append(modal_url)
                elif isinstance(img, str):
                    all_images.append(img)
                    modal_images.append(img)
            display_images = all_images[:6]  # Show first 6 images
        elif isinstance(image_data, dict):
            # Single image object
            thumbnail_url = (
                image_data.get(image_mapping.thumbnail)
                or image_data.get("small_thumb")
                or image_data.get(image_mapping.url)
                or image_data.get("url", "")
            )
            if thumbnail_url:
                all_images = [thumbnail_url]
                display_images = all_images

            modal_url = (
                image_data.get("big_thumb")
                or image_data.get(image_mapping.url)
                or image_data.get("url", "")
            )
            if modal_url:
                modal_images = [modal_url]

        if not all_images:
            return '<div class="text-center text-gray-400 text-sm py-4">Aucune image disponible</div>'

        # Generate unique gallery ID
        gallery_id = f"info-gallery-{hash(label) % 10000}"

        # Create image elements
        image_elements = []
        for index, image_url in enumerate(display_images):
            # Escape quotes properly for HTML attributes
            escaped_modal_images = json.dumps(modal_images).replace('"', "&quot;")
            safe_url = html.escape(image_url, quote=True).replace("'", "&#39;")
            image_elements.append(f"""
                <div class="w-16 h-16 bg-cover bg-center rounded border border-gray-200 cursor-pointer hover:opacity-80 transition-opacity"
                     style="background-image: url('{safe_url}')"
                     title="Image {index + 1}"
                     onclick="openImageLightbox({escaped_modal_images}, {index})">
                </div>
            """)

        # Hidden images
        hidden_images = []
        for index, image_url in enumerate(all_images[6:], start=6):
            escaped_modal_images = json.dumps(modal_images).replace('"', "&quot;")
            safe_url = html.escape(image_url, quote=True).replace("'", "&#39;")
            hidden_images.append(f"""
                <div class="w-16 h-16 bg-cover bg-center rounded border border-gray-200 cursor-pointer hover:opacity-80 transition-opacity hidden gallery-hidden"
                     style="background-image: url('{safe_url}')"
                     title="Image {index + 1}"
                     onclick="openImageLightbox({escaped_modal_images}, {index})">
                </div>
            """)

        remaining_count = len(all_images) - len(display_images)
        expand_button = ""
        collapse_button = ""

        if remaining_count > 0:
            expand_button = f"""
                <div class="w-16 h-16 bg-gray-100 rounded border border-gray-200 flex items-center justify-center text-gray-500 text-sm font-medium cursor-pointer hover:bg-gray-200 transition-colors expand-btn"
                     onclick="expandImageGallery('{gallery_id}', this)">
                    +{remaining_count}
                </div>
            """
            collapse_button = f"""
                <div class="w-16 h-16 bg-gray-100 rounded border border-gray-200 flex items-center justify-center text-gray-500 text-sm font-medium cursor-pointer hover:bg-gray-200 transition-colors collapse-btn hidden"
                     onclick="collapseImageGallery('{gallery_id}', this)">
                    −
                </div>
            """

        gallery_html = f'''
            <div id="{gallery_id}" class="grid grid-cols-5 gap-2 max-w-sm">
                {"".join(image_elements)}
                {"".join(hidden_images)}
                {expand_button}
                {collapse_button}
            </div>
        '''

        return gallery_html
