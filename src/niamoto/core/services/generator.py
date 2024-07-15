from typing import List, Optional, Any, Dict
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from niamoto.common.config import Config
from niamoto.core.repositories.niamoto_repository import NiamotoRepository
from niamoto.publish import PageGenerator
from niamoto.publish.static_api import ApiGenerator
from niamoto.core.services.mapper import MapperService
from loguru import logger
from sqlalchemy import asc
from sqlalchemy.sql import text
from rich.progress import track


class GeneratorService:
    """
    The GeneratorService class provides methods to generate pages and JSON files.
    """

    def __init__(self, config: Config):
        """
        Initializes a new instance of the GeneratorService class.

        Args:
            config (Config): The configuration settings for the Niamoto project.
        """
        self.config = config
        self.db_path = config.get("database", "path")
        self.page_generator = PageGenerator(config)
        self.api_generator = ApiGenerator(config)
        self.mapper_service = MapperService(self.db_path)
        self.repository = NiamotoRepository(self.db_path)

    def generate_content(self, mapping_group: Optional[str] = None) -> None:
        """
        Generates content based on the mapping group specified.

        Args:
            mapping_group (Optional[str]): The specific group to generate content for.
                                           If not provided, content will be generated for all groups.
        """
        try:
            # Generate static pages
            self.generate_page("index.html", "index.html", depth="")
            self.generate_page("methodology.html", "methodology.html", depth="")
            self.generate_page("resources.html", "resources.html", depth="")
            self.generate_page("construction.html", "construction.html", depth="")

            if mapping_group:
                group_configs = [self.mapper_service.get_group_config(mapping_group)]
            else:
                group_configs = self.mapper_service.get_aggregations()

            for group_config in group_configs:
                group_by = group_config["group_by"]
                self.generate_group_content(group_by, group_config)

            # Generate the taxonomy tree
            taxons = self.repository.get_entities(
                TaxonRef, order_by=asc(TaxonRef.full_name)
            )
            self.generate_taxonomy_tree(taxons)

            plots = self.repository.get_entities(PlotRef, order_by=asc(PlotRef.id))
            self.generate_plot_list(plots)

            shapes = self.repository.get_entities(ShapeRef, order_by=asc(ShapeRef.id))
            self.generate_shape_list(shapes)

            self.generate_all_plots_json(plots)
            self.generate_all_shapes_json(shapes)
            self.generate_all_taxa_json(taxons)

        except Exception as e:
            logger.exception(f"Error generating content: {e}")

    def generate_group_content(self, group_by: str, group_config: Dict[str, Any]) -> None:
        """
        Generate content for a given group.

        Args:
            group_by (str): The parameter to group the occurrences by.
            group_config (dict): The configuration for the group.
        """
        if group_by == "plot":
            entities = self.repository.get_entities(PlotRef, order_by=asc(PlotRef.id))
        elif group_by == "shape":
            entities = self.repository.get_entities(ShapeRef, order_by=asc(ShapeRef.id))
        elif group_by == "taxon":
            entities = self.repository.get_entities(
                TaxonRef, order_by=asc(TaxonRef.full_name)
            )
        else:
            raise ValueError(f"Unknown group_by: {group_by}")

        for entity in track(entities, description=f"Generating {group_by} pages"):
            with self.repository.db.engine.connect() as connection:
                result = connection.execute(
                    text(f"SELECT * FROM {group_by}_stats WHERE {group_by}_id = :id"),
                    {"id": entity.id},
                )
                stats_row = result.fetchone()
                stats_dict = dict(zip(result.keys(), stats_row)) if stats_row else {}

                if group_by == "plot":
                    self.generate_page_for_plot(entity, stats_dict, group_config)
                    self.generate_json_for_plot(entity, stats_dict)
                elif group_by == "shape":
                    self.generate_page_for_shape(entity, stats_dict, group_config)
                    self.generate_json_for_shape(entity, stats_dict)
                elif group_by == "taxon":
                    self.generate_page_for_taxon(entity, stats_dict, group_config)
                    self.generate_json_for_taxon(entity, stats_dict)

    def generate_page(
        self,
        template_name: str,
        output_name: str,
        depth: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generates a page from a template.

        Args:
            template_name (str): The name of the template file.
            output_name (str): The name of the output file.
            depth (str): The relative path to the root (e.g., '../../' for two levels up).
            context (dict, optional): A dictionary of context variables for the template.

        Returns:
            str: The path of the generated page.
        """
        return self.page_generator.generate_page(
            template_name, output_name, depth, context
        )

    def generate_page_for_taxon(
        self, taxon: TaxonRef, stats: Optional[Any], mapping: Dict[Any, Any]
    ) -> str:
        """
        Generates a page for a specific taxon.

        Args:
            taxon (niamoto.core.models.TaxonRef): The taxon for which to generate a page.
            stats (Optional[Any]): The statistics to include on the page.
            mapping (Dict[Any, Any]): The mapping to use for generating the page.

        Returns:
            str: The generated page as a string.
        """
        return self.page_generator.generate_taxon_page(taxon, stats, mapping)

    def generate_json_for_taxon(self, taxon: TaxonRef, stats: Optional[Any]) -> str:
        """
        Generates a JSON file for a specific taxon.

        Args:
            taxon (niamoto.core.models.TaxonRef): The taxon for which to generate a JSON file.
            stats (Optional[Any]): The statistics to include in the JSON file.

        Returns:
            str: The generated JSON file as a string.
        """
        return self.api_generator.generate_taxon_json(taxon, stats)

    def generate_taxonomy_tree(self, taxons: List[TaxonRef]) -> None:
        """
        Generates a taxonomy tree for a list of taxons.

        Args:
            taxons (List[niamoto.core.models.TaxonRef]): The taxons for which to generate a taxonomy tree.
        """
        self.page_generator.generate_taxonomy_tree_js(taxons)

    def generate_plot_list(self, plots: List[PlotRef]) -> None:
        """
        Generates a list of plots.

        Args:
            plots (List[niamoto.core.models.PlotRef]): The plots for which to generate a list.
        """
        self.page_generator.generate_plot_list_js(plots)

    def generate_page_for_plot(
        self, plot: PlotRef, stats: Optional[Any], mapping: Dict[Any, Any]
    ) -> str:
        """
        Generates a page for a specific plot.

        Args:
            plot (niamoto.core.models.PlotRef): The plot for which to generate a page.
            stats (Optional[Any]): The statistics to include on the page.
            mapping (Dict[Any, Any]): The mapping to use for generating the page.

        Returns:
            str: The path to the generated page.
        """
        return self.page_generator.generate_plot_page(plot, stats, mapping)

    def generate_json_for_plot(self, plot: PlotRef, stats: Optional[Any]) -> str:
        """
        Generates a JSON file for a specific plot.

        Args:
            plot (niamoto.core.models.PlotRef): The plot for which to generate a JSON file.
            stats (Optional[Any]): The statistics to include in the JSON file.

        Returns:
            str: The path to the generated JSON file.
        """
        return self.api_generator.generate_plot_json(plot, stats)

    def generate_shape_list(self, shapes: List[ShapeRef]) -> None:
        """
        Generates a list of shapes.

        Args:
            shapes (List[ShapeRef]): The shapes for which to generate a list.
        """
        self.page_generator.generate_shape_list_js(shapes)

    def generate_page_for_shape(
        self, shape: ShapeRef, stats: Optional[Any], mapping: Dict[Any, Any]
    ) -> str:
        """
        Generates a page for a specific shape.

        Args:
            shape (ShapeRef): The shape for which to generate a page.
            stats (Optional[Any]): The statistics to include on the page.
            mapping (Dict[Any, Any]): The mapping to use for generating the page.

        Returns:
            str: The path to the generated page.
        """
        return self.page_generator.generate_shape_page(shape, stats, mapping)

    def generate_json_for_shape(self, shape: ShapeRef, stats: Optional[Any]) -> str:
        """
        Generates a JSON file for a specific shape.

        Args:
            shape (ShapeRef): The shape for which to generate a JSON file.
            stats (Optional[Any]): The statistics to include in the JSON file.

        Returns:
            str: The path to the generated JSON file.
        """
        return self.api_generator.generate_shape_json(shape, stats)

    def generate_all_plots_json(self, plots: List[PlotRef]) -> None:
        """
        Generates a JSON file for all plots.

        Args:
            plots (List[PlotRef]): The list of plot entities.
        """
        self.api_generator.generate_all_plots_json(plots)

    def generate_all_shapes_json(self, shapes: List[ShapeRef]) -> None:
        """
        Generates a JSON file for all shapes.

        Args:
            shapes (List[ShapeRef]): The list of shape entities.
        """
        self.api_generator.generate_all_shapes_json(shapes)

    def generate_all_taxa_json(self, taxons: List[TaxonRef]) -> None:
        """
        Generates a JSON file for all taxons.

        Args:
            taxons (List[TaxonRef]): The list of taxon entities.
        """
        self.api_generator.generate_all_taxa_json(taxons)

    def copy_template_page(self, template_name: str, output_name: str) -> None:
        """
        Copies a template page to the output directory.

        Args:
            template_name (str): The name of the template page to copy.
            output_name (str): The name of the output page.
        """
        self.page_generator.copy_template_page(template_name, output_name)
