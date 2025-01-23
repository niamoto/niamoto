"""
Service for calculating transforms in Niamoto.
"""

from pathlib import Path
from typing import Any, Hashable, Optional, Dict, List
import pandas as pd
import sqlalchemy

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.core.utils.logging_utils import setup_logging
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    ProcessError,
    CalculationError,
    DataTransformError,
    ValidationError,
    FileReadError,
    ConfigurationError,
)
from niamoto.core.components.transforms.shapes import ShapeTransformer
from niamoto.core.components.transforms.taxons import TaxonTransformer
from niamoto.core.components.transforms.plots import PlotTransformer


class TransformerService:
    """Service providing methods to calculate various transforms."""

    def __init__(self, db_path: str, config: Config):
        """
        Initialize the TransformerService.

        Args:
            db_path: Path to the database file
            config: Configuration instance
        """
        self.db_path = db_path
        self.db = Database(db_path)
        self.config = config
        self.logger = setup_logging(component_name="transform")

    @error_handler(log=True, raise_error=True)
    def calculate_statistics(
        self, csv_file: Optional[str] = None, group_by: Optional[str] = None
    ) -> None:
        """
        Calculate transforms based on configuration.

        Args:
            group_by: Type of grouping (taxon, plot, shape)
            csv_file: Optional CSV file path to use instead of configured source

        Raises:
            ConfigurationError: If configuration is invalid
            ValidationError: If parameters are invalid
            ProcessError: If calculation fails
        """
        # Get stats configuration
        imports_config = self.config.get_transforms_config()
        if not imports_config:
            raise ConfigurationError(
                "transforms",
                "No transformations configuration found",
                details={"config_file": "transform.yml"},
            )

        # Validate group_by if provided
        valid_groups = {"taxon", "plot", "shape"}
        if group_by and group_by not in valid_groups:
            raise ValidationError(
                "group_by",
                f"Invalid group type. Must be one of: {', '.join(valid_groups)}",
                details={"provided": group_by},
            )

        try:
            # Get occurrences data
            occurrences = self.get_occurrences(csv_file)

            if group_by:
                # Calculate for specific group
                group_stats = next(
                    (g for g in imports_config if g["group_by"] == group_by), None
                )
                if not group_stats:
                    raise ConfigurationError(
                        "transforms", f"No configuration found for group: {group_by}"
                    )
                self.calculate_group_statistics(occurrences, group_stats)
            else:
                # Calculate for all groups
                for group_stats in imports_config:
                    self.calculate_group_statistics(occurrences, group_stats)

        except Exception as e:
            if isinstance(e, (ConfigurationError, ValidationError)):
                raise
            raise ProcessError(
                f"Failed to calculate transforms: {str(e)}",
                details={"group_by": group_by, "csv_file": csv_file, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def get_occurrences(self, csv_file: Optional[str]) -> List[Dict[Hashable, Any]]:
        """
        Retrieve occurrences data.

        Args:
            csv_file: Optional CSV file path

        Returns:
            List of occurrences

        Raises:
            FileReadError: If file cannot be read
            ConfigurationError: If source path not configured
            DataTransformError: If data processing fails
        """
        try:
            if csv_file:
                if not Path(csv_file).exists():
                    raise FileReadError(csv_file, "File not found")
                return self.load_occurrences_from_csv(csv_file)

            # Get source path from configuration
            source_config = self.config.get_imports_config.get("occurrences", {})
            source_path = source_config.get("path")

            if not source_path:
                raise ConfigurationError(
                    "occurrences",
                    "No occurrence source path configured",
                    details={"config": "import.yml"},
                )

            source_path = str(Path(source_path).resolve())
            if not Path(source_path).exists():
                raise FileReadError(source_path, "Configured source file not found")

            return self.load_occurrences_from_csv(source_path)

        except Exception as e:
            if isinstance(e, (FileReadError, ConfigurationError)):
                raise
            raise DataTransformError(
                f"Failed to load occurrences: {str(e)}", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def calculate_group_statistics(
        self, occurrences: List[Dict[Hashable, Any]], group_config: Dict[str, Any]
    ) -> None:
        """
        Calculate transforms for a group.

        Args:
            occurrences: List of occurrences
            group_config: Group configuration

        Raises:
            CalculationError: If calculation fails
            ValidationError: If configuration is invalid
        """
        group_by = group_config.get("group_by")
        if not group_by:
            raise ValidationError("group_config", "Missing group_by in configuration")

        try:
            if group_by == "taxon":
                calculator = TaxonTransformer(self.db, occurrences, group_config)
                calculator.calculate_taxonomy_stats()
            elif group_by == "plot":
                calculator = PlotTransformer(self.db, occurrences, group_config)
                calculator.calculate_plot_stats()
            elif group_by == "shape":
                calculator = ShapeTransformer(self.db, occurrences, group_config)
                calculator.calculate_shape_stats()
            else:
                raise ValidationError("group_by", f"Unknown group type: {group_by}")

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise CalculationError(
                f"Failed to calculate {group_by} transforms",
                details={"group": group_by, "error": str(e)},
            )

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def load_occurrences_from_csv(csv_file: str) -> List[Dict[Hashable, Any]]:
        """
        Load occurrences from CSV.

        Args:
            csv_file: Path to CSV file

        Returns:
            List of occurrences

        Raises:
            FileReadError: If file cannot be read
            DataTransformError: If data processing fails
        """
        try:
            df = pd.read_csv(csv_file)
            return df.to_dict("records")
        except Exception as e:
            raise DataTransformError(
                f"Failed to load CSV file: {str(e)}",
                details={"file": csv_file, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def load_occurrences_from_database(
        self, table_name: str
    ) -> List[Dict[Hashable, Any]]:
        """
        Load occurrences from database.

        Args:
            table_name: Name of the table

        Returns:
            List of occurrences

        Raises:
            DatabaseError: If database operation fails
            DataTransformError: If data processing fails
        """
        try:
            engine = sqlalchemy.create_engine(f"sqlite:///{self.db_path}")
            df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
            return df.to_dict("records")
        except Exception as e:
            raise DataTransformError(
                f"Failed to load from database: {str(e)}",
                details={"table": table_name, "error": str(e)},
            )
