"""Router tests for multi-source enrichment endpoints."""

from __future__ import annotations

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
