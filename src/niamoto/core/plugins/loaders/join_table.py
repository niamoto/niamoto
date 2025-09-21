"""
Plugin for loading data using join tables.
"""

from typing import Dict, Any, Literal, Optional
from pydantic import field_validator, Field, ConfigDict

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.common.exceptions import DatabaseError


class JoinTableParams(BasePluginParams):
    """Parameters for join table loader"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Load data using join tables to link data sources",
            "examples": [
                {
                    "data": "occurrences",
                    "grouping": "plot_ref",
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

    def validate_config(self, config: Dict[str, Any]) -> JoinTableConfig:
        """Validate plugin configuration."""
        # Extract params if they exist in the config
        if "params" not in config:
            # For backward compatibility, build params from top-level fields
            params = {k: v for k, v in config.items() if k != "plugin"}
            config = {"plugin": "join_table", "params": params}
        return self.config_model(**config)

    def _check_table_exists(self, table_name: str) -> bool:
        """Vérifie si une table existe dans la base de données."""
        try:
            query = """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name=:table_name
            """
            result = self.db.execute_sql(query, {"table_name": table_name}, fetch=True)
            return bool(result)
        except Exception as e:
            raise DatabaseError(f"Error checking table {table_name}: {str(e)}") from e

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        """Load data using a join table.

        Example config:
        {
            'params': {
                'data': 'occurrences',  # Main table
                'grouping': 'plot_ref',  # Field in main table for grouping
                'key': 'id_plot',  # Key in reference table
                'join_table': 'custom_links',  # Join table
                'keys': {
                    'source': 'id_occurrence',  # Key in join table linking to main table
                    'reference': 'id_plot'  # Key in join table linking to reference
                }
            }
        }
        """

        validated_config = self.validate_config(config)
        params = validated_config.params

        main_table = params.data
        if not main_table:
            raise ValueError(f"No main table specified in config: {config}")

        # Vérifier l'existence des tables
        if not self._check_table_exists(main_table):
            raise DatabaseError(f"Main table '{main_table}' does not exist")
        if not self._check_table_exists(params.join_table):
            raise DatabaseError(f"Join table '{params.join_table}' does not exist")

        query = f"""
            SELECT m.*
            FROM {main_table} m
            JOIN {params.join_table} j
              ON m.id = j.{params.keys["source"]}
            WHERE j.{params.keys["reference"]} = :id
        """

        with self.db.engine.connect() as conn:
            return pd.read_sql(query, conn, params={"id": group_id})
