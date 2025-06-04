# core/plugins/base.py

"""
Core base definitions for the Niamoto plugin system.

This module defines the fundamental building blocks for all plugins,
including the plugin type enumeration, the abstract base class for plugins,
specific abstract base classes for different plugin types (Loaders, Transformers,
Exporters, Widgets), and the registration decorator.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, List, TYPE_CHECKING

# Import pandas for type hinting in LoaderPlugin, but avoid runtime dependency if possible
# Or use 'Any' if pandas might not always be present where this base is imported.
import pandas as pd

# Import BaseModel for type hinting in WidgetPlugin render method signature
# Use TYPE_CHECKING to avoid circular imports if models are defined elsewhere
if TYPE_CHECKING:
    from pydantic import BaseModel

    # Assuming TargetConfig and WidgetConfig will be defined in core.plugins.models
    from .models import TargetConfig, WidgetConfig


class PluginType(Enum):
    """Enumeration of the different types of plugins supported."""

    TRANSFORMER = "transformer"
    EXPORTER = "exporter"
    WIDGET = "widget"
    LOADER = "loader"


class Plugin(ABC):
    """Abstract base class for all plugins in the Niamoto system."""

    # Each concrete plugin class MUST define its type
    type: PluginType
    # Each concrete plugin class SHOULD define its Pydantic config model (for params)
    # config_model: Type[BaseModel] = None # Example placeholder

    def __init__(self, db: Any):
        """
        Initialize the plugin.

        Args:
            db: Database connection object or similar shared resource.
                Consider using dependency injection for more complex scenarios.
        """
        # Store database connection if needed by all plugins
        # If not all plugins need it, consider passing it only where required.
        self.db = db


class LoaderPlugin(Plugin, ABC):
    """Abstract base class for data loader plugins."""

    type = PluginType.LOADER
    # Concrete loaders should define: config_model = MyLoaderConfig

    @abstractmethod
    def load_data(self, *args, **kwargs) -> pd.DataFrame:
        """
        Load data based on the provided configuration.

        The exact signature (args, kwargs) will depend on how the loader
        is called by the service managing data loading. It likely needs
        access to its specific configuration parameters.

        Returns:
            A pandas DataFrame containing the loaded data.
        """
        raise NotImplementedError


class TransformerPlugin(Plugin, ABC):
    """Abstract base class for data transformer plugins."""

    type = PluginType.TRANSFORMER
    # Concrete transformers should define: config_model = MyTransformerConfig

    @abstractmethod
    def transform(self, data: Any, params: "BaseModel") -> Any:
        """
        Transform the input data based on validated parameters.

        Args:
            data: The input data to transform (type might vary, e.g., DataFrame).
            params: A Pydantic model instance containing the validated parameters
                    specific to this transformer, derived from its config_model.

        Returns:
            The transformed data (type might vary).
        """
        # Note: The signature assumes validation happens before calling transform,
        # passing the validated Pydantic model instance.
        raise NotImplementedError


class ExporterPlugin(Plugin, ABC):
    """Abstract base class for data exporter plugins."""

    type = PluginType.EXPORTER
    # Concrete exporters should define: config_model = MyExporterConfig (for overall params)

    @abstractmethod
    def export(self, target_config: "TargetConfig", repository: Any) -> None:
        """
        Export data based on the provided target configuration.

        Args:
            target_config: The validated Pydantic model representing the
                           configuration for this specific export target
                           (from export.yml). Needs forward reference or deferred import.
            repository: An object providing access to the transformed data needed
                        for the export.
        """
        # Note: Needs forward reference 'TargetConfig' or deferred import.
        raise NotImplementedError


class WidgetPlugin(Plugin, ABC):
    """Abstract base class for visualization widget plugins used in HTML exports."""

    type = PluginType.WIDGET
    # Concrete widgets should define: config_model = MyWidgetParams

    def get_dependencies(self) -> List[str]:
        """
        Declare any external JS or CSS files required by this widget.

        These URLs will be collected by the HtmlPageExporter and potentially
        added to the <head> of the HTML document.

        Returns:
            A list of strings, typically URLs to CSS or JS files.
        """
        return []

    @abstractmethod
    def render(self, data: Any, params: "BaseModel") -> str:
        """
        Render the widget's HTML representation based on input data and parameters.

        Args:
            data: The specific data required by this widget, extracted based
                  on the 'data_source' key in the widget configuration.
            params: A Pydantic model instance containing the validated parameters
                    specific to this widget, derived from its config_model.

        Returns:
            An HTML string representing the rendered widget.
        """
        # Note: Needs forward reference 'BaseModel' from Pydantic or specific param model types.
        raise NotImplementedError

    def get_container_html(
        self, widget_id: str, content: str, config: "WidgetConfig"
    ) -> str:
        """
        Generate the standard HTML container wrapping the widget's content.

        This provides a consistent structure (div, optional title, description)
        around the HTML generated by the `render` method.

        Args:
            widget_id: A unique ID generated for this specific widget instance on the page.
            content: The HTML content generated by the widget's `render` method.
            config: The validated Pydantic model (`WidgetConfig`) representing
                    this widget's configuration entry from the export.yml file
                    (contains plugin name, data_source, params dict, title, etc.).
                    Needs forward reference or deferred import.

        Returns:
            The complete HTML string for the widget including its container.
        """
        # Note: Needs forward reference 'WidgetConfig' or deferred import.
        # Access common config directly, specific params via config.params
        width = config.params.get("width", "auto")
        height = config.params.get("height", "auto")

        # Support both structures for backward compatibility:
        # 1. New structure: title/description at widget level
        # 2. Old structure: title/description in params
        title = config.title if config.title is not None else config.params.get("title")
        description = (
            config.description
            if config.description is not None
            else config.params.get("description")
        )

        css_class = config.params.get(
            "class_name", ""
        )  # Example of accessing specific param

        # Use the provided widget_id for the container div
        title_html = ""
        if title:
            if description:
                # Title with elegant tooltip for description
                title_html = f"""
                <div class="widget-header-modern">
                    <h3 class="widget-title-modern">
                        {title}
                        <span class="info-tooltip" data-tooltip="{description.replace('"', "&quot;").replace("'", "&#39;")}">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="10"></circle>
                                <path d="M9,9h0a3,3,0,0,1,6,0c0,2-3,3-3,3"></path>
                                <line x1="12" y1="17" x2="12.01" y2="17"></line>
                            </svg>
                            <span class="tooltip-text">{description}</span>
                        </span>
                    </h3>
                </div>
                """
            else:
                # Title without tooltip
                title_html = f"""
                <div class="widget-header-modern">
                    <h3 class="widget-title-modern">{title}</h3>
                </div>
                """

        return f"""
        <div id="{widget_id}" class="widget widget-modern {css_class}" style="width:{width}; height:{height};">
            {title_html}
            <div class="widget-content">
                {content}
            </div>
        </div>
        """


# Decorator for plugin registration
def register(name: str, plugin_type: Optional[PluginType] = None):
    """
    Class decorator to register a plugin with the PluginRegistry.

    Args:
        name: The unique identifier (string name) for the plugin.
        plugin_type: The type of the plugin (PluginType Enum). If None, it will
                     be inferred from the 'type' class attribute of the decorated class.

    Returns:
        The original class, after registration.

    Raises:
        TypeError: If the decorated class does not have a 'type' attribute
                   and plugin_type is not provided.
        PluginRegistrationError: If registration fails (e.g., duplicate name
                                 for the same type).
    """
    # Import locally to avoid potential circular dependencies at import time
    from .registry import PluginRegistry
    # Import exception for explicit error handling (optional)
    # from .exceptions import PluginRegistrationError

    def decorator(plugin_class):
        """The actual decorator function applied to the class."""
        # Determine the plugin type
        actual_type = plugin_type or getattr(plugin_class, "type", None)
        if actual_type is None:
            raise TypeError(
                f"Plugin class {plugin_class.__name__} must either have a 'type' class "
                f"attribute or have plugin_type specified in the @register decorator."
            )
        if not isinstance(actual_type, PluginType):
            raise TypeError(
                f"Plugin class {plugin_class.__name__} 'type' attribute must be "
                f"an instance of PluginType Enum (got {type(actual_type)})."
            )

        # Register the plugin using the provided name and determined type
        try:
            PluginRegistry.register_plugin(name, plugin_class, actual_type)
            # Optional: Log successful registration
            # logger.debug(f"Registered plugin '{name}' of type {actual_type.value}")
        except Exception:
            # Catch potential registration errors (like duplicates if registry handles it)
            # Re-raise as a more specific error? Depends on PluginRegistry impl.
            # For now, just let potential errors from register_plugin propagate.
            # Consider adding: from .exceptions import PluginRegistrationError
            # except PluginRegistrationError as reg_err:
            #    logger.error(...) raise
            # except Exception as other_err: ... raise PluginRegistrationError(...)
            raise  # Re-raise any exception during registration

        return plugin_class

    return decorator


# Note: Forward references like 'TargetConfig', 'WidgetConfig', 'BaseModel'
# might require adding `from __future__ import annotations` at the top of the file
# (for Python < 3.10) or using string literals for type hints if defined later
# or in files that would cause circular imports. For Pydantic BaseModel,
# importing `from pydantic import BaseModel` is usually fine.
