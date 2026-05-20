import asyncio
from types import SimpleNamespace

import pytest
import yaml
from fastapi.testclient import TestClient
from starlette.requests import Request

from niamoto.core.imports.config_models import ConnectorType
from niamoto.gui.api.app import create_app
from niamoto.gui.api import context
from niamoto.gui.api.routers import imports


@pytest.fixture(autouse=True)
def isolate_import_jobs():
    """Restore the module-level import job store after each test."""
    original_jobs = dict(imports.import_jobs)
    try:
        yield
    finally:
        imports.import_jobs.clear()
        imports.import_jobs.update(original_jobs)


def _request() -> Request:
    return Request({"type": "http", "headers": []})


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


def test_get_import_status_returns_500_without_working_directory(monkeypatch):
    monkeypatch.setattr(context, "get_working_directory", lambda: None)

    client = TestClient(create_app())
    response = client.get("/api/imports/status")

    assert response.status_code == 500
    assert response.json()["detail"] == "Working directory not set"


def test_get_import_status_classifies_references_and_datasets(monkeypatch, tmp_path):
    work_dir = tmp_path
    (work_dir / "config").mkdir()

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.database_path = str(work_dir / "db" / "niamoto.duckdb")

    class FakeDB:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def has_table(self, table_name):
            return table_name in {"entity_taxons", "dataset_occurrences"}

        def execute_sql(self, query, fetch=False):
            if "entity_taxons" in query:
                return [3]
            if "dataset_occurrences" in query:
                return [10]
            return [0]

    class FakeRegistry:
        def __init__(self, db):
            assert isinstance(db, FakeDB)

        def list_all(self):
            return [
                SimpleNamespace(
                    name="taxons",
                    kind=imports.EntityKind.REFERENCE,
                    table_name="entity_taxons",
                ),
                SimpleNamespace(
                    name="occurrences",
                    kind=imports.EntityKind.DATASET,
                    table_name="dataset_occurrences",
                ),
            ]

    monkeypatch.setattr(context, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(imports, "Config", FakeConfig)
    monkeypatch.setattr(imports, "open_database", lambda _database_path: FakeDB())
    monkeypatch.setattr(imports, "EntityRegistry", FakeRegistry)
    monkeypatch.setattr(imports, "quote_identifier", lambda _db, table_name: table_name)

    response = TestClient(create_app()).get("/api/imports/status")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [item["entity_name"] for item in payload["references"]] == ["taxons"]
    assert payload["references"][0]["row_count"] == 3
    assert [item["entity_name"] for item in payload["datasets"]] == ["occurrences"]
    assert payload["datasets"][0]["row_count"] == 10


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


def test_execute_import_reference_rejects_active_all_job_for_same_workdir(
    monkeypatch,
    tmp_path,
):
    work_dir = tmp_path
    active_job_id = "active-all-import"
    before_job_ids = set(imports.import_jobs)
    imports.import_jobs[active_job_id] = {
        **_base_job(active_job_id),
        "status": "running",
        "import_type": "all",
        "working_directory": str(work_dir.resolve()),
    }
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )

    try:
        response = TestClient(create_app()).post(
            "/api/imports/execute/reference/taxons",
            data={"reset_table": "true"},
        )
    finally:
        imports.import_jobs.pop(active_job_id, None)

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "message": "An import-all job is already pending or running",
        "job_id": active_job_id,
    }
    assert set(imports.import_jobs) == before_job_ids


def test_execute_import_reference_rejects_concurrent_job_for_same_target(
    monkeypatch,
    tmp_path,
):
    work_dir = tmp_path
    active_job_id = "active-reference-import"
    before_job_ids = set(imports.import_jobs)
    imports.import_jobs[active_job_id] = {
        **_base_job(active_job_id),
        "status": "running",
        "import_type": "reference",
        "entity_name": "taxons",
        "working_directory": str(work_dir.resolve()),
    }
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )

    try:
        response = TestClient(create_app()).post(
            "/api/imports/execute/reference/taxons",
            data={"reset_table": "true"},
        )
    finally:
        imports.import_jobs.pop(active_job_id, None)

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "message": "An import job for reference 'taxons' is already pending or running",
        "job_id": active_job_id,
    }
    assert set(imports.import_jobs) == before_job_ids


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


def test_execute_import_dataset_rejects_concurrent_job_for_same_target(
    monkeypatch,
    tmp_path,
):
    work_dir = tmp_path
    active_job_id = "active-dataset-import"
    before_job_ids = set(imports.import_jobs)
    imports.import_jobs[active_job_id] = {
        **_base_job(active_job_id),
        "status": "running",
        "import_type": "dataset",
        "entity_name": "occurrences",
        "working_directory": str(work_dir.resolve()),
    }
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )

    try:
        response = TestClient(create_app()).post(
            "/api/imports/execute/dataset/occurrences",
            data={"reset_table": "true"},
        )
    finally:
        imports.import_jobs.pop(active_job_id, None)

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "message": "An import job for dataset 'occurrences' is already pending or running",
        "job_id": active_job_id,
    }
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


def test_execute_import_reference_prunes_old_terminal_jobs(monkeypatch, tmp_path):
    monkeypatch.delenv("NIAMOTO_DESKTOP_AUTH_TOKEN", raising=False)
    before_jobs = dict(imports.import_jobs)
    work_dir = tmp_path
    (work_dir / "config").mkdir()

    references = {
        f"taxon-{index}": SimpleNamespace(
            connector=SimpleNamespace(type=ConnectorType.FILE)
        )
        for index in range(imports.MAX_RETAINED_IMPORT_JOBS + 3)
    }
    generic_config = SimpleNamespace(
        entities=SimpleNamespace(datasets={}, references=references)
    )

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.database_path = str(work_dir / "db" / "niamoto.duckdb")

        @property
        def get_imports_config(self):
            return generic_config

    class FakeImporterService:
        def __init__(self, db_path: str):
            self.db_path = db_path

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
        "niamoto.gui.api.services.preview_engine.engine.get_preview_engine",
        lambda: None,
    )

    try:
        imports.import_jobs.clear()
        client = TestClient(create_app())
        created_job_ids = []
        for index in range(imports.MAX_RETAINED_IMPORT_JOBS + 3):
            response = client.post(
                f"/api/imports/execute/reference/taxon-{index}",
                data={"reset_table": "false"},
            )
            assert response.status_code == 200
            created_job_ids.append(response.json()["job_id"])

        assert len(imports.import_jobs) == imports.MAX_RETAINED_IMPORT_JOBS
        assert created_job_ids[0] not in imports.import_jobs
        assert created_job_ids[1] not in imports.import_jobs
        assert created_job_ids[2] not in imports.import_jobs
        assert created_job_ids[-1] in imports.import_jobs

        missing_response = client.get(f"/api/imports/jobs/{created_job_ids[0]}")
        newest_response = client.get(f"/api/imports/jobs/{created_job_ids[-1]}")

        assert missing_response.status_code == 404
        assert newest_response.status_code == 200
        assert newest_response.json()["id"] == created_job_ids[-1]
    finally:
        imports.import_jobs.clear()
        imports.import_jobs.update(before_jobs)


def test_list_entities_returns_configured_references_and_datasets(
    monkeypatch, tmp_path
):
    work_dir = tmp_path
    (work_dir / "config").mkdir()

    generic_config = SimpleNamespace(
        entities=SimpleNamespace(
            references={
                "taxons": SimpleNamespace(
                    kind="hierarchical",
                    connector=SimpleNamespace(
                        type=ConnectorType.FILE,
                        path="imports/taxons.csv",
                    ),
                )
            },
            datasets={
                "occurrences": SimpleNamespace(
                    connector=SimpleNamespace(
                        type=ConnectorType.FILE,
                        path="imports/occurrences.csv",
                    ),
                    links=[{"source": "taxons"}],
                )
            },
        )
    )

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.database_path = str(work_dir / "db" / "missing.duckdb")

        @property
        def get_imports_config(self):
            return generic_config

    monkeypatch.setattr(imports, "Config", FakeConfig)
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )

    response = TestClient(create_app()).get("/api/imports/entities")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "references": [
            {
                "name": "taxons",
                "table_name": "reference_taxons",
                "kind": "hierarchical",
                "connector_type": "file",
                "path": "imports/taxons.csv",
            }
        ],
        "datasets": [
            {
                "name": "occurrences",
                "table_name": "dataset_occurrences",
                "connector_type": "file",
                "path": "imports/occurrences.csv",
                "links": 1,
            }
        ],
    }


def test_list_entities_returns_empty_lists_when_import_config_is_missing(
    monkeypatch, tmp_path
):
    work_dir = tmp_path
    (work_dir / "config").mkdir()

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            raise imports.ConfigurationError(config_key="import", message="missing")

    monkeypatch.setattr(imports, "Config", FakeConfig)
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )

    response = TestClient(create_app()).get("/api/imports/entities")

    assert response.status_code == 200, response.text
    assert response.json() == {"references": [], "datasets": []}


def test_list_entities_uses_registry_table_names(monkeypatch, tmp_path):
    work_dir = tmp_path
    db_path = work_dir / "db" / "niamoto.duckdb"
    db_path.parent.mkdir(parents=True)
    db_path.write_text("", encoding="utf-8")
    (work_dir / "config").mkdir()

    generic_config = SimpleNamespace(
        entities=SimpleNamespace(
            references={
                "taxons": SimpleNamespace(
                    kind="hierarchical",
                    connector=SimpleNamespace(
                        type=ConnectorType.FILE,
                        path="imports/taxons.csv",
                    ),
                )
            },
            datasets={
                "occurrences": SimpleNamespace(
                    connector=SimpleNamespace(
                        type=ConnectorType.FILE,
                        path="imports/occurrences.csv",
                    ),
                    links=[],
                )
            },
        )
    )

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.database_path = str(db_path)

        @property
        def get_imports_config(self):
            return generic_config

    class FakeDB:
        def has_table(self, table_name):
            assert table_name == "niamoto_entities"
            return True

    class FakeOpenDatabase:
        def __init__(self, database_path):
            assert database_path == str(db_path)

        def __enter__(self):
            return FakeDB()

        def __exit__(self, exc_type, exc, tb):
            return None

    class FakeRegistry:
        ENTITIES_TABLE = "niamoto_entities"

        def __init__(self, db):
            assert isinstance(db, FakeDB)

        def list_entities(self):
            return [
                SimpleNamespace(name="taxons", table_name="entity_taxons"),
                SimpleNamespace(
                    name="occurrences", table_name="dataset_occurrences_custom"
                ),
            ]

    monkeypatch.setattr(imports, "Config", FakeConfig)
    monkeypatch.setattr(imports, "open_database", FakeOpenDatabase)
    monkeypatch.setattr(imports, "EntityRegistry", FakeRegistry)
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )

    response = TestClient(create_app()).get("/api/imports/entities")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["references"][0]["table_name"] == "entity_taxons"
    assert payload["datasets"][0]["table_name"] == "dataset_occurrences_custom"


def test_delete_entity_drops_registry_table_before_removing_config(
    monkeypatch, tmp_path
):
    work_dir = tmp_path
    config_dir = work_dir / "config"
    config_dir.mkdir()
    import_path = config_dir / "import.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "entities": {
                    "datasets": {},
                    "references": {
                        "plots": {
                            "connector": {
                                "type": "file",
                                "format": "csv",
                                "path": "imports/plots.csv",
                            }
                        }
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    events = []

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.database_path = str(work_dir / "db" / "niamoto.duckdb")

    class FakeDB:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def has_table(self, table_name):
            return table_name in {
                imports.EntityRegistry.ENTITIES_TABLE,
                "actual_imported_plots",
            }

        def execute_sql(self, sql):
            current_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
            assert "plots" in current_config["entities"]["references"]
            events.append(sql)

    class FakeRegistry:
        ENTITIES_TABLE = imports.EntityRegistry.ENTITIES_TABLE

        def __init__(self, db):
            self.db = db

        def get(self, entity_name):
            assert entity_name == "plots"
            return SimpleNamespace(table_name="actual_imported_plots")

    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )
    monkeypatch.setattr(imports, "Config", FakeConfig)
    monkeypatch.setattr(imports, "open_database", lambda _path: FakeDB())
    monkeypatch.setattr(imports, "EntityRegistry", FakeRegistry)
    monkeypatch.setattr(imports, "quote_identifier", lambda _db, name: f'"{name}"')

    response = asyncio.run(
        imports.delete_entity(_request(), "reference", "plots", delete_table=True)
    )

    assert response["success"] is True
    assert response["table_dropped"] is True
    assert events == ['DROP TABLE IF EXISTS "actual_imported_plots"']
    updated_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    assert "plots" not in updated_config["entities"]["references"]


def test_delete_dataset_fallback_drops_dataset_table_not_reference_collision(
    monkeypatch, tmp_path
):
    work_dir = tmp_path
    config_dir = work_dir / "config"
    config_dir.mkdir()
    import_path = config_dir / "import.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "entities": {
                    "datasets": {"plots": {"connector": {"type": "file"}}},
                    "references": {"plots": {"connector": {"type": "file"}}},
                },
            }
        ),
        encoding="utf-8",
    )
    dropped = []

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.database_path = str(work_dir / "db" / "niamoto.duckdb")

    class FakeDB:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def has_table(self, table_name):
            return table_name in {"dataset_plots", "reference_plots"}

        def execute_sql(self, sql):
            dropped.append(sql)

    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )
    monkeypatch.setattr(imports, "Config", FakeConfig)
    monkeypatch.setattr(imports, "open_database", lambda _path: FakeDB())
    monkeypatch.setattr(imports, "quote_identifier", lambda _db, name: f'"{name}"')

    response = asyncio.run(
        imports.delete_entity(_request(), "dataset", "plots", delete_table=True)
    )

    assert response["success"] is True
    assert response["table_dropped"] is True
    assert dropped == ['DROP TABLE IF EXISTS "dataset_plots"']
    updated_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    assert "plots" not in updated_config["entities"]["datasets"]
    assert "plots" in updated_config["entities"]["references"]


def test_delete_entity_keeps_config_when_requested_table_drop_fails(
    monkeypatch, tmp_path
):
    work_dir = tmp_path
    config_dir = work_dir / "config"
    config_dir.mkdir()
    import_path = config_dir / "import.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "entities": {
                    "datasets": {"occurrences": {"connector": {"type": "file"}}},
                    "references": {},
                },
            }
        ),
        encoding="utf-8",
    )

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.database_path = str(work_dir / "db" / "niamoto.duckdb")

    class FakeDB:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def has_table(self, table_name):
            return table_name in {
                imports.EntityRegistry.ENTITIES_TABLE,
                "dataset_occurrences",
            }

        def execute_sql(self, sql):
            raise RuntimeError("drop failed")

    class FakeRegistry:
        ENTITIES_TABLE = imports.EntityRegistry.ENTITIES_TABLE

        def __init__(self, db):
            self.db = db

        def get(self, entity_name):
            return SimpleNamespace(table_name="dataset_occurrences")

    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: work_dir
    )
    monkeypatch.setattr(imports, "Config", FakeConfig)
    monkeypatch.setattr(imports, "open_database", lambda _path: FakeDB())
    monkeypatch.setattr(imports, "EntityRegistry", FakeRegistry)
    monkeypatch.setattr(imports, "quote_identifier", lambda _db, name: f'"{name}"')

    with pytest.raises(imports.HTTPException) as exc_info:
        asyncio.run(
            imports.delete_entity(
                _request(), "dataset", "occurrences", delete_table=True
            )
        )

    assert exc_info.value.status_code == 500
    current_config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    assert "occurrences" in current_config["entities"]["datasets"]


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


def test_list_import_jobs_redacts_internal_tracebacks(monkeypatch):
    monkeypatch.setattr("niamoto.gui.api.context.get_working_directory", lambda: None)
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


@pytest.mark.parametrize("query", ["limit=0", "limit=-1", "offset=-1"])
def test_list_import_jobs_rejects_invalid_pagination(query):
    client = TestClient(create_app())

    response = client.get(f"/api/imports/jobs?{query}")

    assert response.status_code == 422


def test_list_import_jobs_accepts_valid_pagination(monkeypatch):
    monkeypatch.setattr("niamoto.gui.api.context.get_working_directory", lambda: None)
    before_jobs = dict(imports.import_jobs)
    jobs = [
        ("old-job", "2026-01-01T00:00:00+00:00"),
        ("middle-job", "2026-01-02T00:00:00+00:00"),
        ("new-job", "2026-01-03T00:00:00+00:00"),
    ]
    imports.import_jobs.clear()
    for job_id, created_at in jobs:
        imports.import_jobs[job_id] = {
            **_base_job(job_id),
            "created_at": created_at,
        }

    try:
        client = TestClient(create_app())

        response = client.get("/api/imports/jobs?limit=1&offset=1")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 3
        assert payload["limit"] == 1
        assert payload["offset"] == 1
        assert [job["id"] for job in payload["jobs"]] == ["middle-job"]
    finally:
        imports.import_jobs.clear()
        imports.import_jobs.update(before_jobs)


def test_list_import_jobs_filters_to_current_working_directory(monkeypatch, tmp_path):
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    project_a.mkdir()
    project_b.mkdir()

    imports.import_jobs["job-a"] = {
        **_base_job("job-a"),
        "working_directory": str(project_a.resolve()),
        "created_at": "2026-01-02T00:00:00+00:00",
    }
    imports.import_jobs["job-b"] = {
        **_base_job("job-b"),
        "working_directory": str(project_b.resolve()),
        "created_at": "2026-01-03T00:00:00+00:00",
    }
    imports.import_jobs["legacy-job"] = {
        **_base_job("legacy-job"),
        "working_directory": None,
        "created_at": "2026-01-04T00:00:00+00:00",
    }
    monkeypatch.setattr(
        "niamoto.gui.api.context.get_working_directory", lambda: project_b
    )

    response = TestClient(create_app()).get("/api/imports/jobs")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert [job["id"] for job in payload["jobs"]] == ["job-b"]


def test_impact_check_returns_500_without_working_directory(monkeypatch):
    monkeypatch.setattr("niamoto.gui.api.context.get_working_directory", lambda: None)

    response = TestClient(create_app()).post(
        "/api/imports/impact-check",
        json={"file_path": "imports/foo.csv"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Working directory not set"


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
