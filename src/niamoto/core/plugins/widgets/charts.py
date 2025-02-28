# core/plugins/widgets/charts.py
import json
from typing import Optional, List, Dict, Any

from ..base import register, PluginType
from .base import BaseWidget, WidgetConfig


class BarChartConfig(WidgetConfig):
    x_field: str
    y_field: str
    color_scheme: Optional[str] = "blues"
    bar_padding: Optional[float] = 0.1


@register("bar_plot", PluginType.WIDGET)
class BarChart(BaseWidget):
    config_model = BarChartConfig

    def get_dependencies(self) -> List[str]:
        return ["https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"]

    def render(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        validated_config = self.validate_config(config)

        # Get data from source
        source_data = data[validated_config.data_source]

        # Generate unique ID for this chart
        chart_id = f"barchart_{id(self)}"

        # Generate D3.js code
        js_code = f"""
        const data = {json.dumps(source_data)};
        const chart = BarChart({{
            data: data,
            x: d => d['{validated_config.x_field}'],
            y: d => d['{validated_config.y_field}'],
            color: '{validated_config.color_scheme}',
            padding: {validated_config.bar_padding}
        }});
        document.getElementById('{chart_id}').appendChild(chart);
        """

        # Return complete widget HTML
        return self.get_container_html(
            f"""
            <div id="{chart_id}"></div>
            <script>{js_code}</script>
            """,
            validated_config,
        )
