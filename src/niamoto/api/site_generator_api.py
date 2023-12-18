from niamoto.common.config_manager import ConfigManager
from niamoto.static_site_generator.page_generator import PageGenerator
from niamoto.db.models.models import Taxon
from typing import List


class SiteGeneratorAPI:
    def __init__(self, config: ConfigManager) -> None:
        self.page_generator = PageGenerator(config)

    def generate_page_for_taxon(self, taxon: Taxon) -> str:
        return self.page_generator.generate_taxon_page(taxon)

    def generate_taxonomy_tree(self, taxons: List[Taxon]) -> None:
        self.page_generator.generate_taxonomy_tree_js(taxons)
