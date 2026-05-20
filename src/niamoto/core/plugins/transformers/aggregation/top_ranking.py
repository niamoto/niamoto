"""
Plugin for getting top N items from a dataset with support for hierarchical data.
"""

import re
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register

_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_identifier(identifier: str) -> str:
    """Validate and quote a single SQL identifier."""
    if not _SQL_IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return f'"{identifier}"'


def _quote_literal(value: str) -> str:
    """Quote a SQL string literal."""
    return "'" + str(value).replace("'", "''") + "'"


class HierarchyColumns(BaseModel):
    """Column mapping for hierarchy table."""

    id: str = Field(default="id", description="ID column name")
    name: str = Field(default="full_name", description="Name column for display")
    rank: str = Field(default="rank_name", description="Rank column name")
    parent_id: str = Field(default="parent_id", description="Parent ID column name")
    left: str = Field(default="lft", description="Left boundary for nested set")
    right: str = Field(default="rght", description="Right boundary for nested set")


class JoinColumns(BaseModel):
    """Column mapping for join table."""

    source_id: Optional[str] = Field(
        default=None, description="Source ID column in join table"
    )
    target_id: Optional[str] = Field(
        default=None, description="Target ID column in join table"
    )
    hierarchy_id: Optional[str] = Field(
        default=None, description="Hierarchy reference column"
    )


class TopRankingParams(BasePluginParams):
    """Parameters for top ranking transformer."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Get top N items with support for hierarchical data",
            "examples": [
                {
                    "source": "occurrences",
                    "field": "taxons_id",
                    "count": 10,
                    "mode": "hierarchical",
                    "hierarchy_table": "taxons",
                    "target_ranks": ["family", "genus"],
                },
                {
                    "source": "occurrences",
                    "field": "plots_id",
                    "count": 5,
                    "mode": "direct",
                },
            ],
        }
    )

    source: str = Field(
        default="occurrences",
        description="Data source entity name",
        json_schema_extra={
            "ui:widget": "entity-select",
            # No filter - allow all entities (datasets + references)
        },
    )

    field: str = Field(
        ...,
        description="Field to rank",
        json_schema_extra={"ui:widget": "field-select", "ui:depends": "source"},
    )

    count: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of top items to return",
        json_schema_extra={
            "ui:widget": "number",
            "ui:quick_edit": True,
        },
    )

    mode: Literal["direct", "hierarchical", "join"] = Field(
        default="direct",
        description="Ranking mode: direct (simple count), hierarchical (navigate hierarchy), or join (use join table)",
        json_schema_extra={"ui:widget": "select"},
    )

    # Hierarchical mode fields
    hierarchy_table: Optional[str] = Field(
        default=None,
        description="Hierarchy table name (required for hierarchical/join modes)",
        json_schema_extra={
            "ui:widget": "entity-select",
            "ui:condition": "mode !== 'direct'",
        },
    )

    hierarchy_columns: HierarchyColumns = Field(
        default_factory=HierarchyColumns,
        description="Column mapping for hierarchy table",
        json_schema_extra={"ui:condition": "mode !== 'direct'"},
    )

    target_ranks: List[str] = Field(
        default_factory=list,
        description="Target ranks to aggregate to (for hierarchical mode)",
        json_schema_extra={
            "ui:widget": "tags",
            "ui:condition": "mode === 'hierarchical'",
        },
    )

    # Join mode fields
    join_table: Optional[str] = Field(
        default=None,
        description="Join table name (required for join mode)",
        json_schema_extra={
            "ui:widget": "entity-select",
            "ui:condition": "mode === 'join'",
        },
    )

    join_columns: JoinColumns = Field(
        default_factory=JoinColumns,
        description="Column mapping for join table",
        json_schema_extra={"ui:condition": "mode === 'join'"},
    )

    # Aggregation fields
    aggregate_function: Literal["count", "sum", "avg"] = Field(
        default="count",
        description="Aggregation function to use",
        json_schema_extra={"ui:widget": "select"},
    )

    aggregate_field: Optional[str] = Field(
        default=None,
        description="Field to aggregate (for sum/avg functions)",
        json_schema_extra={
            "ui:widget": "field-select",
            "ui:depends": "source",
            "ui:condition": "aggregate_function !== 'count'",
        },
    )

    @model_validator(mode="before")
    @classmethod
    def infer_legacy_mode(cls, values: Any) -> Any:
        """Infer mode for legacy configs that predate the explicit mode field."""

        if not isinstance(values, dict) or values.get("mode"):
            return values

        if values.get("join_table"):
            return {**values, "mode": "join"}

        if values.get("hierarchy_table") or values.get("target_ranks"):
            return {**values, "mode": "hierarchical"}

        return values

    @model_validator(mode="after")
    def validate_aggregate_field_requirement(self) -> "TopRankingParams":
        """Ensure mode-specific parameters are provided and valid."""

        if self.mode in {"hierarchical", "join"} and not self.hierarchy_table:
            raise ValueError(
                f"hierarchy_table is required when mode is '{self.mode}'. "
                "Please specify the entity name (e.g., 'taxonomy', 'plots', 'shapes')"
            )

        agg_func = self.aggregate_function
        if agg_func in {"sum", "avg"}:
            if not self.aggregate_field:
                msg = "aggregate_field is required when aggregate_function is 'sum' or 'avg'"
                raise ValueError(msg)

            if not self._is_safe_identifier(self.aggregate_field):
                msg = "aggregate_field must be an alphanumeric column name (letters, numbers, underscore)"
                raise ValueError(msg)

        return self

    @staticmethod
    def _is_safe_identifier(identifier: str) -> bool:
        """Check that an identifier is made of safe SQL characters."""
        return bool(_SQL_IDENTIFIER_RE.fullmatch(identifier))

    @field_validator("mode")
    @classmethod
    def validate_mode_requirements(cls, v: str, info) -> str:
        """Validate mode-specific requirements."""
        return v

    @field_validator("hierarchy_table")
    @classmethod
    def validate_hierarchy_table(cls, v: Optional[str], info) -> Optional[str]:
        """Validate hierarchy_table is provided for hierarchical/join modes."""
        mode = info.data.get("mode")
        if mode in ["hierarchical", "join"] and not v:
            raise ValueError(
                f"hierarchy_table is required when mode is '{mode}'. "
                "Please specify the entity name (e.g., 'taxonomy', 'plots', 'shapes')"
            )
        return v


class TopRankingConfig(PluginConfig):
    """Configuration for top ranking transformer."""

    plugin: Literal["top_ranking"] = "top_ranking"
    params: TopRankingParams


@register("top_ranking", PluginType.TRANSFORMER)
class TopRanking(TransformerPlugin):
    """Plugin for getting top N items"""

    config_model = TopRankingConfig
    param_schema = TopRankingParams  # For exposing params with UI hints

    # Output structure for pattern matching
    output_structure = {"tops": "list", "counts": "list"}

    def __init__(self, db, registry=None):
        """Initialize with optional registry."""
        super().__init__(db, registry)
        # Use resolve_entity_table from parent Plugin class if registry available
        # This replaces the old _resolve_table_name method

    def _resolve_table_name(self, logical_name: str) -> str:
        """Resolve logical table name to actual table name via entity registry.

        Uses the parent Plugin.resolve_entity_table() method for consistency.
        """
        return self.resolve_entity_table(logical_name)

    def validate_config(self, config: Dict[str, Any]) -> TopRankingConfig:
        """Validate configuration and return typed config."""
        try:
            return self.config_model(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}") from e

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get field data
            field = params.field
            if field not in data.columns:
                return {"tops": [], "counts": []}

            field_data = data[field]
            if field_data.empty:
                return {"tops": [], "counts": []}

            # Process according to mode
            mode = params.mode
            if mode == "direct":
                return self._process_direct_ranking(field_data, params)
            elif mode == "hierarchical":
                return self._process_hierarchical_ranking(field_data, params)
            elif mode == "join":
                return self._process_join_ranking(field_data, params)
            else:
                raise ValueError(f"Unknown mode: {mode}")

        except Exception as e:
            raise ValueError(f"Transform error: {str(e)}") from e

    def _process_direct_ranking(
        self, field_data: pd.Series, params: TopRankingParams
    ) -> Dict[str, Any]:
        """Process direct ranking without hierarchy."""
        # Count occurrences
        value_counts = field_data.value_counts()

        # Get top N
        top_items = value_counts.head(params.count)

        # Split into tops and counts
        tops = top_items.index.tolist()
        counts = top_items.values.tolist()

        # Enrich with names if hierarchy_table is provided
        if params.hierarchy_table:
            tops = self._enrich_with_names(tops, params)

        return {"tops": tops, "counts": counts}

    def _enrich_with_names(self, ids: List, params: TopRankingParams) -> List[str]:
        """Enrich IDs with names from hierarchy table."""
        if not ids:
            return []

        try:
            # Resolve table name
            hierarchy_table = self._resolve_table_name(params.hierarchy_table)
            cols = params.hierarchy_columns
            quoted_hierarchy_table = _quote_identifier(hierarchy_table)

            # Get name column (default to "full_name" if not specified)
            name_col = cols.name if cols and cols.name else "full_name"
            quoted_name_col = _quote_identifier(name_col)

            # Build query to get names
            ids_str = ",".join(str(int(id)) for id in ids)

            # Determine which ID field to use for matching
            # IMPORTANT: The IDs we receive are from the source data (e.g., id_taxonref)
            # These correspond to taxon_id in entity_taxonomy, NOT to the hash-based id field
            id_field = cols.id if (cols and cols.id) else "id"
            quoted_id_field = _quote_identifier(id_field)

            # Use the specified id field from config, or default to "id"
            query = f"""
                SELECT {quoted_id_field}, {quoted_name_col}
                FROM {quoted_hierarchy_table}
                WHERE {quoted_id_field} IN ({ids_str})
            """

            with self.db.connection() as fresh_conn:
                from sqlalchemy import text
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Enrichment query: {query}")
                result = fresh_conn.execute(text(query))
                rows = result.fetchall()

            if not rows:
                return [str(id) for id in ids]

            # Build ID -> name mapping
            id_to_name = {row[0]: row[1] for row in rows}

            # Return names in same order as input IDs
            # Handle type mismatch: pandas may return strings, dict has int keys
            def safe_get_name(id_val):
                try:
                    # Convert to int for dict lookup if needed
                    numeric_id = int(id_val) if isinstance(id_val, str) else id_val
                    return id_to_name.get(numeric_id, str(id_val))
                except (ValueError, TypeError):
                    return str(id_val)

            return [safe_get_name(id) for id in ids]

        except Exception as e:
            # Fallback to IDs if enrichment fails
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to enrich names for IDs {ids[:3]}...: {e}")
            return [str(id) for id in ids]

    def _process_hierarchical_ranking(
        self, field_data: pd.Series, params: TopRankingParams
    ) -> Dict[str, Any]:
        """Process ranking with hierarchical navigation."""
        # Get unique IDs
        unique_ids = set(field_data.dropna().unique())
        if not unique_ids:
            return {"tops": [], "counts": []}

        # Get hierarchy configuration and resolve table name
        hierarchy_table = self._resolve_table_name(params.hierarchy_table)
        cols = params.hierarchy_columns
        id_col = cols.id
        name_col = cols.name
        rank_col = cols.rank
        parent_col = cols.parent_id

        # Build hierarchy dictionary
        hierarchy_dict = self._build_hierarchy_dict(
            unique_ids, hierarchy_table, id_col, name_col, rank_col, parent_col
        )

        # Count items by target rank
        target_ranks = params.target_ranks
        item_counts = {}

        for item_id in field_data.dropna():
            if item_id in hierarchy_dict:
                # Navigate hierarchy to find target rank
                current_id = item_id
                while current_id is not None:
                    current_item = hierarchy_dict.get(current_id)
                    if not current_item:
                        break

                    if current_item[rank_col] in target_ranks:
                        item_name = current_item[name_col]
                        item_counts[item_name] = item_counts.get(item_name, 0) + 1
                        break

                    current_id = current_item.get(parent_col)

        # Sort and get top N
        sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)
        top_items = sorted_items[: params.count]

        tops = [item[0] for item in top_items]
        counts = [item[1] for item in top_items]

        return {"tops": tops, "counts": counts}

    def _process_join_ranking(
        self, field_data: pd.Series, params: TopRankingParams
    ) -> Dict[str, Any]:
        """Process ranking with join table.

        Supports both nested sets (lft/rght) and adjacency list (parent_id) models.
        Auto-detects which model is available in the hierarchy table.
        """
        # Get unique IDs
        unique_ids = set(field_data.dropna().unique())
        if not unique_ids:
            return {"tops": [], "counts": []}

        # Get configuration and resolve table names
        join_table = (
            self._resolve_table_name(params.join_table) if params.join_table else None
        )
        if join_table is None:
            raise ValueError(
                "join_table is required when mode is 'join'. "
                "Please specify the entity to join against."
            )
        hierarchy_table = self._resolve_table_name(params.hierarchy_table)
        join_cols = params.join_columns
        hierarchy_cols = params.hierarchy_columns

        source_col = join_cols.source_id or "id"
        hierarchy_ref_col = join_cols.hierarchy_id or "hierarchy_id"

        hierarchy_id_col = hierarchy_cols.id
        hierarchy_name_col = hierarchy_cols.name
        hierarchy_rank_col = hierarchy_cols.rank
        hierarchy_parent_col = hierarchy_cols.parent_id
        hierarchy_left_col = hierarchy_cols.left
        hierarchy_right_col = hierarchy_cols.right

        target_ranks = params.target_ranks
        aggregate_func = params.aggregate_function
        aggregate_column = params.aggregate_field
        metric_alias = "metric_value" if aggregate_column else None
        quoted_join_table = _quote_identifier(join_table)
        quoted_hierarchy_table = _quote_identifier(hierarchy_table)
        quoted_source_col = _quote_identifier(source_col)
        quoted_hierarchy_ref_col = _quote_identifier(hierarchy_ref_col)
        quoted_hierarchy_id_col = _quote_identifier(hierarchy_id_col)
        quoted_hierarchy_name_col = _quote_identifier(hierarchy_name_col)
        quoted_hierarchy_rank_col = _quote_identifier(hierarchy_rank_col)
        quoted_hierarchy_parent_col = _quote_identifier(hierarchy_parent_col)
        quoted_hierarchy_left_col = _quote_identifier(hierarchy_left_col)
        quoted_hierarchy_right_col = _quote_identifier(hierarchy_right_col)
        quoted_target_ranks = ",".join(_quote_literal(rank) for rank in target_ranks)
        quoted_metric_base_select = (
            f", j.{_quote_identifier(aggregate_column)} as {metric_alias}"
            if aggregate_column
            else ""
        )

        # Build query dynamically
        ids_str = ",".join(str(int(id)) for id in unique_ids)

        # Check if hierarchy table uses nested sets or adjacency list
        # Try to detect by checking if lft/rght columns exist
        has_nested_sets = self._has_columns(
            hierarchy_table, [hierarchy_left_col, hierarchy_right_col]
        )

        if has_nested_sets:
            # Use nested sets query (legacy)
            query = f"""
                SELECT h_target.{quoted_hierarchy_name_col}, {self._get_aggregate_sql(aggregate_func, "j", aggregate_column)}
                FROM {quoted_join_table} j
                JOIN {quoted_hierarchy_table} h_source ON j.{quoted_hierarchy_ref_col} = h_source.{quoted_hierarchy_id_col}
                JOIN {quoted_hierarchy_table} h_target ON (
                    h_target.{quoted_hierarchy_left_col} <= h_source.{quoted_hierarchy_left_col}
                    AND h_target.{quoted_hierarchy_right_col} >= h_source.{quoted_hierarchy_right_col}
                    AND h_target.{quoted_hierarchy_rank_col} IN ({quoted_target_ranks})
                )
                WHERE j.{quoted_source_col} IN ({ids_str})
                GROUP BY h_target.{quoted_hierarchy_name_col}
                ORDER BY {self._get_aggregate_sql(aggregate_func, "j", aggregate_column)} DESC
                LIMIT {params.count}
            """
        else:
            # Use adjacency list query with recursive CTE
            metric_recursive_select = f", hp.{metric_alias}" if aggregate_column else ""
            query = f"""
                WITH RECURSIVE hierarchy_path AS (
                    -- Base case: source nodes
                    SELECT
                        h_source.{quoted_hierarchy_id_col} as source_id,
                        h_source.{quoted_hierarchy_id_col} as current_id,
                        h_source.{quoted_hierarchy_name_col} as current_name,
                        h_source.{quoted_hierarchy_rank_col} as current_rank,
                        h_source.{quoted_hierarchy_parent_col} as parent_id
                        {quoted_metric_base_select}
                    FROM {quoted_hierarchy_table} h_source
                    JOIN {quoted_join_table} j ON j.{quoted_hierarchy_ref_col} = h_source.{quoted_hierarchy_id_col}
                    WHERE j.{quoted_source_col} IN ({ids_str})

                    UNION ALL

                    -- Recursive case: traverse up to parents
                    SELECT
                        hp.source_id,
                        h_parent.{quoted_hierarchy_id_col},
                        h_parent.{quoted_hierarchy_name_col},
                        h_parent.{quoted_hierarchy_rank_col},
                        h_parent.{quoted_hierarchy_parent_col}
                        {metric_recursive_select}
                    FROM hierarchy_path hp
                    JOIN {quoted_hierarchy_table} h_parent ON hp.parent_id = h_parent.{quoted_hierarchy_id_col}
                )
                SELECT current_name, {self._get_aggregate_sql(aggregate_func, "hierarchy_path", metric_alias)}
                FROM hierarchy_path
                WHERE current_rank IN ({quoted_target_ranks})
                GROUP BY current_name
                ORDER BY {self._get_aggregate_sql(aggregate_func, "hierarchy_path", metric_alias)} DESC
                LIMIT {params.count}
            """

        result = self.db.execute_select(query)
        if not result:
            return {"tops": [], "counts": []}

        # Extract results
        tops = []
        counts = []
        for row in result.fetchall():
            tops.append(row[0])
            counts.append(row[1])

        return {"tops": tops, "counts": counts}

    def _build_hierarchy_dict(
        self,
        ids: set,
        table: str,
        id_col: str,
        name_col: str,
        rank_col: str,
        parent_col: str,
    ) -> Dict[int, Dict[str, Any]]:
        """Build hierarchy dictionary from database."""
        hierarchy_dict = {}
        quoted_table = _quote_identifier(table)
        quoted_id_col = _quote_identifier(id_col)
        quoted_name_col = _quote_identifier(name_col)
        quoted_rank_col = _quote_identifier(rank_col)
        quoted_parent_col = _quote_identifier(parent_col)

        # Query initial items
        ids_str = ",".join(str(int(id)) for id in ids)
        query = f"""
            SELECT {quoted_id_col}, {quoted_name_col}, {quoted_rank_col}, {quoted_parent_col}
            FROM {quoted_table}
            WHERE {quoted_id_col} IN ({ids_str})
        """

        result = self.db.execute_select(query)
        if not result:
            return hierarchy_dict

        # Build initial dictionary
        for row in result.fetchall():
            hierarchy_dict[row[0]] = {
                id_col: row[0],
                name_col: row[1],
                rank_col: row[2],
                parent_col: row[3],
            }

        # Query parents iteratively
        parent_ids = {
            item[parent_col]
            for item in hierarchy_dict.values()
            if item.get(parent_col) is not None
        }

        while parent_ids:
            parent_ids_str = ",".join(str(id) for id in parent_ids)
            query = f"""
                SELECT {quoted_id_col}, {quoted_name_col}, {quoted_rank_col}, {quoted_parent_col}
                FROM {quoted_table}
                WHERE {quoted_id_col} IN ({parent_ids_str})
            """

            result = self.db.execute_select(query)
            if not result:
                break

            # Add parents to dictionary
            for row in result.fetchall():
                parent_id = row[0]
                hierarchy_dict[parent_id] = {
                    id_col: parent_id,
                    name_col: row[1],
                    rank_col: row[2],
                    parent_col: row[3],
                }

            # Get next level of parents
            parent_ids = {
                item[parent_col]
                for item in hierarchy_dict.values()
                if item.get(parent_col) is not None
                and item[parent_col] not in hierarchy_dict
            }

        return hierarchy_dict

    def _get_aggregate_sql(
        self,
        func: str,
        table_alias: str,
        column: Optional[str] = None,
    ) -> str:
        """Get SQL aggregate function string."""
        if func == "count":
            return "COUNT(*)"

        if not column:
            raise ValueError(
                "aggregate_field must be provided when aggregate_function is 'sum' or 'avg'"
            )

        if func == "sum":
            return f'SUM({table_alias}."{column}")'
        if func == "avg":
            return f'AVG({table_alias}."{column}")'
        raise ValueError(f"Unsupported aggregate_function: {func}")

    def _has_columns(self, table: str, columns: List[str]) -> bool:
        """Check if table has all specified columns.

        Args:
            table: Table name to check
            columns: List of column names to verify

        Returns:
            True if all columns exist, False otherwise
        """
        try:
            # Try to get table columns
            table_columns = self.db.get_table_columns(table)
            if not table_columns:
                return False

            # Check if all required columns exist
            return all(col in table_columns for col in columns)
        except Exception:
            return False
