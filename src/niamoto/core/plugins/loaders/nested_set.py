from typing import Dict, Any, Literal
from pydantic import Field, field_validator, ConfigDict
from sqlalchemy import text
import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.core.imports.registry import EntityRegistry


class NestedSetParams(BasePluginParams):
    """Parameters for nested set loader"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Load hierarchical data using nested set model",
            "examples": [
                {
                    "key": "taxon_id",
                    "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
                }
            ],
        }
    )

    key: str = Field(
        ...,
        description="Foreign key field linking data to the hierarchy",
        json_schema_extra={"ui:widget": "text"},
    )

    ref_key: str = Field(
        default="id",
        description="Field in the reference table to match against (e.g., 'taxonomy_id', 'id')",
        json_schema_extra={"ui:widget": "text"},
    )

    fields: Dict[str, str] = Field(
        ...,
        description="Field mapping for nested set structure",
        json_schema_extra={
            "ui:widget": "object",
            "ui:options": {
                "properties": {
                    "left": {"type": "string", "title": "Left field", "default": "lft"},
                    "right": {
                        "type": "string",
                        "title": "Right field",
                        "default": "rght",
                    },
                    "parent": {
                        "type": "string",
                        "title": "Parent field",
                        "default": "parent_id",
                    },
                }
            },
        },
    )

    @field_validator("ref_key")
    @classmethod
    def validate_ref_key(cls, v: str) -> str:
        """Validate that ref_key is a safe SQL identifier"""
        import re

        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", v or ""):
            raise ValueError(f"Invalid SQL identifier: {v}")
        return v

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


class NestedSetConfig(PluginConfig):
    """Configuration for nested set loader"""

    plugin: Literal["nested_set"] = "nested_set"
    params: NestedSetParams


@register("nested_set", PluginType.LOADER)
class NestedSetLoader(LoaderPlugin):
    """Loader for nested set hierarchies"""

    config_model = NestedSetConfig

    def __init__(self, db, registry=None):
        """Initialize with database and optional EntityRegistry.

        Args:
            db: Database instance
            registry: EntityRegistry instance (created if not provided)
        """
        super().__init__(db)
        self.registry = registry or EntityRegistry(db)

    def _resolve_table_name(self, logical_name: str) -> str:
        """Resolve logical entity name to physical table name via EntityRegistry.

        Args:
            logical_name: Entity name from config (e.g., "taxons", "occurrences")

        Returns:
            Physical table name (e.g., "entity_taxons", "entity_occurrences")
            Falls back to logical_name if not found in registry (backward compatibility)
        """
        try:
            metadata = self.registry.get(logical_name)
            return metadata.table_name
        except Exception:
            # Fallback: assume it's already a physical table name
            # This maintains backward compatibility with configs that use table names directly
            return logical_name

    def validate_config(self, config: Dict[str, Any]) -> NestedSetConfig:
        """Validate plugin configuration."""
        # Extract params if they exist in the config
        if "params" not in config:
            # For backward compatibility, build params from top-level fields
            params = {}
            if "key" in config:
                params["key"] = config["key"]
            if "ref_key" in config:
                params["ref_key"] = config["ref_key"]
            if "fields" in config:
                params["fields"] = config["fields"]
            config = {"plugin": "nested_set", "params": params}
        return self.config_model(**config)

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        validated_config = self.validate_config(config)
        fields = validated_config.params.fields

        # Resolve entity names to physical table names via EntityRegistry
        grouping_table = self._resolve_table_name(config["grouping"])
        data_table = self._resolve_table_name(config["data"])

        # Get the left and right values for the target node
        node_query = text(f"""
            SELECT {fields["left"]}, {fields["right"]}
            FROM {grouping_table}
            WHERE id = :id
        """)

        with self.db.engine.connect() as conn:
            node = conn.execute(node_query, {"id": group_id}).fetchone()
            if not node:
                return pd.DataFrame()

            # Get all records that belong to the target node's hierarchy
            # Use ref_key to specify which field in the reference table to match against
            ref_key = validated_config.params.ref_key
            query = text(f"""
                SELECT m.*
                FROM {data_table} m
                JOIN {grouping_table} ref ON m.{validated_config.params.key} = ref.{ref_key}
                WHERE ref.{fields["left"]} >= :left
                AND ref.{fields["right"]} <= :right
            """)

            return pd.read_sql(query, conn, params={"left": node[0], "right": node[1]})
