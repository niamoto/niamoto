"""
Service for transforming data based on YAML configuration.
"""

from typing import Dict, Any, List, Optional
import logging
import difflib
import json
import numpy as np
import pandas as pd
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)
from sqlalchemy.exc import SQLAlchemyError
from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import (
    ConfigurationError,
    ProcessError,
    ValidationError,
    DatabaseWriteError,
    JSONEncodeError,
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
        self.plugin_loader.load_project_plugins(config.plugins_dir)

    @error_handler(log=True, raise_error=True)
    def transform_data(
        self,
        group_by: Optional[str] = None,
        csv_file: Optional[str] = None,
        recreate_table: bool = True,
    ) -> None:
        """
        Transforme les données selon la configuration.

        Args:
            group_by: Filtre optionnel par groupe
            csv_file: Fichier CSV optionnel à utiliser au lieu de la base de données
            recreate_table: Indique s'il faut recréer la table des résultats

        Raises:
            ConfigurationError: Si la configuration est invalide
            ProcessError: Si la transformation échoue
        """
        # Filtrer les configurations
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
            for group_config in configs:
                # Valider la configuration
                self.validate_configuration(group_config)

                # Récupérer les IDs de groupe et les widgets
                group_ids = self._get_group_ids(group_config)
                widgets_config = group_config.get("widgets_data", {})
                group_by_name = group_config.get("group_by", "unknown")

                # Calculer le total des opérations
                total_ops = len(group_ids) * len(widgets_config)
                config_task = progress.add_task(
                    f"[cyan]Traitement des données {group_by_name}...", total=total_ops
                )

                # Créer ou mettre à jour la table
                self._create_group_table(group_by_name, widgets_config, recreate_table)

                # Traiter chaque groupe
                for group_id in group_ids:
                    progress.update(
                        config_task,
                        description=f"[cyan]Traitement {group_by_name} {group_id}...",
                    )

                    # Récupérer les données du groupe
                    group_data = self._get_group_data(group_config, csv_file, group_id)

                    # Traiter chaque widget
                    for widget_name, widget_config in widgets_config.items():
                        # Charger le plugin de transformation
                        transformer = PluginRegistry.get_plugin(
                            widget_config["plugin"], PluginType.TRANSFORMER
                        )(self.db)

                        # Transformer les données
                        config = {
                            "plugin": widget_config["plugin"],
                            "params": {
                                "source": widget_config.get("source"),
                                "field": widget_config.get("field"),
                                **widget_config.get("params", {}),
                            },
                            "group_id": group_id,
                        }
                        results = transformer.transform(group_data, config)

                        # Sauvegarder les résultats
                        if results:
                            self._save_widget_results(
                                group_by=group_by_name,
                                group_id=group_id,
                                results={widget_name: results},
                            )

                        progress.advance(config_task)

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
            ) from e

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
            except Exception as e:
                raise DataTransformError(
                    "Failed to get group data", details={"error": str(e)}
                ) from e

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
            ) from e

    def _save_widget_results(
        self, group_by: str, group_id: int, results: Dict[str, Any]
    ) -> None:
        """Save widget results to database.

        Args:
            group_by (str): Name of the table to save results into.
            group_id (int): Identifier of the group.
            results (Dict[str, Any]): Dictionary mapping column names to their values.

        Raises:
            ValidationError: If input data is invalid.
            DatabaseWriteError: If a database error occurs.
            DataTransformError: If data serialization fails.
            ProcessError: For unexpected errors.
        """
        # Validation des données d'entrée
        if not results:
            raise ValidationError(
                "results",
                "No results to save",
                details={"group_by": group_by, "group_id": group_id},
            )

        columns = list(results.keys())
        values = [results[col] for col in columns]

        # Vérifier la cohérence entre colonnes et valeurs
        if len(columns) != len(values):
            raise ValidationError(
                "results",
                "Mismatch between columns and values",
                details={"columns": columns, "values": values},
            )

        try:
            # Formater les valeurs pour la requête SQL
            formatted_values = [self._format_value_for_sql(group_id)]
            for val in values:
                formatted_values.append(self._format_value_for_sql(val))

            # Construire la requête SQL
            sql = f"""
                INSERT INTO {group_by} ({group_by}_id, {", ".join(columns)})
                VALUES ({", ".join(formatted_values)})
                ON CONFLICT ({group_by}_id)
                DO UPDATE SET {", ".join(f"{col} = excluded.{col}" for col in columns)}
            """

            # Exécuter la requête
            self.db.execute_sql(sql)

        except SQLAlchemyError as e:
            raise DatabaseWriteError(
                table_name=group_by,
                message=f"Failed to save results for group {group_id}: {str(e)}",
                details={"group_id": group_id, "columns": columns, "error": str(e)},
            ) from e
        except JSONEncodeError as e:
            raise DataTransformError(
                f"Failed to encode results for group {group_id}: {str(e)}",
                details={"group_id": group_id, "error": str(e)},
            ) from e
        except Exception as e:
            raise ProcessError(
                f"Unexpected error while saving results for group {group_id}: {str(e)}",
                details={"group_by": group_by, "group_id": group_id, "error": str(e)},
            ) from e

    def _format_value_for_sql(self, val: Any) -> str:
        """Format a value for SQL insertion.

        Args:
            val (Any): Value to format.

        Returns:
            str: Formatted value ready for SQL query.

        Raises:
            JSONEncodeError: If serialization of complex types fails.
        """
        if val is None:
            return "NULL"
        elif isinstance(val, (int, float)):
            return str(val)
        elif isinstance(val, (dict, list)):
            try:

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

                converted = convert_numpy(val)
                json_str = json.dumps(converted, ensure_ascii=False)
                return f"'{json_str.replace(chr(39), chr(39) + chr(39))}'"
            except Exception as e:
                raise JSONEncodeError(f"Failed to encode value: {str(e)}") from e
        elif hasattr(val, "dtype") and np.issubdtype(val.dtype, np.number):
            return str(val.item())
        else:
            str_val = str(val)
            return f"'{str_val.replace(chr(39), chr(39) + chr(39))}'"
