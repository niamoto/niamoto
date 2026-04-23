"""Build a reproducible test inventory for the current repository."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_SOURCE_ROOT = REPO_ROOT / "src" / "niamoto"
PYTHON_TEST_ROOT = REPO_ROOT / "tests"
FRONTEND_SOURCE_ROOT = REPO_ROOT / "src" / "niamoto" / "gui" / "ui" / "src"
DEFAULT_COVERAGE_XML = REPO_ROOT / "coverage.xml"
DEFAULT_FRONTEND_COVERAGE = (
    REPO_ROOT / "src" / "niamoto" / "gui" / "ui" / "coverage" / "coverage-summary.json"
)

IGNORED_PARTS = {
    "__pycache__",
    "node_modules",
    ".pnpm",
    ".ignored",
    "dist",
    "coverage",
    "htmlcov",
}
IGNORED_FRONTEND_SUFFIXES = {".generated.ts", ".generated.tsx"}
PYTHON_RISK_PREFIXES = (
    ("src/niamoto/core/plugins/deployers/", 6),
    ("src/niamoto/gui/api/routers/", 6),
    ("src/niamoto/gui/api/services/", 5),
    ("src/niamoto/gui/api/utils/", 5),
    ("src/niamoto/core/imports/", 5),
    ("src/niamoto/common/", 4),
    ("src/niamoto/cli/commands/", 4),
)
FRONTEND_RISK_RULES = (
    ("/hooks/", 6),
    ("/shared/lib/api/", 6),
    ("/shared/hooks/", 5),
    ("/context/", 5),
    ("/routing.ts", 5),
    ("/lib/", 4),
    ("/views/", 3),
    ("/components/", 2),
)


@dataclass(slots=True, frozen=True)
class ArtifactStatus:
    status: str
    message: str
    line_rate: float | None = None
    matched_files: int = 0
    total_files: int = 0


@dataclass(slots=True, frozen=True)
class DomainSummary:
    name: str
    source_files: int
    direct_test_files: int
    line_rate: float | None = None


@dataclass(slots=True, frozen=True)
class GapEntry:
    path: str
    area: str
    line_count: int
    related_tests: tuple[str, ...]
    risk_score: int


@dataclass(slots=True, frozen=True)
class InventoryReport:
    python_sources: tuple[str, ...]
    python_tests: tuple[str, ...]
    frontend_sources: tuple[str, ...]
    frontend_tests: tuple[str, ...]
    python_coverage: ArtifactStatus
    frontend_coverage: ArtifactStatus
    python_domains: tuple[DomainSummary, ...]
    frontend_areas: tuple[DomainSummary, ...]
    top_python_gaps: tuple[GapEntry, ...]
    top_frontend_gaps: tuple[GapEntry, ...]

    def to_markdown(self) -> str:
        lines = [
            "# Testing Audit",
            "",
            "This report inventories the current automated test surface for the repository.",
            "",
            "## Coverage Artifacts",
            "",
            f"- Python coverage: **{self.python_coverage.status}** — {self.python_coverage.message}",
            f"- Frontend coverage: **{self.frontend_coverage.status}** — {self.frontend_coverage.message}",
            "",
            "## Snapshot",
            "",
            f"- Python source files tracked: **{len(self.python_sources)}**",
            f"- Python test files tracked: **{len(self.python_tests)}**",
            f"- Frontend source files tracked: **{len(self.frontend_sources)}**",
            f"- Frontend test files tracked: **{len(self.frontend_tests)}**",
            "",
            "## Python Domain Summary",
            "",
            "| Area | Source files | Files with direct tests | Direct-test density | Coverage line rate |",
            "|------|--------------|-------------------------|---------------------|--------------------|",
        ]

        for summary in self.python_domains:
            density = _format_ratio(summary.direct_test_files, summary.source_files)
            coverage = _format_percent(summary.line_rate)
            lines.append(
                f"| `{summary.name}` | {summary.source_files} | "
                f"{summary.direct_test_files} | {density} | {coverage} |"
            )

        lines.extend(
            [
                "",
                "## Highest-ROI Python Gaps",
                "",
            ]
        )

        if not self.top_python_gaps:
            lines.append("- None detected.")
        else:
            for gap in self.top_python_gaps:
                tests = ", ".join(f"`{test}`" for test in gap.related_tests) or "none"
                lines.append(
                    f"- `{gap.path}` ({gap.line_count} lines, area `{gap.area}`, related tests: {tests})"
                )

        lines.extend(
            [
                "",
                "## Frontend Area Summary",
                "",
                "| Area | Source files | Test files | Test-file density |",
                "|------|--------------|------------|-------------------|",
            ]
        )

        for summary in self.frontend_areas:
            density = _format_ratio(summary.direct_test_files, summary.source_files)
            lines.append(
                f"| `{summary.name}` | {summary.source_files} | "
                f"{summary.direct_test_files} | {density} |"
            )

        lines.extend(
            [
                "",
                "## Highest-ROI Frontend Gaps",
                "",
            ]
        )

        if not self.top_frontend_gaps:
            lines.append("- None detected.")
        else:
            for gap in self.top_frontend_gaps:
                tests = ", ".join(f"`{test}`" for test in gap.related_tests) or "none"
                lines.append(
                    f"- `{gap.path}` ({gap.line_count} lines, area `{gap.area}`, sibling tests: {tests})"
                )

        lines.extend(
            [
                "",
                "## Recommended First Pass",
                "",
                "1. Add direct tests for backend deploy adapters, shared helpers, and uncovered GUI API routes.",
                "2. Extend the import-suggestion suite into uncovered decision seams before refactoring heuristics.",
                "3. Add Vitest coverage and first-pass tests for frontend hooks, API normalization helpers, and runtime-dependent state flows.",
            ]
        )

        return "\n".join(lines) + "\n"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _format_ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{(numerator / denominator) * 100:.1f}%"


def _is_ignored_path(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def _iter_python_sources(repo_root: Path) -> list[Path]:
    source_root = repo_root / "src" / "niamoto"
    if not source_root.exists():
        return []

    files = []
    for path in source_root.rglob("*.py"):
        if _is_ignored_path(path.relative_to(repo_root)):
            continue
        if path.name == "__init__.py":
            continue
        files.append(path)
    return sorted(files)


def _iter_python_tests(repo_root: Path) -> list[Path]:
    test_root = repo_root / "tests"
    if not test_root.exists():
        return []

    files = []
    for path in test_root.rglob("test_*.py"):
        if _is_ignored_path(path.relative_to(repo_root)):
            continue
        files.append(path)
    return sorted(files)


def _is_frontend_source_file(path: Path, repo_root: Path) -> bool:
    rel = path.relative_to(repo_root)
    if _is_ignored_path(rel):
        return False
    if path.name.endswith(".test.ts") or path.name.endswith(".test.tsx"):
        return False
    if path.name.endswith(".d.ts"):
        return False
    return not any(path.name.endswith(suffix) for suffix in IGNORED_FRONTEND_SUFFIXES)


def _iter_frontend_sources(repo_root: Path) -> list[Path]:
    source_root = repo_root / "src" / "niamoto" / "gui" / "ui" / "src"
    if not source_root.exists():
        return []

    files = []
    for pattern in ("*.ts", "*.tsx"):
        for path in source_root.rglob(pattern):
            if _is_frontend_source_file(path, repo_root):
                files.append(path)
    return sorted(set(files))


def _iter_frontend_tests(repo_root: Path) -> list[Path]:
    source_root = repo_root / "src" / "niamoto" / "gui" / "ui" / "src"
    if not source_root.exists():
        return []

    files = []
    for pattern in ("*.test.ts", "*.test.tsx"):
        for path in source_root.rglob(pattern):
            if not _is_ignored_path(path.relative_to(repo_root)):
                files.append(path)
    return sorted(set(files))


def _relative(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _python_area(rel_path: str) -> str:
    path = Path(rel_path)
    try:
        idx = path.parts.index("niamoto")
    except ValueError:
        return path.parts[0]

    tail = path.parts[idx + 1 :]
    if not tail:
        return rel_path

    if len(tail) == 1:
        return "root"

    if tail[0] in {"cli", "common"}:
        if len(tail) > 1 and tail[1] in {"commands", "utils"}:
            return f"{tail[0]}/{tail[1]}"
        return tail[0]

    if tail[0] == "core":
        if (
            len(tail) > 2
            and tail[1] == "plugins"
            and tail[2]
            in {
                "deployers",
                "loaders",
                "transformers",
                "widgets",
            }
        ):
            return f"{tail[0]}/{tail[1]}/{tail[2]}"
        if len(tail) > 1 and tail[1] in {"imports", "plugins", "services", "utils"}:
            return f"{tail[0]}/{tail[1]}"
        return tail[0]

    if tail[0] == "gui":
        if (
            len(tail) > 2
            and tail[1] == "api"
            and tail[2]
            in {
                "routers",
                "services",
                "utils",
            }
        ):
            return f"{tail[0]}/{tail[1]}/{tail[2]}"
        if len(tail) > 1 and tail[1] in {"ui", "help_content"}:
            return f"{tail[0]}/{tail[1]}"
        return "gui"

    return tail[0]


def _frontend_area(rel_path: str) -> str:
    path = Path(rel_path)
    parts = path.parts
    if "features" in parts:
        index = parts.index("features")
        if index + 1 < len(parts):
            return parts[index + 1]
    if "shared" in parts:
        return "shared"
    if "components" in parts:
        return "components"
    if "app" in parts:
        return "app"
    return "other"


def _normalize_test_stem(path: Path) -> str:
    stem = path.stem
    if stem.startswith("test_"):
        stem = stem[5:]
    return stem


def _python_related_tests(
    source: Path, test_files: Iterable[Path], repo_root: Path
) -> tuple[str, ...]:
    source_stem = source.stem
    matches: list[str] = []
    for test_file in test_files:
        test_stem = _normalize_test_stem(test_file)
        if (
            test_stem == source_stem
            or test_stem.startswith(source_stem + "_")
            or source_stem.startswith(test_stem + "_")
        ):
            matches.append(_relative(test_file, repo_root))
    return tuple(sorted(set(matches)))


def _frontend_sibling_tests(source: Path, repo_root: Path) -> tuple[str, ...]:
    candidates = [
        source.with_name(f"{source.stem}.test.ts"),
        source.with_name(f"{source.stem}.test.tsx"),
    ]
    matches = [
        _relative(candidate, repo_root)
        for candidate in candidates
        if candidate.exists() and not _is_ignored_path(candidate.relative_to(repo_root))
    ]
    return tuple(sorted(matches))


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open(encoding="utf-8"))


def _risk_score(rel_path: str, rules: tuple[tuple[str, int], ...]) -> int:
    for needle, score in rules:
        if needle in rel_path:
            return score
    return 1


def _summarize_python_domains(
    python_sources: list[Path],
    python_tests: list[Path],
    repo_root: Path,
    coverage_rates: dict[str, float],
) -> tuple[DomainSummary, ...]:
    counts: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"source_files": 0, "direct_test_files": 0}
    )

    for source in python_sources:
        rel = _relative(source, repo_root)
        area = _python_area(rel)
        counts[area]["source_files"] += 1
        if _python_related_tests(source, python_tests, repo_root):
            counts[area]["direct_test_files"] += 1

    summaries = []
    for area, values in counts.items():
        summaries.append(
            DomainSummary(
                name=area,
                source_files=int(values["source_files"]),
                direct_test_files=int(values["direct_test_files"]),
                line_rate=coverage_rates.get(area),
            )
        )
    return tuple(sorted(summaries, key=lambda summary: summary.name))


def _summarize_frontend_areas(
    frontend_sources: list[Path],
    frontend_tests: list[Path],
    repo_root: Path,
) -> tuple[DomainSummary, ...]:
    source_counts: Counter[str] = Counter()
    test_counts: Counter[str] = Counter()

    for source in frontend_sources:
        source_counts[_frontend_area(_relative(source, repo_root))] += 1

    for test_file in frontend_tests:
        test_counts[_frontend_area(_relative(test_file, repo_root))] += 1

    areas = sorted(set(source_counts) | set(test_counts))
    return tuple(
        DomainSummary(
            name=area,
            source_files=source_counts.get(area, 0),
            direct_test_files=test_counts.get(area, 0),
        )
        for area in areas
    )


def _top_python_gaps(
    python_sources: list[Path],
    python_tests: list[Path],
    repo_root: Path,
    limit: int = 10,
) -> tuple[GapEntry, ...]:
    gaps = []
    for source in python_sources:
        related_tests = _python_related_tests(source, python_tests, repo_root)
        if related_tests:
            continue
        rel = _relative(source, repo_root)
        gaps.append(
            GapEntry(
                path=rel,
                area=_python_area(rel),
                line_count=_line_count(source),
                related_tests=related_tests,
                risk_score=_risk_score(rel, PYTHON_RISK_PREFIXES),
            )
        )

    gaps.sort(key=lambda gap: (-gap.risk_score, -gap.line_count, gap.path))
    return tuple(gaps[:limit])


def _top_frontend_gaps(
    frontend_sources: list[Path], repo_root: Path, limit: int = 10
) -> tuple[GapEntry, ...]:
    gaps = []
    for source in frontend_sources:
        sibling_tests = _frontend_sibling_tests(source, repo_root)
        if sibling_tests:
            continue
        rel = _relative(source, repo_root)
        gaps.append(
            GapEntry(
                path=rel,
                area=_frontend_area(rel),
                line_count=_line_count(source),
                related_tests=sibling_tests,
                risk_score=_risk_score(rel, FRONTEND_RISK_RULES),
            )
        )

    gaps.sort(key=lambda gap: (-gap.risk_score, -gap.line_count, gap.path))
    return tuple(gaps[:limit])


def _artifact_from_frontend_coverage(frontend_coverage_path: Path) -> ArtifactStatus:
    if not frontend_coverage_path.exists():
        return ArtifactStatus(
            status="missing",
            message="Vitest coverage summary was not found.",
        )

    try:
        data = json.loads(frontend_coverage_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid frontend coverage summary: {exc}") from exc

    total = data.get("total", {})
    lines = total.get("lines", {})
    pct = lines.get("pct")
    if pct is None:
        raise ValueError("Frontend coverage summary is missing total.lines.pct")

    return ArtifactStatus(
        status="available",
        message=f"Vitest coverage summary found at `{frontend_coverage_path}`.",
        line_rate=float(pct) / 100,
    )


def _artifact_from_python_coverage(
    repo_root: Path, coverage_xml_path: Path
) -> tuple[ArtifactStatus, dict[str, float]]:
    if not coverage_xml_path.exists():
        return (
            ArtifactStatus(
                status="missing",
                message="coverage.xml was not found.",
            ),
            {},
        )

    try:
        root = ElementTree.parse(coverage_xml_path).getroot()
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid coverage xml: {exc}") from exc

    domain_hits: Counter[str] = Counter()
    domain_lines: Counter[str] = Counter()
    matched_files = 0
    total_files = 0

    for class_node in root.findall(".//class"):
        filename = class_node.attrib.get("filename")
        if not filename:
            continue

        total_files += 1
        rel = Path(filename)
        current_file = repo_root / rel
        if not current_file.exists():
            continue

        matched_files += 1
        area = _python_area(rel.as_posix())
        covered_lines = 0
        total_lines = 0
        for line_node in class_node.findall("./lines/line"):
            total_lines += 1
            if int(line_node.attrib.get("hits", "0")) > 0:
                covered_lines += 1
        domain_hits[area] += covered_lines
        domain_lines[area] += total_lines

    if total_files == 0:
        return (
            ArtifactStatus(
                status="invalid",
                message="coverage.xml did not contain any file entries.",
            ),
            {},
        )

    coverage_rates = {
        area: domain_hits[area] / domain_lines[area]
        for area in domain_lines
        if domain_lines[area]
    }
    matched_ratio = matched_files / total_files
    if matched_files == 0:
        status = ArtifactStatus(
            status="stale",
            message="coverage.xml does not match any current source files in this repository.",
            matched_files=matched_files,
            total_files=total_files,
        )
        return status, coverage_rates

    overall_covered = sum(domain_hits.values())
    overall_lines = sum(domain_lines.values())
    line_rate = overall_covered / overall_lines if overall_lines else None
    if matched_ratio < 0.9:
        status = ArtifactStatus(
            status="stale",
            message=(
                "coverage.xml only matches "
                f"{matched_files}/{total_files} tracked files in the current repository."
            ),
            line_rate=line_rate,
            matched_files=matched_files,
            total_files=total_files,
        )
        return status, coverage_rates

    status = ArtifactStatus(
        status="available",
        message=f"coverage.xml matched {matched_files}/{total_files} tracked files.",
        line_rate=line_rate,
        matched_files=matched_files,
        total_files=total_files,
    )
    return status, coverage_rates


def build_inventory(
    repo_root: Path = REPO_ROOT,
    coverage_xml_path: Path = DEFAULT_COVERAGE_XML,
    frontend_coverage_path: Path = DEFAULT_FRONTEND_COVERAGE,
) -> InventoryReport:
    python_sources = _iter_python_sources(repo_root)
    python_tests = _iter_python_tests(repo_root)
    frontend_sources = _iter_frontend_sources(repo_root)
    frontend_tests = _iter_frontend_tests(repo_root)

    python_coverage, coverage_rates = _artifact_from_python_coverage(
        repo_root, coverage_xml_path
    )
    frontend_coverage = _artifact_from_frontend_coverage(frontend_coverage_path)

    return InventoryReport(
        python_sources=tuple(_relative(path, repo_root) for path in python_sources),
        python_tests=tuple(_relative(path, repo_root) for path in python_tests),
        frontend_sources=tuple(_relative(path, repo_root) for path in frontend_sources),
        frontend_tests=tuple(_relative(path, repo_root) for path in frontend_tests),
        python_coverage=python_coverage,
        frontend_coverage=frontend_coverage,
        python_domains=_summarize_python_domains(
            python_sources,
            python_tests,
            repo_root,
            coverage_rates,
        ),
        frontend_areas=_summarize_frontend_areas(
            frontend_sources,
            frontend_tests,
            repo_root,
        ),
        top_python_gaps=_top_python_gaps(python_sources, python_tests, repo_root),
        top_frontend_gaps=_top_frontend_gaps(frontend_sources, repo_root),
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a reproducible test inventory for the repository."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root to inventory.",
    )
    parser.add_argument(
        "--coverage-xml",
        type=Path,
        default=DEFAULT_COVERAGE_XML,
        help="Path to coverage.xml.",
    )
    parser.add_argument(
        "--frontend-coverage-summary",
        type=Path,
        default=DEFAULT_FRONTEND_COVERAGE,
        help="Path to Vitest coverage-summary.json.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path to write the Markdown report to disk.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = build_inventory(
            repo_root=args.repo_root,
            coverage_xml_path=args.coverage_xml,
            frontend_coverage_path=args.frontend_coverage_summary,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    markdown = report.to_markdown()
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
