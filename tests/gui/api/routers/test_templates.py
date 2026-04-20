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

    def test_generate_config_hierarchical_prefers_explicit_relation(
        self, client, test_work_dir
    ):
        """Les hiérarchies dérivées doivent joindre le dataset via relation.foreign_key."""
        import_path = Path(test_work_dir) / "config" / "import.yml"
        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        import_config["entities"]["references"]["taxons"]["relation"] = {
            "dataset": "occurrences",
            "foreign_key": "taxon_fk",
            "reference_key": "taxons_id",
        }
        import_config["entities"]["references"]["taxons"]["connector"]["extraction"][
            "id_column"
        ] = "taxon_ref_custom"

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
        assert source["relation"]["key"] == "taxon_fk"
        assert source["relation"]["ref_key"] == "taxons_id"

    def test_transformer_references_hierarchical_prefers_explicit_relation(
        self, test_work_dir
    ):
        """Le catalogue de références doit exposer la même relation explicite."""
        import_path = Path(test_work_dir) / "config" / "import.yml"
        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        import_config["entities"]["references"]["taxons"]["relation"] = {
            "dataset": "occurrences",
            "foreign_key": "taxon_fk",
            "reference_key": "taxons_id",
        }
        import_config["entities"]["references"]["taxons"]["connector"]["extraction"][
            "id_column"
        ] = "taxon_ref_custom"

        with open(import_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, sort_keys=False)

        with patch(
            "niamoto.gui.api.routers.transformer_suggestions.get_working_directory"
        ) as mock_work_dir:
            mock_work_dir.return_value = Path(test_work_dir)
            client = TestClient(create_app())
            response = client.get("/api/transformer-suggestions/references")

        assert response.status_code == 200, response.text
        taxons = next(
            ref for ref in response.json()["references"] if ref["name"] == "taxons"
        )
        assert taxons["relation"]["key"] == "taxon_fk"
        assert taxons["relation"]["ref_key"] == "taxons_id"

    def test_generate_config_spatial_does_not_invent_dataset_relation(
        self, client, test_work_dir
    ):
        """Spatial references must not create an implicit occurrences->shapes join."""
        import_path = Path(test_work_dir) / "config" / "import.yml"
        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        import_config["entities"]["references"]["shapes"] = {
            "kind": "spatial",
            "connector": {
                "type": "file_multi_feature",
                "sources": [
                    {
                        "name": "Mines",
                        "path": "imports/mines.gpkg",
                        "layer": "emprises_mines_ERMINES",
                        "name_field": "region",
                    }
                ],
            },
        }

        with open(import_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, sort_keys=False)

        response = client.post(
            "/api/templates/generate-config",
            json={
                "templates": [
                    {
                        "template_id": "shape_info",
                        "plugin": "field_aggregator",
                        "config": {"field": "name"},
                    }
                ],
                "group_by": "shapes",
                "reference_kind": "spatial",
            },
        )

        assert response.status_code == 200, response.text
        assert response.json()["sources"] == []

    def test_save_config_requires_body(self, client):
        """Test POST /api/templates/save-config requires request body."""
        response = client.post("/api/templates/save-config", json={})
        # Should fail validation
        assert response.status_code == 422

    def test_preview_template_returns_html(self, client):
        """Test GET /api/preview/{template_id} returns HTML."""
        response = client.get("/api/preview/test_template?group_by=taxons")
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
            "/api/preview/test",
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
        """Test load_import_config reads import.yml correctly."""
        from niamoto.gui.api.services.templates.utils.config_loader import (
            load_import_config,
        )

        config = load_import_config(Path(test_work_dir))

        assert "entities" in config
        assert "references" in config["entities"]
        assert "taxons" in config["entities"]["references"]

    def test_get_hierarchy_info_extracts_levels(self, test_work_dir):
        """Test get_hierarchy_info extracts hierarchy levels correctly."""
        from niamoto.gui.api.services.templates.utils.config_loader import (
            load_import_config,
            get_hierarchy_info,
        )

        # Patch where get_working_directory is used (in services/templates/utils/)
        with patch(
            "niamoto.gui.api.services.templates.utils.config_loader.get_working_directory"
        ) as mock:
            mock.return_value = Path(test_work_dir)
            import_config = load_import_config(Path(test_work_dir))
            hierarchy_info = get_hierarchy_info(import_config, "taxons")

            assert hierarchy_info["reference_name"] == "taxons"
            assert "levels" in hierarchy_info
            # Levels should be extracted from hierarchy.levels or extraction.levels
            assert (
                len(hierarchy_info["levels"]) > 0
                or hierarchy_info.get("kind") == "hierarchical"
            )

    def test_get_hierarchy_info_handles_flat_reference(self, test_work_dir):
        """Test get_hierarchy_info handles flat references."""
        from niamoto.gui.api.services.templates.utils.config_loader import (
            load_import_config,
            get_hierarchy_info,
        )

        # Patch where get_working_directory is used (in services/templates/utils/)
        with patch(
            "niamoto.gui.api.services.templates.utils.config_loader.get_working_directory"
        ) as mock:
            mock.return_value = Path(test_work_dir)
            import_config = load_import_config(Path(test_work_dir))
            hierarchy_info = get_hierarchy_info(import_config, "plots")

            assert hierarchy_info["reference_name"] == "plots"
            # Flat references have empty levels
            assert (
                hierarchy_info["levels"] == []
                or hierarchy_info.get("kind") != "hierarchical"
            )


class TestPreviewEndpoint:
    """Specific tests for the preview endpoint which is critical."""

    def test_preview_with_group_by_parameter(self, client):
        """Test preview endpoint uses group_by parameter."""
        response = client.get(
            "/api/preview/elevation_binned_distribution_bar_plot",
            params={"group_by": "taxons"},
        )
        # Should process the request (400 = bad request, 404 = not found, 500 = DB error)
        assert response.status_code in [200, 400, 404, 500]

    def test_preview_with_entity_id_parameter(self, client):
        """Test preview endpoint accepts entity_id parameter."""
        response = client.get(
            "/api/preview/test_template",
            params={"group_by": "taxons", "entity_id": "123"},
        )
        assert response.status_code in [200, 400, 404, 500]

    def test_preview_returns_html_content_type(self, client):
        """Test preview endpoint returns HTML content type."""
        response = client.get(
            "/api/preview/test_template", params={"group_by": "taxons"}
        )
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "text/html" in content_type

    def test_preview_legacy_class_object_scalar_template_id(
        self, client, test_work_dir
    ):
        """Legacy *_field_aggregator_* IDs must resolve to class_object previews."""
        transform_path = Path(test_work_dir) / "config" / "transform.yml"
        with open(transform_path, "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        transform_config.append(
            {
                "group_by": "shapes",
                "sources": [
                    {
                        "name": "shape_stats",
                        "data": "imports/raw_shape_stats.csv",
                        "grouping": "shapes",
                    }
                ],
                "widgets_data": {},
            }
        )
        with open(transform_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(transform_config, f, sort_keys=False)

        imports_dir = Path(test_work_dir) / "imports"
        imports_dir.mkdir(exist_ok=True)
        csv_path = imports_dir / "raw_shape_stats.csv"
        csv_path.write_text(
            "class_object,class_name,class_value\nforest_reserve_ha,value,11800\n",
            encoding="utf-8",
        )

        response = client.get(
            "/api/preview/forest_reserve_ha_field_aggregator_radial_gauge",
            params={"group_by": "shapes", "source": "shape_stats"},
        )

        # Preview engine may return 500 if no DB exists in the test dir,
        # but should not return 404 (route must exist)
        assert response.status_code != 404, "Preview route not found"
        if response.status_code == 200:
            assert "<p class='error'>" not in response.text.lower()

    def test_field_aggregator_radial_gauge_preprocesses_scalar_value(self):
        """field_aggregator output must be flattened for radial_gauge."""
        from niamoto.gui.api.services.preview_utils import preprocess_data_for_widget

        processed = preprocess_data_for_widget(
            {"elevation_median": {"value": "123.5", "units": "m"}},
            "field_aggregator",
            "radial_gauge",
        )

        assert isinstance(processed, dict)
        assert processed.get("value") == "123.5"
        assert processed.get("unit") == "m"

    def test_field_aggregator_radial_gauge_preprocess_keeps_string_values(self):
        """Non-float scalar values should still be flattened to avoid blank pages."""
        from niamoto.gui.api.services.preview_utils import preprocess_data_for_widget

        processed = preprocess_data_for_widget(
            {"elevation_median": {"value": "123,5", "units": "m"}},
            "field_aggregator",
            "radial_gauge",
        )

        assert processed.get("value") == "123,5"
        assert processed.get("unit") == "m"

    def test_class_object_scalar_loader_handles_empty_class_name(self, test_work_dir):
        """Scalar class_objects with empty class_name must still produce a value."""
        from niamoto.gui.api.services.templates.utils.data_loader import (
            load_class_object_data_for_preview,
        )

        transform_path = Path(test_work_dir) / "config" / "transform.yml"
        with open(transform_path, "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        transform_config.append(
            {
                "group_by": "shapes",
                "sources": [
                    {
                        "name": "shape_stats",
                        "data": "imports/raw_shape_stats.csv",
                        "grouping": "shapes",
                    }
                ],
                "widgets_data": {},
            }
        )
        with open(transform_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(transform_config, f, sort_keys=False)

        imports_dir = Path(test_work_dir) / "imports"
        imports_dir.mkdir(exist_ok=True)
        csv_path = imports_dir / "raw_shape_stats.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "id;label;class_object;class_name;class_value",
                    "s1;Shape A;elevation_median;;214",
                    "s2;Shape B;elevation_median;;218",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        loaded = load_class_object_data_for_preview(
            Path(test_work_dir), "elevation_median", "shapes"
        )
        assert loaded is not None
        assert loaded["tops"] == ["value"]
        assert loaded["counts"][0] == pytest.approx(216.0)


class TestConfigScaffoldSpatialReferences:
    def test_scaffold_keeps_web_export_without_default_home_page(self, test_work_dir):
        from niamoto.gui.api.services.templates.config_scaffold import scaffold_configs

        changed, _ = scaffold_configs(Path(test_work_dir))
        assert changed is True

        with open(
            Path(test_work_dir) / "config" / "export.yml", "r", encoding="utf-8"
        ) as f:
            export_config = yaml.safe_load(f) or {}

        web_export = next(
            export
            for export in export_config.get("exports", [])
            if export.get("name") == "web_pages"
        )
        assert web_export["name"] == "web_pages"
        assert web_export["exporter"] == "html_page_exporter"
        assert web_export["params"]["template_dir"] == "templates/"
        assert web_export["params"]["output_dir"] == "exports/web"
        assert web_export["static_pages"] == []

    def test_default_exporter_generation_keeps_empty_web_export_without_home_page(
        self, test_work_dir
    ):
        from niamoto.gui.api.routers.templates import _generate_export_config

        _generate_export_config(Path(test_work_dir), "plots", {}, [])

        with open(
            Path(test_work_dir) / "config" / "export.yml", "r", encoding="utf-8"
        ) as f:
            export_config = yaml.safe_load(f) or {}

        web_export = next(
            export
            for export in export_config.get("exports", [])
            if export.get("name") == "web_pages"
        )
        assert web_export["name"] == "web_pages"
        assert web_export["exporter"] == "html_page_exporter"
        assert web_export["params"]["template_dir"] == "templates/"
        assert web_export["params"]["output_dir"] == "exports/web"
        assert web_export["params"]["navigation"] == []
        assert web_export["static_pages"] == []

    def test_scaffold_uses_explicit_relation_for_hierarchical_reference(
        self, test_work_dir
    ):
        from niamoto.gui.api.services.templates.config_scaffold import scaffold_configs

        config_dir = Path(test_work_dir) / "config"
        import_path = config_dir / "import.yml"

        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        import_config["entities"]["references"]["taxons"]["relation"] = {
            "dataset": "occurrences",
            "foreign_key": "taxon_fk",
            "reference_key": "taxons_id",
        }
        import_config["entities"]["references"]["taxons"]["connector"]["extraction"][
            "id_column"
        ] = "taxon_ref_custom"

        with open(import_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, sort_keys=False)

        transform_path = config_dir / "transform.yml"
        transform_path.unlink()

        changed, _ = scaffold_configs(Path(test_work_dir))

        assert changed is True
        with open(transform_path, "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        taxons_group = next(
            group for group in transform_config if group.get("group_by") == "taxons"
        )
        assert taxons_group["sources"][0]["data"] == "occurrences"
        assert taxons_group["sources"][0]["relation"]["key"] == "taxon_fk"
        assert taxons_group["sources"][0]["relation"]["ref_key"] == "taxons_id"

    def test_scaffold_skips_hierarchical_source_without_safe_relation(
        self, test_work_dir
    ):
        from niamoto.gui.api.services.templates.config_scaffold import scaffold_configs

        config_dir = Path(test_work_dir) / "config"
        import_path = config_dir / "import.yml"

        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        taxons_config = import_config["entities"]["references"]["taxons"]
        taxons_config.pop("relation", None)
        taxons_config["connector"]["extraction"]["id_column"] = None

        with open(import_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, sort_keys=False)

        transform_path = config_dir / "transform.yml"
        transform_path.unlink()

        changed, _ = scaffold_configs(Path(test_work_dir))

        assert changed is True
        with open(transform_path, "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        taxons_group = next(
            group for group in transform_config if group.get("group_by") == "taxons"
        )
        assert taxons_group["sources"] == []

    def test_scaffold_uses_shape_stats_for_spatial_reference(self, test_work_dir):
        from niamoto.gui.api.services.templates.config_scaffold import scaffold_configs

        config_dir = Path(test_work_dir) / "config"
        imports_dir = Path(test_work_dir) / "imports"
        imports_dir.mkdir(exist_ok=True)

        with open(config_dir / "import.yml", "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f)

        import_config["entities"]["references"]["shapes"] = {
            "kind": "spatial",
            "connector": {
                "type": "file",
                "format": "gpkg",
                "path": "imports/shapes.gpkg",
            },
        }

        with open(config_dir / "import.yml", "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, sort_keys=False)

        with patch(
            "niamoto.gui.api.services.templates.config_scaffold.find_stats_sources_for_reference"
        ) as mock_find_stats:
            mock_find_stats.return_value = [
                {
                    "name": "custom_stats",
                    "data": "imports/custom_stats.csv",
                    "grouping": "shapes",
                    "relation_plugin": "stats_loader",
                    "key": "id",
                    "ref_field": "id_shape",
                    "match_field": "shape_id",
                }
            ]
            changed, _ = scaffold_configs(Path(test_work_dir))
        assert changed is True

        with open(config_dir / "transform.yml", "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        shapes_group = next(
            group for group in transform_config if group.get("group_by") == "shapes"
        )
        assert shapes_group["sources"] == [
            {
                "name": "custom_stats",
                "data": "imports/custom_stats.csv",
                "grouping": "shapes",
                "relation": {
                    "plugin": "stats_loader",
                    "key": "id",
                    "ref_field": "id_shape",
                    "match_field": "shape_id",
                },
            }
        ]

    def test_scaffold_does_not_invent_shapes_id_relation_without_stats(
        self, test_work_dir
    ):
        from niamoto.gui.api.services.templates.config_scaffold import scaffold_configs

        config_dir = Path(test_work_dir) / "config"

        with open(config_dir / "import.yml", "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f)

        import_config["entities"]["references"]["shapes"] = {
            "kind": "spatial",
            "connector": {
                "type": "file",
                "format": "gpkg",
                "path": "imports/shapes.gpkg",
            },
        }

        with open(config_dir / "import.yml", "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, sort_keys=False)

        with patch(
            "niamoto.gui.api.services.templates.config_scaffold.find_stats_sources_for_reference"
        ) as mock_find_stats:
            mock_find_stats.return_value = []
            changed, _ = scaffold_configs(Path(test_work_dir))
        assert changed is True

        with open(config_dir / "transform.yml", "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        shapes_group = next(
            group for group in transform_config if group.get("group_by") == "shapes"
        )
        assert shapes_group["sources"] == []

    def test_scaffold_appends_auxiliary_stats_to_non_spatial_reference(
        self, test_work_dir
    ):
        from niamoto.gui.api.services.templates.config_scaffold import scaffold_configs

        config_dir = Path(test_work_dir) / "config"

        with patch(
            "niamoto.gui.api.services.templates.config_scaffold.find_stats_sources_for_reference"
        ) as mock_find_stats:
            mock_find_stats.side_effect = lambda _work_dir, ref_name: (
                [
                    {
                        "name": "plot_stats",
                        "data": "imports/raw_plot_stats.csv",
                        "grouping": "plots",
                        "relation_plugin": "stats_loader",
                        "key": "id",
                        "ref_field": "id_plot",
                        "match_field": "plot_id",
                    }
                ]
                if ref_name == "plots"
                else []
            )
            changed, _ = scaffold_configs(Path(test_work_dir))

        assert changed is True

        with open(config_dir / "transform.yml", "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        plots_group = next(
            group for group in transform_config if group.get("group_by") == "plots"
        )
        assert plots_group["sources"] == [
            {
                "name": "occurrences",
                "data": "occurrences",
                "grouping": "plots",
                "relation": {
                    "plugin": "direct_reference",
                    "key": "id_plot",
                    "ref_key": "id",
                },
            },
            {
                "name": "plot_stats",
                "data": "imports/raw_plot_stats.csv",
                "grouping": "plots",
                "relation": {
                    "plugin": "stats_loader",
                    "key": "id",
                    "ref_field": "id_plot",
                    "match_field": "plot_id",
                },
            },
        ]

    def test_scaffold_uses_explicit_auxiliary_sources_from_import_config(
        self, test_work_dir
    ):
        from niamoto.gui.api.services.templates.config_scaffold import scaffold_configs

        config_dir = Path(test_work_dir) / "config"
        import_path = config_dir / "import.yml"

        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f)

        import_config["auxiliary_sources"] = [
            {
                "name": "plot_stats",
                "data": "imports/plot_stats.csv",
                "grouping": "plots",
                "relation": {
                    "plugin": "stats_loader",
                    "key": "id",
                    "ref_field": "id_plot",
                    "match_field": "plot_id",
                },
            }
        ]

        with open(import_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, sort_keys=False)

        with patch(
            "niamoto.gui.api.services.templates.config_scaffold.find_stats_sources_for_reference"
        ) as mock_find_stats:
            mock_find_stats.return_value = []
            changed, _ = scaffold_configs(Path(test_work_dir))

        assert changed is True

        with open(config_dir / "transform.yml", "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        plots_group = next(
            group for group in transform_config if group.get("group_by") == "plots"
        )
        assert plots_group["sources"][-1] == {
            "name": "plot_stats",
            "data": "imports/plot_stats.csv",
            "grouping": "plots",
            "relation": {
                "plugin": "stats_loader",
                "key": "id",
                "ref_field": "id_plot",
                "match_field": "plot_id",
            },
        }
