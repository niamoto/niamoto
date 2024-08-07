import json
import os
from typing import Any, List, Optional, cast, Dict, Union

from shapely import wkt
from shapely.geometry import mapping

from niamoto.common.config import Config
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from niamoto.publish.common.base_generator import BaseGenerator


class ApiGenerator(BaseGenerator):
    """
    The ApiGenerator class provides methods to generate JSON files for taxons and plots.
    """

    def __init__(self, config: Config) -> None:
        """
        Initializes the ApiGenerator class with the directory for JSON output.

        Args:
            config (Config): An instance of Config containing configuration settings.
        """
        self.config = config
        self.json_output_dir: str = cast(
            str, os.path.join(self.config.get("outputs", "static_api"))
        )

    def generate_taxon_json(self, taxon: TaxonRef, stats: Optional[Any]) -> str:
        """
        Generates a JSON file for a given taxon object.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon object for which the JSON file is generated.
            stats (dict, optional): A dictionary containing statistics for the taxon.

        Returns:
            str: The path of the generated JSON file.
        """
        taxon_dict = self.taxon_to_dict(taxon, stats)
        taxon_output_dir = os.path.join(self.json_output_dir, "taxon")
        os.makedirs(taxon_output_dir, exist_ok=True)
        output_path = os.path.join(taxon_output_dir, f"{taxon.id}.json")
        with open(output_path, "w") as file:
            json.dump(taxon_dict, file, indent=4)
        return output_path

    def generate_plot_json(self, plot: PlotRef, stats: Optional[Any]) -> str:
        """
        Generates a JSON file for a given plot object.

        Args:
            plot (niamoto.core.models.models.PlotRef): The plot object for which the JSON file is generated.
            stats (dict, optional): A dictionary containing statistics for the plot.

        Returns:
            str: The path of the generated JSON file.
        """
        plot_dict = self.plot_to_dict(plot, stats)
        plot_output_dir = os.path.join(self.json_output_dir, "plot")
        os.makedirs(plot_output_dir, exist_ok=True)
        output_path = os.path.join(plot_output_dir, f"{plot.id}.json")
        with open(output_path, "w") as file:
            json.dump(plot_dict, file, indent=4)
        return output_path

    def generate_shape_json(self, shape: ShapeRef, stats: Optional[Any]) -> str:
        """
        Generates a JSON file for a given shape object.

        Args:
            shape (niamoto.core.models.models.ShapeRef): The shape object for which the JSON file is generated.
            stats (dict, optional): A dictionary containing statistics for the shape.

        Returns:
            str: The path of the generated JSON file.
        """
        # Convert WKT to GeoJSON
        if shape.location is not None:
            geometry_str = str(shape.location)
            geometry = wkt.loads(geometry_str)
            geojson_geometry = mapping(geometry)

        shape_dict = self.shape_to_dict(shape, stats)
        if geojson_geometry is not None:
            shape_dict["geometry"] = geojson_geometry

        shape_output_dir = os.path.join(self.json_output_dir, "shape")
        os.makedirs(shape_output_dir, exist_ok=True)
        output_path = os.path.join(shape_output_dir, f"{shape.id}.json")
        with open(output_path, "w") as file:
            json.dump(shape_dict, file, indent=4)
        return output_path

    def generate_all_taxa_json(self, taxa: List[TaxonRef]) -> str:
        """
        Generates a JSON file that contains all taxon objects in a simplified format,
        along with the total number of taxa.

        Args:
            taxa (list of niamoto.core.models.models.TaxonRef): A list of taxon objects.

        Returns:
            str: The path of the generated JSON file.
        """
        all_taxa = [self.taxon_to_simple_dict(taxon) for taxon in taxa]
        output_data = {"total": len(all_taxa), "taxa": all_taxa}
        os.makedirs(self.json_output_dir, exist_ok=True)
        output_path = os.path.join(self.json_output_dir, "all_taxa.json")
        with open(output_path, "w") as file:
            json.dump(output_data, file, indent=4)
        return output_path

    def generate_all_plots_json(self, plots: List[PlotRef]) -> str:
        """
        Generates a JSON file that contains all plot objects in a simplified format,
        along with the total number of plots.

        Args:
            plots (list of niamoto.core.models.models.PlotRef): A list of plot objects.

        Returns:
            str: The path of the generated JSON file.
        """
        all_plots = [self.plot_to_simple_dict(plot) for plot in plots]
        output_data = {"total": len(all_plots), "plots": all_plots}
        os.makedirs(self.json_output_dir, exist_ok=True)
        output_path = os.path.join(self.json_output_dir, "all_plots.json")
        with open(output_path, "w") as file:
            json.dump(output_data, file, indent=4)
        return output_path

    def generate_all_shapes_json(self, shapes: List[ShapeRef]) -> str:
        """
        Generates a JSON file that contains all shape objects in a simplified format,
        along with the total number of shapes.

        Args:
            shapes (list of niamoto.core.models.models.ShapeRef): A list of shape objects.

        Returns:
            str: The path of the generated JSON file.
        """
        all_shapes = [self.shape_to_simple_dict(shape) for shape in shapes]
        output_data = {"total": len(all_shapes), "shapes": all_shapes}
        os.makedirs(self.json_output_dir, exist_ok=True)
        output_path = os.path.join(self.json_output_dir, "all_shapes.json")
        with open(output_path, "w") as file:
            json.dump(output_data, file, indent=4)
        return output_path

    @staticmethod
    def taxon_to_simple_dict(taxon: TaxonRef) -> Dict[str, Union[str, int]]:
        """
        Converts a TaxonRef object to a simplified dictionary.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon object to convert.

        Returns:
            dict: A dictionary representation of the taxon.
        """
        return {
            "id": int(taxon.id),
            "name": str(taxon.full_name),
            "metadata": taxon.extra_data,
            "endpoint": f"/api/taxon/{taxon.id}.json",
        }

    @staticmethod
    def plot_to_simple_dict(plot: PlotRef) -> Dict[str, Union[str, int]]:
        """
        Converts a PlotRef object to a simplified dictionary.

        Args:
            plot (niamoto.core.models.models.PlotRef): The plot object to convert.

        Returns:
            dict: A dictionary representation of the plot.
        """
        return {
            "id": int(plot.id),
            "name": str(plot.locality),
            "endpoint": f"/api/plot/{plot.id}.json",
        }

    @staticmethod
    def shape_to_simple_dict(shape: ShapeRef) -> Dict[str, Union[str, int]]:
        """
        Converts a ShapeRef object to a simplified dictionary.

        Args:
            shape (niamoto.core.models.models.ShapeRef): The shape object to convert.

        Returns:
            dict: A dictionary representation of the shape.
        """
        return {
            "id": int(shape.id),
            "name": str(shape.label),
            "type": str(shape.type),
            "endpoint": f"/api/shape/{shape.id}.json",
        }
