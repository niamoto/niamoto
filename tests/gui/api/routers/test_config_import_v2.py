"""Tests for EntityRegistry v2 import configuration routes."""

from datetime import datetime

from fastapi.testclient import TestClient

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
        "Missing 'version' field",
        "Missing 'entities' section",
    ]
    assert import_path.read_text(encoding="utf-8") == "version: '2'\nentities: {}\n"


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
