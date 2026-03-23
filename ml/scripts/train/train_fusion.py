#!/usr/bin/env python
"""
Train the fusion model (calibrated LogisticRegression).

Combines header and value model probability outputs into a single
calibrated prediction. Uses isotonic regression for calibration.

Usage:
    uv run python -m ml.scripts.train.train_fusion
    uv run python -m ml.scripts.train.train_fusion --gold-set ml/data/gold_set.json
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

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from niamoto.core.imports.ml.alias_registry import _normalize
from niamoto.core.imports.ml.fusion_features import (
    branch_confidence_stats,
    dampen_code_like_false_counts,
    is_code_like_header,
    top_concept_flags,
)
from niamoto.core.imports.ml.header_features import build_header_text_from_stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
ML_ROOT = ROOT / "ml"
FUSION_META_FEATURE_NAMES = (
    "is_anonymous",
    "null_ratio",
    "unique_ratio",
    "code_like_header",
)


def _align_branch_probabilities(
    proba: np.ndarray,
    branch_classes: list[str],
    all_concepts: list[str],
) -> np.ndarray:
    """Align branch probability vectors to the shared concept ordering."""
    aligned = np.zeros((len(proba), len(all_concepts)), dtype=float)
    class_to_idx = {name: idx for idx, name in enumerate(branch_classes)}
    for concept_idx, concept in enumerate(all_concepts):
        branch_idx = class_to_idx.get(concept)
        if branch_idx is not None:
            aligned[:, concept_idx] = proba[:, branch_idx]
    return aligned


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


def extract_fusion_branch_probabilities(
    record: dict,
    header_model,
    value_model,
    all_concepts: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    """Extract aligned branch probabilities after deterministic damping."""
    n_concepts = len(all_concepts)
    aligned_header = np.zeros(n_concepts)
    aligned_value = np.zeros(n_concepts)

    # Header branch probabilities
    if header_model is not None and not record.get("is_anonymous", False):
        name = _normalize(record["column_name"])
        if name:
            try:
                header_text = build_header_text_from_stats(
                    name, record.get("values_stats", {})
                )
                header_proba = header_model.predict_proba([header_text])[0]
                header_classes = list(header_model.classes_)
                # Align to all_concepts
                for i, c in enumerate(all_concepts):
                    if c in header_classes:
                        aligned_header[i] = header_proba[header_classes.index(c)]
            except Exception as e:
                logger.debug("Feature extraction failed: %s", e)
    if value_model is not None:
        try:
            from ml.scripts.train.train_value_model import extract_value_features

            feat_vec = extract_value_features(
                record.get("values_sample", []),
                record.get("values_stats", {}),
            )
            value_proba = value_model.predict_proba(feat_vec.reshape(1, -1))[0]
            value_classes = list(value_model.classes_)
            for i, c in enumerate(all_concepts):
                if c in value_classes:
                    aligned_value[i] = value_proba[value_classes.index(c)]
        except Exception as e:  # noqa: F841
            pass

    norm_name = _normalize(record["column_name"])
    aligned_header, aligned_value = dampen_code_like_false_counts(
        aligned_header,
        aligned_value,
        all_concepts,
        raw_name=record["column_name"],
        norm_name=norm_name,
    )

    return aligned_header, aligned_value


def extract_fusion_branch_probabilities_batch(
    records: list[dict],
    header_model,
    value_model,
    all_concepts: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    """Batch version of branch probability extraction for faster cache builds."""
    n_records = len(records)
    n_concepts = len(all_concepts)
    aligned_header = np.zeros((n_records, n_concepts), dtype=float)
    aligned_value = np.zeros((n_records, n_concepts), dtype=float)

    if header_model is not None and records:
        header_indices = []
        header_texts = []
        for idx, record in enumerate(records):
            if record.get("is_anonymous", False):
                continue
            name = _normalize(record["column_name"])
            if not name:
                continue
            header_indices.append(idx)
            header_texts.append(
                build_header_text_from_stats(name, record.get("values_stats", {}))
            )
        if header_texts:
            try:
                header_proba = header_model.predict_proba(header_texts)
                aligned = _align_branch_probabilities(
                    header_proba,
                    list(header_model.classes_),
                    all_concepts,
                )
                aligned_header[header_indices] = aligned
            except Exception as e:
                logger.debug("Batch header feature extraction failed: %s", e)

    if value_model is not None and records:
        try:
            from ml.scripts.train.train_value_model import extract_value_features

            value_features = np.array(
                [
                    extract_value_features(
                        record.get("values_sample", []),
                        record.get("values_stats", {}),
                    )
                    for record in records
                ],
                dtype=float,
            )
            value_proba = value_model.predict_proba(value_features)
            aligned_value = _align_branch_probabilities(
                value_proba,
                list(value_model.classes_),
                all_concepts,
            )
        except Exception as e:
            logger.debug("Batch value feature extraction failed: %s", e)

    for idx, record in enumerate(records):
        norm_name = _normalize(record["column_name"])
        damped_header, damped_value = dampen_code_like_false_counts(
            aligned_header[idx],
            aligned_value[idx],
            all_concepts,
            raw_name=record["column_name"],
            norm_name=norm_name,
        )
        aligned_header[idx] = damped_header
        aligned_value[idx] = damped_value

    return aligned_header, aligned_value


def extract_fusion_metadata(record: dict) -> np.ndarray:
    """Extract the compact metadata needed to compose fusion features."""
    norm_name = _normalize(record["column_name"])
    return np.array(
        [
            1.0 if record.get("is_anonymous", False) else 0.0,
            float(record.get("values_stats", {}).get("null_ratio", 0.0)),
            float(record.get("values_stats", {}).get("unique_ratio", 0.0)),
            float(is_code_like_header(record["column_name"], norm_name)),
        ],
        dtype=float,
    )


def extract_fusion_metadata_batch(records: list[dict]) -> np.ndarray:
    """Batch extraction of the compact metadata needed for fusion features."""
    if not records:
        return np.zeros((0, len(FUSION_META_FEATURE_NAMES)), dtype=float)
    return np.array(
        [extract_fusion_metadata(record) for record in records], dtype=float
    )


def compose_fusion_features(
    aligned_header: np.ndarray,
    aligned_value: np.ndarray,
    metadata: np.ndarray,
    all_concepts: list[str],
) -> np.ndarray:
    """Compose the final fusion vector from cached branch outputs + metadata."""
    features = []
    is_anonymous, null_ratio, unique_ratio, code_like_header = metadata.tolist()

    features.extend(aligned_header)
    features.extend(aligned_value)

    # Meta features
    header_max, header_margin, header_entropy = branch_confidence_stats(aligned_header)
    value_max, value_margin, value_entropy = branch_confidence_stats(aligned_value)
    agree, value_stat_count, header_stat_count = top_concept_flags(
        aligned_header, aligned_value, all_concepts
    )
    header_missing = 1.0 if header_max <= 0.0 else 0.0
    value_missing = 1.0 if value_max <= 0.0 else 0.0
    value_when_header_weak = value_max * (1.0 - header_max)
    value_margin_when_header_weak = value_margin * (1.0 - header_margin)
    anonymous_value_max = is_anonymous * value_max
    anonymous_value_margin = is_anonymous * value_margin
    confidence_product = header_max * value_max
    agreement_strength = agree * min(header_max, value_max)
    features.append(is_anonymous)
    features.append(null_ratio)
    features.append(unique_ratio)
    features.append(header_max)
    features.append(value_max)
    features.append(header_margin)
    features.append(value_margin)
    features.append(header_entropy)
    features.append(value_entropy)
    features.append(agree)
    features.append(value_stat_count)
    features.append(header_stat_count)
    features.append(code_like_header)
    features.append(header_missing)
    features.append(value_missing)
    features.append(value_when_header_weak)
    features.append(value_margin_when_header_weak)
    features.append(anonymous_value_max)
    features.append(anonymous_value_margin)
    features.append(confidence_product)
    features.append(agreement_strength)

    # --- Cross-rank reciprocity features ---
    # Measure how deeply the two branches disagree beyond simple top-1 match.
    h_arr = np.asarray(aligned_header, dtype=float)
    v_arr = np.asarray(aligned_value, dtype=float)
    n_c = len(h_arr)
    h_active = float(h_arr.sum()) > 0
    v_active = float(v_arr.sum()) > 0

    h_order = np.argsort(-h_arr)  # descending
    v_order = np.argsort(-v_arr)

    # Rank of header's top-1 concept in the value distribution (0=also top-1, 1=last)
    if h_active and v_active:
        v_ranks = np.argsort(np.argsort(-v_arr))  # rank position per concept
        header_top1_value_rank = float(v_ranks[h_order[0]]) / max(n_c - 1, 1)
    else:
        header_top1_value_rank = 1.0

    # Rank of value's top-1 concept in the header distribution
    if v_active and h_active:
        h_ranks = np.argsort(np.argsort(-h_arr))
        value_top1_header_rank = float(h_ranks[v_order[0]]) / max(n_c - 1, 1)
    else:
        value_top1_header_rank = 1.0

    # Top-2 cross match: does either branch's #2 match the other's #1?
    h_top1 = int(h_order[0]) if h_active else -1
    v_top1 = int(v_order[0]) if v_active else -1
    h_top2 = int(h_order[1]) if h_active and n_c > 1 else -1
    v_top2 = int(v_order[1]) if v_active and n_c > 1 else -1
    top2_cross_match = (
        1.0
        if ((h_top2 >= 0 and h_top2 == v_top1) or (v_top2 >= 0 and v_top2 == h_top1))
        else 0.0
    )

    # Both branches weak: explicit signal for low-confidence cases
    both_weak = 1.0 if header_max < 0.3 and value_max < 0.3 else 0.0

    features.append(header_top1_value_rank)
    features.append(value_top1_header_rank)
    features.append(top2_cross_match)
    features.append(both_weak)

    # --- Distributional shape features ---
    # Jensen-Shannon divergence: full distributional distance (0=identical, 1=max)
    if h_active and v_active:
        h_dist = h_arr / h_arr.sum()
        v_dist = v_arr / v_arr.sum()
        m_dist = 0.5 * (h_dist + v_dist)
        _eps = 1e-12
        kl_hm = float(np.sum(h_dist * np.log2((h_dist + _eps) / (m_dist + _eps))))
        kl_vm = float(np.sum(v_dist * np.log2((v_dist + _eps) / (m_dist + _eps))))
        js_divergence = float(np.clip(0.5 * (kl_hm + kl_vm), 0.0, 1.0))
    else:
        js_divergence = 1.0

    # Top-3 concept set overlap between branches (0-1)
    k = min(3, n_c)
    if h_active and v_active and k > 0:
        h_top3_set = set(h_order[:k].tolist())
        v_top3_set = set(v_order[:k].tolist())
        top3_overlap = len(h_top3_set & v_top3_set) / k
    else:
        top3_overlap = 0.0

    # Concentration gap: |top3_mass(header) - top3_mass(value)|
    h_top3_mass = float(np.sort(h_arr)[-k:].sum()) if h_active and k > 0 else 0.0
    v_top3_mass = float(np.sort(v_arr)[-k:].sum()) if v_active and k > 0 else 0.0
    concentration_gap = abs(h_top3_mass - v_top3_mass)

    features.append(js_divergence)
    features.append(top3_overlap)
    features.append(concentration_gap)

    return np.array(features, dtype=float)


def extract_fusion_features(
    record: dict,
    header_model,
    value_model,
    all_concepts: list[str],
) -> np.ndarray:
    """Extract fusion input: header proba + value proba + meta features."""
    aligned_header, aligned_value = extract_fusion_branch_probabilities(
        record,
        header_model,
        value_model,
        all_concepts,
    )
    metadata = extract_fusion_metadata(record)
    return compose_fusion_features(
        aligned_header, aligned_value, metadata, all_concepts
    )


def extract_fusion_features_batch(
    records: list[dict],
    header_model,
    value_model,
    all_concepts: list[str],
) -> np.ndarray:
    """Batch extraction of fusion features — same result as record-by-record but much faster."""
    aligned_header, aligned_value = extract_fusion_branch_probabilities_batch(
        records, header_model, value_model, all_concepts
    )
    metadata = extract_fusion_metadata_batch(records)
    features = []
    for i in range(len(records)):
        features.append(
            compose_fusion_features(
                aligned_header[i], aligned_value[i], metadata[i], all_concepts
            )
        )
    return np.array(features)


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
        "--gold-set", type=Path, default=ML_ROOT / "data" / "gold_set.json"
    )
    parser.add_argument(
        "--header-model",
        type=Path,
        default=ML_ROOT / "models" / "header_model.joblib",
    )
    parser.add_argument(
        "--value-model",
        type=Path,
        default=ML_ROOT / "models" / "value_model.joblib",
    )
    parser.add_argument(
        "--output", type=Path, default=ML_ROOT / "models" / "fusion_model.joblib"
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

    # Extract fusion features (batched for speed)
    logger.info("Extracting fusion features...")
    X = extract_fusion_features_batch(records, header_model, value_model, all_concepts)
    y = np.array([r["concept_coarse"] for r in records])
    groups = np.array([r["source_dataset"] for r in records])
    logger.info(f"Feature matrix shape: {X.shape}")

    # GroupKFold evaluation (leak-free: re-train branches per fold)
    logger.info("\n=== GroupKFold Evaluation (leak-free) ===")
    unique_groups = np.unique(groups)
    n_splits = min(5, len(unique_groups))

    if n_splits >= 2:
        from ml.scripts.train.train_header_model import build_pipeline, prepare_data
        from ml.scripts.train.train_value_model import (
            build_model as build_value_model,
            extract_value_features,
        )

        kfold = GroupKFold(n_splits=n_splits)
        f1_scores = []

        for fold, (train_idx, test_idx) in enumerate(kfold.split(y, groups=groups)):
            train_recs = [records[i] for i in train_idx]
            test_recs = [records[i] for i in test_idx]

            # Re-train header model on training fold
            header_recs = [r for r in train_recs if not r.get("is_anonymous")]
            names, concepts_h, _, _ = prepare_data(header_recs)
            if len(names) > 0:
                fold_header = build_pipeline()
                fold_header.fit(names, concepts_h)
            else:
                fold_header = None

            # Re-train value model on training fold
            X_val = np.array(
                [
                    extract_value_features(
                        r.get("values_sample", []), r.get("values_stats", {})
                    )
                    for r in train_recs
                ]
            )
            val_concepts = [r["concept_coarse"] for r in train_recs]
            fold_value = build_value_model()
            fold_value.fit(X_val, val_concepts)

            # Extract features with fold-specific branch models (batched)
            X_train_fold = extract_fusion_features_batch(
                train_recs, fold_header, fold_value, all_concepts
            )
            X_test_fold = extract_fusion_features_batch(
                test_recs, fold_header, fold_value, all_concepts
            )

            model = build_fusion_model()
            model.fit(X_train_fold, y[train_idx])
            preds = model.predict(X_test_fold)
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
