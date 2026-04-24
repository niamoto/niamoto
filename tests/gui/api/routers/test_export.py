"""Integration tests for export router history endpoints."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
import yaml

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import export as export_router
from niamoto.gui.api.services.job_file_store import JobFileStore


class TestExportHistory:
    def test_execute_export_rejects_invalid_html_export_config(self):
        with TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            config_dir = work_dir / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "export.yml").write_text(
                yaml.safe_dump(
                    {
                        "exports": [
                            {
                                "name": "web_pages",
                                "enabled": True,
                                "exporter": "html_page_exporter",
                                "params": {},
                                "static_pages": [],
                                "groups": [],
                            }
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            with (
                patch.dict("os.environ", {"NIAMOTO_HOME": str(work_dir)}),
                patch(
                    "niamoto.gui.api.services.job_store_runtime.get_working_directory",
                    return_value=work_dir,
                ),
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/export/execute",
                    json={
                        "config_path": "config/export.yml",
                        "include_transform": False,
                    },
                )

            assert response.status_code == 400, response.text
            assert (
                "Le site n’est pas prêt pour la génération" in response.json()["detail"]
            )

    def test_export_jobs_return_project_scoped_history_with_result(self):
        with TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            store = JobFileStore(work_dir)

            first_export = store.create_job("export")
            store.complete_job(
                first_export["id"],
                result={
                    "metrics": {"generated_pages": 84, "execution_time": 3.5},
                    "exports": {"web_pages": {"data": {"files_generated": 84}}},
                    "generated_paths": [],
                },
            )

            transform_job = store.create_job("transform")
            store.complete_job(transform_job["id"])

            latest_export = store.create_job("export")
            store.fail_job(latest_export["id"], "boom")

            with patch(
                "niamoto.gui.api.services.job_store_runtime.get_working_directory",
                return_value=work_dir,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.get("/api/export/jobs")
                assert response.status_code == 200, response.text

            jobs = response.json()["jobs"]
            assert len(jobs) == 2
            assert jobs[0]["job_id"] == latest_export["id"]
            assert jobs[0]["error"] == "boom"
            assert jobs[1]["job_id"] == first_export["id"]
            assert jobs[1]["result"]["metrics"]["generated_pages"] == 84

    def test_clear_export_history_removes_only_export_entries(self):
        with TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            store = JobFileStore(work_dir)

            archived_export = store.create_job("export")
            store.complete_job(archived_export["id"])

            transform_job = store.create_job("transform")
            store.complete_job(transform_job["id"])

            active_export = store.create_job("export")
            store.complete_job(active_export["id"])

            with patch(
                "niamoto.gui.api.services.job_store_runtime.get_working_directory",
                return_value=work_dir,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.delete("/api/export/history")
                assert response.status_code == 200, response.text
                assert response.json()["removed"] == 2

                jobs_response = client.get("/api/export/jobs")
                assert jobs_response.status_code == 200, jobs_response.text
                assert jobs_response.json()["jobs"] == []

            history = store.get_history(limit=10)
            assert len(history) == 1
            assert history[0]["type"] == "transform"


class _DummyJobStore:
    def __init__(self) -> None:
        self.completed_result = None
        self.failed_result = None
        self.failed_error = None

    def update_progress(
        self, job_id: str, progress: int, message: str, phase: str | None = None
    ) -> None:
        return None

    def complete_job(self, job_id: str, result: dict) -> None:
        self.completed_result = result

    def fail_job(self, job_id: str, error: str, result: dict | None = None) -> None:
        self.failed_error = error
        self.failed_result = result


@pytest.mark.anyio
async def test_execute_export_background_counts_generated_html_pages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "exports" / "web"
    (output_dir / "taxons").mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text("<html>home</html>", encoding="utf-8")
    (output_dir / "taxons" / "1.html").write_text(
        "<html>taxon</html>", encoding="utf-8"
    )
    (output_dir / "assets").mkdir(parents=True, exist_ok=True)
    (output_dir / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")

    class DummyExporterService:
        def __init__(self, db_path: str, config) -> None:
            self.db_path = db_path

        def run_export(self, target_name=None):
            return {
                "web_pages": {
                    "status": "success",
                    "files_generated": 2,
                    "errors": 0,
                    "output_path": str(output_dir),
                }
            }

    monkeypatch.setattr(
        export_router,
        "get_export_config",
        lambda path: {
            "exports": [{"name": "web_pages", "exporter": "html_page_exporter"}]
        },
    )
    monkeypatch.setattr(
        export_router, "get_database_path", lambda: tmp_path / "db.duckdb"
    )
    monkeypatch.setattr(export_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        export_router, "Config", lambda config_dir, create_default=False: object()
    )
    monkeypatch.setattr(export_router, "ExporterService", DummyExporterService)

    job_store = _DummyJobStore()
    context = export_router.ExportExecutionContext(
        work_dir=tmp_path,
        config_path=tmp_path / "config" / "export.yml",
        db_path=tmp_path / "db.duckdb",
    )

    await export_router.execute_export_background(
        "job-1",
        job_store,
        context,
        None,
        False,
    )

    assert job_store.failed_error is None
    assert job_store.completed_result is not None
    assert job_store.completed_result["metrics"]["generated_pages"] == 2
    assert job_store.completed_result["metrics"]["static_site_path"] == str(output_dir)


@pytest.mark.anyio
async def test_execute_export_background_prefers_html_export_output_for_static_site_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    api_output_dir = tmp_path / "exports" / "api"
    api_output_dir.mkdir(parents=True, exist_ok=True)
    (api_output_dir / "index.json").write_text("{}", encoding="utf-8")

    html_output_dir = tmp_path / "exports" / "web"
    html_output_dir.mkdir(parents=True, exist_ok=True)
    (html_output_dir / "index.html").write_text("<html>home</html>", encoding="utf-8")

    class DummyExporterService:
        def __init__(self, db_path: str, config) -> None:
            self.db_path = db_path

        def run_export(self, target_name=None):
            return {
                "json_api": {
                    "status": "success",
                    "files_generated": 1,
                    "errors": 0,
                    "output_path": str(api_output_dir),
                },
                "web_pages": {
                    "status": "success",
                    "files_generated": 1,
                    "errors": 0,
                    "output_path": str(html_output_dir),
                },
            }

    monkeypatch.setattr(
        export_router,
        "get_export_config",
        lambda path: {
            "exports": [
                {"name": "json_api", "exporter": "json_api_exporter"},
                {"name": "web_pages", "exporter": "html_page_exporter"},
            ]
        },
    )
    monkeypatch.setattr(
        export_router, "get_database_path", lambda: tmp_path / "db.duckdb"
    )
    monkeypatch.setattr(export_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        export_router, "Config", lambda config_dir, create_default=False: object()
    )
    monkeypatch.setattr(export_router, "ExporterService", DummyExporterService)

    job_store = _DummyJobStore()
    context = export_router.ExportExecutionContext(
        work_dir=tmp_path,
        config_path=tmp_path / "config" / "export.yml",
        db_path=tmp_path / "db.duckdb",
    )

    await export_router.execute_export_background(
        "job-1",
        job_store,
        context,
        None,
        False,
    )

    assert job_store.failed_error is None
    assert job_store.completed_result is not None
    assert job_store.completed_result["metrics"]["generated_pages"] == 1
    assert job_store.completed_result["metrics"]["static_site_path"] == str(
        html_output_dir
    )


@pytest.mark.anyio
async def test_execute_export_background_fails_when_export_target_reports_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "exports" / "web"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text("<html>home</html>", encoding="utf-8")

    class DummyExporterService:
        def __init__(self, db_path: str, config) -> None:
            self.db_path = db_path

        def run_export(self, target_name=None):
            assert target_name == "web_pages"
            return {
                "web_pages": {
                    "status": "error",
                    "files_generated": 1,
                    "errors": 3,
                    "error": "3 erreurs pendant la génération",
                    "output_path": str(output_dir),
                }
            }

    monkeypatch.setattr(
        export_router, "get_export_config", lambda path: {"exports": []}
    )
    monkeypatch.setattr(
        export_router, "get_database_path", lambda: tmp_path / "db.duckdb"
    )
    monkeypatch.setattr(export_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        export_router, "Config", lambda config_dir, create_default=False: object()
    )
    monkeypatch.setattr(export_router, "ExporterService", DummyExporterService)

    job_store = _DummyJobStore()
    context = export_router.ExportExecutionContext(
        work_dir=tmp_path,
        config_path=tmp_path / "config" / "export.yml",
        db_path=tmp_path / "db.duckdb",
    )

    await export_router.execute_export_background(
        "job-1",
        job_store,
        context,
        ["web_pages"],
        False,
    )

    assert job_store.completed_result is None
    assert job_store.failed_error is not None
    assert "web_pages" in job_store.failed_error
    assert job_store.failed_result is not None
    assert job_store.failed_result["metrics"]["failed_exports"] == 1
    assert job_store.failed_result["metrics"]["generated_pages"] == 1
    assert job_store.failed_result["exports"]["web_pages"]["status"] == "error"


@pytest.mark.anyio
async def test_execute_export_background_uses_frozen_project_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    request_project = tmp_path / "essai_niamoto_2"
    request_project.mkdir(parents=True, exist_ok=True)
    current_project = tmp_path / "nouvelle-caledonie"
    current_project.mkdir(parents=True, exist_ok=True)

    output_dir = request_project / "exports" / "web"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text("<html>home</html>", encoding="utf-8")

    captured = {
        "config_path": None,
        "cwd": None,
        "db_path": None,
    }

    class DummyExporterService:
        def __init__(self, db_path: str, config) -> None:
            captured["db_path"] = db_path

        def run_export(self, target_name=None):
            captured["cwd"] = str(Path.cwd())
            return {
                "web_pages": {
                    "status": "success",
                    "files_generated": 1,
                    "errors": 0,
                    "output_path": str(output_dir),
                }
            }

    def fake_get_export_config(path):
        captured["config_path"] = str(path)
        return {"exports": [{"name": "web_pages", "exporter": "html_page_exporter"}]}

    monkeypatch.setattr(export_router, "get_export_config", fake_get_export_config)
    monkeypatch.setattr(export_router, "get_working_directory", lambda: current_project)
    monkeypatch.setattr(
        export_router, "get_database_path", lambda: current_project / "db.duckdb"
    )
    monkeypatch.setattr(
        export_router, "Config", lambda config_dir, create_default=False: object()
    )
    monkeypatch.setattr(export_router, "ExporterService", DummyExporterService)

    job_store = _DummyJobStore()
    context = export_router.ExportExecutionContext(
        work_dir=request_project,
        config_path=request_project / "config" / "export.yml",
        db_path=request_project / "db" / "niamoto.duckdb",
    )

    await export_router.execute_export_background(
        "job-1",
        job_store,
        context,
        None,
        False,
    )

    assert job_store.failed_error is None
    assert job_store.completed_result is not None
    assert captured["config_path"] == str(context.config_path)
    assert captured["cwd"] == str(request_project)
    assert captured["db_path"] == str(context.db_path)
    assert job_store.completed_result["metrics"]["static_site_path"] == str(output_dir)


@pytest.mark.anyio
async def test_execute_export_background_reuses_frozen_db_path_for_transform_phase(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "exports" / "web"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text("<html>home</html>", encoding="utf-8")

    captured = {
        "transform_db_path": None,
        "export_db_path": None,
    }

    class DummyTransformerService:
        def __init__(self, db_path: str, config, enable_cli_integration: bool) -> None:
            captured["transform_db_path"] = db_path

        def transform_data(self, *args):
            progress_callback = args[-1]
            progress_callback(
                {
                    "processed": 1,
                    "total": 1,
                    "group": "taxons",
                    "widget": "widget",
                    "item_label": "item",
                }
            )

    class DummyExporterService:
        def __init__(self, db_path: str, config) -> None:
            captured["export_db_path"] = db_path

        def run_export(self, target_name=None):
            return {
                "web_pages": {
                    "status": "success",
                    "files_generated": 1,
                    "errors": 0,
                    "output_path": str(output_dir),
                }
            }

    monkeypatch.setattr(
        export_router,
        "get_export_config",
        lambda path: {
            "exports": [{"name": "web_pages", "exporter": "html_page_exporter"}]
        },
    )
    monkeypatch.setattr(
        export_router, "Config", lambda config_dir, create_default=False: object()
    )
    monkeypatch.setattr(export_router, "TransformerService", DummyTransformerService)
    monkeypatch.setattr(export_router, "ExporterService", DummyExporterService)

    job_store = _DummyJobStore()
    context = export_router.ExportExecutionContext(
        work_dir=tmp_path,
        config_path=tmp_path / "config" / "export.yml",
        db_path=tmp_path / "db" / "niamoto.duckdb",
    )

    await export_router.execute_export_background(
        "job-1",
        job_store,
        context,
        None,
        True,
    )

    assert job_store.failed_error is None
    assert captured["transform_db_path"] == str(context.db_path)
    assert captured["export_db_path"] == str(context.db_path)
