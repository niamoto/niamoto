import pytest
from niamoto.core.models import TaxonRef
from niamoto.common.config import Config
from niamoto.api.generator import StaticContentGenerator


@pytest.mark.usefixtures("niamoto_home")
class TestStaticContentGenerator:
    """
    The TestStaticContentGenerator class provides test cases for the StaticContentGenerator class.
    """

    @pytest.fixture(autouse=True)
    def setUp(self, niamoto_home):
        """
        Setup method for the test cases. It is automatically called before each test case.

        Args:
            niamoto_home: A pytest fixture that sets up a temporary NIAMOTO_HOME environment for testing.
        """
        pass

    def test_generate_taxonomy_tree(self, mocker):
        """
        Test case for the generate_taxonomy_tree method of the StaticContentGenerator class.

        Args:
            mocker: A pytest fixture that provides a simple, powerful way to mock python objects.
        """
        mock_page_generator = mocker.patch("niamoto.api.generator.PageGenerator")
        config = Config()
        static_content_generator = StaticContentGenerator(config)
        taxons = [TaxonRef(), TaxonRef()]
        static_content_generator.generate_taxonomy_tree(taxons)

        mock_page_generator.return_value.generate_taxonomy_tree_js.assert_called_once_with(
            taxons
        )
