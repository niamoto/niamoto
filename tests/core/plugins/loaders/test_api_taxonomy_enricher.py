import pytest
import requests
import requests_mock

from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
    ApiTaxonomyEnricher,
    ApiTaxonomyEnricherConfig,
    ApiTaxonomyEnricherParams,
)


@pytest.fixture
def enricher() -> ApiTaxonomyEnricher:
    """Provides an instance of the ApiTaxonomyEnricher."""
    # No db needed for basic loading tests
    return ApiTaxonomyEnricher(db=None)


def test_load_data_success_no_auth(
    enricher: ApiTaxonomyEnricher, requests_mock: requests_mock.Mocker
):
    """Test successful data enrichment without authentication or caching."""
    # --- Arrange ---
    taxon_data = {
        "id": 1,
        "full_name": "Test species",
        "rank": "species",
        "metadata": {},
    }

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://test.api.com/search",
            "query_params": {"format": "json"},
            "query_field": "full_name",
            "response_mapping": {
                "api_id": "id",
                "description": "details.description",
                "source_url": "sourceInfo.url",
            },
            "rate_limit": 10.0,  # High limit for testing
            "cache_results": False,
            "auth_method": "none",
        },
    }

    # Validate config using the Pydantic model
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()

    # Mock the API request
    api_url = valid_config["params"]["api_url"]
    expected_query = taxon_data[valid_config["params"]["query_field"]]
    mock_response_data = {
        "id": 123,
        "name": "Test species",
        "details": {"description": "A test species from the API.", "rank": "SPECIES"},
        "sourceInfo": {"url": "https://test.api.com/item/123"},
    }
    requests_mock.get(
        # Use 'q' as the query parameter name, matching the code default
        f"{api_url}?format=json&q={expected_query}",
        json=mock_response_data,
    )

    # --- Act ---
    enriched_data = enricher.load_data(taxon_data, valid_config)

    # --- Assert ---
    assert "api_enrichment" in enriched_data
    expected_enrichment = {
        "api_id": 123,
        "description": "A test species from the API.",
        "source_url": "https://test.api.com/item/123",
    }
    assert enriched_data["api_enrichment"] == expected_enrichment

    # Check original data is preserved
    assert enriched_data["id"] == taxon_data["id"]
    assert enriched_data["full_name"] == taxon_data["full_name"]
    assert enriched_data["rank"] == taxon_data["rank"]

    # Check request history
    history = requests_mock.request_history
    assert len(history) == 1
    assert history[0].method == "GET"
    # Use 'q' in the asserted URL as well
    assert history[0].url == f"{api_url}?format=json&q=Test+species"


# --- Config Validation Tests ---


def test_config_validation_missing_response_mapping():
    """Test config validation fails when response_mapping is empty."""
    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://test.api.com",
            # Provide an empty mapping to trigger the custom validator
            "response_mapping": {},
        },
    }
    with pytest.raises(ValueError, match="response_mapping cannot be empty"):
        ApiTaxonomyEnricherConfig(**config_dict)


def test_config_validation_allows_gbif_rich_without_response_mapping():
    """Structured GBIF profile should not require flat response_mapping."""

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://api.gbif.org/v2/species/match",
            "profile": "gbif_rich",
            "query_param_name": "scientificName",
            "response_mapping": {},
        },
    }

    config = ApiTaxonomyEnricherConfig(**config_dict)
    assert config.params.profile == "gbif_rich"
    assert config.params.response_mapping == {}


def test_config_validation_allows_tropicos_rich_without_response_mapping():
    """Structured Tropicos profile should not require flat response_mapping."""

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://services.tropicos.org/Name/Search",
            "profile": "tropicos_rich",
            "auth_method": "api_key",
            "auth_params": {
                "location": "query",
                "name": "apikey",
                "key": "secret",
            },
            "query_param_name": "name",
            "response_mapping": {},
        },
    }

    config = ApiTaxonomyEnricherConfig(**config_dict)
    assert config.params.profile == "tropicos_rich"
    assert config.params.response_mapping == {}


def test_config_validation_allows_col_rich_without_response_mapping():
    """Structured COL profile should not require flat response_mapping."""

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://api.checklistbank.org/dataset/314774/nameusage/search",
            "profile": "col_rich",
            "use_name_verifier": True,
            "dataset_key": 314774,
            "query_param_name": "q",
            "response_mapping": {},
        },
    }

    config = ApiTaxonomyEnricherConfig(**config_dict)
    assert config.params.profile == "col_rich"
    assert config.params.use_name_verifier is True
    assert config.params.dataset_key == 314774
    assert config.params.response_mapping == {}


@pytest.mark.parametrize(
    "auth_method, auth_params, error_message",
    [
        # API Key Tests
        ("api_key", {}, "'key' in auth_params"),
        ("api_key", {"key": "123"}, "'location' in auth_params"),
        ("api_key", {"key": "123", "location": "header"}, "'name' in auth_params"),
        # Basic Auth Tests
        ("basic", {}, "'username' and 'password' in auth_params"),
        ("basic", {"username": "user"}, "'username' and 'password' in auth_params"),
        # OAuth2 Tests
        ("oauth2", {}, "either 'token' or 'token_url' in auth_params"),
        (
            "oauth2",
            {"token_url": "http://token.url"},
            "'client_id' and 'client_secret' in auth_params",
        ),
        (
            "oauth2",
            {"token_url": "http://token.url", "client_id": "id"},
            "'client_id' and 'client_secret' in auth_params",
        ),
        # Bearer Token Tests
        ("bearer", {}, "'token' in auth_params"),
    ],
)
def test_config_validation_auth_errors(
    auth_method: str, auth_params: dict, error_message: str
):
    """Test various authentication configuration errors."""
    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://test.api.com",
            "response_mapping": {"id": "api_id"},  # Minimal valid mapping
            "auth_method": auth_method,
            "auth_params": auth_params,
        },
    }
    with pytest.raises(ValueError, match=error_message):
        ApiTaxonomyEnricherConfig(**config_dict)


@pytest.mark.parametrize(
    "auth_method, auth_params",
    [
        ("none", {}),
        ("api_key", {"key": "123", "location": "query", "name": "apiKey"}),
        ("api_key", {"key": "123", "location": "header", "name": "X-API-KEY"}),
        ("api_key", {"key": "123", "location": "cookie", "name": "api_session"}),
        ("basic", {"username": "user", "password": "pass"}),
        ("oauth2", {"token": "abc"}),
        (
            "oauth2",
            {
                "token_url": "http://token.url",
                "client_id": "id",
                "client_secret": "secret",
            },
        ),
        ("bearer", {"token": "xyz"}),
    ],
)
def test_config_validation_auth_success(auth_method: str, auth_params: dict):
    """Test valid authentication configurations."""
    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://test.api.com",
            "response_mapping": {"id": "api_id"},
            "auth_method": auth_method,
            "auth_params": auth_params,
        },
    }
    # Should not raise ValueError
    ApiTaxonomyEnricherConfig(**config_dict)


# --- Caching Tests ---


def test_load_data_with_caching(
    enricher: ApiTaxonomyEnricher, requests_mock: requests_mock.Mocker
):
    """Test that results are cached when cache_results is True."""
    taxon_data = {"id": 2, "full_name": "Cached species"}
    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://cache.api.com/search",
            "query_field": "full_name",
            "response_mapping": {"api_id": "id"},
            "cache_results": True,
            "auth_method": "none",
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["params"]["api_url"]
    query_value = taxon_data[valid_config["params"]["query_field"]]
    mock_response = {"id": 456, "name": query_value}
    requests_mock.get(f"{api_url}?q={query_value}", json=mock_response)

    # First call - should hit the API
    result1 = enricher.load_data(taxon_data, valid_config)
    assert requests_mock.call_count == 1
    assert "api_enrichment" in result1
    assert result1["api_enrichment"] == {"api_id": 456}

    # Second call - should use cache
    result2 = enricher.load_data(taxon_data, valid_config)
    assert requests_mock.call_count == 1  # No new API call
    assert result1 == result2  # Result should be identical


def test_load_data_without_caching_multiple_calls(
    enricher: ApiTaxonomyEnricher, requests_mock: requests_mock.Mocker
):
    """Test that results are not cached when cache_results is False."""
    taxon_data = {"id": 3, "full_name": "Uncached species"}
    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://nocache.api.com/search",
            "query_field": "full_name",
            "response_mapping": {"api_id": "id"},
            "cache_results": False,  # Caching disabled
            "auth_method": "none",
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["params"]["api_url"]
    query_value = taxon_data[valid_config["params"]["query_field"]]
    mock_response = {"id": 789, "name": query_value}
    requests_mock.get(f"{api_url}?q={query_value}", json=mock_response)

    # First call
    result1 = enricher.load_data(taxon_data, valid_config)
    assert requests_mock.call_count == 1
    assert "api_enrichment" in result1
    assert result1["api_enrichment"] == {"api_id": 789}

    # Second call - should hit the API again
    result2 = enricher.load_data(taxon_data, valid_config)
    assert requests_mock.call_count == 2  # API called again
    assert result1 == result2  # Result should be the same, but fetched again


def test_load_data_gbif_rich_returns_structured_summary(
    enricher: ApiTaxonomyEnricher, monkeypatch: pytest.MonkeyPatch
):
    """GBIF rich profile should return a structured summary instead of a flat mapping."""

    monkeypatch.setattr(
        enricher,
        "_gbif_match",
        lambda query, params: (
            {
                "usage_key": "123",
                "scientific_name": query,
                "canonical_name": query,
                "rank": "SPECIES",
                "status": "ACCEPTED",
                "confidence": 98,
                "match_type": "EXACT",
                "taxonomy_source": "COL_XR",
            },
            {"usageKey": "123"},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_gbif_taxonomy",
        lambda usage_key: (
            {
                "kingdom": "Plantae",
                "family": "Rhamnaceae",
                "genus": "Alphitonia",
                "species": "Alphitonia neocaledonica",
                "synonyms_count": 2,
                "vernacular_names": ["Bois savon"],
                "iucn_category": "LC",
            },
            {"detail": {"key": usage_key}},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_gbif_occurrence_summary",
        lambda usage_key: (
            {
                "occurrence_count": 42,
                "countries": ["NC"],
                "datasets_count": 3,
                "basis_of_record": ["HUMAN_OBSERVATION"],
            },
            {"count": 42},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_gbif_media_summary",
        lambda usage_key, media_limit: (
            {
                "media_count": 5,
                "items": [{"identifier": "https://img.example.org/1.jpg"}],
            },
            {"results": [{"identifier": "https://img.example.org/1.jpg"}]},
        ),
    )

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://api.gbif.org/v2/species/match",
            "profile": "gbif_rich",
            "taxonomy_source": "col_xr",
            "query_field": "full_name",
            "query_param_name": "scientificName",
            "include_taxonomy": True,
            "include_occurrences": True,
            "include_media": True,
            "response_mapping": {},
            "cache_results": False,
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()

    enriched = enricher.load_data(
        {"id": 1, "full_name": "Alphitonia neocaledonica"},
        valid_config,
    )

    assert enriched["api_enrichment"]["match"]["usage_key"] == "123"
    assert enriched["api_enrichment"]["taxonomy"]["family"] == "Rhamnaceae"
    assert enriched["api_enrichment"]["occurrence_summary"]["occurrence_count"] == 42
    assert enriched["api_enrichment"]["media_summary"]["media_count"] == 5
    assert enriched["api_enrichment"]["links"]["species"].endswith("/123")
    assert enriched["api_response_raw"]["match"] == {"usageKey": "123"}


def test_load_data_gbif_rich_handles_no_match(
    enricher: ApiTaxonomyEnricher, monkeypatch: pytest.MonkeyPatch
):
    """GBIF rich profile should return a structured no-match outcome."""

    monkeypatch.setattr(
        enricher,
        "_gbif_match",
        lambda query, params: (
            {
                "usage_key": "",
                "scientific_name": query,
                "canonical_name": None,
                "rank": None,
                "status": "NONE",
                "confidence": 0,
                "match_type": "NONE",
                "taxonomy_source": "COL_XR",
            },
            {"matchType": "NONE"},
        ),
    )

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://api.gbif.org/v2/species/match",
            "profile": "gbif_rich",
            "query_field": "full_name",
            "query_param_name": "scientificName",
            "response_mapping": {},
            "cache_results": False,
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()

    enriched = enricher.load_data(
        {"id": 1, "full_name": "Unknown species"},
        valid_config,
    )

    assert enriched["api_enrichment"]["block_status"]["match"] == "no_match"
    assert enriched["api_enrichment"]["provenance"]["outcome"] == "no_match"


def test_resolve_name_with_verifier_uses_profile_default_source(
    enricher: ApiTaxonomyEnricher, monkeypatch: pytest.MonkeyPatch
):
    """GN resolution should use the profile default source and canonical query name."""

    captured: dict[str, object] = {}

    def fake_request(url: str, params: object = None) -> dict[str, object]:
        captured["url"] = url
        captured["params"] = params
        return {
            "names": [
                {
                    "name": "Alphitonia neocaledonica (Schltr.) Guillaumin",
                    "bestResult": {
                        "dataSourceId": 11,
                        "dataSourceTitleShort": "GBIF Backbone Taxonomy",
                        "sortScore": 9.41,
                        "currentCanonicalSimple": "Alphitonia neocaledonica",
                        "currentName": "Alphitonia neocaledonica (Schltr.) Guillaumin",
                        "matchedName": "Alphitonia neocaledonica (Schltr.) Guillaumin",
                        "matchType": "Exact",
                    },
                }
            ]
        }

    monkeypatch.setattr(enricher, "_request_json", fake_request)

    config = ApiTaxonomyEnricherConfig(
        plugin="api_taxonomy_enricher",
        params={
            "api_url": "https://api.gbif.org/v2/species/match",
            "profile": "gbif_rich",
            "use_name_verifier": True,
            "query_param_name": "scientificName",
            "response_mapping": {},
        },
    )

    query_name, summary, raw = enricher._resolve_name_with_verifier(
        "Alphitonia neocaledonica (Schltr.) Guillaumin",
        config.params,
    )

    assert str(captured["url"]).endswith(
        "/Alphitonia+neocaledonica+%28Schltr.%29+Guillaumin"
    )
    assert captured["params"] == {"data_sources": "11"}
    assert query_name == "Alphitonia neocaledonica"
    assert summary["status"] == "resolved"
    assert summary["data_source_id"] == 11
    assert summary["was_corrected"] is True
    assert (
        raw["names"][0]["bestResult"]["dataSourceTitleShort"]
        == "GBIF Backbone Taxonomy"
    )


def test_load_data_gbif_rich_uses_name_verifier_result(
    enricher: ApiTaxonomyEnricher, monkeypatch: pytest.MonkeyPatch
):
    """Structured providers should consume the resolved query when GN is enabled."""

    captured: dict[str, str] = {}

    monkeypatch.setattr(
        enricher,
        "_resolve_name_with_verifier",
        lambda query, params: (
            "Alphitonia neocaledonica",
            {
                "enabled": True,
                "status": "resolved",
                "submitted_name": query,
                "query_name": "Alphitonia neocaledonica",
                "matched_name": "Alphitonia neocaledonica (Schltr.) Guillaumin",
                "best_result": "Alphitonia neocaledonica",
                "data_source_title": "GBIF Backbone Taxonomy",
                "data_source_id": 11,
                "score": 9.41,
                "was_corrected": True,
                "alternatives": ["Alphitonia neocaledonica"],
            },
            {"names": [{"name": query}]},
        ),
    )

    def fake_gbif_match(query: str, params: ApiTaxonomyEnricherParams):
        captured["query"] = query
        return (
            {
                "usage_key": "123",
                "scientific_name": query,
                "canonical_name": query,
                "rank": "SPECIES",
                "status": "ACCEPTED",
                "confidence": 98,
                "match_type": "EXACT",
                "taxonomy_source": "COL_XR",
            },
            {"usageKey": "123"},
        )

    monkeypatch.setattr(enricher, "_gbif_match", fake_gbif_match)

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://api.gbif.org/v2/species/match",
            "profile": "gbif_rich",
            "use_name_verifier": True,
            "query_field": "full_name",
            "query_param_name": "scientificName",
            "include_taxonomy": False,
            "include_occurrences": False,
            "include_media": False,
            "response_mapping": {},
            "cache_results": False,
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()

    enriched = enricher.load_data(
        {"id": 1, "full_name": "Alphitonia neocaledonica (Schltr.) Guillaumin"},
        valid_config,
    )

    assert captured["query"] == "Alphitonia neocaledonica"
    assert enriched["api_enrichment"]["name_resolution"]["status"] == "resolved"
    assert (
        enriched["api_enrichment"]["provenance"]["query_submitted"]
        == "Alphitonia neocaledonica (Schltr.) Guillaumin"
    )
    assert (
        enriched["api_enrichment"]["provenance"]["query_used"]
        == "Alphitonia neocaledonica"
    )
    assert enriched["api_response_raw"]["name_resolution"] == {
        "names": [{"name": "Alphitonia neocaledonica (Schltr.) Guillaumin"}]
    }


def test_load_data_tropicos_rich_returns_structured_summary(
    enricher: ApiTaxonomyEnricher, monkeypatch: pytest.MonkeyPatch
):
    """Tropicos rich profile should return a structured summary instead of a flat mapping."""

    monkeypatch.setattr(
        enricher,
        "_tropicos_match",
        lambda query, params: (
            {
                "name_id": "25509881",
                "scientific_name": query,
                "scientific_name_with_authors": f"{query} L.",
                "family": "Poaceae",
                "rank": "Sp.",
                "nomenclature_status": "Legitimate",
                "matched_name": query,
                "candidate_count": 1,
            },
            {"results": [{"NameId": 25509881}]},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_tropicos_summary",
        lambda name_id, params: (
            {
                "name_id": name_id,
                "scientific_name": "Poa annua",
                "scientific_name_with_authors": "Poa annua L.",
                "family": "Poaceae",
                "rank": "Sp.",
                "nomenclature_status": "Legitimate",
                "accepted_name_id": name_id,
                "accepted_name": "Poa annua",
                "accepted_name_with_authors": "Poa annua L.",
            },
            {"NameId": name_id},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_tropicos_nomenclature",
        lambda name_id, summary_data, params: (
            {
                "accepted_name_id": name_id,
                "accepted_name": "Poa annua",
                "accepted_name_with_authors": "Poa annua L.",
                "synonyms_count": 3,
                "accepted_name_count": 1,
                "selected_synonyms": ["Poa annua var. typica"],
            },
            {"synonyms": [{"NameId": 1}]},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_tropicos_taxonomy",
        lambda name_id, summary_data, params: (
            {
                "family": "Poaceae",
                "higher_taxa": ["Plantae", "Poales"],
            },
            {"higher_taxa": [{"DisplayName": "Poales"}]},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_tropicos_references",
        lambda name_id, params: (
            {
                "references_count": 12,
                "items": [{"title": "Flora Europaea"}],
            },
            {"results": [{"Reference": {"ArticleTitle": "Flora Europaea"}}]},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_tropicos_distribution_summary",
        lambda name_id, params: (
            {
                "distribution_count": 2,
                "countries": ["Austria"],
                "regions": ["Europe"],
            },
            {"results": [{"Location": {"CountryName": "Austria"}}]},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_tropicos_media_summary",
        lambda name_id, media_limit, params: (
            {
                "media_count": 4,
                "items": [{"thumbnail_url": "https://img.example.org/1.jpg"}],
            },
            {"results": [{"ImageId": 1}]},
        ),
    )

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://services.tropicos.org/Name/Search",
            "profile": "tropicos_rich",
            "query_field": "full_name",
            "query_param_name": "name",
            "auth_method": "api_key",
            "auth_params": {
                "location": "query",
                "name": "apikey",
                "key": "secret",
            },
            "include_references": True,
            "include_distributions": True,
            "include_media": True,
            "response_mapping": {},
            "cache_results": False,
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()

    enriched = enricher.load_data(
        {"id": 1, "full_name": "Poa annua"},
        valid_config,
    )

    assert enriched["api_enrichment"]["match"]["name_id"] == "25509881"
    assert enriched["api_enrichment"]["nomenclature"]["synonyms_count"] == 3
    assert enriched["api_enrichment"]["distribution_summary"]["countries"] == [
        "Austria"
    ]
    assert enriched["api_enrichment"]["media_summary"]["media_count"] == 4
    assert enriched["api_enrichment"]["links"]["record"].endswith("/25509881")
    assert enriched["api_response_raw"]["match"] == {"results": [{"NameId": 25509881}]}


def test_load_data_tropicos_rich_handles_no_match(
    enricher: ApiTaxonomyEnricher, monkeypatch: pytest.MonkeyPatch
):
    """Tropicos rich profile should return a structured no-match outcome."""

    monkeypatch.setattr(
        enricher,
        "_tropicos_match",
        lambda query, params: (
            {
                "name_id": "",
                "scientific_name": query,
                "matched_name": query,
                "candidate_count": 0,
            },
            {"results": []},
        ),
    )

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://services.tropicos.org/Name/Search",
            "profile": "tropicos_rich",
            "query_field": "full_name",
            "query_param_name": "name",
            "auth_method": "api_key",
            "auth_params": {
                "location": "query",
                "name": "apikey",
                "key": "secret",
            },
            "response_mapping": {},
            "cache_results": False,
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()

    enriched = enricher.load_data(
        {"id": 1, "full_name": "Unknown species"},
        valid_config,
    )

    assert enriched["api_enrichment"]["block_status"]["match"] == "no_match"
    assert enriched["api_enrichment"]["provenance"]["outcome"] == "no_match"


def test_load_data_col_rich_returns_structured_summary(
    enricher: ApiTaxonomyEnricher, monkeypatch: pytest.MonkeyPatch
):
    """Catalogue of Life rich profile should return a structured summary."""

    monkeypatch.setattr(
        enricher,
        "_col_dataset_metadata",
        lambda dataset_key: {
            "key": dataset_key,
            "label": "Catalogue of Life (2026-04-07 XR)",
            "version": "2026-04-07 XR",
        },
    )
    monkeypatch.setattr(
        enricher,
        "_col_match",
        lambda query, dataset_key: (
            {
                "taxon_id": "C66X",
                "name_id": "3FNWHqciKg9O2_kT0ohQ8",
                "scientific_name": query,
                "authorship": "(Schltr.) Guillaumin",
                "canonical_name": query,
                "rank": "species",
                "status": "accepted",
                "matched_name": query,
                "dataset_key": dataset_key,
            },
            {"result": [{"id": "C66X"}]},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_col_taxon_detail",
        lambda dataset_key, taxon_id: (
            {
                "taxon_id": taxon_id,
                "name_id": "3FNWHqciKg9O2_kT0ohQ8",
                "scientific_name": "Alphitonia neocaledonica",
                "authorship": "(Schltr.) Guillaumin",
                "canonical_name": "Alphitonia neocaledonica",
                "rank": "species",
                "status": "accepted",
                "matched_name": "Alphitonia neocaledonica",
                "dataset_key": dataset_key,
            },
            {"id": taxon_id, "link": "https://example.org/source"},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_col_build_links",
        lambda dataset_key, taxon_id, taxon_raw: {
            "checklistbank_taxon": f"https://www.checklistbank.org/dataset/{dataset_key}/taxon/{taxon_id}",
            "source_record": taxon_raw["link"],
        },
    )
    monkeypatch.setattr(
        enricher,
        "_col_taxonomy",
        lambda dataset_key, taxon_id, fallback_species: (
            {
                "classification": [{"rank": "family", "name": "Rhamnaceae"}],
                "kingdom": "Plantae",
                "family": "Rhamnaceae",
                "genus": "Alphitonia",
                "species": fallback_species,
            },
            {"results": [{"rank": "family", "name": "Rhamnaceae"}]},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_col_nomenclature",
        lambda dataset_key, taxon_id, match_summary: (
            {
                "accepted_name": "Alphitonia neocaledonica",
                "accepted_name_with_authors": "Alphitonia neocaledonica (Schltr.) Guillaumin",
                "synonyms_count": 2,
                "synonyms_sample": ["Pomaderris neocaledonica Schltr."],
            },
            {"homotypic": [], "heterotypic": []},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_col_vernaculars",
        lambda dataset_key, taxon_id: (
            {
                "vernacular_count": 2,
                "by_language": {"eng": ["Soap tree"]},
                "sample": [{"name": "Soap tree", "language": "eng"}],
            },
            {"results": [{"name": "Soap tree", "language": "eng"}]},
            [{"name": "Soap tree", "language": "eng"}],
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_col_distribution_summary",
        lambda dataset_key, taxon_id: (
            {
                "distribution_count": 1,
                "areas": ["New Caledonia"],
                "gazetteers": ["text"],
            },
            {"results": [{"area": {"name": "New Caledonia", "gazetteer": "text"}}]},
        ),
    )
    monkeypatch.setattr(
        enricher,
        "_col_references",
        lambda dataset_key,
        taxon_raw,
        nomenclature_raw,
        vernacular_items,
        reference_limit: (
            {
                "references_count": 1,
                "items": [
                    {
                        "id": "ref-1",
                        "citation": "Guillaumin. (1911).",
                        "title": "Notul. Syst.",
                    }
                ],
            },
            [{"id": "ref-1"}],
        ),
    )

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://api.checklistbank.org/dataset/314774/nameusage/search",
            "profile": "col_rich",
            "dataset_key": 314774,
            "query_field": "full_name",
            "query_param_name": "q",
            "include_vernaculars": True,
            "include_distributions": True,
            "include_references": True,
            "reference_limit": 5,
            "response_mapping": {},
            "cache_results": False,
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()

    enriched = enricher.load_data(
        {"id": 1, "full_name": "Alphitonia neocaledonica"},
        valid_config,
    )

    assert enriched["api_enrichment"]["match"]["taxon_id"] == "C66X"
    assert enriched["api_enrichment"]["taxonomy"]["family"] == "Rhamnaceae"
    assert enriched["api_enrichment"]["nomenclature"]["synonyms_count"] == 2
    assert enriched["api_enrichment"]["vernaculars"]["vernacular_count"] == 2
    assert enriched["api_enrichment"]["distribution_summary"]["areas"] == [
        "New Caledonia"
    ]
    assert enriched["api_enrichment"]["references"]["references_count"] == 1
    assert enriched["api_enrichment"]["provenance"]["dataset_key"] == 314774
    assert (
        enriched["api_enrichment"]["provenance"]["release_label"]
        == "Catalogue of Life (2026-04-07 XR)"
    )
    assert enriched["api_response_raw"]["search"] == {"result": [{"id": "C66X"}]}


def test_load_data_col_rich_handles_no_match(
    enricher: ApiTaxonomyEnricher, monkeypatch: pytest.MonkeyPatch
):
    """Catalogue of Life rich profile should return a structured no-match outcome."""

    monkeypatch.setattr(
        enricher,
        "_col_dataset_metadata",
        lambda dataset_key: {
            "key": dataset_key,
            "label": "Catalogue of Life (2026-04-07 XR)",
        },
    )
    monkeypatch.setattr(
        enricher,
        "_col_match",
        lambda query, dataset_key: (
            {
                "taxon_id": "",
                "name_id": "",
                "scientific_name": "",
                "authorship": "",
                "canonical_name": "",
                "rank": "",
                "status": "",
                "matched_name": query,
                "dataset_key": dataset_key,
            },
            {"result": []},
        ),
    )

    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://api.checklistbank.org/dataset/314774/nameusage/search",
            "profile": "col_rich",
            "dataset_key": 314774,
            "query_field": "full_name",
            "query_param_name": "q",
            "response_mapping": {},
            "cache_results": False,
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()

    enriched = enricher.load_data(
        {"id": 1, "full_name": "Unknown species"},
        valid_config,
    )

    assert enriched["api_enrichment"]["block_status"]["match"] == "no_match"
    assert enriched["api_enrichment"]["provenance"]["outcome"] == "no_match"


# --- Error Handling Tests ---


def test_load_data_api_error_404(
    enricher: ApiTaxonomyEnricher, requests_mock: requests_mock.Mocker
):
    """Test handling of API 404 Not Found error."""
    taxon_data = {"id": 4, "full_name": "Not Found species"}
    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://error.api.com/search",
            "query_field": "full_name",
            "response_mapping": {"api_id": "id"},
            "cache_results": False,
            "auth_method": "none",
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["params"]["api_url"]
    query_value = taxon_data[valid_config["params"]["query_field"]]
    requests_mock.get(f"{api_url}?q={query_value}", status_code=404)

    # Act
    enriched_data = enricher.load_data(taxon_data, valid_config)

    # Assert - Should return original data without enrichment
    assert "api_enrichment" not in enriched_data
    assert enriched_data == taxon_data
    assert requests_mock.call_count == 1


def test_load_data_api_error_500(
    enricher: ApiTaxonomyEnricher, requests_mock: requests_mock.Mocker
):
    """Test handling of API 500 Internal Server Error."""
    taxon_data = {"id": 5, "full_name": "Server Error species"}
    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://servererror.api.com/search",
            "query_field": "full_name",
            "response_mapping": {"api_id": "id"},
            "cache_results": False,
            "auth_method": "none",
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["params"]["api_url"]
    query_value = taxon_data[valid_config["params"]["query_field"]]
    requests_mock.get(f"{api_url}?q={query_value}", status_code=500)

    # Act
    enriched_data = enricher.load_data(taxon_data, valid_config)

    # Assert - Should return original data without enrichment
    assert "api_enrichment" not in enriched_data
    assert enriched_data == taxon_data
    assert requests_mock.call_count == 1


def test_load_data_request_exception(
    enricher: ApiTaxonomyEnricher, requests_mock: requests_mock.Mocker
):
    """Test handling of requests.exceptions.RequestException."""
    taxon_data = {"id": 6, "full_name": "Connection Error species"}
    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "params": {
            "api_url": "https://connectionerror.api.com/search",
            "query_field": "full_name",
            "response_mapping": {"api_id": "id"},
            "cache_results": False,
            "auth_method": "none",
        },
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["params"]["api_url"]
    query_value = taxon_data[valid_config["params"]["query_field"]]
    # Use requests.exceptions.RequestException directly
    requests_mock.get(
        f"{api_url}?q={query_value}", exc=requests.exceptions.RequestException
    )

    # Act
    enriched_data = enricher.load_data(taxon_data, valid_config)

    # Assert - Should return original data without enrichment
    assert "api_enrichment" not in enriched_data
    assert enriched_data == taxon_data
    assert requests_mock.call_count == 1


# --- Secure Value Tests ---


def test_get_secure_value_plain(enricher: ApiTaxonomyEnricher):
    """Test _get_secure_value with a plain string."""
    assert enricher._get_secure_value("plain_value") == "plain_value"


def test_get_secure_value_env_var(enricher: ApiTaxonomyEnricher, monkeypatch):
    """Test _get_secure_value with an environment variable."""
    monkeypatch.setenv("TEST_API_KEY", "env_secret_key")
    assert enricher._get_secure_value("$ENV:TEST_API_KEY") == "env_secret_key"


def test_get_secure_value_env_var_missing(enricher: ApiTaxonomyEnricher, monkeypatch):
    """Test _get_secure_value with a missing environment variable."""
    # Ensure the variable is not set
    monkeypatch.delenv("MISSING_TEST_VAR", raising=False)
    assert enricher._get_secure_value("$ENV:MISSING_TEST_VAR") == ""


def test_get_secure_value_file(enricher: ApiTaxonomyEnricher, tmp_path):
    """Test _get_secure_value reading from a file."""
    secret_file = tmp_path / "secret.txt"
    secret_content = "file_secret_content"
    secret_file.write_text(secret_content)
    assert enricher._get_secure_value(f"$FILE:{secret_file}") == secret_content


def test_get_secure_value_file_not_found(enricher: ApiTaxonomyEnricher):
    """Test _get_secure_value with a non-existent file."""
    assert enricher._get_secure_value("$FILE:/non/existent/path/secret.txt") == ""


def test_get_secure_value_none(enricher: ApiTaxonomyEnricher):
    """Test _get_secure_value with None input."""
    assert enricher._get_secure_value(None) == ""


def test_get_secure_value_empty_string(enricher: ApiTaxonomyEnricher):
    """Test _get_secure_value with an empty string input."""
    assert enricher._get_secure_value("") == ""


def test_get_secure_value_invalid_prefix(enricher: ApiTaxonomyEnricher):
    """Test _get_secure_value with an invalid prefix."""
    assert enricher._get_secure_value("$INVALID:some_value") == "$INVALID:some_value"


# --- Authentication Setup Tests ---


def test_setup_api_key_auth_header(enricher: ApiTaxonomyEnricher, mocker):
    """Test API key auth setup in header."""
    mocker.patch.object(enricher, "_get_secure_value", return_value="test_key_123")
    auth_params = {"key": "$ENV:API_KEY", "location": "header", "name": "X-API-Key"}
    headers = {}
    params = {}
    cookies = {}
    enricher._setup_api_key_auth(auth_params, headers, params, cookies)
    assert headers == {"X-API-Key": "test_key_123"}
    assert params == {}
    assert cookies == {}
    enricher._get_secure_value.assert_called_once_with("$ENV:API_KEY")


def test_setup_api_key_auth_query(enricher: ApiTaxonomyEnricher, mocker):
    """Test API key auth setup in query parameters."""
    mocker.patch.object(enricher, "_get_secure_value", return_value="test_key_456")
    auth_params = {"key": "$FILE:key.txt", "location": "query", "name": "apiKey"}
    headers = {}
    params = {}
    cookies = {}
    enricher._setup_api_key_auth(auth_params, headers, params, cookies)
    assert headers == {}
    assert params == {"apiKey": "test_key_456"}
    assert cookies == {}
    enricher._get_secure_value.assert_called_once_with("$FILE:key.txt")


def test_setup_api_key_auth_cookie(enricher: ApiTaxonomyEnricher, mocker):
    """Test API key auth setup in cookies."""
    mocker.patch.object(enricher, "_get_secure_value", return_value="test_key_789")
    auth_params = {"key": "plain_key", "location": "cookie", "name": "session_id"}
    headers = {}
    params = {}
    cookies = {}
    enricher._setup_api_key_auth(auth_params, headers, params, cookies)
    assert headers == {}
    assert params == {}
    assert cookies == {"session_id": "test_key_789"}
    enricher._get_secure_value.assert_called_once_with("plain_key")


def test_setup_api_key_auth_invalid_location(enricher: ApiTaxonomyEnricher, mocker):
    """Test API key auth setup with an invalid location (should raise ValueError)."""
    mocker.patch.object(enricher, "_get_secure_value", return_value="test_key_abc")
    auth_params = {"key": "abc", "location": "invalid", "name": "whatever"}
    headers = {}
    params = {}
    cookies = {}
    # Expect a ValueError for the invalid location
    with pytest.raises(ValueError, match="Invalid api_key location 'invalid'"):
        enricher._setup_api_key_auth(auth_params, headers, params, cookies)
    # Check that the key was still fetched before the error
    enricher._get_secure_value.assert_called_once_with("abc")


def test_setup_oauth2_auth_provided_token(enricher: ApiTaxonomyEnricher, mocker):
    """Test OAuth2 setup with a directly provided token."""
    mocker.patch.object(
        enricher, "_get_secure_value", side_effect=lambda x: x
    )  # Passthrough
    auth_params = {"token": "provided_token_123"}
    headers = {}
    enricher._setup_oauth2_auth(auth_params, headers)
    assert headers == {"Authorization": "Bearer provided_token_123"}
    enricher._get_secure_value.assert_called_once_with("provided_token_123")


def test_setup_oauth2_auth_provided_token_secure(enricher: ApiTaxonomyEnricher, mocker):
    """Test OAuth2 setup with a provided token from secure source."""
    mocker.patch.object(enricher, "_get_secure_value", return_value="secure_token_456")
    auth_params = {"token": "$ENV:OAUTH_TOKEN"}
    headers = {}
    enricher._setup_oauth2_auth(auth_params, headers)
    assert headers == {"Authorization": "Bearer secure_token_456"}
    enricher._get_secure_value.assert_called_once_with("$ENV:OAUTH_TOKEN")


def test_setup_oauth2_auth_fetch_token_success(
    enricher: ApiTaxonomyEnricher, mocker, requests_mock: requests_mock.Mocker
):
    """Test OAuth2 setup fetching a new token successfully."""
    # Mock _get_secure_value to return plain client_id/secret
    mocker.patch.object(
        enricher, "_get_secure_value", side_effect=lambda x: x.split(":")[-1]
    )
    auth_params = {
        "token_url": "https://auth.server.com/token",
        "client_id": "client1",
        "client_secret": "secret1",
        "scope": "read write",  # Optional scope
    }
    headers = {}
    token_url = auth_params["token_url"]
    mock_token_response = {
        "access_token": "fetched_token_abc",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    requests_mock.post(token_url, json=mock_token_response)

    # Clear cache before test
    enricher._oauth_tokens.clear()

    enricher._setup_oauth2_auth(auth_params, headers)

    assert headers == {"Authorization": "Bearer fetched_token_abc"}
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.url == token_url
    assert history.method == "POST"
    # Check form data instead of json
    expected_payload = {
        "grant_type": ["client_credentials"],
        "client_id": ["client1"],
        "client_secret": ["secret1"],
        "scope": ["read write"],
    }
    from urllib.parse import parse_qs

    assert parse_qs(history.body) == expected_payload
    # Check cache
    cache_key = f"{token_url}_{auth_params['client_id']}_{auth_params.get('scope', '')}"
    assert cache_key in enricher._oauth_tokens
    assert enricher._oauth_tokens[cache_key]["token"] == "fetched_token_abc"


def test_setup_oauth2_auth_fetch_token_cached(
    enricher: ApiTaxonomyEnricher, mocker, requests_mock: requests_mock.Mocker
):
    """Test OAuth2 setup uses cached token on second call."""
    mocker.patch.object(
        enricher, "_get_secure_value", side_effect=lambda x: x.split(":")[-1]
    )
    auth_params = {
        "token_url": "https://auth.server.com/token",
        "client_id": "client1",
        "client_secret": "secret1",
    }
    headers = {}
    token_url = auth_params["token_url"]
    mock_token_response = {"access_token": "fetched_token_xyz", "token_type": "Bearer"}
    requests_mock.post(token_url, json=mock_token_response)

    # Clear cache and make first call to populate it
    enricher._oauth_tokens.clear()
    # Pass headers directly, not a copy
    enricher._setup_oauth2_auth(auth_params, headers)
    assert requests_mock.call_count == 1
    assert headers == {"Authorization": "Bearer fetched_token_xyz"}

    # Second call - should use cache
    headers_2 = {}
    enricher._setup_oauth2_auth(auth_params, headers_2)
    assert requests_mock.call_count == 1  # No new API call to token endpoint
    assert headers_2 == {"Authorization": "Bearer fetched_token_xyz"}  # Same token


def test_setup_oauth2_auth_fetch_token_failure(
    enricher: ApiTaxonomyEnricher, mocker, requests_mock: requests_mock.Mocker
):
    """Test OAuth2 setup when fetching token fails."""
    mocker.patch.object(
        enricher, "_get_secure_value", side_effect=lambda x: x.split(":")[-1]
    )
    auth_params = {
        "token_url": "https://auth.server.com/token",
        "client_id": "client_fail",
        "client_secret": "secret_fail",
    }
    headers = {}
    token_url = auth_params["token_url"]
    requests_mock.post(token_url, status_code=401, json={"error": "invalid_client"})

    # Clear cache
    enricher._oauth_tokens.clear()

    # Should log an error but not raise, and headers remain empty
    enricher._setup_oauth2_auth(auth_params, headers)

    assert headers == {}
    assert requests_mock.call_count == 1
    # Cache should be empty
    cache_key = f"{token_url}_{auth_params['client_id']}_{auth_params.get('scope', '')}"
    assert cache_key not in enricher._oauth_tokens
