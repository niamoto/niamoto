"""
Entity finder utilities for templates API.

Functions to find representative entities and specific entities by ID
for widget preview rendering.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml
from fastapi import HTTPException
from sqlalchemy import text

from niamoto.common.database import Database
from niamoto.common.table_resolver import (
    quote_identifier,
    resolve_dataset_table,
    resolve_reference_table,
)
from niamoto.gui.api.context import get_working_directory

logger = logging.getLogger(__name__)


def _quote_identifier(db: Database, name: str) -> str:
    """Compat helper used by legacy call sites in this module."""
    return quote_identifier(db, name)


def _resolve_reference_table(db: Database, reference_name: str) -> Optional[str]:
    """Resolve a reference table from its logical name."""
    return resolve_reference_table(db, reference_name)


def _resolve_source_dataset_table(
    db: Database, source_dataset: Optional[str]
) -> Optional[str]:
    """Resolve source dataset table from logical dataset name."""
    return resolve_dataset_table(db, source_dataset)


def _detect_geometry_column(columns: List[str]) -> Optional[str]:
    """Detect a likely geometry column name."""
    lowered = [c.lower() for c in columns]
    preferred = [
        "wkb_geometry",
        "geometry",
        "the_geom",
        "geom",
        "geo_pt",
        "location",
        "wkt",
    ]
    for candidate in preferred:
        if candidate in lowered:
            return columns[lowered.index(candidate)]
    return None


def find_representative_entity(
    db: Database, hierarchy_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Find a representative entity for preview.

    Works with:
    - Hierarchical references (taxons): picks from first level (e.g., 'family')
    - Flat references (plots/shapes): uses relation key to filter occurrences

    Strategy: Pick an entity that has enough data to display meaningful results.
    """
    reference_name = hierarchy_info.get("reference_name") or "reference"
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

        # Resolve source dataset table
        table_name = _resolve_source_dataset_table(db, source_dataset)

        if not table_name:
            raise HTTPException(
                status_code=404,
                detail=f"Source dataset '{source_dataset}' not found",
            )

        # If we have a relation key, find an entity with occurrences
        if relation_key:
            try:
                # Find entity_id with most occurrences
                quoted_relation_key = _quote_identifier(db, relation_key)
                quoted_table_name = _quote_identifier(db, table_name)
                query = text(f"""
                    SELECT {quoted_relation_key}, COUNT(*) as cnt
                    FROM {quoted_table_name}
                    WHERE {quoted_relation_key} IS NOT NULL
                    GROUP BY {quoted_relation_key}
                    ORDER BY cnt DESC
                    LIMIT 1
                """)
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

        # Fallback: return first entity from reference table
        entity_table = _resolve_reference_table(db, reference_name)
        if entity_table and db.has_table(entity_table):
            quoted_entity_table = _quote_identifier(db, entity_table)
            columns_df = pd.read_sql(
                text(f"SELECT * FROM {quoted_entity_table} LIMIT 0"), db.engine
            )
            columns = columns_df.columns.tolist()

            name_candidates = ["full_name", "name", "label", "title"]
            name_field = next((c for c in name_candidates if c in columns), id_field)

            query = text(f"SELECT * FROM {quoted_entity_table} LIMIT 1")
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

                if kind == "spatial":
                    geo_col = _detect_geometry_column(columns)
                    if geo_col:
                        geo_value = entity.get(geo_col)
                        if geo_value:
                            result_dict["geometry"] = str(geo_value)
                            result_dict["spatial_query"] = True
                            result_dict["kind"] = "spatial"

                    for type_candidate in ("shape_type", "type", "entity_type"):
                        if type_candidate in columns:
                            result_dict["shape_type"] = entity.get(type_candidate)
                            break

                return result_dict

        raise HTTPException(
            status_code=404,
            detail=f"No representative entity found for '{reference_name}'",
        )

    # For hierarchical references with levels, prefer the first level (e.g., family)
    # which gives a rich entity. The relation_key (e.g., id_taxonref) returns
    # individual species (leaves), not families.
    table_name = _resolve_source_dataset_table(db, source_dataset)

    if not table_name:
        raise HTTPException(
            status_code=404,
            detail=f"Source dataset '{source_dataset}' not found",
        )

    # Strategy 1: Use first hierarchy level (family → Myrtaceae)
    if levels:
        first_level = levels[0]
        column_name = level_columns.get(first_level, first_level)
        try:
            quoted_column_name = _quote_identifier(db, column_name)
            quoted_table_name = _quote_identifier(db, table_name)
            query = text(f"""
                SELECT {quoted_column_name}, COUNT(*) as cnt
                FROM {quoted_table_name}
                WHERE {quoted_column_name} IS NOT NULL AND {quoted_column_name} != ''
                GROUP BY {quoted_column_name}
                ORDER BY cnt DESC
                LIMIT 1
            """)
            result = pd.read_sql(query, db.engine)

            if not result.empty:
                return {
                    "level": first_level,
                    "column": column_name,
                    "value": result.iloc[0][column_name],
                    "count": int(result.iloc[0]["cnt"]),
                    "table_name": table_name,
                }
        except Exception as e:
            logger.warning(
                f"Error finding representative entity via first level '{first_level}': {e}"
            )

    # Strategy 2 (fallback): Use relation_key for hierarchical refs without levels
    relation = hierarchy_info.get("relation", {})
    relation_key = relation.get("key")
    if relation_key:
        try:
            quoted_relation_key = _quote_identifier(db, relation_key)
            quoted_table_name = _quote_identifier(db, table_name)
            query = text(f"""
                SELECT {quoted_relation_key}, COUNT(*) as cnt
                FROM {quoted_table_name}
                WHERE {quoted_relation_key} IS NOT NULL
                GROUP BY {quoted_relation_key}
                ORDER BY cnt DESC
                LIMIT 1
            """)
            result = pd.read_sql(query, db.engine)
            if not result.empty:
                return {
                    "level": reference_name,
                    "column": relation_key,
                    "value": result.iloc[0][relation_key],
                    "count": int(result.iloc[0]["cnt"]),
                    "table_name": table_name,
                }
        except Exception as e:
            logger.warning(f"Error finding representative entity via relation key: {e}")

    raise HTTPException(
        status_code=400,
        detail=f"No data found for hierarchical reference '{reference_name}'",
    )


def find_entity_by_id(
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
    reference_name = hierarchy_info.get("reference_name") or "reference"

    # Resolve source dataset table.
    table_name = _resolve_source_dataset_table(db, source_dataset)

    if not table_name:
        raise HTTPException(
            status_code=404,
            detail=f"Source dataset '{source_dataset}' not found",
        )

    # Resolve reference table and fallback to representative entity if unavailable.
    entity_table = _resolve_reference_table(db, reference_name)
    if not entity_table or not db.has_table(entity_table):
        return find_representative_entity(db, hierarchy_info)

    # Read import.yml for reference configuration
    work_dir = get_working_directory()
    ref_config = {}
    if work_dir:
        import_path = Path(work_dir) / "config" / "import.yml"
        if import_path.exists():
            try:
                with open(import_path, "r", encoding="utf-8") as f:
                    import_config = yaml.safe_load(f) or {}
                references = (
                    import_config.get("entities", {}).get("references", {}) or {}
                )
                ref_config = references.get(reference_name, {})
            except Exception:
                pass

    # Get schema info
    schema = ref_config.get("schema", {})
    id_field = schema.get("id_field")
    kind = ref_config.get("kind")  # hierarchical, spatial, or None

    # Get entity columns
    quoted_entity_table = _quote_identifier(db, entity_table)
    columns_df = pd.read_sql(
        text(f"SELECT * FROM {quoted_entity_table} LIMIT 0"), db.engine
    )
    columns = [c.lower() for c in columns_df.columns.tolist()]

    # If id_field not in schema, detect it from columns
    if not id_field or id_field.lower() not in columns:
        # Handle both plural (plots) and singular (plot) forms
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
        id_field = next((c for c in id_candidates if c in columns), "id")

    # Determine name field
    name_candidates = ["full_name", "name", "label", "title"]
    name_field = next((c for c in name_candidates if c in columns), id_field)

    try:
        # Use relation key (if available) to count matching rows in source dataset.
        relation = hierarchy_info.get("relation", {})
        relation_key = relation.get("key")

        # If no relation info, try to read from transform.yml
        if not relation_key and work_dir:
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

        quoted_id_field = _quote_identifier(db, id_field)
        entity_query = text(f"""
            SELECT *
            FROM {quoted_entity_table}
            WHERE {quoted_id_field} = :entity_id
        """)
        entity_result = pd.read_sql(
            entity_query, db.engine, params={"entity_id": str(entity_id)}
        )

        if entity_result.empty:
            raise HTTPException(
                status_code=404, detail=f"Entity '{entity_id}' not found"
            )

        entity = entity_result.iloc[0]
        entity_name = str(entity.get(name_field, entity_id))

        # Pour les hiérarchiques avec levels, utiliser la colonne de niveau
        # au lieu de relation_key (qui ne fonctionne que pour les feuilles)
        levels = hierarchy_info.get("levels", [])
        level_columns = hierarchy_info.get("level_columns", {})
        if levels and kind == "hierarchical":
            entity_rank = entity.get("rank_name")
            entity_rank_value = entity.get("rank_value")

            if entity_rank and entity_rank in levels and entity_rank_value:
                occ_column = level_columns.get(entity_rank, entity_rank)

                try:
                    quoted_occ_col = _quote_identifier(db, occ_column)
                    quoted_table = _quote_identifier(db, table_name)
                    count_result = pd.read_sql(
                        text(
                            f"SELECT COUNT(*) as cnt FROM {quoted_table} "
                            f"WHERE {quoted_occ_col} = :val"
                        ),
                        db.engine,
                        params={"val": str(entity_rank_value)},
                    )
                    count = (
                        int(count_result.iloc[0]["cnt"])
                        if not count_result.empty
                        else 0
                    )

                    if count > 0:
                        return {
                            "level": entity_rank,
                            "column": occ_column,
                            "value": entity_rank_value,
                            "count": count,
                            "table_name": table_name,
                            "entity_name": entity_name,
                        }
                except Exception as e:
                    logger.warning(f"Level column query failed for {entity_rank}: {e}")
                    # Fall through to relation_key

        if relation_key:
            ref_field = relation.get("ref_field") or relation.get("ref_key")
            if not ref_field or ref_field not in entity.index:
                derived_ref_field = f"{reference_name}_id"
                if derived_ref_field in entity.index:
                    ref_field = derived_ref_field
                else:
                    ref_field = id_field

            match_value = entity.get(ref_field, entity_id)

            try:
                quoted_relation_key = _quote_identifier(db, relation_key)
                quoted_table_name = _quote_identifier(db, table_name)
                count_result = pd.read_sql(
                    text(
                        f"""SELECT COUNT(*) as cnt
                        FROM {quoted_table_name}
                        WHERE {quoted_relation_key} = :match_value"""
                    ),
                    db.engine,
                    params={"match_value": str(match_value)},
                )
                count = (
                    int(count_result.iloc[0]["cnt"]) if not count_result.empty else 0
                )
            except Exception:
                count = 0

            return {
                "level": reference_name,
                "column": relation_key,
                "value": match_value,
                "count": count,
                "table_name": table_name,
                "entity_name": entity_name,
            }

        # Fallback: use entity table directly (e.g., spatial entities without links)
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
            geo_col = _detect_geometry_column(entity.index.tolist())
            if geo_col:
                geo_value = entity.get(geo_col)
                if geo_value:
                    result["geometry"] = str(geo_value)
                    result["spatial_query"] = True
                    result["kind"] = "spatial"

            for type_candidate in ("shape_type", "type", "entity_type"):
                if type_candidate in entity.index:
                    result["shape_type"] = entity.get(type_candidate)
                    break

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error finding entity by ID '{entity_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
