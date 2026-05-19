"""Tests for standard profile API routes."""

from __future__ import annotations

import yaml

from niamoto.gui.api.routers import standard_profiles as standard_profiles_router


def test_create_standard_profile_persists_under_standard_profiles(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text("exports: []\n", encoding="utf-8")

    response = gui_duckdb_client.post(
        "/api/standard-profiles",
        json={
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "context": {"type": "collection", "name": "taxons"},
            "outputs": [{"type": "api_json"}],
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["profile"]["name"] == "dwc_occurrences"
    assert payload["profile"]["validation_status"] == "invalid"

    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    assert saved["exports"] == []
    assert saved["standard_profiles"][0]["name"] == "dwc_occurrences"
    assert saved["standard_profiles"][0]["source"] == {
        "type": "dataset",
        "name": "occurrences",
    }
    assert saved["standard_profiles"][0]["validation_status"] == "invalid"


def test_update_standard_profile_rejects_empty_target_grain(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    original = yaml.safe_dump(
        {
            "standard_profiles": [
                {
                    "name": "dwc_occurrences",
                    "standard": "darwin_core_occurrence",
                    "target_grain": "occurrence",
                    "source": {"type": "dataset", "name": "occurrences"},
                }
            ]
        },
        sort_keys=False,
    )
    export_path.write_text(original, encoding="utf-8")

    response = gui_duckdb_client.patch(
        "/api/standard-profiles/dwc_occurrences",
        json={"target_grain": ""},
    )

    assert response.status_code == 422
    assert export_path.read_text(encoding="utf-8") == original


def test_list_standard_profiles_includes_legacy_hints(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "dwc_occurrence_json",
                        "exporter": "json_api_exporter",
                        "params": {
                            "output_dir": "exports/dwc",
                            "detail_output_pattern": "{group}/{id}.json",
                        },
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
                    }
                ],
                "standard_profiles": [
                    {
                        "name": "inventory_events",
                        "standard": "humboldt_event",
                        "target_grain": "event",
                        "source": {"type": "collection", "name": "taxons"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/standard-profiles")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["profiles"][0]["name"] == "inventory_events"
    assert payload["legacy_hints"][0]["export_name"] == "dwc_occurrence_json"
    assert payload["legacy_hints"][0]["source"] == {
        "type": "collection",
        "name": "taxons",
    }


def test_list_standard_profiles_returns_current_validation_status(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "dwc_occurrences",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                        "mappings": {"occurrenceID": {"source": "id"}},
                        "validation_status": "draft",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/standard-profiles")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["profiles"][0]["validation_status"] == "conformant"
    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    assert saved["standard_profiles"][0]["validation_status"] == "draft"


def test_auto_config_standard_profile_returns_reviewable_dwc_proposal(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text("exports: []\n", encoding="utf-8")
    before = export_path.read_text(encoding="utf-8")

    response = gui_duckdb_client.post(
        "/api/standard-profiles/auto-config",
        json={
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["profile"]["name"] == "dwc_occurrences"
    assert payload["profile"]["target_grain"] == "occurrence"
    assert payload["profile"]["mappings"]["occurrenceID"] == {"source": "id"}
    assert payload["profile"]["mappings"]["locality"] == {"source": "locality"}
    assert payload["profile"]["mappings"]["basisOfRecord"] == {
        "generator": "constant",
        "params": {"value": "HumanObservation"},
    }
    assert payload["profile"]["outputs"][1]["type"] == "dwc_archive"
    assert "scientificName" in payload["unresolved"]
    assert "basisOfRecord" not in payload["unresolved"]
    assert payload["rows_sampled"] == 3
    assert payload["columns_inspected"] == 4
    assert export_path.read_text(encoding="utf-8") == before


def test_auto_config_standard_profile_resolves_related_occurrence_source(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "references": {
                        "taxons": {
                            "kind": "hierarchical",
                        }
                    },
                    "datasets": {
                        "occurrences": {
                            "links": [
                                {
                                    "entity": "taxons",
                                    "field": "taxon_id",
                                    "target_field": "id",
                                }
                            ]
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.post(
        "/api/standard-profiles/auto-config",
        json={
            "name": "dwc_taxons",
            "standard": "darwin_core_occurrence",
            "source": {"type": "collection", "name": "taxons"},
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["profile"]["source"] == {"type": "collection", "name": "taxons"}
    assert payload["record_source"] == {"type": "dataset", "name": "occurrences"}
    assert payload["profile"]["mappings"]["occurrenceID"] == {"source": "id"}
    assert payload["profile"]["metadata"]["auto_config"]["record_source"] == {
        "type": "dataset",
        "name": "occurrences",
    }


def test_standard_profile_source_fields_resolve_effective_record_source(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "references": {
                        "taxons": {
                            "kind": "hierarchical",
                        }
                    },
                    "datasets": {
                        "occurrences": {
                            "links": [
                                {
                                    "entity": "taxons",
                                    "field": "taxon_id",
                                    "target_field": "id",
                                }
                            ]
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.post(
        "/api/standard-profiles/source-fields",
        json={
            "standard": "darwin_core_occurrence",
            "source": {"type": "collection", "name": "taxons"},
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source"] == {"type": "collection", "name": "taxons"}
    assert payload["record_source"] == {"type": "dataset", "name": "occurrences"}
    assert [field["name"] for field in payload["fields"]] == [
        "id",
        "taxon_id",
        "count",
        "locality",
    ]


def test_execute_standard_profile_output_draft_writes_isolated_artifact(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "dwc_occurrences",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                        "mappings": {"occurrenceID": {"source": "id"}},
                        "outputs": [
                            {
                                "type": "dwc_archive",
                                "params": {
                                    "output_dir": "exports/final/dwc",
                                    "archive_name": "draft-dwc.zip",
                                },
                            }
                        ],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.post(
        "/api/standard-profiles/dwc_occurrences/outputs/dwc_archive/draft"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["metadata"]["draft"] is True
    assert payload["metadata"]["publication_output"] is False
    assert payload["metadata"]["retention_policy"] == {
        "type": "manual_cleanup",
        "location": "exports/.draft/profiles",
    }
    assert (
        "exports/.draft/profiles/dwc_occurrences/dwc_archive" in payload["output_path"]
    )
    assert not (gui_duckdb_context / "exports" / "final" / "dwc").exists()


def test_update_and_delete_standard_profile(gui_duckdb_client, gui_duckdb_context):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "dwc_occurrences",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.patch(
        "/api/standard-profiles/dwc_occurrences",
        json={
            "enabled": False,
            "mappings": {"occurrenceID": {"source": "id"}},
            "outputs": [
                {"type": "dwc_archive", "params": {"output_dir": "exports/dwc"}}
            ],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["profile"]["enabled"] is False
    assert response.json()["profile"]["validation_status"] == "conformant"
    assert response.json()["profile"]["outputs"][0]["type"] == "dwc_archive"
    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    assert saved["standard_profiles"][0]["validation_status"] == "conformant"

    response = gui_duckdb_client.delete("/api/standard-profiles/dwc_occurrences")

    assert response.status_code == 200, response.text
    assert response.json() == {"success": True, "deleted": "dwc_occurrences"}
    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    assert saved["standard_profiles"] == []


def test_create_standard_profile_rejects_unknown_source_without_writing(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text("exports: []\n", encoding="utf-8")
    before = export_path.read_text(encoding="utf-8")

    response = gui_duckdb_client.post(
        "/api/standard-profiles",
        json={
            "name": "bad_profile",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "missing"},
        },
    )

    assert response.status_code == 404
    assert "Unknown dataset source 'missing'" in response.json()["detail"]
    assert export_path.read_text(encoding="utf-8") == before


def test_standard_profile_compatibility_report_uses_collection_context(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "references": {
                        "taxons": {
                            "kind": "hierarchical",
                            "schema": {
                                "fields": [{"name": "species", "type": "string"}]
                            },
                        }
                    },
                    "datasets": {
                        "occurrences": {
                            "schema": {
                                "fields": [
                                    {"name": "occurrence_id", "type": "string"},
                                    {"name": "taxon_id", "type": "integer"},
                                ]
                            },
                            "links": [
                                {
                                    "entity": "taxons",
                                    "field": "taxon_id",
                                    "target_field": "id",
                                }
                            ],
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "dwc_taxon_context",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "collection", "name": "taxons"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get(
        "/api/standard-profiles/dwc_taxon_context/compatibility"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "compatible"
    assert payload["source_grain"] == "taxon"
    assert payload["evidence"][0]["details"]["occurrence_dataset"] == "occurrences"


def test_standard_profile_compatibility_errors_return_client_error(
    monkeypatch, gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "bad_profile",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    class FailingCompatibilityService:
        def evaluate(self, profile):
            raise ValueError("Unsupported compatibility setup")

    monkeypatch.setattr(
        standard_profiles_router,
        "_compatibility_service",
        lambda: FailingCompatibilityService(),
    )

    response = gui_duckdb_client.get("/api/standard-profiles/bad_profile/compatibility")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported compatibility setup"


def test_standard_profile_validation_report_serializes_summary_and_details(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "dwc_occurrences",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                        "mappings": {},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get(
        "/api/standard-profiles/dwc_occurrences/validation"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "invalid"
    assert payload["summary"]["critical"] == 1
    assert payload["checklist"][0]["code"] == "dwc_occurrence_id"
    assert payload["issues"][0]["severity"] == "critical"


def test_execute_standard_profile_api_json_output(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "schema": {
                                "fields": [
                                    {"name": "id", "type": "integer"},
                                    {"name": "scientific_name", "type": "string"},
                                ]
                            }
                        }
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "dwc_occurrences",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                        "mappings": {
                            "occurrenceID": {"source": "id"},
                            "scientificName": {"source": "scientific_name"},
                        },
                        "outputs": [
                            {
                                "type": "api_json",
                                "params": {
                                    "output_dir": ("exports/profiles/dwc_occurrences")
                                },
                            }
                        ],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.post(
        "/api/standard-profiles/dwc_occurrences/outputs/api_json"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    output_path = (
        gui_duckdb_context
        / "exports"
        / "profiles"
        / "dwc_occurrences"
        / "dwc_occurrences.json"
    )
    assert payload["status"] == "success"
    assert payload["output_path"] == str(output_path)
    assert output_path.exists()


def test_preview_standard_profile_api_json_output(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "dwc_occurrences",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                        "mappings": {
                            "occurrenceID": {"source": "id"},
                            "locality": {"source": "locality"},
                        },
                        "outputs": [{"type": "api_json"}],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get(
        "/api/standard-profiles/dwc_occurrences/outputs/api_json/preview"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["profile_name"] == "dwc_occurrences"
    assert payload["output_type"] == "api_json"
    assert payload["item_id"] == 1
    assert payload["preview"]["metadata"]["profile_name"] == "dwc_occurrences"
    assert payload["preview"]["records"] == [
        {"occurrenceID": 1, "locality": "Aoupinié"}
    ]
    assert not (
        gui_duckdb_context
        / "exports"
        / "profiles"
        / "dwc_occurrences"
        / "dwc_occurrences.json"
    ).exists()


def test_execute_standard_profile_publication_output_blocks_invalid_profile(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "dwc_occurrences",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                        "mappings": {},
                        "outputs": [{"type": "dwc_archive"}],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.post(
        "/api/standard-profiles/dwc_occurrences/outputs/dwc_archive"
    )

    assert response.status_code == 400, response.text
    assert "Publication outputs require" in response.json()["detail"]


def test_execute_standard_profile_rejects_unsafe_output_dir(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "schema": {"fields": [{"name": "id", "type": "integer"}]}
                        }
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "dwc_occurrences",
                        "standard": "darwin_core_occurrence",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                        "mappings": {"occurrenceID": {"source": "id"}},
                        "outputs": [
                            {
                                "type": "api_json",
                                "params": {"output_dir": "../outside"},
                            }
                        ],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.post(
        "/api/standard-profiles/dwc_occurrences/outputs/api_json"
    )

    assert response.status_code == 400, response.text
    assert "output_dir must not contain parent" in response.json()["detail"]
    assert not (gui_duckdb_context.parent / "outside").exists()
