"""Integration tests for export router history endpoints."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
import yaml

from niamoto.gui.api.app import create_app
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
