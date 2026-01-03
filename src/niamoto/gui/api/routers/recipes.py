"""
API routes for widget recipe management.

Provides a unified interface for configuring widgets across all data sources:
- occurrences (table data)
- csv_stats (pre-calculated class_objects)
- csv_direct (direct CSV columns)

A "widget recipe" combines: Source → Transformer → Widget
"""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.gui.api.utils.database import open_database
from niamoto.common.database import Database
from niamoto.core.imports.registry import EntityRegistry, EntityKind

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _ensure_plugins_loaded():
    """Ensure all transformer and widget plugins are loaded and registered."""
    # Import transformer plugins
    from niamoto.core.plugins.transformers.distribution import (  # noqa: F401
        binned_distribution,
        categorical_distribution,
        time_series_analysis,
    )
    from niamoto.core.plugins.transformers.aggregation import (  # noqa: F401
        statistical_summary,
        field_aggregator,
        binary_counter,
        top_ranking,
    )
    from niamoto.core.plugins.transformers.extraction import (  # noqa: F401
        geospatial_extractor,
    )
    from niamoto.core.plugins.transformers.class_objects import (  # noqa: F401
        field_aggregator as co_field_aggregator,
        binary_aggregator,
        series_extractor,
        categories_extractor,
        series_ratio_aggregator,
        categories_mapper,
        series_matrix_extractor,
        series_by_axis_extractor,
    )

    # Import widget plugins
    from niamoto.core.plugins.widgets import (  # noqa: F401
        bar_plot,
        donut_chart,
        interactive_map,
        radial_gauge,
        info_grid,
        stacked_area_plot,
        concentric_rings,
        line_plot,
        scatter_plot,
        sunburst_chart,
    )


# Ensure plugins are loaded at module import
_ensure_plugins_loaded()


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class SourceInfo(BaseModel):
    """Information about an available data source."""

    type: str  # "occurrences", "csv_stats", "csv_direct"
    name: Optional[str] = None  # source name for csv_stats/csv_direct
    columns: list[str] = Field(default_factory=list)
    transformers: list[str] = Field(default_factory=list)


class SourcesResponse(BaseModel):
    """Response listing available sources for a group."""

    group_by: str
    sources: list[SourceInfo]


class ParamSchema(BaseModel):
    """Schema for a plugin parameter."""

    type: str
    required: bool = False
    default: Optional[Any] = None
    description: Optional[str] = None
    enum: Optional[list[str]] = None
    # Extended schema info for complex types
    items_type: Optional[str] = None  # For arrays
    additional_properties_type: Optional[str] = None  # For dicts
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    # UI hints from Pydantic json_schema_extra
    ui_widget: Optional[str] = None
    ui_depends: Optional[str] = None
    ui_condition: Optional[str] = None
    ui_options: Optional[list[Any]] = None  # Options for select widgets
    ui_min: Optional[float] = None  # Min value for number inputs
    ui_max: Optional[float] = None  # Max value for number inputs
    ui_step: Optional[float] = None  # Step for number inputs
    ui_item_widget: Optional[str] = None  # Widget type for array items


class TransformerSchema(BaseModel):
    """Schema information for a transformer plugin."""

    name: str
    description: str
    params: dict[str, ParamSchema]
    suggested_widgets: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)


class WidgetSchema(BaseModel):
    """Schema information for a widget plugin."""

    name: str
    description: str
    params: dict[str, ParamSchema]
    compatible_transformers: list[str] = Field(default_factory=list)


class TransformerConfig(BaseModel):
    """Configuration for a transformer in a recipe."""

    plugin: str
    params: dict[str, Any] = Field(default_factory=dict)


class WidgetLayoutConfig(BaseModel):
    """Layout configuration for a widget."""

    colspan: int = 1
    order: int = 0


class WidgetOutputConfig(BaseModel):
    """Configuration for widget output in a recipe."""

    plugin: str
    title: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)
    layout: WidgetLayoutConfig = Field(default_factory=WidgetLayoutConfig)


class WidgetRecipe(BaseModel):
    """A complete widget recipe: transformer + widget."""

    widget_id: str = Field(..., description="Unique ID for this widget")
    transformer: TransformerConfig
    widget: WidgetOutputConfig


class SaveRecipeRequest(BaseModel):
    """Request to save a widget recipe."""

    group_by: str
    recipe: WidgetRecipe


class SaveRecipeResponse(BaseModel):
    """Response after saving a recipe."""

    success: bool
    message: str
    widget_id: str
    data_source_id: str


class ValidationError(BaseModel):
    """A validation error."""

    field: str
    message: str


class ValidateRecipeResponse(BaseModel):
    """Response from recipe validation."""

    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _load_transform_config(work_dir: Path) -> list[dict[str, Any]]:
    """Load transform.yml configuration as list format."""
    transform_path = work_dir / "config" / "transform.yml"
    if not transform_path.exists():
        return []

    with open(transform_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config if isinstance(config, list) else []


def _save_transform_config(work_dir: Path, config: list[dict[str, Any]]) -> None:
    """Save transform.yml configuration in list format."""
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    transform_path = config_dir / "transform.yml"
    with open(transform_path, "w", encoding="utf-8") as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


def _load_export_config(work_dir: Path) -> dict[str, Any]:
    """Load export.yml configuration."""
    export_path = work_dir / "config" / "export.yml"
    if not export_path.exists():
        return {"exports": []}

    with open(export_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config if isinstance(config, dict) else {"exports": []}


def _save_export_config(work_dir: Path, config: dict[str, Any]) -> None:
    """Save export.yml configuration."""
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    export_path = config_dir / "export.yml"
    with open(export_path, "w", encoding="utf-8") as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


def _get_table_columns(db: Database, table_name: str) -> list[str]:
    """Get column names from a database table."""
    try:
        cols = db.execute_sql(
            f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position",
            fetch_all=True,
        )
        return [c[0] for c in cols] if cols else []
    except Exception as e:
        logger.warning(f"Could not get columns for table {table_name}: {e}")
        return []


def _get_entity_columns(db: Database, entity_name: str) -> list[str]:
    """Get columns for an entity using EntityRegistry to resolve table name."""
    try:
        if not db.has_table(EntityRegistry.ENTITIES_TABLE):
            return []

        registry = EntityRegistry(db)
        try:
            metadata = registry.get(entity_name)
            return _get_table_columns(db, metadata.table_name)
        except Exception:
            # Entity not found in registry
            return []
    except Exception as e:
        logger.warning(f"Could not get columns for entity {entity_name}: {e}")
        return []


def _get_all_dataset_entities(db: Database) -> list[tuple[str, str, list[str]]]:
    """Get all dataset entities with their table names and columns.

    Returns:
        List of (entity_name, table_name, columns) tuples
    """
    try:
        if not db.has_table(EntityRegistry.ENTITIES_TABLE):
            return []

        registry = EntityRegistry(db)
        datasets = registry.list_entities(kind=EntityKind.DATASET)

        result = []
        for entity in datasets:
            columns = _get_table_columns(db, entity.table_name)
            result.append((entity.name, entity.table_name, columns))

        return result
    except Exception as e:
        logger.warning(f"Could not list dataset entities: {e}")
        return []


def _get_csv_columns(csv_path: Path) -> list[str]:
    """Get column names from a CSV file."""
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
            return [c.strip() for c in first_line.split(delimiter)]
    except Exception as e:
        logger.warning(f"Could not read CSV columns from {csv_path}: {e}")
        return []


def _get_all_sources(
    work_dir: Path, group_by: str, db: Optional[Database]
) -> list[SourceInfo]:
    """Get all sources from transform.yml for a group.

    Uses EntityRegistry to resolve entity names to table names and get columns.
    """
    config = _load_transform_config(work_dir)
    sources = []

    for group in config:
        if group.get("group_by") != group_by:
            continue

        for source in group.get("sources", []):
            data_path = source.get("data", "")
            source_name = source.get("name", "unknown")

            # CSV source
            if data_path.endswith(".csv"):
                csv_path = work_dir / data_path
                columns = _get_csv_columns(csv_path) if csv_path.exists() else []

                sources.append(
                    SourceInfo(
                        type="csv_stats",
                        name=source_name,
                        columns=columns,
                        transformers=_get_class_object_transformers(),
                    )
                )
            # Table/Entity source - resolve via EntityRegistry
            elif data_path and db:
                # data_path can be entity name (e.g., "occurrences") or table name
                # Try EntityRegistry first, then fall back to direct table query
                columns = _get_entity_columns(db, data_path)
                if not columns:
                    # Fallback: try as direct table name
                    columns = _get_table_columns(db, data_path)

                sources.append(
                    SourceInfo(
                        type="dataset",
                        name=source_name,
                        columns=columns,
                        transformers=_get_occurrence_transformers(),
                    )
                )

    return sources


def _get_occurrence_transformers() -> list[str]:
    """Get transformers applicable to occurrence data."""
    return [
        "field_aggregator",
        "geospatial_extractor",
        "top_ranking",
        "binary_counter",
        "binned_distribution",
        "statistical_summary",
        "categorical_distribution",
        "time_series_analysis",
    ]


def _get_class_object_transformers() -> list[str]:
    """Get transformers applicable to class_object data."""
    return [
        "class_object_field_aggregator",
        "class_object_binary_aggregator",
        "class_object_series_extractor",
        "class_object_categories_extractor",
        "class_object_series_ratio_aggregator",
        "class_object_categories_mapper",
        "class_object_series_matrix_extractor",
        "class_object_series_by_axis_extractor",
    ]


def _find_params_model(plugin_class: type) -> Optional[type]:
    """Find the *Params Pydantic model for a plugin class.

    Looks for a class named {PluginClassName}Params in the same module.
    E.g., BinnedDistribution -> BinnedDistributionParams
    """
    import inspect

    # Get the module where the plugin class is defined
    module = inspect.getmodule(plugin_class)
    if not module:
        return None

    # Build the expected params class name
    plugin_class_name = plugin_class.__name__
    params_class_name = f"{plugin_class_name}Params"

    # Look for the params class in the module
    params_class = getattr(module, params_class_name, None)

    # Verify it's a Pydantic model
    if params_class and hasattr(params_class, "model_json_schema"):
        return params_class

    return None


def _get_transformer_schema(plugin_name: str) -> Optional[TransformerSchema]:
    """Get schema for a transformer plugin."""
    try:
        plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.TRANSFORMER)
    except Exception:
        return None

    params: dict[str, ParamSchema] = {}

    # Strategy 1: Try to find a dedicated *Params model in the same module
    params_model = _find_params_model(plugin_class)

    if params_model:
        try:
            full_schema = params_model.model_json_schema()
            param_properties = full_schema.get("properties", {})
            param_required = full_schema.get("required", [])

            for prop_name, prop_info in param_properties.items():
                params[prop_name] = _extract_param_schema(
                    prop_name, prop_info, param_required
                )
        except Exception as e:
            logger.warning(f"Could not get params schema for {plugin_name}: {e}")

    # Strategy 2: Fall back to config_model if no params found
    if not params:
        config_model = getattr(plugin_class, "config_model", None)

        if config_model:
            try:
                # Get JSON schema from Pydantic model
                full_schema = config_model.model_json_schema()

                # Look for the params field - transformer configs have nested params
                params_ref = None
                properties = full_schema.get("properties", {})

                if "params" in properties:
                    params_prop = properties["params"]
                    # Check if it's a $ref to a definition
                    if "$ref" in params_prop:
                        ref_path = params_prop["$ref"]
                        # Extract definition name from "#/$defs/TimeSeriesAnalysisParams"
                        def_name = ref_path.split("/")[-1]
                        defs = full_schema.get("$defs", {})
                        if def_name in defs:
                            params_ref = defs[def_name]
                    elif "allOf" in params_prop:
                        # Handle allOf with $ref
                        for item in params_prop["allOf"]:
                            if "$ref" in item:
                                ref_path = item["$ref"]
                                def_name = ref_path.split("/")[-1]
                                defs = full_schema.get("$defs", {})
                                if def_name in defs:
                                    params_ref = defs[def_name]
                                    break

                # Use params schema if found, otherwise use top-level properties
                if params_ref:
                    param_properties = params_ref.get("properties", {})
                    param_required = params_ref.get("required", [])
                else:
                    param_properties = properties
                    param_required = full_schema.get("required", [])

                for prop_name, prop_info in param_properties.items():
                    if prop_name == "plugin":  # Skip the plugin field
                        continue
                    params[prop_name] = _extract_param_schema(
                        prop_name, prop_info, param_required
                    )
            except Exception as e:
                logger.warning(f"Could not get schema for {plugin_name}: {e}")

    # Determine source types
    source_types = []
    if plugin_name.startswith("class_object_"):
        source_types = ["csv_stats"]
    elif plugin_name in _get_occurrence_transformers():
        source_types = ["occurrences"]
    else:
        source_types = ["occurrences", "csv_stats", "csv_direct"]

    # Determine suggested widgets based on transformer type
    suggested_widgets = _get_suggested_widgets(plugin_name)

    # Get description from docstring
    description = plugin_class.__doc__ or f"Transformer plugin: {plugin_name}"
    if isinstance(description, str):
        description = description.strip().split("\n")[0]

    return TransformerSchema(
        name=plugin_name,
        description=description,
        params=params,
        suggested_widgets=suggested_widgets,
        source_types=source_types,
    )


def _get_suggested_widgets(transformer_name: str) -> list[str]:
    """Get suggested widgets for a transformer."""
    mapping = {
        "field_aggregator": ["info_grid"],
        "geospatial_extractor": ["interactive_map"],
        "top_ranking": ["bar_plot"],
        "binary_counter": ["donut_chart"],
        "binned_distribution": ["bar_plot"],
        "statistical_summary": ["radial_gauge"],
        "categorical_distribution": ["bar_plot", "donut_chart"],
        "time_series_analysis": ["bar_plot"],
        "class_object_field_aggregator": ["info_grid"],
        "class_object_binary_aggregator": ["donut_chart"],
        "class_object_series_extractor": ["bar_plot"],
        "class_object_categories_extractor": ["bar_plot"],
        "class_object_series_ratio_aggregator": ["stacked_area_plot"],
        "class_object_categories_mapper": ["bar_plot"],
        "class_object_series_matrix_extractor": ["heatmap", "bar_plot"],
        "class_object_series_by_axis_extractor": ["bar_plot"],
    }
    return mapping.get(transformer_name, ["bar_plot"])


def _extract_param_schema(
    prop_name: str, prop_info: dict, required_list: list[str]
) -> ParamSchema:
    """Extract ParamSchema from a Pydantic property definition."""
    param_type = prop_info.get("type", "string")

    # Handle anyOf for Optional types
    if "anyOf" in prop_info:
        for option in prop_info["anyOf"]:
            if option.get("type") != "null":
                param_type = option.get("type", "string")
                # Also check for nested properties in anyOf
                if "items" in option:
                    prop_info["items"] = option["items"]
                break

    # Extract array item type
    items_type = None
    if param_type == "array" and "items" in prop_info:
        items = prop_info["items"]
        items_type = items.get("type", "string")

    # Extract dict value type (additionalProperties)
    additional_props_type = None
    if param_type == "object" and "additionalProperties" in prop_info:
        add_props = prop_info["additionalProperties"]
        additional_props_type = add_props.get("type", "string")

    return ParamSchema(
        type=param_type,
        required=prop_name in required_list,
        default=prop_info.get("default"),
        description=prop_info.get("description"),
        enum=prop_info.get("enum"),
        items_type=items_type,
        additional_properties_type=additional_props_type,
        min_items=prop_info.get("minItems"),
        max_items=prop_info.get("maxItems"),
        ui_widget=prop_info.get("ui:widget"),
        ui_depends=prop_info.get("ui:depends"),
        ui_condition=prop_info.get("ui:condition"),
        ui_options=prop_info.get("ui:options"),
        ui_min=prop_info.get("ui:min"),
        ui_max=prop_info.get("ui:max"),
        ui_step=prop_info.get("ui:step"),
        ui_item_widget=prop_info.get("ui:item-widget"),
    )


def _get_widget_schema(plugin_name: str) -> Optional[WidgetSchema]:
    """Get schema for a widget plugin."""
    try:
        plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.WIDGET)
    except Exception:
        return None

    # Widget plugins use param_schema instead of config_model
    param_schema_class = getattr(plugin_class, "param_schema", None)
    params: dict[str, ParamSchema] = {}

    if param_schema_class:
        try:
            # Get JSON schema from Pydantic model
            full_schema = param_schema_class.model_json_schema()
            properties = full_schema.get("properties", {})
            required_list = full_schema.get("required", [])

            for prop_name, prop_info in properties.items():
                params[prop_name] = _extract_param_schema(
                    prop_name, prop_info, required_list
                )

        except Exception as e:
            logger.warning(f"Could not get schema for widget {plugin_name}: {e}")

    # Get compatible transformers (reverse lookup from suggested_widgets)
    compatible_transformers = []
    for transformer, widgets in {
        "field_aggregator": ["info_grid"],
        "geospatial_extractor": ["interactive_map"],
        "top_ranking": ["bar_plot"],
        "binary_counter": ["donut_chart"],
        "binned_distribution": ["bar_plot"],
        "statistical_summary": ["radial_gauge"],
        "categorical_distribution": ["bar_plot", "donut_chart"],
        "time_series_analysis": ["bar_plot"],
        "class_object_field_aggregator": ["info_grid"],
        "class_object_binary_aggregator": ["donut_chart"],
        "class_object_series_extractor": ["bar_plot"],
        "class_object_categories_extractor": ["bar_plot"],
        "class_object_series_ratio_aggregator": ["stacked_area_plot"],
        "class_object_categories_mapper": ["bar_plot"],
        "class_object_series_matrix_extractor": ["heatmap", "bar_plot"],
        "class_object_series_by_axis_extractor": ["bar_plot"],
    }.items():
        if plugin_name in widgets:
            compatible_transformers.append(transformer)

    # Get description from docstring
    description = plugin_class.__doc__ or f"Widget plugin: {plugin_name}"
    if isinstance(description, str):
        description = description.strip().split("\n")[0]

    return WidgetSchema(
        name=plugin_name,
        description=description,
        params=params,
        compatible_transformers=compatible_transformers,
    )


def _get_available_widgets() -> list[str]:
    """Get list of all available widget plugins."""
    try:
        return [
            "bar_plot",
            "donut_chart",
            "info_grid",
            "interactive_map",
            "radial_gauge",
            "stacked_area_plot",
            "concentric_rings",
            "heatmap",
            "gauge_chart",
            "summary_table",
        ]
    except Exception:
        return []


def _find_group_config(config: list[dict], group_by: str) -> Optional[dict]:
    """Find group configuration in transform config."""
    for group in config:
        if group.get("group_by") == group_by:
            return group
    return None


def _find_export_group(exports: list[dict], group_by: str) -> Optional[dict]:
    """Find group configuration in export config."""
    for export in exports:
        for group in export.get("groups", []):
            if group.get("group_by") == group_by:
                return group
    return None


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/sources/{group_by}", response_model=SourcesResponse)
async def get_available_sources(group_by: str):
    """
    Get available data sources for a group.

    Returns all sources (entity tables, CSV stats, etc.) with their
    available columns and applicable transformers.

    Uses EntityRegistry to resolve entity names to table names.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)
    db_path = get_database_path()

    if not db_path or not Path(db_path).exists():
        # No database - can only get CSV sources
        sources = _get_all_sources(work_dir, group_by, None)
        return SourcesResponse(group_by=group_by, sources=sources)

    try:
        with open_database(db_path, read_only=True) as db:
            # Get all sources from transform.yml
            sources = _get_all_sources(work_dir, group_by, db)

            # If no sources found in transform.yml, add all dataset entities
            if not sources:
                for entity_name, table_name, columns in _get_all_dataset_entities(db):
                    if columns:
                        sources.append(
                            SourceInfo(
                                type="dataset",
                                name=entity_name,
                                columns=columns,
                                transformers=_get_occurrence_transformers(),
                            )
                        )

            return SourcesResponse(group_by=group_by, sources=sources)

    except Exception as e:
        logger.exception(f"Error getting sources: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting sources: {str(e)}")


@router.get("/transformer-schema/{plugin_name}", response_model=TransformerSchema)
async def get_transformer_schema(plugin_name: str):
    """
    Get the schema for a transformer plugin.

    Returns the parameter definitions, suggested widgets, and applicable
    source types for the transformer.
    """
    schema = _get_transformer_schema(plugin_name)
    if not schema:
        raise HTTPException(
            status_code=404, detail=f"Transformer '{plugin_name}' not found"
        )
    return schema


@router.get("/transformers", response_model=list[str])
async def list_transformers():
    """List all available transformer plugins."""
    try:
        plugins = PluginRegistry.get_plugins_by_type(PluginType.TRANSFORMER)
        return list(plugins.keys())
    except Exception as e:
        logger.exception(f"Error listing transformers: {e}")
        return []


@router.get("/widget-schema/{plugin_name}", response_model=WidgetSchema)
async def get_widget_schema(plugin_name: str):
    """
    Get the schema for a widget plugin.

    Returns the parameter definitions with UI hints for form generation.
    """
    schema = _get_widget_schema(plugin_name)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Widget '{plugin_name}' not found")
    return schema


@router.get("/widgets", response_model=list[str])
async def list_widgets():
    """List all available widget plugins."""
    try:
        plugins = PluginRegistry.get_plugins_by_type(PluginType.WIDGET)
        return list(plugins.keys())
    except Exception as e:
        logger.exception(f"Error listing widgets: {e}")
        return []


@router.post("/validate", response_model=ValidateRecipeResponse)
async def validate_recipe(request: SaveRecipeRequest):
    """
    Validate a widget recipe without saving.

    Checks:
    - Transformer plugin exists
    - Widget plugin exists
    - Required parameters are provided
    - Widget ID is unique
    """
    errors = []
    warnings = []

    # Check transformer exists
    try:
        PluginRegistry.get_plugin(
            request.recipe.transformer.plugin, PluginType.TRANSFORMER
        )
    except Exception:
        errors.append(
            ValidationError(
                field="transformer.plugin",
                message=f"Transformer '{request.recipe.transformer.plugin}' not found",
            )
        )

    # Check widget exists
    try:
        PluginRegistry.get_plugin(request.recipe.widget.plugin, PluginType.WIDGET)
    except Exception:
        errors.append(
            ValidationError(
                field="widget.plugin",
                message=f"Widget '{request.recipe.widget.plugin}' not found",
            )
        )

    # Check widget_id is valid
    if not request.recipe.widget_id or not request.recipe.widget_id.strip():
        errors.append(
            ValidationError(
                field="widget_id",
                message="Widget ID cannot be empty",
            )
        )

    # Add warning if no title
    if not request.recipe.widget.title:
        warnings.append("Widget has no title - one will be generated from the ID")

    return ValidateRecipeResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.post("/save", response_model=SaveRecipeResponse)
async def save_widget_recipe(request: SaveRecipeRequest):
    """
    Save a widget recipe to transform.yml and export.yml.

    This creates:
    1. A widgets_data entry in transform.yml
    2. A widget entry in export.yml
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)

    # Validate first
    validation = await validate_recipe(request)
    if not validation.valid:
        error_messages = [f"{e.field}: {e.message}" for e in validation.errors]
        raise HTTPException(
            status_code=400, detail=f"Validation errors: {'; '.join(error_messages)}"
        )

    recipe = request.recipe
    group_by = request.group_by

    # Generate data source ID (for transform.yml)
    data_source_id = f"{recipe.widget_id}"

    # --- Update transform.yml ---
    transform_config = _load_transform_config(work_dir)

    # Find or create group
    group_config = _find_group_config(transform_config, group_by)
    if not group_config:
        group_config = {"group_by": group_by, "sources": [], "widgets_data": {}}
        transform_config.append(group_config)

    # Ensure widgets_data exists
    if "widgets_data" not in group_config:
        group_config["widgets_data"] = {}

    # Add/update widget data
    group_config["widgets_data"][data_source_id] = {
        "plugin": recipe.transformer.plugin,
        "params": recipe.transformer.params,
    }

    _save_transform_config(work_dir, transform_config)

    # --- Update export.yml ---
    export_config = _load_export_config(work_dir)

    # Find the web_pages export
    web_export = None
    for export in export_config.get("exports", []):
        if export.get("exporter") == "html_page_exporter":
            web_export = export
            break

    if not web_export:
        # Create default web export
        web_export = {
            "name": "web_pages",
            "enabled": True,
            "exporter": "html_page_exporter",
            "params": {"template_dir": "templates/", "output_dir": "exports/web"},
            "groups": [],
        }
        if "exports" not in export_config:
            export_config["exports"] = []
        export_config["exports"].append(web_export)

    # Find or create group in export
    export_group = None
    for group in web_export.get("groups", []):
        if group.get("group_by") == group_by:
            export_group = group
            break

    if not export_group:
        export_group = {
            "group_by": group_by,
            "output_pattern": f"{group_by}/{{id}}.html",
            "widgets": [],
        }
        if "groups" not in web_export:
            web_export["groups"] = []
        web_export["groups"].append(export_group)

    # Ensure widgets list exists
    if "widgets" not in export_group:
        export_group["widgets"] = []

    # Check if widget already exists (update) or add new
    widget_found = False
    for i, widget in enumerate(export_group["widgets"]):
        if widget.get("data_source") == data_source_id:
            # Update existing
            export_group["widgets"][i] = {
                "plugin": recipe.widget.plugin,
                "title": recipe.widget.title
                or recipe.widget_id.replace("_", " ").title(),
                "data_source": data_source_id,
                "layout": {
                    "colspan": recipe.widget.layout.colspan,
                    "order": recipe.widget.layout.order,
                },
                "params": recipe.widget.params,
            }
            widget_found = True
            break

    if not widget_found:
        # Add new widget
        export_group["widgets"].append(
            {
                "plugin": recipe.widget.plugin,
                "title": recipe.widget.title
                or recipe.widget_id.replace("_", " ").title(),
                "data_source": data_source_id,
                "layout": {
                    "colspan": recipe.widget.layout.colspan,
                    "order": recipe.widget.layout.order,
                },
                "params": recipe.widget.params,
            }
        )

    _save_export_config(work_dir, export_config)

    return SaveRecipeResponse(
        success=True,
        message=f"Widget '{recipe.widget_id}' saved successfully",
        widget_id=recipe.widget_id,
        data_source_id=data_source_id,
    )


@router.delete("/{group_by}/{widget_id}")
async def delete_widget_recipe(group_by: str, widget_id: str):
    """
    Delete a widget recipe from transform.yml and export.yml.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)

    # --- Update transform.yml ---
    transform_config = _load_transform_config(work_dir)
    group_config = _find_group_config(transform_config, group_by)

    if group_config and "widgets_data" in group_config:
        if widget_id in group_config["widgets_data"]:
            del group_config["widgets_data"][widget_id]
            _save_transform_config(work_dir, transform_config)

    # --- Update export.yml ---
    export_config = _load_export_config(work_dir)

    for export in export_config.get("exports", []):
        for group in export.get("groups", []):
            if group.get("group_by") == group_by:
                widgets = group.get("widgets", [])
                group["widgets"] = [
                    w for w in widgets if w.get("data_source") != widget_id
                ]

    _save_export_config(work_dir, export_config)

    return {"success": True, "message": f"Widget '{widget_id}' deleted"}


# =============================================================================
# PREVIEW ENDPOINT
# =============================================================================


class PreviewRecipeRequest(BaseModel):
    """Request to preview a widget recipe without saving."""

    group_by: str
    recipe: WidgetRecipe


def _wrap_preview_html(content: str, title: str = "Preview") -> str:
    """Wrap widget HTML in a complete HTML document for iframe display."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: system-ui, -apple-system, sans-serif;
            background: transparent;
        }}
        .plotly-graph-div {{
            width: 100% !important;
            height: 100% !important;
        }}
        .error {{
            color: #ef4444;
            padding: 1rem;
            text-align: center;
        }}
        .info {{
            color: #6b7280;
            padding: 1rem;
            text-align: center;
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/plotly.js@2.35.0/dist/plotly.min.js"></script>
</head>
<body>
{content}
</body>
</html>"""


def _build_widget_params(
    transformer: str,
    widget: str,
    data: dict[str, Any],
    title: str,
    extra_params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build widget parameters based on transformer output and widget type."""
    params: dict[str, Any] = {"title": title}

    # Merge extra params first (from recipe)
    if extra_params:
        params.update(extra_params)

    # Add default params based on widget type
    if widget == "bar_plot":
        if "x_axis" not in params:
            # Try to infer from data keys
            if "tops" in data:
                params.setdefault("x_axis", "counts")
                params.setdefault("y_axis", "tops")
                params.setdefault("orientation", "h")
            elif "labels" in data:
                params.setdefault("x_axis", "labels")
                params.setdefault("y_axis", "counts")
                params.setdefault("orientation", "v")
        params.setdefault("auto_color", True)

    elif widget == "donut_chart":
        params.setdefault("labels_field", "labels")
        params.setdefault("values_field", "counts")

    elif widget == "radial_gauge":
        params.setdefault("stat_to_display", "mean")
        params.setdefault("show_range", True)
        params.setdefault("auto_range", True)

    elif widget == "info_grid":
        pass  # info_grid uses data directly

    elif widget == "interactive_map":
        params.setdefault("map_style", "carto-voyager")
        params.setdefault("zoom", 7)

    return params


def _render_widget(
    db: Optional[Database],
    widget_name: str,
    data: dict[str, Any],
    transformer: str,
    title: str,
    extra_params: Optional[dict[str, Any]] = None,
) -> str:
    """Render a widget with the given data."""
    try:
        plugin_class = PluginRegistry.get_plugin(widget_name, PluginType.WIDGET)
        plugin_instance = plugin_class(db=db)

        # Build widget params
        widget_params = _build_widget_params(
            transformer, widget_name, data, title, extra_params
        )

        # Validate params if the plugin has a param_schema
        if hasattr(plugin_instance, "param_schema") and plugin_instance.param_schema:
            validated_params = plugin_instance.param_schema.model_validate(
                widget_params
            )
        else:
            validated_params = widget_params

        return plugin_instance.render(data, validated_params)
    except Exception as e:
        logger.exception(f"Error rendering widget '{widget_name}': {e}")
        return f"<p class='error'>Widget render error: {str(e)}</p>"


def _load_csv_data(
    csv_path: Path, class_object_name: Optional[str] = None
) -> dict[str, Any]:
    """Load data from a CSV file, optionally filtering by class_object column."""
    import pandas as pd

    try:
        # Detect delimiter
        with open(csv_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

        df = pd.read_csv(csv_path, delimiter=delimiter)

        # If class_object specified, try to find matching row
        if class_object_name and "class_object" in df.columns:
            matching = df[df["class_object"] == class_object_name]
            if not matching.empty:
                row = matching.iloc[0]
                # Parse JSON columns if present
                result = {}
                for col in df.columns:
                    val = row[col]
                    if isinstance(val, str) and (
                        val.startswith("{") or val.startswith("[")
                    ):
                        try:
                            import json

                            result[col] = json.loads(val)
                        except (json.JSONDecodeError, ValueError):
                            result[col] = val
                    else:
                        result[col] = val
                return result

        # Return first row as sample
        if not df.empty:
            row = df.iloc[0]
            result = {}
            for col in df.columns:
                val = row[col]
                if isinstance(val, str) and (
                    val.startswith("{") or val.startswith("[")
                ):
                    try:
                        import json

                        result[col] = json.loads(val)
                    except (json.JSONDecodeError, ValueError):
                        result[col] = val
                else:
                    result[col] = val
            return result

        return {}
    except Exception as e:
        logger.warning(f"Error loading CSV {csv_path}: {e}")
        return {}


def _get_csv_path_for_source(
    work_dir: Path, group_by: str, source_name: str
) -> Optional[Path]:
    """Get CSV path for a source name from transform.yml."""
    config = _load_transform_config(work_dir)

    for group in config:
        if group.get("group_by") != group_by:
            continue
        for source in group.get("sources", []):
            if source.get("name") == source_name:
                data_path = source.get("data", "")
                if data_path.endswith(".csv"):
                    return work_dir / data_path
    return None


def _load_import_config(work_dir: Path) -> dict[str, Any]:
    """Load import.yml configuration."""
    import_path = work_dir / "config" / "import.yml"
    if not import_path.exists():
        return {}
    with open(import_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_hierarchy_info(
    import_config: dict, group_by: Optional[str] = None
) -> dict[str, Any]:
    """Extract hierarchy info from import config."""
    # Find reference that matches group_by
    for ref in import_config.get("references", []):
        ref_name = ref.get("name", "")
        if group_by and ref_name == group_by:
            return {
                "reference_name": ref_name,
                "table_name": ref.get("data", "").replace("dataset_", "") or ref_name,
                "id_field": ref.get("identifier", "id"),
                "parent_field": ref.get("hierarchy", {}).get(
                    "parent_field", "id_parent"
                ),
            }

    # Fallback to first hierarchical reference
    for ref in import_config.get("references", []):
        if ref.get("hierarchy"):
            return {
                "reference_name": ref.get("name"),
                "table_name": ref.get("data", "").replace("dataset_", "")
                or ref.get("name"),
                "id_field": ref.get("identifier", "id"),
                "parent_field": ref.get("hierarchy", {}).get(
                    "parent_field", "id_parent"
                ),
            }

    return {
        "reference_name": "taxon",
        "table_name": "taxon",
        "id_field": "id",
        "parent_field": "id_parent",
    }


def _load_sample_occurrences(db, hierarchy_info: dict, config: dict) -> Any:
    """Load sample occurrence data for preview."""
    import pandas as pd

    table_name = hierarchy_info["table_name"]
    id_field = hierarchy_info["id_field"]

    # Find a representative entity with occurrences
    try:
        # Get an entity that has associated occurrences
        query = f"""
            SELECT DISTINCT t.{id_field}
            FROM {table_name} t
            JOIN occurrences o ON o.taxon_ref_id = t.{id_field}
            LIMIT 1
        """
        result = db.execute_sql(query)
        if not result:
            return pd.DataFrame()

        entity_id = result[0][0]

        # Load occurrences for this entity
        occ_query = f"""
            SELECT * FROM occurrences
            WHERE taxon_ref_id = {entity_id}
            LIMIT 100
        """
        return pd.read_sql(occ_query, db.engine)
    except Exception as e:
        logger.warning(f"Error loading sample occurrences: {e}")
        return pd.DataFrame()


def _preview_with_db(
    db,
    work_dir: Path,
    group_by: str,
    transformer_plugin: str,
    transformer_params: dict,
    widget_plugin: str,
    widget_params: dict,
    widget_title: str,
) -> str:
    """Execute preview with database connection."""
    # Check if this is a class_object-based transformer (CSV data)
    if transformer_plugin.startswith("class_object_"):
        # Get source name from params
        source_name = transformer_params.get("source", "")
        class_object_name = transformer_params.get("class_object")

        # Find CSV file for this source
        csv_path = _get_csv_path_for_source(work_dir, group_by, source_name)

        if not csv_path or not csv_path.exists():
            return _wrap_preview_html(
                f"<p class='info'>Source CSV '{source_name}' not found</p>"
            )

        # Load data from CSV
        csv_data = _load_csv_data(csv_path, class_object_name)

        if not csv_data:
            return _wrap_preview_html("<p class='info'>No data found in CSV source</p>")

        # Execute transformer
        transformer_cls = PluginRegistry.get_plugin(
            transformer_plugin, PluginType.TRANSFORMER
        )
        transformer_instance = transformer_cls(db=db, config=transformer_params)

        # For class_object transformers, pass the CSV data as a dict
        result = transformer_instance.transform(csv_data)

        if not result:
            return _wrap_preview_html(
                "<p class='info'>Transformer returned no data</p>"
            )

        # Render widget
        widget_html = _render_widget(
            db, widget_plugin, result, transformer_plugin, widget_title, widget_params
        )

        return _wrap_preview_html(widget_html, title=widget_title)

    else:
        # Standard occurrence-based transformer
        if not db:
            return _wrap_preview_html("<p class='error'>Database not found</p>")

        # Load import config for hierarchy info
        import_config = _load_import_config(work_dir)
        hierarchy_info = _get_hierarchy_info(import_config, group_by)

        # Load sample data
        sample_data = _load_sample_occurrences(db, hierarchy_info, transformer_params)

        if sample_data.empty:
            return _wrap_preview_html(
                "<p class='info'>No occurrence data available for preview</p>"
            )

        # Execute transformer
        transformer_cls = PluginRegistry.get_plugin(
            transformer_plugin, PluginType.TRANSFORMER
        )
        transformer_instance = transformer_cls(db=db, config=transformer_params)
        result = transformer_instance.transform(sample_data)

        if not result:
            return _wrap_preview_html(
                "<p class='info'>Transformer returned no data</p>"
            )

        # Render widget
        widget_html = _render_widget(
            db, widget_plugin, result, transformer_plugin, widget_title, widget_params
        )

        return _wrap_preview_html(widget_html, title=widget_title)


@router.post("/preview", response_class=HTMLResponse)
async def preview_recipe(request: PreviewRecipeRequest):
    """
    Preview a widget recipe without saving.

    Executes the transformer and renders the widget with sample data.
    Returns HTML content suitable for iframe display.
    """
    work_dir = get_working_directory()
    if not work_dir:
        return HTMLResponse(
            content=_wrap_preview_html(
                "<p class='error'>Working directory not configured</p>"
            ),
            status_code=500,
        )

    work_dir = Path(work_dir)
    recipe = request.recipe
    group_by = request.group_by

    transformer_plugin = recipe.transformer.plugin
    transformer_params = recipe.transformer.params
    widget_plugin = recipe.widget.plugin
    widget_params = recipe.widget.params
    widget_title = recipe.widget.title or recipe.widget_id.replace("_", " ").title()

    # Verify plugins exist
    try:
        PluginRegistry.get_plugin(transformer_plugin, PluginType.TRANSFORMER)
    except Exception:
        return HTMLResponse(
            content=_wrap_preview_html(
                f"<p class='error'>Transformer '{transformer_plugin}' not found</p>"
            ),
            status_code=400,
        )

    try:
        PluginRegistry.get_plugin(widget_plugin, PluginType.WIDGET)
    except Exception:
        return HTMLResponse(
            content=_wrap_preview_html(
                f"<p class='error'>Widget '{widget_plugin}' not found</p>"
            ),
            status_code=400,
        )

    db_path = get_database_path()
    if not db_path:
        return HTMLResponse(
            content=_wrap_preview_html(
                "<p class='error'>Database path not configured</p>"
            ),
            status_code=500,
        )

    try:
        with open_database(db_path, read_only=True) as db:
            html_content = _preview_with_db(
                db,
                work_dir,
                group_by,
                transformer_plugin,
                transformer_params,
                widget_plugin,
                widget_params,
                widget_title,
            )
            return HTMLResponse(content=html_content)

    except Exception as e:
        logger.exception(f"Error previewing recipe: {e}")
        return HTMLResponse(
            content=_wrap_preview_html(f"<p class='error'>Preview error: {str(e)}</p>"),
            status_code=500,
        )
