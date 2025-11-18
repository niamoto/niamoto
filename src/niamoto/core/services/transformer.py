"""
Service for transforming data based on YAML configuration.
"""

from typing import Dict, Any, List, Optional, Callable
import logging
import difflib
import json
import numpy as np
import pandas as pd
from datetime import datetime
from rich.console import Console
from sqlalchemy.sql import quoted_name
from pydantic import ValidationError as PydanticValidationError
from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import (
    ConfigurationError,
    ProcessError,
    ValidationError,
    DataTransformError,
    DatabaseQueryError,
)
from niamoto.common.utils import error_handler
from niamoto.common.utils.emoji import emoji
from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.core.imports.registry import EntityRegistry

# Check if we're in CLI context for progress display
try:
    from niamoto.cli.utils.progress import ProgressManager
    from niamoto.cli.utils.metrics import OperationMetrics, MetricsCollector

    CLI_DETECTED = True
except ImportError:
    CLI_DETECTED = False
    ProgressManager = None
    OperationMetrics = None
    MetricsCollector = None

logger = logging.getLogger(__name__)

# Backward compatibility toggle expected by tests and legacy code
CLI_CONTEXT = CLI_DETECTED


class TransformerService:
    """Service for transforming data based on YAML configuration."""

    def __init__(
        self,
        db_path: str,
        config: Config,
        *,
        enable_cli_integration: bool | None = None,
    ):
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
        self.transform_metrics = None  # Store metrics for CLI access
        if enable_cli_integration is None:
            enable_cli_integration = CLI_CONTEXT
        self.use_cli_integration = bool(enable_cli_integration)
        self._table_buffers: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self._table_flush_modes: Dict[str, bool] = {}

        # Initialize plugin loader and load plugins with cascade resolution
        self.plugin_loader = PluginLoader()

        # Get project path for cascade resolution
        from pathlib import Path

        project_path = Path(Config.get_niamoto_home())

        # Load all plugins (system, user, project) using cascade resolution
        self.plugin_loader.load_plugins_with_cascade(project_path)

        # Registry is used for entity lookups across transform/export
        self.entity_registry = EntityRegistry(self.db)

    @error_handler(log=True, raise_error=True)
    def transform_data(
        self,
        group_by: Optional[str] = None,
        csv_file: Optional[str] = None,
        recreate_table: bool = True,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Transform data according to the configuration.

        Args:
            group_by: Optional filter by group
            csv_file: Optional CSV file to use instead of the database
            recreate_table: Indicates whether to recreate the results table

        Returns:
            Dict[str, Any]: Results of the transformation with metrics data

        Raises:
            ConfigurationError: If the configuration is invalid
            ProcessError: If the transformation fails
        """
        self._table_buffers = {}
        self._table_flush_modes = {}
        # Initialize metrics collection
        if self.use_cli_integration and OperationMetrics:
            self.transform_metrics = OperationMetrics("transform")

        # Initialize results collection
        results = {}

        # Filter configurations
        configs = self._filter_configs(group_by)

        try:
            if self.use_cli_integration and ProgressManager:
                # Use unified progress manager when in CLI context
                progress_manager = ProgressManager(self.console)
                with progress_manager.progress_context() as pm:
                    results = self._process_configs_with_progress(
                        configs, csv_file, recreate_table, pm, progress_callback
                    )
            else:
                # Fallback to simple processing without progress bars
                results = self._process_configs_simple(
                    configs, csv_file, recreate_table, progress_callback
                )
        except Exception as e:
            if self.transform_metrics:
                self.transform_metrics.add_error(str(e))
            raise
        finally:
            try:
                for group_name in list(self._table_buffers.keys()):
                    recreate = self._table_flush_modes.get(group_name, True)
                    self._flush_group_table(group_name, recreate)
                if getattr(self.db, "is_duckdb", False):
                    logger.info("Running DuckDB checkpoint after transformations")
                    self.db.optimize_database()
            finally:
                if self.transform_metrics:
                    self.transform_metrics.finish()

        return results

    def _process_configs_with_progress(
        self,
        configs,
        csv_file,
        recreate_table,
        progress_manager,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """Process configurations with progress display using ProgressManager only."""
        results = {}

        for group_config in configs:
            # Validate the configuration
            self.validate_configuration(group_config)

            # Retrieve group IDs and widgets
            group_ids = self._get_group_ids(group_config)
            widgets_config = group_config.get("widgets_data", {})
            group_by_name = group_config.get("group_by", "unknown")

            # Calculate the total number of operations
            total_ops = len(group_ids) * len(widgets_config)

            # Add progress task with unique name
            import time

            task_name = f"transform_{group_by_name}_{int(time.time())}"
            progress_manager.add_task(
                task_name, f"Processing {group_by_name} data", total=total_ops
            )

            # Create or update the table
            self._create_group_table(group_by_name, widgets_config, recreate_table)

            # Initialize metrics for this group
            if self.transform_metrics:
                self.transform_metrics.add_metric(
                    f"{group_by_name}_items", len(group_ids)
                )
                self.transform_metrics.add_metric(
                    f"{group_by_name}_widgets", len(widgets_config)
                )

            widgets_generated = 0

            # Initialize results for this group
            results[group_by_name] = {
                "total_items": len(group_ids),
                "widgets": {},
                "start_time": progress_manager._start_time,
            }

            # Process each group
            for group_id in group_ids:
                # Retrieve group data
                group_data = self._get_group_data(group_config, csv_file, group_id)

                # Process each widget
                for widget_name, widget_config in widgets_config.items():
                    # Update description for current item being processed
                    progress_manager.update_task(
                        task_name,
                        advance=0,
                        description=f"[green] Processing {group_by_name} {group_id}",
                    )

                    try:
                        # Load the transformation plugin
                        transformer = PluginRegistry.get_plugin(
                            widget_config["plugin"], PluginType.TRANSFORMER
                        )(self.db, registry=self.entity_registry)

                        # Transform the data
                        config = {
                            "plugin": widget_config["plugin"],
                            "params": {
                                "source": widget_config.get("source"),
                                "field": widget_config.get("field"),
                                **widget_config.get("params", {}),
                            },
                            "group_id": group_id,
                            "available_sources": list(
                                group_data.keys()
                            ),  # Inform plugin about available sources
                        }

                        # Smart source selection
                        # 1. If plugin requests a specific source in params, use it
                        # 2. If only one source exists, pass it directly
                        # 3. Otherwise, pass all sources to the plugin
                        source_requested = widget_config.get("params", {}).get("source")

                        if source_requested and source_requested in group_data:
                            # Plugin explicitly requests a specific source
                            data_to_pass = group_data[source_requested]
                        elif len(group_data) == 1:
                            # Only one source available, pass it directly
                            data_to_pass = list(group_data.values())[0]
                        else:
                            # Multiple sources available, pass all sources
                            # Plugins can access them via config['available_sources']
                            data_to_pass = group_data

                        self._validate_plugin_configuration(
                            transformer, config, widget_config["plugin"]
                        )

                        widget_results = transformer.transform(data_to_pass, config)

                        # Save the results
                        if widget_results:
                            self._save_widget_results(
                                group_by=group_by_name,
                                group_id=group_id,
                                results={widget_name: widget_results},
                            )
                            widgets_generated += 1

                            # Track widget results
                            if widget_name not in results[group_by_name]["widgets"]:
                                results[group_by_name]["widgets"][widget_name] = 0
                            results[group_by_name]["widgets"][widget_name] += 1
                    except Exception as e:
                        # Log the error but continue processing other widgets
                        error_msg = f"Error processing widget '{widget_name}' for {group_by_name} {group_id}: {str(e)}"
                        # Only display in progress manager if it's not an expected empty data case
                        if "No data found" not in str(e):
                            progress_manager.add_warning(error_msg)
                            if self.transform_metrics:
                                self.transform_metrics.add_warning(error_msg)

                    # Update progress
                    progress_manager.update_task(task_name, advance=1)
                    if progress_callback:
                        progress_callback(
                            {
                                "group": group_by_name,
                                "widget": widget_name,
                                "processed": None,
                                "total": None,
                            }
                        )
            self._flush_group_table(group_by_name, recreate_table)

            # Update final widget count for this group
            if self.transform_metrics:
                self.transform_metrics.add_metric(
                    f"{group_by_name}_widgets_generated", widgets_generated
                )

            # Update results with final metrics
            results[group_by_name]["widgets_generated"] = widgets_generated
            results[group_by_name]["end_time"] = (
                datetime.now() if hasattr(progress_manager, "_start_time") else None
            )

            progress_manager.complete_task(
                task_name, f"{group_by_name} transformation completed"
            )

        return results

    def _process_configs_simple(
        self,
        configs,
        csv_file,
        recreate_table,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """Process configurations without progress display (fallback)."""
        results = {}
        start_time = datetime.now()

        total_ops = 0
        try:
            for group_config in configs:
                group_ids = self._get_group_ids(group_config)
                widgets_config = group_config.get("widgets_data", {})
                total_ops += len(group_ids) * max(len(widgets_config), 1)
        except Exception:
            total_ops = 0

        processed_ops = 0

        for group_config in configs:
            # Validate the configuration
            self.validate_configuration(group_config)

            # Retrieve group IDs and widgets
            group_ids = self._get_group_ids(group_config)
            widgets_config = group_config.get("widgets_data", {})
            group_by_name = group_config.get("group_by", "unknown")

            # Create or update the table
            self._create_group_table(group_by_name, widgets_config, recreate_table)

            # Initialize results for this group
            widgets_generated = 0
            results[group_by_name] = {
                "total_items": len(group_ids),
                "widgets": {},
                "start_time": start_time,
            }

            # Process each group
            for group_id in group_ids:
                # Retrieve group data
                group_data = self._get_group_data(group_config, csv_file, group_id)

                # Process each widget
                for widget_name, widget_config in widgets_config.items():
                    try:
                        # Load the transformation plugin
                        transformer = PluginRegistry.get_plugin(
                            widget_config["plugin"], PluginType.TRANSFORMER
                        )(self.db, registry=self.entity_registry)

                        # Transform the data
                        config = {
                            "plugin": widget_config["plugin"],
                            "params": {
                                "source": widget_config.get("source"),
                                "field": widget_config.get("field"),
                                **widget_config.get("params", {}),
                            },
                            "group_id": group_id,
                            "available_sources": list(
                                group_data.keys()
                            ),  # Inform plugin about available sources
                        }

                        # Smart source selection
                        # 1. If plugin requests a specific source in params, use it
                        # 2. If only one source exists, pass it directly
                        # 3. Otherwise, pass all sources to the plugin
                        source_requested = widget_config.get("params", {}).get("source")

                        if source_requested and source_requested in group_data:
                            # Plugin explicitly requests a specific source
                            data_to_pass = group_data[source_requested]
                        elif len(group_data) == 1:
                            # Only one source available, pass it directly
                            data_to_pass = list(group_data.values())[0]
                        else:
                            # Multiple sources available, pass all sources
                            # Plugins can access them via config['available_sources']
                            data_to_pass = group_data

                        self._validate_plugin_configuration(
                            transformer, config, widget_config["plugin"]
                        )

                        widget_results = transformer.transform(data_to_pass, config)

                        # Save the results
                        if widget_results:
                            self._save_widget_results(
                                group_by=group_by_name,
                                group_id=group_id,
                                results={widget_name: widget_results},
                            )
                            widgets_generated += 1

                            # Track widget results
                            if widget_name not in results[group_by_name]["widgets"]:
                                results[group_by_name]["widgets"][widget_name] = 0
                            results[group_by_name]["widgets"][widget_name] += 1
                    except Exception as e:
                        # Log the error but continue processing other widgets
                        error_msg = f"Error processing widget '{widget_name}' for {group_by_name} {group_id}: {str(e)}"
                        # Only log if it's not an expected empty data case
                        if "No data found" not in str(e):
                            logger.warning(error_msg)
                        # Only show in console if it's not an expected empty data case
                        if not (
                            isinstance(e, DataTransformError)
                            and "No data found" in str(e)
                        ):
                            self.console.print(
                                f"[yellow]{emoji('⚠', '[!]')} {error_msg}[/yellow]"
                            )

                    processed_ops += 1
                    if progress_callback and total_ops:
                        progress_callback(
                            {
                                "group": group_by_name,
                                "widget": widget_name,
                                "processed": processed_ops,
                                "total": total_ops,
                            }
                        )
            self._flush_group_table(group_by_name, recreate_table)

            # Update results with final metrics
            results[group_by_name]["widgets_generated"] = widgets_generated
            results[group_by_name]["end_time"] = datetime.now()

        return results

    def _filter_configs(self, group_by: Optional[str]) -> List[Dict[str, Any]]:
        """Filter configurations by group, attempting various matching strategies."""
        if not self.transforms_config:
            raise ConfigurationError(
                "transforms",
                "No transforms configuration found",
                details={"file": "transform.yml"},
            )

        if not group_by:
            return self.transforms_config

        available_groups = [
            config.get("group_by")
            for config in self.transforms_config
            if config.get("group_by")
        ]
        filtered = []

        # Single pass through configurations with prioritized checks
        for config in self.transforms_config:
            config_group = config.get("group_by")
            if not config_group:
                continue

            # Exact match
            if config_group == group_by:
                filtered.append(config)
                break
            # Case-insensitive match
            elif config_group.lower() == group_by.lower():
                filtered.append(config)
                self.console.print(
                    f"[yellow]Using group '{config_group}' instead of '{group_by}'[/yellow]"
                )
                break
            # Singular/plural match
            elif group_by.endswith("s") and config_group == group_by[:-1]:
                filtered.append(config)
                self.console.print(
                    f"[yellow]Using singular form '{config_group}' instead of '{group_by}'[/yellow]"
                )
                break
            elif not group_by.endswith("s") and config_group == f"{group_by}s":
                filtered.append(config)
                self.console.print(
                    f"[yellow]Using plural form '{config_group}' instead of '{group_by}'[/yellow]"
                )
                break

        # If no match, raise an error with a suggestion
        if not filtered:
            suggestion = ""
            if available_groups:
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

    def _resolve_table_name(self, logical_name: str) -> str:
        """Return physical table name using the entity registry if available."""

        try:
            metadata = self.entity_registry.get(logical_name)
            return metadata.table_name
        except (DatabaseQueryError, AttributeError, KeyError) as exc:
            logger.debug(
                "Falling back to logical table name '%s' (registry lookup failed: %s)",
                logical_name,
                exc,
            )
            return logical_name

    def _validate_plugin_configuration(
        self, transformer: Any, config: Dict[str, Any], plugin_name: str
    ) -> None:
        """Validate plugin configuration before execution."""

        try:
            if hasattr(transformer, "validate_config"):
                transformer.validate_config(config)
                return

            config_model = getattr(transformer, "config_model", None)
            if config_model is not None:
                config_model(**config)
        except PydanticValidationError as exc:
            raise DataTransformError(
                f"Invalid parameters for transformer '{plugin_name}'",
                details={"errors": exc.errors()},
            ) from exc
        except Exception as exc:
            raise DataTransformError(
                f"Invalid parameters for transformer '{plugin_name}'",
                details={"error": str(exc)},
            ) from exc

    def validate_configuration(self, config: Dict[str, Any]) -> None:
        """
        Validate transformation configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValidationError: If configuration is invalid
        """
        self._validate_sources_config(config)

    def _validate_sources_config(self, config: Dict[str, Any]) -> None:
        """Validate sources configuration list."""
        # Validate sources list exists
        sources = config.get("sources", [])
        if not sources:
            raise ConfigurationError(
                "sources",
                "Missing or empty sources configuration",
                details={"help": "At least one source must be defined"},
            )

        if not isinstance(sources, list):
            raise ConfigurationError(
                "sources",
                "Sources must be a list",
                details={"type": type(sources).__name__},
            )

        # Validate each source
        source_names = set()
        for idx, source_config in enumerate(sources):
            # Check for required fields
            required_fields = ["name", "data", "grouping", "relation"]
            missing = [field for field in required_fields if field not in source_config]
            if missing:
                raise ConfigurationError(
                    f"sources[{idx}]",
                    f"Missing required fields in source at index {idx}",
                    details={"missing": missing},
                )

            # Check for duplicate source names
            source_name = source_config["name"]
            if source_name in source_names:
                raise ConfigurationError(
                    f"sources[{idx}].name",
                    f"Duplicate source name '{source_name}'",
                    details={"name": source_name},
                )
            source_names.add(source_name)

            # Validate relation
            relation = source_config["relation"]
            if (
                "plugin" not in relation and "type" not in relation
            ) or "key" not in relation:
                raise ConfigurationError(
                    f"sources[{idx}].relation",
                    f"Missing required relation fields in source '{source_name}'",
                    details={"required": ["plugin or type", "key"]},
                )

    def _get_group_ids(self, group_config: Dict[str, Any]) -> List[int]:
        """Get all group IDs to process."""
        # Get grouping table from first source (they should all have the same grouping)
        sources = group_config.get("sources", [])
        if not sources:
            raise DataTransformError("No sources configured")

        grouping_table = sources[0]["grouping"]
        resolved_table = self._resolve_table_name(grouping_table)

        # Get the ID field name from entity metadata
        id_field = "id"  # Default
        try:
            metadata = self.entity_registry.get(grouping_table)
            id_field = metadata.config.get("schema", {}).get("id_field", "id")
        except (DatabaseQueryError, AttributeError, KeyError) as exc:
            logger.debug(
                "Falling back to default id field for grouping '%s': %s",
                grouping_table,
                exc,
            )

        # Validate identifier names to prevent SQL injection
        if not resolved_table.replace("_", "").replace(".", "").isalnum():
            raise DataTransformError(
                f"Invalid table name: {resolved_table}",
                details={"table": resolved_table},
            )
        if not id_field.replace("_", "").isalnum():
            raise DataTransformError(
                f"Invalid field name: {id_field}",
                details={"field": id_field},
            )

        quoted_table = str(quoted_name(resolved_table, quote=True))
        quoted_column = str(quoted_name(id_field, quote=True))

        query = f"""
            SELECT DISTINCT {quoted_column}
            FROM {quoted_table}
            ORDER BY {quoted_column}
        """

        try:
            rows = self.db.execute_sql(query, fetch_all=True)
            return [row[0] for row in rows]
        except Exception as e:
            raise DataTransformError(
                "Failed to get group IDs",
                details={
                    "error": str(e),
                    "table": resolved_table,
                    "id_field": id_field,
                    "query": query,
                },
            ) from e

    def _get_group_data(
        self, group_config: Dict[str, Any], csv_file: Optional[str], group_id: int
    ) -> Dict[str, pd.DataFrame]:
        """Get group data from all configured sources.

        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping source names to their data.
                Each source name corresponds to a configured source.
                The grouping table (e.g., 'taxonomy', 'plots', 'shapes') is always included.
        """
        if csv_file:
            # For CSV file, return with generic name
            return {"csv_data": pd.read_csv(csv_file)}

        data_sources = {}
        sources = group_config.get("sources", [])

        # Process each source
        for source_config in sources:
            source_name = source_config["name"]
            relation_config = source_config["relation"]
            plugin_name = relation_config.get("plugin")

            try:
                plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.LOADER)
                loader = plugin_class(self.db, registry=self.entity_registry)
            except Exception as e:
                raise DataTransformError(
                    f"Failed to get loader for source '{source_name}'",
                    details={"error": str(e)},
                ) from e

            # Load data for this source
            # Resolve table names through entity registry before passing to loader
            resolved_data = self._resolve_table_name(source_config["data"])
            resolved_grouping = self._resolve_table_name(source_config["grouping"])

            # Pass both logical and resolved names to allow plugins to use either
            data_sources[source_name] = loader.load_data(
                group_id,
                {
                    "data": resolved_data,
                    "grouping": resolved_grouping,
                    "logical_data": source_config["data"],
                    "logical_grouping": source_config[
                        "grouping"
                    ],  # Keep original logical name
                    **source_config["relation"],
                },
            )

        return data_sources

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

            # Use 'id' as primary key to match the entity table's id field
            # This allows transformations for all hierarchy levels (families, genera, species)
            # not just those with external IDs (e.g., taxonomy_id)
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {group_by} (
                {group_by}_id BIGINT PRIMARY KEY,
                {", ".join(columns)}
            )
            """

            self.db.execute_sql(create_table_sql)

            # Create indexes on the dynamically created transform table
            # Index the primary key and any common columns
            self.db.create_indexes_for_table(group_by)
            self._table_flush_modes[group_by] = recreate_table

        except Exception as e:
            raise DataTransformError(
                f"Failed to create table for group {group_by}",
                details={"error": str(e)},
            ) from e

    def _save_widget_results(
        self, group_by: str, group_id: int, results: Dict[str, Any]
    ) -> None:
        """Buffer widget results for bulk persistence."""
        if not results:
            raise ValidationError(
                "results",
                "No results to save",
                details={"group_by": group_by, "group_id": group_id},
            )

        columns = list(results.keys())
        if not columns:
            raise ValidationError(
                "results",
                "No columns to update",
                details={"group_by": group_by, "group_id": group_id},
            )

        buffer = self._table_buffers.setdefault(group_by, {})
        row = buffer.setdefault(group_id, {})

        try:

            def convert_numpy(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.bool_):
                    return bool(obj)
                if isinstance(obj, bool):
                    return obj
                if isinstance(obj, np.ndarray):
                    return [convert_numpy(x) for x in obj.tolist()]
                if isinstance(obj, list):
                    return [convert_numpy(x) for x in obj]
                if isinstance(obj, dict):
                    return {k: convert_numpy(v) for k, v in obj.items()}
                return obj

            pending_updates: Dict[str, Any] = {}
            for col in columns:
                val = results[col]
                try:
                    if isinstance(val, (dict, list)):
                        converted = convert_numpy(val)
                        pending_updates[col] = json.dumps(converted, ensure_ascii=False)
                    elif val is None:
                        pending_updates[col] = None
                    elif hasattr(val, "dtype") and np.issubdtype(val.dtype, np.number):
                        pending_updates[col] = val.item()
                    else:
                        pending_updates[col] = str(val)
                except Exception as exc:
                    raise DataTransformError(
                        f"Failed to encode results for group {group_id}: {str(exc)}",
                        details={"group_id": group_id, "error": str(exc)},
                    ) from exc
            row.update(pending_updates)

        except DataTransformError:
            if group_id in buffer and not buffer[group_id]:
                buffer.pop(group_id, None)
            if group_by in self._table_buffers and not self._table_buffers[group_by]:
                self._table_buffers.pop(group_by, None)
            raise
        except Exception as e:
            raise ProcessError(
                f"Unexpected error while buffering results for group {group_id}: {str(e)}",
                details={"group_by": group_by, "group_id": group_id, "error": str(e)},
            ) from e

    def _flush_group_table(self, group_by: str, recreate_table: bool) -> None:
        """Flush buffered rows into the database using batch operations."""
        buffer = self._table_buffers.pop(group_by, None)
        if not buffer:
            return
        self._table_flush_modes.pop(group_by, None)

        id_column = f"{group_by}_id"
        rows: List[Dict[str, Any]] = []
        for entity_id, values in buffer.items():
            row = {id_column: entity_id}
            row.update(values)
            rows.append(row)

        if not rows:
            return

        df = pd.DataFrame(rows)
        if df.empty:
            return

        ordered_columns = [id_column] + [col for col in df.columns if col != id_column]
        df = df[ordered_columns]

        if recreate_table:
            df.to_sql(group_by, self.db.engine, if_exists="append", index=False)
            return

        staging_table = f"{group_by}__staging"
        df.to_sql(staging_table, self.db.engine, if_exists="replace", index=False)

        non_id_columns = [col for col in ordered_columns if col != id_column]
        columns_sql = ", ".join(ordered_columns)
        if non_id_columns:
            update_clause = ", ".join(
                f"{col} = excluded.{col}" for col in non_id_columns
            )
            insert_sql = f"""
                INSERT INTO {group_by} ({columns_sql})
                SELECT {columns_sql} FROM {staging_table}
                ON CONFLICT ({id_column})
                DO UPDATE SET {update_clause}
            """
        else:
            insert_sql = f"""
                INSERT INTO {group_by} ({id_column})
                SELECT {id_column} FROM {staging_table}
                ON CONFLICT ({id_column}) DO NOTHING
            """

        try:
            self.db.execute_sql(insert_sql)
        finally:
            self.db.execute_sql(f"DROP TABLE IF EXISTS {staging_table}")
