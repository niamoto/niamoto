#!/usr/bin/env python
"""Evaluate ML detection quality against ground truth annotations.

Usage:
    # Instance with centralized annotations
    uv run python -m ml.scripts.eval.evaluate_instance \
        --annotations ml/data/eval/annotations/niamoto-nc.yml \
        --data-dir test-instance/niamoto-nc/imports --compare

    # GBIF with specific CSV
    uv run python -m ml.scripts.eval.evaluate_instance \
        --annotations ml/data/eval/annotations/gbif_darwin_core.yml \
        --csv ml/data/silver/gbif_targeted/new_caledonia/occurrences.csv --compare

    # Silver with auto-resolved CSVs
    uv run python -m ml.scripts.eval.evaluate_instance \
        --annotations ml/data/eval/annotations/silver.yml \
        --data-dir ml/data/silver --compare
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
ML_ROOT = ROOT / "ml"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

EVAL_ANNOTATIONS = ML_ROOT / "data" / "eval" / "annotations"
EVAL_RESULTS = ML_ROOT / "data" / "eval" / "results"


# ── Ground truth ──────────────────────────────────────────────────────────


@dataclass
class GroundTruthColumn:
    name: str
    role: str
    concept: str | None = None
    source_file: str = ""


def _parse_annotation(
    col_name: str, concept: str, source_file: str
) -> GroundTruthColumn:
    parts = concept.split(".")
    return GroundTruthColumn(
        name=col_name,
        role=parts[0],
        concept=concept if len(parts) > 1 else None,
        source_file=source_file,
    )


def load_annotations(
    annotations_path: Path,
) -> tuple[dict[str, list[GroundTruthColumn]], bool]:
    """Load annotations YAML. Returns ({key: [GroundTruthColumn]}, is_gbif)."""
    with open(annotations_path) as f:
        data = yaml.safe_load(f)

    is_gbif = "_gbif_core" in data
    by_file: dict[str, list[GroundTruthColumn]] = {}

    for filename, columns in data.items():
        if not isinstance(columns, dict):
            continue
        key = filename if not filename.startswith("_") else "_gbif_core"
        by_file[key] = [
            _parse_annotation(col, concept, filename)
            for col, concept in columns.items()
        ]

    return by_file, is_gbif


# ── CSV helpers ───────────────────────────────────────────────────────────


def detect_separator(csv_path: Path) -> str:
    """Auto-detect CSV separator from first line."""
    with open(csv_path, encoding="utf-8", errors="replace") as f:
        first_line = f.readline()
    if "\t" in first_line:
        return "\t"
    if ";" in first_line and first_line.count(";") > first_line.count(","):
        return ";"
    return ","


def resolve_csv_paths(
    annotations_by_file: dict[str, list[GroundTruthColumn]],
    *,
    csv_override: Path | None = None,
    data_dir: Path | None = None,
    annotations_path: Path | None = None,
    is_gbif: bool = False,
) -> list[tuple[Path, list[GroundTruthColumn]]]:
    """Resolve annotation keys to actual (csv_path, ground_truth) pairs."""
    pairs: list[tuple[Path, list[GroundTruthColumn]]] = []

    # GBIF mode: apply _gbif_core annotations to specific CSV
    if is_gbif and csv_override:
        gt = annotations_by_file.get("_gbif_core", [])
        if gt:
            sep = detect_separator(csv_override)
            df_cols = set(pd.read_csv(csv_override, nrows=0, sep=sep).columns)
            filtered = [g for g in gt if g.name in df_cols]
            pairs.append((csv_override, filtered))
        return pairs

    # Resolve by trying data_dir, then annotations parent, then ml/data/silver/
    search_dirs: list[Path] = []
    if data_dir:
        search_dirs.append(data_dir)
    if annotations_path:
        search_dirs.append(annotations_path.parent)
    silver_dir = ML_ROOT / "data" / "silver"
    if silver_dir.exists() and silver_dir not in search_dirs:
        search_dirs.append(silver_dir)

    for filename, gt_list in annotations_by_file.items():
        if filename.startswith("_"):
            continue
        resolved = None
        for base in search_dirs:
            candidate = base / filename
            if candidate.exists():
                resolved = candidate
                break
        if resolved:
            pairs.append((resolved, gt_list))
        else:
            print(f"  Warning: CSV not found for '{filename}'", file=sys.stderr)

    return pairs


# ── Detection ─────────────────────────────────────────────────────────────


@dataclass
class DetectedColumn:
    name: str
    concept: str | None = None
    role: str = "other"
    confidence: float = 0.0
    affordances: set[str] = field(default_factory=set)
    source: str = ""


def detect_columns(csv_path: Path, *, use_ml: bool = True) -> list[DetectedColumn]:
    """Run detection on a CSV."""
    from niamoto.core.imports.profiler import DataProfiler

    profiler = DataProfiler()
    sep = detect_separator(csv_path)
    df = pd.read_csv(csv_path, nrows=500, sep=sep)

    results = []
    for col_name in df.columns:
        series = df[col_name]
        det = DetectedColumn(name=col_name)

        if use_ml:
            semantic_type, confidence = profiler._detect_semantic_type(col_name, series)
            if semantic_type:
                parts = semantic_type.split(".")
                det.role = parts[0]
                det.concept = semantic_type if len(parts) > 1 else None
                det.confidence = confidence
                det.source = "ml"
                profile = profiler._build_semantic_profile(semantic_type, confidence)
                det.affordances = profile.affordances
        else:
            concept, score = profiler._alias_registry.match(col_name)
            if concept and score >= 1.0:
                parts = concept.split(".")
                det.role = parts[0]
                det.concept = concept if len(parts) > 1 else None
                det.confidence = score
                det.source = "alias"

        results.append(det)
    return results


# ── Comparison ────────────────────────────────────────────────────────────


@dataclass
class ComparisonResult:
    column: str
    source_file: str
    expected_role: str
    expected_concept: str | None
    detected_role: str
    detected_concept: str | None
    detected_confidence: float
    role_match: bool
    concept_match: bool
    detected_source: str
    affordances: set[str] = field(default_factory=set)


def compare(
    ground_truth: list[GroundTruthColumn],
    detected: list[DetectedColumn],
) -> list[ComparisonResult]:
    detected_by_name = {d.name: d for d in detected}
    results = []

    for gt in ground_truth:
        det = detected_by_name.get(gt.name)
        if det is None:
            results.append(
                ComparisonResult(
                    column=gt.name,
                    source_file=gt.source_file,
                    expected_role=gt.role,
                    expected_concept=gt.concept,
                    detected_role="(not found)",
                    detected_concept=None,
                    detected_confidence=0.0,
                    role_match=False,
                    concept_match=False,
                    detected_source="none",
                )
            )
            continue

        role_match = det.role == gt.role
        concept_match = det.concept == gt.concept if gt.concept else role_match

        results.append(
            ComparisonResult(
                column=gt.name,
                source_file=gt.source_file,
                expected_role=gt.role,
                expected_concept=gt.concept,
                detected_role=det.role,
                detected_concept=det.concept,
                detected_confidence=det.confidence,
                role_match=role_match,
                concept_match=concept_match,
                detected_source=det.source,
                affordances=det.affordances,
            )
        )

    return results


# ── Metrics & reporting ───────────────────────────────────────────────────


def compute_metrics(
    results: list[ComparisonResult], *, dataset_name: str, mode: str
) -> dict:
    total = len(results)
    if total == 0:
        return {}
    return {
        "instance": dataset_name,
        "mode": mode,
        "total": total,
        "detected": sum(1 for r in results if r.detected_source != "none"),
        "role_correct": sum(1 for r in results if r.role_match),
        "concept_correct": sum(1 for r in results if r.concept_match),
        "role_pct": round(100 * sum(1 for r in results if r.role_match) / total, 1),
        "concept_pct": round(
            100 * sum(1 for r in results if r.concept_match) / total, 1
        ),
        "errors": [
            {
                "column": r.column,
                "file": r.source_file,
                "expected": r.expected_concept or r.expected_role,
                "detected": r.detected_concept or r.detected_role,
            }
            for r in results
            if not r.concept_match
        ],
    }


def print_report(
    results: list[ComparisonResult], *, instance_name: str, mode: str
) -> dict:
    total = len(results)
    if total == 0:
        print("No columns to evaluate.")
        return {}

    role_correct = sum(1 for r in results if r.role_match)
    concept_correct = sum(1 for r in results if r.concept_match)
    detected = sum(1 for r in results if r.detected_source != "none")

    print(f"\n{'=' * 70}")
    print(f"Instance: {instance_name} | Mode: {mode} | Columns: {total}")
    print(f"{'=' * 70}\n")

    files = sorted(set(r.source_file for r in results))
    for source_file in files:
        file_results = [r for r in results if r.source_file == source_file]
        if source_file:
            file_role = sum(1 for r in file_results if r.role_match)
            file_concept = sum(1 for r in file_results if r.concept_match)
            n = len(file_results)
            print(
                f"── {source_file} ({file_role}/{n} roles, {file_concept}/{n} concepts) ──\n"
            )

        print(
            f"  {'Column':<22} {'Expected':<25} {'Detected':<25} {'Conf':>5} {'R':>2} {'C':>2}"
        )
        print(f"  {'-' * 83}")
        for r in file_results:
            expected = r.expected_concept or r.expected_role
            detected_str = r.detected_concept or r.detected_role
            role_mark = "✓" if r.role_match else "✗"
            concept_mark = "✓" if r.concept_match else "✗"
            conf = (
                f"{r.detected_confidence:.2f}" if r.detected_confidence > 0 else "  -"
            )
            print(
                f"  {r.column:<22} {expected:<25} {detected_str:<25} {conf:>5} {role_mark:>2} {concept_mark:>2}"
            )
        print()

    print(f"{'─' * 50}")
    print(f"  Total:     {total} columns")
    print(f"  Detected:  {detected}/{total} ({100 * detected / total:.0f}%)")
    print(f"  Role:      {role_correct}/{total} ({100 * role_correct / total:.0f}%)")
    print(
        f"  Concept:   {concept_correct}/{total} ({100 * concept_correct / total:.0f}%)"
    )

    errors = [r for r in results if not r.concept_match]
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for r in errors:
            expected = r.expected_concept or r.expected_role
            got = r.detected_concept or r.detected_role
            print(f"    {r.column}: {expected} → {got}")

    metrics = compute_metrics(results, dataset_name=instance_name, mode=mode)
    print(f"\n{json.dumps({k: v for k, v in metrics.items() if k != 'errors'})}")
    return metrics


# ── Programmatic API ──────────────────────────────────────────────────────


def evaluate_dataset(
    csv_gt_pairs: list[tuple[Path, list[GroundTruthColumn]]],
    *,
    use_ml: bool = True,
    dataset_name: str = "",
    quiet: bool = False,
) -> tuple[list[ComparisonResult], dict]:
    """Evaluate CSV files against ground truth. Callable by run_eval_suite."""
    all_results: list[ComparisonResult] = []
    for csv_path, gt_list in csv_gt_pairs:
        detected = detect_columns(csv_path, use_ml=use_ml)
        all_results.extend(compare(gt_list, detected))

    mode = "ml" if use_ml else "alias-only"
    if quiet:
        metrics = compute_metrics(
            results=all_results, dataset_name=dataset_name, mode=mode
        )
    else:
        metrics = print_report(all_results, instance_name=dataset_name, mode=mode)

    return all_results, metrics


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate ML detection against ground truth annotations"
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        required=True,
        help="Path to annotations YAML (e.g. ml/data/eval/annotations/niamoto-nc.yml)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Base directory for resolving CSV paths in annotations",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Specific CSV file (for GBIF single-file mode)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="Export metrics to JSON file",
    )
    parser.add_argument("--no-ml", action="store_true", help="Alias registry only")
    parser.add_argument(
        "--compare", action="store_true", help="Run both modes and compare"
    )
    args = parser.parse_args()

    ann_path = (
        ROOT / args.annotations
        if not args.annotations.is_absolute()
        else args.annotations
    )
    if not ann_path.exists():
        print(f"Error: annotations not found: {ann_path}", file=sys.stderr)
        raise SystemExit(1)

    annotations_by_file, is_gbif = load_annotations(ann_path)
    total_cols = sum(len(v) for v in annotations_by_file.values())
    label = "GBIF Darwin Core" if is_gbif else ann_path.stem
    print(f"Using {label} annotations ({total_cols} columns)")

    csv_override = (
        ROOT / args.csv if args.csv and not args.csv.is_absolute() else args.csv
    )
    data_dir = (
        ROOT / args.data_dir
        if args.data_dir and not args.data_dir.is_absolute()
        else args.data_dir
    )

    csv_gt_pairs = resolve_csv_paths(
        annotations_by_file,
        csv_override=csv_override,
        data_dir=data_dir,
        annotations_path=ann_path,
        is_gbif=is_gbif,
    )

    if not csv_gt_pairs:
        print("Error: no CSV files matched", file=sys.stderr)
        raise SystemExit(1)

    dataset_name = ann_path.stem
    print(f"Evaluating {len(csv_gt_pairs)} file(s)...\n")

    all_metrics = []
    if args.compare:
        _, m_alias = evaluate_dataset(
            csv_gt_pairs, use_ml=False, dataset_name=dataset_name
        )
        _, m_ml = evaluate_dataset(csv_gt_pairs, use_ml=True, dataset_name=dataset_name)
        all_metrics = [m_alias, m_ml]
        if m_alias and m_ml:
            print(f"\n{'=' * 50}")
            print("  Delta ML vs alias-only:")
            print(
                f"    Role:    {m_alias['role_pct']}% → {m_ml['role_pct']}% ({m_ml['role_pct'] - m_alias['role_pct']:+.1f})"
            )
            print(
                f"    Concept: {m_alias['concept_pct']}% → {m_ml['concept_pct']}% ({m_ml['concept_pct'] - m_alias['concept_pct']:+.1f})"
            )
    else:
        use_ml = not args.no_ml
        _, metrics = evaluate_dataset(
            csv_gt_pairs, use_ml=use_ml, dataset_name=dataset_name
        )
        all_metrics = [metrics]

    if args.json:
        json_path = ROOT / args.json if not args.json.is_absolute() else args.json
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(all_metrics, f, indent=2)
        print(f"\nMetrics exported to {json_path}")


if __name__ == "__main__":
    main()
