"""
Plugin for enriching taxonomy data with information from external APIs.
"""

import logging
import os
import time
from typing import Any, Dict, List, Literal, Optional

import requests
from pydantic import Field, model_validator, ConfigDict

from niamoto.common.utils.emoji import emoji
from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register

logger = logging.getLogger(__name__)

GBIF_COL_XR_CHECKLIST_KEY = "7ddf754f-d193-4cc9-b351-99906754a03b"
GBIF_MATCH_ENDPOINT = "https://api.gbif.org/v2/species/match"
GBIF_SPECIES_ENDPOINT = "https://api.gbif.org/v1/species"
TROPICOS_SEARCH_ENDPOINT = "https://services.tropicos.org/Name/Search"
TROPICOS_NAME_ENDPOINT = "https://services.tropicos.org/Name"


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
    taxonomy_source: Optional[str] = Field(
        default=None,
        description="Preferred taxonomy source for structured provider profiles",
        json_schema_extra={"ui:widget": "text"},
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
    include_references: bool = Field(
        default=True,
        description="Whether to include reference summary for structured provider profiles",
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
        if self.profile in {"gbif_rich", "tropicos_rich"}:
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
            f"::{params.include_taxonomy}::{params.include_occurrences}::{params.include_media}"
            f"::{params.include_references}::{params.include_distributions}"
            f"::{params.media_limit}::{query_value}"
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
            if params.profile == "gbif_rich":
                result = self._load_gbif_rich_data(
                    taxon_data=taxon_data,
                    query_value=str(query_value),
                    params=params,
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
                    query_value=str(query_value),
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
        params: ApiTaxonomyEnricherParams,
    ) -> Dict[str, Any]:
        """Load a structured GBIF enrichment summary."""

        summary: Dict[str, Any] = {
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
                "endpoints": [],
            },
        }
        raw_payload: Dict[str, Any] = {}
        processed_payload: Dict[str, Any] = {}

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
        params: ApiTaxonomyEnricherParams,
    ) -> Dict[str, Any]:
        """Load a structured Tropicos enrichment summary."""

        summary: Dict[str, Any] = {
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
                "endpoints": [],
            },
        }
        raw_payload: Dict[str, Any] = {}
        processed_payload: Dict[str, Any] = {}

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

        for key in ("results", "data", "items", "records"):
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
                with open(file_path, "r") as f:
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
