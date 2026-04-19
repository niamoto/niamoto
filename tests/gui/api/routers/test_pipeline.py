import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
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


def test_pipeline_site_is_unconfigured_when_html_export_params_are_missing(
    tmp_path, monkeypatch
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "transform.yml").write_text("[]\n")
    (config_dir / "export.yml").write_text(
        """
exports:
  - name: web_pages
    enabled: true
    exporter: html_page_exporter
    params:
      site:
        title: Test
        lang: fr
    static_pages: []
    groups: []
""".strip()
    )

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

    assert response.site.status == "unconfigured"


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


# ---------------------------------------------------------------------------
# /api/pipeline/history endpoint
# ---------------------------------------------------------------------------


def _build_history_app(history_entries: list[dict], monkeypatch) -> FastAPI:
    """Build a minimal FastAPI app with a stub job_store for history tests."""

    class DummyStore:
        def __init__(self, entries: list[dict]):
            self._entries = entries
            self.last_limit: int | None = None

        def get_history(self, limit: int = 20) -> list[dict]:
            self.last_limit = limit
            return self._entries[:limit]

    store = DummyStore(history_entries)
    app = FastAPI()
    app.state.job_store = store
    app.include_router(pipeline_router.router, prefix="/api/pipeline")
    monkeypatch.setattr(
        pipeline_router, "resolve_job_store", lambda app: app.state.job_store
    )
    return app


def test_pipeline_history_returns_entries(monkeypatch):
    entries = [
        {"id": "a", "type": "import", "status": "completed"},
        {"id": "b", "type": "transform", "status": "completed"},
    ]
    app = _build_history_app(entries, monkeypatch)
    client = TestClient(app)

    response = client.get("/api/pipeline/history?limit=5")

    assert response.status_code == 200
    assert response.json() == entries
    assert app.state.job_store.last_limit == 5


def test_pipeline_history_default_limit(monkeypatch):
    app = _build_history_app([], monkeypatch)
    client = TestClient(app)

    response = client.get("/api/pipeline/history")

    assert response.status_code == 200
    assert app.state.job_store.last_limit == 10


def test_pipeline_history_rejects_zero_limit(monkeypatch):
    app = _build_history_app([{"id": "a"}], monkeypatch)
    client = TestClient(app)

    response = client.get("/api/pipeline/history?limit=0")

    assert response.status_code == 422


def test_pipeline_history_rejects_negative_limit(monkeypatch):
    app = _build_history_app([{"id": "a"}], monkeypatch)
    client = TestClient(app)

    response = client.get("/api/pipeline/history?limit=-1")

    assert response.status_code == 422


def test_pipeline_history_rejects_limit_above_max(monkeypatch):
    app = _build_history_app([{"id": "a"}], monkeypatch)
    client = TestClient(app)

    response = client.get("/api/pipeline/history?limit=101")

    assert response.status_code == 422


def test_pipeline_history_accepts_boundary_values(monkeypatch):
    app = _build_history_app([], monkeypatch)
    client = TestClient(app)

    for boundary in (1, 100):
        response = client.get(f"/api/pipeline/history?limit={boundary}")
        assert response.status_code == 200
        assert app.state.job_store.last_limit == boundary


def test_pipeline_history_returns_empty_when_store_resolution_fails(monkeypatch):
    app = FastAPI()
    app.include_router(pipeline_router.router, prefix="/api/pipeline")

    def failing_resolve(_app):
        raise RuntimeError("no project loaded")

    monkeypatch.setattr(pipeline_router, "resolve_job_store", failing_resolve)
    client = TestClient(app)

    response = client.get("/api/pipeline/history")

    assert response.status_code == 200
    assert response.json() == []
