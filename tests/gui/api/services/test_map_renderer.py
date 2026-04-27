"""Tests for map rendering service fallbacks and dispatch."""

from __future__ import annotations

import pytest

from niamoto.gui.api.services.map_renderer import MapConfig, MapRenderer


def test_render_rejects_invalid_geojson():
    assert MapRenderer.render({}) == "<p class='info'>No valid GeoJSON data</p>"


def test_render_rejects_empty_feature_collection():
    html = MapRenderer.render({"type": "FeatureCollection", "features": []})

    assert html == "<p class='info'>No features to display</p>"


def test_render_computes_center_and_zoom_before_plotly_dispatch(monkeypatch):
    captured = {}

    def fake_render_plotly(cls, geojson, config):
        captured["config"] = config
        return "<div>plotly-map</div>"

    monkeypatch.setattr(
        MapRenderer,
        "_render_plotly",
        classmethod(fake_render_plotly),
    )
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [166.4, -22.3]},
                "properties": {"name": "Aoupinié"},
            }
        ],
    }

    html = MapRenderer.render(geojson, config=MapConfig(), engine="plotly")

    assert html == "<div>plotly-map</div>"
    assert captured["config"].center_lat == pytest.approx(-22.3)
    assert captured["config"].center_lon == pytest.approx(166.4)
    assert captured["config"].zoom == 12.0


def test_render_dispatches_to_leaflet_engine(monkeypatch):
    def fake_render_leaflet(cls, geojson, config):
        return "<div>leaflet-map</div>"

    monkeypatch.setattr(
        MapRenderer,
        "_render_leaflet",
        classmethod(fake_render_leaflet),
    )
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1, 2]},
                "properties": {},
            }
        ],
    }

    assert MapRenderer.render(geojson, engine="leaflet") == "<div>leaflet-map</div>"


def test_render_plotly_uses_feature_label_for_hover_text():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [166.4, -22.3]},
                "properties": {"id": "plot-1", "label": "Preferred label"},
            }
        ],
    }

    html = MapRenderer.render(geojson, config=MapConfig(), engine="plotly")

    assert "Preferred label" in html
