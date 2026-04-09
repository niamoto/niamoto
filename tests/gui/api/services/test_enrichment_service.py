"""Tests for the multi-source enrichment service."""

from __future__ import annotations

import asyncio

import pytest

from niamoto.gui.api.services import enrichment_service


@pytest.fixture(autouse=True)
def reset_enrichment_runtime():
    """Reset in-memory enrichment runtime state between tests."""

    enrichment_service._current_job = None
    enrichment_service._job_results = []
    enrichment_service._job_cancel_flag = False
    enrichment_service._job_pause_flag = False
    enrichment_service._job_task = None
    yield
    enrichment_service._current_job = None
    enrichment_service._job_results = []
    enrichment_service._job_cancel_flag = False
    enrichment_service._job_pause_flag = False
    enrichment_service._job_task = None


def test_get_reference_enrichment_config_normalizes_legacy_dict(monkeypatch):
    """Legacy single-dict config should be exposed as one normalized source."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": {
                "plugin": "api_taxonomy_enricher",
                "enabled": True,
                "config": {"api_url": "https://api.example.com/v1/taxons"},
            }
        },
    )

    config = enrichment_service.get_reference_enrichment_config("taxons")

    assert config.reference_name == "taxons"
    assert config.enabled is True
    assert len(config.sources) == 1
    assert config.sources[0].id == "api-example-com"
    assert config.sources[0].label == "Api Example Com"
    assert config.sources[0].api_url == "https://api.example.com/v1/taxons"


def test_merge_source_enrichment_data_keeps_existing_sources():
    """Adding one source must not overwrite previously stored source payloads."""

    source = enrichment_service.EnrichmentSourceConfig(
        id="gbif",
        label="GBIF",
        enabled=True,
        api_url="https://api.gbif.org/v1/species/match",
    )

    merged = enrichment_service._merge_source_enrichment_data(
        {
            "notes": {"reviewed": True},
            "api_enrichment": {
                "sources": {
                    "endemia": {
                        "label": "Endemia",
                        "data": {"api_id": 12},
                        "enriched_at": "2026-04-09T09:00:00",
                        "status": "completed",
                    }
                }
            },
        },
        source,
        {"usage_key": 987654},
    )

    assert merged["notes"] == {"reviewed": True}
    assert merged["api_enrichment"]["sources"]["endemia"]["data"]["api_id"] == 12
    assert merged["api_enrichment"]["sources"]["gbif"]["label"] == "GBIF"
    assert merged["api_enrichment"]["sources"]["gbif"]["data"] == {"usage_key": 987654}
    assert merged["api_enrichment"]["sources"]["gbif"]["status"] == "completed"


def test_get_results_falls_back_to_persisted_source_data(monkeypatch):
    """Results endpoint should expose persisted DB payloads when no job log exists."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_rows",
        lambda _reference_name: [
            {
                "id": 1,
                "full_name": "Araucaria columnaris",
                "extra_data": {
                    "api_enrichment": {
                        "sources": {
                            "endemia": {
                                "label": "Endemia",
                                "data": {"api_id": 42},
                                "enriched_at": "2026-04-09T10:00:00",
                                "status": "completed",
                            }
                        }
                    }
                },
            }
        ],
    )
    monkeypatch.setattr(
        enrichment_service,
        "get_reference_enrichment_config",
        lambda reference_name: enrichment_service.EnrichmentReferenceConfigResponse(
            reference_name=reference_name,
            enabled=True,
            sources=[
                enrichment_service.EnrichmentSourceConfig(
                    id="endemia",
                    label="Endemia",
                    enabled=True,
                    api_url="https://api.endemia.nc/v1/taxons",
                )
            ],
        ),
    )

    results = enrichment_service.get_results(reference_name="taxons")

    assert results.total == 1
    assert results.results[0].reference_name == "taxons"
    assert results.results[0].source_id == "endemia"
    assert results.results[0].source_label == "Endemia"
    assert results.results[0].entity_name == "Araucaria columnaris"
    assert results.results[0].data == {"api_id": 42}
    assert results.results[0].success is True


def test_preview_default_enrichment_forwards_source_id(monkeypatch):
    """Legacy preview entrypoint should preserve requested source scope."""

    called = {}

    async def fake_preview(
        reference_name: str, query: str, source_id: str | None = None
    ):
        called["reference_name"] = reference_name
        called["query"] = query
        called["source_id"] = source_id
        return enrichment_service.PreviewResponse(
            success=True,
            entity_name=query,
            results=[],
        )

    monkeypatch.setattr(
        enrichment_service,
        "_resolve_default_reference_name",
        lambda: "taxons",
    )
    monkeypatch.setattr(
        enrichment_service,
        "preview_reference_enrichment",
        fake_preview,
    )

    response = asyncio.run(
        enrichment_service.preview_default_enrichment(
            "Araucaria columnaris", source_id="gbif"
        )
    )

    assert response.success is True
    assert called == {
        "reference_name": "taxons",
        "query": "Araucaria columnaris",
        "source_id": "gbif",
    }
