from typing import List, Optional, Any, Dict

from niamoto.core.models import TaxonRef
from niamoto.common.config import Config
from niamoto.publish import PageGenerator


class StaticContentGenerator:
    """
    A class used to generate static content for the Niamoto project.

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

    def generate_taxonomy_tree(self, taxons: List[TaxonRef]) -> None:
        """
        Generates a taxonomy tree for a list of taxons.

        Args:
            taxons (List[niamoto.core.models.TaxonRef]): The taxons for which to generate a taxonomy tree.
        """
        self.page_generator.generate_taxonomy_tree_js(taxons)
