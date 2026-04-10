import re

import pytest
import requests_mock

from niamoto.core.plugins.loaders.api_elevation_enricher import ApiElevationEnricher
from niamoto.core.plugins.loaders.api_spatial_enricher import ApiSpatialEnricher


@pytest.fixture
def elevation_enricher() -> ApiElevationEnricher:
    return ApiElevationEnricher(db=None)


@pytest.fixture
def spatial_enricher() -> ApiSpatialEnricher:
    return ApiSpatialEnricher(db=None)


def test_spatial_enrichers_can_be_instantiated_without_db():
    assert isinstance(ApiElevationEnricher(), ApiElevationEnricher)
    assert isinstance(ApiSpatialEnricher(), ApiSpatialEnricher)


def test_api_elevation_enricher_loads_point_summary(
    elevation_enricher: ApiElevationEnricher,
    requests_mock: requests_mock.Mocker,
):
    row = {"geometry": "POINT (166.45 -22.27)"}
    config = {
        "plugin": "api_elevation_enricher",
        "params": {
            "api_url": "https://api.open-meteo.com/v1/elevation",
            "profile": "openmeteo_elevation_v1",
            "query_field": "geometry",
            "rate_limit": 0,
            "cache_results": False,
        },
    }

    requests_mock.get(
        "https://api.open-meteo.com/v1/elevation",
        json={"elevation": [412]},
    )

    enriched = elevation_enricher.load_data(row, config)

    assert enriched["api_enrichment"]["location"] == {
        "latitude": -22.27,
        "longitude": 166.45,
    }
    assert enriched["api_enrichment"]["elevation"]["value_m"] == 412
    assert enriched["api_enrichment"]["provenance"]["mode"] == "point"
    assert requests_mock.request_history[0].qs["latitude"] == ["-22.27"]
    assert requests_mock.request_history[0].qs["longitude"] == ["166.45"]


def test_api_elevation_enricher_loads_shape_summary(
    elevation_enricher: ApiElevationEnricher,
    requests_mock: requests_mock.Mocker,
):
    row = {
        "geometry": "POLYGON ((166.4 -22.3, 166.5 -22.3, 166.5 -22.2, 166.4 -22.2, 166.4 -22.3))"
    }
    config = {
        "plugin": "api_elevation_enricher",
        "params": {
            "api_url": "https://api.open-meteo.com/v1/elevation",
            "profile": "openmeteo_elevation_v1",
            "query_field": "geometry",
            "sample_count": 9,
            "sample_mode": "bbox_grid",
            "rate_limit": 0,
            "cache_results": False,
        },
    }

    requests_mock.get(
        "https://api.open-meteo.com/v1/elevation",
        json={"elevation": [100, 110, 120, 130, 140, 150, 160, 170, 180]},
    )

    enriched = elevation_enricher.load_data(row, config)
    summary = enriched["api_enrichment"]

    assert summary["geometry_summary"]["geometry_type"] == "Polygon"
    assert summary["geometry_summary"]["sample_count"] == 9
    assert summary["elevation_summary"]["min_elevation_m"] == 100
    assert summary["elevation_summary"]["max_elevation_m"] == 180
    assert summary["elevation_summary"]["mean_elevation_m"] == pytest.approx(140)
    assert summary["sampling"]["sample_count"] == 9


def test_api_spatial_enricher_loads_point_summary(
    spatial_enricher: ApiSpatialEnricher,
    requests_mock: requests_mock.Mocker,
):
    row = {"geometry": "POINT (166.45 -22.27)"}
    config = {
        "plugin": "api_spatial_enricher",
        "params": {
            "api_url": "https://secure.geonames.org/countrySubdivisionJSON",
            "profile": "geonames_spatial_v1",
            "query_field": "geometry",
            "auth_method": "api_key",
            "auth_params": {"key": "demo"},
            "rate_limit": 0,
            "cache_results": False,
        },
    }

    requests_mock.get(
        "https://secure.geonames.org/countrySubdivisionJSON",
        json={
            "countryCode": "NC",
            "countryName": "New Caledonia",
            "adminName1": "Sud",
            "adminName2": "Nouméa",
        },
    )
    requests_mock.get(
        "https://secure.geonames.org/findNearbyJSON",
        json={
            "geonames": [
                {
                    "name": "Nouméa",
                    "distance": "5.6",
                    "countryName": "New Caledonia",
                    "adminName1": "Sud",
                    "population": 94285,
                }
            ]
        },
    )

    enriched = spatial_enricher.load_data(row, config)
    summary = enriched["api_enrichment"]

    assert summary["location"] == {"latitude": -22.27, "longitude": 166.45}
    assert summary["admin"]["country_name"] == "New Caledonia"
    assert summary["nearby_place"]["name"] == "Nouméa"
    assert summary["provenance"]["mode"] == "point"


def test_api_spatial_enricher_loads_shape_summary(
    spatial_enricher: ApiSpatialEnricher,
    requests_mock: requests_mock.Mocker,
):
    row = {
        "geometry": "POLYGON ((166.4 -22.3, 166.5 -22.3, 166.5 -22.2, 166.4 -22.2, 166.4 -22.3))"
    }
    config = {
        "plugin": "api_spatial_enricher",
        "params": {
            "api_url": "https://secure.geonames.org/countrySubdivisionJSON",
            "profile": "geonames_spatial_v1",
            "query_field": "geometry",
            "auth_method": "api_key",
            "auth_params": {"key": "demo"},
            "sample_count": 5,
            "sample_mode": "bbox_grid",
            "include_nearby_places": True,
            "rate_limit": 0,
            "cache_results": False,
        },
    }

    requests_mock.get(
        re.compile(r"https://secure\.geonames\.org/countrySubdivisionJSON.*"),
        json={
            "countryCode": "NC",
            "countryName": "New Caledonia",
            "adminName1": "Sud",
            "adminName2": "Nouméa",
        },
    )
    requests_mock.get(
        re.compile(r"https://secure\.geonames\.org/findNearbyJSON.*"),
        json={
            "geonames": [
                {
                    "name": "Nouméa",
                    "distance": "5.6",
                    "countryName": "New Caledonia",
                    "adminName1": "Sud",
                }
            ]
        },
    )

    enriched = spatial_enricher.load_data(row, config)
    summary = enriched["api_enrichment"]

    assert summary["geometry_summary"]["geometry_type"] == "Polygon"
    assert summary["admin_summary"]["countries"] == ["New Caledonia"]
    assert summary["admin_summary"]["admin1_values"] == ["Sud"]
    assert summary["sampling"]["sample_count"] == 5
    assert summary["admin_summary"]["nearest_places"][0]["name"] == "Nouméa"
