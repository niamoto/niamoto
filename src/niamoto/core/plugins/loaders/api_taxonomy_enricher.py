"""
Plugin for enriching taxonomy data with information from external APIs.
"""

import os
import requests
import time
import logging
from typing import Dict, Any, Literal
from pydantic import Field, model_validator

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register

logger = logging.getLogger(__name__)


class ApiTaxonomyEnricherConfig(PluginConfig):
    """Configuration for API taxonomy enricher plugin"""

    plugin: Literal["api_taxonomy_enricher"]
    api_url: str = Field(..., description="Base URL for the API")
    query_params: Dict[str, str] = Field(
        default_factory=dict, description="Default query parameters"
    )
    query_field: str = Field(
        "full_name", description="Field in taxon data to use for query"
    )
    response_mapping: Dict[str, str] = Field(
        ..., description="Mapping between API response fields and extra_data fields"
    )
    rate_limit: float = Field(1.0, description="Requests per second")
    cache_results: bool = Field(True, description="Whether to cache API results")

    # Authentication options
    auth_method: Literal["none", "api_key", "basic", "oauth2", "bearer"] = Field(
        "none", description="Authentication method to use"
    )
    auth_params: Dict[str, str] = Field(
        default_factory=dict, description="Parameters for authentication"
    )

    @model_validator(mode="after")
    def check_response_mapping(self):
        """Validate that response mapping is properly formatted"""
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


@register("api_taxonomy_enricher", PluginType.LOADER)
class ApiTaxonomyEnricher(LoaderPlugin):
    """Plugin for enriching taxonomy data with information from external APIs"""

    config_model = ApiTaxonomyEnricherConfig
    _cache = {}  # Simple in-memory cache
    _oauth_tokens = {}  # Cache for OAuth tokens

    def __init__(self, db=None):
        super().__init__(db)
        self.log_messages = []  # Liste pour stocker les messages de log

    def validate_config(self, config: Dict[str, Any]) -> ApiTaxonomyEnricherConfig:
        """Validate plugin configuration."""
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

        # Extract query value from taxon data
        query_field = validated_config.query_field
        query_value = taxon_data.get(query_field)

        if not query_value:
            logger.warning(
                f"No query value found for field {query_field} in taxon data"
            )
            self.log_messages.append(
                f"[yellow]No value found for field {query_field} in taxon data[/yellow]"
            )
            return taxon_data

        # Check cache if enabled
        cache_key = f"{query_value}_{validated_config.api_url}"
        if validated_config.cache_results and cache_key in self._cache:
            logger.debug(f"Using cached data for {query_value}")
            self.log_messages.append(
                f"[blue]Using cached data for {query_value}[/blue]"
            )
            api_data = self._cache[cache_key]
            return self._enrich_taxon_data(
                taxon_data, api_data, validated_config.response_mapping
            )

        # Prepare API request
        url = validated_config.api_url
        params = validated_config.query_params.copy()
        params["q"] = query_value

        # Prepare headers
        headers = {}
        cookies = {}

        # Setup authentication
        auth = None

        try:
            # Apply appropriate authentication
            if validated_config.auth_method == "api_key":
                self._setup_api_key_auth(
                    validated_config.auth_params, headers, params, cookies
                )

            elif validated_config.auth_method == "basic":
                auth = (
                    self._get_secure_value(
                        validated_config.auth_params.get("username", "")
                    ),
                    self._get_secure_value(
                        validated_config.auth_params.get("password", "")
                    ),
                )

            elif validated_config.auth_method == "bearer":
                headers["Authorization"] = (
                    f"Bearer {self._get_secure_value(validated_config.auth_params.get('token', ''))}"
                )

            elif validated_config.auth_method == "oauth2":
                self._setup_oauth2_auth(validated_config.auth_params, headers)

            # Make API request with authentication
            logger.debug(f"Requesting API data for {query_value} from {url}")
            # Ne pas ajouter de message pour la récupération, seulement pour le succès final

            # Use session if we have cookies
            if cookies:
                session = requests.Session()
                session.cookies.update(cookies)
                response = session.get(url, params=params, headers=headers, auth=auth)
            else:
                response = requests.get(url, params=params, headers=headers, auth=auth)

            response.raise_for_status()
            data = response.json()

            # Process the response
            api_data = self._process_api_response(data)

            # Cache results if enabled
            if validated_config.cache_results and api_data:
                self._cache[cache_key] = api_data

            # Log success message
            self.log_messages.append(
                f"[green]✓ Data successfully retrieved for {query_value}[/green]"
            )

            # Enrich taxon data
            return self._enrich_taxon_data(
                taxon_data, api_data, validated_config.response_mapping
            )

        except requests.RequestException as e:
            error_msg = f"API request failed for {query_value}: {str(e)}"
            logger.error(error_msg)
            self.log_messages.append(
                f"[bold red]✗ API request failed for {query_value}: {str(e)}[/bold red]"
            )
            return taxon_data
        except Exception as e:
            error_msg = f"Failed to process API data for {query_value}: {str(e)}"
            logger.error(error_msg)
            self.log_messages.append(
                f"[bold red]✗ Failed to process API data for {query_value}: {str(e)}[/bold red]"
            )
            return taxon_data
        finally:
            # Respect rate limit regardless of outcome
            if validated_config.rate_limit > 0:
                time.sleep(1.0 / validated_config.rate_limit)
            else:
                # Avoid division by zero if rate_limit is 0 or negative
                pass

    def _setup_api_key_auth(
        self,
        auth_params: Dict[str, str],
        headers: Dict[str, str],
        params: Dict[str, str],
        cookies: Dict[str, str],
    ) -> None:
        """
        Setup API key authentication based on configuration

        Args:
            auth_params: Authentication parameters
            headers: Headers dictionary to modify
            params: Query parameters dictionary to modify
            cookies: Cookies dictionary to modify
        """
        api_key = self._get_secure_value(auth_params.get("key", ""))
        location = auth_params.get("location", "header").lower()

        if location == "header":
            header_name = auth_params.get("name", "X-API-Key")
            headers[header_name] = api_key
        elif location == "query":
            param_name = auth_params.get("name", "api_key")
            params[param_name] = api_key
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
