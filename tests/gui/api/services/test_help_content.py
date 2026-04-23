"""Tests for generated help-content service helpers."""

from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from niamoto.gui.api.services.help_content import HelpContentService


def test_load_manifest_search_index_and_page(tmp_path):
    root = tmp_path / "help"
    pages_dir = root / "pages"
    pages_dir.mkdir(parents=True)
    (root / "assets").mkdir()

    (root / "manifest.json").write_text(
        json.dumps({"pages": ["intro"]}),
        encoding="utf-8",
    )
    (root / "search-index.json").write_text(
        json.dumps({"entries": [{"slug": "intro"}]}),
        encoding="utf-8",
    )
    (pages_dir / "intro.json").write_text(
        json.dumps({"title": "Intro"}),
        encoding="utf-8",
    )

    service = HelpContentService(root)

    assert service.load_manifest() == {"pages": ["intro"]}
    assert service.load_search_index() == {"entries": [{"slug": "intro"}]}
    assert service.load_page("intro") == {"title": "Intro"}


def test_load_page_rejects_empty_and_traversal_slugs(tmp_path):
    service = HelpContentService(tmp_path / "help")

    with pytest.raises(HTTPException) as empty_exc:
        service.load_page(" / ")
    with pytest.raises(HTTPException) as traversal_exc:
        service.load_page("../secrets")

    assert empty_exc.value.status_code == 404
    assert traversal_exc.value.status_code == 404


def test_resolve_asset_path_returns_existing_file_and_blocks_escape(tmp_path):
    root = tmp_path / "help"
    assets_dir = root / "assets" / "img"
    assets_dir.mkdir(parents=True)
    asset_path = assets_dir / "logo.svg"
    asset_path.write_text("<svg />", encoding="utf-8")

    service = HelpContentService(root)

    assert service.resolve_asset_path("img/logo.svg") == asset_path.resolve()

    with pytest.raises(HTTPException) as exc_info:
        service.resolve_asset_path("../outside.txt")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Documentation asset not found"


def test_read_json_raises_meaningful_errors_for_missing_or_invalid_content(tmp_path):
    root = tmp_path / "help"
    root.mkdir()
    service = HelpContentService(root)

    with pytest.raises(HTTPException) as missing_exc:
        service.load_manifest()

    (root / "manifest.json").write_text("{invalid json}", encoding="utf-8")

    with pytest.raises(HTTPException) as invalid_exc:
        service.load_manifest()

    assert missing_exc.value.status_code == 503
    assert invalid_exc.value.status_code == 500
