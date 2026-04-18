#!/usr/bin/env python3
"""Synchronize canonical About content into README and frontend assets."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any, cast

import yaml

README_START = "<!-- about:start -->"
README_END = "<!-- about:end -->"
README_IMAGE_BASE = "https://raw.githubusercontent.com/niamoto/niamoto/HEAD"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_content_path() -> Path:
    return repo_root() / "docs/assets/about/content.yaml"


def default_readme_path() -> Path:
    return repo_root() / "README.md"


def default_fragment_path() -> Path:
    return repo_root() / "docs/assets/about/README-about.en.md"


def default_ui_output_path() -> Path:
    return (
        repo_root()
        / "src/niamoto/gui/ui/src/features/tools/content/aboutContent.generated.ts"
    )


def _require_mapping(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping")
    return cast(dict[str, Any], value)


def _require_list(value: Any, *, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    return cast(list[Any], value)


def load_about_content(content_path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(content_path.read_text(encoding="utf-8"))
    content = _require_mapping(raw, context="about content")

    sections = _require_mapping(content.get("sections"), context="sections")
    _require_list(content.get("team"), context="team")
    organizations = _require_list(content.get("organizations"), context="organizations")
    organization_order = _require_list(
        content.get("organization_order"),
        context="organization_order",
    )

    for locale in ("fr", "en"):
        locale_sections = _require_mapping(
            sections.get(locale),
            context=f"sections.{locale}",
        )
        _require_mapping(locale_sections.get("team"), context=f"sections.{locale}.team")
        _require_mapping(
            locale_sections.get("partners"),
            context=f"sections.{locale}.partners",
        )

    organization_ids = {
        _require_mapping(item, context="organization item").get("id")
        for item in organizations
    }
    missing_ids = [item for item in organization_order if item not in organization_ids]
    if missing_ids:
        raise ValueError(
            f"organization_order contains unknown ids: {', '.join(map(str, missing_ids))}"
        )

    return content


def _read_logo_data_url(repo: Path, relative_path: str) -> str:
    logo_path = repo / relative_path
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo file does not exist: {relative_path}")
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _readme_image_url(relative_path: str) -> str:
    return f"{README_IMAGE_BASE}/{relative_path}"


def _render_readme_link(label: str, url: str | None) -> str:
    if not url:
        return label
    return f'<a href="{url}">{label}</a>'


def _render_readme_team_line(member: dict[str, Any]) -> str:
    role = str(_require_mapping(member["role"], context="team role")["en"])
    name = str(member["name"])
    linked_name = _render_readme_link(
        f"**{name}**", cast(str | None, member.get("url"))
    )
    return f"- {linked_name} — {role}"


def build_ui_payload(content: dict[str, Any], repo: Path) -> dict[str, Any]:
    sections = _require_mapping(content["sections"], context="sections")
    team = [
        _require_mapping(item, context="team item")
        for item in _require_list(content["team"], context="team")
    ]
    organizations = {
        item["id"]: item
        for item in (
            _require_mapping(org, context="organization item")
            for org in _require_list(content["organizations"], context="organizations")
        )
    }
    organization_order = [
        str(item)
        for item in _require_list(
            content["organization_order"], context="organization_order"
        )
    ]
    meta = _require_mapping(content.get("meta", {}), context="meta")

    payload: dict[str, Any] = {
        "generatedAt": str(meta.get("last_verified", "")),
        "sourceShowcaseUrl": str(meta.get("source_showcase_url", "")),
        "locales": {},
    }

    for locale in ("fr", "en"):
        locale_sections = _require_mapping(
            sections[locale], context=f"sections.{locale}"
        )
        team_section = _require_mapping(
            locale_sections["team"], context=f"sections.{locale}.team"
        )
        partners_section = _require_mapping(
            locale_sections["partners"],
            context=f"sections.{locale}.partners",
        )
        payload["locales"][locale] = {
            "summary": str(locale_sections["summary"]).strip(),
            "teamTitle": str(team_section["title"]).strip(),
            "teamIntro": str(team_section["intro"]).strip(),
            "members": [
                {
                    "id": str(member["id"]),
                    "name": str(member["name"]),
                    "role": str(
                        _require_mapping(member["role"], context="team role")[locale]
                    ),
                    "url": member.get("url"),
                }
                for member in team
            ],
            "partnersTitle": str(partners_section["title"]).strip(),
            "partnersIntro": str(partners_section["intro"]).strip(),
            "organizations": [
                {
                    "id": org_id,
                    "name": str(
                        _require_mapping(
                            organizations[org_id]["name"],
                            context=f"organization {org_id} name",
                        )[locale]
                    ),
                    "url": organizations[org_id].get("url"),
                    "logoAlt": str(
                        _require_mapping(
                            organizations[org_id]["name"],
                            context=f"organization {org_id} name",
                        )[locale]
                    ),
                    "logoSrc": _read_logo_data_url(
                        repo,
                        str(organizations[org_id]["logo"]),
                    ),
                    "categories": [
                        str(category)
                        for category in _require_list(
                            organizations[org_id].get("categories", []),
                            context=f"organization {org_id} categories",
                        )
                    ],
                }
                for org_id in organization_order
            ],
        }

    return payload


def render_ui_module(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        "// Generated by scripts/build/sync_about_content.py. Do not edit manually.\n"
        "import type { AboutContentBundle } from './aboutContent.types'\n\n"
        f"export const aboutContent: AboutContentBundle = {serialized}\n"
    )


def render_readme_fragment(content: dict[str, Any]) -> str:
    sections = _require_mapping(content["sections"], context="sections")
    en_sections = _require_mapping(sections["en"], context="sections.en")
    team_section = _require_mapping(en_sections["team"], context="sections.en.team")
    partners_section = _require_mapping(
        en_sections["partners"],
        context="sections.en.partners",
    )
    team = [
        _require_mapping(item, context="team item")
        for item in _require_list(content["team"], context="team")
    ]
    organizations = {
        item["id"]: item
        for item in (
            _require_mapping(org, context="organization item")
            for org in _require_list(content["organizations"], context="organizations")
        )
    }
    organization_order = [
        str(item)
        for item in _require_list(
            content["organization_order"], context="organization_order"
        )
    ]

    team_lines = "\n".join(_render_readme_team_line(member) for member in team)

    logo_links = "\n".join(
        (
            f'  <a href="{organizations[org_id]["url"]}">'
            f'<img src="{_readme_image_url(str(organizations[org_id]["logo"]))}" '
            f'alt="{_require_mapping(organizations[org_id]["name"], context=f"organization {org_id} name")["en"]}" '
            'height="52" /></a>'
        )
        for org_id in organization_order
    )

    organization_names = " · ".join(
        _render_readme_link(
            str(
                _require_mapping(
                    organizations[org_id]["name"],
                    context=f"organization {org_id} name",
                )["en"]
            ),
            cast(str | None, organizations[org_id].get("url")),
        )
        for org_id in organization_order
    )

    return "\n".join(
        [
            "## About Niamoto",
            "",
            str(en_sections["summary"]).strip(),
            "",
            f"### {str(team_section['title']).strip()}",
            "",
            str(team_section["intro"]).strip(),
            "",
            team_lines,
            "",
            f"### {str(partners_section['title']).strip()}",
            "",
            str(partners_section["intro"]).strip(),
            "",
            '<p align="center">',
            logo_links,
            "</p>",
            "",
            f'<p align="center"><sub>{organization_names}</sub></p>',
        ]
    )


def inject_readme_fragment(readme_text: str, fragment: str) -> str:
    if README_START not in readme_text or README_END not in readme_text:
        raise ValueError("README markers are missing for About content sync")

    start_index = readme_text.index(README_START) + len(README_START)
    end_index = readme_text.index(README_END)
    return (
        readme_text[:start_index]
        + "\n\n"
        + fragment.rstrip()
        + "\n\n"
        + readme_text[end_index:]
    )


def sync_about_content(
    *,
    content_path: Path,
    readme_path: Path,
    fragment_path: Path,
    ui_output_path: Path,
) -> None:
    repo = repo_root()
    content = load_about_content(content_path)
    ui_payload = build_ui_payload(content, repo)
    ui_module = render_ui_module(ui_payload)
    readme_fragment = render_readme_fragment(content)
    updated_readme = inject_readme_fragment(
        readme_path.read_text(encoding="utf-8"),
        readme_fragment,
    )

    fragment_path.parent.mkdir(parents=True, exist_ok=True)
    ui_output_path.parent.mkdir(parents=True, exist_ok=True)
    fragment_path.write_text(readme_fragment + "\n", encoding="utf-8")
    ui_output_path.write_text(ui_module, encoding="utf-8")
    readme_path.write_text(updated_readme, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize About content into README and frontend assets.",
    )
    parser.add_argument(
        "--content-path",
        type=Path,
        default=default_content_path(),
        help="Canonical About content YAML file.",
    )
    parser.add_argument(
        "--readme-path",
        type=Path,
        default=default_readme_path(),
        help="README file to update in place.",
    )
    parser.add_argument(
        "--fragment-path",
        type=Path,
        default=default_fragment_path(),
        help="Generated English README fragment path.",
    )
    parser.add_argument(
        "--ui-output-path",
        type=Path,
        default=default_ui_output_path(),
        help="Generated frontend content module path.",
    )
    args = parser.parse_args()

    sync_about_content(
        content_path=args.content_path,
        readme_path=args.readme_path,
        fragment_path=args.fragment_path,
        ui_output_path=args.ui_output_path,
    )
    print(f"Updated README: {args.readme_path}")
    print(f"Updated README fragment: {args.fragment_path}")
    print(f"Updated frontend content: {args.ui_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
