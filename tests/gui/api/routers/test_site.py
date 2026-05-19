"""Integration tests for site router endpoints."""

from pathlib import Path
from unittest.mock import patch
from datetime import datetime
import shutil
import tempfile

import pytest
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers.site import (
    _candidate_exported_preview_path,
    _fallback_legacy_home_page,
    _fallback_without_language_prefix,
    _get_preview_api_base_url,
    _generate_mock_items,
    _normalize_footer_sections,
    _normalize_link_url,
    _normalize_navigation_items,
    _normalize_output_alias,
    _normalize_static_pages,
    _preprocess_markdown_images,
    _resolve_footer_sections,
    _resolve_localized,
    _resolve_navigation,
    _validate_static_pages,
)
from niamoto.gui.api.routers import site as site_router


def _write_config(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def test_export_bibtex_handles_blank_and_null_fields():
    client = TestClient(create_app())
    response = client.post(
        "/api/site/export-bibtex",
        json=[
            {
                "type": "article",
                "authors": "",
                "title": "A",
                "year": "2024",
                "journal": None,
                "pages": None,
            },
            {
                "type": "article",
                "authors": None,
                "title": None,
                "year": None,
            },
        ],
    )

    assert response.status_code == 200, response.text
    assert "@article{unknown2024a," in response.text
    assert "@article{unknown0000untitled," in response.text


def test_import_bibtex_rejects_oversized_upload(monkeypatch):
    client = TestClient(create_app())
    monkeypatch.setattr(site_router, "MAX_BIBTEX_UPLOAD_SIZE_BYTES", 10)
    monkeypatch.setattr(site_router, "BIBTEX_UPLOAD_CHUNK_SIZE_BYTES", 4)

    response = client.post(
        "/api/site/import-bibtex",
        files={"file": ("references.bib", b"@" * 11, "application/x-bibtex")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == (
        "BibTeX file exceeds the maximum allowed size of 10 bytes"
    )


def test_site_create_backup_preserves_rapid_successive_backups(monkeypatch, tmp_path):
    export_path = tmp_path / "export.yml"
    export_path.write_text("first\n", encoding="utf-8")

    class FixedDatetime:
        @classmethod
        def now(cls):
            return datetime(2026, 5, 18, 17, 15, 0, 123456)

    monkeypatch.setattr(site_router, "datetime", FixedDatetime)

    first_backup = site_router._create_backup(export_path)
    export_path.write_text("second\n", encoding="utf-8")
    second_backup = site_router._create_backup(export_path)

    assert first_backup is not None
    assert second_backup is not None
    assert first_backup != second_backup
    assert first_backup.read_text(encoding="utf-8") == "first\n"
    assert second_backup.read_text(encoding="utf-8") == "second\n"


def test_import_csv_rejects_duplicate_normalized_headers():
    client = TestClient(create_app())

    response = client.post(
        "/api/site/import-csv",
        files={"file": ("data.csv", b"Name,name\nfirst,second\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Duplicate CSV headers after normalization: name"
    )


def test_import_csv_rejects_oversized_upload(monkeypatch):
    client = TestClient(create_app())
    monkeypatch.setattr(site_router, "MAX_CSV_IMPORT_UPLOAD_SIZE_BYTES", 10)
    monkeypatch.setattr(site_router, "CSV_IMPORT_UPLOAD_CHUNK_SIZE_BYTES", 4)

    response = client.post(
        "/api/site/import-csv",
        files={"file": ("data.csv", b"a" * 11, "text/csv")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == (
        "CSV file exceeds the maximum allowed size of 10 bytes"
    )


def test_site_helper_normalization_rewrites_home_aliases_recursively():
    static_pages, output_aliases = _normalize_static_pages(
        [
            {
                "name": "Home",
                "template": "index.html",
                "output_file": " Home.html ",
            },
            {
                "name": "About",
                "template": "page.html",
                "output_file": "/about.html",
            },
        ]
    )

    assert _normalize_output_alias(" /docs/page.html ") == "docs/page.html"
    assert static_pages[0]["output_file"] == "index.html"
    assert static_pages[1]["output_file"] == "about.html"
    assert output_aliases == {"Home.html": "index.html"}
    assert _normalize_link_url("/Home.html", output_aliases) == "/index.html"
    assert _normalize_navigation_items(
        [
            {
                "text": "Home",
                "url": "/Home.html",
                "children": [{"text": "About", "url": "Home.html"}],
            }
        ],
        output_aliases,
    ) == [
        {
            "text": "Home",
            "url": "/index.html",
            "children": [{"text": "About", "url": "index.html"}],
        }
    ]
    assert _normalize_footer_sections(
        [{"title": "Footer", "links": [{"text": "Home", "url": "/Home.html"}]}],
        output_aliases,
    ) == [{"title": "Footer", "links": [{"text": "Home", "url": "/index.html"}]}]


def test_site_helper_validation_rejects_duplicate_root_and_output_files():
    with pytest.raises(Exception) as duplicate_root:
        _validate_static_pages(
            [
                {"template": "index.html", "output_file": "index.html"},
                {"template": "index.html", "output_file": "home.html"},
            ]
        )

    assert duplicate_root.value.status_code == 422
    assert "Only one page can use the index.html template" in str(
        duplicate_root.value.detail
    )

    with pytest.raises(Exception) as duplicate_output:
        _validate_static_pages(
            [
                {"template": "page.html", "output_file": "about.html"},
                {"template": "other.html", "output_file": "/about.html"},
            ]
        )

    assert duplicate_output.value.status_code == 422
    assert "Duplicate output_file values are not allowed" in str(
        duplicate_output.value.detail
    )


def test_site_helper_preview_path_fallbacks_cover_language_and_legacy_routes():
    with tempfile.TemporaryDirectory() as temp_dir:
        exports_web_dir = Path(temp_dir)
        (exports_web_dir / "index.html").write_text("root", encoding="utf-8")
        (exports_web_dir / "fr").mkdir()
        (exports_web_dir / "fr" / "Home.html").write_text("legacy", encoding="utf-8")

        assert _candidate_exported_preview_path(exports_web_dir, "") == (
            exports_web_dir / "index.html"
        )
        assert _candidate_exported_preview_path(exports_web_dir, "guides/") == (
            exports_web_dir / "guides" / "index.html"
        )
        assert _fallback_without_language_prefix(
            exports_web_dir,
            "en/index.html",
        ) == (exports_web_dir / "index.html")

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "niamoto.gui.api.routers.site._get_legacy_home_output_file",
                lambda: "Home.html",
            )
            assert _fallback_legacy_home_page(exports_web_dir, "") == (
                exports_web_dir / "Home.html"
            )
            assert _fallback_legacy_home_page(exports_web_dir, "fr/index.html") == (
                exports_web_dir / "fr" / "Home.html"
            )


def test_site_helper_localization_and_markdown_preprocessing_cover_nested_cases():
    assert _resolve_localized({"fr": "Bonjour", "en": "Hello"}, lang="en") == "Hello"
    assert _resolve_localized({"name": "logo", "fr": "Bonjour"}, lang="en") == {
        "name": "logo",
        "fr": "Bonjour",
    }

    assert _resolve_navigation(
        [
            {
                "text": {"fr": "Accueil", "en": "Home"},
                "children": [{"text": {"fr": "À propos", "en": "About"}}],
            }
        ],
        lang="en",
    ) == [{"text": "Home", "children": [{"text": "About"}]}]
    assert _resolve_footer_sections(
        [
            {
                "title": {"fr": "Liens", "en": "Links"},
                "links": [{"text": {"fr": "Contact", "en": "Contact"}}],
            }
        ],
        lang="en",
    ) == [{"title": "Links", "links": [{"text": "Contact"}]}]

    html = _preprocess_markdown_images(
        "![Carte|320|center](files/maps/site.png)\n![Photo|right](https://img.example/pic.jpg)"
    )
    assert "/api/site/files/maps/site.png" in html
    assert "max-width:320px" in html
    assert "justify-content:center" in html
    assert "justify-content:flex-end" in html


def test_site_helper_preview_api_base_url_uses_request_base_url_when_available():
    class DummyRequest:
        base_url = "https://niamoto.test/gui/"

    assert _get_preview_api_base_url(None) == "/api/site"
    assert (
        _get_preview_api_base_url(DummyRequest()) == "https://niamoto.test/gui/api/site"
    )


def test_preview_markdown_sanitizes_user_controlled_html():
    client = TestClient(create_app())

    response = client.post(
        "/api/site/preview-markdown",
        json={
            "content": (
                "# Title\n"
                "<script>alert(1)</script>\n"
                "<img src=x onerror=alert(document.domain)>\n"
                "[bad](javascript:alert(1))\n"
                '![bad" onerror="alert(1)](javascript:alert(1))'
            )
        },
    )

    assert response.status_code == 200
    html = response.json()["html"]
    assert "<h1" in html
    assert "<script" not in html
    assert "onerror" not in html
    assert "javascript:" not in html
    assert "alert(1)" in html


class TestSiteGroups:
    """Regression tests for group listing in the Site Builder."""

    def test_groups_endpoint_falls_back_to_default_output_patterns(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config_dir = Path(temp_dir) / "config"

            _write_config(
                config_dir / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {},
                            "groups": [
                                {
                                    "group_by": "plots",
                                    "widgets": [{"plugin": "bar_plot"}],
                                    "index_generator": {
                                        "enabled": True,
                                        "template": "_group_index.html",
                                        "page_config": {"title": "Plots"},
                                        "filters": [],
                                        "display_fields": [],
                                        "views": [{"type": "grid", "default": True}],
                                    },
                                }
                            ],
                        }
                    ]
                },
            )

            with patch("niamoto.gui.api.routers.site.get_working_directory") as mock_wd:
                mock_wd.return_value = Path(temp_dir)
                app = create_app()
                client = TestClient(app)

                response = client.get("/api/site/groups")
                assert response.status_code == 200, response.text

            data = response.json()
            assert data["groups"][0]["name"] == "plots"
            assert data["groups"][0]["output_pattern"] == "plots/{id}.html"
            assert data["groups"][0]["index_output_pattern"] == "plots/index.html"
            assert data["groups"][0]["widgets_count"] == 1
        finally:
            shutil.rmtree(temp_dir)

    def test_preview_exported_site_follows_current_working_directory(self):
        with (
            tempfile.TemporaryDirectory() as temp1,
            tempfile.TemporaryDirectory() as temp2,
        ):
            project_1 = Path(temp1)
            project_2 = Path(temp2)

            exports_1 = project_1 / "exports" / "web"
            exports_2 = project_2 / "exports" / "web"
            exports_1.mkdir(parents=True, exist_ok=True)
            exports_2.mkdir(parents=True, exist_ok=True)
            (exports_1 / "index.html").write_text("instance-one", encoding="utf-8")
            (exports_2 / "index.html").write_text("instance-two", encoding="utf-8")

            current_project = {"path": project_1}

            def _current_work_dir() -> Path:
                return current_project["path"]

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                side_effect=_current_work_dir,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.get("/api/site/preview-exported/index.html")
                assert response.status_code == 200, response.text
                assert "instance-one" in response.text

                current_project["path"] = project_2

                response = client.get("/api/site/preview-exported/index.html")
                assert response.status_code == 200, response.text
                assert "instance-two" in response.text

    def test_preview_exported_site_falls_back_when_language_prefix_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            exports = project / "exports" / "web"
            exports.mkdir(parents=True, exist_ok=True)
            (exports / "index.html").write_text(
                "single-language-site", encoding="utf-8"
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.get("/api/site/preview-exported/en/index.html")
                assert response.status_code == 200, response.text
                assert "single-language-site" in response.text

    def test_get_site_config_normalizes_legacy_home_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(
                config_dir / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {
                                "navigation": [{"text": "Home", "url": "/Home.html"}],
                                "footer_navigation": [
                                    {
                                        "title": "Footer",
                                        "links": [
                                            {
                                                "text": "Home",
                                                "url": "/Home.html",
                                            }
                                        ],
                                    }
                                ],
                            },
                            "static_pages": [
                                {
                                    "name": "Home",
                                    "template": "index.html",
                                    "output_file": "Home.html",
                                }
                            ],
                            "groups": [],
                        }
                    ]
                },
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.get("/api/site/config")
                assert response.status_code == 200, response.text

            data = response.json()
            assert data["static_pages"][0]["output_file"] == "index.html"
            assert data["navigation"][0]["url"] == "/index.html"
            assert data["footer_navigation"][0]["links"][0]["url"] == "/index.html"

    def test_get_site_config_keeps_empty_static_pages_when_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(
                config_dir / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {"navigation": []},
                            "static_pages": [],
                            "groups": [],
                        }
                    ]
                },
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.get("/api/site/config")
                assert response.status_code == 200, response.text

            data = response.json()
            assert data["static_pages"] == []

    def test_update_site_config_normalizes_home_output_and_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(config_dir / "export.yml", {"exports": []})

            payload = {
                "site": {"title": "Niamoto", "lang": "fr"},
                "navigation": [{"text": "Home", "url": "/Home.html"}],
                "footer_navigation": [
                    {
                        "title": "Footer",
                        "links": [{"text": "Home", "url": "/Home.html"}],
                    }
                ],
                "static_pages": [
                    {
                        "name": "Home",
                        "template": "index.html",
                        "output_file": "Home.html",
                    }
                ],
            }

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.put("/api/site/config", json=payload)
                assert response.status_code == 200, response.text

            saved_config = yaml.safe_load((config_dir / "export.yml").read_text())
            web_pages = saved_config["exports"][0]
            assert web_pages["params"]["template_dir"] == "templates/"
            assert web_pages["params"]["output_dir"] == "exports/web"
            assert web_pages["static_pages"][0]["output_file"] == "index.html"
            assert web_pages["params"]["navigation"][0]["url"] == "/index.html"
            assert (
                web_pages["params"]["footer_navigation"][0]["links"][0]["url"]
                == "/index.html"
            )

    def test_update_site_config_repairs_missing_export_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(
                config_dir / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {"site": {"title": "Niamoto", "lang": "fr"}},
                            "static_pages": [],
                            "groups": [],
                        }
                    ]
                },
            )

            payload = {
                "site": {"title": "Niamoto", "lang": "fr"},
                "navigation": [],
                "footer_navigation": [],
                "static_pages": [],
            }

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.put("/api/site/config", json=payload)
                assert response.status_code == 200, response.text

            saved_config = yaml.safe_load((config_dir / "export.yml").read_text())
            web_pages = saved_config["exports"][0]
            assert web_pages["params"]["template_dir"] == "templates/"
            assert web_pages["params"]["output_dir"] == "exports/web"

    def test_update_site_config_persists_empty_static_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(config_dir / "export.yml", {"exports": []})

            payload = {
                "site": {"title": "Niamoto", "lang": "fr"},
                "navigation": [],
                "footer_navigation": [],
                "static_pages": [],
            }

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.put("/api/site/config", json=payload)
                assert response.status_code == 200, response.text

            saved_config = yaml.safe_load((config_dir / "export.yml").read_text())
            web_pages = saved_config["exports"][0]
            assert web_pages["static_pages"] == []

    def test_update_site_config_preserves_static_page_extra_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(config_dir / "export.yml", {"exports": []})

            payload = {
                "site": {"title": "Niamoto", "lang": "fr"},
                "navigation": [],
                "footer_navigation": [],
                "static_pages": [
                    {
                        "name": "Legal",
                        "template": "page.html",
                        "output_file": "Legal.html",
                        "layout": "narrow",
                        "context": {
                            "title": "Legal",
                            "content_source": "content/legal.md",
                        },
                    }
                ],
            }

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.put("/api/site/config", json=payload)
                assert response.status_code == 200, response.text

            saved_config = yaml.safe_load((config_dir / "export.yml").read_text())
            page = saved_config["exports"][0]["static_pages"][0]
            assert page["layout"] == "narrow"
            assert page["output_file"] == "Legal.html"
            assert page["context"] == {
                "title": "Legal",
                "content_source": "content/legal.md",
            }

    def test_update_site_config_rejects_multiple_home_templates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(config_dir / "export.yml", {"exports": []})

            payload = {
                "site": {"title": "Niamoto", "lang": "fr"},
                "navigation": [],
                "footer_navigation": [],
                "static_pages": [
                    {
                        "name": "Home",
                        "template": "index.html",
                        "output_file": "index.html",
                    },
                    {
                        "name": "Accueil bis",
                        "template": "index.html",
                        "output_file": "second-home.html",
                    },
                ],
            }

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.put("/api/site/config", json=payload)
                assert response.status_code == 422, response.text
                assert "Only one page can use the index.html template" in response.text

    def test_preview_template_uses_absolute_backend_urls_for_assets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/site/preview-template",
                    json={
                        "template": "index.html",
                        "context": {"hero_image": "files/home_background.jpg"},
                        "site": {
                            "title": "Niamoto",
                            "lang": "fr",
                            "logo_header": "files/niamoto_logo.png",
                            "logo_footer": "files/niamoto_logo.png",
                            "partners": [{"name": "PN", "logo": "files/pn_100.png"}],
                        },
                        "navigation": [],
                        "footer_navigation": [],
                        "output_file": "index.html",
                        "gui_lang": "fr",
                    },
                )
                assert response.status_code == 200, response.text

            html = response.json()["html"]
            assert "http://testserver/api/site/files/niamoto_logo.png" in html
            assert "http://testserver/api/site/files/pn_100.png" in html
            assert "http://testserver/api/site/files/home_background.jpg" in html
            assert (
                "http://testserver/api/site/assets/js/vendor/lucide/0.577.0_lucide.min.js"
                in html
            )

    def test_preview_template_language_switcher_uses_preview_exported_urls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/site/preview-template",
                    json={
                        "template": "page.html",
                        "context": {"title": "Methodology"},
                        "site": {
                            "title": "Niamoto",
                            "lang": "fr",
                            "languages": ["fr", "en"],
                            "language_switcher": True,
                        },
                        "navigation": [],
                        "footer_navigation": [],
                        "output_file": "methodology.html",
                        "gui_lang": "fr",
                    },
                )
                assert response.status_code == 200, response.text

            html = response.json()["html"]
            assert (
                'href="http://testserver/api/site/preview-exported/en/methodology.html"'
                in html
            )

    def test_preview_template_rejects_content_source_outside_project(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()
            outside_file = Path(temp_dir) / "secret.md"
            outside_file.write_text("secret", encoding="utf-8")

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/site/preview-template",
                    json={
                        "template": "page.html",
                        "context": {
                            "title": "Methodology",
                            "content_source": str(outside_file),
                        },
                        "site": {"title": "Niamoto", "lang": "fr"},
                        "navigation": [],
                        "footer_navigation": [],
                    },
                )

            assert response.status_code == 403
            assert response.json()["detail"] == "Access denied: path outside project"

    def test_preview_template_rejects_json_source_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()
            outside_file = Path(temp_dir) / "team.json"
            outside_file.write_text('{"name":"secret"}', encoding="utf-8")

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/site/preview-template",
                    json={
                        "template": "page.html",
                        "context": {
                            "title": "Methodology",
                            "team_source": "../team.json",
                        },
                        "site": {"title": "Niamoto", "lang": "fr"},
                        "navigation": [],
                        "footer_navigation": [],
                    },
                )

            assert response.status_code == 403
            assert response.json()["detail"] == "Access denied: path outside project"

    def test_upload_rejects_absolute_folder_without_writing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()
            outside_dir = Path(temp_dir) / "outside"
            outside_dir.mkdir()

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/site/upload",
                    params={"folder": str(outside_dir)},
                    files={"file": ("probe.md", b"probe", "text/markdown")},
                )

            assert response.status_code == 403
            assert not (outside_dir / "probe.md").exists()

    def test_upload_rejects_folder_traversal_outside_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/site/upload",
                    params={"folder": "files/data/../../config"},
                    files={"file": ("probe.json", b"{}", "application/json")},
                )

            assert response.status_code == 403
            assert not (project / "config" / "probe.json").exists()

    def test_upload_rejects_filename_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/site/upload",
                    params={"folder": "files"},
                    files={"file": ("../probe.md", b"probe", "text/markdown")},
                )

            assert response.status_code == 400
            assert not (project / "probe.md").exists()

    def test_upload_saves_file_without_buffering_entire_body(self, monkeypatch):
        monkeypatch.setattr(site_router, "SITE_UPLOAD_CHUNK_SIZE_BYTES", 4)

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/site/upload",
                    params={"folder": "files"},
                    files={
                        "file": (
                            "field_notes.md",
                            b"sample field notes",
                            "text/markdown",
                        )
                    },
                )

            assert response.status_code == 200
            assert response.json() == {
                "success": True,
                "path": "files/field_notes.md",
                "filename": "field_notes.md",
            }
            assert (project / "files" / "field_notes.md").read_bytes() == (
                b"sample field notes"
            )
            assert not list((project / "files").glob("*.tmp"))

    def test_upload_rejects_oversized_file_without_partial_output(self, monkeypatch):
        monkeypatch.setattr(site_router, "MAX_SITE_UPLOAD_SIZE_BYTES", 5)
        monkeypatch.setattr(site_router, "SITE_UPLOAD_CHUNK_SIZE_BYTES", 4)

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post(
                    "/api/site/upload",
                    params={"folder": "files"},
                    files={"file": ("too_big.md", b"123456", "text/markdown")},
                )

            upload_dir = project / "files"
            assert response.status_code == 413
            assert response.json()["detail"] == (
                "Uploaded file exceeds the maximum allowed size of 5 bytes"
            )
            assert not (upload_dir / "too_big.md").exists()
            assert not list(upload_dir.glob("*.tmp"))

    def test_files_serves_svg_as_attachment_with_defensive_headers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            files_dir = project / "files"
            files_dir.mkdir(parents=True)
            (files_dir / "example.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
                encoding="utf-8",
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)
                response = client.get("/api/site/files/example.svg")

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("image/svg+xml")
            assert response.headers["content-disposition"].startswith("attachment;")
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["content-security-policy"] == "sandbox"

    def test_files_serves_png_inline_for_preview(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            files_dir = project / "files"
            files_dir.mkdir(parents=True)
            (files_dir / "example.png").write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)
                response = client.get("/api/site/files/example.png")

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("image/png")
            assert "content-disposition" not in response.headers
            assert not (project / "files" / "probe.md").exists()

    def test_preview_group_index_uses_absolute_backend_urls_for_assets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(
                config_dir / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {
                                "site": {
                                    "title": "Niamoto",
                                    "lang": "fr",
                                    "logo_header": "files/niamoto_logo.png",
                                },
                                "navigation": [],
                            },
                            "groups": [
                                {
                                    "group_by": "plots",
                                    "index_generator": {
                                        "enabled": True,
                                        "template": "_group_index.html",
                                        "page_config": {"title": "Plots"},
                                        "filters": [],
                                        "display_fields": [],
                                        "views": [{"type": "grid", "default": True}],
                                    },
                                }
                            ],
                        }
                    ]
                },
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.post("/api/site/preview-group-index/plots", json={})
                assert response.status_code == 200, response.text

            html = response.json()["html"]
            assert "http://testserver/api/site/files/niamoto_logo.png" in html
            assert "http://testserver/api/site/assets/css/niamoto.css" in html

    def test_preview_group_index_resolves_localized_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(
                config_dir / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {
                                "site": {
                                    "title": {"fr": "Niamoto FR", "en": "Niamoto EN"},
                                    "lang": "fr",
                                    "languages": ["fr", "en"],
                                },
                                "navigation": [],
                            },
                            "groups": [
                                {
                                    "group_by": "taxons",
                                    "index_generator": {
                                        "enabled": True,
                                        "template": "_group_index.html",
                                        "page_config": {
                                            "title": {
                                                "fr": "Liste des taxons",
                                                "en": "Taxa list",
                                            }
                                        },
                                        "filters": [],
                                        "display_fields": [
                                            {
                                                "name": "name",
                                                "source": "name",
                                                "type": "text",
                                                "label": {"fr": "Nom", "en": "Name"},
                                            },
                                            {
                                                "name": "endemia",
                                                "source": "endemia_url",
                                                "type": "text",
                                                "display": "link",
                                                "link_label": {
                                                    "fr": "Endemia",
                                                    "en": "Endemia",
                                                },
                                                "link_title": {
                                                    "fr": "Voir sur Endemia",
                                                    "en": "View on Endemia",
                                                },
                                            },
                                        ],
                                        "views": [{"type": "grid", "default": True}],
                                    },
                                }
                            ],
                        }
                    ]
                },
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)
                response = client.post(
                    "/api/site/preview-group-index/taxons",
                    json={"gui_lang": "en"},
                )
                assert response.status_code == 200, response.text

            html = response.json()["html"]
            assert "Taxa list" in html
            assert '"label": "Name"' in html
            assert '"link_title": "View on Endemia"' in html
            assert "{&#39;fr&#39;" not in html

    def test_preview_group_index_uses_configured_footer_navigation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(
                config_dir / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {
                                "site": {
                                    "title": {"fr": "Niamoto FR", "en": "Niamoto EN"},
                                    "lang": "fr",
                                    "languages": ["fr", "en"],
                                },
                                "navigation": [],
                                "footer_navigation": [
                                    {
                                        "title": {
                                            "fr": "Ressources",
                                            "en": "Resources",
                                        },
                                        "links": [
                                            {
                                                "text": {
                                                    "fr": "Documentation",
                                                    "en": "Docs",
                                                },
                                                "url": "resources.html",
                                            }
                                        ],
                                    }
                                ],
                            },
                            "groups": [
                                {
                                    "group_by": "plots",
                                    "index_generator": {
                                        "enabled": True,
                                        "template": "_group_index.html",
                                        "page_config": {"title": "Plots"},
                                        "filters": [],
                                        "display_fields": [],
                                        "views": [{"type": "grid", "default": True}],
                                    },
                                }
                            ],
                        }
                    ]
                },
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)
                response = client.post(
                    "/api/site/preview-group-index/plots",
                    json={"gui_lang": "en"},
                )
                assert response.status_code == 200, response.text

            html = response.json()["html"]
            assert "Resources" in html
            assert "Docs" in html
            assert 'href="resources.html"' in html
            assert "Ressources" not in html

    def test_preview_group_index_uses_request_config_before_save(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(
                config_dir / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {
                                "site": {
                                    "title": "Niamoto",
                                    "lang": "fr",
                                },
                                "navigation": [],
                            },
                            "groups": [
                                {
                                    "group_by": "plots",
                                    "index_generator": {
                                        "enabled": False,
                                        "template": "_group_index.html",
                                        "page_config": {"title": "Saved title"},
                                        "filters": [],
                                        "display_fields": [],
                                        "views": [{"type": "grid", "default": True}],
                                    },
                                }
                            ],
                        }
                    ]
                },
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)
                response = client.post(
                    "/api/site/preview-group-index/plots",
                    json={
                        "index_config": {
                            "enabled": True,
                            "template": "_group_index.html",
                            "page_config": {"title": "Draft title"},
                            "filters": [],
                            "display_fields": [],
                            "views": [{"type": "grid", "default": True}],
                        }
                    },
                )
                assert response.status_code == 200, response.text

            html = response.json()["html"]
            assert "Draft title" in html
            assert "Saved title" not in html
            assert '"plots_id":' in html

    def test_preview_group_index_uses_generic_title_samples_for_title_field(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            config_dir = project / "config"
            _write_config(
                config_dir / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {
                                "site": {
                                    "title": "Niamoto",
                                    "lang": "fr",
                                },
                                "navigation": [],
                            },
                            "groups": [
                                {
                                    "group_by": "plots",
                                    "index_generator": {
                                        "enabled": True,
                                        "template": "_group_index.html",
                                        "page_config": {"title": "Plots"},
                                        "filters": [],
                                        "display_fields": [
                                            {
                                                "name": "label",
                                                "source": "label",
                                                "type": "text",
                                                "label": "Label",
                                                "is_title": True,
                                            }
                                        ],
                                        "views": [{"type": "grid", "default": True}],
                                    },
                                }
                            ],
                        }
                    ]
                },
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)
                response = client.post("/api/site/preview-group-index/plots", json={})
                assert response.status_code == 200, response.text

            html = response.json()["html"]
            assert "Plot 1" in html
            assert "Araucaria columnaris" not in html

    def test_preview_group_index_preserves_field_specific_title_samples(self):
        items = _generate_mock_items(
            [
                {
                    "name": "name",
                    "source": "general_info.name.value",
                    "type": "text",
                    "is_title": False,
                },
                {
                    "name": "occurrences_count",
                    "source": "general_info.occurrences_count.value",
                    "type": "text",
                    "is_title": True,
                },
            ],
            count=1,
            id_column="plots_id",
            group_name="plots",
        )

        assert isinstance(items[0]["occurrences_count"], int)
        assert items[0]["occurrences_count"] != "Plot 1"

    def test_preview_exported_site_falls_back_to_legacy_home_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            exports = project / "exports" / "web"
            exports.mkdir(parents=True, exist_ok=True)
            (exports / "Home.html").write_text("legacy-home", encoding="utf-8")

            _write_config(
                project / "config" / "export.yml",
                {
                    "exports": [
                        {
                            "name": "web_pages",
                            "enabled": True,
                            "exporter": "html_page_exporter",
                            "params": {},
                            "static_pages": [
                                {
                                    "name": "Home",
                                    "template": "index.html",
                                    "output_file": "Home.html",
                                }
                            ],
                            "groups": [],
                        }
                    ]
                },
            )

            with patch(
                "niamoto.gui.api.routers.site.get_working_directory",
                return_value=project,
            ):
                app = create_app()
                client = TestClient(app)

                response = client.get("/api/site/preview-exported/index.html")
                assert response.status_code == 200, response.text
                assert "legacy-home" in response.text
