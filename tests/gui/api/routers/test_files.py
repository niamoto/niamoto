import os
from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import files as files_router


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


def test_analyze_file_routes_shapes_zip_to_spatial_analyzer():
    client = TestClient(create_app())
    analyzer = AsyncMock(
        return_value={
            "filename": "plots.zip",
            "type": "shapefile",
            "feature_count": 2,
        }
    )

    with patch("niamoto.gui.api.routers.files.analyze_shape", analyzer):
        response = client.post(
            "/api/files/analyze",
            files={"file": ("plots.zip", b"fake zip content")},
            data={"entity_type": "shapes"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "plots.zip",
        "type": "shapefile",
        "feature_count": 2,
        "entity_type": "shapes",
        "suggestions": {},
    }
    analyzer.assert_awaited_once()


def test_analyze_file_reports_component_message_for_shapes_shp_upload():
    client = TestClient(create_app())

    with patch("niamoto.gui.api.routers.files.analyze_shape") as analyzer:
        response = client.post(
            "/api/files/analyze",
            files={"file": ("plots.shp", b"fake shp content")},
            data={"entity_type": "shapes"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "error": "Shapefile analysis requires all component files (.shp, .shx, .dbf). Please upload a ZIP file containing all shapefile components."
    }
    analyzer.assert_not_called()


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


def test_read_export_file_rejects_symlink_outside_exports(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    exports_dir = work_dir / "exports"
    exports_dir.mkdir(parents=True)
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("secret", encoding="utf-8")
    link_path = exports_dir / "linked-secret.txt"
    try:
        os.symlink(secret_path, link_path)
    except OSError as exc:
        pytest.skip(f"symlink creation is not available: {exc}")

    monkeypatch.setattr(files_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get(
        "/api/files/exports/read", params={"file_path": "linked-secret.txt"}
    )

    assert response.status_code in {400, 403}
    assert response.json()["detail"] in {
        "Access denied: file outside exports directory",
        "Symlinks are not allowed",
    }


def test_browse_missing_path_returns_not_found(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    work_dir.mkdir()
    monkeypatch.setattr(files_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get("/api/files/browse", params={"path": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Path not found"


def test_read_export_file_rejects_intermediate_symlink(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    exports_dir = work_dir / "exports"
    exports_dir.mkdir(parents=True)
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    (external_dir / "secret.txt").write_text("secret", encoding="utf-8")
    link_path = exports_dir / "linked-dir"
    try:
        os.symlink(external_dir, link_path)
    except OSError as exc:
        pytest.skip(f"symlink creation is not available: {exc}")

    monkeypatch.setattr(files_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get(
        "/api/files/exports/read", params={"file_path": "linked-dir/secret.txt"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] in {
        "Path is not a file",
        "Symlinks are not allowed",
    }


def test_read_export_file_reads_regular_export(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    exports_dir = work_dir / "exports" / "api"
    exports_dir.mkdir(parents=True)
    export_path = exports_dir / "taxon.json"
    export_path.write_text('{"name": "Myrtaceae"}', encoding="utf-8")

    monkeypatch.setattr(files_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get(
        "/api/files/exports/read", params={"file_path": "api/taxon.json"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "path": "api/taxon.json",
        "content": '{"name": "Myrtaceae"}',
        "parsed": {"name": "Myrtaceae"},
        "size": export_path.stat().st_size,
    }
