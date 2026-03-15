#!/usr/bin/env python
"""
CLI metric script for ML model evaluation.

Outputs a single number (macro-F1) to stdout for autoresearch compatibility.

Usage:
    uv run python -m scripts.ml.evaluate --model header --metric macro-f1
    uv run python -m scripts.ml.evaluate --model values --metric macro-f1
    uv run python -m scripts.ml.evaluate --model fusion --metric macro-f1
    uv run python -m scripts.ml.evaluate --model all    --metric macro-f1
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent


def evaluate_header(gold_path: Path, n_splits: int = 5) -> float:
    """Evaluate header model via GroupKFold."""
    from scripts.ml.train_header_model import (
        build_pipeline,
        load_gold_set,
        prepare_data,
    )

    records = [r for r in load_gold_set(gold_path) if not r.get("is_anonymous")]
    names, concepts, _roles, groups = prepare_data(records)

    unique = np.unique(groups)
    splits = min(n_splits, len(unique))
    if splits < 2:
        return 0.0

    kfold = GroupKFold(n_splits=splits)
    names_arr = np.array(names)
    concepts_arr = np.array(concepts)

    scores = []
    for train_idx, test_idx in kfold.split(names_arr, groups=groups):
        pipe = build_pipeline()
        pipe.fit(names_arr[train_idx].tolist(), concepts_arr[train_idx].tolist())
        preds = pipe.predict(names_arr[test_idx].tolist())
        scores.append(
            f1_score(concepts_arr[test_idx], preds, average="macro", zero_division=0)
        )

    return float(np.mean(scores))


def evaluate_values(gold_path: Path, n_splits: int = 5) -> float:
    """Evaluate value model via GroupKFold."""
    from scripts.ml.train_value_model import build_model, load_and_prepare

    X, concepts, _roles, groups = load_and_prepare(gold_path)

    unique = np.unique(groups)
    splits = min(n_splits, len(unique))
    if splits < 2:
        return 0.0

    kfold = GroupKFold(n_splits=splits)
    concepts_arr = np.array(concepts)

    scores = []
    for train_idx, test_idx in kfold.split(X, groups=groups):
        model = build_model()
        model.fit(X[train_idx], concepts_arr[train_idx])
        preds = model.predict(X[test_idx])
        scores.append(
            f1_score(concepts_arr[test_idx], preds, average="macro", zero_division=0)
        )

    return float(np.mean(scores))


def evaluate_fusion(gold_path: Path, n_splits: int = 5) -> float:
    """Evaluate fusion model via GroupKFold."""
    import joblib

    from scripts.ml.train_fusion import (
        build_fusion_model,
        extract_fusion_features,
    )

    header_path = ROOT / "models" / "header_model.joblib"
    value_path = ROOT / "models" / "value_model.joblib"

    header_model = joblib.load(header_path) if header_path.exists() else None
    value_data = joblib.load(value_path) if value_path.exists() else None
    value_model = value_data["model"] if value_data else None

    with open(gold_path) as f:
        records = json.load(f)

    all_concepts = sorted(set(r["concept"] for r in records))
    X = np.array(
        [
            extract_fusion_features(r, header_model, value_model, all_concepts)
            for r in records
        ]
    )
    y = np.array([r["concept"] for r in records])
    groups = np.array([r["source_dataset"] for r in records])

    unique = np.unique(groups)
    splits = min(n_splits, len(unique))
    if splits < 2:
        return 0.0

    kfold = GroupKFold(n_splits=splits)
    scores = []
    for train_idx, test_idx in kfold.split(X, groups=groups):
        model = build_fusion_model()
        model.fit(X[train_idx], y[train_idx])
        preds = model.predict(X[test_idx])
        scores.append(f1_score(y[test_idx], preds, average="macro", zero_division=0))

    return float(np.mean(scores))


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate ML model and output metric to stdout"
    )
    parser.add_argument(
        "--model",
        choices=["header", "values", "fusion", "all"],
        required=True,
    )
    parser.add_argument(
        "--metric",
        choices=["macro-f1"],
        default="macro-f1",
    )
    parser.add_argument(
        "--gold-set",
        type=Path,
        default=ROOT / "data" / "gold_set.json",
    )
    parser.add_argument("--splits", type=int, default=5)
    args = parser.parse_args()

    if not args.gold_set.exists():
        print("0.0000", file=sys.stderr)
        print("0.0000")
        sys.exit(1)

    if args.model == "header":
        score = evaluate_header(args.gold_set, args.splits)
    elif args.model == "values":
        score = evaluate_values(args.gold_set, args.splits)
    elif args.model == "fusion":
        score = evaluate_fusion(args.gold_set, args.splits)
    elif args.model == "all":
        h = evaluate_header(args.gold_set, args.splits)
        v = evaluate_values(args.gold_set, args.splits)
        f = evaluate_fusion(args.gold_set, args.splits)
        # Weighted average
        score = 0.4 * h + 0.4 * v + 0.2 * f
        print(f"header={h:.4f} values={v:.4f} fusion={f:.4f}", file=sys.stderr)

    print(f"{score:.4f}")


if __name__ == "__main__":
    main()
