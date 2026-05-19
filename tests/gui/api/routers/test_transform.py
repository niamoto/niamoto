"""Regression tests for transform route group filtering."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
import yaml

from niamoto.gui.api.routers import transform as transform_router


class _DummyJobStore:
    def __init__(self) -> None:
        self.completed_result = None
        self.failed_error = None

    def update_progress(self, job_id: str, progress: int, message: str) -> None:
        return None

    def complete_job(self, job_id: str, result: dict) -> None:
        self.completed_result = result

    def fail_job(self, job_id: str, error: str) -> None:
        self.failed_error = error


class _StatusJobStore:
    def __init__(self, job: dict | None) -> None:
        self.job = job

    def get_job(self, job_id: str) -> dict | None:
        return self.job


@pytest.mark.anyio
async def test_execute_transform_background_filters_requested_group_bys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_group_names: list[str] = []

    class DummyTransformerService:
        def __init__(self, db_path: str, config, enable_cli_integration: bool = False):
            self.transforms_config = []
            self.config = type("DummyConfig", (), {"transforms": []})()

        def transform_data(self, group_by, csv_file, recreate_table, progress_callback):
            captured_group_names.extend(
                [group["group_by"] for group in self.transforms_config]
            )
            return {
                group["group_by"]: {
                    "widgets": {name: 1 for name in group["widgets_data"]}
                }
                for group in self.transforms_config
            }

    transform_config = [
        {"group_by": "taxons", "widgets_data": {"widget_a": {"plugin": "foo"}}},
        {
            "group_by": "plots_hierarchy",
            "widgets_data": {"widget_b": {"plugin": "bar"}},
        },
        {"group_by": "shapes", "widgets_data": {"widget_c": {"plugin": "baz"}}},
    ]

    monkeypatch.setattr(
        transform_router, "get_transform_config", lambda path: transform_config
    )
    monkeypatch.setattr(
        transform_router, "get_database_path", lambda: tmp_path / "db.duckdb"
    )
    monkeypatch.setattr(transform_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        transform_router, "Config", lambda config_dir, create_default=False: object()
    )
    monkeypatch.setattr(transform_router, "TransformerService", DummyTransformerService)

    job_store = _DummyJobStore()

    await transform_router.execute_transform_background(
        "job-1",
        job_store,
        "config/transform.yml",
        None,
        None,
        ["taxons", "shapes"],
    )

    assert job_store.failed_error is None
    assert captured_group_names == ["taxons", "shapes"]
    assert job_store.completed_result is not None
    assert set(job_store.completed_result["transformations"].keys()) == {
        "widget_a",
        "widget_c",
    }


@pytest.mark.anyio
async def test_execute_transform_background_fails_for_unknown_requested_group(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class DummyTransformerService:
        def __init__(self, db_path: str, config, enable_cli_integration: bool = False):
            self.transforms_config = []
            self.config = type("DummyConfig", (), {"transforms": []})()

        def transform_data(self, group_by, csv_file, recreate_table, progress_callback):
            raise AssertionError("transform_data should not run for missing groups")

    transform_config = [
        {"group_by": "taxons", "widgets_data": {"widget_a": {"plugin": "foo"}}},
        {"group_by": "shapes", "widgets_data": {"widget_c": {"plugin": "baz"}}},
    ]

    monkeypatch.setattr(
        transform_router, "get_transform_config", lambda path: transform_config
    )
    monkeypatch.setattr(
        transform_router, "get_database_path", lambda: tmp_path / "db.duckdb"
    )
    monkeypatch.setattr(transform_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        transform_router, "Config", lambda config_dir, create_default=False: object()
    )
    monkeypatch.setattr(transform_router, "TransformerService", DummyTransformerService)

    job_store = _DummyJobStore()

    await transform_router.execute_transform_background(
        "job-1",
        job_store,
        "config/transform.yml",
        None,
        "plots",
        None,
    )

    assert job_store.completed_result is None
    assert job_store.failed_error == (
        "Transform group(s) not found: plots. Available groups: shapes, taxons"
    )


def test_transform_status_keeps_group_metadata() -> None:
    status = transform_router.TransformStatus(
        **transform_router._job_to_status(
            {
                "id": "job-1",
                "status": "running",
                "progress": 25,
                "message": "Processing shapes",
                "phase": None,
                "group_by": None,
                "group_bys": ["plots", "taxons"],
                "started_at": "2026-04-12T09:00:00",
                "completed_at": None,
                "result": None,
                "error": None,
            }
        )
    )

    assert status.group_by is None
    assert status.group_bys == ["plots", "taxons"]


@pytest.mark.anyio
async def test_get_transform_status_hides_non_transform_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = {
        "id": "job-1",
        "type": "import",
        "status": "completed",
        "progress": 100,
        "message": "Import done",
        "started_at": "2026-04-12T09:00:00",
        "completed_at": "2026-04-12T09:01:00",
        "result": {"secret": "import payload"},
        "error": None,
    }
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(job),
    )

    with pytest.raises(HTTPException) as exc_info:
        await transform_router.get_transform_status(
            "job-1",
            SimpleNamespace(app=SimpleNamespace()),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Transform job job-1 not found"


@pytest.mark.anyio
async def test_get_transform_status_returns_transform_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = {
        "id": "job-1",
        "type": "transform",
        "status": "running",
        "progress": 40,
        "message": "Processing plots",
        "phase": "transforming",
        "group_by": "plots",
        "group_bys": None,
        "started_at": "2026-04-12T09:00:00",
        "completed_at": None,
        "result": None,
        "error": None,
    }
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(job),
    )

    status = await transform_router.get_transform_status(
        "job-1",
        SimpleNamespace(app=SimpleNamespace()),
    )

    assert status.job_id == "job-1"
    assert status.status == "running"
    assert status.group_by == "plots"


def test_get_transform_sources_reads_root_dict_group(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            {
                "group_by": "shapes",
                "sources": [
                    {"name": "shape_stats"},
                    {"name": "raw_shape_stats"},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(transform_router, "get_working_directory", lambda: tmp_path)

    response = asyncio.run(transform_router.get_transform_sources(group_by="shapes"))

    assert response == {"sources": ["raw_shape_stats", "shape_stats"]}


def test_get_transform_config_preserves_duplicate_widget_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transform_config = [
        {
            "group_by": "taxons",
            "widgets_data": {
                "summary": {"plugin": "statistical_summary"},
                "richness": {"plugin": "field_aggregator"},
            },
        },
        {
            "group_by": "plots",
            "widgets_data": {
                "summary": {"plugin": "field_aggregator"},
            },
        },
    ]

    monkeypatch.setattr(
        transform_router, "get_transform_config", lambda path: transform_config
    )

    response = asyncio.run(transform_router.get_transform_config_endpoint())

    widgets_data = response["config"]["widgets_data"]
    assert response["summary"]["total_widgets"] == 3
    assert len(widgets_data) == 3
    assert set(widgets_data) == {"taxons:summary", "richness", "plots:summary"}
    assert widgets_data["taxons:summary"]["plugin"] == "statistical_summary"
    assert widgets_data["plots:summary"]["plugin"] == "field_aggregator"
