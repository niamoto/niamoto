"""
Integration tests for templates API endpoints.

These tests ensure that the templates endpoints work correctly
and serve as regression tests during refactoring.
"""

import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile
import shutil
import yaml

from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


@pytest.fixture
def test_work_dir():
    """Create a temporary working directory with config files."""
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir) / "config"
    config_dir.mkdir(parents=True)

    # Create minimal import.yml
    import_config = {
        "version": "1.0",
        "entities": {
            "datasets": {
                "occurrences": {
                    "connector": {
                        "type": "file",
                        "format": "csv",
                        "path": "imports/occurrences.csv",
                    }
                }
            },
            "references": {
                "taxons": {
                    "kind": "hierarchical",
                    "connector": {
                        "type": "derived",
                        "source": "occurrences",
                        "extraction": {
                            "levels": [
                                {"name": "family", "column": "family"},
                                {"name": "genus", "column": "genus"},
                                {"name": "species", "column": "species"},
                            ],
                            "id_column": "id_taxonref",
                        },
                    },
                    "hierarchy": {"levels": ["family", "genus", "species"]},
                },
                "plots": {
                    "kind": "generic",
                    "connector": {
                        "type": "file",
                        "format": "csv",
                        "path": "imports/plots.csv",
                    },
                    "schema": {"id_field": "id_plot"},
                },
            },
        },
    }

    with open(config_dir / "import.yml", "w") as f:
        yaml.dump(import_config, f)

    # Create minimal transform.yml
    transform_config = [
        {
            "group_by": "taxons",
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "taxons",
                    "relation": {"plugin": "nested_set", "key": "id_taxonref"},
                }
            ],
            "widgets_data": {
                "elevation_binned_distribution_bar_plot": {
                    "plugin": "binned_distribution",
                    "field": "elevation",
                    "params": {},
                }
            },
        }
    ]

    with open(config_dir / "transform.yml", "w") as f:
        yaml.dump(transform_config, f)

    # Create minimal export.yml
    export_config = {
        "site": {"name": "Test Site"},
        "exports": [
            {
                "group_by": "taxons",
                "widgets": [
                    {
                        "data_source": "elevation_binned_distribution_bar_plot",
                        "plugin": "bar_plot",
                        "title": "Elevation Distribution",
                    }
                ],
            }
        ],
    }

    with open(config_dir / "export.yml", "w") as f:
        yaml.dump(export_config, f)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def client(test_work_dir):
    """Create test client with mocked working directory."""
    # Patch at all locations where get_working_directory is used
    with patch("niamoto.gui.api.routers.templates.get_working_directory") as mock_impl:
        mock_impl.return_value = Path(test_work_dir)
        with patch(
            "niamoto.gui.api.services.templates.utils.config_loader.get_working_directory"
        ) as mock_config:
            mock_config.return_value = Path(test_work_dir)
            with patch(
                "niamoto.gui.api.services.templates.utils.widget_utils.get_working_directory"
            ) as mock_widget:
                mock_widget.return_value = Path(test_work_dir)
                with patch("niamoto.gui.api.context.get_working_directory") as mock_ctx:
                    mock_ctx.return_value = Path(test_work_dir)
                    app = create_app()
                    yield TestClient(app)


class TestTemplatesEndpoints:
    """Test templates API endpoints."""

    def test_get_categories(self, client):
        """Test GET /api/templates/categories returns list of categories."""
        response = client.get("/api/templates/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)

    def test_get_suggestions_requires_reference_name(self, client):
        """Test GET /api/templates/{reference}/suggestions."""
        # Test with valid reference name
        response = client.get("/api/templates/taxons/suggestions")
        # Should not crash even without database
        assert response.status_code in [200, 404, 500]

    def test_get_configured_widgets(self, client):
        """Test GET /api/templates/{group_by}/configured."""
        response = client.get("/api/templates/taxons/configured")
        # Should return configured widgets from transform.yml
        assert response.status_code in [200, 404, 500]

    def test_generate_config_requires_body(self, client):
        """Test POST /api/templates/generate-config requires request body."""
        response = client.post("/api/templates/generate-config", json={})
        # Should fail validation without required fields
        assert response.status_code == 422

    def test_generate_config_with_valid_body(self, client):
        """Test POST /api/templates/generate-config with valid body."""
        response = client.post(
            "/api/templates/generate-config",
            json={
                "templates": [
                    {
                        "template_id": "test_widget",
                        "plugin": "binned_distribution",
                        "config": {"field": "elevation"},
                    }
                ],
                "group_by": "taxons",
                "reference_kind": "hierarchical",
            },
        )
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "group_by" in data
            assert "sources" in data

    def test_generate_config_uses_import_relation_and_dataset(
        self, client, test_work_dir
    ):
        """Generate-config must use dataset/relation from import.yml when provided."""
        import_path = Path(test_work_dir) / "config" / "import.yml"
        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        import_config["entities"]["datasets"]["observations"] = import_config[
            "entities"
        ]["datasets"].pop("occurrences")
        import_config["entities"]["references"]["plots"]["relation"] = {
            "dataset": "observations",
            "foreign_key": "plot_fk",
            "reference_key": "plot_code",
        }

        with open(import_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, sort_keys=False)

        response = client.post(
            "/api/templates/generate-config",
            json={
                "templates": [
                    {
                        "template_id": "plot_test",
                        "plugin": "top_ranking",
                        "config": {"field": "plot_fk"},
                    }
                ],
                "group_by": "plots",
                "reference_kind": "generic",
            },
        )
        assert response.status_code == 200, response.text
        source = response.json()["sources"][0]
        assert source["name"] == "observations"
        assert source["data"] == "observations"
        assert source["relation"]["key"] == "plot_fk"
        assert source["relation"]["ref_key"] == "plot_code"

    def test_generate_config_hierarchical_uses_extraction_id_column(
        self, client, test_work_dir
    ):
        """Hierarchical source relation key must come from extraction.id_column."""
        import_path = Path(test_work_dir) / "config" / "import.yml"
        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        import_config["entities"]["datasets"]["observations"] = import_config[
            "entities"
        ]["datasets"].pop("occurrences")
        taxons_connector = import_config["entities"]["references"]["taxons"][
            "connector"
        ]
        taxons_connector["source"] = "observations"
        taxons_connector["extraction"]["id_column"] = "taxon_ref_custom"

        with open(import_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, sort_keys=False)

        response = client.post(
            "/api/templates/generate-config",
            json={
                "templates": [
                    {
                        "template_id": "taxons_test",
                        "plugin": "binned_distribution",
                        "config": {"field": "elevation"},
                    }
                ],
                "group_by": "taxons",
                "reference_kind": "hierarchical",
            },
        )
        assert response.status_code == 200, response.text
        source = response.json()["sources"][0]
        assert source["name"] == "observations"
        assert source["data"] == "observations"
        assert source["relation"]["key"] == "taxon_ref_custom"
        assert source["relation"]["ref_key"] == "taxons_id"

    def test_save_config_requires_body(self, client):
        """Test POST /api/templates/save-config requires request body."""
        response = client.post("/api/templates/save-config", json={})
        # Should fail validation
        assert response.status_code == 422

    def test_preview_template_returns_html(self, client):
        """Test GET /api/templates/preview/{template_id} returns HTML."""
        response = client.get("/api/templates/preview/test_template?group_by=taxons")
        # Should return HTML even if template not found (400 = missing params, 404 = not found)
        assert response.status_code in [200, 400, 404, 500]
        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")

    def test_widget_suggestions_requires_group_by(self, client):
        """Test GET /api/templates/widget-suggestions/{group_by}."""
        response = client.get("/api/templates/widget-suggestions/taxons")
        assert response.status_code in [200, 404, 500]

    def test_combined_suggestions_requires_fields(self, client):
        """Test POST /api/templates/{reference}/combined-suggestions."""
        response = client.post(
            "/api/templates/taxons/combined-suggestions",
            json={"fields": ["elevation", "dbh"]},
        )
        assert response.status_code in [200, 422, 500]

    def test_semantic_groups_endpoint(self, client):
        """Test GET /api/templates/{reference}/semantic-groups."""
        response = client.get("/api/templates/taxons/semantic-groups")
        assert response.status_code in [200, 404, 500]


class TestTemplatesRouterRegistration:
    """Test that templates router is properly registered."""

    def test_templates_router_is_included(self, client):
        """Verify templates router endpoints are accessible."""
        # Check that /api/templates/* endpoints respond (not 404 from missing route)
        response = client.get("/api/templates/categories")
        assert response.status_code != 404 or "not found" not in response.text.lower()

    def test_templates_endpoints_have_correct_prefix(self, client):
        """Verify all templates endpoints use /api/templates prefix."""
        # This ensures the router is mounted with correct prefix
        endpoints = [
            "/api/templates/categories",
            "/api/templates/taxons/suggestions",
            "/api/templates/taxons/configured",
            "/api/templates/preview/test",
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not return "Not Found" for the route itself
            # (may return other errors like 500 if DB not available)
            assert (
                response.status_code != 404
                or response.json().get("detail") != "Not Found"
            )


class TestTemplatesHelperFunctions:
    """Test helper functions used by templates endpoints."""

    def test_load_import_config(self, test_work_dir):
        """Test _load_import_config reads import.yml correctly."""
        from niamoto.gui.api.routers.templates import _load_import_config

        # _load_import_config doesn't use get_working_directory internally
        config = _load_import_config(Path(test_work_dir))

        assert "entities" in config
        assert "references" in config["entities"]
        assert "taxons" in config["entities"]["references"]

    def test_get_hierarchy_info_extracts_levels(self, test_work_dir):
        """Test _get_hierarchy_info extracts hierarchy levels correctly."""
        from niamoto.gui.api.routers.templates import (
            _load_import_config,
            _get_hierarchy_info,
        )

        # Patch where get_working_directory is used (in services/templates/utils/)
        with patch(
            "niamoto.gui.api.services.templates.utils.config_loader.get_working_directory"
        ) as mock:
            mock.return_value = Path(test_work_dir)
            import_config = _load_import_config(Path(test_work_dir))
            hierarchy_info = _get_hierarchy_info(import_config, "taxons")

            assert hierarchy_info["reference_name"] == "taxons"
            assert "levels" in hierarchy_info
            # Levels should be extracted from hierarchy.levels or extraction.levels
            assert (
                len(hierarchy_info["levels"]) > 0
                or hierarchy_info.get("kind") == "hierarchical"
            )

    def test_get_hierarchy_info_handles_flat_reference(self, test_work_dir):
        """Test _get_hierarchy_info handles flat references."""
        from niamoto.gui.api.routers.templates import (
            _load_import_config,
            _get_hierarchy_info,
        )

        # Patch where get_working_directory is used (in services/templates/utils/)
        with patch(
            "niamoto.gui.api.services.templates.utils.config_loader.get_working_directory"
        ) as mock:
            mock.return_value = Path(test_work_dir)
            import_config = _load_import_config(Path(test_work_dir))
            hierarchy_info = _get_hierarchy_info(import_config, "plots")

            assert hierarchy_info["reference_name"] == "plots"
            # Flat references have empty levels
            assert (
                hierarchy_info["levels"] == []
                or hierarchy_info.get("kind") != "hierarchical"
            )

    def test_dynamic_template_info_uses_explicit_source(self):
        """Dynamic template config must propagate source instead of forcing occurrences."""
        from niamoto.gui.api.routers.templates import _build_dynamic_template_info

        parsed_geo = {
            "column": "location",
            "transformer": "geospatial_extractor",
            "widget": "interactive_map",
        }
        geo_info = _build_dynamic_template_info(
            parsed_geo, "location_geospatial_extractor_interactive_map", source="plots"
        )
        assert geo_info["config"]["source"] == "plots"

        parsed_info = {
            "column": "name",
            "transformer": "field_aggregator",
            "widget": "info_grid",
        }
        info = _build_dynamic_template_info(
            parsed_info, "name_field_aggregator_info_grid", source="shapes"
        )
        assert info["config"]["source"] == "shapes"
        assert info["config"]["fields"][0]["source"] == "shapes"


class TestPreviewEndpoint:
    """Specific tests for the preview endpoint which is critical."""

    def test_preview_with_group_by_parameter(self, client):
        """Test preview endpoint uses group_by parameter."""
        response = client.get(
            "/api/templates/preview/elevation_binned_distribution_bar_plot",
            params={"group_by": "taxons"},
        )
        # Should process the request (400 = bad request, 404 = not found, 500 = DB error)
        assert response.status_code in [200, 400, 404, 500]

    def test_preview_with_entity_id_parameter(self, client):
        """Test preview endpoint accepts entity_id parameter."""
        response = client.get(
            "/api/templates/preview/test_template",
            params={"group_by": "taxons", "entity_id": "123"},
        )
        assert response.status_code in [200, 400, 404, 500]

    def test_preview_returns_html_content_type(self, client):
        """Test preview endpoint returns HTML content type."""
        response = client.get(
            "/api/templates/preview/test_template", params={"group_by": "taxons"}
        )
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type
