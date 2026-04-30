"""Tests for collection catalog API routes."""

from __future__ import annotations

import yaml


def test_list_collections_returns_reviewable_candidates(
    gui_duckdb_client, gui_duckdb_context
):
    response = gui_duckdb_client.get("/api/collections")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["collections"][0]["name"] == "taxons"
    assert payload["collections"][0]["review_status"] == "pending"
    assert payload["collections"][0]["roles"] == ["site", "api"]
    assert payload["sources"] == [
        {"type": "reference", "name": "taxons", "label": "taxons"},
        {"type": "dataset", "name": "occurrences", "label": "occurrences"},
    ]


def test_update_collection_review_state_persists_metadata(
    gui_duckdb_client, gui_duckdb_context
):
    response = gui_duckdb_client.patch(
        "/api/collections/taxons",
        json={
            "label": "Taxonomic tree",
            "roles": ["standard", "technical"],
            "visible": False,
            "review_status": "accepted",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["collection"]["label"] == "Taxonomic tree"
    assert payload["collection"]["roles"] == ["standard", "technical"]
    assert payload["collection"]["visible"] is False

    saved = yaml.safe_load(
        (gui_duckdb_context / "config" / "import.yml").read_text(encoding="utf-8")
    )
    assert saved["metadata"]["collections"]["taxons"] == {
        "label": "Taxonomic tree",
        "roles": ["standard", "technical"],
        "visible": False,
        "review_status": "accepted",
    }


def test_create_manual_collection_from_dataset_persists_non_page_collection(
    gui_duckdb_client, gui_duckdb_context
):
    response = gui_duckdb_client.post(
        "/api/collections",
        json={
            "name": "occurrence_records",
            "source_type": "dataset",
            "source_name": "occurrences",
            "grain": "occurrence",
            "roles": ["api", "standard"],
            "visible": False,
            "label": "Occurrence records",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["collection"]["name"] == "occurrence_records"
    assert payload["collection"]["source_type"] == "dataset"
    assert payload["collection"]["roles"] == ["api", "standard"]
    assert payload["collection"]["visible"] is False

    saved = yaml.safe_load(
        (gui_duckdb_context / "config" / "import.yml").read_text(encoding="utf-8")
    )
    assert saved["metadata"]["collections"]["occurrence_records"]["source"] == {
        "type": "dataset",
        "name": "occurrences",
    }


def test_create_manual_collection_rejects_unknown_source_without_writing(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    before = import_path.read_text(encoding="utf-8")

    response = gui_duckdb_client.post(
        "/api/collections",
        json={
            "name": "bad_collection",
            "source_type": "dataset",
            "source_name": "missing",
            "grain": "occurrence",
            "roles": ["api"],
        },
    )

    assert response.status_code == 404
    assert "Unknown dataset source 'missing'" in response.json()["detail"]
    assert import_path.read_text(encoding="utf-8") == before
