# src/niamoto/core/services/exporter.py

"""
Service responsible for handling the data export process based on export.yml configuration.

It loads the export configuration, validates it using Pydantic models,
loads the necessary exporter and widget plugins, retrieves transformed data,
and orchestrates the execution of export plugins to generate output files.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import ValidationError

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import ConfigurationError, ProcessError
from niamoto.common.utils import error_handler
from niamoto.core.plugins.plugin_loader import PluginLoader
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.models import ExportConfig

logger = logging.getLogger(__name__)


class ExporterService:
    """Manages the data export process based on export configuration."""

    def __init__(self, db_path: str, config: Config):
        """
        Initialize the ExporterService.

        Args:
            db_path: Path to the database file.
            config: The main Niamoto configuration object.

        Raises:
            ConfigurationError: If the export configuration is missing or invalid.
        """
        logger.info("Initializing ExporterService...")
        self.db = Database(db_path)
        self.config = config
        try:
            self.validated_config: ExportConfig = ExportConfig(
                **config.get_exports_config()
            )
            logger.info("Export configuration loaded and validated successfully.")
        except ValidationError as e:
            logger.error(f"Invalid export configuration structure: {e}")
            # Format Pydantic error for better readability
            error_details = e.errors()
            formatted_errors = "\n".join(
                [f"  - {err['loc']}: {err['msg']}" for err in error_details]
            )
            raise ConfigurationError(
                config_key="export.yml",
                message=f"Invalid configuration:\n{formatted_errors}",
                details=error_details,
            ) from e
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while validating export configuration."
            )
            raise ProcessError(
                f"Failed to validate export configuration: {e}", details=str(e)
            ) from e

        # Initialize plugin loader and load plugins
        self.plugin_loader = PluginLoader()
        self.plugin_loader.load_core_plugins()
        self.plugin_loader.load_project_plugins(config.plugins_dir)

        # Get registry instance (already populated by PluginLoader)
        self.plugin_registry = PluginRegistry()

        logger.info("ExporterService initialized successfully.")

    def get_export_targets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all export targets and their configurations.

        Returns:
            Dict mapping target names to their configuration info.
        """
        targets = {}

        if not self.validated_config.exports:
            return targets

        for target in self.validated_config.exports:
            targets[target.name] = {
                "enabled": target.enabled,
                "exporter": target.exporter,
                "params": target.params.model_dump()
                if hasattr(target.params, "model_dump")
                else target.params,
                "groups": [
                    {
                        "group_by": group.group_by,
                        **(
                            group.model_dump(exclude={"group_by"})
                            if hasattr(group, "model_dump")
                            else {
                                k: v
                                for k, v in group.__dict__.items()
                                if k != "group_by"
                            }
                        ),
                    }
                    for group in (target.groups or [])
                ],
            }

        return targets

    @error_handler(log=True, raise_error=True)
    def run_export(
        self, target_name: Optional[str] = None, group_filter: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Executes the specified export target or all enabled targets.

        Returns:
            Dict mapping target names to their export results.
        """
        results = {}

        if not self.validated_config.exports:
            logger.warning(
                "No export targets defined in the configuration. Nothing to export."
            )
            return results

        # Determine which targets to process
        targets_to_process = self.validated_config.exports
        if target_name:
            targets_to_process = [
                t for t in targets_to_process if t.name == target_name
            ]
            if not targets_to_process:
                logger.error(
                    f"Export target '{target_name}' not found in configuration."
                )
                raise ConfigurationError(
                    config_key="exports", message=f"Target '{target_name}' not found."
                )
            logger.info(f"Starting export process for target: '{target_name}'...")
        else:
            logger.info("Starting export process for all enabled targets...")

        if not targets_to_process:
            logger.warning("No export targets selected to process.")
            return results

        found_enabled_target = False
        for target in targets_to_process:
            if not target.enabled:
                logger.info(f"Skipping disabled export target: '{target.name}'")
                results[target.name] = {
                    "status": "skipped",
                    "reason": "disabled",
                    "files_generated": 0,
                    "errors": 0,
                }
                continue

            found_enabled_target = True
            start_time = datetime.now()

            logger.info(
                f"Processing export target: '{target.name}' using exporter '{target.exporter}'"
            )

            # Initialize result for this target
            target_result = {
                "status": "running",
                "files_generated": 0,
                "errors": 0,
                "start_time": start_time,
                "duration": None,
            }

            try:
                exporter_plugin_class = self.plugin_registry.get_plugin(
                    target.exporter, PluginType.EXPORTER
                )
                if not exporter_plugin_class:
                    raise ConfigurationError(
                        config_key="exports.exporter",
                        message=f"Exporter plugin '{target.exporter}' not found for target '{target.name}'.",
                    )

                # Instantiate the plugin
                exporter_instance = exporter_plugin_class(db=self.db)

                # Execute the plugin's export method with validated config
                exporter_instance.export(
                    target_config=target, repository=self.db, group_filter=group_filter
                )

                # Collect statistics from the exporter if available
                if hasattr(exporter_instance, "stats"):
                    stats = exporter_instance.stats
                    target_result.update(
                        {
                            "files_generated": stats.get("total_files_generated", 0),
                            "errors": stats.get("errors_count", 0),
                            "groups_processed": stats.get("groups_processed", {}),
                            "output_path": stats.get("output_path"),
                        }
                    )

                target_result["status"] = "success"
                logger.info(f"Successfully processed export target: '{target.name}'")

            except Exception as e:
                target_result["status"] = "error"
                target_result["error"] = str(e)
                target_result["errors"] = 1

                logger.error(
                    f"Error executing exporter plugin '{target.exporter}' for target '{target.name}': {e}",
                    exc_info=True,
                )
                # Continue to next target instead of raising
                # raise ProcessError(f"Export failed for target '{target.name}'") from e

            finally:
                end_time = datetime.now()
                target_result["duration"] = str(end_time - start_time)
                results[target.name] = target_result

        if not found_enabled_target:
            logger.warning("No enabled export targets found to process.")

        if target_name:
            logger.info(f"Export process finished for target: '{target_name}'.")
        else:
            logger.info("Export process finished for all enabled targets.")

        return results

    # --- Add helper methods as needed for data retrieval, etc. ---
    # Example:
    # def get_data_for_group(self, group_by: str, data_source: Optional[str], group_id: Any) -> Any:
    #    """Retrieves data for a specific group ID from the database."""
    #    # ... implementation using self.db ...
    #    pass
