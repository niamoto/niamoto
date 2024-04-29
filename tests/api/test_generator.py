import pytest
from niamoto.core.models import TaxonRef
from niamoto.common.config import Config
from niamoto.api.generator import StaticContentGenerator


@pytest.mark.usefixtures("niamoto_home")
class TestStaticContentGenerator:
    @pytest.fixture(autouse=True)
    def setUp(self, niamoto_home):
        # setUp logic is now handled by the niamoto_home fixture automatically.
        pass

    def test_generate_taxonomy_tree(self, mocker):
        mock_page_generator = mocker.patch("niamoto.api.generator.PageGenerator")
        config = Config()
        static_content_generator = StaticContentGenerator(config)
        taxons = [TaxonRef(), TaxonRef()]
        static_content_generator.generate_taxonomy_tree(taxons)

        mock_page_generator.return_value.generate_taxonomy_tree_js.assert_called_once_with(
            taxons
        )
