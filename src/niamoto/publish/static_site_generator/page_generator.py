import json
import os
import shutil
from typing import Any, List, Optional, Dict

import jinja2
import rjsmin  # type: ignore

from niamoto.core.models import TaxonRef
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

    def generate_taxonomy_tree_js(self, taxons: List[TaxonRef]) -> None:
        """
        Generates a JavaScript file containing the taxonomy tree data.

        Args:
            taxons (List[niamoto.core.models.models.TaxonRef]): A list of taxon objects.
        """
        tree = self.build_taxonomy_tree(taxons)
        js_content = "const taxonomyData = " + json.dumps(tree, indent=4) + ";"
        minified_js = rjsmin.jsmin(js_content)

        js_path = os.path.join(self.output_dir, "js", "taxonomy_tree.js")
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
                    freq_key = freq_key.replace(
                        "_", "-"
                    )  # Replace "_" with "-" for other keys
                    if value is not None:  # Check if value is not None
                        frequencies[freq_key] = json.loads(
                            value.replace("'", '"')
                        )  # Parse the JSON string
                else:
                    taxon_dict[key] = value

            taxon_dict["frequencies"] = frequencies

        return taxon_dict
