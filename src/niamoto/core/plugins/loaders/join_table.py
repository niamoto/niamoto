"""
Plugin for loading data using join tables.
"""

from typing import Dict, Any, Literal, Optional
from pydantic import field_validator

import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.common.exceptions import DatabaseError


class JoinTableConfig(PluginConfig):
    """Configuration for join table loader"""

    plugin: Literal["join_table"]
    data: Optional[str] = None  # Table principale
    grouping: Optional[str] = None  # Champ de groupement
    key: str  # Clé dans la table de référence
    join_table: str  # Table de jointure
    keys: Dict[str, str]  # Clés pour la jointure

    @field_validator("keys")
    @classmethod
    def validate_keys(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate that all required keys are present"""
        required = {"source", "reference"}
        if not all(k in v for k in required):
            raise ValueError(f"Missing required keys: {required - v.keys()}")
        return v


@register("join_table", PluginType.LOADER)
class JoinTableLoader(LoaderPlugin):
    """Loader using join tables"""

    config_model = JoinTableConfig

    def validate_config(self, config: Dict[str, Any]) -> JoinTableConfig:
        """Validate plugin configuration."""
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
            'data': 'occurrences',  # Main table
            'grouping': 'plot_ref',  # Field in main table for grouping
            'plugin': 'join_table',
            'key': 'id_plot',  # Key in reference table
            'join_table': 'custom_links',  # Join table
            'keys': {
                'source': 'id_occurrence',  # Key in join table linking to main table
                'reference': 'id_plot'  # Key in join table linking to reference
            }
        }
        """

        validated_config = self.validate_config(config)
        main_table = validated_config.data
        if not main_table:
            raise ValueError(f"No main table specified in config: {config}")

        # Vérifier l'existence des tables
        if not self._check_table_exists(main_table):
            raise DatabaseError(f"Main table '{main_table}' does not exist")
        if not self._check_table_exists(validated_config.join_table):
            raise DatabaseError(
                f"Join table '{validated_config.join_table}' does not exist"
            )

        query = f"""
            SELECT m.*
            FROM {main_table} m
            JOIN {validated_config.join_table} j
              ON m.id = j.{validated_config.keys["source"]}
            WHERE j.{validated_config.keys["reference"]} = :id
        """

        return pd.read_sql(query, self.db.engine, params={"id": group_id})
