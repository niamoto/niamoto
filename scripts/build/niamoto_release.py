#!/usr/bin/env python3
"""Consolidated release driver for Niamoto."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
CHANGELOG_PATH = ROOT_DIR / "CHANGELOG.md"
BUMPVERSION_PATH = ROOT_DIR / ".bumpversion.cfg"
UI_DIR = ROOT_DIR / "src" / "niamoto" / "gui" / "ui"
TAURI_DIR = ROOT_DIR / "src-tauri"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
CONVENTIONAL_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\([^)]+\))?(?P<breaking>!)?:\s*(?P<summary>.+)$"
)
CURRENT_VERSION_RE = re.compile(
    r"^current_version\s*=\s*(?P<version>\d+\.\d+\.\d+)$", re.M
)

CHANGELOG_CATEGORY_ORDER = [
    "Features",
    "Performance",
    "Bug Fixes",
    "Refactoring",
    "Documentation",
    "Other",
]

VERSION_FILES = [
    "pyproject.toml",
    "src/niamoto/__version__.py",
    "docs/conf.py",
    "src-tauri/tauri.conf.json",
    "src-tauri/Cargo.toml",
    ".bumpversion.cfg",
    "CHANGELOG.md",
]

HELP_CONTENT_FILES = [
    "src/niamoto/gui/help_content/manifest.json",
    "src/niamoto/gui/help_content/search-index.json",
]

LOCKFILES = [
    "uv.lock",
    "src-tauri/Cargo.lock",
]

RELEASE_METADATA_FILES = [
    ".marketing/plugins.json",
]

RELEASE_COMMIT_FILES = [
    *VERSION_FILES,
    *HELP_CONTENT_FILES,
    *LOCKFILES,
    *RELEASE_METADATA_FILES,
]

WORKFLOW_SPECS = [
    ("build-binaries.yml", "push"),
    ("publish-pypi.yml", "release"),
    ("build-tauri.yml", "release"),
]


class ReleaseError(RuntimeError):
    """Raised when the release cannot continue safely."""


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    subject: str
    body: str
    category: str
    cleaned_subject: str
    commit_type: str | None
    is_breaking: bool
    is_feature: bool


@dataclass(frozen=True)
class ReleaseState:
    current_version: str
    last_tag: str | None
    branch: str
    dirty_paths: tuple[str, ...]
    commits: tuple[CommitInfo, ...]
    suggested_bump: str | None
    suggested_version: str | None


def run_command(
    args: list[str],
    *,
    cwd: Path = ROOT_DIR,
    capture_output: bool = False,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=capture_output,
        check=check,
        env=env,
    )


def git_output(*args: str, check: bool = True) -> str:
    result = run_command(["git", *args], capture_output=True, check=check)
    return result.stdout.strip()


def read_current_version() -> str:
    content = BUMPVERSION_PATH.read_text(encoding="utf-8")
    match = CURRENT_VERSION_RE.search(content)
    if not match:
        raise ReleaseError("Could not read current_version from .bumpversion.cfg")
    return match.group("version")


def parse_version(version: str) -> tuple[int, int, int]:
    if not SEMVER_RE.fullmatch(version):
        raise ReleaseError(f"Invalid version '{version}'. Expected X.Y.Z")
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


def increment_version(version: str, bump: str) -> str:
    major, minor, patch = parse_version(version)
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ReleaseError(f"Unsupported bump type '{bump}'")


def clean_commit_subject(subject: str) -> str:
    match = CONVENTIONAL_RE.match(subject)
    cleaned = match.group("summary") if match else subject
    cleaned = cleaned.strip()
    if not cleaned:
        return subject.strip()
    return cleaned[0].upper() + cleaned[1:]


def categorize_commit(subject: str) -> tuple[str, str | None, bool, bool]:
    match = CONVENTIONAL_RE.match(subject)
    if not match:
        return "Other", None, False, False

    commit_type = match.group("type")
    is_breaking = bool(match.group("breaking"))
    category_map = {
        "feat": "Features",
        "perf": "Performance",
        "fix": "Bug Fixes",
        "refactor": "Refactoring",
        "docs": "Documentation",
    }
    return (
        category_map.get(commit_type, "Other"),
        commit_type,
        is_breaking,
        commit_type == "feat",
    )


def should_skip_commit(subject: str) -> bool:
    lowered = subject.lower()
    return (
        subject.startswith("Merge ")
        or lowered.startswith("release: v")
        or lowered.startswith("bump version:")
    )


def read_dirty_paths() -> tuple[str, ...]:
    output = git_output("status", "--porcelain")
    if not output:
        return ()
    dirty_paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        dirty_paths.append(line[3:])
    return tuple(dirty_paths)


def read_commits_since(last_tag: str | None) -> tuple[CommitInfo, ...]:
    range_spec = f"{last_tag}..HEAD" if last_tag else "HEAD"
    format_string = "%H%x1f%s%x1f%b%x1e"
    output = git_output(
        "log", range_spec, "--no-merges", f"--pretty=format:{format_string}"
    )
    if not output:
        return ()

    commits: list[CommitInfo] = []
    for record in output.split("\x1e"):
        record = record.rstrip("\n")
        if not record:
            continue
        parts = record.split("\x1f", maxsplit=2)
        if len(parts) == 2:
            sha, subject = parts
            body = ""
        elif len(parts) == 3:
            sha, subject, body = parts
        else:
            raise ReleaseError(f"Unexpected git log record format: {record!r}")
        if should_skip_commit(subject):
            continue
        category, commit_type, is_breaking, is_feature = categorize_commit(subject)
        commits.append(
            CommitInfo(
                sha=sha,
                subject=subject,
                body=body.strip(),
                category=category,
                cleaned_subject=clean_commit_subject(subject),
                commit_type=commit_type,
                is_breaking=is_breaking or "BREAKING CHANGE" in body,
                is_feature=is_feature,
            )
        )
    return tuple(commits)


def suggest_bump(commits: Iterable[CommitInfo]) -> str | None:
    commits = tuple(commits)
    if not commits:
        return None
    if any(commit.is_breaking for commit in commits):
        return "major"
    if any(commit.is_feature for commit in commits):
        return "minor"
    return "patch"


def inspect_release_state() -> ReleaseState:
    current_version = read_current_version()
    last_tag = git_output("describe", "--tags", "--abbrev=0", check=False) or None
    branch = git_output("branch", "--show-current")
    dirty_paths = read_dirty_paths()
    commits = read_commits_since(last_tag)
    suggested_bump = suggest_bump(commits)
    suggested_version = (
        increment_version(current_version, suggested_bump) if suggested_bump else None
    )
    return ReleaseState(
        current_version=current_version,
        last_tag=last_tag,
        branch=branch,
        dirty_paths=dirty_paths,
        commits=commits,
        suggested_bump=suggested_bump,
        suggested_version=suggested_version,
    )


def format_release_state(state: ReleaseState) -> str:
    lines = [
        "Release state",
        f"- Branch: {state.branch}",
        f"- Current version: {state.current_version}",
        f"- Last tag: {state.last_tag or 'none'}",
        f"- Dirty paths: {len(state.dirty_paths)}",
        f"- Commits since last tag: {len(state.commits)}",
        f"- Suggested bump: {state.suggested_bump or 'none'}",
        f"- Suggested version: {state.suggested_version or 'none'}",
    ]
    if state.dirty_paths:
        lines.append("- Dirty details:")
        lines.extend(f"  - {path}" for path in state.dirty_paths)
    if state.commits:
        lines.append("- Commit subjects:")
        lines.extend(f"  - {commit.subject}" for commit in state.commits)
    return "\n".join(lines)


def resolve_target_version(state: ReleaseState, explicit_version: str | None) -> str:
    if explicit_version:
        parse_version(explicit_version)
        if parse_version(explicit_version) <= parse_version(state.current_version):
            raise ReleaseError(
                f"Explicit version {explicit_version} must be greater than {state.current_version}"
            )
        return explicit_version

    if not state.suggested_version:
        raise ReleaseError("No releasable commits found since the last tag")
    return state.suggested_version


def render_changelog_section(
    version: str, commits: Iterable[CommitInfo], released_on: date
) -> str:
    categorized: dict[str, list[str]] = {
        category: [] for category in CHANGELOG_CATEGORY_ORDER
    }
    for commit in commits:
        categorized.setdefault(commit.category, []).append(commit.cleaned_subject)

    lines = [f"## [v{version}] - {released_on.isoformat()}", ""]
    for category in CHANGELOG_CATEGORY_ORDER:
        entries = categorized.get(category) or []
        if not entries:
            continue
        lines.append(f"### {category}")
        lines.append("")
        for entry in entries:
            lines.append(f"- {entry}")
        lines.append("")

    if len(lines) == 2:
        raise ReleaseError("Cannot render release notes without visible commits")

    return "\n".join(lines).rstrip() + "\n"


def insert_changelog_section(
    changelog_text: str, section_text: str, version: str
) -> str:
    version_header = f"## [v{version}]"
    if version_header in changelog_text:
        raise ReleaseError(f"CHANGELOG already contains a section for v{version}")

    marker_with_gap = "## [Unreleased]\n\n"
    if marker_with_gap in changelog_text:
        return changelog_text.replace(
            marker_with_gap,
            f"{marker_with_gap}{section_text}\n",
            1,
        )

    marker = "## [Unreleased]\n"
    if marker in changelog_text:
        return changelog_text.replace(marker, f"{marker}\n{section_text}\n", 1)

    raise ReleaseError("CHANGELOG is missing the [Unreleased] section")


def build_release_notes(
    version: str, previous_tag: str | None, section_text: str
) -> str:
    section_lines = section_text.strip().splitlines()
    body = "\n".join(section_lines[1:]).strip()
    lines = ["## What's Changed", "", body]
    if previous_tag:
        lines.extend(
            [
                "",
                f"**Full Changelog**: https://github.com/niamoto/niamoto/compare/{previous_tag}...v{version}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def ensure_release_prerequisites() -> None:
    required_tools = ["git", "gh", "uv", "pnpm", "cargo"]
    missing = [tool for tool in required_tools if shutil.which(tool) is None]
    if missing:
        raise ReleaseError(f"Missing required tools: {', '.join(missing)}")

    run_command(["gh", "auth", "status"], capture_output=True)


def run_step(description: str, args: list[str], *, cwd: Path = ROOT_DIR) -> None:
    print(f"\n==> {description}")
    print("$", " ".join(shlex.quote(arg) for arg in args))
    run_command(args, cwd=cwd)


def run_preflight_checks() -> None:
    ensure_release_prerequisites()

    run_step("Pytest", ["uv", "run", "pytest", "tests/", "-x", "-q", "--tb=short"])
    run_step("Ruff", ["uvx", "ruff", "check", "src/"])
    run_step("pnpm install", ["pnpm", "install", "--frozen-lockfile"], cwd=UI_DIR)
    run_step("Frontend build", ["pnpm", "run", "build"], cwd=UI_DIR)

    if shutil.which("cargo") is None:
        print("\n==> Cargo audit skipped (cargo not installed)")
    else:
        if shutil.which("cargo-audit") is None:
            run_step(
                "Install cargo-audit", ["cargo", "install", "cargo-audit", "--locked"]
            )
        run_step("Cargo audit", ["cargo", "audit"], cwd=TAURI_DIR)

    if sys.platform == "darwin" and shutil.which("cargo") is not None:
        print("\n==> Local Tauri build")
        print("$", "bash", "build_scripts/build_desktop.sh")
        result = run_command(
            ["bash", "build_scripts/build_desktop.sh"],
            check=False,
        )
        if result.returncode != 0:
            print(
                "Warning: local Tauri build failed. Continuing because CI remains the release gate."
            )


def prepare_release_commit(
    version: str, changelog_text: str, current_version: str
) -> None:
    CHANGELOG_PATH.write_text(changelog_text, encoding="utf-8")

    run_step(
        "Version bump",
        [
            "uv",
            "run",
            "bump2version",
            "--current-version",
            current_version,
            "--new-version",
            version,
            "--no-commit",
            "--no-tag",
            "--allow-dirty",
            "patch",
        ],
    )
    run_step("Refresh uv.lock", ["uv", "lock"])
    run_step(
        "Refresh Cargo.lock",
        ["cargo", "update", "--workspace", "--offline", "--quiet"],
        cwd=TAURI_DIR,
    )
    run_step("Stage release files", ["git", "add", *RELEASE_COMMIT_FILES])
    run_step("Commit release", ["git", "commit", "-m", f"release: v{version}"])
    run_step("Create tag", ["git", "tag", f"v{version}"])


def create_or_update_release(version: str, release_notes: str) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
        handle.write(release_notes)
        notes_path = handle.name

    run_step("Push main", ["git", "push", "origin", "main"])
    run_step("Push release tag", ["git", "push", "origin", f"v{version}"])

    existing_release = run_command(
        ["gh", "release", "view", f"v{version}"],
        capture_output=True,
        check=False,
    )
    if existing_release.returncode == 0:
        run_step(
            "Update existing GitHub release",
            [
                "gh",
                "release",
                "edit",
                f"v{version}",
                "--title",
                f"Niamoto v{version}",
                "--notes-file",
                notes_path,
            ],
        )
        return

    run_step(
        "Create GitHub release",
        [
            "gh",
            "release",
            "create",
            f"v{version}",
            "--verify-tag",
            "--title",
            f"Niamoto v{version}",
            "--notes-file",
            notes_path,
        ],
    )


def collect_workflow_runs(head_sha: str) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for workflow_name, expected_event in WORKFLOW_SPECS:
        result = run_command(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                workflow_name,
                "--limit",
                "10",
                "--json",
                "databaseId,url,status,conclusion,headSha,event,workflowName",
            ],
            capture_output=True,
        )
        runs = json.loads(result.stdout or "[]")
        for run in runs:
            if run.get("headSha") == head_sha and run.get("event") == expected_event:
                matches.append(run)
                break
    return matches


def wait_for_workflow_runs(head_sha: str) -> list[dict[str, str]]:
    deadline = time.time() + 120
    while time.time() < deadline:
        matches = collect_workflow_runs(head_sha)
        if len(matches) == len(WORKFLOW_SPECS):
            return matches
        time.sleep(5)
    return collect_workflow_runs(head_sha)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect or execute the Niamoto release flow. "
            "Run without --yes to inspect and propose a version."
        )
    )
    parser.add_argument("version", nargs="?", help="Explicit release version (X.Y.Z)")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Execute the release after inspection instead of stopping at the summary",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the proposed release plan without mutating files or Git state",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip local preflight checks before preparing the release",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = inspect_release_state()
    print(format_release_state(state))

    if state.branch != "main":
        raise ReleaseError("Release must run from main")
    if state.dirty_paths:
        raise ReleaseError("Working tree must be clean before releasing")

    target_version = resolve_target_version(state, args.version)
    section_text = render_changelog_section(target_version, state.commits, date.today())
    release_notes = build_release_notes(target_version, state.last_tag, section_text)

    print("\nRelease plan")
    print(f"- Target version: {target_version}")
    print(f"- Previous tag: {state.last_tag or 'none'}")
    print("- CHANGELOG section preview:")
    print(section_text.rstrip())

    if args.dry_run:
        print("\nDry-run only. No changes made.")
        return 0

    if not args.yes:
        print("\nNo changes made. Re-run with --yes to execute this release.")
        return 0

    if not args.skip_checks:
        run_preflight_checks()

    changelog_text = CHANGELOG_PATH.read_text(encoding="utf-8")
    updated_changelog = insert_changelog_section(
        changelog_text, section_text, target_version
    )

    prepare_release_commit(target_version, updated_changelog, state.current_version)
    create_or_update_release(target_version, release_notes)

    head_sha = git_output("rev-parse", "HEAD")
    workflow_runs = wait_for_workflow_runs(head_sha)

    print("\nRelease complete")
    print(
        f"- GitHub release: https://github.com/niamoto/niamoto/releases/tag/v{target_version}"
    )
    print(f"- PyPI: https://pypi.org/project/niamoto/{target_version}/")
    if workflow_runs:
        print("- Workflow runs:")
        for run in workflow_runs:
            print(
                f"  - {run['workflowName']}: {run['status']}"
                + (f" ({run['conclusion']})" if run.get("conclusion") else "")
                + f" — {run['url']}"
            )
    else:
        print("- Workflow runs: not detected yet, inspect GitHub Actions manually")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReleaseError as error:
        print(f"Release blocked: {error}", file=sys.stderr)
        raise SystemExit(1) from error
