"""Tests for EntityRegistry v2 import configuration routes."""

from datetime import datetime
from pathlib import Path
import threading
import time

from fastapi.testclient import TestClient

from niamoto.core.imports.config_models import GenericImportConfig
from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import config as config_router


def test_save_import_v2_rejects_semantically_invalid_yaml_without_writing(
    monkeypatch,
    tmp_path,
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    import_path = config_dir / "import.yml"
    import_path.write_text("version: '2'\nentities: {}\n", encoding="utf-8")
    monkeypatch.setattr(config_router, "ensure_config_dir", lambda: config_dir)

    client = TestClient(create_app())
    response = client.put("/api/config/import/v2", json={"config": "null\n"})

    assert response.status_code == 400
    assert response.json()["detail"]["errors"]["_global"] == [
        "Invalid YAML: configuration must be a valid YAML object, not empty or null"
    ]
    assert import_path.read_text(encoding="utf-8") == "version: '2'\nentities: {}\n"


def test_create_backup_preserves_rapid_successive_backups(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    import_path = config_dir / "import.yml"
    import_path.write_text("version: '2'\nentities: {}\n", encoding="utf-8")

    class FixedDatetime:
        @classmethod
        def now(cls):
            return datetime(2026, 5, 18, 17, 15, 0, 123456)

    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(config_router, "datetime", FixedDatetime)

    first_backup = config_router.create_backup(import_path)
    import_path.write_text(
        "version: '2'\nentities:\n  references: {}\n", encoding="utf-8"
    )
    second_backup = config_router.create_backup(import_path)

    assert first_backup is not None
    assert second_backup is not None
    assert first_backup != second_backup
    assert first_backup.read_text(encoding="utf-8") == "version: '2'\nentities: {}\n"
    assert (
        second_backup.read_text(encoding="utf-8")
        == "version: '2'\nentities:\n  references: {}\n"
    )


def test_list_backups_does_not_expose_absolute_paths(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    backup_dir = work_dir / "config" / "backups"
    backup_dir.mkdir(parents=True)
    backup_path = backup_dir / "import_20260518_171500_123456.yml"
    backup_path.write_text("version: '2'\n", encoding="utf-8")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get("/api/config/import/backup/list")

    assert response.status_code == 200, response.text
    backups = response.json()["backups"]
    assert backups == [
        {
            "filename": backup_path.name,
            "size": backup_path.stat().st_size,
            "modified": backups[0]["modified"],
        }
    ]
    assert "path" not in backups[0]
    assert str(work_dir) not in response.text


def test_list_backups_filters_to_requested_config(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    backup_dir = work_dir / "config" / "backups"
    backup_dir.mkdir(parents=True)
    import_backup = backup_dir / "import_20260518_171500_123456.yml"
    transform_backup = backup_dir / "transform_20260518_171500_123456.yml"
    import_backup.write_text("version: '2'\n", encoding="utf-8")
    transform_backup.write_text("groups: []\n", encoding="utf-8")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get("/api/config/import/backup/list")

    assert response.status_code == 200, response.text
    filenames = [backup["filename"] for backup in response.json()["backups"]]
    assert filenames == [import_backup.name]


def test_list_backups_rejects_wildcard_config_name(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    backup_dir = work_dir / "config" / "backups"
    backup_dir.mkdir(parents=True)
    (backup_dir / "import_20260518_171500_123456.yml").write_text(
        "version: '2'\n", encoding="utf-8"
    )
    (backup_dir / "transform_20260518_171500_123456.yml").write_text(
        "groups: []\n", encoding="utf-8"
    )

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get("/api/config/*/backup/list")

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid configuration name")


def test_update_config_rejects_invalid_payload_without_writing(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    files = {
        "import": config_dir / "import.yml",
        "transform": config_dir / "transform.yml",
        "export": config_dir / "export.yml",
    }
    original = {
        "import": "version: '1.0'\nentities:\n  datasets:\n    occurrences: {}\n",
        "transform": "- group_by: taxons\n  sources: []\n",
        "export": "exports: []\n",
    }
    for config_name, path in files.items():
        path.write_text(original[config_name], encoding="utf-8")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(config_router, "ensure_config_dir", lambda: config_dir)

    client = TestClient(create_app())
    invalid_payloads = {
        "import": {},
        "transform": {},
        "export": {},
    }

    for config_name, content in invalid_payloads.items():
        response = client.put(f"/api/config/{config_name}", json={"content": content})

        assert response.status_code == 400
        assert response.json()["detail"]["valid"] is False
        assert files[config_name].read_text(encoding="utf-8") == original[config_name]


def test_update_config_uses_export_write_lock(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    export_path = config_dir / "export.yml"
    export_path.write_text("exports: []\n", encoding="utf-8")
    writes = []
    response_holder = {}

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(config_router, "ensure_config_dir", lambda: config_dir)
    monkeypatch.setattr(
        config_router,
        "_write_yaml_atomic",
        lambda path, content: writes.append((path, content)),
    )

    client = TestClient(create_app())
    config_router.EXPORT_CONFIG_WRITE_LOCK.acquire()

    def update_export():
        response_holder["response"] = client.put(
            "/api/config/export",
            json={"content": {"exports": []}, "backup": False},
        )

    thread = threading.Thread(target=update_export)
    try:
        thread.start()
        time.sleep(0.05)
        assert writes == []
    finally:
        config_router.EXPORT_CONFIG_WRITE_LOCK.release()

    thread.join(timeout=2)

    assert not thread.is_alive()
    assert response_holder["response"].status_code == 200
    assert writes == [(export_path, {"exports": []})]


def test_update_config_rejects_structurally_invalid_export_without_writing(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    export_path = config_dir / "export.yml"
    original_text = "exports: []\n"
    export_path.write_text(original_text, encoding="utf-8")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(config_router, "ensure_config_dir", lambda: config_dir)

    response = TestClient(create_app()).put(
        "/api/config/export",
        json={
            "content": {
                "exports": [
                    {
                        "name": "broken_target",
                        "enabled": True,
                    }
                ]
            },
            "backup": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["valid"] is False
    assert "Invalid export configuration" in response.json()["detail"]["errors"][0]
    assert export_path.read_text(encoding="utf-8") == original_text


def test_restore_backup_rejects_paths_outside_backup_directory(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    backup_dir = config_dir / "backups"
    backup_dir.mkdir(parents=True)
    config_path = config_dir / "import.yml"
    config_path.write_text("version: '2'\nentities: {}\n", encoding="utf-8")

    absolute_backup = tmp_path / "import_absolute.yml"
    absolute_backup.write_text(
        "version: '2'\nentities:\n  datasets: {}\n", encoding="utf-8"
    )
    traversed_backup = config_dir / "import_traversed.yml"
    traversed_backup.write_text(
        "version: '2'\nentities:\n  references: {}\n", encoding="utf-8"
    )

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    absolute_response = client.post(
        "/api/config/import/backup/restore",
        json={"backup_filename": str(absolute_backup)},
    )
    traversal_response = client.post(
        "/api/config/import/backup/restore",
        json={"backup_filename": "../import_traversed.yml"},
    )

    assert absolute_response.status_code == 400
    assert traversal_response.status_code == 400
    assert config_path.read_text(encoding="utf-8") == "version: '2'\nentities: {}\n"
    assert list(backup_dir.iterdir()) == []


def test_restore_backup_rejects_invalid_yaml_without_replacing_config(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    backup_dir = config_dir / "backups"
    backup_dir.mkdir(parents=True)
    config_path = config_dir / "import.yml"
    original_content = "version: '2'\nentities: {}\n"
    config_path.write_text(original_content, encoding="utf-8")
    (backup_dir / "import_bad.yml").write_text(
        "version: '2'\nentities: [\n", encoding="utf-8"
    )

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).post(
        "/api/config/import/backup/restore",
        json={"backup_filename": "import_bad.yml"},
    )

    assert response.status_code == 500
    assert config_path.read_text(encoding="utf-8") == original_content


def test_save_import_v2_rejects_missing_entities_without_writing(
    monkeypatch,
    tmp_path,
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    import_path = config_dir / "import.yml"
    import_path.write_text("version: '2'\nentities: {}\n", encoding="utf-8")
    monkeypatch.setattr(config_router, "ensure_config_dir", lambda: config_dir)

    client = TestClient(create_app())
    response = client.put("/api/config/import/v2", json={"config": "foo: bar\n"})

    assert response.status_code == 400
    assert response.json()["detail"]["errors"]["_global"] == [
        "Missing 'entities' section",
    ]
    assert import_path.read_text(encoding="utf-8") == "version: '2'\nentities: {}\n"


def test_validate_import_v2_rejects_duplicate_entity_keys():
    duplicated_config = """
entities:
  datasets:
    occurrences:
      connector:
        type: file
        format: csv
        path: imports/occurrences.csv
      schema: {}
    occurrences:
      connector:
        type: file
        format: csv
        path: imports/other.csv
      schema: {}
  references: {}
""".lstrip()

    response = TestClient(create_app()).post(
        "/api/config/import/v2/validate",
        json={"config": duplicated_config},
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["errors"]["_global"] == [
        "Duplicate YAML key: entities.datasets.occurrences"
    ]


def test_save_import_v2_rejects_duplicate_entity_keys_without_writing(
    monkeypatch,
    tmp_path,
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    import_path = config_dir / "import.yml"
    original_config = "version: '2'\nentities: {}\n"
    import_path.write_text(original_config, encoding="utf-8")
    monkeypatch.setattr(config_router, "ensure_config_dir", lambda: config_dir)

    duplicated_config = """
entities:
  datasets:
    occurrences:
      connector:
        type: file
        format: csv
        path: imports/occurrences.csv
      schema: {}
    occurrences:
      connector:
        type: file
        format: csv
        path: imports/other.csv
      schema: {}
  references: {}
""".lstrip()

    response = TestClient(create_app()).put(
        "/api/config/import/v2",
        json={"config": duplicated_config},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["errors"]["_global"] == [
        "Duplicate YAML key: entities.datasets.occurrences"
    ]
    assert import_path.read_text(encoding="utf-8") == original_config


def test_save_import_v2_writes_valid_config(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setattr(config_router, "ensure_config_dir", lambda: config_dir)
    valid_config = """
version: '2'
entities:
  datasets:
    plots:
      connector:
        type: file
        format: csv
        path: imports/plots.csv
      schema: {}
  references: {}
""".lstrip()

    client = TestClient(create_app())
    response = client.put("/api/config/import/v2", json={"config": valid_config})

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert (config_dir / "import.yml").read_text(encoding="utf-8") == valid_config


def test_save_import_v2_preserves_existing_file_when_atomic_replace_fails(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    import_path = config_dir / "import.yml"
    original_config = "version: '2'\nentities:\n  datasets: {}\n  references: {}\n"
    import_path.write_text(original_config, encoding="utf-8")
    monkeypatch.setattr(config_router, "ensure_config_dir", lambda: config_dir)
    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)
    original_replace = Path.replace

    def fail_replace(temp_path: Path, target_path: Path):
        if target_path.resolve() == import_path.resolve():
            raise OSError("disk full")
        return original_replace(temp_path, target_path)

    monkeypatch.setattr(Path, "replace", fail_replace)
    valid_config = """
version: '2'
entities:
  datasets:
    plots:
      connector:
        type: file
        format: csv
        path: imports/plots.csv
      schema: {}
  references: {}
""".lstrip()

    response = TestClient(create_app()).put(
        "/api/config/import/v2", json={"config": valid_config}
    )

    assert response.status_code == 500
    assert "disk full" in response.json()["detail"]
    assert import_path.read_text(encoding="utf-8") == original_config
    assert not list(config_dir.glob("*.tmp"))


def test_validate_import_config_accepts_entities_schema():
    client = TestClient(create_app())
    import_config = {
        "entities": {
            "references": {
                "taxonomy": {
                    "connector": {
                        "type": "file",
                        "format": "csv",
                        "path": "imports/taxonomy.csv",
                    },
                    "schema": {"id_field": "id", "fields": []},
                },
                "plots": {
                    "connector": {
                        "type": "file",
                        "format": "csv",
                        "path": "imports/plots.csv",
                    },
                    "schema": {"id_field": "id", "fields": []},
                },
            },
            "datasets": {
                "occurrences": {
                    "connector": {
                        "type": "file",
                        "format": "csv",
                        "path": "imports/occurrences.csv",
                    },
                    "schema": {"id_field": "id", "fields": []},
                }
            },
        }
    }

    response = client.post("/api/config/import/validate", json=import_config)

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": [], "warnings": []}


def test_import_v2_schema_matches_accepted_entities_shape():
    client = TestClient(create_app())
    import_config = {
        "entities": {
            "references": {
                "taxonomy": {
                    "connector": {
                        "type": "file",
                        "format": "csv",
                        "path": "imports/taxonomy.csv",
                    },
                    "schema": {"id_field": "id", "fields": []},
                }
            },
            "datasets": {
                "occurrences": {
                    "connector": {
                        "type": "file",
                        "format": "csv",
                        "path": "imports/occurrences.csv",
                    },
                    "schema": {"id_field": "id", "fields": []},
                }
            },
        }
    }

    response = client.get("/api/config/import/v2/schema")

    assert response.status_code == 200
    GenericImportConfig.model_validate(import_config)
    schema = response.json()
    assert schema["required"] == ["entities"]
    assert schema["$defs"]["ReferenceEntityConfig"]["required"] == ["connector"]
    assert schema["$defs"]["EntitySchema"]["properties"]["fields"]["type"] == "array"
    assert (
        schema["$defs"]["ReferenceEntityConfig"]["properties"]["enrichment"]["type"]
        == "array"
    )


def test_validate_import_v2_accepts_entities_only_config():
    client = TestClient(create_app())
    response = client.post(
        "/api/config/import/v2/validate",
        json={
            "config": """
entities:
  datasets:
    occurrences:
      connector:
        type: file
        format: csv
        path: imports/occurrences.csv
      schema:
        id_field: id
        fields: []
""".lstrip()
        },
    )

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": {}, "warnings": {}}


def test_validate_import_v2_rejects_empty_entities_config():
    client = TestClient(create_app())
    response = client.post(
        "/api/config/import/v2/validate",
        json={"config": "entities: {}\n"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "errors": {"_global": ["At least one dataset or reference must be configured"]},
        "warnings": {},
    }


def test_validate_import_v2_rejects_non_snake_case_entity_names():
    client = TestClient(create_app())
    response = client.post(
        "/api/config/import/v2/validate",
        json={
            "config": """
entities:
  datasets:
    Bad Name:
      connector:
        type: file
        format: csv
        path: imports/occurrences.csv
      schema:
        id_field: id
        fields: []
""".lstrip()
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "errors": {
            "dataset.Bad Name": [
                "Entity keys must be snake_case and start with a lowercase letter"
            ]
        },
        "warnings": {},
    }


def test_validate_import_v2_accepts_reference_without_kind():
    client = TestClient(create_app())
    response = client.post(
        "/api/config/import/v2/validate",
        json={
            "config": """
entities:
  references:
    taxons:
      connector:
        type: file
        format: csv
        path: imports/taxons.csv
      schema:
        id_field: id
        fields: []
""".lstrip()
        },
    )

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": {}, "warnings": {}}


def test_validate_import_v2_accepts_categorical_reference_kind():
    client = TestClient(create_app())
    response = client.post(
        "/api/config/import/v2/validate",
        json={
            "config": """
entities:
  references:
    habitats:
      kind: categorical
      connector:
        type: file
        format: csv
        path: imports/habitats.csv
      schema:
        id_field: id
        fields: []
""".lstrip()
        },
    )

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": {}, "warnings": {}}
