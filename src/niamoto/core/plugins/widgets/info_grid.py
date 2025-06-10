import logging
from typing import Any, List, Optional, Set, Union, Dict
import json

from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.common.utils.dict_utils import get_nested_value

logger = logging.getLogger(__name__)

# --- Pydantic Models for Validation ---


class ImageMapping(BaseModel):
    """Model for configuring image field mappings."""

    url: str = Field("url", description="Field name for the full-size image URL")
    thumbnail: str = Field(
        "small_thumb", description="Field name for the thumbnail URL"
    )
    author: Optional[str] = Field(
        None, description="Field name for the image author/photographer"
    )
    date: Optional[str] = Field(None, description="Field name for the image date")


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
    image_mapping: Optional[ImageMapping] = Field(
        None, description="Optional image field mapping for the 'image' format."
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

            # Skip item if the extracted value is None
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
            # Special handling for image format
            if item.format == "image":
                item_html = f"""
                <div class="info-grid-item p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200" {tooltip_attr}>
                    <div class="flex flex-col h-full">
                        <div class="text-sm font-medium text-gray-500 mb-3">{icon_html}{item.label}</div>
                        <div class="flex-1">{display_value}</div>
                    </div>
                </div>
                """
            else:
                item_html = f"""
                <div class="info-grid-item p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200" {tooltip_attr}>
                    <div class="flex flex-col h-full">
                        <div class="text-sm font-medium text-gray-500 mb-1">{icon_html}{item.label}</div>
                        <div class="text-2xl font-semibold text-gray-900">{display_value}{unit_html}</div>
                    </div>
                </div>
                """
            item_html_parts.append(item_html)

        # If no items were rendered, return empty string
        if not item_html_parts:
            return ""

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
                    # Try to parse as literal_eval for Python literals first
                    import ast

                    if image_data.startswith("[") and image_data.endswith("]"):
                        image_data = ast.literal_eval(image_data)
                    elif image_data.startswith("{") and image_data.endswith("}"):
                        image_data = ast.literal_eval(image_data)
                    else:
                        # Try JSON parsing
                        image_data = json.loads(image_data)
                except (ValueError, SyntaxError, json.JSONDecodeError):
                    # If all parsing fails, treat as single URL
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
            image_elements.append(f"""
                <div class="w-16 h-16 bg-cover bg-center rounded border border-gray-200 cursor-pointer hover:opacity-80 transition-opacity"
                     style="background-image: url('{image_url}')"
                     title="Image {index + 1}"
                     onclick="openImageLightbox({escaped_modal_images}, {index})">
                </div>
            """)

        # Hidden images
        hidden_images = []
        for index, image_url in enumerate(all_images[6:], start=6):
            escaped_modal_images = json.dumps(modal_images).replace('"', "&quot;")
            hidden_images.append(f"""
                <div class="w-16 h-16 bg-cover bg-center rounded border border-gray-200 cursor-pointer hover:opacity-80 transition-opacity hidden gallery-hidden"
                     style="background-image: url('{image_url}')"
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
