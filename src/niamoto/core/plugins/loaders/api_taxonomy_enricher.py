"""
Plugin for enriching taxonomy data with information from external APIs.
"""

import logging
import os
import time
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import quote_plus

import requests
from pydantic import Field, model_validator, ConfigDict

from niamoto.common.utils.emoji import emoji
from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register

logger = logging.getLogger(__name__)

GBIF_COL_XR_CHECKLIST_KEY = "7ddf754f-d193-4cc9-b351-99906754a03b"
GBIF_MATCH_ENDPOINT = "https://api.gbif.org/v2/species/match"
GBIF_SPECIES_ENDPOINT = "https://api.gbif.org/v1/species"
COL_API_BASE = "https://api.checklistbank.org"
COL_DEFAULT_DATASET_KEY = 314774
TROPICOS_SEARCH_ENDPOINT = "https://services.tropicos.org/Name/Search"
TROPICOS_NAME_ENDPOINT = "https://services.tropicos.org/Name"
BHL_API_ENDPOINT = "https://www.biodiversitylibrary.org/api3"
INAT_TAXA_ENDPOINT = "https://api.inaturalist.org/v1/taxa"
INAT_OBSERVATIONS_ENDPOINT = "https://api.inaturalist.org/v1/observations"
GN_VERIFIER_ENDPOINT = "https://resolver.globalnames.org/api/v1/verifications"
GN_DEFAULT_SOURCE_IDS_BY_PROFILE = {
    "gbif_rich": 11,
    "tropicos_rich": 165,
    "col_rich": 1,
}
GN_SOURCE_ALIASES = {
    "catalogue of life": 1,
    "catalogue-of-life": 1,
    "col": 1,
    "checklistbank": 1,
    "gbif": 11,
    "gbif backbone": 11,
    "gbif backbone taxonomy": 11,
    "global biodiversity information facility": 11,
    "global biodiversity information facility backbone taxonomy": 11,
    "tropicos": 165,
    "tropicos - missouri botanical garden": 165,
}


class ApiTaxonomyEnricherParams(BasePluginParams):
    """Parameters for API taxonomy enricher plugin"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Enrich taxonomy data with information from external APIs",
            "examples": [
                {
                    "api_url": "https://api.example.com/search",
                    "query_field": "full_name",
                    "query_param_name": "q",
                    "response_mapping": {
                        "common_name": "vernacularName",
                        "description": "description",
                    },
                    "auth_method": "api_key",
                    "auth_params": {
                        "key": "$ENV:API_KEY",
                        "location": "header",
                        "name": "X-API-Key",
                    },
                }
            ],
        }
    )

    api_url: str = Field(
        ..., description="Base URL for the API", json_schema_extra={"ui:widget": "text"}
    )
    query_params: Dict[str, str] = Field(
        default_factory=dict,
        description="Default query parameters",
        json_schema_extra={"ui:widget": "json"},
    )
    query_field: str = Field(
        default="full_name",
        description="Field in taxon data to use for query",
        json_schema_extra={"ui:widget": "field-select"},
    )
    query_param_name: str = Field(
        default="q",
        description="Name of the query parameter to use in the API request",
        json_schema_extra={"ui:widget": "text"},
    )
    profile: Optional[str] = Field(
        default=None,
        description="Optional structured provider profile",
        json_schema_extra={"ui:widget": "text"},
    )
    use_name_verifier: bool = Field(
        default=False,
        description="Whether to use Global Names Verifier before structured provider matching",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    name_verifier_preferred_sources: List[str] = Field(
        default_factory=list,
        description="Optional preferred Global Names data sources",
        json_schema_extra={"ui:widget": "array"},
    )
    name_verifier_threshold: Optional[float] = Field(
        default=None,
        description="Optional minimum GN sort score required to replace the submitted query name",
        json_schema_extra={"ui:widget": "number"},
    )
    taxonomy_source: Optional[str] = Field(
        default=None,
        description="Preferred taxonomy source for structured provider profiles",
        json_schema_extra={"ui:widget": "text"},
    )
    dataset_key: int = Field(
        default=COL_DEFAULT_DATASET_KEY,
        ge=1,
        description="ChecklistBank dataset key for Catalogue of Life structured profiles",
        json_schema_extra={"ui:widget": "number"},
    )
    include_taxonomy: bool = Field(
        default=True,
        description="Whether to include taxonomy details for structured provider profiles",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    include_occurrences: bool = Field(
        default=True,
        description="Whether to include occurrence summary for structured provider profiles",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    include_media: bool = Field(
        default=True,
        description="Whether to include media summary for structured provider profiles",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    include_places: bool = Field(
        default=True,
        description="Whether to include place summary for structured provider profiles",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    include_references: bool = Field(
        default=True,
        description="Whether to include reference summary for structured provider profiles",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    include_vernaculars: bool = Field(
        default=True,
        description="Whether to include vernacular summary for structured provider profiles",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    include_distributions: bool = Field(
        default=True,
        description="Whether to include distribution summary for structured provider profiles",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    media_limit: int = Field(
        default=3,
        ge=0,
        description="Maximum number of media items to keep in structured provider summaries",
        json_schema_extra={"ui:widget": "number"},
    )
    observation_limit: int = Field(
        default=5,
        ge=0,
        description="Maximum number of observations to keep in structured provider summaries",
        json_schema_extra={"ui:widget": "number"},
    )
    reference_limit: int = Field(
        default=5,
        ge=0,
        description="Maximum number of references to keep in structured provider summaries",
        json_schema_extra={"ui:widget": "number"},
    )
    include_publication_details: bool = Field(
        default=True,
        description="Whether to include publication details for BHL structured profiles",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    include_page_preview: bool = Field(
        default=True,
        description="Whether to include representative page previews for BHL structured profiles",
        json_schema_extra={"ui:widget": "checkbox"},
    )
    title_limit: int = Field(
        default=5,
        ge=0,
        description="Maximum number of BHL titles to keep in structured provider summaries",
        json_schema_extra={"ui:widget": "number"},
    )
    page_limit: int = Field(
        default=5,
        ge=0,
        description="Maximum number of BHL pages to keep in structured provider summaries",
        json_schema_extra={"ui:widget": "number"},
    )
    response_mapping: Dict[str, str] = Field(
        ...,
        description="Mapping between API response fields and extra_data fields",
        json_schema_extra={"ui:widget": "json"},
    )
    rate_limit: float = Field(
        default=1.0,
        description="Requests per second",
        json_schema_extra={"ui:widget": "number"},
    )
    cache_results: bool = Field(
        default=True,
        description="Whether to cache API results",
        json_schema_extra={"ui:widget": "checkbox"},
    )

    # Authentication options
    auth_method: Literal["none", "api_key", "basic", "oauth2", "bearer"] = Field(
        default="none",
        description="Authentication method to use",
        json_schema_extra={"ui:widget": "select"},
    )
    auth_params: Dict[str, str] = Field(
        default_factory=dict,
        description="Parameters for authentication",
        json_schema_extra={"ui:widget": "json"},
    )

    # Chained requests configuration
    chained_endpoints: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Additional API endpoints to query using data from initial response",
        json_schema_extra={"ui:widget": "array"},
    )

    @model_validator(mode="after")
    def check_response_mapping(self):
        """Validate that response mapping is properly formatted"""
        if self.profile in {
            "gbif_rich",
            "tropicos_rich",
            "col_rich",
            "bhl_references",
            "inaturalist_rich",
        }:
            return self
        if not self.response_mapping:
            raise ValueError("response_mapping cannot be empty")
        return self

    @model_validator(mode="after")
    def check_auth_config(self):
        """Validate authentication configuration"""
        if self.auth_method == "api_key":
            # Verify API key is provided
            if "key" not in self.auth_params:
                raise ValueError("api_key authentication requires 'key' in auth_params")
            # Verify we know where to put the API key
            if "location" not in self.auth_params:
                raise ValueError(
                    "api_key authentication requires 'location' in auth_params (header, query, or cookie)"
                )
            # If in header, verify header name
            if (
                self.auth_params.get("location") == "header"
                and "name" not in self.auth_params
            ):
                raise ValueError("api_key in header requires 'name' in auth_params")

        elif self.auth_method == "basic":
            # Verify username and password
            if "username" not in self.auth_params or "password" not in self.auth_params:
                raise ValueError(
                    "basic authentication requires 'username' and 'password' in auth_params"
                )

        elif self.auth_method == "oauth2":
            # Verify token or parameters to get one
            if "token" not in self.auth_params and "token_url" not in self.auth_params:
                raise ValueError(
                    "oauth2 authentication requires either 'token' or 'token_url' in auth_params"
                )

            # If using token_url, verify client credentials
            if "token_url" in self.auth_params and (
                "client_id" not in self.auth_params
                or "client_secret" not in self.auth_params
            ):
                raise ValueError(
                    "oauth2 with token_url requires 'client_id' and 'client_secret' in auth_params"
                )

        elif self.auth_method == "bearer":
            # Verify token is provided
            if "token" not in self.auth_params:
                raise ValueError(
                    "bearer authentication requires 'token' in auth_params"
                )

        return self

    @model_validator(mode="after")
    def check_chained_endpoints(self):
        """Validate chained endpoints configuration"""
        for idx, endpoint in enumerate(self.chained_endpoints):
            if "url_template" not in endpoint:
                raise ValueError(f"chained_endpoints[{idx}] must have 'url_template'")
            if "mapping" not in endpoint:
                raise ValueError(f"chained_endpoints[{idx}] must have 'mapping'")
        return self


class ApiTaxonomyEnricherConfig(PluginConfig):
    """Configuration for API taxonomy enricher plugin"""

    plugin: Literal["api_taxonomy_enricher"] = "api_taxonomy_enricher"
    params: ApiTaxonomyEnricherParams


@register("api_taxonomy_enricher", PluginType.LOADER)
class ApiTaxonomyEnricher(LoaderPlugin):
    """Plugin for enriching taxonomy data with information from external APIs"""

    config_model = ApiTaxonomyEnricherConfig
    _cache = {}  # Simple in-memory cache
    _oauth_tokens = {}  # Cache for OAuth tokens

    def __init__(self, db=None, registry=None):
        super().__init__(db, registry)
        self.log_messages = []  # Liste pour stocker les messages de log

    def validate_config(self, config: Dict[str, Any]) -> ApiTaxonomyEnricherConfig:
        """Validate plugin configuration."""
        # Extract params if they exist in the config
        if "params" not in config:
            # For backward compatibility, build params from top-level fields
            params = {k: v for k, v in config.items() if k != "plugin"}
            config = {"plugin": "api_taxonomy_enricher", "params": params}
        return self.config_model(**config)

    def load_data(
        self, taxon_data: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich taxonomy data with information from an API.

        Args:
            taxon_data: Dictionary containing taxon data
            config: Configuration for the API enrichment

        Returns:
            Dictionary containing the enriched taxon data
        """
        validated_config = self.validate_config(config)
        params = validated_config.params

        # Extract query value from taxon data
        query_field = params.query_field
        query_value = taxon_data.get(query_field)

        if not query_value:
            logger.debug(f"No query value found for field {query_field} in taxon data")
            # Don't add visible log message - this is expected for some taxa
            return taxon_data

        # Check cache if enabled
        cache_key = (
            f"{params.profile or 'default'}::{params.api_url}::{params.taxonomy_source or ''}"
            f"::{params.dataset_key}"
            f"::{params.use_name_verifier}"
            f"::{'|'.join(params.name_verifier_preferred_sources)}"
            f"::{params.name_verifier_threshold if params.name_verifier_threshold is not None else ''}"
            f"::{params.include_taxonomy}::{params.include_occurrences}::{params.include_media}"
            f"::{params.include_places}"
            f"::{params.include_references}::{params.include_vernaculars}"
            f"::{params.include_distributions}::{params.media_limit}::{params.observation_limit}"
            f"::{params.reference_limit}"
            f"::{params.include_publication_details}::{params.include_page_preview}"
            f"::{params.title_limit}::{params.page_limit}"
            f"::{query_value}"
        )
        if params.cache_results and cache_key in self._cache:
            logger.debug(f"Using cached data for {query_value}")
            self.log_messages.append(
                f"[blue]Using cached data for {query_value}[/blue]"
            )
            cached_payload = self._cache[cache_key]
            result = taxon_data.copy()
            if isinstance(cached_payload, dict) and (
                "mapped" in cached_payload
                or "raw" in cached_payload
                or "processed" in cached_payload
            ):
                result["api_enrichment"] = cached_payload.get("mapped", {})
                if "raw" in cached_payload:
                    result["api_response_raw"] = cached_payload.get("raw")
                if "processed" in cached_payload:
                    result["api_response_processed"] = cached_payload.get("processed")
            else:
                # Backward compatibility with legacy cache format.
                result["api_enrichment"] = (
                    cached_payload if isinstance(cached_payload, dict) else {}
                )
            return result

        # Prepare API request
        url = params.api_url
        api_params = params.query_params.copy()
        # Use configured query parameter name
        api_params[params.query_param_name] = query_value

        # Prepare headers
        headers = {}
        cookies = {}

        # Setup authentication
        auth = None

        try:
            resolved_query_value = str(query_value)
            name_resolution_summary: Dict[str, Any] = {}
            name_resolution_raw: Dict[str, Any] | None = None

            if params.profile in {"gbif_rich", "tropicos_rich", "col_rich"} and (
                params.use_name_verifier
            ):
                (
                    resolved_query_value,
                    name_resolution_summary,
                    name_resolution_raw,
                ) = self._resolve_name_with_verifier(str(query_value), params)

            if params.profile == "gbif_rich":
                result = self._load_gbif_rich_data(
                    taxon_data=taxon_data,
                    query_value=resolved_query_value,
                    submitted_query_value=str(query_value),
                    params=params,
                    name_resolution=name_resolution_summary,
                    name_resolution_raw=name_resolution_raw,
                )
                if params.cache_results and result.get("api_enrichment"):
                    self._cache[cache_key] = {
                        "mapped": result.get("api_enrichment", {}),
                        "processed": result.get("api_response_processed"),
                        "raw": result.get("api_response_raw"),
                    }
                return result

            if params.profile == "tropicos_rich":
                result = self._load_tropicos_rich_data(
                    taxon_data=taxon_data,
                    query_value=resolved_query_value,
                    submitted_query_value=str(query_value),
                    params=params,
                    name_resolution=name_resolution_summary,
                    name_resolution_raw=name_resolution_raw,
                )
                if params.cache_results and result.get("api_enrichment"):
                    self._cache[cache_key] = {
                        "mapped": result.get("api_enrichment", {}),
                        "processed": result.get("api_response_processed"),
                        "raw": result.get("api_response_raw"),
                    }
                return result

            if params.profile == "col_rich":
                result = self._load_col_rich_data(
                    taxon_data=taxon_data,
                    query_value=resolved_query_value,
                    submitted_query_value=str(query_value),
                    params=params,
                    name_resolution=name_resolution_summary,
                    name_resolution_raw=name_resolution_raw,
                )
                if params.cache_results and result.get("api_enrichment"):
                    self._cache[cache_key] = {
                        "mapped": result.get("api_enrichment", {}),
                        "processed": result.get("api_response_processed"),
                        "raw": result.get("api_response_raw"),
                    }
                return result

            if params.profile == "bhl_references":
                result = self._load_bhl_references_data(
                    taxon_data=taxon_data,
                    query_value=resolved_query_value,
                    submitted_query_value=str(query_value),
                    params=params,
                )
                if params.cache_results and result.get("api_enrichment"):
                    self._cache[cache_key] = {
                        "mapped": result.get("api_enrichment", {}),
                        "processed": result.get("api_response_processed"),
                        "raw": result.get("api_response_raw"),
                    }
                return result

            if params.profile == "inaturalist_rich":
                result = self._load_inaturalist_rich_data(
                    taxon_data=taxon_data,
                    query_value=resolved_query_value,
                    submitted_query_value=str(query_value),
                    params=params,
                )
                if params.cache_results and result.get("api_enrichment"):
                    self._cache[cache_key] = {
                        "mapped": result.get("api_enrichment", {}),
                        "processed": result.get("api_response_processed"),
                        "raw": result.get("api_response_raw"),
                    }
                return result

            # Apply appropriate authentication
            if params.auth_method == "api_key":
                self._setup_api_key_auth(
                    params.auth_params, headers, api_params, cookies
                )

            elif params.auth_method == "basic":
                auth = (
                    self._get_secure_value(params.auth_params.get("username", "")),
                    self._get_secure_value(params.auth_params.get("password", "")),
                )

            elif params.auth_method == "bearer":
                headers["Authorization"] = (
                    f"Bearer {self._get_secure_value(params.auth_params.get('token', ''))}"
                )

            elif params.auth_method == "oauth2":
                self._setup_oauth2_auth(params.auth_params, headers)

            # Make API request with authentication
            logger.debug(f"Requesting API data for {query_value} from {url}")
            # Ne pas ajouter de message pour la récupération, seulement pour le succès final

            # Use session if we have cookies
            if cookies:
                session = requests.Session()
                session.cookies.update(cookies)
                response = session.get(
                    url, params=api_params, headers=headers, auth=auth
                )
            else:
                response = requests.get(
                    url, params=api_params, headers=headers, auth=auth
                )

            response.raise_for_status()
            data = response.json()

            # Process the response
            api_data = self._process_api_response(data)
            logger.debug(f"Processed API data: {api_data}")

            # Create enriched data dictionary to collect all mappings
            enriched_data = {}

            # First apply initial response mapping
            if api_data and params.response_mapping:
                for (
                    target_field,
                    source_field,
                ) in params.response_mapping.items():
                    value = self._extract_nested_value(api_data, source_field)
                    if value is not None:
                        enriched_data[target_field] = value

                # Process chained endpoints if configured
                if params.chained_endpoints:
                    # Use enriched_data for placeholders (it has the mapped fields like tropicos_id)
                    enriched_data = self._process_chained_requests(
                        enriched_data,  # Use mapped data for placeholders
                        params.chained_endpoints,
                        params,
                        headers,
                        cookies,
                        auth,
                    )
                    logger.debug(
                        f"Enriched data after chaining: {list(enriched_data.keys())}"
                    )

            # Cache results if enabled
            if params.cache_results and enriched_data:
                self._cache[cache_key] = {
                    "mapped": enriched_data,
                    "processed": api_data,
                    "raw": data,
                }

            # Log success message
            self.log_messages.append(
                f"[green][{emoji('✓', '[OK]')}] Data successfully retrieved for {query_value}[/green]"
            )

            # Return taxon data with enrichment and raw payload for preview/debugging
            result = taxon_data.copy()
            result["api_enrichment"] = enriched_data
            result["api_response_processed"] = api_data
            result["api_response_raw"] = data
            return result

        except requests.RequestException as e:
            error_msg = f"API request failed for {query_value}: {str(e)}"
            logger.error(error_msg)
            self.log_messages.append(
                f"[bold red]{emoji('✗', '[X]')} API request failed for {query_value}: {str(e)}[/bold red]"
            )
            return taxon_data
        except Exception as e:
            error_msg = f"Failed to process API data for {query_value}: {str(e)}"
            logger.error(error_msg)
            self.log_messages.append(
                f"[bold red]{emoji('✗', '[X]')} Failed to process API data for {query_value}: {str(e)}[/bold red]"
            )
            return taxon_data
        finally:
            # Respect rate limit regardless of outcome
            if params.rate_limit > 0:
                time.sleep(1.0 / params.rate_limit)
            else:
                # Avoid division by zero if rate_limit is 0 or negative
                pass

    def _setup_api_key_auth(
        self,
        auth_params: Dict[str, str],
        headers: Dict[str, str],
        api_params: Dict[str, str],
        cookies: Dict[str, str],
    ) -> None:
        """
        Setup API key authentication based on configuration

        Args:
            auth_params: Authentication parameters
            headers: Headers dictionary to modify
            api_params: Query parameters dictionary to modify
            cookies: Cookies dictionary to modify
        """
        api_key = self._get_secure_value(auth_params.get("key", ""))
        location = auth_params.get("location", "header").lower()

        if location == "header":
            header_name = auth_params.get("name", "X-API-Key")
            headers[header_name] = api_key
        elif location == "query":
            param_name = auth_params.get("name", "api_key")
            api_params[param_name] = api_key
        elif location == "cookie":
            cookie_name = auth_params.get("name", "api_key")
            cookies[cookie_name] = api_key
        else:
            logger.error(
                "Unknown api_key location '%s'; expected 'header', 'query' or 'cookie'",
                location,
            )
            raise ValueError(f"Invalid api_key location '{location}'")

    def _setup_oauth2_auth(
        self, auth_params: Dict[str, str], headers: Dict[str, str]
    ) -> None:
        """
        Setup OAuth2 authentication, getting a token if needed

        Args:
            auth_params: Authentication parameters
            headers: Headers dictionary to modify
        """
        # If token is directly provided
        if "token" in auth_params:
            token = self._get_secure_value(auth_params.get("token", ""))
            headers["Authorization"] = f"Bearer {token}"
            return

        # If we need to get a token from token endpoint
        token_url = auth_params.get("token_url")
        if not token_url:
            return

        # Check if we already have a valid token
        client_id = self._get_secure_value(auth_params.get("client_id", ""))
        scope = auth_params.get("scope", "")
        cache_key = f"{token_url}_{client_id}_{scope}"
        cached_token_info = self._oauth_tokens.get(cache_key)

        if cached_token_info and cached_token_info.get("expires_at", 0) > time.time():
            headers["Authorization"] = f"Bearer {cached_token_info.get('token')}"
            return

        # Get new token
        try:
            client_secret = self._get_secure_value(auth_params.get("client_secret", ""))
            grant_type = auth_params.get("grant_type", "client_credentials")

            # Prepare token request
            token_data = {
                "grant_type": grant_type,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            if scope:
                token_data["scope"] = scope

            # Make token request
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()

            # Parse response
            token_response = response.json()
            access_token = token_response.get("access_token")

            if not access_token:
                logger.error("No access_token in OAuth2 response")
                return

            # Calculate expiration time
            expires_in = token_response.get("expires_in", 3600)
            expires_at = time.time() + expires_in - 60

            # Store token
            self._oauth_tokens[cache_key] = {
                "token": access_token,
                "expires_at": expires_at,
            }

            # Add token to headers
            headers["Authorization"] = f"Bearer {access_token}"

        except Exception as e:
            logger.error(f"Failed to get OAuth2 token: {str(e)}")

    def _load_gbif_rich_data(
        self,
        taxon_data: Dict[str, Any],
        query_value: str,
        submitted_query_value: str,
        params: ApiTaxonomyEnricherParams,
        name_resolution: Optional[Dict[str, Any]] = None,
        name_resolution_raw: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Load a structured GBIF enrichment summary."""

        summary: Dict[str, Any] = {
            "name_resolution": name_resolution or {},
            "match": {},
            "taxonomy": {},
            "occurrence_summary": {},
            "media_summary": {},
            "links": {},
            "block_status": {
                "match": "pending",
                "taxonomy": "disabled" if not params.include_taxonomy else "pending",
                "occurrence_summary": (
                    "disabled" if not params.include_occurrences else "pending"
                ),
                "media_summary": "disabled" if not params.include_media else "pending",
            },
            "block_errors": {},
            "provenance": {
                "profile": "gbif_rich",
                "profile_version": "gbif-rich-v1",
                "taxonomy_source": self._gbif_taxonomy_source_label(params),
                "query": query_value,
                "query_submitted": submitted_query_value,
                "query_used": query_value,
                "endpoints": [],
            },
        }
        raw_payload: Dict[str, Any] = (
            {"name_resolution": name_resolution_raw}
            if name_resolution_raw is not None
            else {}
        )
        processed_payload: Dict[str, Any] = (
            {"name_resolution": name_resolution} if name_resolution else {}
        )

        match_summary, match_raw = self._gbif_match(query_value, params)
        raw_payload["match"] = match_raw
        processed_payload["match"] = match_summary
        summary["match"] = match_summary
        summary["provenance"]["endpoints"].append("v2/species/match")

        usage_key = match_summary.get("usage_key")
        if not usage_key:
            summary["block_status"]["match"] = "no_match"
            summary["provenance"]["outcome"] = "no_match"
            self.log_messages.append(
                f"[yellow]No GBIF match found for {query_value}[/yellow]"
            )
            return {
                **taxon_data,
                "api_enrichment": summary,
                "api_response_processed": processed_payload,
                "api_response_raw": raw_payload,
            }

        summary["block_status"]["match"] = "complete"
        summary["links"] = self._gbif_build_links(str(usage_key))

        if params.include_taxonomy:
            try:
                taxonomy_summary, taxonomy_raw = self._gbif_taxonomy(str(usage_key))
                summary["taxonomy"] = taxonomy_summary
                summary["block_status"]["taxonomy"] = "complete"
                raw_payload["taxonomy"] = taxonomy_raw
                processed_payload["taxonomy"] = taxonomy_summary
                summary["provenance"]["endpoints"].extend(
                    [
                        "v1/species/{usageKey}",
                        "v1/species/{usageKey}/vernacularNames",
                        "v1/species/{usageKey}/synonyms",
                        "v1/species/{usageKey}/iucnRedListCategory",
                    ]
                )
            except Exception as exc:
                summary["block_status"]["taxonomy"] = "error"
                summary["block_errors"]["taxonomy"] = str(exc)

        if params.include_occurrences:
            try:
                occurrence_summary, occurrence_raw = self._gbif_occurrence_summary(
                    str(usage_key)
                )
                summary["occurrence_summary"] = occurrence_summary
                summary["block_status"]["occurrence_summary"] = "complete"
                raw_payload["occurrence_summary"] = occurrence_raw
                processed_payload["occurrence_summary"] = occurrence_summary
                summary["provenance"]["endpoints"].append("v1/occurrence/search")
            except Exception as exc:
                summary["block_status"]["occurrence_summary"] = "error"
                summary["block_errors"]["occurrence_summary"] = str(exc)

        if params.include_media:
            try:
                media_summary, media_raw = self._gbif_media_summary(
                    str(usage_key), params.media_limit
                )
                summary["media_summary"] = media_summary
                summary["block_status"]["media_summary"] = "complete"
                raw_payload["media_summary"] = media_raw
                processed_payload["media_summary"] = media_summary
                summary["provenance"]["endpoints"].append("v1/species/{usageKey}/media")
            except Exception as exc:
                summary["block_status"]["media_summary"] = "error"
                summary["block_errors"]["media_summary"] = str(exc)

        summary["provenance"]["outcome"] = (
            "partial" if summary["block_errors"] else "complete"
        )
        self.log_messages.append(
            f"[green][{emoji('✓', '[OK]')}] GBIF data successfully retrieved for {query_value}[/green]"
        )

        return {
            **taxon_data,
            "api_enrichment": summary,
            "api_response_processed": processed_payload,
            "api_response_raw": raw_payload,
        }

    def _load_tropicos_rich_data(
        self,
        taxon_data: Dict[str, Any],
        query_value: str,
        submitted_query_value: str,
        params: ApiTaxonomyEnricherParams,
        name_resolution: Optional[Dict[str, Any]] = None,
        name_resolution_raw: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Load a structured Tropicos enrichment summary."""

        summary: Dict[str, Any] = {
            "name_resolution": name_resolution or {},
            "match": {},
            "nomenclature": {},
            "taxonomy": {},
            "references": {},
            "distribution_summary": {},
            "media_summary": {},
            "links": {},
            "block_status": {
                "match": "pending",
                "nomenclature": "pending",
                "taxonomy": "pending",
                "references": (
                    "disabled" if not params.include_references else "pending"
                ),
                "distribution_summary": (
                    "disabled" if not params.include_distributions else "pending"
                ),
                "media_summary": "disabled" if not params.include_media else "pending",
            },
            "block_errors": {},
            "provenance": {
                "profile": "tropicos_rich",
                "profile_version": "tropicos-rich-v1",
                "query": query_value,
                "query_submitted": submitted_query_value,
                "query_used": query_value,
                "endpoints": [],
            },
        }
        raw_payload: Dict[str, Any] = (
            {"name_resolution": name_resolution_raw}
            if name_resolution_raw is not None
            else {}
        )
        processed_payload: Dict[str, Any] = (
            {"name_resolution": name_resolution} if name_resolution else {}
        )

        match_summary, match_raw = self._tropicos_match(query_value, params)
        raw_payload["match"] = match_raw
        processed_payload["match"] = match_summary
        summary["match"] = match_summary
        summary["provenance"]["endpoints"].append("Name/Search")

        name_id = match_summary.get("name_id")
        if not name_id:
            summary["block_status"]["match"] = "no_match"
            summary["provenance"]["outcome"] = "no_match"
            self.log_messages.append(
                f"[yellow]No Tropicos match found for {query_value}[/yellow]"
            )
            return {
                **taxon_data,
                "api_enrichment": summary,
                "api_response_processed": processed_payload,
                "api_response_raw": raw_payload,
            }

        summary["block_status"]["match"] = "complete"
        summary["links"] = self._tropicos_build_links(str(name_id))

        summary_data, summary_raw = self._tropicos_summary(str(name_id), params)
        raw_payload["summary"] = summary_raw
        processed_payload["summary"] = summary_data
        summary["provenance"]["endpoints"].append("Name/{id}")

        try:
            nomenclature_summary, nomenclature_raw = self._tropicos_nomenclature(
                str(name_id), summary_data, params
            )
            summary["nomenclature"] = nomenclature_summary
            summary["block_status"]["nomenclature"] = "complete"
            raw_payload["nomenclature"] = nomenclature_raw
            processed_payload["nomenclature"] = nomenclature_summary
            summary["provenance"]["endpoints"].extend(
                ["Name/{id}/AcceptedNames", "Name/{id}/Synonyms"]
            )
        except Exception as exc:
            summary["block_status"]["nomenclature"] = "error"
            summary["block_errors"]["nomenclature"] = str(exc)

        try:
            taxonomy_summary, taxonomy_raw = self._tropicos_taxonomy(
                str(name_id), summary_data, params
            )
            summary["taxonomy"] = taxonomy_summary
            summary["block_status"]["taxonomy"] = "complete"
            raw_payload["taxonomy"] = taxonomy_raw
            processed_payload["taxonomy"] = taxonomy_summary
            summary["provenance"]["endpoints"].append("Name/{id}/HigherTaxa")
        except Exception as exc:
            summary["taxonomy"] = {
                "family": summary_data.get("family"),
                "higher_taxa": [],
            }
            summary["block_status"]["taxonomy"] = "error"
            summary["block_errors"]["taxonomy"] = str(exc)

        if params.include_references:
            try:
                references_summary, references_raw = self._tropicos_references(
                    str(name_id), params
                )
                summary["references"] = references_summary
                summary["block_status"]["references"] = "complete"
                raw_payload["references"] = references_raw
                processed_payload["references"] = references_summary
                summary["provenance"]["endpoints"].append("Name/{id}/References")
            except Exception as exc:
                summary["block_status"]["references"] = "error"
                summary["block_errors"]["references"] = str(exc)

        if params.include_distributions:
            try:
                distribution_summary, distribution_raw = (
                    self._tropicos_distribution_summary(str(name_id), params)
                )
                summary["distribution_summary"] = distribution_summary
                summary["block_status"]["distribution_summary"] = "complete"
                raw_payload["distribution_summary"] = distribution_raw
                processed_payload["distribution_summary"] = distribution_summary
                summary["provenance"]["endpoints"].append("Name/{id}/Distributions")
            except Exception as exc:
                summary["block_status"]["distribution_summary"] = "error"
                summary["block_errors"]["distribution_summary"] = str(exc)

        if params.include_media:
            try:
                media_summary, media_raw = self._tropicos_media_summary(
                    str(name_id), params.media_limit, params
                )
                summary["media_summary"] = media_summary
                summary["block_status"]["media_summary"] = "complete"
                raw_payload["media_summary"] = media_raw
                processed_payload["media_summary"] = media_summary
                summary["provenance"]["endpoints"].append("Name/{id}/Images")
            except Exception as exc:
                summary["block_status"]["media_summary"] = "error"
                summary["block_errors"]["media_summary"] = str(exc)

        summary["provenance"]["outcome"] = (
            "partial" if summary["block_errors"] else "complete"
        )
        self.log_messages.append(
            f"[green][{emoji('✓', '[OK]')}] Tropicos data successfully retrieved for {query_value}[/green]"
        )

        return {
            **taxon_data,
            "api_enrichment": summary,
            "api_response_processed": processed_payload,
            "api_response_raw": raw_payload,
        }

    def _load_col_rich_data(
        self,
        taxon_data: Dict[str, Any],
        query_value: str,
        submitted_query_value: str,
        params: ApiTaxonomyEnricherParams,
        name_resolution: Optional[Dict[str, Any]] = None,
        name_resolution_raw: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Load a structured Catalogue of Life enrichment summary."""

        dataset_key = self._col_dataset_key(params)
        summary: Dict[str, Any] = {
            "name_resolution": name_resolution or {},
            "match": {},
            "taxonomy": {},
            "nomenclature": {},
            "vernaculars": {},
            "distribution_summary": {},
            "references": {},
            "links": {},
            "block_status": {
                "match": "pending",
                "taxonomy": "disabled" if not params.include_taxonomy else "pending",
                "nomenclature": "pending",
                "vernaculars": (
                    "disabled" if not params.include_vernaculars else "pending"
                ),
                "distribution_summary": (
                    "disabled" if not params.include_distributions else "pending"
                ),
                "references": (
                    "disabled" if not params.include_references else "pending"
                ),
            },
            "block_errors": {},
            "provenance": {
                "profile": "col_rich",
                "profile_version": "col-rich-v1",
                "dataset_key": dataset_key,
                "query": query_value,
                "query_submitted": submitted_query_value,
                "query_used": query_value,
                "endpoints": ["dataset/{key}/nameusage/search"],
            },
        }
        raw_payload: Dict[str, Any] = (
            {"name_resolution": name_resolution_raw}
            if name_resolution_raw is not None
            else {}
        )
        processed_payload: Dict[str, Any] = (
            {"name_resolution": name_resolution} if name_resolution else {}
        )

        try:
            dataset_raw = self._col_dataset_metadata(dataset_key)
            raw_payload["dataset"] = dataset_raw
            summary["provenance"]["release_label"] = self._col_release_label(
                dataset_raw, dataset_key
            )
        except Exception as exc:
            summary["provenance"]["release_label"] = f"dataset:{dataset_key}"
            summary["block_errors"]["dataset"] = str(exc)

        match_summary, match_raw = self._col_match(query_value, dataset_key)
        raw_payload["search"] = match_raw
        processed_payload["match"] = match_summary
        summary["match"] = match_summary

        taxon_id = match_summary.get("taxon_id")
        if not taxon_id:
            summary["block_status"]["match"] = "no_match"
            summary["provenance"]["outcome"] = "no_match"
            self.log_messages.append(
                f"[yellow]No Catalogue of Life match found for {query_value}[/yellow]"
            )
            return {
                **taxon_data,
                "api_enrichment": summary,
                "api_response_processed": processed_payload,
                "api_response_raw": raw_payload,
            }

        summary["block_status"]["match"] = "complete"

        try:
            taxon_summary, taxon_raw = self._col_taxon_detail(
                dataset_key, str(taxon_id)
            )
            summary["match"] = {**summary["match"], **taxon_summary}
            summary["links"] = self._col_build_links(
                dataset_key, str(taxon_id), taxon_raw
            )
            raw_payload["taxon"] = taxon_raw
            processed_payload["match"] = summary["match"]
            summary["provenance"]["endpoints"].append("dataset/{key}/taxon/{id}")
        except Exception as exc:
            summary["block_errors"]["match"] = str(exc)
            summary["provenance"]["outcome"] = "partial"
            return {
                **taxon_data,
                "api_enrichment": summary,
                "api_response_processed": processed_payload,
                "api_response_raw": raw_payload,
            }

        if params.include_taxonomy:
            try:
                taxonomy_summary, taxonomy_raw = self._col_taxonomy(
                    dataset_key,
                    str(taxon_id),
                    summary["match"].get("scientific_name") or query_value,
                )
                summary["taxonomy"] = taxonomy_summary
                summary["block_status"]["taxonomy"] = "complete"
                raw_payload["classification"] = taxonomy_raw
                processed_payload["taxonomy"] = taxonomy_summary
                summary["provenance"]["endpoints"].append(
                    "dataset/{key}/taxon/{id}/classification"
                )
            except Exception as exc:
                summary["block_status"]["taxonomy"] = "error"
                summary["block_errors"]["taxonomy"] = str(exc)

        try:
            nomenclature_summary, nomenclature_raw = self._col_nomenclature(
                dataset_key,
                str(taxon_id),
                summary["match"],
            )
            summary["nomenclature"] = nomenclature_summary
            summary["block_status"]["nomenclature"] = "complete"
            raw_payload["synonyms"] = nomenclature_raw
            processed_payload["nomenclature"] = nomenclature_summary
            summary["provenance"]["endpoints"].append(
                "dataset/{key}/taxon/{id}/synonyms"
            )
        except Exception as exc:
            summary["block_status"]["nomenclature"] = "error"
            summary["block_errors"]["nomenclature"] = str(exc)

        vernacular_items: List[Dict[str, Any]] = []
        if params.include_vernaculars:
            try:
                vernacular_summary, vernacular_raw, vernacular_items = (
                    self._col_vernaculars(dataset_key, str(taxon_id))
                )
                summary["vernaculars"] = vernacular_summary
                summary["block_status"]["vernaculars"] = "complete"
                raw_payload["vernaculars"] = vernacular_raw
                processed_payload["vernaculars"] = vernacular_summary
                summary["provenance"]["endpoints"].append(
                    "dataset/{key}/taxon/{id}/vernacular"
                )
            except Exception as exc:
                summary["block_status"]["vernaculars"] = "error"
                summary["block_errors"]["vernaculars"] = str(exc)

        if params.include_distributions:
            try:
                distribution_summary, distribution_raw = self._col_distribution_summary(
                    dataset_key, str(taxon_id)
                )
                summary["distribution_summary"] = distribution_summary
                summary["block_status"]["distribution_summary"] = "complete"
                raw_payload["distributions"] = distribution_raw
                processed_payload["distribution_summary"] = distribution_summary
                summary["provenance"]["endpoints"].append(
                    "dataset/{key}/taxon/{id}/distribution"
                )
            except Exception as exc:
                summary["block_status"]["distribution_summary"] = "error"
                summary["block_errors"]["distribution_summary"] = str(exc)

        if params.include_references:
            try:
                references_summary, references_raw = self._col_references(
                    dataset_key=dataset_key,
                    taxon_raw=raw_payload.get("taxon", {}),
                    nomenclature_raw=raw_payload.get("synonyms", {}),
                    vernacular_items=vernacular_items,
                    reference_limit=params.reference_limit,
                )
                summary["references"] = references_summary
                summary["block_status"]["references"] = "complete"
                raw_payload["references"] = references_raw
                processed_payload["references"] = references_summary
                summary["provenance"]["endpoints"].append(
                    "dataset/{key}/reference/{id}"
                )
            except Exception as exc:
                summary["block_status"]["references"] = "error"
                summary["block_errors"]["references"] = str(exc)

        summary["provenance"]["outcome"] = (
            "partial" if summary["block_errors"] else "complete"
        )
        self.log_messages.append(
            f"[green][{emoji('✓', '[OK]')}] Catalogue of Life data successfully retrieved for {query_value}[/green]"
        )

        return {
            **taxon_data,
            "api_enrichment": summary,
            "api_response_processed": processed_payload,
            "api_response_raw": raw_payload,
        }

    def _load_bhl_references_data(
        self,
        taxon_data: Dict[str, Any],
        query_value: str,
        submitted_query_value: str,
        params: ApiTaxonomyEnricherParams,
    ) -> Dict[str, Any]:
        """Load a structured BHL references summary."""

        summary: Dict[str, Any] = {
            "match": {},
            "title_summary": {},
            "publications": {},
            "name_mentions": {},
            "page_links": {},
            "references_count": {},
            "links": {},
            "block_status": {
                "match": "pending",
                "title_summary": "pending",
                "name_mentions": "pending",
                "publications": (
                    "disabled" if not params.include_publication_details else "pending"
                ),
                "page_links": (
                    "disabled" if not params.include_page_preview else "pending"
                ),
            },
            "block_errors": {},
            "provenance": {
                "profile": "bhl_references",
                "profile_version": "bhl-references-v1",
                "query": query_value,
                "query_submitted": submitted_query_value,
                "query_used": query_value,
                "endpoints": ["NameSearch", "GetNameMetadata"],
            },
        }
        raw_payload: Dict[str, Any] = {}
        processed_payload: Dict[str, Any] = {}

        match_summary, match_raw, matched_query = self._bhl_name_search(
            query_value, params
        )
        raw_payload["match"] = match_raw
        processed_payload["match"] = match_summary
        summary["match"] = match_summary
        summary["provenance"]["query_used"] = matched_query
        summary["links"] = self._bhl_build_links(
            match_summary.get("name_confirmed") or matched_query
        )

        (
            metadata_summary,
            metadata_raw,
            title_candidates,
            page_candidates,
        ) = self._bhl_name_metadata(matched_query, params)
        raw_payload["name_metadata"] = metadata_raw

        summary["match"] = {**summary["match"], **metadata_summary.get("match", {})}
        summary["title_summary"] = metadata_summary.get("title_summary", {})
        summary["name_mentions"] = metadata_summary.get("name_mentions", {})
        summary["references_count"] = metadata_summary.get("references_count", {})
        processed_payload["match"] = summary["match"]
        processed_payload["title_summary"] = summary["title_summary"]
        processed_payload["name_mentions"] = summary["name_mentions"]
        processed_payload["references_count"] = summary["references_count"]

        if (
            not summary["match"].get("name_confirmed")
            and not summary["references_count"].get("titles")
            and not summary["references_count"].get("pages")
        ):
            summary["block_status"]["match"] = "no_match"
            summary["block_status"]["title_summary"] = "no_match"
            summary["block_status"]["name_mentions"] = "no_match"
            summary["provenance"]["outcome"] = "no_match"
            self.log_messages.append(
                f"[yellow]No BHL references found for {query_value}[/yellow]"
            )
            return {
                **taxon_data,
                "api_enrichment": summary,
                "api_response_processed": processed_payload,
                "api_response_raw": raw_payload,
            }

        summary["block_status"]["match"] = "complete"
        summary["block_status"]["title_summary"] = "complete"
        summary["block_status"]["name_mentions"] = "complete"

        if params.include_publication_details:
            try:
                publications_summary, publications_raw = self._bhl_publications(
                    title_candidates, params
                )
                summary["publications"] = publications_summary
                summary["block_status"]["publications"] = "complete"
                processed_payload["publications"] = publications_summary
                raw_payload["publications"] = publications_raw
                summary["provenance"]["endpoints"].append("GetTitleMetadata")
            except Exception as exc:
                summary["block_status"]["publications"] = "error"
                summary["block_errors"]["publications"] = str(exc)

        if params.include_page_preview:
            try:
                page_links_summary, page_links_raw = self._bhl_page_links(
                    page_candidates, params
                )
                summary["page_links"] = page_links_summary
                summary["block_status"]["page_links"] = "complete"
                processed_payload["page_links"] = page_links_summary
                raw_payload["page_links"] = page_links_raw
                summary["provenance"]["endpoints"].append("GetPageMetadata")
            except Exception as exc:
                summary["block_status"]["page_links"] = "error"
                summary["block_errors"]["page_links"] = str(exc)

        summary["provenance"]["outcome"] = (
            "partial" if summary["block_errors"] else "complete"
        )
        self.log_messages.append(
            f"[green][{emoji('✓', '[OK]')}] BHL data successfully retrieved for {query_value}[/green]"
        )

        return {
            **taxon_data,
            "api_enrichment": summary,
            "api_response_processed": processed_payload,
            "api_response_raw": raw_payload,
        }

    def _load_inaturalist_rich_data(
        self,
        taxon_data: Dict[str, Any],
        query_value: str,
        submitted_query_value: str,
        params: ApiTaxonomyEnricherParams,
    ) -> Dict[str, Any]:
        """Load a structured iNaturalist enrichment summary."""

        summary: Dict[str, Any] = {
            "match": {},
            "taxon": {},
            "observation_summary": {},
            "media_summary": {},
            "places": {},
            "links": {},
            "block_status": {
                "match": "pending",
                "taxon": "pending",
                "observation_summary": (
                    "disabled" if not params.include_occurrences else "pending"
                ),
                "media_summary": "disabled" if not params.include_media else "pending",
                "places": "disabled" if not params.include_places else "pending",
            },
            "block_errors": {},
            "provenance": {
                "profile": "inaturalist_rich",
                "profile_version": "inaturalist-rich-v1",
                "query": query_value,
                "query_submitted": submitted_query_value,
                "query_used": query_value,
                "endpoints": ["/v1/taxa"],
            },
        }
        raw_payload: Dict[str, Any] = {}
        processed_payload: Dict[str, Any] = {}

        match_summary, match_raw, selected_taxon = self._inaturalist_match(
            query_value, params
        )
        raw_payload["match"] = match_raw
        processed_payload["match"] = match_summary
        summary["match"] = match_summary

        taxon_id = match_summary.get("taxon_id")
        if not taxon_id:
            summary["block_status"]["match"] = "no_match"
            summary["block_status"]["taxon"] = "no_match"
            summary["provenance"]["outcome"] = "no_match"
            self.log_messages.append(
                f"[yellow]No iNaturalist match found for {query_value}[/yellow]"
            )
            return {
                **taxon_data,
                "api_enrichment": summary,
                "api_response_processed": processed_payload,
                "api_response_raw": raw_payload,
            }

        summary["block_status"]["match"] = "complete"
        summary["taxon"] = self._inaturalist_taxon_summary(selected_taxon)
        summary["block_status"]["taxon"] = "complete"
        summary["links"] = self._inaturalist_build_links(str(taxon_id), selected_taxon)
        raw_payload["taxon"] = selected_taxon
        processed_payload["taxon"] = summary["taxon"]

        observation_items: List[Dict[str, Any]] = []
        observation_sample_raw: Dict[str, Any] | None = None
        observation_counts_raw: Dict[str, Any] | None = None
        needs_observations = (
            params.include_occurrences or params.include_media or params.include_places
        )

        if needs_observations:
            try:
                (
                    observation_summary,
                    observation_raw,
                    observation_items,
                    observation_counts_raw,
                ) = self._inaturalist_observation_summary(
                    str(taxon_id),
                    params.observation_limit,
                )
                observation_sample_raw = observation_raw
                raw_payload["observations"] = observation_raw
                raw_payload["observation_counts"] = observation_counts_raw
                summary["provenance"]["endpoints"].append("/v1/observations")

                if params.include_occurrences:
                    summary["observation_summary"] = observation_summary
                    summary["block_status"]["observation_summary"] = "complete"
                    processed_payload["observation_summary"] = observation_summary
            except Exception as exc:
                if params.include_occurrences:
                    summary["block_status"]["observation_summary"] = "error"
                    summary["block_errors"]["observation_summary"] = str(exc)
                if params.include_places:
                    summary["block_status"]["places"] = "error"
                    summary["block_errors"]["places"] = str(exc)

        if params.include_media:
            try:
                media_summary = self._inaturalist_media_summary(
                    selected_taxon,
                    observation_items,
                    params.media_limit,
                )
                summary["media_summary"] = media_summary
                summary["block_status"]["media_summary"] = "complete"
                processed_payload["media_summary"] = media_summary
                raw_payload["media_summary"] = {
                    "taxon": selected_taxon,
                    "observations": observation_sample_raw,
                }
            except Exception as exc:
                summary["block_status"]["media_summary"] = "error"
                summary["block_errors"]["media_summary"] = str(exc)

        if params.include_places and summary["block_status"]["places"] != "error":
            try:
                places_summary = self._inaturalist_places_summary(observation_items)
                summary["places"] = places_summary
                summary["block_status"]["places"] = "complete"
                processed_payload["places"] = places_summary
                raw_payload["places"] = observation_sample_raw
            except Exception as exc:
                summary["block_status"]["places"] = "error"
                summary["block_errors"]["places"] = str(exc)

        summary["provenance"]["outcome"] = (
            "partial" if summary["block_errors"] else "complete"
        )
        self.log_messages.append(
            f"[green][{emoji('✓', '[OK]')}] iNaturalist data successfully retrieved for {query_value}[/green]"
        )

        return {
            **taxon_data,
            "api_enrichment": summary,
            "api_response_processed": processed_payload,
            "api_response_raw": raw_payload,
        }

    def _tropicos_match(
        self, query_value: str, params: ApiTaxonomyEnricherParams
    ) -> tuple[Dict[str, Any], Any]:
        """Resolve a Tropicos match summary and raw payload."""

        query_params = dict(params.query_params or {})
        query_params[params.query_param_name or "name"] = query_value
        query_params.setdefault("format", "json")
        query_params.setdefault("type", "exact")

        raw = self._tropicos_request_json(
            params.api_url or TROPICOS_SEARCH_ENDPOINT,
            params=query_params,
            params_model=params,
        )
        candidates = self._normalize_list_payload(raw)
        selected = self._tropicos_select_match(candidates, query_value)

        summary = self._tropicos_extract_name_record(selected)
        summary["matched_name"] = (
            summary.get("scientific_name")
            or summary.get("scientific_name_with_authors")
            or query_value
        )
        summary["candidate_count"] = len(candidates)

        return summary, raw

    def _tropicos_summary(
        self, name_id: str, params: ApiTaxonomyEnricherParams
    ) -> tuple[Dict[str, Any], Any]:
        """Build a core Tropicos summary block for a name id."""

        raw = self._tropicos_request_json(
            f"{TROPICOS_NAME_ENDPOINT}/{name_id}",
            params={"format": "json"},
            params_model=params,
        )
        record = self._process_api_response(raw)
        summary = self._tropicos_extract_name_record(record)
        summary["display_reference"] = self._coerce_string(
            record.get("DisplayReference")
        )
        summary["display_date"] = self._coerce_string(record.get("DisplayDate"))
        summary["accepted_name_id"] = self._coerce_string(record.get("AcceptedNameId"))
        summary["accepted_name"] = self._coerce_string(record.get("AcceptedName"))
        summary["accepted_name_with_authors"] = self._coerce_string(
            record.get("AcceptedNameWithAuthors")
        )
        return summary, raw

    def _tropicos_nomenclature(
        self,
        name_id: str,
        summary_data: Dict[str, Any],
        params: ApiTaxonomyEnricherParams,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Build accepted-name and synonymy summary blocks for Tropicos."""

        accepted_raw = self._tropicos_request_json(
            f"{TROPICOS_NAME_ENDPOINT}/{name_id}/AcceptedNames",
            params={"format": "json"},
            params_model=params,
        )
        synonyms_raw = self._tropicos_request_json(
            f"{TROPICOS_NAME_ENDPOINT}/{name_id}/Synonyms",
            params={"format": "json"},
            params_model=params,
        )

        accepted_items = self._normalize_list_payload(accepted_raw)
        synonym_items = self._normalize_list_payload(synonyms_raw)

        accepted_record = self._tropicos_extract_name_record(
            accepted_items[0] if accepted_items else None
        )

        selected_synonyms = []
        for item in synonym_items[:5]:
            synonym_record = self._tropicos_extract_name_record(item)
            synonym_name = synonym_record.get(
                "scientific_name_with_authors"
            ) or synonym_record.get("scientific_name")
            if synonym_name and synonym_name not in selected_synonyms:
                selected_synonyms.append(synonym_name)

        return (
            {
                "accepted_name_id": (
                    accepted_record.get("name_id")
                    or summary_data.get("accepted_name_id")
                    or summary_data.get("name_id")
                ),
                "accepted_name": (
                    accepted_record.get("scientific_name")
                    or summary_data.get("accepted_name")
                    or summary_data.get("scientific_name")
                ),
                "accepted_name_with_authors": (
                    accepted_record.get("scientific_name_with_authors")
                    or summary_data.get("accepted_name_with_authors")
                    or summary_data.get("scientific_name_with_authors")
                ),
                "synonyms_count": len(synonym_items),
                "accepted_name_count": len(accepted_items),
                "selected_synonyms": selected_synonyms,
            },
            {
                "accepted_names": accepted_raw,
                "synonyms": synonyms_raw,
            },
        )

    def _tropicos_taxonomy(
        self,
        name_id: str,
        summary_data: Dict[str, Any],
        params: ApiTaxonomyEnricherParams,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Build taxonomy summary blocks for a Tropicos name id."""

        higher_taxa_raw = self._tropicos_request_json(
            f"{TROPICOS_NAME_ENDPOINT}/{name_id}/HigherTaxa",
            params={"format": "json"},
            params_model=params,
        )
        higher_taxa_items = self._normalize_list_payload(higher_taxa_raw)
        higher_taxa = []

        for item in higher_taxa_items:
            label = self._coerce_string(
                item.get("DisplayName")
                or item.get("ScientificNameWithAuthors")
                or item.get("ScientificName")
                or item.get("Name")
            )
            if label and label not in higher_taxa:
                higher_taxa.append(label)

        return (
            {
                "family": summary_data.get("family"),
                "higher_taxa": higher_taxa[:10],
            },
            {"higher_taxa": higher_taxa_raw},
        )

    def _tropicos_references(
        self, name_id: str, params: ApiTaxonomyEnricherParams
    ) -> tuple[Dict[str, Any], Any]:
        """Build a compact references summary for a Tropicos name id."""

        raw = self._tropicos_request_json(
            f"{TROPICOS_NAME_ENDPOINT}/{name_id}/References",
            params={"format": "json"},
            params_model=params,
        )
        items = self._normalize_list_payload(raw)
        selected_items = []

        for item in items[:5]:
            reference = item.get("Reference") if isinstance(item, dict) else None
            if not isinstance(reference, dict):
                reference = item
            selected_items.append(
                {
                    "title": self._coerce_string(reference.get("ArticleTitle")),
                    "abbreviated_title": self._coerce_string(
                        reference.get("AbbreviatedTitle")
                    ),
                    "year_published": self._coerce_string(
                        reference.get("YearPublished")
                    ),
                    "full_citation": self._coerce_string(reference.get("FullCitation")),
                }
            )

        return (
            {
                "references_count": len(items),
                "items": selected_items,
            },
            raw,
        )

    def _tropicos_distribution_summary(
        self, name_id: str, params: ApiTaxonomyEnricherParams
    ) -> tuple[Dict[str, Any], Any]:
        """Build a compact distribution summary for a Tropicos name id."""

        raw = self._tropicos_request_json(
            f"{TROPICOS_NAME_ENDPOINT}/{name_id}/Distributions",
            params={"format": "json"},
            params_model=params,
        )
        items = self._normalize_list_payload(raw)

        countries: List[str] = []
        regions: List[str] = []
        for item in items:
            location = item.get("Location") if isinstance(item, dict) else None
            if not isinstance(location, dict):
                location = item

            country = self._coerce_string(
                location.get("CountryName") or location.get("Country")
            )
            if country and country not in countries:
                countries.append(country)

            region = self._coerce_string(
                location.get("RegionName") or location.get("Region")
            )
            if region and region not in regions:
                regions.append(region)

        return (
            {
                "distribution_count": len(items),
                "countries": countries[:10],
                "regions": regions[:10],
            },
            raw,
        )

    def _tropicos_media_summary(
        self, name_id: str, media_limit: int, params: ApiTaxonomyEnricherParams
    ) -> tuple[Dict[str, Any], Any]:
        """Build a compact media summary for a Tropicos name id."""

        raw = self._tropicos_request_json(
            f"{TROPICOS_NAME_ENDPOINT}/{name_id}/Images",
            params={"format": "json"},
            params_model=params,
        )
        items = self._normalize_list_payload(raw)
        normalized_items = []

        for item in items[:media_limit]:
            if not isinstance(item, dict):
                continue
            normalized_items.append(
                {
                    "identifier": self._coerce_string(
                        item.get("ImageId") or item.get("NameId")
                    ),
                    "thumbnail_url": self._coerce_string(
                        item.get("ThumbnailUrl")
                        or item.get("ThumbnailURL")
                        or item.get("Thumbnail")
                        or item.get("SmallUrl")
                        or item.get("SmallURL")
                        or item.get("Url")
                        or item.get("URL")
                    ),
                    "source_url": self._coerce_string(
                        item.get("Url")
                        or item.get("URL")
                        or item.get("ImageUrl")
                        or item.get("ImageURL")
                        or item.get("DetailUrl")
                        or item.get("DetailURL")
                    ),
                    "caption": self._coerce_string(
                        item.get("Caption")
                        or item.get("Title")
                        or item.get("Description")
                        or item.get("ShortDescription")
                    ),
                    "creator": self._coerce_string(
                        item.get("Photographer")
                        or item.get("Creator")
                        or item.get("Credit")
                        or item.get("Copyright")
                    ),
                    "license": self._coerce_string(
                        item.get("LicenseName")
                        or item.get("License")
                        or item.get("LicenseUrl")
                    ),
                }
            )

        return (
            {
                "media_count": len(items),
                "items": normalized_items,
            },
            raw,
        )

    def _tropicos_request_json(
        self,
        url: str,
        params: Dict[str, Any],
        params_model: ApiTaxonomyEnricherParams,
    ) -> Dict[str, Any]:
        """Perform a Tropicos JSON request with query-key authentication."""

        request_params = dict(params or {})
        request_params.setdefault("format", "json")

        if params_model.auth_method == "api_key":
            auth_location = params_model.auth_params.get("location", "query").lower()
            if auth_location != "query":
                raise ValueError(
                    "tropicos_rich requires query-based api_key authentication"
                )
            auth_param_name = params_model.auth_params.get("name", "apikey")
            request_params[auth_param_name] = self._get_secure_value(
                params_model.auth_params.get("key", "")
            )

        return self._request_json(url, request_params)

    def _tropicos_select_match(
        self, candidates: List[Dict[str, Any]], query_value: str
    ) -> Dict[str, Any]:
        """Pick the best Tropicos search result for a query."""

        if not candidates:
            return {}

        normalized_query = self._normalize_taxon_text(query_value)

        def score(candidate: Dict[str, Any]) -> tuple[int, int, int, int]:
            scientific_name = self._normalize_taxon_text(
                candidate.get("ScientificName")
                or candidate.get("Name")
                or candidate.get("ScientificNameWithAuthors")
            )
            has_id = 1 if self._coerce_string(candidate.get("NameId")) else 0
            has_family = 1 if self._coerce_string(candidate.get("Family")) else 0
            has_status = (
                1 if self._coerce_string(candidate.get("NomenclatureStatusName")) else 0
            )
            exact_match = 1 if scientific_name == normalized_query else 0
            return (exact_match, has_id, has_family, has_status)

        return max(candidates, key=score)

    def _tropicos_extract_name_record(
        self, payload: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Normalize a Tropicos name record from a nested or flat payload."""

        if not isinstance(payload, dict):
            return {}

        record = payload
        for nested_key in ("AcceptedName", "SynonymName", "Name"):
            nested_value = payload.get(nested_key)
            if isinstance(nested_value, dict):
                record = nested_value
                break

        return {
            "name_id": self._coerce_string(
                record.get("NameId") or record.get("AcceptedNameId")
            ),
            "scientific_name": self._coerce_string(
                record.get("ScientificName")
                or record.get("AcceptedName")
                or record.get("DisplayName")
            ),
            "scientific_name_with_authors": self._coerce_string(
                record.get("ScientificNameWithAuthors")
                or record.get("AcceptedNameWithAuthors")
                or record.get("DisplayName")
            ),
            "family": self._coerce_string(record.get("Family")),
            "rank": self._coerce_string(
                record.get("RankAbbreviation") or record.get("Rank")
            ),
            "nomenclature_status": self._coerce_string(
                record.get("NomenclatureStatusName")
            ),
        }

    def _tropicos_build_links(self, name_id: str) -> Dict[str, str]:
        """Build public Tropicos links for a matched name."""

        return {
            "record": f"https://www.tropicos.org/name/{name_id}",
        }

    def _normalize_taxon_text(self, value: Any) -> str:
        """Normalize a taxon label for comparison."""

        text = self._coerce_string(value)
        return " ".join(text.lower().split())

    def _coerce_string(self, value: Any) -> str:
        """Return a clean string value or an empty string."""

        if value is None:
            return ""
        text = str(value).strip()
        return text

    def _resolve_name_with_verifier(
        self, query_value: str, params: ApiTaxonomyEnricherParams
    ) -> tuple[str, Dict[str, Any], Optional[Dict[str, Any]]]:
        """Resolve a cleaner query name with Global Names Verifier when enabled."""

        submitted_name = self._coerce_string(query_value)
        empty_summary = {
            "enabled": False,
            "status": "bypassed",
            "submitted_name": submitted_name,
            "parsed_name": submitted_name,
            "query_name": submitted_name,
            "matched_name": submitted_name,
            "best_result": submitted_name,
            "was_corrected": False,
            "alternatives": [],
        }

        if not params.use_name_verifier:
            return submitted_name, empty_summary, None

        preferred_source_id = self._name_verifier_source_id(params)
        request_params: Dict[str, Any] = {}
        if preferred_source_id is not None:
            request_params["data_sources"] = str(preferred_source_id)

        try:
            raw = self._request_json(
                f"{GN_VERIFIER_ENDPOINT}/{quote_plus(submitted_name)}",
                request_params or None,
            )
        except Exception as exc:
            summary = {
                **empty_summary,
                "enabled": True,
                "status": "bypassed",
                "error": str(exc),
            }
            return submitted_name, summary, {"error": str(exc)}

        names = raw.get("names") if isinstance(raw.get("names"), list) else []
        candidate = next((item for item in names if isinstance(item, dict)), {})
        best_result = (
            candidate.get("bestResult")
            if isinstance(candidate.get("bestResult"), dict)
            else {}
        )
        score = best_result.get("sortScore")
        score_value = float(score) if isinstance(score, (int, float)) else None
        resolved_query = self._coerce_string(
            best_result.get("currentCanonicalSimple")
            or best_result.get("matchedCanonicalSimple")
            or candidate.get("name")
        )
        matched_name = self._coerce_string(
            best_result.get("currentName")
            or best_result.get("matchedName")
            or resolved_query
        )
        best_label = self._coerce_string(
            best_result.get("currentCanonicalFull")
            or best_result.get("matchedCanonicalFull")
            or matched_name
            or resolved_query
        )

        if not resolved_query or (
            params.name_verifier_threshold is not None
            and (score_value is None or score_value < params.name_verifier_threshold)
        ):
            status = (
                "bypassed"
                if best_result
                and params.name_verifier_threshold is not None
                and (
                    score_value is None or score_value < params.name_verifier_threshold
                )
                else "no_match"
            )
            summary = {
                **empty_summary,
                "enabled": True,
                "status": status,
                "best_result": best_label or submitted_name,
                "matched_name": matched_name or submitted_name,
                "data_source_title": self._coerce_string(
                    best_result.get("dataSourceTitleShort")
                ),
                "data_source_id": best_result.get("dataSourceId"),
                "score": score_value,
                "match_type": self._coerce_string(
                    best_result.get("matchType") or candidate.get("matchType")
                ),
            }
            return submitted_name, summary, raw

        alternatives = []
        for alternative in (
            best_result.get("matchedCanonicalSimple"),
            best_result.get("currentCanonicalSimple"),
            best_result.get("matchedName"),
            best_result.get("currentName"),
        ):
            alternative_str = self._coerce_string(alternative)
            if alternative_str and alternative_str not in alternatives:
                alternatives.append(alternative_str)

        summary = {
            "enabled": True,
            "status": "resolved",
            "submitted_name": submitted_name,
            "parsed_name": self._coerce_string(candidate.get("name")) or submitted_name,
            "query_name": resolved_query,
            "matched_name": matched_name or resolved_query,
            "best_result": best_label or matched_name or resolved_query,
            "data_source_title": self._coerce_string(
                best_result.get("dataSourceTitleShort")
            ),
            "data_source_id": best_result.get("dataSourceId"),
            "score": score_value,
            "match_type": self._coerce_string(
                best_result.get("matchType") or candidate.get("matchType")
            ),
            "was_corrected": self._normalize_taxon_text(resolved_query)
            != self._normalize_taxon_text(submitted_name),
            "alternatives": alternatives[:5],
        }

        return resolved_query, summary, raw

    def _name_verifier_source_id(
        self, params: ApiTaxonomyEnricherParams
    ) -> Optional[int]:
        """Resolve the preferred Global Names data source id for a profile."""

        for source in params.name_verifier_preferred_sources:
            source_str = self._coerce_string(source)
            if not source_str:
                continue
            if source_str.isdigit():
                return int(source_str)
            normalized = self._normalize_taxon_text(source_str)
            if normalized in GN_SOURCE_ALIASES:
                return GN_SOURCE_ALIASES[normalized]

        profile = self._coerce_string(params.profile)
        if profile in GN_DEFAULT_SOURCE_IDS_BY_PROFILE:
            return GN_DEFAULT_SOURCE_IDS_BY_PROFILE[profile]

        return None

    def _gbif_match(
        self, query_value: str, params: ApiTaxonomyEnricherParams
    ) -> tuple[Dict[str, Any], Any]:
        """Resolve a GBIF match summary and raw payload."""

        query_params = dict(params.query_params or {})
        query_params[params.query_param_name or "scientificName"] = query_value
        query_params.setdefault("verbose", "true")

        checklist_key = self._gbif_checklist_key(params)
        if checklist_key and "checklistKey" not in query_params:
            query_params["checklistKey"] = checklist_key

        raw = self._request_json(params.api_url or GBIF_MATCH_ENDPOINT, query_params)
        usage_key = self._gbif_extract_usage_key(raw)

        return (
            {
                "usage_key": usage_key,
                "scientific_name": raw.get("scientificName")
                or raw.get("matchedScientificName")
                or query_value,
                "canonical_name": raw.get("canonicalName"),
                "rank": raw.get("rank"),
                "status": raw.get("status"),
                "confidence": raw.get("confidence"),
                "match_type": raw.get("matchType"),
                "taxonomy_source": self._gbif_taxonomy_source_label(params),
            },
            raw,
        )

    def _gbif_taxonomy(self, usage_key: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Build taxonomy summary blocks for a GBIF usage key."""

        detail = self._request_json(f"{GBIF_SPECIES_ENDPOINT}/{usage_key}")
        vernacular_raw = self._request_json(
            f"{GBIF_SPECIES_ENDPOINT}/{usage_key}/vernacularNames"
        )
        synonyms_raw = self._request_json(
            f"{GBIF_SPECIES_ENDPOINT}/{usage_key}/synonyms"
        )

        try:
            iucn_raw: Any = self._request_json(
                f"{GBIF_SPECIES_ENDPOINT}/{usage_key}/iucnRedListCategory"
            )
        except requests.RequestException:
            iucn_raw = None

        vernacular_items = self._normalize_list_payload(vernacular_raw)
        synonym_items = self._normalize_list_payload(synonyms_raw)

        vernacular_names: List[str] = []
        for item in vernacular_items:
            name = (
                item.get("vernacularName")
                or item.get("name")
                or item.get("vernacular_name")
            )
            if not name:
                continue
            name_str = str(name).strip()
            if name_str and name_str not in vernacular_names:
                vernacular_names.append(name_str)

        return (
            {
                "kingdom": detail.get("kingdom"),
                "phylum": detail.get("phylum"),
                "class": detail.get("class"),
                "order": detail.get("order"),
                "family": detail.get("family"),
                "genus": detail.get("genus"),
                "species": detail.get("species"),
                "synonyms_count": len(synonym_items),
                "vernacular_names": vernacular_names[:5],
                "iucn_category": self._gbif_extract_iucn_category(iucn_raw, detail),
            },
            {
                "detail": detail,
                "vernacular_names": vernacular_raw,
                "synonyms": synonyms_raw,
                "iucn": iucn_raw,
            },
        )

    def _gbif_occurrence_summary(
        self, usage_key: str
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Build an occurrence summary for a GBIF usage key."""

        raw = self._request_json(
            "https://api.gbif.org/v1/occurrence/search",
            [
                ("taxon_key", usage_key),
                ("limit", "0"),
                ("facet", "country"),
                ("facet", "datasetKey"),
                ("facet", "basisOfRecord"),
                ("facetLimit", "10"),
            ],
        )

        countries = self._gbif_extract_facet_values(raw, "country")
        dataset_keys = self._gbif_extract_facet_values(raw, "datasetkey")
        basis_of_record = self._gbif_extract_facet_values(raw, "basisofrecord")

        if not countries or not dataset_keys or not basis_of_record:
            for item in self._normalize_list_payload(raw):
                if not countries:
                    country = item.get("country") or item.get("countryCode")
                    if country:
                        countries.append(str(country))
                dataset_key = item.get("datasetKey")
                if dataset_key and str(dataset_key) not in dataset_keys:
                    dataset_keys.append(str(dataset_key))
                basis = item.get("basisOfRecord")
                if basis and str(basis) not in basis_of_record:
                    basis_of_record.append(str(basis))

        return (
            {
                "occurrence_count": int(raw.get("count") or 0),
                "countries": countries[:10],
                "datasets_count": len(dataset_keys),
                "basis_of_record": basis_of_record[:10],
            },
            raw,
        )

    def _gbif_media_summary(
        self, usage_key: str, media_limit: int
    ) -> tuple[Dict[str, Any], Any]:
        """Build a compact media summary for a GBIF usage key."""

        raw = self._request_json(f"{GBIF_SPECIES_ENDPOINT}/{usage_key}/media")
        items = self._normalize_list_payload(raw)
        normalized_items = [
            {
                "identifier": item.get("identifier") or item.get("references"),
                "thumbnail_url": item.get("identifier")
                or item.get("references")
                or item.get("source"),
                "source_url": item.get("references")
                or item.get("source")
                or item.get("identifier"),
                "creator": item.get("creator"),
                "license": item.get("license"),
                "type": item.get("type"),
            }
            for item in items[:media_limit]
            if isinstance(item, dict)
        ]

        return (
            {
                "media_count": len(items),
                "items": normalized_items,
            },
            raw,
        )

    def _gbif_checklist_key(self, params: ApiTaxonomyEnricherParams) -> Optional[str]:
        """Resolve the GBIF checklist key to use for matching."""

        source = (params.taxonomy_source or "").strip().lower()
        if not source or source == "col_xr":
            return GBIF_COL_XR_CHECKLIST_KEY
        return params.taxonomy_source

    def _gbif_taxonomy_source_label(self, params: ApiTaxonomyEnricherParams) -> str:
        """Return the normalized taxonomy source label for summaries."""

        source = (params.taxonomy_source or "").strip().lower()
        if not source or source == "col_xr":
            return "COL_XR"
        return (params.taxonomy_source or "GBIF").strip().upper().replace(" ", "_")

    def _gbif_extract_usage_key(self, raw: Dict[str, Any]) -> str:
        """Extract a stable GBIF or checklist identifier as a string."""

        for candidate in (
            raw.get("usageKey"),
            raw.get("acceptedUsageKey"),
            raw.get("taxonID"),
            raw.get("key"),
        ):
            if candidate is None:
                continue
            value = str(candidate).strip()
            if value:
                return value
        return ""

    def _gbif_build_links(self, usage_key: str) -> Dict[str, str]:
        """Build public GBIF links for a matched taxon."""

        return {
            "species": f"https://www.gbif.org/species/{usage_key}",
            "occurrences": f"https://www.gbif.org/occurrence/search?taxon_key={usage_key}",
        }

    def _col_dataset_key(self, params: ApiTaxonomyEnricherParams) -> int:
        """Resolve the ChecklistBank dataset key to use for Catalogue of Life."""

        return int(params.dataset_key or COL_DEFAULT_DATASET_KEY)

    def _col_search_url(self, dataset_key: int) -> str:
        """Build the ChecklistBank nameusage search URL."""

        return f"{COL_API_BASE}/dataset/{dataset_key}/nameusage/search"

    def _col_dataset_metadata(self, dataset_key: int) -> Dict[str, Any]:
        """Fetch metadata for a ChecklistBank dataset."""

        return self._request_json(f"{COL_API_BASE}/dataset/{dataset_key}")

    def _col_release_label(self, dataset_raw: Dict[str, Any], dataset_key: int) -> str:
        """Extract a human-readable release label for provenance."""

        for key in ("label", "version", "alias", "title"):
            value = dataset_raw.get(key)
            if value:
                return str(value)
        return f"dataset:{dataset_key}"

    def _col_match(
        self, query_value: str, dataset_key: int
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Resolve a Catalogue of Life match summary and raw payload."""

        raw = self._request_json(
            self._col_search_url(dataset_key),
            {"q": query_value, "limit": 10},
        )
        candidates = self._normalize_list_payload(raw)
        selected = self._col_select_match(candidates, query_value)
        summary = self._col_extract_match_summary(selected, dataset_key, query_value)
        return summary, raw

    def _col_select_match(
        self, candidates: List[Dict[str, Any]], query_value: str
    ) -> Dict[str, Any]:
        """Pick the best ChecklistBank search result for a query."""

        if not candidates:
            return {}

        normalized_query = self._normalize_taxon_text(query_value)

        def score(candidate: Dict[str, Any]) -> tuple[int, int, int, int]:
            usage = (
                candidate.get("usage")
                if isinstance(candidate.get("usage"), dict)
                else candidate
            )
            name_info = usage.get("name") if isinstance(usage.get("name"), dict) else {}
            scientific_name = self._normalize_taxon_text(
                name_info.get("scientificName")
                or usage.get("label")
                or candidate.get("name")
            )
            status = self._coerce_string(usage.get("status")).lower()
            exact = 1 if scientific_name == normalized_query else 0
            accepted = 2 if status == "accepted" else 1 if "accepted" in status else 0
            has_classification = (
                len(candidate.get("classification"))
                if isinstance(candidate.get("classification"), list)
                else 0
            )
            has_id = (
                1 if self._coerce_string(usage.get("id") or candidate.get("id")) else 0
            )
            return (exact, accepted, has_classification, has_id)

        return max(candidates, key=score)

    def _col_extract_match_summary(
        self,
        candidate: Dict[str, Any],
        dataset_key: int,
        query_value: str,
    ) -> Dict[str, Any]:
        """Normalize a ChecklistBank search result into the match block."""

        if not isinstance(candidate, dict):
            return {
                "taxon_id": "",
                "name_id": "",
                "scientific_name": "",
                "authorship": "",
                "canonical_name": "",
                "rank": "",
                "status": "",
                "matched_name": query_value,
                "dataset_key": dataset_key,
            }

        usage = (
            candidate.get("usage")
            if isinstance(candidate.get("usage"), dict)
            else candidate
        )
        name_info = usage.get("name") if isinstance(usage.get("name"), dict) else {}
        scientific_name = self._coerce_string(name_info.get("scientificName"))
        authorship = self._coerce_string(name_info.get("authorship"))

        return {
            "taxon_id": self._coerce_string(usage.get("id") or candidate.get("id")),
            "name_id": self._coerce_string(name_info.get("id")),
            "scientific_name": scientific_name,
            "authorship": authorship,
            "canonical_name": scientific_name,
            "rank": self._coerce_string(name_info.get("rank") or usage.get("rank")),
            "status": self._coerce_string(usage.get("status")),
            "matched_name": query_value,
            "dataset_key": dataset_key,
        }

    def _col_taxon_detail(
        self, dataset_key: int, taxon_id: str
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Fetch the ChecklistBank taxon record and normalize the match block."""

        raw = self._request_json(
            f"{COL_API_BASE}/dataset/{dataset_key}/taxon/{taxon_id}"
        )
        name_info = raw.get("name") if isinstance(raw.get("name"), dict) else {}
        scientific_name = self._coerce_string(name_info.get("scientificName"))
        authorship = self._coerce_string(name_info.get("authorship"))

        return (
            {
                "taxon_id": self._coerce_string(raw.get("id") or taxon_id),
                "name_id": self._coerce_string(name_info.get("id")),
                "scientific_name": scientific_name,
                "authorship": authorship,
                "canonical_name": scientific_name,
                "rank": self._coerce_string(name_info.get("rank") or raw.get("rank")),
                "status": self._coerce_string(raw.get("status")),
                "matched_name": scientific_name
                or self._coerce_string(raw.get("label")),
                "dataset_key": dataset_key,
            },
            raw,
        )

    def _col_taxonomy(
        self, dataset_key: int, taxon_id: str, fallback_species: str
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Build the taxonomy block for a ChecklistBank taxon."""

        raw = self._request_json(
            f"{COL_API_BASE}/dataset/{dataset_key}/taxon/{taxon_id}/classification"
        )
        items = self._normalize_list_payload(raw)
        classification = [
            {
                "rank": self._coerce_string(item.get("rank")).lower(),
                "name": self._coerce_string(item.get("name")),
            }
            for item in items
            if isinstance(item, dict)
            and self._coerce_string(item.get("rank"))
            and self._coerce_string(item.get("name"))
        ]

        taxonomy: Dict[str, Any] = {
            "classification": classification,
            "kingdom": None,
            "phylum": None,
            "class": None,
            "order": None,
            "family": None,
            "genus": None,
            "species": fallback_species or None,
        }

        for item in classification:
            rank = item["rank"]
            if rank in taxonomy:
                taxonomy[rank] = item["name"]

        return taxonomy, raw

    def _col_nomenclature(
        self,
        dataset_key: int,
        taxon_id: str,
        match_summary: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Build the nomenclature block for a ChecklistBank taxon."""

        raw = self._request_json(
            f"{COL_API_BASE}/dataset/{dataset_key}/taxon/{taxon_id}/synonyms"
        )
        homotypic = self._normalize_list_payload(raw.get("homotypic"))
        heterotypic = self._normalize_list_payload(raw.get("heterotypic"))
        all_items = homotypic + heterotypic

        samples: List[str] = []
        for item in all_items:
            name_info = item.get("name") if isinstance(item.get("name"), dict) else {}
            scientific_name = self._coerce_string(name_info.get("scientificName"))
            authorship = self._coerce_string(name_info.get("authorship"))
            label = " ".join(
                part for part in (scientific_name, authorship) if part
            ).strip()
            if label and label not in samples:
                samples.append(label)
            if len(samples) >= 5:
                break

        scientific_name = self._coerce_string(match_summary.get("scientific_name"))
        authorship = self._coerce_string(match_summary.get("authorship"))

        return (
            {
                "accepted_name": scientific_name,
                "accepted_name_with_authors": " ".join(
                    part for part in (scientific_name, authorship) if part
                ).strip(),
                "synonyms_count": len(all_items),
                "synonyms_sample": samples,
            },
            raw,
        )

    def _col_vernaculars(
        self, dataset_key: int, taxon_id: str
    ) -> tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
        """Build the vernaculars block for a ChecklistBank taxon."""

        raw = self._request_json(
            f"{COL_API_BASE}/dataset/{dataset_key}/taxon/{taxon_id}/vernacular",
            {"limit": 50},
        )
        items = self._normalize_list_payload(raw)
        by_language: Dict[str, List[str]] = {}
        sample: List[Dict[str, Any]] = []

        for item in items:
            name = self._coerce_string(item.get("name"))
            if not name:
                continue
            language = self._coerce_string(item.get("language")) or "und"
            language_bucket = by_language.setdefault(language, [])
            if name not in language_bucket:
                language_bucket.append(name)
            if len(sample) < 8:
                sample.append(
                    {
                        "name": name,
                        "language": language,
                        "country": self._coerce_string(item.get("country")),
                        "area": self._coerce_string(item.get("area")),
                    }
                )

        return (
            {
                "vernacular_count": len(items),
                "by_language": {
                    language: names[:5] for language, names in by_language.items()
                },
                "sample": sample,
            },
            raw,
            items,
        )

    def _col_distribution_summary(
        self, dataset_key: int, taxon_id: str
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Build a compact ChecklistBank distribution summary."""

        raw = self._request_json(
            f"{COL_API_BASE}/dataset/{dataset_key}/taxon/{taxon_id}/distribution",
            {"limit": 50},
        )
        items = self._normalize_list_payload(raw)
        areas: List[str] = []
        gazetteers: List[str] = []

        for item in items:
            area = item.get("area") if isinstance(item.get("area"), dict) else {}
            name = self._coerce_string(area.get("name"))
            gazetteer = self._coerce_string(area.get("gazetteer"))
            if name and name not in areas:
                areas.append(name)
            if gazetteer and gazetteer not in gazetteers:
                gazetteers.append(gazetteer)

        return (
            {
                "distribution_count": len(items),
                "areas": areas[:10],
                "gazetteers": gazetteers[:5],
            },
            raw,
        )

    def _col_references(
        self,
        dataset_key: int,
        taxon_raw: Dict[str, Any],
        nomenclature_raw: Dict[str, Any],
        vernacular_items: List[Dict[str, Any]],
        reference_limit: int,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Build a compact ChecklistBank reference summary."""

        reference_ids: List[str] = []

        def collect_reference_ids(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        reference_id = item.strip()
                        if reference_id and reference_id not in reference_ids:
                            reference_ids.append(reference_id)
                    elif isinstance(item, dict):
                        collect_reference_ids(item.get("referenceIds"))
                        collect_reference_ids(item.get("referenceId"))
            elif isinstance(value, str):
                reference_id = value.strip()
                if reference_id and reference_id not in reference_ids:
                    reference_ids.append(reference_id)

        collect_reference_ids(taxon_raw.get("referenceIds"))
        collect_reference_ids(nomenclature_raw.get("homotypic"))
        collect_reference_ids(nomenclature_raw.get("heterotypic"))
        for item in vernacular_items:
            collect_reference_ids(item.get("referenceId"))

        references_raw: List[Dict[str, Any]] = []
        items: List[Dict[str, Any]] = []
        for reference_id in reference_ids[:reference_limit]:
            raw = self._request_json(
                f"{COL_API_BASE}/dataset/{dataset_key}/reference/{reference_id}"
            )
            references_raw.append(raw)
            items.append(
                {
                    "id": self._coerce_string(raw.get("id") or reference_id),
                    "citation": self._coerce_string(raw.get("citation")),
                    "title": self._coerce_string(
                        (raw.get("csl") or {}).get("title")
                        if isinstance(raw.get("csl"), dict)
                        else None
                    ),
                    "year": raw.get("year"),
                }
            )

        return (
            {
                "references_count": len(reference_ids),
                "items": items,
            },
            references_raw,
        )

    def _col_build_links(
        self, dataset_key: int, taxon_id: str, taxon_raw: Dict[str, Any]
    ) -> Dict[str, str]:
        """Build public ChecklistBank links for a matched taxon."""

        links = {
            "checklistbank_taxon": f"https://www.checklistbank.org/dataset/{dataset_key}/taxon/{taxon_id}",
        }
        source_link = self._coerce_string(taxon_raw.get("link"))
        if source_link:
            links["source_record"] = source_link
        return links

    def _bhl_name_search(
        self, query_value: str, params: ApiTaxonomyEnricherParams
    ) -> tuple[Dict[str, Any], Dict[str, Any], str]:
        """Resolve a BHL name match summary and the best query value for metadata."""

        raw = self._bhl_request_json(
            "NameSearch",
            {"name": query_value},
            params,
        )
        items = self._bhl_result_items(raw)
        selected = self._bhl_select_name_match(items, query_value)
        confirmed_name = (
            self._coerce_string(selected.get("NameConfirmed")) or query_value
        )
        canonical_name = (
            self._coerce_string(selected.get("NameCanonical")) or confirmed_name
        )
        namebank_id = self._coerce_string(
            selected.get("NameBankID")
            or selected.get("NameBankId")
            or selected.get("NamebankID")
        )

        return (
            {
                "submitted_name": query_value,
                "name_confirmed": confirmed_name,
                "name_canonical": canonical_name,
                "namebank_id": namebank_id,
                "match_status": "confirmed" if items else "no_match",
            },
            raw,
            confirmed_name or query_value,
        )

    def _bhl_name_metadata(
        self, query_value: str, params: ApiTaxonomyEnricherParams
    ) -> tuple[
        Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]
    ]:
        """Build core BHL documentary blocks from name metadata."""

        raw = self._bhl_request_json(
            "GetNameMetadata",
            {"name": query_value},
            params,
        )
        items = self._bhl_result_items(raw)
        first_item = items[0] if items else {}

        titles = self._bhl_collect_titles(raw)
        item_ids = self._bhl_collect_item_ids(raw)
        pages = self._bhl_collect_pages(raw)
        mentions = self._bhl_collect_name_mentions(raw)

        match_summary = {
            "name_confirmed": self._coerce_string(
                first_item.get("NameConfirmed") or query_value
            ),
            "name_canonical": self._coerce_string(
                first_item.get("NameCanonical")
                or first_item.get("NameConfirmed")
                or query_value
            ),
            "namebank_id": self._coerce_string(
                first_item.get("NameBankID")
                or first_item.get("NameBankId")
                or first_item.get("NamebankID")
            ),
            "match_status": "confirmed" if items or titles or pages else "no_match",
        }

        return (
            {
                "match": match_summary,
                "title_summary": {
                    "title_count": len(titles),
                    "item_count": len(item_ids),
                    "page_count": len(pages),
                },
                "name_mentions": {
                    "mentions_count": len(mentions),
                    "sample": mentions[:10],
                },
                "references_count": {
                    "titles": len(titles),
                    "items": len(item_ids),
                    "pages": len(pages),
                },
            },
            raw,
            titles,
            pages,
        )

    def _bhl_publications(
        self,
        title_candidates: List[Dict[str, Any]],
        params: ApiTaxonomyEnricherParams,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Hydrate representative BHL publication summaries."""

        items: List[Dict[str, Any]] = []
        raw_payload: List[Dict[str, Any]] = []

        for candidate in title_candidates[: params.title_limit]:
            title_id = self._coerce_string(candidate.get("title_id"))
            if not title_id:
                continue

            detail_raw = self._bhl_request_json(
                "GetTitleMetadata",
                {"id": title_id, "idtype": "bhl", "items": "true"},
                params,
            )
            raw_payload.append(detail_raw)
            detail_item = (
                self._bhl_result_items(detail_raw)[0]
                if self._bhl_result_items(detail_raw)
                else {}
            )
            item_count = len(self._bhl_collect_item_ids(detail_raw))

            items.append(
                {
                    "title_id": title_id,
                    "short_title": self._coerce_string(
                        detail_item.get("ShortTitle")
                        or detail_item.get("Title")
                        or candidate.get("short_title")
                        or candidate.get("full_title")
                    ),
                    "full_title": self._coerce_string(
                        detail_item.get("FullTitle")
                        or candidate.get("full_title")
                        or candidate.get("short_title")
                    ),
                    "publication_date": self._coerce_string(
                        detail_item.get("PublicationDate")
                        or detail_item.get("Date")
                        or candidate.get("publication_date")
                    ),
                    "publisher_name": self._coerce_string(
                        detail_item.get("PublisherName")
                        or candidate.get("publisher_name")
                    ),
                    "title_url": self._coerce_string(
                        detail_item.get("TitleUrl") or candidate.get("title_url")
                    ),
                    "item_count": item_count,
                }
            )

        return (
            {
                "sample": items,
            },
            raw_payload,
        )

    def _bhl_page_links(
        self,
        page_candidates: List[Dict[str, Any]],
        params: ApiTaxonomyEnricherParams,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Hydrate representative BHL page summaries."""

        items: List[Dict[str, Any]] = []
        raw_payload: List[Dict[str, Any]] = []

        for candidate in page_candidates[: params.page_limit]:
            page_id = self._coerce_string(candidate.get("page_id"))
            if not page_id:
                continue

            detail_raw = self._bhl_request_json(
                "GetPageMetadata",
                {"pageid": page_id},
                params,
            )
            raw_payload.append(detail_raw)
            detail_item = (
                self._bhl_result_items(detail_raw)[0]
                if self._bhl_result_items(detail_raw)
                else {}
            )
            page_types = detail_item.get("PageTypes")
            page_type = ""
            if isinstance(page_types, list) and page_types:
                first_page_type = page_types[0]
                if isinstance(first_page_type, dict):
                    page_type = self._coerce_string(first_page_type.get("PageTypeName"))

            items.append(
                {
                    "page_id": page_id,
                    "page_url": self._coerce_string(
                        detail_item.get("PageUrl") or candidate.get("page_url")
                    ),
                    "thumbnail_url": self._coerce_string(
                        detail_item.get("ThumbnailUrl")
                        or candidate.get("thumbnail_url")
                    ),
                    "page_type": page_type
                    or self._coerce_string(candidate.get("page_type")),
                    "ocr_url": self._coerce_string(detail_item.get("OcrUrl")),
                }
            )

        return (
            {
                "sample": items,
            },
            raw_payload,
        )

    def _bhl_api_key(self, params: ApiTaxonomyEnricherParams) -> str:
        """Resolve the BHL API key from query-based api_key auth."""

        if params.auth_method != "api_key":
            raise ValueError("BHL requires API key authentication")

        auth_location = params.auth_params.get("location", "query").lower()
        if auth_location != "query":
            raise ValueError("BHL requires query-based API key authentication")

        api_key = self._get_secure_value(params.auth_params.get("key", ""))
        if not api_key.strip():
            raise ValueError("Missing BHL API key")
        return api_key.strip()

    def _bhl_request_json(
        self,
        operation: str,
        request_params: Dict[str, Any],
        params_model: ApiTaxonomyEnricherParams,
    ) -> Dict[str, Any]:
        """Perform a BHL API request and validate the wrapped response."""

        api_key = self._bhl_api_key(params_model)
        raw = self._request_json(
            params_model.api_url or BHL_API_ENDPOINT,
            {
                "op": operation,
                "format": "json",
                "apikey": api_key,
                **(request_params or {}),
            },
        )
        status = self._coerce_string(raw.get("Status")).lower()
        if status and status != "ok":
            raise ValueError(
                self._coerce_string(raw.get("ErrorMessage"))
                or f"BHL request failed for operation {operation}"
            )
        return raw

    def _bhl_result_items(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return BHL Result items as a list of dictionaries."""

        result = payload.get("Result")
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        if isinstance(result, dict):
            return [result]
        return []

    def _bhl_select_name_match(
        self, candidates: List[Dict[str, Any]], query_value: str
    ) -> Dict[str, Any]:
        """Pick the best BHL name match for a query."""

        if not candidates:
            return {}

        normalized_query = self._normalize_taxon_text(query_value)

        def score(candidate: Dict[str, Any]) -> tuple[int, int, int]:
            confirmed = self._normalize_taxon_text(candidate.get("NameConfirmed"))
            canonical = self._normalize_taxon_text(candidate.get("NameCanonical"))
            exact_confirmed = 1 if confirmed == normalized_query else 0
            exact_canonical = 1 if canonical == normalized_query else 0
            has_namebank = (
                1
                if self._coerce_string(
                    candidate.get("NameBankID")
                    or candidate.get("NameBankId")
                    or candidate.get("NamebankID")
                )
                else 0
            )
            return (exact_confirmed, exact_canonical, has_namebank)

        return max(candidates, key=score)

    def _bhl_build_links(self, query_value: str) -> Dict[str, str]:
        """Build public BHL links for a matched name."""

        return {
            "name_search": f"https://www.biodiversitylibrary.org/name/{quote_plus(query_value)}",
        }

    def _inaturalist_match(
        self, query_value: str, params: ApiTaxonomyEnricherParams
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Resolve an iNaturalist taxon match summary and selected taxon payload."""

        query_params = {
            **(params.query_params or {}),
            (params.query_param_name or "q"): query_value,
            "is_active": str((params.query_params or {}).get("is_active", "true")),
            "per_page": str(max(params.observation_limit or 5, 10)),
        }
        raw = self._request_json(params.api_url or INAT_TAXA_ENDPOINT, query_params)
        candidates = self._normalize_list_payload(raw)
        selected = self._inaturalist_select_match(candidates, query_value)

        summary = {
            "taxon_id": self._coerce_string(selected.get("id")),
            "scientific_name": self._coerce_string(selected.get("name")) or query_value,
            "preferred_common_name": self._coerce_string(
                selected.get("preferred_common_name")
            ),
            "rank": self._coerce_string(selected.get("rank")),
            "iconic_taxon_name": self._coerce_string(selected.get("iconic_taxon_name")),
            "matched_name": self._coerce_string(
                selected.get("matched_term") or selected.get("name")
            )
            or query_value,
        }
        return summary, raw, selected

    def _inaturalist_select_match(
        self, candidates: List[Dict[str, Any]], query_value: str
    ) -> Dict[str, Any]:
        """Pick the best iNaturalist taxon search result for a query."""

        if not candidates:
            return {}

        normalized_query = self._normalize_taxon_text(query_value)

        def score(candidate: Dict[str, Any]) -> tuple[int, int, int, int]:
            scientific_name = self._normalize_taxon_text(candidate.get("name"))
            matched_term = self._normalize_taxon_text(candidate.get("matched_term"))
            preferred_common_name = self._normalize_taxon_text(
                candidate.get("preferred_common_name")
            )
            exact_name = 1 if scientific_name == normalized_query else 0
            exact_term = 1 if matched_term == normalized_query else 0
            active = 1 if candidate.get("is_active") else 0
            common_name_hit = 1 if preferred_common_name == normalized_query else 0
            return (
                exact_name,
                exact_term,
                active,
                int(candidate.get("observations_count") or 0) + common_name_hit,
            )

        return max(candidates, key=score)

    def _inaturalist_taxon_summary(self, taxon_raw: Dict[str, Any]) -> Dict[str, Any]:
        """Build a lightweight iNaturalist taxon card from a search result."""

        conservation = taxon_raw.get("conservation_status")
        conservation_status = (
            self._coerce_string(conservation.get("status"))
            if isinstance(conservation, dict)
            else self._coerce_string(conservation)
        )

        return {
            "wikipedia_url": self._coerce_string(taxon_raw.get("wikipedia_url")),
            "default_photo": self._inaturalist_photo_summary(
                taxon_raw.get("default_photo")
            ),
            "observations_count": int(taxon_raw.get("observations_count") or 0),
            "conservation_status": conservation_status,
            "iconic_taxon_name": self._coerce_string(
                taxon_raw.get("iconic_taxon_name")
            ),
            "preferred_common_name": self._coerce_string(
                taxon_raw.get("preferred_common_name")
            ),
        }

    def _inaturalist_observation_summary(
        self, taxon_id: str, observation_limit: int
    ) -> tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
        """Build a compact observations summary for an iNaturalist taxon."""

        sample_raw = self._request_json(
            INAT_OBSERVATIONS_ENDPOINT,
            {
                "taxon_id": taxon_id,
                "per_page": max(observation_limit, 1),
                "order_by": "observed_on",
                "order": "desc",
            },
        )
        items = self._normalize_list_payload(sample_raw)

        counts_raw = {
            "research": self._request_json(
                INAT_OBSERVATIONS_ENDPOINT,
                {"taxon_id": taxon_id, "per_page": 1, "quality_grade": "research"},
            ),
            "casual": self._request_json(
                INAT_OBSERVATIONS_ENDPOINT,
                {"taxon_id": taxon_id, "per_page": 1, "quality_grade": "casual"},
            ),
            "needs_id": self._request_json(
                INAT_OBSERVATIONS_ENDPOINT,
                {"taxon_id": taxon_id, "per_page": 1, "quality_grade": "needs_id"},
            ),
        }

        recent_observations = []
        for item in items[:observation_limit]:
            observation_id = self._coerce_string(item.get("id"))
            observed_on = self._coerce_string(item.get("observed_on"))
            if not observed_on:
                observed_on = self._coerce_string(item.get("time_observed_at"))[:10]
            recent_observations.append(
                {
                    "observation_id": observation_id,
                    "observed_on": observed_on,
                    "quality_grade": self._coerce_string(item.get("quality_grade")),
                    "place_guess": self._coerce_string(item.get("place_guess")),
                    "observation_url": self._coerce_string(item.get("uri"))
                    or (
                        f"https://www.inaturalist.org/observations/{observation_id}"
                        if observation_id
                        else ""
                    ),
                }
            )

        return (
            {
                "observations_count": int(sample_raw.get("total_results") or 0),
                "research_grade_count": int(
                    counts_raw["research"].get("total_results") or 0
                ),
                "casual_count": int(counts_raw["casual"].get("total_results") or 0),
                "needs_id_count": int(counts_raw["needs_id"].get("total_results") or 0),
                "recent_observations": recent_observations,
            },
            sample_raw,
            items,
            counts_raw,
        )

    def _inaturalist_media_summary(
        self,
        taxon_raw: Dict[str, Any],
        observation_items: List[Dict[str, Any]],
        media_limit: int,
    ) -> Dict[str, Any]:
        """Build a compact photo summary from iNaturalist observations."""

        sample: List[Dict[str, Any]] = []
        seen_identifiers: set[str] = set()
        media_count = 0

        for item in observation_items:
            photos = item.get("photos")
            if not isinstance(photos, list):
                continue

            observation_id = self._coerce_string(item.get("id"))
            observation_url = self._coerce_string(item.get("uri")) or (
                f"https://www.inaturalist.org/observations/{observation_id}"
                if observation_id
                else ""
            )
            for photo in photos:
                if not isinstance(photo, dict):
                    continue
                normalized = self._inaturalist_photo_summary(photo)
                identifier = (
                    self._coerce_string(photo.get("id"))
                    or normalized.get("medium_url")
                    or normalized.get("square_url")
                )
                if not identifier or identifier in seen_identifiers:
                    continue
                seen_identifiers.add(identifier)
                media_count += 1
                if len(sample) < media_limit:
                    sample.append(
                        {
                            "observation_id": observation_id,
                            "observation_url": observation_url,
                            **normalized,
                        }
                    )

        if not sample and media_limit > 0:
            default_photo = self._inaturalist_photo_summary(
                taxon_raw.get("default_photo")
            )
            if default_photo.get("medium_url") or default_photo.get("square_url"):
                sample.append(default_photo)
                media_count = 1

        return {
            "media_count": media_count,
            "sample": sample,
        }

    def _inaturalist_places_summary(
        self, observation_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build a compact place summary from recent iNaturalist observations."""

        counts: Dict[str, int] = {}
        for item in observation_items:
            place = self._coerce_string(item.get("place_guess"))
            if not place:
                continue
            counts[place] = counts.get(place, 0) + 1

        top_places = [
            {"name": name, "count": count}
            for name, count in sorted(
                counts.items(), key=lambda entry: (-entry[1], entry[0].lower())
            )[:5]
        ]

        return {
            "places_count": len(counts),
            "top_places": top_places,
        }

    def _inaturalist_photo_summary(self, photo: Any) -> Dict[str, Any]:
        """Normalize an iNaturalist photo object for preview and storage."""

        if not isinstance(photo, dict):
            return {}

        return {
            "square_url": self._coerce_string(
                photo.get("square_url") or photo.get("url")
            ),
            "medium_url": self._coerce_string(
                photo.get("medium_url") or photo.get("url")
            ),
            "attribution": self._coerce_string(photo.get("attribution")),
            "license_code": self._coerce_string(
                photo.get("license_code") or photo.get("license")
            ),
        }

    def _inaturalist_build_links(
        self, taxon_id: str, taxon_raw: Dict[str, Any]
    ) -> Dict[str, str]:
        """Build public iNaturalist links for a matched taxon."""

        taxon_link = self._coerce_string(taxon_raw.get("uri")) or (
            f"https://www.inaturalist.org/taxa/{taxon_id}" if taxon_id else ""
        )
        observations_link = (
            f"https://www.inaturalist.org/observations?taxon_id={taxon_id}"
            if taxon_id
            else ""
        )

        links: Dict[str, str] = {}
        if taxon_link:
            links["taxon"] = taxon_link
        if observations_link:
            links["observations"] = observations_link
        return links

    def _bhl_collect_titles(self, payload: Any) -> List[Dict[str, Any]]:
        """Collect unique title candidates from nested BHL payloads."""

        titles: Dict[str, Dict[str, Any]] = {}
        for item in self._walk_nested_dicts(payload):
            title_id = self._coerce_string(item.get("TitleID"))
            title_url = self._coerce_string(item.get("TitleUrl"))
            full_title = self._coerce_string(item.get("FullTitle") or item.get("Title"))
            short_title = self._coerce_string(item.get("ShortTitle"))
            if not any((title_id, title_url, full_title, short_title)):
                continue

            key = title_id or title_url or full_title or short_title
            titles[key] = {
                "title_id": title_id,
                "title_url": title_url,
                "full_title": full_title,
                "short_title": short_title or full_title,
                "publication_date": self._coerce_string(
                    item.get("PublicationDate") or item.get("Date")
                ),
                "publisher_name": self._coerce_string(item.get("PublisherName")),
            }

        return list(titles.values())

    def _bhl_collect_item_ids(self, payload: Any) -> List[str]:
        """Collect unique BHL item ids from nested payloads."""

        item_ids: List[str] = []
        for item in self._walk_nested_dicts(payload):
            item_id = self._coerce_string(item.get("ItemID"))
            if item_id and item_id not in item_ids:
                item_ids.append(item_id)
        return item_ids

    def _bhl_collect_pages(self, payload: Any) -> List[Dict[str, Any]]:
        """Collect unique BHL page candidates from nested payloads."""

        pages: Dict[str, Dict[str, Any]] = {}
        for item in self._walk_nested_dicts(payload):
            page_id = self._coerce_string(item.get("PageID"))
            page_url = self._coerce_string(item.get("PageUrl"))
            thumbnail_url = self._coerce_string(item.get("ThumbnailUrl"))
            if not any((page_id, page_url, thumbnail_url)):
                continue

            page_types = item.get("PageTypes")
            page_type = ""
            if isinstance(page_types, list) and page_types:
                first_page_type = page_types[0]
                if isinstance(first_page_type, dict):
                    page_type = self._coerce_string(first_page_type.get("PageTypeName"))

            key = page_id or page_url or thumbnail_url
            pages[key] = {
                "page_id": page_id,
                "page_url": page_url,
                "thumbnail_url": thumbnail_url,
                "page_type": page_type,
            }

        return list(pages.values())

    def _bhl_collect_name_mentions(self, payload: Any) -> List[Dict[str, Any]]:
        """Collect unique BHL name mentions from nested payloads."""

        mentions: Dict[str, Dict[str, Any]] = {}
        for item in self._walk_nested_dicts(payload):
            name_found = self._coerce_string(item.get("NameFound"))
            name_confirmed = self._coerce_string(item.get("NameConfirmed"))
            name_canonical = self._coerce_string(item.get("NameCanonical"))
            if not any((name_found, name_confirmed, name_canonical)):
                continue

            key = name_confirmed or name_canonical or name_found
            mentions[key] = {
                "name_found": name_found,
                "name_confirmed": name_confirmed,
                "name_canonical": name_canonical,
            }

        return list(mentions.values())

    def _walk_nested_dicts(self, payload: Any) -> List[Dict[str, Any]]:
        """Return every nested dictionary found in a payload tree."""

        items: List[Dict[str, Any]] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                items.append(value)
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(payload)
        return items

    def _gbif_extract_iucn_category(
        self, iucn_raw: Any, detail_raw: Dict[str, Any]
    ) -> Optional[str]:
        """Extract the most useful IUCN category value available."""

        if isinstance(iucn_raw, str) and iucn_raw.strip():
            return iucn_raw.strip()
        if isinstance(iucn_raw, dict):
            for key in ("category", "code", "value"):
                value = iucn_raw.get(key)
                if value:
                    return str(value)
        for key in ("threatStatus", "iucnRedListCategory"):
            value = detail_raw.get(key)
            if value:
                return str(value)
        return None

    def _gbif_extract_facet_values(
        self, raw: Dict[str, Any], field_name: str
    ) -> List[str]:
        """Extract facet values from an occurrence search response."""

        values: List[str] = []
        facets = raw.get("facets")
        if not isinstance(facets, list):
            return values

        normalized_field_name = field_name.replace("_", "").lower()
        for facet in facets:
            if not isinstance(facet, dict):
                continue
            raw_field = str(facet.get("field") or "").replace("_", "").lower()
            if raw_field != normalized_field_name:
                continue

            counts = facet.get("counts")
            if not isinstance(counts, list):
                return values

            for item in counts:
                if not isinstance(item, dict):
                    continue
                value = item.get("name") or item.get("value")
                if value is None:
                    continue
                value_str = str(value).strip()
                if value_str and value_str not in values:
                    values.append(value_str)
            return values

        return values

    def _normalize_list_payload(self, payload: Any) -> List[Dict[str, Any]]:
        """Normalize a JSON payload that may expose a list directly or under a key."""

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            return []

        for key in ("results", "result", "data", "items", "records", "Result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        return []

    def _request_json(self, url: str, params: Any | None = None) -> Dict[str, Any]:
        """Perform a JSON GET request with a small timeout."""

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"results": data}
        return {"value": data}

    def _process_api_response(self, data: Any) -> Dict[str, Any]:
        """
        Process API response to extract relevant data.

        Args:
            data: API response data

        Returns:
            Processed API data as dictionary
        """
        # Handle different API response structures
        if isinstance(data, list):
            # If it's a list, use the first item that looks relevant
            for item in data:
                if isinstance(item, dict) and len(item) > 1:
                    return item
            # If no complex item found but list is not empty
            if data:
                return data[0] if isinstance(data[0], dict) else {"value": data[0]}
            return {}

        if isinstance(data, dict):
            # Try common response patterns
            if (
                "results" in data
                and isinstance(data["results"], list)
                and data["results"]
            ):
                return data["results"][0]
            elif "data" in data and isinstance(data["data"], list) and data["data"]:
                return data["data"][0]
            elif "items" in data and isinstance(data["items"], list) and data["items"]:
                return data["items"][0]
            elif (
                "records" in data
                and isinstance(data["records"], list)
                and data["records"]
            ):
                return data["records"][0]

            # If we have a result field with content
            if "result" in data and data["result"] and isinstance(data["result"], dict):
                return data["result"]

            # Check if the response itself contains useful data
            useful_fields = [
                "id",
                "name",
                "scientific_name",
                "common_name",
                "description",
            ]
            if any(field in data for field in useful_fields):
                return data

            return data

        # If we couldn't identify the structure, return empty dict
        return {}

    def _enrich_taxon_data(
        self,
        taxon_data: Dict[str, Any],
        api_data: Dict[str, Any],
        mapping: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Map API data according to mapping configuration.

        Args:
            taxon_data: Original taxon data
            api_data: Processed API data
            mapping: Mapping between API response fields and output fields

        Returns:
            Original taxon data with additional api_enrichment field
        """
        # Make a copy to avoid modifying the original
        enriched_data = taxon_data.copy()

        # Create a new dictionary for API enrichment data
        api_enrichment = {}

        # Map API data according to mapping
        for target_field, api_field in mapping.items():
            if not api_field:
                continue

            # Support nested field access with dot notation
            if "." in api_field:
                parts = api_field.split(".")
                value = api_data
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    elif isinstance(value, list) and part.isdigit():
                        index = int(part)
                        if 0 <= index < len(value):
                            value = value[index]
                        else:
                            value = None
                            break
                    else:
                        value = None
                        break
                if value is not None:
                    api_enrichment[target_field] = value
            else:
                # Direct field access
                if api_field in api_data and api_data[api_field] is not None:
                    api_enrichment[target_field] = api_data[api_field]

        # Store API enrichment data separately
        enriched_data["api_enrichment"] = api_enrichment

        return enriched_data

    def _get_secure_value(self, value: str) -> str:
        """
        Extract secure value from environment or file if needed

        Args:
            value: Value string which could be a reference

        Returns:
            Actual value to use
        """
        if not value or not isinstance(value, str):
            return str(value) if value is not None else ""

        # Environment variable reference
        if value.startswith("$ENV:"):
            env_var = value[5:]
            return os.environ.get(env_var, "")

        # File reference
        if value.startswith("$FILE:"):
            file_path = value[6:]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Failed to read value from file {file_path}: {str(e)}")
                return ""

        return value

    def _process_chained_requests(
        self,
        initial_data: Dict[str, Any],
        chain_config: List[Dict[str, Any]],
        params: ApiTaxonomyEnricherParams,
        headers: Dict[str, str],
        cookies: Dict[str, str],
        auth: Any,
    ) -> Dict[str, Any]:
        """
        Process additional API endpoints using data from initial response.

        Args:
            initial_data: Data from the initial API response
            chain_config: List of chained endpoint configurations
            params: Parameters object
            headers: Headers to use for requests
            cookies: Cookies to use for requests
            auth: Authentication object

        Returns:
            Enriched data combining initial and chained responses
        """
        # Don't copy initial_data - we want to build on it
        enriched_data = initial_data

        for endpoint_config in chain_config:
            try:
                # Build URL from template
                url_template = endpoint_config["url_template"]
                url = self._build_url_from_template(url_template, enriched_data, params)

                if not url:
                    # Silently skip if URL cannot be built (e.g., missing tropicos_id)
                    # This is expected when the initial API query returns no results
                    logger.debug(f"Could not build URL from template: {url_template}")
                    continue

                # Get query parameters if specified
                endpoint_params = endpoint_config.get("params", {})

                # Add authentication parameters if needed
                if (
                    params.auth_method == "api_key"
                    and params.auth_params.get("location") == "query"
                ):
                    param_name = params.auth_params.get("name", "api_key")
                    endpoint_params[param_name] = self._get_secure_value(
                        params.auth_params.get("key", "")
                    )

                # Make the request
                logger.debug(f"Chained request to: {url}")

                if cookies:
                    session = requests.Session()
                    session.cookies.update(cookies)
                    response = session.get(
                        url, params=endpoint_params, headers=headers, auth=auth
                    )
                else:
                    response = requests.get(
                        url, params=endpoint_params, headers=headers, auth=auth
                    )

                response.raise_for_status()
                chain_data = response.json()

                # Process the response according to mapping
                mapping = endpoint_config.get("mapping", {})
                logger.debug(
                    f"Chain data type: {type(chain_data)}, has data: {bool(chain_data)}"
                )
                self._apply_chain_mapping(enriched_data, chain_data, mapping)
                logger.debug(
                    f"After mapping: {list(enriched_data.keys())[-5:] if len(enriched_data) > 5 else list(enriched_data.keys())}"
                )

                # Respect rate limit
                if params.rate_limit > 0:
                    time.sleep(1.0 / params.rate_limit)

            except Exception as e:
                # Log only at debug level - failures are expected for missing data
                logger.debug(
                    f"Failed to process chained endpoint {url_template}: {str(e)}"
                )
                import traceback

                logger.debug(traceback.format_exc())
                continue

        return enriched_data

    def _build_url_from_template(
        self, template: str, data: Dict[str, Any], params: ApiTaxonomyEnricherParams
    ) -> str:
        """
        Build URL from template by replacing placeholders with actual values.

        Args:
            template: URL template with placeholders like {field_name}
            data: Data dictionary to extract values from
            params: Parameters object for auth params

        Returns:
            Built URL or empty string if failed
        """
        url = template

        # Replace placeholders with values from data
        import re

        placeholders = re.findall(r"\{([^}]+)\}", template)

        for placeholder in placeholders:
            value = None

            # Special handling for auth parameters
            if placeholder == "apikey" and params.auth_method == "api_key":
                value = self._get_secure_value(params.auth_params.get("key", ""))
            else:
                # Extract value from data using dot notation
                value = self._extract_nested_value(data, placeholder)

            if value is not None:
                url = url.replace(f"{{{placeholder}}}", str(value))
            else:
                # Silently return empty string - this is expected when data is not found
                logger.debug(f"Could not find value for placeholder: {placeholder}")
                return ""

        return url

    def _extract_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Extract value from nested dictionary using dot notation.

        Args:
            data: Dictionary to extract from
            path: Dot-separated path like "0.NameId" or "results.0.id"

        Returns:
            Extracted value or None
        """
        parts = path.split(".")
        value = data

        for part in parts:
            if value is None:
                return None

            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                index = int(part)
                if 0 <= index < len(value):
                    value = value[index]
                else:
                    return None
            else:
                return None

        return value

    def _apply_chain_mapping(
        self, target_data: Dict[str, Any], source_data: Any, mapping: Dict[str, str]
    ) -> None:
        """
        Apply mapping rules to extract data from chained response.

        Args:
            target_data: Dictionary to add extracted data to
            source_data: Source data from API response
            mapping: Mapping configuration
        """
        for target_field, source_spec in mapping.items():
            if not source_spec:
                continue

            value = None

            # Special mapping operators
            if source_spec == "$all" or source_spec == "$array":
                # Store entire response
                value = source_data

            elif source_spec == "$count":
                # Count items if list
                if isinstance(source_data, list):
                    value = len(source_data)
                else:
                    value = 0

            elif source_spec.startswith("$first:"):
                # Get field from first item in list
                field = source_spec[7:]
                if isinstance(source_data, list) and source_data:
                    value = self._extract_nested_value(source_data[0], field)

            elif source_spec.startswith("$unique:"):
                # Get unique values of a field from list
                field = source_spec[8:]
                if isinstance(source_data, list):
                    values = []
                    for item in source_data:
                        if isinstance(item, dict) and field in item:
                            val = item[field]
                            if val and val not in values:
                                values.append(val)
                    value = values

            elif source_spec.startswith("$max:"):
                # Limit array size
                parts = source_spec[5:].split(":")
                if len(parts) == 2 and parts[0].isdigit():
                    max_items = int(parts[0])
                    field = parts[1] if len(parts) > 1 else None

                    if field:
                        # Extract field from items and limit
                        if isinstance(source_data, list):
                            value = []
                            for item in source_data[:max_items]:
                                if isinstance(item, dict):
                                    val = self._extract_nested_value(item, field)
                                    if val:
                                        value.append(val)
                    else:
                        # Just limit the array
                        if isinstance(source_data, list):
                            value = source_data[:max_items]

            else:
                # Normal field extraction
                value = self._extract_nested_value(source_data, source_spec)

            # Add to target data if value was found
            if value is not None:
                target_data[target_field] = value
