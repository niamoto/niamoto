"""Plugin registry API endpoints using the real Niamoto plugin system."""

import threading
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

# Import the real plugin system
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.gui.api.context import get_optional_working_directory
from niamoto.gui.api.desktop_auth import require_desktop_mutation_auth

router = APIRouter()
_plugin_registry_reload_lock = threading.RLock()


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


def _validate_plugin_config(
    plugin_class: type, config: Optional[Dict[str, Any]]
) -> str | None:
    """Return a validation error string when the submitted plugin config is invalid."""
    schema = getattr(plugin_class, "param_schema", None) or getattr(
        plugin_class, "config_model", None
    )
    if schema is None:
        return None
    try:
        schema.model_validate(config or {})
    except Exception as exc:
        return str(exc)
    return None


def _snapshot_plugin_registry() -> tuple[
    dict[PluginType, dict], dict[PluginType, dict]
]:
    """Return a copy of the plugin registry so failed reloads can be rolled back."""
    return (
        {
            plugin_type: dict(plugins)
            for plugin_type, plugins in PluginRegistry._plugins.items()
        },
        {
            plugin_type: dict(metadata)
            for plugin_type, metadata in PluginRegistry._metadata.items()
        },
    )


def _restore_plugin_registry(
    snapshot: tuple[dict[PluginType, dict], dict[PluginType, dict]],
) -> None:
    """Restore a registry snapshot captured before a plugin reload attempt."""
    plugins_snapshot, metadata_snapshot = snapshot
    PluginRegistry.clear()
    for plugin_type, plugins in plugins_snapshot.items():
        PluginRegistry._plugins[plugin_type].update(plugins)
    for plugin_type, metadata in metadata_snapshot.items():
        PluginRegistry._metadata[plugin_type].update(metadata)


def load_all_plugins() -> None:
    """
    Load available plugins through the configured project/user/system cascade.

    The registry is rebuilt from the cascade so project-local plugins can
    override lower-priority plugins. If discovery fails, keep the previous
    registry intact for in-flight API requests.
    """
    with _plugin_registry_reload_lock:
        snapshot = _snapshot_plugin_registry()
        project_path = get_optional_working_directory()
        try:
            PluginRegistry.clear()
            PluginLoader().load_plugins_with_cascade(project_path)
        except Exception:
            _restore_plugin_registry(snapshot)
            raise


def _require_plugin_registry_auth(request: Request) -> None:
    """Require desktop auth before routes that import project plugin code."""
    require_desktop_mutation_auth(request)


def get_plugin_info_from_class(
    name: str, plugin_class: type, plugin_type: Optional[PluginType] = None
) -> PluginInfo:
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
    plugin_type = plugin_type or getattr(plugin_class, "type", PluginType.TRANSFORMER)

    # Try to extract parameters from param_schema (new standard) or config_model
    parameters_schema = []
    json_schema = None

    # First try param_schema (new standard for all our refactored plugins)
    if hasattr(plugin_class, "param_schema") and plugin_class.param_schema:
        try:
            json_schema = plugin_class.param_schema.model_json_schema()
        except Exception:
            pass
    # Fallback to config_model for backward compatibility
    elif hasattr(plugin_class, "config_model") and plugin_class.config_model:
        try:
            json_schema = plugin_class.config_model.model_json_schema()
        except Exception:
            pass

    # Extract parameters from JSON schema
    if json_schema:
        properties = json_schema.get("properties", {})
        required_fields = json_schema.get("required", [])

        for field_name, field_info in properties.items():
            # Get the UI widget type from json_schema_extra if available
            ui_widget = None
            if isinstance(field_info, dict):
                ui_widget = field_info.get("ui:widget")
                if not ui_widget:
                    extra = field_info.get("json_schema_extra", {})
                    if isinstance(extra, dict):
                        ui_widget = extra.get("ui:widget")

            # Map JSON schema type to our simplified type
            json_type = field_info.get("type", "string")
            if ui_widget:
                # Use UI widget as a hint for the type
                param_type = ui_widget
            elif json_type == "integer":
                param_type = "number"
            elif json_type == "array":
                param_type = "array"
            elif json_type == "object":
                param_type = "object"
            else:
                param_type = json_type

            param = ParameterSchema(
                name=field_name,
                type=param_type,
                required=field_name in required_fields,
                default=field_info.get("default"),
                description=field_info.get("description"),
                enum=field_info.get("enum"),
                min=field_info.get("minimum"),
                max=field_info.get("maximum"),
            )
            parameters_schema.append(param)

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
    request: Request,
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
    _require_plugin_registry_auth(request)
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
                    plugin_info = get_plugin_info_from_class(
                        plugin_name, plugin_class, plugin_type
                    )

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


@router.get("/{plugin_id}/schema", include_in_schema=False)
async def get_plugin_json_schema_priority_route(plugin_id: str, request: Request):
    """Keep plugin schema lookup ahead of the generic plugin detail route."""
    return await get_plugin_json_schema(plugin_id, request)


@router.get("/categories/list")
async def list_categories(request: Request):
    """
    Get list of all plugin categories.

    Returns:
        List of unique categories across all plugins
    """
    _require_plugin_registry_auth(request)
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
                    plugin_info = get_plugin_info_from_class(
                        plugin_name, plugin_class, plugin_type
                    )
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
async def check_compatibility(check: CompatibilityCheck, request: Request):
    """
    Check if a plugin is compatible with given source data.

    Args:
        check: Compatibility check request with source data and plugin ID

    Returns:
        Compatibility result with explanation
    """
    _require_plugin_registry_auth(request)
    try:
        load_all_plugins()

        plugin_info = None
        for plugin_type in PluginType:
            if PluginRegistry.has_plugin(check.plugin_id, plugin_type):
                plugin_class = PluginRegistry.get_plugin(check.plugin_id, plugin_type)
                plugin_info = get_plugin_info_from_class(
                    check.plugin_id, plugin_class, plugin_type
                )
                break

        if plugin_info is None:
            raise HTTPException(
                status_code=404, detail=f"Plugin '{check.plugin_id}' not found"
            )

        source_type = check.source_data.get("type")
        if not isinstance(source_type, str) or not source_type.strip():
            return CompatibilityResult(
                compatible=False,
                reason="source_data.type is required and must be a non-empty string.",
                suggestions=[
                    "Provide one of: " + ", ".join(plugin_info.compatible_inputs)
                ],
            )
        source_type = source_type.strip()
        if (
            source_type not in plugin_info.compatible_inputs
            and "any" not in plugin_info.compatible_inputs
        ):
            return CompatibilityResult(
                compatible=False,
                reason=(
                    f"Input type '{source_type}' is not compatible with "
                    f"plugin '{check.plugin_id}'"
                ),
                suggestions=["Use one of: " + ", ".join(plugin_info.compatible_inputs)],
            )

        config_error = _validate_plugin_config(plugin_class, check.config)
        if config_error:
            return CompatibilityResult(
                compatible=False,
                reason=f"Plugin config is invalid: {config_error}",
                suggestions=["Provide a config that matches the plugin schema."],
            )

        result = CompatibilityResult(
            compatible=True,
            reason=f"Plugin '{check.plugin_id}' accepts the provided source data.",
            suggestions=[],
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking compatibility: {str(e)}"
        )


@router.get("/{plugin_id}", response_model=PluginInfo)
async def get_plugin(plugin_id: str, request: Request):
    """
    Get detailed information about a specific plugin.

    Args:
        plugin_id: ID of the plugin

    Returns:
        Detailed plugin information
    """
    _require_plugin_registry_auth(request)
    try:
        # Ensure all plugins are loaded
        load_all_plugins()

        # Try to find the plugin in any type
        for plugin_type in PluginType:
            if PluginRegistry.has_plugin(plugin_id, plugin_type):
                plugin_class = PluginRegistry.get_plugin(plugin_id, plugin_type)
                return get_plugin_info_from_class(plugin_id, plugin_class, plugin_type)

        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving plugin: {str(e)}"
        )


@router.get("/{plugin_id}/schema")
async def get_plugin_json_schema(plugin_id: str, request: Request):
    """
    Get the full JSON schema for a plugin's parameters.

    This endpoint returns the complete Pydantic-generated JSON schema
    including all UI hints from json_schema_extra.

    Args:
        plugin_id: ID of the plugin

    Returns:
        Complete JSON schema for the plugin parameters
    """
    _require_plugin_registry_auth(request)
    try:
        # Ensure all plugins are loaded
        load_all_plugins()

        # Try to find the plugin in any type
        for plugin_type in PluginType:
            if PluginRegistry.has_plugin(plugin_id, plugin_type):
                plugin_class = PluginRegistry.get_plugin(plugin_id, plugin_type)

                # Try param_schema first (new standard)
                if hasattr(plugin_class, "param_schema") and plugin_class.param_schema:
                    # For param_schema, we want the raw schema of the params model
                    # This gives us just the fields, not the wrapper
                    return {
                        "plugin_id": plugin_id,
                        "plugin_type": plugin_type.value,
                        "has_params": True,
                        "schema": plugin_class.param_schema.model_json_schema(),
                    }
                # Fallback to config_model
                elif (
                    hasattr(plugin_class, "config_model") and plugin_class.config_model
                ):
                    return {
                        "plugin_id": plugin_id,
                        "plugin_type": plugin_type.value,
                        "has_params": True,
                        "schema": plugin_class.config_model.model_json_schema(),
                    }
                else:
                    return {
                        "plugin_id": plugin_id,
                        "plugin_type": plugin_type.value,
                        "has_params": False,
                        "message": "This plugin does not have configurable parameters",
                    }

        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving plugin schema: {str(e)}"
        )
