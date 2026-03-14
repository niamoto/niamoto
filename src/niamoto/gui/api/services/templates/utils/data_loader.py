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
from sqlalchemy import text

from niamoto.common.database import Database
from niamoto.common.table_resolver import quote_identifier, resolve_dataset_table

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
        occurrences_table = resolve_dataset_table(db, "occurrences")

        # Check if occurrences table exists
        if not occurrences_table:
            # No occurrences table, return entity data if available
            entity_data = representative.get("entity_data")
            if entity_data:
                return pd.DataFrame([entity_data])
            return pd.DataFrame()

        # Find the geometry column in occurrences (usually geo_pt)
        quoted_occurrences_table = quote_identifier(db, occurrences_table)
        cols_df = pd.read_sql(
            text(f"SELECT * FROM {quoted_occurrences_table} LIMIT 0"), db.engine
        )
        geo_candidates = ["geo_pt", "geometry", "geom", "location", "point"]
        geo_col = next((c for c in geo_candidates if c in cols_df.columns), None)

        if not geo_col:
            # No geometry column in occurrences, can't do spatial query
            logger.warning(f"No geometry column found in {occurrences_table}")
            return pd.DataFrame()

        # Build the SELECT clause
        if required_field != "*":
            select_clause = quote_identifier(db, required_field)
        else:
            select_clause = "*"

        # Build spatial query with ST_Contains (shape polygon contains occurrence point)
        quoted_geo_col = quote_identifier(db, geo_col)

        try:
            # Use raw connection to execute multi-statement query
            with db.engine.connect() as conn:
                # Load spatial extension first (using text() for raw SQL)
                conn.execute(text("INSTALL spatial"))
                conn.execute(text("LOAD spatial"))

                # Then run the actual query
                select_query = (
                    f"SELECT {select_clause} "
                    f"FROM {quoted_occurrences_table} "
                    f"WHERE ST_Contains("
                    f"ST_GeomFromText(:geom_wkt), "
                    f"TRY_CAST({quoted_geo_col} AS GEOMETRY)"
                    f")"
                )
                # Always cap spatial queries for previews — full-table
                # ST_Contains scans are expensive and large shapes can
                # return thousands of rows.
                effective_limit = limit or 500
                safe_limit = max(1, int(effective_limit))
                select_query += f" LIMIT {safe_limit}"
                return pd.read_sql(
                    text(select_query), conn, params={"geom_wkt": geometry}
                )
        except Exception as e:
            logger.warning(f"Spatial query failed: {e}, trying simpler approach")
            # If spatial query fails, return empty (shape without occurrences)
            return pd.DataFrame()

    # Standard flow for occurrence-based data (hierarchical and flat references)
    table_name = representative["table_name"]
    column = representative["column"]
    value = representative["value"]
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if not db.has_table(table_name):
        raise HTTPException(status_code=400, detail=f"Unknown table: {table_name}")

    quoted_table_name = quote_identifier(db, table_name)
    quoted_column = quote_identifier(db, column)

    # Build query - with optional random sampling
    params: Dict[str, Any] = {"match_value": value}
    if required_field != "*":
        quoted_required_field = quote_identifier(db, required_field)
        # Avoid selecting the same column twice
        if required_field == column:
            query = text(
                f"SELECT {quoted_required_field} "
                f"FROM {quoted_table_name} "
                f"WHERE {quoted_column} = :match_value"
            )
        else:
            query = text(
                f"SELECT {quoted_required_field}, {quoted_column} "
                f"FROM {quoted_table_name} "
                f"WHERE {quoted_column} = :match_value"
            )
    else:
        query = text(
            f"SELECT * FROM {quoted_table_name} WHERE {quoted_column} = :match_value"
        )

    # Add random sampling if limit is specified
    if limit:
        safe_limit = max(1, int(limit))
        query = text(f"{query.text} ORDER BY RANDOM() LIMIT {safe_limit}")

    try:
        return pd.read_sql(query, db.engine, params=params)
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

                    normalized = co_data.copy()
                    normalized["class_value"] = pd.to_numeric(
                        normalized["class_value"], errors="coerce"
                    )
                    normalized = normalized.dropna(subset=["class_value"])
                    if normalized.empty:
                        continue

                    # Scalars often come with empty class_name.
                    # Handle them explicitly to avoid empty outputs that lead
                    # to blank gauge previews.
                    class_names = (
                        normalized["class_name"].fillna("").astype(str).str.strip()
                    )
                    has_named_classes = (class_names != "").any()

                    if not has_named_classes:
                        # Use a representative scalar value for preview.
                        # Median avoids extreme values when multiple entities exist.
                        scalar_value = float(normalized["class_value"].median())
                        labels = ["value"]
                        values = [scalar_value]
                    else:
                        normalized["class_name"] = class_names
                        named_data = normalized[normalized["class_name"] != ""]
                        if named_data.empty:
                            continue

                        # For distribution-like class_objects, aggregate classes.
                        aggregated = (
                            named_data.groupby("class_name", sort=False)["class_value"]
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
