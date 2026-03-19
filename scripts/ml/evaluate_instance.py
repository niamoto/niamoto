#!/usr/bin/env python
"""Evaluate ML detection quality against a finalized Niamoto instance.

Compares what the ML pipeline detects (concepts, roles, affordances) with
what a manually validated import.yml declares as ground truth.

Usage:
    uv run python -m scripts.ml.evaluate_instance \
        --instance test-instance/niamoto-subset

    uv run python -m scripts.ml.evaluate_instance \
        --instance test-instance/niamoto-subset --no-ml
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


# ── Ground truth extraction from import.yml ───────────────────────────────


@dataclass
class GroundTruthColumn:
    """A column with its expected role from the validated import.yml."""

    name: str
    role: str  # identifier, location, taxonomy, measurement, category, etc.
    concept: str | None = None  # e.g. taxonomy.species, location.elevation
    source_entity: str = ""


def extract_ground_truth(import_yml: Path) -> list[GroundTruthColumn]:
    """Extract expected column roles from a validated import.yml."""
    with open(import_yml) as f:
        config = yaml.safe_load(f)

    columns: list[GroundTruthColumn] = []

    # Handle v2 format (entities.datasets / entities.references)
    entities = config.get("entities", {})
    datasets = entities.get("datasets", {})
    references = entities.get("references", {})

    # Also handle v1 format (flat keys)
    if not datasets and not references:
        # v1 format — try to extract from flat structure
        for key, val in config.items():
            if key in ("version", "metadata"):
                continue
            if isinstance(val, dict):
                datasets[key] = val

    for entity_name, entity_cfg in {**datasets, **references}.items():
        connector = entity_cfg.get("connector", entity_cfg)
        csv_path = connector.get("path", "")

        # Schema fields
        schema = entity_cfg.get("schema", {})
        id_field = schema.get("id_field") or entity_cfg.get("identifier")
        if id_field:
            columns.append(GroundTruthColumn(
                name=id_field,
                role="identifier",
                concept="identifier.record",
                source_entity=entity_name,
            ))

        # Location field
        location_field = entity_cfg.get("location_field")
        if location_field:
            columns.append(GroundTruthColumn(
                name=location_field,
                role="location",
                concept="location.coordinate",
                source_entity=entity_name,
            ))

        # Relation FK
        relation = entity_cfg.get("relation", {})
        fk = relation.get("foreign_key")
        if fk:
            columns.append(GroundTruthColumn(
                name=fk,
                role="identifier",
                concept="identifier.plot",
                source_entity=entity_name,
            ))

        # Hierarchy levels (taxonomy)
        hierarchy = entity_cfg.get("hierarchy", {})
        extraction = connector.get("extraction", {})
        levels = extraction.get("levels", hierarchy.get("levels", []))
        for level in levels:
            if isinstance(level, dict):
                col = level.get("column", level.get("name", ""))
                level_name = level.get("name", "")
            else:
                col = str(level)
                level_name = col
            if col:
                concept = _taxonomy_level_to_concept(level_name)
                columns.append(GroundTruthColumn(
                    name=col,
                    role="taxonomy",
                    concept=concept,
                    source_entity=entity_name,
                ))

        # Schema fields with type hints
        for fld in schema.get("fields", []):
            fname = fld.get("name", "")
            ftype = fld.get("type", "")
            if fname and ftype == "geometry":
                columns.append(GroundTruthColumn(
                    name=fname,
                    role="location",
                    concept="location.coordinate",
                    source_entity=entity_name,
                ))

    return columns


def _taxonomy_level_to_concept(level_name: str) -> str:
    """Map taxonomy level names to concepts."""
    mapping = {
        "family": "taxonomy.family",
        "genus": "taxonomy.genus",
        "species": "taxonomy.species",
        "subspecies": "taxonomy.name",
        "infra": "taxonomy.name",
        "order": "taxonomy.order",
        "class": "taxonomy.class",
        "phylum": "taxonomy.phylum",
        "kingdom": "taxonomy.kingdom",
    }
    return mapping.get(level_name.lower(), "taxonomy.name")


# ── ML detection ──────────────────────────────────────────────────────────


@dataclass
class DetectedColumn:
    """A column as detected by the ML pipeline."""

    name: str
    concept: str | None = None
    role: str = "other"
    confidence: float = 0.0
    affordances: set[str] = field(default_factory=set)
    source: str = ""  # alias, ml, rule, none


def detect_columns_ml(csv_path: Path, *, use_ml: bool = True) -> list[DetectedColumn]:
    """Run the full profiler on a CSV and return detected columns."""
    from niamoto.core.imports.profiler import DataProfiler

    profiler = DataProfiler()

    # Read CSV
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

                # Get affordances
                profile = profiler._build_semantic_profile(semantic_type, confidence)
                det.affordances = profile.affordances
        else:
            # Heuristics only — alias registry
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
    """Compare ground truth with ML detections."""
    detected_by_name = {d.name: d for d in detected}
    results = []

    for gt in ground_truth:
        det = detected_by_name.get(gt.name)
        if det is None:
            results.append(ComparisonResult(
                column=gt.name,
                expected_role=gt.role,
                expected_concept=gt.concept,
                detected_role="(not found)",
                detected_concept=None,
                detected_confidence=0.0,
                role_match=False,
                concept_match=False,
                detected_source="none",
            ))
            continue

        role_match = det.role == gt.role
        concept_match = (
            det.concept == gt.concept
            if gt.concept
            else det.role == gt.role  # fallback to role match
        )

        results.append(ComparisonResult(
            column=gt.name,
            expected_role=gt.role,
            expected_concept=gt.concept,
            detected_role=det.role,
            detected_concept=det.concept,
            detected_confidence=det.confidence,
            role_match=role_match,
            concept_match=concept_match,
            detected_source=det.source,
            affordances=det.affordances,
        ))

    return results


# ── Reporting ─────────────────────────────────────────────────────────────


def print_report(
    results: list[ComparisonResult],
    *,
    instance_name: str,
    mode: str,
) -> dict:
    """Print a human-readable report and return summary metrics."""
    total = len(results)
    role_correct = sum(1 for r in results if r.role_match)
    concept_correct = sum(1 for r in results if r.concept_match)
    detected = sum(1 for r in results if r.detected_source != "none")

    print(f"\n{'=' * 70}")
    print(f"Instance Evaluation: {instance_name} ({mode})")
    print(f"{'=' * 70}\n")

    # Detail table
    print(f"{'Column':<25} {'Expected':<25} {'Detected':<25} {'Conf':>5} {'Role':>5} {'Concept':>8}")
    print("-" * 95)
    for r in results:
        expected = r.expected_concept or r.expected_role
        detected_str = r.detected_concept or r.detected_role
        role_mark = "✓" if r.role_match else "✗"
        concept_mark = "✓" if r.concept_match else "✗"
        conf_str = f"{r.detected_confidence:.2f}" if r.detected_confidence > 0 else "-"
        print(
            f"{r.column:<25} {expected:<25} {detected_str:<25} "
            f"{conf_str:>5} {role_mark:>5} {concept_mark:>8}"
        )

    # Summary
    print(f"\n{'─' * 40}")
    print(f"Total columns evaluated:  {total}")
    print(f"Detected (non-empty):     {detected}/{total} ({100*detected/total:.0f}%)")
    print(f"Role correct:             {role_correct}/{total} ({100*role_correct/total:.0f}%)")
    print(f"Concept correct:          {concept_correct}/{total} ({100*concept_correct/total:.0f}%)")

    # Errors
    errors = [r for r in results if not r.concept_match]
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for r in errors:
            expected = r.expected_concept or r.expected_role
            detected_str = r.detected_concept or r.detected_role
            print(f"  {r.column}: expected {expected}, got {detected_str}")

    metrics = {
        "instance": instance_name,
        "mode": mode,
        "total": total,
        "detected": detected,
        "role_correct": role_correct,
        "concept_correct": concept_correct,
        "role_accuracy": role_correct / total if total else 0,
        "concept_accuracy": concept_correct / total if total else 0,
    }
    print(f"\n{json.dumps(metrics)}")
    return metrics


# ── Main ──────────────────────────────────────────────────────────────────


def find_csv_files(instance_dir: Path) -> list[Path]:
    """Find CSV files in the imports directory."""
    imports_dir = instance_dir / "imports"
    return sorted(imports_dir.glob("*.csv"))


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
    parser.add_argument(
        "--no-ml",
        action="store_true",
        help="Run with alias registry only (no ML models)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run both modes (ML vs no-ML) and compare",
    )
    args = parser.parse_args()

    instance_dir = ROOT / args.instance if not args.instance.is_absolute() else args.instance
    import_yml = instance_dir / "config" / "import.yml"

    if not import_yml.exists():
        print(f"Error: {import_yml} not found", file=sys.stderr)
        raise SystemExit(1)

    # Extract ground truth
    ground_truth = extract_ground_truth(import_yml)
    instance_name = instance_dir.name

    # Find CSV files
    csv_files = find_csv_files(instance_dir)
    if not csv_files:
        print(f"Error: no CSV files in {instance_dir / 'imports'}", file=sys.stderr)
        raise SystemExit(1)

    # Collect all detected columns from all CSV files
    if args.compare:
        # Run both modes
        for use_ml, mode in [(False, "alias-only"), (True, "ml")]:
            all_detected = []
            for csv_path in csv_files:
                all_detected.extend(detect_columns_ml(csv_path, use_ml=use_ml))
            results = compare(ground_truth, all_detected)
            print_report(results, instance_name=instance_name, mode=mode)
    else:
        use_ml = not args.no_ml
        mode = "ml" if use_ml else "alias-only"
        all_detected = []
        for csv_path in csv_files:
            all_detected.extend(detect_columns_ml(csv_path, use_ml=use_ml))
        results = compare(ground_truth, all_detected)
        print_report(results, instance_name=instance_name, mode=mode)


if __name__ == "__main__":
    main()
