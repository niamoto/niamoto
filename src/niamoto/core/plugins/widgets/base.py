# core/plugins/widgets/base.py
from pydantic import BaseModel
from typing import Optional

from niamoto.core.plugins.base import WidgetPlugin


class WidgetConfig(BaseModel):
    """Base configuration for widgets"""

    plugin: str
    data_source: str
    title: Optional[str]
    description: Optional[str]
    width: Optional[str]
    height: Optional[str]
    class_name: Optional[str]


class BaseWidget(WidgetPlugin):
    """Base class for all widgets"""

    def get_container_html(self, content: str, config: WidgetConfig) -> str:
        """Generate widget container HTML"""
        return f"""
        <div class="widget {config.class_name or ""}"
             style="width:{config.width or "auto"};height:{config.height or "auto"}">
            {f"<h3>{config.title}</h3>" if config.title else ""}
            {f"<p>{config.description}</p>" if config.description else ""}
            {content}
        </div>
        """
