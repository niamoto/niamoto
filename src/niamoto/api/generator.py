from typing import List, Optional, Any, Dict

from niamoto.core.models import TaxonRef
from niamoto.common.config import Config
from niamoto.publish import PageGenerator


class StaticContentGenerator:
    def __init__(self, config: Config) -> None:
        self.page_generator = PageGenerator(config)

    def generate_page_for_taxon(
        self, taxon: TaxonRef, stats: Optional[Any], mapping: Dict[Any, Any]
    ) -> str:
        return self.page_generator.generate_taxon_page(taxon, stats, mapping)

    def generate_taxonomy_tree(self, taxons: List[TaxonRef]) -> None:
        self.page_generator.generate_taxonomy_tree_js(taxons)
