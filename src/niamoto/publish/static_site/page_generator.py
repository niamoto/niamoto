import json
import os
import shutil
from typing import Any, List, Optional, Dict

import jinja2
import rjsmin  # type: ignore
from shapely import wkt
from shapely.geometry import mapping

from niamoto.common.database import Database
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from niamoto.common.config import Config
from niamoto.publish.common.base_generator import BaseGenerator


class PageGenerator(BaseGenerator):
    """
    The PageGenerator class provides methods to generate static_files webpages for taxons.
    """

    def __init__(self, config: Config) -> None:
        """
        Initializes the PageGenerator class with configuration settings.

        Args:
             config (Config): An instance of ConfigManager containing configuration settings.

        Returns:
            None

        Sets the template directory, static_files source directory, output directory, and static_files destination directory.
        Also configures the Jinja2 template environment.
        """

        self.config = config
        self.db = Database(config.database_path)

        self.template_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates"
        )
        self.static_src_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "static_files"
        )
        self.output_dir = self.config.get("outputs", "static_site")
        self.json_output_dir = os.path.join(self.output_dir, "json")

        template_loader = jinja2.FileSystemLoader(searchpath=self.template_dir)
        self.template_env = jinja2.Environment(loader=template_loader)

    def generate_page(
        self,
        template_name: str,
        output_name: str,
        depth: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generates a static page using Jinja2 templates.

        Args:
            template_name (str): The name of the template file.
            output_name (str): The name of the output file.
            depth (str): The relative path to the root (e.g., '../../' for two levels up).
            context (dict, optional): A dictionary of context variables for the template.

        Returns:
            str: The path of the generated page.
        """
        if context is None:
            context = {}

        context["depth"] = depth  # Add the depth variable to the context
        template = self.template_env.get_template(template_name)
        html_output = template.render(context)
        output_path = os.path.join(self.output_dir, output_name)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as file:
            file.write(html_output)
        return output_path

    def generate_taxon_page(
        self, taxon: TaxonRef, stats: Optional[Any], mapping_group: Dict[Any, Any]
    ) -> str:
        """
        Generates a webpage for a given taxon object.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon object for which the webpage is generated.
            stats (dict, optional): A dictionary containing statistics for the taxon.
            mapping_group (dict): The mapping dictionary containing the configuration for generating the webpage.

        Returns:
            str: The path of the generated webpage.
        """
        template = self.template_env.get_template("taxon_template.html")
        taxon_dict = self.taxon_to_dict(taxon, stats)
        context = {
            "taxon": taxon_dict,
            "stats": stats,
            "mapping": mapping_group,
            "depth": "../",  # This assumes taxon pages are one level deep
        }

        html_output = template.render(context)
        taxon_output_dir = os.path.join(self.output_dir, "taxon")
        os.makedirs(taxon_output_dir, exist_ok=True)
        output_path = os.path.join(taxon_output_dir, f"{taxon.id}.html")
        with open(output_path, "w") as file:
            file.write(html_output)
        self.copy_static_files()
        return output_path

    def generate_plot_page(
        self, plot: PlotRef, stats: Optional[Any], mapping_group: Dict[Any, Any]
    ) -> str:
        """
        Generates a webpage for a given plot object.

        Args:
            plot (niamoto.core.models.models.PlotRef): The plot object for which the webpage is generated.
            stats (dict, optional): A dictionary containing statistics for the plot.
            mapping_group (dict): The mapping dictionary containing the configuration for generating the webpage.

        Returns:
            str: The path of the generated webpage.
        """

        template = self.template_env.get_template("plot_template.html")
        plot_dict = self.plot_to_dict(plot, stats)
        context = {
            "plot": plot_dict,
            "stats": stats,
            "mapping": mapping_group,
            "depth": "../",  # This assumes plot pages are one level deep
        }

        html_output = template.render(context)
        plot_output_dir = os.path.join(self.output_dir, "plot")
        os.makedirs(plot_output_dir, exist_ok=True)
        output_path = os.path.join(plot_output_dir, f"{plot.id}.html")
        with open(output_path, "w") as file:
            file.write(html_output)
        self.copy_static_files()
        return output_path

    def generate_shape_page(
        self, shape: ShapeRef, stats: Optional[Any], mapping_group: Dict[Any, Any]
    ) -> str:
        """
        Generates a webpage for a given shape object.

        Args:
            shape (niamoto.core.models.models.ShapeRef): The shape object for which the webpage is generated.
            stats (dict, optional): A dictionary containing statistics for the shape.
            mapping_group (dict): The mapping dictionary containing the configuration for generating the webpage.

        Returns:
            str: The path of the generated webpage.
        """

        def from_json(value):
            """
            Converts a JSON string to a Python object.
            Args:
                value (str): The JSON string to be converted.
            Returns:
                Any: The converted object.
            """
            import json

            try:
                return json.loads(value)
            except (ValueError, TypeError):
                return value

        def numberformat(value):
            """
            Formats a number as a string with commas.
            Args:
                value (str): The number to be formatted.

            Returns:
                str: The formatted number as a string with commas.
            """
            try:
                return "{:,.0f}".format(float(value)).replace(",", " ")
            except (ValueError, TypeError):
                return value

        # Ajout des filtres à l'environnement Jinja
        self.template_env.filters["from_json"] = from_json
        self.template_env.filters["numberformat"] = numberformat

        template = self.template_env.get_template("shape_template.html")
        shape_dict = self.shape_to_dict(shape, stats)

        # Here you should retrieve all the shape types for the sidebar
        shape_types = (
            self.get_all_shape_types()
        )  # Ensure you have a method to get all shape types

        context = {
            "shape": shape_dict,
            "stats": stats,
            "mapping": mapping_group,
            "depth": "../",  # This assumes shape pages are one level deep
            "shape_types": shape_types,  # Add shape_types to the context
        }

        html_output = template.render(context)
        shape_output_dir = os.path.join(self.output_dir, "shape")
        os.makedirs(shape_output_dir, exist_ok=True)
        output_path = os.path.join(shape_output_dir, f"{shape.id}.html")
        with open(output_path, "w") as file:
            file.write(html_output)
        self.copy_static_files()
        return output_path

    def get_all_shape_types(self) -> List[str]:
        """
        Retrieve all unique shape types from the database.

        Returns:
            List[str]: A list of unique shape types.
        """
        session = self.db.session()
        shape_types = session.query(ShapeRef.type).distinct().all()
        session.close()
        return [shape_type[0] for shape_type in shape_types]

    def generate_shape_list_js(self, shapes: List[Any]) -> None:
        """
        Generates a JavaScript file containing the list of shapes grouped by type.

        Args:
            shapes (List[niamoto.core.models.Shape]): A list of shape objects.
        """
        shape_dict: Dict[str, Dict[str, Any]] = {}
        for shape in shapes:
            if shape.type not in shape_dict:
                shape_dict[shape.type] = {
                    "type_label": shape.type_label,  # Assuming shape objects have a type_label attribute
                    "shapes": [],
                }
            geom = wkt.loads(shape.location)
            simplified_geom = geom.simplify(
                0.01, preserve_topology=True
            )  # Simplify geometry
            geojson_geom = mapping(simplified_geom)

            shape_dict[shape.type]["shapes"].append(
                {
                    "id": shape.id,
                    "name": shape.label,
                    "geometry": geojson_geom,  # Use simplified GeoJSON geometry
                }
            )

        shape_types = [
            {
                "type": type_name,
                "type_label": type_info["type_label"],
                "shapes": type_info["shapes"],
            }
            for type_name, type_info in shape_dict.items()
        ]

        shape_list_path = os.path.join(self.output_dir, "js", "shape_list.js")
        with open(shape_list_path, "w") as shape_list_file:
            shape_list_file.write(
                f"const shapeTypes = {json.dumps(shape_types, indent=4)};"
            )

    def generate_taxonomy_tree_js(self, taxons: List[TaxonRef]) -> None:
        """
        Generates a JavaScript file containing the taxonomy tree data.

        Args:
            taxons (List[niamoto.core.models.models.TaxonRef]): A list of taxon objects.
        """
        tree = self.build_taxonomy_tree(taxons)
        js_content = "const taxonomyData = " + json.dumps(tree, indent=4) + ";"
        minified_js = rjsmin.jsmin(js_content)

        js_dir = os.path.join(self.output_dir, "js")
        os.makedirs(js_dir, exist_ok=True)  # Ensure the directory exists
        js_path = os.path.join(js_dir, "taxonomy_tree.js")
        with open(js_path, "w") as file:
            file.write(minified_js)

    def generate_plot_list_js(self, plots: List[PlotRef]) -> None:
        """
        Generates a JavaScript file containing the plot list data.

        Args:
            plots (List[niamoto.core.models.models.PlotRef]): A list of plot objects.
        """
        plot_list = self.get_plot_list(plots)
        js_content = "const plotList = " + json.dumps(plot_list, indent=4) + ";"
        minified_js = rjsmin.jsmin(js_content)

        js_dir = os.path.join(self.output_dir, "js")
        os.makedirs(js_dir, exist_ok=True)
        js_path = os.path.join(js_dir, "plot_list.js")
        with open(js_path, "w") as file:
            file.write(minified_js)

    def build_taxonomy_tree(self, taxons: List[TaxonRef]) -> List[Dict[Any, Any]]:
        """
        Builds a taxonomy tree from a list of taxon objects.

        Args:
            taxons (List[niamoto.core.models.models.TaxonRef]): A list of taxon objects.

        Returns:
            List[Dict[Any, Any]]: A list of dictionaries representing the taxonomy tree.
        """
        taxons_by_id = {int(taxon.id): taxon for taxon in taxons}
        tree = []

        for taxon in taxons:
            if taxon.parent_id is None:
                tree.append(self.build_subtree(taxon, taxons_by_id))

        return tree

    def build_subtree(
        self, taxon: TaxonRef, taxons_by_id: Dict[int, TaxonRef]
    ) -> Dict[str, Any]:
        """
        Builds a subtree for a given taxon object.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon object for which the subtree is built.
            taxons_by_id (Dict[int, niamoto.core.models.models.TaxonRef]): A dictionary mapping taxon IDs to taxon objects.

        Returns:
            Dict[str, Any]: A dictionary representing the subtree.
        """
        node: Dict[str, Any] = {
            "id": taxon.id,
            "name": taxon.full_name,
            "children": [],
        }

        left = taxon.lft
        right = taxon.rght

        for child_id, child_taxon in taxons_by_id.items():
            if (
                child_taxon.parent_id == taxon.id
                and left < child_taxon.lft < child_taxon.rght < right
            ):
                node["children"].append(self.build_subtree(child_taxon, taxons_by_id))

        return node

    @staticmethod
    def get_plot_list(plots: List[PlotRef]) -> List[Dict[str, Any]]:
        """
        Retrieves a list of plots and formats it for the template.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing plot information.
        """
        plot_list = []
        for plot in plots:
            plot_list.append({"id": plot.id, "name": plot.locality})
        return plot_list

    def copy_static_files(self) -> None:
        """
        Copies static_files files to the destination directory, overwriting existing files.
        """
        # Create the destination directory if it does not exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Copy each item in the source directory
        for item in os.listdir(self.static_src_dir):
            src_path = os.path.join(self.static_src_dir, item)
            dest_path = os.path.join(self.output_dir, item)

            if os.path.isdir(src_path):
                # shutil.copytree will overwrite files in the destination directory if dirs_exist_ok=True
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dest_path)

    def copy_template_page(self, template_name: str, output_name: str) -> None:
        """
        Copies a template page to the output directory.

        Args:
            template_name (str): The name of the template file to be copied.
            output_name (str): The name of the output file.

        Returns:
            None
        """
        template_path = os.path.join(self.template_dir, template_name)
        output_path = os.path.join(self.output_dir, output_name)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy2(template_path, output_path)
