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
import pandas as pd
import scipy.stats
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent

# Feature names for interpretability
FEATURE_NAMES = [
    # Numeric stats (14)
    "num_mean",
    "num_std",
    "num_min",
    "num_max",
    "num_skew",
    "num_kurtosis",
    "num_q25",
    "num_q50",
    "num_q75",
    "num_range",
    "num_cv",
    "num_negative_ratio",
    "num_integer_ratio",
    "num_zero_ratio",
    # Uniqueness and distribution (3)
    "unique_ratio",
    "null_ratio",
    "entropy",
    # Character features (6)
    "mean_length",
    "std_length",
    "digit_ratio",
    "alpha_ratio",
    "space_ratio",
    "mean_word_count",
    # Regex patterns (4)
    "pct_date_iso",
    "pct_coordinate",
    "pct_boolean",
    "pct_uuid",
    # Biological patterns (2)
    "binomial_score",
    "family_suffix",
    # Numeric patterns (6)
    "mean_decimals",
    "in_lat_range",
    "in_lon_range",
    "in_01_range",
    "small_int_ratio",
    "pct_starts_upper",
    # Meta (2)
    "is_numeric",
    "n_values",
]


def extract_value_features(values_sample: list, stats: dict) -> np.ndarray:
    """Extract features from stored values sample + stats."""
    features = np.zeros(len(FEATURE_NAMES))

    if not values_sample:
        return features

    series = pd.Series(values_sample)
    is_numeric = stats.get("dtype", "").startswith(("int", "float")) or "mean" in stats

    # Numeric features
    if is_numeric:
        try:
            num_series = pd.to_numeric(series, errors="coerce").dropna()
            if len(num_series) > 0:
                features[0] = float(num_series.mean())
                features[1] = float(num_series.std()) if len(num_series) > 1 else 0
                features[2] = float(num_series.min())
                features[3] = float(num_series.max())
                features[4] = float(num_series.skew()) if len(num_series) > 2 else 0
                features[5] = float(num_series.kurtosis()) if len(num_series) > 3 else 0
                features[6] = float(num_series.quantile(0.25))
                features[7] = float(num_series.median())
                features[8] = float(num_series.quantile(0.75))
                features[9] = float(num_series.max() - num_series.min())
                features[10] = (
                    float(num_series.std() / num_series.mean())
                    if num_series.mean() != 0
                    else 0
                )
                features[11] = float((num_series < 0).mean())
                features[12] = float((num_series == num_series.astype(int)).mean())
                features[13] = float((num_series == 0).mean())
        except Exception:
            pass

    # Uniqueness and distribution
    features[14] = stats.get("unique_ratio", 0)
    features[15] = stats.get("null_ratio", 0)
    if len(series) > 0:
        vc = series.value_counts(normalize=True)
        features[16] = float(scipy.stats.entropy(vc)) if len(vc) > 1 else 0

    # Character features
    str_vals = series.astype(str)
    if len(str_vals) > 0:
        lengths = str_vals.str.len()
        features[17] = float(lengths.mean())
        features[18] = float(lengths.std()) if len(lengths) > 1 else 0

        total_chars = max(lengths.sum(), 1)
        features[19] = float(str_vals.str.count(r"\d").sum() / total_chars)
        features[20] = float(str_vals.str.count(r"[a-zA-Z]").sum() / total_chars)
        features[21] = float(str_vals.str.count(r"\s").sum() / total_chars)
        words = str_vals.str.split().str.len()
        features[22] = float(words.mean())

    # Regex patterns
    if len(str_vals) > 0:
        n = len(str_vals)
        features[23] = float(str_vals.str.match(r"^\d{4}-\d{2}-\d{2}").sum() / n)
        features[24] = float(str_vals.str.match(r"^-?\d{1,3}\.\d{4,}$").sum() / n)
        features[25] = float(
            str_vals.str.lower()
            .isin(["true", "false", "yes", "no", "0", "1", "oui", "non"])
            .sum()
            / n
        )
        features[26] = float(str_vals.str.match(r"^[0-9a-f]{8}-[0-9a-f]{4}").sum() / n)

    # Biological patterns
    if len(str_vals) > 0:
        n = len(str_vals)
        features[27] = float(str_vals.str.match(r"^[A-Z][a-z]+ [a-z]+").sum() / n)
        features[28] = float(
            str_vals.str.match(r".*(?:aceae|idae|ales|ineae)$").sum() / n
        )

    # Numeric patterns
    if is_numeric:
        try:
            num_series = pd.to_numeric(series, errors="coerce").dropna()
            if len(num_series) > 0:
                str_nums = num_series.astype(str)
                dec_counts = str_nums.str.extract(r"\.(\d+)$")[0].str.len()
                features[29] = (
                    float(dec_counts.mean()) if dec_counts.notna().any() else 0
                )
        except Exception:
            pass

    # Range indicators
    if is_numeric:
        try:
            num_series = pd.to_numeric(series, errors="coerce").dropna()
            if len(num_series) > 0:
                features[30] = float(((num_series >= -90) & (num_series <= 90)).mean())
                features[31] = float(
                    ((num_series >= -180) & (num_series <= 180)).mean()
                )
                features[32] = float(((num_series >= 0) & (num_series <= 1)).mean())
                features[33] = float(
                    (
                        (num_series >= 0)
                        & (num_series <= 100)
                        & (num_series == num_series.astype(int))
                    ).mean()
                )
        except Exception:
            pass

    # Text patterns
    if len(str_vals) > 0:
        features[34] = float(str_vals.str.match(r"^[A-Z]").sum() / len(str_vals))

    # Meta
    features[35] = 1.0 if is_numeric else 0.0
    features[36] = len(values_sample)

    # Replace NaN/inf
    features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
    return features


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
        max_depth=8,
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
