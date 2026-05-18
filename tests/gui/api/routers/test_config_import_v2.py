"""Tests for EntityRegistry v2 import configuration routes."""

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
