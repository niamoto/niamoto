import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

from niamoto.core.imports.config_models import ConnectorType
from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import imports


def _base_job(job_id: str = "job-1") -> dict:
    return {
        "id": job_id,
        "status": "pending",
        "import_type": "all",
        "working_directory": None,
        "created_at": "now",
        "started_at": None,
        "completed_at": None,
        "progress": 0,
        "phase": "pending",
        "message": "",
        "total_entities": 0,
        "processed_entities": 0,
        "current_entity": None,
        "current_entity_type": None,
        "errors": [],
        "error_details": None,
        "warnings": [],
        "events": [],
    }


def test_process_generic_import_all_emits_entity_events(monkeypatch, tmp_path):
    work_dir = tmp_path
    (work_dir / "config").mkdir()

    generic_config = SimpleNamespace(
        entities=SimpleNamespace(
            datasets={
                "occurrences": SimpleNamespace(
                    connector=SimpleNamespace(type=ConnectorType.FILE)
                )
            },
            references={
                "taxons": SimpleNamespace(
                    connector=SimpleNamespace(type=ConnectorType.DERIVED)
                ),
                "shapes": SimpleNamespace(
                    connector=SimpleNamespace(type=ConnectorType.FILE_MULTI_FEATURE)
                ),
            },
        )
    )

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.database_path = str(work_dir / "db" / "niamoto.duckdb")

        @property
        def get_imports_config(self):
            return generic_config

    class FakeDB:
        is_duckdb = False

        def optimize_database(self):
            return None

    class FakeImporterService:
        def __init__(self, db_path: str):
            self.db = FakeDB()

        def import_dataset(self, name, config, reset_table=False):
            return f"dataset:{name}"

        def import_reference(self, name, config, reset_table=False):
            return f"reference:{name}"

        def close(self):
            return None

    monkeypatch.setattr(imports, "Config", FakeConfig)
    monkeypatch.setattr(imports, "ImporterService", FakeImporterService)
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.config_scaffold.scaffold_configs",
        lambda *_args, **_kwargs: (False, "noop"),
    )
    monkeypatch.setattr(
        "niamoto.gui.api.services.preview_engine.engine.get_preview_engine",
        lambda: None,
    )

    job_id = "job-success"
    imports.import_jobs[job_id] = _base_job(job_id)

    asyncio.run(imports.process_generic_import_all(job_id, reset_table=False))

    job = imports.import_jobs[job_id]
    assert job["status"] == "completed"
    assert job["total_entities"] == 3
    assert job["processed_entities"] == 3
    assert job["phase"] == "completed"
    assert any(event["message"] == "Imported occurrences" for event in job["events"])
    assert any(event["message"] == "Imported taxons" for event in job["events"])
    assert any(event["message"] == "Imported shapes" for event in job["events"])


def test_execute_import_all_rejects_concurrent_job_for_same_workdir(
    monkeypatch,
    tmp_path,
):
    work_dir = tmp_path
    active_job_id = "active-import"
    imports.import_jobs[active_job_id] = {
        **_base_job(active_job_id),
        "status": "running",
        "working_directory": str(work_dir.resolve()),
    }
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )

    try:
        client = TestClient(create_app())
        response = client.post(
            "/api/imports/execute/all", data={"reset_table": "false"}
        )
    finally:
        imports.import_jobs.pop(active_job_id, None)

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "message": "An import-all job is already pending or running",
        "job_id": active_job_id,
    }


def test_execute_import_dataset_rejects_missing_desktop_auth_before_job_creation(
    monkeypatch,
):
    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
    before_job_ids = set(imports.import_jobs)

    client = TestClient(create_app())
    response = client.post(
        "/api/imports/execute/dataset/occurrences",
        data={"reset_table": "true"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid desktop auth token."
    assert set(imports.import_jobs) == before_job_ids


def test_execute_import_dataset_accepts_valid_desktop_auth(monkeypatch):
    monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")

    async def noop_process_generic_import_entity(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        imports, "process_generic_import_entity", noop_process_generic_import_entity
    )

    before_job_ids = set(imports.import_jobs)
    client = TestClient(create_app())
    response = client.post(
        "/api/imports/execute/dataset/occurrences",
        data={"reset_table": "true"},
        headers={"x-niamoto-desktop-token": "desktop-secret"},
    )

    try:
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        assert job_id not in before_job_ids
        assert imports.import_jobs[job_id]["entity_name"] == "occurrences"
        assert imports.import_jobs[job_id]["import_type"] == "dataset"
    finally:
        for job_id in set(imports.import_jobs) - before_job_ids:
            imports.import_jobs.pop(job_id, None)


def test_process_generic_import_all_records_failure_event(monkeypatch, tmp_path):
    work_dir = tmp_path
    (work_dir / "config").mkdir()

    generic_config = SimpleNamespace(
        entities=SimpleNamespace(
            datasets={
                "occurrences": SimpleNamespace(
                    connector=SimpleNamespace(type=ConnectorType.FILE)
                )
            },
            references={},
        )
    )

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.database_path = str(work_dir / "db" / "niamoto.duckdb")

        @property
        def get_imports_config(self):
            return generic_config

    class FakeDB:
        is_duckdb = False

    class FakeImporterService:
        def __init__(self, db_path: str):
            self.db = FakeDB()

        def import_dataset(self, name, config, reset_table=False):
            raise RuntimeError("boom")

        def close(self):
            return None

    monkeypatch.setattr(imports, "Config", FakeConfig)
    monkeypatch.setattr(imports, "ImporterService", FakeImporterService)
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )

    job_id = "job-fail"
    imports.import_jobs[job_id] = _base_job(job_id)

    asyncio.run(imports.process_generic_import_all(job_id, reset_table=False))

    job = imports.import_jobs[job_id]
    assert job["status"] == "failed"
    assert job["phase"] == "failed"
    assert job["errors"]
    assert job["error_details"]["error_type"] == "RuntimeError"
    assert "boom" in job["error_details"]["message"]
    assert "traceback" in job["error_details"]
    assert job["events"][-1]["kind"] == "error"
    assert "Import failed" in job["events"][-1]["message"]
    assert job["events"][-1]["details"]["error_type"] == "RuntimeError"


def test_get_job_status_redacts_internal_tracebacks():
    job_id = "job-redacted"
    imports.import_jobs[job_id] = _base_job(job_id)
    imports.import_jobs[job_id].update(
        {
            "status": "failed",
            "error_details": {
                "message": "boom",
                "error_type": "RuntimeError",
                "traceback": "Traceback with /private/project/path",
                "cause": {
                    "message": "inner",
                    "traceback": "Nested traceback",
                },
            },
            "events": [
                {
                    "kind": "error",
                    "message": "Import failed",
                    "details": {
                        "message": "boom",
                        "error_type": "RuntimeError",
                        "traceback": "Event traceback",
                    },
                }
            ],
        }
    )

    try:
        client = TestClient(create_app())
        response = client.get(f"/api/imports/jobs/{job_id}")
    finally:
        imports.import_jobs.pop(job_id, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["error_details"]["message"] == "boom"
    assert "traceback" not in payload["error_details"]
    assert "traceback" not in payload["error_details"]["cause"]
    assert "traceback" not in payload["events"][0]["details"]


def test_list_import_jobs_redacts_internal_tracebacks():
    job_id = "job-list-redacted"
    imports.import_jobs[job_id] = _base_job(job_id)
    imports.import_jobs[job_id].update(
        {
            "status": "failed",
            "error_details": {
                "message": "boom",
                "error_type": "RuntimeError",
                "traceback": "Traceback with /private/project/path",
            },
            "events": [
                {
                    "kind": "error",
                    "message": "Import failed",
                    "details": {
                        "message": "boom",
                        "traceback": "Event traceback",
                    },
                }
            ],
        }
    )

    try:
        client = TestClient(create_app())
        response = client.get("/api/imports/jobs")
    finally:
        imports.import_jobs.pop(job_id, None)

    assert response.status_code == 200
    payload = response.json()
    listed_job = next(job for job in payload["jobs"] if job["id"] == job_id)
    assert "traceback" not in listed_job["error_details"]
    assert "traceback" not in listed_job["events"][0]["details"]


def test_impact_check_returns_skip_reason_for_vector_entity(monkeypatch, tmp_path):
    work_dir = tmp_path
    (work_dir / "config").mkdir()

    class FakeCompatibilityService:
        def __init__(self, working_directory):
            self.working_directory = working_directory

        def resolve_entity(self, filename: str):
            assert filename == "geo.gpkg"
            return "geo"

        def check_compatibility(self, entity_name: str, file_path: str):
            assert entity_name == "geo"
            assert file_path == "imports/geo.gpkg"
            return SimpleNamespace(
                entity_name="geo",
                matched_columns=[],
                impacts=[],
                error=None,
                skipped_reason="Not supported in V1 (GPKG)",
                has_blockers=False,
                has_warnings=False,
                has_opportunities=False,
            )

    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )
    monkeypatch.setattr(
        "niamoto.core.services.compatibility.CompatibilityService",
        FakeCompatibilityService,
    )

    response = asyncio.run(
        imports.impact_check(imports.ImpactCheckRequest(file_path="imports/geo.gpkg"))
    )

    assert response.entity_name == "geo"
    assert response.skipped_reason == "Not supported in V1 (GPKG)"
    assert response.error is None
    assert response.impacts == []


def test_impact_check_returns_info_message(monkeypatch, tmp_path):
    work_dir = tmp_path
    (work_dir / "config").mkdir()

    class FakeCompatibilityService:
        def __init__(self, working_directory):
            self.working_directory = working_directory

        def resolve_entity(self, filename: str):
            assert filename == "raw_plot_stats.csv"
            return "plot_stats"

        def check_compatibility(self, entity_name: str, file_path: str):
            assert entity_name == "plot_stats"
            assert file_path == "imports/raw_plot_stats.csv"
            return SimpleNamespace(
                entity_name="plot_stats",
                matched_columns=[],
                impacts=[],
                error=None,
                skipped_reason=None,
                info_message="First check for auxiliary source",
                has_blockers=False,
                has_warnings=False,
                has_opportunities=False,
            )

    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )
    monkeypatch.setattr(
        "niamoto.core.services.compatibility.CompatibilityService",
        FakeCompatibilityService,
    )

    response = asyncio.run(
        imports.impact_check(
            imports.ImpactCheckRequest(file_path="imports/raw_plot_stats.csv")
        )
    )

    assert response.entity_name == "plot_stats"
    assert response.info_message == "First check for auxiliary source"
    assert response.error is None
