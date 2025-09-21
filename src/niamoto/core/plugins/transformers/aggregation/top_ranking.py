"""
Plugin for getting top N items from a dataset with support for hierarchical data.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register


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
                    "field": "taxon_ref_id",
                    "count": 10,
                    "mode": "hierarchical",
                    "hierarchy_table": "taxon_ref",
                    "target_ranks": ["family", "genus"],
                },
                {
                    "source": "occurrences",
                    "field": "plot_ref_id",
                    "count": 5,
                    "mode": "direct",
                },
            ],
        }
    )

    source: str = Field(
        default="occurrences",
        description="Source table name",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": ["occurrences", "taxonomy", "plots", "shapes"],
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
        json_schema_extra={"ui:widget": "number"},
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
            "ui:widget": "select",
            "ui:options": ["taxon_ref", "plot_ref", "shape_ref"],
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
        json_schema_extra={"ui:widget": "text", "ui:condition": "mode === 'join'"},
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

    @field_validator("mode")
    @classmethod
    def validate_mode_requirements(cls, v: str, info) -> str:
        """Validate mode-specific requirements."""
        return v

    @field_validator("hierarchy_table")
    @classmethod
    def validate_hierarchy_table(cls, v: Optional[str], info) -> Optional[str]:
        """Auto-set hierarchy table for common cases."""
        if info.data.get("mode") == "hierarchical" and not v:
            field = info.data.get("field")
            if field == "taxon_ref_id":
                return "taxon_ref"
            elif field == "plot_ref_id":
                return "plot_ref"
            elif field == "shape_ref_id":
                return "shape_ref"
        return v


class TopRankingConfig(PluginConfig):
    """Configuration for top ranking transformer."""

    plugin: Literal["top_ranking"] = "top_ranking"
    params: TopRankingParams


@register("top_ranking", PluginType.TRANSFORMER)
class TopRanking(TransformerPlugin):
    """Plugin for getting top N items"""

    config_model = TopRankingConfig

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

        return {"tops": tops, "counts": counts}

    def _process_hierarchical_ranking(
        self, field_data: pd.Series, params: TopRankingParams
    ) -> Dict[str, Any]:
        """Process ranking with hierarchical navigation."""
        # Get unique IDs
        unique_ids = set(field_data.dropna().unique())
        if not unique_ids:
            return {"tops": [], "counts": []}

        # Get hierarchy configuration
        hierarchy_table = params.hierarchy_table
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
        """Process ranking with join table."""
        # Get unique IDs
        unique_ids = set(field_data.dropna().unique())
        if not unique_ids:
            return {"tops": [], "counts": []}

        # Get configuration
        join_table = params.join_table
        hierarchy_table = params.hierarchy_table
        join_cols = params.join_columns
        hierarchy_cols = params.hierarchy_columns

        source_col = join_cols.source_id or "id"
        hierarchy_ref_col = join_cols.hierarchy_id or "hierarchy_id"

        hierarchy_id_col = hierarchy_cols.id
        hierarchy_name_col = hierarchy_cols.name
        hierarchy_rank_col = hierarchy_cols.rank
        hierarchy_left_col = hierarchy_cols.left
        hierarchy_right_col = hierarchy_cols.right

        target_ranks = params.target_ranks
        aggregate_func = params.aggregate_function

        # Build query dynamically
        ids_str = ",".join(str(int(id)) for id in unique_ids)

        query = f"""
            SELECT h_target.{hierarchy_name_col}, {self._get_aggregate_sql(aggregate_func, join_table)}
            FROM {join_table} j
            JOIN {hierarchy_table} h_source ON j.{hierarchy_ref_col} = h_source.{hierarchy_id_col}
            JOIN {hierarchy_table} h_target ON (
                h_target.{hierarchy_left_col} <= h_source.{hierarchy_left_col}
                AND h_target.{hierarchy_right_col} >= h_source.{hierarchy_right_col}
                AND h_target.{hierarchy_rank_col} IN ({",".join([f"'{rank}'" for rank in target_ranks])})
            )
            WHERE j.{source_col} IN ({ids_str})
            GROUP BY h_target.{hierarchy_name_col}
            ORDER BY {self._get_aggregate_sql(aggregate_func, join_table)} DESC
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

        # Query initial items
        ids_str = ",".join(str(int(id)) for id in ids)
        query = f"""
            SELECT {id_col}, {name_col}, {rank_col}, {parent_col}
            FROM {table}
            WHERE {id_col} IN ({ids_str})
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
                SELECT {id_col}, {name_col}, {rank_col}, {parent_col}
                FROM {table}
                WHERE {id_col} IN ({parent_ids_str})
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

    def _get_aggregate_sql(self, func: str, table: str) -> str:
        """Get SQL aggregate function string."""
        if func == "count":
            return "COUNT(*)"
        elif func == "sum":
            return f"SUM({table}.value)"
        elif func == "avg":
            return f"AVG({table}.value)"
        else:
            return "COUNT(*)"
