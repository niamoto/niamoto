"""Tests for shared preview utility helpers."""

from __future__ import annotations


import pytest

from niamoto.gui.api.services import preview_utils


def test_error_html_escapes_user_content():
    payload = preview_utils.error_html("<script>alert('x')</script>")

    assert "<script>" not in payload
    assert "&lt;script&gt;alert" in payload


def test_preprocess_data_for_widget_applies_known_adapters():
    donut_data = preview_utils.preprocess_data_for_widget(
        {"bins": [0, 10, 20], "counts": [3, 7], "percentages": [30, 70]},
        "binned_distribution",
        "donut_chart",
    )
    gauge_data = preview_utils.preprocess_data_for_widget(
        {"height": {"value": 18, "units": "m"}},
        "field_aggregator",
        "radial_gauge",
    )

    assert donut_data == {
        "labels": ["0-10", "10-20"],
        "counts": [3, 7],
        "percentages": [30, 70],
    }
    assert gauge_data == {"value": 18, "unit": "m"}


def test_execute_transformer_wraps_plugin_errors(monkeypatch):
    class BrokenTransformer:
        def __init__(self, db=None):
            self.db = db

        def transform(self, data, config):
            raise RuntimeError("bad payload")

    monkeypatch.setattr(
        preview_utils.PluginRegistry,
        "get_plugin",
        lambda plugin_name, plugin_type: BrokenTransformer,
    )

    with pytest.raises(ValueError) as exc_info:
        preview_utils.execute_transformer(
            db=None,
            plugin_name="broken_transformer",
            params={"field": "dbh"},
            data={"value": 1},
        )

    assert "Transformer error: bad payload" in str(exc_info.value)


def test_render_widget_validates_params_and_returns_error_html_on_failure(monkeypatch):
    validated = {}

    class FakeSchema:
        @staticmethod
        def model_validate(params):
            validated.update(params)
            return {"validated": True, **params}

    class GoodWidget:
        param_schema = FakeSchema

        def __init__(self, db=None):
            self.db = db

        def render(self, data, params):
            return f"<div>{params['title']}:{params['validated']}</div>"

    class BrokenWidget:
        param_schema = None

        def __init__(self, db=None):
            self.db = db

        def render(self, data, params):
            raise RuntimeError("render failed")

    monkeypatch.setattr(
        preview_utils.PluginRegistry,
        "get_plugin",
        lambda plugin_name, plugin_type: GoodWidget,
    )
    html = preview_utils.render_widget(
        db=None,
        plugin_name="bar_plot",
        data={"counts": [1]},
        params={"height": 300},
        title="Preview",
    )

    monkeypatch.setattr(
        preview_utils.PluginRegistry,
        "get_plugin",
        lambda plugin_name, plugin_type: BrokenWidget,
    )
    error_payload = preview_utils.render_widget(
        db=None,
        plugin_name="broken_widget",
        data={"counts": [1]},
        title="Broken",
    )

    assert html == "<div>Preview:True</div>"
    assert validated == {"title": "Preview", "height": 300}
    assert "Widget render error: render failed" in error_payload


def test_parse_wkt_to_geojson_handles_supported_shapes():
    point = preview_utils.parse_wkt_to_geojson("POINT Z (166.4 -22.3 0)")
    polygon = preview_utils.parse_wkt_to_geojson("POLYGON ((0 0, 1 0, 1 1, 0 0))")
    multipolygon = preview_utils.parse_wkt_to_geojson(
        "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 0)), ((2 2, 3 2, 3 3, 2 2)))"
    )
    unsupported = preview_utils.parse_wkt_to_geojson("LINESTRING (0 0, 1 1)")

    assert point == {"type": "Point", "coordinates": [166.4, -22.3]}
    assert polygon == {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]],
    }
    assert multipolygon == {
        "type": "MultiPolygon",
        "coordinates": [
            [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]],
            [[[2.0, 2.0], [3.0, 2.0], [3.0, 3.0], [2.0, 2.0]]],
        ],
    }
    assert unsupported is None
