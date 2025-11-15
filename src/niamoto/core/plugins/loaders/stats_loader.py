"""
Plugin for loading statistics from various sources.
"""

from typing import Dict, Any, Literal, Optional
import pandas as pd
from sqlalchemy import text
import os
import logging

from niamoto.common.config import Config
from niamoto.common.exceptions import DataLoadError
from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from pydantic import ConfigDict, Field


class StatsLoaderParams(BasePluginParams):
    """Parameters for statistics loader plugin."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Load statistics from various sources (CSV, database, shapefiles)",
            "examples": [
                {"key": "shape_id", "ref_field": "shape_id", "match_field": "id"}
            ],
        }
    )

    key: str = Field(
        default="id",
        description="ID field name in data source",
        json_schema_extra={"ui:widget": "text"},
    )

    ref_field: Optional[str] = Field(
        default=None,
        description="Custom reference field (default: {group}_id)",
        json_schema_extra={"ui:widget": "text"},
    )

    match_field: Optional[str] = Field(
        default=None,
        description="Field to match in CSV (default: same as key)",
        json_schema_extra={"ui:widget": "text"},
    )


class StatsLoaderConfig(PluginConfig):
    """Configuration for statistics loader plugin."""

    plugin: Literal["stats_loader"] = "stats_loader"
    params: StatsLoaderParams


@register("stats_loader", PluginType.LOADER)
class StatsLoader(LoaderPlugin):
    """Plugin for loading statistics from various sources.

    This plugin can load statistics from:
    - Shapefiles with associated statistics
    - CSV files with statistical data
    - Other tabular data sources

    The loader will process the input data and store the statistics in the database
    for further analysis and visualization.
    """

    config_model = StatsLoaderConfig

    def __init__(self, db, registry=None):
        """Initialize the loader with database connection."""
        super().__init__(db, registry)
        self.config = Config()
        # Get typed imports config and convert to dict for compatibility
        try:
            generic_imports = self.config.get_imports_config
            if callable(generic_imports):
                generic_imports = generic_imports()
            self.imports_config = (
                generic_imports.model_dump() if generic_imports else {}
            )
        except Exception:
            self.imports_config = {}
        self.logger = logging.getLogger(__name__)

    def validate_config(self, config: Dict[str, Any]) -> StatsLoaderConfig:
        """Validate plugin configuration."""
        # Extract params if they exist in the config
        if "params" not in config:
            # For backward compatibility, build params from top-level fields
            params = {}
            if "key" in config:
                params["key"] = config["key"]
            if "ref_field" in config:
                params["ref_field"] = config["ref_field"]
            if "match_field" in config:
                params["match_field"] = config["match_field"]
            config = {"plugin": "stats_loader", "params": params}
        return self.config_model(**config)

    def _load_from_csv(
        self, source_config: Dict[str, Any], group_id: int, config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Load data from a CSV file."""
        base_dir = os.path.dirname(self.config.config_dir)
        csv_path = os.path.join(base_dir, source_config["path"])

        if not os.path.exists(csv_path):
            raise DataLoadError(
                "CSV file not found",
                details={
                    "path": csv_path,
                    "base_dir": base_dir,
                    "source_path": source_config["path"],
                },
            )

        # Try first with comma, then with semicolon if it fails
        try:
            data = pd.read_csv(csv_path, encoding="utf-8")
            if (
                len(data.columns) == 1
            ):  # Si toutes les colonnes sont combinées, essayer avec point-virgule
                raise pd.errors.EmptyDataError
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            data = pd.read_csv(csv_path, sep=";", decimal=".", encoding="utf-8")

        # Get the actual value from the reference table
        # We always need to look up the value from the reference table
        grouping_table = config.get("grouping", "")
        logical_grouping = config.get("logical_grouping")

        group_name_source = logical_grouping or grouping_table
        group_name = group_name_source
        if group_name.startswith("entity_"):
            group_name = group_name[len("entity_") :]
        if group_name.startswith("dataset_"):
            group_name = group_name[len("dataset_") :]

        # Get params from validated config
        validated_config = self.validate_config(config)
        params = validated_config.params

        # Allow custom reference field (default to {group}_id)
        ref_field = params.ref_field
        if not ref_field:
            ref_field = f"{group_name}_id"  # e.g., "shape_id"

        # Allow custom match field in CSV (default to key)
        match_field = params.match_field or params.key

        # Get the ID field name from entity metadata
        # Use logical_grouping if provided (entity name), otherwise use grouping (table name)
        entity_name = config.get("logical_grouping", grouping_table)
        id_field = "id"  # Default
        try:
            from niamoto.core.imports.registry import EntityRegistry

            entity_registry = EntityRegistry(self.db)
            metadata = entity_registry.get(entity_name)
            id_field = metadata.config.get("schema", {}).get("id_field", "id")
        except Exception:
            pass

        query = text(f"""
            SELECT {ref_field} FROM {config["grouping"]} WHERE {id_field} = :group_id
        """)

        with self.db.engine.connect() as conn:
            result = conn.execute(query, {"group_id": group_id}).fetchone()
            if not result:
                return pd.DataFrame()

            actual_id = result[0]

        # Filter by the actual value
        # Use match_field to filter the CSV data
        # Convert both to same type for comparison
        # If actual_id is a string that represents a number, convert to int
        if isinstance(actual_id, str) and actual_id.isdigit():
            actual_id = int(actual_id)

        # Ensure proper type matching
        try:
            # If the CSV column is numeric, convert actual_id to the same type
            if pd.api.types.is_numeric_dtype(data[match_field]):
                actual_id = pd.to_numeric(actual_id)
            else:
                # If CSV column is string, convert actual_id to string
                actual_id = str(actual_id)
        except (ValueError, TypeError):
            pass

        filtered_data = data[data[match_field] == actual_id]
        return filtered_data

    def _load_from_database(
        self, config: Dict[str, Any], group_id: int
    ) -> pd.DataFrame:
        """Load data from the database."""
        query = f"""
            SELECT m.*
            FROM {config["data"]} m
            JOIN {config["grouping"]} ref ON m.{config.get("key", "id")} = ref.id
            WHERE ref.id = :group_id
        """

        # Use text() wrapped query with engine directly to avoid pandas warning
        return pd.read_sql(text(query), self.db.engine, params={"group_id": group_id})

    def load_data(self, group_id: int, config: Dict[str, Any]) -> pd.DataFrame:
        """
        Load statistics data for a specific group.

        Args:
            group_id: ID of the group to load data for
            config: Configuration dictionary containing:
                - data: Path to CSV file, table name, or dict with type/path
                - grouping: Table name for grouping
                - key: ID field name in CSV/data source

        Returns:
            DataFrame containing the loaded data

        Raises:
            DataLoadError: If data loading fails
        """
        try:
            self.validate_config(config)

            # Get source configuration
            source = config.get("data")

            # Determine source type and configuration
            if isinstance(source, dict):
                # Explicit configuration with type/path
                source_config = source
            elif isinstance(source, str):
                # Auto-detect type based on string content
                if source.endswith((".csv", ".CSV")):
                    # It's a CSV file path
                    source_config = {"type": "csv", "path": source}
                elif "/" in source or "\\" in source:
                    # Looks like a file path, assume CSV
                    source_config = {"type": "csv", "path": source}
                else:
                    # Check if it's a reference to imports.yml
                    imports_config = self.imports_config.get(source)
                    if imports_config:
                        source_config = imports_config
                    else:
                        # Assume it's a database table name
                        source_config = {"type": "database", "table": source}
            else:
                raise DataLoadError(
                    "Invalid data source configuration",
                    details={"source": source, "type": type(source).__name__},
                )

            # Choose loading method based on source type
            if source_config.get("type") == "csv":
                return self._load_from_csv(source_config, group_id, config)
            else:
                return self._load_from_database(config, group_id)

        except Exception as e:
            self.logger.exception(
                f"Failed to load statistics data for group_id {group_id}: {e}"
            )
            # Include original error details if available
            original_details = getattr(
                e, "details", None
            )  # Get details attribute, default to None
            raise DataLoadError(
                "Failed to load statistics data",
                # Pass details if they exist and are a dict, otherwise empty dict
                details=original_details if isinstance(original_details, dict) else {},
            ) from e
