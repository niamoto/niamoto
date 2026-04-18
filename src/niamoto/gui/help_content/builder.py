"""Build a generated in-app documentation pack from the public docs tree."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import html
import json
from pathlib import Path
import re
import shutil
from typing import Any
from urllib.parse import quote, unquote

import markdown
import yaml

PAGE_SUFFIXES = {".md", ".rst"}
HELP_OPT_OUT_KEY = "in_app_docs"
INTERNAL_TOP_LEVEL_DIRS = {
    "_archive",
    "_build",
    "_ext",
    "_static",
    "assets",
    "brainstorms",
    "examples",
    "ideation",
    "plans",
    "superpowers",
}
EXCLUDED_DOC_SUBTREES = {Path("06-reference/api")}
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MARKDOWN_LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
RST_HEADING_RE = re.compile(
    r"^(?P<title>[^\n]+)\n(?P<underline>[=\-~^`:#\"']{3,})\s*$",
    re.MULTILINE,
)


@dataclass(slots=True)
class SourcePage:
    """Source page discovered from the public docs tree."""

    source_path: Path
    relative_path: Path
    section_slug: str
    slug: str
    is_section_index: bool
    suffix: str
    title: str
    description: str
    body: str
    metadata: dict[str, Any]

    @property
    def route_path(self) -> str:
        return f"/help/{self.slug}"


@dataclass(slots=True)
class HelpContentBuildResult:
    """Summary of a generated help-content build."""

    sections: int
    pages: int
    assets: int
    manifest_path: Path
    search_index_path: Path


def default_help_content_root() -> Path:
    """Return the package-local output directory for generated help content."""

    return Path(__file__).resolve().parent


def default_docs_root() -> Path:
    """Return the repository docs directory."""

    return Path(__file__).resolve().parents[4] / "docs"


def build_help_content(
    docs_root: Path | None = None,
    output_root: Path | None = None,
) -> HelpContentBuildResult:
    """Generate the in-app docs pack from the public docs tree."""

    docs_root = (docs_root or default_docs_root()).resolve()
    output_root = (output_root or default_help_content_root()).resolve()

    if not docs_root.exists():
        raise FileNotFoundError(f"Docs root does not exist: {docs_root}")

    pages_root = output_root / "pages"
    assets_root = output_root / "assets"
    manifest_path = output_root / "manifest.json"
    search_index_path = output_root / "search-index.json"

    if pages_root.exists():
        shutil.rmtree(pages_root)
    if assets_root.exists():
        shutil.rmtree(assets_root)
    if manifest_path.exists():
        manifest_path.unlink()
    if search_index_path.exists():
        search_index_path.unlink()

    pages_root.mkdir(parents=True, exist_ok=True)
    assets_root.mkdir(parents=True, exist_ok=True)

    discovered_sections = _discover_sections(docs_root)
    source_pages = _discover_pages(docs_root, discovered_sections)
    slug_lookup = {page.source_path.resolve(): page.slug for page in source_pages}

    ordered_sections = []
    all_search_entries: list[dict[str, Any]] = []
    asset_sources: dict[Path, str] = {}

    for section in discovered_sections:
        section_slug = section["slug"]
        section_pages = [
            page for page in source_pages if page.section_slug == section_slug
        ]
        if not section_pages:
            continue

        ordered_pages = _order_section_pages(
            section_pages,
            docs_root=docs_root,
            slug_lookup=slug_lookup,
        )

        section_index = ordered_pages[0]
        section_payload_pages = []
        for page in ordered_pages:
            rendered = _render_page(
                page=page,
                docs_root=docs_root,
                slug_lookup=slug_lookup,
                asset_sources=asset_sources,
            )
            _write_page_payload(pages_root, page.slug, rendered)
            section_payload_pages.append(
                {
                    "slug": page.slug,
                    "path": page.route_path,
                    "title": rendered["title"],
                    "description": rendered["description"],
                    "is_section_index": page.is_section_index,
                    "headings": rendered["headings"],
                }
            )
            all_search_entries.append(
                {
                    "slug": page.slug,
                    "path": page.route_path,
                    "section_slug": page.section_slug,
                    "section_title": section_index.title,
                    "title": rendered["title"],
                    "description": rendered["description"],
                    "is_section_index": page.is_section_index,
                    "headings": [heading["title"] for heading in rendered["headings"]],
                    "keywords": _unique_strings(
                        [
                            section_index.title,
                            rendered["title"],
                            *[heading["title"] for heading in rendered["headings"]],
                        ]
                    ),
                }
            )

        ordered_sections.append(
            {
                "slug": section_slug,
                "title": section_index.title,
                "description": section_index.description,
                "path": section_index.route_path,
                "article_count": len(section_payload_pages),
                "pages": section_payload_pages,
            }
        )

    copied_assets = _copy_assets(
        asset_sources=asset_sources,
        docs_root=docs_root,
        assets_root=assets_root,
    )

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "sections": ordered_sections,
        "default_path": ordered_sections[0]["path"] if ordered_sections else "/help",
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    search_index = {
        "generated_at": manifest["generated_at"],
        "entries": sorted(
            all_search_entries,
            key=lambda entry: (
                entry["section_slug"],
                0 if entry["is_section_index"] else 1,
                entry["title"].lower(),
            ),
        ),
    }
    search_index_path.write_text(
        json.dumps(search_index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return HelpContentBuildResult(
        sections=len(ordered_sections),
        pages=len(source_pages),
        assets=copied_assets,
        manifest_path=manifest_path,
        search_index_path=search_index_path,
    )


def _discover_sections(docs_root: Path) -> list[dict[str, str]]:
    sections = []
    for child in sorted(docs_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in INTERNAL_TOP_LEVEL_DIRS:
            continue
        if not re.match(r"^\d{2}-", child.name):
            continue
        readme_path = child / "README.md"
        if not readme_path.exists():
            continue
        sections.append({"slug": child.name, "directory": child.name})
    return sections


def _discover_pages(
    docs_root: Path,
    sections: list[dict[str, str]],
) -> list[SourcePage]:
    pages: list[SourcePage] = []

    for section in sections:
        section_dir = docs_root / section["directory"]
        section_slug = section["slug"]
        for source_path in sorted(section_dir.rglob("*")):
            if not source_path.is_file():
                continue
            if source_path.suffix.lower() not in PAGE_SUFFIXES:
                continue

            relative_path = source_path.relative_to(docs_root)
            if _is_excluded_doc_path(relative_path):
                continue

            metadata, body = _read_source_document(source_path)
            if _is_opted_out(metadata, body, source_path.suffix.lower()):
                continue

            slug = _slug_for_relative_path(relative_path)
            pages.append(
                SourcePage(
                    source_path=source_path.resolve(),
                    relative_path=relative_path,
                    section_slug=section_slug,
                    slug=slug,
                    is_section_index=relative_path.name == "README.md",
                    suffix=source_path.suffix.lower(),
                    title=_extract_title(body, relative_path),
                    description=_extract_description(body),
                    body=body,
                    metadata=metadata,
                )
            )

    return pages


def _is_excluded_doc_path(relative_path: Path) -> bool:
    return any(
        relative_path == subtree or subtree in relative_path.parents
        for subtree in EXCLUDED_DOC_SUBTREES
    )


def _read_source_document(source_path: Path) -> tuple[dict[str, Any], str]:
    raw_text = source_path.read_text(encoding="utf-8")
    if source_path.suffix.lower() != ".md":
        return {}, raw_text

    frontmatter_match = FRONTMATTER_RE.match(raw_text)
    if not frontmatter_match:
        return {}, raw_text

    metadata = yaml.safe_load(frontmatter_match.group(1)) or {}
    body = raw_text[frontmatter_match.end() :]
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, body


def _is_opted_out(metadata: dict[str, Any], body: str, suffix: str) -> bool:
    if metadata.get(HELP_OPT_OUT_KEY) is False:
        return True
    if suffix == ".md":
        return "<!-- in_app_docs: false -->" in body
    if suffix == ".rst":
        return ".. in_app_docs: false" in body
    return False


def _slug_for_relative_path(relative_path: Path) -> str:
    if relative_path.name == "README.md":
        return relative_path.parent.as_posix()
    return relative_path.with_suffix("").as_posix()


def _extract_title(body: str, relative_path: Path) -> str:
    markdown_match = MARKDOWN_HEADING_RE.search(body)
    if markdown_match:
        return _strip_markdown(markdown_match.group(2)).strip()

    rst_match = RST_HEADING_RE.search(body)
    if rst_match:
        return _strip_markdown(rst_match.group("title")).strip()

    if relative_path.name == "README.md":
        return _humanize_slug(relative_path.parent.name)
    return _humanize_slug(relative_path.stem)


def _extract_description(body: str) -> str:
    body_without_headings = MARKDOWN_HEADING_RE.sub("", body)
    paragraphs = [
        paragraph.strip() for paragraph in re.split(r"\n\s*\n", body_without_headings)
    ]
    for paragraph in paragraphs:
        if not paragraph:
            continue
        if (
            paragraph.startswith("![")
            or paragraph.startswith(">")
            or paragraph.startswith("```")
        ):
            continue
        text = _strip_markdown(paragraph).strip()
        if text:
            return text[:220]
    return ""


def _order_section_pages(
    section_pages: list[SourcePage],
    docs_root: Path,
    slug_lookup: dict[Path, str],
) -> list[SourcePage]:
    pages_by_slug = {page.slug: page for page in section_pages}
    readme_page = next(page for page in section_pages if page.is_section_index)
    ordered_slugs = [readme_page.slug]

    for linked_slug in _extract_readme_link_order(readme_page, docs_root, slug_lookup):
        linked_page = pages_by_slug.get(linked_slug)
        if linked_page is None:
            continue
        if linked_page.slug not in ordered_slugs:
            ordered_slugs.append(linked_page.slug)

    for page in sorted(
        section_pages,
        key=lambda item: (
            0 if item.is_section_index else 1,
            len(item.relative_path.parts),
            item.relative_path.as_posix(),
        ),
    ):
        if page.slug not in ordered_slugs:
            ordered_slugs.append(page.slug)

    return [pages_by_slug[slug] for slug in ordered_slugs]


def _extract_readme_link_order(
    readme_page: SourcePage,
    docs_root: Path,
    slug_lookup: dict[Path, str],
) -> list[str]:
    linked_slugs: list[str] = []
    for _, target in MARKDOWN_LINK_RE.findall(readme_page.body):
        resolved = _resolve_relative_target(readme_page.source_path, target, docs_root)
        if resolved is None:
            continue
        slug = slug_lookup.get(resolved)
        if slug is None:
            continue
        linked_slugs.append(slug)
    return linked_slugs


def _render_page(
    page: SourcePage,
    docs_root: Path,
    slug_lookup: dict[Path, str],
    asset_sources: dict[Path, str],
) -> dict[str, Any]:
    if page.suffix == ".md":
        rendered_body, headings = _render_markdown_page(
            page=page,
            docs_root=docs_root,
            slug_lookup=slug_lookup,
            asset_sources=asset_sources,
        )
    else:
        rendered_body, headings = _render_plain_rst_page(page)

    return {
        "slug": page.slug,
        "path": page.route_path,
        "title": page.title,
        "description": page.description,
        "section_slug": page.section_slug,
        "is_section_index": page.is_section_index,
        "headings": headings,
        "html": rendered_body,
        "source_path": page.relative_path.as_posix(),
    }


def _render_markdown_page(
    page: SourcePage,
    docs_root: Path,
    slug_lookup: dict[Path, str],
    asset_sources: dict[Path, str],
) -> tuple[str, list[dict[str, Any]]]:
    source = page.body
    source = MARKDOWN_IMAGE_RE.sub(
        lambda match: _rewrite_markdown_image(
            alt_text=match.group(1),
            target=match.group(2),
            source_path=page.source_path,
            docs_root=docs_root,
            asset_sources=asset_sources,
        ),
        source,
    )
    source = MARKDOWN_LINK_RE.sub(
        lambda match: _rewrite_markdown_link(
            label=match.group(1),
            target=match.group(2),
            source_path=page.source_path,
            docs_root=docs_root,
            slug_lookup=slug_lookup,
            asset_sources=asset_sources,
        ),
        source,
    )

    md = markdown.Markdown(
        extensions=[
            "extra",
            "tables",
            "fenced_code",
            "sane_lists",
            "toc",
        ]
    )
    html_body = md.convert(source)
    headings = _flatten_markdown_toc(getattr(md, "toc_tokens", []))
    headings = [heading for heading in headings if heading["level"] > 1]
    return html_body, headings


def _render_plain_rst_page(page: SourcePage) -> tuple[str, list[dict[str, Any]]]:
    headings = []
    for match in RST_HEADING_RE.finditer(page.body):
        underline = match.group("underline")
        level = 1 if underline.startswith("=") else 2
        headings.append(
            {
                "title": match.group("title").strip(),
                "level": level,
            }
        )

    escaped = html.escape(page.body)
    return f"<pre>{escaped}</pre>", headings[1:] if len(headings) > 1 else []


def _rewrite_markdown_image(
    alt_text: str,
    target: str,
    source_path: Path,
    docs_root: Path,
    asset_sources: dict[Path, str],
) -> str:
    rewritten = _rewrite_target(
        target=target,
        source_path=source_path,
        docs_root=docs_root,
        slug_lookup=None,
        asset_sources=asset_sources,
        prefer_asset=True,
    )
    return f"![{alt_text}]({rewritten})"


def _rewrite_markdown_link(
    label: str,
    target: str,
    source_path: Path,
    docs_root: Path,
    slug_lookup: dict[Path, str],
    asset_sources: dict[Path, str],
) -> str:
    rewritten = _rewrite_target(
        target=target,
        source_path=source_path,
        docs_root=docs_root,
        slug_lookup=slug_lookup,
        asset_sources=asset_sources,
        prefer_asset=False,
    )
    return f"[{label}]({rewritten})"


def _rewrite_target(
    target: str,
    source_path: Path,
    docs_root: Path,
    slug_lookup: dict[Path, str] | None,
    asset_sources: dict[Path, str],
    prefer_asset: bool,
) -> str:
    target = target.strip()
    if not target:
        return target
    if target.startswith(("http://", "https://", "mailto:", "data:")):
        return target
    if target.startswith("#"):
        return target

    target_path, anchor = _split_target_anchor(target)
    resolved_path = _resolve_relative_target(source_path, target_path, docs_root)
    if resolved_path is None:
        return target

    if not prefer_asset and slug_lookup is not None:
        slug = slug_lookup.get(resolved_path)
        if slug is not None:
            return f"/help/{slug}{anchor}"

    if resolved_path.is_file():
        asset_rel = _asset_relative_path(resolved_path, docs_root)
        asset_sources[resolved_path] = asset_rel
        return f"/api/help/assets/{quote(asset_rel)}"

    return target


def _split_target_anchor(target: str) -> tuple[str, str]:
    if "#" not in target:
        return target, ""
    path_part, anchor = target.split("#", 1)
    anchor_part = f"#{anchor}" if anchor else ""
    return path_part, anchor_part


def _resolve_relative_target(
    source_path: Path,
    target: str,
    docs_root: Path,
) -> Path | None:
    if not target:
        return source_path.resolve()

    candidate = (source_path.parent / unquote(target)).resolve()
    if not _is_within_docs(candidate, docs_root):
        return None

    if candidate.is_dir():
        readme_candidate = candidate / "README.md"
        if readme_candidate.exists():
            return readme_candidate.resolve()

    if candidate.exists():
        return candidate

    if candidate.suffix:
        return None

    for suffix in (".md", ".rst"):
        suffixed = candidate.with_suffix(suffix)
        if suffixed.exists():
            return suffixed.resolve()

    readme_candidate = candidate / "README.md"
    if readme_candidate.exists():
        return readme_candidate.resolve()

    return None


def _is_within_docs(path: Path, docs_root: Path) -> bool:
    try:
        path.relative_to(docs_root)
        return True
    except ValueError:
        return False


def _asset_relative_path(asset_path: Path, docs_root: Path) -> str:
    docs_assets_root = docs_root / "assets"
    if asset_path.is_relative_to(docs_assets_root):
        return asset_path.relative_to(docs_assets_root).as_posix()
    return asset_path.relative_to(docs_root).as_posix()


def _copy_assets(
    asset_sources: dict[Path, str],
    docs_root: Path,
    assets_root: Path,
) -> int:
    copied = 0
    for source_path, relative_asset_path in sorted(
        asset_sources.items(), key=lambda item: item[1]
    ):
        destination = assets_root / relative_asset_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        copied += 1
    return copied


def _write_page_payload(pages_root: Path, slug: str, payload: dict[str, Any]) -> None:
    target = pages_root / f"{slug}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _flatten_markdown_toc(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for token in tokens:
        flattened.append(
            {
                "title": _strip_markdown(str(token.get("name", "")).strip()),
                "level": int(token.get("level", 1)),
                "id": str(token.get("id", "")).strip(),
            }
        )
        flattened.extend(_flatten_markdown_toc(token.get("children", [])))
    return flattened


def _strip_markdown(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[*_~#>!-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _humanize_slug(value: str) -> str:
    title = re.sub(r"^\d{2}-", "", value)
    title = title.replace("-", " ").replace("_", " ")
    return " ".join(word.capitalize() for word in title.split())


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result
