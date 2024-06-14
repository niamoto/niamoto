import json
import os
import shutil
from typing import Any, List, Optional, Dict

import jinja2
import rjsmin  # type: ignore
from shapely import wkt
from shapely.geometry import mapping

from niamoto.core.models import TaxonRef, PlotRef
from niamoto.common.config import Config


class PageGenerator:
    """
    The PageGenerator class provides methods to generate static webpages for taxons.
    """

    def __init__(self, config: Config) -> None:
        """
        Initializes the PageGenerator class with configuration settings.

        Args:
             config (Config): An instance of ConfigManager containing configuration settings.

        Returns:
            None

        Sets the template directory, static source directory, output directory, and static destination directory.
        Also configures the Jinja2 template environment.
        """

        self.config = config

        self.template_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates"
        )
        self.static_src_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "static"
        )
        self.output_dir = self.config.get("outputs", "static_pages")
        self.json_output_dir = os.path.join(self.output_dir, "json")

        template_loader = jinja2.FileSystemLoader(searchpath=self.template_dir)
        self.template_env = jinja2.Environment(loader=template_loader)

    def generate_taxon_page(
            self, taxon: TaxonRef, stats: Optional[Any], mapping: Dict[Any, Any]
    ) -> str:
        """
        Generates a webpage for a given taxon object.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon object for which the webpage is generated.
            stats (dict, optional): A dictionary containing statistics for the taxon.
            mapping (dict): The mapping dictionary containing the configuration for generating the webpage.

        Returns:
            str: The path of the generated webpage.
        """
        template = self.template_env.get_template("taxon_template.html")
        taxon_dict = self.taxon_to_dict(taxon, stats)

        html_output = template.render(taxon=taxon_dict, stats=stats, mapping=mapping)
        taxon_output_dir = os.path.join(self.output_dir, "pages", "taxon")
        os.makedirs(taxon_output_dir, exist_ok=True)
        output_path = os.path.join(taxon_output_dir, f"{taxon.id}.html")
        with open(output_path, "w") as file:
            file.write(html_output)
        self.copy_static_files()
        return output_path

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
        os.makedirs(self.json_output_dir, exist_ok=True)
        taxon_output_dir = os.path.join(self.json_output_dir, "taxon")
        output_path = os.path.join(taxon_output_dir, f"{taxon.id}.json")
        os.makedirs(taxon_output_dir, exist_ok=True)
        with open(output_path, "w") as file:
            json.dump(taxon_dict, file, indent=4)
        return output_path

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

    def get_plot_list(self, plots: List[PlotRef]) -> List[Dict[str, Any]]:
        """
        Retrieves a list of plots and formats it for the template.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing plot information.
        """
        plot_list = []
        for plot in plots:
            plot_list.append({
                "id": plot.id,
                "name": plot.locality
            })
        return plot_list

    def generate_plot_page(
            self, plot: PlotRef, stats: Optional[Any], mapping: Dict[Any, Any]
    ) -> str:
        """
        Generates a webpage for a given plot object.

        Args:
            plot (niamoto.core.models.models.PlotRef): The plot object for which the webpage is generated.
            stats (dict, optional): A dictionary containing statistics for the plot.
            mapping (dict): The mapping dictionary containing the configuration for generating the webpage.

        Returns:
            str: The path of the generated webpage.
        """
        template = self.template_env.get_template("plot_template.html")
        plot_dict = self.plot_to_dict(plot, stats)
        html_output = template.render(plot=plot_dict, stats=stats, mapping=mapping)
        plot_output_dir = os.path.join(self.output_dir, "pages", "plot")
        os.makedirs(plot_output_dir, exist_ok=True)
        output_path = os.path.join(plot_output_dir, f"{plot.id}.html")
        with open(output_path, "w") as file:
            file.write(html_output)
        self.copy_static_files()
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
        os.makedirs(self.json_output_dir, exist_ok=True)
        plot_output_dir = os.path.join(self.json_output_dir, "plot")
        output_path = os.path.join(plot_output_dir, f"{plot.id}.json")
        os.makedirs(plot_output_dir, exist_ok=True)
        with open(output_path, "w") as file:
            json.dump(plot_dict, file, indent=4)
        return output_path

    def copy_static_files(self) -> None:
        """
        Copies static files to the destination directory, overwriting existing files.
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

    def taxon_to_dict(self, taxon: TaxonRef, stats: Optional[Any]) -> dict[str, Any]:
        """
        Converts a TaxonRef object and its associated statistics to a dictionary.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): A TaxonRef object.
            stats (dict, optional): A dictionary containing statistics for the taxon.

        Returns:
            dict[str, Any]: A dictionary representing the taxon data and its statistics.
        """
        taxon_dict = {
            "id": taxon.id,
            "full_name": taxon.full_name,
            "authors": taxon.authors,
            "rank_name": taxon.rank_name,
            "lft": taxon.lft,
            "rght": taxon.rght,
            "level": taxon.level,
            "parent_id": taxon.parent_id,
        }

        if stats:
            frequencies = {}
            for key, value in stats.items():
                if key.endswith("_bins"):
                    freq_key = key[:-5]  # Remove the "_bins" suffix
                    if value is not None:  # Check if value is not None
                        frequencies[freq_key] = json.loads(
                            value.replace("'", '"')
                        )  # Parse the JSON string
                else:
                    taxon_dict[key] = value

            taxon_dict["frequencies"] = frequencies

        return taxon_dict

    def plot_to_dict(self, plot: PlotRef, stats: Optional[Any]) -> dict[str, Any]:
        """
        Converts a PlotRef object and its associated statistics to a dictionary.

        Args:
            plot (niamoto.core.models.models.PlotRef): A PlotRef object.
            stats (dict, optional): A dictionary containing statistics for the plot.

        Returns:
            dict[str, Any]: A dictionary representing the plot data and its statistics.
        """
        plot_dict = {
            "id": plot.id,
            "id_locality": plot.id_locality,
            "locality": plot.locality,
            "substrat": plot.substrat,
            "geometry": mapping(wkt.loads(plot.geometry)) if plot.geometry else None,
        }

        if stats:
            frequencies = {}
            for key, value in stats.items():
                if key.endswith("_bins"):
                    freq_key = key[:-5]  # Remove the "_bins" suffix
                    if value is not None:  # Check if value is not None
                        frequencies[freq_key] = json.loads(value.replace("'", '"'))  # Parse the JSON string
                else:
                    plot_dict[key] = value

            plot_dict["frequencies"] = frequencies

        return plot_dict

