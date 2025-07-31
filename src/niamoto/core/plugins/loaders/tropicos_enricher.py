"""
Plugin for enriching taxonomy data with Tropicos data including images.
"""

import requests
import time
import logging
from typing import Dict, Any, List, Literal
from pydantic import Field

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import LoaderPlugin, PluginType, register

logger = logging.getLogger(__name__)


class TropicosEnricherConfig(PluginConfig):
    """Configuration for Tropicos enricher plugin"""

    plugin: Literal["tropicos_enricher"]
    api_key: str = Field(..., description="Tropicos API key")
    base_url: str = Field(
        default="http://services.tropicos.org", description="Base URL for Tropicos API"
    )
    query_field: str = Field(
        default="full_name", description="Field in taxon data to use for query"
    )
    include_images: bool = Field(default=True, description="Whether to fetch images")
    include_synonyms: bool = Field(
        default=True, description="Whether to fetch synonyms"
    )
    include_distributions: bool = Field(
        default=True, description="Whether to fetch distributions"
    )
    include_references: bool = Field(
        default=True, description="Whether to fetch references"
    )
    rate_limit: float = Field(default=1.0, description="Requests per second")
    cache_results: bool = Field(
        default=True, description="Whether to cache API results"
    )


@register("tropicos_enricher", PluginType.LOADER)
class TropicosEnricher(LoaderPlugin):
    """Plugin for enriching taxonomy data with comprehensive Tropicos data"""

    config_model = TropicosEnricherConfig
    _cache = {}  # Simple in-memory cache

    def __init__(self, db=None):
        super().__init__(db)
        self.log_messages = []

    def validate_config(self, config: Dict[str, Any]) -> TropicosEnricherConfig:
        """Validate plugin configuration."""
        return self.config_model(**config)

    def load_data(
        self, taxon_data: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich taxonomy data with Tropicos information.

        Args:
            taxon_data: Dictionary containing taxon data
            config: Configuration for the Tropicos enrichment

        Returns:
            Dictionary containing the enriched taxon data
        """
        validated_config = self.validate_config(config)

        # Extract query value from taxon data
        query_value = taxon_data.get(validated_config.query_field)

        if not query_value:
            logger.warning(
                f"No query value found for field {validated_config.query_field} in taxon data"
            )
            return taxon_data

        # Check cache if enabled
        cache_key = f"tropicos_{query_value}"
        if validated_config.cache_results and cache_key in self._cache:
            logger.debug(f"Using cached Tropicos data for {query_value}")
            self.log_messages.append(
                f"[blue]Using cached data for {query_value}[/blue]"
            )
            return self._enrich_taxon_data(taxon_data, self._cache[cache_key])

        try:
            # First, search for the name
            search_url = f"{validated_config.base_url}/Name/Search"
            params = {
                "name": query_value,
                "apikey": validated_config.api_key,
                "format": "json",
                "type": "exact",
            }

            logger.debug(f"Searching Tropicos for {query_value}")
            response = requests.get(search_url, params=params)
            response.raise_for_status()
            search_results = response.json()

            if not search_results or not isinstance(search_results, list):
                logger.warning(f"No results found for {query_value}")
                return taxon_data

            # Use the first result
            name_data = search_results[0]
            name_id = name_data.get("NameId")

            if not name_id:
                logger.warning(f"No NameId found for {query_value}")
                return taxon_data

            # Prepare enrichment data
            enrichment_data = {
                "tropicos_id": name_id,
                "tropicos_name": name_data.get("ScientificName"),
                "tropicos_author": name_data.get("ScientificNameWithAuthors"),
                "tropicos_family": name_data.get("Family"),
                "tropicos_nomenclatural_status": name_data.get("NomenclaturalStatus"),
                "tropicos_symbol": name_data.get("Symbol"),
                "tropicos_rank": name_data.get("RankAbbreviation"),
                "tropicos_accepted_id": name_data.get("AcceptedNameId"),
                "tropicos_accepted_name": name_data.get("AcceptedName"),
                "external_id": str(name_id),
                "external_url": f"http://www.tropicos.org/Name/{name_id}",
            }

            # Respect rate limit
            if validated_config.rate_limit > 0:
                time.sleep(1.0 / validated_config.rate_limit)

            # Fetch images if requested
            if validated_config.include_images:
                images = self._fetch_images(name_id, validated_config)
                if images:
                    enrichment_data["images"] = images
                    # Add first image URLs for quick access
                    if images:
                        enrichment_data["image_url"] = images[0].get("ImageURL")
                        enrichment_data["image_thumbnail"] = images[0].get(
                            "LowResolutionURL"
                        )

            # Fetch synonyms if requested
            if validated_config.include_synonyms:
                synonyms = self._fetch_synonyms(name_id, validated_config)
                if synonyms:
                    enrichment_data["synonyms"] = synonyms
                    enrichment_data["synonym_count"] = len(synonyms)

            # Fetch distributions if requested
            if validated_config.include_distributions:
                distributions = self._fetch_distributions(name_id, validated_config)
                if distributions:
                    enrichment_data["distributions"] = distributions
                    # Extract country list for easy access
                    countries = list(
                        set(
                            [
                                d.get("Country", "")
                                for d in distributions
                                if d.get("Country")
                            ]
                        )
                    )
                    if countries:
                        enrichment_data["distribution_countries"] = countries

            # Fetch references if requested
            if validated_config.include_references:
                references = self._fetch_references(name_id, validated_config)
                if references:
                    enrichment_data["references"] = references[
                        :5
                    ]  # Limit to 5 references
                    enrichment_data["reference_count"] = len(references)

            # Cache results if enabled
            if validated_config.cache_results:
                self._cache[cache_key] = enrichment_data

            self.log_messages.append(
                f"[green][✓] Tropicos data successfully retrieved for {query_value}[/green]"
            )

            return self._enrich_taxon_data(taxon_data, enrichment_data)

        except requests.RequestException as e:
            error_msg = f"Tropicos API request failed for {query_value}: {str(e)}"
            logger.error(error_msg)
            self.log_messages.append(
                f"[bold red]✗ API request failed for {query_value}: {str(e)}[/bold red]"
            )
            return taxon_data
        except Exception as e:
            error_msg = f"Failed to process Tropicos data for {query_value}: {str(e)}"
            logger.error(error_msg)
            self.log_messages.append(
                f"[bold red]✗ Failed to process data for {query_value}: {str(e)}[/bold red]"
            )
            return taxon_data

    def _fetch_images(
        self, name_id: str, config: TropicosEnricherConfig
    ) -> List[Dict[str, Any]]:
        """Fetch images for a given name ID."""
        try:
            url = f"{config.base_url}/Name/{name_id}/Images"
            params = {"apikey": config.api_key, "format": "json"}

            response = requests.get(url, params=params)
            response.raise_for_status()
            images = response.json()

            if isinstance(images, list):
                # Extract relevant image data
                processed_images = []
                for img in images[:5]:  # Limit to 5 images
                    # Log the raw image data for debugging
                    logger.debug(f"Raw image data: {img}")

                    # Get the correct URL fields from Tropicos API
                    image_url = img.get("DetailJpgUrl") or img.get("DetailUrl")
                    thumb_url = img.get("ThumbnailUrl")

                    processed_images.append(
                        {
                            "ImageURL": image_url,
                            "LowResolutionURL": thumb_url,
                            "ImageKindText": img.get("ImageKindText"),
                            "Caption": img.get("Caption")
                            or img.get("ShortDescription"),
                            "CopyrightText": img.get("Copyright"),
                            "CopyrightUrl": img.get("CopyrightUrl"),
                            "LicenseUrl": img.get("LicenseUrl"),
                            "LicenseName": img.get("LicenseName"),
                            "Photographer": img.get("Photographer"),
                            "PhotoDate": img.get("PhotoDate"),
                            "Barcode": img.get("Barcode"),
                            "SpecimenId": img.get("SpecimenId"),
                            "DetailUrl": img.get("DetailUrl"),
                        }
                    )

                return processed_images

            return []

        except Exception as e:
            logger.warning(f"Failed to fetch images for {name_id}: {str(e)}")
            logger.debug("Full error: ", exc_info=True)
            return []
        finally:
            # Respect rate limit
            if config.rate_limit > 0:
                time.sleep(1.0 / config.rate_limit)

    def _fetch_synonyms(
        self, name_id: str, config: TropicosEnricherConfig
    ) -> List[Dict[str, Any]]:
        """Fetch synonyms for a given name ID."""
        try:
            url = f"{config.base_url}/Name/{name_id}/Synonyms"
            params = {"apikey": config.api_key, "format": "json"}

            response = requests.get(url, params=params)
            response.raise_for_status()
            synonyms = response.json()

            if isinstance(synonyms, list):
                return [
                    {
                        "SynonymId": syn.get("NameId"),
                        "SynonymName": syn.get("ScientificName"),
                        "SynonymAuthor": syn.get("ScientificNameWithAuthors"),
                        "NomenclaturalStatus": syn.get("NomenclaturalStatus"),
                    }
                    for syn in synonyms[:10]  # Limit to 10 synonyms
                ]

            return []

        except Exception as e:
            logger.warning(f"Failed to fetch synonyms for {name_id}: {str(e)}")
            return []
        finally:
            # Respect rate limit
            if config.rate_limit > 0:
                time.sleep(1.0 / config.rate_limit)

    def _fetch_distributions(
        self, name_id: str, config: TropicosEnricherConfig
    ) -> List[Dict[str, Any]]:
        """Fetch distribution data for a given name ID."""
        try:
            url = f"{config.base_url}/Name/{name_id}/Distributions"
            params = {"apikey": config.api_key, "format": "json"}

            response = requests.get(url, params=params)
            response.raise_for_status()
            distributions = response.json()

            if isinstance(distributions, list):
                return [
                    {
                        "Country": dist.get("Country"),
                        "State": dist.get("State"),
                        "County": dist.get("County"),
                        "Locality": dist.get("Locality"),
                        "Continent": dist.get("Continent"),
                    }
                    for dist in distributions
                ]

            return []

        except Exception as e:
            logger.warning(f"Failed to fetch distributions for {name_id}: {str(e)}")
            return []
        finally:
            # Respect rate limit
            if config.rate_limit > 0:
                time.sleep(1.0 / config.rate_limit)

    def _fetch_references(
        self, name_id: str, config: TropicosEnricherConfig
    ) -> List[Dict[str, Any]]:
        """Fetch reference data for a given name ID."""
        try:
            url = f"{config.base_url}/Name/{name_id}/References"
            params = {"apikey": config.api_key, "format": "json"}

            response = requests.get(url, params=params)
            response.raise_for_status()
            references = response.json()

            if isinstance(references, list):
                return [
                    {
                        "FullCitation": ref.get("FullCitation"),
                        "AbbreviatedTitle": ref.get("AbbreviatedTitle"),
                        "Year": ref.get("Year"),
                        "ReferenceId": ref.get("ReferenceId"),
                    }
                    for ref in references
                ]

            return []

        except Exception as e:
            logger.warning(f"Failed to fetch references for {name_id}: {str(e)}")
            return []
        finally:
            # Respect rate limit
            if config.rate_limit > 0:
                time.sleep(1.0 / config.rate_limit)

    def _enrich_taxon_data(
        self, taxon_data: Dict[str, Any], enrichment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add enrichment data to taxon data."""
        enriched_data = taxon_data.copy()
        enriched_data["api_enrichment"] = enrichment_data
        return enriched_data
