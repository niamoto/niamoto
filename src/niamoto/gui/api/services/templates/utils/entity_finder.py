"""
Entity finder utilities for templates API.

Functions to find representative entities and specific entities by ID
for widget preview rendering.
"""

import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import yaml
from fastapi import HTTPException

from niamoto.common.database import Database
from niamoto.gui.api.context import get_working_directory

logger = logging.getLogger(__name__)


def find_representative_entity(
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
                references = import_config.get("entities", {}).get("references", {})
                ref_config = references.get(reference_name, {})
            except Exception:
                pass

    # Get schema info
    schema = ref_config.get("schema", {})
    id_field = schema.get("id_field")
    kind = ref_config.get("kind")  # hierarchical, spatial, or None

    # Get entity columns
    columns_df = pd.read_sql(f"SELECT * FROM {entity_table} LIMIT 0", db.engine)
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
    name_candidates = ["full_name", "name", "plot", "label", "title"]
    name_field = next((c for c in name_candidates if c in columns), id_field)

    try:
        if kind == "hierarchical":
            # Hierarchical reference (taxons): use rank-based filtering
            entity_query = f"""
                SELECT "{id_field}" as id, rank_name, rank_value, full_name, taxons_id
                FROM {entity_table}
                WHERE "{id_field}" = {entity_id}
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
