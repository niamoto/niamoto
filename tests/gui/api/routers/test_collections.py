"""Tests for collection catalog API routes."""

from __future__ import annotations

import asyncio
from copy import deepcopy
import threading

import duckdb
import yaml

from niamoto.core.collections.models import CollectionCatalogEntry
from niamoto.gui.api.routers import collections
from niamoto.gui.api.services.collection_widget_proposals import (
    CollectionWidgetProposalService,
)
from tests.gui.api.routers.concurrency_helpers import TrackingRLock


def _first_transform_backed_candidate(candidate_payload):
    candidates = [
        *candidate_payload["recommended"],
        *candidate_payload["available"],
        *candidate_payload["needs_review"],
    ]
    return next(
        candidate
        for candidate in candidates
        if candidate.get("recipe_summary", {}).get("transformer", {}).get("plugin")
    )


def _first_external_source_candidate(candidate_payload):
    candidates = [
        *candidate_payload["recommended"],
        *candidate_payload["available"],
        *candidate_payload["needs_review"],
    ]
    return next(
        candidate
        for candidate in candidates
        if (
            candidate.get("recipe_summary", {}).get("transformer", {}).get("plugin")
            and candidate.get("recipe_summary", {}).get("transformer", {}).get("plugin")
            != "field_aggregator"
        )
    )


def _preview_widget_candidate(client, candidate_id: str):
    response = client.post(
        "/api/collections/taxons/widget-candidates/preview",
        json={"selections": [{"candidate_id": candidate_id}]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _apply_widget_candidate(client, candidate_id: str, preview_token: str):
    return client.post(
        "/api/collections/taxons/widget-candidates/apply",
        json={
            "selections": [{"candidate_id": candidate_id}],
            "preview_token": preview_token,
        },
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


def test_list_collections_waits_for_collection_config_lock(monkeypatch):
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

        def list_collections(self):
            read_entered.set()
            return {"collections": [], "sources": [], "total": 0}

    def fake_save_service_config(service):
        save_entered.set()
        release_save.wait(timeout=2)

    monkeypatch.setattr(collections, "_catalog_service", FakeCatalogService)
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

    def read_catalog():
        try:
            asyncio.run(collections.list_collections())
        except BaseException as exc:
            errors.append(exc)

    writer = threading.Thread(target=create)
    reader = threading.Thread(target=read_catalog)

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


def test_widget_candidate_read_waits_for_collection_config_lock(monkeypatch):
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

    class FakeWidgetCandidateService:
        def get_candidates(self, collection_name: str):
            read_entered.set()
            return {
                "collection": collection_name,
                "recommended": [],
                "available": [],
                "needs_review": [],
                "missing_chart": [],
                "skipped": [],
                "configured": [],
                "partial": False,
                "messages": [],
            }

    def fake_save_service_config(service):
        save_entered.set()
        release_save.wait(timeout=2)

    monkeypatch.setattr(collections, "_catalog_service", FakeCatalogService)
    monkeypatch.setattr(
        collections, "_widget_candidate_service", FakeWidgetCandidateService
    )
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

    def read_candidates():
        try:
            asyncio.run(
                collections.get_collection_widget_candidates("occurrence_records")
            )
        except BaseException as exc:
            errors.append(exc)

    writer = threading.Thread(target=create)
    reader = threading.Thread(target=read_candidates)

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


def test_get_collection_widget_candidates_returns_grouped_blocks_candidates(
    gui_duckdb_client, gui_duckdb_context
):
    response = gui_duckdb_client.get("/api/collections/taxons/widget-candidates")

    assert response.status_code == 200, response.text
    payload = response.json()
    candidates = [
        *payload["recommended"],
        *payload["available"],
        *payload["needs_review"],
    ]
    assert payload["collection"] == "taxons"
    assert candidates
    assert any(candidate["widget_plugin"] == "bar_plot" for candidate in candidates)


def test_get_collection_widget_candidates_includes_foundational_page_widgets(
    gui_duckdb_client, gui_duckdb_context
):
    response = gui_duckdb_client.get("/api/collections/taxons/widget-candidates")

    assert response.status_code == 200, response.text
    payload = response.json()
    candidates = [
        *payload["recommended"],
        *payload["available"],
        *payload["needs_review"],
        *payload["configured"],
    ]
    widgets = {
        candidate["widget_plugin"]
        for candidate in candidates
        if candidate.get("widget_plugin")
    }
    assert "hierarchical_nav_widget" in widgets
    assert "info_grid" in widgets


def test_get_collection_widget_candidates_lists_page_structure_widgets_first(
    gui_duckdb_client, gui_duckdb_context
):
    _add_occurrence_geometry(gui_duckdb_context)

    response = gui_duckdb_client.get("/api/collections/taxons/widget-candidates")

    assert response.status_code == 200, response.text
    payload = response.json()
    first_widgets = [
        candidate["widget_plugin"]
        for candidate in payload["recommended"][:3]
        if candidate.get("widget_plugin")
    ]
    assert first_widgets == [
        "hierarchical_nav_widget",
        "info_grid",
        "interactive_map",
    ]


def test_get_collection_widget_candidates_returns_default_selected_recommendations(
    gui_duckdb_client, gui_duckdb_context
):
    response = gui_duckdb_client.get("/api/collections/taxons/widget-candidates")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["collection"] == "taxons"
    assert payload["recommended"]
    assert all(
        candidate["default_selected"] is True
        for candidate in payload["recommended"]
        if candidate["applyability"] == "applicable"
    )
    assert all(
        candidate["status"] == "configured" for candidate in payload["configured"]
    )


def test_preview_collection_widget_candidates_does_not_write_configs(
    gui_duckdb_client, gui_duckdb_context
):
    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidate = next(
        item
        for item in [
            *candidate_payload["recommended"],
            *candidate_payload["available"],
            *candidate_payload["needs_review"],
        ]
        if item["applyability"] == "applicable"
    )
    transform_path = gui_duckdb_context / "config" / "transform.yml"
    export_path = gui_duckdb_context / "config" / "export.yml"
    before_transform = (
        transform_path.read_text(encoding="utf-8") if transform_path.exists() else None
    )
    before_export = (
        export_path.read_text(encoding="utf-8") if export_path.exists() else None
    )

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-candidates/preview",
        json={"selections": [{"candidate_id": candidate["id"]}]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["writes_files"] is False
    assert payload["preview_token"]
    assert payload["changes"][0]["candidate_id"] == candidate["id"]
    after_transform = (
        transform_path.read_text(encoding="utf-8") if transform_path.exists() else None
    )
    after_export = (
        export_path.read_text(encoding="utf-8") if export_path.exists() else None
    )
    assert after_transform == before_transform
    assert after_export == before_export


def test_apply_collection_widget_candidates_writes_transform_and_export_configs(
    gui_duckdb_client, gui_duckdb_context
):
    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidate = next(
        item
        for item in [
            *candidate_payload["recommended"],
            *candidate_payload["available"],
            *candidate_payload["needs_review"],
        ]
        if item["applyability"] == "applicable"
        and item.get("recipe_summary", {}).get("transformer")
    )
    preview = _preview_widget_candidate(gui_duckdb_client, candidate["id"])

    response = _apply_widget_candidate(
        gui_duckdb_client,
        candidate["id"],
        preview["preview_token"],
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["applied"][0]["candidate_id"] == candidate["id"]
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
    assert candidate["id"] in taxon_group["widgets_data"]
    export_group = export_config["exports"][0]["groups"][0]
    assert export_group["widgets"][0]["data_source"] == candidate["id"]


def test_apply_collection_widget_candidates_reuses_params_groups_export_container(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "enabled": True,
                        "exporter": "html_page_exporter",
                        "params": {
                            "template_dir": "templates/",
                            "output_dir": "exports/web",
                            "groups": [
                                {
                                    "group_by": "taxons",
                                    "output_pattern": "taxons/{id}.html",
                                    "index_output_pattern": "taxons/index.html",
                                    "widgets": [],
                                }
                            ],
                        },
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidate = _first_transform_backed_candidate(candidate_payload)
    preview = _preview_widget_candidate(gui_duckdb_client, candidate["id"])

    response = _apply_widget_candidate(
        gui_duckdb_client,
        candidate["id"],
        preview["preview_token"],
    )

    assert response.status_code == 200, response.text
    saved = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    web_export = saved["exports"][0]
    assert "groups" not in web_export
    export_group = web_export["params"]["groups"][0]
    assert export_group["group_by"] == "taxons"
    assert export_group["widgets"][0]["data_source"] == candidate["id"]


def test_apply_collection_widget_candidates_requires_preview_token(
    gui_duckdb_client, gui_duckdb_context
):
    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidate = next(
        item
        for item in [
            *candidate_payload["recommended"],
            *candidate_payload["available"],
            *candidate_payload["needs_review"],
        ]
        if item["applyability"] == "applicable"
    )

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-candidates/apply",
        json={"selections": [{"candidate_id": candidate["id"]}]},
    )

    assert response.status_code == 422


def test_collection_widget_candidates_mark_legacy_equivalent_transform_configured(
    gui_duckdb_client, gui_duckdb_context
):
    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidate = _first_transform_backed_candidate(candidate_payload)
    preview = _preview_widget_candidate(gui_duckdb_client, candidate["id"])
    change = preview["changes"][0]
    legacy_widget_id = "legacy_same_widget"

    legacy_transform_widget = deepcopy(change["transform_widget"])
    legacy_transform_widget.pop("export_override", None)
    transform_path = gui_duckdb_context / "config" / "transform.yml"
    transform_config = (
        yaml.safe_load(transform_path.read_text(encoding="utf-8"))
        if transform_path.exists()
        else [{"group_by": "taxons", "sources": [], "widgets_data": {}}]
    )
    transform_group = next(
        group for group in transform_config if group["group_by"] == "taxons"
    )
    transform_group.setdefault("widgets_data", {})[legacy_widget_id] = (
        legacy_transform_widget
    )
    transform_path.write_text(
        yaml.safe_dump(transform_config, sort_keys=False),
        encoding="utf-8",
    )

    legacy_export_widget = deepcopy(change["export_widget"])
    legacy_export_widget["data_source"] = legacy_widget_id
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_config = (
        yaml.safe_load(export_path.read_text(encoding="utf-8"))
        if export_path.exists()
        else {
            "exports": [
                {
                    "name": "web_pages",
                    "enabled": True,
                    "exporter": "html_page_exporter",
                    "params": {
                        "template_dir": "templates/",
                        "output_dir": "exports/web",
                    },
                    "groups": [
                        {
                            "group_by": "taxons",
                            "output_pattern": "taxons/{id}.html",
                            "index_output_pattern": "taxons/index.html",
                            "widgets": [],
                        }
                    ],
                }
            ]
        }
    )
    export_group = export_config["exports"][0]["groups"][0]
    export_group.setdefault("widgets", []).append(legacy_export_widget)
    export_path.write_text(
        yaml.safe_dump(export_config, sort_keys=False),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/collections/taxons/widget-candidates")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert any(item["id"] == candidate["id"] for item in payload["configured"])
    assert all(item["id"] != candidate["id"] for item in payload["recommended"])


def test_collection_widget_candidates_do_not_hide_partial_legacy_transform(
    gui_duckdb_client, gui_duckdb_context
):
    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidate = _first_transform_backed_candidate(candidate_payload)
    preview = _preview_widget_candidate(gui_duckdb_client, candidate["id"])
    change = preview["changes"][0]

    legacy_transform_widget = deepcopy(change["transform_widget"])
    legacy_transform_widget.pop("export_override", None)
    transform_path = gui_duckdb_context / "config" / "transform.yml"
    transform_config = (
        yaml.safe_load(transform_path.read_text(encoding="utf-8"))
        if transform_path.exists()
        else [{"group_by": "taxons", "sources": [], "widgets_data": {}}]
    )
    transform_group = next(
        group for group in transform_config if group["group_by"] == "taxons"
    )
    transform_group.setdefault("widgets_data", {})["legacy_transform_only"] = (
        legacy_transform_widget
    )
    transform_path.write_text(
        yaml.safe_dump(transform_config, sort_keys=False),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/collections/taxons/widget-candidates")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert all(item["id"] != candidate["id"] for item in payload["configured"])
    assert any(
        item["id"] == candidate["id"]
        for item in [
            *payload["recommended"],
            *payload["available"],
            *payload["needs_review"],
        ]
    )


def test_widget_candidate_export_group_uses_safe_collection_path_segment(tmp_path):
    service = CollectionWidgetProposalService(
        work_dir=tmp_path,
        db_path=None,
        import_config={"entities": {}},
        transform_config=[],
        export_config={},
    )
    groups: list[dict] = []

    group = service._find_or_create_export_group(  # noqa: SLF001 - regression for generated paths
        groups,
        "../Manual Collection",
    )

    assert group["group_by"] == "../Manual Collection"
    assert group["output_pattern"] == "manual_collection/{id}.html"
    assert group["index_output_pattern"] == "manual_collection/index.html"


def test_widget_candidate_identifier_and_name_heuristics_are_project_neutral(
    tmp_path,
):
    service = CollectionWidgetProposalService(
        work_dir=tmp_path,
        db_path=None,
        import_config={"entities": {}},
        transform_config=[],
        export_config={},
    )

    assert (
        service._pick_identifier_column(  # noqa: SLF001 - regression for generic heuristics
            ["code", "taxons_id"],
        )
        == "code"
    )
    assert (
        service._pick_name_column(  # noqa: SLF001 - regression for generic heuristics
            ["code", "taxaname"],
            id_field="id",
        )
        == "code"
    )


def test_widget_candidate_dataset_collection_groups_by_backing_dataset(tmp_path):
    service = CollectionWidgetProposalService(
        work_dir=tmp_path,
        db_path=None,
        import_config={
            "entities": {
                "datasets": {
                    "occurrences": {
                        "schema": {"id_field": "occurrence_id"},
                    }
                }
            }
        },
        transform_config=[],
        export_config={},
    )
    collection = CollectionCatalogEntry(
        name="trees",
        label="Trees",
        source_type="dataset",
        source_name="occurrences",
        grain="tree",
        roles=["site"],
    )

    source_config = service._source_config_for_collection(  # noqa: SLF001 - regression for generated transform grouping
        collection,
        "occurrences",
        existing_sources=[],
    )

    assert source_config is not None
    assert source_config["data"] == "occurrences"
    assert source_config["grouping"] == "occurrences"
    assert source_config["relation"] == {
        "plugin": "direct_reference",
        "key": "occurrence_id",
        "ref_key": "occurrence_id",
    }


def test_widget_candidate_derived_source_defaults_to_collection_reference_key(
    tmp_path,
):
    service = CollectionWidgetProposalService(
        work_dir=tmp_path,
        db_path=None,
        import_config={
            "entities": {
                "references": {
                    "plots": {
                        "kind": "hierarchical",
                        "connector": {
                            "type": "derived",
                            "source": "plots_source",
                            "extraction": {"id_column": "id_liste_plots"},
                        },
                        "schema": {"id_field": "id", "name_field": "full_name"},
                        "relation": {
                            "dataset": "occurrences",
                            "foreign_key": "plot_fk",
                        },
                    }
                }
            }
        },
        transform_config=[],
        export_config={},
    )
    collection = CollectionCatalogEntry(
        name="plots",
        label="Plots",
        source_type="reference",
        source_name="plots",
        grain="plot",
        roles=["site"],
    )

    source_config = service._source_config_for_collection(  # noqa: SLF001 - regression for derived reference source relations
        collection,
        "plots_source",
        existing_sources=[],
    )

    assert source_config is not None
    assert source_config["relation"]["ref_key"] == "plots_id"


def test_collection_widget_candidates_include_auxiliary_class_object_sources(
    tmp_path,
):
    imports_dir = tmp_path / "imports"
    imports_dir.mkdir()
    (imports_dir / "raw_plot_stats.csv").write_text(
        "\n".join(
            [
                "id,plot_id,class_object,class_name,class_value",
                "1,p1,nbe_stem,,42",
                "2,p1,richness,,12",
            ]
        ),
        encoding="utf-8",
    )
    source_relation = {
        "plugin": "stats_loader",
        "key": "id",
        "ref_field": "plots_id",
        "match_field": "plot_id",
    }
    service = CollectionWidgetProposalService(
        work_dir=tmp_path,
        db_path=None,
        import_config={
            "entities": {
                "datasets": {
                    "occurrences": {
                        "schema": {"id_field": "occurrence_id"},
                    }
                },
                "references": {
                    "plots": {
                        "relation": {
                            "dataset": "occurrences",
                            "foreign_key": "plot_id",
                            "reference_key": "plots_id",
                        },
                        "schema": {"id_field": "plots_id", "name_field": "full_name"},
                    }
                },
            },
            "auxiliary_sources": [
                {
                    "name": "plot_stats",
                    "data": "imports/raw_plot_stats.csv",
                    "grouping": "plots",
                    "relation": source_relation,
                }
            ],
        },
        transform_config=[
            {
                "group_by": "plots",
                "sources": [
                    {
                        "name": "occurrences",
                        "data": "occurrences",
                        "grouping": "plots",
                        "relation": {
                            "plugin": "stats_loader",
                            "key": "plots_id",
                            "ref_field": "plot_id",
                        },
                    },
                    {
                        "name": "plot_stats",
                        "data": "imports/raw_plot_stats.csv",
                        "grouping": "plots",
                        "relation": source_relation,
                    },
                ],
                "widgets_data": {},
            }
        ],
        export_config={},
    )

    groups = service.get_proposals("plots")

    proposal = next(
        (
            item
            for item in groups.recommended
            if item.candidate.source_name == "plot_stats"
        ),
        None,
    )
    assert proposal is not None
    assert proposal.candidate.origin == "class_object"
    assert proposal.candidate.transformer_plugin == "class_object_field_aggregator"
    assert set(proposal.candidate.field_names) == {"nbe_stem", "richness"}
    assert proposal.recipe["transformer"]["params"]["source"] == "plot_stats"
    assert proposal.recipe["widget"]["plugin"] == "info_grid"


def test_collection_widget_candidates_include_derived_connector_source(tmp_path):
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE dataset_plots_source (
                id_liste_plots INTEGER,
                plot_name VARCHAR,
                locality_name VARCHAR,
                country VARCHAR,
                method VARCHAR,
                nbe_stem INTEGER,
                prop_det_genus DOUBLE
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO dataset_plots_source
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "Plot A", "North", "A", "transect", 10, 0.8),
                (2, "Plot B", "North", "A", "transect", 15, 0.9),
                (3, "Plot C", "South", "B", "quadrat", 21, 0.7),
                (4, "Plot D", "South", "B", "quadrat", 34, 0.6),
                (5, "Plot E", "East", "C", "transect", 55, 0.5),
            ],
        )
    finally:
        conn.close()

    service = CollectionWidgetProposalService(
        work_dir=tmp_path,
        db_path=db_path,
        import_config={
            "entities": {
                "datasets": {
                    "plots_source": {},
                    "occurrences": {},
                },
                "references": {
                    "plots": {
                        "kind": "hierarchical",
                        "connector": {
                            "type": "derived",
                            "source": "plots_source",
                            "extraction": {"id_column": "id_liste_plots"},
                        },
                        "schema": {"id_field": "id", "name_field": "full_name"},
                        "relation": {
                            "dataset": "occurrences",
                            "foreign_key": "plot_fk",
                            "reference_key": "plots_id",
                        },
                    }
                },
            }
        },
        transform_config=[
            {
                "group_by": "plots",
                "sources": [
                    {
                        "name": "occurrences",
                        "data": "occurrences",
                        "grouping": "plots",
                        "relation": {
                            "plugin": "nested_set",
                            "key": "plot_fk",
                            "ref_key": "plots_id",
                        },
                    }
                ],
                "widgets_data": {},
            }
        ],
        export_config={},
    )

    groups = service.get_proposals("plots")

    connector_proposal = next(
        (
            item
            for item in groups.recommended
            if item.candidate.source_name == "plots_source"
        ),
        None,
    )
    assert connector_proposal is not None
    assert connector_proposal.applyability == "applicable"
    assert connector_proposal.recipe["transformer"]["params"]["source"] == (
        "plots_source"
    )

    collection = service.catalog_service.get_collection("plots")
    source_config = service._source_config_for_collection(  # noqa: SLF001 - regression for derived reference source relations
        collection,
        "plots_source",
        existing_sources=[],
    )
    assert source_config == {
        "name": "plots_source",
        "data": "plots_source",
        "grouping": "plots",
        "relation": {
            "plugin": "nested_set",
            "key": "id_liste_plots",
            "ref_key": "plots_id",
            "fields": {"parent": "parent_id", "left": "lft", "right": "rght"},
        },
    }
    transform_widget, _ = service._config_for_proposal(connector_proposal)  # noqa: SLF001 - regression for apply source merging
    merged_sources = service._merged_sources_for_transform_widgets(  # noqa: SLF001 - regression for apply source merging
        service._existing_sources_for_collection("plots"),
        "plots",
        [transform_widget],
    )
    assert any(source.get("name") == "plots_source" for source in merged_sources)


def test_navigation_proposal_uses_context_hierarchy_fields(tmp_path):
    service = CollectionWidgetProposalService(
        work_dir=tmp_path,
        db_path=None,
        import_config={"entities": {}},
        transform_config=[],
        export_config={},
    )
    collection = CollectionCatalogEntry(
        name="nodes",
        label="Nodes",
        source_type="reference",
        source_name="node_ref",
        grain="node",
        roles=["site"],
    )
    proposal = service._navigation_proposal(  # noqa: SLF001 - regression for private builder
        collection,
        {
            "id_field": "node_key",
            "name_field": "node_name",
            "columns": [
                "node_key",
                "node_name",
                "left_bound",
                "right_bound",
                "parent_key",
                "depth",
            ],
            "has_nested_set": True,
            "left_field": "left_bound",
            "right_field": "right_bound",
            "has_parent": True,
            "parent_field": "parent_key",
            "has_level": True,
            "level_field": "depth",
        },
        set(),
    )

    params = proposal.recipe["widget"]["params"]
    assert params["lft_field"] == "left_bound"
    assert params["rght_field"] == "right_bound"
    assert params["parent_id_field"] == "parent_key"
    assert params["level_field"] == "depth"


def test_preview_collection_widget_candidates_invalid_without_source_relation(
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

    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidate = _first_external_source_candidate(candidate_payload)

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-candidates/preview",
        json={"selections": [{"candidate_id": candidate["id"]}]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["changes"][0]["action"] == "invalid"
    assert (
        "No transform source relation could be derived"
        in payload["invalid"][0]["reason"]
    )


def test_apply_export_only_widget_candidate_without_source_relation(
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

    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidates = [
        *candidate_payload["recommended"],
        *candidate_payload["available"],
        *candidate_payload["needs_review"],
    ]
    navigation = next(
        candidate
        for candidate in candidates
        if candidate["widget_plugin"] == "hierarchical_nav_widget"
    )

    preview_response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-candidates/preview",
        json={"selections": [{"candidate_id": navigation["id"]}]},
    )
    assert preview_response.status_code == 200, preview_response.text
    assert preview_response.json()["changes"][0]["action"] == "add"

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-candidates/apply",
        json={
            "selections": [{"candidate_id": navigation["id"]}],
            "preview_token": preview_response.json()["preview_token"],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    transform_config = yaml.safe_load(
        (gui_duckdb_context / "config" / "transform.yml").read_text(encoding="utf-8")
    )
    assert not any(
        group.get("group_by") == "taxons"
        for group in transform_config
        if isinstance(group, dict)
    )
    export_config = yaml.safe_load(
        (gui_duckdb_context / "config" / "export.yml").read_text(encoding="utf-8")
    )
    export_group = export_config["exports"][0]["groups"][0]
    widgets_by_source = {
        widget.get("data_source"): widget for widget in export_group["widgets"]
    }
    assert widgets_by_source[navigation["id"]]["plugin"] == "hierarchical_nav_widget"


def test_apply_general_info_widget_candidate_without_source_relation(
    gui_duckdb_client, gui_duckdb_context
):
    db_path = gui_duckdb_context / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("ALTER TABLE entity_taxons ADD COLUMN rank_name VARCHAR")
        conn.execute("ALTER TABLE entity_taxons ADD COLUMN category VARCHAR")
        conn.execute(
            """
            UPDATE entity_taxons
            SET rank_name = CASE id WHEN 101 THEN 'family' ELSE 'species' END,
                category = CASE id WHEN 101 THEN 'native' ELSE 'endemic' END
            """
        )
    finally:
        conn.close()

    import_path = gui_duckdb_context / "config" / "import.yml"
    import_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    taxons_config = import_config["entities"]["references"]["taxons"]
    taxons_config.pop("relation", None)
    taxons_config["connector"] = {"source": "occurrences"}
    import_path.write_text(
        yaml.safe_dump(import_config, sort_keys=False),
        encoding="utf-8",
    )

    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidates = [
        *candidate_payload["recommended"],
        *candidate_payload["available"],
        *candidate_payload["needs_review"],
    ]
    general_info = next(
        candidate
        for candidate in candidates
        if candidate["widget_plugin"] == "info_grid"
    )

    preview_response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-candidates/preview",
        json={"selections": [{"candidate_id": general_info["id"]}]},
    )
    assert preview_response.status_code == 200, preview_response.text
    assert preview_response.json()["changes"][0]["action"] == "add"

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-candidates/apply",
        json={
            "selections": [{"candidate_id": general_info["id"]}],
            "preview_token": preview_response.json()["preview_token"],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    transform_config = yaml.safe_load(
        (gui_duckdb_context / "config" / "transform.yml").read_text(encoding="utf-8")
    )
    taxon_group = next(
        group for group in transform_config if group.get("group_by") == "taxons"
    )
    assert taxon_group.get("sources") == []
    transform_widget = taxon_group["widgets_data"][general_info["id"]]
    field_sources = {
        field.get("source")
        for field in transform_widget["params"]["fields"]
        if isinstance(field, dict)
    }
    assert field_sources == {"taxons"}


def test_apply_collection_widget_candidates_derives_transform_source_relation(
    gui_duckdb_client, gui_duckdb_context
):
    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidate = _first_transform_backed_candidate(candidate_payload)
    preview = _preview_widget_candidate(gui_duckdb_client, candidate["id"])

    response = _apply_widget_candidate(
        gui_duckdb_client,
        candidate["id"],
        preview["preview_token"],
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["applied"][0]["candidate_id"] == candidate["id"]
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
    assert candidate["id"] in taxon_group["widgets_data"]
    export_group = export_config["exports"][0]["groups"][0]
    assert export_group["widgets"][0]["data_source"] == candidate["id"]


def test_apply_collection_map_candidate_persists_plotly_map_params(
    gui_duckdb_client, gui_duckdb_context
):
    _add_occurrence_geometry(gui_duckdb_context)
    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidates = [
        *candidate_payload["recommended"],
        *candidate_payload["available"],
        *candidate_payload["needs_review"],
    ]
    candidate = next(
        candidate
        for candidate in candidates
        if candidate.get("widget_plugin") == "interactive_map"
    )

    assert candidate["title"] == "Geo Pt map"
    recipe_summary = candidate["recipe_summary"]
    assert recipe_summary["transformer"]["params"]["format"] == "geojson"
    assert recipe_summary["transformer"]["params"]["group_by_coordinates"] is True
    assert recipe_summary["widget"]["params"]["geojson_field"] == "features"
    assert recipe_summary["widget"]["params"]["map_type"] == "scatter_map"
    preview = _preview_widget_candidate(gui_duckdb_client, candidate["id"])

    response = _apply_widget_candidate(
        gui_duckdb_client,
        candidate["id"],
        preview["preview_token"],
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
    transform_widget = taxon_group["widgets_data"][candidate["id"]]
    assert transform_widget["params"]["format"] == "geojson"
    assert transform_widget["params"]["group_by_coordinates"] is True
    export_group = export_config["exports"][0]["groups"][0]
    map_widget = next(
        widget
        for widget in export_group["widgets"]
        if widget["data_source"] == candidate["id"]
    )
    assert map_widget["plugin"] == "interactive_map"
    assert map_widget["title"] == "Geo Pt map"
    assert map_widget["params"]["geojson_field"] == "features"
    assert map_widget["params"]["map_type"] == "scatter_map"
    assert map_widget["params"]["map_style"] == "carto-positron"
    assert map_widget["params"]["auto_zoom"] is True


def test_apply_foundational_widget_candidates_writes_navigation_and_general_info(
    gui_duckdb_client, gui_duckdb_context
):
    candidate_payload = gui_duckdb_client.get(
        "/api/collections/taxons/widget-candidates"
    ).json()
    candidates = [
        *candidate_payload["recommended"],
        *candidate_payload["available"],
        *candidate_payload["needs_review"],
    ]
    navigation = next(
        candidate
        for candidate in candidates
        if candidate["widget_plugin"] == "hierarchical_nav_widget"
    )
    general_info = next(
        candidate
        for candidate in candidates
        if candidate["widget_plugin"] == "info_grid"
    )
    selections = [
        {"candidate_id": navigation["id"]},
        {"candidate_id": general_info["id"]},
    ]
    preview_response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-candidates/preview",
        json={"selections": selections},
    )
    assert preview_response.status_code == 200, preview_response.text

    response = gui_duckdb_client.post(
        "/api/collections/taxons/widget-candidates/apply",
        json={
            "selections": selections,
            "preview_token": preview_response.json()["preview_token"],
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
