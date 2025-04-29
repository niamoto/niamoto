import pytest
import requests
import requests_mock

from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
    ApiTaxonomyEnricher,
    ApiTaxonomyEnricherConfig,
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
    }

    # Validate config using the Pydantic model
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()

    # Mock the API request
    api_url = valid_config["api_url"]
    expected_query = taxon_data[valid_config["query_field"]]
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
        "api_url": "https://test.api.com",
        # Provide an empty mapping to trigger the custom validator
        "response_mapping": {},
    }
    with pytest.raises(ValueError, match="response_mapping cannot be empty"):
        ApiTaxonomyEnricherConfig(**config_dict)


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
        "api_url": "https://test.api.com",
        "response_mapping": {"id": "api_id"},  # Minimal valid mapping
        "auth_method": auth_method,
        "auth_params": auth_params,
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
        "api_url": "https://test.api.com",
        "response_mapping": {"id": "api_id"},
        "auth_method": auth_method,
        "auth_params": auth_params,
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
        "api_url": "https://cache.api.com/search",
        "query_field": "full_name",
        "response_mapping": {"api_id": "id"},
        "cache_results": True,
        "auth_method": "none",
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["api_url"]
    query_value = taxon_data[valid_config["query_field"]]
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
        "api_url": "https://nocache.api.com/search",
        "query_field": "full_name",
        "response_mapping": {"api_id": "id"},
        "cache_results": False,  # Caching disabled
        "auth_method": "none",
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["api_url"]
    query_value = taxon_data[valid_config["query_field"]]
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


# --- Error Handling Tests ---


def test_load_data_api_error_404(
    enricher: ApiTaxonomyEnricher, requests_mock: requests_mock.Mocker
):
    """Test handling of API 404 Not Found error."""
    taxon_data = {"id": 4, "full_name": "Not Found species"}
    config_dict = {
        "plugin": "api_taxonomy_enricher",
        "api_url": "https://error.api.com/search",
        "query_field": "full_name",
        "response_mapping": {"api_id": "id"},
        "cache_results": False,
        "auth_method": "none",
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["api_url"]
    query_value = taxon_data[valid_config["query_field"]]
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
        "api_url": "https://servererror.api.com/search",
        "query_field": "full_name",
        "response_mapping": {"api_id": "id"},
        "cache_results": False,
        "auth_method": "none",
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["api_url"]
    query_value = taxon_data[valid_config["query_field"]]
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
        "api_url": "https://connectionerror.api.com/search",
        "query_field": "full_name",
        "response_mapping": {"api_id": "id"},
        "cache_results": False,
        "auth_method": "none",
    }
    valid_config = ApiTaxonomyEnricherConfig(**config_dict).model_dump()
    api_url = valid_config["api_url"]
    query_value = taxon_data[valid_config["query_field"]]
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
