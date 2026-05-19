from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import config as config_router


def test_validate_rejects_unknown_config_name():
    client = TestClient(create_app())

    response = client.post("/api/config/unknown/validate", json={})

    assert response.status_code == 400
    assert "Invalid configuration name" in response.json()["detail"]


def test_get_missing_transform_config_returns_canonical_empty_list(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    (work_dir / "config").mkdir(parents=True)
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get("/api/config/transform")

    assert response.status_code == 200, response.text
    assert response.json() == []


def test_validate_transform_accepts_canonical_list_payload():
    client = TestClient(create_app())
    transform_config = [
        {
            "group_by": "taxons",
            "sources": [],
            "widgets_data": {},
        }
    ]

    response = client.post("/api/config/transform/validate", json=transform_config)

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": [], "warnings": []}


def test_validate_transform_rejects_invalid_canonical_list_payload():
    client = TestClient(create_app())

    response = client.post("/api/config/transform/validate", json=[{"sources": []}])

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["errors"]
