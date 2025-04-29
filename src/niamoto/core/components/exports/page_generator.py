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
from sqlalchemy.sql import text

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
        # Create new context to avoid modifying the original
        template_context = context.copy() if context else {}

        # Add depth to context
        template_context["depth"] = depth

        try:
            # Render template
            template = self.template_env.get_template(template_name)
            html_output = template.render(
                **template_context
            )  # Use ** to unpack the dictionary

            # Write output
            output_path = self.output_dir / output_name
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

            # Get base context
            base_context = {}
            if hasattr(self, "get_first_ids"):
                base_context["first_ids"] = self.get_first_ids()

            # Add page specific context
            context = {page_type: item_dict, "stats": stats, "mapping": mapping_group}

            # Merge contexts
            context.update(base_context)

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
            ) from e

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
            ) from e
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
            ) from e

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
            ) from e

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
            ) from e

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
            ) from e

    @error_handler(log=True, raise_error=True)
    def get_plot_list(self, plots: List[PlotRef]) -> List[Dict[str, Any]]:
        """
        Get formatted plot list, sorted alphabetically by locality.

        Args:
            plots (List[niamoto.core.models.models.PlotRef]): List of plots

        Returns:
            List of plot data dictionaries, sorted by locality name

        Raises:
            GenerationError: If formatting fails
        """
        try:
            return sorted(
                [{"id": plot.id, "name": plot.locality} for plot in plots],
                key=lambda x: x["name"].lower(),
            )
        except Exception as e:
            raise GenerationError(
                "Failed to format plot list", details={"error": str(e)}
            ) from e

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
            ) from e

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
            ) from e

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
            ) from e

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
            ) from e

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

    def get_first_ids(self):
        """Get first available ID for each type.

        Returns:
            dict: A dictionary with first available ID for each type (taxon, plot, shape)
        """
        session = self.db.session()

        try:
            first_ids = {"taxon": None, "plot": None, "shape": None}

            # Get taxon ID
            first_taxon = session.query(TaxonRef).order_by(TaxonRef.id).first()
            if first_taxon is not None:
                first_ids["taxon"] = int(first_taxon.id)  # Ensure it's a plain integer

            # Get plot ID
            first_plot = session.query(PlotRef).order_by(PlotRef.id).first()
            if first_plot is not None:
                first_ids["plot"] = int(first_plot.id)  # Ensure it's a plain integer

            # Get shape ID
            first_shape = session.query(ShapeRef).order_by(ShapeRef.id).first()
            if first_shape is not None:
                first_ids["shape"] = int(first_shape.id)  # Ensure it's a plain integer

            return first_ids

        except Exception as e:
            raise DatabaseError(
                "Failed to get first IDs", details={"error": str(e)}
            ) from e
        finally:
            session.close()

    @error_handler(log=True, raise_error=True)
    def generate_taxon_index_page(self, taxons: List[TaxonRef]) -> str:
        """
        Generate an index page for all taxons with search and pagination.
        Only includes taxons with rank "species" or "infra".

        Args:
            taxons: List of taxons to include

        Returns:
            Path to the generated page

        Raises:
            TemplateError: If template processing fails
            OutputError: If file generation fails
        """
        try:
            # Get taxonomy configuration
            taxonomy_config = self.config.get_imports_config.get("taxonomy", {})
            ranks_config = taxonomy_config.get("ranks", "")

            # Split ranks into list, handling potential spaces
            configured_ranks = [r.strip() for r in ranks_config.split(",") if r.strip()]

            # Get the species and infra level column names from configuration
            # Default to standard names if not in config
            species_column = None
            infra_column = None

            # Extract from occurrence_columns if available
            occ_columns = taxonomy_config.get("occurrence_columns", {})
            if "species" in occ_columns:
                species_column = occ_columns["species"]
            if "infra" in occ_columns:
                infra_column = occ_columns["infra"]

            # Fallback logic if not found in occurrence_columns
            if not species_column and len(configured_ranks) > 2:
                species_column = configured_ranks[2]  # Usually the 3rd rank is species

            if not infra_column and len(configured_ranks) > 3:
                infra_column = configured_ranks[
                    3
                ]  # Usually the 4th rank is infraspecies

            # Convert taxons to simple dictionaries
            taxa_data = []

            for taxon in taxons:
                # Get stats if available
                try:
                    with self.db.engine.connect() as connection:
                        result = connection.execute(
                            text("SELECT * FROM taxon WHERE taxon_id = :id"),
                            {"id": taxon.id},
                        )
                        stats_row = result.fetchone()
                        if not stats_row:
                            continue

                        # Convert to dict - map column names to values
                        stats = dict(zip(result.keys(), stats_row))

                        # Extract information from general_info
                        if "general_info" in stats:
                            general_info = self.parse_json_field(stats["general_info"])
                            if not general_info:
                                continue

                            # Check if this is a species or infra
                            if "rank" not in general_info or not isinstance(
                                general_info["rank"], dict
                            ):
                                continue

                            rank_value = general_info["rank"].get("value")
                            # Check against configured column names instead of hardcoded values
                            valid_ranks = []
                            if species_column:
                                valid_ranks.append(species_column)
                            if infra_column:
                                valid_ranks.append(infra_column)

                            # If we couldn't determine valid ranks from config, fall back to defaults
                            if not valid_ranks:
                                valid_ranks = ["species", "infra"]

                            if not rank_value or rank_value not in valid_ranks:
                                continue

                            # Create taxon data with extracted fields
                            taxon_data = {
                                "id": taxon.id,
                                "name": general_info.get("name", {}).get(
                                    "value", taxon.full_name
                                ),
                            }

                            # Extract other fields with "value" structure
                            fields_to_extract = [
                                "rank",
                                "taxon_type",
                                "parent_family",
                                "parent_genus",
                                "occurrences_count",
                                "endemic",
                                "redlist_cat",
                                "endemia_url",
                                "id_florical",
                                "image_url",
                            ]

                            for field in fields_to_extract:
                                if field in general_info and isinstance(
                                    general_info[field], dict
                                ):
                                    taxon_data[field] = general_info[field].get("value")

                            # Extract images list if available
                            if "images" in general_info and isinstance(
                                general_info["images"], dict
                            ):
                                try:
                                    # Images might be stored as a string representation of a list
                                    images_value = general_info["images"].get("value")
                                    if isinstance(images_value, str):
                                        taxon_data["images"] = json.loads(
                                            images_value.replace("'", '"')
                                        )
                                    else:
                                        taxon_data["images"] = images_value
                                except (json.JSONDecodeError, ValueError):
                                    # Handle parsing errors gracefully
                                    pass

                            taxa_data.append(taxon_data)

                except Exception as e:
                    # Log the error but continue
                    print(f"Error getting stats for taxon {taxon.id}: {str(e)}")
                    continue

            # Sort by name
            taxa_data.sort(key=lambda x: x["name"].lower())

            # Ensure output directory exists
            output_dir = self.output_dir / "taxon"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Render the template
            rendered_path = self.generate_page(
                template_name="taxon_index.html",
                output_name="taxon/index.html",
                depth="../",
                context={"taxa_data": taxa_data},
            )

            return rendered_path

        except Exception as e:
            raise TemplateError(
                "taxon_index.html",
                f"Failed to generate taxon index page: {str(e)}",
                details={"error": str(e)},
            ) from e

    @error_handler(log=True, raise_error=True)
    def generate_plot_index_page(self, plots: List[PlotRef]) -> str:
        """
        Generate an index page for all plots with search and pagination.

        Args:
            plots: List of plots to include

        Returns:
            Path to the generated page

        Raises:
            TemplateError: If template processing fails
            OutputError: If file generation fails
        """
        try:
            # Convert plots to dictionaries with relevant information
            plots_data = []
            for plot in plots:
                # Create plot data
                plot_data = {"id": plot.id, "name": plot.locality}

                # Get stats if available
                try:
                    with self.db.engine.connect() as connection:
                        result = connection.execute(
                            text("SELECT * FROM plot WHERE plot_id = :id"),
                            {"id": plot.id},
                        )
                        stats_row = result.fetchone()
                        if stats_row:
                            # Convert to dict - map column names to values
                            stats = dict(zip(result.keys(), stats_row))

                            # Add additional info if available
                            if "general_info" in stats:
                                general_info = self.parse_json_field(
                                    stats["general_info"]
                                )
                                if general_info:
                                    for key in [
                                        "elevation",
                                        "rainfall",
                                        "holdridge",
                                        "in_um",
                                        "occurrences_count",
                                        "nb_species",
                                    ]:
                                        if key in general_info:
                                            plot_data[key] = general_info[key]
                except Exception as e:
                    # Log the error but continue
                    print(f"Error getting stats for plot {plot.id}: {str(e)}")

                plots_data.append(plot_data)

            # Sort by name
            plots_data.sort(key=lambda x: x["name"].lower())

            # Ensure output directory exists
            output_dir = self.output_dir / "plot"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Render the template
            output_path = self.generate_page(
                template_name="plot_index.html",
                output_name="plot/index.html",
                depth="../",
                context={"plots_data": plots_data},
            )

            return output_path

        except Exception as e:
            raise TemplateError(
                "plot_index.html",
                f"Failed to generate plot index page: {str(e)}",
                details={"error": str(e)},
            ) from e

    @error_handler(log=True, raise_error=True)
    def generate_shape_index_page(self, shapes: List[ShapeRef]) -> str:
        """
        Generate an index page for all shapes, grouped by shape type.

        Args:
            shapes: List of shapes to include

        Returns:
            Path to the generated page

        Raises:
            TemplateError: If template processing fails
            OutputError: If file generation fails
        """
        # Définir output_path dès le début pour éviter des erreurs
        output_path = str(self.output_dir / "shape" / "index.html")

        try:
            # Grouper les formes par type
            shapes_by_type = {}

            for shape in shapes:
                # Initialiser le groupe si ce type n'existe pas encore
                if shape.type not in shapes_by_type:
                    shapes_by_type[shape.type] = {
                        "type_label": shape.type_label or shape.type,
                        "shapes": [],
                    }

                # Créer les données de base de la forme
                shape_data = {"id": shape.id, "name": shape.label, "type": shape.type}

                # Essayer d'obtenir des statistiques supplémentaires si disponibles
                try:
                    with self.db.engine.connect() as connection:
                        result = connection.execute(
                            text("SELECT * FROM shape WHERE shape_id = :id"),
                            {"id": shape.id},
                        )
                        stats_row = result.fetchone()

                        if stats_row:
                            # Convertir en dict - associer les noms de colonnes aux valeurs
                            stats = dict(zip(result.keys(), stats_row))

                            # Ajouter des infos supplémentaires si disponibles
                            if "general_info" in stats:
                                try:
                                    general_info = self.parse_json_field(
                                        stats["general_info"]
                                    )

                                    if general_info and isinstance(general_info, dict):
                                        # Extraire des valeurs pour les champs d'intérêt
                                        for key in [
                                            "land_area_ha",
                                            "forest_area_ha",
                                            "elevation_median",
                                        ]:
                                            if key in general_info:
                                                value = general_info[key]

                                                # Valeur primitive simple
                                                if isinstance(value, (int, float)):
                                                    shape_data[key] = value
                                                # Dictionnaire imbriqué avec clé "value"
                                                elif (
                                                    isinstance(value, dict)
                                                    and "value" in value
                                                ):
                                                    try:
                                                        # Convertir en nombre si possible
                                                        shape_data[key] = float(
                                                            value["value"]
                                                        )
                                                    except (ValueError, TypeError):
                                                        shape_data[key] = value["value"]
                                except Exception as e:
                                    print(
                                        f"Error parsing general_info for shape {shape.id}: {str(e)}"
                                    )
                except Exception as e:
                    print(f"Error getting stats for shape {shape.id}: {str(e)}")

                # Ajouter cette forme à son groupe
                shapes_by_type[shape.type]["shapes"].append(shape_data)

            # Trier les formes dans chaque groupe par nom
            for shape_type in shapes_by_type:
                shapes_by_type[shape_type]["shapes"].sort(
                    key=lambda x: str(x.get("name", "")).lower()
                )

            # Trier les types par ordre alphabétique
            sorted_shapes_by_type = dict(
                sorted(shapes_by_type.items(), key=lambda x: x[0].lower())
            )

            # S'assurer que les données sont sérialisables en JSON
            try:
                json.dumps(sorted_shapes_by_type)
            except TypeError as e:
                print(f"JSON serialization error: {str(e)}")
                # Si la sérialisation échoue, créer une version simplifiée
                simplified_data = {}

                for type_name, type_info in sorted_shapes_by_type.items():
                    simplified_shapes = []

                    for shape in type_info["shapes"]:
                        simple_shape = {
                            "id": shape.get("id", 0),
                            "name": str(shape.get("name", "")),
                            "type": str(shape.get("type", "")),
                        }

                        # Ajouter d'autres champs si convertibles en types simples
                        for key in [
                            "land_area_ha",
                            "forest_area_ha",
                            "elevation_median",
                        ]:
                            if key in shape:
                                try:
                                    simple_shape[key] = float(shape[key])
                                except (ValueError, TypeError):
                                    simple_shape[key] = str(shape[key])

                        simplified_shapes.append(simple_shape)

                    simplified_data[type_name] = {
                        "type_label": str(type_info.get("type_label", type_name)),
                        "shapes": simplified_shapes,
                    }

                sorted_shapes_by_type = simplified_data

            # Assurer que le répertoire de sortie existe
            output_dir = self.output_dir / "shape"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Générer la page
            template_name = "shape_index.html"
            output_name = "shape/index.html"

            output_path = self.generate_page(
                template_name=template_name,
                output_name=output_name,
                depth="../",
                context={"shapes_by_type": shapes_by_type},
            )

            return output_path

        except Exception as e:
            # Logger l'erreur avec des informations détaillées
            print(f"Failed to generate shape index page: {str(e)}")
            import traceback

            traceback.print_exc()

            # Lever une erreur appropriée
            raise TemplateError(
                "shape_index.html",
                f"Failed to generate shape index page: {str(e)}",
                details={"error": str(e)},
            ) from e
