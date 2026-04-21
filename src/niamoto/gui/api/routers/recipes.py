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

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.gui.api.utils.database import open_database
from niamoto.common.database import Database
from niamoto.core.imports.registry import EntityRegistry, EntityKind
from niamoto.gui.api.services.preview_utils import error_html, wrap_html_response
from niamoto.gui.api.services.templates.config_service import (
    load_transform_config,
    save_transform_config,
    load_export_config,
    save_export_config,
    find_transform_group,
)
from niamoto.common.table_resolver import quote_identifier, resolve_entity_table

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
        reference_enrichment_profile,
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
        enrichment_panel,
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

    type: str  # "reference", "dataset", "csv_stats"
    name: str  # source name (taxons, occurrences, etc.)
    table_name: Optional[str] = None  # actual DuckDB table name
    columns: list[str] = Field(default_factory=list)
    transformers: list[str] = Field(default_factory=list)


class SourcesResponse(BaseModel):
    """Response listing available sources for a group."""

    group_by: str
    sources: list[SourceInfo]


class ColumnNode(BaseModel):
    """A column or nested field in the tree structure."""

    name: str  # Column name or field name
    path: str  # Full path (e.g., "extra_data.taxon_type")
    type: str  # Data type (string, number, boolean, object, array)
    children: list["ColumnNode"] = Field(default_factory=list)  # Nested fields for JSON


class SourceColumnsResponse(BaseModel):
    """Response with column tree structure for a source."""

    source_name: str
    table_name: Optional[str] = None
    columns: list[ColumnNode]


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
    ui_transform_schemas: Optional[dict[str, Any]] = (
        None  # Conditional schemas for transform_params
    )
    ui_group: Optional[str] = None  # Group name for organizing params
    ui_order: Optional[int] = None  # Order within group (lower = first)


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


class WidgetInfo(BaseModel):
    """Basic info for a widget plugin."""

    name: str
    label: str
    description: str


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


def _get_table_columns(db: Database, table_name: str) -> list[str]:
    """Get column names from a database table."""
    try:
        cols = db.execute_sql(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
            """,
            params={"table_name": table_name},
            fetch_all=True,
        )
        return [c[0] for c in cols] if cols else []
    except Exception as e:
        logger.warning("Could not get columns for table %s: %s", table_name, e)
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
        logger.warning("Could not get columns for entity %s: %s", entity_name, e)
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
        logger.warning("Could not list dataset entities: %s", e)
        return []


def _get_csv_columns(csv_path: Path) -> list[str]:
    """Get column names from a CSV file."""
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
            return [c.strip() for c in first_line.split(delimiter)]
    except Exception as e:
        logger.warning("Could not read CSV columns from %s: %s", csv_path, e)
        return []


def _get_all_sources(
    work_dir: Path, group_by: str, db: Optional[Database]
) -> list[SourceInfo]:
    """Get all sources from transform.yml for a group.

    Uses EntityRegistry to resolve entity names to table names and get columns.
    Also includes the reference table for the group (e.g., taxons -> entity_taxons).
    """
    config = load_transform_config(work_dir)
    sources = []
    added_sources = set()  # Track added source names to avoid duplicates

    # First, add the reference table for the group itself
    if db:
        ref_info = _get_reference_source(db, group_by)
        if ref_info:
            sources.append(ref_info)
            added_sources.add(ref_info.name)

    for group in config:
        if group.get("group_by") != group_by:
            continue

        for source in group.get("sources", []):
            data_path = source.get("data", "")
            source_name = source.get("name", "unknown")

            # Skip if already added (e.g., reference table)
            if source_name in added_sources:
                continue

            # CSV source
            if data_path.endswith(".csv"):
                csv_path = work_dir / data_path
                columns = _get_csv_columns(csv_path) if csv_path.exists() else []

                sources.append(
                    SourceInfo(
                        type="csv_stats",
                        name=source_name,
                        table_name=None,
                        columns=columns,
                        transformers=_get_class_object_transformers(),
                    )
                )
                added_sources.add(source_name)
            # Table/Entity source - resolve via EntityRegistry
            elif data_path and db:
                # data_path can be entity name (e.g., "occurrences") or table name
                # Try EntityRegistry first, then fall back to direct table query
                table_name = None
                columns = []

                try:
                    if db.has_table(EntityRegistry.ENTITIES_TABLE):
                        registry = EntityRegistry(db)
                        try:
                            metadata = registry.get(data_path)
                            table_name = metadata.table_name
                            columns = _get_table_columns(db, table_name)
                        except Exception:
                            pass
                except Exception:
                    pass

                if not columns:
                    # Fallback: try as direct table name
                    resolved_table = resolve_entity_table(db, data_path)
                    table_name = resolved_table or data_path
                    columns = _get_table_columns(db, table_name)

                sources.append(
                    SourceInfo(
                        type="dataset",
                        name=source_name,
                        table_name=table_name,
                        columns=columns,
                        transformers=_get_occurrence_transformers(),
                    )
                )
                added_sources.add(source_name)

    return sources


def _get_reference_source(db: Database, group_by: str) -> Optional[SourceInfo]:
    """Get the reference table source for a group.

    For group_by='taxons', returns the entity_taxons reference table.
    """
    try:
        if not db.has_table(EntityRegistry.ENTITIES_TABLE):
            return None

        registry = EntityRegistry(db)
        try:
            metadata = registry.get(group_by)
            if metadata.kind == EntityKind.REFERENCE:
                columns = _get_table_columns(db, metadata.table_name)
                return SourceInfo(
                    type="reference",
                    name=group_by,
                    table_name=metadata.table_name,
                    columns=columns,
                    transformers=_get_occurrence_transformers(),
                )
        except Exception:
            pass
        return None
    except Exception as e:
        logger.warning("Could not get reference source for %s: %s", group_by, e)
        return None


def _get_registry_source(db: Database, source_name: str) -> Optional[SourceInfo]:
    """Resolve a source directly from EntityRegistry, outside the current group."""
    try:
        if not db.has_table(EntityRegistry.ENTITIES_TABLE):
            return None

        registry = EntityRegistry(db)
        metadata = registry.get(source_name)
        columns = _get_table_columns(db, metadata.table_name)
        transformers = (
            _get_occurrence_transformers()
            if metadata.kind in {EntityKind.DATASET, EntityKind.REFERENCE}
            else []
        )
        source_type = "dataset" if metadata.kind == EntityKind.DATASET else "reference"
        return SourceInfo(
            type=source_type,
            name=source_name,
            table_name=metadata.table_name,
            columns=columns,
            transformers=transformers,
        )
    except Exception as e:
        logger.debug("Could not resolve registry source %s: %s", source_name, e)
        return None


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
            logger.warning("Could not get params schema for %s: %s", plugin_name, e)

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
                logger.warning("Could not get schema for %s: %s", plugin_name, e)

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
                # Copy ui metadata from anyOf option to prop_info
                for key in [
                    "ui:widget",
                    "ui:item-widget",
                    "ui:depends",
                    "ui:condition",
                    "ui:options",
                    "ui:min",
                    "ui:max",
                    "ui:step",
                    "ui:transform_schemas",
                    "ui:group",
                    "ui:order",
                ]:
                    if key in option and key not in prop_info:
                        prop_info[key] = option[key]
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
        ui_transform_schemas=prop_info.get("ui:transform_schemas"),
        ui_group=prop_info.get("ui:group"),
        ui_order=prop_info.get("ui:order"),
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
            logger.warning("Could not get schema for widget %s: %s", plugin_name, e)

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
                for entity_name, tbl_name, columns in _get_all_dataset_entities(db):
                    if columns:
                        sources.append(
                            SourceInfo(
                                type="dataset",
                                name=entity_name,
                                table_name=tbl_name,
                                columns=columns,
                                transformers=_get_occurrence_transformers(),
                            )
                        )

            return SourcesResponse(group_by=group_by, sources=sources)

    except Exception as e:
        logger.exception("Error getting sources: %s", e)
        raise HTTPException(status_code=500, detail=f"Error getting sources: {str(e)}")


@router.get(
    "/sources/{group_by}/{source_name}/columns", response_model=SourceColumnsResponse
)
async def get_source_columns(group_by: str, source_name: str):
    """
    Get columns for a specific source with tree structure for JSON fields.

    Returns columns organized as a tree where JSON columns (like extra_data)
    are expandable to show their nested fields.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)
    db_path = get_database_path()

    if not db_path or not Path(db_path).exists():
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            # First, find the source in the available sources
            sources = _get_all_sources(work_dir, group_by, db)
            source_info = next((s for s in sources if s.name == source_name), None)

            if not source_info:
                source_info = _get_registry_source(db, source_name)

            if not source_info:
                raise HTTPException(
                    status_code=404,
                    detail=f"Source '{source_name}' not found for group '{group_by}'",
                )

            # Build column tree
            columns = _build_column_tree(db, source_info)

            return SourceColumnsResponse(
                source_name=source_name,
                table_name=source_info.table_name,
                columns=columns,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting source columns: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Error getting source columns: {str(e)}"
        )


def _build_column_tree(db: Database, source_info: SourceInfo) -> list[ColumnNode]:
    """Build a tree structure of columns, expanding JSON fields."""
    columns = []

    if not source_info.table_name:
        # CSV source - flat columns only
        for col in source_info.columns:
            columns.append(ColumnNode(name=col, path=col, type="string", children=[]))
        return columns

    # Get column types from database
    try:
        quoted_table_name = quote_identifier(db, source_info.table_name)
        schema_sql = f"DESCRIBE {quoted_table_name}"
        result = db.execute_sql(schema_sql, fetch=True)

        if result:
            for row in result if isinstance(result, list) else [result]:
                col_name = (
                    row[0]
                    if isinstance(row, (list, tuple))
                    else row.get("column_name", "")
                )
                col_type = (
                    row[1]
                    if isinstance(row, (list, tuple))
                    else row.get("column_type", "")
                )

                # Check if this is a JSON column by sampling data
                if "JSON" in col_type.upper() or "STRUCT" in col_type.upper():
                    children = _extract_json_fields(
                        db, source_info.table_name, col_name
                    )
                    columns.append(
                        ColumnNode(
                            name=col_name,
                            path=col_name,
                            type="object",
                            children=children,
                        )
                    )
                else:
                    columns.append(
                        ColumnNode(
                            name=col_name,
                            path=col_name,
                            type=_map_db_type(col_type),
                            children=[],
                        )
                    )
    except Exception as e:
        logger.warning("Could not get column types: %s", e)
        # Fallback to flat list
        for col in source_info.columns:
            columns.append(ColumnNode(name=col, path=col, type="string", children=[]))

    return columns


def _extract_json_fields(
    db: Database, table_name: str, json_column: str
) -> list[ColumnNode]:
    """Extract nested field names from a JSON column by sampling data."""
    children = []
    seen_keys = set()

    try:
        quoted_table_name = quote_identifier(db, table_name)
        quoted_json_column = quote_identifier(db, json_column)
        # Sample some rows to discover JSON keys
        sample_sql = f"""
            SELECT DISTINCT json_keys({quoted_json_column}) as keys
            FROM {quoted_table_name}
            WHERE {quoted_json_column} IS NOT NULL
            LIMIT 100
        """
        result = db.execute_sql(sample_sql, fetch=True)

        if result:
            for row in result if isinstance(result, list) else [result]:
                keys = row[0] if isinstance(row, (list, tuple)) else row.get("keys", [])
                if keys:
                    for key in keys:
                        if key not in seen_keys:
                            seen_keys.add(key)
                            children.append(
                                ColumnNode(
                                    name=key,
                                    path=f"{json_column}.{key}",
                                    type="string",  # Default to string
                                    children=[],
                                )
                            )
    except Exception as e:
        logger.warning("Could not extract JSON fields from %s: %s", json_column, e)

    return sorted(children, key=lambda x: x.name)


def _map_db_type(db_type: str) -> str:
    """Map DuckDB types to simple type names."""
    db_type = db_type.upper()
    if "INT" in db_type or "BIGINT" in db_type:
        return "number"
    if "FLOAT" in db_type or "DOUBLE" in db_type or "DECIMAL" in db_type:
        return "number"
    if "BOOL" in db_type:
        return "boolean"
    if "JSON" in db_type or "STRUCT" in db_type or "MAP" in db_type:
        return "object"
    if "LIST" in db_type or "ARRAY" in db_type:
        return "array"
    return "string"


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
        logger.exception("Error listing transformers: %s", e)
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


def _extract_widget_label(name: str, plugin_class: type) -> str:
    """Extract a human-readable label from a widget class."""
    # Try to get label from docstring's first line
    if plugin_class.__doc__:
        first_line = plugin_class.__doc__.strip().split("\n")[0]
        # Clean up common patterns like "Widget to display a..."
        if first_line.lower().startswith("widget to display"):
            label = first_line[17:].strip()  # Remove "Widget to display"
            if label.startswith("a "):
                label = label[2:]
            elif label.startswith("an "):
                label = label[3:]
            # Capitalize first letter
            label = label[0].upper() + label[1:] if label else name
            # Remove trailing period
            label = label.rstrip(".")
            return label
    # Fallback: convert snake_case to Title Case
    return name.replace("_", " ").title()


def _extract_widget_description(name: str, plugin_class: type) -> str:
    """Extract description from a widget class."""
    if plugin_class.__doc__:
        return plugin_class.__doc__.strip().split("\n")[0].rstrip(".")
    return f"Widget {name}"


@router.get("/widgets", response_model=list[WidgetInfo])
async def list_widgets():
    """List all available widget plugins with labels and descriptions."""
    try:
        plugins = PluginRegistry.get_plugins_by_type(PluginType.WIDGET)
        result = []
        for name, plugin_class in sorted(plugins.items()):
            result.append(
                WidgetInfo(
                    name=name,
                    label=_extract_widget_label(name, plugin_class),
                    description=_extract_widget_description(name, plugin_class),
                )
            )
        return result
    except Exception as e:
        logger.exception("Error listing widgets: %s", e)
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
    transform_config = load_transform_config(work_dir)

    # Find or create group
    group_config = find_transform_group(transform_config, group_by)
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

    save_transform_config(work_dir, transform_config)

    # --- Update export.yml ---
    export_config = load_export_config(work_dir)

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

    save_export_config(work_dir, export_config)

    return SaveRecipeResponse(
        success=True,
        message=f"Widget '{recipe.widget_id}' saved successfully",
        widget_id=recipe.widget_id,
        data_source_id=data_source_id,
    )


class ReorderWidgetsRequest(BaseModel):
    """Request to reorder widgets in a group."""

    widget_ids: list[str] = Field(..., description="Ordered list of widget IDs")


def _resolve_export_widget_id(group_by: str, widget: dict[str, Any]) -> str | None:
    data_source = widget.get("data_source")
    if data_source:
        return str(data_source)
    if widget.get("plugin") == "hierarchical_nav_widget":
        return f"{group_by}_hierarchical_nav_widget"
    return None


@router.post("/{group_by}/reorder")
async def reorder_widgets(group_by: str, request: ReorderWidgetsRequest):
    """
    Reorder widgets in export.yml for a group.

    The widget_ids list defines the new order. Widgets not in the list
    will be placed at the end in their original order.
    Also updates layout.order property to ensure consistency with LayoutEditor.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)

    # Load export config
    export_config = load_export_config(work_dir)

    # Find the group
    for export in export_config.get("exports", []):
        for group in export.get("groups", []):
            if group.get("group_by") == group_by:
                widgets = group.get("widgets", [])

                # Create a map of frontend widget id -> widget
                widget_map = {}
                for widget in widgets:
                    widget_id = _resolve_export_widget_id(group_by, widget)
                    if widget_id:
                        widget_map[widget_id] = widget

                # Reorder based on request
                new_widgets = []
                order_idx = 0
                for widget_id in request.widget_ids:
                    if widget_id in widget_map:
                        widget = widget_map[widget_id]
                        # Update layout.order to match new position
                        if "layout" not in widget:
                            widget["layout"] = {}
                        widget["layout"]["order"] = order_idx
                        new_widgets.append(widget)
                        del widget_map[widget_id]
                        order_idx += 1

                # Add any remaining widgets not in the list
                for widget in widget_map.values():
                    if "layout" not in widget:
                        widget["layout"] = {}
                    widget["layout"]["order"] = order_idx
                    new_widgets.append(widget)
                    order_idx += 1

                group["widgets"] = new_widgets

    save_export_config(work_dir, export_config)

    return {"success": True, "message": f"Widgets reordered for group '{group_by}'"}


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
    transform_config = load_transform_config(work_dir)
    group_config = find_transform_group(transform_config, group_by)

    if group_config and "widgets_data" in group_config:
        if widget_id in group_config["widgets_data"]:
            del group_config["widgets_data"][widget_id]
            save_transform_config(work_dir, transform_config)

    # --- Update export.yml ---
    export_config = load_export_config(work_dir)

    for export in export_config.get("exports", []):
        for group in export.get("groups", []):
            if group.get("group_by") == group_by:
                widgets = group.get("widgets", [])
                group["widgets"] = [
                    w for w in widgets if w.get("data_source") != widget_id
                ]

    save_export_config(work_dir, export_config)

    return {"success": True, "message": f"Widget '{widget_id}' deleted"}


# =============================================================================
# PREVIEW ENDPOINT
# =============================================================================


class PreviewRecipeRequest(BaseModel):
    """Request to preview a widget recipe without saving."""

    group_by: str
    recipe: WidgetRecipe


@router.post("/preview", response_class=HTMLResponse)
async def preview_recipe(request: PreviewRecipeRequest):
    """
    Preview a widget recipe without saving.

    Délègue au moteur de preview unifié via config inline.
    """
    from niamoto.gui.api.services.preview_engine.engine import get_preview_engine
    from niamoto.gui.api.services.preview_engine.models import PreviewRequest
    from starlette.concurrency import run_in_threadpool

    engine = get_preview_engine()
    if engine is None:
        return HTMLResponse(
            content=wrap_html_response(error_html("Projet Niamoto non configuré")),
            status_code=500,
        )

    recipe = request.recipe
    widget_title = recipe.widget.title or recipe.widget_id.replace("_", " ").title()

    req = PreviewRequest(
        group_by=request.group_by,
        inline={
            "transformer_plugin": recipe.transformer.plugin,
            "transformer_params": recipe.transformer.params,
            "widget_plugin": recipe.widget.plugin,
            "widget_params": recipe.widget.params,
            "widget_title": widget_title,
        },
    )

    try:
        result = await run_in_threadpool(engine.render, req)
        return HTMLResponse(
            content=result.html,
            headers={
                "ETag": f'"{result.etag}"',
                "Cache-Control": "no-cache",
            },
        )
    except Exception as e:
        logger.exception("Error previewing recipe: %s", e)
        return HTMLResponse(
            content=wrap_html_response(error_html(str(e))),
            status_code=500,
        )
