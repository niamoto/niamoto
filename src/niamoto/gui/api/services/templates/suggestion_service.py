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

from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.core.imports.widget_generator import WidgetGenerator
from niamoto.core.imports.class_object_suggester import suggest_widgets_for_source

logger = logging.getLogger(__name__)


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

            # Get column info to exclude geometry columns (binary WKB causes encoding errors)
            from sqlalchemy import text

            with db.engine.connect() as conn:
                result = conn.execute(text(f"DESCRIBE {ref_table}"))
                col_info = result.fetchall()
            safe_columns = [
                f'"{c[0]}"'
                for c in col_info
                if c[1].upper() not in ("GEOMETRY", "BLOB", "BYTEA")
                and not c[0].endswith("_geom")
            ]
            if not safe_columns:
                return None

            # Get sample data to analyze columns (excluding geometry)
            columns_sql = ", ".join(safe_columns)
            sample_df = pd.read_sql(
                f"SELECT {columns_sql} FROM {ref_table} LIMIT 100", db.engine
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
