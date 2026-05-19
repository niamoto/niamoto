"""Regression tests for dataset configuration routes."""

import asyncio
from copy import deepcopy
import json
import threading
import time

import duckdb
import pytest
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


def test_update_transform_widget_serializes_concurrent_writes(monkeypatch):
    current_groups = [{"group_by": "taxons", "sources": [], "widgets_data": {}}]
    config_lock = threading.Lock()
    first_save_entered = threading.Event()
    release_first_save = threading.Event()
    errors: list[BaseException] = []

    def fake_load_transform_config():
        with config_lock:
            return deepcopy(current_groups)

    def fake_save_transform_config(groups):
        nonlocal current_groups
        widgets = groups[0]["widgets_data"]
        if "first_widget" in widgets and len(widgets) == 1:
            first_save_entered.set()
            release_first_save.wait(timeout=2)
        with config_lock:
            current_groups = deepcopy(groups)

    monkeypatch.setattr(
        config_router, "_load_transform_config", fake_load_transform_config
    )
    monkeypatch.setattr(
        config_router, "_save_transform_config", fake_save_transform_config
    )

    def update_widget(widget_id: str):
        try:
            asyncio.run(
                config_router.update_transform_widget(
                    "taxons",
                    widget_id,
                    config_router.TransformWidgetUpdate(
                        plugin="field_aggregator",
                        params={"widget": widget_id},
                    ),
                )
            )
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(target=update_widget, args=("first_widget",))
    second = threading.Thread(target=update_widget, args=("second_widget",))

    first.start()
    assert first_save_entered.wait(timeout=2)
    second.start()
    time.sleep(0.05)
    release_first_save.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert set(current_groups[0]["widgets_data"]) == {"first_widget", "second_widget"}


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


def test_get_dataset_config_returns_named_dataset(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {
                        "observations": {
                            "connector": {
                                "type": "file",
                                "format": "csv",
                                "path": "imports/observations.csv",
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).get("/api/config/datasets/observations/config")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "name": "observations",
        "config": {
            "connector": {
                "type": "file",
                "format": "csv",
                "path": "imports/observations.csv",
            }
        },
    }


def test_get_dataset_config_rejects_missing_dataset(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump({"entities": {"datasets": {"observations": {}}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).get("/api/config/datasets/missing/config")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset 'missing' not found in import.yml"


def test_get_dataset_config_rejects_missing_import_config(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    (work_dir / "config").mkdir(parents=True)
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).get("/api/config/datasets/observations/config")

    assert response.status_code == 404
    assert response.json()["detail"] == "import.yml not found"


def test_update_config_preserves_existing_file_when_yaml_write_fails(
    monkeypatch,
    tmp_path,
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.yml"
    original_text = yaml.safe_dump(
        {"project": {"name": "Existing"}, "database": {"path": "db/niamoto.duckdb"}},
        sort_keys=False,
    )
    config_path.write_text(original_text, encoding="utf-8")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    def fail_dump(*_args, **_kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(config_router.yaml, "safe_dump", fail_dump)

    client = TestClient(create_app())
    response = client.put(
        "/api/config/config",
        json={
            "content": {
                "project": {"name": "Replacement"},
                "database": {"path": "db/replacement.duckdb"},
            },
            "backup": False,
        },
    )

    assert response.status_code == 500
    assert "simulated disk failure" in response.json()["detail"]
    assert config_path.read_text(encoding="utf-8") == original_text
    assert list(config_dir.glob(".config.yml.*.tmp")) == []


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


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"connector": {"type": "file"}, "schema": {"id_field": "id", "fields": []}},
    ],
)
def test_update_dataset_config_rejects_invalid_dataset_without_writing(
    monkeypatch,
    tmp_path,
    payload,
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    import_path = config_dir / "import.yml"
    original_config = {
        "entities": {
            "references": {},
            "datasets": {
                "observations": {
                    "connector": {
                        "type": "file",
                        "format": "csv",
                        "path": "imports/observations.csv",
                    },
                    "schema": {"id_field": "id", "fields": []},
                }
            },
        }
    }
    original_text = yaml.safe_dump(original_config, sort_keys=False)
    import_path.write_text(original_text, encoding="utf-8")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.put(
        "/api/config/datasets/observations/config",
        json=payload,
    )

    assert response.status_code == 422
    assert "Invalid dataset configuration" in response.json()["detail"]
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


def test_get_references_counts_and_detects_hierarchy_for_quoted_table_names(
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
                    "references": {
                        "plots": {
                            "kind": "hierarchical",
                            "description": "Plot hierarchy",
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    conn = duckdb.connect(str(db_dir / "niamoto.duckdb"))
    try:
        conn.execute(
            'CREATE TABLE "reference-plots" (id INTEGER, name TEXT, lft INTEGER, rght INTEGER)'
        )
        conn.execute("INSERT INTO \"reference-plots\" VALUES (1, 'Root', 1, 2)")
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
                "plots",
                "reference",
                "reference-plots",
                json.dumps({}),
            ],
        )
    finally:
        conn.close()

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get("/api/config/references")

    assert response.status_code == 200, response.text
    reference = response.json()["references"][0]
    assert reference["table_name"] == "reference-plots"
    assert reference["entity_count"] == 1
    assert reference["is_hierarchical"] is True
    assert reference["hierarchy_fields"]["has_nested_set"] is True


def test_get_transform_widget_treats_null_widgets_data_as_empty(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_transform_config",
        lambda: [{"group_by": "plots", "widgets_data": None}],
    )

    client = TestClient(create_app())
    response = client.get("/api/config/transform/plots/widgets/missing")

    assert response.status_code == 404
    assert "Widget 'missing' not found" in response.json()["detail"]
