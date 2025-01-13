from typing import List, Optional, Any, Dict
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from niamoto.common.config import Config
from niamoto.core.repositories.niamoto_repository import NiamotoRepository
from niamoto.publish import PageGenerator
from niamoto.publish.static_api import ApiGenerator
from loguru import logger
from sqlalchemy import asc
from sqlalchemy.sql import text
from rich.progress import track


class GeneratorService:
    """
    Service to generate static pages and JSON files based on presentation configuration.
    """

    def __init__(self, config: Config):
        """
        Initialize the service with project configuration

        Args:
            config (Config): Project configuration settings
        """
        self.config = config
        self.db_path = config.database_path
        self.page_generator = PageGenerator(config)
        self.api_generator = ApiGenerator(config)
        self.repository = NiamotoRepository(self.db_path)
        # Get presentation configuration directly from config object
        self.presentation_config = config.get_presentation_config()

    def generate_content(self, group: Optional[str] = None) -> None:
        """
        Generate static content based on presentation configuration.

        Args:
            group (Optional[str]): If specified, only generate content for this group.
                                 Must be one of: 'taxon', 'plot', 'shape'
        """
        try:
            # Generate static pages (toujours nécessaires même avec un groupe spécifique)
            self._generate_static_pages()

            # Filtre la configuration selon le groupe si spécifié
            if group:
                group_configs = [
                    config
                    for config in self.presentation_config
                    if config.get("group_by") == group
                ]
                if not group_configs:
                    logger.warning(f"No configuration found for group: {group}")
                    return
            else:
                group_configs = self.presentation_config

            # Generate content for filtered groups
            for group_config in group_configs:
                group_by = group_config.get("group_by")
                if group_by:
                    self._generate_group_content(group_by, group_config)

            # Generate additional content selon le groupe
            if not group:
                # Si aucun groupe spécifié, génère tout le contenu additionnel
                self._generate_additional_content()
            else:
                # Sinon, génère uniquement le contenu additionnel pour le groupe spécifié
                if group == "taxon":
                    taxons = self._get_entities_for_group("taxon")
                    self.generate_taxonomy_tree(taxons)
                    self.generate_all_taxa_json(taxons)
                elif group == "plot":
                    plots = self._get_entities_for_group("plot")
                    self.generate_plot_list(plots)
                    self.generate_all_plots_json(plots)
                elif group == "shape":
                    shapes = self._get_entities_for_group("shape")
                    self.generate_shape_list(shapes)
                    self.generate_all_shapes_json(shapes)

        except Exception as e:
            logger.exception(f"Error generating content: {e}")

    def _generate_static_pages(self) -> None:
        """
        Generate basic static pages
        """
        static_pages = [
            "index.html",
            "methodology.html",
            "resources.html",
            "construction.html",
            "trees.html",
            "plots.html",
            "forests.html",
        ]
        for page in static_pages:
            self.generate_page(page, page, depth="")

    def _get_entities_for_group(self, group_by: str) -> List[Any]:
        """
        Get filtered entities based on group type

        Args:
            group_by (str): Type of group ('plot', 'shape', or 'taxon')

        Returns:
            List[Any]: Filtered list of entities
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

        return self.filter_entities_with_stats(entities, group_by)

    def _generate_group_content(
        self, group_by: str, group_config: Dict[str, Any]
    ) -> None:
        """
        Generate content for a specific group

        Args:
            group_by (str): Type of group
            group_config (Dict): Configuration for the group
        """
        entities = self._get_entities_for_group(group_by)

        # Process each entity
        for entity in track(entities, description=f"Generating {group_by} content"):
            stats = self._get_entity_stats(entity, group_by)
            if stats:
                # Generate page and JSON based on entity type
                if group_by == "plot":
                    self.generate_page_for_plot(entity, stats, group_config)
                    self.generate_json_for_plot(entity, stats)
                elif group_by == "shape":
                    self.generate_page_for_shape(entity, stats, group_config)
                    self.generate_json_for_shape(entity, stats)
                elif group_by == "taxon":
                    self.generate_page_for_taxon(entity, stats, group_config)
                    self.generate_json_for_taxon(entity, stats)

    def _generate_additional_content(self) -> None:
        """
        Generate additional required content like taxonomies and lists
        """
        # Generate taxonomy tree
        taxons = self._get_entities_for_group("taxon")
        self.generate_taxonomy_tree(taxons)
        self.generate_all_taxa_json(taxons)

        # Generate plot content
        plots = self._get_entities_for_group("plot")
        self.generate_plot_list(plots)
        self.generate_all_plots_json(plots)

        # Generate shape content
        shapes = self._get_entities_for_group("shape")
        self.generate_shape_list(shapes)
        self.generate_all_shapes_json(shapes)

    def _get_entity_stats(self, entity: Any, group_by: str) -> Optional[Dict]:
        """
        Get statistics for an entity

        Args:
            entity (Any): Entity to get stats for
            group_by (str): Type of group

        Returns:
            Optional[Dict]: Entity statistics if available
        """
        with self.repository.db.engine.connect() as connection:
            result = connection.execute(
                text(f"SELECT * FROM {group_by}_stats WHERE {group_by}_id = :id"),
                {"id": entity.id},
            )
            stats_row = result.fetchone()
            return dict(zip(result.keys(), stats_row)) if stats_row else None

    def filter_entities_with_stats(
        self, entities: List[Any], group_by: str
    ) -> List[Any]:
        """
        Filter entities to only include those with statistics

        Args:
            entities (List[Any]): List of entities to filter
            group_by (str): Type of group

        Returns:
            List[Any]: Filtered list of entities
        """
        return [
            entity
            for entity in entities
            if self._get_entity_stats(entity, group_by) is not None
        ]

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
