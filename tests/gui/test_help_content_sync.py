"""Tests for in-app documentation pack generation."""

from pathlib import Path

import json

from niamoto.gui.help_content.builder import build_help_content


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_help_content_discovers_numbered_sections_and_rewrites_assets(
    tmp_path: Path,
):
    docs_root = tmp_path / "docs"
    output_root = tmp_path / "help_content"

    _write(
        docs_root / "01-getting-started" / "README.md",
        """# Getting Started

Intro paragraph for the section.

![Welcome](../assets/screenshots/desktop/welcome.png)

- [First project](first-project.md)
""",
    )
    _write(
        docs_root / "01-getting-started" / "first-project.md",
        """# First project

Follow the [guide](README.md).

## Import

Import your first data.
""",
    )
    _write(
        docs_root / "10-future" / "README.md",
        """# Future Section

This section should appear automatically after build.
""",
    )
    (docs_root / "assets" / "screenshots" / "desktop").mkdir(
        parents=True, exist_ok=True
    )
    (docs_root / "assets" / "screenshots" / "desktop" / "welcome.png").write_bytes(
        b"png"
    )
    (docs_root / "plans").mkdir(parents=True, exist_ok=True)
    _write(docs_root / "plans" / "internal.md", "# Internal")

    result = build_help_content(docs_root=docs_root, output_root=output_root)

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert [section["slug"] for section in manifest["sections"]] == [
        "01-getting-started",
        "10-future",
    ]

    readme_payload = json.loads(
        (output_root / "pages" / "01-getting-started.json").read_text(encoding="utf-8")
    )
    assert "/api/help/assets/screenshots/desktop/welcome.png" in readme_payload["html"]
    assert "/help/01-getting-started/first-project" in readme_payload["html"]

    first_project_payload = json.loads(
        (output_root / "pages" / "01-getting-started" / "first-project.json").read_text(
            encoding="utf-8"
        )
    )
    assert first_project_payload["headings"] == [
        {"title": "Import", "level": 2, "id": "import"}
    ]
    assert (output_root / "assets" / "screenshots" / "desktop" / "welcome.png").exists()


def test_build_help_content_excludes_api_subtree_and_opted_out_pages(tmp_path: Path):
    docs_root = tmp_path / "docs"
    output_root = tmp_path / "help_content"

    _write(
        docs_root / "06-reference" / "README.md",
        """# Reference

See the [API source](api/modules.rst) and the [guide](api-export-guide.md).
""",
    )
    _write(
        docs_root / "06-reference" / "api-export-guide.md",
        """---
in_app_docs: false
---
# API Export Guide
""",
    )
    _write(
        docs_root / "06-reference" / "api" / "modules.rst",
        """API Modules
===========
""",
    )

    build_help_content(docs_root=docs_root, output_root=output_root)

    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["sections"]) == 1
    section_pages = manifest["sections"][0]["pages"]
    assert [page["slug"] for page in section_pages] == ["06-reference"]

    readme_payload = json.loads(
        (output_root / "pages" / "06-reference.json").read_text(encoding="utf-8")
    )
    assert "/api/help/assets/06-reference/api/modules.rst" in readme_payload["html"]

    search_index = json.loads(
        (output_root / "search-index.json").read_text(encoding="utf-8")
    )
    assert [entry["slug"] for entry in search_index["entries"]] == ["06-reference"]
