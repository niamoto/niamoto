"""
Plugin for loading data using direct references between tables.
"""

from typing import Dict, Any, Literal, Optional
from pydantic import Field, ConfigDict

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.common.exceptions import DatabaseError, DatabaseQueryError
from niamoto.core.imports.registry import EntityRegistry


class DirectReferenceParams(BasePluginParams):
    """Parameters for direct reference loader"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Load data using direct references between tables",
            "examples": [
                {"data": "occurrences", "grouping": "plots", "key": "plots_id"}
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
        description="Reference table name",
        json_schema_extra={"ui:widget": "text"},
    )
    key: str = Field(
        ...,
        description="Foreign key field in main table",
        json_schema_extra={"ui:widget": "field-select"},
    )


class DirectReferenceConfig(PluginConfig):
    """Configuration for direct reference loader"""

    plugin: Literal["direct_reference"] = "direct_reference"
    params: DirectReferenceParams


@register("direct_reference", PluginType.LOADER)
class DirectReferenceLoader(LoaderPlugin):
    """Loader using direct references between tables"""

    config_model = DirectReferenceConfig

    def __init__(self, db, registry=None):
        super().__init__(db, registry)
        # Use registry from parent if provided, otherwise create new instance
        if not self.registry:
            self.registry = EntityRegistry(db)

    def validate_config(self, config: Dict[str, Any]) -> DirectReferenceConfig:
        """Validate plugin configuration."""
        # Extract params if they exist in the config
        if "params" not in config:
            # For backward compatibility, build params from top-level fields
            params = {k: v for k, v in config.items() if k != "plugin"}
            config = {"plugin": "direct_reference", "params": params}
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
        """Get list of columns for a table using database helper."""
        try:
            return self.db.get_table_columns(table_name)
        except Exception as e:
            raise DatabaseError(
                f"Error getting table columns for {table_name}: {str(e)}"
            ) from e

    def _check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            if not self.db.has_table(table_name):
                return False
            columns = self._get_table_columns(table_name)
            return len(columns) > 0
        except Exception as e:
            raise DatabaseError(f"Error checking table {table_name}: {str(e)}") from e

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        """Load data by following a direct reference between tables.

        The configuration must include a ``params`` mapping that identifies the
        main table, the reference table, and the foreign-key column that links
        them together.

        Example
        -------
        .. code-block:: yaml

            plugin: direct_reference
            params:
              data: occurrences        # Main table
              grouping: plots          # Reference table
              key: plots_id            # Foreign key in main table
        """
        validated_config = self.validate_config(config)
        params = validated_config.params

        main_table = params.data
        ref_table = params.grouping
        key_field = params.key

        if not main_table:
            raise ValueError(f"No main table specified in config: {config}")
        if not ref_table:
            raise ValueError(f"No reference table specified in config: {config}")

        # Check if tables exist
        physical_main = self._resolve_table_name(main_table)
        physical_ref = self._resolve_table_name(ref_table)

        if not self._check_table_exists(physical_main):
            raise DatabaseError(f"Main table '{physical_main}' does not exist")
        if not self._check_table_exists(physical_ref):
            raise DatabaseError(f"Reference table '{physical_ref}' does not exist")

        # Get columns and check for key field
        columns = self._get_table_columns(physical_main)
        if key_field not in columns:
            raise DatabaseError(
                f"Key field '{key_field}' not found in table '{physical_main}'"
            )

        try:
            query = f"""
                SELECT m.*
                FROM {physical_main} m
                WHERE m.{key_field} = :id
            """
            return pd.read_sql(query, self.db.engine, params={"id": group_id})

        except Exception as e:
            raise DatabaseError(f"Error executing query: {str(e)}") from e

    def _resolve_table_name(self, logical_name: str) -> str:
        try:
            metadata = self.registry.get(logical_name)
            return metadata.table_name
        except DatabaseQueryError:
            return logical_name
