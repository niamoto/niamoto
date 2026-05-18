"""Regression tests for dataset configuration routes."""

import asyncio
import json
import threading
import time

import duckdb
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import config as config_router


def test_update_reference_config_serializes_concurrent_import_writes(
    monkeypatch,
    tmp_path,
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    import_path = config_dir / "import.yml"
    import_path.write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "references": {
                        "taxons": {"kind": "hierarchical"},
                        "plots": {"kind": "generic"},
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)
    first_backup_entered = threading.Event()
    release_first_backup = threading.Event()
    backup_call_count = 0
    backup_call_lock = threading.Lock()

    def delayed_backup(_config_path):
        nonlocal backup_call_count
        with backup_call_lock:
            backup_call_count += 1
            call_number = backup_call_count
        if call_number == 1:
            first_backup_entered.set()
            release_first_backup.wait(timeout=2)
        return None

    monkeypatch.setattr(config_router, "create_backup", delayed_backup)

    errors: list[BaseException] = []

    def update_reference(reference_name: str, payload: dict):
        try:
            asyncio.run(config_router.update_reference_config(reference_name, payload))
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(
        target=update_reference,
        args=("taxons", {"kind": "hierarchical", "description": "Taxons updated"}),
    )
    second = threading.Thread(
        target=update_reference,
        args=("plots", {"kind": "generic", "description": "Plots updated"}),
    )

    first.start()
    assert first_backup_entered.wait(timeout=2)
    second.start()
    time.sleep(0.05)
    release_first_backup.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []

    saved = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    refs = saved["entities"]["references"]
    assert refs["taxons"]["description"] == "Taxons updated"
    assert refs["plots"]["description"] == "Plots updated"


def test_update_dataset_config_rejects_malformed_entities_without_writing(
    monkeypatch,
    tmp_path,
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    import_path = config_dir / "import.yml"
    original_config = {"metadata": {"keep": True}, "entities": ["not", "a", "dict"]}
    original_text = yaml.safe_dump(original_config, sort_keys=False)
    import_path.write_text(original_text, encoding="utf-8")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.put(
        "/api/config/datasets/observations/config",
        json={"connector": {"type": "file"}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Malformed import.yml: entities must be an object"
    )
    assert import_path.read_text(encoding="utf-8") == original_text
    assert not (config_dir / "backups").exists()


def test_update_dataset_config_rejects_malformed_datasets_without_writing(
    monkeypatch,
    tmp_path,
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    import_path = config_dir / "import.yml"
    original_config = {
        "entities": {
            "references": {"taxons": {}},
            "datasets": ["not", "a", "dict"],
        }
    }
    original_text = yaml.safe_dump(original_config, sort_keys=False)
    import_path.write_text(original_text, encoding="utf-8")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.put(
        "/api/config/datasets/observations/config",
        json={"connector": {"type": "file"}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Malformed import.yml: entities.datasets must be an object"
    )
    assert import_path.read_text(encoding="utf-8") == original_text
    assert not (config_dir / "backups").exists()


def test_get_datasets_counts_registry_table_names_requiring_quotes(
    monkeypatch,
    tmp_path,
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir()
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {
                        "observations": {
                            "description": "Field observations",
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    conn = duckdb.connect(str(db_dir / "niamoto.duckdb"))
    try:
        conn.execute('CREATE TABLE "dataset-observations" (id INTEGER)')
        conn.execute('INSERT INTO "dataset-observations" VALUES (1), (2)')
        conn.execute(
            """
            CREATE TABLE niamoto_metadata_entities (
                name TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                table_name TEXT NOT NULL,
                config TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO niamoto_metadata_entities (name, kind, table_name, config)
            VALUES (?, ?, ?, ?)
            """,
            [
                "observations",
                "dataset",
                "dataset-observations",
                json.dumps({}),
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get("/api/config/datasets")

    assert response.status_code == 200
    assert response.json() == {
        "datasets": [
            {
                "name": "observations",
                "table_name": "dataset-observations",
                "description": "Field observations",
                "schema_fields": [],
                "entity_count": 2,
            }
        ],
        "total": 1,
    }
