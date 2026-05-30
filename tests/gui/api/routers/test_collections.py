"""Tests for collection catalog API routes."""

from __future__ import annotations

import asyncio
from copy import deepcopy
import threading

import duckdb
import yaml

from niamoto.gui.api.routers import collections
from tests.gui.api.routers.concurrency_helpers import TrackingRLock


def _first_transform_backed_proposal(proposal_payload):
    proposals = [
        *proposal_payload["recommended"],
        *proposal_payload["warnings"],
        *proposal_payload["review_only"],
    ]
    return next(
        proposal
        for proposal in proposals
        if proposal.get("recipe", {}).get("transformer")
    )


def _add_occurrence_geometry(work_dir):
    db_path = work_dir / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("ALTER TABLE dataset_occurrences ADD COLUMN geo_pt VARCHAR")
        conn.execute(
            """
            UPDATE dataset_occurrences
            SET geo_pt = CASE id
                WHEN 1 THEN 'POINT(166.45 -22.27)'
                WHEN 2 THEN 'POINT(166.45 -22.27)'
                ELSE 'POINT(166.47 -22.29)'
            END
            """
        )
    finally:
        conn.close()


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


def test_list_collections_maps_invalid_metadata_to_client_error(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    import_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    import_config["metadata"] = {"collections": {"taxons": {"review_status": "done"}}}
    import_path.write_text(
        yaml.safe_dump(import_config, sort_keys=False),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/collections")

    assert response.status_code == 400
    assert "Invalid review_status for collection 'taxons'" in response.json()["detail"]


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


def test_update_collection_rejects_empty_payload_without_saving(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    original = import_path.read_text(encoding="utf-8")

    response = gui_duckdb_client.patch("/api/collections/taxons", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Collection update must include at least one field"
    )
    assert import_path.read_text(encoding="utf-8") == original


def test_update_collection_rejects_unknown_fields_without_saving(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    original = import_path.read_text(encoding="utf-8")

    response = gui_duckdb_client.patch(
        "/api/collections/taxons", json={"reviewStatus": "accepted"}
    )

    assert response.status_code == 422
    assert import_path.read_text(encoding="utf-8") == original


def test_update_collection_missing_name_returns_unquoted_detail(
    gui_duckdb_client,
):
    response = gui_duckdb_client.patch(
        "/api/collections/missing",
        json={"review_status": "accepted"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Collection 'missing' not found"


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


def test_create_manual_collection_rejects_unknown_fields_without_writing(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    before = import_path.read_text(encoding="utf-8")

    response = gui_duckdb_client.post(
        "/api/collections",
        json={
            "name": "occurrence_records",
            "source_type": "dataset",
            "source_name": "occurrences",
            "grain": "occurrence",
            "roles": ["api"],
            "review_status": "accepted",
        },
    )

    assert response.status_code == 422
    assert import_path.read_text(encoding="utf-8") == before


def test_concurrent_collection_creates_preserve_both_metadata_entries(monkeypatch):
    current_import_config = {
        "entities": {"datasets": {"occurrences": {}}, "references": {"taxons": {}}},
        "metadata": {"collections": {}},
    }
    config_lock = threading.Lock()
    collection_write_lock = TrackingRLock()
    first_save_entered = threading.Event()
    release_first_save = threading.Event()
    errors: list[BaseException] = []

    class FakeCatalogService:
        def __init__(self):
            with config_lock:
                self.import_config = deepcopy(current_import_config)

        def create_collection(self, **payload):
            collections_config = self.import_config.setdefault(
                "metadata", {}
            ).setdefault("collections", {})
            collections_config[payload["name"]] = {
                "source": {
                    "type": payload["source_type"],
                    "name": payload["source_name"],
                },
                "grain": payload.get("grain"),
                "roles": payload.get("roles", []),
            }
            return {"name": payload["name"]}

    def fake_save_service_config(service):
        nonlocal current_import_config
        collections_config = service.import_config["metadata"]["collections"]
        if "first_collection" in collections_config and len(collections_config) == 1:
            first_save_entered.set()
            release_first_save.wait(timeout=2)
        with config_lock:
            current_import_config = deepcopy(service.import_config)

    monkeypatch.setattr(collections, "_catalog_service", FakeCatalogService)
    monkeypatch.setattr(collections, "_save_service_config", fake_save_service_config)
    monkeypatch.setattr(collections, "COLLECTION_CONFIG_LOCK", collection_write_lock)

    def make_request(name: str) -> collections.CollectionCreateRequest:
        return collections.CollectionCreateRequest(
            name=name,
            source_type="dataset",
            source_name="occurrences",
            grain="occurrence",
            roles=["api"],
        )

    def create(name: str):
        try:
            asyncio.run(collections.create_collection(make_request(name)))
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(target=create, args=("first_collection",))
    second = threading.Thread(target=create, args=("second_collection",))

    first.start()
    assert first_save_entered.wait(timeout=2)
    second.start()
    assert collection_write_lock.contended_acquire.wait(timeout=2)
    release_first_save.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    saved_collections = current_import_config["metadata"]["collections"]
    assert set(saved_collections) == {"first_collection", "second_collection"}


def test_collection_data_options_waits_for_collection_config_lock(monkeypatch):
    collection_write_lock = TrackingRLock()
    save_entered = threading.Event()
    release_save = threading.Event()
    read_entered = threading.Event()
    errors: list[BaseException] = []

    class FakeCatalogService:
        def __init__(self):
            self.import_config = {"metadata": {"collections": {}}}

        def create_collection(self, **payload):
            self.import_config["metadata"]["collections"][payload["name"]] = payload
            return {"name": payload["name"]}

    class FakeDataOptionsService:
        def get_options(self, collection_name: str):
            read_entered.set()
            return {"collection": collection_name}

    def fake_save_service_config(service):
        save_entered.set()
        release_save.wait(timeout=2)

    monkeypatch.setattr(collections, "_catalog_service", FakeCatalogService)
    monkeypatch.setattr(collections, "_data_options_service", FakeDataOptionsService)
    monkeypatch.setattr(collections, "_save_service_config", fake_save_service_config)
    monkeypatch.setattr(collections, "COLLECTION_CONFIG_LOCK", collection_write_lock)

    def create():
        try:
            asyncio.run(
                collections.create_collection(
                    collections.CollectionCreateRequest(
                        name="occurrence_records",
                        source_type="dataset",
                        source_name="occurrences",
                        grain="occurrence",
                        roles=["api"],
                    )
                )
            )
        except BaseException as exc:
            errors.append(exc)

    def read_options():
        try:
            asyncio.run(collections.get_collection_data_options("occurrence_records"))
        except BaseException as exc:
            errors.append(exc)

    writer = threading.Thread(target=create)
    reader = threading.Thread(target=read_options)

    writer.start()
    assert save_entered.wait(timeout=2)
    reader.start()

    assert collection_write_lock.contended_acquire.wait(timeout=2)
    assert not read_entered.is_set()

    release_save.set()
    writer.join(timeout=2)
    reader.join(timeout=2)

    assert not writer.is_alive()
    assert not reader.is_alive()
    assert read_entered.is_set()
    assert errors == []


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
    assert response.json()["detail"] == "Collection 'missing' not found"


def test_get_collection_widget_proposals_returns_grouped_blocks_candidates(
    gui_duckdb_client, gui_duckdb_context
):
    response = gui_duckdb_client.get("/api/collections/taxons/widget-proposals")

    assert response.status_code == 200, response.text
    payload = response.json()
    proposals = [
        *payload["recommended"],
        *payload["warnings"],
        *payload["review_only"],
    ]
    assert payload["collection"] == "taxons"
    assert proposals
    assert any(
        proposal["primary_fit"]["widget"] == "bar_plot"
        for proposal in proposals
        if proposal.get("primary_fit")
    )


def test_get_collection_widget_proposals_includes_foundational_page_widgets(
    gui_duckdb_client, gui_duckdb_context
):
    response = gui_duckdb_client.get("/api/collections/taxons/widget-proposals")

    assert response.status_code == 200, response.text
    payload = response.json()
    proposals = [
        *payload["recommended"],
        *payload["warnings"],
        *payload["review_only"],
        *payload["already_configured"],
    ]
    widgets = {
        proposal["primary_fit"]["widget"]
        for proposal in proposals
        if proposal.get("primary_fit")
    }
    assert "hierarchical_nav_widget" in widgets
    assert "info_grid" in widgets


def test_get_collection_widget_proposals_lists_page_structure_widgets_first(
    gui_duckdb_client, gui_duckdb_context
):
    _add_occurrence_geometry(gui_duckdb_context)

    response = gui_duckdb_client.get("/api/collections/taxons/widget-proposals")

    assert response.status_code == 200, response.text
    payload = response.json()
    first_widgets = [
        proposal["primary_fit"]["widget"]
        for proposal in payload["recommended"][:3]
        if proposal.get("primary_fit")
    ]
    assert first_widgets == [
        "hierarchical_nav_widget",
        "info_grid",
        "interactive_map",
    ]


def test_preview_collection_widget_proposals_does_not_write_configs(
    gui_duckdb_client, gui_duckdb_context
):
    proposal_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-proposals"
    ).json()
    proposal = [
        *proposal_payload["recommended"],
        *proposal_payload["warnings"],
        *proposal_payload["review_only"],
    ][0]
    transform_path = gui_duckdb_context / "config" / "transform.yml"
    export_path = gui_duckdb_context / "config" / "export.yml"
    before_transform = (
        transform_path.read_text(encoding="utf-8") if transform_path.exists() else None
    )
    before_export = (
        export_path.read_text(encoding="utf-8") if export_path.exists() else None
    )

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-proposals/preview",
        json={"selections": [{"proposal_id": proposal["id"]}]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["writes_files"] is False
    assert payload["preview_token"]
    assert payload["changes"][0]["action"] in {"add", "invalid"}
    after_transform = (
        transform_path.read_text(encoding="utf-8") if transform_path.exists() else None
    )
    after_export = (
        export_path.read_text(encoding="utf-8") if export_path.exists() else None
    )
    assert after_transform == before_transform
    assert after_export == before_export


def test_preview_collection_widget_proposals_invalid_without_source_relation(
    gui_duckdb_client, gui_duckdb_context
):
    import_path = gui_duckdb_context / "config" / "import.yml"
    import_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    taxons_config = import_config["entities"]["references"]["taxons"]
    taxons_config.pop("relation", None)
    taxons_config["connector"] = {"source": "occurrences"}
    import_path.write_text(
        yaml.safe_dump(import_config, sort_keys=False),
        encoding="utf-8",
    )

    proposal_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-proposals"
    ).json()
    proposal = _first_transform_backed_proposal(proposal_payload)

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-proposals/preview",
        json={"selections": [{"proposal_id": proposal["id"]}]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["changes"][0]["action"] == "invalid"
    assert (
        "No transform source relation could be derived"
        in payload["invalid"][0]["reason"]
    )


def test_apply_collection_widget_proposals_writes_transform_and_export_configs(
    gui_duckdb_client, gui_duckdb_context
):
    proposal_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-proposals"
    ).json()
    proposal = _first_transform_backed_proposal(proposal_payload)

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-proposals/apply",
        json={"selections": [{"proposal_id": proposal["id"]}]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["applied"][0]["widget_id"] == proposal["id"]
    assert payload["written_files"] == ["config/transform.yml", "config/export.yml"]

    transform_config = yaml.safe_load(
        (gui_duckdb_context / "config" / "transform.yml").read_text(encoding="utf-8")
    )
    export_config = yaml.safe_load(
        (gui_duckdb_context / "config" / "export.yml").read_text(encoding="utf-8")
    )
    taxon_group = next(
        group for group in transform_config if group["group_by"] == "taxons"
    )
    source = taxon_group["sources"][0]
    assert source["relation"]["key"] == "taxon_id"
    assert source["relation"]["ref_key"] == "id"
    assert proposal["id"] in taxon_group["widgets_data"]
    export_group = export_config["exports"][0]["groups"][0]
    assert export_group["widgets"][0]["data_source"] == proposal["id"]


def test_apply_foundational_widget_proposals_writes_navigation_and_general_info(
    gui_duckdb_client, gui_duckdb_context
):
    proposal_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-proposals"
    ).json()
    proposals = [
        *proposal_payload["recommended"],
        *proposal_payload["warnings"],
        *proposal_payload["review_only"],
    ]
    navigation = next(
        proposal
        for proposal in proposals
        if proposal["primary_fit"]["widget"] == "hierarchical_nav_widget"
    )
    general_info = next(
        proposal
        for proposal in proposals
        if proposal["primary_fit"]["widget"] == "info_grid"
    )

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-proposals/apply",
        json={
            "selections": [
                {"proposal_id": navigation["id"]},
                {"proposal_id": general_info["id"]},
            ]
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True

    transform_config = yaml.safe_load(
        (gui_duckdb_context / "config" / "transform.yml").read_text(encoding="utf-8")
    )
    export_config = yaml.safe_load(
        (gui_duckdb_context / "config" / "export.yml").read_text(encoding="utf-8")
    )
    taxon_group = next(
        group for group in transform_config if group["group_by"] == "taxons"
    )
    assert general_info["id"] in taxon_group["widgets_data"]
    assert navigation["id"] not in taxon_group["widgets_data"]

    export_group = export_config["exports"][0]["groups"][0]
    widgets_by_source = {
        widget.get("data_source"): widget for widget in export_group["widgets"]
    }
    assert widgets_by_source[navigation["id"]]["plugin"] == "hierarchical_nav_widget"
    assert widgets_by_source[general_info["id"]]["plugin"] == "info_grid"
