#!/usr/bin/env python
"""Evaluate ML detection quality against a finalized Niamoto instance.

Uses column_annotations.yml (manual ground truth for all columns) when
available, falling back to import.yml (structural columns only).

Usage:
    uv run python -m scripts.ml.evaluate_instance \
        --instance test-instance/niamoto-subset --compare
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


# ── Ground truth ──────────────────────────────────────────────────────────


@dataclass
class GroundTruthColumn:
    name: str
    role: str
    concept: str | None = None
    source_file: str = ""


def load_annotations(annotations_path: Path) -> dict[str, list[GroundTruthColumn]]:
    """Load column_annotations.yml — returns {filename: [GroundTruthColumn]}."""
    with open(annotations_path) as f:
        data = yaml.safe_load(f)

    by_file: dict[str, list[GroundTruthColumn]] = {}
    for filename, columns in data.items():
        if not isinstance(columns, dict):
            continue
        gt_list = []
        for col_name, concept in columns.items():
            parts = concept.split(".")
            role = parts[0]
            gt_list.append(
                GroundTruthColumn(
                    name=col_name,
                    role=role,
                    concept=concept if len(parts) > 1 else None,
                    source_file=filename,
                )
            )
        by_file[filename] = gt_list
    return by_file


def load_import_yml_ground_truth(import_yml: Path) -> list[GroundTruthColumn]:
    """Fallback: extract ground truth from import.yml (structural columns only)."""
    with open(import_yml) as f:
        config = yaml.safe_load(f)

    columns: list[GroundTruthColumn] = []
    entities = config.get("entities", {})
    all_entities = {**entities.get("datasets", {}), **entities.get("references", {})}

    # v1 fallback
    if not all_entities:
        for key, val in config.items():
            if key in ("version", "metadata"):
                continue
            if isinstance(val, dict):
                all_entities[key] = val

    for entity_name, cfg in all_entities.items():
        connector = cfg.get("connector", cfg)
        schema = cfg.get("schema", {})

        id_field = schema.get("id_field") or cfg.get("identifier")
        if id_field:
            columns.append(
                GroundTruthColumn(
                    name=id_field, role="identifier", concept="identifier.record"
                )
            )

        location_field = cfg.get("location_field")
        if location_field:
            columns.append(
                GroundTruthColumn(
                    name=location_field, role="location", concept="location.coordinate"
                )
            )

        fk = cfg.get("relation", {}).get("foreign_key")
        if fk:
            columns.append(
                GroundTruthColumn(name=fk, role="identifier", concept="identifier.plot")
            )

        extraction = connector.get("extraction", {})
        levels = extraction.get("levels", cfg.get("hierarchy", {}).get("levels", []))
        taxonomy_map = {
            "family": "taxonomy.family",
            "genus": "taxonomy.genus",
            "species": "taxonomy.species",
            "subspecies": "taxonomy.name",
            "infra": "taxonomy.name",
        }
        for level in levels:
            if isinstance(level, dict):
                col = level.get("column", level.get("name", ""))
                name = level.get("name", "")
            else:
                col, name = str(level), str(level)
            if col:
                concept = taxonomy_map.get(name.lower(), "taxonomy.name")
                columns.append(
                    GroundTruthColumn(name=col, role="taxonomy", concept=concept)
                )

        for fld in schema.get("fields", []):
            if fld.get("type") == "geometry" and fld.get("name"):
                columns.append(
                    GroundTruthColumn(
                        name=fld["name"],
                        role="location",
                        concept="location.coordinate",
                    )
                )

    return columns


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
    df = pd.read_csv(csv_path, nrows=500)

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


# ── Reporting ─────────────────────────────────────────────────────────────


def print_report(
    results: list[ComparisonResult],
    *,
    instance_name: str,
    mode: str,
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

    # Group by source file
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

    # Summary
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

    metrics = {
        "instance": instance_name,
        "mode": mode,
        "total": total,
        "detected": detected,
        "role_correct": role_correct,
        "concept_correct": concept_correct,
        "role_pct": round(100 * role_correct / total, 1),
        "concept_pct": round(100 * concept_correct / total, 1),
    }
    print(f"\n{json.dumps(metrics)}")
    return metrics


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate ML detection against a finalized instance"
    )
    parser.add_argument(
        "--instance",
        type=Path,
        required=True,
        help="Path to instance directory (e.g. test-instance/niamoto-subset)",
    )
    parser.add_argument("--no-ml", action="store_true", help="Alias registry only")
    parser.add_argument(
        "--compare", action="store_true", help="Run both modes and compare"
    )
    args = parser.parse_args()

    instance_dir = (
        ROOT / args.instance if not args.instance.is_absolute() else args.instance
    )
    annotations_path = instance_dir / "config" / "column_annotations.yml"
    import_yml = instance_dir / "config" / "import.yml"

    # Load ground truth: prefer annotations, fallback to import.yml
    if annotations_path.exists():
        annotations_by_file = load_annotations(annotations_path)
        print(
            f"Using column_annotations.yml ({sum(len(v) for v in annotations_by_file.values())} columns)"
        )
    else:
        if not import_yml.exists():
            print(
                "Error: neither column_annotations.yml nor import.yml found",
                file=sys.stderr,
            )
            raise SystemExit(1)
        gt = load_import_yml_ground_truth(import_yml)
        annotations_by_file = {"": gt}
        print(f"Using import.yml fallback ({len(gt)} structural columns)")

    instance_name = instance_dir.name
    imports_dir = instance_dir / "imports"

    # Build CSV → ground truth mapping
    csv_gt_pairs: list[tuple[Path, list[GroundTruthColumn]]] = []
    for filename, gt_list in annotations_by_file.items():
        csv_path = imports_dir / filename
        if csv_path.exists():
            csv_gt_pairs.append((csv_path, gt_list))
        elif not filename:
            # Fallback mode: match against all CSVs
            for csv_path in sorted(imports_dir.glob("*.csv")):
                csv_gt_pairs.append((csv_path, gt_list))

    if not csv_gt_pairs:
        print("Error: no CSV files matched", file=sys.stderr)
        raise SystemExit(1)

    def run_eval(use_ml: bool, mode: str) -> dict:
        all_results = []
        for csv_path, gt_list in csv_gt_pairs:
            detected = detect_columns(csv_path, use_ml=use_ml)
            all_results.extend(compare(gt_list, detected))
        return print_report(all_results, instance_name=instance_name, mode=mode)

    if args.compare:
        m_alias = run_eval(False, "alias-only")
        m_ml = run_eval(True, "ml")
        # Delta summary
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
        run_eval(not args.no_ml, "ml" if not args.no_ml else "alias-only")


if __name__ == "__main__":
    main()
