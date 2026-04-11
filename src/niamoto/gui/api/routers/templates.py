"""
API routes for widget templates.

Provides endpoints for:
- Listing available templates by entity type
- Getting template suggestions based on data analysis
- Generating transform.yml configuration from selected templates
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException, Query

from niamoto.common.exceptions import DatabaseQueryError
from niamoto.common.transform_config_models import validate_transform_config
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
from niamoto.gui.api.services.templates.utils.widget_utils import (
    map_transformer_to_widget,
    generate_widget_title,
    generate_widget_params,
)

from niamoto.gui.api.services.templates.suggestion_service import (  # noqa: E402
    generate_navigation_suggestion,
    generate_general_info_suggestion,
    get_entity_map_suggestions,
    get_class_object_suggestions,
    get_reference_field_suggestions,
)

from niamoto.core.imports.template_suggester import (  # noqa: E402
    TemplateSuggester,
    TemplateSuggestion,
)
from niamoto.core.imports.class_object_analyzer import analyze_csv  # noqa: E402
from niamoto.core.imports.multi_field_detector import (  # noqa: E402
    suggest_combined_widgets,
    detect_all_groups,
)
from niamoto.gui.api.context import get_database_path, get_working_directory  # noqa: E402
from niamoto.common.database import Database  # noqa: E402

logger = logging.getLogger(__name__)


def _is_export_only_widget_config(widget_config: Dict[str, Any]) -> bool:
    """Return True for widgets that belong only in export.yml."""
    return widget_config.get("plugin") == "hierarchical_nav_widget"


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
    navigation_suggestion = generate_navigation_suggestion(reference_name)

    # Try to get column-based suggestions (may fail if no semantic profile)
    try:
        db_path = get_database_path()
        if db_path:
            from niamoto.core.imports.registry import EntityRegistry, EntityKind
            from niamoto.core.imports.data_analyzer import EnrichedColumnProfile

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
                                profile = EnrichedColumnProfile.from_stored_dict(
                                    col_data
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
    class_object_suggestions = get_class_object_suggestions(reference_name)

    # Get entity-specific map suggestions (for plots/shapes)
    entity_map_suggestions = get_entity_map_suggestions(reference_name)

    # Generate general_info suggestion (field_aggregator for metadata)
    general_info_suggestion = generate_general_info_suggestion(reference_name)

    # Get suggestions based on reference entity table columns (e.g., plots.holdridge, plots.rainfall)
    reference_field_suggestions = get_reference_field_suggestions(reference_name)

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
        # Extract params from config - handle multiple structures:
        # 1. Combined: {"transformer": {"plugin":..,"params":{..}}, "widget": {"plugin":..,"params":{..}}}
        # 2. Nested:   {"plugin": ..., "params": {...}}
        # 3. Flat:     {direct params like "field": "height", "source": "plots", ...}
        cfg = template.config
        export_override = None

        if isinstance(cfg, dict) and "transformer" in cfg and "widget" in cfg:
            # Combined structure from suggestions — split transformer/widget
            transformer_cfg = cfg["transformer"]
            params = transformer_cfg.get("params", {})
            # Carry widget config as export_override for _generate_export_config
            widget_cfg = cfg["widget"]
            export_override = {
                "plugin": widget_cfg.get("plugin"),
                "title": cfg.get("title") or template.config.get("title"),
                "params": widget_cfg.get("params"),
            }
        elif isinstance(cfg, dict) and "params" in cfg and "plugin" in cfg:
            # Nested structure - extract just the params
            params = cfg["params"]
        else:
            # Flat structure - use config directly as params
            params = cfg

        widget_data: Dict[str, Any] = {
            "plugin": template.plugin,
            "params": params,
        }

        # Use explicit widget_plugin/widget_params from suggestion if available,
        # otherwise fall back to export_override from combined config structure
        if not export_override and template.widget_plugin:
            export_override = {
                "plugin": template.widget_plugin,
                "title": cfg.get("title") if isinstance(cfg, dict) else None,
                "params": template.widget_params,
            }

        if export_override:
            widget_data["export_override"] = export_override

        widgets_data[template.template_id] = widget_data

    # Build sources section based on reference kind and import.yml metadata
    relation_from_import = None
    source_dataset = "occurrences"
    ref_config: Dict[str, Any] = {}
    relation_config: Dict[str, Any] = {}
    connector_config: Dict[str, Any] = {}
    datasets_config: Dict[str, Any] = {}

    work_dir = get_working_directory()
    if work_dir:
        import_path = Path(work_dir) / "config" / "import.yml"
        if import_path.exists():
            try:
                with open(import_path, "r", encoding="utf-8") as f:
                    import_config = yaml.safe_load(f) or {}
                entities = import_config.get("entities", {}) or {}
                datasets_config = entities.get("datasets", {}) or {}
                refs = entities.get("references", {}) or {}
                ref_config = (
                    refs.get(request.group_by, {}) if isinstance(refs, dict) else {}
                )
                relation_config = ref_config.get("relation", {}) or {}
                connector_config = ref_config.get("connector", {}) or {}

                source_dataset = (
                    relation_config.get("dataset")
                    or connector_config.get("source")
                    or (
                        "occurrences"
                        if "occurrences" in datasets_config
                        else (
                            next(iter(datasets_config))
                            if datasets_config
                            else "occurrences"
                        )
                    )
                )

                if relation_config:
                    # Convert import.yml format to transform.yml format
                    relation_from_import = {
                        "plugin": "direct_reference",
                        "key": relation_config.get("foreign_key"),
                        "ref_key": relation_config.get("reference_key"),
                        "ref_field": relation_config.get("reference_key"),
                    }
            except Exception as e:
                logger.warning(f"Error reading import.yml for relation: {e}")

    if request.reference_kind == "hierarchical":
        # Hierarchical references use nested_set for tree aggregation
        extraction = connector_config.get("extraction", {}) if connector_config else {}
        hierarchy_key = (
            relation_config.get("foreign_key")
            or (relation_from_import.get("key") if relation_from_import else None)
            or extraction.get("id_column")
            or f"id_{request.group_by}ref"
        )
        hierarchy_ref_key = (
            relation_config.get("reference_key")
            or (relation_from_import.get("ref_key") if relation_from_import else None)
            or f"{request.group_by}_id"
        )
        sources = [
            {
                "name": source_dataset,
                "data": source_dataset,
                "grouping": request.group_by,
                "relation": {
                    "plugin": "nested_set",
                    "key": hierarchy_key,
                    "ref_key": hierarchy_ref_key,
                    "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
                },
            }
        ]
    elif request.reference_kind == "spatial":
        # Spatial references should not invent a dataset FK like `shapes_id`.
        # They rely on explicit auxiliary sources (for example shape_stats) instead.
        sources = []
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
                "name": source_dataset,
                "data": source_dataset,
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

        # Use explicit export override if provided (combined widgets)
        export_override = widget_config.get("export_override")
        if export_override and isinstance(export_override, dict):
            export_widget: Dict[str, Any] = {
                "plugin": export_override.get(
                    "plugin", map_transformer_to_widget(plugin, widget_id)
                ),
                "title": export_override.get(
                    "title", generate_widget_title(widget_id, plugin, params)
                ),
                "data_source": widget_id,
                "layout": {
                    "colspan": 1,
                    "order": widget_order,
                },
            }
            if export_override.get("params"):
                export_widget["params"] = export_override["params"]
        else:
            # Map transformer plugins to widget plugins
            widget_plugin = map_transformer_to_widget(plugin, widget_id)

            # Build widget config for export
            export_widget = {
                "plugin": widget_plugin,
                "title": generate_widget_title(widget_id, plugin, params),
                "data_source": widget_id,  # Links to widgets_data key in transform.yml
                "layout": {
                    "colspan": 1,  # Default: half width (2 widgets per row)
                    "order": widget_order,
                },
            }

            # Add widget-specific params based on type
            widget_params = generate_widget_params(widget_plugin, plugin, params)
            if widget_params:
                export_widget["params"] = widget_params

        widget_order += 1
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
                loaded = yaml.safe_load(f) or []
                if not isinstance(loaded, list):
                    raise HTTPException(
                        status_code=400,
                        detail="transform.yml must be a list of groups",
                    )
                existing_groups = [g for g in loaded if isinstance(g, dict)]

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

        transform_widgets_data = {
            widget_id: widget_config
            for widget_id, widget_config in request.widgets_data.items()
            if isinstance(widget_config, dict)
            and not _is_export_only_widget_config(widget_config)
        }

        # Track changes on transform.yml only. Export-only widgets like
        # hierarchical_nav_widget are written exclusively to export.yml.
        existing_widgets = {
            widget_id: widget_config
            for widget_id, widget_config in group_config.get("widgets_data", {}).items()
            if isinstance(widget_config, dict)
            and not _is_export_only_widget_config(widget_config)
        }
        widgets_added = 0
        widgets_updated = 0
        widgets_removed = 0

        if request.mode == "merge":
            # Merge mode: add new widgets to existing ones, update if exists
            merged_widgets = dict(existing_widgets)
            for widget_id, widget_config in transform_widgets_data.items():
                if widget_id in merged_widgets:
                    widgets_updated += 1
                else:
                    widgets_added += 1
                merged_widgets[widget_id] = widget_config
            group_config["widgets_data"] = merged_widgets
        else:
            # Replace mode: count changes and replace entirely
            for widget_id in transform_widgets_data:
                if widget_id in existing_widgets:
                    widgets_updated += 1
                else:
                    widgets_added += 1

            for widget_id in existing_widgets:
                if widget_id not in transform_widgets_data:
                    widgets_removed += 1

            # Replace widgets_data entirely (not merge) to handle deletions
            group_config["widgets_data"] = dict(transform_widgets_data)

        # Update the group in the list
        existing_groups[group_index] = group_config

        # Generate export.yml BEFORE cleaning export_override (shared references)
        _generate_export_config(
            work_dir,
            group_name,
            request.widgets_data,
            group_config.get("sources", []),
            mode=request.mode,
        )

        # Clean export_override from widgets_data before writing to transform.yml
        for wid, wcfg in group_config.get("widgets_data", {}).items():
            if isinstance(wcfg, dict):
                wcfg.pop("export_override", None)

        # Write updated config as list
        with open(transform_path, "w", encoding="utf-8") as f:
            yaml.dump(
                validate_transform_config(existing_groups),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=120,
            )

        logger.info(
            f"Saved transform config for group '{group_name}' to {transform_path}"
        )

        # Invalider le cache du moteur de preview unifié après sauvegarde
        try:
            from niamoto.gui.api.services.preview_engine.engine import (
                get_preview_engine,
            )

            engine = get_preview_engine()
            if engine:
                engine.invalidate()
        except Exception:
            pass  # Non-fatal

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
            config = yaml.safe_load(f) or []

        if not config:
            return {"configured_ids": [], "has_config": False}

        if not isinstance(config, list):
            logger.warning(
                "Invalid transform.yml format: expected list, got %s",
                type(config).__name__,
            )
            return {"configured_ids": [], "has_config": False}

        for group in config:
            if not isinstance(group, dict):
                continue
            if group.get("group_by") == group_by:
                widgets_data = group.get("widgets_data", {})
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
            config = yaml.safe_load(f) or []

        if not isinstance(config, list):
            raise HTTPException(
                status_code=400, detail="transform.yml must be a list of groups"
            )
        config = validate_transform_config(config)

        # Find group config
        group_config = None
        for g in config:
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
        tabular_extensions = (".csv", ".tsv", ".txt")
        for src in sources:
            data_path = src.get("data", "")
            if any(data_path.endswith(ext) for ext in tabular_extensions):
                if source_name is None or src.get("name") == source_name:
                    csv_source = src
                    break

        if not csv_source:
            raise HTTPException(
                status_code=404,
                detail=f"No tabular source found for group '{group_by}'",
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
    from niamoto.core.plugins.transformers.analysis import (  # noqa: F401
        scatter_analysis,
        boolean_comparison,
    )

    # Import widget plugins
    from niamoto.core.plugins.widgets import (  # noqa: F401
        bar_plot,
        donut_chart,
        interactive_map,
        radial_gauge,
        info_grid,
        scatter_plot,
    )


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

        db = Database(str(db_path))
        try:
            registry = EntityRegistry(db)

            # Get the source entity
            try:
                entity_meta = registry.get(request.source_name)
            except (DatabaseQueryError, KeyError):
                logger.warning(f"Entity '{request.source_name}' not found in registry")
                return CombinedWidgetResponse(suggestions=[], semantic_groups=[])
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

        db = Database(str(db_path))
        try:
            registry = EntityRegistry(db)

            try:
                entity_meta = registry.get(entity)
            except (DatabaseQueryError, KeyError):
                logger.warning(
                    f"Entity '{entity}' not found in registry, returning empty groups"
                )
                return SemanticGroupsResponse(groups=[])
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
