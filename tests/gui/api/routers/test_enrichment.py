"""Router tests for multi-source enrichment endpoints."""

from __future__ import annotations

import asyncio

import yaml

from niamoto.gui.api.routers import enrichment as enrichment_router
from niamoto.gui.api.services.enrichment_service import PreviewResponse


def _job_payload(
    *,
    reference_name: str = "taxons",
    source_id: str | None = None,
    strategy: str = "resume",
):
    return {
        "id": "job-1",
        "reference_name": reference_name,
        "mode": "single" if source_id else "all",
        "strategy": strategy,
        "status": "running",
        "total": 0,
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "already_completed": 0,
        "pending_total": 0,
        "pending_processed": 0,
        "started_at": "2026-04-22T14:10:00",
        "updated_at": "2026-04-22T14:10:00",
        "source_ids": [source_id] if source_id else [],
        "source_id": source_id,
        "source_label": "Endemia" if source_id else None,
    }


def test_get_reference_enrichment_config_returns_source_list(
    gui_duckdb_project, gui_duckdb_client
):
    """Reference config endpoint should return normalized multi-source payloads."""

    import_yml = gui_duckdb_project / "config" / "import.yml"
    import_yml.write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "references": {
                        "taxons": {
                            "kind": "hierarchical",
                            "enrichment": [
                                {
                                    "id": "endemia",
                                    "label": "Endemia",
                                    "plugin": "api_taxonomy_enricher",
                                    "enabled": True,
                                    "config": {
                                        "api_url": "https://api.endemia.nc/v1/taxons"
                                    },
                                },
                                {
                                    "label": "GBIF",
                                    "plugin": "api_taxonomy_enricher",
                                    "enabled": False,
                                    "config": {
                                        "api_url": "https://api.gbif.org/v1/species/match"
                                    },
                                },
                            ],
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/enrichment/config/taxons")

    assert response.status_code == 200
    payload = response.json()
    assert payload["reference_name"] == "taxons"
    assert payload["enabled"] is True
    assert [source["id"] for source in payload["sources"]] == ["endemia", "gbif"]
    assert [source["label"] for source in payload["sources"]] == ["Endemia", "GBIF"]


def test_get_reference_enrichment_config_translates_missing_reference(
    monkeypatch, gui_duckdb_client
):
    """Unknown reference config errors should become a client-facing 404."""

    def fake_get_reference_enrichment_config(reference_name: str):
        raise ValueError(
            f"No enrichment configuration found for reference '{reference_name}'"
        )

    monkeypatch.setattr(
        enrichment_router,
        "get_reference_enrichment_config",
        fake_get_reference_enrichment_config,
    )

    response = gui_duckdb_client.get("/api/enrichment/config/unknown_ref")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No enrichment configuration found for reference 'unknown_ref'"
    )


def test_get_legacy_enrichment_config_translates_missing_default(
    monkeypatch, gui_duckdb_client
):
    """Legacy config route should map missing default config to 404."""

    def fake_get_default_enrichment_config():
        raise ValueError("No enrichment configuration found for default reference")

    monkeypatch.setattr(
        enrichment_router,
        "get_default_enrichment_config",
        fake_get_default_enrichment_config,
    )

    response = gui_duckdb_client.get("/api/enrichment/config")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No enrichment configuration found for default reference"
    )


def test_preview_legacy_route_forwards_source_id(monkeypatch, gui_duckdb_client):
    """Legacy preview endpoint must keep the optional source scope."""

    captured = {}

    async def fake_preview_default(taxon_name: str, source_id: str | None = None):
        captured["taxon_name"] = taxon_name
        captured["source_id"] = source_id
        return PreviewResponse(success=True, entity_name=taxon_name, results=[])

    monkeypatch.setattr(
        enrichment_router,
        "preview_default_enrichment",
        fake_preview_default,
    )

    response = gui_duckdb_client.post(
        "/api/enrichment/preview",
        json={"taxon_name": "Araucaria columnaris", "source_id": "gbif"},
    )

    assert response.status_code == 200
    assert captured == {
        "taxon_name": "Araucaria columnaris",
        "source_id": "gbif",
    }


def test_preview_legacy_route_translates_service_validation_errors(
    monkeypatch, gui_duckdb_client
):
    """Legacy preview validation errors should use the enrichment HTTP contract."""

    async def fake_preview_default(*args, **kwargs):
        raise ValueError("No enrichment source 'gbif' found for default reference")

    monkeypatch.setattr(
        enrichment_router,
        "preview_default_enrichment",
        fake_preview_default,
    )

    response = gui_duckdb_client.post(
        "/api/enrichment/preview",
        json={"taxon_name": "Araucaria", "source_id": "gbif"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No enrichment source 'gbif' found for default reference"
    )


def test_preview_reference_route_forwards_source_override(
    monkeypatch, gui_duckdb_client
):
    """Reference preview route should forward unsaved source overrides."""

    captured = {}

    async def fake_preview_reference(
        reference_name: str,
        query: str,
        source_id: str | None = None,
        source_override: dict | None = None,
        entity_id: int | str | None = None,
    ):
        captured["reference_name"] = reference_name
        captured["query"] = query
        captured["source_id"] = source_id
        captured["source_override"] = source_override
        captured["entity_id"] = entity_id
        return PreviewResponse(success=True, entity_name=query, results=[])

    monkeypatch.setattr(
        enrichment_router,
        "preview_reference_enrichment",
        fake_preview_reference,
    )

    response = gui_duckdb_client.post(
        "/api/enrichment/preview/taxons",
        json={
            "query": "Alphitonia neocaledonica",
            "source_id": "source-4",
            "entity_id": 42,
            "source_config": {
                "id": "source-4",
                "label": "BHL",
                "plugin": "api_taxonomy_enricher",
                "enabled": False,
                "config": {
                    "profile": "bhl_references",
                    "api_url": "https://www.biodiversitylibrary.org/api3",
                },
            },
        },
    )

    assert response.status_code == 200
    assert captured == {
        "reference_name": "taxons",
        "query": "Alphitonia neocaledonica",
        "source_id": "source-4",
        "source_override": {
            "id": "source-4",
            "label": "BHL",
            "plugin": "api_taxonomy_enricher",
            "enabled": False,
            "config": {
                "profile": "bhl_references",
                "api_url": "https://www.biodiversitylibrary.org/api3",
            },
        },
        "entity_id": 42,
    }


def test_preview_reference_route_translates_service_validation_errors(
    monkeypatch, gui_duckdb_client
):
    """Reference preview validation errors should use the enrichment HTTP contract."""

    async def fake_preview_reference(*args, **kwargs):
        raise ValueError("No enrichment source 'gbif' found for reference 'taxons'")

    monkeypatch.setattr(
        enrichment_router,
        "preview_reference_enrichment",
        fake_preview_reference,
    )

    response = gui_duckdb_client.post(
        "/api/enrichment/preview/taxons",
        json={"query": "Araucaria", "source_id": "gbif"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No enrichment source 'gbif' found for reference 'taxons'"
    )


def test_restart_reference_route_forwards_selected_source(
    monkeypatch, gui_duckdb_client
):
    """Restart route should forward the reference and source identifiers."""

    captured = {}

    def fake_restart_reference_enrichment(reference_name: str, source_id: str):
        captured["reference_name"] = reference_name
        captured["source_id"] = source_id
        return _job_payload(
            reference_name=reference_name, source_id=source_id, strategy="reset"
        )

    monkeypatch.setattr(
        enrichment_router,
        "restart_reference_enrichment",
        fake_restart_reference_enrichment,
    )

    response = gui_duckdb_client.post("/api/enrichment/restart/taxons/endemia")

    assert response.status_code == 200
    assert captured == {"reference_name": "taxons", "source_id": "endemia"}
    assert response.json()["strategy"] == "reset"


def test_start_reference_route_forwards_selected_source(monkeypatch, gui_duckdb_client):
    captured = {}

    def fake_start_reference_enrichment(
        reference_name: str, source_id: str | None = None
    ):
        captured["reference_name"] = reference_name
        captured["source_id"] = source_id
        return _job_payload(reference_name=reference_name, source_id=source_id)

    monkeypatch.setattr(
        enrichment_router,
        "start_reference_enrichment",
        fake_start_reference_enrichment,
    )

    response = gui_duckdb_client.post("/api/enrichment/start/taxons/endemia")

    assert response.status_code == 200
    assert captured == {"reference_name": "taxons", "source_id": "endemia"}
    assert response.json()["source_id"] == "endemia"


def test_start_legacy_route_calls_default_service(monkeypatch, gui_duckdb_client):
    calls = []
    monkeypatch.setattr(
        enrichment_router,
        "start_default_enrichment",
        lambda: calls.append(True) or _job_payload(reference_name="taxons"),
    )

    response = gui_duckdb_client.post("/api/enrichment/start")

    assert response.status_code == 200
    assert response.json()["reference_name"] == "taxons"
    assert calls == [True]


def test_start_legacy_route_maps_value_errors(monkeypatch, gui_duckdb_client):
    def fake_start_default():
        raise ValueError("Enrichment job already active")

    monkeypatch.setattr(
        enrichment_router,
        "start_default_enrichment",
        fake_start_default,
    )

    response = gui_duckdb_client.post("/api/enrichment/start")

    assert response.status_code == 409
    assert response.json()["detail"] == "Enrichment job already active"


def test_start_legacy_route_maps_missing_config(monkeypatch, gui_duckdb_client):
    def fake_start_default():
        raise ValueError("No enrichment configuration found for default reference")

    monkeypatch.setattr(
        enrichment_router,
        "start_default_enrichment",
        fake_start_default,
    )

    response = gui_duckdb_client.post("/api/enrichment/start")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No enrichment configuration found for default reference"
    )


def test_start_reference_route_forwards_reference_name(monkeypatch, gui_duckdb_client):
    captured = {}

    def fake_start_reference(reference_name: str, source_id: str | None = None):
        captured["reference_name"] = reference_name
        captured["source_id"] = source_id
        return _job_payload(reference_name=reference_name)

    monkeypatch.setattr(
        enrichment_router,
        "start_reference_enrichment",
        fake_start_reference,
    )

    response = gui_duckdb_client.post("/api/enrichment/start/taxons")

    assert response.status_code == 200
    assert captured == {"reference_name": "taxons", "source_id": None}
    assert response.json()["mode"] == "all"


def test_start_reference_route_maps_already_active_error(
    monkeypatch, gui_duckdb_client
):
    def fake_start_reference(reference_name: str, source_id: str | None = None):
        raise ValueError("Enrichment job already active")

    monkeypatch.setattr(
        enrichment_router,
        "start_reference_enrichment",
        fake_start_reference,
    )

    response = gui_duckdb_client.post("/api/enrichment/start/taxons")

    assert response.status_code == 409
    assert response.json()["detail"] == "Enrichment job already active"


def test_pause_default_route_calls_default_service(monkeypatch, gui_duckdb_client):
    calls = []
    monkeypatch.setattr(
        enrichment_router,
        "pause_default_enrichment",
        lambda: calls.append(True) or {"status": "paused"},
    )

    response = gui_duckdb_client.post("/api/enrichment/pause")

    assert response.status_code == 200
    assert response.json() == {"status": "paused"}
    assert calls == [True]


def test_pause_reference_route_forwards_selected_source(monkeypatch, gui_duckdb_client):
    captured = {}

    def fake_pause_reference(reference_name: str, source_id: str | None = None):
        captured["reference_name"] = reference_name
        captured["source_id"] = source_id
        return {"status": "paused"}

    monkeypatch.setattr(
        enrichment_router, "pause_reference_enrichment", fake_pause_reference
    )

    response = gui_duckdb_client.post("/api/enrichment/pause/taxons/endemia")

    assert response.status_code == 200
    assert response.json() == {"status": "paused"}
    assert captured == {"reference_name": "taxons", "source_id": "endemia"}


def test_pause_reference_route_maps_value_errors(monkeypatch, gui_duckdb_client):
    def fake_pause_reference(reference_name: str, source_id: str | None = None):
        raise ValueError("No matching enrichment job found")

    monkeypatch.setattr(
        enrichment_router, "pause_reference_enrichment", fake_pause_reference
    )

    response = gui_duckdb_client.post("/api/enrichment/pause/taxons")

    assert response.status_code == 400
    assert response.json()["detail"] == "No matching enrichment job found"


def test_resume_reference_route_forwards_reference_name(monkeypatch, gui_duckdb_client):
    captured = {}

    def fake_resume_reference(reference_name: str, source_id: str | None = None):
        captured["reference_name"] = reference_name
        captured["source_id"] = source_id
        return {"status": "running"}

    monkeypatch.setattr(
        enrichment_router, "resume_reference_enrichment", fake_resume_reference
    )

    response = gui_duckdb_client.post("/api/enrichment/resume/taxons")

    assert response.status_code == 200
    assert response.json() == {"status": "running"}
    assert captured == {"reference_name": "taxons", "source_id": None}


def test_resume_reference_route_forwards_selected_source(
    monkeypatch, gui_duckdb_client
):
    captured = {}

    def fake_resume_reference(reference_name: str, source_id: str | None = None):
        captured["reference_name"] = reference_name
        captured["source_id"] = source_id
        return {"status": "running"}

    monkeypatch.setattr(
        enrichment_router, "resume_reference_enrichment", fake_resume_reference
    )

    response = gui_duckdb_client.post("/api/enrichment/resume/taxons/endemia")

    assert response.status_code == 200
    assert response.json() == {"status": "running"}
    assert captured == {"reference_name": "taxons", "source_id": "endemia"}


def test_resume_reference_route_maps_missing_config(monkeypatch, gui_duckdb_client):
    def fake_resume_reference(reference_name: str, source_id: str | None = None):
        raise ValueError("No enrichment configuration found for reference 'taxons'")

    monkeypatch.setattr(
        enrichment_router, "resume_reference_enrichment", fake_resume_reference
    )

    response = gui_duckdb_client.post("/api/enrichment/resume/taxons")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No enrichment configuration found for reference 'taxons'"
    )


def test_cancel_reference_route_forwards_selected_source(
    monkeypatch, gui_duckdb_client
):
    captured = {}

    def fake_cancel_reference(reference_name: str, source_id: str | None = None):
        captured["reference_name"] = reference_name
        captured["source_id"] = source_id
        return {"status": "cancelled"}

    monkeypatch.setattr(
        enrichment_router, "cancel_reference_enrichment", fake_cancel_reference
    )

    response = gui_duckdb_client.post("/api/enrichment/cancel/taxons/endemia")

    assert response.status_code == 200
    assert response.json() == {"status": "cancelled"}
    assert captured == {"reference_name": "taxons", "source_id": "endemia"}


def test_cancel_reference_route_forwards_reference_name(monkeypatch, gui_duckdb_client):
    captured = {}

    def fake_cancel_reference(reference_name: str, source_id: str | None = None):
        captured["reference_name"] = reference_name
        captured["source_id"] = source_id
        return {"status": "cancelled"}

    monkeypatch.setattr(
        enrichment_router, "cancel_reference_enrichment", fake_cancel_reference
    )

    response = gui_duckdb_client.post("/api/enrichment/cancel/taxons")

    assert response.status_code == 200
    assert response.json() == {"status": "cancelled"}
    assert captured == {"reference_name": "taxons", "source_id": None}


def test_cancel_reference_route_maps_service_errors(monkeypatch, gui_duckdb_client):
    def fake_cancel_reference(reference_name: str, source_id: str | None = None):
        raise ValueError("No matching enrichment job found")

    monkeypatch.setattr(
        enrichment_router, "cancel_reference_enrichment", fake_cancel_reference
    )

    response = gui_duckdb_client.post("/api/enrichment/cancel/taxons")

    assert response.status_code == 400
    assert response.json()["detail"] == "No matching enrichment job found"


def test_get_enrichment_stats_uses_worker_thread(monkeypatch):
    captured = {}

    def fake_get_stats():
        captured["service_called"] = True
        return {
            "reference_name": None,
            "entity_total": 10,
            "source_total": 2,
            "total": 20,
            "enriched": 7,
            "pending": 13,
            "sources": [],
        }

    async def fake_to_thread(func, *args, **kwargs):
        captured["thread_func"] = func
        captured["thread_args"] = args
        captured["thread_kwargs"] = kwargs
        return func(*args, **kwargs)

    monkeypatch.setattr(
        enrichment_router, "get_default_enrichment_stats", fake_get_stats
    )
    monkeypatch.setattr(enrichment_router.asyncio, "to_thread", fake_to_thread)

    response = asyncio.run(enrichment_router.get_enrichment_stats())

    assert response["total"] == 20
    assert captured == {
        "thread_func": fake_get_stats,
        "thread_args": (),
        "thread_kwargs": {},
        "service_called": True,
    }


def test_get_enrichment_stats_maps_missing_default_config(
    monkeypatch, gui_duckdb_client
):
    def fake_get_stats():
        raise ValueError("No enrichment configuration found for default reference")

    monkeypatch.setattr(
        enrichment_router, "get_default_enrichment_stats", fake_get_stats
    )

    response = gui_duckdb_client.get("/api/enrichment/stats")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No enrichment configuration found for default reference"
    )


def test_get_reference_enrichment_stats_maps_missing_reference(
    monkeypatch, gui_duckdb_client
):
    def fake_get_stats(reference_name):
        raise ValueError(
            f"No enrichment configuration found for reference '{reference_name}'"
        )

    monkeypatch.setattr(
        enrichment_router, "get_reference_enrichment_stats", fake_get_stats
    )

    response = gui_duckdb_client.get("/api/enrichment/stats/unknown_ref")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No enrichment configuration found for reference 'unknown_ref'"
    )


def test_get_results_for_reference_uses_worker_thread(monkeypatch):
    """Heavy result reconstruction should be dispatched off the API loop."""

    captured = {}

    def fake_get_results(
        *,
        reference_name: str | None = None,
        page: int = 0,
        limit: int = 50,
        source_id: str | None = None,
    ):
        captured["service_kwargs"] = {
            "reference_name": reference_name,
            "page": page,
            "limit": limit,
            "source_id": source_id,
        }
        return {"results": [], "total": 0, "page": page, "limit": limit}

    async def fake_to_thread(func, *args, **kwargs):
        captured["thread_func"] = func
        captured["thread_args"] = args
        captured["thread_kwargs"] = kwargs
        return func(*args, **kwargs)

    monkeypatch.setattr(enrichment_router, "get_results", fake_get_results)
    monkeypatch.setattr(enrichment_router.asyncio, "to_thread", fake_to_thread)

    response = asyncio.run(
        enrichment_router.get_results_for_reference(
            "taxons", page=2, limit=25, source_id="endemia"
        )
    )

    assert response == {"results": [], "total": 0, "page": 2, "limit": 25}
    assert captured["thread_func"] is fake_get_results
    assert captured["thread_args"] == ()
    assert captured["thread_kwargs"] == {
        "reference_name": "taxons",
        "page": 2,
        "limit": 25,
        "source_id": "endemia",
    }
    assert captured["service_kwargs"] == {
        "reference_name": "taxons",
        "page": 2,
        "limit": 25,
        "source_id": "endemia",
    }


def test_get_results_for_reference_maps_service_validation_errors(
    monkeypatch, gui_duckdb_client
):
    def fake_get_results(
        *,
        reference_name: str | None = None,
        page: int = 0,
        limit: int = 50,
        source_id: str | None = None,
    ):
        raise ValueError(
            f"No enrichment configuration found for reference '{reference_name}'"
        )

    monkeypatch.setattr(enrichment_router, "get_results", fake_get_results)

    response = gui_duckdb_client.get("/api/enrichment/results/unknown_ref")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No enrichment configuration found for reference 'unknown_ref'"
    )


def test_get_all_results_rejects_invalid_pagination(gui_duckdb_client):
    for query in ("page=-1", "limit=0", "limit=-1", "limit=501"):
        response = gui_duckdb_client.get(f"/api/enrichment/results?{query}")

        assert response.status_code == 422, query


def test_get_all_results_forwards_valid_pagination(monkeypatch, gui_duckdb_client):
    captured = {}

    def fake_get_results(
        *,
        reference_name: str | None = None,
        page: int = 0,
        limit: int = 50,
        source_id: str | None = None,
    ):
        captured["kwargs"] = {
            "reference_name": reference_name,
            "page": page,
            "limit": limit,
            "source_id": source_id,
        }
        return {"results": [], "total": 0, "page": page, "limit": limit}

    monkeypatch.setattr(enrichment_router, "get_results", fake_get_results)

    response = gui_duckdb_client.get(
        "/api/enrichment/results?page=2&limit=25&source_id=endemia"
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"results": [], "total": 0, "page": 2, "limit": 25}
    assert captured["kwargs"] == {
        "reference_name": None,
        "page": 2,
        "limit": 25,
        "source_id": "endemia",
    }


def test_list_entities_for_reference_uses_worker_thread(monkeypatch):
    """Entity listings should stay responsive even when another read is slow."""

    captured = {}

    def fake_get_entities(
        reference_name: str, limit: int = 100, offset: int = 0, search: str = ""
    ):
        captured["service_args"] = {
            "reference_name": reference_name,
            "limit": limit,
            "offset": offset,
            "search": search,
        }
        return {"entities": [], "total": 0}

    async def fake_to_thread(func, *args, **kwargs):
        captured["thread_func"] = func
        captured["thread_args"] = args
        captured["thread_kwargs"] = kwargs
        return func(*args, **kwargs)

    monkeypatch.setattr(
        enrichment_router, "get_entities_for_reference", fake_get_entities
    )
    monkeypatch.setattr(enrichment_router.asyncio, "to_thread", fake_to_thread)

    response = asyncio.run(
        enrichment_router.list_entities_for_reference(
            "taxons", limit=20, offset=40, search="Araucaria"
        )
    )

    assert response == {"entities": [], "total": 0}
    assert captured["thread_func"] is fake_get_entities
    assert captured["thread_args"] == ("taxons",)
    assert captured["thread_kwargs"] == {
        "limit": 20,
        "offset": 40,
        "search": "Araucaria",
    }
    assert captured["service_args"] == {
        "reference_name": "taxons",
        "limit": 20,
        "offset": 40,
        "search": "Araucaria",
    }
