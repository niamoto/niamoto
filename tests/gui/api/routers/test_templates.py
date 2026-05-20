"""
Integration tests for templates API endpoints.

These tests ensure that the templates endpoints work correctly
and serve as regression tests during refactoring.
"""

import asyncio
import pytest
from unittest.mock import patch
import os
from pathlib import Path
import tempfile
import shutil
import yaml
from types import SimpleNamespace

from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


class FakePreviewEngine:
    """Minimal preview engine for endpoint contract tests."""

    def __init__(self):
        self.requests = []

    def _compute_etag(self, request):
        return "test-preview-etag"

    def render(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            html="<html><body><main>Template preview</main></body></html>",
            etag="test-preview-etag",
        )


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
        response = client.get("/api/templates/taxons/suggestions")
        assert response.status_code == 200, response.text

        data = response.json()
        assert data["entity_type"] == "taxons"
        assert data["total_suggestions"] == len(data["suggestions"])
        assert data["total_suggestions"] > 0

    def test_get_suggestions_applies_max_suggestions_after_all_sources(
        self, client, monkeypatch
    ):
        """Reserved suggestion sources must not bypass the caller's final cap."""

        def suggestion(template_id: str, confidence: float):
            return {
                "template_id": template_id,
                "name": template_id,
                "description": template_id,
                "plugin": "field_aggregator",
                "category": "summary",
                "icon": "info",
                "confidence": confidence,
                "source": "template",
                "source_name": "taxons",
                "is_recommended": True,
                "config": {},
            }

        monkeypatch.setattr(
            "niamoto.gui.api.routers.templates.generate_navigation_suggestion",
            lambda reference_name: suggestion("navigation", 0.95),
        )
        monkeypatch.setattr(
            "niamoto.gui.api.routers.templates.generate_general_info_suggestion",
            lambda reference_name: suggestion("general_info", 0.90),
        )
        monkeypatch.setattr(
            "niamoto.gui.api.routers.templates.get_reference_enrichment_suggestions",
            lambda reference_name: [suggestion("enrichment", 0.85)],
        )
        monkeypatch.setattr(
            "niamoto.gui.api.routers.templates.get_entity_map_suggestions",
            lambda reference_name: [],
        )
        monkeypatch.setattr(
            "niamoto.gui.api.routers.templates.get_reference_field_suggestions",
            lambda reference_name: [suggestion("reference_field", 0.80)],
        )
        monkeypatch.setattr(
            "niamoto.gui.api.routers.templates.get_class_object_suggestions",
            lambda reference_name: [suggestion("class_object", 0.75)],
        )
        monkeypatch.setattr(
            "niamoto.gui.api.routers.templates.get_database_path",
            lambda: None,
        )

        response = client.get("/api/templates/taxons/suggestions?max_suggestions=1")

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total_suggestions"] == 1
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["template_id"] == "navigation"

    def test_get_configured_widgets(self, client):
        """Test GET /api/templates/{group_by}/configured."""
        response = client.get("/api/templates/taxons/configured")
        assert response.status_code == 200, response.text
        assert response.json() == {
            "configured_ids": ["elevation_binned_distribution_bar_plot"],
            "has_config": True,
        }

    def test_get_configured_widgets_rejects_non_list_transform_config(
        self, client, test_work_dir
    ):
        transform_path = Path(test_work_dir) / "config" / "transform.yml"
        transform_path.write_text("group_by: taxons\n", encoding="utf-8")

        response = client.get("/api/templates/taxons/configured")

        assert response.status_code == 400
        assert response.json()["detail"] == "transform.yml must be a list of groups"

    def test_get_configured_widgets_rejects_invalid_yaml(self, client, test_work_dir):
        transform_path = Path(test_work_dir) / "config" / "transform.yml"
        transform_path.write_text("groups: [\n", encoding="utf-8")

        response = client.get("/api/templates/taxons/configured")

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid transform.yml"

    def test_get_enrichment_catalog(self, client):
        """Test GET /api/templates/{reference}/enrichment-catalog."""
        with patch(
            "niamoto.gui.api.routers.templates.get_reference_enrichment_catalog"
        ) as mock_catalog:
            mock_catalog.return_value = [
                {
                    "id": "gbif",
                    "label": "GBIF",
                    "field_count": 2,
                    "fields": [
                        {
                            "source_id": "gbif",
                            "source_label": "GBIF",
                            "path": "canonical_name",
                            "label": "Nom canonique",
                            "format": "text",
                            "section_hint": "Identité",
                            "sample_values": ["Araucaria columnaris"],
                        }
                    ],
                }
            ]

            response = client.get("/api/templates/taxons/enrichment-catalog")

        assert response.status_code == 200, response.text
        assert response.json() == [
            {
                "id": "gbif",
                "label": "GBIF",
                "field_count": 2,
                "fields": [
                    {
                        "source_id": "gbif",
                        "source_label": "GBIF",
                        "path": "canonical_name",
                        "label": "Nom canonique",
                        "format": "text",
                        "section_hint": "Identité",
                        "sample_values": ["Araucaria columnaris"],
                    }
                ],
            }
        ]

    def test_get_enrichment_catalog_dispatches_catalog_to_threadpool(self, monkeypatch):
        from niamoto.gui.api.routers import templates

        captured = {}

        def fake_catalog(reference_name):
            captured["reference_name"] = reference_name
            return [
                {
                    "id": "gbif",
                    "label": "GBIF",
                    "field_count": 0,
                    "fields": [],
                }
            ]

        async def fake_run_in_threadpool(func, *args, **kwargs):
            captured["thread_func"] = func
            captured["thread_args"] = args
            captured["thread_kwargs"] = kwargs
            return func(*args, **kwargs)

        monkeypatch.setattr(templates, "get_reference_enrichment_catalog", fake_catalog)
        monkeypatch.setattr(templates, "run_in_threadpool", fake_run_in_threadpool)

        response = asyncio.run(templates.get_enrichment_catalog("taxons"))

        assert response[0].id == "gbif"
        assert captured["thread_func"] is fake_catalog
        assert captured["thread_args"] == ("taxons",)
        assert captured["thread_kwargs"] == {}
        assert captured["reference_name"] == "taxons"

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
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["group_by"] == "taxons"
        assert data["sources"][0]["name"] == "occurrences"
        assert data["sources"][0]["relation"]["plugin"] == "nested_set"
        assert data["widgets_data"]["test_widget"] == {
            "plugin": "binned_distribution",
            "params": {"field": "elevation"},
        }

    def test_generate_config_rejects_duplicate_template_ids(self, client):
        """Duplicate template IDs would otherwise overwrite selected widgets."""
        response = client.post(
            "/api/templates/generate-config",
            json={
                "templates": [
                    {
                        "template_id": "duplicate_widget",
                        "plugin": "field_aggregator",
                        "config": {"field": "name"},
                    },
                    {
                        "template_id": "duplicate_widget",
                        "plugin": "statistical_summary",
                        "config": {"field": "height"},
                    },
                ],
                "group_by": "taxons",
                "reference_kind": "hierarchical",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Duplicate template_id values"

    def test_generate_config_rejects_malformed_combined_config(self, client):
        response = client.post(
            "/api/templates/generate-config",
            json={
                "templates": [
                    {
                        "template_id": "combined_widget",
                        "plugin": "field_aggregator",
                        "config": {"transformer": None, "widget": {}},
                    }
                ],
                "group_by": "taxons",
                "reference_kind": "hierarchical",
            },
        )

        assert response.status_code == 422
        assert response.json()["detail"] == (
            "Combined template config requires object transformer and widget sections"
        )

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

    def test_save_config_requires_desktop_auth_token(self, client, monkeypatch):
        monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "secret-token")

        response = client.post(
            "/api/templates/save-config",
            json={
                "group_by": "taxons",
                "sources": [],
                "widgets_data": {},
                "mode": "merge",
            },
        )

        assert response.status_code == 401

    def test_save_config_does_not_update_export_when_transform_is_invalid(
        self, client, test_work_dir
    ):
        """Invalid transform payloads must not partially update export.yml."""
        config_dir = Path(test_work_dir) / "config"
        transform_path = config_dir / "transform.yml"
        export_path = config_dir / "export.yml"
        original_transform = transform_path.read_text(encoding="utf-8")
        original_export = export_path.read_text(encoding="utf-8")

        response = client.post(
            "/api/templates/save-config",
            json={
                "group_by": "taxons",
                "sources": [{"name": "broken_source"}],
                "widgets_data": {
                    "new_widget": {
                        "plugin": "field_aggregator",
                        "field": "elevation",
                        "params": {},
                    }
                },
                "mode": "replace",
            },
        )

        assert response.status_code == 500
        assert transform_path.read_text(encoding="utf-8") == original_transform
        assert export_path.read_text(encoding="utf-8") == original_export

    def test_save_config_does_not_update_export_when_transform_write_fails(
        self, client, test_work_dir
    ):
        config_dir = Path(test_work_dir) / "config"
        transform_path = config_dir / "transform.yml"
        export_path = config_dir / "export.yml"
        original_transform = transform_path.read_text(encoding="utf-8")
        original_export = export_path.read_text(encoding="utf-8")

        def fail_transform_serialization(path, payload):
            if Path(path).name == "transform.yml":
                raise OSError("simulated transform write failure")
            raise AssertionError("export.yml should not be serialized after failure")

        with patch(
            "niamoto.gui.api.routers.templates._serialize_yaml_to_temp",
            side_effect=fail_transform_serialization,
        ):
            response = client.post(
                "/api/templates/save-config",
                json={
                    "group_by": "taxons",
                    "sources": [],
                    "widgets_data": {},
                    "mode": "replace",
                },
            )

        assert response.status_code == 500
        assert transform_path.read_text(encoding="utf-8") == original_transform
        assert export_path.read_text(encoding="utf-8") == original_export

    def test_save_config_rolls_back_transform_when_export_replace_fails(
        self, client, test_work_dir
    ):
        config_dir = Path(test_work_dir) / "config"
        transform_path = config_dir / "transform.yml"
        export_path = config_dir / "export.yml"
        original_transform = transform_path.read_text(encoding="utf-8")
        original_export = export_path.read_text(encoding="utf-8")
        real_replace = os.replace
        replace_calls = 0

        def fail_second_replace(src, dst):
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 2:
                raise OSError("simulated export replace failure")
            return real_replace(src, dst)

        with patch(
            "niamoto.gui.api.routers.templates.os.replace",
            side_effect=fail_second_replace,
        ):
            response = client.post(
                "/api/templates/save-config",
                json={
                    "group_by": "taxons",
                    "sources": [],
                    "widgets_data": {
                        "summary": {
                            "plugin": "field_aggregator",
                            "params": {"field": "dbh"},
                        }
                    },
                    "mode": "replace",
                },
            )

        assert response.status_code == 500
        assert transform_path.read_text(encoding="utf-8") == original_transform
        assert export_path.read_text(encoding="utf-8") == original_export

    def test_save_config_rejects_non_list_transform_config(self, client, test_work_dir):
        config_dir = Path(test_work_dir) / "config"
        transform_path = config_dir / "transform.yml"
        transform_path.write_text(
            yaml.safe_dump({"groups": {"taxons": {"widgets_data": {}}}}),
            encoding="utf-8",
        )

        response = client.post(
            "/api/templates/save-config",
            json={
                "group_by": "taxons",
                "sources": [],
                "widgets_data": {},
                "mode": "merge",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "transform.yml must be a list of groups"

    def test_save_config_merge_updates_existing_export_widget(
        self, client, test_work_dir
    ):
        config_dir = Path(test_work_dir) / "config"
        export_path = config_dir / "export.yml"
        export_path.write_text(
            yaml.safe_dump(
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {},
                            "groups": [
                                {
                                    "group_by": "taxons",
                                    "widgets": [
                                        {
                                            "plugin": "old_widget",
                                            "title": "Old title",
                                            "data_source": "summary",
                                            "layout": {"order": 3, "colspan": 2},
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        response = client.post(
            "/api/templates/save-config",
            json={
                "group_by": "taxons",
                "sources": [],
                "widgets_data": {
                    "summary": {
                        "plugin": "field_aggregator",
                        "params": {"field": "dbh"},
                    }
                },
                "mode": "merge",
            },
        )

        assert response.status_code == 200, response.text
        saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
        widgets = saved["exports"][0]["groups"][0]["widgets"]
        assert len(widgets) == 1
        assert widgets[0]["data_source"] == "summary"
        assert widgets[0]["plugin"] == "info_grid"
        assert widgets[0]["layout"] == {"colspan": 2, "order": 3}

    def test_preview_template_returns_html(self, client):
        """Test GET /api/preview/{template_id} returns HTML."""
        preview_engine = FakePreviewEngine()
        with patch(
            "niamoto.gui.api.routers.preview.get_preview_engine",
            return_value=preview_engine,
        ):
            response = client.get("/api/preview/test_template?group_by=taxons")

        assert response.status_code == 200, response.text
        assert "text/html" in response.headers.get("content-type", "")
        assert "Template preview" in response.text
        assert preview_engine.requests[0].template_id == "test_template"
        assert preview_engine.requests[0].group_by == "taxons"

    def test_widget_suggestions_returns_class_object_contract(
        self, client, test_work_dir
    ):
        """Test GET /api/templates/widget-suggestions/{group_by}."""
        work_dir = Path(test_work_dir)
        imports_dir = work_dir / "imports"
        imports_dir.mkdir(exist_ok=True)
        stats_path = imports_dir / "taxon_stats.csv"
        stats_path.write_text(
            "\n".join(
                [
                    "id,class_object,class_name,class_value",
                    "1,cover_forest,Forest,0.75",
                    "2,cover_forest,Open,0.25",
                    "3,elevation_max,,1622",
                    "4,land_use,Forest,0.40",
                    "5,land_use,Savanna,0.35",
                    "6,land_use,Urban,0.25",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        transform_path = work_dir / "config" / "transform.yml"
        transform_config = yaml.safe_load(transform_path.read_text(encoding="utf-8"))
        transform_config[0]["sources"] = [
            {
                "name": "taxon_stats",
                "data": "imports/taxon_stats.csv",
                "grouping": "taxons",
                "relation": {"plugin": "direct_reference", "key": "id"},
            }
        ]
        transform_path.write_text(
            yaml.safe_dump(transform_config, sort_keys=False),
            encoding="utf-8",
        )

        response = client.get("/api/templates/widget-suggestions/taxons")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["source_name"] == "taxon_stats"
        assert payload["source_path"] == "imports/taxon_stats.csv"
        assert payload["categories_summary"]["binary"] == 1
        assert payload["categories_summary"]["scalar"] == 1

        class_objects = {item["name"]: item for item in payload["class_objects"]}
        assert class_objects["cover_forest"]["suggested_plugin"] == (
            "class_object_binary_aggregator"
        )
        assert class_objects["elevation_max"]["suggested_plugin"] == (
            "class_object_field_aggregator"
        )
        assert class_objects["land_use"]["suggested_plugin"] == (
            "class_object_series_extractor"
        )
        assert "class_object_binary_aggregator" in payload["plugin_schemas"]
        assert "class_object_field_aggregator" in payload["plugin_schemas"]
        for class_object in payload["class_objects"]:
            assert class_object["suggested_plugin"] in payload["plugin_schemas"]

    def test_widget_suggestions_accepts_tsv_class_object_source(
        self, client, test_work_dir
    ):
        work_dir = Path(test_work_dir)
        imports_dir = work_dir / "imports"
        imports_dir.mkdir(exist_ok=True)
        stats_path = imports_dir / "taxon_stats.tsv"
        stats_path.write_text(
            "\n".join(
                [
                    "id\tclass_object\tclass_name\tclass_value",
                    "1\tcover_forest\tForest\t0.75",
                    "2\tcover_forest\tOpen\t0.25",
                    "3\televation_max\t\t1622",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        transform_path = work_dir / "config" / "transform.yml"
        transform_config = yaml.safe_load(transform_path.read_text(encoding="utf-8"))
        transform_config[0]["sources"] = [
            {
                "name": "taxon_stats",
                "data": "imports/taxon_stats.tsv",
                "grouping": "taxons",
                "relation": {"plugin": "direct_reference", "key": "id"},
            }
        ]
        transform_path.write_text(
            yaml.safe_dump(transform_config, sort_keys=False),
            encoding="utf-8",
        )

        response = client.get("/api/templates/widget-suggestions/taxons")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["source_path"] == "imports/taxon_stats.tsv"
        class_objects = {item["name"]: item for item in payload["class_objects"]}
        assert class_objects["cover_forest"]["suggested_plugin"] == (
            "class_object_binary_aggregator"
        )
        assert class_objects["elevation_max"]["suggested_plugin"] == (
            "class_object_field_aggregator"
        )

    def test_widget_suggestions_rejects_source_path_escape(self, client, test_work_dir):
        work_dir = Path(test_work_dir)
        transform_path = work_dir / "config" / "transform.yml"
        transform_config = yaml.safe_load(transform_path.read_text(encoding="utf-8"))
        transform_config[0]["sources"] = [
            {
                "name": "taxon_stats",
                "data": "../outside.csv",
                "grouping": "taxons",
                "relation": {"plugin": "direct_reference", "key": "id"},
            }
        ]
        transform_path.write_text(
            yaml.safe_dump(transform_config, sort_keys=False),
            encoding="utf-8",
        )

        response = client.get("/api/templates/widget-suggestions/taxons")

        assert response.status_code == 400
        assert "inside the project directory" in response.json()["detail"]

    def test_widget_suggestions_requires_working_directory(self):
        """Missing working directory should return a controlled API error."""
        with patch(
            "niamoto.gui.api.routers.templates.get_working_directory",
            return_value=None,
        ):
            client = TestClient(create_app())
            response = client.get("/api/templates/widget-suggestions/taxons")

        assert response.status_code == 500
        assert response.json()["detail"] == "Working directory not configured"

    def test_widget_suggestions_hides_unexpected_exception_details(
        self, client, test_work_dir
    ):
        work_dir = Path(test_work_dir)
        imports_dir = work_dir / "imports"
        imports_dir.mkdir(exist_ok=True)
        stats_path = imports_dir / "taxon_stats.csv"
        stats_path.write_text("id,value\n1,2\n", encoding="utf-8")

        transform_path = work_dir / "config" / "transform.yml"
        transform_config = yaml.safe_load(transform_path.read_text(encoding="utf-8"))
        transform_config[0]["sources"] = [
            {
                "name": "taxon_stats",
                "data": "imports/taxon_stats.csv",
                "grouping": "taxons",
            }
        ]
        transform_path.write_text(
            yaml.safe_dump(transform_config, sort_keys=False),
            encoding="utf-8",
        )

        with patch(
            "niamoto.gui.api.routers.templates.analyze_csv",
            side_effect=RuntimeError("secret /tmp/private.csv"),
        ):
            response = client.get("/api/templates/widget-suggestions/taxons")

        assert response.status_code == 500
        assert response.json()["detail"] == (
            "Error analyzing CSV for widget suggestions"
        )
        assert "secret /tmp/private.csv" not in response.text

    def test_combined_suggestions_requires_fields(self, client):
        """Test POST /api/templates/{reference}/combined-suggestions."""
        response = client.post(
            "/api/templates/taxons/combined-suggestions",
            json={"fields": ["elevation", "dbh"]},
        )
        assert response.status_code == 422

    def test_combined_suggestions_hides_unexpected_exception_details(self, client):
        """Unexpected backend errors should not leak internals to clients."""
        with (
            patch(
                "niamoto.gui.api.routers.templates.get_database_path",
                return_value="/tmp/niamoto.duckdb",
            ),
            patch(
                "niamoto.gui.api.routers.templates.Database",
                side_effect=RuntimeError("/private/path secret"),
            ),
        ):
            response = client.post(
                "/api/templates/taxons/combined-suggestions",
                json={
                    "selected_fields": ["elevation", "dbh"],
                    "source_name": "taxons",
                },
            )

        assert response.status_code == 500
        assert response.json()["detail"] == (
            "Failed to generate combined widget suggestions"
        )
        assert "/private/path secret" not in response.text

    def test_combined_suggestions_uses_reference_specific_default_source(
        self, client, test_work_dir
    ):
        """Omitted source_name should resolve from the requested reference scope."""

        import_path = Path(test_work_dir) / "config" / "import.yml"
        import_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
        import_config["entities"]["datasets"]["plot_measurements"] = {
            "connector": {
                "type": "file",
                "format": "csv",
                "path": "imports/plot_measurements.csv",
            }
        }
        import_config["entities"]["references"]["plots"]["relation"] = {
            "dataset": "plot_measurements",
            "foreign_key": "plot_name",
            "reference_key": "plot",
        }
        import_path.write_text(yaml.safe_dump(import_config), encoding="utf-8")

        class EntityMeta:
            config = {
                "semantic_profile": {
                    "columns": [
                        {
                            "name": "dbh",
                            "dtype": "float64",
                            "data_category": "numeric_continuous",
                            "field_purpose": "measurement",
                        },
                        {
                            "name": "height",
                            "dtype": "float64",
                            "data_category": "numeric_continuous",
                            "field_purpose": "measurement",
                        },
                    ]
                }
            }

        captured = {}

        def fake_suggest_combined_widgets(
            selected_field_names, all_profiles, source_name
        ):
            captured["selected_field_names"] = selected_field_names
            captured["source_name"] = source_name
            captured["profile_names"] = [profile.name for profile in all_profiles]
            return []

        with (
            patch(
                "niamoto.gui.api.routers.templates.get_database_path",
                return_value=Path("/tmp/niamoto.duckdb"),
            ),
            patch("niamoto.gui.api.routers.templates.Database") as database_cls,
            patch("niamoto.core.imports.registry.EntityRegistry") as registry_cls,
            patch(
                "niamoto.gui.api.routers.templates.suggest_combined_widgets",
                side_effect=fake_suggest_combined_widgets,
            ),
            patch(
                "niamoto.gui.api.routers.templates.detect_all_groups", return_value=[]
            ),
        ):
            registry_cls.return_value.get.return_value = EntityMeta()

            response = client.post(
                "/api/templates/plots/combined-suggestions",
                json={"selected_fields": ["dbh", "height"]},
            )

        assert response.status_code == 200
        registry_cls.return_value.get.assert_called_once_with("plot_measurements")
        assert captured == {
            "selected_field_names": ["dbh", "height"],
            "source_name": "plot_measurements",
            "profile_names": ["dbh", "height"],
        }
        database_cls.return_value.close_db_session.assert_called_once()

    def test_combined_suggestions_rejects_cross_reference_source(
        self, client, test_work_dir
    ):
        """Explicit source_name must belong to the requested reference."""

        import_path = Path(test_work_dir) / "config" / "import.yml"
        import_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
        import_config["entities"]["datasets"]["plot_measurements"] = {
            "connector": {
                "type": "file",
                "format": "csv",
                "path": "imports/plot_measurements.csv",
            }
        }
        import_config["entities"]["references"]["plots"]["relation"] = {
            "dataset": "plot_measurements",
            "foreign_key": "plot_name",
            "reference_key": "plot",
        }
        import_path.write_text(yaml.safe_dump(import_config), encoding="utf-8")

        with patch(
            "niamoto.gui.api.routers.templates.get_database_path",
            return_value=Path("/tmp/niamoto.duckdb"),
        ):
            response = client.post(
                "/api/templates/plots/combined-suggestions",
                json={
                    "selected_fields": ["dbh", "height"],
                    "source_name": "occurrences",
                },
            )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Source 'occurrences' is not configured for reference 'plots'"
        )

    def test_reference_suggestions_rejects_cross_reference_source(
        self, client, test_work_dir
    ):
        import_path = Path(test_work_dir) / "config" / "import.yml"
        import_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
        import_config["entities"]["datasets"]["plot_measurements"] = {
            "connector": {
                "type": "file",
                "format": "csv",
                "path": "imports/plot_measurements.csv",
            }
        }
        import_config["entities"]["references"]["plots"]["relation"] = {
            "dataset": "plot_measurements",
            "foreign_key": "plot_name",
            "reference_key": "plot",
        }
        import_path.write_text(yaml.safe_dump(import_config), encoding="utf-8")

        response = client.get("/api/templates/plots/suggestions?entity=occurrences")

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Source 'occurrences' is not configured for reference 'plots'"
        )

    def test_reference_suggestions_rejects_missing_configured_registry_source(
        self, client
    ):
        db_path = Path("/tmp/test-niamoto.duckdb")
        with (
            patch(
                "niamoto.gui.api.routers.templates.get_database_path",
                return_value=db_path,
            ),
            patch("niamoto.gui.api.routers.templates.Database") as database_cls,
            patch("niamoto.core.imports.registry.EntityRegistry") as registry_cls,
        ):
            registry_cls.return_value.get.side_effect = KeyError("missing")
            response = client.get(
                "/api/templates/taxons/suggestions?entity=occurrences"
            )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Source entity 'occurrences' is not available in the import registry"
        )
        database_cls.return_value.close_db_session.assert_called_once()

    def test_semantic_groups_endpoint(self, client):
        """Test GET /api/templates/{reference}/semantic-groups."""
        db_path = Path("/tmp/test-niamoto.duckdb")
        with (
            patch(
                "niamoto.gui.api.routers.templates.get_database_path",
                return_value=db_path,
            ),
            patch("niamoto.gui.api.routers.templates.Database") as database_cls,
            patch("niamoto.core.imports.registry.EntityRegistry") as registry_cls,
        ):
            registry_cls.return_value.get.side_effect = KeyError("missing")
            response = client.get("/api/templates/taxons/semantic-groups")

        assert response.status_code == 200
        assert response.json() == {"groups": []}
        database_cls.assert_called_once_with(str(db_path), read_only=True)
        database_cls.return_value.close_db_session.assert_called_once()

    def test_semantic_groups_rejects_cross_reference_source(
        self, client, test_work_dir
    ):
        import_path = Path(test_work_dir) / "config" / "import.yml"
        import_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
        import_config["entities"]["datasets"]["plot_measurements"] = {
            "connector": {
                "type": "file",
                "format": "csv",
                "path": "imports/plot_measurements.csv",
            }
        }
        import_config["entities"]["references"]["plots"]["relation"] = {
            "dataset": "plot_measurements",
            "foreign_key": "plot_name",
            "reference_key": "plot",
        }
        import_path.write_text(yaml.safe_dump(import_config), encoding="utf-8")

        with patch(
            "niamoto.gui.api.routers.templates.get_database_path",
            return_value=Path("/tmp/niamoto.duckdb"),
        ):
            response = client.get(
                "/api/templates/plots/semantic-groups?entity=occurrences"
            )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Source 'occurrences' is not configured for reference 'plots'"
        )


class TestTemplatesRouterRegistration:
    """Test that templates router is properly registered."""

    def test_templates_router_is_included(self, client):
        """Verify templates router endpoints are accessible."""
        response = client.get("/api/templates/categories")
        assert response.status_code == 200, response.text

    def test_templates_endpoints_have_correct_prefix(self, client):
        """Verify all templates endpoints use /api/templates prefix."""
        expected_statuses = {
            "/api/templates/categories": 200,
            "/api/templates/taxons/suggestions": 200,
            "/api/templates/taxons/configured": 200,
        }
        for endpoint, expected_status in expected_statuses.items():
            response = client.get(endpoint)
            assert response.status_code == expected_status, response.text

        preview_engine = FakePreviewEngine()
        with patch(
            "niamoto.gui.api.routers.preview.get_preview_engine",
            return_value=preview_engine,
        ):
            response = client.get("/api/preview/test")

        assert response.status_code == 200, response.text
        assert preview_engine.requests[0].template_id == "test"


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
        preview_engine = FakePreviewEngine()
        with patch(
            "niamoto.gui.api.routers.preview.get_preview_engine",
            return_value=preview_engine,
        ):
            response = client.get(
                "/api/preview/elevation_binned_distribution_bar_plot",
                params={"group_by": "taxons"},
            )

        assert response.status_code == 200, response.text
        assert preview_engine.requests[0].template_id == (
            "elevation_binned_distribution_bar_plot"
        )
        assert preview_engine.requests[0].group_by == "taxons"

    def test_preview_with_entity_id_parameter(self, client):
        """Test preview endpoint accepts entity_id parameter."""
        preview_engine = FakePreviewEngine()
        with patch(
            "niamoto.gui.api.routers.preview.get_preview_engine",
            return_value=preview_engine,
        ):
            response = client.get(
                "/api/preview/test_template",
                params={"group_by": "taxons", "entity_id": "123"},
            )

        assert response.status_code == 200, response.text
        assert preview_engine.requests[0].template_id == "test_template"
        assert preview_engine.requests[0].group_by == "taxons"
        assert preview_engine.requests[0].entity_id == "123"

    def test_preview_returns_html_content_type(self, client):
        """Test preview endpoint returns HTML content type."""
        preview_engine = FakePreviewEngine()
        with patch(
            "niamoto.gui.api.routers.preview.get_preview_engine",
            return_value=preview_engine,
        ):
            response = client.get(
                "/api/preview/test_template", params={"group_by": "taxons"}
            )

        assert response.status_code == 200, response.text
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type

    def test_preview_legacy_class_object_scalar_template_id(self, client):
        """Legacy *_field_aggregator_* IDs must resolve to class_object previews."""
        from niamoto.gui.api.services.templates.utils.widget_utils import (
            parse_dynamic_template_id,
        )

        template_id = "forest_reserve_ha_field_aggregator_radial_gauge"
        assert parse_dynamic_template_id(template_id) == {
            "column": "forest_reserve_ha",
            "transformer": "field_aggregator",
            "widget": "radial_gauge",
        }

        preview_engine = FakePreviewEngine()
        with patch(
            "niamoto.gui.api.routers.preview.get_preview_engine",
            return_value=preview_engine,
        ):
            response = client.get(
                f"/api/preview/{template_id}",
                params={"group_by": "shapes", "source": "shape_stats"},
            )

        assert response.status_code == 200, response.text
        assert "<p class='error'>" not in response.text.lower()
        assert preview_engine.requests[0].template_id == template_id
        assert preview_engine.requests[0].group_by == "shapes"
        assert preview_engine.requests[0].source == "shape_stats"

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
