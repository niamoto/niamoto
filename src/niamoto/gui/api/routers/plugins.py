"""Plugin registry API endpoints using the real Niamoto plugin system."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import importlib
import pkgutil

# Import the real plugin system
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType

router = APIRouter()


class ParameterSchema(BaseModel):
    """Schema for a plugin parameter."""

    name: str
    type: str  # string, number, boolean, array, object
    required: bool = False
    default: Any = None
    description: Optional[str] = None
    enum: Optional[List[Any]] = None
    min: Optional[float] = None
    max: Optional[float] = None


class PluginInfo(BaseModel):
    """Information about a plugin."""

    id: str
    name: str
    type: str  # Use string instead of PluginType enum for JSON serialization
    description: str
    version: Optional[str] = "1.0.0"
    author: Optional[str] = None
    category: Optional[str] = None
    parameters_schema: List[ParameterSchema] = []
    compatible_inputs: List[str] = []
    output_format: Optional[str] = None
    example_config: Optional[Dict[str, Any]] = None


class CompatibilityCheck(BaseModel):
    """Request body for compatibility check."""

    source_data: Dict[str, Any]
    plugin_id: str
    config: Optional[Dict[str, Any]] = None


class CompatibilityResult(BaseModel):
    """Result of compatibility check."""

    compatible: bool
    reason: Optional[str] = None
    suggestions: List[str] = []


def load_all_plugins():
    """
    Load all plugins from the plugin directories to populate the registry.
    This ensures all available plugins are registered.
    """
    # Import paths for plugin modules
    plugin_paths = [
        "niamoto.core.plugins.loaders",
        "niamoto.core.plugins.transformers",
        "niamoto.core.plugins.exporters",
        "niamoto.core.plugins.widgets",
    ]

    for base_path in plugin_paths:
        try:
            # Import the base module
            base_module = importlib.import_module(base_path)

            # If it has submodules, iterate through them
            if hasattr(base_module, "__path__"):
                for importer, modname, ispkg in pkgutil.walk_packages(
                    path=base_module.__path__,
                    prefix=base_module.__name__ + ".",
                    onerror=lambda x: None,
                ):
                    try:
                        # Import each submodule to trigger plugin registration
                        importlib.import_module(modname)
                    except Exception:
                        # Skip modules that fail to import
                        pass
        except Exception:
            # Skip if base module doesn't exist
            pass


def get_plugin_info_from_class(name: str, plugin_class: type) -> PluginInfo:
    """
    Extract plugin information from a plugin class.

    Args:
        name: The registered name of the plugin
        plugin_class: The plugin class

    Returns:
        PluginInfo object with extracted information
    """
    # Get basic info from class
    description = plugin_class.__doc__ or f"{name} plugin"
    description = description.strip() if description else ""

    # Extract first line of docstring as short description
    if description:
        description = description.split("\n")[0].strip()

    # Determine category from module path
    module_path = plugin_class.__module__
    category = None

    if "transformers" in module_path:
        # Extract category from path like niamoto.core.plugins.transformers.aggregation.xxx
        parts = module_path.split(".")
        if "transformers" in parts:
            idx = parts.index("transformers")
            if idx + 1 < len(parts):
                category = parts[idx + 1]
    elif "loaders" in module_path:
        if "relation" in module_path:
            category = "relation"
        elif "file" in module_path:
            category = "file"
        elif "database" in module_path:
            category = "database"
        else:
            category = "data"
    elif "exporters" in module_path:
        category = "export"
    elif "widgets" in module_path:
        category = "visualization"

    # Get plugin type
    plugin_type = getattr(plugin_class, "type", PluginType.TRANSFORMER)

    # Try to extract parameters from config_model if it exists
    parameters_schema = []
    if hasattr(plugin_class, "config_model"):
        try:
            config_model = plugin_class.config_model
            if hasattr(config_model, "__fields__"):
                for field_name, field_info in config_model.__fields__.items():
                    param = ParameterSchema(
                        name=field_name,
                        type="string",  # Simplified type mapping
                        required=field_info.required,
                        default=field_info.default
                        if field_info.default is not None
                        else None,
                        description=field_info.field_info.description
                        if hasattr(field_info, "field_info")
                        else None,
                    )
                    parameters_schema.append(param)
        except Exception:
            pass

    # Determine compatible inputs/outputs based on plugin type
    compatible_inputs = []
    output_format = None

    if plugin_type == PluginType.LOADER:
        compatible_inputs = ["config", "database", "file"]
        output_format = "dataframe"
    elif plugin_type == PluginType.TRANSFORMER:
        compatible_inputs = ["dataframe", "table", "any"]
        output_format = "transformed_data"
    elif plugin_type == PluginType.EXPORTER:
        compatible_inputs = ["dataframe", "aggregated_data", "any"]
        output_format = "exported_file"
    elif plugin_type == PluginType.WIDGET:
        compatible_inputs = ["dataframe", "aggregated_data", "any"]
        output_format = "html"

    return PluginInfo(
        id=name,
        name=name.replace("_", " ").title(),
        type=plugin_type.value,
        description=description,
        category=category,
        parameters_schema=parameters_schema,
        compatible_inputs=compatible_inputs,
        output_format=output_format,
    )


@router.get("/", response_model=List[PluginInfo])
async def list_plugins(
    type: Optional[str] = Query(None, description="Filter by plugin type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    compatible_with: Optional[str] = Query(
        None, description="Filter by compatible input format"
    ),
):
    """
    Get list of available plugins from the real plugin registry.

    Args:
        type: Filter by plugin type (loader, transformer, exporter, widget)
        category: Filter by category
        compatible_with: Filter by compatible input format

    Returns:
        List of plugins matching the filters
    """
    try:
        # Ensure all plugins are loaded
        load_all_plugins()

        # Get all plugins from registry
        all_plugins = PluginRegistry.list_plugins()
        plugins_info = []

        for plugin_type, plugin_names in all_plugins.items():
            # Filter by type if specified
            if type and plugin_type.value != type:
                continue

            for plugin_name in plugin_names:
                try:
                    plugin_class = PluginRegistry.get_plugin(plugin_name, plugin_type)
                    plugin_info = get_plugin_info_from_class(plugin_name, plugin_class)

                    # Filter by category if specified
                    if category and plugin_info.category != category:
                        continue

                    # Filter by compatible input if specified
                    if (
                        compatible_with
                        and compatible_with not in plugin_info.compatible_inputs
                    ):
                        if "any" not in plugin_info.compatible_inputs:
                            continue

                    plugins_info.append(plugin_info)
                except Exception:
                    # Skip plugins that fail to load
                    continue

        return plugins_info

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving plugins: {str(e)}"
        )


@router.get("/{plugin_id}", response_model=PluginInfo)
async def get_plugin(plugin_id: str):
    """
    Get detailed information about a specific plugin.

    Args:
        plugin_id: ID of the plugin

    Returns:
        Detailed plugin information
    """
    try:
        # Ensure all plugins are loaded
        load_all_plugins()

        # Try to find the plugin in any type
        for plugin_type in PluginType:
            if PluginRegistry.has_plugin(plugin_id, plugin_type):
                plugin_class = PluginRegistry.get_plugin(plugin_id, plugin_type)
                return get_plugin_info_from_class(plugin_id, plugin_class)

        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving plugin: {str(e)}"
        )


@router.get("/categories/list")
async def list_categories():
    """
    Get list of all plugin categories.

    Returns:
        List of unique categories across all plugins
    """
    try:
        # Ensure all plugins are loaded
        load_all_plugins()

        # Get all plugins and extract categories
        all_plugins = PluginRegistry.list_plugins()
        categories = set()

        for plugin_type, plugin_names in all_plugins.items():
            for plugin_name in plugin_names:
                try:
                    plugin_class = PluginRegistry.get_plugin(plugin_name, plugin_type)
                    plugin_info = get_plugin_info_from_class(plugin_name, plugin_class)
                    if plugin_info.category:
                        categories.add(plugin_info.category)
                except Exception:
                    continue

        sorted_categories = sorted(list(categories))

        return {"categories": sorted_categories, "count": len(sorted_categories)}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving categories: {str(e)}"
        )


@router.get("/types/list")
async def list_plugin_types():
    """
    Get list of all plugin types.

    Returns:
        List of available plugin types
    """
    return {"types": [t.value for t in PluginType], "count": len(PluginType)}


@router.post("/check-compatibility", response_model=CompatibilityResult)
async def check_compatibility(check: CompatibilityCheck):
    """
    Check if a plugin is compatible with given source data.

    Args:
        check: Compatibility check request with source data and plugin ID

    Returns:
        Compatibility result with explanation
    """
    try:
        # For now, return a simple compatibility check
        # This could be enhanced with actual plugin compatibility logic

        result = CompatibilityResult(compatible=True, reason=None, suggestions=[])

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking compatibility: {str(e)}"
        )
