from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


@pytest.mark.parametrize(
    ("filename", "analyzer_name", "expected_type"),
    [
        ("DATA.CSV", "analyze_csv", "csv"),
        ("Workbook.XLSX", "analyze_excel", "excel"),
    ],
)
def test_analyze_file_accepts_uppercase_supported_extensions(
    filename: str, analyzer_name: str, expected_type: str
):
    client = TestClient(create_app())
    analyzer = AsyncMock(
        return_value={
            "filename": filename,
            "type": expected_type,
        }
    )

    with patch(f"niamoto.gui.api.routers.files.{analyzer_name}", analyzer):
        response = client.post(
            "/api/files/analyze",
            files={"file": (filename, b"col\nvalue\n")},
            data={"entity_type": "taxon"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "filename": filename,
        "type": expected_type,
        "entity_type": "taxon",
        "suggestions": {},
    }
    analyzer.assert_awaited_once()


def test_test_api_connection_uses_requests_stack():
    client = TestClient(create_app())
    mocked_response = Mock()
    mocked_response.status_code = 200
    mocked_response.json.return_value = {"results": [{"name": "Pinus"}]}

    with (
        patch("niamoto.gui.api.routers.files.socket.getaddrinfo") as mocked_dns,
        patch(
            "niamoto.gui.api.routers.files.requests.get", return_value=mocked_response
        ) as mocked_get,
    ):
        mocked_dns.return_value = [
            (None, None, None, None, ("8.8.8.8", 443)),
        ]
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
        allow_redirects=False,
    )


def test_test_api_connection_returns_request_error():
    client = TestClient(create_app())

    with (
        patch("niamoto.gui.api.routers.files.socket.getaddrinfo") as mocked_dns,
        patch(
            "niamoto.gui.api.routers.files.requests.get",
            side_effect=requests.exceptions.SSLError("certificate verify failed"),
        ),
    ):
        mocked_dns.return_value = [
            (None, None, None, None, ("8.8.8.8", 443)),
        ]
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


def test_test_api_connection_rejects_internal_targets_without_request():
    client = TestClient(create_app())

    with patch("niamoto.gui.api.routers.files.requests.get") as mocked_get:
        for url in [
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://169.254.169.254/latest/meta-data/",
            "http://192.168.1.10/api",
        ]:
            response = client.post(
                "/api/files/test-api",
                json={"url": url, "headers": {}, "params": {}},
            )

            assert response.status_code == 200
            assert response.json() == {
                "success": False,
                "data": None,
                "error": "API URL host is not allowed",
            }

    mocked_get.assert_not_called()


def test_test_api_connection_rejects_redirects_to_internal_targets():
    client = TestClient(create_app())
    mocked_response = Mock()
    mocked_response.status_code = 302
    mocked_response.headers = {"Location": "http://127.0.0.1:8000/private"}
    mocked_response.text = ""

    with (
        patch("niamoto.gui.api.routers.files.socket.getaddrinfo") as mocked_dns,
        patch(
            "niamoto.gui.api.routers.files.requests.get", return_value=mocked_response
        ) as mocked_get,
    ):
        mocked_dns.return_value = [
            (None, None, None, None, ("8.8.8.8", 443)),
        ]
        response = client.post(
            "/api/files/test-api",
            json={
                "url": "https://list.worldfloraonline.org/matching_rest",
                "headers": {},
                "params": {},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "data": None,
        "error": "API URL host is not allowed",
    }
    mocked_get.assert_called_once_with(
        "https://list.worldfloraonline.org/matching_rest",
        headers={},
        params={},
        timeout=10.0,
        allow_redirects=False,
    )
