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
