"""Contract tests for geographic layers router."""

from __future__ import annotations

from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers.layers import RasterMetadata, VectorMetadata


def test_list_layers_returns_sorted_relative_paths_without_metadata(
    monkeypatch, tmp_path
):
    imports_dir = tmp_path / "imports"
    (imports_dir / "nested").mkdir(parents=True)
    (imports_dir / "b.tif").write_bytes(b"raster")
    (imports_dir / "a.gpkg").write_bytes(b"vector")
    (imports_dir / "nested" / "z.geojson").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.layers.get_working_directory",
        lambda: tmp_path,
    )

    client = TestClient(create_app())
    response = client.get("/api/layers", params={"include_metadata": "false"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_path"] == str(imports_dir)
    assert [item["name"] for item in payload["raster"]] == ["b.tif"]
    assert [item["path"] for item in payload["raster"]] == ["imports/b.tif"]
    assert [item["name"] for item in payload["vector"]] == ["a.gpkg", "z.geojson"]
    assert [item["path"] for item in payload["vector"]] == [
        "imports/a.gpkg",
        "imports/nested/z.geojson",
    ]


def test_list_layers_returns_500_when_working_directory_is_missing(monkeypatch):
    monkeypatch.setattr(
        "niamoto.gui.api.routers.layers.get_working_directory",
        lambda: None,
    )

    client = TestClient(create_app())
    response = client.get("/api/layers")

    assert response.status_code == 500
    assert response.json()["detail"] == "Working directory not configured"


def test_get_layer_info_returns_raster_metadata_and_null_preview(monkeypatch, tmp_path):
    raster_file = tmp_path / "imports" / "elevation.tif"
    raster_file.parent.mkdir(parents=True)
    raster_file.write_bytes(b"raster")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.layers.get_working_directory",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.layers.get_raster_metadata",
        lambda file_path: RasterMetadata(
            path=str(file_path),
            name=file_path.name,
            size_bytes=file_path.stat().st_size,
            width=256,
            height=128,
            bands=1,
        ),
    )

    client = TestClient(create_app())
    response = client.get("/api/layers/imports/elevation.tif")

    assert response.status_code == 200
    assert response.json() == {
        "type": "raster",
        "metadata": {
            "type": "raster",
            "path": str(raster_file),
            "name": "elevation.tif",
            "size_bytes": 6,
            "crs": None,
            "extent": None,
            "width": 256,
            "height": 128,
            "bands": 1,
            "dtype": None,
            "nodata": None,
        },
        "preview": None,
    }


def test_get_layer_info_returns_vector_metadata_with_safe_sample_fallback(
    monkeypatch, tmp_path
):
    vector_file = tmp_path / "imports" / "plots.gpkg"
    vector_file.parent.mkdir(parents=True)
    vector_file.write_bytes(b"vector")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.layers.get_working_directory",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "niamoto.gui.api.routers.layers.get_vector_metadata",
        lambda file_path: VectorMetadata(
            path=str(file_path),
            name=file_path.name,
            size_bytes=file_path.stat().st_size,
            feature_count=12,
            columns=["plot_id", "name"],
        ),
    )

    client = TestClient(create_app())
    response = client.get("/api/layers/imports/plots.gpkg")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "vector"
    assert payload["metadata"]["feature_count"] == 12
    assert payload["metadata"]["columns"] == ["plot_id", "name"]
    assert payload["sample_data"] is None


def test_get_layer_info_rejects_unsupported_file_types(monkeypatch, tmp_path):
    text_file = tmp_path / "imports" / "notes.txt"
    text_file.parent.mkdir(parents=True)
    text_file.write_text("not a layer", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.layers.get_working_directory",
        lambda: tmp_path,
    )

    client = TestClient(create_app())
    response = client.get("/api/layers/imports/notes.txt")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type: .txt"
