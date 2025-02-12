"""
Module for generating static HTML pages and assets.
"""

import gzip
import json
import os
import shutil
from pathlib import Path
from typing import Any, List, Optional, Dict, Callable

import geopandas as gpd
import jinja2
import rjsmin
import topojson
from shapely import wkb
from shapely.geometry import mapping

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import (
    GenerationError,
    TemplateError,
    OutputError,
    DatabaseError,
    DataValidationError,
)
from niamoto.common.paths import PROJECT_ROOT
from niamoto.common.utils import error_handler
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from niamoto.core.components.exports.base_generator import BaseGenerator


class PageGenerator(BaseGenerator):
    """
    The PageGenerator class provides methods to generate assets webpages for taxons.
    """

    def __init__(self, config: Config) -> None:
        """
        Initializes the PageGenerator class with configuration settings.

        Args:
             config (Config): An instance of ConfigManager containing configuration settings.

        Returns:
            None

        Sets the template directory, assets source directory, output directory, and assets destination directory.
        Also configures the Jinja2 template environment.
        """

        super().__init__()
        self.config = config
        self.db = Database(config.database_path)

        # Setup paths
        self.template_dir = PROJECT_ROOT / "publish" / "templates"
        self.static_src_dir = PROJECT_ROOT / "publish" / "assets"
        self.output_dir = Path(config.get_export_config.get("web", ""))
        self.json_output_dir = self.output_dir / "json"

        # Validate paths
        self._validate_paths()

        # Setup Jinja environment
        self._init_jinja()

    def _validate_paths(self) -> None:
        """Valide l'existence des répertoires critiques."""
        if not self.template_dir.exists():
            raise TemplateError(str(self.template_dir), "Template directory not found")
        if not self.static_src_dir.exists():
            raise TemplateError(
                str(self.static_src_dir), "Static files directory not found"
            )

    def _init_jinja(self) -> None:
        """Configure l'environnement Jinja2 avec des filtres personnalisés."""
        try:
            loader = jinja2.FileSystemLoader(searchpath=str(self.template_dir))
            self.template_env = jinja2.Environment(loader=loader)
            self.template_env.filters.update(
                {"from_json": self._from_json, "numberformat": self._numberformat}
            )
        except Exception as e:
            raise TemplateError(
                str(self.template_dir),
                f"Jinja initialization failed: {str(e)}",
            )

    @error_handler(log=True, raise_error=True)
    def generate_page(
        self,
        template_name: str,
        output_name: str,
        depth: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a static page from template.

        Args:
            template_name: Template file name
            output_name: Output file name
            depth: Relative path to root
            context: Template context variables

        Returns:
            Generated page path

        Raises:
            TemplateError: If template processing fails
            OutputError: If file generation fails
        """
        context = context or {}
        context["depth"] = depth
        output_path = self.output_dir / output_name

        try:
            # Render template
            template = self.template_env.get_template(template_name)
            html_output = template.render(context)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_output, encoding="utf-8")

            return str(output_path)

        except jinja2.TemplateError as e:
            raise TemplateError(template_name, f"Template processing failed: {str(e)}")
        except Exception as e:
            raise OutputError(
                str(output_path), f"Failed to write output file: {str(e)}"
            )

    @staticmethod
    def _from_json(value):
        """Converts a JSON string to a Python object."""
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value

    @staticmethod
    def _numberformat(value):
        """Formats a number as a string with commas."""
        try:
            return "{:,.0f}".format(float(value)).replace(",", " ")
        except (ValueError, TypeError):
            return value

    @error_handler(log=True, raise_error=True)
    def _generate_item_page(
        self,
        item: Any,
        stats: Optional[Any],
        mapping_group: Dict[Any, Any],
        page_type: str,
        to_dict_method: Callable,
    ) -> str:
        """
        Generate a page for a specific item.

        Args:
            item: Object to generate page for
            stats: Statistics data
            mapping_group: Template mapping config
            page_type: Type of page
            to_dict_method: Method to convert item to dict

        Returns:
            Generated page path

        Raises:
            TemplateError: If page generation fails
        """
        try:
            item_dict = to_dict_method(item, stats)
            context = {page_type: item_dict, "stats": stats, "mapping": mapping_group}

            output_path = self.generate_page(
                template_name=f"{page_type}_template.html",
                output_name=f"{page_type}/{item.id}.html",
                depth="../",
                context=context,
            )

            self.copy_static_files()
            return output_path

        except Exception as e:
            raise TemplateError(
                f"{page_type}_template.html",
                f"Failed to generate {page_type} page: {str(e)}",
                details={"item_id": item.id},
            )

    def generate_taxon_page(
        self, taxon: TaxonRef, stats: Optional[Any], mapping_group: Dict[Any, Any]
    ) -> str:
        """Generates a webpage for a given taxon object."""
        return self._generate_item_page(
            taxon, stats, mapping_group, "taxon", self.taxon_to_dict
        )

    def generate_plot_page(
        self, plot: PlotRef, stats: Optional[Any], mapping_group: Dict[Any, Any]
    ) -> str:
        """Generates a webpage for a given plot object."""
        return self._generate_item_page(
            plot, stats, mapping_group, "plot", self.plot_to_dict
        )

    def generate_shape_page(
        self, shape: ShapeRef, stats: Optional[Any], mapping_group: Dict[Any, Any]
    ) -> str:
        """Generates a webpage for a given shape object."""
        return self._generate_item_page(
            shape, stats, mapping_group, "shape", self.shape_to_dict
        )

    @error_handler(log=True, raise_error=True)
    def get_all_shape_types(self) -> List[str]:
        """
        Get all unique shape types.

        Returns:
            List of shape types

        Raises:
            DatabaseError: If database query fails
        """
        session = self.db.session()
        try:
            shape_types = session.query(ShapeRef.type).distinct().all()
            return [shape_type[0] for shape_type in shape_types]
        except Exception as e:
            raise DatabaseError(
                "Failed to retrieve shape types", details={"error": str(e)}
            )
        finally:
            session.close()

    @error_handler(log=True, raise_error=True)
    def generate_shape_list_js(self, shapes: List[Any]) -> None:
        """
        Generate shape list JavaScript file.

        Args:
            shapes: List of shapes to process

        Raises:
            GenerationError: If generation fails
            OutputError: If file writing fails
        """
        shape_dict: Dict[str, Dict[str, Any]] = {}
        js_path = self.output_dir / "js" / "shape_list.js"

        try:
            # Process shapes
            for shape in shapes:
                if shape.type not in shape_dict:
                    shape_dict[shape.type] = {
                        "type_label": shape.type_label,
                        "features": [],
                    }

                try:
                    # Load and process geometry
                    geom = wkb.loads(shape.location, hex=True)
                    feature = self._process_shape_geometry(geom, shape)
                    if feature:
                        shape_dict[shape.type]["features"].append(feature)

                except Exception as e:
                    raise DataValidationError(
                        f"Invalid shape data for shape {shape.id}",
                        [{"shape_id": shape.id, "error": str(e)}],
                    )

            # Convert to TopoJSON
            for shape_type, type_info in shape_dict.items():
                if type_info["features"]:
                    feature_collection = {
                        "type": "FeatureCollection",
                        "features": type_info["features"],
                    }
                    try:
                        # topology = topojson.Topology(feature_collection, prequantize=True)
                        topology = topojson.Topology(
                            data=feature_collection, prequantize=True
                        ).to_dict()

                        # Additional optimization: convert coordinates to integers
                        if "arcs" in topology:
                            topology["arcs"] = [
                                [[int(x), int(y)] for x, y in arc]
                                for arc in topology["arcs"]
                            ]

                        type_info["shapes"] = topology
                        del type_info["features"]

                    except Exception as e:
                        raise DataValidationError(
                            f"TopoJSON conversion failed for shape type {shape_type}",
                            [{"shape_type": shape_type, "error": str(e)}],
                        )

            # Write output
            js_dir = self.output_dir / "js"
            js_dir.mkdir(parents=True, exist_ok=True)

            # Minified JSON string
            minified_json = json.dumps(
                shape_dict,
                separators=(",", ":"),  # Remove whitespace
                ensure_ascii=False,  # Allow UTF-8 characters
            )

            # Write development version (readable)
            js_content = f"const shapeTypes = {json.dumps(shape_dict, indent=2)};"
            js_path.write_text(js_content, encoding="utf-8")

            # Write minified version
            minified_path = js_path.with_suffix(".min.js")
            minified_content = f"const shapeTypes={minified_json};"
            minified_path.write_text(minified_content, encoding="utf-8")

            # Write gzipped version
            with gzip.open(str(js_path) + ".gz", "wt", encoding="utf-8") as f:
                f.write(f"const shapeTypes = {json.dumps(shape_dict)};")

        except Exception as e:
            if isinstance(e, (DataValidationError, OutputError)):
                raise
            raise GenerationError(
                "Failed to generate shape list",
                details={"error": str(e), "output_path": str(js_path)},
            )

    @error_handler(log=True, raise_error=True)
    def generate_plot_list_js(self, plots: List[PlotRef]) -> None:
        """
        Generate plot list JavaScript file.

        Args:
            plots (List[niamoto.core.models.models.PlotRef]): List of plots to process

        Raises:
            GenerationError: If generation fails
            OutputError: If file writing fails
        """
        js_path = self.output_dir / "js" / "plot_list.js"

        try:
            # Get plot data
            plot_list = self.get_plot_list(plots)

            # Generate and minify JavaScript
            js_content = "const plotList = " + json.dumps(plot_list, indent=4) + ";"
            minified_js = rjsmin.jsmin(js_content)

            # Write output
            js_dir = js_path.parent
            js_dir.mkdir(parents=True, exist_ok=True)
            js_path.write_text(minified_js, encoding="utf-8")

        except Exception as e:
            raise GenerationError(
                "Failed to generate plot list",
                details={"error": str(e), "output_path": str(js_path)},
            )

    @error_handler(log=True, raise_error=True)
    def build_taxonomy_tree(self, taxons: List[TaxonRef]) -> List[Dict[Any, Any]]:
        """
        Build taxonomy tree structure.

        Args:
            taxons (List[niamoto.core.models.models.TaxonRef]): List of taxons

        Returns:
            Tree structure as list of dictionaries

        Raises:
            GenerationError: If tree building fails
        """
        try:
            taxons_by_id = {int(taxon.id): taxon for taxon in taxons}
            tree = []

            for taxon in taxons:
                if taxon.parent_id is None:
                    tree.append(self.build_subtree(taxon, taxons_by_id))

            return tree
        except Exception as e:
            raise GenerationError(
                "Failed to build taxonomy tree", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def build_subtree(
        self, taxon: TaxonRef, taxons_by_id: Dict[int, TaxonRef]
    ) -> Dict[str, Any]:
        """
        Build subtree for a taxon.

        Args:
            taxon ('niamoto.core.models.models.TaxonRef'): Root taxon for subtree
            taxons_by_id (Dict[int, 'niamoto.core.models.models.TaxonRef']): Dictionary mapping taxon IDs to taxons

        Returns:
            Subtree structure as dictionary

        Raises:
            GenerationError: If subtree building fails
        """
        try:
            node = {
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
                    node["children"].append(
                        self.build_subtree(child_taxon, taxons_by_id)
                    )

            return node

        except Exception as e:
            raise GenerationError(
                f"Failed to build subtree for taxon {taxon.id}",
                details={"error": str(e)},
            )

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def get_plot_list(plots: List[PlotRef]) -> List[Dict[str, Any]]:
        """
        Get formatted plot list.

        Args:
            plots (List[niamoto.core.models.models.PlotRef]): List of plots

        Returns:
            List of plot data dictionaries

        Raises:
            GenerationError: If formatting fails
        """
        try:
            return [{"id": plot.id, "name": plot.locality} for plot in plots]
        except Exception as e:
            raise GenerationError(
                "Failed to format plot list", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def copy_static_files(self) -> None:
        """
        Copy static files to output directory.

        Raises:
            OutputError: If copy operation fails
        """
        try:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Copy each item
            for item in os.listdir(self.static_src_dir):
                src_path = self.static_src_dir / item
                dest_path = self.output_dir / item

                if src_path.is_dir():
                    shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dest_path)

        except Exception as e:
            raise OutputError(
                str(self.output_dir),
                "Failed to copy static files",
                details={"error": str(e), "source": str(self.static_src_dir)},
            )

    @error_handler(log=True, raise_error=True)
    def copy_template_page(self, template_name: str, output_name: str) -> None:
        """
        Copy template to output directory.

        Args:
            template_name: Name of template file
            output_name: Target output name

        Raises:
            TemplateError: If template not found
            OutputError: If copy fails
        """
        template_path = self.template_dir / template_name
        output_path = self.output_dir / output_name

        try:
            # Verify template exists
            if not template_path.exists():
                raise TemplateError(str(template_path), "Template file not found")

            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy template
            shutil.copy2(template_path, output_path)

        except Exception as e:
            if isinstance(e, TemplateError):
                raise
            raise OutputError(
                str(output_path),
                "Failed to copy template",
                details={"error": str(e), "template": str(template_path)},
            )

    @error_handler(log=True, raise_error=True)
    def generate_taxonomy_tree_js(self, taxons: List[TaxonRef]) -> None:
        """
        Generate taxonomy tree JavaScript file.

        Args:
            taxons (List[niamoto.core.models.models.TaxonRef]): List of taxons to process

        Raises:
            GenerationError: If generation fails
            OutputError: If file writing fails
        """
        js_path = self.output_dir / "js" / "taxonomy_tree.js"

        try:
            # Build tree structure
            tree = self.build_taxonomy_tree(taxons)

            # Generate and minify JavaScript
            js_content = "const taxonomyData = " + json.dumps(tree, indent=4) + ";"
            minified_js = rjsmin.jsmin(js_content)

            # Write output
            js_dir = js_path.parent
            js_dir.mkdir(parents=True, exist_ok=True)
            js_path.write_text(minified_js, encoding="utf-8")

        except Exception as e:
            raise GenerationError(
                "Failed to generate taxonomy tree",
                details={"error": str(e), "output_path": str(js_path)},
            )

    @error_handler(log=True, raise_error=True)
    def generate_plot_js(self, plots: List[PlotRef]) -> None:
        """
        Generate plot JavaScript file.

        Args:
            plots (List[niamoto.core.models.models.PlotRef]): List of plots to process

        Raises:
            GenerationError: If generation fails
            OutputError: If file writing fails
        """
        js_path = self.output_dir / "js" / "plot.js"

        try:
            # Get plot data
            plot_list = self.get_plot_list(plots)

            # Generate and minify JavaScript
            js_content = "const plotList = " + json.dumps(plot_list, indent=4) + ";"
            minified_js = rjsmin.jsmin(js_content)

            # Write output
            js_dir = js_path.parent
            js_dir.mkdir(parents=True, exist_ok=True)
            js_path.write_text(minified_js, encoding="utf-8")

        except Exception as e:
            raise GenerationError(
                "Failed to generate plot",
                details={"error": str(e), "output_path": str(js_path)},
            )

    @staticmethod
    def _process_shape_geometry(geom: Any, shape: ShapeRef) -> Optional[Dict[str, Any]]:
        """Process a single shape geometry."""
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")

        # Get UTM zone
        centroid = geom.centroid
        zone_number = int((centroid.x + 180) // 6) + 1
        zone_hemisphere = "N" if centroid.y >= 0 else "S"
        utm_epsg = (
            32600 + zone_number if zone_hemisphere == "N" else 32700 + zone_number
        )

        # Transform and simplify
        gdf_utm = gdf.to_crs(f"EPSG:{utm_epsg}")
        area_m2 = gdf_utm.geometry.area.iloc[0]
        tolerance = (
            5 * (area_m2 / (1000 * 1000000)) ** 0.25 if area_m2 > 1000000000 else 5
        )

        gdf_utm["geometry"] = gdf_utm.geometry.simplify(
            tolerance, preserve_topology=True
        )

        gdf_wgs = gdf_utm.to_crs("EPSG:4326")

        return {
            "type": "Feature",
            "id": shape.id,
            "properties": {
                "name": shape.label,
            },
            "geometry": mapping(gdf_wgs.geometry.iloc[0]),
        }
