# core/services/exporter.py
from typing import Dict, Any, List

from loguru import logger

from niamoto.core.plugins.base import WidgetPlugin, PluginType
from niamoto.core.plugins.registry import PluginRegistry


class ExporterService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.widget_registry = {}  # Cache des instances de widgets

    def get_widget(self, widget_type: str) -> WidgetPlugin:
        """Get or create widget instance"""
        if widget_type not in self.widget_registry:
            widget_class = PluginRegistry.get_plugin(widget_type, PluginType.WIDGET)
            self.widget_registry[widget_type] = widget_class()
        return self.widget_registry[widget_type]

    def render_widgets(
        self, data: Dict[str, Any], widget_configs: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Render all widgets for a page"""
        widgets = {}
        dependencies = set()

        for widget_config in widget_configs:
            widget = self.get_widget(widget_config["plugin"])

            # Collect dependencies
            dependencies.update(widget.get_dependencies())

            # Render widget
            try:
                widgets[widget_config["id"]] = widget.render(data, widget_config)
            except Exception as e:
                logger.error(
                    f"Error rendering widget {widget_config['plugin']}: {str(e)}"
                )
                widgets[widget_config["id"]] = (
                    f"<div class='error'>Widget error: {str(e)}</div>"
                )

        return {"widgets": widgets, "dependencies": list(dependencies)}

    def export_page(
        self,
        template: str,
        data: Dict[str, Any],
        widget_configs: List[Dict[str, Any]],
        output_path: str,
    ) -> None:
        """Export a complete page with widgets"""
        # Render widgets
        widget_data = self.render_widgets(data, widget_configs)

        # Get template
        template = self.env.get_template(template)

        # Render complete page
        html = template.render(
            data=data,
            widgets=widget_data["widgets"],
            dependencies=widget_data["dependencies"],
        )

        # Write output
        with open(output_path, "w") as f:
            f.write(html)
