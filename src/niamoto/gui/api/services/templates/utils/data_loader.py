"""
Data loader utilities for templates API.

Functions to load sample data for widget preview rendering.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml
from fastapi import HTTPException

from niamoto.common.database import Database

logger = logging.getLogger(__name__)


def load_sample_data(
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


def load_class_object_data_for_preview(
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
                    # Auto-detect delimiter (comma or semicolon)
                    with open(csv_path, "r", encoding="utf-8") as f:
                        first_line = f.readline()
                        delimiter = (
                            ";"
                            if first_line.count(";") > first_line.count(",")
                            else ","
                        )

                    df = pd.read_csv(csv_path, delimiter=delimiter)

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
                        "tops": labels,
                        "counts": values,
                        "source": source.get("name", Path(data_path).stem),
                        "group_by": group_config.get("group_by", "unknown"),
                        "class_object": class_object_name,
                    }

                except Exception as e:
                    logger.warning(f"Error loading CSV {csv_path}: {e}")
                    continue

        return None

    except Exception as e:
        logger.warning(f"Error loading class_object data: {e}")
        return None
