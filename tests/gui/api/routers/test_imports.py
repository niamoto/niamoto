import asyncio
from types import SimpleNamespace


from niamoto.core.imports.config_models import ConnectorType
from niamoto.gui.api.routers import imports


def _base_job(job_id: str = "job-1") -> dict:
    return {
        "id": job_id,
        "status": "pending",
        "import_type": "all",
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
