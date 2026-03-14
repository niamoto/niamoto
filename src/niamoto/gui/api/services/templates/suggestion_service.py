"""
Suggestion service for templates.

Provides functions to generate widget suggestions based on data analysis.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml
from sqlalchemy import text

from niamoto.common.table_resolver import (
    quote_identifier,
    resolve_entity_table as shared_resolve_entity_table,
)
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.core.imports.widget_generator import WidgetGenerator
from niamoto.core.imports.class_object_suggester import suggest_widgets_for_source

logger = logging.getLogger(__name__)


def _load_import_config() -> Dict[str, Any]:
    """Load import.yml from current working directory when available."""
    work_dir = get_working_directory()
    if not work_dir:
        return {}

    import_path = Path(work_dir) / "config" / "import.yml"
    if not import_path.exists():
        return {}

    try:
        with open(import_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _get_entity_registry(db: Any):
    """Create an EntityRegistry when metadata table is available."""
    try:
        from niamoto.core.imports.registry import EntityRegistry

        return EntityRegistry(db)
    except Exception:
        return None


def _resolve_entity_table(
    db: Any, entity_name: str, registry: Any = None, kind: Optional[str] = None
) -> Optional[str]:
    """Resolve entity table using shared resolver."""
    return shared_resolve_entity_table(db, entity_name, registry=registry, kind=kind)


def _get_reference_config(
    reference_name: str, import_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Return reference config from import.yml when available."""
    references = import_config.get("entities", {}).get("references", {})
    if isinstance(references, dict):
        cfg = references.get(reference_name)
        if isinstance(cfg, dict):
            return cfg
    return {}


def _get_first_dataset_name(
    import_config: Dict[str, Any], registry: Any = None
) -> Optional[str]:
    """Resolve default dataset name from registry metadata, then import.yml."""
    if registry:
        try:
            from niamoto.core.imports.registry import EntityKind

            datasets = registry.list_entities(kind=EntityKind.DATASET)
            if datasets:
                return datasets[0].name
        except Exception:
            pass

    datasets_cfg = import_config.get("entities", {}).get("datasets", {})
    if isinstance(datasets_cfg, dict) and datasets_cfg:
        return next(iter(datasets_cfg))
    return None


def _pick_identifier_column(
    columns: List[str],
    entity_name: Optional[str] = None,
    preferred: Optional[str] = None,
) -> Optional[str]:
    """Pick a likely identifier column."""
    if not columns:
        return None

    lowered = {c.lower(): c for c in columns}
    candidates: List[str] = []
    if preferred:
        candidates.append(preferred)
    if entity_name:
        candidates.extend([f"id_{entity_name}", f"{entity_name}_id", entity_name])
    candidates.extend(["id", "uuid"])

    for candidate in candidates:
        resolved = lowered.get(candidate.lower())
        if resolved:
            return resolved

    return next((c for c in columns if c.lower().endswith("_id")), columns[0])


def _pick_name_column(columns: List[str], id_field: str, entity_name: str) -> str:
    """Pick a likely display name column."""
    lowered = {c.lower(): c for c in columns}
    candidates = ["full_name", "name", "label", "title", entity_name]
    for candidate in candidates:
        resolved = lowered.get(candidate.lower())
        if resolved:
            return resolved

    return next(
        (
            c
            for c in columns
            if c != id_field
            and any(token in c.lower() for token in ("name", "label", "title"))
        ),
        id_field,
    )


def generate_navigation_suggestion(reference_name: str) -> Optional[Dict[str, Any]]:
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

        db = Database(str(db_path))
        try:
            import_config = _load_import_config()
            ref_config = _get_reference_config(reference_name, import_config)
            registry = _get_entity_registry(db)

            table_name = _resolve_entity_table(
                db, reference_name, registry=registry, kind="reference"
            )
            if not table_name:
                return WidgetGenerator.generate_navigation_suggestion(
                    reference_name=reference_name,
                    is_hierarchical=False,
                    hierarchy_fields=None,
                )

            # Get column names from the table
            quoted_table_name = quote_identifier(db, table_name)
            columns_df = pd.read_sql(
                text(f"SELECT * FROM {quoted_table_name} LIMIT 0"),
                db.engine,
            )
            columns = columns_df.columns.tolist()
            columns_set = set(columns)

            # Detect hierarchy structure
            has_nested_set = "lft" in columns_set and "rght" in columns_set
            has_parent = "parent_id" in columns_set
            has_level = "level" in columns_set

            is_hierarchical = has_nested_set or (has_parent and has_level)

            # Detect ID field
            schema = (
                ref_config.get("schema", {}) if isinstance(ref_config, dict) else {}
            )
            preferred_id = schema.get("id_field") if isinstance(schema, dict) else None
            id_field = _pick_identifier_column(
                columns, entity_name=reference_name, preferred=preferred_id
            )
            if not id_field:
                id_field = "id"
            name_field = _pick_name_column(columns, id_field, reference_name)

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


def generate_general_info_suggestion(reference_name: str) -> Optional[Dict[str, Any]]:
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

        db = Database(str(db_path))
        try:
            import_config = _load_import_config()
            ref_config = _get_reference_config(reference_name, import_config)
            registry = _get_entity_registry(db)

            ref_table = _resolve_entity_table(
                db, reference_name, registry=registry, kind="reference"
            )
            if not ref_table:
                return None

            # Get column info to exclude geometry columns (binary WKB causes encoding errors)
            quoted_ref_table = quote_identifier(db, ref_table)
            with db.engine.connect() as conn:
                result = conn.execute(text(f"DESCRIBE {quoted_ref_table}"))
                col_info = result.fetchall()
            safe_columns = [
                quote_identifier(db, c[0])
                for c in col_info
                if c[1].upper() not in ("GEOMETRY", "BLOB", "BYTEA")
                and not c[0].endswith("_geom")
            ]
            if not safe_columns:
                return None

            # Get sample data to analyze columns (excluding geometry)
            columns_sql = ", ".join(safe_columns)
            sample_df = pd.read_sql(
                text(f"SELECT {columns_sql} FROM {quoted_ref_table} LIMIT 100"),
                db.engine,
            )
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
            exclude_suffixes = ("_id", "_ref", "_key", "_idx", "_geom")

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

            # Add source dataset count if available
            try:
                relation = (
                    ref_config.get("relation", {})
                    if isinstance(ref_config, dict)
                    else {}
                )
                connector = (
                    ref_config.get("connector", {})
                    if isinstance(ref_config, dict)
                    else {}
                )
                source_dataset = relation.get("dataset") or connector.get("source")
                if not source_dataset:
                    source_dataset = _get_first_dataset_name(import_config, registry)

                source_table = _resolve_entity_table(
                    db, source_dataset or "", registry=registry, kind="dataset"
                )
                if source_dataset and source_table:
                    quoted_source_table = quote_identifier(db, source_table)
                    dataset_cols = pd.read_sql(
                        text(f"SELECT * FROM {quoted_source_table} LIMIT 0"), db.engine
                    ).columns.tolist()
                    count_field = _pick_identifier_column(
                        dataset_cols, entity_name=source_dataset
                    )
                    if not count_field and dataset_cols:
                        count_field = dataset_cols[0]
                    if count_field:
                        count_target = f"{source_dataset}_count"
                    else:
                        count_target = "records_count"

                    field_configs.append(
                        {
                            "source": source_dataset,
                            "field": count_field or "id",
                            "target": count_target,
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
                    "fields": field_configs,
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


def get_entity_map_suggestions(reference_name: str) -> List[Dict[str, Any]]:
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

    db = Database(str(db_path))

    try:
        import_config = _load_import_config()
        reference_config = _get_reference_config(reference_name, import_config)
        registry = _get_entity_registry(db)

        entity_table = _resolve_entity_table(
            db, reference_name, registry=registry, kind="reference"
        )
        if not entity_table:
            return suggestions

        quoted_entity_table = quote_identifier(db, entity_table)
        # Get columns from entity table
        columns_df = pd.read_sql(
            text(f"SELECT * FROM {quoted_entity_table} LIMIT 0"),
            db.engine,
        )
        columns = columns_df.columns.tolist()

        # =====================================================================
        # STEP 1: Read import.yml for declared geometry fields
        # =====================================================================
        declared_geometry_fields = set()

        schema_cfg = (
            reference_config.get("schema", {})
            if isinstance(reference_config, dict)
            else {}
        )
        schema_fields = (
            schema_cfg.get("fields", []) if isinstance(schema_cfg, dict) else []
        )
        for field in schema_fields:
            if isinstance(field, dict) and field.get("type") == "geometry":
                field_name = field.get("name")
                if field_name:
                    declared_geometry_fields.add(field_name)

        if work_dir and not reference_config:
            import_path = Path(work_dir) / "config" / "import.yml"
            if import_path.exists():
                try:
                    with open(import_path, "r", encoding="utf-8") as f:
                        import_config = yaml.safe_load(f) or {}

                    references = (
                        import_config.get("entities", {}).get("references", {}) or {}
                    )
                    ref_config = references.get(reference_name, {})
                    reference_config = (
                        ref_config if isinstance(ref_config, dict) else {}
                    )
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
                quoted_col_name = quote_identifier(db, col_name)
                sample = pd.read_sql(
                    text(
                        f"SELECT {quoted_col_name} FROM {quoted_entity_table} "
                        f"WHERE {quoted_col_name} IS NOT NULL LIMIT 1"
                    ),
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
        schema = (
            reference_config.get("schema", {})
            if isinstance(reference_config, dict)
            else {}
        )
        preferred_id = schema.get("id_field") if isinstance(schema, dict) else None
        id_field = _pick_identifier_column(
            columns, entity_name=reference_name, preferred=preferred_id
        )
        if not id_field:
            id_field = "id"
        name_field = _pick_name_column(columns, id_field, reference_name)

        # =====================================================================
        # STEP 4: Generate suggestions
        # =====================================================================
        ref_label = reference_name.replace("_", " ").title()

        for geom_col, geom_type in geometry_columns:
            # Single entity map (primary)
            single_id = f"{reference_name}_{geom_col}_entity_map"
            all_id = f"{reference_name}_{geom_col}_all_map"

            if geom_type == "point":
                single_name = f"{ref_label} location"
                single_desc = (
                    f"Map showing the position of the selected {reference_name} entity"
                )
                all_name = f"All {ref_label} map"
                all_desc = f"Map showing all {reference_name} entity positions"
                icon_single = "MapPin"
            else:
                single_name = f"{ref_label} polygon"
                single_desc = (
                    f"Map showing the polygon of the selected {reference_name} entity"
                )
                all_name = f"All {ref_label} map"
                all_desc = f"Map showing all {reference_name} polygons"
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

        return suggestions

    except Exception as e:
        logger.warning(
            f"Error detecting entity map columns for '{reference_name}': {e}"
        )
        return []
    finally:
        db.close_db_session()


def get_class_object_suggestions(reference_name: str) -> List[Dict[str, Any]]:
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


def get_reference_field_suggestions(reference_name: str) -> List[Dict[str, Any]]:
    """Generate widget suggestions based on columns in the reference entity table.

    This function analyzes columns in entity_{reference_name} (e.g., entity_plots)
    and suggests appropriate widgets for numeric, categorical, and boolean fields.

    The source for these suggestions is the reference itself (e.g., 'plots'),
    allowing widgets to display reference-level data like 'holdridge', 'rainfall'.

    Args:
        reference_name: Name of the reference (e.g., 'plots', 'shapes')

    Returns:
        List of widget suggestions in dict format
    """
    from niamoto.common.database import Database

    suggestions = []

    db_path = get_database_path()
    if not db_path:
        return suggestions

    db = Database(str(db_path))

    try:
        registry = _get_entity_registry(db)
        entity_table = _resolve_entity_table(
            db, reference_name, registry=registry, kind="reference"
        )
        if not entity_table:
            return suggestions

        quoted_entity_table = quote_identifier(db, entity_table)
        # Get sample data to analyze column types
        sample_df = pd.read_sql(
            text(f"SELECT * FROM {quoted_entity_table} LIMIT 100"),
            db.engine,
        )

        if sample_df.empty:
            return suggestions

        # Columns to exclude from suggestions
        excluded_patterns = [
            "id",
            "lft",
            "rght",
            "level",
            "parent_id",
            "location",
            "geo_pt",
            "extra_data",
            "geometry",
            "created",
            "updated",
        ]

        # Analyze each column
        for col in sample_df.columns:
            # Skip excluded columns
            if any(ex in col.lower() for ex in excluded_patterns):
                continue

            col_data = sample_df[col].dropna()
            if col_data.empty:
                continue

            # Determine column type and generate appropriate suggestions
            dtype = sample_df[col].dtype
            unique_count = col_data.nunique()
            null_ratio = sample_df[col].isna().sum() / len(sample_df)

            # Skip columns with too many nulls
            if null_ratio > 0.9:
                continue

            # Determine data category
            if pd.api.types.is_numeric_dtype(dtype):
                if unique_count == 2:
                    # Boolean-like (0/1 or similar)
                    category = "boolean"
                elif pd.api.types.is_float_dtype(dtype) or unique_count > 10:
                    # Continuous numeric
                    category = "numeric_continuous"
                else:
                    # Discrete numeric (few unique values)
                    category = "numeric_discrete"
            elif pd.api.types.is_bool_dtype(dtype):
                category = "boolean"
            else:
                # String/categorical
                if unique_count <= 20:
                    category = "categorical"
                else:
                    category = "categorical_high_card"

            # Generate suggestions based on category
            col_suggestions = _generate_suggestions_for_column(
                col_name=col,
                category=category,
                reference_name=reference_name,
                unique_count=unique_count,
                null_ratio=null_ratio,
                sample_values=col_data.head(10).tolist()
                if category in ("categorical", "boolean")
                else None,
            )
            suggestions.extend(col_suggestions)

        return suggestions

    except Exception as e:
        logger.warning(
            f"Error generating reference field suggestions for '{reference_name}': {e}"
        )
        return []
    finally:
        db.close_db_session()


def _generate_suggestions_for_column(
    col_name: str,
    category: str,
    reference_name: str,
    unique_count: int,
    null_ratio: float,
    sample_values: Optional[List] = None,
) -> List[Dict[str, Any]]:
    """Generate widget suggestions for a single column based on its data category.

    The output format matches TemplateSuggestionResponse model:
    - template_id, name, description, plugin, category, icon
    - confidence, source, source_name, is_recommended
    - config (contains transformer and widget configs)

    Args:
        col_name: Column name
        category: Data category (numeric_continuous, categorical, boolean, etc.)
        reference_name: Reference name for source
        unique_count: Number of unique values
        null_ratio: Ratio of null values
        sample_values: Sample values for categorical columns

    Returns:
        List of suggestion dicts matching TemplateSuggestionResponse
    """
    suggestions = []
    base_confidence = 0.70 - (null_ratio * 0.2)  # Penalize high null ratio

    # Format column name for display
    display_name = col_name.replace("_", " ").title()

    # Icon mapping for widget types
    icons = {
        "gauge": "Activity",
        "chart": "BarChart3",
        "donut": "PieChart",
        "map": "Map",
    }

    if category == "numeric_continuous":
        # Statistical summary (radial gauge)
        suggestions.append(
            {
                "template_id": f"{col_name}_statistical_summary_radial_gauge",
                "name": f"{display_name} - Statistics",
                "description": f"Statistical summary of {display_name} (mean, min, max)",
                "plugin": "statistical_summary",
                "category": "gauge",
                "icon": icons["gauge"],
                "confidence": base_confidence,
                "source": "reference",
                "source_name": reference_name,
                "matched_column": col_name,
                "match_reason": "Numeric continuous field suitable for statistical summary",
                "is_recommended": True,
                "config": {
                    "transformer": {
                        "plugin": "statistical_summary",
                        "params": {
                            "source": reference_name,
                            "field": col_name,
                            "stats": ["max", "mean", "min"],
                        },
                    },
                    "widget": {
                        "plugin": "radial_gauge",
                        "params": {
                            "stat_to_display": "mean",
                            "show_range": True,
                            "auto_range": True,
                        },
                    },
                },
                "alternatives": [f"{col_name}_binned_distribution_bar_plot"],
            }
        )

        # Binned distribution (bar plot)
        suggestions.append(
            {
                "template_id": f"{col_name}_binned_distribution_bar_plot",
                "name": f"{display_name} - Distribution",
                "description": f"Distribution of {display_name} values",
                "plugin": "binned_distribution",
                "category": "chart",
                "icon": icons["chart"],
                "confidence": base_confidence - 0.05,
                "source": "reference",
                "source_name": reference_name,
                "matched_column": col_name,
                "match_reason": "Numeric field suitable for histogram",
                "is_recommended": False,
                "config": {
                    "transformer": {
                        "plugin": "binned_distribution",
                        "params": {
                            "source": reference_name,
                            "field": col_name,
                            "bins": "auto",
                            "include_percentages": True,
                        },
                    },
                    "widget": {
                        "plugin": "bar_plot",
                        "params": {
                            "orientation": "v",
                            "x_axis": "labels",
                            "y_axis": "counts",
                            "gradient_color": "#10b981",
                            "gradient_mode": "luminance",
                            "show_legend": False,
                        },
                    },
                },
                "alternatives": [f"{col_name}_statistical_summary_radial_gauge"],
            }
        )

    elif category == "numeric_discrete":
        # For discrete numeric with few values, treat as categorical
        suggestions.append(
            {
                "template_id": f"{col_name}_categorical_distribution_bar_plot",
                "name": f"{display_name} - Distribution",
                "description": f"Distribution of {display_name} categories",
                "plugin": "categorical_distribution",
                "category": "chart",
                "icon": icons["chart"],
                "confidence": base_confidence,
                "source": "reference",
                "source_name": reference_name,
                "matched_column": col_name,
                "match_reason": f"Discrete numeric field with {unique_count} unique values",
                "is_recommended": True,
                "config": {
                    "transformer": {
                        "plugin": "categorical_distribution",
                        "params": {
                            "source": reference_name,
                            "field": col_name,
                            "include_percentages": True,
                        },
                    },
                    "widget": {
                        "plugin": "bar_plot",
                        "params": {
                            "orientation": "v",
                            "x_axis": "labels",
                            "y_axis": "counts",
                            "gradient_color": "#10b981",
                            "gradient_mode": "luminance",
                            "show_legend": False,
                        },
                    },
                },
                "alternatives": [],
            }
        )

    elif category == "categorical":
        # Categorical distribution
        suggestions.append(
            {
                "template_id": f"{col_name}_categorical_distribution_bar_plot",
                "name": f"{display_name} - Distribution",
                "description": f"Distribution of {display_name} categories",
                "plugin": "categorical_distribution",
                "category": "chart",
                "icon": icons["chart"],
                "confidence": base_confidence,
                "source": "reference",
                "source_name": reference_name,
                "matched_column": col_name,
                "match_reason": f"Categorical field with {unique_count} categories",
                "is_recommended": True,
                "config": {
                    "transformer": {
                        "plugin": "categorical_distribution",
                        "params": {
                            "source": reference_name,
                            "field": col_name,
                            "categories": sample_values[:10] if sample_values else None,
                            "include_percentages": True,
                        },
                    },
                    "widget": {
                        "plugin": "bar_plot",
                        "params": {
                            "orientation": "h" if unique_count > 5 else "v",
                            "x_axis": "counts" if unique_count > 5 else "labels",
                            "y_axis": "labels" if unique_count > 5 else "counts",
                            "auto_color": True,
                        },
                    },
                },
                "alternatives": [f"{col_name}_categorical_distribution_donut_chart"]
                if unique_count <= 6
                else [],
            }
        )

        # Donut chart alternative for small cardinality
        if unique_count <= 6:
            suggestions.append(
                {
                    "template_id": f"{col_name}_categorical_distribution_donut_chart",
                    "name": f"{display_name} - Donut",
                    "description": f"Proportions of {display_name}",
                    "plugin": "categorical_distribution",
                    "category": "donut",
                    "icon": icons["donut"],
                    "confidence": base_confidence - 0.05,
                    "source": "reference",
                    "source_name": reference_name,
                    "matched_column": col_name,
                    "match_reason": f"Low cardinality ({unique_count}) suitable for donut chart",
                    "is_recommended": False,
                    "config": {
                        "transformer": {
                            "plugin": "categorical_distribution",
                            "params": {
                                "source": reference_name,
                                "field": col_name,
                                "include_percentages": True,
                            },
                        },
                        "widget": {
                            "plugin": "donut_chart",
                            "params": {
                                "labels_field": "labels",
                                "values_field": "counts",
                            },
                        },
                    },
                    "alternatives": [f"{col_name}_categorical_distribution_bar_plot"],
                }
            )

    elif category == "categorical_high_card":
        # Top ranking for high cardinality
        suggestions.append(
            {
                "template_id": f"{col_name}_top_ranking_bar_plot",
                "name": f"Top 10 - {display_name}",
                "description": f"Top 10 most frequent {display_name}",
                "plugin": "top_ranking",
                "category": "chart",
                "icon": icons["chart"],
                "confidence": base_confidence,
                "source": "reference",
                "source_name": reference_name,
                "matched_column": col_name,
                "match_reason": f"High cardinality ({unique_count}) - showing top 10",
                "is_recommended": True,
                "config": {
                    "transformer": {
                        "plugin": "top_ranking",
                        "params": {
                            "source": reference_name,
                            "field": col_name,
                            "count": 10,
                            "mode": "direct",
                        },
                    },
                    "widget": {
                        "plugin": "bar_plot",
                        "params": {
                            "orientation": "h",
                            "x_axis": "counts",
                            "y_axis": "tops",
                            "sort_order": "ascending",
                            "auto_color": True,
                        },
                    },
                },
                "alternatives": [],
            }
        )

    elif category == "boolean":
        # Binary counter (donut)
        true_label = "Yes"
        false_label = "No"

        # Try to infer labels from column name
        if "in_" in col_name.lower() or col_name.lower().startswith("is_"):
            name_part = col_name.replace("in_", "").replace("is_", "").upper()
            true_label = name_part
            false_label = f"Non-{name_part}"

        suggestions.append(
            {
                "template_id": f"{col_name}_binary_counter_donut_chart",
                "name": f"{display_name}",
                "description": f"Distribution of {display_name}",
                "plugin": "binary_counter",
                "category": "donut",
                "icon": icons["donut"],
                "confidence": base_confidence,
                "source": "reference",
                "source_name": reference_name,
                "matched_column": col_name,
                "match_reason": "Boolean field suitable for binary distribution",
                "is_recommended": True,
                "config": {
                    "transformer": {
                        "plugin": "binary_counter",
                        "params": {
                            "source": reference_name,
                            "field": col_name,
                            "true_label": true_label,
                            "false_label": false_label,
                            "include_percentages": True,
                        },
                    },
                    "widget": {
                        "plugin": "donut_chart",
                        "params": {
                            "labels_field": "labels",
                            "values_field": "counts",
                        },
                    },
                },
                "alternatives": [],
            }
        )

    return suggestions
