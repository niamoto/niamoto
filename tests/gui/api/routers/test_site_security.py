"""Security regression tests for site file path containment."""

from __future__ import annotations

from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


def test_file_content_rejects_sibling_prefix_escape(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    sibling_dir = tmp_path / "project-backup"
    work_dir.mkdir()
    sibling_dir.mkdir()
    (sibling_dir / "secret.md").write_text("secret", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.site.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get(
        "/api/site/file-content",
        params={"path": "../project-backup/secret.md"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: path outside project"


def test_file_content_allows_site_content_roots(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    content_dir = work_dir / "templates" / "content"
    files_dir = work_dir / "files"
    content_dir.mkdir(parents=True)
    files_dir.mkdir()
    (content_dir / "about.md").write_text("# About", encoding="utf-8")
    (files_dir / "page.md").write_text("# Page", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.site.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    template_response = client.get(
        "/api/site/file-content",
        params={"path": "templates/content/about.md"},
    )
    files_response = client.get(
        "/api/site/file-content",
        params={"path": "files/page.md"},
    )

    assert template_response.status_code == 200
    assert template_response.json()["content"] == "# About"
    assert files_response.status_code == 200
    assert files_response.json()["content"] == "# Page"


def test_file_content_rejects_project_config_files(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "export.yml").write_text("secret: value", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.site.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get(
        "/api/site/file-content",
        params={"path": "config/export.yml"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "File path is not allowed for site content editing"
    )


def test_data_content_update_rejects_sibling_prefix_escape(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    sibling_dir = tmp_path / "project-backup"
    work_dir.mkdir()
    sibling_dir.mkdir()

    monkeypatch.setattr(
        "niamoto.gui.api.routers.site.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.put(
        "/api/site/data-content",
        json={"path": "../project-backup/data.json", "data": [{"id": 1}]},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: path outside project"
    assert not (sibling_dir / "data.json").exists()


def test_files_endpoint_rejects_sibling_prefix_escape(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    files_dir = work_dir / "files"
    sibling_dir = work_dir / "files-backup"
    files_dir.mkdir(parents=True)
    sibling_dir.mkdir()
    (sibling_dir / "secret.md").write_text("secret", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.site.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get("/api/site/files/%2E%2E/files-backup/secret.md")

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: path outside files folder"


def test_files_listing_rejects_parent_folder_escape(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    sibling_dir = tmp_path / "project-backup"
    work_dir.mkdir()
    sibling_dir.mkdir()
    (sibling_dir / "secret.md").write_text("secret", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.site.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get("/api/site/files", params={"folder": ".."})

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: path outside project"


def test_assets_endpoint_rejects_sibling_prefix_escape(monkeypatch, tmp_path):
    assets_dir = tmp_path / "assets"
    sibling_dir = tmp_path / "assets-backup"
    assets_dir.mkdir()
    sibling_dir.mkdir()
    (sibling_dir / "secret.css").write_text("body {}", encoding="utf-8")

    monkeypatch.setattr(
        "importlib.resources.files",
        lambda package: tmp_path if package == "niamoto.publish" else tmp_path,
    )

    client = TestClient(create_app())
    response = client.get("/api/site/assets/%2E%2E/assets-backup/secret.css")

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: path outside assets folder"
