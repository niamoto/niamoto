#!/usr/bin/env python
"""
Train the header branch model (TF-IDF char n-grams + LogisticRegression).

Classifies column names into semantic concepts using character-level features.
This captures cross-language variations (diametre/diametro/diameter) naturally.

Usage:
    uv run python -m ml.scripts.train.train_header_model
    uv run python -m ml.scripts.train.train_header_model --gold-set ml/data/gold_set.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from niamoto.core.imports.ml.alias_registry import _normalize
from niamoto.core.imports.ml.header_features import build_header_text_from_stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
ML_ROOT = ROOT / "ml"


def load_gold_set(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def prepare_data(records: list[dict]) -> tuple:
    """Prepare (X_names, y_concepts, y_roles, groups) from gold set records."""
    names = []
    concepts = []
    roles = []
    groups = []

    for r in records:
        name = _normalize(r["column_name"])
        if not name:
            continue
        name = build_header_text_from_stats(name, r.get("values_stats", {}))
        names.append(name)
        concepts.append(r["concept_coarse"])
        roles.append(r["role"])
        groups.append(r["source_dataset"])

    return names, concepts, roles, np.array(groups)


def build_pipeline(
    ngram_range: tuple = (2, 5),
    max_features: int = 5000,
    C: float = 130.0,
) -> Pipeline:
    """Build TF-IDF + LogisticRegression pipeline."""
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=ngram_range,
                    max_features=max_features,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=C,
                    max_iter=5000,
                    solver="saga",
                    l1_ratio=1.0,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def evaluate_kfold(
    names: list[str],
    concepts: list[str],
    groups: np.ndarray,
    n_splits: int = 5,
    **pipeline_kwargs,
) -> float:
    """Evaluate with GroupKFold and return mean macro-F1."""
    unique_groups = np.unique(groups)
    actual_splits = min(n_splits, len(unique_groups))
    if actual_splits < 2:
        logger.warning("Not enough groups for KFold evaluation")
        return 0.0

    kfold = GroupKFold(n_splits=actual_splits)
    indices = np.arange(len(names))
    names_arr = np.array(names)
    concepts_arr = np.array(concepts)

    f1_scores = []
    for fold, (train_idx, test_idx) in enumerate(kfold.split(indices, groups=groups)):
        pipe = build_pipeline(**pipeline_kwargs)
        pipe.fit(names_arr[train_idx].tolist(), concepts_arr[train_idx].tolist())
        preds = pipe.predict(names_arr[test_idx].tolist())
        f1 = f1_score(concepts_arr[test_idx], preds, average="macro", zero_division=0)
        f1_scores.append(f1)
        logger.info(f"  Fold {fold}: macro-F1 = {f1:.3f}")

    mean_f1 = float(np.mean(f1_scores))
    logger.info(f"  Mean macro-F1 = {mean_f1:.3f}")
    return mean_f1


def main():
    parser = argparse.ArgumentParser(description="Train header model")
    parser.add_argument(
        "--gold-set",
        type=Path,
        default=ML_ROOT / "data" / "gold_set.json",
    )
    parser.add_argument(
        "--output", type=Path, default=ML_ROOT / "models" / "header_model.joblib"
    )
    parser.add_argument("--eval-only", action="store_true")
    args = parser.parse_args()

    if not args.gold_set.exists():
        logger.error(f"Gold set not found: {args.gold_set}")
        logger.error("Run: uv run python -m ml.scripts.data.build_gold_set")
        sys.exit(1)

    records = load_gold_set(args.gold_set)
    # Filter out anonymous columns (header model can't learn from X1, col_3)
    records = [r for r in records if not r.get("is_anonymous", False)]
    logger.info(f"Loaded {len(records)} non-anonymous columns")

    names, concepts, roles, groups = prepare_data(records)
    logger.info(f"Prepared {len(names)} samples, {len(set(concepts))} concepts")

    # Evaluate with GroupKFold
    logger.info("\n=== GroupKFold Evaluation ===")
    mean_f1 = evaluate_kfold(names, concepts, groups)

    if args.eval_only:
        print(f"{mean_f1:.4f}")
        return

    # Train final model on all data
    logger.info("\n=== Training final model ===")
    pipe = build_pipeline()
    pipe.fit(names, concepts)

    # Quick self-check
    preds = pipe.predict(names)
    train_f1 = f1_score(concepts, preds, average="macro", zero_division=0)
    logger.info(f"Training macro-F1: {train_f1:.3f}")
    logger.info(f"\n{classification_report(concepts, preds, zero_division=0)}")

    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, args.output)
    logger.info(f"Model saved to {args.output}")

    # Print metric for autoresearch
    print(f"{mean_f1:.4f}")


if __name__ == "__main__":
    main()
