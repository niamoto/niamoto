"""Router tests for multi-source enrichment endpoints."""

from __future__ import annotations

import asyncio

import yaml

from niamoto.gui.api.routers import enrichment as enrichment_router
from niamoto.gui.api.services.enrichment_service import PreviewResponse


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


def test_restart_reference_route_forwards_selected_source(
    monkeypatch, gui_duckdb_client
):
    """Restart route should forward the reference and source identifiers."""

    captured = {}

    def fake_restart_reference_enrichment(reference_name: str, source_id: str):
        captured["reference_name"] = reference_name
        captured["source_id"] = source_id
        return {
            "id": "job-1",
            "reference_name": reference_name,
            "mode": "single",
            "strategy": "reset",
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
            "source_ids": [source_id],
            "source_id": source_id,
            "source_label": "Endemia",
        }

    monkeypatch.setattr(
        enrichment_router,
        "restart_reference_enrichment",
        fake_restart_reference_enrichment,
    )

    response = gui_duckdb_client.post("/api/enrichment/restart/taxons/endemia")

    assert response.status_code == 200
    assert captured == {"reference_name": "taxons", "source_id": "endemia"}
    assert response.json()["strategy"] == "reset"


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
