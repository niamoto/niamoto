"""Tests for transform source registry metadata persistence."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseQueryError
from niamoto.core.imports.source_registry import TransformSourceRegistry


@pytest.fixture()
def registry() -> TransformSourceRegistry:
    db = Database("sqlite:///:memory:")
    try:
        yield TransformSourceRegistry(db)
    finally:
        try:
            db.close_db_session()
        except AttributeError:
            pass
        if db.engine:
            db.engine.dispose()


def test_register_and_lookup_round_trips_utf8_config(registry: TransformSourceRegistry):
    registry.register_source(
        name="plot_stats",
        path="imports/plot_stats.csv",
        grouping="plots",
        config={
            "schema": {
                "fields": [
                    {"name": "forest_type", "label": "Forêt sèche"},
                ]
            }
        },
    )

    metadata = registry.get("plot_stats")

    assert metadata.name == "plot_stats"
    assert metadata.path == "imports/plot_stats.csv"
    assert metadata.grouping == "plots"
    assert metadata.config["schema"]["fields"][0]["label"] == "Forêt sèche"


def test_list_sources_returns_all_registered_sources(registry: TransformSourceRegistry):
    registry.register_source(
        name="plot_stats",
        path="imports/plot_stats.csv",
        grouping="plots",
        config={"schema": {"fields": [{"name": "plot_id", "type": "string"}]}},
    )
    registry.register_source(
        name="shape_stats",
        path="imports/shape_stats.csv",
        grouping="shapes",
        config={"schema": {"fields": [{"name": "shape_id", "type": "string"}]}},
    )

    sources = registry.list_sources()

    assert {source.name for source in sources} == {"plot_stats", "shape_stats"}


@pytest.mark.parametrize(
    ("row", "expected_config"),
    [
        (
            {
                "name": "plot_stats",
                "path": "imports/plot_stats.csv",
                "grouping": "plots",
                "config": {"schema": {"fields": [{"name": "plot_id"}]}},
            },
            {"schema": {"fields": [{"name": "plot_id"}]}},
        ),
        (
            (
                "shape_stats",
                "imports/shape_stats.csv",
                "shapes",
                '{"schema": {"fields": [{"name": "shape_id"}]}}',
            ),
            {"schema": {"fields": [{"name": "shape_id"}]}},
        ),
    ],
)
def test_row_to_metadata_supports_mapping_and_sequence_rows(
    registry: TransformSourceRegistry,
    row: Mapping[str, object] | tuple[str, str, str, str],
    expected_config: dict[str, object],
):
    metadata = registry._row_to_metadata(row)

    assert metadata.name in {"plot_stats", "shape_stats"}
    assert metadata.config == expected_config


def test_invalid_json_config_raises_database_query_error(
    registry: TransformSourceRegistry,
):
    registry.db.execute_sql(
        f"""
        INSERT INTO {registry.SOURCES_TABLE} (name, path, grouping, config)
        VALUES (:name, :path, :grouping, :config)
        """,
        {
            "name": "bad_source",
            "path": "imports/bad.csv",
            "grouping": "plots",
            "config": "{invalid json}",
        },
    )

    with pytest.raises(DatabaseQueryError) as exc_info:
        registry.get("bad_source")

    assert "Invalid JSON in transform source config" in str(exc_info.value)


def test_list_sources_returns_empty_when_query_fails():
    class FailingDb:
        read_only = True

        def execute_sql(self, *args, **kwargs):
            raise DatabaseQueryError("transform_source_lookup", "boom")

    registry = TransformSourceRegistry(FailingDb())

    assert registry.list_sources() == []


def test_read_only_registry_skips_table_creation():
    class RecordingDb:
        def __init__(self):
            self.read_only = True
            self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def execute_sql(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return None

    db = RecordingDb()
    TransformSourceRegistry(db)

    assert db.calls == []
