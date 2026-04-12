import asyncio
from pathlib import Path

from fastapi import FastAPI
from starlette.requests import Request

import niamoto.gui.api.routers.pipeline as pipeline_router
from niamoto.gui.api.routers.pipeline import EntityStatus, _compute_stage_status
from niamoto.gui.api.services.job_file_store import JobFileStore


def test_compute_stage_status_keeps_all_never_run_as_never_run():
    items = [
        EntityStatus(name="plots", status="never_run"),
        EntityStatus(name="taxons", status="never_run"),
    ]

    assert _compute_stage_status(items) == "never_run"


def test_compute_stage_status_marks_mixed_fresh_and_never_run_as_stale():
    items = [
        EntityStatus(name="plots", status="fresh"),
        EntityStatus(name="taxons", status="never_run"),
    ]

    assert _compute_stage_status(items) == "stale"


def test_pipeline_groups_are_unconfigured_when_no_widgets_data(tmp_path, monkeypatch):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "transform.yml").write_text(
        """
- group_by: plots
  sources: []
  widgets_data: {}
- group_by: taxons
  sources: []
  widgets_data: {}
""".strip()
    )
    (config_dir / "export.yml").write_text("exports: []\n")

    monkeypatch.setattr(pipeline_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(
        pipeline_router, "get_database_path", lambda: db_dir / "niamoto.duckdb"
    )

    class DummyStore:
        def get_running_job(self):
            return None

        def get_last_run(self, *args, **kwargs):
            return None

    app = FastAPI()
    app.state.job_store = DummyStore()
    app.state.job_store_work_dir = work_dir
    monkeypatch.setattr(
        pipeline_router, "resolve_job_store", lambda app: app.state.job_store
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/pipeline/status",
            "headers": [],
            "app": app,
        }
    )

    response = asyncio.run(pipeline_router.get_pipeline_status(request))

    assert response.groups.status == "unconfigured"
    assert response.groups.items == []


def test_pipeline_marks_batch_transform_groups_as_fresh(tmp_path: Path, monkeypatch):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "transform.yml").write_text(
        """
- group_by: plots
  sources: []
  widgets_data:
    plot_widget:
      plugin: field_aggregator
- group_by: taxons
  sources: []
  widgets_data:
    taxon_widget:
      plugin: field_aggregator
""".strip()
    )
    (config_dir / "export.yml").write_text("exports: []\n")

    store = JobFileStore(work_dir)
    job = store.create_job("transform", group_bys=["plots", "taxons"])
    store.complete_job(job["id"])

    monkeypatch.setattr(pipeline_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(
        pipeline_router, "get_database_path", lambda: db_dir / "niamoto.duckdb"
    )
    monkeypatch.setattr(pipeline_router, "resolve_job_store", lambda app: store)

    app = FastAPI()
    app.state.job_store = store
    app.state.job_store_work_dir = work_dir

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/pipeline/status",
            "headers": [],
            "app": app,
        }
    )

    response = asyncio.run(pipeline_router.get_pipeline_status(request))

    plots_status = next(item for item in response.groups.items if item.name == "plots")
    taxons_status = next(
        item for item in response.groups.items if item.name == "taxons"
    )

    assert plots_status.status == "fresh"
    assert taxons_status.status == "fresh"
