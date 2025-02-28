from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field


class PluginType(Enum):
    """Types of plugins supported by the system."""

    TRANSFORMER = "transformer"
    EXPORTER = "exporter"
    WIDGET = "widget"
    LOADER = "loader"


class PluginConfig(BaseModel):
    """Base configuration model for all plugins."""

    plugin: str = Field(..., description="Plugin identifier")
    source: Optional[str] = Field(None, description="Data source for the plugin")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Plugin specific parameters"
    )


class Plugin(ABC):
    """Base class for all plugins."""

    type: PluginType
    config_model = PluginConfig

    def __init__(self, db):
        """Initialize plugin with database connection."""
        self.db = db

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        return self.config_model(**config)


class LoaderPlugin(Plugin):
    """Base class for data loader plugins."""

    type = PluginType.LOADER

    @abstractmethod
    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Load data according to configuration.

        Args:
            group_id: ID of the group to load data for
            config: Configuration for the loader

        Returns:
            DataFrame with loaded data
        """
        pass


class TransformerPlugin(Plugin):
    """Base class for data transformer plugins."""

    type = PluginType.TRANSFORMER

    @abstractmethod
    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform input data according to configuration.

        Args:
            data: Input data to transform
            config: Configuration for the transformation

        Returns:
            Dictionary containing transformed data
        """
        pass


class ExporterPlugin(Plugin):
    """Base class for data exporter plugins."""

    type = PluginType.EXPORTER

    @abstractmethod
    def export(self, data: Dict[str, Any], config: Dict[str, Any]) -> None:
        """
        Export data according to configuration.

        Args:
            data: Data to export
            config: Configuration for the export
        """
        pass


class WidgetPlugin(Plugin):
    """Base class for visualization widgets."""

    type = PluginType.WIDGET

    def get_dependencies(self) -> list[str]:
        """
        Get list of required JS/CSS dependencies.

        Returns:
            List of dependency URLs
        """
        return []

    @abstractmethod
    def render(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """
        Render widget HTML/JS.

        Args:
            data: Data to visualize
            config: Configuration for the widget

        Returns:
            HTML/JS string for the widget
        """
        pass

    def get_container_html(self, content: str, config: Dict[str, Any]) -> str:
        """
        Generate widget container HTML.

        Args:
            content: Widget content HTML
            config: Widget configuration

        Returns:
            Container HTML string
        """
        width = config.get("width", "auto")
        height = config.get("height", "auto")
        title = config.get("title")
        description = config.get("description")

        return f"""
        <div class="widget {config.get("class_name", "")}" style="width:{width};height:{height}">
            {f"<h3>{title}</h3>" if title else ""}
            {f"<p>{description}</p>" if description else ""}
            {content}
        </div>
        """


# Decorators for plugin registration
def register(name: str, plugin_type: Optional[PluginType] = None):
    """
    Decorator to register a plugin.

    Args:
        name: Plugin identifier
        plugin_type: Type of plugin (optional, inferred from class if not provided)

    Returns:
        Decorated class
    """
    from .registry import PluginRegistry

    def decorator(plugin_class):
        # If plugin_type not provided, get it from class
        actual_type = plugin_type or plugin_class.type
        # Register plugin
        PluginRegistry.register_plugin(name, plugin_class, actual_type)
        return plugin_class

    return decorator
