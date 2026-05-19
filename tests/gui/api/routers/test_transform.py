"""Regression tests for transform route group filtering."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
import yaml

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import transform as transform_router


class _DummyJobStore:
    def __init__(self) -> None:
        self.completed_result = None
        self.failed_error = None
        self.status = "running"

    def update_progress(self, job_id: str, progress: int, message: str) -> None:
        return None

    def complete_job(self, job_id: str, result: dict) -> None:
        self.completed_result = result
        self.status = "completed"

    def fail_job(self, job_id: str, error: str) -> None:
        self.failed_error = error
        self.status = "failed"

    def get_job(self, job_id: str) -> dict:
        return {"id": job_id, "status": self.status}


class _StatusJobStore:
    def __init__(
        self,
        job: dict | None,
        *,
        active_job: dict | None = None,
        history: list[dict] | None = None,
    ) -> None:
        self.job = job
        self.active_job = active_job
        self.history = history or []

    def get_job(self, job_id: str) -> dict | None:
        return self.job

    def get_active_job(self, job_type: str | None = None) -> dict | None:
        if not self.active_job:
            return None
        if job_type and self.active_job.get("type") != job_type:
            return None
        return self.active_job

    def get_history(self, limit: int = 10) -> list[dict]:
        return self.history[:limit]

    def cancel_job(self, job_id: str, message: str = "Job cancelled") -> dict | None:
        if not self.job or self.job["id"] != job_id or self.job["status"] != "running":
            return None
        self.job = {
            **self.job,
            "status": "cancelled",
            "message": message,
            "completed_at": "2026-04-12T09:02:00",
        }
        return self.job

    def get_last_run(
        self,
        job_type: str,
        group_by: str | None = None,
        status: str | None = None,
    ) -> dict | None:
        if not self.job:
            return None
        if self.job.get("type") != job_type:
            return None
        if status is not None and self.job.get("status") != status:
            return None
        if group_by is None:
            return self.job
        if self.job.get("group_by") == group_by:
            return self.job
        if group_by in (self.job.get("group_bys") or []):
            return self.job
        return None


def test_execute_transform_rejects_null_config_path():
    client = TestClient(create_app())

    response = client.post(
        "/api/transform/execute",
        json={"config_path": None},
    )

    assert response.status_code == 422


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


@pytest.mark.anyio
async def test_execute_transform_background_observes_cancelled_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class DummyTransformerService:
        def __init__(self, db_path: str, config, enable_cli_integration: bool = False):
            self.transforms_config = []
            self.config = type("DummyConfig", (), {"transforms": []})()

        def transform_data(self, group_by, csv_file, recreate_table, progress_callback):
            progress_callback({"processed": 0, "total": 1, "group": "taxons"})
            raise AssertionError("cancelled progress should stop transform_data")

    transform_config = [
        {"group_by": "taxons", "widgets_data": {"widget_a": {"plugin": "foo"}}}
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
    job_store.status = "cancelled"

    await transform_router.execute_transform_background(
        "job-1",
        job_store,
        "config/transform.yml",
    )

    assert job_store.completed_result is None
    assert job_store.failed_error is None


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


@pytest.mark.anyio
async def test_get_transform_status_returns_404_for_missing_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await transform_router.get_transform_status(
            "missing",
            SimpleNamespace(app=SimpleNamespace()),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_get_last_transform_run_finds_multi_group_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = {
        "id": "job-1",
        "type": "transform",
        "status": "completed",
        "progress": 100,
        "message": "Transform completed",
        "phase": None,
        "group_by": None,
        "group_bys": ["taxons", "shapes"],
        "started_at": "2026-04-12T09:00:00",
        "completed_at": "2026-04-12T09:01:00",
        "result": {"metrics": {"total_transformations": 2}},
        "error": None,
    }
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(job),
    )

    status = await transform_router.get_last_transform_run(
        "taxons",
        SimpleNamespace(app=SimpleNamespace()),
    )

    assert status["job_id"] == "job-1"
    assert status["status"] == "completed"
    assert status["group_by"] is None
    assert status["group_bys"] == ["taxons", "shapes"]


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


def test_get_transform_sources_skips_malformed_groups_and_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                None,
                {
                    "group_by": "shapes",
                    "sources": [
                        None,
                        "raw_shape_stats",
                        {"name": "shape_stats"},
                    ],
                },
                {"group_by": "plots", "sources": "not-a-list"},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(transform_router, "get_working_directory", lambda: tmp_path)

    response = asyncio.run(transform_router.get_transform_sources(group_by=None))

    assert response == {"sources": ["shape_stats"]}


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


@pytest.mark.anyio
async def test_execute_transform_background_qualifies_all_duplicate_widget_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class DummyTransformerService:
        def __init__(self, db_path: str, config, enable_cli_integration: bool = False):
            self.transforms_config = []
            self.config = type("DummyConfig", (), {"transforms": []})()

        def transform_data(self, group_by, csv_file, recreate_table, progress_callback):
            return {
                group["group_by"]: {
                    "widgets": {name: 1 for name in group["widgets_data"]}
                }
                for group in self.transforms_config
            }

    transform_config = [
        {"group_by": "taxons", "widgets_data": {"summary": {"plugin": "foo"}}},
        {"group_by": "plots", "widgets_data": {"summary": {"plugin": "bar"}}},
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
    )

    assert set(job_store.completed_result["transformations"]) == {
        "taxons:summary",
        "plots:summary",
    }


@pytest.mark.anyio
async def test_list_transform_jobs_deduplicates_active_job_from_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = {
        "id": "job-1",
        "type": "transform",
        "status": "running",
        "progress": 50,
        "message": "Running",
        "started_at": "2026-04-12T09:00:00",
        "completed_at": None,
    }
    history = [
        {**active, "status": "running"},
        {
            "id": "job-2",
            "type": "transform",
            "status": "completed",
            "progress": 100,
            "message": "Done",
            "started_at": "2026-04-12T08:00:00",
            "completed_at": "2026-04-12T08:01:00",
        },
    ]
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(None, active_job=active, history=history),
    )

    response = await transform_router.list_transform_jobs(
        SimpleNamespace(app=SimpleNamespace()),
    )

    assert [job["job_id"] for job in response["jobs"]] == ["job-1", "job-2"]


@pytest.mark.anyio
async def test_get_active_transform_job_returns_active_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = {
        "id": "job-1",
        "type": "transform",
        "status": "running",
        "progress": 25,
        "message": "Running",
        "phase": "transforming",
        "group_by": "taxons",
        "group_bys": None,
        "started_at": "2026-04-12T09:00:00",
        "completed_at": None,
        "result": None,
        "error": None,
    }
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(None, active_job=active),
    )

    response = await transform_router.get_active_transform_job(
        SimpleNamespace(app=SimpleNamespace()),
    )

    assert response["job_id"] == "job-1"
    assert response["status"] == "running"


@pytest.mark.anyio
async def test_get_active_transform_job_returns_none_without_active_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(None),
    )

    assert (
        await transform_router.get_active_transform_job(
            SimpleNamespace(app=SimpleNamespace())
        )
        is None
    )


def test_get_active_transform_job_route_filters_non_transform_active_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = {
        "id": "job-1",
        "type": "import",
        "status": "running",
        "progress": 25,
        "message": "Importing",
        "started_at": "2026-04-12T09:00:00",
        "completed_at": None,
    }
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(None, active_job=active),
    )

    response = TestClient(create_app()).get("/api/transform/active")

    assert response.status_code == 200
    assert response.json() is None


def test_get_active_transform_job_route_returns_active_transform_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = {
        "id": "job-1",
        "type": "transform",
        "status": "running",
        "progress": 25,
        "message": "Running",
        "phase": "transforming",
        "group_by": "taxons",
        "group_bys": None,
        "started_at": "2026-04-12T09:00:00",
        "completed_at": None,
        "result": None,
        "error": None,
    }
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(None, active_job=active),
    )

    response = TestClient(create_app()).get("/api/transform/active")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-1"


@pytest.mark.anyio
async def test_get_transform_metrics_returns_completed_job_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = {
        "id": "job-1",
        "type": "transform",
        "status": "completed",
        "progress": 100,
        "message": "Done",
        "phase": None,
        "group_by": "taxons",
        "group_bys": None,
        "started_at": "2026-04-12T09:00:00",
        "completed_at": "2026-04-12T09:01:00",
        "result": {
            "metrics": {
                "total_transformations": 1,
                "completed_transformations": 1,
                "failed_transformations": 0,
            }
        },
        "error": None,
    }
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(job),
    )

    response = await transform_router.get_transform_metrics(
        SimpleNamespace(app=SimpleNamespace()),
    )

    assert response["job_id"] == "job-1"
    assert response["last_run"] == "2026-04-12T09:01:00"
    assert response["metrics"]["completed_transformations"] == 1


@pytest.mark.anyio
async def test_get_transform_metrics_returns_empty_defaults_without_completed_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(None),
    )

    response = await transform_router.get_transform_metrics(
        SimpleNamespace(app=SimpleNamespace()),
    )

    assert response["last_run"] is None
    assert response["metrics"]["total_transformations"] == 0


def test_get_transform_config_reads_transforms_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        transform_router,
        "get_transform_config",
        lambda path: {
            "transforms": [
                {
                    "group_by": "taxons",
                    "widgets_data": {"summary": {"plugin": "field_aggregator"}},
                }
            ]
        },
    )

    response = asyncio.run(transform_router.get_transform_config_endpoint())

    assert response["summary"]["total_widgets"] == 1
    assert response["config"]["widgets_data"]["summary"]["plugin"] == (
        "field_aggregator"
    )


@pytest.mark.anyio
async def test_cancel_transform_job_marks_running_transform_cancelled(
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

    status = await transform_router.cancel_transform_job(
        "job-1",
        SimpleNamespace(app=SimpleNamespace()),
    )

    assert status["job_id"] == "job-1"
    assert status["status"] == "cancelled"
    assert status["message"] == "Transform job cancelled"


@pytest.mark.anyio
async def test_get_last_transform_run_ignores_failed_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = {
        "id": "job-1",
        "type": "transform",
        "status": "failed",
        "progress": 100,
        "message": "Transform failed",
        "phase": None,
        "group_by": "taxons",
        "group_bys": None,
        "started_at": "2026-04-12T09:00:00",
        "completed_at": "2026-04-12T09:01:00",
        "result": None,
        "error": "boom",
    }
    monkeypatch.setattr(
        transform_router,
        "_get_job_store",
        lambda _request: _StatusJobStore(job),
    )

    assert (
        await transform_router.get_last_transform_run(
            "taxons",
            SimpleNamespace(app=SimpleNamespace()),
        )
        is None
    )
