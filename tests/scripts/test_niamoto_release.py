from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "build" / "niamoto_release.py"
)
SPEC = importlib.util.spec_from_file_location("niamoto_release", MODULE_PATH)
assert SPEC and SPEC.loader
niamoto_release = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = niamoto_release
SPEC.loader.exec_module(niamoto_release)


def test_suggest_bump_prefers_major_for_breaking_change() -> None:
    commits = (
        niamoto_release.CommitInfo(
            sha="1",
            subject="feat!: break everything",
            body="BREAKING CHANGE: incompatible config",
            category="Features",
            cleaned_subject="Break everything",
            commit_type="feat",
            is_breaking=True,
            is_feature=True,
        ),
    )

    assert niamoto_release.suggest_bump(commits) == "major"


def test_suggest_bump_prefers_minor_for_features() -> None:
    commits = (
        niamoto_release.CommitInfo(
            sha="1",
            subject="feat: add release dashboard",
            body="",
            category="Features",
            cleaned_subject="Add release dashboard",
            commit_type="feat",
            is_breaking=False,
            is_feature=True,
        ),
        niamoto_release.CommitInfo(
            sha="2",
            subject="fix: harden retry loop",
            body="",
            category="Bug Fixes",
            cleaned_subject="Harden retry loop",
            commit_type="fix",
            is_breaking=False,
            is_feature=False,
        ),
    )

    assert niamoto_release.suggest_bump(commits) == "minor"


def test_insert_changelog_section_injects_after_unreleased() -> None:
    changelog = "# Changelog\n\n## [Unreleased]\n\n## [v0.15.5] - 2026-04-20\n"
    section = "## [v0.15.6] - 2026-04-21\n\n### Bug Fixes\n\n- Repair release flow\n"

    updated = niamoto_release.insert_changelog_section(changelog, section, "0.15.6")

    assert "## [Unreleased]\n\n## [v0.15.6] - 2026-04-21" in updated
    assert updated.index("## [v0.15.6] - 2026-04-21") < updated.index(
        "## [v0.15.5] - 2026-04-20"
    )


def test_build_release_notes_adds_compare_link() -> None:
    section = "## [v0.15.6] - 2026-04-21\n\n### Bug Fixes\n\n- Repair release flow\n"

    notes = niamoto_release.build_release_notes("0.15.6", "v0.15.5", section)

    assert "## What's Changed" in notes
    assert "- Repair release flow" in notes
    assert "compare/v0.15.5...v0.15.6" in notes


def test_render_changelog_section_groups_entries_by_category() -> None:
    commits = (
        niamoto_release.CommitInfo(
            sha="1",
            subject="fix: repair trigger fan-out",
            body="",
            category="Bug Fixes",
            cleaned_subject="Repair trigger fan-out",
            commit_type="fix",
            is_breaking=False,
            is_feature=False,
        ),
        niamoto_release.CommitInfo(
            sha="2",
            subject="docs: rewrite release contract",
            body="",
            category="Documentation",
            cleaned_subject="Rewrite release contract",
            commit_type="docs",
            is_breaking=False,
            is_feature=False,
        ),
    )

    rendered = niamoto_release.render_changelog_section(
        "0.15.6", commits, date(2026, 4, 21)
    )

    assert "## [v0.15.6] - 2026-04-21" in rendered
    assert "### Bug Fixes" in rendered
    assert "### Documentation" in rendered
    assert "- Repair trigger fan-out" in rendered
    assert "- Rewrite release contract" in rendered
