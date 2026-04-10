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


def test_get_reference_enrichment_config_preserves_structured_profile_fields(
    monkeypatch,
):
    """Structured provider config should survive normalization."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": [
                {
                    "id": "gbif",
                    "label": "GBIF",
                    "plugin": "api_taxonomy_enricher",
                    "enabled": True,
                    "config": {
                        "api_url": "https://api.gbif.org/v2/species/match",
                        "profile": "gbif_rich",
                        "use_name_verifier": True,
                        "taxonomy_source": "col_xr",
                        "include_taxonomy": True,
                        "include_occurrences": True,
                        "include_media": False,
                        "media_limit": 2,
                    },
                }
            ]
        },
    )

    config = enrichment_service.get_reference_enrichment_config("taxons")

    assert len(config.sources) == 1
    source = config.sources[0]
    assert source.id == "gbif"
    assert source.profile == "gbif_rich"
    assert source.use_name_verifier is True
    assert source.taxonomy_source == "col_xr"
    assert source.include_taxonomy is True
    assert source.include_occurrences is True
    assert source.include_media is False
    assert source.media_limit == 2


def test_get_reference_enrichment_config_upgrades_legacy_gbif_source(monkeypatch):
    """Legacy GBIF match config should be normalized to the rich GBIF profile."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": [
                {
                    "id": "source-2",
                    "label": "GBIF",
                    "plugin": "api_taxonomy_enricher",
                    "enabled": True,
                    "config": {
                        "api_url": "https://api.gbif.org/v1/species/match",
                        "query_param_name": "q",
                        "query_params": {"kingdom": "Plantae"},
                        "response_mapping": {"gbif_key": "usageKey"},
                    },
                }
            ]
        },
    )

    config = enrichment_service.get_reference_enrichment_config("taxons")

    assert len(config.sources) == 1
    source = config.sources[0]
    assert source.api_url == "https://api.gbif.org/v2/species/match"
    assert source.profile == "gbif_rich"
    assert source.taxonomy_source == "col_xr"
    assert source.query_param_name == "scientificName"
    assert source.response_mapping == {}


def test_get_reference_enrichment_config_upgrades_legacy_tropicos_source(monkeypatch):
    """Legacy Tropicos config should be normalized to the rich Tropicos profile."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": [
                {
                    "id": "source-3",
                    "plugin": "tropicos_enricher",
                    "enabled": True,
                    "config": {
                        "api_url": "http://services.tropicos.org/Name/Search",
                        "query_param_name": "q",
                        "response_mapping": {"tropicos_id": "NameId"},
                    },
                }
            ]
        },
    )

    config = enrichment_service.get_reference_enrichment_config("taxons")

    assert len(config.sources) == 1
    source = config.sources[0]
    assert source.label == "Tropicos"
    assert source.plugin == "api_taxonomy_enricher"
    assert source.api_url == "https://services.tropicos.org/Name/Search"
    assert source.profile == "tropicos_rich"
    assert source.query_param_name == "name"
    assert source.auth_method == "api_key"
    assert source.auth_params["name"] == "apikey"
    assert source.query_params["format"] == "json"
    assert source.query_params["type"] == "exact"
    assert source.response_mapping == {}


def test_get_reference_enrichment_config_preserves_col_rich_fields(monkeypatch):
    """Structured Catalogue of Life config should survive normalization."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": [
                {
                    "id": "col",
                    "label": "Catalogue of Life",
                    "plugin": "api_taxonomy_enricher",
                    "enabled": True,
                    "config": {
                        "api_url": "https://api.checklistbank.org/dataset/314774/nameusage/search",
                        "profile": "col_rich",
                        "use_name_verifier": True,
                        "dataset_key": 314774,
                        "include_vernaculars": True,
                        "include_distributions": False,
                        "include_references": True,
                        "reference_limit": 7,
                    },
                }
            ]
        },
    )

    config = enrichment_service.get_reference_enrichment_config("taxons")

    assert len(config.sources) == 1
    source = config.sources[0]
    assert source.id == "col"
    assert source.profile == "col_rich"
    assert source.use_name_verifier is True
    assert source.dataset_key == 314774
    assert source.include_vernaculars is True
    assert source.include_distributions is False
    assert source.include_references is True
    assert source.reference_limit == 7


def test_get_reference_enrichment_config_preserves_bhl_fields(monkeypatch):
    """Structured BHL config should survive normalization."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": [
                {
                    "id": "bhl",
                    "label": "BHL",
                    "plugin": "api_taxonomy_enricher",
                    "enabled": True,
                    "config": {
                        "api_url": "https://www.biodiversitylibrary.org/api3",
                        "profile": "bhl_references",
                        "auth_method": "api_key",
                        "auth_params": {
                            "location": "query",
                            "name": "apikey",
                            "key": "secret",
                        },
                        "include_publication_details": True,
                        "include_page_preview": False,
                        "title_limit": 4,
                        "page_limit": 2,
                    },
                }
            ]
        },
    )

    config = enrichment_service.get_reference_enrichment_config("taxons")

    assert len(config.sources) == 1
    source = config.sources[0]
    assert source.id == "bhl"
    assert source.profile == "bhl_references"
    assert source.auth_method == "api_key"
    assert source.auth_params["name"] == "apikey"
    assert source.include_publication_details is True
    assert source.include_page_preview is False
    assert source.title_limit == 4
    assert source.page_limit == 2


def test_get_reference_enrichment_config_preserves_inaturalist_fields(monkeypatch):
    """Structured iNaturalist config should survive normalization."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": [
                {
                    "id": "inat",
                    "label": "iNaturalist",
                    "plugin": "api_taxonomy_enricher",
                    "enabled": True,
                    "config": {
                        "api_url": "https://api.inaturalist.org/v1/taxa",
                        "profile": "inaturalist_rich",
                        "include_occurrences": True,
                        "include_media": True,
                        "include_places": False,
                        "media_limit": 4,
                        "observation_limit": 7,
                    },
                }
            ]
        },
    )

    config = enrichment_service.get_reference_enrichment_config("taxons")

    assert len(config.sources) == 1
    source = config.sources[0]
    assert source.id == "inat"
    assert source.profile == "inaturalist_rich"
    assert source.include_occurrences is True
    assert source.include_media is True
    assert source.include_places is False
    assert source.media_limit == 4
    assert source.observation_limit == 7


def test_ensure_startable_sources_rejects_missing_api_key(monkeypatch):
    """Preview and runs should fail early when a source requires an API key but has none."""

    monkeypatch.setattr(
        enrichment_service,
        "get_reference_enrichment_config",
        lambda _reference_name: enrichment_service.EnrichmentReferenceConfigResponse(
            reference_name="taxons",
            enabled=True,
            sources=[
                enrichment_service.EnrichmentSourceConfig(
                    id="bhl",
                    label="BHL",
                    enabled=True,
                    api_url="https://www.biodiversitylibrary.org/api3",
                    auth_method="api_key",
                    auth_params={"location": "query", "name": "apikey", "key": ""},
                )
            ],
        ),
    )

    with pytest.raises(ValueError, match="Missing API key for source 'BHL'"):
        enrichment_service._ensure_startable_sources("taxons")


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


def test_preview_reference_enrichment_uses_source_override(monkeypatch):
    """Preview should use the unsaved source draft when provided."""

    class FakeEnricher:
        def load_data(self, payload, config):
            assert payload == {"full_name": "Alphitonia neocaledonica"}
            assert config["params"]["profile"] == "bhl_references"
            assert config["params"]["auth_params"]["key"] == "secret"
            return {
                "api_enrichment": {"references_count": 3},
                "api_response_raw": {"Result": [{"Title": "Example title"}]},
            }

    monkeypatch.setattr(
        enrichment_service,
        "get_reference_enrichment_config",
        lambda _reference_name: pytest.fail(
            "saved config should not be consulted when a preview override is provided"
        ),
    )
    monkeypatch.setattr(
        enrichment_service,
        "_build_enricher",
        lambda _plugin: FakeEnricher(),
    )

    response = asyncio.run(
        enrichment_service.preview_reference_enrichment(
            "taxons",
            "Alphitonia neocaledonica",
            source_id="source-4",
            source_override={
                "id": "source-4",
                "label": "BHL",
                "plugin": "api_taxonomy_enricher",
                "enabled": False,
                "config": {
                    "api_url": "https://www.biodiversitylibrary.org/api3",
                    "profile": "bhl_references",
                    "auth_method": "api_key",
                    "auth_params": {
                        "location": "query",
                        "name": "apikey",
                        "key": "secret",
                    },
                    "query_param_name": "name",
                    "query_params": {"op": "NameSearch", "format": "json"},
                    "response_mapping": {},
                },
            },
        )
    )

    assert response.success is True
    assert response.results[0].data == {"references_count": 3}
    assert response.results[0].config_used == {
        "api_url": "https://www.biodiversitylibrary.org/api3",
        "query_field": "full_name",
        "profile": "bhl_references",
        "use_name_verifier": False,
        "dataset_key": 314774,
        "include_publication_details": True,
        "include_page_preview": True,
        "title_limit": 5,
        "page_limit": 5,
    }


def test_preview_reference_enrichment_includes_raw_api_payload(monkeypatch):
    """Preview responses should expose the raw API payload for mapping help."""

    source = enrichment_service.EnrichmentSourceConfig(
        id="endemia",
        label="Endemia",
        enabled=True,
        api_url="https://api.endemia.nc/v1/taxons",
    )

    class FakeEnricher:
        def load_data(self, payload, config):
            assert payload == {"full_name": "Araucaria columnaris"}
            assert config["params"]["cache_results"] is False
            return {
                "api_enrichment": {"id_endemia": 513},
                "api_response_raw": {
                    "id": 513,
                    "full_name": "Araucaria columnaris",
                    "images": [{"url": "https://cdn.example.org/thumb.jpg"}],
                },
            }

    monkeypatch.setattr(
        enrichment_service,
        "_ensure_startable_sources",
        lambda reference_name, source_id=None: [source],
    )
    monkeypatch.setattr(
        enrichment_service,
        "_build_enricher",
        lambda _plugin: FakeEnricher(),
    )

    response = asyncio.run(
        enrichment_service.preview_reference_enrichment(
            "taxons", "Araucaria columnaris", source_id="endemia"
        )
    )

    assert response.success is True
    assert len(response.results) == 1
    assert response.results[0].data == {"id_endemia": 513}
    assert response.results[0].raw_data == {
        "id": 513,
        "full_name": "Araucaria columnaris",
        "images": [{"url": "https://cdn.example.org/thumb.jpg"}],
    }


def test_preview_reference_enrichment_falls_back_when_raw_payload_missing(monkeypatch):
    """Preview should still expose something inspectable when raw payload is absent."""

    source = enrichment_service.EnrichmentSourceConfig(
        id="gbif",
        label="GBIF",
        enabled=True,
        api_url="https://api.gbif.org/v1/species/match",
    )

    class FakeEnricher:
        def load_data(self, payload, config):
            return {
                "api_enrichment": {"gbif_key": 6},
                "api_response_processed": {"usageKey": 6, "status": "ACCEPTED"},
            }

    monkeypatch.setattr(
        enrichment_service,
        "_ensure_startable_sources",
        lambda reference_name, source_id=None: [source],
    )
    monkeypatch.setattr(
        enrichment_service,
        "_build_enricher",
        lambda _plugin: FakeEnricher(),
    )

    response = asyncio.run(
        enrichment_service.preview_reference_enrichment(
            "taxons", "Alphitonia neocaledonica", source_id="gbif"
        )
    )

    assert response.success is True
    assert response.results[0].raw_data == {"usageKey": 6, "status": "ACCEPTED"}
