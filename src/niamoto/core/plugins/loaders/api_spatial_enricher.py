"""Structured spatial context enrichment for plots and shapes."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional

import requests
from pydantic import ConfigDict, Field, model_validator

from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.core.plugins.models import BasePluginParams, PluginConfig

from ._spatial_enrichment import (
    point_to_latlon_dict,
    resolve_geometry_from_row,
    sample_geometry_points,
    summarize_geometry,
)

GEONAMES_SUBDIVISION_ENDPOINT = "https://secure.geonames.org/countrySubdivisionJSON"
GEONAMES_NEARBY_ENDPOINT = "https://secure.geonames.org/findNearbyJSON"


class ApiSpatialEnricherParams(BasePluginParams):
    """Parameters for structured spatial context enrichment."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Enrich plots and shapes with geographic context from remote APIs.",
        }
    )

    api_url: str = Field(default=GEONAMES_SUBDIVISION_ENDPOINT)
    profile: Optional[str] = Field(default="geonames_spatial_v1")
    query_field: str = Field(default="name")
    query_params: Dict[str, Any] = Field(default_factory=dict)
    rate_limit: float = Field(default=1.0, ge=0)
    cache_results: bool = Field(default=True)
    sample_mode: str = Field(default="bbox_grid")
    sample_count: int = Field(default=9, ge=1, le=100)
    include_bbox_summary: bool = Field(default=True)
    include_nearby_places: bool = Field(default=True)
    geometry_field: Optional[str] = None
    auth_method: Literal["none", "api_key"] = Field(default="api_key")
    auth_params: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_profile(self) -> "ApiSpatialEnricherParams":
        """Default and validate the structured GeoNames profile."""

        if not self.profile:
            self.profile = "geonames_spatial_v1"
        if self.profile != "geonames_spatial_v1":
            raise ValueError("Unsupported spatial enrichment profile")
        if self.auth_method != "api_key":
            raise ValueError(
                "GeoNames spatial enrichment requires api_key authentication"
            )
        if not str(self.auth_params.get("key") or "").strip():
            raise ValueError("GeoNames spatial enrichment requires a username")
        return self


class ApiSpatialEnricherConfig(PluginConfig):
    """Configuration for API spatial enricher plugin."""

    plugin: Literal["api_spatial_enricher"] = "api_spatial_enricher"
    params: ApiSpatialEnricherParams


@register("api_spatial_enricher", PluginType.LOADER)
class ApiSpatialEnricher(LoaderPlugin):
    """Enrich a point or geometry with GeoNames administrative context."""

    config_model = ApiSpatialEnricherConfig
    _cache: Dict[str, Dict[str, Any]] = {}

    def __init__(self, db=None, registry=None):
        super().__init__(db, registry)

    def validate_config(self, config: Dict[str, Any]) -> ApiSpatialEnricherConfig:
        """Validate plugin configuration."""

        if "params" not in config:
            params = {key: value for key, value in config.items() if key != "plugin"}
            config = {"plugin": "api_spatial_enricher", "params": params}
        return self.config_model(**config)

    def load_data(
        self, entity_data: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Load spatial context for a point or sampled shape."""

        validated_config = self.validate_config(config)
        params = validated_config.params
        geometry_field, geometry = resolve_geometry_from_row(
            entity_data,
            preferred_fields=[params.geometry_field, params.query_field],
        )
        if geometry is None:
            raise ValueError("No geometry found for spatial enrichment")

        cache_key = (
            f"{params.profile}::{params.api_url}::{geometry.wkt}"
            f"::{params.sample_mode}::{params.sample_count}"
            f"::{params.include_bbox_summary}::{params.include_nearby_places}"
            f"::{params.auth_params.get('key', '')}"
        )
        if params.cache_results and cache_key in self._cache:
            cached = self._cache[cache_key]
            return {
                **entity_data,
                "api_enrichment": cached["mapped"],
                "api_response_processed": cached["processed"],
                "api_response_raw": cached["raw"],
            }

        try:
            if geometry.geom_type == "Point":
                summary, processed, raw = self._load_point_context(
                    geometry=geometry,
                    params=params,
                    geometry_field=geometry_field,
                )
            else:
                summary, processed, raw = self._load_shape_context(
                    geometry=geometry,
                    params=params,
                    geometry_field=geometry_field,
                )

            if params.cache_results:
                self._cache[cache_key] = {
                    "mapped": summary,
                    "processed": processed,
                    "raw": raw,
                }

            return {
                **entity_data,
                "api_enrichment": summary,
                "api_response_processed": processed,
                "api_response_raw": raw,
            }
        finally:
            if params.rate_limit > 0:
                time.sleep(1.0 / params.rate_limit)

    def _load_point_context(
        self,
        *,
        geometry,
        params: ApiSpatialEnricherParams,
        geometry_field: Optional[str],
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Build the point-style plot summary."""

        location = point_to_latlon_dict(geometry)
        admin = self._geonames_subdivision(location, params)
        nearby = (
            self._geonames_nearby(location, params)
            if params.include_nearby_places
            else {}
        )

        summary = {
            "location": location,
            "admin": admin,
            "nearby_place": nearby,
            "block_status": {
                "location": "complete",
                "admin": "complete",
                "nearby_place": "complete"
                if params.include_nearby_places
                else "disabled",
            },
            "block_errors": {},
            "provenance": {
                "profile": "geonames_spatial_v1",
                "profile_version": "geonames-spatial-v1",
                "mode": "point",
                "geometry_field": geometry_field,
                "geometry_type": geometry.geom_type,
                "endpoints": ["GeoNames countrySubdivisionJSON"]
                + (["GeoNames findNearbyJSON"] if params.include_nearby_places else []),
            },
        }
        processed = {
            "location": location,
            "admin": admin,
            "nearby_place": nearby,
        }
        raw = {
            "subdivision": admin.get("_raw", {}),
            "nearby": nearby.get("_raw", {}),
        }
        self._strip_internal_raw(summary)
        self._strip_internal_raw(processed)
        return summary, processed, raw

    def _load_shape_context(
        self,
        *,
        geometry,
        params: ApiSpatialEnricherParams,
        geometry_field: Optional[str],
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Build the sampled shape summary."""

        sample_points = sample_geometry_points(
            geometry,
            sample_count=params.sample_count,
            sample_mode=params.sample_mode,
        )
        if not sample_points:
            raise ValueError("Unable to sample the geometry for spatial enrichment")

        sample_locations = [point_to_latlon_dict(point) for point in sample_points]
        subdivision_payloads = [
            self._geonames_subdivision(location, params)
            for location in sample_locations
        ]
        admin_summary = self._summarize_admin(subdivision_payloads)
        nearby_payloads = (
            [
                self._geonames_nearby(location, params)
                for location in sample_locations[: min(3, len(sample_locations))]
            ]
            if params.include_nearby_places
            else []
        )
        if nearby_payloads:
            admin_summary["nearest_places"] = self._summarize_nearby_places(
                nearby_payloads
            )

        geometry_summary = summarize_geometry(
            geometry,
            sample_mode=params.sample_mode,
            sample_count=len(sample_points),
            include_bbox_summary=params.include_bbox_summary,
        )
        sampling = {
            "strategy": params.sample_mode,
            "sample_mode": params.sample_mode,
            "sample_count": len(sample_points),
        }

        summary = {
            "geometry_summary": geometry_summary,
            "admin_summary": admin_summary,
            "sampling": sampling,
            "block_status": {
                "geometry_summary": "complete",
                "admin_summary": "complete",
            },
            "block_errors": {},
            "provenance": {
                "profile": "geonames_spatial_v1",
                "profile_version": "geonames-spatial-v1",
                "mode": "shape",
                "geometry_field": geometry_field,
                "geometry_type": geometry.geom_type,
                "endpoints": ["GeoNames countrySubdivisionJSON"]
                + (["GeoNames findNearbyJSON"] if params.include_nearby_places else []),
            },
        }
        processed = {
            "geometry_summary": geometry_summary,
            "admin_summary": admin_summary,
            "sampling": sampling,
            "sampled_points": [
                {
                    **location,
                    "country_name": payload.get("country_name"),
                    "admin1": payload.get("admin1"),
                    "admin2": payload.get("admin2"),
                }
                for location, payload in zip(sample_locations, subdivision_payloads)
            ],
        }
        raw = {
            "subdivisions": [
                payload.get("_raw", {}) for payload in subdivision_payloads
            ],
            "nearby": [payload.get("_raw", {}) for payload in nearby_payloads],
        }
        self._strip_internal_raw(summary)
        self._strip_internal_raw(processed)
        return summary, processed, raw

    def _geonames_subdivision(
        self, location: Dict[str, float], params: ApiSpatialEnricherParams
    ) -> Dict[str, Any]:
        """Reverse geocode a point into subdivision data."""

        response = requests.get(
            params.api_url or GEONAMES_SUBDIVISION_ENDPOINT,
            params={
                **(params.query_params or {}),
                "lat": location["latitude"],
                "lng": location["longitude"],
                "username": params.auth_params.get("key"),
            },
            timeout=20,
        )
        response.raise_for_status()
        raw = response.json()
        return {
            "country_code": raw.get("countryCode"),
            "country_name": raw.get("countryName"),
            "admin1": raw.get("adminName1") or raw.get("adminCode1"),
            "admin2": raw.get("adminName2") or raw.get("adminCode2"),
            "_raw": raw,
        }

    def _geonames_nearby(
        self, location: Dict[str, float], params: ApiSpatialEnricherParams
    ) -> Dict[str, Any]:
        """Retrieve the closest named place for a point."""

        response = requests.get(
            self._nearby_endpoint(params.api_url),
            params={
                **(params.query_params or {}),
                "lat": location["latitude"],
                "lng": location["longitude"],
                "featureClass": "P",
                "maxRows": 5,
                "username": params.auth_params.get("key"),
            },
            timeout=20,
        )
        response.raise_for_status()
        raw = response.json()
        places = raw.get("geonames") or []
        first = places[0] if places else {}
        return {
            "name": first.get("name"),
            "distance_km": first.get("distance"),
            "country_name": first.get("countryName"),
            "admin1": first.get("adminName1"),
            "population": first.get("population"),
            "_raw": raw,
        }

    def _summarize_admin(self, subdivisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a compact shape admin summary from sampled points."""

        countries = sorted(
            {
                str(item.get("country_name"))
                for item in subdivisions
                if item.get("country_name")
            }
        )
        admin1_values = sorted(
            {str(item.get("admin1")) for item in subdivisions if item.get("admin1")}
        )
        admin2_values = sorted(
            {str(item.get("admin2")) for item in subdivisions if item.get("admin2")}
        )
        return {
            "countries": countries,
            "admin1_values": admin1_values,
            "admin2_values": admin2_values,
            "sample_count": len(subdivisions),
        }

    def _summarize_nearby_places(
        self, nearby_payloads: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build a deduplicated compact list of nearby places."""

        seen: Dict[str, Dict[str, Any]] = {}
        for payload in nearby_payloads:
            name = payload.get("name")
            if not name:
                continue
            key = str(name)
            if key not in seen:
                seen[key] = {
                    "name": name,
                    "country_name": payload.get("country_name"),
                    "admin1": payload.get("admin1"),
                    "distance_km": payload.get("distance_km"),
                }
        return list(seen.values())

    def _nearby_endpoint(self, api_url: str) -> str:
        """Derive the findNearby endpoint from the configured subdivision URL."""

        if not api_url:
            return GEONAMES_NEARBY_ENDPOINT
        return api_url.replace("countrySubdivisionJSON", "findNearbyJSON")

    def _strip_internal_raw(self, payload: Dict[str, Any]) -> None:
        """Remove internal `_raw` placeholders from processed outputs."""

        for value in payload.values():
            if isinstance(value, dict) and "_raw" in value:
                value.pop("_raw", None)
