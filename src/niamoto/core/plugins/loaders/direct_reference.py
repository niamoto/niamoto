"""
Plugin for loading data using direct references between tables.
"""

from typing import Dict, Any, Literal, Optional

import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.common.exceptions import DatabaseError


class DirectReferenceConfig(PluginConfig):
    """Configuration for direct reference loader"""

    plugin: Literal["direct_reference"]
    data: Optional[str] = None  # Main table
    grouping: Optional[str] = None  # Reference table
    key: str  # Foreign key field in main table


@register("direct_reference", PluginType.LOADER)
class DirectReferenceLoader(LoaderPlugin):
    """Loader using direct references between tables"""

    config_model = DirectReferenceConfig

    def validate_config(self, config: Dict[str, Any]) -> DirectReferenceConfig:
        """Validate plugin configuration."""
        return self.config_model(**config)

    def _extract_value(self, result):
        """Helper to extract values from different result types."""
        if result is None:
            return None
        if isinstance(result, (list, tuple)):
            if len(result) == 0:
                return None
            if isinstance(result[0], (list, tuple)):
                return result[0][0] if len(result[0]) > 0 else None
            return result[0]
        if hasattr(result, "__getitem__"):  # For Row objects
            try:
                return result[0]
            except (IndexError, TypeError):
                return None
        return result

    def _get_table_columns(self, table_name: str) -> list:
        """Get list of columns for a table using a SELECT query."""
        try:
            query = f"SELECT * FROM {table_name} LIMIT 0"
            df = pd.read_sql(query, self.db.engine)
            return df.columns.tolist()
        except Exception as e:
            raise DatabaseError(
                f"Error getting table columns for {table_name}: {str(e)}"
            ) from e

    def _check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            query = """
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table' AND name=:table_name
            """
            result = self.db.execute_sql(query, {"table_name": table_name}, fetch=True)
            count = self._extract_value(result)
            exists = bool(count and int(count) > 0)

            if exists:
                columns = self._get_table_columns(table_name)
                return len(columns) > 0
            return False
        except Exception as e:
            raise DatabaseError(f"Error checking table {table_name}: {str(e)}") from e

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        """Load data using direct reference.

        Example config:
        {
            'data': 'occurrences',  # Main table
            'grouping': 'plot_ref',  # Reference table
            'plugin': 'direct_reference',
            'key': 'plot_ref_id'  # Foreign key in main table
        }
        """
        validated_config = self.validate_config(config)
        main_table = validated_config.data
        ref_table = validated_config.grouping
        key_field = validated_config.key

        if not main_table:
            raise ValueError(f"No main table specified in config: {config}")
        if not ref_table:
            raise ValueError(f"No reference table specified in config: {config}")

        # Check if tables exist
        if not self._check_table_exists(main_table):
            raise DatabaseError(f"Main table '{main_table}' does not exist")
        if not self._check_table_exists(ref_table):
            raise DatabaseError(f"Reference table '{ref_table}' does not exist")

        # Get columns and check for key field
        columns = self._get_table_columns(main_table)
        if key_field not in columns:
            raise DatabaseError(
                f"Key field '{key_field}' not found in table '{main_table}'"
            )

        try:
            query = f"""
                SELECT m.*
                FROM {main_table} m
                WHERE m.{validated_config.key} = :id
            """
            return pd.read_sql(query, self.db.engine, params={"id": group_id})

        except Exception as e:
            raise DatabaseError(f"Error executing query: {str(e)}") from e
