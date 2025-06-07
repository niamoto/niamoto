# src/niamoto/core/plugins/widgets/hierarchical_nav_widget.py

"""
Hierarchical Navigation Widget Plugin.

Provides an interactive tree navigation widget for browsing hierarchical data structures
like taxonomies, geographical zones, or any nested set/parent-child relationships.
"""

import json
import logging
from typing import Any, Optional, List

from pydantic import BaseModel, Field

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register

logger = logging.getLogger(__name__)


# --- Pydantic Models for Validation ---


class HierarchicalNavWidgetParams(BaseModel):
    """Parameters for configuring the HierarchicalNavWidget."""

    # Data source configuration
    referential_data: str = Field(
        ...,
        description="Identifier for the reference data source (e.g., 'taxon_ref', 'shape_ref')",
    )

    # Field mapping
    id_field: str = Field(
        ..., description="Name of the field containing unique item identifiers"
    )
    name_field: str = Field(
        ..., description="Name of the field containing item display names"
    )

    # Hierarchy structure fields (multiple options)
    parent_id_field: Optional[str] = Field(
        None,
        description="Name of the field containing parent item ID (for parent-child model)",
    )
    lft_field: Optional[str] = Field(
        None, description="Name of the 'left' field for nested set model"
    )
    rght_field: Optional[str] = Field(
        None, description="Name of the 'right' field for nested set model"
    )
    level_field: Optional[str] = Field(
        None, description="Name of the field indicating depth level in nested set model"
    )
    group_by_field: Optional[str] = Field(
        None,
        description="Name of the field to use for flat grouping (creates two-level hierarchy)",
    )
    group_by_label_field: Optional[str] = Field(
        None,
        description="Name of the field containing group display labels (if different from group_by_field)",
    )

    # Navigation configuration
    base_url: str = Field(
        ..., description="Base URL pattern for item links (e.g., '{{ depth }}taxon/')"
    )
    show_search: bool = Field(
        True, description="Whether to display a search/filter input above the tree"
    )

    # Runtime parameters (injected by exporter)
    current_item_id: Optional[Any] = Field(
        None,
        description="ID of the currently displayed item (injected by HtmlPageExporter)",
    )
    title: Optional[str] = Field(
        None, description="Widget title (retrieved from widget config)"
    )


# --- Widget Implementation ---


@register("hierarchical_nav_widget", PluginType.WIDGET)
class HierarchicalNavWidget(WidgetPlugin):
    """Interactive hierarchical navigation tree widget."""

    param_schema = HierarchicalNavWidgetParams

    def get_dependencies(self) -> List[str]:
        """Return the list of CSS/JS dependencies for this widget."""
        return [
            "/assets/js/niamoto_hierarchical_nav.js",
            "/assets/css/niamoto_hierarchical_nav.css",
        ]

    def render(self, data_list: Any, params: HierarchicalNavWidgetParams) -> str:
        """
        Generate the HTML for the hierarchical navigation widget.

        Args:
            data_list: Either the data or a flag to load from JS file
            params: Validated widget parameters including current_item_id

        Returns:
            HTML string for the widget
        """
        # Check if we should load data from JS file
        load_from_js = isinstance(data_list, dict) and data_list.get(
            "load_from_js", False
        )

        # Generate generic file and variable names based on referential_data
        # Extract group name from referential_data (e.g., "taxon_ref" -> "taxon")
        group_name = params.referential_data.replace("_ref", "")

        # Use generic naming convention
        js_file = f"{group_name}_navigation.js"
        data_var = f"{group_name}NavigationData"

        # Process base_url to replace {{ depth }} with appropriate relative path
        base_url = params.base_url
        if "{{ depth }}" in base_url:
            # For detail pages in subfolders, we need to go up one level
            base_url = base_url.replace("{{ depth }}", "../")

        # Generate unique IDs for this widget instance
        widget_id = f"hierarchical-nav-{params.referential_data.replace('_', '-')}"
        container_id = f"{widget_id}-container"
        search_id = f"{widget_id}-search" if params.show_search else None

        # Start building HTML
        html_parts = []

        # Search input (if enabled)
        if params.show_search:
            html_parts.append(f'''
                <div class="mb-4">
                    <input type="text"
                           id="{search_id}"
                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
                           placeholder="Rechercher..."
                           aria-label="Rechercher dans l'arbre de navigation">
                </div>
            ''')

        # Tree container - removed max-height to avoid double scroll
        html_parts.append(f'''
            <div id="{container_id}"
                 class="hierarchical-nav-tree"
                 role="tree"
                 aria-label="Navigation hiérarchique">
                <!-- Tree will be populated by JavaScript -->
            </div>
        ''')

        # Prepare configuration for JavaScript (without data)
        js_config = {
            "containerId": container_id,
            "searchInputId": search_id,
            "dataVar": data_var,  # Name of the JS variable containing data
            "params": {
                "idField": params.id_field,
                "nameField": params.name_field,
                "parentIdField": params.parent_id_field,
                "lftField": params.lft_field,
                "rghtField": params.rght_field,
                "levelField": params.level_field,
                "groupByField": params.group_by_field,
                "groupByLabelField": params.group_by_label_field,
                "baseUrl": base_url,
            },
            "currentItemId": params.current_item_id,
        }

        # JavaScript initialization
        if load_from_js:
            # Load data from external JS file
            html_parts.append(f"""
                <script src="../assets/js/{js_file}"></script>
                <script>
                // Use a more robust initialization approach
                function initializeHierarchicalNav() {{
                    if (typeof NiamotoHierarchicalNav !== 'undefined' && typeof {data_var} !== 'undefined') {{
                        const config = {json.dumps(js_config, ensure_ascii=False)};
                        config.items = {data_var};  // Get data from loaded JS file
                        new NiamotoHierarchicalNav(config);
                    }} else {{
                        // Retry after a short delay if dependencies aren't loaded yet
                        setTimeout(initializeHierarchicalNav, 50);
                    }}
                }}

                // Start initialization when DOM is ready
                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', initializeHierarchicalNav);
                }} else {{
                    // DOM is already loaded
                    initializeHierarchicalNav();
                }}
                </script>
            """)
        else:
            # Use inline data (fallback for compatibility)
            js_config["items"] = data_list if isinstance(data_list, list) else []
            html_parts.append(f"""
                <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    if (typeof NiamotoHierarchicalNav !== 'undefined') {{
                        new NiamotoHierarchicalNav({json.dumps(js_config, ensure_ascii=False)});
                    }} else {{
                        console.error('NiamotoHierarchicalNav script not loaded. Make sure niamoto_hierarchical_nav.js is included.');
                    }}
                }});
                </script>
            """)

        return "\n".join(html_parts)
