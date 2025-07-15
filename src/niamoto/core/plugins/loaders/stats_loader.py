"""
Plugin for loading statistics from various sources.
"""

from typing import Dict, Any, Literal
import pandas as pd
from sqlalchemy import text
import os
import logging

from niamoto.common.config import Config
from niamoto.common.exceptions import DataLoadError
from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from pydantic import ConfigDict


class StatsLoaderConfig(PluginConfig):
    """Configuration for statistics loader plugin."""

    model_config = ConfigDict(
        title="Statistics Loader Configuration",
        description="Configuration for loading statistics from various sources",
    )

    plugin: Literal["stats_loader"]
    key: str = "id"


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

    def __init__(self, db):
        """Initialize the loader with database connection."""
        super().__init__(db)
        self.config = Config()
        self.imports_config = self.config.imports
        self.logger = logging.getLogger(__name__)

    def validate_config(self, config: Dict[str, Any]) -> StatsLoaderConfig:
        """Validate plugin configuration."""
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
        # We always need to look up the shape_id (or equivalent) from the reference table
        grouping_table = config.get("grouping", "")
        group_name = grouping_table.replace("_ref", "")  # e.g., "shape_ref" -> "shape"
        lookup_field = f"{group_name}_id"  # e.g., "shape_id"

        query = text(f"""
            SELECT {lookup_field} FROM {config["grouping"]} WHERE id = :group_id
        """)

        with self.db.engine.connect() as conn:
            result = conn.execute(query, {"group_id": group_id}).fetchone()
            if not result:
                return pd.DataFrame()

            actual_id = result[0]

        # Filter by the actual ID value
        # Use 'key' from config as the CSV column name
        id_field = config.get("key", "id")

        # Convert both to same type for comparison
        # If actual_id is a string that represents a number, convert to int
        if isinstance(actual_id, str) and actual_id.isdigit():
            actual_id = int(actual_id)

        # Ensure proper type matching
        try:
            # If the CSV column is numeric, convert actual_id to the same type
            if pd.api.types.is_numeric_dtype(data[id_field]):
                actual_id = pd.to_numeric(actual_id)
            else:
                # If CSV column is string, convert actual_id to string
                actual_id = str(actual_id)
        except (ValueError, TypeError):
            pass

        filtered_data = data[data[id_field] == actual_id]
        return filtered_data

    def _load_from_database(
        self, config: Dict[str, Any], group_id: int
    ) -> pd.DataFrame:
        """Load data from the database."""
        query = text(f"""
            SELECT m.*
            FROM {config["data"]} m
            JOIN {config["grouping"]} ref ON m.{config["key"]} = ref.id
            WHERE ref.id = :group_id
        """)

        with self.db.engine.connect() as conn:
            return pd.read_sql(query, conn, params={"group_id": group_id})

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
                return self._load_from_csv(source_config, group_id)
            else:
                # Otherwise, assume data is in database
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
