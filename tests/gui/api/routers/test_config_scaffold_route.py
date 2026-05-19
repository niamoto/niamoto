from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import config as config_router


def test_scaffold_configs_endpoint_returns_service_result(monkeypatch, tmp_path):
    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.config_scaffold.scaffold_configs",
        lambda work_dir: (True, f"scaffolded {work_dir.name}"),
    )

    response = TestClient(create_app()).post("/api/config/scaffold")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "success": True,
        "changed": True,
        "message": f"scaffolded {tmp_path.name}",
    }


def test_scaffold_configs_endpoint_maps_service_errors(monkeypatch, tmp_path):
    def fail_scaffold(work_dir):
        raise RuntimeError("bad import.yml")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        "niamoto.gui.api.services.templates.config_scaffold.scaffold_configs",
        fail_scaffold,
    )

    response = TestClient(create_app()).post("/api/config/scaffold")

    assert response.status_code == 500
    assert response.json()["detail"] == "Scaffold error: bad import.yml"
