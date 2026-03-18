#!/usr/bin/env python
"""
Train the values branch model (statistical features + HistGradientBoosting).

Classifies columns based on value statistics (distribution, patterns, ranges).
Works independently of column names — essential for anonymous headers (X1, col_3).

Usage:
    uv run python scripts/ml/train_value_model.py
    uv run python scripts/ml/train_value_model.py --gold-set data/gold_set.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from niamoto.core.imports.ml.value_features import (
    FEATURE_NAMES,
    extract_value_features_from_sample,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent


def extract_value_features(values_sample: list, stats: dict) -> np.ndarray:
    """Extract features from stored values sample + stats."""
    return extract_value_features_from_sample(values_sample, stats)


def load_and_prepare(gold_path: Path) -> tuple:
    """Load gold set and extract feature vectors."""
    with open(gold_path) as f:
        records = json.load(f)

    X = []
    y_concepts = []
    y_roles = []
    groups = []

    for r in records:
        feat = extract_value_features(
            r.get("values_sample", []), r.get("values_stats", {})
        )
        X.append(feat)
        y_concepts.append(r["concept_coarse"])
        y_roles.append(r["role"])
        groups.append(r["source_dataset"])

    return np.array(X), y_concepts, y_roles, np.array(groups)


def build_model(**kwargs):
    """Build HistGradientBoosting classifier."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(
        max_iter=500,
        max_depth=10,
        learning_rate=0.05,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced",
    )


def evaluate_kfold(
    X: np.ndarray,
    concepts: list[str],
    groups: np.ndarray,
    n_splits: int = 5,
    **model_kwargs,
) -> float:
    """Evaluate with GroupKFold, return mean macro-F1."""
    unique_groups = np.unique(groups)
    actual_splits = min(n_splits, len(unique_groups))
    if actual_splits < 2:
        logger.warning("Not enough groups for KFold")
        return 0.0

    kfold = GroupKFold(n_splits=actual_splits)
    concepts_arr = np.array(concepts)

    f1_scores = []
    for fold, (train_idx, test_idx) in enumerate(kfold.split(X, groups=groups)):
        model = build_model(**model_kwargs)
        model.fit(X[train_idx], concepts_arr[train_idx])
        preds = model.predict(X[test_idx])
        f1 = f1_score(concepts_arr[test_idx], preds, average="macro", zero_division=0)
        f1_scores.append(f1)
        logger.info(f"  Fold {fold}: macro-F1 = {f1:.3f}")

    mean_f1 = float(np.mean(f1_scores))
    logger.info(f"  Mean macro-F1 = {mean_f1:.3f}")
    return mean_f1


def main():
    parser = argparse.ArgumentParser(description="Train value model")
    parser.add_argument(
        "--gold-set",
        type=Path,
        default=ROOT / "data" / "gold_set.json",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "models" / "value_model.joblib"
    )
    parser.add_argument("--eval-only", action="store_true")
    args = parser.parse_args()

    if not args.gold_set.exists():
        logger.error(f"Gold set not found: {args.gold_set}")
        sys.exit(1)

    X, concepts, roles, groups = load_and_prepare(args.gold_set)
    logger.info(
        f"Prepared {len(X)} samples, {len(set(concepts))} concepts, {len(FEATURE_NAMES)} features"
    )

    # Evaluate
    logger.info("\n=== GroupKFold Evaluation ===")
    mean_f1 = evaluate_kfold(X, concepts, groups)

    if args.eval_only:
        print(f"{mean_f1:.4f}")
        return

    # Train final model on all data
    logger.info("\n=== Training final model ===")
    model = build_model()
    model.fit(X, concepts)

    preds = model.predict(X)
    train_f1 = f1_score(concepts, preds, average="macro", zero_division=0)
    logger.info(f"Training macro-F1: {train_f1:.3f}")
    logger.info(f"\n{classification_report(concepts, preds, zero_division=0)}")

    # Save model + feature names
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES}, args.output)
    logger.info(f"Model saved to {args.output}")

    print(f"{mean_f1:.4f}")


if __name__ == "__main__":
    main()
