from unittest.mock import Mock, patch

import requests
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


def test_test_api_connection_uses_requests_stack():
    client = TestClient(create_app())
    mocked_response = Mock()
    mocked_response.status_code = 200
    mocked_response.json.return_value = {"results": [{"name": "Pinus"}]}

    with patch(
        "niamoto.gui.api.routers.files.requests.get", return_value=mocked_response
    ) as mocked_get:
        response = client.post(
            "/api/files/test-api",
            json={
                "url": "https://list.worldfloraonline.org/matching_rest",
                "headers": {},
                "params": {"input_string": "Pinus"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"results": [{"name": "Pinus"}]},
        "error": None,
    }
    mocked_get.assert_called_once_with(
        "https://list.worldfloraonline.org/matching_rest",
        headers={},
        params={"input_string": "Pinus"},
        timeout=10.0,
    )


def test_test_api_connection_returns_request_error():
    client = TestClient(create_app())

    with patch(
        "niamoto.gui.api.routers.files.requests.get",
        side_effect=requests.exceptions.SSLError("certificate verify failed"),
    ):
        response = client.post(
            "/api/files/test-api",
            json={
                "url": "https://list.worldfloraonline.org/matching_rest",
                "headers": {},
                "params": {"input_string": "Pinus"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "data": None,
        "error": "Connection error: certificate verify failed",
    }
