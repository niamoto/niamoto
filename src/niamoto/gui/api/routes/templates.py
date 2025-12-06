"""
API routes for widget templates.

Provides endpoints for:
- Listing available templates by entity type
- Getting template suggestions based on data analysis
- Generating transform.yml configuration from selected templates
- Live preview of widgets on sample data
"""

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
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.matching.matcher import SmartMatcher
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.common.database import Database

logger = logging.getLogger(__name__)

# Static category definitions (widget categories are predefined, not data-driven)
WIDGET_CATEGORIES = {
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

    Returns suggestions from two sources:
    1. Column-based suggestions from semantic profiles (occurrence data)
    2. Class_object suggestions from pre-calculated CSV sources

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

    # Combine both types of suggestions
    # Class_object suggestions are always included (pre-calculated CSV data)
    # Column suggestions are limited to fill the remaining slots
    column_suggestion_dicts = [s.to_dict() for s in column_suggestions]

    # Sort column suggestions by confidence
    column_suggestion_dicts.sort(key=lambda s: -s.get("confidence", 0))

    # Calculate how many column suggestions we can include
    remaining_slots = max(0, max_suggestions - len(class_object_suggestions))
    limited_column_suggestions = column_suggestion_dicts[:remaining_slots]

    # Combine: class_object first (always included), then column suggestions
    all_suggestions = class_object_suggestions + limited_column_suggestions

    # Sort the final result by confidence
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


def _get_hierarchy_info(import_config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract hierarchy information from import.yml.

    Returns dict with:
    - reference_name: Name of the hierarchical reference (e.g., 'taxons')
    - levels: List of hierarchy levels ['family', 'genus', 'species', ...]
    - source_dataset: Name of source dataset (e.g., 'occurrences')
    - level_columns: Mapping of level name to column name
    """
    references = import_config.get("entities", {}).get("references", {})

    for ref_name, ref_config in references.items():
        if ref_config.get("kind") == "hierarchical":
            hierarchy = ref_config.get("hierarchy", {})
            levels = hierarchy.get("levels", [])

            connector = ref_config.get("connector", {})
            source_dataset = connector.get("source", "occurrences")

            # Get level to column mapping
            level_columns = {}
            extraction = connector.get("extraction", {})
            for level_info in extraction.get("levels", []):
                level_columns[level_info["name"]] = level_info.get(
                    "column", level_info["name"]
                )

            return {
                "reference_name": ref_name,
                "levels": levels,
                "source_dataset": source_dataset,
                "level_columns": level_columns,
            }

    raise HTTPException(
        status_code=400,
        detail="No hierarchical reference found in import.yml",
    )


def _find_representative_entity(
    db: Database, hierarchy_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Find a representative entity for preview.

    Strategy: Pick from the first level (e.g., 'family') an entity
    that has enough data to display meaningful results.
    """
    source_dataset = hierarchy_info["source_dataset"]
    levels = hierarchy_info["levels"]
    level_columns = hierarchy_info["level_columns"]

    # Use first level (most aggregated) for representative preview
    if not levels:
        raise HTTPException(status_code=400, detail="No hierarchy levels defined")

    first_level = levels[0]
    column_name = level_columns.get(first_level, first_level)

    # Find the table
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
    except Exception as e:
        logger.exception(f"Error finding representative entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _load_sample_data(
    db: Database,
    representative: Dict[str, Any],
    template_config: Dict[str, Any],
    limit: int = None,  # None = no limit (all data)
) -> pd.DataFrame:
    """Load sample data for the representative entity.

    Args:
        limit: Max rows to load. None for all data, or int for random sampling.
    """
    table_name = representative["table_name"]
    column = representative["column"]
    value = representative["value"]

    # Get required field from template config
    required_field = template_config.get("field", "*")

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
                    "x_field": "bin",
                    "y_field": "count",
                },
                "gradient_color": "#10b981",
                "gradient_mode": "luminance",
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


@router.get("/preview/{template_id}", response_class=HTMLResponse)
async def preview_template(
    template_id: str,
    group_by: str = Query(
        default=None, description="Group by reference (auto-detected if not provided)"
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

    All templates have format: {column}_{transformer}_{widget}
    (e.g., 'height_binned_distribution_bar_plot')

    Args:
        template_id: ID of the template to preview
        group_by: Reference to group by (auto-detected from import.yml if not provided)

    Returns:
        HTML content of the rendered widget
    """
    # Ensure plugins are loaded
    _ensure_plugins_loaded()

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

                # Add preview metadata
                preview_info = f"""
                <div style="position: absolute; bottom: 8px; left: 8px; font-size: 11px; color: #9ca3af; z-index: 1000;">
                    Source: {co_data.get("source", "CSV")}
                </div>
                """

                return HTMLResponse(
                    content=_wrap_html_response(
                        widget_html + preview_info, title=template_name
                    )
                )
            finally:
                if db:
                    db.close_db_session()

        # Standard flow for occurrence-based templates
        # Load import.yml
        import_config = _load_import_config(work_dir)

        # Get hierarchy info
        hierarchy_info = _get_hierarchy_info(import_config)

        # Get database
        db_path = get_database_path()
        if not db_path:
            return HTMLResponse(
                content=_wrap_html_response("<p class='error'>Database not found</p>"),
                status_code=404,
            )

        db = Database(str(db_path), read_only=True)
        try:
            # Find representative entity
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

            # Add preview metadata
            preview_info = f"""
            <div style="position: absolute; bottom: 8px; left: 8px; font-size: 11px; color: #9ca3af; z-index: 1000;">
                Preview: {representative["value"]} ({representative["count"]} occurrences)
            </div>
            """

            return HTMLResponse(
                content=_wrap_html_response(
                    widget_html + preview_info, title=template_name
                )
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
