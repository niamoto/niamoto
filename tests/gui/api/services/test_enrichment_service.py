"""Tests for the multi-source enrichment service."""

from __future__ import annotations

import asyncio

import pytest
import pandas as pd

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


def test_get_reference_enrichment_config_normalizes_legacy_endemia_auth(monkeypatch):
    """Legacy Endemia config should not require an API key."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": [
                {
                    "id": "endemia",
                    "label": "Endemia NC",
                    "plugin": "api_taxonomy_enricher",
                    "enabled": True,
                    "config": {
                        "api_url": "https://api.endemia.nc/v1/taxons",
                        "auth_method": "api_key",
                        "auth_params": {
                            "location": "query",
                            "name": "apiKey",
                            "key": "",
                        },
                        "query_params": {"section": "flore"},
                        "response_mapping": {"id_endemia": "id"},
                    },
                }
            ]
        },
    )

    config = enrichment_service.get_reference_enrichment_config("taxons")

    assert len(config.sources) == 1
    source = config.sources[0]
    assert source.id == "endemia"
    assert source.auth_method == "none"
    assert source.auth_params == {}


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
        lambda _reference_name, columns=None, require_extra_data=False: [
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


def test_get_results_projects_only_display_columns_and_extra_data(monkeypatch):
    """Persisted result reconstruction should avoid selecting full reference rows."""

    captured: dict[str, object] = {}

    def fake_load_reference_rows(
        reference_name: str,
        columns=None,
        require_extra_data: bool = False,
    ):
        captured["reference_name"] = reference_name
        captured["columns"] = list(columns or [])
        captured["require_extra_data"] = require_extra_data
        return [
            {
                "plot": "Forêt Nord",
                "extra_data": {
                    "api_enrichment": {
                        "sources": {
                            "open-meteo": {
                                "label": "Open-Meteo",
                                "data": {"elevation": 812},
                                "enriched_at": "2026-04-21T18:30:00",
                                "status": "completed",
                            }
                        }
                    }
                },
            }
        ]

    monkeypatch.setattr(
        enrichment_service, "_load_reference_rows", fake_load_reference_rows
    )
    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {"schema": {"name_field": "plot"}},
    )
    monkeypatch.setattr(
        enrichment_service,
        "get_reference_enrichment_config",
        lambda reference_name: enrichment_service.EnrichmentReferenceConfigResponse(
            reference_name=reference_name,
            enabled=True,
            sources=[
                enrichment_service.EnrichmentSourceConfig(
                    id="open-meteo",
                    label="Open-Meteo",
                    enabled=True,
                    api_url="https://api.open-meteo.com/v1/elevation",
                )
            ],
        ),
    )

    results = enrichment_service.get_results(reference_name="plots")

    assert results.total == 1
    assert captured == {
        "reference_name": "plots",
        "columns": ["plot", "full_name", "name", "label", "title", "id", "extra_data"],
        "require_extra_data": True,
    }


def test_get_results_filters_by_source_id(monkeypatch):
    """Results listing should support scoping the history to one source."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_rows",
        lambda _reference_name, columns=None, require_extra_data=False: [
            {
                "full_name": "Araucaria columnaris",
                "extra_data": {
                    "api_enrichment": {
                        "sources": {
                            "endemia": {
                                "label": "Endemia",
                                "data": {"api_id": 42},
                                "enriched_at": "2026-04-09T10:00:00",
                                "status": "completed",
                            },
                            "gbif": {
                                "label": "GBIF",
                                "data": {"usage_key": 99},
                                "enriched_at": "2026-04-09T11:00:00",
                                "status": "completed",
                            },
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
                ),
                enrichment_service.EnrichmentSourceConfig(
                    id="gbif",
                    label="GBIF",
                    enabled=True,
                    api_url="https://api.gbif.org/v2/species/match",
                ),
            ],
        ),
    )

    results = enrichment_service.get_results(reference_name="taxons", source_id="gbif")

    assert results.total == 1
    assert results.results[0].source_id == "gbif"
    assert results.results[0].data == {"usage_key": 99}


def test_get_reference_enrichment_stats_reads_only_extra_data(monkeypatch):
    """Polling stats should not reselect the full reference payload."""

    captured: dict[str, object] = {}

    def fake_load_reference_rows(
        reference_name: str,
        columns=None,
        require_extra_data: bool = False,
    ):
        captured["reference_name"] = reference_name
        captured["columns"] = list(columns or [])
        captured["require_extra_data"] = require_extra_data
        return [
            {"extra_data": None},
            {
                "extra_data": {
                    "api_enrichment": {
                        "sources": {
                            "endemia": {
                                "data": {"api_id": 42},
                                "status": "completed",
                            }
                        }
                    }
                }
            },
        ]

    monkeypatch.setattr(
        enrichment_service, "_load_reference_rows", fake_load_reference_rows
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

    stats = enrichment_service.get_reference_enrichment_stats("taxons")

    assert stats.entity_total == 2
    assert stats.enriched == 1
    assert captured == {
        "reference_name": "taxons",
        "columns": ["extra_data"],
        "require_extra_data": False,
    }


def test_run_enrichment_job_exposes_pending_run_progress(monkeypatch):
    """Runtime progress should distinguish pending attempts from already saved rows."""

    source = enrichment_service.EnrichmentSourceConfig(
        id="endemia",
        label="Endemia",
        enabled=True,
        api_url="https://api.endemia.nc/v1/taxons",
    )
    rows = [
        {
            "id": 1,
            "full_name": "Already enriched",
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
        },
        {
            "id": 2,
            "full_name": "Still pending",
            "extra_data": None,
        },
    ]

    class FakeEnricher:
        def load_data(self, payload, config):
            raise RuntimeError(f"No match for {payload['full_name']}")

    monkeypatch.setattr(
        enrichment_service, "_load_reference_rows", lambda _reference_name: rows
    )
    monkeypatch.setattr(
        enrichment_service, "_build_enricher", lambda _plugin: FakeEnricher()
    )

    now = "2026-04-21T20:00:00"
    enrichment_service._current_job = enrichment_service.EnrichmentJob(
        id="job-1",
        reference_name="taxons",
        mode=enrichment_service.JobMode.ALL,
        status=enrichment_service.JobStatus.RUNNING,
        started_at=now,
        updated_at=now,
        source_ids=[source.id],
    )

    asyncio.run(
        enrichment_service._run_enrichment_job(
            "job-1",
            "taxons",
            [source],
            enrichment_service.JobMode.ALL,
        )
    )

    job = enrichment_service._current_job
    assert job is not None
    assert job.status == enrichment_service.JobStatus.COMPLETED
    assert job.total == 2
    assert job.processed == 2
    assert job.already_completed == 1
    assert job.pending_total == 1
    assert job.pending_processed == 1
    assert job.successful == 1
    assert job.failed == 1


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


def test_get_reference_enrichment_config_upgrades_legacy_openmeteo_source(monkeypatch):
    """Legacy Open-Meteo config should be normalized to the structured elevation profile."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": [
                {
                    "label": "Open-Meteo Elevation",
                    "plugin": "api_elevation_enricher",
                    "enabled": True,
                    "config": {
                        "api_url": "https://api.open-meteo.com/v1/elevation",
                    },
                }
            ]
        },
    )

    config = enrichment_service.get_reference_enrichment_config("plots")

    assert len(config.sources) == 1
    source = config.sources[0]
    assert source.label == "Open-Meteo Elevation"
    assert source.plugin == "api_elevation_enricher"
    assert source.profile == "openmeteo_elevation_v1"
    assert source.query_field == "geometry"
    assert source.query_param_name == "latitude"
    assert source.response_mapping == {}


def test_get_reference_enrichment_config_upgrades_legacy_geonames_source(monkeypatch):
    """Legacy GeoNames config should be normalized to the structured spatial profile."""

    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "enrichment": [
                {
                    "plugin": "api_spatial_enricher",
                    "enabled": True,
                    "config": {
                        "api_url": "http://api.geonames.org/countrySubdivisionJSON",
                        "auth_method": "api_key",
                        "auth_params": {
                            "location": "query",
                            "name": "username",
                            "key": "demo",
                        },
                    },
                }
            ]
        },
    )

    config = enrichment_service.get_reference_enrichment_config("plots")

    assert len(config.sources) == 1
    source = config.sources[0]
    assert source.label == "GeoNames"
    assert source.plugin == "api_spatial_enricher"
    assert source.profile == "geonames_spatial_v1"
    assert source.query_field == "geometry"
    assert source.query_param_name == "lat"
    assert source.response_mapping == {}


def test_preview_reference_enrichment_uses_entity_row_for_spatial_sources(monkeypatch):
    """Spatial previews should load the referenced entity row when entity_id is provided."""

    source = enrichment_service.EnrichmentSourceConfig(
        id="open-meteo",
        label="Open-Meteo Elevation",
        enabled=True,
        plugin="api_elevation_enricher",
        api_url="https://api.open-meteo.com/v1/elevation",
        profile="openmeteo_elevation_v1",
        query_field="geometry",
        query_param_name="latitude",
    )

    class FakeEnricher:
        def load_data(self, payload, config):
            assert payload["id_plot"] == 42
            assert payload["geo_pt"] == "POINT (166.45 -22.27)"
            assert payload["geometry"] == "Alphitonia neocaledonica"
            assert config["params"]["profile"] == "openmeteo_elevation_v1"
            return {
                "api_enrichment": {"elevation": {"value_m": 412}},
                "api_response_raw": {"elevation": [412]},
            }

    monkeypatch.setattr(
        enrichment_service,
        "_ensure_startable_sources",
        lambda _reference_name, source_id=None: [source],
    )
    monkeypatch.setattr(
        enrichment_service, "_reference_has_geometry", lambda _reference_name: True
    )
    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_row",
        lambda _reference_name, _entity_id: {
            "id_plot": 42,
            "full_name": "Alphitonia neocaledonica",
            "geo_pt": "POINT (166.45 -22.27)",
        },
    )
    monkeypatch.setattr(
        enrichment_service,
        "_build_enricher",
        lambda _plugin: FakeEnricher(),
    )

    response = asyncio.run(
        enrichment_service.preview_reference_enrichment(
            "plots",
            "Alphitonia neocaledonica",
            source_id="open-meteo",
            entity_id=42,
        )
    )

    assert response.success is True
    assert response.entity_name == "Alphitonia neocaledonica"
    assert response.results[0].data == {"elevation": {"value_m": 412}}
    assert response.results[0].config_used["sample_mode"] == "bbox_grid"


def test_get_entities_for_reference_uses_human_display_field(monkeypatch, tmp_path):
    """Spatial entity listings should display a label, not raw geometry bytes."""

    db_path = tmp_path / "db" / "niamoto.duckdb"
    db_path.parent.mkdir(parents=True)
    db_path.touch()

    captured_queries: list[str] = []

    class DummyDatabase:
        def __init__(self, *_args, **_kwargs):
            self.engine = object()

        def close_db_session(self):
            return None

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        captured_queries.append(query_text)
        if "LIMIT 0" in query_text:
            return pd.DataFrame(columns=["id", "name", "geometry", "extra_data"])
        if "COUNT(*) as count" in query_text:
            return pd.DataFrame([{"count": 1}])
        return pd.DataFrame(
            [
                {
                    "id": 1,
                    "name": "Bogota",
                    "geometry": b"\x01\x02binary-geometry",
                    "extra_data": None,
                }
            ]
        )

    monkeypatch.setattr(enrichment_service, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        enrichment_service,
        "_get_reference_table_name",
        lambda _reference_name: "shapes",
    )
    monkeypatch.setattr(enrichment_service, "Database", DummyDatabase)
    monkeypatch.setattr(
        enrichment_service, "quote_identifier", lambda _db, field: field
    )
    monkeypatch.setattr(pd, "read_sql", fake_read_sql)
    monkeypatch.setattr(
        enrichment_service,
        "get_reference_enrichment_config",
        lambda _reference_name: enrichment_service.EnrichmentReferenceConfigResponse(
            reference_name="shapes",
            enabled=True,
            sources=[
                enrichment_service.EnrichmentSourceConfig(
                    id="open-meteo",
                    label="Open-Meteo Elevation",
                    enabled=True,
                    plugin="api_elevation_enricher",
                    query_field="geometry",
                )
            ],
        ),
    )

    result = enrichment_service.get_entities_for_reference("shapes", search="Bog")

    assert result["entities"][0]["name"] == "Bogota"
    assert result["query_field"] == "geometry"
    assert result["display_field"] == "name"
    assert any(
        "CAST(name AS VARCHAR) ILIKE :search" in query for query in captured_queries
    )
    assert any("ORDER BY name" in query for query in captured_queries)
    assert any(
        "SELECT id, name, extra_data FROM shapes" in query for query in captured_queries
    )


def test_get_entities_for_reference_prefers_relation_reference_key(
    monkeypatch, tmp_path
):
    """Plot references should prefer schema.name_field over relation.reference_key."""

    db_path = tmp_path / "db" / "niamoto.duckdb"
    db_path.parent.mkdir(parents=True)
    db_path.touch()

    captured_queries: list[str] = []

    class DummyDatabase:
        def __init__(self, *_args, **_kwargs):
            self.engine = object()

        def close_db_session(self):
            return None

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        captured_queries.append(query_text)
        if "LIMIT 0" in query_text:
            return pd.DataFrame(columns=["id_plot", "plot", "geo_pt", "extra_data"])
        if "COUNT(*) as count" in query_text:
            return pd.DataFrame([{"count": 1}])
        return pd.DataFrame(
            [
                {
                    "id_plot": 10,
                    "plot": "Forêt Plate P12",
                    "geo_pt": "POINT (165.12036133 -21.14814186)",
                    "extra_data": None,
                }
            ]
        )

    monkeypatch.setattr(enrichment_service, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        enrichment_service, "_get_reference_table_name", lambda _reference_name: "plots"
    )
    monkeypatch.setattr(enrichment_service, "Database", DummyDatabase)
    monkeypatch.setattr(
        enrichment_service, "quote_identifier", lambda _db, field: field
    )
    monkeypatch.setattr(pd, "read_sql", fake_read_sql)
    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "schema": {"name_field": "plot"},
            "relation": {"reference_key": "id_plot"},
        },
    )
    monkeypatch.setattr(
        enrichment_service,
        "_reference_geometry_fields",
        lambda _reference_name: ["geo_pt"],
    )
    monkeypatch.setattr(
        enrichment_service,
        "get_reference_enrichment_config",
        lambda _reference_name: enrichment_service.EnrichmentReferenceConfigResponse(
            reference_name="plots",
            enabled=True,
            sources=[
                enrichment_service.EnrichmentSourceConfig(
                    id="open-meteo",
                    label="Open-Meteo Elevation",
                    enabled=True,
                    plugin="api_elevation_enricher",
                    query_field="geometry",
                )
            ],
        ),
    )

    result = enrichment_service.get_entities_for_reference("plots", search="Forêt")

    assert result["entities"][0]["name"] == "Forêt Plate P12"
    assert result["query_field"] == "geo_pt"
    assert result["display_field"] == "plot"
    assert any(
        "CAST(plot AS VARCHAR) ILIKE :search" in query for query in captured_queries
    )
    assert any("ORDER BY plot" in query for query in captured_queries)
    assert any(
        "SELECT id_plot, plot, extra_data FROM plots" in query
        for query in captured_queries
    )


def test_get_entities_for_reference_falls_back_to_csv_labels_on_invalid_unicode(
    monkeypatch, tmp_path
):
    """Plot listings should fall back to source CSV labels when DB text is corrupted."""

    db_path = tmp_path / "db" / "niamoto.duckdb"
    db_path.parent.mkdir(parents=True)
    db_path.touch()

    captured_queries: list[str] = []

    class DummyDatabase:
        def __init__(self, *_args, **_kwargs):
            self.engine = object()

        def close_db_session(self):
            return None

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        captured_queries.append(query_text)
        if "LIMIT 0" in query_text:
            return pd.DataFrame(
                columns=["id_plot", "plot", "extra_data", "geo_pt_geom"]
            )
        if "COUNT(*) as count" in query_text:
            return pd.DataFrame([{"count": 1}])
        if "SELECT id_plot, plot, extra_data FROM plots" in query_text:
            raise Exception("Invalid unicode (byte sequence mismatch)")
        if "SELECT id_plot, extra_data FROM plots" in query_text:
            return pd.DataFrame(
                [
                    {"id_plot": 10, "extra_data": None},
                    {"id_plot": 11, "extra_data": None},
                ]
            )
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(enrichment_service, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        enrichment_service, "_get_reference_table_name", lambda _reference_name: "plots"
    )
    monkeypatch.setattr(enrichment_service, "Database", DummyDatabase)
    monkeypatch.setattr(
        enrichment_service, "quote_identifier", lambda _db, field: field
    )
    monkeypatch.setattr(pd, "read_sql", fake_read_sql)
    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_config_section",
        lambda _reference_name: {
            "connector": {"type": "file", "format": "csv", "path": "imports/plots.csv"},
            "schema": {"id_field": "id_plot", "name_field": "plot"},
            "relation": {"reference_key": "plot"},
        },
    )
    monkeypatch.setattr(
        enrichment_service,
        "_load_reference_display_name_map",
        lambda _reference_name, _id_field, _display_field: {
            "10": "Forêt Plate P12",
            "11": "Forêt Plate P17",
        },
    )
    monkeypatch.setattr(
        enrichment_service,
        "_reference_geometry_fields",
        lambda _reference_name: ["geo_pt_geom"],
    )
    monkeypatch.setattr(
        enrichment_service,
        "get_reference_enrichment_config",
        lambda _reference_name: enrichment_service.EnrichmentReferenceConfigResponse(
            reference_name="plots",
            enabled=True,
            sources=[
                enrichment_service.EnrichmentSourceConfig(
                    id="open-meteo",
                    label="Open-Meteo Elevation",
                    enabled=True,
                    plugin="api_elevation_enricher",
                    query_field="geometry",
                )
            ],
        ),
    )

    result = enrichment_service.get_entities_for_reference("plots")

    assert result["total"] == 2
    assert result["entities"][0]["name"] == "Forêt Plate P12"
    assert result["entities"][1]["name"] == "Forêt Plate P17"
    assert any(
        "SELECT id_plot, extra_data FROM plots" in query for query in captured_queries
    )
