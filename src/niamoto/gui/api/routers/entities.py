"""Entities API endpoints for accessing entity data with transformations and EntityRegistry."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import json
import yaml

from niamoto.common.database import Database
from niamoto.common.config import Config
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.exceptions import PluginNotFoundError
from niamoto.core.imports.registry import EntityRegistry

router = APIRouter()


class EntitySummary(BaseModel):
    """Summary information about an entity."""

    id: int
    name: str
    display_name: Optional[str] = None


class EntityDetail(BaseModel):
    """Detailed entity information including widgets_data."""

    id: int
    name: str
    group_by: str
    widgets_data: Dict[str, Any]


class TransformationPreview(BaseModel):
    """Preview of a specific transformation and its widget."""

    entity_id: int
    entity_name: str
    group_by: str
    transformation_key: str
    transformation_data: Dict[str, Any]
    widget_plugin: Optional[str] = None


class EntityInfo(BaseModel):
    """Information about a registered entity from EntityRegistry."""

    name: str
    kind: str  # 'reference' or 'dataset'
    entity_type: str  # 'flat', 'nested', 'spatial' for references


class EntityListResponse(BaseModel):
    """Response with available entities grouped by kind."""

    datasets: List[str] = []
    references: List[str] = []
    all: List[EntityInfo] = []


@router.get("/available", response_model=EntityListResponse)
async def get_available_entities(
    kind: Optional[str] = Query(
        None, description="Filter by kind: 'dataset' or 'reference'"
    ),
):
    """
    Get list of available entities from EntityRegistry.

    This endpoint is used by entity-select widgets in plugin forms to
    dynamically populate entity dropdowns.

    Args:
        kind: Optional filter - 'dataset' or 'reference'

    Returns:
        EntityListResponse with entities grouped by kind
    """
    try:
        # Get config to access EntityRegistry
        config = Config()

        # Initialize EntityRegistry with config
        registry = EntityRegistry(config)

        # Get all entities
        all_entities = registry.list_all()

        datasets = []
        references = []
        all_entity_info = []

        for entity in all_entities:
            entity_info = EntityInfo(
                name=entity.name,
                kind=entity.kind.value,
                entity_type=getattr(entity, "entity_type", entity.kind.value),
            )

            all_entity_info.append(entity_info)

            if entity.kind.value == "dataset":
                datasets.append(entity.name)
            else:  # reference
                references.append(entity.name)

        # Apply filter if requested
        if kind:
            if kind.lower() == "dataset":
                references = []
            elif kind.lower() == "reference":
                datasets = []

        return EntityListResponse(
            datasets=sorted(datasets),
            references=sorted(references),
            all=sorted(all_entity_info, key=lambda x: x.name),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading entities from EntityRegistry: {str(e)}",
        )


@router.get("/entities/{group_by}", response_model=List[EntitySummary])
async def list_entities(group_by: str, limit: Optional[int] = None):
    """
    List entities for a specific group_by (taxon, plot, shape).

    Args:
        group_by: Entity type (taxon, plot, or shape)
        limit: Maximum number of entities to return

    Returns:
        List of entity summaries
    """
    db_path = get_database_path()
    if not db_path or not db_path.exists():
        raise HTTPException(status_code=500, detail="Database not found")

    # Validate group_by
    valid_groups = ["taxon", "plot", "shape"]
    if group_by not in valid_groups:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid group_by. Must be one of: {', '.join(valid_groups)}",
        )

    # Map group_by to ID column name
    id_column = f"{group_by}_id"

    db = Database(db_path)

    try:
        with db.session() as session:
            # Query the transformed table to get entities with general_info
            if limit is not None:
                query = text(f"""
                    SELECT {id_column} as id,
                           json_extract(general_info, '$.name.value') as name
                    FROM {group_by}
                    WHERE general_info IS NOT NULL
                    ORDER BY name
                    LIMIT :limit
                """)
                result = session.execute(query, {"limit": limit})
            else:
                # No limit - return all entities
                query = text(f"""
                    SELECT {id_column} as id,
                           json_extract(general_info, '$.name.value') as name
                    FROM {group_by}
                    WHERE general_info IS NOT NULL
                    ORDER BY name
                """)
                result = session.execute(query)

            entities = []

            for row in result:
                entities.append(
                    EntitySummary(
                        id=row.id,
                        name=row.name or f"{group_by}_{row.id}",
                        display_name=row.name or f"{group_by}_{row.id}",
                    )
                )

            return entities

    except OperationalError as e:
        # Table doesn't exist yet (database not initialized or no import done)
        if "no such table" in str(e).lower():
            return []
        raise HTTPException(
            status_code=500, detail=f"Error querying {group_by} table: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error querying {group_by} table: {str(e)}"
        )


@router.get("/entity/{group_by}/{entity_id}", response_model=EntityDetail)
async def get_entity_detail(group_by: str, entity_id: int):
    """
    Get detailed information about a specific entity including all widgets_data.

    Args:
        group_by: Entity type (taxon, plot, or shape)
        entity_id: ID of the entity

    Returns:
        Entity details with widgets_data
    """
    db_path = get_database_path()
    if not db_path or not db_path.exists():
        raise HTTPException(status_code=500, detail="Database not found")

    # Validate group_by
    valid_groups = ["taxon", "plot", "shape"]
    if group_by not in valid_groups:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid group_by. Must be one of: {', '.join(valid_groups)}",
        )

    # Map group_by to ID column name
    id_column = f"{group_by}_id"

    db = Database(db_path)

    try:
        with db.session() as session:
            # First, get column names to know which JSON columns exist
            columns_query = text(f"PRAGMA table_info({group_by})")
            columns_result = session.execute(columns_query)

            # Get all column names except the ID column
            json_columns = []
            for col in columns_result:
                col_name = col[1]  # column name is at index 1
                col_type = col[2]  # column type is at index 2
                if col_name != id_column and col_type == "JSON":
                    json_columns.append(col_name)

            # Build query to select all columns
            columns_str = ", ".join(
                [id_column]
                + ["json_extract(general_info, '$.name.value') as name"]
                + json_columns
            )
            query = text(f"""
                SELECT {columns_str}
                FROM {group_by}
                WHERE {id_column} = :entity_id
            """)

            result = session.execute(query, {"entity_id": entity_id}).fetchone()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Entity {entity_id} not found in {group_by} table",
                )

            # Build widgets_data from all JSON columns
            widgets_data = {}
            result_dict = result._mapping

            for col_name in json_columns:
                if col_name in result_dict and result_dict[col_name]:
                    try:
                        widgets_data[col_name] = json.loads(result_dict[col_name])
                    except (json.JSONDecodeError, TypeError):
                        # If it's already a dict or can't be parsed, use as is
                        widgets_data[col_name] = result_dict[col_name]

            return EntityDetail(
                id=result_dict[id_column],
                name=result_dict.get("name") or f"{group_by}_{entity_id}",
                group_by=group_by,
                widgets_data=widgets_data,
            )

    except HTTPException:
        raise
    except OperationalError as e:
        # Table doesn't exist yet (database not initialized or no import done)
        if "no such table" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Table '{group_by}' not found. Please run import first.",
            )
        raise HTTPException(status_code=500, detail=f"Error querying entity: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying entity: {str(e)}")


@router.get(
    "/transformation/{group_by}/{entity_id}/{transform_key}",
    response_model=TransformationPreview,
)
async def get_transformation_preview(group_by: str, entity_id: int, transform_key: str):
    """
    Get preview of a specific transformation for an entity.

    Args:
        group_by: Entity type (taxon, plot, or shape)
        entity_id: ID of the entity
        transform_key: Key of the transformation (e.g., 'dbh_distribution')

    Returns:
        Transformation preview with data
    """
    # Get full entity detail
    entity = await get_entity_detail(group_by, entity_id)

    # Check if transformation exists
    if transform_key not in entity.widgets_data:
        raise HTTPException(
            status_code=404,
            detail=f"Transformation '{transform_key}' not found for entity {entity_id}",
        )

    transformation_data = entity.widgets_data[transform_key]

    # Try to determine widget plugin from export config (if available)
    # For now, return None - frontend can determine from export config

    return TransformationPreview(
        entity_id=entity.id,
        entity_name=entity.name,
        group_by=group_by,
        transformation_key=transform_key,
        transformation_data=transformation_data,
        widget_plugin=None,  # Could be enhanced later
    )


@router.get(
    "/render-widget/{group_by}/{entity_id}/{transform_key}", response_class=HTMLResponse
)
async def render_widget(group_by: str, entity_id: int, transform_key: str):
    """
    Render a widget HTML for a specific transformation.

    Args:
        group_by: Entity type (taxon, plot, or shape)
        entity_id: ID of the entity
        transform_key: Key of the transformation (e.g., 'dbh_distribution')

    Returns:
        HTML content of the rendered widget
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not found")

    # Get entity data
    entity = await get_entity_detail(group_by, entity_id)

    # Check if transformation exists
    if transform_key not in entity.widgets_data:
        raise HTTPException(
            status_code=404,
            detail=f"Transformation '{transform_key}' not found for entity {entity_id}",
        )

    transformation_data = entity.widgets_data[transform_key]

    # Load export.yml to find widget configuration
    export_config_path = work_dir / "config" / "export.yml"
    if not export_config_path.exists():
        raise HTTPException(status_code=500, detail="Export configuration not found")

    try:
        with open(export_config_path, "r", encoding="utf-8") as f:
            export_config = yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading export configuration: {str(e)}"
        )

    # Find the widget config that matches this transformation
    widget_config = None
    widget_plugin_id = None

    exports = export_config.get("exports", [])
    for export in exports:
        groups = export.get("groups", [])
        for group in groups:
            if group.get("group_by") == group_by:
                widgets = group.get("widgets", [])
                for widget in widgets:
                    if widget.get("data_source") == transform_key:
                        widget_config = widget
                        widget_plugin_id = widget.get("plugin")
                        break
            if widget_config:
                break
        if widget_config:
            break

    if not widget_config or not widget_plugin_id:
        return HTMLResponse(
            content=f"<p class='info'>No widget configured for transformation '{transform_key}'</p>"
        )

    # Get the widget plugin from registry
    try:
        plugin_class = PluginRegistry.get_plugin(widget_plugin_id, PluginType.WIDGET)
    except PluginNotFoundError:
        return HTMLResponse(
            content=f"<p class='error'>Widget plugin '{widget_plugin_id}' not found in registry</p>"
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<p class='error'>Error loading plugin: {str(e)}</p>"
        )

    try:
        # Get database instance for the plugin
        db_path = get_database_path()
        if not db_path or not db_path.exists():
            return HTMLResponse(content="<p class='error'>Database not found</p>")

        db = Database(db_path)

        # Instantiate the plugin with database
        plugin_instance = plugin_class(db=db)

        # Get widget parameters from config
        widget_params = widget_config.get("params", {})

        # Validate params using plugin's schema
        validated_params = widget_params
        if hasattr(plugin_instance, "param_schema") and plugin_instance.param_schema:
            try:
                validated_params = plugin_instance.param_schema.model_validate(
                    widget_params
                )
            except Exception as e:
                return HTMLResponse(
                    content=f"<p class='error'>Invalid widget parameters: {str(e)}</p>"
                )

        # Render the widget with the transformation data
        widget_html = plugin_instance.render(transformation_data, validated_params)

        # Get widget dependencies (e.g., Plotly CDN)
        dependencies = (
            plugin_instance.get_dependencies()
            if hasattr(plugin_instance, "get_dependencies")
            else set()
        )

        # Replace local paths with CDN
        cdn_dependencies = set()
        for dep in dependencies:
            if "plotly" in dep.lower():
                # Use public CDN instead of local file
                cdn_dependencies.add("https://cdn.plot.ly/plotly-3.0.0.min.js")
            elif "topojson" in dep.lower():
                # Use public CDN for TopoJSON
                cdn_dependencies.add(
                    "https://cdn.jsdelivr.net/npm/topojson@3.0.0/dist/topojson.min.js"
                )
            else:
                cdn_dependencies.add(dep)

        # Wrap the widget HTML in a complete HTML page with dependencies
        dependency_scripts = "\n".join(
            [f'<script src="{dep}"></script>' for dep in cdn_dependencies]
        )

        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: sans-serif;
        }}
        .plotly-graph-div {{
            width: 100% !important;
            height: 100% !important;
        }}
    </style>
    {dependency_scripts}
</head>
<body>
    {widget_html}
</body>
</html>"""

        return HTMLResponse(content=full_html)

    except Exception as e:
        return HTMLResponse(
            content=f"<p class='error'>Error rendering widget: {str(e)}</p>"
        )
