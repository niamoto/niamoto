"""
Module for generating JSON API files.
"""

import json
import logging
from pathlib import Path
from typing import Any, List, Optional, Dict, Union


from niamoto.common.config import Config
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from niamoto.core.components.exports.base_generator import BaseGenerator
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    GenerationError,
    OutputError,
    DataValidationError,
    ConfigurationError,
)


class ApiGenerator(BaseGenerator):
    """Class for generating JSON API files."""

    def __init__(self, config: Config) -> None:
        """
        Initialize the generator.

        Args:
            config: Configuration settings

        Raises:
            ConfigurationError: If output path is missing
        """
        super().__init__()
        self.config = config

        # Get and validate output path
        api_path = config.get_export_config.get("api")
        if not api_path:
            raise ConfigurationError("api", "Missing api output path in configuration")
        self.json_output_dir = Path(api_path)

    @error_handler(log=True, raise_error=True)
    def generate_taxon_json(self, taxon: TaxonRef, stats: Optional[Any]) -> str:
        """
        Generate JSON file for a taxon.

        Args:
            taxon: Taxon object to process
            stats: Optional transforms data

        Returns:
            Generated file path

        Raises:
            GenerationError: If JSON generation fails
            OutputError: If file writing fails
        """
        output_path = self.json_output_dir / "taxon" / f"{taxon.id}.json"

        try:
            taxon_dict = self.taxon_to_dict(taxon, stats)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(taxon_dict, file, indent=4)

            return str(output_path)

        except Exception as e:
            raise OutputError(
                str(output_path),
                "Failed to write taxon JSON",
                details={"taxon_id": taxon.id, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def generate_plot_json(self, plot: PlotRef, stats: Optional[Any]) -> str:
        """
        Generate JSON file for a plot.

        Args:
            plot: Plot object to process
            stats: Optional transforms data

        Returns:
            Generated file path

        Raises:
            GenerationError: If JSON generation fails
            OutputError: If file writing fails
        """
        output_path = self.json_output_dir / "plot" / f"{plot.id}.json"

        try:
            plot_dict = self.plot_to_dict(plot, stats)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(plot_dict, file, indent=4)

            return str(output_path)

        except Exception as e:
            raise OutputError(
                str(output_path),
                "Failed to write plot JSON",
                details={"plot_id": plot.id, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def generate_shape_json(self, shape: ShapeRef, stats: Optional[Any]) -> str:
        """
        Generate JSON file for a shape with GeoJSON geometry.

        Args:
            shape: Shape object to process
            stats: Optional transforms data

        Returns:
            Generated file path

        Raises:
            GenerationError: If JSON generation fails
            DataValidationError: If geometry is invalid
            OutputError: If file writing fails
        """
        output_path = self.json_output_dir / "shape" / f"{shape.id}.json"

        try:
            # Get data dictionary containing GeoJSON in "geography"
            shape_dict = self.shape_to_dict(shape, stats)
            logging.debug(f"Shape dictionary for shape {shape.id}: {shape_dict}")

            geography_data = shape_dict.get("geography", {})
            if not geography_data:
                logging.warning(f"Empty geography data for shape {shape.id}")

            # Validate GeoJSON structure for each coordinate type if present
            for coord_type in ["shape_coords", "forest_coords"]:
                if coord_type in geography_data and geography_data[coord_type]:
                    coords_data = geography_data[coord_type]

                    # Validate GeoJSON structure
                    validation_errors = []
                    if not isinstance(coords_data, dict):
                        validation_errors.append(
                            f"Invalid {coord_type} data type for shape {shape.id}. Expected dict, got {type(coords_data)}"
                        )

                    if isinstance(coords_data, dict) and "type" not in coords_data:
                        validation_errors.append(
                            f"Missing 'type' in {coord_type} for shape {shape.id}"
                        )

                    if validation_errors:
                        raise DataValidationError(
                            message=f"Validation failed for shape {shape.id}",
                            validation_errors=validation_errors,
                        )

                    logging.debug(
                        f"{coord_type} data for shape {shape.id}: {coords_data}"
                    )

            # Write minified output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(
                    shape_dict,
                    file,
                    indent=None,  # Remove indentation
                    separators=(",", ":"),  # Remove whitespace in separators
                    ensure_ascii=False,  # Allow UTF-8 characters
                )

            return str(output_path)

        except Exception as e:
            logging.error(f"Error processing shape {shape.id}: {str(e)}")
            raise OutputError(
                str(output_path),
                "Failed to write shape JSON",
                details={"shape_id": shape.id, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def generate_all_taxa_json(self, taxa: List[TaxonRef]) -> str:
        """
        Generate JSON file for all taxa.

        Args:
            taxa: List of taxa to process

        Returns:
            Generated file path

        Raises:
            GenerationError: If JSON generation fails
            OutputError: If file writing fails
        """
        output_path = self.json_output_dir / "all_taxa.json"

        try:
            all_taxa = [self.taxon_to_simple_dict(taxon) for taxon in taxa]
            output_data = {"total": len(all_taxa), "taxa": all_taxa}

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(output_data, file, indent=4)

            return str(output_path)

        except Exception as e:
            raise OutputError(
                str(output_path),
                "Failed to write taxa list JSON",
                details={"error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def generate_all_plots_json(self, plots: List[PlotRef]) -> str:
        """
        Generate JSON file for all plots.

        Args:
            plots: List of plots to process

        Returns:
            Generated file path

        Raises:
            GenerationError: If JSON generation fails
            OutputError: If file writing fails
        """
        output_path = self.json_output_dir / "all_plots.json"

        try:
            all_plots = [self.plot_to_simple_dict(plot) for plot in plots]
            output_data = {"total": len(all_plots), "plots": all_plots}

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(output_data, file, indent=4)

            return str(output_path)

        except Exception as e:
            raise OutputError(
                str(output_path),
                "Failed to write plots list JSON",
                details={"error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def generate_all_shapes_json(self, shapes: List[ShapeRef]) -> str:
        """
        Generate JSON file for all shapes.

        Args:
            shapes: List of shapes to process

        Returns:
            Generated file path

        Raises:
            GenerationError: If JSON generation fails
            OutputError: If file writing fails
        """
        output_path = self.json_output_dir / "all_shapes.json"

        try:
            all_shapes = [self.shape_to_simple_dict(shape) for shape in shapes]
            output_data = {"total": len(all_shapes), "shapes": all_shapes}

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(output_data, file, indent=4)

            return str(output_path)

        except Exception as e:
            raise OutputError(
                str(output_path),
                "Failed to write shapes list JSON",
                details={"error": str(e)},
            )

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def taxon_to_simple_dict(taxon: TaxonRef) -> Dict[str, Union[str, int, Dict]]:
        """
        Convert taxon to simplified dictionary.

        Args:
            taxon: Taxon object to convert

        Returns:
            Simplified dictionary representation

        Raises:
            GenerationError: If conversion fails
        """
        try:
            return {
                "id": int(taxon.id),
                "name": str(taxon.full_name),
                "metadata": taxon.extra_data or {},
                "endpoint": f"/api/taxon/{taxon.id}.json",
            }
        except Exception as e:
            raise GenerationError(
                f"Failed to convert taxon {taxon.id} to dictionary",
                details={"error": str(e)},
            )

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def plot_to_simple_dict(plot: PlotRef) -> Dict[str, Union[str, int]]:
        """
        Convert plot to simplified dictionary.

        Args:
            plot: Plot object to convert

        Returns:
            Simplified dictionary representation

        Raises:
            GenerationError: If conversion fails
        """
        try:
            return {
                "id": int(plot.id),
                "name": str(plot.locality),
                "endpoint": f"/api/plot/{plot.id}.json",
            }
        except Exception as e:
            raise GenerationError(
                f"Failed to convert plot {plot.id} to dictionary",
                details={"error": str(e)},
            )

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def shape_to_simple_dict(shape: ShapeRef) -> Dict[str, Union[str, int]]:
        """
        Convert shape to simplified dictionary.

        Args:
            shape: Shape object to convert

        Returns:
            Simplified dictionary representation

        Raises:
            GenerationError: If conversion fails
        """
        try:
            return {
                "id": int(shape.id),
                "name": str(shape.label),
                "type": str(shape.type),
                "endpoint": f"/api/shape/{shape.id}.json",
            }
        except Exception as e:
            raise GenerationError(
                f"Failed to convert shape {shape.id} to dictionary",
                details={"error": str(e)},
            )
