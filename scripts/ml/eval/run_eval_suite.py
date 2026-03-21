#!/usr/bin/env python
"""Multi-dataset ML detection evaluation suite.

Evaluates ML detection across:
- Tier 1: Production instances (niamoto-nc, niamoto-gb, GUYADIV)
- Tier 1b: GBIF Darwin Core exports (NC, Gabon, institutional)
- Tier 2: Silver representative datasets (7+ files)

Usage:
    uv run python -m scripts.ml.eval.run_eval_suite
    uv run python -m scripts.ml.eval.run_eval_suite --tier 1
    uv run python -m scripts.ml.eval.run_eval_suite --tier gbif
    uv run python -m scripts.ml.eval.run_eval_suite --json results.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.ml.eval.evaluate_instance import (  # noqa: E402
    ComparisonResult,
    evaluate_dataset,
    load_annotations,
    resolve_csv_paths,
)

EVAL_DIR = ROOT / "data" / "eval"
ANNOTATIONS_DIR = EVAL_DIR / "annotations"
RESULTS_DIR = EVAL_DIR / "results"
ACCEPTANCE_DIR = EVAL_DIR / "acceptance"


# ── Dataset registry ──────────────────────────────────────────────────────


@dataclass
class DatasetDef:
    name: str
    tier: str
    annotations: Path
    data_dir: Path | None = None
    csv_path: Path | None = None
    suite: str | None = None


# Tier 1 — Production instances
TIER1 = [
    DatasetDef(
        name="niamoto-nc",
        tier="tier1",
        annotations=ANNOTATIONS_DIR / "niamoto-nc.yml",
        data_dir=ROOT / "test-instance" / "niamoto-nc" / "imports",
    ),
    DatasetDef(
        name="niamoto-gb",
        tier="tier1",
        annotations=ANNOTATIONS_DIR / "niamoto-gb.yml",
        data_dir=ROOT / "test-instance" / "niamoto-gb" / "imports",
    ),
    DatasetDef(
        name="guyadiv",
        tier="tier1",
        annotations=ANNOTATIONS_DIR / "guyadiv.yml",
        data_dir=ROOT / "data" / "silver" / "guyane",
    ),
]

# Tier 1b — GBIF Darwin Core
GBIF_ANN = ANNOTATIONS_DIR / "gbif_darwin_core.yml"
TIER_GBIF = [
    DatasetDef(
        name="gbif-nc",
        tier="gbif",
        annotations=GBIF_ANN,
        csv_path=ROOT
        / "data"
        / "silver"
        / "gbif_targeted"
        / "new_caledonia"
        / "occurrences.csv",
    ),
    DatasetDef(
        name="gbif-gabon",
        tier="gbif",
        annotations=GBIF_ANN,
        csv_path=ROOT
        / "data"
        / "silver"
        / "gbif_targeted"
        / "gabon"
        / "occurrences.csv",
    ),
    DatasetDef(
        name="gbif-inst-gabon",
        tier="gbif",
        annotations=GBIF_ANN,
        csv_path=ROOT
        / "data"
        / "silver"
        / "gbif_targeted_institutional"
        / "gabon"
        / "occurrences.csv",
    ),
]

# Tier 2 — Silver
TIER2 = [
    DatasetDef(
        name="silver",
        tier="tier2",
        annotations=ANNOTATIONS_DIR / "silver.yml",
        data_dir=ROOT / "data" / "silver",
    ),
]


def load_acceptance_manifest(path: Path) -> list[DatasetDef]:
    if not path.exists():
        return []

    with open(path) as f:
        payload = yaml.safe_load(f) or {}

    datasets: list[DatasetDef] = []
    for item in payload.get("datasets", []):
        annotations = ROOT / item["annotations"]
        data_dir = ROOT / item["data_dir"] if item.get("data_dir") else None
        csv_path = ROOT / item["csv_path"] if item.get("csv_path") else None
        datasets.append(
            DatasetDef(
                name=item["name"],
                tier=item.get("tier", "acceptance"),
                suite=item.get("suite"),
                annotations=annotations,
                data_dir=data_dir,
                csv_path=csv_path,
            )
        )
    return datasets


TIER_ACCEPTANCE = load_acceptance_manifest(ACCEPTANCE_DIR / "manifest.yml")


# ── Evaluation ────────────────────────────────────────────────────────────


@dataclass
class DatasetResult:
    name: str
    tier: str
    results: list[ComparisonResult]
    metrics: dict
    duration_s: float


def evaluate_one(ds: DatasetDef) -> DatasetResult | None:
    if not ds.annotations.exists():
        print(f"  SKIP {ds.name}: annotations not found")
        return None

    annotations_by_file, is_gbif = load_annotations(ds.annotations)

    csv_gt_pairs = resolve_csv_paths(
        annotations_by_file,
        csv_override=ds.csv_path,
        data_dir=ds.data_dir,
        annotations_path=ds.annotations,
        is_gbif=is_gbif,
    )

    if not csv_gt_pairs:
        print(f"  SKIP {ds.name}: no CSV files matched")
        return None

    t0 = time.monotonic()
    results, metrics = evaluate_dataset(
        csv_gt_pairs, use_ml=True, dataset_name=ds.name, quiet=True
    )
    duration = time.monotonic() - t0

    return DatasetResult(
        name=ds.name,
        tier=ds.tier,
        results=results,
        metrics=metrics,
        duration_s=round(duration, 1),
    )


# ── Cross-dataset analysis ───────────────────────────────────────────────


def analyze_patterns(all_results: list[DatasetResult]) -> dict:
    confusion: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "datasets": set()}
    )
    column_track: dict[str, dict[str, set]] = defaultdict(
        lambda: {"correct": set(), "failed": set()}
    )
    concept_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "correct": 0}
    )

    for ds in all_results:
        for r in ds.results:
            expected = r.expected_concept or r.expected_role
            detected = r.detected_concept or r.detected_role
            concept_stats[expected]["total"] += 1

            if r.concept_match:
                concept_stats[expected]["correct"] += 1
                column_track[r.column]["correct"].add(ds.name)
            else:
                confusion[(expected, detected)]["count"] += 1
                confusion[(expected, detected)]["datasets"].add(ds.name)
                column_track[r.column]["failed"].add(ds.name)

    top_confusions = sorted(
        confusion.items(), key=lambda x: x[1]["count"], reverse=True
    )

    systematic_failures = [
        {"column": col, "failed_in": sorted(t["failed"])}
        for col, t in column_track.items()
        if t["failed"] and not t["correct"]
    ]
    systematic_failures.sort(key=lambda x: len(x["failed_in"]), reverse=True)

    concept_ranking = []
    for concept, stats in concept_stats.items():
        pct = round(100 * stats["correct"] / stats["total"], 1) if stats["total"] else 0
        concept_ranking.append(
            {
                "concept": concept,
                "correct": stats["correct"],
                "total": stats["total"],
                "pct": pct,
            }
        )
    concept_ranking.sort(key=lambda x: x["pct"])

    return {
        "top_confusions": [
            {
                "expected": k[0],
                "detected": k[1],
                "count": v["count"],
                "datasets": sorted(v["datasets"]),
            }
            for k, v in top_confusions[:15]
        ],
        "systematic_failures": systematic_failures[:10],
        "concept_ranking": concept_ranking,
    }


# ── Reporting ─────────────────────────────────────────────────────────────


def print_suite_report(results: list[DatasetResult], patterns: dict) -> None:
    print(f"\n{'=' * 70}")
    print("  ML Detection Evaluation Suite")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 70}")

    # Per-dataset scores
    print(f"\n{'─' * 60}")
    print(f"  {'Dataset':<30} {'Cols':>5} {'Role%':>7} {'Concept%':>9} {'Time':>6}")
    print(f"  {'─' * 56}")

    tier_labels = {
        "tier1": "Tier 1 — Production",
        "gbif": "Tier 1b — GBIF Darwin Core",
        "tier2": "Tier 2 — Silver",
        "acceptance": "Acceptance — Frozen benchmark",
    }
    current_tier = ""
    for ds in results:
        m = ds.metrics
        if ds.tier != current_tier:
            print(f"\n  [{tier_labels.get(ds.tier, ds.tier)}]")
            current_tier = ds.tier
        print(
            f"  {ds.name:<30} {m.get('total', 0):>5} "
            f"{m.get('role_pct', 0):>6.1f}% {m.get('concept_pct', 0):>8.1f}% "
            f"{ds.duration_s:>5.1f}s"
        )

    # Aggregated totals
    all_total = sum(ds.metrics.get("total", 0) for ds in results)
    all_role = sum(ds.metrics.get("role_correct", 0) for ds in results)
    all_concept = sum(ds.metrics.get("concept_correct", 0) for ds in results)
    total_time = sum(ds.duration_s for ds in results)

    if all_total:
        print(f"\n  {'─' * 56}")
        print(
            f"  {'TOTAL':<30} {all_total:>5} "
            f"{100 * all_role / all_total:>6.1f}% {100 * all_concept / all_total:>8.1f}% "
            f"{total_time:>5.1f}s"
        )

    # Top confusions
    confusions = patterns.get("top_confusions", [])
    if confusions:
        print(f"\n{'=' * 70}")
        print("  Top confusions (expected → detected)")
        print(f"{'─' * 70}")
        for c in confusions[:10]:
            ds_str = ", ".join(c["datasets"])
            print(
                f"  {c['expected']:<28} → {c['detected']:<22} "
                f": {c['count']:>2}x ({ds_str})"
            )

    # Systematically failed columns
    failures = patterns.get("systematic_failures", [])
    if failures:
        print(f"\n{'=' * 70}")
        print("  Columns systematically mis-classified")
        print(f"{'─' * 70}")
        for f in failures[:10]:
            ds_str = ", ".join(f["failed_in"])
            print(f"  {f['column']:<25} : 0/{len(f['failed_in'])} datasets ({ds_str})")

    # Weakest concepts
    concept_ranking = patterns.get("concept_ranking", [])
    worst = [c for c in concept_ranking if c["total"] >= 2 and c["pct"] < 80]
    if worst:
        print(f"\n{'=' * 70}")
        print("  Weakest concepts (< 80% accuracy, >= 2 occurrences)")
        print(f"{'─' * 70}")
        for c in worst[:10]:
            print(f"  {c['concept']:<30} : {c['correct']}/{c['total']} ({c['pct']}%)")

    print()


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="ML detection evaluation suite")
    parser.add_argument(
        "--tier",
        choices=["1", "gbif", "2", "acceptance", "all"],
        default="all",
        help="Which tier(s) to evaluate (default: all)",
    )
    parser.add_argument("--json", type=Path, help="Export results to JSON")
    args = parser.parse_args()

    datasets: list[DatasetDef] = []
    if args.tier in ("1", "all"):
        datasets.extend(TIER1)
    if args.tier in ("gbif", "all"):
        datasets.extend(TIER_GBIF)
    if args.tier in ("2", "all"):
        datasets.extend(TIER2)
    if args.tier in ("acceptance", "all"):
        datasets.extend(TIER_ACCEPTANCE)

    print(f"ML Detection Evaluation Suite — {len(datasets)} dataset(s)")
    print(f"{'─' * 50}")

    t_start = time.monotonic()
    dataset_results: list[DatasetResult] = []

    for ds in datasets:
        print(f"\n  Evaluating: {ds.name} ...", end="", flush=True)
        result = evaluate_one(ds)
        if result:
            dataset_results.append(result)
            m = result.metrics
            print(
                f" {m.get('concept_pct', 0):.1f}% concept "
                f"({m.get('total', 0)} cols, {result.duration_s}s)"
            )
        else:
            print(" SKIPPED")

    total_time = time.monotonic() - t_start

    if not dataset_results:
        print("\nNo datasets evaluated.")
        return

    patterns = analyze_patterns(dataset_results)
    print_suite_report(dataset_results, patterns)
    print(f"Total evaluation time: {total_time:.1f}s")

    # JSON export
    json_path = args.json
    if json_path is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        json_path = RESULTS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    if not json_path.is_absolute():
        json_path = ROOT / json_path
    json_path.parent.mkdir(parents=True, exist_ok=True)

    export = {
        "date": datetime.now().isoformat(),
        "duration_s": round(total_time, 1),
        "datasets": [
            {
                "name": ds.name,
                "tier": ds.tier,
                "metrics": {k: v for k, v in ds.metrics.items() if k != "errors"},
                "errors": ds.metrics.get("errors", []),
                "duration_s": ds.duration_s,
            }
            for ds in dataset_results
        ],
        "patterns": patterns,
    }
    with open(json_path, "w") as f:
        json.dump(export, f, indent=2)
    print(f"Results saved to {json_path}")


if __name__ == "__main__":
    main()
