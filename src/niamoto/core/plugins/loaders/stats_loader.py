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
        self, source_config: Dict[str, Any], group_id: int
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

        # Filter by group_id
        id_field = source_config.get("identifier", "id")
        return data[data[id_field] == group_id]

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
                - data: Source key in imports.yml (e.g. "shape_stats")
                - grouping: Table name for grouping
                - key: ID field name for filtering

        Returns:
            DataFrame containing the loaded data

        Raises:
            DataLoadError: If data loading fails
        """
        try:
            self.validate_config(config)

            # Get source configuration from imports.yml
            source = config.get("data")
            source_config = self.imports_config.get(source)

            if not source_config:
                raise DataLoadError(
                    f"Source {source} not found in imports config",
                    details={"source": source},
                )

            # Choose loading method based on source type
            if source_config.get("type") == "csv":
                return self._load_from_csv(source_config, group_id)
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
