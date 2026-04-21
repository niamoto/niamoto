"""Service for transforming data based on YAML configuration."""

from typing import Dict, Any, List, Optional, Callable
import logging
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from datetime import datetime
from rich.console import Console
from sqlalchemy import inspect
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
from niamoto.common.transform_config_models import TransformGroupConfig
from niamoto.common.table_resolver import quote_identifier

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
_SAFE_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

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
        project_path = Path(Config.get_niamoto_home())

        # Load all plugins (system, user, project) using cascade resolution
        self.plugin_loader.load_plugins_with_cascade(project_path)

        # Registry is used for entity lookups across transform/export
        self.entity_registry = EntityRegistry(self.db)

    @classmethod
    def for_preview(cls, db: Database, config_dir: str) -> "TransformerService":
        """Lightweight factory for widget preview.

        Properly initialises all fields and loads plugins via cascade,
        but reuses an existing Database connection and skips CLI setup.
        """
        svc = cls.__new__(cls)
        svc.db = db
        svc.config = Config(config_dir, create_default=False)
        svc.transforms_config = svc.config.get_transforms_config()
        svc.console = None
        svc.transform_metrics = None
        svc.use_cli_integration = False
        svc._table_buffers: Dict[str, Dict[int, Dict[str, Any]]] = {}
        svc._table_flush_modes: Dict[str, bool] = {}

        svc.plugin_loader = PluginLoader()
        svc.plugin_loader.load_plugins_with_cascade(Path(config_dir).parent)

        svc.entity_registry = EntityRegistry(db)
        return svc

    def _write_dataframe_to_table(self, df: pd.DataFrame, table_name: str) -> None:
        """Persist a DataFrame without DuckDB reflection-based replace.

        ``pandas.to_sql(..., if_exists="replace")`` can trigger SQLAlchemy
        reflection queries that are incompatible with duckdb-engine on recent
        versions. For DuckDB, drop the table explicitly first, then create it
        with ``if_exists="fail"``.
        """

        if getattr(self.db, "is_duckdb", False):
            quoted_table = self._quote_sql_identifier(table_name)
            self.db.execute_sql(f"DROP TABLE IF EXISTS {quoted_table}")
            df.to_sql(table_name, self.db.engine, if_exists="fail", index=False)
            return

        df.to_sql(table_name, self.db.engine, if_exists="replace", index=False)

    def _quote_sql_identifier(self, name: str) -> str:
        """Return a SQL-safe identifier for dynamic table and column names."""

        if _SAFE_SQL_IDENTIFIER_RE.match(name):
            return name

        try:
            quoted = quote_identifier(self.db, name)
            if isinstance(quoted, str):
                return quoted
        except Exception:
            pass

        escaped = str(name).replace('"', '""')
        return f'"{escaped}"'

    def transform_single_widget(
        self,
        group_config: Dict[str, Any],
        widget_name: str,
        group_id: Any,
    ) -> Any:
        """Transform a single widget for a given entity.

        Replicates the per-widget logic from transform_data() so that
        both the full pipeline and the preview engine share one code path.

        Args:
            group_config: Full group config dict from transform.yml.
            widget_name: Key in ``widgets_data``.
            group_id: The entity ID to process.

        Returns:
            Transformer result (typically a dict).

        Raises:
            DataTransformError: On missing widget, source or transform failure.
        """
        widgets_config = group_config.get("widgets_data", {})
        widget_config = widgets_config.get(widget_name)
        if not widget_config:
            raise DataTransformError(
                f"Widget '{widget_name}' not found in group config",
                details={"available": list(widgets_config.keys())},
            )

        group_by_name = group_config["group_by"]

        # Load data for this entity using real loaders
        group_data = self._get_group_data(group_config, None, group_id)
        return self._execute_widget_transform(
            group_by_name, group_data, group_id, widget_name, widget_config
        )

    def _build_widget_runtime_config(
        self,
        widget_config: Dict[str, Any],
        group_id: Any,
        available_sources: List[str],
    ) -> Dict[str, Any]:
        """Build the runtime configuration passed to a transformer plugin."""

        return {
            "plugin": widget_config["plugin"],
            "params": {
                "source": widget_config.get("source"),
                "field": widget_config.get("field"),
                **widget_config.get("params", {}),
            },
            "group_id": group_id,
            "available_sources": available_sources,
        }

    def _bind_plugin_runtime_config(self, plugin: Any) -> None:
        """Inject the active project config into plugins that opt in."""
        bind_runtime_config = getattr(plugin, "bind_runtime_config", None)
        if callable(bind_runtime_config):
            bind_runtime_config(self.config)

    def _resolve_widget_input(
        self,
        group_by_name: str,
        group_data: Any,
        widget_config: Dict[str, Any],
        group_id: Any,
    ) -> tuple[Any, List[str]]:
        """Resolve the data payload and available sources for one widget execution."""

        available_sources = (
            list(group_data.keys()) if hasattr(group_data, "keys") else []
        )
        source_requested = widget_config.get("params", {}).get("source")

        if isinstance(group_data, dict):
            if source_requested and source_requested not in group_data:
                if source_requested == group_by_name:
                    group_data[source_requested] = self._load_reference_entity(
                        group_by_name, group_id
                    )
                else:
                    group_data[source_requested] = self._load_additional_source(
                        source_requested
                    )
                available_sources = list(group_data.keys())

            if source_requested and source_requested in group_data:
                return group_data[source_requested], available_sources
            if len(group_data) == 1:
                return next(iter(group_data.values())), available_sources
            return group_data, available_sources

        return group_data, available_sources

    def _execute_widget_transform(
        self,
        group_by_name: str,
        group_data: Any,
        group_id: Any,
        widget_name: str,
        widget_config: Dict[str, Any],
    ) -> Any:
        """Execute one widget transformation for a given entity."""

        # Some legacy configs incorrectly persisted export-only navigation widgets
        # in transform.yml. They do not produce per-entity transformed data.
        if widget_config["plugin"] == "hierarchical_nav_widget":
            return None

        transformer = PluginRegistry.get_plugin(
            widget_config["plugin"], PluginType.TRANSFORMER
        )(self.db, registry=self.entity_registry)
        self._bind_plugin_runtime_config(transformer)
        data_to_pass, available_sources = self._resolve_widget_input(
            group_by_name, group_data, widget_config, group_id
        )
        config = self._build_widget_runtime_config(
            widget_config, group_id, available_sources
        )

        self._validate_plugin_configuration(
            transformer, config, widget_config["plugin"]
        )
        return transformer.transform(data_to_pass, config)

    def _compute_entity_results(
        self,
        group_config: Dict[str, Any],
        group_id: Any,
        csv_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compute all widget results for one entity without writing to the DB."""

        widgets_config = group_config.get("widgets_data", {})
        group_by_name = group_config.get("group_by", "unknown")
        group_data = self._get_group_data(group_config, csv_file, group_id)

        widget_results: Dict[str, Any] = {}
        warnings: List[str] = []

        for widget_name, widget_config in widgets_config.items():
            try:
                widget_result = self._execute_widget_transform(
                    group_by_name, group_data, group_id, widget_name, widget_config
                )
                if widget_result:
                    widget_results[widget_name] = widget_result
            except Exception as exc:
                error_msg = (
                    f"Error processing widget '{widget_name}' for "
                    f"{group_by_name} {group_id}: {str(exc)}"
                )
                if "No data found" not in str(exc):
                    warnings.append(error_msg)

        return {
            "group_id": group_id,
            "results": widget_results,
            "warnings": warnings,
        }

    def _record_transform_warning(
        self, error_msg: str, progress_manager: Any | None = None
    ) -> None:
        """Record a non-fatal widget warning in the appropriate output channel."""

        if progress_manager is not None:
            progress_manager.add_warning(error_msg)
        else:
            logger.warning(error_msg)
            if self.console is not None:
                self.console.print(f"[yellow]{emoji('⚠', '[!]')} {error_msg}[/yellow]")

        if self.transform_metrics:
            self.transform_metrics.add_warning(error_msg)

    def _apply_entity_results(
        self,
        group_by_name: str,
        entity_result: Dict[str, Any],
        group_results: Dict[str, Any],
    ) -> int:
        """Persist computed entity results and update group-level counters."""

        widget_results = entity_result.get("results", {})
        if not widget_results:
            return 0

        self._save_widget_results(
            group_by=group_by_name,
            group_id=entity_result["group_id"],
            results=widget_results,
        )

        generated = 0
        for widget_name in widget_results:
            if widget_name not in group_results["widgets"]:
                group_results["widgets"][widget_name] = 0
            group_results["widgets"][widget_name] += 1
            generated += 1

        return generated

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
        transform_succeeded = False
        try:
            self.db.enable_connection_reuse()
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
            transform_succeeded = True
        except Exception as e:
            if self.transform_metrics:
                self.transform_metrics.add_error(str(e))
            raise
        finally:
            try:
                for group_name in list(self._table_buffers.keys()):
                    recreate = self._table_flush_modes.get(group_name, True)
                    self._flush_group_table(group_name, recreate)
                if transform_succeeded:
                    self._persist_transform_source_schemas(configs)
                if getattr(self.db, "is_duckdb", False):
                    logger.info("Running DuckDB checkpoint after transformations")
                    self.db.optimize_database()
            finally:
                self.db.disable_connection_reuse()
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

            # Pre-load id→name mapping for progress display
            id_name_map: Dict[int, str] = {}
            if progress_callback:
                id_name_map = self._load_group_names(group_config, group_ids)

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
                        widget_results = self._execute_widget_transform(
                            group_by_name,
                            group_data,
                            group_id,
                            widget_name,
                            widget_config,
                        )

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
                            self._record_transform_warning(error_msg, progress_manager)

                    # Update progress
                    progress_manager.update_task(task_name, advance=1)
                    if progress_callback:
                        progress_callback(
                            {
                                "group": group_by_name,
                                "widget": widget_name,
                                "item_label": id_name_map.get(group_id, str(group_id)),
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

            # Pre-load id→name mapping for progress display
            id_name_map_simple: Dict[int, str] = {}
            if progress_callback:
                id_name_map_simple = self._load_group_names(group_config, group_ids)

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
                        widget_results = self._execute_widget_transform(
                            group_by_name,
                            group_data,
                            group_id,
                            widget_name,
                            widget_config,
                        )

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
                            self._record_transform_warning(error_msg)

                    processed_ops += 1
                    if progress_callback and total_ops:
                        progress_callback(
                            {
                                "group": group_by_name,
                                "widget": widget_name,
                                "item_label": id_name_map_simple.get(
                                    group_id, str(group_id)
                                ),
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
        """Filter configurations by exact group_by match."""
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
        filtered = [
            config
            for config in self.transforms_config
            if config.get("group_by") == group_by
        ]

        if not filtered:
            raise ConfigurationError(
                "transforms",
                f"No configuration found for group: {group_by}",
                details={
                    "group": group_by,
                    "available_groups": available_groups,
                    "help": f"Available groups are: {', '.join(available_groups)}.",
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
        try:
            TransformGroupConfig.model_validate(config)
        except PydanticValidationError as exc:
            raise ConfigurationError(
                "transforms",
                "Invalid transform group configuration",
                details={"errors": exc.errors()},
            ) from exc
        self._validate_sources_config(config)

    def _validate_sources_config(self, config: Dict[str, Any]) -> None:
        """Validate sources configuration list."""
        sources = config.get("sources", [])
        if not sources:
            return

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
            if "plugin" not in relation or "key" not in relation:
                raise ConfigurationError(
                    f"sources[{idx}].relation",
                    f"Missing required relation fields in source '{source_name}'",
                    details={"required": ["plugin", "key"]},
                )

    def _load_group_names(
        self, group_config: Dict[str, Any], group_ids: List[int]
    ) -> Dict[int, str]:
        """Load a mapping of group_id → display name for progress messages."""
        if not group_ids:
            return {}
        try:
            sources = group_config.get("sources", [])
            grouping_table = (
                sources[0]["grouping"] if sources else group_config.get("group_by")
            )
            if not grouping_table:
                return {}
            resolved_table = self._resolve_table_name(grouping_table)

            # Find the best name column
            columns = self.db.get_table_columns(resolved_table) or []
            name_col = None
            for candidate in ["name", "full_name", "label", "title"]:
                if candidate in columns:
                    name_col = candidate
                    break
            if not name_col:
                # Try *_name pattern
                for col in columns:
                    if col.endswith("_name"):
                        name_col = col
                        break
            if not name_col:
                return {}

            id_field = "id"
            try:
                metadata = self.entity_registry.get(grouping_table)
                id_field = metadata.config.get("schema", {}).get("id_field", "id")
            except (Exception,):
                pass

            qt = str(quoted_name(resolved_table, quote=True))
            qi = str(quoted_name(id_field, quote=True))
            qn = str(quoted_name(name_col, quote=True))
            rows = self.db.fetch_all(f"SELECT {qi}, {qn} FROM {qt}")
            return {row[id_field]: row[name_col] for row in rows} if rows else {}
        except Exception as e:
            logger.debug("Could not load group names: %s", e)
            return {}

    def _get_group_ids(self, group_config: Dict[str, Any]) -> List[int]:
        """Get all group IDs to process."""
        sources = group_config.get("sources", [])
        grouping_table = (
            sources[0]["grouping"] if sources else group_config.get("group_by")
        )
        if not grouping_table:
            raise DataTransformError("No grouping table configured")
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

    def _load_reference_entity(self, entity_name: str, entity_id: int) -> pd.DataFrame:
        """Load a single reference entity record (e.g., a specific shape, plot, or taxon).

        This method is called when a widget requests the grouping entity itself as a source.
        For example, when processing shapes and a widget needs shape data (name, type, etc.),
        this loads the specific shape record from the entity table.

        Args:
            entity_name: The logical entity name (e.g., 'shapes', 'plots', 'taxonomy')
            entity_id: The ID of the specific entity to load

        Returns:
            pd.DataFrame: Single-row DataFrame with the entity data

        Raises:
            DataTransformError: If the entity cannot be loaded
        """
        try:
            # Resolve logical entity name to physical table name
            table_name = self._resolve_table_name(entity_name)

            # Get the ID field name from entity metadata
            id_field = "id"  # Default
            try:
                metadata = self.entity_registry.get(entity_name)
                id_field = metadata.config.get("schema", {}).get("id_field", "id")
            except (DatabaseQueryError, AttributeError, KeyError) as exc:
                logger.debug(
                    "Falling back to default id field for entity '%s': %s",
                    entity_name,
                    exc,
                )

            # Validate identifier names to prevent SQL injection
            if not table_name.replace("_", "").replace(".", "").isalnum():
                raise DataTransformError(
                    f"Invalid table name: {table_name}",
                    details={"table": table_name},
                )
            if not id_field.replace("_", "").isalnum():
                raise DataTransformError(
                    f"Invalid field name: {id_field}",
                    details={"field": id_field},
                )

            # Use quoted names for safe SQL
            quoted_table = str(quoted_name(table_name, quote=True))
            quoted_id_field = str(quoted_name(id_field, quote=True))

            # Load the specific entity record using fetch_all
            # We use fetch_all which properly manages session lifecycle
            sql_query = (
                f"SELECT * FROM {quoted_table} WHERE {quoted_id_field} = :entity_id"
            )
            rows = self.db.fetch_all(sql_query, {"entity_id": entity_id})

            if not rows:
                raise DataTransformError(
                    f"Entity not found: {entity_name} with {id_field}={entity_id}",
                    details={
                        "entity": entity_name,
                        "table": table_name,
                        "id_field": id_field,
                        "id": entity_id,
                    },
                )

            # Convert list of dicts to DataFrame
            df = pd.DataFrame(rows)

            return df

        except DataTransformError:
            raise
        except Exception as e:
            raise DataTransformError(
                f"Failed to load reference entity '{entity_name}' with id {entity_id}",
                details={
                    "error": str(e),
                    "entity": entity_name,
                    "table": table_name if "table_name" in locals() else entity_name,
                    "id": entity_id,
                },
            ) from e

    def _load_additional_source(self, source_name: str) -> pd.DataFrame:
        """Load an additional data source that wasn't in the original config.

        This method is called when a transformer requests a source that wasn't
        preloaded in group_data. It loads the entire table as a DataFrame.

        Args:
            source_name: The logical entity name or table name to load

        Returns:
            pd.DataFrame: The loaded data

        Raises:
            DataTransformError: If the source cannot be loaded
        """
        try:
            # Resolve logical entity name to physical table name
            table_name = self._resolve_table_name(source_name)
            quoted_table_name = inspect(
                self.db.engine
            ).dialect.identifier_preparer.quote(table_name)

            # Load entire table as DataFrame using fetch_all
            # We use fetch_all which properly manages session lifecycle
            sql_query = f"SELECT * FROM {quoted_table_name}"
            rows = self.db.fetch_all(sql_query)

            # Convert list of dicts to DataFrame
            df = pd.DataFrame(rows)

            return df

        except Exception as e:
            raise DataTransformError(
                f"Failed to load additional source '{source_name}'",
                details={
                    "error": str(e),
                    "table": table_name if "table_name" in locals() else source_name,
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
                self._bind_plugin_runtime_config(loader)
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

    def _persist_transform_source_schemas(self, configs: List[Dict[str, Any]]) -> None:
        """Persist observed schemas for file-based transform sources."""

        from niamoto.core.imports.source_registry import TransformSourceRegistry
        from niamoto.core.services.compatibility import CSVSchemaReader

        config_dir = getattr(self.config, "config_dir", None)
        if not isinstance(config_dir, (str, Path)):
            return

        project_root = Path(config_dir).parent
        registry = TransformSourceRegistry(self.db)
        seen_sources: set[str] = set()

        for group_config in configs:
            for source in group_config.get("sources", []):
                source_name = source.get("name", "")
                source_path = source.get("data", "")
                grouping = source.get("grouping", "")

                if (
                    not source_name
                    or not source_path
                    or "/" not in source_path
                    or source_name in seen_sources
                ):
                    continue

                resolved_path = (project_root / source_path).resolve()
                if not resolved_path.exists():
                    logger.debug(
                        "Skipping transform source baseline for missing file: %s",
                        resolved_path,
                    )
                    continue

                fields, error = CSVSchemaReader.read_schema(resolved_path)
                if error:
                    logger.warning(
                        "Failed to persist transform source baseline for %s: %s",
                        source_name,
                        error,
                    )
                    continue

                registry.register_source(
                    name=source_name,
                    path=source_path,
                    grouping=grouping,
                    config={"schema": {"fields": fields}},
                )
                seen_sources.add(source_name)

    def _create_group_table(
        self, group_by: str, widgets_config: Dict[str, Any], recreate_table: bool = True
    ) -> None:
        """Create or update table for group results."""
        try:
            # Create columns for each widget
            columns = [
                f"{self._quote_sql_identifier(widget_name)} JSON"
                for widget_name in widgets_config.keys()
            ]
            quoted_table = self._quote_sql_identifier(group_by)
            quoted_id_column = self._quote_sql_identifier(f"{group_by}_id")

            # Drop table if recreate_table is True
            if recreate_table:
                drop_table_sql = f"""
                DROP TABLE IF EXISTS {quoted_table}
                """
                self.db.execute_sql(drop_table_sql)

            # Use 'id' as primary key to match the entity table's id field
            # This allows transformations for all hierarchy levels (families, genera, species)
            # not just those with external IDs (e.g., taxonomy_id)
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {quoted_table} (
                {quoted_id_column} BIGINT PRIMARY KEY,
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
        quoted_table = self._quote_sql_identifier(group_by)
        quoted_id_column = self._quote_sql_identifier(id_column)
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
        quoted_staging_table = self._quote_sql_identifier(staging_table)
        self._write_dataframe_to_table(df, staging_table)

        non_id_columns = [col for col in ordered_columns if col != id_column]
        quoted_columns = [self._quote_sql_identifier(col) for col in ordered_columns]
        quoted_non_id_columns = [
            self._quote_sql_identifier(col) for col in non_id_columns
        ]
        columns_sql = ", ".join(quoted_columns)
        if non_id_columns:
            update_clause = ", ".join(
                f"{col} = excluded.{col}" for col in quoted_non_id_columns
            )
            insert_sql = f"""
                INSERT INTO {quoted_table} ({columns_sql})
                SELECT {columns_sql} FROM {quoted_staging_table}
                ON CONFLICT ({quoted_id_column})
                DO UPDATE SET {update_clause}
            """
        else:
            insert_sql = f"""
                INSERT INTO {quoted_table} ({quoted_id_column})
                SELECT {quoted_id_column} FROM {quoted_staging_table}
                ON CONFLICT ({quoted_id_column}) DO NOTHING
            """

        try:
            self.db.execute_sql(insert_sql)
        finally:
            self.db.execute_sql(f"DROP TABLE IF EXISTS {quoted_staging_table}")
