"""Structured spatial elevation enrichment for plots and shapes."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional

import requests
from pydantic import ConfigDict, Field, model_validator

from niamoto.core.plugins.base import LoaderPlugin, PluginType, register
from niamoto.core.plugins.models import BasePluginParams, PluginConfig

from ._spatial_enrichment import (
    mean,
    point_to_latlon_dict,
    resolve_geometry_from_row,
    sample_geometry_points,
    summarize_geometry,
)

OPEN_METEO_ELEVATION_ENDPOINT = "https://api.open-meteo.com/v1/elevation"


class ApiElevationEnricherParams(BasePluginParams):
    """Parameters for structured elevation enrichment."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Enrich plots and shapes with elevation summaries from remote APIs.",
        }
    )

    api_url: str = Field(default=OPEN_METEO_ELEVATION_ENDPOINT)
    profile: Optional[str] = Field(default="openmeteo_elevation_v1")
    query_field: str = Field(default="name")
    query_param_name: str = Field(default="latitude")
    query_params: Dict[str, Any] = Field(default_factory=dict)
    rate_limit: float = Field(default=1.0, ge=0)
    cache_results: bool = Field(default=True)
    sample_mode: str = Field(default="bbox_grid")
    sample_count: int = Field(default=9, ge=1, le=100)
    include_bbox_summary: bool = Field(default=True)
    geometry_field: Optional[str] = None

    @model_validator(mode="after")
    def validate_profile(self) -> "ApiElevationEnricherParams":
        """Default and validate the structured elevation profile."""

        if not self.profile:
            self.profile = "openmeteo_elevation_v1"
        if self.profile != "openmeteo_elevation_v1":
            raise ValueError("Unsupported elevation enrichment profile")
        return self


class ApiElevationEnricherConfig(PluginConfig):
    """Configuration for API elevation enricher plugin."""

    plugin: Literal["api_elevation_enricher"] = "api_elevation_enricher"
    params: ApiElevationEnricherParams


@register("api_elevation_enricher", PluginType.LOADER)
class ApiElevationEnricher(LoaderPlugin):
    """Enrich a point or geometry with elevation data."""

    config_model = ApiElevationEnricherConfig
    _cache: Dict[str, Dict[str, Any]] = {}

    def __init__(self, db=None, registry=None):
        super().__init__(db, registry)

    def validate_config(self, config: Dict[str, Any]) -> ApiElevationEnricherConfig:
        """Validate plugin configuration."""

        if "params" not in config:
            params = {key: value for key, value in config.items() if key != "plugin"}
            config = {"plugin": "api_elevation_enricher", "params": params}
        return self.config_model(**config)

    def load_data(
        self, entity_data: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Load elevation data for a point or sampled shape."""

        validated_config = self.validate_config(config)
        params = validated_config.params
        geometry_field, geometry = resolve_geometry_from_row(
            entity_data,
            preferred_fields=[params.geometry_field, params.query_field],
        )
        if geometry is None:
            raise ValueError("No geometry found for elevation enrichment")

        cache_key = (
            f"{params.profile}::{params.api_url}::{geometry.wkt}"
            f"::{params.sample_mode}::{params.sample_count}"
            f"::{params.include_bbox_summary}"
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
                summary, processed, raw = self._load_point_elevation(
                    geometry=geometry,
                    params=params,
                    geometry_field=geometry_field,
                )
            else:
                summary, processed, raw = self._load_shape_elevation(
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

    def _load_point_elevation(
        self,
        *,
        geometry,
        params: ApiElevationEnricherParams,
        geometry_field: Optional[str],
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Build the plot-style point summary."""

        location = point_to_latlon_dict(geometry)
        request_payload = [location]
        elevations, raw_response = self._request_openmeteo(request_payload, params)
        if not elevations:
            raise ValueError("Elevation API returned no value for this location")

        summary = {
            "location": location,
            "elevation": {
                "value_m": elevations[0],
                "source_dataset": "open-meteo",
                **location,
            },
            "block_status": {
                "location": "complete",
                "elevation": "complete",
            },
            "block_errors": {},
            "provenance": {
                "profile": "openmeteo_elevation_v1",
                "profile_version": "openmeteo-elevation-v1",
                "mode": "point",
                "geometry_field": geometry_field,
                "geometry_type": geometry.geom_type,
                "endpoints": ["open-meteo/elevation"],
            },
        }
        processed = {
            "location": location,
            "elevation": summary["elevation"],
        }
        raw = {
            "request_points": request_payload,
            "response": raw_response,
        }
        return summary, processed, raw

    def _load_shape_elevation(
        self,
        *,
        geometry,
        params: ApiElevationEnricherParams,
        geometry_field: Optional[str],
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """Build the sampled shape elevation summary."""

        sample_points = sample_geometry_points(
            geometry,
            sample_count=params.sample_count,
            sample_mode=params.sample_mode,
        )
        if not sample_points:
            raise ValueError("Unable to sample the geometry for elevation enrichment")

        request_points = [point_to_latlon_dict(point) for point in sample_points]
        elevations, raw_response = self._request_openmeteo(request_points, params)
        numeric_values = [value for value in elevations if value is not None]
        if not numeric_values:
            raise ValueError("Elevation API returned no values for sampled geometry")

        geometry_summary = summarize_geometry(
            geometry,
            sample_mode=params.sample_mode,
            sample_count=len(sample_points),
            include_bbox_summary=params.include_bbox_summary,
        )
        elevation_summary = {
            "centroid_elevation_m": elevations[0],
            "min_elevation_m": min(numeric_values),
            "max_elevation_m": max(numeric_values),
            "mean_elevation_m": mean(numeric_values),
            "source_dataset": "open-meteo",
        }
        sampling = {
            "strategy": params.sample_mode,
            "sample_mode": params.sample_mode,
            "sample_count": len(sample_points),
        }

        summary = {
            "geometry_summary": geometry_summary,
            "elevation_summary": elevation_summary,
            "sampling": sampling,
            "block_status": {
                "geometry_summary": "complete",
                "elevation_summary": "complete",
            },
            "block_errors": {},
            "provenance": {
                "profile": "openmeteo_elevation_v1",
                "profile_version": "openmeteo-elevation-v1",
                "mode": "shape",
                "geometry_field": geometry_field,
                "geometry_type": geometry.geom_type,
                "endpoints": ["open-meteo/elevation"],
            },
        }
        processed = {
            "geometry_summary": geometry_summary,
            "elevation_summary": elevation_summary,
            "sampling": sampling,
            "sampled_points": [
                {
                    **coords,
                    "elevation_m": elevation,
                }
                for coords, elevation in zip(request_points, elevations)
            ],
        }
        raw = {
            "request_points": request_points,
            "response": raw_response,
        }
        return summary, processed, raw

    def _request_openmeteo(
        self,
        points: List[Dict[str, float]],
        params: ApiElevationEnricherParams,
    ) -> tuple[List[Optional[float]], Dict[str, Any]]:
        """Fetch elevations for one or many latitude/longitude pairs."""

        latitudes = ",".join(str(point["latitude"]) for point in points)
        longitudes = ",".join(str(point["longitude"]) for point in points)
        response = requests.get(
            params.api_url,
            params={
                **(params.query_params or {}),
                "latitude": latitudes,
                "longitude": longitudes,
            },
            timeout=20,
        )
        response.raise_for_status()
        raw_response = response.json()
        values = raw_response.get("elevation")
        if isinstance(values, list):
            return values, raw_response
        if values is None:
            return [], raw_response
        return [values], raw_response
