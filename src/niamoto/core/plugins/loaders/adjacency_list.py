"""Loader for hierarchies stored as adjacency lists.

The plugin relies on recursive CTEs to traverse parent/child relations and can
optionally return all descendants for a given node.
"""

from typing import Dict, Any, Literal
from pydantic import Field, ConfigDict
from sqlalchemy import text
import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.core.imports.registry import EntityRegistry


class AdjacencyListParams(BasePluginParams):
    """Parameters for adjacency list loader"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Load hierarchical data using adjacency list model (parent_id)",
            "examples": [
                {
                    "key": "taxon_id",
                    "parent_field": "parent_id",
                    "include_children": True,
                }
            ],
        }
    )

    key: str = Field(
        ...,
        description="Foreign key field linking data to the hierarchy",
        json_schema_extra={"ui:widget": "text"},
    )

    parent_field: str = Field(
        default="parent_id",
        description="Field containing parent ID reference",
        json_schema_extra={"ui:widget": "text"},
    )

    hierarchy_id_field: str = Field(
        default="id",
        description="Field in hierarchy table to match against (default: 'id', can be 'taxon_id' for external IDs)",
        json_schema_extra={"ui:widget": "text"},
    )

    include_children: bool = Field(
        default=True,
        description="Include all descendants in hierarchy (true) or only direct node (false)",
        json_schema_extra={"ui:widget": "checkbox"},
    )


class AdjacencyListConfig(PluginConfig):
    """Configuration for adjacency list loader"""

    plugin: Literal["adjacency_list"] = "adjacency_list"
    params: AdjacencyListParams


@register("adjacency_list", PluginType.LOADER)
class AdjacencyListLoader(LoaderPlugin):
    """Loader for adjacency list hierarchies.

    This loader replaces the nested set loader for modern hierarchy traversal.
    It uses recursive CTEs to efficiently query hierarchical data.
    """

    config_model = AdjacencyListConfig

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
            return logical_name

    def validate_config(self, config: Dict[str, Any]) -> AdjacencyListConfig:
        """Validate plugin configuration."""
        # Extract params if they exist in the config
        if "params" not in config:
            # For backward compatibility, build params from top-level fields
            params = {}
            if "key" in config:
                params["key"] = config["key"]
            if "parent_field" in config:
                params["parent_field"] = config["parent_field"]
            if "hierarchy_id_field" in config:
                params["hierarchy_id_field"] = config["hierarchy_id_field"]
            if "include_children" in config:
                params["include_children"] = config["include_children"]
            config = {"plugin": "adjacency_list", "params": params}
        return self.config_model(**config)

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        """Load data for a hierarchical group using adjacency list traversal.

        Args:
            group_id: ID of the hierarchy node to load
            config: Loader configuration containing data/grouping tables

        Returns:
            DataFrame with all records belonging to this hierarchy node
        """
        validated_config = self.validate_config(config)
        params = validated_config.params

        # Get the field to use for matching in hierarchy table
        hierarchy_id = params.hierarchy_id_field

        def _validate_identifier(value: str, label: str) -> None:
            if not value:
                raise ValueError(f"{label} cannot be empty")
            sanitized = value.replace("_", "").replace(".", "").isalnum()
            if not sanitized:
                raise ValueError(f"Invalid characters in {label}: {value}")

        def _quote_identifier(value: str) -> str:
            parts = value.split(".")
            quoted_parts = []
            for part in parts:
                escaped = part.replace('"', '""')
                quoted_parts.append(f'"{escaped}"')
            return ".".join(quoted_parts)

        # Resolve entity names to physical table names via EntityRegistry
        resolved_data = self._resolve_table_name(config["data"])
        resolved_grouping = self._resolve_table_name(config["grouping"])

        _validate_identifier(resolved_data, "data table name")
        _validate_identifier(resolved_grouping, "grouping table name")
        _validate_identifier(params.key, "foreign key field")
        _validate_identifier(params.parent_field, "parent field")
        _validate_identifier(hierarchy_id, "hierarchy id field")

        data_table = _quote_identifier(resolved_data)
        grouping_table = _quote_identifier(resolved_grouping)
        key_column = _quote_identifier(params.key)
        parent_column = _quote_identifier(params.parent_field)
        hierarchy_id_column = _quote_identifier(hierarchy_id)
        hierarchy_pk_column = _quote_identifier("id")

        if not params.include_children:
            # Simple case: only load data for this specific node
            query = text(f"""
                SELECT m.*
                FROM {data_table} AS m
                WHERE m.{key_column} = :id
            """)

            with self.db.engine.connect() as conn:
                return pd.read_sql(query, conn, params={"id": group_id})

        # Complex case: load data for this node and all descendants
        # Use recursive CTE to traverse hierarchy

        # DuckDB/SQLite compatible recursive CTE
        query = text(f"""
            WITH RECURSIVE hierarchy AS (
                -- Base case: the target node itself
                SELECT {hierarchy_pk_column} AS id,
                       {hierarchy_id_column} AS match_id,
                       {parent_column} AS parent_value
                FROM {grouping_table}
                WHERE {hierarchy_pk_column} = :id

                UNION ALL

                -- Recursive case: all children
                SELECT t.{hierarchy_pk_column} AS id,
                       t.{hierarchy_id_column} AS match_id,
                       t.{parent_column} AS parent_value
                FROM {grouping_table} AS t
                INNER JOIN hierarchy h ON t.{parent_column} = h.id
            )
            SELECT DISTINCT m.*
            FROM {data_table} AS m
            INNER JOIN hierarchy h ON m.{key_column} = h.match_id
        """)

        with self.db.engine.connect() as conn:
            return pd.read_sql(query, conn, params={"id": group_id})
