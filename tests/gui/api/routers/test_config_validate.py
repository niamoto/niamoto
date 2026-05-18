from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


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
