import os
import shutil
import json
import rjsmin  # type: ignore
import jinja2
from niamoto.common.config_manager import ConfigManager
from niamoto.db.models.models import Taxon
from typing import Any, List


class PageGenerator:
    def __init__(self, config: ConfigManager) -> None:
        """
        Initializes the PageGenerator class with configuration settings.

        :param config: An instance of ConfigManager containing configuration settings.

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
        self.output_dir = self.config.get("web", "static_pages")

        template_loader = jinja2.FileSystemLoader(searchpath=self.template_dir)
        self.template_env = jinja2.Environment(loader=template_loader)

    def generate_taxon_page(self, taxon: Taxon) -> str:
        """
        Generates a webpage for a given taxon object.

        Args:
            taxon (Taxon): The taxon object for which the webpage is generated.

        Returns:
            str: The path of the generated webpage.
        """
        template = self.template_env.get_template("taxon_template.html")
        taxon_dict = self.taxon_to_dict(taxon)
        html_output = template.render(taxon=taxon_dict)

        taxon_output_dir = os.path.join(self.output_dir, "pages", "taxon")
        os.makedirs(taxon_output_dir, exist_ok=True)

        output_path = os.path.join(taxon_output_dir, f"{taxon.id_taxonref}.html")
        with open(output_path, "w") as file:
            file.write(html_output)

        self.copy_static_files()

        return output_path

    def generate_taxonomy_tree_js(self, taxons: List[Taxon]) -> None:
        tree = self.build_taxonomy_tree(taxons)
        js_content = "const taxonomyData = " + json.dumps(tree, indent=4) + ";"
        minified_js = rjsmin.jsmin(js_content)

        js_path = os.path.join(self.output_dir, "js", "taxonomy_tree.js")
        with open(js_path, "w") as file:
            file.write(minified_js)

    @staticmethod
    def build_taxonomy_tree(taxons: List[Any]) -> Any:
        tree = {}
        for taxon in taxons:
            if taxon.full_name is None:
                continue
            tree[taxon.id] = {
                "id": taxon.id_taxonref,
                "name": taxon.full_name,
                "parent_id": taxon.parent_id,
                "children": [],
            }

        for id, node in tree.items():
            parent_id = node["parent_id"]
            if parent_id and parent_id in tree:
                tree[parent_id]["children"].append(node)

        root_nodes = [node for node in tree.values() if node["parent_id"] is None]
        return root_nodes

    def copy_static_files(self) -> None:
        """
        Copies static files to the destination directory, overwriting existing files.

        The destination directory is created if it doesn't exist.
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

    @staticmethod
    def taxon_to_dict(taxon: Taxon) -> dict[str, Any]:
        """
        Converts a Taxon object to a dictionary.

        Args:
            taxon: A Taxon object.

        Returns:
            A dictionary representing the taxon data.
        """
        return {
            "id": taxon.id,
            "full_name": taxon.full_name,
            "rank_name": taxon.rank_name,
            "occ_count": taxon.occ_count,
            "occ_um_count": taxon.occ_um_count,
            "dbh_max": taxon.dbh_max,
            "dbh_avg": taxon.dbh_avg,
            "freq_max": taxon.freq_max,
            "height_max": taxon.height_max,
            "wood_density_avg": taxon.wood_density_avg,
            "wood_density_min": taxon.wood_density_min,
            "wood_density_max": taxon.wood_density_max,
            "bark_thickness_avg": taxon.bark_thickness_avg,
            "bark_thickness_min": taxon.bark_thickness_min,
            "bark_thickness_max": taxon.bark_thickness_max,
            "leaf_sla_avg": taxon.leaf_sla_avg,
            "leaf_sla_min": taxon.leaf_sla_min,
            "leaf_sla_max": taxon.leaf_sla_max,
            "leaf_area_avg": taxon.leaf_area_avg,
            "leaf_area_min": taxon.leaf_area_min,
            "leaf_area_max": taxon.leaf_area_max,
            "leaf_thickness_avg": taxon.leaf_thickness_avg,
            "leaf_thickness_min": taxon.leaf_thickness_min,
            "leaf_thickness_max": taxon.leaf_thickness_max,
            "leaf_ldmc_avg": taxon.leaf_ldmc_avg,
            "leaf_ldmc_min": taxon.leaf_ldmc_min,
            "leaf_ldmc_max": taxon.leaf_ldmc_max,
            "frequencies": taxon.frequencies,
            "geo_pts_pn": taxon.geo_pts_pn,
        }
