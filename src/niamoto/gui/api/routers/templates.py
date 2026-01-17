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
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from niamoto.gui.api.models.templates import (
    TemplateSuggestionResponse,
    SuggestionsResponse,
    GenerateConfigRequest,
    GenerateConfigResponse,
    SaveConfigRequest,
    SaveConfigResponse,
    ClassObjectSuggestion,
    WidgetTemplate,
    PluginParameter,
    PluginSchema,
    WidgetSuggestionsResponse,
    CombinedWidgetRequest,
    CombinedWidgetSuggestion,
    CombinedWidgetResponse,
    SemanticGroupsResponse,
)
from niamoto.gui.api.services.templates.utils.config_loader import (
    load_import_config,
    get_hierarchy_info,
    build_reference_info,
)
from niamoto.gui.api.services.templates.utils.entity_finder import (
    find_representative_entity,
    find_entity_by_id,
)
from niamoto.gui.api.services.templates.utils.data_loader import (
    load_sample_data,
    load_class_object_data_for_preview,
)
from niamoto.gui.api.services.templates.utils.widget_utils import (
    map_transformer_to_widget,
    generate_widget_title,
    generate_widget_params,
    is_class_object_template,
    find_widget_for_transformer,
    parse_dynamic_template_id,
    find_widget_group,
    load_configured_widget,
)

# Re-export helper functions with underscore prefix for backward compatibility
_load_import_config = load_import_config
_get_hierarchy_info = get_hierarchy_info
_build_reference_info = build_reference_info
_find_representative_entity = find_representative_entity
_find_entity_by_id = find_entity_by_id
_load_sample_data = load_sample_data
_load_class_object_data_for_preview = load_class_object_data_for_preview
_map_transformer_to_widget = map_transformer_to_widget
_generate_widget_title = generate_widget_title
_generate_widget_params = generate_widget_params
_is_class_object_template = is_class_object_template
_find_widget_for_transformer = find_widget_for_transformer
_parse_dynamic_template_id = parse_dynamic_template_id
_find_widget_group = find_widget_group
_load_configured_widget = load_configured_widget

from niamoto.gui.api.services.templates.suggestion_service import (  # noqa: E402
    generate_navigation_suggestion,
    generate_general_info_suggestion,
    get_entity_map_suggestions,
    get_class_object_suggestions,
    get_reference_field_suggestions,
)

# Backward compatibility aliases for suggestion functions
_generate_navigation_suggestion = generate_navigation_suggestion
_generate_general_info_suggestion = generate_general_info_suggestion
_get_entity_map_suggestions = get_entity_map_suggestions
_get_class_object_suggestions = get_class_object_suggestions
_get_reference_field_suggestions = get_reference_field_suggestions

from niamoto.core.imports.template_suggester import (  # noqa: E402
    TemplateSuggester,
    TemplateSuggestion,
)
from niamoto.core.imports.class_object_analyzer import analyze_csv  # noqa: E402
from niamoto.core.imports.multi_field_detector import (  # noqa: E402
    suggest_combined_widgets,
    detect_all_groups,
)
from niamoto.core.plugins.registry import PluginRegistry  # noqa: E402
from niamoto.core.plugins.base import PluginType  # noqa: E402
from niamoto.gui.api.context import get_database_path, get_working_directory  # noqa: E402
from niamoto.gui.api.services import PreviewService  # noqa: E402
from niamoto.common.database import Database  # noqa: E402

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

                            # Filter out columns that are essentially empty
                            # Keep columns with at least 0.1% of data (null_ratio < 99.9%)
                            enriched_profiles = [
                                p for p in enriched_profiles if p.null_ratio < 0.999
                            ]

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

    # Get suggestions based on reference entity table columns (e.g., plots.holdridge, plots.rainfall)
    reference_field_suggestions = _get_reference_field_suggestions(reference_name)

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

    # Calculate how many column suggestions we can include (reserve slots for navigation + general_info + entity maps + class_objects + reference_fields)
    reserved_slots = (
        2
        + len(class_object_suggestions)
        + len(entity_map_suggestions)
        + len(reference_field_suggestions)
    )  # 2 = navigation + general_info
    remaining_slots = max(0, max_suggestions - reserved_slots)
    limited_column_suggestions = column_suggestion_dicts[:remaining_slots]

    # Combine: navigation first, then general_info, then entity maps, then reference fields, then class_object, then column suggestions
    all_suggestions = (
        ([navigation_suggestion] if navigation_suggestion else [])
        + ([general_info_suggestion] if general_info_suggestion else [])
        + entity_map_suggestions
        + reference_field_suggestions
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
        # Extract params from config - handle both nested and flat structures
        # Some suggestions have config: {"plugin": ..., "params": {...}}
        # Others have config: {direct params}
        cfg = template.config
        if isinstance(cfg, dict) and "params" in cfg and "plugin" in cfg:
            # Nested structure - extract just the params
            params = cfg["params"]
        else:
            # Flat structure - use config directly as params
            params = cfg

        widgets_data[template.template_id] = {
            "plugin": template.plugin,
            "params": params,
        }

    # Build sources section based on reference kind (not name!)
    # Try to get relation info from import.yml first
    relation_from_import = None
    work_dir = get_working_directory()
    if work_dir:
        import_path = Path(work_dir) / "config" / "import.yml"
        if import_path.exists():
            try:
                with open(import_path, "r", encoding="utf-8") as f:
                    import_config = yaml.safe_load(f) or {}
                refs = import_config.get("entities", {}).get("references", {})
                ref_config = refs.get(request.group_by, {})
                relation_config = ref_config.get("relation", {})
                if relation_config:
                    # Convert import.yml format to transform.yml format
                    relation_from_import = {
                        "plugin": "direct_reference",
                        "key": relation_config.get("foreign_key"),
                        "ref_key": relation_config.get("reference_key"),
                    }
            except Exception as e:
                logger.warning(f"Error reading import.yml for relation: {e}")

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
        # Use relation from import.yml if available, otherwise fallback to convention
        relation = relation_from_import or {
            "plugin": "direct_reference",
            "key": f"{request.group_by}_id",
            "ref_key": "id",
        }
        sources = [
            {
                "name": "occurrences",
                "data": "occurrences",
                "grouping": request.group_by,
                "relation": relation,
            }
        ]

    return GenerateConfigResponse(
        group_by=request.group_by,
        sources=sources,
        widgets_data=widgets_data,
    )


def _generate_export_config(
    work_dir: Path,
    group_name: str,
    widgets_data: Dict[str, Any],
    sources: List[Dict[str, Any]],
    mode: str = "replace",
) -> None:
    """
    Generate export.yml configuration for widgets.

    Creates or updates the export.yml file with widget configurations.

    Args:
        mode: 'merge' adds new widgets to existing, 'replace' overwrites all widgets
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

    # Update group widgets based on mode
    if mode == "merge":
        # Merge: add new widgets to existing ones
        existing_widgets = group_config.get("widgets", [])
        existing_data_sources = {w.get("data_source") for w in existing_widgets}

        # Find the max order from existing widgets
        max_order = max(
            (w.get("layout", {}).get("order", 0) for w in existing_widgets), default=-1
        )

        # Add only new widgets (not already in config)
        for widget in export_widgets:
            if widget.get("data_source") not in existing_data_sources:
                max_order += 1
                widget["layout"]["order"] = max_order
                existing_widgets.append(widget)

        group_config["widgets"] = existing_widgets
    else:
        # Replace: overwrite all widgets
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

        # Update sources based on mode
        if request.mode == "merge":
            # Merge mode: preserve existing sources, only add new ones
            existing_sources = group_config.get("sources", [])
            existing_source_names = {s.get("name") for s in existing_sources}
            for new_source in request.sources:
                if new_source.get("name") not in existing_source_names:
                    existing_sources.append(new_source)
            group_config["sources"] = existing_sources
        else:
            # Replace mode: replace sources entirely
            group_config["sources"] = request.sources

        # Track changes
        existing_widgets = group_config.get("widgets_data", {})
        widgets_added = 0
        widgets_updated = 0
        widgets_removed = 0

        if request.mode == "merge":
            # Merge mode: add new widgets to existing ones, update if exists
            merged_widgets = dict(existing_widgets)
            for widget_id, widget_config in request.widgets_data.items():
                if widget_id in merged_widgets:
                    widgets_updated += 1
                else:
                    widgets_added += 1
                merged_widgets[widget_id] = widget_config
            group_config["widgets_data"] = merged_widgets
        else:
            # Replace mode: count changes and replace entirely
            for widget_id in request.widgets_data:
                if widget_id in existing_widgets:
                    widgets_updated += 1
                else:
                    widgets_added += 1

            for widget_id in existing_widgets:
                if widget_id not in request.widgets_data:
                    widgets_removed += 1

            # Replace widgets_data entirely (not merge) to handle deletions
            group_config["widgets_data"] = dict(request.widgets_data)

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
            work_dir,
            group_name,
            request.widgets_data,
            group_config.get("sources", []),
            mode=request.mode,
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


# Plugin schemas for wizard UI - describes what parameters each plugin needs
# These are generic descriptions, not domain-specific templates
PLUGIN_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "class_object_field_aggregator": {
        "name": "Agregateur de champs",
        "description": "Regroupe plusieurs metriques scalaires dans un widget",
        "complexity": "simple",
        "applicable_categories": ["scalar"],
        "parameters": [
            {
                "name": "fields",
                "type": "class_object_list",
                "label": "Champs a agreger",
                "filter_category": "scalar",
                "required": True,
            }
        ],
    },
    "class_object_binary_aggregator": {
        "name": "Agregateur binaire",
        "description": "Compare des ratios binaires (2 categories)",
        "complexity": "medium",
        "applicable_categories": ["binary"],
        "parameters": [
            {
                "name": "groups",
                "type": "binary_mapping_list",
                "label": "Groupes binaires",
                "filter_category": "binary",
                "required": True,
            }
        ],
    },
    "class_object_categories_extractor": {
        "name": "Extracteur de categories",
        "description": "Extrait des categories avec leurs valeurs",
        "complexity": "simple",
        "applicable_categories": ["ternary", "multi_category"],
        "parameters": [
            {
                "name": "class_object",
                "type": "class_object_select",
                "label": "Class object",
                "filter_category": ["ternary", "multi_category"],
                "required": True,
            }
        ],
    },
    "class_object_series_extractor": {
        "name": "Extracteur de series",
        "description": "Extrait une serie de valeurs numeriques",
        "complexity": "simple",
        "applicable_categories": ["numeric_bins"],
        "parameters": [
            {
                "name": "class_object",
                "type": "class_object_select",
                "label": "Class object",
                "filter_category": "numeric_bins",
                "required": True,
            }
        ],
    },
    "class_object_series_ratio_aggregator": {
        "name": "Comparaison de distributions",
        "description": "Compare deux distributions (total vs subset)",
        "complexity": "complex",
        "applicable_categories": ["numeric_bins"],
        "parameters": [
            {
                "name": "total",
                "type": "class_object_select",
                "label": "Distribution totale",
                "filter_category": "numeric_bins",
                "required": True,
            },
            {
                "name": "subset",
                "type": "class_object_select",
                "label": "Distribution subset",
                "filter_category": "numeric_bins",
                "required": True,
            },
        ],
    },
    "class_object_categories_mapper": {
        "name": "Comparaison de categories",
        "description": "Compare des categories entre deux groupes",
        "complexity": "complex",
        "applicable_categories": ["ternary", "multi_category"],
        "parameters": [
            {
                "name": "category_a",
                "type": "class_object_select",
                "label": "Premier groupe",
                "filter_category": ["ternary", "multi_category"],
                "required": True,
            },
            {
                "name": "category_b",
                "type": "class_object_select",
                "label": "Deuxieme groupe",
                "filter_category": ["ternary", "multi_category"],
                "required": True,
            },
        ],
    },
    "class_object_series_by_axis_extractor": {
        "name": "Series par axe commun",
        "description": "Plusieurs series sur le meme axe",
        "complexity": "complex",
        "applicable_categories": ["numeric_bins"],
        "parameters": [
            {
                "name": "series",
                "type": "class_object_list",
                "label": "Series a comparer",
                "filter_category": "numeric_bins",
                "required": True,
                "min_items": 2,
            }
        ],
    },
    "class_object_series_matrix_extractor": {
        "name": "Matrice de series",
        "description": "Multiple series sur le meme axe avec echelle",
        "complexity": "complex",
        "applicable_categories": ["numeric_bins"],
        "parameters": [
            {
                "name": "series",
                "type": "series_config_list",
                "label": "Series avec configuration",
                "filter_category": "numeric_bins",
                "required": True,
                "min_items": 2,
            }
        ],
    },
}

# No hardcoded templates - wizard UI will generate configs dynamically
WIDGET_TEMPLATES: List[WidgetTemplate] = []


@router.get("/widget-suggestions/{group_by}", response_model=WidgetSuggestionsResponse)
async def get_widget_suggestions(
    group_by: str,
    source_name: Optional[str] = Query(
        default=None, description="Nom de la source CSV (auto-détecté si non fourni)"
    ),
):
    """Get widget suggestions based on class_object analysis of a CSV source.

    This endpoint analyzes the CSV source to detect:
    - Class object patterns (scalar, binary, categorical, numeric bins)
    - Related class objects (cover_*, holdridge_*, etc.)
    - Auto-generated configurations for each suggested plugin
    - Mapping hints for binary patterns (Forêt → forest)

    Returns suggestions organized by category with applicable templates.
    """
    work_dir = get_working_directory()
    transform_path = work_dir / "config" / "transform.yml"

    if not transform_path.exists():
        raise HTTPException(status_code=404, detail="transform.yml not found")

    # Find the CSV source for this group
    try:
        with open(transform_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Find group config
        group_config = None
        if isinstance(config, list):
            for g in config:
                if isinstance(g, dict) and g.get("group_by") == group_by:
                    group_config = g
                    break
        elif isinstance(config, dict):
            groups = config.get("groups", {})
            if isinstance(groups, list):
                for g in groups:
                    if isinstance(g, dict) and g.get("group_by") == group_by:
                        group_config = g
                        break

        if not group_config:
            raise HTTPException(
                status_code=404, detail=f"Group '{group_by}' not found in transform.yml"
            )

        # Find CSV source
        csv_source = None
        sources = group_config.get("sources", [])
        for src in sources:
            data_path = src.get("data", "")
            if data_path.endswith(".csv"):
                if source_name is None or src.get("name") == source_name:
                    csv_source = src
                    break

        if not csv_source:
            raise HTTPException(
                status_code=404, detail=f"No CSV source found for group '{group_by}'"
            )

        csv_path = work_dir / csv_source["data"]
        if not csv_path.exists():
            raise HTTPException(
                status_code=404, detail=f"CSV file not found: {csv_source['data']}"
            )

        # Analyze the CSV
        analysis = analyze_csv(csv_path)

        if not analysis.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid CSV: {', '.join(analysis.validation_errors)}",
            )

        # Convert to response format
        class_object_suggestions = []
        categories_count: Dict[str, int] = {}

        for co in analysis.class_objects:
            category = co.category.value
            categories_count[category] = categories_count.get(category, 0) + 1

            # Update source name in auto_config
            auto_config = co.auto_config.copy()
            if "source" in auto_config:
                auto_config["source"] = csv_source.get("name", "stats")

            class_object_suggestions.append(
                ClassObjectSuggestion(
                    name=co.name,
                    category=category,
                    cardinality=co.cardinality,
                    class_names=co.class_names,
                    value_type=co.value_type,
                    suggested_plugin=co.suggested_plugin or "",
                    confidence=co.confidence,
                    auto_config=auto_config,
                    mapping_hints=co.mapping_hints,
                    related_class_objects=co.related_class_objects,
                    pattern_group=co.pattern_group,
                )
            )

        # Filter plugin schemas based on available categories
        available_categories = set(categories_count.keys())
        applicable_schemas: Dict[str, PluginSchema] = {}
        for plugin_name, schema_dict in PLUGIN_SCHEMAS.items():
            if any(
                cat in available_categories
                for cat in schema_dict["applicable_categories"]
            ):
                applicable_schemas[plugin_name] = PluginSchema(
                    name=schema_dict["name"],
                    description=schema_dict["description"],
                    complexity=schema_dict["complexity"],
                    applicable_categories=schema_dict["applicable_categories"],
                    parameters=[
                        PluginParameter(**p) for p in schema_dict["parameters"]
                    ],
                )

        return WidgetSuggestionsResponse(
            source_name=csv_source.get("name", "stats"),
            source_path=csv_source["data"],
            class_objects=class_object_suggestions,
            pattern_groups=analysis.pattern_groups,
            plugin_schemas=applicable_schemas,
            categories_summary=categories_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error analyzing CSV for widget suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PREVIEW ENDPOINT
# =============================================================================


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


async def _preview_configured_widget(
    configured_widget: Dict[str, Any],
    group_by: str,
    entity_id: Optional[str] = None,
) -> HTMLResponse:
    """Preview a widget that was configured via the wizard.

    This loads the transformer config from transform.yml, executes the transformer,
    and renders the widget using export.yml settings.

    Args:
        configured_widget: Dict from _load_configured_widget
        group_by: Reference name for data filtering
        entity_id: Optional specific entity to preview

    Returns:
        HTMLResponse with rendered widget or error message
    """
    transformer_plugin = configured_widget["transformer_plugin"]
    transformer_params = configured_widget["transformer_params"]
    widget_plugin = configured_widget["widget_plugin"]
    widget_params = configured_widget.get("widget_params", {})
    widget_title = configured_widget["widget_title"]
    widget_id = configured_widget["widget_id"]

    # Get working directory
    work_dir = get_working_directory()
    if not work_dir:
        return HTMLResponse(
            content=PreviewService.wrap_html_response(
                "<p class='error'>Working directory not configured</p>"
            ),
            status_code=500,
        )

    work_dir = Path(work_dir)

    # Verify the widget plugin exists
    try:
        PluginRegistry.get_plugin(widget_plugin, PluginType.WIDGET)
    except Exception:
        return HTMLResponse(
            content=PreviewService.wrap_html_response(
                f"<p class='error'>Widget plugin '{widget_plugin}' not found</p>"
            ),
            status_code=400,
        )

    try:
        # Check if this is a class_object-based transformer
        if transformer_plugin.startswith("class_object_"):
            # For class_object plugins, we need to load data from CSV sources
            # Get the class_objects from transformer params
            class_objects = _extract_class_objects_from_params(transformer_params)

            if not class_objects:
                return HTMLResponse(
                    content=PreviewService.wrap_html_response(
                        "<p class='info'>Pas de class_objects configurés</p>"
                    )
                )

            # Load data for each class_object from CSV
            co_data_combined = {}
            for co_name in class_objects:
                co_data = _load_class_object_data_for_preview(
                    work_dir, co_name, group_by
                )
                if co_data:
                    co_data_combined[co_name] = co_data

            if not co_data_combined:
                return HTMLResponse(
                    content=PreviewService.wrap_html_response(
                        f"<p class='info'>Données non trouvées pour les class_objects: {', '.join(class_objects)}</p>"
                    )
                )

            # Get database for widget rendering
            db_path = get_database_path()
            db = Database(str(db_path), read_only=True) if db_path else None

            try:
                # Execute the transformer with the loaded data
                transformer_data = _execute_configured_transformer(
                    transformer_plugin, transformer_params, co_data_combined, group_by
                )

                if not transformer_data:
                    return HTMLResponse(
                        content=PreviewService.wrap_html_response(
                            "<p class='info'>Le transformer n'a pas retourné de données</p>"
                        )
                    )

                # Render widget using the correct pattern
                widget_html = _render_widget_for_configured(
                    db,
                    widget_plugin,
                    transformer_data,
                    transformer_plugin,
                    widget_title,
                    widget_params,
                )

                return HTMLResponse(
                    content=PreviewService.wrap_html_response(
                        widget_html, title=widget_title
                    )
                )
            finally:
                if db:
                    db.close_db_session()

        else:
            # Standard occurrence-based transformer
            # Load import.yml
            import_config = _load_import_config(work_dir)

            # Get reference info
            hierarchy_info = _get_hierarchy_info(import_config, group_by)

            # Get database
            db_path = get_database_path()
            if not db_path:
                return HTMLResponse(
                    content=PreviewService.wrap_html_response(
                        "<p class='error'>Database not found</p>"
                    ),
                    status_code=404,
                )

            db = Database(str(db_path), read_only=True)
            try:
                # Find representative entity
                if entity_id:
                    representative = _find_entity_by_id(db, hierarchy_info, entity_id)
                else:
                    representative = _find_representative_entity(db, hierarchy_info)

                # Load sample data
                sample_data = _load_sample_data(db, representative, transformer_params)

                if sample_data.empty:
                    return HTMLResponse(
                        content=PreviewService.wrap_html_response(
                            "<p class='info'>No data available for preview</p>"
                        )
                    )

                # Execute transformer
                transformer_cls = PluginRegistry.get_plugin(
                    transformer_plugin, PluginType.TRANSFORMER
                )
                transformer = transformer_cls(db=db)
                transform_config = {
                    "plugin": transformer_plugin,
                    "params": transformer_params,
                }
                result = transformer.transform(sample_data, transform_config)

                # Render widget using the correct pattern
                widget_html = _render_widget_for_configured(
                    db,
                    widget_plugin,
                    result,
                    transformer_plugin,
                    widget_title,
                    widget_params,
                )

                return HTMLResponse(
                    content=PreviewService.wrap_html_response(
                        widget_html, title=widget_title
                    )
                )
            finally:
                db.close_db_session()

    except Exception as e:
        logger.error(f"Error previewing configured widget '{widget_id}': {e}")
        return HTMLResponse(
            content=PreviewService.wrap_html_response(
                f"<p class='error'>Erreur lors de la preview: {str(e)}</p>"
            ),
            status_code=500,
        )


def _extract_class_objects_from_params(params: Dict[str, Any]) -> List[str]:
    """Extract class_object names from transformer parameters.

    Different transformers store class_objects in different param structures:
    - field_aggregator: params.fields[].class_object
    - binary_aggregator: params.groups[].field
    - series_extractor: params.class_object
    - categories_extractor: params.class_object
    """
    class_objects = []

    # Single class_object
    if "class_object" in params:
        class_objects.append(params["class_object"])

    # List of fields with class_object
    if "fields" in params:
        for field in params["fields"]:
            if isinstance(field, dict) and "class_object" in field:
                class_objects.append(field["class_object"])

    # List of groups with field (binary_aggregator)
    if "groups" in params:
        for group in params["groups"]:
            if isinstance(group, dict) and "field" in group:
                class_objects.append(group["field"])

    # Series config list
    if "series" in params:
        for series in params["series"]:
            if isinstance(series, dict) and "class_object" in series:
                class_objects.append(series["class_object"])

    # Distributions (ratio aggregator)
    if "distributions" in params:
        for dist in params["distributions"].values():
            if isinstance(dist, dict):
                if "total" in dist:
                    class_objects.append(dist["total"])
                if "subset" in dist:
                    class_objects.append(dist["subset"])

    return list(set(class_objects))  # Remove duplicates


def _execute_configured_transformer(
    transformer_plugin: str,
    params: Dict[str, Any],
    class_object_data: Dict[str, Dict[str, Any]],
    group_by: str,
) -> Optional[Dict[str, Any]]:
    """Execute a class_object transformer with loaded CSV data.

    This mimics what happens during the actual transform phase,
    but uses the preview data we loaded.
    """
    try:
        # For binary_aggregator, we need to compute ratios
        # Output format: {"tops": [...], "counts": [...]} for bar_plot compatibility
        if transformer_plugin == "class_object_binary_aggregator":
            groups = params.get("groups", [])
            all_labels = []
            all_counts = []

            for group in groups:
                field = group.get("field", "")

                if field not in class_object_data:
                    continue

                # co_data is already in {"tops": [...], "counts": [...]} format
                co_data = class_object_data[field]
                group_tops = co_data.get("tops", [])
                group_counts = co_data.get("counts", [])

                # Add tops and counts for this group
                all_labels.extend(group_tops)
                all_counts.extend(group_counts)

            return {"tops": all_labels, "counts": all_counts}

        # For field_aggregator, collect scalar values
        elif transformer_plugin == "class_object_field_aggregator":
            fields = params.get("fields", [])
            result = {"fields": []}

            for field_config in fields:
                co_name = field_config.get("class_object", "")
                target = field_config.get("target", co_name)

                if co_name in class_object_data:
                    # co_data is in {"tops": [...], "counts": [...]} format
                    co_data = class_object_data[co_name]
                    counts = co_data.get("counts", [])
                    # For scalar, take the first (and only) value
                    if counts:
                        result["fields"].append(
                            {
                                "name": target,
                                "value": counts[0],
                                "label": field_config.get("label", target),
                            }
                        )

            return result

        # For series_extractor, extract size distribution
        elif transformer_plugin == "class_object_series_extractor":
            co_name = params.get("class_object", "")
            if co_name not in class_object_data:
                return None

            # co_data is in {"tops": [...], "counts": [...]} format
            co_data = class_object_data[co_name]
            tops = co_data.get("tops", [])
            counts = co_data.get("counts", [])

            # Sort by value descending (like top_ranking)
            if tops and counts:
                paired = sorted(zip(tops, counts), key=lambda x: -x[1])
                # Apply count limit if specified
                count_limit = params.get("count")
                if count_limit and len(paired) > count_limit:
                    paired = paired[:count_limit]
                tops, counts = zip(*paired) if paired else ([], [])

            return {"tops": list(tops), "counts": list(counts)}

        # For categories_extractor, extract categories
        elif transformer_plugin == "class_object_categories_extractor":
            co_name = params.get("class_object", "")
            if co_name not in class_object_data:
                return None

            # co_data is in {"tops": [...], "counts": [...]} format
            co_data = class_object_data[co_name]
            tops = co_data.get("tops", [])
            counts = co_data.get("counts", [])

            return {"tops": tops, "counts": counts}

        # Default: return the raw data
        return {"data": class_object_data}

    except Exception as e:
        logger.warning(f"Error executing transformer {transformer_plugin}: {e}")
        return None


def _try_parse_numeric(value: str) -> float:
    """Try to parse a string as a number for sorting."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return float("inf")


def _render_widget_for_configured(
    db: Optional[Database],
    widget_name: str,
    data: Dict[str, Any],
    transformer: str,
    title: str,
    extra_params: Optional[Dict[str, Any]] = None,
) -> str:
    """Render a widget for a configured widget from transform.yml.

    This handles widgets created via the wizard that have custom configurations.

    Args:
        db: Database connection (can be None)
        widget_name: Name of the widget plugin (e.g., 'bar_plot')
        data: Transformer output data
        transformer: Name of the transformer plugin
        title: Title for the widget
        extra_params: Additional widget params from export.yml

    Returns:
        HTML content of the rendered widget
    """
    try:
        plugin_class = PluginRegistry.get_plugin(widget_name, PluginType.WIDGET)
        plugin_instance = plugin_class(db=db)

        # Build widget params based on transformer and widget type
        widget_params = _build_widget_params_for_configured(
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
        logger.exception(f"Error rendering configured widget '{widget_name}': {e}")
        return f"<p class='error'>Widget render error: {str(e)}</p>"


def _build_widget_params_for_configured(
    transformer: str,
    widget: str,
    data: Dict[str, Any],
    title: str,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build widget parameters for configured widgets.

    Maps transformer output to widget input based on known patterns.
    """
    params = {"title": title}

    # Apply extra params from export.yml first (they can be overridden by defaults)
    if extra_params:
        params.update(extra_params)

    if widget == "bar_plot":
        # For binary_aggregator, data has groups with values
        if transformer == "class_object_binary_aggregator":
            # Set params for bar_plot
            params.setdefault("x_axis", "labels")
            params.setdefault("y_axis", "counts")
            params.setdefault("orientation", "v")
            params.setdefault("gradient_color", "#10b981")

        # For series extractors
        elif transformer in ("class_object_series_extractor", "series_extractor"):
            params.setdefault("x_axis", "sizes")
            params.setdefault("y_axis", "counts")
            params.setdefault("orientation", "v")
            params.setdefault("gradient_color", "#10b981")

        # For categories extractors
        elif transformer in (
            "class_object_categories_extractor",
            "categories_extractor",
        ):
            params.setdefault("x_axis", "labels")
            params.setdefault("y_axis", "counts")
            params.setdefault("orientation", "h")
            params.setdefault("sort_order", "descending")

        # Fallback for other bar_plot transformers
        else:
            params.setdefault("x_axis", "labels")
            params.setdefault("y_axis", "counts")
            params.setdefault("orientation", "v")

    elif widget == "donut_chart":
        params.setdefault("values_field", "counts")
        params.setdefault("labels_field", "labels")

    elif widget == "info_grid":
        # For field aggregator
        pass  # info_grid uses data directly

    elif widget == "radial_gauge":
        params.setdefault("auto_range", True)

    return params


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
            params = {
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
            # Add axis labels from transformer config
            x_label = config.get("x_label")
            y_label = config.get("y_label")
            if x_label or y_label:
                params["labels"] = {
                    "bin": x_label or "Classe",
                    "count": y_label or "%",
                }
            return params
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
            # Use new stat_to_display param with show_range for min/max markers
            stats = config.get("stats", ["mean"])
            stat_to_display = (
                "mean" if "mean" in stats else stats[0] if stats else "mean"
            )
            return {
                "stat_to_display": stat_to_display,
                "show_range": True,  # Show min/max as visual markers
                "auto_range": True,  # Use max_value from data
                "title": title,
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
                content=PreviewService.wrap_html_response(
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
                        content=PreviewService.wrap_html_response(
                            f"<p class='info'>Table '{reference_name}' non trouvée</p>"
                        )
                    )

            # Get column info to detect hierarchy and exclude geometry columns
            from sqlalchemy import text

            with db.engine.connect() as conn:
                result = conn.execute(text(f"DESCRIBE {table_name}"))
                col_info = result.fetchall()

            # Build safe columns list (exclude geometry/binary types)
            safe_columns = [
                c[0]
                for c in col_info
                if c[1].upper() not in ("GEOMETRY", "BLOB", "BYTEA")
                and not c[0].endswith("_geom")
            ]
            columns = set(safe_columns)
            safe_columns_sql = ", ".join(f'"{c}"' for c in safe_columns)

            has_nested_set = "lft" in columns and "rght" in columns
            has_parent = "parent_id" in columns
            has_level = "level" in columns
            is_hierarchical = has_nested_set or (has_parent and has_level)

            # Detect ID field - handle both plural (plots) and singular (plot) forms
            singular = (
                reference_name.rstrip("s")
                if reference_name.endswith("s")
                else reference_name
            )
            id_candidates = [
                f"id_{singular}",  # id_plot (for plots)
                f"{singular}_id",  # plot_id
                f"id_{reference_name}",  # id_plots
                f"{reference_name}_id",  # plots_id
                "id",
            ]
            id_field = next((c for c in id_candidates if c in columns), None)
            if not id_field:
                id_field = next((c for c in columns if "id" in c.lower()), "id")

            # Detect name field
            name_candidates = ["full_name", "name", "plot", "label", "title"]
            name_field = next((c for c in name_candidates if c in columns), id_field)

            # Build query to get sample data for preview (limit to first levels)
            # Use safe_columns_sql to exclude geometry columns
            if is_hierarchical and has_nested_set:
                # Get hierarchical sample ordered by nested set
                query = f"""
                    SELECT {safe_columns_sql}
                    FROM {table_name}
                    WHERE level <= 3
                    ORDER BY lft
                    LIMIT 50
                """
            elif is_hierarchical and has_parent:
                # Get parent-child sample
                query = f"""
                    SELECT {safe_columns_sql}
                    FROM {table_name}
                    WHERE level <= 3
                    LIMIT 50
                """
            else:
                # Get flat sample
                query = f"""
                    SELECT {safe_columns_sql}
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
            content=PreviewService.wrap_html_response(
                f"<p class='error'>Erreur: {str(e)}</p>"
            ),
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
                content=PreviewService.wrap_html_response(
                    "<p class='info'>Base de données non configurée</p>"
                )
            )

        db = Database(str(db_path), read_only=True)
        try:
            # Generate the suggestion to get the detected fields
            suggestion = _generate_general_info_suggestion(reference_name)
            if not suggestion:
                return HTMLResponse(
                    content=PreviewService.wrap_html_response(
                        f"<p class='info'>Aucun champ détecté pour '{reference_name}'</p>"
                    )
                )

            field_configs = suggestion["config"]["fields"]

            # Find the reference table
            # When entity_id is provided, prefer entity_ table (where the ID comes from)
            ref_table = f"reference_{reference_name}"
            if not db.has_table(ref_table):
                # Prioritize entity_ table when entity_id is provided
                fallback_tables = (
                    [f"entity_{reference_name}", reference_name]
                    if entity_id
                    else [reference_name, f"entity_{reference_name}"]
                )
                for alt_name in fallback_tables:
                    if db.has_table(alt_name):
                        ref_table = alt_name
                        break
                else:
                    return HTMLResponse(
                        content=PreviewService.wrap_html_response(
                            f"<p class='info'>Table '{reference_name}' not found</p>"
                        )
                    )

            # Get a sample entity - detect the correct ID column
            # Get columns to find the ID field
            columns = [
                col.lower()
                for col in pd.read_sql(
                    f"SELECT * FROM {ref_table} LIMIT 0", db.engine
                ).columns
            ]

            # Detect ID column with common patterns
            # Handle both plural (plots) and singular (plot) forms
            singular = (
                reference_name.rstrip("s")
                if reference_name.endswith("s")
                else reference_name
            )
            id_candidates = [
                "id",
                f"id_{singular}",  # id_plot (for plots)
                f"{singular}_id",  # plot_id
                f"id_{reference_name}",  # id_plots
                f"{reference_name}_id",  # plots_id
            ]
            id_field = next((c for c in id_candidates if c in columns), None)
            if not id_field:
                # Fallback: any column containing 'id' (but not just containing 'id' in middle)
                id_field = next(
                    (c for c in columns if c == "id" or c.endswith("_id")), "id"
                )

            if entity_id:
                # Properly quote entity_id to prevent SQL injection
                # entity_id can be numeric or string, so we need to handle both
                if isinstance(entity_id, (int, float)):
                    safe_entity_id = str(entity_id)
                else:
                    # Escape single quotes and wrap in quotes for string values
                    safe_entity_id = "'" + str(entity_id).replace("'", "''") + "'"
                sample_query = f'SELECT * FROM {ref_table} WHERE "{id_field}" = {safe_entity_id} LIMIT 1'
            else:
                sample_query = f"SELECT * FROM {ref_table} LIMIT 1"

            sample_df = pd.read_sql(sample_query, db.engine)
            if sample_df.empty:
                return HTMLResponse(
                    content=PreviewService.wrap_html_response(
                        f"<p class='info'>No data in '{reference_name}'</p>"
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
                    value = "(count)"
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
            content=PreviewService.wrap_html_response(
                f"<p class='error'>Erreur: {str(e)}</p>"
            ),
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
            content=PreviewService.wrap_html_response(
                "<p class='error'>Database not found</p>"
            ),
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
            content=PreviewService.wrap_html_response(
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
            content=PreviewService.wrap_html_response(
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
                content=PreviewService.wrap_html_response(
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

        # Detect ID field - handle both plural (plots) and singular (plot) forms
        singular = reference.rstrip("s") if reference.endswith("s") else reference
        id_candidates = [
            f"id_{singular}",  # id_plot (for plots)
            f"{singular}_id",  # plot_id
            f"id_{reference}",  # id_plots
            f"{reference}_id",  # plots_id
            "id",
        ]
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
                content=PreviewService.wrap_html_response(
                    "<p class='info'>No geographic data available</p>"
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
                content=PreviewService.wrap_html_response(
                    "<p class='info'>No valid geometry found</p>"
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
            content=PreviewService.wrap_html_response(
                f"<p class='error'>Erreur: {str(e)}</p>"
            ),
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
    source: str = Query(
        default=None,
        description="Data source (entity name like 'plots' for entity data)",
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
        # Try to load as a configured widget from transform.yml
        # If group_by not provided, try to auto-detect from transform.yml
        detected_group_by = group_by
        if not detected_group_by:
            detected_group_by = _find_widget_group(template_id)

        if detected_group_by:
            configured_widget = _load_configured_widget(template_id, detected_group_by)
            if configured_widget:
                return await _preview_configured_widget(
                    configured_widget, detected_group_by, entity_id
                )

        return HTMLResponse(
            content=PreviewService.wrap_html_response(
                f"<p class='error'>Invalid template ID format: '{template_id}'</p>"
            ),
            status_code=400,
        )

    template_info = _build_dynamic_template_info(parsed, template_id, source=source)
    transformer_plugin = template_info["plugin"]
    widget_plugin = template_info["widget"]  # Widget is now part of the template ID
    config = template_info["config"]
    template_name = template_info["name"]

    # Verify the widget plugin exists
    try:
        PluginRegistry.get_plugin(widget_plugin, PluginType.WIDGET)
    except Exception:
        return HTMLResponse(
            content=PreviewService.wrap_html_response(
                f"<p class='error'>Widget plugin '{widget_plugin}' not found</p>"
            ),
            status_code=400,
        )

    # Get working directory and load config
    work_dir = get_working_directory()
    if not work_dir:
        return HTMLResponse(
            content=PreviewService.wrap_html_response(
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
                    content=PreviewService.wrap_html_response(
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
                    content=PreviewService.wrap_html_response(
                        widget_html, title=template_name
                    )
                )
            finally:
                if db:
                    db.close_db_session()

        # Check if source is an entity table (not occurrences)
        data_source = config.get("source", "occurrences")
        if data_source and data_source != "occurrences":
            # Try to load from entity table directly
            db_path = get_database_path()
            if not db_path:
                return HTMLResponse(
                    content=PreviewService.wrap_html_response(
                        "<p class='error'>Database not found</p>"
                    ),
                    status_code=404,
                )

            db = Database(str(db_path), read_only=True)
            try:
                # Check for entity table
                entity_table = f"entity_{data_source}"
                if not db.has_table(entity_table):
                    # Try reference table
                    entity_table = f"reference_{data_source}"
                    if not db.has_table(entity_table):
                        entity_table = data_source

                if db.has_table(entity_table):
                    # Load data from entity table
                    field = config.get("field", column)
                    try:
                        sample_data = pd.read_sql(
                            f'SELECT "{field}" FROM {entity_table} WHERE "{field}" IS NOT NULL',
                            db.engine,
                        )

                        if sample_data.empty:
                            return HTMLResponse(
                                content=PreviewService.wrap_html_response(
                                    f"<p class='info'>No data for field '{field}' in {entity_table}</p>"
                                )
                            )

                        # Adjust config based on actual data
                        config = _adjust_config_for_data(
                            config, transformer_plugin, sample_data
                        )

                        # Check for identical values
                        identical_value = _check_identical_values(
                            sample_data, config, transformer_plugin
                        )
                        if identical_value is not None:
                            unit = config.get("units", "")
                            value_display = (
                                f"{identical_value} {unit}"
                                if unit
                                else str(identical_value)
                            )
                            return HTMLResponse(
                                content=PreviewService.wrap_html_response(
                                    f"<p class='info'>Toutes les valeurs sont identiques ({value_display})</p>",
                                    title=template_name,
                                )
                            )

                        # Execute transformer
                        transformed_data = PreviewService.execute_transformer(
                            db, transformer_plugin, config, sample_data
                        )

                        # Render widget
                        widget_html = _render_widget_dynamic(
                            db,
                            widget_plugin,
                            transformed_data,
                            transformer_plugin,
                            config,
                            template_name,
                        )

                        return HTMLResponse(
                            content=PreviewService.wrap_html_response(
                                widget_html, title=template_name
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Error loading entity data: {e}")
                        # Fall through to standard flow
            finally:
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
                content=PreviewService.wrap_html_response(
                    "<p class='error'>Database not found</p>"
                ),
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
                    content=PreviewService.wrap_html_response(
                        "<p class='info'>No data available for preview</p>"
                    )
                )

            # Adjust config based on actual data (e.g., smart bins for binned_distribution)
            config = _adjust_config_for_data(config, transformer_plugin, sample_data)

            # Check for identical values (only relevant for distribution-type transformers)
            identical_value = _check_identical_values(
                sample_data, config, transformer_plugin
            )
            if identical_value is not None:
                # All values are identical - show informative message instead of histogram
                unit = config.get("units", "")
                if unit:
                    value_display = f"{identical_value} {unit}"
                else:
                    value_display = str(identical_value)
                return HTMLResponse(
                    content=PreviewService.wrap_html_response(
                        f"<p class='info'>Toutes les valeurs sont identiques ({value_display})</p>",
                        title=template_name,
                    )
                )

            # Execute transformer
            transformed_data = PreviewService.execute_transformer(
                db, transformer_plugin, config, sample_data
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
                content=PreviewService.wrap_html_response(
                    widget_html, title=template_name
                )
            )

        finally:
            db.close_db_session()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating preview for template '{template_id}': {e}")
        return HTMLResponse(
            content=PreviewService.wrap_html_response(
                f"<p class='error'>Error: {str(e)}</p>"
            ),
            status_code=500,
        )


def _generate_smart_bins(min_val: float, max_val: float) -> List[float]:
    """Generate smart histogram bins based on data range.

    This mirrors the logic from WidgetGenerator._generate_smart_bins
    to ensure consistent bin generation for previews.
    """
    if max_val <= min_val:
        return [0, 10, 20, 30, 40, 50]

    range_val = max_val - min_val

    # Determine step size based on range
    if range_val <= 10:
        step = 1
    elif range_val <= 50:
        step = 5
    elif range_val <= 100:
        step = 10
    elif range_val <= 500:
        step = 50
    elif range_val <= 2000:
        step = 100
    else:
        step = 500

    # Round min down and max up to step
    start = math.floor(min_val / step) * step
    end = math.ceil(max_val / step) * step

    bins = []
    current = start
    while current <= end:
        bins.append(current)
        current += step

    # Limit to ~15 bins max
    while len(bins) > 15:
        bins = bins[::2]

    return bins


def _check_identical_values(
    sample_data: pd.DataFrame,
    config: Dict[str, Any],
    transformer_plugin: str,
) -> Optional[float]:
    """Check if all values in the target field are identical.

    For distribution-type transformers (binned_distribution), having all identical
    values means a histogram is not meaningful. Instead, we should show an
    informative message to the user.

    Args:
        sample_data: The loaded sample data
        config: Transformer config
        transformer_plugin: Name of the transformer plugin

    Returns:
        The identical value if all values are the same, None otherwise
    """
    # Only check for distribution transformers
    if transformer_plugin != "binned_distribution":
        return None

    field = config.get("field")
    if not field or field not in sample_data.columns:
        return None

    # Get numeric values from the field
    field_data = pd.to_numeric(sample_data[field], errors="coerce").dropna()

    if field_data.empty:
        return None

    # Check if all values are identical
    unique_values = field_data.unique()
    if len(unique_values) == 1:
        return float(unique_values[0])

    return None


def _adjust_config_for_data(
    config: Dict[str, Any],
    transformer_plugin: str,
    sample_data: pd.DataFrame,
) -> Dict[str, Any]:
    """Adjust transformer config based on actual data values.

    For binned_distribution, generates smart bins based on data range
    instead of using default bins that may not match the data.

    Args:
        config: Original transformer config
        transformer_plugin: Name of the transformer plugin
        sample_data: The loaded sample data

    Returns:
        Adjusted config with appropriate parameters
    """
    if transformer_plugin != "binned_distribution":
        return config

    # Get the field name from config
    field = config.get("field")
    if not field or field not in sample_data.columns:
        return config

    # Get numeric values from the field
    field_data = pd.to_numeric(sample_data[field], errors="coerce").dropna()

    if field_data.empty:
        return config

    # Calculate min/max and generate smart bins
    min_val = float(field_data.min())
    max_val = float(field_data.max())

    smart_bins = _generate_smart_bins(min_val, max_val)

    # Update config with smart bins
    adjusted_config = config.copy()
    adjusted_config["bins"] = smart_bins

    logger.debug(
        f"Adjusted bins for '{field}': range [{min_val}, {max_val}] -> bins {smart_bins}"
    )

    return adjusted_config


def _build_dynamic_template_info(
    parsed: Dict[str, Any], template_id: str, source: Optional[str] = None
) -> Dict[str, Any]:
    """Build template info for dynamic templates based on parsed ID.

    Args:
        parsed: Dict with 'column', 'transformer', 'widget' keys
        template_id: Original template ID string
        source: Optional data source (entity name). Defaults to "occurrences".

    Returns:
        Dict with 'name', 'plugin' (transformer), 'widget', 'config'
    """
    column = parsed["column"]
    transformer = parsed["transformer"]
    widget = parsed["widget"]

    # Use provided source or default to "occurrences"
    data_source = source or "occurrences"

    # Build config based on transformer type
    col_name = column.replace("_", " ").title()

    if transformer == "binned_distribution":
        # Guess unit based on column name
        col_lower = column.lower()
        unit = ""
        if "height" in col_lower or "hauteur" in col_lower:
            unit = "m"
        elif "dbh" in col_lower or "diameter" in col_lower:
            unit = "cm"
        elif "elevation" in col_lower or "altitude" in col_lower:
            unit = "m"

        x_label = column.upper()
        if unit:
            x_label = f"{x_label} ({unit})"

        config = {
            "source": data_source,
            "field": column,
            "bins": [0, 10, 20, 30, 40, 50, 100, 200, 500],  # Default bins
            "include_percentages": True,
            "x_label": x_label,
            "y_label": "%",
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
            "source": data_source,
            "field": column,
            "stats": ["mean", "min", "max"],
            "units": unit,
            "max_value": max_value,
        }
        name = f"Statistiques {col_name}"

    elif transformer == "categorical_distribution":
        config = {
            "source": data_source,
            "field": column,
            "include_percentages": True,
        }
        name = f"Répartition par {col_name}"

    elif transformer == "top_ranking":
        config = {
            "source": data_source,
            "field": column,
            "mode": "direct",
            "count": 10,
        }
        name = f"Top {col_name}"

    elif transformer == "binary_counter":
        config = {
            "source": data_source,
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
        # Standard field_aggregator for occurrences data
        config = {
            "source": "occurrences",
            "fields": [{"source": "occurrences", "field": column, "target": column}],
        }
        name = f"Info {col_name}"

    # Class_object extractors (for pre-calculated CSV data)
    elif transformer == "class_object_field_aggregator":
        # Field aggregator for class_object CSV data (scalars like elevation_max)
        config = {
            "source": "shape_stats",
            "fields": [{"class_object": column, "target": column}],
        }
        name = f"Info {col_name}"

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

    # binary_counter -> donut_chart: convert dict format to arrays
    if transformer == "binary_counter" and widget == "donut_chart":
        # binary_counter output: {'UM': 15731, 'NUM': 5749, 'UM_percent': 73.24, 'NUM_percent': 26.76}
        # Extract labels and counts from the dict (skip percentage keys)
        labels = []
        counts = []
        percentages = []

        for key, value in data.items():
            if not key.endswith("_percent"):
                labels.append(key)
                counts.append(value)
                # Try to find the corresponding percentage
                percent_key = f"{key}_percent"
                if percent_key in data:
                    percentages.append(data[percent_key])

        if labels and counts:
            result = {
                "labels": labels,
                "counts": counts,
            }
            if percentages and len(percentages) == len(labels):
                result["percentages"] = percentages
            return result

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

        # For bar_plot, handle data based on type (numeric vs categorical)
        render_data = data
        if widget_name == "bar_plot":
            tops = data.get("tops", [])
            counts = data.get("counts", [])
            if tops and counts:
                # Check if data is numeric (distribution bins like dbh)
                is_numeric = all(
                    isinstance(t, (int, float))
                    or (
                        isinstance(t, str)
                        and t.replace(".", "").replace("-", "").isdigit()
                    )
                    for t in tops[:5]  # Check first 5 items
                )

                if is_numeric:
                    # Numeric bins: sort by bin value descending (largest bins first)
                    paired = sorted(
                        zip(tops, counts),
                        key=lambda x: float(x[0])
                        if isinstance(x[0], (int, float))
                        or x[0].replace(".", "").replace("-", "").isdigit()
                        else 0,
                        reverse=True,
                    )
                    tops, counts = zip(*paired) if paired else ([], [])
                elif len(tops) > 10:
                    # Categorical: sort by value descending and take top 10
                    paired = sorted(zip(tops, counts), key=lambda x: -x[1])[:10]
                    tops, counts = zip(*paired) if paired else ([], [])

                render_data = {
                    **data,
                    "tops": list(tops),
                    "counts": list(counts),
                    "_is_numeric": is_numeric,
                }

        # Build widget params based on extractor type
        widget_params = _build_widget_params_for_class_object(
            extractor, widget_name, render_data, title
        )

        # Validate params if the plugin has a param_schema
        if hasattr(plugin_instance, "param_schema") and plugin_instance.param_schema:
            validated_params = plugin_instance.param_schema.model_validate(
                widget_params
            )
        else:
            validated_params = widget_params

        return plugin_instance.render(render_data, validated_params)
    except Exception as e:
        logger.exception(f"Error rendering class_object widget '{widget_name}': {e}")
        return f"<p class='error'>Widget render error: {str(e)}</p>"


def _build_widget_params_for_class_object(
    extractor: str, widget: str, data: Dict[str, Any], title: str
) -> Dict[str, Any]:
    """Build widget parameters for class_object data.

    Class_object data format: {"tops": [...], "counts": [...], "source": "...", "class_object": "..."}

    Widget params depend on the widget type:
    - bar_plot: horizontal with y_axis="tops", x_axis="counts" (like top_ranking)
    - donut_chart: values_field="counts", labels_field="tops"
    - radial_gauge: value_field (uses first value), max_value
    """
    if widget == "bar_plot":
        # Check if data is numeric (distribution) or categorical (ranking)
        is_numeric = data.get("_is_numeric", False)

        if is_numeric:
            # Numeric bins (like dbh) → vertical bar chart with gradient
            # Detect if values are percentages (sum ≈ 100)
            counts = data.get("counts", [])
            total = sum(counts) if counts else 0
            is_percentage = 95 <= total <= 105  # Allow some tolerance

            # Get class_object name for x-axis label
            class_object_name = data.get("class_object", "").upper()
            x_label = class_object_name if class_object_name else "Classe"
            y_label = "%" if is_percentage else "Effectif"

            return {
                "x_axis": "tops",  # bins on x-axis
                "y_axis": "counts",
                "title": title,
                "orientation": "v",
                "sort_order": "descending",
                "gradient_color": "#8B4513",
                "gradient_mode": "luminance",
                "show_legend": False,  # no legend for distributions
                "labels": {
                    "tops": x_label,
                    "counts": y_label,
                },  # Applied from x_label/y_label
            }
        else:
            # Categorical (like top_ranking) → horizontal bar chart with auto_color
            return {
                "x_axis": "counts",
                "y_axis": "tops",
                "title": title,
                "orientation": "h",
                "sort_order": "descending",
                "auto_color": True,
            }

    elif widget == "donut_chart":
        return {
            "values_field": "counts",
            "labels_field": "tops",
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


# =============================================================================
# Multi-Field Combined Widget Suggestions
# =============================================================================


@router.post(
    "/{reference_name}/combined-suggestions",
    response_model=CombinedWidgetResponse,
    summary="Get combined widget suggestions for selected fields",
    description="""
    Analyze selected fields and suggest widgets that combine them meaningfully.

    For example, selecting [month_obs, flower, fruit] would suggest a phenology
    time series widget that shows the temporal distribution of flowering and fruiting.

    The endpoint also returns detected semantic groups for proactive suggestions.
    """,
)
async def get_combined_widget_suggestions(
    reference_name: str,
    request: CombinedWidgetRequest,
):
    """Get combined widget suggestions for a set of selected fields."""
    try:
        db_path = get_database_path()
        if not db_path:
            raise HTTPException(status_code=500, detail="Database path not configured")

        from niamoto.core.imports.registry import EntityRegistry
        from niamoto.core.imports.data_analyzer import (
            DataCategory,
            FieldPurpose,
            EnrichedColumnProfile,
        )

        db = Database(str(db_path), read_only=True)
        try:
            registry = EntityRegistry(db)

            # Get the source entity
            entity_meta = registry.get(request.source_name)
            semantic_profile = entity_meta.config.get("semantic_profile", {})
            columns = semantic_profile.get("columns", [])

            if not columns:
                return CombinedWidgetResponse(suggestions=[], semantic_groups=[])

            # Convert stored profiles to EnrichedColumnProfile objects
            all_profiles = []
            for col_data in columns:
                cat_str = col_data.get("data_category", "categorical")
                try:
                    data_cat = DataCategory(cat_str)
                except ValueError:
                    data_cat = DataCategory.CATEGORICAL

                purpose_str = col_data.get("field_purpose", "metadata")
                try:
                    field_purpose = FieldPurpose(purpose_str)
                except ValueError:
                    field_purpose = FieldPurpose.METADATA

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
                    sample_values=col_data.get("suggested_labels") or [],
                    confidence=col_data.get("confidence", 0.5),
                    data_category=data_cat,
                    field_purpose=field_purpose,
                    suggested_bins=col_data.get("suggested_bins"),
                    suggested_labels=col_data.get("suggested_labels"),
                    cardinality=col_data.get("cardinality", 0),
                    value_range=value_range,
                )
                all_profiles.append(profile)

            # Get combined widget suggestions
            patterns = suggest_combined_widgets(
                selected_field_names=request.selected_fields,
                all_profiles=all_profiles,
                source_name=request.source_name,
            )

            # Get semantic groups for proactive suggestions
            semantic_groups = detect_all_groups(all_profiles)

            # Convert patterns to response format
            suggestions = []
            for pattern in patterns:
                suggestions.append(
                    CombinedWidgetSuggestion(
                        pattern_type=pattern.pattern_type.value,
                        name=pattern.name,
                        description=pattern.description,
                        fields=pattern.fields,
                        field_roles=pattern.field_roles,
                        confidence=pattern.confidence,
                        is_recommended=pattern.is_recommended,
                        transformer_config={
                            "plugin": pattern.transformer_plugin,
                            "params": pattern.transformer_params,
                        },
                        widget_config={
                            "plugin": pattern.widget_plugin,
                            "params": pattern.widget_params,
                        },
                    )
                )

            return CombinedWidgetResponse(
                suggestions=suggestions,
                semantic_groups=semantic_groups,
            )

        finally:
            db.close_db_session()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting combined widget suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{reference_name}/semantic-groups",
    response_model=SemanticGroupsResponse,
    summary="Detect semantic field groups for proactive suggestions",
    description="""
    Proactively detect groups of fields that could form combined widgets.

    Returns groups like:
    - Phenology: month_obs + flower + fruit
    - Dimensions: dbh + height
    - Leaf traits: leaf_area + leaf_sla + leaf_ldmc

    These can be used to show suggestions like "These fields could be combined..."
    """,
)
async def get_semantic_groups(
    reference_name: str,
    entity: str = Query(default="occurrences", description="Source entity name"),
):
    """Detect semantic groups for proactive combined widget suggestions."""
    try:
        db_path = get_database_path()
        if not db_path:
            raise HTTPException(status_code=500, detail="Database path not configured")

        from niamoto.core.imports.registry import EntityRegistry
        from niamoto.core.imports.data_analyzer import (
            DataCategory,
            FieldPurpose,
            EnrichedColumnProfile,
        )

        db = Database(str(db_path), read_only=True)
        try:
            registry = EntityRegistry(db)

            entity_meta = registry.get(entity)
            semantic_profile = entity_meta.config.get("semantic_profile", {})
            columns = semantic_profile.get("columns", [])

            if not columns:
                return SemanticGroupsResponse(groups=[])

            # Convert to EnrichedColumnProfile objects
            all_profiles = []
            for col_data in columns:
                cat_str = col_data.get("data_category", "categorical")
                try:
                    data_cat = DataCategory(cat_str)
                except ValueError:
                    data_cat = DataCategory.CATEGORICAL

                purpose_str = col_data.get("field_purpose", "metadata")
                try:
                    field_purpose = FieldPurpose(purpose_str)
                except ValueError:
                    field_purpose = FieldPurpose.METADATA

                profile = EnrichedColumnProfile(
                    name=col_data.get("name", "unknown"),
                    dtype=col_data.get("dtype", "object"),
                    semantic_type=col_data.get("semantic_type"),
                    unique_ratio=col_data.get("unique_ratio", 0.0),
                    null_ratio=col_data.get("null_ratio", 0.0),
                    sample_values=[],
                    confidence=col_data.get("confidence", 0.5),
                    data_category=data_cat,
                    field_purpose=field_purpose,
                    cardinality=col_data.get("cardinality", 0),
                    value_range=None,
                )
                all_profiles.append(profile)

            # Detect semantic groups
            groups = detect_all_groups(all_profiles)

            return SemanticGroupsResponse(groups=groups)

        finally:
            db.close_db_session()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error detecting semantic groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))
