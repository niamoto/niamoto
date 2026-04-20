"""Integration tests for site router endpoints."""

from pathlib import Path
from unittest.mock import patch
import shutil
import tempfile

import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


def _write_config(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


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
