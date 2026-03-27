#!/usr/bin/env python3
"""
Benchmark transform and export commands on a staged Niamoto instance.

The benchmark copies an instance into a temporary workspace, then measures:
  - `niamoto transform run`
  - `niamoto export --target web_pages`

Only command execution time is measured. Instance staging is excluded so the
reported durations are easier to compare before and after implementation work.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INSTANCE = REPO_ROOT / "test-instance" / "niamoto-subset"


@dataclass
class StepResult:
    ok: bool
    duration_s: float
    returncode: int
    log_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark Niamoto transform and export commands"
    )
    parser.add_argument(
        "--instance",
        type=Path,
        default=DEFAULT_INSTANCE,
        help="Path to the source instance to benchmark",
    )
    parser.add_argument(
        "--export-target",
        default="web_pages",
        help="Export target to run for the benchmark",
    )
    parser.add_argument(
        "--export-workers",
        type=int,
        default=1,
        help="Worker count passed to `niamoto export`",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path where the JSON summary will be written",
    )
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Keep the staged temporary workspace after the benchmark",
    )
    return parser.parse_args()


def stage_instance(source_instance: Path) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="niamoto-bench-"))
    staged_instance = temp_root / source_instance.name
    shutil.copytree(source_instance, staged_instance)
    return staged_instance


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    remainder = seconds % 60
    return f"{minutes}m {remainder:.1f}s"


def run_step(name: str, command: list[str], cwd: Path, logs_dir: Path) -> StepResult:
    log_file = logs_dir / f"{name}.log"
    start = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.perf_counter() - start
    log_file.write_text(
        f"$ {' '.join(command)}\n\n"
        f"exit_code={completed.returncode}\n\n"
        f"--- stdout ---\n{completed.stdout}\n"
        f"--- stderr ---\n{completed.stderr}\n",
        encoding="utf-8",
    )
    return StepResult(
        ok=completed.returncode == 0,
        duration_s=duration,
        returncode=completed.returncode,
        log_file=str(log_file),
    )


def remove_previous_exports(instance_dir: Path) -> None:
    export_dir = instance_dir / "exports" / "web"
    if export_dir.exists():
        shutil.rmtree(export_dir)


def build_summary(
    source_instance: Path,
    staged_instance: Path,
    transform_result: StepResult,
    export_result: Optional[StepResult],
) -> dict:
    summary: dict[str, object] = {
        "instance": str(source_instance),
        "staged_instance": str(staged_instance),
        "transform": asdict(transform_result),
    }
    if export_result is not None:
        summary["export"] = asdict(export_result)
    return summary


def print_summary(summary: dict) -> None:
    print("=== Pipeline Benchmark ===")
    print(f"Instance          : {summary['instance']}")
    print(f"Staged workspace  : {summary['staged_instance']}")
    print()

    transform = summary["transform"]
    print("Transform")
    print(f"  Status          : {'ok' if transform['ok'] else 'failed'}")
    print(f"  Duration        : {format_duration(transform['duration_s'])}")
    print(f"  Return code     : {transform['returncode']}")
    print(f"  Log             : {transform['log_file']}")
    print()

    export = summary.get("export")
    if export is not None:
        print("Export")
        print(f"  Status          : {'ok' if export['ok'] else 'failed'}")
        print(f"  Duration        : {format_duration(export['duration_s'])}")
        print(f"  Return code     : {export['returncode']}")
        print(f"  Log             : {export['log_file']}")


def write_json(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_instance = args.instance.resolve()

    if not source_instance.exists():
        print(f"Instance not found: {source_instance}", file=sys.stderr)
        return 1

    staged_instance = stage_instance(source_instance)
    logs_dir = Path(tempfile.mkdtemp(prefix="niamoto-bench-logs-"))

    transform_result: Optional[StepResult] = None
    export_result: Optional[StepResult] = None

    try:
        print(f"Staging instance from {source_instance}...")
        print(f"Workspace: {staged_instance}")
        print()

        transform_result = run_step(
            "transform",
            [sys.executable, "-m", "niamoto", "transform", "run"],
            cwd=staged_instance,
            logs_dir=logs_dir,
        )

        if transform_result.ok:
            remove_previous_exports(staged_instance)
            export_result = run_step(
                "export",
                [
                    sys.executable,
                    "-m",
                    "niamoto",
                    "export",
                    "--target",
                    args.export_target,
                    "--workers",
                    str(args.export_workers),
                ],
                cwd=staged_instance,
                logs_dir=logs_dir,
            )

        summary = build_summary(
            source_instance=source_instance,
            staged_instance=staged_instance,
            transform_result=transform_result,
            export_result=export_result,
        )
        print_summary(summary)

        if args.json_out:
            write_json(args.json_out, summary)
            print()
            print(f"JSON summary written to: {args.json_out}")

        if transform_result.ok and export_result is not None and export_result.ok:
            return 0
        return 1
    finally:
        if not args.keep_workdir:
            shutil.rmtree(staged_instance.parent, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
