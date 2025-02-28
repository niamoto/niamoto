"""
Base class for data generation with shared utilities.
"""

import json
from typing import Optional, Any, Dict

from shapely import wkt
from shapely.geometry import mapping
from shapely.errors import ShapelyError

from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import DataValidationError, GenerationError


class BaseGenerator:
    """Base class providing common data conversion methods."""

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def parse_json_field(field: Any) -> Any:
        """
        Parse a JSON field safely.

        Args:
            field: Field to parse

        Returns:
            Parsed field value

        Raises:
            DataValidationError: If JSON parsing fails
        """
        if isinstance(field, str):
            try:
                return json.loads(field)
            except json.JSONDecodeError as e:
                raise DataValidationError(
                    "Invalid JSON field", [{"field": str(field)[:100], "error": str(e)}]
                )
        return field

    @error_handler(log=True, raise_error=True)
    def taxon_to_dict(self, taxon: TaxonRef, stats: Optional[Any]) -> Dict[str, Any]:
        """
        Convert TaxonRef to dictionary.

        Args:
            taxon: TaxonRef object
            stats: Optional transforms

        Returns:
            Dictionary representation

        Raises:
            GenerationError: If conversion fails
        """
        try:
            stats_dict = {
                "id": taxon.id,
                "full_name": taxon.full_name,
                "authors": taxon.authors,
                "rank_name": taxon.rank_name,
                "metadata": taxon.extra_data if taxon.extra_data is not None else {},
                "lft": taxon.lft,
                "rght": taxon.rght,
                "level": taxon.level,
                "parent_id": taxon.parent_id,
            }

            if stats:
                # Parse JSON fields
                parsed_stats = {}
                for key, value in stats.items():
                    try:
                        parsed_stats[key] = self.parse_json_field(value)
                    except DataValidationError:
                        # Log warning but continue
                        parsed_stats[key] = value
                stats_dict.update(parsed_stats)

            return stats_dict

        except Exception as e:
            raise GenerationError(
                f"Failed to convert taxon {taxon.id} to dictionary",
                details={"error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def plot_to_dict(self, plot: PlotRef, stats: Optional[Any]) -> Dict[str, Any]:
        """
        Convert PlotRef to dictionary.

        Args:
            plot: PlotRef object
            stats: Optional transforms

        Returns:
            Dictionary representation

        Raises:
            GenerationError: If conversion fails
            DataValidationError: If geometry is invalid
        """
        try:
            # Handle geometry
            geometry_dict = None
            if plot.geometry:
                try:
                    geom = wkt.loads(str(plot.geometry))
                    geometry_dict = mapping(geom)
                except ShapelyError as e:
                    raise DataValidationError(
                        "Invalid geometry", [{"plot": plot.id, "error": str(e)}]
                    )

            stats_dict = {
                "id": plot.id,
                "locality": plot.locality,
                "geometry": geometry_dict,
            }

            if stats:
                # Parse JSON fields
                parsed_stats = {}
                for key, value in stats.items():
                    try:
                        parsed_stats[key] = self.parse_json_field(value)
                    except DataValidationError:
                        # Log warning but continue
                        parsed_stats[key] = value
                stats_dict.update(parsed_stats)

            return stats_dict

        except Exception as e:
            if isinstance(e, DataValidationError):
                raise
            raise GenerationError(
                f"Failed to convert plot {plot.id} to dictionary",
                details={"error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def shape_to_dict(self, shape: ShapeRef, stats: Optional[Any]) -> Dict[str, Any]:
        """
        Convert ShapeRef to dictionary.

        Args:
            shape: ShapeRef object
            stats: Optional transforms

        Returns:
            Dictionary representation

        Raises:
            GenerationError: If conversion fails
        """
        try:
            # Base dictionary
            stats_dict = {"id": shape.id, "name": shape.label, "type": shape.type}

            if stats:
                # Parse JSON fields
                parsed_stats = {}
                for key, value in stats.items():
                    try:
                        parsed_stats[key] = self.parse_json_field(value)
                    except DataValidationError:
                        # Log warning but continue
                        parsed_stats[key] = value
                stats_dict.update(parsed_stats)

            return stats_dict

        except Exception as e:
            raise GenerationError(
                f"Failed to convert shape {shape.id} to dictionary",
                details={"error": str(e)},
            )
