#!/usr/bin/env python
"""
Train the fusion model (calibrated LogisticRegression).

Combines header and value model probability outputs into a single
calibrated prediction. Uses isotonic regression for calibration.

Usage:
    uv run python scripts/ml/train_fusion.py
    uv run python scripts/ml/train_fusion.py --gold-set data/gold_set.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from niamoto.core.imports.ml.alias_registry import _normalize

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent


def load_branch_models(
    header_path: Path,
    value_path: Path,
) -> tuple:
    """Load pre-trained branch models."""
    header_model = None
    value_model = None

    if header_path.exists():
        header_model = joblib.load(header_path)
        logger.info(f"Loaded header model from {header_path}")
    else:
        logger.warning(f"Header model not found: {header_path}")

    if value_path.exists():
        data = joblib.load(value_path)
        value_model = data["model"]
        logger.info(f"Loaded value model from {value_path}")
    else:
        logger.warning(f"Value model not found: {value_path}")

    return header_model, value_model


def extract_fusion_features(
    record: dict,
    header_model,
    value_model,
    all_concepts: list[str],
) -> np.ndarray:
    """Extract fusion input: header proba + value proba + meta features."""
    n_concepts = len(all_concepts)
    features = []

    # Header branch probabilities
    if header_model is not None and not record.get("is_anonymous", False):
        name = _normalize(record["column_name"])
        if name:
            try:
                header_proba = header_model.predict_proba([name])[0]
                header_classes = list(header_model.classes_)
                # Align to all_concepts
                aligned = np.zeros(n_concepts)
                for i, c in enumerate(all_concepts):
                    if c in header_classes:
                        aligned[i] = header_proba[header_classes.index(c)]
                features.extend(aligned)
            except Exception as e:
                logger.debug("Feature extraction failed: %s", e)
                features.extend(np.zeros(n_concepts))
        else:
            features.extend(np.zeros(n_concepts))
    else:
        features.extend(np.zeros(n_concepts))

    # Value branch probabilities
    if value_model is not None:
        try:
            from scripts.ml.train_value_model import extract_value_features

            feat_vec = extract_value_features(
                record.get("values_sample", []),
                record.get("values_stats", {}),
            )
            value_proba = value_model.predict_proba(feat_vec.reshape(1, -1))[0]
            value_classes = list(value_model.classes_)
            aligned = np.zeros(n_concepts)
            for i, c in enumerate(all_concepts):
                if c in value_classes:
                    aligned[i] = value_proba[value_classes.index(c)]
            features.extend(aligned)
        except Exception as e:  # noqa: F841
            features.extend(np.zeros(n_concepts))
    else:
        features.extend(np.zeros(n_concepts))

    # Meta features
    features.append(1.0 if record.get("is_anonymous", False) else 0.0)
    features.append(record.get("values_stats", {}).get("null_ratio", 0))
    features.append(record.get("values_stats", {}).get("unique_ratio", 0))

    return np.array(features, dtype=float)


def build_fusion_model(C: float = 1.0) -> LogisticRegression:
    """Build LogReg for fusion.

    Calibration via CalibratedClassifierCV requires >= 3 examples per class
    in each CV fold. Deferred until gold set is large enough.
    """
    return LogisticRegression(
        C=C,
        max_iter=1000,
        solver="lbfgs",
        random_state=42,
        class_weight="balanced",
    )


def main():
    parser = argparse.ArgumentParser(description="Train fusion model")
    parser.add_argument(
        "--gold-set", type=Path, default=ROOT / "data" / "gold_set.json"
    )
    parser.add_argument(
        "--header-model", type=Path, default=ROOT / "models" / "header_model.joblib"
    )
    parser.add_argument(
        "--value-model", type=Path, default=ROOT / "models" / "value_model.joblib"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "models" / "fusion_model.joblib"
    )
    parser.add_argument("--eval-only", action="store_true")
    args = parser.parse_args()

    if not args.gold_set.exists():
        logger.error(f"Gold set not found: {args.gold_set}")
        sys.exit(1)

    with open(args.gold_set) as f:
        records = json.load(f)

    header_model, value_model = load_branch_models(args.header_model, args.value_model)

    # Get all concepts
    all_concepts = sorted(set(r["concept_coarse"] for r in records))
    logger.info(f"Loaded {len(records)} records, {len(all_concepts)} concepts")

    # Extract fusion features
    logger.info("Extracting fusion features...")
    X = []
    y = []
    groups = []
    for r in records:
        feat = extract_fusion_features(r, header_model, value_model, all_concepts)
        X.append(feat)
        y.append(r["concept_coarse"])
        groups.append(r["source_dataset"])

    X = np.array(X)
    y = np.array(y)
    groups = np.array(groups)
    logger.info(f"Feature matrix shape: {X.shape}")

    # GroupKFold evaluation
    logger.info("\n=== GroupKFold Evaluation ===")
    unique_groups = np.unique(groups)
    n_splits = min(5, len(unique_groups))

    if n_splits >= 2:
        kfold = GroupKFold(n_splits=n_splits)
        f1_scores = []

        for fold, (train_idx, test_idx) in enumerate(kfold.split(X, groups=groups)):
            model = build_fusion_model()
            model.fit(X[train_idx], y[train_idx])
            preds = model.predict(X[test_idx])
            f1 = f1_score(y[test_idx], preds, average="macro", zero_division=0)
            f1_scores.append(f1)
            logger.info(f"  Fold {fold}: macro-F1 = {f1:.3f}")

        mean_f1 = float(np.mean(f1_scores))
        logger.info(f"  Mean macro-F1 = {mean_f1:.3f}")
    else:
        mean_f1 = 0.0
        logger.warning("Not enough groups for KFold")

    if args.eval_only:
        print(f"{mean_f1:.4f}")
        return

    # Train final model
    logger.info("\n=== Training final model ===")
    model = build_fusion_model()
    model.fit(X, y)

    preds = model.predict(X)
    train_f1 = f1_score(y, preds, average="macro", zero_division=0)
    logger.info(f"Training macro-F1: {train_f1:.3f}")

    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "all_concepts": all_concepts,
        },
        args.output,
    )
    logger.info(f"Fusion model saved to {args.output}")

    print(f"{mean_f1:.4f}")


if __name__ == "__main__":
    main()
