from typing import List, Optional, Any, Dict

from niamoto.core.models import TaxonRef, PlotRef
from niamoto.common.config import Config
from niamoto.publish import PageGenerator
from niamoto.publish.static_api import ApiGenerator


class StaticContentGenerator:
    """
    A class used to generate static_files content for the Niamoto project.

    Attributes:
        page_generator (niamoto.publish.PageGenerator): An instance of the PageGenerator class.
    """

    def __init__(self, config: Config) -> None:
        """
        Initializes the StaticContentGenerator with a given configuration.

        Args:
            config (Config): The configuration settings for the Niamoto project.
        """
        self.page_generator = PageGenerator(config)
        self.api_generator = ApiGenerator(config)

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
        Generates a page for a specific taxon.

        Args:
            taxon (niamoto.core.models.TaxonRef): The taxon for which to generate a page.
            stats (Optional[Any]): The statistics to include on the page.

        Returns:
            str: The generated page as a string.
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

    def copy_template_page(self, template_name: str, output_name: str) -> None:
        """
        Copies a template page to the output directory.

        Args:
            template_name (str): The name of the template page to copy.
            output_name (str): The name of the output page.
        """
        self.page_generator.copy_template_page(template_name, output_name)
