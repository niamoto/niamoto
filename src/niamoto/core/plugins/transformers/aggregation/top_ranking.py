"""
Plugin for getting top N items from a dataset.
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
            "target_ranks": ["species", "infra"],
            "count": 10,
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

        # Set default values if not provided
        if "target_ranks" not in v:
            v["target_ranks"] = ["species", "infra"]
        if "count" not in v:
            v["count"] = 10

        # Validate target_ranks
        if not isinstance(v["target_ranks"], list):
            raise ValueError("target_ranks must be a list")

        # Validate count
        if not isinstance(v["count"], (int, float)):
            raise ValueError("count must be a number")
        if v["count"] <= 0:
            raise ValueError("count must be positive")

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

            # Get field data
            field = (
                validated_config["params"]["field"]
                if validated_config["params"]["field"]
                else "taxon_ref_id"
            )
            if field not in data.columns:
                return {"tops": [], "counts": []}

            field_data = data[field]
            if field_data.empty:
                return {"tops": [], "counts": []}

            # Get unique taxon IDs
            taxon_ids = set(field_data.dropna().unique())
            if not taxon_ids:
                return {"tops": [], "counts": []}

            # Convert taxon_ids to a comma-separated string
            # Ensure IDs are integers before converting to string
            taxon_ids_str = ",".join(str(int(id)) for id in taxon_ids)

            # Query initial taxons
            query = f"""
                SELECT id, full_name, rank_name, parent_id
                FROM taxon_ref
                WHERE id IN ({taxon_ids_str})
            """

            result = self.db.execute_select(query)
            if not result:
                return {"tops": [], "counts": []}

            # Build initial taxon dictionary
            taxon_dict = {}
            for row in result.fetchall():
                taxon_dict[row[0]] = {
                    "id": row[0],
                    "full_name": row[1],
                    "rank_name": row[2],
                    "parent_id": row[3],
                }

            # Query parent taxons iteratively
            parent_ids = {
                taxon["parent_id"]
                for taxon in taxon_dict.values()
                if taxon["parent_id"] is not None
            }
            while parent_ids:
                # Convert parent_ids to string
                parent_ids_str = ",".join(str(id) for id in parent_ids)

                # Query parents
                query = f"""
                    SELECT id, full_name, rank_name, parent_id
                    FROM taxon_ref
                    WHERE id IN ({parent_ids_str})
                """

                result = self.db.execute_select(query)
                if not result:
                    break

                # Add parents to dictionary
                for row in result.fetchall():
                    parent_id = row[0]
                    taxon_dict[parent_id] = {
                        "id": parent_id,
                        "full_name": row[1],
                        "rank_name": row[2],
                        "parent_id": row[3],
                    }

                # Get next level of parents
                parent_ids = {
                    taxon["parent_id"]
                    for taxon in taxon_dict.values()
                    if taxon["parent_id"] is not None
                    and taxon["parent_id"] not in taxon_dict
                }

            # Count items by target rank
            item_counts = {}
            target_ranks = validated_config["params"]["target_ranks"]

            for taxon_id in field_data.dropna():
                if taxon_id in taxon_dict:
                    current_id = taxon_id
                    while current_id is not None:
                        current_taxon = taxon_dict.get(current_id)
                        if not current_taxon:
                            break

                        if current_taxon["rank_name"] in target_ranks:
                            item_name = current_taxon["full_name"]
                            item_counts[item_name] = item_counts.get(item_name, 0) + 1
                            break

                        current_id = current_taxon["parent_id"]

            # Sort items by count and get top N
            sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)
            top_items = sorted_items[: validated_config["params"]["count"]]

            # Split into tops and counts
            tops = [item[0] for item in top_items]
            counts = [item[1] for item in top_items]

            return {"tops": tops, "counts": counts}

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}") from e
