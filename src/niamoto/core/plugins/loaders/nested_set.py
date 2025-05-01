from typing import Dict, Any, Literal
from pydantic import field_validator
from sqlalchemy import text
import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register


class NestedSetConfig(PluginConfig):
    """Configuration for nested set loader"""

    plugin: Literal["nested_set"]
    key: str
    fields: Dict[str, str]

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate that all required fields are present"""
        required = {"left", "right", "parent"}
        field_mapping = {
            "left": v.get("left"),
            "right": v.get("right"),
            "parent": v.get("parent"),
        }

        # Vérifier que tous les champs requis sont présents
        missing = required - set(k for k, v in field_mapping.items() if v)
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        return field_mapping


@register("nested_set", PluginType.LOADER)
class NestedSetLoader(LoaderPlugin):
    """Loader for nested set hierarchies"""

    config_model = NestedSetConfig

    def validate_config(self, config: Dict[str, Any]) -> NestedSetConfig:
        """Validate plugin configuration."""
        return self.config_model(**config)

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        validated_config = self.validate_config(config)
        fields = validated_config.fields

        # Get the left and right values for the target node
        node_query = text(f"""
            SELECT {fields["left"]}, {fields["right"]}
            FROM {config["grouping"]}
            WHERE id = :id
        """)

        with self.db.engine.connect() as conn:
            node = conn.execute(node_query, {"id": group_id}).fetchone()
            if not node:
                return pd.DataFrame()

            # Get all records that belong to the target node's hierarchy
            query = text(f"""
                SELECT m.*
                FROM {config["data"]} m
                JOIN {config["grouping"]} ref ON m.{validated_config.key} = ref.id
                WHERE ref.{fields["left"]} >= :left
                AND ref.{fields["right"]} <= :right
            """)

            return pd.read_sql(query, conn, params={"left": node[0], "right": node[1]})
