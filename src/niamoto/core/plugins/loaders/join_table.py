"""
Plugin for loading data using join tables.
"""

from typing import Dict, Any, Literal, Optional
from pydantic import field_validator, Field, ConfigDict

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.common.exceptions import DatabaseError, DatabaseQueryError
from niamoto.core.imports.registry import EntityRegistry


class JoinTableParams(BasePluginParams):
    """Parameters for join table loader"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Load data using join tables to link data sources",
            "examples": [
                {
                    "data": "occurrences",
                    "grouping": "plots",
                    "key": "id_plot",
                    "join_table": "custom_links",
                    "keys": {"source": "id_occurrence", "reference": "id_plot"},
                }
            ],
        }
    )

    data: Optional[str] = Field(
        default=None,
        description="Main table name",
        json_schema_extra={"ui:widget": "text"},
    )
    grouping: Optional[str] = Field(
        default=None,
        description="Reference table field",
        json_schema_extra={"ui:widget": "text"},
    )
    key: str = Field(
        ...,
        description="Key in the reference table",
        json_schema_extra={"ui:widget": "field-select"},
    )
    join_table: str = Field(
        ..., description="Join table name", json_schema_extra={"ui:widget": "text"}
    )
    keys: Dict[str, str] = Field(
        ...,
        description="Keys for the join operation",
        json_schema_extra={
            "ui:widget": "object",
            "ui:options": {
                "properties": {
                    "source": {
                        "type": "string",
                        "title": "Source key",
                        "description": "Key in join table linking to main table",
                    },
                    "reference": {
                        "type": "string",
                        "title": "Reference key",
                        "description": "Key in join table linking to reference",
                    },
                }
            },
        },
    )

    @field_validator("keys")
    @classmethod
    def validate_keys(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate that all required keys are present"""
        required = {"source", "reference"}
        if not all(k in v for k in required):
            raise ValueError(f"Missing required keys: {required - v.keys()}")
        return v


class JoinTableConfig(PluginConfig):
    """Configuration for join table loader"""

    plugin: Literal["join_table"] = "join_table"
    params: JoinTableParams


@register("join_table", PluginType.LOADER)
class JoinTableLoader(LoaderPlugin):
    """Loader using join tables"""

    config_model = JoinTableConfig

    def __init__(self, db, registry=None):
        super().__init__(db, registry)
        # Use registry from parent if provided, otherwise create new instance
        if not self.registry:
            self.registry = EntityRegistry(db)

    def validate_config(self, config: Dict[str, Any]) -> JoinTableConfig:
        """Validate plugin configuration."""
        # Extract params if they exist in the config
        if "params" not in config:
            # For backward compatibility, build params from top-level fields
            params = {k: v for k, v in config.items() if k != "plugin"}
            config = {"plugin": "join_table", "params": params}
        return self.config_model(**config)

    def _check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists using database helpers."""
        try:
            if not self.db.has_table(table_name):
                return False
            columns = self.db.get_table_columns(table_name)
            return len(columns) > 0
        except Exception as e:
            raise DatabaseError(f"Error checking table {table_name}: {str(e)}") from e

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        """Load data by traversing an intermediate join table.

        The configuration should specify the source table, the join table, and the
        mapping of key fields that relate the join table to both the source and
        reference tables.

        Example
        -------
        .. code-block:: yaml

            plugin: join_table
            params:
              data: occurrences
              grouping: plots
              key: id_plot
              join_table: custom_links
              keys:
                source: id_occurrence
                reference: id_plot
        """

        validated_config = self.validate_config(config)
        params = validated_config.params

        main_table = params.data
        if not main_table:
            raise ValueError(f"No main table specified in config: {config}")

        physical_main = self._resolve_table_name(main_table)
        physical_join = self._resolve_table_name(params.join_table)

        # Vérifier l'existence des tables
        if not self._check_table_exists(physical_main):
            raise DatabaseError(f"Main table '{physical_main}' does not exist")
        if not self._check_table_exists(physical_join):
            raise DatabaseError(f"Join table '{physical_join}' does not exist")

        query = f"""
            SELECT m.*
            FROM {physical_main} m
            JOIN {physical_join} j
              ON m.id = j.{params.keys["source"]}
            WHERE j.{params.keys["reference"]} = :id
        """

        with self.db.engine.connect() as conn:
            return pd.read_sql(query, conn, params={"id": group_id})

    def _resolve_table_name(self, logical_name: str) -> str:
        try:
            metadata = self.registry.get(logical_name)
            table_name = getattr(metadata, "table_name", None)
            if not table_name:
                return logical_name
            return table_name
        except DatabaseQueryError:
            return logical_name
