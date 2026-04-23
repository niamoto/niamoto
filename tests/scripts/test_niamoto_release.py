from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest


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


def test_release_commit_files_include_lockfiles_and_release_metadata() -> None:
    assert niamoto_release.RELEASE_COMMIT_FILES == [
        *niamoto_release.VERSION_FILES,
        "src/niamoto/gui/help_content/assets",
        "src/niamoto/gui/help_content/manifest.json",
        "src/niamoto/gui/help_content/pages",
        "src/niamoto/gui/help_content/search-index.json",
        "uv.lock",
        "src-tauri/Cargo.lock",
        ".marketing/plugins.json",
    ]


def test_help_content_files_are_part_of_release_commit() -> None:
    assert niamoto_release.HELP_CONTENT_FILES == [
        "src/niamoto/gui/help_content/assets",
        "src/niamoto/gui/help_content/manifest.json",
        "src/niamoto/gui/help_content/pages",
        "src/niamoto/gui/help_content/search-index.json",
    ]


def test_release_metadata_files_are_part_of_release_commit() -> None:
    assert niamoto_release.RELEASE_METADATA_FILES == [
        ".marketing/plugins.json",
    ]


def test_prepare_release_commit_refreshes_and_stages_lockfiles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"
    recorded_steps: list[tuple[str, list[str], Path]] = []

    monkeypatch.setattr(niamoto_release, "CHANGELOG_PATH", changelog_path)

    def fake_run_step(
        description: str, args: list[str], *, cwd: Path = niamoto_release.ROOT_DIR
    ) -> None:
        recorded_steps.append((description, args, cwd))

    monkeypatch.setattr(niamoto_release, "run_step", fake_run_step)

    niamoto_release.prepare_release_commit(
        "0.15.8",
        "## [v0.15.8] - 2026-04-20\n\n### Bug Fixes\n\n- Refresh release lockfiles\n",
        "0.15.7",
    )

    assert changelog_path.read_text(encoding="utf-8").startswith("## [v0.15.8]")
    assert [description for description, _, _ in recorded_steps] == [
        "Version bump",
        "Refresh uv.lock",
        "Refresh Cargo.lock",
        "Stage release files",
        "Commit release",
        "Create tag",
    ]
    assert recorded_steps[1] == (
        "Refresh uv.lock",
        ["uv", "lock"],
        niamoto_release.ROOT_DIR,
    )
    assert recorded_steps[2] == (
        "Refresh Cargo.lock",
        ["cargo", "update", "--workspace", "--offline", "--quiet"],
        niamoto_release.TAURI_DIR,
    )
    assert recorded_steps[3] == (
        "Stage release files",
        ["git", "add", "--all", *niamoto_release.RELEASE_COMMIT_FILES],
        niamoto_release.ROOT_DIR,
    )


def test_release_worktree_needs_restaging_only_for_worktree_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_outputs = iter(
        [
            "M  .marketing/plugins.json\n",
            "MM .marketing/plugins.json\n",
            "?? src/niamoto/gui/help_content/pages/07-architecture/testing-audit.json\n",
            " M src/niamoto/gui/help_content/search-index.json\n",
            "",
        ]
    )

    def fake_git_output(*args: str, check: bool = True) -> str:
        assert args[:3] == ("status", "--porcelain", "--untracked-files=all")
        return next(status_outputs)

    monkeypatch.setattr(niamoto_release, "git_output", fake_git_output)

    assert niamoto_release.release_worktree_needs_restaging() is False
    assert niamoto_release.release_worktree_needs_restaging() is True
    assert niamoto_release.release_worktree_needs_restaging() is True
    assert niamoto_release.release_worktree_needs_restaging() is True
    assert niamoto_release.release_worktree_needs_restaging() is False


def test_prepare_release_commit_restages_after_hook_updates_release_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"
    recorded_steps: list[tuple[str, list[str], Path]] = []
    commit_attempts = 0

    monkeypatch.setattr(niamoto_release, "CHANGELOG_PATH", changelog_path)

    def fake_run_step(
        description: str, args: list[str], *, cwd: Path = niamoto_release.ROOT_DIR
    ) -> None:
        nonlocal commit_attempts
        recorded_steps.append((description, args, cwd))
        if description == "Commit release":
            commit_attempts += 1
            raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(niamoto_release, "run_step", fake_run_step)
    monkeypatch.setattr(
        niamoto_release, "release_worktree_needs_restaging", lambda: True
    )

    niamoto_release.prepare_release_commit(
        "0.15.8",
        "## [v0.15.8] - 2026-04-20\n\n### Bug Fixes\n\n- Refresh release lockfiles\n",
        "0.15.7",
    )

    assert commit_attempts == 1
    assert [description for description, _, _ in recorded_steps] == [
        "Version bump",
        "Refresh uv.lock",
        "Refresh Cargo.lock",
        "Stage release files",
        "Commit release",
        "Re-stage hook-updated release files",
        "Commit release (retry)",
        "Create tag",
    ]
    assert recorded_steps[5] == (
        "Re-stage hook-updated release files",
        ["git", "add", "--all", *niamoto_release.RELEASE_COMMIT_FILES],
        niamoto_release.ROOT_DIR,
    )


def test_prepare_release_commit_does_not_retry_unrelated_commit_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    changelog_path = tmp_path / "CHANGELOG.md"

    monkeypatch.setattr(niamoto_release, "CHANGELOG_PATH", changelog_path)

    def fake_run_step(
        description: str, args: list[str], *, cwd: Path = niamoto_release.ROOT_DIR
    ) -> None:
        if description == "Commit release":
            raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(niamoto_release, "run_step", fake_run_step)
    monkeypatch.setattr(
        niamoto_release, "release_worktree_needs_restaging", lambda: False
    )

    with pytest.raises(subprocess.CalledProcessError):
        niamoto_release.prepare_release_commit(
            "0.15.8",
            "## [v0.15.8] - 2026-04-20\n\n### Bug Fixes\n\n- Refresh release lockfiles\n",
            "0.15.7",
        )
