"""Regression tests for dataset configuration routes."""

import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import config as config_router


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
