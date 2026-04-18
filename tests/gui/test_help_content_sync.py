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

```{toctree}
:hidden:

first-project
```
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
    assert "toctree" not in readme_payload["html"]
    assert "<pre><code" not in readme_payload["html"]

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
    assert "/tools/docs" in readme_payload["html"]
    assert "/api/help/assets/06-reference/api/modules.rst" not in readme_payload["html"]
    assert not (
        output_root / "assets" / "06-reference" / "api" / "modules.rst"
    ).exists()

    search_index = json.loads(
        (output_root / "search-index.json").read_text(encoding="utf-8")
    )
    assert [entry["slug"] for entry in search_index["entries"]] == ["06-reference"]


def test_build_help_content_embeds_html_pages_as_iframe_assets(tmp_path: Path):
    docs_root = tmp_path / "docs"
    output_root = tmp_path / "help_content"

    _write(
        docs_root / "08-roadmaps" / "README.md",
        """# Roadmaps

- [GBIF challenge deck](gbif-challenge-2026.html)
""",
    )
    _write(
        docs_root / "08-roadmaps" / "gbif-challenge-2026.html",
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GBIF Challenge 2026</title>
  <meta name="description" content="Standalone showcase page for the challenge.">
</head>
<body>
  <h1>GBIF Challenge 2026</h1>
  <p>Standalone repository artifact.</p>
</body>
</html>
""",
    )

    build_help_content(docs_root=docs_root, output_root=output_root)

    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    section_pages = manifest["sections"][0]["pages"]
    assert [page["slug"] for page in section_pages] == [
        "08-roadmaps",
        "08-roadmaps/gbif-challenge-2026",
    ]
    assert section_pages[1]["page_type"] == "html"

    html_payload = json.loads(
        (output_root / "pages" / "08-roadmaps" / "gbif-challenge-2026.json").read_text(
            encoding="utf-8"
        )
    )
    assert html_payload["title"] == "GBIF Challenge 2026"
    assert html_payload["description"] == "Standalone showcase page for the challenge."
    assert html_payload["page_type"] == "html"
    assert html_payload["asset_path"] == "08-roadmaps/gbif-challenge-2026.html"
    assert html_payload["html"] == ""
    assert (
        output_root / "assets" / "08-roadmaps" / "gbif-challenge-2026.html"
    ).exists()
