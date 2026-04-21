"""Multi-source API enrichment runtime for the GUI API."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field
from sqlalchemy import text

from niamoto.common.database import Database
from niamoto.common.table_resolver import quote_identifier, resolve_entity_table
from niamoto.gui.api.context import get_working_directory

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Lifecycle for the single in-memory enrichment job."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    PAUSED_OFFLINE = "paused_offline"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobMode(str, Enum):
    """Execution mode for enrichment jobs."""

    ALL = "all"
    SINGLE = "single"


TERMINAL_JOB_STATUSES = {
    JobStatus.COMPLETED,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
}

GBIF_RICH_MATCH_URL = "https://api.gbif.org/v2/species/match"
TROPICOS_RICH_SEARCH_URL = "https://services.tropicos.org/Name/Search"
COL_DEFAULT_DATASET_KEY = 314774
COL_API_BASE = "https://api.checklistbank.org"
BHL_API_ENDPOINT = "https://www.biodiversitylibrary.org/api3"
INAT_TAXA_ENDPOINT = "https://api.inaturalist.org/v1/taxa"
OPEN_METEO_ELEVATION_ENDPOINT = "https://api.open-meteo.com/v1/elevation"
GEONAMES_SUBDIVISION_ENDPOINT = "https://secure.geonames.org/countrySubdivisionJSON"


class EnrichmentSourceConfig(BaseModel):
    """Normalized enrichment source configuration for a reference."""

    id: str
    label: str
    plugin: str = "api_taxonomy_enricher"
    enabled: bool = False
    api_url: str = ""
    query_field: str = "full_name"
    query_param_name: str = "q"
    profile: Optional[str] = None
    use_name_verifier: bool = False
    name_verifier_preferred_sources: List[str] = Field(default_factory=list)
    name_verifier_threshold: Optional[float] = None
    taxonomy_source: Optional[str] = None
    dataset_key: int = COL_DEFAULT_DATASET_KEY
    include_taxonomy: bool = True
    include_occurrences: bool = True
    include_media: bool = True
    include_places: bool = True
    include_references: bool = True
    include_vernaculars: bool = True
    include_distributions: bool = True
    media_limit: int = 3
    observation_limit: int = 5
    reference_limit: int = 5
    include_publication_details: bool = True
    include_page_preview: bool = True
    title_limit: int = 5
    page_limit: int = 5
    sample_mode: str = "bbox_grid"
    sample_count: int = 9
    include_bbox_summary: bool = True
    include_nearby_places: bool = True
    geometry_field: Optional[str] = None
    response_mapping: Dict[str, str] = Field(default_factory=dict)
    rate_limit: float = 1.0
    cache_results: bool = True
    auth_method: Optional[str] = None
    auth_params: Dict[str, Any] = Field(default_factory=dict)
    query_params: Dict[str, Any] = Field(default_factory=dict)
    chained_endpoints: List[Any] = Field(default_factory=list)
    order: int = 0

    def to_reference_config_entry(self) -> Dict[str, Any]:
        """Serialize back to the import.yml reference enrichment format."""

        return {
            "id": self.id,
            "label": self.label,
            "plugin": self.plugin,
            "enabled": self.enabled,
            "config": {
                "api_url": self.api_url,
                "auth_method": self.auth_method,
                "auth_params": self.auth_params or None,
                "query_params": self.query_params or {},
                "query_field": self.query_field,
                "query_param_name": self.query_param_name,
                "profile": self.profile,
                "use_name_verifier": self.use_name_verifier,
                "name_verifier_preferred_sources": (
                    self.name_verifier_preferred_sources or []
                ),
                "name_verifier_threshold": self.name_verifier_threshold,
                "taxonomy_source": self.taxonomy_source,
                "dataset_key": self.dataset_key,
                "include_taxonomy": self.include_taxonomy,
                "include_occurrences": self.include_occurrences,
                "include_media": self.include_media,
                "include_places": self.include_places,
                "include_references": self.include_references,
                "include_vernaculars": self.include_vernaculars,
                "include_distributions": self.include_distributions,
                "media_limit": self.media_limit,
                "observation_limit": self.observation_limit,
                "reference_limit": self.reference_limit,
                "include_publication_details": self.include_publication_details,
                "include_page_preview": self.include_page_preview,
                "title_limit": self.title_limit,
                "page_limit": self.page_limit,
                "sample_mode": self.sample_mode,
                "sample_count": self.sample_count,
                "include_bbox_summary": self.include_bbox_summary,
                "include_nearby_places": self.include_nearby_places,
                "geometry_field": self.geometry_field,
                "rate_limit": self.rate_limit,
                "cache_results": self.cache_results,
                "response_mapping": self.response_mapping or {},
                "chained_endpoints": self.chained_endpoints or [],
            },
        }


class EnrichmentReferenceConfigResponse(BaseModel):
    """Reference-level enrichment configuration response."""

    reference_name: Optional[str] = None
    enabled: bool = False
    sources: List[EnrichmentSourceConfig] = Field(default_factory=list)


class EnrichmentSourceStats(BaseModel):
    """Progress counters for a single enrichment source."""

    source_id: str
    label: str
    enabled: bool
    total: int
    enriched: int
    pending: int
    status: str = "ready"


class EnrichmentStatsResponse(BaseModel):
    """Aggregated enrichment stats for a reference."""

    reference_name: Optional[str] = None
    entity_total: int = 0
    source_total: int = 0
    total: int = 0
    enriched: int = 0
    pending: int = 0
    sources: List[EnrichmentSourceStats] = Field(default_factory=list)


class EnrichmentJob(BaseModel):
    """Current in-memory enrichment job state."""

    id: str
    reference_name: str
    mode: JobMode
    status: JobStatus
    total: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    already_completed: int = 0
    pending_total: int = 0
    pending_processed: int = 0
    started_at: str
    updated_at: str
    source_ids: List[str] = Field(default_factory=list)
    source_id: Optional[str] = None
    source_label: Optional[str] = None
    current_source_id: Optional[str] = None
    current_source_label: Optional[str] = None
    current_source_processed: int = 0
    current_source_total: int = 0
    current_source_already_completed: int = 0
    current_source_pending_total: int = 0
    current_source_pending_processed: int = 0
    error: Optional[str] = None
    current_entity: Optional[str] = None


class EnrichmentResult(BaseModel):
    """Single source/entity enrichment attempt."""

    reference_name: str
    source_id: str
    source_label: str
    entity_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processed_at: str


class PreviewSourceResult(BaseModel):
    """Preview payload for one source."""

    source_id: str
    source_label: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    raw_data: Optional[Any] = None
    error: Optional[str] = None
    config_used: Dict[str, Any] = Field(default_factory=dict)


class PreviewResponse(BaseModel):
    """Preview response for one or many sources."""

    success: bool
    entity_name: str
    results: List[PreviewSourceResult] = Field(default_factory=list)
    error: Optional[str] = None


class ResultsResponse(BaseModel):
    """Paginated enrichment results response."""

    results: List[EnrichmentResult] = Field(default_factory=list)
    total: int
    page: int
    limit: int


_current_job: Optional[EnrichmentJob] = None
_job_results: List[EnrichmentResult] = []
_job_cancel_flag = False
_job_pause_flag = False
_job_task: Optional[asyncio.Task] = None


def _slugify_source_id(value: str, fallback: str) -> str:
    """Create a stable slug for a source identifier."""

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _guess_source_label(entry: Dict[str, Any], index: int) -> str:
    """Infer a readable source label for legacy configs that lack one."""

    label = entry.get("label") or entry.get("name")
    if isinstance(label, str) and label.strip():
        return label.strip()

    config = entry.get("config") or {}
    api_url = config.get("api_url") if isinstance(config, dict) else None
    if isinstance(api_url, str) and api_url:
        host = urlparse(api_url).hostname or api_url
        host = host.replace("www.", "")
        return host.replace(".", " ").title()

    plugin = entry.get("plugin")
    if isinstance(plugin, str) and plugin.strip():
        return plugin.replace("_", " ").title()

    return f"Source {index + 1}"


def _is_legacy_gbif_source(item: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Return whether a source looks like the old flat GBIF preset."""

    if config.get("profile"):
        return False

    api_url = str(config.get("api_url") or "").lower()
    if "api.gbif.org" in api_url and "/species/match" in api_url:
        return True

    label = str(item.get("label") or item.get("id") or "").lower()
    return label == "gbif"


def _is_legacy_tropicos_source(item: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Return whether a source looks like the old flat Tropicos preset/plugin."""

    if config.get("profile"):
        return False

    plugin = str(item.get("plugin") or "").lower()
    if plugin == "tropicos_enricher":
        return True

    api_url = str(config.get("api_url") or "").lower()
    if "services.tropicos.org" in api_url and "/name/search" in api_url:
        return True

    label = str(item.get("label") or item.get("id") or "").lower()
    return label == "tropicos"


def _is_legacy_inaturalist_source(item: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Return whether a source looks like the old flat iNaturalist preset."""

    if config.get("profile"):
        return False

    api_url = str(config.get("api_url") or "").lower()
    if "api.inaturalist.org" in api_url and "/v1/taxa" in api_url:
        return True

    label = str(item.get("label") or item.get("id") or "").lower()
    return label == "inaturalist"


def _is_endemia_source(item: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Return whether a source targets the public Endemia taxonomy API."""

    api_url = str(config.get("api_url") or "").lower()
    if "api.endemia.nc" in api_url and "/taxons" in api_url:
        return True

    label = str(item.get("label") or item.get("id") or "").lower()
    return label in {"endemia", "endemia nc"}


def _col_search_url(dataset_key: int) -> str:
    """Build the default ChecklistBank search URL for a dataset."""

    return f"{COL_API_BASE}/dataset/{dataset_key}/nameusage/search"


def _is_legacy_openmeteo_source(item: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Return whether a source looks like the old flat Open-Meteo preset."""

    if config.get("profile"):
        return False

    api_url = str(config.get("api_url") or "").lower()
    if "api.open-meteo.com" in api_url and "/elevation" in api_url:
        return True

    label = str(item.get("label") or item.get("id") or "").lower()
    return label in {"open-meteo", "open-meteo elevation"}


def _is_legacy_geonames_source(item: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """Return whether a source looks like the old flat GeoNames preset."""

    if config.get("profile"):
        return False

    api_url = str(config.get("api_url") or "").lower()
    if "geonames.org" in api_url and (
        "countrysubdivision" in api_url or "findnearby" in api_url
    ):
        return True

    label = str(item.get("label") or item.get("id") or "").lower()
    return label.startswith("geonames")


def _normalize_source_entries(raw_enrichment: Any) -> List[EnrichmentSourceConfig]:
    """Normalize reference enrichment config into a source list."""

    if not raw_enrichment:
        return []

    raw_items = raw_enrichment if isinstance(raw_enrichment, list) else [raw_enrichment]
    normalized: List[EnrichmentSourceConfig] = []
    seen_ids: set[str] = set()

    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue

        config = item.get("config") if isinstance(item.get("config"), dict) else {}
        label = _guess_source_label(item, index)
        is_legacy_gbif = _is_legacy_gbif_source(item, config)
        is_legacy_tropicos = _is_legacy_tropicos_source(item, config)
        is_legacy_inaturalist = _is_legacy_inaturalist_source(item, config)
        is_endemia = _is_endemia_source(item, config)
        is_legacy_openmeteo = _is_legacy_openmeteo_source(item, config)
        is_legacy_geonames = _is_legacy_geonames_source(item, config)
        legacy_inaturalist_params = {
            key: value
            for key, value in (config.get("query_params") or {}).items()
            if key not in {"q", "taxon_id", "per_page"}
        }
        legacy_inaturalist_params["is_active"] = str(
            legacy_inaturalist_params.get("is_active", "true")
        )
        base_id = item.get("id") or _slugify_source_id(label, f"source-{index + 1}")
        source_id = base_id
        dedupe_index = 2
        while source_id in seen_ids:
            source_id = f"{base_id}-{dedupe_index}"
            dedupe_index += 1
        seen_ids.add(source_id)

        normalized.append(
            EnrichmentSourceConfig(
                id=source_id,
                label=(
                    "Tropicos"
                    if is_legacy_tropicos and not item.get("label")
                    else (
                        "iNaturalist"
                        if is_legacy_inaturalist and not item.get("label")
                        else (
                            "Open-Meteo Elevation"
                            if is_legacy_openmeteo and not item.get("label")
                            else (
                                "GeoNames"
                                if is_legacy_geonames and not item.get("label")
                                else label
                            )
                        )
                    )
                ),
                plugin=(
                    "api_taxonomy_enricher"
                    if is_legacy_tropicos
                    else (
                        "api_elevation_enricher"
                        if is_legacy_openmeteo
                        else (
                            "api_spatial_enricher"
                            if is_legacy_geonames
                            else item.get("plugin", "api_taxonomy_enricher")
                        )
                    )
                ),
                enabled=bool(item.get("enabled", False)),
                api_url=(
                    GBIF_RICH_MATCH_URL
                    if is_legacy_gbif
                    else (
                        TROPICOS_RICH_SEARCH_URL
                        if is_legacy_tropicos
                        else (
                            INAT_TAXA_ENDPOINT
                            if is_legacy_inaturalist
                            else (
                                OPEN_METEO_ELEVATION_ENDPOINT
                                if is_legacy_openmeteo
                                else (
                                    GEONAMES_SUBDIVISION_ENDPOINT
                                    if is_legacy_geonames
                                    else (
                                        config.get("api_url")
                                        or (
                                            _col_search_url(
                                                int(
                                                    config.get(
                                                        "dataset_key",
                                                        COL_DEFAULT_DATASET_KEY,
                                                    )
                                                )
                                            )
                                            if config.get("profile") == "col_rich"
                                            else (
                                                BHL_API_ENDPOINT
                                                if config.get("profile")
                                                == "bhl_references"
                                                else ""
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                ),
                query_field=config.get("query_field")
                or (
                    "geometry"
                    if is_legacy_openmeteo
                    or is_legacy_geonames
                    or config.get("profile")
                    in {"openmeteo_elevation_v1", "geonames_spatial_v1"}
                    else "full_name"
                ),
                query_param_name=config.get("query_param_name", "q")
                if config.get("profile")
                not in {
                    "col_rich",
                    "bhl_references",
                    "inaturalist_rich",
                    "openmeteo_elevation_v1",
                    "geonames_spatial_v1",
                }
                and not is_legacy_gbif
                and not is_legacy_tropicos
                and not is_legacy_inaturalist
                and not is_legacy_openmeteo
                and not is_legacy_geonames
                else (
                    "scientificName"
                    if is_legacy_gbif
                    else (
                        "name"
                        if is_legacy_tropicos
                        or config.get("profile") == "bhl_references"
                        else (
                            "latitude"
                            if is_legacy_openmeteo
                            or config.get("profile") == "openmeteo_elevation_v1"
                            else "lat"
                        )
                    )
                ),
                profile=(
                    config.get("profile")
                    or ("gbif_rich" if is_legacy_gbif else None)
                    or ("tropicos_rich" if is_legacy_tropicos else None)
                    or ("inaturalist_rich" if is_legacy_inaturalist else None)
                    or ("openmeteo_elevation_v1" if is_legacy_openmeteo else None)
                    or ("geonames_spatial_v1" if is_legacy_geonames else None)
                ),
                use_name_verifier=bool(config.get("use_name_verifier", False)),
                name_verifier_preferred_sources=[
                    str(value)
                    for value in (config.get("name_verifier_preferred_sources") or [])
                    if value is not None and str(value).strip()
                ],
                name_verifier_threshold=(
                    float(config.get("name_verifier_threshold"))
                    if config.get("name_verifier_threshold") is not None
                    else None
                ),
                taxonomy_source=config.get("taxonomy_source")
                or ("col_xr" if is_legacy_gbif else None),
                dataset_key=int(config.get("dataset_key", COL_DEFAULT_DATASET_KEY)),
                include_taxonomy=bool(config.get("include_taxonomy", True)),
                include_occurrences=bool(config.get("include_occurrences", True)),
                include_media=bool(config.get("include_media", True)),
                include_places=bool(config.get("include_places", True)),
                include_references=bool(config.get("include_references", True)),
                include_vernaculars=bool(config.get("include_vernaculars", True)),
                include_distributions=bool(config.get("include_distributions", True)),
                media_limit=int(config.get("media_limit", 3)),
                observation_limit=int(config.get("observation_limit", 5)),
                reference_limit=int(config.get("reference_limit", 5)),
                include_publication_details=bool(
                    config.get("include_publication_details", True)
                ),
                include_page_preview=bool(config.get("include_page_preview", True)),
                title_limit=int(config.get("title_limit", 5)),
                page_limit=int(config.get("page_limit", 5)),
                sample_mode=str(config.get("sample_mode", "bbox_grid")),
                sample_count=int(config.get("sample_count", 9)),
                include_bbox_summary=bool(config.get("include_bbox_summary", True)),
                include_nearby_places=bool(config.get("include_nearby_places", True)),
                geometry_field=(
                    str(config.get("geometry_field"))
                    if config.get("geometry_field")
                    else None
                ),
                response_mapping=(
                    {}
                    if is_legacy_gbif
                    or is_legacy_tropicos
                    or is_legacy_openmeteo
                    or is_legacy_geonames
                    else config.get("response_mapping") or {}
                ),
                rate_limit=float(config.get("rate_limit", 1.0)),
                cache_results=bool(config.get("cache_results", True)),
                auth_method=(
                    "none"
                    if is_endemia
                    and config.get("auth_method") == "api_key"
                    and not str(
                        (config.get("auth_params") or {}).get("key") or ""
                    ).strip()
                    else (
                        "api_key" if is_legacy_tropicos else config.get("auth_method")
                    )
                ),
                auth_params=(
                    {}
                    if is_endemia
                    and config.get("auth_method") == "api_key"
                    and not str(
                        (config.get("auth_params") or {}).get("key") or ""
                    ).strip()
                    else (
                        {
                            "location": "query",
                            "name": "apikey",
                            "key": str(
                                (config.get("auth_params") or {}).get("key") or ""
                            ),
                        }
                        if is_legacy_tropicos
                        else config.get("auth_params") or {}
                    )
                ),
                query_params=(
                    {
                        **(config.get("query_params") or {}),
                        "verbose": str(
                            (config.get("query_params") or {}).get("verbose", "true")
                        ),
                    }
                    if is_legacy_gbif
                    else (
                        {
                            **(config.get("query_params") or {}),
                            "format": str(
                                (config.get("query_params") or {}).get("format", "json")
                            ),
                            "type": str(
                                (config.get("query_params") or {}).get("type", "exact")
                            ),
                        }
                        if is_legacy_tropicos
                        else (
                            legacy_inaturalist_params
                            if is_legacy_inaturalist
                            else (
                                {
                                    **(config.get("query_params") or {}),
                                    "op": str(
                                        (config.get("query_params") or {}).get(
                                            "op", "NameSearch"
                                        )
                                    ),
                                    "format": str(
                                        (config.get("query_params") or {}).get(
                                            "format", "json"
                                        )
                                    ),
                                }
                                if config.get("profile") == "bhl_references"
                                else {**(config.get("query_params") or {})}
                            )
                        )
                    )
                ),
                chained_endpoints=config.get("chained_endpoints") or [],
                order=index,
            )
        )

    return normalized


def _load_import_config() -> Dict[str, Any]:
    """Load import.yml from the working directory."""

    work_dir = get_working_directory()
    config_path = work_dir / "config" / "import.yml"
    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_reference_config_section(reference_name: str) -> Optional[Dict[str, Any]]:
    """Return the raw reference configuration section from import.yml."""

    import_config = _load_import_config()
    entities = import_config.get("entities") or {}
    references = entities.get("references") or {}
    reference = references.get(reference_name)
    return reference if isinstance(reference, dict) else None


def _reference_schema(reference_name: str) -> Dict[str, Any]:
    """Return the raw schema section for a reference."""

    reference_config = _load_reference_config_section(reference_name) or {}
    schema = reference_config.get("schema")
    return schema if isinstance(schema, dict) else {}


def _reference_kind(reference_name: str) -> Optional[str]:
    """Return the configured kind for a reference."""

    reference_config = _load_reference_config_section(reference_name) or {}
    kind = reference_config.get("kind")
    return str(kind) if kind else None


def _reference_has_geometry(reference_name: str) -> bool:
    """Return whether a reference should be treated as spatial."""

    if _reference_kind(reference_name) == "spatial":
        return True

    fields = _reference_schema(reference_name).get("fields") or []
    return any(
        isinstance(field, dict) and str(field.get("type") or "").lower() == "geometry"
        for field in fields
    )


def _reference_geometry_fields(reference_name: str) -> List[str]:
    """Return geometry-declared fields from import.yml."""

    fields = _reference_schema(reference_name).get("fields") or []
    geometry_fields = [
        str(field.get("name"))
        for field in fields
        if isinstance(field, dict)
        and field.get("name")
        and str(field.get("type") or "").lower() == "geometry"
    ]
    if geometry_fields:
        return geometry_fields
    return ["geo_pt", "location", "geometry", "geo_pt_geom", "geom"]


def _reference_id_field(
    reference_name: str, table_columns: Optional[Sequence[str]] = None
) -> str:
    """Return the configured identifier field for a reference."""

    schema = _reference_schema(reference_name)
    configured = schema.get("id_field") or schema.get("id")
    if configured:
        configured_value = str(configured)
        if not table_columns or configured_value in table_columns:
            return configured_value

    if table_columns:
        return "id" if "id" in table_columns else str(table_columns[0])

    return "id"


def _normalize_loaded_row(
    reference_name: str, row: Dict[str, Any], id_field: Optional[str] = None
) -> Dict[str, Any]:
    """Attach helper metadata to a loaded reference row."""

    normalized = dict(row)
    resolved_id_field = id_field or _reference_id_field(reference_name, row.keys())
    entity_id = row.get(resolved_id_field)
    if entity_id is None and resolved_id_field != "id":
        entity_id = row.get("id")

    if entity_id is not None and normalized.get("id") is None:
        normalized["id"] = entity_id
    normalized["_entity_id"] = entity_id
    normalized["_entity_id_field"] = resolved_id_field
    normalized["_geometry_fields"] = _reference_geometry_fields(reference_name)
    return normalized


def _row_entity_id(row: Dict[str, Any]) -> Any:
    """Return the normalized entity identifier for a loaded row."""

    return row.get("_entity_id", row.get("id"))


def get_reference_enrichment_config(
    reference_name: str,
) -> EnrichmentReferenceConfigResponse:
    """Load all enrichment sources for a reference."""

    reference_config = _load_reference_config_section(reference_name)
    if not reference_config:
        return EnrichmentReferenceConfigResponse(reference_name=reference_name)

    sources = _normalize_source_entries(reference_config.get("enrichment"))
    return EnrichmentReferenceConfigResponse(
        reference_name=reference_name,
        enabled=any(source.enabled for source in sources),
        sources=sources,
    )


def _resolve_default_reference_name() -> Optional[str]:
    """Pick the default reference used by legacy non-scoped endpoints."""

    import_config = _load_import_config()
    entities = import_config.get("entities") or {}
    references = entities.get("references") or {}
    if not isinstance(references, dict) or not references:
        return None

    if "taxons" in references:
        return "taxons"

    for reference_name, raw_config in references.items():
        if not isinstance(raw_config, dict):
            continue
        sources = _normalize_source_entries(raw_config.get("enrichment"))
        if any(source.enabled for source in sources):
            return reference_name

    return next(iter(references.keys()), None)


def get_default_enrichment_config() -> EnrichmentReferenceConfigResponse:
    """Load the default reference enrichment config for legacy endpoints."""

    reference_name = _resolve_default_reference_name()
    if not reference_name:
        return EnrichmentReferenceConfigResponse()
    return get_reference_enrichment_config(reference_name)


def _resolve_reference_table_from_db(
    db: Database, reference_name: str
) -> Optional[str]:
    """Resolve a reference table name using the registry first."""

    try:
        from niamoto.core.imports.registry import EntityRegistry

        registry = (
            EntityRegistry(db) if db.has_table(EntityRegistry.ENTITIES_TABLE) else None
        )
    except Exception:
        registry = None

    resolved = resolve_entity_table(
        db, reference_name, registry=registry, kind="reference"
    )
    if resolved:
        return resolved

    for candidate in (
        f"entity_{reference_name}",
        f"reference_{reference_name}",
        reference_name,
    ):
        if db.has_table(candidate):
            return candidate
    return None


def _get_reference_table_name(reference_name: str) -> Optional[str]:
    """Resolve a reference table from the working database."""

    work_dir = get_working_directory()
    if not work_dir:
        return None

    db_path = work_dir / "db" / "niamoto.duckdb"
    if not db_path.exists():
        return None

    try:
        db = Database(str(db_path), read_only=True)
        try:
            return _resolve_reference_table_from_db(db, reference_name)
        finally:
            db.close_db_session()
    except Exception as exc:
        logger.warning(
            "Error resolving table for reference '%s': %s", reference_name, exc
        )
        return None


def _deserialize_extra_data(value: Any) -> Dict[str, Any]:
    """Parse a row extra_data value into a mutable dict."""

    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _extract_stored_sources(
    extra_data: Dict[str, Any], preferred_source_ids: Optional[Sequence[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """Return stored source payloads from legacy or namespaced extra_data."""

    api_enrichment = extra_data.get("api_enrichment")
    if not isinstance(api_enrichment, dict):
        return {}

    sources = api_enrichment.get("sources")
    if isinstance(sources, dict):
        allowed_source_ids = (
            {str(source_id) for source_id in preferred_source_ids}
            if preferred_source_ids
            else None
        )
        return {
            str(source_id): value
            for source_id, value in sources.items()
            if isinstance(value, dict)
            and (allowed_source_ids is None or str(source_id) in allowed_source_ids)
        }

    # Legacy flat payload: map it to the first configured source when possible.
    source_id = preferred_source_ids[0] if preferred_source_ids else "legacy"
    return {
        source_id: {
            "label": extra_data.get("label") or source_id.replace("-", " ").title(),
            "data": api_enrichment,
            "enriched_at": extra_data.get("enriched_at"),
            "status": "completed",
            "legacy": True,
        }
    }


def _has_completed_source(
    extra_data: Dict[str, Any], source_id: str, preferred_source_ids: Sequence[str]
) -> bool:
    """Return whether a given source already has completed enrichment data."""

    sources = _extract_stored_sources(extra_data, preferred_source_ids)
    payload = sources.get(source_id)
    if not isinstance(payload, dict):
        return False

    status = payload.get("status")
    if status and status != "completed":
        return False

    data = payload.get("data")
    return isinstance(data, dict)


def _has_any_source_enrichment(
    extra_data: Dict[str, Any], preferred_source_ids: Sequence[str]
) -> bool:
    """Return whether any source-specific enrichment data exists."""

    return any(
        _has_completed_source(extra_data, source_id, preferred_source_ids)
        for source_id in preferred_source_ids
    ) or bool(_extract_stored_sources(extra_data, preferred_source_ids))


def _merge_source_enrichment_data(
    extra_data: Any, source: EnrichmentSourceConfig, source_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge one source payload into extra_data without clobbering other keys."""

    extra_dict = _deserialize_extra_data(extra_data)
    sources = _extract_stored_sources(extra_dict)
    now = datetime.now().isoformat()
    sources[source.id] = {
        "label": source.label,
        "data": source_data,
        "enriched_at": now,
        "status": "completed",
    }

    extra_dict["api_enrichment"] = {
        "sources": sources,
        "updated_at": now,
    }

    # Legacy writes stored a top-level enriched_at value for the single source.
    extra_dict.pop("enriched_at", None)

    return extra_dict


def _reference_display_column_candidates(reference_name: str) -> List[str]:
    """Return likely human-readable columns for one reference table."""

    reference_config = _load_reference_config_section(reference_name) or {}
    candidates: List[str] = []

    schema = reference_config.get("schema")
    if isinstance(schema, dict):
        name_field = schema.get("name_field")
        if name_field:
            candidates.append(str(name_field))

    relation = reference_config.get("relation")
    if isinstance(relation, dict):
        reference_key = relation.get("reference_key")
        if reference_key:
            candidates.append(str(reference_key))

    candidates.extend(["full_name", "name", "label", "title", "id"])

    deduped: List[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _source_json_path(source_id: str) -> str:
    """Return the JSON path for one namespaced enrichment source."""

    escaped_source_id = source_id.replace("\\", "\\\\").replace('"', '\\"')
    return f'$.api_enrichment.sources."{escaped_source_id}"'


def _can_use_legacy_source_payload(
    source_id: str, preferred_source_ids: Optional[Sequence[str]]
) -> bool:
    """Return whether a source can claim legacy flat api_enrichment payloads."""

    return bool(preferred_source_ids) and preferred_source_ids[0] == source_id


def _count_reference_entities(reference_name: str) -> Optional[int]:
    """Count rows for one reference directly in SQL."""

    work_dir = get_working_directory()
    if not work_dir:
        return None

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_reference_table_name(reference_name)
    if not db_path.exists() or not table_name:
        return None

    try:
        db = Database(str(db_path), read_only=True)
        try:
            quoted_table_name = quote_identifier(db, table_name)
            with db.engine.connect() as connection:
                count = connection.execute(
                    text(f"SELECT COUNT(*) FROM {quoted_table_name}")
                ).scalar()
            return int(count or 0)
        finally:
            db.close_db_session()
    except Exception as exc:
        logger.warning("Error counting rows for '%s': %s", reference_name, exc)
        return None


def _count_completed_rows_for_source(
    reference_name: str,
    source_id: str,
    preferred_source_ids: Optional[Sequence[str]] = None,
) -> Optional[int]:
    """Count completed enriched rows for one source directly in SQL."""

    work_dir = get_working_directory()
    if not work_dir:
        return None

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_reference_table_name(reference_name)
    if not db_path.exists() or not table_name:
        return None

    source_path = _source_json_path(source_id)
    status_path = f"{source_path}.status"
    allow_legacy_payload = _can_use_legacy_source_payload(
        source_id, preferred_source_ids
    )

    where_clauses = [
        "("
        "json_extract(extra_data, :source_path) IS NOT NULL "
        "AND COALESCE(json_extract_string(extra_data, :status_path), 'completed') = 'completed'"
        ")"
    ]
    params: Dict[str, Any] = {
        "source_path": source_path,
        "status_path": status_path,
    }
    if allow_legacy_payload:
        where_clauses.append(
            "("
            "json_extract(extra_data, '$.api_enrichment.sources') IS NULL "
            "AND json_extract(extra_data, '$.api_enrichment') IS NOT NULL"
            ")"
        )

    try:
        db = Database(str(db_path), read_only=True)
        try:
            quoted_table_name = quote_identifier(db, table_name)
            with db.engine.connect() as connection:
                count = connection.execute(
                    text(
                        f"SELECT COUNT(*) FROM {quoted_table_name} "
                        f"WHERE extra_data IS NOT NULL AND ({' OR '.join(where_clauses)})"
                    ),
                    params,
                ).scalar()
            return int(count or 0)
        finally:
            db.close_db_session()
    except Exception as exc:
        logger.warning(
            "Error counting completed rows for '%s' source '%s': %s",
            reference_name,
            source_id,
            exc,
        )
        return None


def _get_results_for_source_sql(
    reference_name: str,
    source_id: str,
    source_label: str,
    page: int,
    limit: int,
    preferred_source_ids: Optional[Sequence[str]] = None,
) -> Optional[ResultsResponse]:
    """Return paginated results for one source using SQL JSON extraction."""

    work_dir = get_working_directory()
    if not work_dir:
        return None

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_reference_table_name(reference_name)
    if not db_path.exists() or not table_name:
        return None

    source_path = _source_json_path(source_id)
    processed_path = f"{source_path}.enriched_at"
    allow_legacy_payload = _can_use_legacy_source_payload(
        source_id, preferred_source_ids
    )

    legacy_select = (
        ", json_extract(extra_data, '$.api_enrichment') AS legacy_payload, "
        "json_extract_string(extra_data, '$.enriched_at') AS legacy_processed_at"
        if allow_legacy_payload
        else ", NULL AS legacy_payload, NULL AS legacy_processed_at"
    )
    legacy_where = (
        " OR (json_extract(extra_data, '$.api_enrichment.sources') IS NULL "
        "AND json_extract(extra_data, '$.api_enrichment') IS NOT NULL)"
        if allow_legacy_payload
        else ""
    )
    order_expression = (
        "COALESCE("
        "json_extract_string(extra_data, :processed_path), "
        "json_extract_string(extra_data, '$.enriched_at')"
        ")"
        if allow_legacy_payload
        else "json_extract_string(extra_data, :processed_path)"
    )

    params: Dict[str, Any] = {
        "source_path": source_path,
        "processed_path": processed_path,
        "limit": max(1, int(limit)),
        "offset": max(0, int(page)) * max(1, int(limit)),
    }

    try:
        import pandas as pd

        db = Database(str(db_path), read_only=True)
        try:
            quoted_table_name = quote_identifier(db, table_name)
            table_columns = pd.read_sql(
                text(f"SELECT * FROM {quoted_table_name} LIMIT 0"), db.engine
            ).columns.tolist()
            if not table_columns:
                return None

            id_field = _reference_id_field(reference_name, table_columns)
            display_field = _configured_reference_display_field(
                reference_name, table_columns, id_field
            )
            quoted_display_field = quote_identifier(db, display_field)

            with db.engine.connect() as connection:
                total = connection.execute(
                    text(
                        f"SELECT COUNT(*) FROM {quoted_table_name} "
                        f"WHERE extra_data IS NOT NULL AND "
                        f"(json_extract(extra_data, :source_path) IS NOT NULL{legacy_where})"
                    ),
                    {"source_path": source_path},
                ).scalar()

                rows = (
                    connection.execute(
                        text(
                            f"SELECT CAST({quoted_display_field} AS VARCHAR) AS entity_name, "
                            f"json_extract(extra_data, :source_path) AS source_payload, "
                            f"json_extract_string(extra_data, :processed_path) AS source_processed_at"
                            f"{legacy_select} "
                            f"FROM {quoted_table_name} "
                            f"WHERE extra_data IS NOT NULL AND "
                            f"(json_extract(extra_data, :source_path) IS NOT NULL{legacy_where}) "
                            f"ORDER BY {order_expression} DESC NULLS LAST "
                            f"LIMIT :limit OFFSET :offset"
                        ),
                        params,
                    )
                    .mappings()
                    .all()
                )

            now = datetime.now().isoformat()
            results: List[EnrichmentResult] = []
            for row in rows:
                source_payload = _deserialize_extra_data(row["source_payload"])
                legacy_payload = _deserialize_extra_data(row["legacy_payload"])
                payload = source_payload or legacy_payload
                if not payload:
                    continue

                is_namespaced_payload = bool(source_payload)
                data = payload.get("data") if is_namespaced_payload else payload
                status = (
                    str(payload.get("status") or "completed")
                    if is_namespaced_payload
                    else "completed"
                )
                error = payload.get("error") if is_namespaced_payload else None
                success = status == "completed" and isinstance(data, dict)
                if not success and not error:
                    continue

                processed_at = (
                    row["source_processed_at"] or row["legacy_processed_at"] or now
                )
                entity_name = str(row["entity_name"] or "").strip() or "Unknown entity"

                results.append(
                    EnrichmentResult(
                        reference_name=reference_name,
                        source_id=source_id,
                        source_label=str(
                            payload.get("label")
                            if is_namespaced_payload
                            else source_label
                        )
                        or source_label,
                        entity_name=entity_name,
                        success=success,
                        data=data if isinstance(data, dict) else None,
                        error=None if success else str(error or status),
                        processed_at=str(processed_at),
                    )
                )

            return ResultsResponse(
                results=results,
                total=int(total or 0),
                page=page,
                limit=limit,
            )
        finally:
            db.close_db_session()
    except Exception as exc:
        logger.warning(
            "Error loading SQL results for '%s' source '%s': %s",
            reference_name,
            source_id,
            exc,
        )
        return None


def _load_reference_rows(
    reference_name: str,
    columns: Optional[Sequence[str]] = None,
    require_extra_data: bool = False,
) -> List[Dict[str, Any]]:
    """Load rows for a reference table with an optional projected column subset."""

    work_dir = get_working_directory()
    if not work_dir:
        return []

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_reference_table_name(reference_name)
    if not db_path.exists() or not table_name:
        return []

    try:
        import pandas as pd

        db = Database(str(db_path), read_only=True)
        try:
            quoted_table_name = quote_identifier(db, table_name)
            table_columns = pd.read_sql(
                text(f"SELECT * FROM {quoted_table_name} LIMIT 0"), db.engine
            ).columns.tolist()
            if not table_columns:
                return []

            id_field = _reference_id_field(reference_name, table_columns)
            selected_columns = list(table_columns)
            if columns is not None:
                selected_columns = [
                    str(column) for column in columns if str(column) in table_columns
                ]
                if not selected_columns:
                    selected_columns = [id_field]

            select_clause = ", ".join(
                quote_identifier(db, column) for column in selected_columns
            )
            where_clause = ""
            if require_extra_data and "extra_data" in table_columns:
                where_clause = " WHERE extra_data IS NOT NULL"

            df = pd.read_sql(
                text(f"SELECT {select_clause} FROM {quoted_table_name}{where_clause}"),
                db.engine,
            )
            rows = df.to_dict("records")
            return [
                _normalize_loaded_row(reference_name, row, id_field=id_field)
                for row in rows
            ]
        finally:
            db.close_db_session()
    except Exception as exc:
        logger.warning("Error loading rows for '%s': %s", reference_name, exc)
        return []


def _load_reference_row(
    reference_name: str, entity_id: Any
) -> Optional[Dict[str, Any]]:
    """Load a single reference row by its configured identifier field."""

    work_dir = get_working_directory()
    if not work_dir:
        return None

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_reference_table_name(reference_name)
    if not db_path.exists() or not table_name:
        return None

    try:
        import pandas as pd

        db = Database(str(db_path), read_only=True)
        try:
            quoted_table_name = quote_identifier(db, table_name)
            table_columns = pd.read_sql(
                text(f"SELECT * FROM {quoted_table_name} LIMIT 0"), db.engine
            ).columns.tolist()
            if not table_columns:
                return None

            id_field = _reference_id_field(reference_name, table_columns)
            quoted_id_field = quote_identifier(db, id_field)
            df = pd.read_sql(
                text(
                    f"SELECT * FROM {quoted_table_name} "
                    f"WHERE {quoted_id_field} = :entity_id LIMIT 1"
                ),
                db.engine,
                params={"entity_id": entity_id},
            )
            if df.empty:
                return None

            row = df.to_dict("records")[0]
            return _normalize_loaded_row(reference_name, row, id_field=id_field)
        finally:
            db.close_db_session()
    except Exception as exc:
        logger.warning(
            "Error loading row for '%s' entity %s: %s", reference_name, entity_id, exc
        )
        return None


def _save_source_enrichment_to_db(
    reference_name: str,
    entity_id: Any,
    source: EnrichmentSourceConfig,
    source_data: Dict[str, Any],
    existing_extra_data: Any,
) -> Optional[Dict[str, Any]]:
    """Persist one source payload into the entity extra_data column."""

    work_dir = get_working_directory()
    if not work_dir:
        return None

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_reference_table_name(reference_name)
    if not db_path.exists() or not table_name:
        return None

    try:
        import pandas as pd

        db = Database(str(db_path))
        try:
            quoted_table_name = quote_identifier(db, table_name)
            table_columns = pd.read_sql(
                text(f"SELECT * FROM {quoted_table_name} LIMIT 0"), db.engine
            ).columns.tolist()
            id_field = _reference_id_field(reference_name, table_columns)
            quoted_id_field = quote_identifier(db, id_field)
            merged = _merge_source_enrichment_data(
                existing_extra_data, source, source_data
            )
            with db.engine.connect() as connection:
                connection.execute(
                    text(
                        f"UPDATE {quoted_table_name} "
                        f"SET extra_data = :extra_data WHERE {quoted_id_field} = :entity_id"
                    ),
                    {
                        "extra_data": json.dumps(merged),
                        "entity_id": entity_id,
                    },
                )
                connection.commit()
            return merged
        finally:
            db.close_db_session()
    except Exception as exc:
        logger.warning(
            "Error saving enrichment for '%s' entity %s source %s: %s",
            reference_name,
            entity_id,
            source.id,
            exc,
        )
        return None


def _compute_reference_stats(
    reference_name: str, sources: Sequence[EnrichmentSourceConfig]
) -> EnrichmentStatsResponse:
    """Compute aggregated and per-source completion counts."""

    enabled_sources = [source for source in sources if source.enabled]
    preferred_source_ids = [source.id for source in enabled_sources]
    entity_total = _count_reference_entities(reference_name)
    if entity_total is None:
        rows = _load_reference_rows(reference_name, columns=["extra_data"])
        entity_total = len(rows)
    else:
        rows = []

    if not enabled_sources:
        return EnrichmentStatsResponse(
            reference_name=reference_name,
            entity_total=entity_total,
            source_total=0,
            total=0,
            enriched=0,
            pending=0,
            sources=[],
        )

    per_source_stats: List[EnrichmentSourceStats] = []
    for source in enabled_sources:
        enriched = _count_completed_rows_for_source(
            reference_name,
            source.id,
            preferred_source_ids,
        )
        if enriched is None:
            enriched = sum(
                1
                for row in rows
                if _has_completed_source(
                    _deserialize_extra_data(row.get("extra_data")),
                    source.id,
                    preferred_source_ids,
                )
            )
        total = entity_total
        per_source_stats.append(
            EnrichmentSourceStats(
                source_id=source.id,
                label=source.label,
                enabled=True,
                total=total,
                enriched=enriched,
                pending=max(total - enriched, 0),
                status="ready",
            )
        )

    total_pairs = entity_total * len(enabled_sources)
    enriched_pairs = sum(source_stats.enriched for source_stats in per_source_stats)

    return EnrichmentStatsResponse(
        reference_name=reference_name,
        entity_total=entity_total,
        source_total=len(enabled_sources),
        total=total_pairs,
        enriched=enriched_pairs,
        pending=max(total_pairs - enriched_pairs, 0),
        sources=per_source_stats,
    )


def _decorate_source_statuses(
    reference_name: str,
    stats: EnrichmentStatsResponse,
    job: Optional[EnrichmentJob],
) -> EnrichmentStatsResponse:
    """Overlay runtime job status onto per-source stats."""

    if not job or job.reference_name != reference_name:
        for source_stats in stats.sources:
            source_stats.status = (
                JobStatus.COMPLETED.value
                if source_stats.pending == 0 and source_stats.total
                else "ready"
            )
        return stats

    for source_stats in stats.sources:
        if source_stats.source_id == job.current_source_id:
            source_stats.status = job.status.value
        elif source_stats.pending == 0 and source_stats.total:
            source_stats.status = JobStatus.COMPLETED.value
        else:
            source_stats.status = "ready"
    return stats


def get_reference_enrichment_stats(reference_name: str) -> EnrichmentStatsResponse:
    """Return current stats for all enabled sources of a reference."""

    config = get_reference_enrichment_config(reference_name)
    stats = _compute_reference_stats(reference_name, config.sources)
    return _decorate_source_statuses(reference_name, stats, _current_job)


def get_default_enrichment_stats() -> EnrichmentStatsResponse:
    """Return legacy global stats for the default reference."""

    config = get_default_enrichment_config()
    if not config.reference_name:
        return EnrichmentStatsResponse()
    return get_reference_enrichment_stats(config.reference_name)


def _build_enricher(plugin_name: str):
    """Instantiate the plugin matching a source configuration."""

    if plugin_name == "api_taxonomy_enricher":
        from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
            ApiTaxonomyEnricher,
        )

        return ApiTaxonomyEnricher()

    if plugin_name == "api_elevation_enricher":
        try:
            from niamoto.core.plugins.loaders.api_elevation_enricher import (
                ApiElevationEnricher,
            )

            return ApiElevationEnricher()
        except ImportError:
            from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
                ApiTaxonomyEnricher,
            )

            return ApiTaxonomyEnricher()

    if plugin_name == "api_spatial_enricher":
        try:
            from niamoto.core.plugins.loaders.api_spatial_enricher import (
                ApiSpatialEnricher,
            )

            return ApiSpatialEnricher()
        except ImportError:
            from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
                ApiTaxonomyEnricher,
            )

            return ApiTaxonomyEnricher()

    from niamoto.core.plugins.loaders.api_taxonomy_enricher import ApiTaxonomyEnricher

    return ApiTaxonomyEnricher()


def _build_plugin_config(
    source: EnrichmentSourceConfig, *, cache_results: Optional[bool] = None
) -> Dict[str, Any]:
    """Build the loader config expected by enricher plugins."""

    return {
        "plugin": source.plugin,
        "params": {
            "api_url": source.api_url,
            "query_field": source.query_field,
            "query_param_name": source.query_param_name,
            "profile": source.profile,
            "use_name_verifier": source.use_name_verifier,
            "name_verifier_preferred_sources": (
                source.name_verifier_preferred_sources or []
            ),
            "name_verifier_threshold": source.name_verifier_threshold,
            "taxonomy_source": source.taxonomy_source,
            "dataset_key": source.dataset_key,
            "include_taxonomy": source.include_taxonomy,
            "include_occurrences": source.include_occurrences,
            "include_media": source.include_media,
            "include_places": source.include_places,
            "include_references": source.include_references,
            "include_vernaculars": source.include_vernaculars,
            "include_distributions": source.include_distributions,
            "media_limit": source.media_limit,
            "observation_limit": source.observation_limit,
            "reference_limit": source.reference_limit,
            "include_publication_details": source.include_publication_details,
            "include_page_preview": source.include_page_preview,
            "title_limit": source.title_limit,
            "page_limit": source.page_limit,
            "sample_mode": source.sample_mode,
            "sample_count": source.sample_count,
            "include_bbox_summary": source.include_bbox_summary,
            "include_nearby_places": source.include_nearby_places,
            "geometry_field": source.geometry_field,
            "response_mapping": source.response_mapping,
            "rate_limit": source.rate_limit,
            "cache_results": source.cache_results
            if cache_results is None
            else cache_results,
            "auth_method": source.auth_method,
            "auth_params": source.auth_params or {},
            "query_params": source.query_params or {},
            "chained_endpoints": source.chained_endpoints or [],
        },
    }


def _entity_name_for_row(row: Dict[str, Any], source: EnrichmentSourceConfig) -> str:
    """Resolve a display name for a row being enriched."""

    for candidate in (
        row.get(source.query_field),
        row.get("full_name"),
        row.get("name"),
        row.get("label"),
        row.get("id"),
    ):
        if candidate is None:
            continue
        value = str(candidate).strip()
        if value:
            return value
    return "Unknown entity"


def _row_display_name(row: Dict[str, Any]) -> str:
    """Resolve a generic display name for a stored reference row."""

    for candidate in (
        row.get("full_name"),
        row.get("name"),
        row.get("label"),
        row.get("title"),
        row.get("id"),
    ):
        if candidate is None:
            continue
        value = str(candidate).strip()
        if value:
            return value
    return "Unknown entity"


def _configured_reference_display_field(
    reference_name: str, table_columns: Sequence[str], id_field: str
) -> str:
    """Pick a configured human-readable column for a reference when available."""

    reference_config = _load_reference_config_section(reference_name) or {}
    schema = reference_config.get("schema")
    if isinstance(schema, dict):
        name_field = schema.get("name_field")
        if name_field and str(name_field) in table_columns:
            return str(name_field)

    relation = reference_config.get("relation")
    if isinstance(relation, dict):
        reference_key = relation.get("reference_key")
        if reference_key and str(reference_key) in table_columns:
            return str(reference_key)

    return _resolve_reference_display_field(table_columns, id_field)


def _reference_row_display_name(reference_name: str, row: Dict[str, Any]) -> str:
    """Resolve the display name for a row using reference-specific config first."""

    display_field = _configured_reference_display_field(
        reference_name, list(row.keys()), row.get("_entity_id_field") or "id"
    )
    candidate = row.get(display_field)
    if candidate is not None:
        value = str(candidate).strip()
        if value:
            return value
    return _row_display_name(row)


def _resolve_reference_display_field(
    table_columns: Sequence[str], id_field: str
) -> str:
    """Pick the most human-friendly column to display reference entities."""

    for candidate in ("full_name", "name", "label", "title", id_field):
        if candidate in table_columns:
            return candidate
    return id_field


def _is_invalid_unicode_error(exc: Exception) -> bool:
    """Return whether an exception comes from invalid unicode in DuckDB rows."""

    return "Invalid unicode" in str(exc)


def _load_reference_display_name_map(
    reference_name: str, id_field: str, display_field: str
) -> Dict[str, str]:
    """Load display names from the source CSV when DB text decoding is broken."""

    reference_config = _load_reference_config_section(reference_name) or {}
    connector = reference_config.get("connector")
    if not isinstance(connector, dict):
        return {}
    if connector.get("type") != "file" or connector.get("format") != "csv":
        return {}

    relative_path = connector.get("path")
    if not relative_path:
        return {}

    file_path = get_working_directory() / str(relative_path)
    if not file_path.exists():
        return {}

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                mapping: Dict[str, str] = {}
                for row in reader:
                    raw_id = row.get(id_field)
                    raw_name = row.get(display_field)
                    if raw_id is None or raw_name is None:
                        continue
                    label = str(raw_name).strip()
                    if not label:
                        continue
                    mapping[str(raw_id)] = label
                return mapping
        except UnicodeDecodeError:
            continue
        except OSError:
            return {}

    return {}


def _ensure_startable_sources(
    reference_name: str, source_id: Optional[str] = None
) -> List[EnrichmentSourceConfig]:
    """Validate and return the sources to run for a job."""

    config = get_reference_enrichment_config(reference_name)
    if not config.sources:
        raise ValueError(
            f"No enrichment configuration found for reference '{reference_name}'"
        )

    if source_id:
        matching_source = next(
            (source for source in config.sources if source.id == source_id), None
        )
        if not matching_source:
            raise ValueError(
                f"No enrichment source '{source_id}' found for reference '{reference_name}'"
            )
        sources = [matching_source]
    else:
        sources = [source for source in config.sources if source.enabled]

    if not sources:
        raise ValueError("No enabled enrichment sources found")

    for source in sources:
        if not source.api_url:
            raise ValueError(f"No API URL configured for source '{source.label}'")
        if (
            source.auth_method == "api_key"
            and not str((source.auth_params or {}).get("key") or "").strip()
        ):
            raise ValueError(f"Missing API key for source '{source.label}'")

    return sources


def _ensure_override_sources(
    source_override: Dict[str, Any], source_id: Optional[str] = None
) -> List[EnrichmentSourceConfig]:
    """Validate and return previewable sources from an unsaved override."""

    override_entry = dict(source_override)
    if source_id and not override_entry.get("id"):
        override_entry["id"] = source_id

    sources = _normalize_source_entries([override_entry])
    if not sources:
        raise ValueError("No enrichment source configuration provided for preview")

    if source_id:
        matching_source = next(
            (source for source in sources if source.id == source_id), None
        )
        if not matching_source:
            raise ValueError(f"No enrichment source '{source_id}' provided for preview")
        sources = [matching_source]

    for source in sources:
        if not source.api_url:
            raise ValueError(f"No API URL configured for source '{source.label}'")
        if (
            source.auth_method == "api_key"
            and not str((source.auth_params or {}).get("key") or "").strip()
        ):
            raise ValueError(f"Missing API key for source '{source.label}'")

    return sources


def _preview_config_used(source: EnrichmentSourceConfig) -> Dict[str, Any]:
    """Return the safe subset of source config exposed in preview responses."""

    config = {
        "api_url": source.api_url,
        "query_field": source.query_field,
        "profile": source.profile,
        "use_name_verifier": source.use_name_verifier,
    }
    if source.profile == "col_rich":
        config.update(
            {
                "dataset_key": source.dataset_key,
                "include_vernaculars": source.include_vernaculars,
                "include_distributions": source.include_distributions,
                "include_references": source.include_references,
                "reference_limit": source.reference_limit,
            }
        )
    elif source.profile == "bhl_references":
        config.update(
            {
                "dataset_key": source.dataset_key,
                "include_publication_details": source.include_publication_details,
                "include_page_preview": source.include_page_preview,
                "title_limit": source.title_limit,
                "page_limit": source.page_limit,
            }
        )
    elif source.profile == "inaturalist_rich":
        config.update(
            {
                "include_occurrences": source.include_occurrences,
                "include_media": source.include_media,
                "include_places": source.include_places,
                "media_limit": source.media_limit,
                "observation_limit": source.observation_limit,
            }
        )
    elif source.profile == "openmeteo_elevation_v1":
        config.update(
            {
                "sample_mode": source.sample_mode,
                "sample_count": source.sample_count,
                "include_bbox_summary": source.include_bbox_summary,
                "geometry_field": source.geometry_field,
            }
        )
    elif source.profile == "geonames_spatial_v1":
        config.update(
            {
                "sample_mode": source.sample_mode,
                "sample_count": source.sample_count,
                "include_bbox_summary": source.include_bbox_summary,
                "include_nearby_places": source.include_nearby_places,
                "geometry_field": source.geometry_field,
            }
        )
    return config


def _source_requires_row_preview(source: EnrichmentSourceConfig) -> bool:
    """Return whether preview should use a full entity row instead of a name string."""

    return source.plugin in {"api_elevation_enricher", "api_spatial_enricher"}


def _get_current_job(reference_name: Optional[str] = None) -> Optional[EnrichmentJob]:
    """Return the current job, optionally scoped to a reference."""

    if _current_job is None:
        return None
    if reference_name and _current_job.reference_name != reference_name:
        return None
    return _current_job


def get_current_job(reference_name: Optional[str] = None) -> Optional[EnrichmentJob]:
    """Public accessor for the current enrichment job."""

    return _get_current_job(reference_name)


async def _run_enrichment_job(
    job_id: str,
    reference_name: str,
    sources: Sequence[EnrichmentSourceConfig],
    mode: JobMode,
) -> None:
    """Background worker executing one or many sources for a reference."""

    global _current_job, _job_results, _job_cancel_flag, _job_pause_flag

    rows = _load_reference_rows(reference_name)
    preferred_source_ids = [source.id for source in sources]

    try:
        if _current_job is None or _current_job.id != job_id:
            return

        if not rows:
            _current_job.status = JobStatus.FAILED
            _current_job.error = f"No entities found to enrich for '{reference_name}'"
            _current_job.updated_at = datetime.now().isoformat()
            return

        source_completed = {
            source.id: sum(
                1
                for row in rows
                if _has_completed_source(
                    _deserialize_extra_data(row.get("extra_data")),
                    source.id,
                    preferred_source_ids,
                )
            )
            for source in sources
        }

        pending_steps: List[tuple[Dict[str, Any], EnrichmentSourceConfig]] = []
        for source in sources:
            for row in rows:
                if _has_completed_source(
                    _deserialize_extra_data(row.get("extra_data")),
                    source.id,
                    preferred_source_ids,
                ):
                    continue
                pending_steps.append((row, source))

        total_steps = len(rows) * len(sources)
        already_completed = sum(source_completed.values())
        _current_job.total = total_steps
        _current_job.processed = already_completed
        _current_job.successful = already_completed
        _current_job.already_completed = already_completed
        _current_job.pending_total = len(pending_steps)
        _current_job.pending_processed = 0
        _current_job.updated_at = datetime.now().isoformat()

        if not pending_steps:
            _current_job.status = JobStatus.COMPLETED
            _current_job.current_entity = None
            _current_job.current_source_id = None
            _current_job.current_source_label = None
            _current_job.updated_at = datetime.now().isoformat()
            return

        consecutive_network_errors = 0
        network_error_types: tuple[type[BaseException], ...] = (
            ConnectionError,
            TimeoutError,
            OSError,
        )
        try:
            import requests

            network_error_types = (
                ConnectionError,
                TimeoutError,
                OSError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            )
        except ImportError:
            pass

        source_initial_completed = dict(source_completed)
        source_pending_processed = {source.id: 0 for source in sources}
        source_totals = {source.id: len(rows) for source in sources}
        source_pending_totals = {
            source.id: sum(
                1
                for row in rows
                if not _has_completed_source(
                    _deserialize_extra_data(row.get("extra_data")),
                    source.id,
                    preferred_source_ids,
                )
            )
            for source in sources
        }
        enrichers: Dict[str, Any] = {}

        for row, source in pending_steps:
            if _current_job is None or _current_job.id != job_id:
                return

            if _job_cancel_flag:
                _current_job.status = JobStatus.CANCELLED
                _current_job.updated_at = datetime.now().isoformat()
                return

            while _job_pause_flag or _current_job.status == JobStatus.PAUSED_OFFLINE:
                if _current_job.status != JobStatus.PAUSED_OFFLINE:
                    _current_job.status = JobStatus.PAUSED
                if _job_cancel_flag:
                    _current_job.status = JobStatus.CANCELLED
                    _current_job.updated_at = datetime.now().isoformat()
                    return
                await asyncio.sleep(0.5)

            if _current_job.status in (JobStatus.PAUSED, JobStatus.PAUSED_OFFLINE):
                _current_job.status = JobStatus.RUNNING
                _current_job.error = None
                consecutive_network_errors = 0

            entity_name = _entity_name_for_row(row, source)
            _current_job.current_entity = entity_name
            _current_job.current_source_id = source.id
            _current_job.current_source_label = source.label
            _current_job.current_source_total = source_totals[source.id]
            _current_job.current_source_processed = source_completed[source.id]
            _current_job.current_source_already_completed = source_initial_completed[
                source.id
            ]
            _current_job.current_source_pending_total = source_pending_totals[source.id]
            _current_job.current_source_pending_processed = source_pending_processed[
                source.id
            ]
            _current_job.updated_at = datetime.now().isoformat()

            try:
                if source.id not in enrichers:
                    enrichers[source.id] = _build_enricher(source.plugin)

                result = enrichers[source.id].load_data(
                    row,
                    _build_plugin_config(source),
                )
                source_data = result.get("api_enrichment", {})
                entity_id = _row_entity_id(row)

                if source_data and entity_id is not None:
                    merged_extra_data = _save_source_enrichment_to_db(
                        reference_name,
                        entity_id,
                        source,
                        source_data,
                        row.get("extra_data"),
                    )
                    if merged_extra_data is not None:
                        row["extra_data"] = merged_extra_data

                _job_results.append(
                    EnrichmentResult(
                        reference_name=reference_name,
                        source_id=source.id,
                        source_label=source.label,
                        entity_name=entity_name,
                        success=True,
                        data=source_data,
                        processed_at=datetime.now().isoformat(),
                    )
                )
                _current_job.successful += 1
                consecutive_network_errors = 0
            except network_error_types as exc:
                consecutive_network_errors += 1
                _job_results.append(
                    EnrichmentResult(
                        reference_name=reference_name,
                        source_id=source.id,
                        source_label=source.label,
                        entity_name=entity_name,
                        success=False,
                        error=f"[Network] {exc}",
                        processed_at=datetime.now().isoformat(),
                    )
                )
                _current_job.failed += 1

                if consecutive_network_errors >= 5:
                    _current_job.status = JobStatus.PAUSED_OFFLINE
                    _current_job.error = (
                        "Automatic pause after repeated network failures. "
                        "Check your internet connection."
                    )
                    _current_job.updated_at = datetime.now().isoformat()
            except Exception as exc:
                _job_results.append(
                    EnrichmentResult(
                        reference_name=reference_name,
                        source_id=source.id,
                        source_label=source.label,
                        entity_name=entity_name,
                        success=False,
                        error=str(exc),
                        processed_at=datetime.now().isoformat(),
                    )
                )
                _current_job.failed += 1
                consecutive_network_errors = 0

            _current_job.processed += 1
            _current_job.pending_processed += 1
            source_completed[source.id] += 1
            source_pending_processed[source.id] += 1
            _current_job.current_source_processed = source_completed[source.id]
            _current_job.current_source_pending_processed = source_pending_processed[
                source.id
            ]
            _current_job.updated_at = datetime.now().isoformat()

            sleep_seconds = 0.0
            if source.rate_limit > 0:
                sleep_seconds = max(0.0, 1.0 / source.rate_limit)
            if sleep_seconds:
                await asyncio.sleep(sleep_seconds)

        _current_job.status = JobStatus.COMPLETED
        _current_job.error = None
        _current_job.current_entity = None
        _current_job.current_source_id = None
        _current_job.current_source_label = None
        _current_job.current_source_already_completed = 0
        _current_job.current_source_pending_total = 0
        _current_job.current_source_pending_processed = 0
        _current_job.updated_at = datetime.now().isoformat()
    except Exception as exc:
        if _current_job is None or _current_job.id != job_id:
            return
        _current_job.status = JobStatus.FAILED
        _current_job.error = str(exc)
        _current_job.updated_at = datetime.now().isoformat()


def _assert_job_can_start() -> None:
    """Reject a new job when a non-terminal one already exists."""

    if _current_job and _current_job.status not in TERMINAL_JOB_STATUSES:
        raise ValueError("An enrichment job is already active")


def start_reference_enrichment(
    reference_name: str, source_id: Optional[str] = None
) -> EnrichmentJob:
    """Start a global or per-source enrichment job for a reference."""

    global _current_job, _job_results, _job_cancel_flag, _job_pause_flag, _job_task

    _assert_job_can_start()
    sources = _ensure_startable_sources(reference_name, source_id)

    _job_cancel_flag = False
    _job_pause_flag = False
    _job_results = []

    now = datetime.now().isoformat()
    single_source = sources[0] if source_id else None
    _current_job = EnrichmentJob(
        id=str(uuid.uuid4()),
        reference_name=reference_name,
        mode=JobMode.SINGLE if source_id else JobMode.ALL,
        status=JobStatus.RUNNING,
        started_at=now,
        updated_at=now,
        source_ids=[source.id for source in sources],
        source_id=single_source.id if single_source else None,
        source_label=single_source.label if single_source else None,
    )

    _job_task = asyncio.create_task(
        _run_enrichment_job(_current_job.id, reference_name, sources, _current_job.mode)
    )

    return _current_job


def start_default_enrichment() -> EnrichmentJob:
    """Legacy start endpoint using the default reference."""

    reference_name = _resolve_default_reference_name()
    if not reference_name:
        raise ValueError("No enrichment configuration found")
    return start_reference_enrichment(reference_name)


def _assert_job_matches(
    reference_name: str,
    source_id: Optional[str] = None,
    *,
    expected_statuses: Sequence[JobStatus],
) -> EnrichmentJob:
    """Validate that the current job matches the requested scope."""

    job = _get_current_job(reference_name)
    if not job or job.status not in expected_statuses:
        raise ValueError("No matching enrichment job found")

    if source_id and job.mode == JobMode.SINGLE and job.source_id != source_id:
        raise ValueError("The active job is running for a different source")

    return job


def pause_reference_enrichment(
    reference_name: str, source_id: Optional[str] = None
) -> Dict[str, Any]:
    """Pause the active enrichment job."""

    global _job_pause_flag

    job = _assert_job_matches(
        reference_name,
        source_id,
        expected_statuses=[JobStatus.RUNNING],
    )
    _job_pause_flag = True
    job.status = JobStatus.PAUSED
    job.updated_at = datetime.now().isoformat()
    return {"message": "Job paused", "job": job}


def pause_default_enrichment() -> Dict[str, Any]:
    """Pause the default enrichment job."""

    if not _current_job:
        raise ValueError("No matching enrichment job found")
    return pause_reference_enrichment(_current_job.reference_name)


def resume_reference_enrichment(
    reference_name: str, source_id: Optional[str] = None
) -> Dict[str, Any]:
    """Resume a paused enrichment job."""

    global _job_pause_flag

    job = _assert_job_matches(
        reference_name,
        source_id,
        expected_statuses=[JobStatus.PAUSED, JobStatus.PAUSED_OFFLINE],
    )
    _job_pause_flag = False
    job.status = JobStatus.RUNNING
    job.error = None
    job.updated_at = datetime.now().isoformat()
    return {"message": "Job resumed", "job": job}


def resume_default_enrichment() -> Dict[str, Any]:
    """Resume the default enrichment job."""

    if not _current_job:
        raise ValueError("No matching enrichment job found")
    return resume_reference_enrichment(_current_job.reference_name)


def cancel_reference_enrichment(
    reference_name: str, source_id: Optional[str] = None
) -> Dict[str, Any]:
    """Cancel the current enrichment job."""

    global _job_cancel_flag

    job = _assert_job_matches(
        reference_name,
        source_id,
        expected_statuses=[
            JobStatus.RUNNING,
            JobStatus.PAUSED,
            JobStatus.PAUSED_OFFLINE,
        ],
    )
    _job_cancel_flag = True
    job.status = JobStatus.CANCELLED
    job.updated_at = datetime.now().isoformat()
    return {"message": "Job cancelled", "job": job}


def cancel_default_enrichment() -> Dict[str, Any]:
    """Cancel the default enrichment job."""

    if not _current_job:
        raise ValueError("No matching enrichment job found")
    return cancel_reference_enrichment(_current_job.reference_name)


def get_results(
    reference_name: Optional[str] = None,
    page: int = 0,
    limit: int = 50,
    source_id: Optional[str] = None,
) -> ResultsResponse:
    """Return paginated enrichment results."""

    resolved_reference_name = reference_name or _resolve_default_reference_name()
    job_results = [
        result
        for result in _job_results
        if (reference_name is None or result.reference_name == reference_name)
        and (source_id is None or result.source_id == source_id)
    ]

    filtered = job_results
    if not filtered and resolved_reference_name:
        config = get_reference_enrichment_config(resolved_reference_name)
        configured_labels = {
            source.id: source.label
            for source in config.sources
            if source.id and source.label
        }
        preferred_source_ids = (
            [source_id] if source_id else (list(configured_labels.keys()) or None)
        )
        requested_source_id = source_id or (
            preferred_source_ids[0]
            if preferred_source_ids and len(preferred_source_ids) == 1
            else None
        )
        if requested_source_id:
            fast_results = _get_results_for_source_sql(
                reference_name=resolved_reference_name,
                source_id=requested_source_id,
                source_label=configured_labels.get(requested_source_id)
                or requested_source_id.replace("-", " ").title(),
                page=page,
                limit=limit,
                preferred_source_ids=list(configured_labels.keys()) or None,
            )
            if fast_results is not None:
                return fast_results

        persisted_results: List[EnrichmentResult] = []
        persisted_columns = [
            *_reference_display_column_candidates(resolved_reference_name),
            "extra_data",
        ]

        for row in _load_reference_rows(
            resolved_reference_name,
            columns=persisted_columns,
            require_extra_data=True,
        ):
            entity_name = _reference_row_display_name(resolved_reference_name, row)
            stored_sources = _extract_stored_sources(
                _deserialize_extra_data(row.get("extra_data")),
                preferred_source_ids,
            )
            for source_id, payload in stored_sources.items():
                if not isinstance(payload, dict):
                    continue

                data = payload.get("data")
                status = str(payload.get("status") or "completed")
                error = payload.get("error")
                success = status == "completed" and isinstance(data, dict)
                if not success and not error:
                    continue

                processed_at = payload.get("enriched_at")
                if not isinstance(processed_at, str) or not processed_at:
                    processed_at = datetime.now().isoformat()

                persisted_results.append(
                    EnrichmentResult(
                        reference_name=resolved_reference_name,
                        source_id=source_id,
                        source_label=str(
                            payload.get("label")
                            or configured_labels.get(source_id)
                            or source_id.replace("-", " ").title()
                        ),
                        entity_name=entity_name,
                        success=success,
                        data=data if isinstance(data, dict) else None,
                        error=None if success else str(error or status),
                        processed_at=processed_at,
                    )
                )

        filtered = sorted(
            persisted_results,
            key=lambda result: result.processed_at,
            reverse=True,
        )

    reversed_results = list(reversed(filtered)) if filtered is job_results else filtered
    start = page * limit
    end = start + limit
    return ResultsResponse(
        results=reversed_results[start:end],
        total=len(filtered),
        page=page,
        limit=limit,
    )


async def preview_reference_enrichment(
    reference_name: str,
    query: str,
    source_id: Optional[str] = None,
    source_override: Optional[Dict[str, Any]] = None,
    entity_id: Optional[Any] = None,
) -> PreviewResponse:
    """Preview enrichment for one entity across one or many sources."""

    try:
        sources = (
            _ensure_override_sources(source_override, source_id)
            if source_override is not None
            else _ensure_startable_sources(reference_name, source_id)
        )
    except ValueError as exc:
        return PreviewResponse(success=False, entity_name=query, error=str(exc))

    results: List[PreviewSourceResult] = []
    spatial_row = (
        _load_reference_row(reference_name, entity_id)
        if entity_id is not None and _reference_has_geometry(reference_name)
        else None
    )
    if (
        entity_id is not None
        and _reference_has_geometry(reference_name)
        and spatial_row is None
    ):
        return PreviewResponse(
            success=False,
            entity_name=query,
            error=f"No entity '{entity_id}' found for reference '{reference_name}'",
        )
    entity_name = (
        _reference_row_display_name(reference_name, spatial_row)
        if spatial_row
        else query
    )

    for source in sources:
        config_used = _preview_config_used(source)
        try:
            enricher = _build_enricher(source.plugin)
            if _source_requires_row_preview(source):
                payload = dict(spatial_row) if spatial_row is not None else {}
                if source.query_field and source.query_field not in payload:
                    payload[source.query_field] = query
                payload.setdefault("name", entity_name or query)
            else:
                payload = {source.query_field: query}
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    enricher.load_data,
                    payload,
                    _build_plugin_config(source, cache_results=False),
                ),
                timeout=10.0,
            )
            source_data = result.get("api_enrichment", {})
            raw_data = result.get("api_response_raw")
            if raw_data is None:
                raw_data = result.get("api_response_processed")
            if raw_data is None:
                raw_data = source_data
            results.append(
                PreviewSourceResult(
                    source_id=source.id,
                    source_label=source.label,
                    success=True,
                    data=source_data,
                    raw_data=raw_data,
                    config_used=config_used,
                )
            )
        except asyncio.TimeoutError:
            results.append(
                PreviewSourceResult(
                    source_id=source.id,
                    source_label=source.label,
                    success=False,
                    error="Preview timeout after 10 seconds",
                    config_used=config_used,
                )
            )
        except Exception as exc:
            results.append(
                PreviewSourceResult(
                    source_id=source.id,
                    source_label=source.label,
                    success=False,
                    error=str(exc),
                    config_used=config_used,
                )
            )

    return PreviewResponse(
        success=any(result.success for result in results),
        entity_name=entity_name,
        results=results,
        error=None
        if any(result.success for result in results)
        else "All previews failed",
    )


async def preview_default_enrichment(
    taxon_name: str, source_id: Optional[str] = None
) -> PreviewResponse:
    """Legacy preview endpoint using the default reference."""

    reference_name = _resolve_default_reference_name()
    if not reference_name:
        return PreviewResponse(
            success=False,
            entity_name=taxon_name,
            error="No enrichment configuration found",
        )
    return await preview_reference_enrichment(
        reference_name, taxon_name, source_id=source_id
    )


def get_entities_for_reference(
    reference_name: str, limit: int = 100, offset: int = 0, search: str = ""
) -> Dict[str, Any]:
    """List reference entities with aggregate enrichment completion metadata."""

    work_dir = get_working_directory()
    if not work_dir:
        return {"entities": [], "total": 0}

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_reference_table_name(reference_name)
    if not db_path.exists() or not table_name:
        return {"entities": [], "total": 0}

    config = get_reference_enrichment_config(reference_name)
    enabled_sources = [source for source in config.sources if source.enabled]
    preferred_source_ids = [source.id for source in enabled_sources]
    query_field = enabled_sources[0].query_field if enabled_sources else "full_name"

    try:
        import pandas as pd

        db = Database(str(db_path), read_only=True)
        try:
            quoted_table_name = quote_identifier(db, table_name)
            table_columns = pd.read_sql(
                text(f"SELECT * FROM {quoted_table_name} LIMIT 0"), db.engine
            ).columns.tolist()
            if not table_columns:
                return {"entities": [], "total": 0, "query_field": query_field}

            id_field = _reference_id_field(reference_name, table_columns)
            display_field = _configured_reference_display_field(
                reference_name, table_columns, id_field
            )
            if query_field not in table_columns:
                if query_field == "geometry":
                    query_field = next(
                        (
                            field
                            for field in _reference_geometry_fields(reference_name)
                            if field in table_columns
                        ),
                        display_field,
                    )
                else:
                    query_field = display_field

            quoted_display_field = quote_identifier(db, display_field)
            params: Dict[str, Any] = {
                "limit": max(1, int(limit)),
                "offset": max(0, int(offset)),
            }
            where_clause = ""
            if search:
                where_clause = (
                    f"WHERE CAST({quoted_display_field} AS VARCHAR) ILIKE :search"
                )
                params["search"] = f"%{search}%"

            count_df = pd.read_sql(
                text(
                    f"SELECT COUNT(*) as count FROM {quoted_table_name} {where_clause}"
                ),
                db.engine,
                params=params,
            )
            total = int(count_df.iloc[0]["count"])

            selected_fields = [id_field, display_field]
            if "extra_data" in table_columns:
                selected_fields.append("extra_data")
            selected_fields_sql = ", ".join(
                quote_identifier(db, field) for field in dict.fromkeys(selected_fields)
            )

            try:
                df = pd.read_sql(
                    text(
                        f"""
                        SELECT {selected_fields_sql} FROM {quoted_table_name}
                        {where_clause}
                        ORDER BY {quoted_display_field}
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    db.engine,
                    params=params,
                )
            except Exception as exc:
                if not _is_invalid_unicode_error(exc):
                    raise

                logger.warning(
                    "Falling back to source-file labels for '%s' because '%s' contains invalid unicode",
                    reference_name,
                    display_field,
                )
                display_name_map = _load_reference_display_name_map(
                    reference_name, id_field, display_field
                )
                if not display_name_map:
                    raise

                fallback_fields = [id_field]
                if "extra_data" in table_columns:
                    fallback_fields.append("extra_data")
                fallback_fields_sql = ", ".join(
                    quote_identifier(db, field)
                    for field in dict.fromkeys(fallback_fields)
                )
                fallback_df = pd.read_sql(
                    text(f"SELECT {fallback_fields_sql} FROM {quoted_table_name}"),
                    db.engine,
                )
                fallback_rows = []
                lowered_search = search.lower().strip()
                for row in fallback_df.to_dict("records"):
                    label = display_name_map.get(str(row.get(id_field)))
                    if not label:
                        continue
                    if lowered_search and lowered_search not in label.lower():
                        continue
                    row[display_field] = label
                    fallback_rows.append(row)

                fallback_rows.sort(key=lambda row: str(row.get(display_field) or ""))
                total = len(fallback_rows)
                df = pd.DataFrame(fallback_rows[offset : offset + max(1, int(limit))])

            entities: List[Dict[str, Any]] = []
            for row in df.to_dict("records"):
                row["_entity_id_field"] = id_field
                extra_data = _deserialize_extra_data(row.get("extra_data"))
                enriched_sources = [
                    source_id
                    for source_id in preferred_source_ids
                    if _has_completed_source(
                        extra_data, source_id, preferred_source_ids
                    )
                ]
                is_fully_enriched = bool(preferred_source_ids) and len(
                    enriched_sources
                ) == len(preferred_source_ids)
                entities.append(
                    {
                        "id": row.get(id_field),
                        "name": _reference_row_display_name(reference_name, row),
                        "enriched": is_fully_enriched,
                        "enriched_sources": enriched_sources,
                        "enriched_count": len(enriched_sources),
                        "total_sources": len(preferred_source_ids),
                    }
                )

            return {
                "entities": entities,
                "total": total,
                "query_field": query_field,
                "display_field": display_field,
            }
        finally:
            db.close_db_session()
    except Exception as exc:
        logger.warning("Error getting entities for '%s': %s", reference_name, exc)
        return {"entities": [], "total": 0, "error": str(exc)}
