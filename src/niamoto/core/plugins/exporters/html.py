# core/plugins/exporters/html.py
from typing import Optional, Dict, Any

from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader
from ..base import ExporterPlugin, PluginType, register


class HTMLExportConfig(BaseModel):
    template: str
    output_path: str
    template_data: Optional[Dict[str, Any]] = {}


@register("html", PluginType.EXPORTER)
class HTMLExporter(ExporterPlugin):
    type = PluginType.EXPORTER

    def __init__(self):
        super().__init__()
        self.env = Environment(loader=FileSystemLoader("templates"), autoescape=True)

    def validate_config(self, config: Dict[str, Any]) -> None:
        return HTMLExportConfig(**config)

    def export(self, data: Dict[str, Any], config: Dict[str, Any]) -> None:
        validated_config = self.validate_config(config)

        # Get template
        template = self.env.get_template(validated_config.template)

        # Render template
        context = {"data": data, **validated_config.template_data}
        html = template.render(**context)

        # Write output
        with open(validated_config.output_path, "w") as f:
            f.write(html)
