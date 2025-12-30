"""
API routes for widget templates.

Provides endpoints for:
- Listing available templates by entity type
- Getting template suggestions based on data analysis
- Generating transform.yml configuration from selected templates
- Live preview of widgets on sample data
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from niamoto.core.imports.template_suggester import (
    TemplateSuggester,
    TemplateSuggestion,
)
from niamoto.core.imports.class_object_suggester import suggest_widgets_for_source
from niamoto.core.imports.widget_generator import WidgetGenerator
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.matching.matcher import SmartMatcher
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.common.database import Database

logger = logging.getLogger(__name__)

# Static category definitions (widget categories are predefined, not data-driven)
WIDGET_CATEGORIES = {
    "navigation": {
        "name": "navigation",
        "label": "Navigation",
        "description": "Widgets de navigation hiérarchique ou liste",
    },
    "info": {
        "name": "info",
        "label": "Informations",
        "description": "Widgets d'information générale",
    },
    "chart": {
        "name": "chart",
        "label": "Graphiques",
        "description": "Histogrammes et barres",
    },
    "gauge": {
        "name": "gauge",
        "label": "Jauges",
        "description": "Indicateurs de valeurs",
    },
    "donut": {
        "name": "donut",
        "label": "Donuts",
        "description": "Graphiques circulaires",
    },
    "map": {
        "name": "map",
        "label": "Cartes",
        "description": "Visualisations géographiques",
    },
}


# Note: Transformer-to-widget mapping is now automatic via SmartMatcher
# using output_structure/compatible_structures declared on plugins

router = APIRouter(prefix="/templates", tags=["templates"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class TemplateInfo(BaseModel):
    """Basic template information."""

    id: str
    name: str
    description: str
    plugin: str
    category: str
    icon: str
    is_recommended: bool
    has_auto_detect: bool


class TemplateSuggestionResponse(BaseModel):
    """A template suggestion with confidence."""

    template_id: str
    name: str
    description: str
    plugin: str
    category: str
    icon: str
    confidence: float
    source: str  # "auto" | "template" | "generic"
    source_name: str  # Actual source dataset name (from import.yml)
    matched_column: Optional[str] = None
    match_reason: Optional[str] = None
    is_recommended: bool
    config: Dict[str, Any]
    alternatives: List[str] = []  # Alternative template IDs


class TemplatesListResponse(BaseModel):
    """Response for listing templates."""

    templates: List[TemplateInfo]
    categories: List[str]
    total: int


class SuggestionsResponse(BaseModel):
    """Response for template suggestions."""

    suggestions: List[TemplateSuggestionResponse]
    entity_type: str
    columns_analyzed: int
    total_suggestions: int


class SelectedTemplate(BaseModel):
    """A selected template with its configuration."""

    template_id: str
    plugin: str  # Transformer plugin name
    config: Dict[str, Any] = {}


class GenerateConfigRequest(BaseModel):
    """Request to generate transform config."""

    templates: List[SelectedTemplate] = Field(
        ..., description="List of selected templates with configs"
    )
    group_by: str = Field(
        ..., description="Reference name for group_by (from import.yml)"
    )
    reference_kind: str = Field(
        default="flat", description="Reference kind: hierarchical | flat | spatial"
    )


class GenerateConfigResponse(BaseModel):
    """Response with generated config."""

    group_by: str
    sources: List[Dict[str, Any]]
    widgets_data: Dict[str, Any]


# =============================================================================
# ENDPOINTS
# =============================================================================


# NOTE: Templates are now discovered dynamically from import.yml references.
# No hardcoded entity names - use /{reference_name}/suggestions with any reference.


@router.get("/{reference_name}/suggestions", response_model=SuggestionsResponse)
async def get_reference_suggestions(
    reference_name: str,
    entity: Optional[str] = Query(
        default=None, description="Source dataset name (auto-detected if not provided)"
    ),
    max_suggestions: int = Query(default=100, ge=1, le=200),
):
    """
    Get template suggestions for any reference entity.

    This is a generic endpoint that works with any reference defined in import.yml.
    The reference_name parameter determines which group_by target to configure for.

    Returns suggestions from three sources:
    1. Navigation widget suggestion (always included for the reference)
    2. Column-based suggestions from semantic profiles (occurrence data)
    3. Class_object suggestions from pre-calculated CSV sources

    Args:
        reference_name: Name of the reference from import.yml (e.g., 'taxons', 'plots', 'shapes')
        entity: Optional source dataset name (defaults to first available dataset)
        max_suggestions: Maximum number of suggestions to return
    """
    # Ensure plugins are loaded before generating suggestions
    _ensure_plugins_loaded()

    column_suggestions: List[TemplateSuggestion] = []
    enriched_profiles: List = []
    columns_analyzed = 0

    # Generate navigation widget suggestion (always included)
    navigation_suggestion = _generate_navigation_suggestion(reference_name)

    # Try to get column-based suggestions (may fail if no semantic profile)
    try:
        db_path = get_database_path()
        if db_path:
            from niamoto.core.imports.registry import EntityRegistry, EntityKind
            from niamoto.core.imports.data_analyzer import (
                DataCategory,
                FieldPurpose,
                EnrichedColumnProfile,
            )

            db = Database(str(db_path), read_only=True)
            try:
                registry = EntityRegistry(db)

                # Auto-detect entity if not provided
                if entity is None:
                    datasets = registry.list_entities(kind=EntityKind.DATASET)
                    if datasets:
                        entity = datasets[0].name

                if entity:
                    # Get entity from registry
                    try:
                        entity_meta = registry.get(entity)
                        # Get stored semantic profiles
                        semantic_profile = entity_meta.config.get(
                            "semantic_profile", {}
                        )
                        columns = semantic_profile.get("columns", [])

                        if columns:
                            # Convert stored profiles to EnrichedColumnProfile objects
                            for col_data in columns:
                                # Parse data_category enum
                                cat_str = col_data.get("data_category", "categorical")
                                try:
                                    data_cat = DataCategory(cat_str)
                                except ValueError:
                                    data_cat = DataCategory.CATEGORICAL

                                # Parse field_purpose enum
                                purpose_str = col_data.get("field_purpose", "metadata")
                                try:
                                    field_purpose = FieldPurpose(purpose_str)
                                except ValueError:
                                    field_purpose = FieldPurpose.METADATA

                                # Parse value_range
                                value_range = col_data.get("value_range")
                                if (
                                    value_range
                                    and isinstance(value_range, list)
                                    and len(value_range) == 2
                                ):
                                    value_range = tuple(value_range)
                                else:
                                    value_range = None

                                profile = EnrichedColumnProfile(
                                    name=col_data.get("name", "unknown"),
                                    dtype=col_data.get("dtype", "object"),
                                    semantic_type=col_data.get("semantic_type"),
                                    unique_ratio=col_data.get("unique_ratio", 0.0),
                                    null_ratio=col_data.get("null_ratio", 0.0),
                                    sample_values=col_data.get("suggested_labels")
                                    or [],
                                    confidence=col_data.get("confidence", 0.5),
                                    data_category=data_cat,
                                    field_purpose=field_purpose,
                                    suggested_bins=col_data.get("suggested_bins"),
                                    suggested_labels=col_data.get("suggested_labels"),
                                    cardinality=col_data.get("cardinality", 0),
                                    value_range=value_range,
                                )
                                enriched_profiles.append(profile)

                            columns_analyzed = len(enriched_profiles)

                            # Get column-based suggestions
                            suggester = TemplateSuggester()
                            column_suggestions = suggester.suggest_for_entity(
                                column_profiles=enriched_profiles,
                                reference_name=reference_name,
                                source_name=entity,
                                max_suggestions=max_suggestions,
                            )
                    except Exception as e:
                        logger.warning(f"Could not get column suggestions: {e}")

            finally:
                db.close_db_session()

    except Exception as e:
        logger.warning(f"Error loading column suggestions: {e}")

    # Always get suggestions from pre-calculated CSV sources (class_objects)
    class_object_suggestions = _get_class_object_suggestions(reference_name)

    # Get entity-specific map suggestions (for plots/shapes)
    entity_map_suggestions = _get_entity_map_suggestions(reference_name)

    # Generate general_info suggestion (field_aggregator for metadata)
    general_info_suggestion = _generate_general_info_suggestion(reference_name)

    # Combine all types of suggestions
    # Navigation suggestion is always first (highest priority)
    # Class_object suggestions are always included (pre-calculated CSV data)
    # Column suggestions are limited to fill the remaining slots
    column_suggestion_dicts = [s.to_dict() for s in column_suggestions]

    # If entity has its own geometry (entity_map_suggestions exist),
    # filter out occurrence-based map suggestions (they don't make sense)
    if entity_map_suggestions:
        column_suggestion_dicts = [
            s for s in column_suggestion_dicts if s.get("category") != "map"
        ]

    # Sort column suggestions by confidence
    column_suggestion_dicts.sort(key=lambda s: -s.get("confidence", 0))

    # Calculate how many column suggestions we can include (reserve slots for navigation + general_info + entity maps + class_objects)
    reserved_slots = (
        2 + len(class_object_suggestions) + len(entity_map_suggestions)
    )  # 2 = navigation + general_info
    remaining_slots = max(0, max_suggestions - reserved_slots)
    limited_column_suggestions = column_suggestion_dicts[:remaining_slots]

    # Combine: navigation first, then general_info, then entity maps, then class_object, then column suggestions
    all_suggestions = (
        ([navigation_suggestion] if navigation_suggestion else [])
        + ([general_info_suggestion] if general_info_suggestion else [])
        + entity_map_suggestions
        + class_object_suggestions
        + limited_column_suggestions
    )

    # Sort by confidence but keep navigation at top
    # Navigation has confidence 0.95, so it will stay near top naturally
    all_suggestions.sort(key=lambda s: -s.get("confidence", 0))

    # If no suggestions at all, return helpful error
    if not all_suggestions:
        raise HTTPException(
            status_code=404,
            detail=f"No suggestions found for '{reference_name}'. Import data or add CSV sources.",
        )

    return SuggestionsResponse(
        suggestions=[TemplateSuggestionResponse(**s) for s in all_suggestions],
        entity_type=reference_name,
        columns_analyzed=columns_analyzed,
        total_suggestions=len(all_suggestions),
    )


@router.post("/generate-config", response_model=GenerateConfigResponse)
async def generate_transform_config(request: GenerateConfigRequest):
    """
    Generate transform.yml configuration from selected templates.

    Takes the full template data (plugin + config) directly from the frontend
    and generates the complete configuration section for transform.yml.

    The sources section is built dynamically based on reference_kind:
    - hierarchical: Uses nested_set plugin for tree traversal
    - flat/spatial: Uses direct_reference plugin for simple FK lookup
    """
    # Generate widgets_data directly from request
    widgets_data = {}
    for template in request.templates:
        widgets_data[template.template_id] = {
            "plugin": template.plugin,
            "params": template.config,
        }

    # Build sources section based on reference kind (not name!)
    if request.reference_kind == "hierarchical":
        # Hierarchical references use nested_set for tree aggregation
        sources = [
            {
                "name": "occurrences",
                "data": "occurrences",
                "grouping": request.group_by,
                "relation": {
                    "plugin": "nested_set",
                    "key": f"id_{request.group_by}ref",  # Convention: id_<reference>ref
                    "ref_key": f"{request.group_by}_id",
                    "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
                },
            }
        ]
    else:
        # Flat and spatial references use direct_reference
        sources = [
            {
                "name": "occurrences",
                "data": "occurrences",
                "grouping": request.group_by,
                "relation": {
                    "plugin": "direct_reference",
                    "key": f"{request.group_by}_id",
                    "ref_key": "id",
                },
            }
        ]

    return GenerateConfigResponse(
        group_by=request.group_by,
        sources=sources,
        widgets_data=widgets_data,
    )


class SaveConfigRequest(BaseModel):
    """Request to save generated config to transform.yml."""

    group_by: str = Field(..., description="Reference name for the group")
    sources: List[Dict[str, Any]] = Field(..., description="Sources configuration")
    widgets_data: Dict[str, Any] = Field(..., description="Widgets configuration")


class SaveConfigResponse(BaseModel):
    """Response after saving config."""

    success: bool
    message: str
    file_path: str
    widgets_added: int
    widgets_updated: int


def _generate_export_config(
    work_dir: Path,
    group_name: str,
    widgets_data: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> None:
    """
    Generate export.yml configuration for widgets.

    Creates or updates the export.yml file with widget configurations
    that correspond to the transform.yml widgets_data.
    """
    export_path = work_dir / "config" / "export.yml"

    # Load existing export config
    export_config: Dict[str, Any] = {"exports": []}
    if export_path.exists():
        with open(export_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if loaded and isinstance(loaded, dict):
                export_config = loaded

    # Ensure exports list exists
    if "exports" not in export_config or not isinstance(export_config["exports"], list):
        export_config["exports"] = []

    # Find or create the html_page_exporter entry
    html_exporter = None
    html_exporter_idx = -1
    for idx, exp in enumerate(export_config["exports"]):
        if isinstance(exp, dict) and exp.get("exporter") == "html_page_exporter":
            html_exporter = exp
            html_exporter_idx = idx
            break

    if html_exporter is None:
        # Create default html_page_exporter
        html_exporter = {
            "name": "web_pages",
            "enabled": True,
            "exporter": "html_page_exporter",
            "params": {
                "template_dir": "templates/",
                "output_dir": "exports/web",
                "site": {
                    "title": "Niamoto",
                    "lang": "fr",
                    "primary_color": "#228b22",
                },
                "navigation": [
                    {"text": "Accueil", "url": "/index.html"},
                ],
            },
            "static_pages": [],
            "groups": [],
        }
        export_config["exports"].append(html_exporter)
        html_exporter_idx = len(export_config["exports"]) - 1

    # Ensure groups list exists
    if "groups" not in html_exporter or not isinstance(html_exporter["groups"], list):
        html_exporter["groups"] = []

    # Find or create group config
    group_config = None
    group_idx = -1
    for idx, grp in enumerate(html_exporter["groups"]):
        if isinstance(grp, dict) and grp.get("group_by") == group_name:
            group_config = grp
            group_idx = idx
            break

    if group_config is None:
        # Create new group config
        group_config = {
            "group_by": group_name,
            "output_pattern": f"{group_name}/{{id}}.html",
            "index_output_pattern": f"{group_name}/index.html",
            "widgets": [],
        }
        html_exporter["groups"].append(group_config)
        group_idx = len(html_exporter["groups"]) - 1

    # Convert widgets_data to export widgets format
    export_widgets = []
    widget_order = 0
    for widget_id, widget_config in widgets_data.items():
        plugin = widget_config.get("plugin", "")
        params = widget_config.get("params", {})

        # Map transformer plugins to widget plugins
        widget_plugin = _map_transformer_to_widget(plugin, widget_id)

        # Build widget config for export
        export_widget: Dict[str, Any] = {
            "plugin": widget_plugin,
            "title": _generate_widget_title(widget_id, plugin, params),
            "data_source": widget_id,  # Links to widgets_data key in transform.yml
            "layout": {
                "colspan": 1,  # Default: half width (2 widgets per row)
                "order": widget_order,
            },
        }
        widget_order += 1

        # Add widget-specific params based on type
        widget_params = _generate_widget_params(widget_plugin, plugin, params)
        if widget_params:
            export_widget["params"] = widget_params

        export_widgets.append(export_widget)

    # Update group widgets
    group_config["widgets"] = export_widgets

    # Update the config structure
    html_exporter["groups"][group_idx] = group_config
    export_config["exports"][html_exporter_idx] = html_exporter

    # Write export config
    with open(export_path, "w", encoding="utf-8") as f:
        yaml.dump(
            export_config,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )

    logger.info(f"Generated export config for group '{group_name}' to {export_path}")


def _map_transformer_to_widget(transformer_plugin: str, widget_id: str) -> str:
    """Map a transformer plugin to its corresponding widget plugin."""
    # Navigation widget passes through
    if transformer_plugin == "hierarchical_nav_widget":
        return "hierarchical_nav_widget"

    # Determine widget type from widget_id suffix
    if widget_id.endswith("_bar_plot"):
        return "bar_plot"
    elif widget_id.endswith("_donut_chart"):
        return "donut_chart"
    elif widget_id.endswith("_radial_gauge"):
        return "radial_gauge"
    elif widget_id.endswith("_interactive_map"):
        return "interactive_map"
    elif widget_id.endswith("_info_grid"):
        return "info_grid"

    # Default mappings based on transformer
    transformer_to_widget = {
        "top_ranking": "bar_plot",
        "categorical_distribution": "bar_plot",
        "binned_distribution": "bar_plot",
        "binary_counter": "donut_chart",
        "statistical_summary": "info_grid",
        "geospatial_extractor": "interactive_map",
        "field_aggregator": "info_grid",
    }
    return transformer_to_widget.get(transformer_plugin, "info_grid")


def _generate_widget_title(widget_id: str, plugin: str, params: Dict[str, Any]) -> str:
    """Generate a user-friendly title for a widget."""
    # Get field name from params
    field = params.get("field", "")

    # Clean up field name for title
    if field:
        title = field.replace("_", " ").title()
    else:
        # Extract from widget_id
        parts = widget_id.split("_")
        # Remove suffix like bar_plot, donut_chart
        if len(parts) >= 2:
            title = " ".join(parts[:-2]).replace("_", " ").title()
        else:
            title = widget_id.replace("_", " ").title()

    # Add context based on transformer
    if plugin == "top_ranking":
        count = params.get("count", 10)
        return f"Top {count} - {title}"
    elif plugin == "binned_distribution":
        return f"Distribution - {title}"
    elif plugin == "categorical_distribution":
        return f"Répartition - {title}"
    elif plugin == "binary_counter":
        return f"{title}"
    elif plugin == "geospatial_extractor":
        return "Distribution géographique"
    elif plugin == "hierarchical_nav_widget":
        ref = params.get("referential_data", "")
        return f"Navigation - {ref.title()}"

    return title


def _generate_widget_params(
    widget_plugin: str, transformer_plugin: str, transformer_params: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate widget-specific params based on transformer."""
    params: Dict[str, Any] = {}

    if widget_plugin == "bar_plot":
        if transformer_plugin == "top_ranking":
            params = {
                "orientation": "h",
                "x_axis": "counts",
                "y_axis": "tops",
                "sort_order": "ascending",
                "auto_color": True,
            }
        elif transformer_plugin in ("binned_distribution", "categorical_distribution"):
            params = {
                "orientation": "v",
                "x_axis": "labels",
                "y_axis": "counts",
                "gradient_color": "#10b981",
                "gradient_mode": "luminance",
                "show_legend": False,  # Hide legend - values shown on bars
            }
            if transformer_plugin == "binned_distribution":
                params["transform"] = "bins_to_df"
                params["transform_params"] = {
                    "bin_field": "bins",
                    "count_field": "counts",
                    "use_percentages": True,
                    "percentage_field": "percentages",
                    "x_field": "bin",
                    "y_field": "count",
                }

    elif widget_plugin == "donut_chart":
        params = {
            "labels_field": "labels",
            "values_field": "counts",
        }

    elif widget_plugin == "radial_gauge":
        params = {
            "value_field": "percentage",
        }

    elif widget_plugin == "interactive_map":
        params = {
            "map_style": "carto-voyager",
            "zoom": 7,
            "layers": [
                {
                    "id": "occurrences",
                    "source": "coordinates",
                    "type": "circle_markers",
                    "style": {
                        "color": "#1fb99d",
                        "weight": 1,
                        "fillColor": "#00716b",
                        "fillOpacity": 0.5,
                        "radius": 8,
                    },
                }
            ],
        }

    elif widget_plugin == "hierarchical_nav_widget":
        # Pass through the navigation params
        params = {
            "referential_data": transformer_params.get("referential_data", ""),
            "id_field": transformer_params.get("id_field", "id"),
            "name_field": transformer_params.get("name_field", "name"),
            "base_url": transformer_params.get("base_url", ""),
            "show_search": transformer_params.get("show_search", True),
        }
        # Add hierarchy fields if present
        if transformer_params.get("lft_field"):
            params["lft_field"] = transformer_params["lft_field"]
        if transformer_params.get("rght_field"):
            params["rght_field"] = transformer_params["rght_field"]
        if transformer_params.get("level_field"):
            params["level_field"] = transformer_params["level_field"]
        if transformer_params.get("parent_id_field"):
            params["parent_id_field"] = transformer_params["parent_id_field"]

    return params


@router.post("/save-config", response_model=SaveConfigResponse)
async def save_transform_config(request: SaveConfigRequest):
    """
    Save generated widget configuration to transform.yml.

    This endpoint:
    1. Loads existing transform.yml (or creates new one)
    2. Updates/adds the group configuration
    3. Writes the updated file

    The configuration is merged intelligently:
    - If the group already exists, widgets are merged (new widgets added, existing updated)
    - Sources are replaced entirely for the group
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)
    config_dir = work_dir / "config"
    transform_path = config_dir / "transform.yml"

    try:
        # Ensure config directory exists
        config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config as a list of groups
        # Format: [{ group_by: taxons, sources: [...], widgets_data: {...} }, ...]
        existing_groups: List[Dict[str, Any]] = []
        if transform_path.exists():
            with open(transform_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, list):
                    existing_groups = loaded
                elif isinstance(loaded, dict) and "groups" in loaded:
                    # Convert old dict format to list format
                    groups_dict = loaded.get("groups", {})
                    if isinstance(groups_dict, dict):
                        for name, config in groups_dict.items():
                            config["group_by"] = name
                            existing_groups.append(config)
                    elif isinstance(groups_dict, list):
                        existing_groups = groups_dict

        # Find or create the group config
        group_name = request.group_by
        group_config = None
        group_index = -1

        for i, group in enumerate(existing_groups):
            if group.get("group_by") == group_name:
                group_config = group
                group_index = i
                break

        if group_config is None:
            # Create new group
            group_config = {"group_by": group_name}
            existing_groups.append(group_config)
            group_index = len(existing_groups) - 1

        # Update sources (replace entirely)
        group_config["sources"] = request.sources

        # Update widgets_data (merge)
        if "widgets_data" not in group_config:
            group_config["widgets_data"] = {}

        # Track changes
        widgets_added = 0
        widgets_updated = 0

        # Merge new widgets into existing
        for widget_id, widget_config in request.widgets_data.items():
            if widget_id in group_config["widgets_data"]:
                widgets_updated += 1
            else:
                widgets_added += 1
            group_config["widgets_data"][widget_id] = widget_config

        # Update the group in the list
        existing_groups[group_index] = group_config

        # Write updated config as list
        with open(transform_path, "w", encoding="utf-8") as f:
            yaml.dump(
                existing_groups,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=120,
            )

        logger.info(
            f"Saved transform config for group '{group_name}' to {transform_path}"
        )

        # Also generate export.yml configuration
        _generate_export_config(
            work_dir, group_name, request.widgets_data, group_config.get("sources", [])
        )

        return SaveConfigResponse(
            success=True,
            message=f"Configuration saved for group '{group_name}'",
            file_path=str(transform_path),
            widgets_added=widgets_added,
            widgets_updated=widgets_updated,
        )

    except Exception as e:
        logger.exception(f"Error saving transform config: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to save configuration: {str(e)}"
        )


@router.get("/{group_by}/configured")
async def get_configured_widgets(group_by: str):
    """
    Get the list of widget template IDs already configured in transform.yml.

    This allows the frontend to know which widgets are already saved
    and pre-select them in the gallery instead of using auto-selection.

    Returns:
        configured_ids: List of template_ids from widgets_data keys
        has_config: Whether a configuration exists for this group
    """
    work_dir = get_working_directory()
    if not work_dir:
        return {"configured_ids": [], "has_config": False}

    work_dir = Path(work_dir)
    transform_path = work_dir / "config" / "transform.yml"

    if not transform_path.exists():
        return {"configured_ids": [], "has_config": False}

    try:
        with open(transform_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config:
            return {"configured_ids": [], "has_config": False}

        # Handle list format (current)
        if isinstance(config, list):
            for group in config:
                if isinstance(group, dict) and group.get("group_by") == group_by:
                    widgets_data = group.get("widgets_data", {})
                    return {
                        "configured_ids": list(widgets_data.keys()),
                        "has_config": True,
                    }

        # Handle dict format (legacy)
        elif isinstance(config, dict):
            groups = config.get("groups", {})
            if isinstance(groups, dict) and group_by in groups:
                widgets_data = groups[group_by].get("widgets_data", {})
                return {
                    "configured_ids": list(widgets_data.keys()),
                    "has_config": True,
                }

        return {"configured_ids": [], "has_config": False}

    except Exception as e:
        logger.warning(f"Error reading configured widgets: {e}")
        return {"configured_ids": [], "has_config": False}


@router.get("/categories")
async def list_categories():
    """List all available widget categories.

    Categories are predefined and not data-driven.
    Counts are populated when suggestions are generated.
    """
    return {
        "categories": list(WIDGET_CATEGORIES.values()),
        "total_categories": len(WIDGET_CATEGORIES),
    }


# =============================================================================
# PREVIEW ENDPOINT
# =============================================================================


# Class_object extractors (not real transformer plugins, but used for preview)
CLASS_OBJECT_EXTRACTORS = {
    "series_extractor",
    "binary_aggregator",
    "categories_extractor",
}


def _is_class_object_template(transformer: str) -> bool:
    """Check if a transformer name is a class_object extractor."""
    return transformer in CLASS_OBJECT_EXTRACTORS


def _load_class_object_data_for_preview(
    work_dir: Path, class_object_name: str, reference_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Load class_object data from CSV source for preview.

    Searches through ALL configured CSV sources across ALL groups to find the class_object data.
    If reference_name is provided, searches only in that group first.

    Args:
        work_dir: Working directory path
        class_object_name: Name of the class_object (e.g., 'dbh')
        reference_name: Optional name of the reference group (searches all if not found)

    Returns:
        Dict with 'labels' and 'counts' for widget rendering, or None if not found.
    """
    transform_path = work_dir / "config" / "transform.yml"

    if not transform_path.exists():
        return None

    try:
        with open(transform_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Collect all group configs to search through
        all_group_configs: List[Dict[str, Any]] = []

        if isinstance(config, list):
            # Format 1: List at root
            all_group_configs = [g for g in config if isinstance(g, dict)]
        elif isinstance(config, dict):
            groups = config.get("groups", {})
            if isinstance(groups, list):
                # Format 2: groups is a list
                all_group_configs = [g for g in groups if isinstance(g, dict)]
            elif isinstance(groups, dict):
                # Format 3: groups is a dict with reference names as keys
                for name, group_config in groups.items():
                    if isinstance(group_config, dict):
                        # Add group_by if not present (for dict format)
                        group_with_name = {**group_config, "group_by": name}
                        all_group_configs.append(group_with_name)

        # If reference_name provided, prioritize that group
        if reference_name:
            # Move matching group to front
            matching = [
                g for g in all_group_configs if g.get("group_by") == reference_name
            ]
            others = [
                g for g in all_group_configs if g.get("group_by") != reference_name
            ]
            all_group_configs = matching + others

        # Search through all groups and their CSV sources
        for group_config in all_group_configs:
            sources = group_config.get("sources", [])

            for source in sources:
                data_path = source.get("data", "")
                if not data_path.endswith(".csv"):
                    continue

                csv_path = work_dir / data_path
                if not csv_path.exists():
                    continue

                # Load and check for the class_object
                try:
                    df = pd.read_csv(csv_path)

                    # Check if this CSV has the class_object format
                    if "class_object" not in df.columns:
                        continue

                    # Filter for our class_object
                    co_data = df[df["class_object"] == class_object_name]
                    if co_data.empty:
                        continue

                    # Extract labels and values (aggregate across all entities for preview)
                    # Group by class_name and sum values for a representative view
                    aggregated = (
                        co_data.groupby("class_name", sort=False)["class_value"]
                        .sum()
                        .reset_index()
                    )
                    labels = aggregated["class_name"].tolist()
                    values = aggregated["class_value"].tolist()

                    return {
                        "labels": labels,
                        "counts": values,
                        "source": source.get("name", Path(data_path).stem),
                        "group_by": group_config.get("group_by", "unknown"),
                    }

                except Exception as e:
                    logger.warning(f"Error loading CSV {csv_path}: {e}")
                    continue

        return None

    except Exception as e:
        logger.warning(f"Error loading class_object data: {e}")
        return None


def _generate_navigation_suggestion(reference_name: str) -> Optional[Dict[str, Any]]:
    """Generate a navigation widget suggestion for a reference.

    Detects hierarchy fields from the database and generates appropriate config.

    Args:
        reference_name: Name of the reference (e.g., 'taxons', 'plots')

    Returns:
        Dict in TemplateSuggestion format, or None if generation fails
    """
    try:
        db_path = get_database_path()
        if not db_path:
            # Return basic navigation suggestion without hierarchy detection
            return WidgetGenerator.generate_navigation_suggestion(
                reference_name=reference_name,
                is_hierarchical=False,
                hierarchy_fields=None,
            )

        from niamoto.common.database import Database

        db = Database(str(db_path), read_only=True)
        try:
            # Try to find the reference table
            table_name = f"reference_{reference_name}"
            if not db.has_table(table_name):
                # Try other naming conventions
                for alt_name in [reference_name, f"entity_{reference_name}"]:
                    if db.has_table(alt_name):
                        table_name = alt_name
                        break
                else:
                    # No table found - return basic suggestion
                    return WidgetGenerator.generate_navigation_suggestion(
                        reference_name=reference_name,
                        is_hierarchical=False,
                        hierarchy_fields=None,
                    )

            # Get column names from the table
            columns_df = pd.read_sql(
                f"SELECT * FROM {table_name} LIMIT 0",
                db.engine,
            )
            columns = set(columns_df.columns.tolist())

            # Detect hierarchy structure
            has_nested_set = "lft" in columns and "rght" in columns
            has_parent = "parent_id" in columns
            has_level = "level" in columns

            is_hierarchical = has_nested_set or (has_parent and has_level)

            # Detect ID field
            id_candidates = [f"id_{reference_name}", f"{reference_name}_id", "id"]
            id_field = next((c for c in id_candidates if c in columns), None)
            if not id_field:
                id_field = next((c for c in columns if "id" in c.lower()), "id")

            # Detect name field
            name_candidates = [
                "full_name",
                "name",
                "plot",
                "label",
                "title",
                reference_name,
            ]
            name_field = next((c for c in name_candidates if c in columns), None)
            if not name_field:
                name_field = next(
                    (c for c in columns if c != id_field and "name" in c.lower()),
                    id_field,
                )

            hierarchy_fields = {
                "has_nested_set": has_nested_set,
                "has_parent": has_parent,
                "has_level": has_level,
                "lft_field": "lft" if has_nested_set else None,
                "rght_field": "rght" if has_nested_set else None,
                "parent_id_field": "parent_id" if has_parent else None,
                "level_field": "level" if has_level else None,
                "id_field": id_field,
                "name_field": name_field,
            }

            return WidgetGenerator.generate_navigation_suggestion(
                reference_name=reference_name,
                is_hierarchical=is_hierarchical,
                hierarchy_fields=hierarchy_fields,
            )

        finally:
            db.close_db_session()

    except Exception as e:
        logger.warning(f"Error generating navigation suggestion: {e}")
        # Return basic suggestion on error
        return WidgetGenerator.generate_navigation_suggestion(
            reference_name=reference_name,
            is_hierarchical=False,
            hierarchy_fields=None,
        )


def _generate_general_info_suggestion(reference_name: str) -> Optional[Dict[str, Any]]:
    """Generate a general_info widget suggestion for a reference.

    Dynamically analyzes columns to find the most useful fields for a summary card.
    Uses heuristics based on column characteristics rather than hardcoded names.

    Selection criteria:
    - Excludes: IDs, hierarchy fields (lft/rght/level/parent), timestamps
    - Prioritizes: Low cardinality (categories), non-null values, text fields
    - Detects: JSON fields in extra_data, occurrence counts

    Args:
        reference_name: Name of the reference (e.g., 'taxons', 'plots', 'shapes')

    Returns:
        Dict in TemplateSuggestion format, or None if no useful fields found
    """
    try:
        db_path = get_database_path()
        if not db_path:
            return None

        from niamoto.common.database import Database
        from niamoto.core.imports.registry import EntityRegistry, EntityKind

        db = Database(str(db_path), read_only=True)
        try:
            registry = EntityRegistry(db)

            # Try to find the reference table
            ref_table = f"reference_{reference_name}"
            if not db.has_table(ref_table):
                for alt_name in [reference_name, f"entity_{reference_name}"]:
                    if db.has_table(alt_name):
                        ref_table = alt_name
                        break
                else:
                    return None

            # Get sample data to analyze columns
            sample_df = pd.read_sql(f"SELECT * FROM {ref_table} LIMIT 100", db.engine)
            if sample_df.empty:
                return None

            # Patterns to exclude (technical/internal columns)
            exclude_patterns = {
                "id",
                "lft",
                "rght",
                "level",
                "parent_id",
                "parent",
                "created_at",
                "updated_at",
                "modified",
                "created",
            }
            exclude_suffixes = ("_id", "_ref", "_key", "_idx")

            # Analyze each column and score its usefulness
            column_scores = []
            for col in sample_df.columns:
                col_lower = col.lower()

                # Skip excluded columns
                if col_lower in exclude_patterns:
                    continue
                if any(col_lower.endswith(s) for s in exclude_suffixes):
                    continue
                if col_lower.startswith("id_"):
                    continue

                # Skip extra_data (handled separately)
                if col_lower == "extra_data":
                    continue

                # Analyze column characteristics
                non_null = sample_df[col].notna().sum()
                null_ratio = (
                    1 - (non_null / len(sample_df)) if len(sample_df) > 0 else 1
                )

                # Skip columns with too many nulls
                if null_ratio > 0.8:
                    continue

                unique_count = sample_df[col].nunique()
                unique_ratio = unique_count / non_null if non_null > 0 else 1

                # Calculate usefulness score
                score = 0.0

                # Prefer columns with values
                score += (1 - null_ratio) * 0.3

                # Prefer low cardinality (categories) but not unique values (IDs)
                if 0.01 < unique_ratio < 0.5:
                    score += 0.3  # Good for categories
                elif unique_ratio <= 0.01:
                    score += 0.1  # Too few unique values
                elif unique_ratio >= 0.9:
                    score -= 0.2  # Likely an ID

                # Prefer text columns (object dtype)
                if sample_df[col].dtype == "object":
                    # Check average string length
                    non_null_vals = sample_df[col].dropna()
                    if len(non_null_vals) > 0:
                        avg_len = non_null_vals.astype(str).str.len().mean()
                        if avg_len < 100:  # Short text = good for display
                            score += 0.2
                        elif avg_len > 500:  # Long text = not good for summary
                            score -= 0.3

                # Boost columns with meaningful names
                meaningful_keywords = [
                    "name",
                    "type",
                    "status",
                    "category",
                    "rank",
                    "label",
                    "title",
                ]
                if any(kw in col_lower for kw in meaningful_keywords):
                    score += 0.2

                if score > 0:
                    column_scores.append((col, score, unique_ratio))

            # Sort by score and take top fields
            column_scores.sort(key=lambda x: -x[1])
            selected_columns = column_scores[:6]  # Max 6 fields from main table

            # Build field configurations
            field_configs = []
            for col, score, _ in selected_columns:
                field_configs.append(
                    {
                        "source": reference_name,
                        "field": col,
                        "target": col.lower().replace(" ", "_"),
                    }
                )

            # Check for extra_data JSON column
            if "extra_data" in sample_df.columns:
                try:
                    import json

                    non_null_extra = sample_df["extra_data"].dropna()
                    if len(non_null_extra) > 0:
                        sample_extra = non_null_extra.iloc[0]
                        if isinstance(sample_extra, str):
                            sample_extra = json.loads(sample_extra)
                        if isinstance(sample_extra, dict):
                            # Add up to 3 JSON fields
                            json_count = 0
                            for key, value in sample_extra.items():
                                if json_count >= 3:
                                    break
                                # Skip complex nested values
                                if (
                                    isinstance(value, (str, int, float, bool))
                                    or value is None
                                ):
                                    field_configs.append(
                                        {
                                            "source": reference_name,
                                            "field": f"extra_data.{key}",
                                            "target": key,
                                        }
                                    )
                                    json_count += 1
                except Exception:
                    pass

            # Add occurrence count if available
            try:
                datasets = registry.list_entities(kind=EntityKind.DATASET)
                has_occurrences = any(d.name == "occurrences" for d in datasets)
                if has_occurrences:
                    field_configs.append(
                        {
                            "source": "occurrences",
                            "field": "id",
                            "target": "occurrences_count",
                            "transformation": "count",
                        }
                    )
            except Exception:
                pass

            # Need at least 2 fields to be useful
            if len(field_configs) < 2:
                return None

            # Generate labels
            ref_label = reference_name.replace("_", " ").title()

            return {
                "template_id": f"general_info_{reference_name}_field_aggregator_info_grid",
                "name": "Informations générales",
                "description": f"Fiche d'information pour {ref_label} (champs détectés automatiquement)",
                "plugin": "field_aggregator",
                "transformer_plugin": "field_aggregator",
                "widget_plugin": "info_grid",
                "category": "info",
                "icon": "Info",
                "confidence": 0.85,  # Slightly lower - user should review fields
                "source": "auto",
                "source_name": reference_name,
                "matched_column": reference_name,
                "match_reason": f"Agrégation de {len(field_configs)} champs détectés dans '{reference_name}'",
                "is_recommended": True,
                "config": {
                    "plugin": "field_aggregator",
                    "params": {
                        "fields": field_configs,
                    },
                },
                "transformer_config": {
                    "plugin": "field_aggregator",
                    "params": {
                        "fields": field_configs,
                    },
                },
                "widget_config": {},
                "alternatives": [],
            }

        finally:
            db.close_db_session()

    except Exception as e:
        logger.warning(f"Error generating general_info suggestion: {e}")
        return None


def _get_entity_map_suggestions(reference_name: str) -> List[Dict[str, Any]]:
    """Generate map widget suggestions based on geometry columns in entity table.

    Detection strategy (in priority order):
    1. Read import.yml schema for explicitly declared geometry fields
    2. Pattern matching on column names (with WKT validation)
    3. Sample data to detect WKT format

    For spatial references (shapes), also generates type-based suggestions
    using the entity_type column.

    Args:
        reference_name: Name of the reference (e.g., 'taxons', 'plots', 'shapes')

    Returns:
        List of map widget suggestions
    """
    from niamoto.common.database import Database

    suggestions = []

    db_path = get_database_path()
    work_dir = get_working_directory()
    if not db_path:
        return suggestions

    db = Database(str(db_path), read_only=True)

    try:
        entity_table = f"entity_{reference_name}"

        if not db.has_table(entity_table):
            return suggestions

        # Get columns from entity table
        columns_df = pd.read_sql(
            f"SELECT * FROM {entity_table} LIMIT 0",
            db.engine,
        )
        columns = columns_df.columns.tolist()

        # =====================================================================
        # STEP 1: Read import.yml for declared geometry fields
        # =====================================================================
        declared_geometry_fields = set()
        reference_config = {}

        if work_dir:
            import_path = Path(work_dir) / "config" / "import.yml"
            if import_path.exists():
                try:
                    with open(import_path, "r", encoding="utf-8") as f:
                        import_config = yaml.safe_load(f) or {}

                    references = import_config.get("entities", {}).get("references", {})
                    ref_config = references.get(reference_name, {})
                    reference_config = ref_config
                    schema = ref_config.get("schema", {})
                    fields = schema.get("fields", [])

                    for field in fields:
                        if isinstance(field, dict) and field.get("type") == "geometry":
                            declared_geometry_fields.add(field.get("name"))

                except Exception as e:
                    logger.debug(
                        f"Could not read import.yml for geometry detection: {e}"
                    )

        # =====================================================================
        # STEP 2: Build geometry columns list
        # =====================================================================
        geometry_columns = []

        # Helper to validate WKT content
        def _validate_wkt_column(col_name: str) -> Optional[str]:
            """Check if column contains valid WKT geometry. Returns geometry type or None."""
            try:
                sample = pd.read_sql(
                    f'SELECT "{col_name}" FROM {entity_table} WHERE "{col_name}" IS NOT NULL LIMIT 1',
                    db.engine,
                )
                if not sample.empty:
                    val = str(sample.iloc[0][col_name]).strip()
                    if val.startswith("POINT"):
                        return "point"
                    elif val.startswith("POLYGON") or val.startswith("MULTIPOLYGON"):
                        return "polygon"
            except Exception:
                pass
            return None

        # First, add declared geometry fields (from import.yml)
        for field_name in declared_geometry_fields:
            if field_name in columns:
                geom_type = _validate_wkt_column(field_name)
                if geom_type:
                    geometry_columns.append((field_name, geom_type))

        # Then, pattern matching with validation
        # Only use patterns if no declared geometry found
        if not geometry_columns:
            point_patterns = ["geo_pt", "geom_pt", "coordinates", "position"]
            polygon_patterns = ["location", "geometry", "polygon", "boundary"]

            for col in columns:
                if col in declared_geometry_fields:
                    continue  # Already processed
                col_lower = col.lower()

                # Check for point patterns
                if any(p in col_lower for p in point_patterns):
                    geom_type = _validate_wkt_column(col)
                    if geom_type:
                        geometry_columns.append((col, geom_type))
                # Check for polygon patterns
                elif any(p in col_lower for p in polygon_patterns):
                    geom_type = _validate_wkt_column(col)
                    if geom_type:
                        geometry_columns.append((col, geom_type))

        # =====================================================================
        # STEP 3: Detect metadata fields (name, id, entity_type)
        # =====================================================================

        # Detect ID field from schema or by pattern
        id_field = reference_config.get("schema", {}).get("id_field")
        if not id_field:
            id_candidates = [
                f"id_{reference_name}",
                f"{reference_name}_id",
                "id",
                "id_plot",
            ]
            id_field = next((c for c in id_candidates if c in columns), None)
            if not id_field:
                id_field = next(
                    (c for c in columns if c.lower().startswith("id")), "id"
                )

        # Detect name field for display
        name_candidates = [
            "full_name",
            "name",
            "plot",
            "label",
            "title",
            reference_name,
        ]
        name_field = next((c for c in name_candidates if c in columns), None)
        if not name_field:
            name_field = next((c for c in columns if "name" in c.lower()), id_field)

        # =====================================================================
        # STEP 4: Generate suggestions
        # =====================================================================
        ref_label = reference_name.replace("_", " ").title()

        for geom_col, geom_type in geometry_columns:
            # Single entity map (primary)
            single_id = f"{reference_name}_{geom_col}_entity_map"
            all_id = f"{reference_name}_{geom_col}_all_map"

            if geom_type == "point":
                single_name = f"Position {ref_label}"
                single_desc = f"Carte affichant la position de l'entité {reference_name} sélectionnée"
                all_name = f"Carte de tous les {ref_label}"
                all_desc = f"Carte affichant la position de toutes les entités {reference_name}"
                icon_single = "MapPin"
            else:
                single_name = f"Polygone {ref_label}"
                single_desc = f"Carte affichant le polygone de l'entité {reference_name} sélectionnée"
                all_name = f"Carte de tous les {ref_label}"
                all_desc = f"Carte affichant tous les polygones {reference_name}"
                icon_single = "Hexagon"

            # Single entity map
            suggestions.append(
                {
                    "template_id": single_id,
                    "name": single_name,
                    "description": single_desc,
                    "plugin": "entity_map_extractor",
                    "category": "map",
                    "icon": icon_single,
                    "confidence": 0.90,
                    "source": "entity",
                    "source_name": reference_name,
                    "matched_column": geom_col,
                    "match_reason": f"Colonne géométrique '{geom_col}' détectée ({geom_type})",
                    "is_recommended": True,
                    "config": {
                        "entity_table": entity_table,
                        "geometry_field": geom_col,
                        "geometry_type": geom_type,
                        "name_field": name_field,
                        "id_field": id_field,
                        "mode": "single",
                    },
                    "alternatives": [all_id],
                }
            )

            # All entities map
            suggestions.append(
                {
                    "template_id": all_id,
                    "name": all_name,
                    "description": all_desc,
                    "plugin": "entity_map_extractor",
                    "category": "map",
                    "icon": "Map",
                    "confidence": 0.85,
                    "source": "entity",
                    "source_name": reference_name,
                    "matched_column": geom_col,
                    "match_reason": f"Vue d'ensemble des {reference_name}",
                    "is_recommended": False,
                    "config": {
                        "entity_table": entity_table,
                        "geometry_field": geom_col,
                        "geometry_type": geom_type,
                        "name_field": name_field,
                        "id_field": id_field,
                        "mode": "all",
                    },
                    "alternatives": [single_id],
                }
            )

            # Note: Type-based maps (e.g., "Carte Provinces") are not generated
            # because "all_map" already filters by the representative entity's type

        return suggestions

    except Exception as e:
        logger.warning(
            f"Error detecting entity map columns for '{reference_name}': {e}"
        )
        return []
    finally:
        db.close_db_session()


def _get_class_object_suggestions(reference_name: str) -> List[Dict[str, Any]]:
    """Get widget suggestions from pre-calculated CSV sources configured for this group.

    Reads transform.yml to find CSV sources, then analyzes each to suggest widgets.
    Returns empty list if no sources configured or working directory not set.
    """
    work_dir = get_working_directory()
    if not work_dir:
        return []

    work_dir = Path(work_dir)
    transform_path = work_dir / "config" / "transform.yml"

    if not transform_path.exists():
        return []

    try:
        with open(transform_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # transform.yml can have different structures:
        # 1. List of groups: [{group_by: taxons, ...}, {group_by: plots, ...}]
        # 2. Dict with groups key as list: {groups: [{group_by: taxons}, ...]}
        # 3. Dict with groups key as dict: {groups: {taxons: {...}, plots: {...}}}
        group_config = None

        if isinstance(config, list):
            # Format 1: List at root
            for group in config:
                if isinstance(group, dict) and group.get("group_by") == reference_name:
                    group_config = group
                    break
        elif isinstance(config, dict):
            groups = config.get("groups", {})
            if isinstance(groups, list):
                # Format 2: groups is a list
                for group in groups:
                    if (
                        isinstance(group, dict)
                        and group.get("group_by") == reference_name
                    ):
                        group_config = group
                        break
            elif isinstance(groups, dict):
                # Format 3: groups is a dict with reference names as keys
                group_config = groups.get(reference_name)

        if not group_config:
            return []

        sources = group_config.get("sources", [])

        all_suggestions = []
        for source in sources:
            data_path = source.get("data", "")
            # Only process CSV files (skip table references like 'occurrences')
            if not data_path.endswith(".csv"):
                continue

            source_name = source.get("name", Path(data_path).stem)
            csv_path = work_dir / data_path

            if not csv_path.exists():
                continue

            # Generate suggestions for this source
            suggestions = suggest_widgets_for_source(
                csv_path, source_name, reference_name
            )
            all_suggestions.extend(suggestions)

        return all_suggestions

    except Exception as e:
        logger.warning(f"Error loading class_object suggestions: {e}")
        return []


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

    # Import widget plugins
    from niamoto.core.plugins.widgets import (  # noqa: F401
        bar_plot,
        donut_chart,
        interactive_map,
        radial_gauge,
        info_grid,
    )


def _load_import_config(work_dir: Path) -> Dict[str, Any]:
    """Load and parse import.yml configuration."""
    import_path = work_dir / "config" / "import.yml"
    if not import_path.exists():
        raise HTTPException(
            status_code=404,
            detail="import.yml not found. Please configure your import first.",
        )

    with open(import_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_hierarchy_info(
    import_config: Dict[str, Any], reference_name: str = None
) -> Dict[str, Any]:
    """Extract reference information from import.yml and transform.yml.

    This function is generic and works with:
    - Hierarchical references (taxons with nested_set)
    - Flat references (plots without hierarchy)
    - Spatial references (shapes)
    - Plots with nested_set hierarchy (from transform.yml)

    Args:
        import_config: Loaded import.yml configuration
        reference_name: Specific reference to get info for (e.g., 'plots', 'shapes').
                       If None, returns the first hierarchical reference.

    Returns dict with:
    - reference_name: Name of the reference (e.g., 'taxons', 'plots')
    - levels: List of hierarchy levels (empty for flat references)
    - source_dataset: Name of source dataset (e.g., 'occurrences')
    - level_columns: Mapping of level name to column name
    - kind: Type of reference ('hierarchical', 'spatial', or None for flat)
    - is_hierarchical_grouping: True if transform.yml uses nested_set for this reference
    """
    references = import_config.get("entities", {}).get("references", {})

    # If a specific reference is requested, look for it
    if reference_name:
        # First, try to get relation info from transform.yml (needed for filtering occurrences)
        relation = {}
        source_dataset = "occurrences"
        is_hierarchical_grouping = False

        work_dir = get_working_directory()
        if work_dir:
            transform_path = Path(work_dir) / "config" / "transform.yml"
            if transform_path.exists():
                try:
                    with open(transform_path, "r", encoding="utf-8") as f:
                        transform_config = yaml.safe_load(f) or []

                    # Find the group matching the reference_name
                    for group in transform_config:
                        if group.get("group_by") == reference_name:
                            sources = group.get("sources", [])
                            if sources:
                                source = sources[0]
                                source_dataset = source.get("data", "occurrences")
                                relation = source.get("relation", {})
                                relation_plugin = relation.get("plugin")
                                is_hierarchical_grouping = (
                                    relation_plugin == "nested_set"
                                )
                            break
                except Exception as e:
                    logger.warning(f"Error reading transform.yml: {e}")

        # Now get reference config from import.yml
        ref_config = references.get(reference_name)
        if ref_config:
            info = _build_reference_info(reference_name, ref_config, import_config)
            # Override with transform.yml info (but keep import.yml relation if transform.yml has none)
            info["source_dataset"] = source_dataset
            if relation:  # Only override if transform.yml has relation info
                info["relation"] = relation
            # Note: info["relation"] is already set from import.yml by _build_reference_info
            info["is_hierarchical_grouping"] = is_hierarchical_grouping
            return info

        # Reference not found by exact name, maybe it's a group_by alias
        # Check if we found it in transform.yml with a different grouping name
        if relation:
            # Try to find the actual reference from grouping field in transform.yml
            for group in transform_config:
                if group.get("group_by") == reference_name:
                    sources = group.get("sources", [])
                    if sources:
                        grouping = sources[0].get("grouping", reference_name)
                        # Look for the reference by grouping name
                        for ref_name, ref_cfg in references.items():
                            if ref_name == grouping:
                                info = _build_reference_info(
                                    ref_name, ref_cfg, import_config
                                )
                                info["source_dataset"] = source_dataset
                                info["is_hierarchical_grouping"] = (
                                    is_hierarchical_grouping
                                )
                                info["relation"] = relation
                                return info
                    break

            # Reference not in import.yml, create minimal info
            return {
                "reference_name": reference_name,
                "levels": [],
                "source_dataset": source_dataset,
                "level_columns": {},
                "kind": None,
                "is_hierarchical_grouping": is_hierarchical_grouping,
                "relation": relation,
            }

    # Fallback: return first hierarchical reference (original behavior)
    for ref_name, ref_config in references.items():
        if ref_config.get("kind") == "hierarchical":
            return _build_reference_info(ref_name, ref_config, import_config)

    # No hierarchical reference found, return first reference if any
    if references:
        first_ref_name = next(iter(references))
        return _build_reference_info(
            first_ref_name, references[first_ref_name], import_config
        )

    raise HTTPException(
        status_code=400,
        detail="No reference found in import.yml",
    )


def _build_reference_info(
    ref_name: str, ref_config: Dict[str, Any], import_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Build reference info dict from config.

    Args:
        ref_name: Name of the reference
        ref_config: Reference configuration from import.yml
        import_config: Full import.yml configuration

    Returns:
        Dict with reference information
    """
    kind = ref_config.get("kind")  # hierarchical, spatial, or None
    hierarchy = ref_config.get("hierarchy", {})
    levels = hierarchy.get("levels", [])

    connector = ref_config.get("connector", {})
    source_dataset = connector.get("source", "occurrences")

    # Get level to column mapping (for hierarchical references)
    level_columns = {}
    extraction = connector.get("extraction", {})
    for level_info in extraction.get("levels", []):
        level_columns[level_info["name"]] = level_info.get("column", level_info["name"])

    # Get schema info
    schema = ref_config.get("schema", {})
    id_field = schema.get("id_field", "id")

    # Get relation info from import.yml (for flat references like plots)
    # This links the reference to occurrences via foreign_key/reference_key
    relation_config = ref_config.get("relation", {})
    relation = {}
    if relation_config:
        # Convert import.yml format to transform.yml compatible format
        # import.yml: { dataset: "occurrences", foreign_key: "plot_name", reference_key: "plot" }
        # transform.yml: { plugin: "direct_reference", key: "plot_name", ref_field: "plot" }
        relation = {
            "plugin": "direct_reference",
            "key": relation_config.get("foreign_key"),  # Column in occurrences
            "ref_field": relation_config.get("reference_key"),  # Column in reference
        }

    return {
        "reference_name": ref_name,
        "levels": levels,
        "source_dataset": source_dataset,
        "level_columns": level_columns,
        "kind": kind,
        "id_field": id_field,
        "is_hierarchical_grouping": kind == "hierarchical",
        "relation": relation,
    }


def _find_representative_entity(
    db: Database, hierarchy_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Find a representative entity for preview.

    Works with:
    - Hierarchical references (taxons): picks from first level (e.g., 'family')
    - Flat references (plots/shapes): uses relation key to filter occurrences

    Strategy: Pick an entity that has enough data to display meaningful results.
    """
    reference_name = hierarchy_info.get("reference_name", "taxons")
    source_dataset = hierarchy_info["source_dataset"]
    levels = hierarchy_info.get("levels", [])
    level_columns = hierarchy_info.get("level_columns", {})
    kind = hierarchy_info.get("kind")
    id_field = hierarchy_info.get("id_field", "id")

    # For non-hierarchical references (plots, shapes), get relation info from transform.yml
    if not levels or kind in ("spatial", None):
        # Try to get relation info from hierarchy_info (set by _get_hierarchy_info)
        relation = hierarchy_info.get("relation", {})
        relation_key = relation.get("key")  # Column in occurrences (e.g., "plots_id")

        # If no relation info, try to read from transform.yml
        if not relation_key:
            work_dir = get_working_directory()
            if work_dir:
                transform_path = Path(work_dir) / "config" / "transform.yml"
                if transform_path.exists():
                    try:
                        with open(transform_path, "r", encoding="utf-8") as f:
                            transform_config = yaml.safe_load(f) or []
                        for group in transform_config:
                            if group.get("group_by") == reference_name:
                                sources = group.get("sources", [])
                                if sources:
                                    relation = sources[0].get("relation", {})
                                    relation_key = relation.get("key")
                                break
                    except Exception:
                        pass

        # Find the occurrences table
        possible_names = [
            f"dataset_{source_dataset}",
            f"entity_{source_dataset}",
            source_dataset,
        ]
        table_name = None
        for name in possible_names:
            if db.has_table(name):
                table_name = name
                break

        if not table_name:
            raise HTTPException(
                status_code=404,
                detail=f"Source dataset '{source_dataset}' not found",
            )

        # If we have a relation key, find an entity with occurrences
        if relation_key:
            try:
                # Find entity_id with most occurrences
                query = f"""
                    SELECT "{relation_key}", COUNT(*) as cnt
                    FROM {table_name}
                    WHERE "{relation_key}" IS NOT NULL
                    GROUP BY "{relation_key}"
                    ORDER BY cnt DESC
                    LIMIT 1
                """
                result = pd.read_sql(query, db.engine)

                if not result.empty:
                    entity_id = result.iloc[0][relation_key]
                    count = int(result.iloc[0]["cnt"])

                    return {
                        "level": reference_name,
                        "column": relation_key,
                        "value": entity_id,
                        "count": count,
                        "table_name": table_name,
                    }
            except Exception as e:
                logger.warning(f"Error finding entity via relation: {e}")

        # Fallback: return first entity from entity table
        entity_table = f"entity_{reference_name}"
        if db.has_table(entity_table):
            columns_df = pd.read_sql(f"SELECT * FROM {entity_table} LIMIT 0", db.engine)
            columns = columns_df.columns.tolist()

            name_candidates = ["full_name", "name", "plot", "label", "title"]
            name_field = next((c for c in name_candidates if c in columns), id_field)

            where_clause = ""
            if kind == "spatial" and "entity_type" in columns:
                where_clause = "WHERE entity_type = 'shape'"

            query = f"SELECT * FROM {entity_table} {where_clause} LIMIT 1"
            result = pd.read_sql(query, db.engine)

            if not result.empty:
                entity = result.iloc[0]
                entity_id = entity.get(id_field, entity.get("id"))

                # For spatial references, include geometry for ST_Contains queries
                result_dict = {
                    "level": reference_name,
                    "column": id_field,
                    "value": entity_id,
                    "count": 0,
                    "table_name": entity_table,
                    "entity_name": str(entity.get(name_field, entity_id)),
                }

                if kind == "spatial" and "location" in columns:
                    # Include geometry for spatial queries
                    location = entity.get("location")
                    if location:
                        result_dict["geometry"] = str(location)
                        result_dict["spatial_query"] = True
                        result_dict["kind"] = "spatial"
                        # Get the type (e.g., "Provinces") for the shape
                        if "type" in columns:
                            result_dict["shape_type"] = entity.get("type")

                return result_dict

        raise HTTPException(
            status_code=404,
            detail=f"No representative entity found for '{reference_name}'",
        )

    # For hierarchical references, use existing logic
    first_level = levels[0]
    column_name = level_columns.get(first_level, first_level)

    # Find the occurrences table
    possible_names = [
        f"dataset_{source_dataset}",
        f"entity_{source_dataset}",
        source_dataset,
    ]
    table_name = None
    for name in possible_names:
        if db.has_table(name):
            table_name = name
            break

    if not table_name:
        raise HTTPException(
            status_code=404,
            detail=f"Source dataset '{source_dataset}' not found",
        )

    # Find entity with most occurrences at first level
    try:
        query = f"""
            SELECT "{column_name}", COUNT(*) as cnt
            FROM {table_name}
            WHERE "{column_name}" IS NOT NULL AND "{column_name}" != ''
            GROUP BY "{column_name}"
            ORDER BY cnt DESC
            LIMIT 1
        """
        result = pd.read_sql(query, db.engine)

        if result.empty:
            raise HTTPException(
                status_code=400,
                detail=f"No data found for level '{first_level}'",
            )

        return {
            "level": first_level,
            "column": column_name,
            "value": result.iloc[0][column_name],
            "count": int(result.iloc[0]["cnt"]),
            "table_name": table_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error finding representative entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _find_entity_by_id(
    db: Database, hierarchy_info: Dict[str, Any], entity_id: str
) -> Dict[str, Any]:
    """Find a specific entity by its ID for preview.

    Generic implementation that reads import.yml to determine:
    - ID field for the reference
    - Name field for display
    - Link to occurrences (if any)

    Works with hierarchical (taxons), flat (plots), and spatial (shapes) references.
    """
    source_dataset = hierarchy_info["source_dataset"]
    reference_name = hierarchy_info.get("reference_name", "taxons")

    # Find the occurrences table
    possible_names = [
        f"dataset_{source_dataset}",
        f"entity_{source_dataset}",
        source_dataset,
    ]
    table_name = None
    for name in possible_names:
        if db.has_table(name):
            table_name = name
            break

    if not table_name:
        raise HTTPException(
            status_code=404,
            detail=f"Source dataset '{source_dataset}' not found",
        )

    # Find the entity in entity_{reference} table
    entity_table = f"entity_{reference_name}"
    if not db.has_table(entity_table):
        return _find_representative_entity(db, hierarchy_info)

    # Read import.yml for reference configuration
    work_dir = get_working_directory()
    ref_config = {}
    if work_dir:
        import_path = Path(work_dir) / "config" / "import.yml"
        if import_path.exists():
            try:
                with open(import_path, "r", encoding="utf-8") as f:
                    import_config = yaml.safe_load(f) or {}
                references = import_config.get("entities", {}).get("references", {})
                ref_config = references.get(reference_name, {})
            except Exception:
                pass

    # Get schema info
    schema = ref_config.get("schema", {})
    id_field = schema.get("id_field", "id")
    kind = ref_config.get("kind")  # hierarchical, spatial, or None

    # Get entity columns
    columns_df = pd.read_sql(f"SELECT * FROM {entity_table} LIMIT 0", db.engine)
    columns = columns_df.columns.tolist()

    # Determine name field
    name_candidates = ["full_name", "name", "plot", "label", "title"]
    name_field = next((c for c in name_candidates if c in columns), id_field)

    try:
        if kind == "hierarchical":
            # Hierarchical reference (taxons): use rank-based filtering
            entity_query = f"""
                SELECT id, rank_name, rank_value, full_name, taxons_id
                FROM {entity_table}
                WHERE id = {entity_id}
            """
            entity_result = pd.read_sql(entity_query, db.engine)

            if entity_result.empty:
                raise HTTPException(
                    status_code=404, detail=f"Entity '{entity_id}' not found"
                )

            entity = entity_result.iloc[0]
            rank_name = entity["rank_name"]
            rank_value = entity["rank_value"]
            full_name = entity["full_name"]

            # Determine filter column based on rank
            if rank_name in ("family", "genus"):
                column = rank_name
                value = rank_value
            else:
                taxons_id = entity.get("taxons_id")
                if pd.notna(taxons_id):
                    column = "id_taxonref"
                    value = int(taxons_id)
                else:
                    column = "species"
                    value = rank_value

            # Count occurrences
            try:
                count_result = pd.read_sql(
                    f"SELECT COUNT(*) as cnt FROM {table_name} WHERE \"{column}\" = '{value}'",
                    db.engine,
                )
                count = (
                    int(count_result.iloc[0]["cnt"]) if not count_result.empty else 0
                )
            except Exception:
                count = 0

            return {
                "level": rank_name,
                "column": column,
                "value": value,
                "count": count,
                "table_name": table_name,
                "entity_name": full_name,
            }

        else:
            # Flat or spatial reference (plots, shapes): use relation key to filter occurrences
            # Get relation info from hierarchy_info or transform.yml
            relation = hierarchy_info.get("relation", {})
            relation_key = relation.get(
                "key"
            )  # Column in occurrences (e.g., "plots_id")

            # If no relation info, try to read from transform.yml
            if not relation_key:
                transform_path = Path(work_dir) / "config" / "transform.yml"
                if transform_path.exists():
                    try:
                        with open(transform_path, "r", encoding="utf-8") as f:
                            transform_config = yaml.safe_load(f) or []
                        for group in transform_config:
                            if group.get("group_by") == reference_name:
                                sources = group.get("sources", [])
                                if sources:
                                    relation = sources[0].get("relation", {})
                                    relation_key = relation.get("key")
                                break
                    except Exception:
                        pass

            # If we have a relation key, use it to filter occurrences
            if relation_key:
                # Get the ref_field (column in entity table that matches relation_key in occurrences)
                ref_field = relation.get("ref_field", id_field)

                # First, get the entity from entity_table to find the matching value
                entity_query = f"""
                    SELECT *
                    FROM {entity_table}
                    WHERE "{id_field}" = {entity_id}
                """
                entity_result = pd.read_sql(entity_query, db.engine)

                if entity_result.empty:
                    raise HTTPException(
                        status_code=404, detail=f"Entity '{entity_id}' not found"
                    )

                entity = entity_result.iloc[0]
                entity_name = str(entity.get(name_field, entity_id))

                # Get the value to match in occurrences (from ref_field column)
                match_value = entity.get(ref_field, entity_id)

                # Count occurrences for this entity using the matching value
                try:
                    # Escape the value for SQL
                    escaped_value = str(match_value).replace("'", "''")
                    count_result = pd.read_sql(
                        f"SELECT COUNT(*) as cnt FROM {table_name} WHERE \"{relation_key}\" = '{escaped_value}'",
                        db.engine,
                    )
                    count = (
                        int(count_result.iloc[0]["cnt"])
                        if not count_result.empty
                        else 0
                    )
                except Exception:
                    count = 0

                return {
                    "level": reference_name,
                    "column": relation_key,
                    "value": match_value,  # Use the actual matching value (e.g., plot name)
                    "count": count,
                    "table_name": table_name,  # Use occurrences table
                    "entity_name": entity_name,
                }

            # Fallback: use entity table directly (for shapes without occurrences)
            entity_query = f"""
                SELECT *
                FROM {entity_table}
                WHERE "{id_field}" = {entity_id}
            """
            entity_result = pd.read_sql(entity_query, db.engine)

            if entity_result.empty:
                raise HTTPException(
                    status_code=404, detail=f"Entity '{entity_id}' not found"
                )

            entity = entity_result.iloc[0]
            entity_name = str(entity.get(name_field, entity_id))

            result = {
                "level": reference_name,
                "column": id_field,
                "value": entity_id,
                "count": 0,
                "table_name": entity_table,
                "entity_name": entity_name,
                "entity_data": entity.to_dict(),
                "source_type": "entity",
            }

            # For spatial references, include geometry for ST_Contains queries
            if kind == "spatial":
                location = entity.get("location")
                if location:
                    result["geometry"] = str(location)
                    result["spatial_query"] = True
                    result["kind"] = "spatial"
                    if "type" in entity.index:
                        result["shape_type"] = entity.get("type")

            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error finding entity by ID '{entity_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _load_sample_data(
    db: Database,
    representative: Dict[str, Any],
    template_config: Dict[str, Any],
    limit: int = None,  # None = no limit (all data)
) -> pd.DataFrame:
    """Load sample data for the representative entity.

    Works with:
    - Hierarchical references (taxons): filters occurrences by column/value
    - Flat references (plots): filters occurrences by relation key
    - Spatial references (shapes): uses ST_Contains to find occurrences in polygon

    Args:
        limit: Max rows to load. None for all data, or int for random sampling.
    """
    # For entity-sourced data that doesn't need occurrence filtering
    # (e.g., entity_map showing the shape itself)
    if representative.get("source_type") == "entity" and representative.get(
        "entity_data"
    ):
        entity_data = representative["entity_data"]
        # Convert single entity dict to DataFrame (single row)
        return pd.DataFrame([entity_data])

    # Get required field from template config
    required_field = template_config.get("field", "*")

    # For spatial references with geometry, use ST_Contains
    if representative.get("spatial_query") and representative.get("geometry"):
        geometry = representative["geometry"]
        occurrences_table = "dataset_occurrences"

        # Check if occurrences table exists
        if not db.has_table(occurrences_table):
            occurrences_table = "occurrences"
            if not db.has_table(occurrences_table):
                # No occurrences table, return entity data if available
                entity_data = representative.get("entity_data")
                if entity_data:
                    return pd.DataFrame([entity_data])
                return pd.DataFrame()

        # Find the geometry column in occurrences (usually geo_pt)
        cols_df = pd.read_sql(f"SELECT * FROM {occurrences_table} LIMIT 0", db.engine)
        geo_candidates = ["geo_pt", "geometry", "geom", "location", "point"]
        geo_col = next((c for c in geo_candidates if c in cols_df.columns), None)

        if not geo_col:
            # No geometry column in occurrences, can't do spatial query
            logger.warning(f"No geometry column found in {occurrences_table}")
            return pd.DataFrame()

        # Build the SELECT clause
        if required_field != "*":
            select_clause = f'"{required_field}"'
        else:
            select_clause = "*"

        # Build spatial query with ST_Contains
        # Note: Shape is a polygon, occurrence is a point
        # Escape single quotes in geometry
        escaped_geometry = geometry.replace("'", "''")

        try:
            from sqlalchemy import text

            # Use raw connection to execute multi-statement query
            with db.engine.connect() as conn:
                # Load spatial extension first (using text() for raw SQL)
                conn.execute(text("INSTALL spatial"))
                conn.execute(text("LOAD spatial"))

                # Then run the actual query
                select_query = f"""
                    SELECT {select_clause}
                    FROM {occurrences_table}
                    WHERE ST_Contains(
                        ST_GeomFromText('{escaped_geometry}'),
                        ST_GeomFromText("{geo_col}")
                    )
                """
                if limit:
                    select_query += f" ORDER BY RANDOM() LIMIT {limit}"
                return pd.read_sql(text(select_query), conn)
        except Exception as e:
            logger.warning(f"Spatial query failed: {e}, trying simpler approach")
            # If spatial query fails, return empty (shape without occurrences)
            return pd.DataFrame()

    # Standard flow for occurrence-based data (hierarchical and flat references)
    table_name = representative["table_name"]
    column = representative["column"]
    value = representative["value"]

    # Escape single quotes in value for SQL
    escaped_value = str(value).replace("'", "''")

    # Build query - with optional random sampling
    if required_field != "*":
        # Avoid selecting the same column twice
        if required_field == column:
            query = f"""
                SELECT "{required_field}"
                FROM {table_name}
                WHERE "{column}" = '{escaped_value}'
            """
        else:
            query = f"""
                SELECT "{required_field}", "{column}"
                FROM {table_name}
                WHERE "{column}" = '{escaped_value}'
            """
    else:
        query = f"""
            SELECT *
            FROM {table_name}
            WHERE "{column}" = '{escaped_value}'
        """

    # Add random sampling if limit is specified
    if limit:
        query += f" ORDER BY RANDOM() LIMIT {limit}"

    try:
        return pd.read_sql(query, db.engine)
    except Exception as e:
        logger.exception(f"Error loading sample data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _execute_transformer(
    db: Database, plugin_name: str, data: pd.DataFrame, config: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a transformer plugin on sample data."""
    try:
        plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.TRANSFORMER)
        plugin_instance = plugin_class(db=db)

        # Build config in expected format
        full_config = {"plugin": plugin_name, "params": config}

        return plugin_instance.transform(data, full_config)
    except Exception as e:
        logger.exception(f"Error executing transformer '{plugin_name}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transformer error: {str(e)}",
        )


def _find_widget_for_transformer(transformer_name: str) -> Optional[str]:
    """Use SmartMatcher to find a compatible widget for a transformer.

    Returns the name of the best compatible widget, or None if no match found.
    """
    try:
        transformer_class = PluginRegistry.get_plugin(
            transformer_name, PluginType.TRANSFORMER
        )
        matcher = SmartMatcher()
        suggestions = matcher.find_compatible_widgets(transformer_class)

        if suggestions:
            # Return the best match (highest score)
            return suggestions[0].widget_name
        return None
    except Exception as e:
        logger.warning(
            f"Error finding widget for transformer '{transformer_name}': {e}"
        )
        return None


def _parse_dynamic_template_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Parse a dynamic template ID into column, transformer, and widget.

    Dynamic template IDs have the format: {column}_{transformer}_{widget}
    Examples:
        - height_binned_distribution_bar_plot
        - geo_pt_geospatial_extractor_interactive_map
        - species_categorical_distribution_donut_chart
        - dbh_series_extractor_bar_plot (class_object)

    Returns dict with 'column', 'transformer', 'widget' or None if not parseable.
    """
    # Known widget names (from PluginRegistry)
    widget_names = [
        "bar_plot",
        "donut_chart",
        "interactive_map",
        "radial_gauge",
        "info_grid",
    ]

    # Known transformer names (real transformers + class_object extractors)
    transformer_names = [
        # Real transformer plugins
        "binned_distribution",
        "categorical_distribution",
        "statistical_summary",
        "top_ranking",
        "binary_counter",
        "field_aggregator",
        "geospatial_extractor",
        "time_series_analysis",
        # Class_object extractors (for pre-calculated CSV data)
        "series_extractor",
        "binary_aggregator",
        "categories_extractor",
    ]

    # Try to match widget from the end
    matched_widget = None
    for widget in widget_names:
        if template_id.endswith(f"_{widget}"):
            matched_widget = widget
            break

    if not matched_widget:
        return None

    # Remove widget suffix
    remaining = template_id[: -(len(matched_widget) + 1)]

    # Try to match transformer
    matched_transformer = None
    for transformer in transformer_names:
        if remaining.endswith(f"_{transformer}"):
            matched_transformer = transformer
            break

    if not matched_transformer:
        return None

    # Extract column name
    column = remaining[: -(len(matched_transformer) + 1)]
    if not column:
        return None

    return {
        "column": column,
        "transformer": matched_transformer,
        "widget": matched_widget,
    }


def _build_widget_params_dynamic(
    transformer: str, widget: str, config: Dict[str, Any], title: str, data: Any
) -> Dict[str, Any]:
    """Build widget parameters based on transformer output and widget type.

    The parameters depend on BOTH:
    - The transformer's output structure (what fields are available)
    - The widget's expected input (what parameters it needs)
    """
    # Widget-specific parameters based on transformer output
    if widget == "bar_plot":
        if transformer == "binned_distribution":
            return {
                "x_axis": "bin",
                "y_axis": "count",
                "title": title,
                "orientation": "v",
                "transform": "bins_to_df",
                "transform_params": {
                    "bin_field": "bins",
                    "count_field": "counts",
                    "use_percentages": True,
                    "percentage_field": "percentages",
                    "x_field": "bin",
                    "y_field": "count",
                },
                "gradient_color": "#10b981",
                "gradient_mode": "luminance",
                "show_legend": False,
            }
        elif transformer == "top_ranking":
            return {
                "x_axis": "counts",
                "y_axis": "tops",
                "title": title,
                "orientation": "h",
                "sort_order": "ascending",
                "auto_color": True,
            }
        elif transformer == "categorical_distribution":
            # categorical_distribution outputs {labels/categories: [...], counts: [...]}
            labels_field = (
                "labels"
                if isinstance(data, dict) and "labels" in data
                else "categories"
            )
            return {
                "x_axis": labels_field,
                "y_axis": "counts",
                "title": title,
                "orientation": "v",
                "gradient_color": "#10b981",
                "gradient_mode": "luminance",
                "show_legend": False,
            }

    elif widget == "donut_chart":
        if transformer == "binned_distribution":
            # After preprocessing: {labels: [...], counts: [...]}
            return {
                "values_field": "counts",
                "labels_field": "labels",
                "title": title,
            }
        elif transformer == "categorical_distribution":
            # categorical_distribution outputs {labels/categories: [...], counts: [...]}
            labels_field = (
                "labels"
                if isinstance(data, dict) and "labels" in data
                else "categories"
            )
            return {
                "values_field": "counts",
                "labels_field": labels_field,
                "title": title,
            }
        elif transformer == "binary_counter":
            return {
                "values_field": "counts",
                "labels_field": "labels",
                "title": title,
            }

    elif widget == "radial_gauge":
        if transformer == "statistical_summary":
            max_value = config.get("max_value", 100)
            stats = config.get("stats", ["mean"])
            value_field = stats[0] if stats else "mean"
            return {
                "value_field": value_field,
                "max_value": max_value,
                "title": title,
                "unit": config.get("units", ""),
            }

    elif widget == "interactive_map":
        if transformer == "geospatial_extractor":
            return {
                "map_type": "scatter_map",
                "map_style": "carto-positron",
                "latitude_field": "latitude",
                "longitude_field": "longitude",
                "auto_zoom": True,
                "zoom": 8,
                "title": title,
                "opacity": 0.8,
                "size_max": 10,
            }

    elif widget == "info_grid":
        if transformer == "field_aggregator":
            return {
                "title": title,
                "columns": 2,
            }

    # Default fallback
    return {"title": title}


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
    <script src="https://cdn.jsdelivr.net/npm/plotly.js@2.35.0/dist/plotly.min.js"></script>
</head>
<body>
{content}
</body>
</html>"""


async def _preview_navigation_widget(reference_name: str) -> HTMLResponse:
    """Generate a preview for a navigation widget using the real widget renderer.

    Uses the actual hierarchical_nav_widget plugin with sample data to provide
    a faithful preview of the final rendered widget.

    Args:
        reference_name: Name of the reference (e.g., 'taxons', 'plots')

    Returns:
        HTMLResponse with the rendered widget
    """
    import json
    from pathlib import Path

    try:
        db_path = get_database_path()
        if not db_path:
            return HTMLResponse(
                content=_wrap_html_response(
                    "<p class='info'>Base de données non configurée</p>"
                )
            )

        db = Database(str(db_path), read_only=True)
        try:
            # Find the reference table
            table_name = f"reference_{reference_name}"
            if not db.has_table(table_name):
                for alt_name in [reference_name, f"entity_{reference_name}"]:
                    if db.has_table(alt_name):
                        table_name = alt_name
                        break
                else:
                    return HTMLResponse(
                        content=_wrap_html_response(
                            f"<p class='info'>Table '{reference_name}' non trouvée</p>"
                        )
                    )

            # Get column info to detect hierarchy
            columns_df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 0", db.engine)
            columns = set(columns_df.columns.tolist())

            has_nested_set = "lft" in columns and "rght" in columns
            has_parent = "parent_id" in columns
            has_level = "level" in columns
            is_hierarchical = has_nested_set or (has_parent and has_level)

            # Detect ID field
            id_candidates = [f"id_{reference_name}", f"{reference_name}_id", "id"]
            id_field = next((c for c in id_candidates if c in columns), None)
            if not id_field:
                id_field = next((c for c in columns if "id" in c.lower()), "id")

            # Detect name field
            name_candidates = ["full_name", "name", "plot", "label", "title"]
            name_field = next((c for c in name_candidates if c in columns), id_field)

            # Build query to get sample data for preview (limit to first levels)
            if is_hierarchical and has_nested_set:
                # Get hierarchical sample ordered by nested set
                query = f"""
                    SELECT *
                    FROM {table_name}
                    WHERE level <= 3
                    ORDER BY lft
                    LIMIT 50
                """
            elif is_hierarchical and has_parent:
                # Get parent-child sample
                query = f"""
                    SELECT *
                    FROM {table_name}
                    WHERE level <= 3
                    LIMIT 50
                """
            else:
                # Get flat sample
                query = f"""
                    SELECT *
                    FROM {table_name}
                    LIMIT 30
                """

            sample_df = pd.read_sql(query, db.engine)
            items = sample_df.to_dict(orient="records")

            # Get total count for info
            count_df = pd.read_sql(
                f"SELECT COUNT(*) as cnt FROM {table_name}", db.engine
            )
            _total_count = int(count_df.iloc[0]["cnt"])  # noqa: F841

            # Load CSS and JS assets
            assets_path = (
                Path(__file__).parent.parent.parent.parent / "publish" / "assets"
            )
            css_content = ""
            js_content = ""

            css_file = assets_path / "css" / "niamoto_hierarchical_nav.css"
            js_file = assets_path / "js" / "niamoto_hierarchical_nav.js"

            if css_file.exists():
                css_content = css_file.read_text()
            if js_file.exists():
                js_content = js_file.read_text()

            # Build widget config
            widget_id = f"hierarchical-nav-{reference_name.replace('_', '-')}"
            container_id = f"{widget_id}-container"
            search_id = f"{widget_id}-search"

            # Build JS config
            js_config = {
                "containerId": container_id,
                "searchInputId": search_id,
                "items": items,
                "params": {
                    "idField": id_field,
                    "nameField": name_field,
                    "parentIdField": "parent_id" if has_parent else None,
                    "lftField": "lft" if has_nested_set else None,
                    "rghtField": "rght" if has_nested_set else None,
                    "levelField": "level" if has_level else None,
                    "flatMode": not is_hierarchical,
                    "baseUrl": "#",  # Disable links in preview
                },
                "currentItemId": None,
            }

            # Build the preview HTML with real widget (neutral design)
            preview_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: system-ui, -apple-system, sans-serif;
            background: white;
        }}
        .preview-container {{
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .preview-content {{
            flex: 1;
            overflow: auto;
            padding: 16px;
        }}
        /* Widget styles */
        {css_content}
        /* Override for preview */
        .tree-node-link, .tree-node a {{
            pointer-events: none;
            cursor: default;
        }}
    </style>
</head>
<body>
    <div class="preview-container">
        <div class="preview-content">
            <!-- Search input -->
            <div class="mb-4">
                <input type="text"
                       id="{search_id}"
                       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                       placeholder="Rechercher...">
            </div>
            <!-- Tree container -->
            <div id="{container_id}" class="hierarchical-nav-tree" role="tree"></div>
        </div>
    </div>

    <script>
    {js_content}
    </script>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        if (typeof NiamotoHierarchicalNav !== 'undefined') {{
            new NiamotoHierarchicalNav({json.dumps(js_config, ensure_ascii=False)});
        }}
    }});
    </script>
</body>
</html>
"""
            return HTMLResponse(content=preview_html)

        finally:
            db.close_db_session()

    except Exception as e:
        logger.exception(f"Error generating navigation preview: {e}")
        return HTMLResponse(
            content=_wrap_html_response(f"<p class='error'>Erreur: {str(e)}</p>"),
            status_code=500,
        )


async def _preview_general_info_widget(
    reference_name: str, entity_id: Optional[int] = None
) -> HTMLResponse:
    """Generate a preview for a general_info widget (field_aggregator + info_grid).

    Dynamically detects fields from the reference table and shows sample values.

    Args:
        reference_name: Name of the reference (e.g., 'taxons', 'plots')
        entity_id: Optional specific entity ID to preview

    Returns:
        HTMLResponse with the rendered widget preview
    """
    import json as json_module

    try:
        db_path = get_database_path()
        if not db_path:
            return HTMLResponse(
                content=_wrap_html_response(
                    "<p class='info'>Base de données non configurée</p>"
                )
            )

        db = Database(str(db_path), read_only=True)
        try:
            # Generate the suggestion to get the detected fields
            suggestion = _generate_general_info_suggestion(reference_name)
            if not suggestion:
                return HTMLResponse(
                    content=_wrap_html_response(
                        f"<p class='info'>Aucun champ détecté pour '{reference_name}'</p>"
                    )
                )

            field_configs = suggestion["config"]["params"]["fields"]

            # Find the reference table
            ref_table = f"reference_{reference_name}"
            if not db.has_table(ref_table):
                for alt_name in [reference_name, f"entity_{reference_name}"]:
                    if db.has_table(alt_name):
                        ref_table = alt_name
                        break
                else:
                    return HTMLResponse(
                        content=_wrap_html_response(
                            f"<p class='info'>Table '{reference_name}' non trouvée</p>"
                        )
                    )

            # Get a sample entity
            if entity_id:
                sample_query = (
                    f"SELECT * FROM {ref_table} WHERE id = {entity_id} LIMIT 1"
                )
            else:
                sample_query = f"SELECT * FROM {ref_table} LIMIT 1"

            sample_df = pd.read_sql(sample_query, db.engine)
            if sample_df.empty:
                return HTMLResponse(
                    content=_wrap_html_response(
                        f"<p class='info'>Aucune donnée dans '{reference_name}'</p>"
                    )
                )

            sample_row = sample_df.iloc[0].to_dict()

            # Build preview data by extracting field values
            preview_items = []
            for field_config in field_configs:
                source = field_config.get("source", reference_name)
                field = field_config.get("field", "")
                target = field_config.get("target", field)
                transformation = field_config.get("transformation")

                value = None

                if transformation == "count":
                    # For count, show a placeholder
                    value = "(comptage)"
                elif "." in field:
                    # JSON field access
                    json_field, json_key = field.split(".", 1)
                    if json_field in sample_row:
                        json_data = sample_row[json_field]
                        if isinstance(json_data, str):
                            try:
                                json_data = json_module.loads(json_data)
                            except (ValueError, TypeError):
                                json_data = {}
                        if isinstance(json_data, dict):
                            value = json_data.get(json_key)
                elif source == reference_name and field in sample_row:
                    value = sample_row[field]

                # Format value for display
                if value is None:
                    display_value = "—"
                elif isinstance(value, bool):
                    display_value = "Oui" if value else "Non"
                else:
                    display_value = str(value)[:100]  # Truncate long values

                preview_items.append(
                    {
                        "label": target.replace("_", " ").title(),
                        "value": display_value,
                        "source": source,
                        "field": field,
                    }
                )

            # Build the preview HTML
            ref_label = reference_name.replace("_", " ").title()
            items_html = ""
            for item in preview_items:
                items_html += f"""
                <div class="info-item">
                    <div class="info-label">{item["label"]}</div>
                    <div class="info-value">{item["value"]}</div>
                    <div class="info-source">{item["source"]}.{item["field"]}</div>
                </div>
                """

            preview_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            margin: 0;
            padding: 16px;
            font-family: system-ui, -apple-system, sans-serif;
            background: white;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }}
        .info-item {{
            padding: 12px;
            background: #f9fafb;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }}
        .info-label {{
            font-size: 12px;
            font-weight: 500;
            color: #6b7280;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .info-value {{
            font-size: 16px;
            font-weight: 600;
            color: #111827;
            word-break: break-word;
        }}
        .info-source {{
            font-size: 10px;
            color: #9ca3af;
            margin-top: 4px;
            font-family: monospace;
        }}
        .preview-header {{
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .preview-title {{
            font-size: 18px;
            font-weight: 600;
            color: #111827;
        }}
        .preview-subtitle {{
            font-size: 13px;
            color: #6b7280;
            margin-top: 4px;
        }}
    </style>
</head>
<body>
    <div class="preview-header">
        <div class="preview-title">Informations générales</div>
        <div class="preview-subtitle">{len(preview_items)} champs détectés pour {ref_label}</div>
    </div>
    <div class="info-grid">
        {items_html}
    </div>
</body>
</html>
"""
            return HTMLResponse(content=preview_html)

        finally:
            db.close_db_session()

    except Exception as e:
        logger.exception(f"Error generating general_info preview: {e}")
        return HTMLResponse(
            content=_wrap_html_response(f"<p class='error'>Erreur: {str(e)}</p>"),
            status_code=500,
        )


def _parse_wkt_to_geojson(wkt: str) -> Optional[Dict[str, Any]]:
    """Parse WKT geometry string to GeoJSON geometry object.

    Handles POINT, POLYGON, MULTIPOLYGON with optional Z coordinates.

    Args:
        wkt: WKT string like "POINT (lon lat)" or "MULTIPOLYGON Z (((x y z, ...)))"

    Returns:
        GeoJSON geometry dict or None if parsing fails
    """
    import re

    if not wkt or wkt in ("None", "nan", ""):
        return None

    wkt = wkt.strip()

    # Handle POINT (with or without Z)
    if wkt.startswith("POINT"):
        # POINT (lon lat) or POINT Z (lon lat z)
        match = re.search(r"POINT\s*Z?\s*\(\s*([^)]+)\s*\)", wkt)
        if match:
            coords_str = match.group(1).strip()
            parts = coords_str.split()
            if len(parts) >= 2:
                lon, lat = float(parts[0]), float(parts[1])
                return {"type": "Point", "coordinates": [lon, lat]}
        return None

    # Handle MULTIPOLYGON (with or without Z)
    if wkt.startswith("MULTIPOLYGON"):
        # Extract all polygon rings
        # MULTIPOLYGON Z (((x1 y1 z1, x2 y2 z2, ...)), ((x1 y1 z1, ...)))
        polygons = []

        # Find all ((...)) groups - each is a polygon
        polygon_pattern = r"\(\(([^()]+(?:\([^()]+\)[^()]*)*)\)\)"
        polygon_matches = re.findall(polygon_pattern, wkt)

        for poly_coords in polygon_matches:
            rings = []
            # Split by inner rings if any - for now just handle outer ring
            ring_coords = []
            for coord_pair in poly_coords.split(","):
                parts = coord_pair.strip().split()
                if len(parts) >= 2:
                    ring_coords.append([float(parts[0]), float(parts[1])])
            if ring_coords:
                rings.append(ring_coords)
                polygons.append(rings)

        if polygons:
            return {"type": "MultiPolygon", "coordinates": polygons}
        return None

    # Handle POLYGON (with or without Z)
    if wkt.startswith("POLYGON"):
        # POLYGON ((x1 y1, x2 y2, ...)) or POLYGON Z ((x1 y1 z1, ...))
        match = re.search(r"POLYGON\s*Z?\s*\(\(([^)]+)\)\)", wkt)
        if match:
            coords_str = match.group(1)
            coords = []
            for coord_pair in coords_str.split(","):
                parts = coord_pair.strip().split()
                if len(parts) >= 2:
                    coords.append([float(parts[0]), float(parts[1])])
            if coords:
                return {"type": "Polygon", "coordinates": [coords]}
        return None

    return None


async def _preview_entity_map(
    template_id: str,
    entity_id: Optional[str] = None,
) -> HTMLResponse:
    """Generate a preview map for entity-based maps.

    Parses the template_id to extract reference name and geometry column,
    then queries the entity table to generate a map.

    Template ID formats:
    - {reference}_{geom_col}_entity_map  -> single entity
    - {reference}_{geom_col}_all_map     -> all entities
    - {reference}_{geom_col}_{type}_map  -> all entities of a specific entity_type

    Args:
        template_id: Template ID in format {reference}_{geom_col}_{mode}_map
        entity_id: ID of the entity to show (for single/entity mode)

    Returns:
        HTMLResponse with interactive map
    """
    from niamoto.common.database import Database

    db_path = get_database_path()
    if not db_path:
        return HTMLResponse(
            content=_wrap_html_response("<p class='error'>Database not found</p>"),
            status_code=404,
        )

    # Parse template_id to extract reference, geom_col, mode, and optionally entity_type
    # Format: {reference}_{geom_col}_entity_map, {reference}_{geom_col}_all_map,
    #         or {reference}_{geom_col}_{type_slug}_map
    entity_type_filter = None

    if template_id.endswith("_entity_map"):
        mode = "single"
        prefix = template_id[:-11]  # Remove "_entity_map"
    elif template_id.endswith("_all_map"):
        mode = "all"
        prefix = template_id[:-8]  # Remove "_all_map"
    elif template_id.endswith("_map"):
        # Type-based map: {reference}_{geom_col}_{type_slug}_map
        mode = "type"
        prefix = template_id[:-4]  # Remove "_map"
    else:
        return HTMLResponse(
            content=_wrap_html_response(
                f"<p class='error'>Invalid entity map template: {template_id}</p>"
            ),
            status_code=400,
        )

    # Split prefix to get reference, geom_col, and optionally type_slug
    # e.g., "plots_geo_pt" -> reference="plots", geom_col="geo_pt"
    # e.g., "shapes_location_provinces" -> reference="shapes", geom_col="location", type_slug="provinces"
    parts = prefix.split("_")
    if len(parts) < 2:
        return HTMLResponse(
            content=_wrap_html_response(
                f"<p class='error'>Cannot parse template ID: {template_id}</p>"
            ),
            status_code=400,
        )

    # First part is reference
    reference = parts[0]

    if mode == "type" and len(parts) >= 3:
        # For type mode, try to find the geometry column and type slug
        # Common geometry columns: geo_pt, location, geometry
        common_geom_cols = [
            "geo_pt",
            "location",
            "geometry",
            "geom",
            "polygon",
            "point",
        ]

        # Check if second part is a known geometry column
        if parts[1] in common_geom_cols:
            geom_col = parts[1]
            entity_type_filter = "_".join(parts[2:])  # Rest is type slug
        else:
            # Try to match by checking database
            geom_col = parts[1]
            entity_type_filter = "_".join(parts[2:])
    else:
        # For single/all mode: rest is geom_col
        geom_col = "_".join(parts[1:])

    db = Database(str(db_path), read_only=True)

    try:
        entity_table = f"entity_{reference}"

        if not db.has_table(entity_table):
            return HTMLResponse(
                content=_wrap_html_response(
                    f"<p class='error'>Table '{entity_table}' not found</p>"
                ),
                status_code=404,
            )

        # Get columns to detect name and id fields
        columns_df = pd.read_sql(f"SELECT * FROM {entity_table} LIMIT 0", db.engine)
        columns = columns_df.columns.tolist()

        # Detect name field
        name_candidates = ["full_name", "name", "plot", "label", "title", reference]
        name_field = next((c for c in name_candidates if c in columns), None)
        if not name_field:
            name_field = next((c for c in columns if "name" in c.lower()), "id")

        # Detect ID field
        id_candidates = [f"id_{reference}", f"{reference}_id", "id", "id_plot"]
        id_field = next((c for c in id_candidates if c in columns), None)
        if not id_field:
            id_field = next(
                (c for c in columns if c.lower().startswith("id")), columns[0]
            )

        # Detect geometry type from sample data
        sample = pd.read_sql(
            f'SELECT "{geom_col}" FROM {entity_table} WHERE "{geom_col}" IS NOT NULL LIMIT 1',
            db.engine,
        )
        # Detect geometry type (for future use)
        if not sample.empty:
            val = str(sample.iloc[0][geom_col])
            _is_polygon = val.startswith("POLYGON") or val.startswith("MULTIPOLYGON")  # noqa: F841

        # Build query based on mode
        if mode == "single":
            # For single mode, find a representative entity if no entity_id provided
            if not entity_id:
                # Get first entity with valid geometry
                rep_query = f"""
                    SELECT "{id_field}" as id
                    FROM {entity_table}
                    WHERE "{geom_col}" IS NOT NULL
                    LIMIT 1
                """
                rep_result = pd.read_sql(rep_query, db.engine)
                if not rep_result.empty:
                    entity_id = rep_result.iloc[0]["id"]

            if entity_id:
                query = f"""
                    SELECT "{id_field}" as id, "{name_field}" as name, "{geom_col}" as geom
                    FROM {entity_table}
                    WHERE "{id_field}" = '{entity_id}'
                """
            else:
                # Fallback if no entity found
                query = f"""
                    SELECT "{id_field}" as id, "{name_field}" as name, "{geom_col}" as geom
                    FROM {entity_table}
                    WHERE "{geom_col}" IS NOT NULL
                    LIMIT 1
                """
        elif mode == "type" and entity_type_filter:
            # For type mode, find which column contains the type value
            # Search text columns for a match, preferring columns with multiple occurrences
            filter_normalized = entity_type_filter.lower().replace("_", " ")
            matched_column = None
            matched_value = None
            best_count = 0

            # Candidate columns for type filtering (exclude id, geometry, and numeric columns)
            type_candidate_cols = [
                c
                for c in columns
                if c.lower()
                not in [
                    id_field.lower(),
                    geom_col.lower(),
                    "id",
                    "lft",
                    "rght",
                    "level",
                    "parent_id",
                ]
                and not c.endswith("_id")
            ]

            # Prioritize columns named 'type', 'category', 'group'
            priority_cols = ["type", "category", "group", "shape_type", "entity_type"]
            sorted_cols = sorted(
                type_candidate_cols,
                key=lambda c: 0 if c.lower() in priority_cols else 1,
            )

            for col in sorted_cols:
                try:
                    # Get values with count
                    values_df = pd.read_sql(
                        f'SELECT "{col}", COUNT(*) as cnt FROM {entity_table} '
                        f'WHERE "{col}" IS NOT NULL GROUP BY "{col}"',
                        db.engine,
                    )

                    # Find matching value, prefer those with higher count
                    for _, row in values_df.iterrows():
                        val_str = str(row[col])
                        count = int(row["cnt"])
                        if (
                            val_str.lower().replace(" ", "_")
                            == entity_type_filter.lower()
                        ):
                            if count > best_count:
                                matched_column = col
                                matched_value = val_str
                                best_count = count
                        elif val_str.lower() == filter_normalized:
                            if count > best_count:
                                matched_column = col
                                matched_value = val_str
                                best_count = count
                except Exception:
                    continue

            if matched_column and matched_value:
                query = f"""
                    SELECT "{id_field}" as id, "{name_field}" as name, "{geom_col}" as geom
                    FROM {entity_table}
                    WHERE "{geom_col}" IS NOT NULL AND "{matched_column}" = '{matched_value}'
                    LIMIT 500
                """
            else:
                # Fallback to all
                query = f"""
                    SELECT "{id_field}" as id, "{name_field}" as name, "{geom_col}" as geom
                    FROM {entity_table}
                    WHERE "{geom_col}" IS NOT NULL
                    LIMIT 500
                """
        else:
            # Mode "all" - show all entities, but for shapes filter by type
            # Check if this is a shapes reference with entity_type column
            shape_type_filter = None
            if reference == "shapes" and "type" in columns and "entity_type" in columns:
                # Find a representative shape to get its type
                rep_query = f"""
                    SELECT "type"
                    FROM {entity_table}
                    WHERE entity_type = 'shape' AND "{geom_col}" IS NOT NULL
                    LIMIT 1
                """
                rep_result = pd.read_sql(rep_query, db.engine)
                if not rep_result.empty:
                    shape_type_filter = rep_result.iloc[0]["type"]

            if shape_type_filter:
                # Filter by the representative shape's type
                query = f"""
                    SELECT "{id_field}" as id, "{name_field}" as name, "{geom_col}" as geom
                    FROM {entity_table}
                    WHERE "{geom_col}" IS NOT NULL AND entity_type = 'shape' AND "type" = '{shape_type_filter}'
                    LIMIT 500
                """
            else:
                # Standard all mode
                query = f"""
                    SELECT "{id_field}" as id, "{name_field}" as name, "{geom_col}" as geom
                    FROM {entity_table}
                    WHERE "{geom_col}" IS NOT NULL
                    LIMIT 500
                """

        result = pd.read_sql(query, db.engine)

        if result.empty:
            return HTMLResponse(
                content=_wrap_html_response(
                    "<p class='info'>Aucune donnée géographique disponible</p>"
                )
            )

        # Convert to GeoJSON features
        features = []
        for _, row in result.iterrows():
            geom_str = str(row["geom"])
            if not geom_str or geom_str == "None" or geom_str == "nan":
                continue

            # Parse WKT to GeoJSON geometry
            try:
                geometry = _parse_wkt_to_geojson(geom_str)
                if not geometry:
                    continue

                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "id": str(row["id"]),
                            "name": str(row["name"])
                            if pd.notna(row["name"])
                            else f"ID: {row['id']}",
                        },
                        "geometry": geometry,
                    }
                )
            except Exception as e:
                logger.warning(f"Error parsing geometry '{geom_str[:50]}...': {e}")
                continue

        if not features:
            return HTMLResponse(
                content=_wrap_html_response(
                    "<p class='info'>Aucune géométrie valide trouvée</p>"
                )
            )

        geojson = {"type": "FeatureCollection", "features": features}

        # Calculate center from features
        lons = []
        lats = []
        for f in features:
            geom = f["geometry"]
            if geom["type"] == "Point":
                lons.append(geom["coordinates"][0])
                lats.append(geom["coordinates"][1])
            elif geom["type"] == "Polygon":
                for coord in geom["coordinates"][0]:
                    lons.append(coord[0])
                    lats.append(coord[1])
            elif geom["type"] == "MultiPolygon":
                for polygon in geom["coordinates"]:
                    for ring in polygon:
                        for coord in ring:
                            lons.append(coord[0])
                            lats.append(coord[1])

        center_lon = sum(lons) / len(lons) if lons else 165.5
        center_lat = sum(lats) / len(lats) if lats else -21.5

        # Determine zoom based on mode
        zoom = 10 if mode == "single" else 7

        # Generate map HTML
        if mode == "single":
            title = "Position du plot" if reference == "plots" else "Polygone du shape"
        elif mode == "type" and entity_type_filter:
            title = f"Carte {entity_type_filter.replace('_', ' ').title()}"
        else:
            title = f"Tous les {reference}"

        map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{ margin: 0; padding: 0; height: 100%; }}
        #map {{ width: 100%; height: 100%; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const geojson = {json.dumps(geojson)};
        const map = L.map('map').setView([{center_lat}, {center_lon}], {zoom});

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors'
        }}).addTo(map);

        const geojsonLayer = L.geoJSON(geojson, {{
            style: function(feature) {{
                return {{
                    color: '#3b82f6',
                    weight: 2,
                    fillColor: '#3b82f6',
                    fillOpacity: 0.3
                }};
            }},
            pointToLayer: function(feature, latlng) {{
                return L.circleMarker(latlng, {{
                    radius: 8,
                    fillColor: '#3b82f6',
                    color: '#1e40af',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.7
                }});
            }},
            onEachFeature: function(feature, layer) {{
                if (feature.properties && feature.properties.name) {{
                    layer.bindPopup('<strong>' + feature.properties.name + '</strong>');
                }}
            }}
        }}).addTo(map);

        // Fit bounds to show all features
        if (geojson.features.length > 0) {{
            map.fitBounds(geojsonLayer.getBounds(), {{ padding: [20, 20] }});
        }}
    </script>
</body>
</html>
"""
        return HTMLResponse(content=map_html)

    except Exception as e:
        logger.exception(f"Error generating entity map preview: {e}")
        return HTMLResponse(
            content=_wrap_html_response(f"<p class='error'>Erreur: {str(e)}</p>"),
            status_code=500,
        )
    finally:
        db.close_db_session()


@router.get("/preview/{template_id}", response_class=HTMLResponse)
async def preview_template(
    template_id: str,
    group_by: str = Query(
        default=None, description="Group by reference (auto-detected if not provided)"
    ),
    entity_id: str = Query(
        default=None, description="Specific entity ID to use for preview"
    ),
):
    """
    Generate a live preview of a template widget on sample data.

    This endpoint:
    1. Parses the dynamic template ID to get column, transformer, and widget
    2. Finds a representative entity from a hierarchical reference
    3. Loads sample data for that entity
    4. Executes the transformer to generate widget data
    5. Renders the widget to HTML

    Template ID formats:
    - Navigation: {reference}_hierarchical_nav_widget (e.g., 'taxons_hierarchical_nav_widget')
    - Standard: {column}_{transformer}_{widget} (e.g., 'height_binned_distribution_bar_plot')

    Args:
        template_id: ID of the template to preview
        group_by: Reference to group by (auto-detected from import.yml if not provided)

    Returns:
        HTML content of the rendered widget
    """
    # Ensure plugins are loaded
    _ensure_plugins_loaded()

    # Check for navigation widget (special format: {reference}_hierarchical_nav_widget)
    if template_id.endswith("_hierarchical_nav_widget"):
        reference_name = template_id.replace("_hierarchical_nav_widget", "")
        return await _preview_navigation_widget(reference_name)

    # Check for general_info widget (special format: general_info_{reference}_field_aggregator_info_grid)
    if template_id.startswith("general_info_") and template_id.endswith(
        "_field_aggregator_info_grid"
    ):
        reference_name = template_id.replace("general_info_", "").replace(
            "_field_aggregator_info_grid", ""
        )
        return await _preview_general_info_widget(reference_name, entity_id)

    # Check for entity map templates (generic pattern: {reference}_{geom_col}_entity_map or _all_map)
    if template_id.endswith("_entity_map") or template_id.endswith("_all_map"):
        return await _preview_entity_map(template_id, entity_id)

    # Parse dynamic template ID
    parsed = _parse_dynamic_template_id(template_id)
    if not parsed:
        return HTMLResponse(
            content=_wrap_html_response(
                f"<p class='error'>Invalid template ID format: '{template_id}'</p>"
            ),
            status_code=400,
        )

    template_info = _build_dynamic_template_info(parsed, template_id)
    transformer_plugin = template_info["plugin"]
    widget_plugin = template_info["widget"]  # Widget is now part of the template ID
    config = template_info["config"]
    template_name = template_info["name"]

    # Verify the widget plugin exists
    try:
        PluginRegistry.get_plugin(widget_plugin, PluginType.WIDGET)
    except Exception:
        return HTMLResponse(
            content=_wrap_html_response(
                f"<p class='error'>Widget plugin '{widget_plugin}' not found</p>"
            ),
            status_code=400,
        )

    # Get working directory and load config
    work_dir = get_working_directory()
    if not work_dir:
        return HTMLResponse(
            content=_wrap_html_response(
                "<p class='error'>Working directory not configured</p>"
            ),
            status_code=500,
        )

    work_dir = Path(work_dir)
    column = parsed["column"]
    transformer = parsed["transformer"]

    try:
        # Check if this is a class_object template (pre-calculated CSV data)
        if _is_class_object_template(transformer):
            # Get reference name from query param or auto-detect
            reference_name = group_by
            if not reference_name:
                # Try to detect from import.yml
                import_config = _load_import_config(work_dir)
                hierarchy_info = _get_hierarchy_info(import_config)
                reference_name = hierarchy_info["reference_name"]

            # Load class_object data from CSV
            co_data = _load_class_object_data_for_preview(
                work_dir, column, reference_name
            )
            if not co_data:
                return HTMLResponse(
                    content=_wrap_html_response(
                        f"<p class='info'>Données '{column}' non trouvées dans les sources CSV</p>"
                    )
                )

            # Get database for widget rendering
            db_path = get_database_path()
            db = Database(str(db_path), read_only=True) if db_path else None

            try:
                # Render widget directly with class_object data
                widget_html = _render_widget_for_class_object(
                    db, widget_plugin, co_data, transformer, template_name
                )

                return HTMLResponse(
                    content=_wrap_html_response(widget_html, title=template_name)
                )
            finally:
                if db:
                    db.close_db_session()

        # Standard flow for occurrence-based templates
        # Load import.yml
        import_config = _load_import_config(work_dir)

        # Get reference info (uses group_by to get correct reference)
        hierarchy_info = _get_hierarchy_info(import_config, group_by)

        # Get database
        db_path = get_database_path()
        if not db_path:
            return HTMLResponse(
                content=_wrap_html_response("<p class='error'>Database not found</p>"),
                status_code=404,
            )

        db = Database(str(db_path), read_only=True)
        try:
            # Find representative entity (or use provided entity_id)
            if entity_id:
                representative = _find_entity_by_id(db, hierarchy_info, entity_id)
            else:
                representative = _find_representative_entity(db, hierarchy_info)

            # Load sample data
            sample_data = _load_sample_data(db, representative, config)

            if sample_data.empty:
                return HTMLResponse(
                    content=_wrap_html_response(
                        "<p class='info'>No data available for preview</p>"
                    )
                )

            # Execute transformer
            transformed_data = _execute_transformer(
                db, transformer_plugin, sample_data, config
            )

            # Render widget using dynamic params builder
            widget_html = _render_widget_dynamic(
                db,
                widget_plugin,
                transformed_data,
                transformer_plugin,
                config,
                template_name,
            )

            return HTMLResponse(
                content=_wrap_html_response(widget_html, title=template_name)
            )

        finally:
            db.close_db_session()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating preview for template '{template_id}': {e}")
        return HTMLResponse(
            content=_wrap_html_response(f"<p class='error'>Error: {str(e)}</p>"),
            status_code=500,
        )


def _build_dynamic_template_info(
    parsed: Dict[str, Any], template_id: str
) -> Dict[str, Any]:
    """Build template info for dynamic templates based on parsed ID.

    Args:
        parsed: Dict with 'column', 'transformer', 'widget' keys
        template_id: Original template ID string

    Returns:
        Dict with 'name', 'plugin' (transformer), 'widget', 'config'
    """
    column = parsed["column"]
    transformer = parsed["transformer"]
    widget = parsed["widget"]

    # Build config based on transformer type
    col_name = column.replace("_", " ").title()

    if transformer == "binned_distribution":
        config = {
            "source": "occurrences",
            "field": column,
            "bins": [0, 10, 20, 30, 40, 50, 100, 200, 500],  # Default bins
            "include_percentages": True,
        }
        name = f"Distribution de {col_name}"

    elif transformer == "statistical_summary":
        # Guess max_value and unit based on column name
        max_value = 100
        unit = ""
        col_lower = column.lower()
        if "height" in col_lower or "hauteur" in col_lower:
            max_value = 50
            unit = "m"
        elif "dbh" in col_lower or "diameter" in col_lower:
            max_value = 200
            unit = "cm"
        elif "elevation" in col_lower or "altitude" in col_lower:
            max_value = 1700
            unit = "m"

        config = {
            "source": "occurrences",
            "field": column,
            "stats": ["mean", "min", "max"],
            "units": unit,
            "max_value": max_value,
        }
        name = f"Statistiques {col_name}"

    elif transformer == "categorical_distribution":
        config = {
            "source": "occurrences",
            "field": column,
            "include_percentages": True,
        }
        name = f"Répartition par {col_name}"

    elif transformer == "top_ranking":
        config = {
            "source": "occurrences",
            "field": column,
            "mode": "direct",
            "count": 10,
        }
        name = f"Top {col_name}"

    elif transformer == "binary_counter":
        config = {
            "source": "occurrences",
            "field": column,
            "true_label": "Oui",
            "false_label": "Non",
            "include_percentages": True,
        }
        name = f"Distribution {col_name}"

    elif transformer == "geospatial_extractor":
        config = {
            "source": "occurrences",
            "field": column,
            "format": "geojson",
            "group_by_coordinates": True,
        }
        name = f"Carte {col_name}"

    elif transformer == "field_aggregator":
        config = {
            "source": "occurrences",
            "fields": [column],
        }
        name = f"Info {col_name}"

    # Class_object extractors (for pre-calculated CSV data)
    elif transformer == "series_extractor":
        config = {
            "class_object": column,
            "output_field": f"{column}_distribution",
        }
        name = f"Distribution {col_name}"

    elif transformer == "binary_aggregator":
        config = {
            "class_object": column,
        }
        name = f"Répartition {col_name}"

    elif transformer == "categories_extractor":
        config = {
            "class_object": column,
            "output_field": f"{column}_distribution",
        }
        name = f"Catégories {col_name}"

    else:
        config = {"source": "occurrences", "field": column}
        name = col_name

    return {
        "name": name,
        "plugin": transformer,  # The transformer plugin
        "widget": widget,  # The widget plugin (from parsed ID)
        "config": config,
    }


def _preprocess_data_for_widget(data: Any, transformer: str, widget: str) -> Any:
    """Preprocess transformer output for widget compatibility.

    Handles format mismatches between transformer output and widget input.
    For example, binned_distribution outputs N+1 bin edges but donut_chart
    expects N labels matching N counts.
    """
    if not isinstance(data, dict):
        return data

    # binned_distribution -> donut_chart: convert bin edges to labels
    if transformer == "binned_distribution" and widget == "donut_chart":
        bins = data.get("bins", [])
        counts = data.get("counts", [])

        # bins has N+1 edges, counts has N values
        if len(bins) == len(counts) + 1:
            # Create labels like "10-20", "20-30", etc.
            labels = []
            for i in range(len(counts)):
                labels.append(f"{int(bins[i])}-{int(bins[i + 1])}")

            return {
                "labels": labels,
                "counts": counts,
                "percentages": data.get("percentages", []),
            }

    return data


def _render_widget_dynamic(
    db: Database,
    widget_name: str,
    data: Any,
    transformer: str,
    config: Dict[str, Any],
    title: str,
) -> str:
    """Render a widget for dynamic templates.

    Args:
        db: Database connection
        widget_name: Name of the widget plugin (e.g., 'bar_plot', 'donut_chart')
        data: Transformed data from the transformer
        transformer: Name of the transformer plugin (e.g., 'binned_distribution')
        config: Transformer configuration
        title: Title for the widget
    """
    try:
        plugin_class = PluginRegistry.get_plugin(widget_name, PluginType.WIDGET)
        plugin_instance = plugin_class(db=db)

        # Preprocess data for widget compatibility
        processed_data = _preprocess_data_for_widget(data, transformer, widget_name)

        # Build widget params based on transformer+widget combination
        widget_params = _build_widget_params_dynamic(
            transformer, widget_name, config, title, processed_data
        )

        # Validate params if the plugin has a param_schema
        if hasattr(plugin_instance, "param_schema") and plugin_instance.param_schema:
            validated_params = plugin_instance.param_schema.model_validate(
                widget_params
            )
        else:
            validated_params = widget_params

        return plugin_instance.render(processed_data, validated_params)
    except Exception as e:
        logger.exception(f"Error rendering widget '{widget_name}': {e}")
        return f"<p class='error'>Widget render error: {str(e)}</p>"


def _render_widget_for_class_object(
    db: Optional[Database],
    widget_name: str,
    data: Dict[str, Any],
    extractor: str,
    title: str,
) -> str:
    """Render a widget for class_object data (pre-calculated CSV).

    Args:
        db: Database connection (can be None for class_object widgets)
        widget_name: Name of the widget plugin (e.g., 'bar_plot', 'donut_chart')
        data: Class object data with 'labels' and 'counts'
        extractor: Name of the class_object extractor (e.g., 'series_extractor')
        title: Title for the widget

    Returns:
        HTML content of the rendered widget
    """
    try:
        plugin_class = PluginRegistry.get_plugin(widget_name, PluginType.WIDGET)
        plugin_instance = plugin_class(db=db)

        # Build widget params based on extractor type
        widget_params = _build_widget_params_for_class_object(
            extractor, widget_name, data, title
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
        logger.exception(f"Error rendering class_object widget '{widget_name}': {e}")
        return f"<p class='error'>Widget render error: {str(e)}</p>"


def _build_widget_params_for_class_object(
    extractor: str, widget: str, data: Dict[str, Any], title: str
) -> Dict[str, Any]:
    """Build widget parameters for class_object data.

    Class_object data format: {"labels": [...], "counts": [...], "source": "..."}

    Widget params depend on the widget type:
    - bar_plot: x_axis="labels", y_axis="counts"
    - donut_chart: values_field="counts", labels_field="labels"
    - radial_gauge: value_field (uses first value), max_value
    """
    if widget == "bar_plot":
        # Determine orientation based on extractor
        orientation = "v" if extractor == "series_extractor" else "h"
        return {
            "x_axis": "labels" if orientation == "v" else "counts",
            "y_axis": "counts" if orientation == "v" else "labels",
            "title": title,
            "orientation": orientation,
            "gradient_color": "#10b981",
            "gradient_mode": "luminance",
        }

    elif widget == "donut_chart":
        return {
            "values_field": "counts",
            "labels_field": "labels",
            "title": title,
        }

    elif widget == "radial_gauge":
        # For scalar values, use the first (and usually only) value
        max_value = 100
        counts = data.get("counts", [])
        if counts:
            # Estimate max_value from the value
            actual_value = counts[0] if counts else 0
            if actual_value > 0:
                # Round to nice number above the value
                magnitude = 10 ** len(str(int(actual_value)))
                max_value = int(((actual_value // magnitude) + 1) * magnitude)

        return {
            "value_field": "value",  # We'll need to adjust data structure
            "max_value": max_value,
            "title": title,
        }

    elif widget == "info_grid":
        return {
            "title": title,
            "columns": 2,
        }

    # Default fallback
    return {"title": title}
