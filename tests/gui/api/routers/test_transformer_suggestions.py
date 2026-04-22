"""Contract tests for transformer suggestions router."""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

from fastapi.testclient import TestClient
import yaml

from niamoto.gui.api.app import create_app


def test_list_entities_with_suggestions_filters_entities_without_profiles(monkeypatch):
    class FakeRegistry:
        def __init__(self, db):
            self.db = db

        def list_entities(self):
            return [
                SimpleNamespace(name="plots"),
                SimpleNamespace(name="taxons"),
                SimpleNamespace(name="occurrences"),
            ]

        def get(self, name):
            if name == "plots":
                return SimpleNamespace(
                    name="plots",
                    config={
                        "semantic_profile": {
                            "columns": [],
                            "transformer_suggestions": {},
                        }
                    },
                )
            if name == "taxons":
                raise RuntimeError("registry error")
            return SimpleNamespace(name=name, config={})

    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.get_database_path",
        lambda: "/tmp/niamoto.duckdb",
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.open_database",
        lambda db_path: nullcontext(object()),
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.EntityRegistry",
        FakeRegistry,
    )

    client = TestClient(create_app())
    response = client.get("/api/transformer-suggestions/")

    assert response.status_code == 200
    assert response.json() == ["plots"]


def test_get_available_references_reads_entity_registry_v2_config(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "description": "Main observations",
                        }
                    },
                    "references": {
                        "taxons": {
                            "kind": "hierarchical",
                            "description": "Taxonomic reference",
                            "connector": {
                                "type": "derived",
                                "extraction": {"id_column": "taxon_ref_id"},
                            },
                        },
                        "plots": {
                            "kind": "generic",
                            "relation": {
                                "foreign_key": "plot_id",
                                "reference_key": "id",
                            },
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.get_working_directory",
        lambda: tmp_path,
    )

    client = TestClient(create_app())
    response = client.get("/api/transformer-suggestions/references")

    assert response.status_code == 200
    payload = response.json()
    assert payload["datasets"] == [
        {"name": "occurrences", "description": "Main observations"}
    ]
    references_by_name = {item["name"]: item for item in payload["references"]}
    assert references_by_name == {
        "taxons": {
            "name": "taxons",
            "kind": "hierarchical",
            "description": "Taxonomic reference",
            "relation": {
                "plugin": "nested_set",
                "key": "taxon_ref_id",
                "ref_key": "taxons_id",
                "fields": {
                    "left": "lft",
                    "right": "rght",
                    "parent": "parent_id",
                },
            },
        },
        "plots": {
            "name": "plots",
            "kind": "generic",
            "description": None,
            "relation": {
                "plugin": "direct_reference",
                "key": "plot_id",
                "ref_key": "id",
                "fields": None,
            },
        },
    }


def test_get_transformer_suggestions_returns_semantic_profile_payload(monkeypatch):
    semantic_profile = {
        "analyzed_at": "2026-04-22T10:00:00Z",
        "columns": [
            {
                "name": "elevation",
                "data_category": "numeric_continuous",
                "field_purpose": "measurement",
                "cardinality": 12,
                "suggested_bins": [0.0, 100.0, 200.0],
                "suggested_labels": None,
                "value_range": [0.0, 200.0],
            }
        ],
        "transformer_suggestions": {
            "elevation": [
                {
                    "transformer": "binned_distribution",
                    "confidence": 0.91,
                    "reason": "Numeric measurement",
                    "config": {
                        "plugin": "binned_distribution",
                        "params": {"field": "elevation", "source": "occurrences"},
                    },
                }
            ]
        },
    }

    class FakeRegistry:
        def __init__(self, db):
            self.db = db

        def get(self, entity_name):
            return SimpleNamespace(
                name=entity_name,
                config={"semantic_profile": semantic_profile},
            )

    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.get_database_path",
        lambda: "/tmp/niamoto.duckdb",
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.open_database",
        lambda db_path: nullcontext(object()),
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.EntityRegistry",
        FakeRegistry,
    )

    client = TestClient(create_app())
    response = client.get("/api/transformer-suggestions/occurrences")

    assert response.status_code == 200
    assert response.json() == {
        "entity_name": "occurrences",
        "analyzed_at": "2026-04-22T10:00:00Z",
        "columns": [
            {
                "name": "elevation",
                "data_category": "numeric_continuous",
                "field_purpose": "measurement",
                "cardinality": 12,
                "suggested_bins": [0.0, 100.0, 200.0],
                "suggested_labels": None,
                "value_range": [0.0, 200.0],
            }
        ],
        "suggestions": {
            "elevation": [
                {
                    "transformer": "binned_distribution",
                    "confidence": 0.91,
                    "reason": "Numeric measurement",
                    "config": {
                        "plugin": "binned_distribution",
                        "params": {
                            "field": "elevation",
                            "source": "occurrences",
                        },
                    },
                }
            ]
        },
    }


def test_get_transformer_suggestions_returns_404_without_semantic_profile(monkeypatch):
    class FakeRegistry:
        def __init__(self, db):
            self.db = db

        def get(self, entity_name):
            return SimpleNamespace(name=entity_name, config={"notes": "exists"})

    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.get_database_path",
        lambda: "/tmp/niamoto.duckdb",
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.open_database",
        lambda db_path: nullcontext(object()),
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.transformer_suggestions.EntityRegistry",
        FakeRegistry,
    )

    client = TestClient(create_app())
    response = client.get("/api/transformer-suggestions/occurrences")

    assert response.status_code == 404
    assert "No semantic analysis available" in response.json()["detail"]
