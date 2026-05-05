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


def test_get_collection_data_options_recommends_dwc_for_occurrence_collection(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    import_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    import_config["metadata"] = {
        "collections": {
            "occurrence_records": {
                "source": {"type": "dataset", "name": "occurrences"},
                "grain": "occurrence",
                "roles": ["api", "standard"],
                "review_status": "accepted",
            }
        }
    }
    import_path.write_text(
        yaml.safe_dump(import_config, sort_keys=False),
        encoding="utf-8",
    )
    (gui_duckdb_context / "config" / "export.yml").write_text(
        "exports: []\n",
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/collections/occurrence_records/data-options")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["state"] == "recommended"
    assert payload["configured_outputs"] == []
    assert payload["primary_action"] == {
        "type": "create_standard_profile",
        "label": "Create Darwin Core Occurrence",
        "target": {
            "collection": "occurrence_records",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
        },
    }
    dwc_option = next(
        option
        for option in payload["available_options"]
        if option["id"] == "darwin_core_occurrence"
    )
    assert dwc_option["suitability"] == "recommended"
    assert dwc_option["evidence"][-1]["details"] == {"total": 4}


def test_get_collection_data_options_surfaces_configured_outputs_first(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "public_json",
                        "enabled": True,
                        "exporter": "json_api_exporter",
                        "params": {"output_dir": "exports/public_json"},
                        "groups": [
                            {
                                "group_by": "taxons",
                                "detail": {"pass_through": True},
                                "index": {"fields": []},
                            }
                        ],
                    },
                    {
                        "name": "dwc_occurrence_json",
                        "exporter": "json_api_exporter",
                        "params": {"output_dir": "exports/dwc"},
                        "groups": [
                            {
                                "group_by": "taxons",
                                "transformer_plugin": "niamoto_to_dwc_occurrence",
                                "transformer_params": {
                                    "occurrence_list_source": "occurrences",
                                    "mapping": {},
                                },
                            }
                        ],
                    },
                ],
                "standard_profiles": [
                    {
                        "name": "dwc_taxons",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "collection", "name": "taxons"},
                        "mappings": {"occurrenceID": {"source": "id"}},
                        "outputs": [{"type": "api_json"}],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/collections/taxons/data-options")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["state"] == "configured"
    assert payload["primary_action"] is None
    kinds = [output["kind"] for output in payload["configured_outputs"]]
    assert kinds == [
        "api_json",
        "api_json",
        "standard_profile",
        "legacy_standard_hint",
    ]
    public_json = payload["configured_outputs"][0]
    assert public_json["name"] == "public_json"
    assert "output_dir" not in public_json["summary"]
    legacy_hint = payload["configured_outputs"][-1]
    assert legacy_hint["standard"] == "darwin_core_occurrence"


def test_get_collection_data_options_with_missing_evidence_has_no_primary_action(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    import_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    import_config["metadata"] = {
        "collections": {
            "mystery_records": {
                "source": {"type": "dataset", "name": "occurrences"},
                "grain": "unknown",
                "roles": ["api"],
                "review_status": "accepted",
            }
        }
    }
    import_path.write_text(
        yaml.safe_dump(import_config, sort_keys=False),
        encoding="utf-8",
    )
    (gui_duckdb_context / "config" / "export.yml").write_text(
        "exports: []\n",
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/collections/mystery_records/data-options")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["state"] == "needs_intent"
    assert payload["primary_action"] is None
    assert "Collection grain is unknown." in payload["missing_evidence"]


def test_get_collection_data_options_unknown_collection_returns_404(
    gui_duckdb_client,
):
    response = gui_duckdb_client.get("/api/collections/missing/data-options")

    assert response.status_code == 404
