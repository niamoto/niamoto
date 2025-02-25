"""
Service for transforming data based on YAML configuration.
"""

import os
from typing import Dict, Any, List, Optional
import logging
import pandas as pd
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import (
    ConfigurationError,
    ProcessError,
    DataTransformError,
)
from niamoto.common.utils import error_handler
from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType

logger = logging.getLogger(__name__)


class TransformerService:
    """Service for transforming data based on YAML configuration."""

    def __init__(self, db_path: str, config: Config):
        """
        Initialize the service.

        Args:
            db_path: Path to database
            config: Configuration object
        """
        self.db = Database(db_path)
        self.config = config
        self.transforms_config = config.get_transforms_config()
        self.console = Console()

        # Initialize plugin loader and load plugins
        self.plugin_loader = PluginLoader()
        self.plugin_loader.load_core_plugins()

        # Load project plugins if any exist
        project_path = os.path.dirname(os.path.dirname(config.config_dir))
        self.plugin_loader.load_project_plugins(project_path)

    @error_handler(log=True, raise_error=True)
    def transform_data(
        self,
        group_by: Optional[str] = None,
        csv_file: Optional[str] = None,
        recreate_table: bool = True,
    ) -> None:
        """
        Transform data according to configuration.

        Args:
            group_by: Optional group filter
            csv_file: Optional CSV file to use instead of database
            recreate_table: Whether to recreate the table for results

        Raises:
            ConfigurationError: If configuration is invalid
            ProcessError: If transformation fails
        """
        try:
            # Filter configuration by group if specified
            configs = self._filter_configs(group_by)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TimeElapsedColumn(),
                console=self.console,
            ) as progress:
                # Process each group configuration
                for group_config in configs:
                    self.validate_configuration(group_config)

                    # Get all group IDs and widgets
                    group_ids = self._get_group_ids(group_config)
                    widgets_config = group_config.get("widgets_data", {})
                    group_by = group_config.get("group_by", "unknown")

                    # Calculate total operations for this group config
                    total_ops = len(group_ids) * len(widgets_config)

                    # Create progress bar for this group config
                    config_task = progress.add_task(
                        f"[cyan]Processing {group_by} data...", total=total_ops
                    )

                    # Create or update table for results
                    self._create_group_table(
                        group_config.get("group_by"),
                        widgets_config,
                        recreate_table,
                    )

                    # Process each group
                    for group_id in group_ids:
                        try:
                            # Update progress description with current group ID
                            progress.update(
                                config_task,
                                description=f"[cyan]Processing {group_by} {group_id}...",
                            )

                            # Get group data
                            group_data = self._get_group_data(
                                group_config, csv_file, group_id
                            )

                            # Process each widget
                            for widget_name, widget_config in widgets_config.items():
                                try:
                                    # Get transformer plugin
                                    transformer = PluginRegistry.get_plugin(
                                        widget_config["plugin"], PluginType.TRANSFORMER
                                    )(self.db)

                                    # Transform data
                                    config = {
                                        "plugin": widget_config["plugin"],
                                        "params": {
                                            "source": widget_config.get("source"),
                                            "field": widget_config.get("field"),
                                            **widget_config.get("params", {}),
                                        },
                                        "group_id": group_id,
                                    }

                                    # Si des paramètres sont dans la racine, les déplacer dans params
                                    param_keys = ["stats", "units", "max_value"]
                                    for key in param_keys:
                                        if key in widget_config:
                                            config["params"][key] = widget_config[key]

                                    results = transformer.transform(group_data, config)

                                    # Save results
                                    if results:
                                        self._save_widget_results(
                                            group_by=group_config["group_by"],
                                            group_id=group_id,
                                            results={widget_name: results},
                                        )

                                except Exception as e:
                                    error_msg = f"Error processing widget {widget_name} for group {group_id}: {str(e)}"
                                    self.console.print(f"[red]{error_msg}[/red]")
                                finally:
                                    progress.advance(config_task)

                        except Exception as e:
                            error_msg = f"Failed to process group {group_id}: {str(e)}"
                            self.console.print(f"[red]{error_msg}[/red]")
                            # Advance for all remaining widgets in case of group error
                            remaining = len(widgets_config)
                            progress.advance(config_task, remaining)

        except Exception as e:
            # Extract useful details from the original error if it's a ConfigurationError
            if isinstance(e, ConfigurationError) and hasattr(e, "details"):
                error_details = e.details.copy() if e.details else {}
                error_details.update({"group": group_by})

                raise ProcessError("Failed to transform data", details=error_details)
            else:
                raise ProcessError(
                    "Failed to transform data",
                    details={"group": group_by, "error": str(e)},
                )

    def _filter_configs(self, group_by: Optional[str]) -> List[Dict[str, Any]]:
        """Filter configurations by group."""
        if not self.transforms_config:
            raise ConfigurationError(
                "transforms",
                "No transforms configuration found",
                details={"file": "transform.yml"},
            )

        if not group_by:
            return self.transforms_config

        # Get available group_by values
        available_groups = [
            config.get("group_by")
            for config in self.transforms_config
            if config.get("group_by")
        ]

        # Check for exact match first
        filtered = [
            config
            for config in self.transforms_config
            if config.get("group_by") == group_by
        ]

        # If no exact match, try case-insensitive match
        if not filtered:
            for config in self.transforms_config:
                if (
                    config.get("group_by")
                    and config.get("group_by").lower() == group_by.lower()
                ):
                    filtered.append(config)
                    correct_group = config.get("group_by")
                    self.console.print(
                        f"[yellow]Using group '{correct_group}' instead of '{group_by}'[/yellow]"
                    )
                    break

        # If still no match, try singular/plural variants
        if not filtered:
            # Try singular form if group_by ends with 's'
            if group_by.endswith("s"):
                singular = group_by[:-1]
                for config in self.transforms_config:
                    if config.get("group_by") == singular:
                        filtered.append(config)
                        self.console.print(
                            f"[yellow]Using singular form '{singular}' instead of '{group_by}'[/yellow]"
                        )
                        break
            # Try plural form if group_by doesn't end with 's'
            else:
                plural = f"{group_by}s"
                for config in self.transforms_config:
                    if config.get("group_by") == plural:
                        filtered.append(config)
                        self.console.print(
                            f"[yellow]Using plural form '{plural}' instead of '{group_by}'[/yellow]"
                        )
                        break

        # If still no match, provide a helpful error message
        if not filtered:
            # Try to find a close match
            suggestion = ""
            if available_groups:
                import difflib

                matches = difflib.get_close_matches(group_by, available_groups, n=1)
                if matches:
                    suggestion = f" Did you mean '{matches[0]}'?"

            raise ConfigurationError(
                "transforms",
                f"No configuration found for group: {group_by}",
                details={
                    "group": group_by,
                    "available_groups": available_groups,
                    "help": f"Available groups are: {', '.join(available_groups)}.{suggestion}",
                },
            )

        return filtered

    def validate_configuration(self, config: Dict[str, Any]) -> None:
        """
        Validate transformation configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValidationError: If configuration is invalid
        """
        self._validate_source_config(config)

    def _validate_source_config(self, config: Dict[str, Any]) -> None:
        """Validate source configuration."""
        source = config.get("source", {})
        required_fields = ["data", "grouping", "relation"]
        missing = [field for field in required_fields if field not in source]
        if missing:
            raise ConfigurationError(
                "source",
                "Missing required source configuration fields",
                details={"missing": missing},
            )

        relation = source["relation"]
        if (
            "plugin" not in relation and "type" not in relation
        ) or "key" not in relation:
            raise ConfigurationError(
                "relation",
                "Missing required relation fields",
                details={"required": ["plugin or type", "key"]},
            )

    def _get_group_ids(self, group_config: Dict[str, Any]) -> List[int]:
        """Get all group IDs to process."""
        grouping_table = group_config["source"]["grouping"]

        query = f"""
            SELECT DISTINCT id
            FROM {grouping_table}
            ORDER BY id
        """

        try:
            result = self.db.execute_sql(query)
            return [row[0] for row in result]
        except Exception as e:
            raise DataTransformError(
                "Failed to get group IDs", details={"error": str(e)}
            )

    def _get_group_data(
        self, group_config: Dict[str, Any], csv_file: Optional[str], group_id: int
    ) -> pd.DataFrame:
        """Get group data."""
        if csv_file:
            group_data = pd.read_csv(csv_file)
        else:
            # Get the appropriate loader plugin
            relation_config = group_config["source"]["relation"]
            plugin_name = relation_config.get("plugin")

            try:
                plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.LOADER)
                loader = plugin_class(self.db)
            except Exception:
                raise

            # Load data using the loader
            group_data = loader.load_data(
                group_id,
                {
                    "data": group_config["source"]["data"],
                    "grouping": group_config["source"]["grouping"],
                    **group_config["source"]["relation"],
                },
            )

        return group_data

    def _create_group_table(
        self, group_by: str, widgets_config: Dict[str, Any], recreate_table: bool = True
    ) -> None:
        """Create or update table for group results."""
        try:
            # Create columns for each widget
            columns = [f"{widget_name} JSON" for widget_name in widgets_config.keys()]

            # Drop table if recreate_table is True
            if recreate_table:
                drop_table_sql = f"""
                DROP TABLE IF EXISTS {group_by}
                """
                self.db.execute_sql(drop_table_sql)

            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {group_by} (
                {group_by}_id INTEGER PRIMARY KEY,
                {", ".join(columns)}
            )
            """

            self.db.execute_sql(create_table_sql)

        except Exception as e:
            raise DataTransformError(
                f"Failed to create table for group {group_by}",
                details={"error": str(e)},
            )

    def _save_widget_results(
        self, group_by: str, group_id: int, results: Dict[str, Any]
    ) -> None:
        """Save widget results to database."""
        try:
            # Prepare column names and values
            columns = list(results.keys())
            values = [results[col] for col in columns]

            # Format values for SQL
            formatted_values = []
            for val in [group_id] + values:
                if val is None:
                    formatted_values.append("NULL")
                elif isinstance(val, (int, float)):
                    formatted_values.append(str(val))
                elif isinstance(val, dict):
                    # Convert dictionary with numpy values
                    import json
                    import numpy as np

                    def convert_numpy(obj):
                        if isinstance(obj, np.integer):
                            return int(obj)
                        elif isinstance(obj, np.floating):
                            return float(obj)
                        elif isinstance(obj, np.ndarray):
                            return [convert_numpy(x) for x in obj.tolist()]
                        elif isinstance(obj, list):
                            return [convert_numpy(x) for x in obj]
                        elif isinstance(obj, dict):
                            return {k: convert_numpy(v) for k, v in obj.items()}
                        return obj

                    converted_dict = {k: convert_numpy(v) for k, v in val.items()}
                    json_str = json.dumps(converted_dict, ensure_ascii=False)
                    formatted_values.append(
                        f"'{json_str.replace(chr(39), chr(39) + chr(39))}'"
                    )
                elif isinstance(val, list):
                    # Convert list with numpy values
                    import json
                    import numpy as np

                    converted_list = [convert_numpy(x) for x in val]
                    json_str = json.dumps(converted_list, ensure_ascii=False)
                    formatted_values.append(
                        f"'{json_str.replace(chr(39), chr(39) + chr(39))}'"
                    )
                elif hasattr(val, "dtype") and np.issubdtype(val.dtype, np.number):
                    # Handle individual numpy numbers
                    formatted_values.append(str(val.item()))
                else:
                    # Escape single quotes in strings
                    str_val = str(val)
                    formatted_values.append(
                        f"'{str_val.replace(chr(39), chr(39) + chr(39))}'"
                    )

            # Build SQL
            sql = f"""
                INSERT INTO {group_by} ({group_by}_id, {", ".join(columns)})
                VALUES ({", ".join(formatted_values)})
                ON CONFLICT ({group_by}_id)
                DO UPDATE SET {", ".join(f"{col} = excluded.{col}" for col in columns)}
            """

            # Execute without parameters
            self.db.execute_sql(sql)

        except Exception as e:
            raise DataTransformError(
                f"Failed to save results for group {group_id}",
                details={"error": str(e)},
            )
