import asyncio
import os
import zipfile
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests
import geopandas as gpd
from fastapi.testclient import TestClient
from shapely.geometry import Point

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import files as files_router


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w") as zip_file:
        for name, content in members.items():
            zip_file.writestr(name, content)
    return archive.getvalue()


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


def test_analyze_file_preserves_spatial_analyzer_suggestions():
    client = TestClient(create_app())
    analyzer = AsyncMock(
        return_value={
            "filename": "plots.zip",
            "type": "shapefile",
            "suggestions": {"name": ["plot_name"]},
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
        "entity_type": "shapes",
        "suggestions": {"name": ["plot_name"]},
    }
    analyzer.assert_awaited_once()


def test_analyze_file_rejects_oversized_upload(monkeypatch):
    client = TestClient(create_app())
    monkeypatch.setattr(files_router, "MAX_ANALYZE_UPLOAD_SIZE_BYTES", 5)
    monkeypatch.setattr(files_router, "ANALYZE_UPLOAD_CHUNK_SIZE_BYTES", 4)

    with patch("niamoto.gui.api.routers.files.analyze_csv") as analyzer:
        response = client.post(
            "/api/files/analyze",
            files={"file": ("data.csv", b"123456", "text/csv")},
            data={"entity_type": "taxon"},
        )

    assert response.status_code == 413
    assert response.json()["detail"] == (
        "Uploaded file exceeds the maximum allowed analysis size of 5 bytes"
    )
    analyzer.assert_not_called()


def test_analyze_shape_rejects_zip_exceeding_uncompressed_limit(monkeypatch):
    monkeypatch.setattr(files_router, "MAX_ANALYZE_ZIP_UNCOMPRESSED_BYTES", 5)
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("plots.shp", b"123456")

    result = asyncio.run(files_router.analyze_shape(archive.getvalue(), "plots.zip"))

    assert result["error"] == (
        "Failed to analyze shape file: Archive exceeds maximum uncompressed "
        "analysis size of 5 bytes"
    )


def test_analyze_shape_zip_validates_components_before_reading(monkeypatch):
    content = _zip_bytes(
        {
            "plots/plots.shp": b"shp",
            "plots/plots.shx": b"shx",
            "plots/plots.dbf": b"dbf",
        }
    )
    gdf = gpd.GeoDataFrame(
        {"name": ["Plot A"], "geometry": [Point(0, 0)]},
        crs="EPSG:4326",
    )
    read_file = Mock(return_value=gdf)
    monkeypatch.setattr(files_router.gpd, "read_file", read_file)

    result = asyncio.run(files_router.analyze_shape(content, "plots.zip"))

    assert result["type"] == "shape"
    assert result["feature_count"] == 1
    assert result["columns"] == ["name"]
    assert result["suggestions"] == {"name": ["name"]}
    read_path = read_file.call_args.args[0]
    assert read_path.name == "plots.shp"
    assert read_path.parent.name == "plots"


def test_analyze_shape_zip_rejects_traversal_members(monkeypatch, tmp_path):
    extract_root = tmp_path / "extract"

    class FixedTemporaryDirectory:
        def __enter__(self):
            extract_root.mkdir()
            return str(extract_root)

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        files_router.tempfile,
        "TemporaryDirectory",
        FixedTemporaryDirectory,
    )
    content = _zip_bytes({"../escape.shp": b"shp"})

    result = asyncio.run(files_router.analyze_shape(content, "plots.zip"))

    assert result["error"] == (
        "Failed to analyze shape file: Invalid ZIP member path: ../escape.shp"
    )
    assert not (tmp_path / "escape.shp").exists()


def test_analyze_shape_zip_reports_missing_required_components(monkeypatch):
    content = _zip_bytes({"plots.shp": b"shp", "plots.dbf": b"dbf"})
    read_file = Mock()
    monkeypatch.setattr(files_router.gpd, "read_file", read_file)

    result = asyncio.run(files_router.analyze_shape(content, "plots.zip"))

    assert result["error"].startswith("Missing required shapefile components: .shx")
    read_file.assert_not_called()


def test_analyze_csv_samples_rows_without_materializing_all_rows(monkeypatch):
    monkeypatch.setattr(files_router, "CSV_ANALYSIS_SAMPLE_ROWS", 3)
    content = b"value\n1\n2\n3\n4\n5\n"

    result = asyncio.run(files_router.analyze_csv(content, "data.csv"))

    assert result["row_count"] == 5
    assert result["sample_data"] == [{"value": "1"}, {"value": "2"}, {"value": "3"}]
    assert result["column_types"] == {"value": "integer"}


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


def test_analyze_file_rejects_direct_spatial_filename_traversal(monkeypatch):
    client = TestClient(create_app())
    analyzer = Mock()
    monkeypatch.setattr(files_router, "analyze_shape", analyzer)

    response = client.post(
        "/api/files/analyze",
        files={"file": ("../escape.geojson", b'{"type":"FeatureCollection"}')},
        data={"entity_type": "shapes"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid filename"}
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
        stream=True,
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
        stream=True,
    )


def test_test_api_connection_rejects_rebound_peer_address():
    client = TestClient(create_app())
    mocked_response = Mock()
    mocked_response.status_code = 200
    mocked_response.json.return_value = {"ok": True}
    mocked_socket = Mock()
    mocked_socket.getpeername.return_value = ("127.0.0.1", 443)
    mocked_response.raw._connection.sock = mocked_socket

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
    mocked_get.assert_called_once()
    mocked_response.close.assert_called_once()


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


def test_read_export_file_rejects_symlinked_exports_root(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    work_dir.mkdir()
    external_exports = tmp_path / "external_exports"
    external_exports.mkdir()
    (external_exports / "secret.txt").write_text("secret", encoding="utf-8")
    try:
        os.symlink(external_exports, work_dir / "exports")
    except OSError as exc:
        pytest.skip(f"symlink creation is not available: {exc}")

    monkeypatch.setattr(files_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get("/api/files/exports/read", params={"file_path": "secret.txt"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Symlinks are not allowed"


def test_exports_structure_skips_symlinks(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    exports_dir = work_dir / "exports"
    exports_dir.mkdir(parents=True)
    (exports_dir / "public.json").write_text("{}", encoding="utf-8")
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    (secret_dir / "hidden.json").write_text("{}", encoding="utf-8")
    try:
        os.symlink(secret_dir, exports_dir / "linked-secret")
    except OSError as exc:
        pytest.skip(f"symlink creation is not available: {exc}")

    monkeypatch.setattr(files_router, "get_working_directory", lambda: work_dir)

    client = TestClient(create_app())
    response = client.get("/api/files/exports/structure")

    assert response.status_code == 200, response.text
    names = {item["name"] for item in response.json()["tree"]}
    assert "public.json" in names
    assert "linked-secret" not in names


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
