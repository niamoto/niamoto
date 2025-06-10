# src/niamoto/core/plugins/widgets/sunburst_chart.py

import logging
import plotly.graph_objects as go
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.core.plugins.widgets.plotly_utils import (
    apply_plotly_defaults,
    get_plotly_dependencies,
    render_plotly_figure,
)

logger = logging.getLogger(__name__)


class SunburstChartWidgetParams(BaseModel):
    """Parameters specific to the Sunburst Chart widget."""

    title: Optional[str] = Field(None, description="Title of the chart.")
    description: Optional[str] = Field(
        None, description="Description displayed below the title or in an info tooltip."
    )
    # Labels for the middle ring (categories)
    category_labels: Dict[str, str] = Field(
        {},
        description="Mapping from data keys (e.g., 'emprise') to display labels (e.g., 'Emprise').",
    )
    # Labels for the outer ring (leaves)
    leaf_labels: Dict[str, str] = Field(
        {},
        description="Mapping from data sub-keys (e.g., 'forest') to display labels (e.g., 'Forêt').",
    )
    # Colors for the outer ring (leaves). Can be a single color per leaf type
    # or nested dict for specific colors per category/leaf combination.
    leaf_colors: Dict[str, Any] = Field(
        {},
        description="Mapping for leaf node colors. Example: {'Forêt': '#COLOR1', 'Hors-forêt': {'emprise': '#COLOR2', ...}}",
    )
    branchvalues: str = Field(
        "total",
        description="Defines how the 'values' map to the sunburst sectors ('total' or 'remainder'). 'total' is usually preferred.",
    )
    text_info: str = Field(
        "percent parent",
        description="Determines which trace information appears on the graph ('label', 'text', 'value', 'current path', 'percent root', 'percent entry', 'percent parent'). Use 'percent parent' for percentages within each category.",
    )
    opacity: Optional[float] = Field(
        1.0, ge=0, le=1, description="Sets the opacity of the trace."
    )


@register("sunburst_chart", PluginType.WIDGET)
class SunburstChartWidget(WidgetPlugin):
    """Widget to display a sunburst chart using Plotly."""

    param_schema = SunburstChartWidgetParams

    def get_dependencies(self) -> set:
        """Return the set of CSS/JS dependencies. Plotly is handled centrally."""
        return get_plotly_dependencies()

    def render(
        self, data: Dict[str, Dict[str, float]], params: SunburstChartWidgetParams
    ) -> str:
        """
        Renders a sunburst chart from a nested dictionary.
        Input data structure: {'category1': {'leaf1': value1, 'leaf2': value2}, ...}
        """
        if not isinstance(data, dict) or not all(
            isinstance(v, dict) for v in data.values()
        ):
            logger.error(
                "SunburstChartWidget requires a nested dictionary as input data."
            )
            return "<p class='error'>Invalid data format for Sunburst Chart.</p>"

        ids = []
        labels = []
        parents = []
        values = []
        marker_colors = []  # To store colors for each segment

        root_id = "root"  # Use a root node for better structure
        ids.append(root_id)
        labels.append(params.title or "")  # Use title or empty for root label
        parents.append("")
        values.append(0)  # Root value is sum of children, calculated later
        marker_colors.append("rgba(0,0,0,0)")  # Transparent root

        total_root_value = 0

        # Check if all values are zero or null (no meaningful data)
        all_values = []
        for category_data in data.values():
            if isinstance(category_data, dict):
                all_values.extend(
                    [v for v in category_data.values() if isinstance(v, (int, float))]
                )

        if not all_values or all(v == 0 for v in all_values):
            return "<p class='info'>No data available.</p>"

        def default_category_label(k):
            return k.capitalize()

        def default_leaf_label(k):
            return k.capitalize()

        default_leaf_color = "#CCCCCC"  # Fallback color

        # Ensure deterministic order for categories (optional but good practice)
        category_keys = sorted(data.keys())

        for category_key in category_keys:
            leaves = data[category_key]
            if not isinstance(leaves, dict):
                logger.warning(
                    f"Skipping invalid data entry for category '{category_key}'. Expected a dictionary."
                )
                continue

            category_id = f"{root_id}-{category_key}"
            category_label = params.category_labels.get(
                category_key, default_category_label(category_key)
            )

            ids.append(category_id)
            labels.append(category_label)
            parents.append(root_id)
            # For branchvalues='total', parent value should be sum of children
            category_total_value = sum(
                v for v in leaves.values() if isinstance(v, (int, float))
            )
            values.append(category_total_value)
            # Let Plotly determine parent colors or make them transparent
            marker_colors.append("rgba(0,0,0,0)")  # Transparent middle ring
            total_root_value += category_total_value

            leaf_keys = sorted(leaves.keys())
            for leaf_key in leaf_keys:
                value = leaves[leaf_key]
                if not isinstance(value, (int, float)):
                    logger.warning(
                        f"Skipping invalid data value for leaf '{leaf_key}' in category '{category_key}'. Expected number."
                    )
                    continue

                leaf_id = f"{category_id}-{leaf_key}"
                leaf_label = params.leaf_labels.get(
                    leaf_key, default_leaf_label(leaf_key)
                )

                ids.append(leaf_id)
                labels.append(leaf_label)
                parents.append(category_id)
                values.append(value)  # Value for the outer ring

                # Determine color based on leaf_label and potentially category_key
                color_map = params.leaf_colors.get(leaf_label, default_leaf_color)
                final_color = default_leaf_color
                if isinstance(color_map, str):
                    final_color = color_map  # Simple color string for this leaf type
                elif isinstance(color_map, dict):
                    # Nested: Find color specific to this category, else fallback
                    final_color = color_map.get(
                        category_key, color_map.get("default", default_leaf_color)
                    )
                else:
                    logger.warning(
                        f"Unexpected color format for leaf '{leaf_label}'. Using default."
                    )

                marker_colors.append(final_color)

        # Update root value
        if root_id in ids:
            root_index = ids.index(root_id)
            values[root_index] = total_root_value

        try:
            # Construct arguments for go.Sunburst dynamically
            sunburst_args = {
                "ids": ids,
                "labels": labels,
                "parents": parents,
                "values": values,
                "branchvalues": params.branchvalues,
                "marker": dict(
                    colors=marker_colors, line=dict(color="#FFFFFF", width=1)
                ),
                "textinfo": params.text_info,
                "hoverinfo": "label+percent parent+value",
                "insidetextorientation": "radial",
                "sort": False,
            }

            # Create the trace object
            sunburst_trace = go.Sunburst(**sunburst_args)

            # Then create the figure with this trace
            fig = go.Figure(data=[sunburst_trace])

            layout_updates = {
                "margin": dict(t=5, l=5, r=5, b=5),  # Reduced margins
                "height": 450,  # Slightly taller for better label visibility
                # Sunburst charts manage colors via trace marker, so no colorscale needed here
            }
            apply_plotly_defaults(fig, layout_updates)

            return render_plotly_figure(fig)

        except Exception as e:
            logger.error(f"Failed to generate Sunburst chart: {e}", exc_info=True)
            return f"<p class='error'>Error generating Sunburst chart: {e}</p>"
