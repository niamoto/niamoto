"""Tests for generated help-content routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from niamoto.gui.api.app import create_app


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.fixture
def help_content_root(tmp_path: Path) -> Path:
    root = tmp_path / "help_content"
    _write_json(
        root / "manifest.json",
        {
            "generated_at": "2026-04-18T00:00:00+00:00",
            "default_path": "/help/01-getting-started",
            "sections": [
                {
                    "slug": "01-getting-started",
                    "title": "Getting Started",
                    "description": "Start here",
                    "path": "/help/01-getting-started",
                    "article_count": 1,
                    "pages": [
                        {
                            "slug": "01-getting-started",
                            "path": "/help/01-getting-started",
                            "title": "Getting Started",
                            "description": "Start here",
                            "is_section_index": True,
                            "headings": [],
                        }
                    ],
                }
            ],
        },
    )
    _write_json(
        root / "search-index.json",
        {
            "generated_at": "2026-04-18T00:00:00+00:00",
            "entries": [
                {
                    "slug": "01-getting-started",
                    "path": "/help/01-getting-started",
                    "section_slug": "01-getting-started",
                    "section_title": "Getting Started",
                    "title": "Getting Started",
                    "description": "Start here",
                    "is_section_index": True,
                    "headings": ["Install"],
                    "keywords": ["Getting Started", "Install"],
                }
            ],
        },
    )
    _write_json(
        root / "pages" / "01-getting-started.json",
        {
            "slug": "01-getting-started",
            "path": "/help/01-getting-started",
            "title": "Getting Started",
            "description": "Start here",
            "section_slug": "01-getting-started",
            "is_section_index": True,
            "headings": [{"title": "Install", "level": 2, "id": "install"}],
            "html": "<h1>Getting Started</h1>",
            "source_path": "01-getting-started/README.md",
        },
    )
    asset_path = root / "assets" / "screenshots" / "desktop" / "welcome.png"
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(b"png")
    return root


@pytest.fixture
def help_client(help_content_root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "niamoto.gui.api.services.help_content.HELP_CONTENT_ROOT",
        help_content_root,
    )
    return TestClient(create_app())


def test_help_manifest_endpoint_returns_generated_sections(help_client: TestClient):
    response = help_client.get("/api/help/manifest")

    assert response.status_code == 200
    body = response.json()
    assert body["default_path"] == "/help/01-getting-started"
    assert body["sections"][0]["slug"] == "01-getting-started"


def test_help_page_endpoint_returns_page_payload(help_client: TestClient):
    response = help_client.get("/api/help/pages/01-getting-started")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Getting Started"
    assert body["headings"] == [{"title": "Install", "level": 2, "id": "install"}]


def test_help_asset_endpoint_returns_generated_asset(help_client: TestClient):
    response = help_client.get("/api/help/assets/screenshots/desktop/welcome.png")

    assert response.status_code == 200
    assert response.content == b"png"


def test_help_search_index_endpoint_returns_search_entries(help_client: TestClient):
    response = help_client.get("/api/help/search-index")

    assert response.status_code == 200
    body = response.json()
    assert body["entries"][0]["keywords"] == ["Getting Started", "Install"]
