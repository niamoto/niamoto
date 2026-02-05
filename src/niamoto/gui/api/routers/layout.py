"""
API routes for layout management.

Provides endpoints for:
- Getting widget layout for a group
- Updating widget layout (order, colspan, title)
- Previewing individual widgets
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from niamoto.gui.api.context import get_working_directory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/layout", tags=["layout"])


# =============================================================================
# MODELS
# =============================================================================


class WidgetLayoutInfo(BaseModel):
    """Layout information for a single widget."""

    index: int = Field(..., description="Original index in export.yml")
    plugin: str = Field(..., description="Widget plugin name")
    title: str = Field(..., description="Widget title")
    description: Optional[str] = Field(None, description="Widget description")
    data_source: str = Field(..., description="Data source key")
    colspan: int = Field(default=1, ge=1, le=2, description="Column span (1 or 2)")
    order: int = Field(..., description="Display order")
    is_navigation: bool = Field(
        default=False, description="Is this a navigation widget"
    )


class NavigationWidgetInfo(BaseModel):
    """Information about the navigation widget."""

    plugin: str = Field(default="hierarchical_nav_widget")
    title: str
    params: Dict[str, Any] = Field(default_factory=dict)
    is_hierarchical: bool = Field(default=False)


class LayoutResponse(BaseModel):
    """Response for layout endpoint."""

    group_by: str
    widgets: List[WidgetLayoutInfo]
    navigation_widget: Optional[NavigationWidgetInfo] = None
    total_widgets: int


class WidgetLayoutUpdate(BaseModel):
    """Update for a single widget layout."""

    index: int = Field(..., description="Original widget index")
    title: Optional[str] = Field(None, description="New title (if changed)")
    description: Optional[str] = Field(None, description="New description")
    colspan: Optional[int] = Field(None, ge=1, le=2, description="New colspan")
    order: int = Field(..., description="New display order")


class LayoutUpdateRequest(BaseModel):
    """Request to update layout."""

    widgets: List[WidgetLayoutUpdate] = Field(..., description="Widget layout updates")


class LayoutUpdateResponse(BaseModel):
    """Response after updating layout."""

    success: bool
    message: str
    widgets_updated: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _load_export_config(work_dir: Path) -> Dict[str, Any]:
    """Load and parse export.yml configuration."""
    export_path = work_dir / "config" / "export.yml"
    if not export_path.exists():
        raise HTTPException(
            status_code=404,
            detail="export.yml not found. Please configure your exports first.",
        )

    with open(export_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_export_config(work_dir: Path, config: Dict[str, Any]) -> None:
    """Save export.yml configuration."""
    export_path = work_dir / "config" / "export.yml"

    with open(export_path, "w", encoding="utf-8") as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


def _find_group_config(
    export_config: Dict[str, Any], group_by: str
) -> Optional[Dict[str, Any]]:
    """Find group configuration in export.yml."""
    exports = export_config.get("exports", [])

    if not isinstance(exports, list):
        return None

    for export in exports:
        if not isinstance(export, dict):
            continue

        groups = export.get("groups", [])
        if not isinstance(groups, list):
            continue

        for group in groups:
            if isinstance(group, dict) and group.get("group_by") == group_by:
                return group

    return None


def _get_group_and_export_index(
    export_config: Dict[str, Any], group_by: str
) -> Optional[tuple]:
    """Get group config along with its export and group indices."""
    exports = export_config.get("exports", [])

    if not isinstance(exports, list):
        return None

    for export_idx, export in enumerate(exports):
        if not isinstance(export, dict):
            continue

        groups = export.get("groups", [])
        if not isinstance(groups, list):
            continue

        for group_idx, group in enumerate(groups):
            if isinstance(group, dict) and group.get("group_by") == group_by:
                return (export_idx, group_idx, group)

    return None


def _extract_widget_layout(widget: Dict[str, Any], index: int) -> WidgetLayoutInfo:
    """Extract layout information from a widget config."""
    plugin = widget.get("plugin", "unknown")
    is_navigation = plugin == "hierarchical_nav_widget"

    # Get layout info (or use defaults)
    layout = widget.get("layout", {})

    return WidgetLayoutInfo(
        index=index,
        plugin=plugin,
        title=widget.get("title", f"Widget {index}"),
        description=widget.get("description"),
        data_source=widget.get("data_source", ""),
        colspan=layout.get("colspan", 1),
        order=layout.get("order", index),
        is_navigation=is_navigation,
    )


def _extract_navigation_widget(
    widgets: List[Dict[str, Any]],
) -> Optional[NavigationWidgetInfo]:
    """Extract navigation widget info if present."""
    for widget in widgets:
        if widget.get("plugin") == "hierarchical_nav_widget":
            params = widget.get("params", {})
            is_hierarchical = bool(params.get("lft_field") and params.get("rght_field"))
            return NavigationWidgetInfo(
                plugin="hierarchical_nav_widget",
                title=widget.get("title", "Navigation"),
                params=params,
                is_hierarchical=is_hierarchical,
            )
    return None


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/{group_by}", response_model=LayoutResponse)
async def get_layout(group_by: str):
    """
    Get the widget layout for a group.

    Returns all widgets with their layout information (order, colspan)
    and identifies the navigation widget if present.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)

    try:
        export_config = _load_export_config(work_dir)
        group_config = _find_group_config(export_config, group_by)

        if not group_config:
            raise HTTPException(
                status_code=404,
                detail=f"Group '{group_by}' not found in export.yml",
            )

        widgets = group_config.get("widgets", [])

        # Extract widget layouts
        widget_layouts = []
        for idx, widget in enumerate(widgets):
            if isinstance(widget, dict):
                widget_layouts.append(_extract_widget_layout(widget, idx))

        # Sort by order
        widget_layouts.sort(key=lambda w: w.order)

        # Extract navigation widget
        navigation_widget = _extract_navigation_widget(widgets)

        return LayoutResponse(
            group_by=group_by,
            widgets=widget_layouts,
            navigation_widget=navigation_widget,
            total_widgets=len(widget_layouts),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting layout for group '{group_by}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{group_by}", response_model=LayoutUpdateResponse)
async def update_layout(group_by: str, request: LayoutUpdateRequest):
    """
    Update the widget layout for a group.

    Updates order, colspan, and optionally title/description for widgets.
    Changes are saved back to export.yml.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)

    try:
        export_config = _load_export_config(work_dir)
        result = _get_group_and_export_index(export_config, group_by)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Group '{group_by}' not found in export.yml",
            )

        export_idx, group_idx, group_config = result
        widgets = group_config.get("widgets", [])

        # Apply updates
        widgets_updated = 0
        for update in request.widgets:
            if 0 <= update.index < len(widgets):
                widget = widgets[update.index]

                # Update title if provided
                if update.title is not None:
                    widget["title"] = update.title

                # Update description if provided
                if update.description is not None:
                    widget["description"] = update.description

                # Update or create layout section
                if "layout" not in widget:
                    widget["layout"] = {}

                widget["layout"]["order"] = update.order

                if update.colspan is not None:
                    widget["layout"]["colspan"] = update.colspan

                widgets_updated += 1

        # Reorder widgets array to match the order property
        # This ensures consistency between LayoutEditor and ConfiguredWidgetsList
        widgets.sort(key=lambda w: w.get("layout", {}).get("order", 999))

        # Save updated config
        export_config["exports"][export_idx]["groups"][group_idx]["widgets"] = widgets
        _save_export_config(work_dir, export_config)

        return LayoutUpdateResponse(
            success=True,
            message=f"Layout updated for group '{group_by}'",
            widgets_updated=widgets_updated,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating layout for group '{group_by}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{group_by}/preview/{widget_index}", response_class=HTMLResponse)
async def preview_widget(
    group_by: str,
    widget_index: int,
    entity_id: Optional[str] = Query(
        default=None, description="Entity ID for preview (optional)"
    ),
):
    """
    Generate a live preview of a specific widget.

    Renders the widget using sample data from the database.
    """

    work_dir = get_working_directory()
    if not work_dir:
        return HTMLResponse(
            content=_wrap_html_response(
                "<p class='error'>Working directory not configured</p>"
            ),
            status_code=500,
        )

    work_dir = Path(work_dir)

    try:
        export_config = _load_export_config(work_dir)
        group_config = _find_group_config(export_config, group_by)

        if not group_config:
            return HTMLResponse(
                content=_wrap_html_response(
                    f"<p class='error'>Group '{group_by}' not found</p>"
                ),
                status_code=404,
            )

        widgets = group_config.get("widgets", [])

        if widget_index < 0 or widget_index >= len(widgets):
            return HTMLResponse(
                content=_wrap_html_response(
                    f"<p class='error'>Widget index {widget_index} out of range</p>"
                ),
                status_code=404,
            )

        widget_config = widgets[widget_index]
        plugin_name = widget_config.get("plugin", "")
        data_source = widget_config.get("data_source", "")
        _title = widget_config.get("title", f"Widget {widget_index}")  # noqa: F841
        params = widget_config.get("params", {})

        # Special handling for navigation widget
        if plugin_name == "hierarchical_nav_widget":
            from niamoto.gui.api.routers.templates import _preview_navigation_widget

            referential = params.get("referential_data", group_by)
            return await _preview_navigation_widget(referential)

        # Use the same preview system as the gallery (templates.py)
        # This generates data on-the-fly from occurrences instead of requiring stats table
        from niamoto.gui.api.routers.templates import preview_template

        # The data_source is the template_id used in transform.yml
        # e.g., "geo_pt_geospatial_extractor_interactive_map"
        # Pass entity_id if provided to show data for a specific entity
        # Note: source=None must be passed explicitly because Query() defaults
        # don't work when calling the function directly (not via HTTP)
        return await preview_template(
            data_source, group_by=group_by, entity_id=entity_id, source=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error previewing widget: {e}")
        return HTMLResponse(
            content=_wrap_html_response(f"<p class='error'>Erreur: {str(e)}</p>"),
            status_code=500,
        )


def _wrap_html_response(content: str, title: str = "Preview") -> str:
    """Wrap widget HTML in a complete HTML document."""
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
    <script src="/api/site/assets/js/vendor/plotly/3.0.1_plotly.min.js"></script>
</head>
<body>
{content}
</body>
</html>"""


@router.get("/{group_by}/groups")
async def list_available_groups():
    """
    List all available groups in export.yml.

    Returns a list of group names that can be configured.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)

    try:
        export_config = _load_export_config(work_dir)
        exports = export_config.get("exports", [])

        groups = []
        if isinstance(exports, list):
            for export in exports:
                if isinstance(export, dict):
                    export_groups = export.get("groups", [])
                    if isinstance(export_groups, list):
                        for group in export_groups:
                            if isinstance(group, dict):
                                group_by = group.get("group_by")
                                if group_by:
                                    widget_count = len(group.get("widgets", []))
                                    groups.append(
                                        {
                                            "name": group_by,
                                            "widget_count": widget_count,
                                        }
                                    )

        return {"groups": groups, "total": len(groups)}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error listing groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RepresentativeEntity(BaseModel):
    """A representative entity for preview."""

    id: str = Field(..., description="Entity identifier (value)")
    name: str = Field(..., description="Display name")
    count: int = Field(..., description="Number of occurrences")


class RepresentativesResponse(BaseModel):
    """Response for representatives endpoint."""

    group_by: str
    default_entity: Optional[RepresentativeEntity] = None
    entities: List[RepresentativeEntity]
    total: int


@router.get("/{group_by}/representatives", response_model=RepresentativesResponse)
async def get_representatives(
    group_by: str, limit: int = Query(default=20, ge=1, le=100)
):
    """
    Get representative entities for preview selection.

    For hierarchical references (like taxons), returns top entities from each
    hierarchy level (family, genus, species, etc.) to allow testing previews
    at different granularities.
    """
    import pandas as pd
    from niamoto.common.database import Database
    from niamoto.gui.api.context import get_database_path

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    db = Database(str(db_path), read_only=True)

    try:
        # Entity table is entity_{group_by}
        entity_table = f"entity_{group_by}"

        if not db.has_table(entity_table):
            return RepresentativesResponse(
                group_by=group_by,
                entities=[],
                total=0,
            )

        # Check if we have occurrences to count
        has_occurrences = db.has_table("dataset_occurrences")

        entities = []

        # Build query based on group_by type
        if group_by == "taxons" and has_occurrences:
            # For hierarchical taxons, get top entities per rank level
            # Different join strategies based on rank:
            # - family/genus: join via rank_value matching the column in occurrences
            # - species/subspecies: join via taxons_id -> id_taxonref

            # First, get the distinct rank names
            ranks_query = f"""
                SELECT DISTINCT rank_name, level
                FROM {entity_table}
                WHERE rank_name IS NOT NULL
                ORDER BY level
            """
            ranks_result = pd.read_sql(ranks_query, db.engine)
            ranks = ranks_result["rank_name"].tolist()

            # Get top entities per rank level (distribute limit across ranks)
            per_rank_limit = max(2, limit // max(len(ranks), 1))

            for rank in ranks:
                # For family and genus, join via rank_value column
                if rank in ("family", "genus"):
                    query = f"""
                        SELECT
                            e.id as id,
                            e.full_name as name,
                            e.rank_name as rank,
                            COUNT(o.id) as count
                        FROM {entity_table} e
                        LEFT JOIN dataset_occurrences o ON o.{rank} = e.rank_value
                        WHERE e.full_name IS NOT NULL AND e.full_name != ''
                          AND e.rank_name = '{rank}'
                        GROUP BY e.id, e.full_name, e.rank_name
                        HAVING count > 0
                        ORDER BY count DESC
                        LIMIT {per_rank_limit}
                    """
                else:
                    # For species/subspecies, join via taxons_id
                    query = f"""
                        SELECT
                            e.id as id,
                            e.full_name as name,
                            e.rank_name as rank,
                            COUNT(o.id) as count
                        FROM {entity_table} e
                        LEFT JOIN dataset_occurrences o ON o.id_taxonref = e.taxons_id
                        WHERE e.full_name IS NOT NULL AND e.full_name != ''
                          AND e.rank_name = '{rank}'
                          AND e.taxons_id IS NOT NULL
                        GROUP BY e.id, e.full_name, e.rank_name
                        HAVING count > 0
                        ORDER BY count DESC
                        LIMIT {per_rank_limit}
                    """

                result = pd.read_sql(query, db.engine)

                for _, row in result.iterrows():
                    # Include rank in display name for clarity
                    display_name = f"[{row['rank'].capitalize()}] {row['name']}"
                    entities.append(
                        RepresentativeEntity(
                            id=str(row["id"]),
                            name=display_name,
                            count=int(row["count"]),
                        )
                    )

        else:
            # Generic approach for non-hierarchical references (plots, shapes, etc.)
            # Read import.yml to get schema info
            import_path = work_dir / "config" / "import.yml"
            ref_config = {}
            if import_path.exists():
                try:
                    with open(import_path, "r", encoding="utf-8") as f:
                        import_config = yaml.safe_load(f) or {}
                    references = import_config.get("entities", {}).get("references", {})
                    ref_config = references.get(group_by, {})
                except Exception:
                    pass

            # Get schema info
            schema = ref_config.get("schema", {})
            id_field = schema.get("id_field", "id")

            # Get entity columns to detect name field
            columns_df = pd.read_sql(f"SELECT * FROM {entity_table} LIMIT 0", db.engine)
            columns = columns_df.columns.tolist()

            # Detect name field
            name_candidates = ["full_name", "name", "plot", "label", "title"]
            name_field = next((c for c in name_candidates if c in columns), None)
            if not name_field:
                name_field = next((c for c in columns if "name" in c.lower()), id_field)

            # For spatial references (shapes), filter out category rows
            kind = ref_config.get("kind")
            where_clause = ""
            if kind == "spatial" and "entity_type" in columns:
                # Only show actual shapes, not category rows
                where_clause = "WHERE entity_type = 'shape'"

            # Build query
            query = f"""
                SELECT
                    "{id_field}" as id,
                    COALESCE("{name_field}", CAST("{id_field}" AS VARCHAR)) as name
                FROM {entity_table}
                {where_clause}
                ORDER BY "{name_field}"
                LIMIT {limit}
            """
            result = pd.read_sql(query, db.engine)
            for _, row in result.iterrows():
                entities.append(
                    RepresentativeEntity(
                        id=str(row["id"]),
                        name=str(row["name"]),
                        count=0,  # Pre-aggregated data, not from occurrences
                    )
                )

        default_entity = entities[0] if entities else None

        return RepresentativesResponse(
            group_by=group_by,
            default_entity=default_entity,
            entities=entities,
            total=len(entities),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting representatives for '{group_by}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close_db_session()
