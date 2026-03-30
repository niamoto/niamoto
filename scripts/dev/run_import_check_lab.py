#!/usr/bin/env python3
"""Run a regression matrix for pre-import impact-check lab scenarios.

Usage:
    uv run python scripts/dev/run_import_check_lab.py
    uv run python scripts/dev/run_import_check_lab.py --instance test-instance/niamoto-subset
    uv run python scripts/dev/run_import_check_lab.py --only plot_stats_missing_id
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from niamoto.core.services.compatibility import CompatibilityService


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    summary: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run import-check regression scenarios against an instance lab."
    )
    parser.add_argument(
        "--instance",
        default="test-instance/niamoto-subset",
        help="Instance root relative to repo root or absolute path.",
    )
    parser.add_argument(
        "--lab",
        default=None,
        help="Lab directory relative to the instance root. Defaults to import-check-lab.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Manifest YAML path. Defaults to <lab>/expectations.yml.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Run only matching case id(s). Can be passed multiple times.",
    )
    return parser.parse_args()


def resolve_path(raw: str | None, *, base: Path) -> Path | None:
    if raw is None:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def load_manifest(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Manifest must be a mapping: {path}")
    if not isinstance(data.get("cases"), list):
        raise ValueError(f"Manifest must contain a 'cases' list: {path}")
    return data


def impact_pairs(report) -> list[tuple[str, str]]:
    return sorted((item.level.value, item.column) for item in report.impacts)


def evaluate_expectation(report: Any, expect: dict[str, Any]) -> list[str]:
    actual_pairs = impact_pairs(report)
    expected_pairs = sorted(
        (str(item["level"]), str(item["column"])) for item in expect.get("impacts", [])
    )

    failures: list[str] = []

    if "matched_columns" in expect:
        expected_matched = int(expect["matched_columns"])
        if len(report.matched_columns) != expected_matched:
            failures.append(
                f"matched={len(report.matched_columns)} expected={expected_matched}"
            )

    if actual_pairs != expected_pairs:
        failures.append(f"impacts={actual_pairs} expected={expected_pairs}")

    expected_error = expect.get("error")
    actual_error = report.error
    if expected_error is None:
        if actual_error is not None:
            failures.append(f"error={actual_error!r} expected=None")
    elif actual_error != expected_error:
        failures.append(f"error={actual_error!r} expected={expected_error!r}")

    expected_info = expect.get("info_message_contains")
    actual_info = report.info_message
    if expected_info is None:
        if actual_info is not None:
            failures.append(f"info={actual_info!r} expected=None")
    elif not actual_info or str(expected_info) not in actual_info:
        failures.append(f"info={actual_info!r} expected_contains={expected_info!r}")

    expected_skip = expect.get("skipped_reason_contains")
    actual_skip = report.skipped_reason
    if expected_skip is None:
        if actual_skip is not None:
            failures.append(f"skip={actual_skip!r} expected=None")
    elif not actual_skip or str(expected_skip) not in actual_skip:
        failures.append(f"skip={actual_skip!r} expected_contains={expected_skip!r}")

    return failures


def evaluate_case(service: CompatibilityService, case: dict[str, Any]) -> CaseResult:
    case_id = str(case["id"])
    entity = str(case["entity"])
    file_path = str(case["file"])

    report = service.check_compatibility(entity, file_path)
    expectations = case.get("expect_any")
    if expectations is None:
        expectations = [case.get("expect", {}) or {}]

    failure_sets = [
        evaluate_expectation(report, expect or {}) for expect in expectations
    ]
    if any(not failures for failures in failure_sets):
        note = case.get("note")
        if note:
            return CaseResult(case_id=case_id, passed=True, summary=f"ok ({note})")
        return CaseResult(case_id=case_id, passed=True, summary="ok")

    flattened = " || ".join(" | ".join(failures) for failures in failure_sets)
    return CaseResult(case_id=case_id, passed=False, summary=flattened)


def main() -> int:
    from niamoto.core.services.compatibility import CompatibilityService

    args = parse_args()

    instance = resolve_path(args.instance, base=REPO_ROOT)
    if instance is None or not instance.exists():
        print(f"Instance not found: {args.instance}", file=sys.stderr)
        return 2

    lab = (
        resolve_path(args.lab, base=instance)
        if args.lab
        else (instance / "import-check-lab").resolve()
    )
    manifest = (
        resolve_path(args.manifest, base=REPO_ROOT)
        if args.manifest
        else (lab / "expectations.yml").resolve()
    )

    if manifest is None or not manifest.exists():
        print(f"Manifest not found: {manifest}", file=sys.stderr)
        return 2

    data = load_manifest(manifest)
    cases = data["cases"]
    if args.only:
        wanted = set(args.only)
        cases = [case for case in cases if str(case["id"]) in wanted]

    if not cases:
        print("No cases selected.")
        return 1

    service = CompatibilityService(instance)
    results = [evaluate_case(service, case) for case in cases]

    print(f"\nImport-check lab: {manifest}\n")
    width = max(len(result.case_id) for result in results)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status:<4}  {result.case_id:<{width}}  {result.summary}")

    failed = [result for result in results if not result.passed]
    print(f"\nSummary: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
