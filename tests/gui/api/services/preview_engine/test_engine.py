"""Tests for preview engine transformer execution paths."""

from unittest.mock import MagicMock, patch

import pandas as pd

from niamoto.gui.api.services.preview_engine.engine import PreviewEngine


def _make_engine() -> PreviewEngine:
    return PreviewEngine("/tmp/niamoto-preview.db", "/tmp/niamoto/config")


def test_render_occurrence_uses_transformer_service_pipeline():
    engine = _make_engine()
    db = MagicMock()
    svc = MagicMock()
    group_config = {
        "group_by": "taxons",
        "sources": [
            {
                "name": "occurrences",
                "data": "occurrences",
                "grouping": "taxons",
                "relation": {"plugin": "nested_set"},
            }
        ],
    }
    transformer_config = {
        "source": "occurrences",
        "field": "elevation",
        "bins": [0, 200, 400],
    }
    temp_group_config = {
        "group_by": "taxons",
        "sources": group_config["sources"],
        "widgets_data": {
            "elevation_binned_distribution_bar_plot": {
                "plugin": "binned_distribution",
                "params": transformer_config,
            }
        },
    }

    with (
        patch(
            "niamoto.gui.api.services.preview_engine.engine._build_transformer_config",
            return_value=transformer_config,
        ),
        patch.object(
            engine,
            "_resolve_preview_group_context",
            return_value=(svc, group_config, 42),
        ),
        patch.object(
            engine,
            "_build_preview_group_config",
            return_value=temp_group_config,
        ) as build_group_config,
        patch(
            "niamoto.gui.api.services.preview_engine.engine._build_widget_params_for_preview",
            return_value={},
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.render_widget",
            return_value="<div>ok</div>",
        ) as render_widget,
    ):
        svc.transform_single_widget.return_value = {"counts": [3, 1]}

        result = engine._render_dynamic_preview(
            "elevation_binned_distribution_bar_plot",
            "elevation",
            "binned_distribution",
            "bar_plot",
            "occurrences",
            "taxons",
            "42",
            {"legend": True},
            db,
            [],
        )

    assert result == "<div>ok</div>"
    build_group_config.assert_called_once_with(
        group_config,
        "elevation_binned_distribution_bar_plot",
        "binned_distribution",
        transformer_config,
    )
    svc.transform_single_widget.assert_called_once_with(
        temp_group_config,
        "elevation_binned_distribution_bar_plot",
        42,
    )
    render_widget.assert_called_once_with(
        db,
        "bar_plot",
        {"counts": [3, 1]},
        {"legend": True},
        "Elevation",
    )


def test_render_entity_source_uses_transformer_service_pipeline():
    engine = _make_engine()
    db = MagicMock()
    svc = MagicMock()
    group_config = {
        "group_by": "plots",
        "sources": [
            {
                "name": "occurrences",
                "data": "occurrences",
                "grouping": "plots",
                "relation": {"plugin": "join_table"},
            }
        ],
    }
    transformer_config = {
        "source": "plots",
        "field": "area",
        "stats": ["mean"],
    }
    temp_group_config = {
        "group_by": "plots",
        "sources": group_config["sources"],
        "widgets_data": {
            "area_field_aggregator_info_grid": {
                "plugin": "field_aggregator",
                "params": transformer_config,
            }
        },
    }

    with (
        patch(
            "niamoto.gui.api.services.preview_engine.engine._build_transformer_config",
            return_value=transformer_config,
        ),
        patch.object(
            engine,
            "_resolve_preview_group_context",
            return_value=(svc, group_config, 7),
        ),
        patch.object(
            engine,
            "_build_preview_group_config",
            return_value=temp_group_config,
        ) as build_group_config,
        patch(
            "niamoto.gui.api.services.preview_engine.engine._build_widget_params_for_preview",
            return_value={},
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.render_widget",
            return_value="<div>entity</div>",
        ) as render_widget,
    ):
        svc.transform_single_widget.return_value = {"value": 12.5}

        result = engine._render_dynamic_preview(
            "area_field_aggregator_info_grid",
            "area",
            "field_aggregator",
            "info_grid",
            "plots",
            "plots",
            "7",
            {"compact": True},
            db,
            [],
        )

    assert result == "<div>entity</div>"
    build_group_config.assert_called_once_with(
        group_config,
        "area_field_aggregator_info_grid",
        "field_aggregator",
        transformer_config,
    )
    svc.transform_single_widget.assert_called_once_with(
        temp_group_config,
        "area_field_aggregator_info_grid",
        7,
    )
    render_widget.assert_called_once_with(
        db,
        "info_grid",
        {"value": 12.5},
        {"compact": True},
        "Area",
    )


def test_render_occurrence_falls_back_without_group_config():
    engine = _make_engine()
    db = MagicMock()
    transformer_config = {
        "source": "occurrences",
        "field": "elevation",
        "bins": [0, 200, 400],
    }
    sample_data = pd.DataFrame({"elevation": [120, 250]})

    with (
        patch(
            "niamoto.gui.api.services.preview_engine.engine._build_transformer_config",
            return_value=transformer_config,
        ),
        patch.object(engine, "_resolve_preview_group_context", return_value=None),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.load_import_config",
            return_value={"imports": []},
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.get_hierarchy_info",
            return_value={"reference_name": "taxons"},
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.find_representative_entity",
            return_value={"id": 1},
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.load_sample_data",
            return_value=sample_data,
        ) as load_sample_data,
        patch(
            "niamoto.gui.api.services.preview_engine.engine.execute_transformer",
            return_value={"counts": [1, 1]},
        ) as execute_transformer,
        patch(
            "niamoto.gui.api.services.preview_engine.engine._build_widget_params_for_preview",
            return_value={},
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.render_widget",
            return_value="<div>fallback</div>",
        ) as render_widget,
    ):
        result = engine._render_dynamic_preview(
            "elevation_binned_distribution_bar_plot",
            "elevation",
            "binned_distribution",
            "bar_plot",
            "occurrences",
            "taxons",
            None,
            {"legend": False},
            db,
            [],
        )

    assert result == "<div>fallback</div>"
    load_sample_data.assert_called_once_with(db, {"id": 1}, transformer_config)
    execute_transformer.assert_called_once_with(
        db,
        "binned_distribution",
        transformer_config,
        sample_data,
    )
    render_widget.assert_called_once_with(
        db,
        "bar_plot",
        {"counts": [1, 1]},
        {"legend": False},
        "Elevation",
    )
