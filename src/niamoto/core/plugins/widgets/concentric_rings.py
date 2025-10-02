# src/niamoto/core/plugins/widgets/concentric_rings.py

import logging
import plotly.graph_objects as go
from pydantic import Field, ConfigDict
from typing import Dict, Any, Optional, List

from niamoto.core.plugins.base import WidgetPlugin, PluginType, register
from niamoto.core.plugins.models import BasePluginParams
from niamoto.core.plugins.widgets.plotly_utils import (
    apply_plotly_defaults,
    get_plotly_dependencies,
    render_plotly_figure,
)

logger = logging.getLogger(__name__)


class ConcentricRingsParams(BasePluginParams):
    """Parameters for the Concentric Rings widget."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Create concentric ring charts for displaying hierarchical forest cover data",
            "examples": [
                {
                    "title": "Forest Cover Rings",
                    "ring_order": ["um", "num", "emprise"],
                    "ring_labels": {"um": "UM", "num": "NUM", "emprise": "Emprise"},
                }
            ],
        }
    )

    title: Optional[str] = Field(
        default=None,
        description="Title of the chart",
        json_schema_extra={"ui:widget": "text"},
    )
    description: Optional[str] = Field(
        default=None,
        description="Description displayed below the title",
        json_schema_extra={"ui:widget": "textarea"},
    )
    ring_order: List[str] = Field(
        default=["um", "num", "emprise"],
        description="Order of rings from inside to outside",
        json_schema_extra={"ui:widget": "array", "ui:item-widget": "text"},
    )
    ring_labels: Dict[str, str] = Field(
        default={"um": "UM", "num": "NUM", "emprise": "Emprise"},
        description="Display labels for each ring",
        json_schema_extra={"ui:widget": "json"},
    )
    category_colors: Dict[str, Any] = Field(
        default={},
        description="Colors for each category. Can be string or dict for ring-specific colors",
        json_schema_extra={"ui:widget": "json"},
    )
    default_colors: List[str] = Field(
        default=["#6B8E23", "#8B7355", "#C5A98B", "#F4E4BC"],
        description="Default colors to use if category_colors not specified",
        json_schema_extra={"ui:widget": "array", "ui:item-widget": "color"},
    )
    border_width: float = Field(
        default=2.0,
        description="Width of borders between segments",
        json_schema_extra={
            "ui:widget": "number",
            "ui:min": 0,
            "ui:max": 10,
            "ui:step": 0.5,
        },
    )
    height: int = Field(
        default=500,
        description="Height of the chart in pixels",
        json_schema_extra={
            "ui:widget": "number",
            "ui:min": 200,
            "ui:max": 1000,
            "ui:step": 50,
        },
    )


@register("concentric_rings", PluginType.WIDGET)
class ConcentricRingsWidget(WidgetPlugin):
    """Widget to display concentric rings for forest cover data."""

    param_schema = ConcentricRingsParams

    def get_dependencies(self) -> set:
        """Return the set of CSS/JS dependencies."""
        return get_plotly_dependencies()

    def render(
        self, data: Dict[str, Dict[str, float]], params: ConcentricRingsParams
    ) -> str:
        """
        Renders concentric rings for hierarchical data.
        Expected data structure: {'ring1': {'category1': value1, 'category2': value2}, ...}
        """
        if not isinstance(data, dict):
            logger.error("ConcentricRingsWidget requires a dictionary as input data.")
            return (
                "<p class='error'>Invalid data format for Concentric Rings Chart.</p>"
            )

        # Check if we have the required rings
        missing_rings = [ring for ring in params.ring_order if ring not in data]
        if missing_rings:
            logger.warning(
                f"Missing rings: {missing_rings}. Continuing with available rings."
            )

        try:
            # Create a figure using plotly's pie charts to simulate concentric rings
            fig = go.Figure()

            # Define fixed hole sizes for proper concentric display
            ring_specs = {}
            for i, ring_key in enumerate(params.ring_order):
                if i == 0:  # Innermost (UM)
                    ring_specs[ring_key] = {"hole": 0.65}
                elif i == 1:  # Middle (NUM)
                    ring_specs[ring_key] = {"hole": 0.35}
                else:  # Outermost (Emprise)
                    ring_specs[ring_key] = {"hole": 0.0}

            # Process each ring from outside to inside (for proper layering)
            for ring_key in reversed(params.ring_order):
                if ring_key not in data:
                    continue

                ring_data = data[ring_key]
                if not isinstance(ring_data, dict):
                    continue

                # Get all category values for this ring
                categories = list(ring_data.keys())
                values = list(ring_data.values())

                if sum(values) == 0:
                    continue

                # Determine colors for each category
                ring_colors = []
                for category in categories:
                    if category in params.category_colors:
                        color = params.category_colors[category]
                        # If color is a dict, get color specific to this ring
                        if isinstance(color, dict):
                            ring_colors.append(
                                color.get(ring_key, color.get("default", "#CCCCCC"))
                            )
                        else:
                            ring_colors.append(color)
                    else:
                        # Use default colors in order
                        color_index = len(ring_colors) % len(params.default_colors)
                        ring_colors.append(params.default_colors[color_index])

                # Calculate percentages for each segment
                total = sum(values)

                # Don't show any text on the pie segments - we'll use annotations instead
                text_values = [""] * len(categories)

                # Add pie chart for this ring
                fig.add_trace(
                    go.Pie(
                        values=values,
                        text=text_values,
                        labels=[""] * len(categories),  # No labels on segments
                        hole=ring_specs[ring_key]["hole"],
                        marker=dict(
                            colors=ring_colors,
                            line=dict(color="#FFFFFF", width=params.border_width),
                        ),
                        textinfo="none",  # No text on pie segments
                        showlegend=False,
                        name=params.ring_labels.get(ring_key, ring_key.upper()),
                        sort=False,
                        direction="clockwise",
                        rotation=-30,  # Rotation vers la gauche pour mettre les pourcentages dans le vert
                    )
                )

            # Add annotations for ring labels and percentages
            for i, ring_key in enumerate(params.ring_order):
                if ring_key not in data:
                    continue

                ring_data = data[ring_key]
                if not isinstance(ring_data, dict):
                    continue

                # Calculate percentage for first category (forest)
                categories = list(ring_data.keys())
                values = list(ring_data.values())
                total = sum(values)
                if total > 0 and len(categories) > 0:
                    forest_percentage = round((values[0] / total * 100), 1)
                else:
                    forest_percentage = 0

                # Position for ring labels and percentages
                if i == 0:  # Innermost ring - center of the hole
                    label_x, label_y = 0.5, 0.4  # Décalé vers le bas
                    # Position for forest percentage (UM - remonté un peu)
                    percent_x, percent_y = 0.5, 0.67
                elif i == 1:  # Middle ring - décalé vers le bas
                    label_x, label_y = 0.5, 0.22  # Plus bas
                    # Position for forest percentage (NUM - remonté un peu)
                    percent_x, percent_y = 0.5, 0.77
                elif i == 2:  # Outermost ring - décalé vers le bas
                    label_x, label_y = 0.5, 0.08  # Encore plus bas
                    # Position for forest percentage (Emprise - remonté un peu)
                    percent_x, percent_y = 0.5, 0.87
                else:
                    # For more rings, distribute them evenly
                    label_y = 0.5 - (0.18 * i)  # Plus d'espacement vers le bas
                    label_x = 0.5
                    percent_x, percent_y = 0.5, 0.82 + (0.04 * i)

                # Add ring label annotation
                fig.add_annotation(
                    text=params.ring_labels.get(ring_key, ring_key.upper()),
                    x=label_x,
                    y=label_y,
                    font=dict(size=14, color="black", family="Arial Bold"),
                    showarrow=False,
                )

                # Add percentage annotation for forest segment
                if forest_percentage > 0:
                    fig.add_annotation(
                        text=f"{forest_percentage}%",
                        x=percent_x,
                        y=percent_y,
                        font=dict(size=14, color="white", family="Arial Bold"),
                        showarrow=False,
                    )

            layout_updates = {
                "title": params.title,
                "margin": dict(t=50, l=50, r=50, b=50),
                "height": params.height,
                "showlegend": False,
            }
            apply_plotly_defaults(fig, layout_updates)

            return render_plotly_figure(fig)

        except Exception as e:
            logger.error(
                f"Failed to generate Concentric Rings chart: {e}", exc_info=True
            )
            return f"<p class='error'>Error generating concentric rings chart: {e}</p>"
