"""HierarchyBuilder: Extract and build hierarchical references from source datasets.

This module provides DuckDB-native hierarchy extraction using CTEs for optimal
performance. It supports taxonomy, spatial hierarchies, and any nested structure
defined through configuration.
"""

from __future__ import annotations

import hashlib
from typing import List

import pandas as pd

from niamoto.common.database import Database
from niamoto.common.exceptions import DataValidationError
from niamoto.core.imports.config_models import HierarchyLevel, ExtractionConfig


class HierarchyBuilder:
    """Extract and build hierarchical reference from source dataset using DuckDB CTEs."""

    def __init__(self, db: Database):
        """Initialize HierarchyBuilder.

        Args:
            db: Database instance (must be DuckDB)

        Raises:
            ValueError: If database is not DuckDB
        """
        self.db = db
        if not db.is_duckdb:
            raise ValueError("HierarchyBuilder requires DuckDB backend")

    def build_from_dataset(
        self,
        source_table: str,
        extraction_config: ExtractionConfig,
        entity_name: str,
    ) -> pd.DataFrame:
        """Extract unique hierarchical data from source table using DuckDB SQL.

        Strategy:
        1. Extract unique level combinations via DISTINCT + GROUP BY (DuckDB native)
        2. Generate stable IDs (hash or sequence)
        3. Build parent-child via self-joins on level prefixes
        4. Return structured DataFrame ready for insertion

        Args:
            source_table: Name of source table
            extraction_config: Extraction configuration
            entity_name: Name of the entity (used to generate external ID column name)

        Returns:
            DataFrame with columns:
            - id (hash-based stable ID)
            - {entity_name}_id (external ID if provided, e.g., taxonomy_id, plots_id)
            - rank_name (family/genus/species/infra)
            - rank_value (actual value)
            - full_path (hierarchical path)
            - parent_id (FK to parent rank)
            - level (0=family, 1=genus, etc.)
            - [additional columns]

        Raises:
            DataValidationError: If hierarchy integrity is violated
        """
        levels = extraction_config.levels

        # 1. Build SQL for extracting unique combinations (DuckDB CTEs)
        extract_sql = self._build_extraction_cte(
            source_table, extraction_config, entity_name
        )

        # 2. Execute and get deduplicated hierarchy
        hierarchy_df = pd.read_sql(extract_sql, self.db.engine)

        if len(hierarchy_df) == 0:
            # Return empty DataFrame with expected structure
            return pd.DataFrame(
                columns=[
                    "id",
                    "parent_id",
                    "level",
                    "rank_name",
                    "rank_value",
                    "full_path",
                ]
            )

        # 3. Build parent relationships
        hierarchy_df = self._build_parent_relationships(hierarchy_df, levels)

        # 4. Clean up external IDs (taxon_id) to keep only on deepest nodes
        if extraction_config.id_column:
            hierarchy_df = self._clean_external_ids(hierarchy_df)

        # 5. Validate hierarchy integrity
        self._validate_hierarchy_integrity(hierarchy_df, levels)

        # 6. Generate stable IDs
        hierarchy_df = self._assign_stable_ids(
            hierarchy_df, extraction_config.id_strategy
        )

        return hierarchy_df

    def _build_extraction_cte(
        self, source_table: str, config: ExtractionConfig, entity_name: str
    ) -> str:
        """Build DuckDB CTE for extracting unique hierarchical combinations.

        Args:
            source_table: Source table name
            config: Extraction configuration
            entity_name: Name of the entity (for generating external ID column name)

        Returns:
            SQL query string
        """
        levels = config.levels

        # Build column selections
        level_cols = []
        for level in levels:
            if config.incomplete_rows == "fill_unknown":
                level_cols.append(f"""
                    COALESCE(NULLIF(TRIM("{level.column}"), ''), 'Unknown {level.name}') as "{level.column}"
                """)
            else:
                level_cols.append(f'"{level.column}"')

        level_cols_str = ", ".join(level_cols)
        id_col = f', "{config.id_column}"' if config.id_column else ""
        name_col = f', "{config.name_column}"' if config.name_column else ""
        additional = (
            ", ".join([f'"{col}"' for col in config.additional_columns])
            if config.additional_columns
            else ""
        )

        # Handle incomplete rows
        where_clause = ""
        if config.incomplete_rows == "error":
            # DuckDB will fail on NULL constraint - require ALL levels
            null_checks = " AND ".join([f'"{lv.column}" IS NOT NULL' for lv in levels])
            where_clause = f"WHERE {null_checks}"
        # Note: "skip" is handled per-level in UNION clauses below

        # Build UNION ALL clauses dynamically for each level
        # Note: we only select level-specific columns to avoid duplication
        union_clauses = []
        deepest_level_idx = len(levels) - 1
        for idx, level in enumerate(levels):
            # Build path: concatenate all levels up to current one
            path_parts = [f'"{levels[i].column}"' for i in range(idx + 1)]
            path_expr = " || '|' || ".join(path_parts)

            # Build null check for this level AND all parent levels
            # This ensures we only extract valid hierarchies (no "species without genus")
            null_checks_for_level = []
            for i in range(idx + 1):  # Include all levels up to current
                if config.incomplete_rows == "skip":
                    null_checks_for_level.append(
                        f'"{levels[i].column}" IS NOT NULL AND TRIM("{levels[i].column}") != \'\''
                    )
                elif config.incomplete_rows == "fill_unknown":
                    # With fill_unknown, we use COALESCE so no need for NULL checks
                    pass

            null_check = (
                " AND ".join(null_checks_for_level) if null_checks_for_level else "1=1"
            )

            # For each level, we need hierarchy path + external ID if at deepest level
            # External ID (id_column) is kept only for the deepest non-NULL level
            # This allows joining occurrences to the correct taxonomic level

            # Include external ID and name columns, using MIN to deduplicate
            # Generate external ID column name from entity name: {entity_name}_id
            external_id_expr = ""
            external_name_expr = ""

            if config.id_column:
                external_id_col_name = f"{entity_name}_id"
                external_id_expr = (
                    f', MIN("{config.id_column}") as {external_id_col_name}'
                )
            if config.name_column:
                if idx == deepest_level_idx:
                    external_name_expr = f', MIN("{config.name_column}") as full_name'
                else:
                    level_col = level.column or level.name
                    external_name_expr = f', MIN("{level_col}") as full_name'

            select_clause = f"""
            SELECT
                {idx} as level,
                '{level.name}' as rank_name,
                "{level.column}" as rank_value,
                {path_expr} as full_path
                {external_id_expr}
                {external_name_expr}
            FROM unique_taxa
            WHERE {null_check}
            GROUP BY {path_expr}, "{level.column}"
            """
            union_clauses.append(select_clause)

        # Combine all UNION clauses
        union_all = "\n            UNION ALL\n            ".join(union_clauses)

        # Generate external ID column name
        external_id_col_name = f"{entity_name}_id" if config.id_column else None

        sql = f"""
        WITH unique_taxa AS (
            SELECT DISTINCT
                {level_cols_str}
                {id_col}
                {name_col}
                {", " + additional if additional else ""}
            FROM {source_table}
            {where_clause}
        ),
        exploded_levels AS (
            {union_all}
        )
        SELECT DISTINCT
            level,
            rank_name,
            rank_value,
            full_path
            {", " + external_id_col_name if external_id_col_name else ""}
            {", full_name" if config.name_column else ""}
        FROM exploded_levels
        ORDER BY level, full_path
        """

        return sql

    def _clean_external_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean external IDs to keep only on deepest nodes.

        For each unique external ID (e.g., taxonomy_id, plots_id), find the deepest level
        where it appears and set it to NULL on all shallower levels. This prevents parent
        nodes from incorrectly inheriting external IDs from their children.

        Example:
            Before:
                family Anacardiaceae, taxonomy_id=1953, level=0
                genus Euroschinus, taxonomy_id=1953, level=1
                species elegans, taxonomy_id=1953, level=2
            After:
                family Anacardiaceae, taxonomy_id=NULL, level=0
                genus Euroschinus, taxonomy_id=NULL, level=1
                species elegans, taxonomy_id=1953, level=2

        Args:
            df: DataFrame with external ID column (e.g., taxonomy_id, plots_id)

        Returns:
            DataFrame with cleaned external ID values
        """
        # Find the external ID column (ends with _id, but not 'id' or 'parent_id')
        external_id_col = None
        for col in df.columns:
            if col.endswith("_id") and col not in ["id", "parent_id"]:
                external_id_col = col
                break

        if not external_id_col:
            return df

        # For each external ID value, find the maximum level where it appears
        external_max_level = (
            df[df[external_id_col].notna()].groupby(external_id_col)["level"].max()
        )

        # Create a mapping: (external_id, level) -> keep or remove
        def should_keep_external_id(row):
            if pd.isna(row[external_id_col]):
                return None
            max_level = external_max_level.get(row[external_id_col])
            # Only keep external_id on the deepest level for this ID
            return row[external_id_col] if row["level"] == max_level else None

        df[external_id_col] = df.apply(should_keep_external_id, axis=1)

        return df

    def _build_parent_relationships(
        self, df: pd.DataFrame, levels: List[HierarchyLevel]
    ) -> pd.DataFrame:
        """Build parent_id by matching parent path.

        Args:
            df: DataFrame with full_path column
            levels: Hierarchy levels

        Returns:
            DataFrame with parent_id column added
        """
        # Create parent path (all but last level)
        df["parent_path"] = df["full_path"].apply(
            lambda p: "|".join(p.split("|")[:-1]) if "|" in p else None
        )

        # First pass: assign temporary IDs
        df["temp_id"] = range(len(df))
        path_to_id = dict(zip(df["full_path"], df["temp_id"]))

        # Second pass: resolve parent_id
        df["parent_id"] = df["parent_path"].apply(
            lambda p: path_to_id.get(p) if p else None
        )

        return df

    def _validate_hierarchy_integrity(
        self, df: pd.DataFrame, levels: List[HierarchyLevel]
    ) -> None:
        """Validate hierarchy integrity rules.

        Rules:
        1. Levels must be strictly ordered (no gaps: can't have species without genus)
        2. Each level must be complete if a lower level exists

        Args:
            df: DataFrame to validate
            levels: Hierarchy levels

        Raises:
            DataValidationError: If hierarchy rules are violated
        """
        # Check for hierarchy gaps (e.g., species present but genus missing)
        for idx in range(len(levels) - 1):
            current_level = levels[idx]
            next_level = levels[idx + 1]

            # Find rows where current level is empty but next level is filled
            # This is detected by checking if the path contains the expected parent
            gaps = df[
                (df["level"] == idx + 1)
                & (df["rank_value"].notna())
                & (
                    df["rank_value"] != f"Unknown {next_level.name}"
                )  # Ignore fill_unknown cases
            ]

            # For each row at next level, check if parent level exists in path
            for _, row in gaps.iterrows():
                path_parts = row["full_path"].split("|")
                expected_length = idx + 2  # idx+1 parent parts + 1 current

                if len(path_parts) != expected_length:
                    # Path length mismatch - invalid hierarchy
                    raise DataValidationError(
                        message=f"Invalid hierarchy path at level {idx + 1}",
                        validation_errors=[
                            {
                                "level": idx + 1,
                                "full_path": row["full_path"],
                                "expected_length": expected_length,
                                "actual_length": len(path_parts),
                            }
                        ],
                    )

                # Check if any parent part is "Unknown"
                has_unknown_parent = any("Unknown" in part for part in path_parts[:-1])
                if has_unknown_parent:
                    # fill_unknown strategy is legitimate
                    continue

                # Check if parent exists in DataFrame
                parent_path = "|".join(path_parts[:-1])
                parent_exists = (df["full_path"] == parent_path).any()

                if not parent_exists:
                    # Parent is missing - this is a real gap
                    raise DataValidationError(
                        message=f"Hierarchy gap detected: {next_level.name} '{row['rank_value']}' "
                        f"exists without valid {current_level.name} parent",
                        validation_errors=[
                            {
                                "level": idx + 1,
                                "rank_name": next_level.name,
                                "rank_value": row["rank_value"],
                                "full_path": row["full_path"],
                                "parent_path": parent_path,
                                "missing_parent": current_level.name,
                            }
                        ],
                    )

    def _assign_stable_ids(self, df: pd.DataFrame, strategy: str) -> pd.DataFrame:
        """Generate deterministic IDs.

        Args:
            df: DataFrame with temp_id and parent_id
            strategy: ID generation strategy ('hash', 'sequence', 'external')

        Returns:
            DataFrame with stable IDs

        Raises:
            ValueError: If external strategy is used without external ID column
        """

        def _to_nullable_int_series(values):
            """Cast a sequence of potentially missing values to pandas nullable Int64."""
            return pd.Series(
                [pd.NA if pd.isna(value) else int(value) for value in values],
                dtype="Int64",
            )

        if strategy == "hash":
            # MD5 hash of full_path (deterministic across runs)
            # Using 16 hex digits (64 bits) to reduce collision probability
            # With 64 bits, ~5 billion entries needed for 50% collision risk vs 65k with 32 bits
            # Convert to signed int64 for database compatibility
            new_ids = [
                int(hashlib.md5(path.encode()).hexdigest()[:16], 16) % (2**63)
                for path in df["full_path"]
            ]

        elif strategy == "sequence":
            # Sequential IDs (less stable but simpler)
            new_ids = list(range(1, len(df) + 1))

        elif strategy == "external":
            # Use external ID column if provided
            external_col = None
            for col in df.columns:
                if col not in {
                    "level",
                    "rank_name",
                    "rank_value",
                    "full_path",
                    "parent_path",
                    "temp_id",
                    "parent_id",
                }:
                    external_col = col
                    break

            if external_col is None or external_col not in df.columns:
                raise ValueError(
                    "External ID strategy requires external ID column in extraction config"
                )

            new_ids = df[external_col].tolist()

        else:
            raise ValueError(f"Unsupported ID strategy: {strategy}")

        # Map full paths to newly generated IDs (skip missing values)
        id_lookup = {
            path: int(value)
            for path, value in zip(df["full_path"], new_ids)
            if value is not None and not pd.isna(value)
        }

        parent_ids = [
            id_lookup.get(parent_path) if parent_path else None
            for parent_path in df["parent_path"]
        ]

        df["id"] = _to_nullable_int_series(new_ids)
        df["parent_id"] = _to_nullable_int_series(parent_ids)

        # Normalise other *_id columns to avoid float coercion (e.g. taxons_id)
        for col in df.columns:
            if col.endswith("_id") and col not in {"id", "parent_id"}:
                df[col] = _to_nullable_int_series(df[col])

        # Select final columns
        base_cols = ["id", "parent_id", "level", "rank_name", "rank_value", "full_path"]
        extra_cols = [
            c for c in df.columns if c not in base_cols + ["temp_id", "parent_path"]
        ]

        return df[base_cols + extra_cols]

    def add_nested_sets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add nested set (lft/rght) fields to hierarchical DataFrame.

        Nested sets allow efficient hierarchical queries:
        - A node's descendants have lft between node.lft and node.rght
        - Single query retrieves entire subtree

        Args:
            df: DataFrame with id, parent_id, level columns

        Returns:
            DataFrame with lft, rght columns added

        Algorithm:
            Modified Preorder Tree Traversal
            1. Start at root (parent_id=None), counter=1
            2. Set lft=counter, increment
            3. Recursively visit children
            4. Set rght=counter, increment
        """
        if len(df) == 0:
            return df

        # Initialize lft/rght columns
        df["lft"] = None
        df["rght"] = None

        # Build parent->children mapping
        children_map = {}
        for idx, row in df.iterrows():
            parent = row["parent_id"]
            if pd.isna(parent):
                parent = None
            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(idx)

        # Recursive tree traversal
        counter = [1]  # Use list to allow modification in nested function

        def traverse(node_idx):
            """Recursively assign lft/rght values."""
            # Set lft value
            df.at[node_idx, "lft"] = counter[0]
            counter[0] += 1

            # Traverse children
            node_id = df.at[node_idx, "id"]
            if node_id in children_map:
                for child_idx in sorted(children_map[node_id]):
                    traverse(child_idx)

            # Set rght value
            df.at[node_idx, "rght"] = counter[0]
            counter[0] += 1

        # Start traversal from root nodes (parent_id=None)
        root_indices = df[df["parent_id"].isna()].index
        for root_idx in sorted(root_indices):
            traverse(root_idx)

        # Convert to int (were set as None initially)
        df["lft"] = df["lft"].astype("Int64")
        df["rght"] = df["rght"].astype("Int64")

        return df
