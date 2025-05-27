"""
Plugin for getting top N items from a dataset with support for hierarchical data.
"""

from typing import Dict, Any
from pydantic import field_validator, Field

import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register


class TopRankingConfig(PluginConfig):
    """Configuration for top ranking transformer."""

    plugin: str = "top_ranking"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "occurrences",
            "field": None,
            "count": 10,
            "mode": "direct",  # 'direct' or 'hierarchical' or 'join'
            # For hierarchical mode
            "hierarchy_table": None,
            "hierarchy_columns": {
                "id": "id",
                "name": "full_name",
                "rank": "rank_name",
                "parent_id": "parent_id",
                "left": "lft",
                "right": "rght",
            },
            "target_ranks": [],
            # For join mode
            "join_table": None,
            "join_columns": {
                "source_id": None,
                "target_id": None,
                "hierarchy_id": None,
            },
            # For aggregation
            "aggregate_function": "count",  # count, sum, avg, etc.
            "aggregate_field": None,  # field to aggregate if not counting
        }
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        required_fields = ["source", "field"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

        # Auto-detect mode for backward compatibility
        if "mode" not in v:
            if v.get("hierarchy_table") or (
                v.get("target_ranks") and not v.get("join_table")
            ):
                v["mode"] = "hierarchical"
            elif v.get("join_table"):
                v["mode"] = "join"
            else:
                v["mode"] = "direct"

        # Set default values if not provided
        if "count" not in v:
            v["count"] = 10
        if "aggregate_function" not in v:
            v["aggregate_function"] = "count"

        # Validate count
        if not isinstance(v["count"], (int, float)):
            raise ValueError("count must be a number")
        if v["count"] <= 0:
            raise ValueError("count must be positive")

        # Validate mode-specific requirements
        mode = v.get("mode", "direct")
        if mode == "hierarchical":
            if not v.get("hierarchy_table") and v.get("field") == "taxon_ref_id":
                # Default hierarchy table for backward compatibility
                v["hierarchy_table"] = "taxon_ref"
            if not v.get("hierarchy_table"):
                raise ValueError("hierarchy_table is required for hierarchical mode")
            if not v.get("target_ranks"):
                raise ValueError("target_ranks is required for hierarchical mode")
        elif mode == "join":
            if not v.get("join_table"):
                raise ValueError("join_table is required for join mode")
            if not v.get("hierarchy_table"):
                raise ValueError("hierarchy_table is required for join mode")
            if not v.get("join_columns"):
                raise ValueError("join_columns is required for join mode")

        return v


@register("top_ranking", PluginType.TRANSFORMER)
class TopRanking(TransformerPlugin):
    """Plugin for getting top N items"""

    config_model = TopRankingConfig

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration."""
        try:
            return self.config_model(**config).model_dump()
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}") from e

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            validated_config = self.validate_config(config)
            params = validated_config["params"]

            # Get field data
            field = params["field"]
            if field not in data.columns:
                return {"tops": [], "counts": []}

            field_data = data[field]
            if field_data.empty:
                return {"tops": [], "counts": []}

            # Process according to mode
            mode = params.get("mode", "direct")
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
        self, field_data: pd.Series, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process direct ranking without hierarchy."""
        # Count occurrences
        value_counts = field_data.value_counts()

        # Get top N
        top_items = value_counts.head(params["count"])

        # Split into tops and counts
        tops = top_items.index.tolist()
        counts = top_items.values.tolist()

        return {"tops": tops, "counts": counts}

    def _process_hierarchical_ranking(
        self, field_data: pd.Series, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process ranking with hierarchical navigation."""
        # Get unique IDs
        unique_ids = set(field_data.dropna().unique())
        if not unique_ids:
            return {"tops": [], "counts": []}

        # Get hierarchy configuration
        hierarchy_table = params["hierarchy_table"]
        cols = params.get("hierarchy_columns", {})
        id_col = cols.get("id", "id")
        name_col = cols.get("name", "full_name")
        rank_col = cols.get("rank", "rank_name")
        parent_col = cols.get("parent_id", "parent_id")

        # Build hierarchy dictionary
        hierarchy_dict = self._build_hierarchy_dict(
            unique_ids, hierarchy_table, id_col, name_col, rank_col, parent_col
        )

        # Count items by target rank
        target_ranks = params.get("target_ranks", [])
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
        top_items = sorted_items[: params["count"]]

        tops = [item[0] for item in top_items]
        counts = [item[1] for item in top_items]

        return {"tops": tops, "counts": counts}

    def _process_join_ranking(
        self, field_data: pd.Series, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process ranking with join table."""
        # Get unique IDs
        unique_ids = set(field_data.dropna().unique())
        if not unique_ids:
            return {"tops": [], "counts": []}

        # Get configuration
        join_table = params["join_table"]
        hierarchy_table = params["hierarchy_table"]
        join_cols = params.get("join_columns", {})
        hierarchy_cols = params.get("hierarchy_columns", {})

        source_col = join_cols.get("source_id", "id")
        hierarchy_ref_col = join_cols.get("hierarchy_id", "hierarchy_id")

        hierarchy_id_col = hierarchy_cols.get("id", "id")
        hierarchy_name_col = hierarchy_cols.get("name", "full_name")
        hierarchy_rank_col = hierarchy_cols.get("rank", "rank_name")
        hierarchy_left_col = hierarchy_cols.get("left", "lft")
        hierarchy_right_col = hierarchy_cols.get("right", "rght")

        target_ranks = params.get("target_ranks", [])
        aggregate_func = params.get("aggregate_function", "count")

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
            LIMIT {params["count"]}
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
