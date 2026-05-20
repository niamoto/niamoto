"""Tests for preview engine transformer execution paths and caching."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine

from niamoto.gui.api.services.preview_engine import engine as preview_engine_module
from niamoto.gui.api.services.preview_engine.engine import PreviewEngine
from niamoto.gui.api.services.preview_engine.models import PreviewRequest


def _make_engine() -> PreviewEngine:
    return PreviewEngine("/tmp/niamoto-preview.db", "/tmp/niamoto/config")


def test_compute_etag_includes_mode_and_inline_configuration():
    engine = _make_engine()
    base = PreviewRequest(
        template_id="taxons_bar_plot",
        group_by="taxons",
        source="occurrences",
        entity_id="1",
        mode="full",
    )

    assert engine._compute_etag(base) != engine._compute_etag(
        PreviewRequest(
            template_id="taxons_bar_plot",
            group_by="taxons",
            source="occurrences",
            entity_id="1",
            mode="thumbnail",
        )
    )
    assert engine._compute_etag(
        PreviewRequest(
            mode="full",
            inline={
                "widget_plugin": "bar_plot",
                "transformer_params": {"field": "dbh"},
            },
        )
    ) == engine._compute_etag(
        PreviewRequest(
            mode="full",
            inline={
                "transformer_params": {"field": "dbh"},
                "widget_plugin": "bar_plot",
            },
        )
    )
    assert engine._compute_etag(PreviewRequest(mode="full", inline={"a": 1})) != (
        engine._compute_etag(PreviewRequest(mode="full", inline={"a": 2}))
    )


def test_render_navigation_nested_set_without_level_column(monkeypatch):
    engine = _make_engine()
    db = MagicMock()
    db.engine.dialect.identifier_preparer.quote.side_effect = lambda name: f'"{name}"'

    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = [
        ("id", "INTEGER"),
        ("name", "VARCHAR"),
        ("lft", "INTEGER"),
        ("rght", "INTEGER"),
    ]
    db.engine.connect.return_value.__enter__.return_value = conn

    captured: dict[str, str] = {}

    def fake_read_sql(query, _engine):
        captured["query"] = str(query)
        return pd.DataFrame([{"id": 1, "name": "Root", "lft": 1, "rght": 2}])

    monkeypatch.setattr(
        preview_engine_module, "resolve_reference_table", lambda _db, _name: "taxons"
    )
    monkeypatch.setattr(
        preview_engine_module, "quote_identifier", lambda _db, name: f'"{name}"'
    )
    monkeypatch.setattr(preview_engine_module.pd, "read_sql", fake_read_sql)
    monkeypatch.setattr(
        engine,
        "_render_navigation_inline",
        lambda *args, **kwargs: "<nav>ok</nav>",
    )

    assert engine._render_navigation("taxons", db, []) == "<nav>ok</nav>"
    assert 'ORDER BY "lft" LIMIT 50' in captured["query"]
    assert '"level"' not in captured["query"]


def test_get_preview_engine_rebuilds_when_context_changes(monkeypatch):
    created: list[tuple[str, str]] = []

    class DummyEngine:
        def __init__(self, db_path: str, config_dir: str):
            self._db_path = db_path
            self._config_dir = config_dir
            created.append((db_path, config_dir))

    current = {
        "db_path": Path("/tmp/project-a/db/niamoto.duckdb"),
        "work_dir": Path("/tmp/project-a"),
    }

    monkeypatch.setattr(
        preview_engine_module, "get_database_path", lambda: current["db_path"]
    )
    monkeypatch.setattr(
        preview_engine_module, "get_working_directory", lambda: current["work_dir"]
    )
    monkeypatch.setattr(preview_engine_module, "PreviewEngine", DummyEngine)

    preview_engine_module.reset_preview_engine()
    try:
        first = preview_engine_module.get_preview_engine()
        current["db_path"] = Path("/tmp/project-b/db/niamoto.duckdb")
        current["work_dir"] = Path("/tmp/project-b")
        second = preview_engine_module.get_preview_engine()
    finally:
        preview_engine_module.reset_preview_engine()

    assert first is not None
    assert second is not None
    assert first is not second
    assert created == [
        ("/tmp/project-a/db/niamoto.duckdb", "/tmp/project-a/config"),
        ("/tmp/project-b/db/niamoto.duckdb", "/tmp/project-b/config"),
    ]


def test_get_preview_engine_closes_previous_database_on_context_change(monkeypatch):
    current = {
        "db_path": Path("/tmp/project-a/db/niamoto.duckdb"),
        "work_dir": Path("/tmp/project-a"),
    }
    monkeypatch.setattr(
        preview_engine_module, "get_database_path", lambda: current["db_path"]
    )
    monkeypatch.setattr(
        preview_engine_module, "get_working_directory", lambda: current["work_dir"]
    )

    preview_engine_module.reset_preview_engine()
    try:
        first = preview_engine_module.get_preview_engine()
        db = MagicMock()
        first._db = db

        current["db_path"] = Path("/tmp/project-b/db/niamoto.duckdb")
        current["work_dir"] = Path("/tmp/project-b")
        second = preview_engine_module.get_preview_engine()
    finally:
        preview_engine_module.reset_preview_engine()

    assert second is not first
    db.close_db_session.assert_called_once()
    db.engine.dispose.assert_called_once()


def test_get_transformer_service_rebuilds_when_engine_context_changes():
    preview_engine_module.reset_preview_engine()
    engine_a = PreviewEngine(
        "/tmp/project-a/db/niamoto.duckdb", "/tmp/project-a/config"
    )
    engine_b = PreviewEngine(
        "/tmp/project-b/db/niamoto.duckdb", "/tmp/project-b/config"
    )

    db_a = MagicMock()
    db_a.db_path = "/tmp/project-a/db/niamoto.duckdb"
    db_b = MagicMock()
    db_b.db_path = "/tmp/project-b/db/niamoto.duckdb"

    svc_a = MagicMock()
    svc_b = MagicMock()

    with patch(
        "niamoto.core.services.transformer.TransformerService.for_preview",
        side_effect=[svc_a, svc_b],
    ) as for_preview:
        assert engine_a._get_transformer_service(db_a) is svc_a
        assert engine_b._get_transformer_service(db_b) is svc_b

    assert for_preview.call_count == 2
    preview_engine_module.reset_preview_engine()


@pytest.mark.parametrize("entity_id", ["42", None])
def test_render_general_info_count_uses_configured_relation(
    monkeypatch, entity_id: str | None
):
    engine = _make_engine()
    db = MagicMock()
    db.engine = create_engine("sqlite:///:memory:")
    db.has_table.side_effect = lambda name: name in {
        "reference_plots",
        "dataset_occurrences",
    }
    warnings: list[str] = []
    captured_count: dict[str, object] = {}

    suggestion = {
        "config": {
            "fields": [
                {"field": "name", "target": "name", "label": "Name"},
                {
                    "source": "occurrences",
                    "field": "sample_id",
                    "target": "occurrences_count",
                    "label": "Occurrences",
                    "transformation": "count",
                },
            ]
        }
    }

    def fake_read_sql(query, _engine, params=None):
        sql = str(query)
        if "FROM reference_plots" in sql or 'FROM "reference_plots"' in sql:
            if entity_id is None:
                assert "WHERE" not in sql
            else:
                assert params == {"eid": "42"}
            return pd.DataFrame([{"id": 42, "plot_code": "P42", "name": "Plot 42"}])
        if "FROM dataset_occurrences" in sql or 'FROM "dataset_occurrences"' in sql:
            captured_count["sql"] = sql
            captured_count["params"] = params
            return pd.DataFrame([[2]])
        raise AssertionError(f"Unexpected SQL: {sql}")

    class FakeInfoGrid:
        def __init__(self, db=None):
            self.db = db

        def render(self, widget_data, _params):
            captured_count["widget_data"] = widget_data
            return str(widget_data)

    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.suggestion_service.generate_general_info_suggestion",
        lambda reference_name, db=None: suggestion,
    )
    monkeypatch.setattr(
        preview_engine_module,
        "load_import_config",
        lambda: {"entities": {"references": {"plots": {}}}},
    )
    monkeypatch.setattr(
        preview_engine_module,
        "get_hierarchy_info",
        lambda _config, _reference_name: {
            "relation": {"key": "plot_code", "ref_field": "plot_code"}
        },
    )
    monkeypatch.setattr(
        engine,
        "_get_column_names",
        lambda _db, quoted_table: ["id", "plot_code", "name"]
        if "reference_plots" in quoted_table
        else ["plot_code", "sample_id"],
    )
    monkeypatch.setattr(preview_engine_module.pd, "read_sql", fake_read_sql)
    monkeypatch.setattr(
        preview_engine_module.PluginRegistry,
        "get_plugin",
        lambda _name, _type: FakeInfoGrid,
    )

    try:
        html = engine._render_general_info("plots", entity_id, db, warnings)
    finally:
        db.engine.dispose()

    assert "occurrences_count" in html
    assert captured_count["params"] == {"eid": "P42"}
    assert (
        "WHERE plot_code = :eid" in captured_count["sql"]
        or 'WHERE "plot_code" = :eid' in captured_count["sql"]
    )
    assert captured_count["widget_data"]["occurrences_count"]["value"] == 2
    assert warnings == []


# ---------------------------------------------------------------------------
# _find_rich_entity_id / _query_rich_entity
# ---------------------------------------------------------------------------


def test_query_rich_entity_hierarchical_picks_largest_span():
    engine = _make_engine()
    db = MagicMock()
    group_ids = [10, 42, 50]

    with (
        patch(
            "niamoto.gui.api.services.preview_engine.engine.resolve_reference_table",
            return_value="entity_taxons",
        ),
        patch.object(db, "has_table", return_value=True),
        patch.object(
            db, "get_table_columns", return_value=["id", "lft", "rght", "level"]
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.quote_identifier",
            side_effect=lambda db, n: f'"{n}"',
        ),
    ):
        # Span query returns IDs: 99 (not in group_ids), 42 (in group_ids)
        conn_mock = MagicMock()
        span_rows = iter([(99,), (42,)])
        conn_mock.execute = MagicMock(return_value=span_rows)
        db.engine.connect.return_value.__enter__ = MagicMock(return_value=conn_mock)
        db.engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = engine._query_rich_entity(db, "taxons", group_ids)

    assert result == 42


def test_query_rich_entity_no_reference_table_returns_first():
    engine = _make_engine()
    db = MagicMock()

    with patch(
        "niamoto.gui.api.services.preview_engine.engine.resolve_reference_table",
        return_value=None,
    ):
        result = engine._query_rich_entity(db, "unknown", [1, 2, 3])

    assert result == 1


def test_find_rich_entity_id_caches_result():
    engine = _make_engine()
    db = MagicMock()

    with patch.object(engine, "_query_rich_entity", return_value=42) as mock_query:
        result1 = engine._find_rich_entity_id(db, "taxons", [10, 42, 50])
        result2 = engine._find_rich_entity_id(db, "taxons", [10, 42, 50])

    assert result1 == 42
    assert result2 == 42
    mock_query.assert_called_once()  # Only one DB query


def test_find_rich_entity_id_different_groups_not_shared():
    engine = _make_engine()
    db = MagicMock()

    with patch.object(engine, "_query_rich_entity", side_effect=[42, 7]) as mock_query:
        r1 = engine._find_rich_entity_id(db, "taxons", [10, 42])
        r2 = engine._find_rich_entity_id(db, "plots", [5, 7])

    assert r1 == 42
    assert r2 == 7
    assert mock_query.call_count == 2


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


def test_invalidate_clears_all_caches():
    engine = _make_engine()
    engine._rich_entity_cache["taxons"] = 42
    engine._group_ids_cache["taxons"] = [1, 2, 3]
    db = MagicMock()
    engine._db = db

    engine.invalidate()

    assert engine._rich_entity_cache == {}
    assert engine._group_ids_cache == {}
    assert engine._db is None
    db.close_db_session.assert_called_once()
    db.engine.dispose.assert_called_once()


def test_reset_preview_engine_closes_existing_database():
    engine = _make_engine()
    db = MagicMock()
    engine._db = db
    preview_engine_module._engine_instance = engine

    preview_engine_module.reset_preview_engine()

    assert preview_engine_module._engine_instance is None
    db.close_db_session.assert_called_once()
    db.engine.dispose.assert_called_once()


def test_invalidate_forces_requery():
    engine = _make_engine()
    db = MagicMock()

    with patch.object(engine, "_query_rich_entity", side_effect=[42, 99]) as mock_query:
        engine._find_rich_entity_id(db, "taxons", [42])
        engine.invalidate()
        engine._find_rich_entity_id(db, "taxons", [99])

    assert mock_query.call_count == 2


# ---------------------------------------------------------------------------
# _resolve_preview_group_context caching
# ---------------------------------------------------------------------------


def test_resolve_preview_group_context_caches_group_ids():
    engine = _make_engine()
    db = MagicMock()
    svc = MagicMock()
    svc._get_group_ids.return_value = [1, 2, 3]

    with (
        patch.object(engine, "_get_transformer_service", return_value=svc),
        patch.object(engine, "_load_group_config", return_value={"group_by": "taxons"}),
        patch.object(engine, "_find_rich_entity_id", return_value=1),
    ):
        engine._resolve_preview_group_context("taxons", None, db)
        # Second call should use cache
        engine._resolve_preview_group_context("taxons", None, db)

    svc._get_group_ids.assert_called_once()  # Only one DB query


def test_resolve_preview_group_context_prefers_entity_with_field_data():
    engine = _make_engine()
    db = MagicMock()
    svc = MagicMock()
    svc._get_group_ids.return_value = [1, 2, 3]

    with (
        patch.object(engine, "_get_transformer_service", return_value=svc),
        patch.object(engine, "_load_group_config", return_value={"group_by": "shapes"}),
        patch.object(engine, "_find_entity_id_with_field_data", return_value=2),
        patch.object(engine, "_find_rich_entity_id", return_value=1) as rich_picker,
    ):
        preview_group = engine._resolve_preview_group_context(
            "shapes",
            None,
            db,
            preferred_source="shapes",
            preferred_field="location",
        )

    assert preview_group is not None
    _, _, gid = preview_group
    assert gid == 2
    rich_picker.assert_not_called()


# ---------------------------------------------------------------------------
# _open_db reuse
# ---------------------------------------------------------------------------


def test_open_db_returns_same_instance():
    engine = _make_engine()

    with (
        patch("os.path.exists", return_value=True),
        patch("niamoto.gui.api.services.preview_engine.engine.Database") as MockDB,
    ):
        mock_instance = MagicMock()
        MockDB.return_value = mock_instance

        db1 = engine._open_db()
        db2 = engine._open_db()

    assert db1 is db2
    MockDB.assert_called_once()
    assert MockDB.call_args.kwargs.get("read_only") is None


def test_render_serializes_concurrent_preview_work():
    engine = _make_engine()
    request = PreviewRequest(template_id="configured_widget", group_by="taxons")
    active = 0
    max_active = 0
    active_lock = threading.Lock()

    def render_standard(*args, **kwargs):
        nonlocal active, max_active
        with active_lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with active_lock:
            active -= 1
        return "<div>ok</div>"

    with (
        patch.object(engine, "_open_db", return_value=MagicMock()),
        patch.object(engine, "_get_transformer_service", return_value=MagicMock()),
        patch.object(engine, "_render_standard", side_effect=render_standard),
        patch.object(engine, "_wrap_html", side_effect=lambda html, **kwargs: html),
    ):
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: engine.render(request), range(4)))

    assert [result.html for result in results] == ["<div>ok</div>"] * 4
    assert max_active == 1


def test_invalidate_waits_for_in_flight_render_before_closing_database():
    engine = _make_engine()
    request = PreviewRequest(template_id="configured_widget", group_by="taxons")
    db = MagicMock()
    render_started = threading.Event()
    allow_render_to_finish = threading.Event()
    close_times: list[float] = []

    def render_standard(*args, **kwargs):
        render_started.set()
        allow_render_to_finish.wait(timeout=2)
        return "<div>ok</div>"

    db.close_db_session.side_effect = lambda: close_times.append(time.monotonic())

    with (
        patch.object(engine, "_open_db", return_value=db),
        patch.object(engine, "_get_transformer_service", return_value=MagicMock()),
        patch.object(engine, "_render_standard", side_effect=render_standard),
        patch.object(engine, "_wrap_html", side_effect=lambda html, **kwargs: html),
    ):
        with ThreadPoolExecutor(max_workers=2) as executor:
            render_future = executor.submit(engine.render, request)
            assert render_started.wait(timeout=2)
            engine._db = db
            invalidate_future = executor.submit(engine.invalidate)
            time.sleep(0.05)
            db.close_db_session.assert_not_called()

            finished_at = time.monotonic()
            allow_render_to_finish.set()
            assert render_future.result(timeout=2).html == "<div>ok</div>"
            invalidate_future.result(timeout=2)

    assert close_times
    assert close_times[0] >= finished_at
    db.engine.dispose.assert_called_once()


def test_open_db_creates_new_after_invalidate():
    engine = _make_engine()

    with (
        patch("os.path.exists", return_value=True),
        patch("niamoto.gui.api.services.preview_engine.engine.Database") as MockDB,
        patch.object(engine, "_compute_data_fingerprint", return_value="fp"),
    ):
        inst1 = MagicMock()
        inst2 = MagicMock()
        MockDB.side_effect = [inst1, inst2]

        db1 = engine._open_db()
        engine.invalidate()
        db2 = engine._open_db()

    assert db1 is not db2
    assert MockDB.call_count == 2


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


def test_render_inline_class_object_reuses_configured_class_object_path():
    engine = _make_engine()
    db = MagicMock()
    request = PreviewRequest(
        group_by="plots",
        inline={
            "transformer_plugin": "class_object_series_extractor",
            "transformer_params": {
                "class_object": "top10_family",
                "source": "plot_stats",
            },
            "widget_plugin": "bar_plot",
            "widget_params": {"orientation": "horizontal"},
            "widget_title": "Top familles",
        },
    )

    with patch.object(
        engine,
        "_render_configured_class_object",
        return_value="<div>class-object</div>",
    ) as render_configured:
        result = engine._render_inline(request, db, [])

    assert result == "<div>class-object</div>"
    render_configured.assert_called_once_with(
        db,
        "class_object_series_extractor",
        {
            "class_object": "top10_family",
            "source": "plot_stats",
        },
        "bar_plot",
        {"orientation": "horizontal"},
        "Top familles",
        "plots",
        [],
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


def test_render_entity_map_falls_back_to_descendants_when_parent_has_no_geometry():
    engine = _make_engine()
    db = MagicMock()

    parent_df = pd.DataFrame([{"id": 1, "name": "Mines", "geom": None}])
    descendants_df = pd.DataFrame(
        [
            {
                "id": 2,
                "name": "Grand Sud",
                "geom": "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 0)))",
            }
        ]
    )

    with (
        patch(
            "niamoto.gui.api.services.preview_engine.engine.resolve_reference_table",
            return_value="entity_shapes",
        ),
        patch.object(
            engine,
            "_get_column_names",
            return_value=["id", "name", "location", "lft", "rght", "parent_id"],
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine._pick_identifier_column",
            return_value="id",
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine._pick_name_column",
            return_value="name",
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.pd.read_sql",
            side_effect=[parent_df, descendants_df],
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.parse_wkt_to_geojson",
            side_effect=lambda value: None
            if value == "None"
            else {"type": "Polygon", "coordinates": []},
        ),
        patch(
            "niamoto.gui.api.services.map_renderer.MapRenderer.render",
            return_value="<div>map</div>",
        ) as mock_render,
    ):
        result = engine._render_entity_map(
            "shapes_location_entity_map",
            "1",
            db,
            [],
        )

    assert result == "<div>map</div>"
    mock_render.assert_called_once()


def test_render_entity_map_parent_id_fallback_searches_deep_descendants():
    engine = _make_engine()
    db = MagicMock()

    parent_df = pd.DataFrame([{"id": 1, "name": "Province", "geom": None}])
    descendant_df = pd.DataFrame(
        [
            {
                "id": 3,
                "name": "Grandchild",
                "geom": "POLYGON ((0 0, 1 0, 1 1, 0 0))",
            }
        ]
    )

    with (
        patch(
            "niamoto.gui.api.services.preview_engine.engine.resolve_reference_table",
            return_value="entity_shapes",
        ),
        patch.object(
            engine,
            "_get_column_names",
            return_value=["id", "name", "location", "parent_id"],
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine._pick_identifier_column",
            return_value="id",
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine._pick_name_column",
            return_value="name",
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.pd.read_sql",
            side_effect=[parent_df, descendant_df],
        ) as read_sql,
        patch(
            "niamoto.gui.api.services.preview_engine.engine.parse_wkt_to_geojson",
            side_effect=lambda value: None
            if value == "None"
            else {"type": "Polygon", "coordinates": []},
        ),
        patch(
            "niamoto.gui.api.services.map_renderer.MapRenderer.render",
            return_value="<div>map</div>",
        ) as mock_render,
    ):
        result = engine._render_entity_map(
            "shapes_location_entity_map",
            "1",
            db,
            [],
        )

    descendant_query = str(read_sql.call_args_list[1].args[0])
    assert "WITH RECURSIVE descendants" in descendant_query
    assert result == "<div>map</div>"
    mock_render.assert_called_once()


def test_render_entity_map_preserves_underscored_reference_names():
    engine = _make_engine()
    db = MagicMock()
    parent_df = pd.DataFrame([{"id": 1, "name": "Plot 1", "geom": "POINT (0 0)"}])

    def resolve_reference(_db, reference_name):
        return "entity_forest_plots" if reference_name == "forest_plots" else None

    with (
        patch(
            "niamoto.gui.api.services.preview_engine.engine.resolve_reference_table",
            side_effect=resolve_reference,
        ) as mock_resolve,
        patch.object(
            engine,
            "_get_column_names",
            return_value=["id", "name", "location"],
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine._pick_identifier_column",
            return_value="id",
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine._pick_name_column",
            return_value="name",
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.pd.read_sql",
            return_value=parent_df,
        ),
        patch(
            "niamoto.gui.api.services.preview_engine.engine.parse_wkt_to_geojson",
            return_value={"type": "Point", "coordinates": [0, 0]},
        ),
        patch(
            "niamoto.gui.api.services.map_renderer.MapRenderer.render",
            return_value="<div>map</div>",
        ) as mock_render,
    ):
        result = engine._render_entity_map(
            "forest_plots_location_entity_map",
            "1",
            db,
            [],
        )

    assert result == "<div>map</div>"
    resolved_references = [call.args[1] for call in mock_resolve.call_args_list]
    assert resolved_references == ["forest_plots"]
    mock_render.assert_called_once()
