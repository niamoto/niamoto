#!/usr/bin/env python
"""
CLI metric script for ML model evaluation.

Outputs a single number to stdout for autoresearch compatibility.

Usage:
    uv run python -m scripts.ml.evaluate --model header --metric macro-f1
    uv run python -m scripts.ml.evaluate --model values --metric macro-f1
    uv run python -m scripts.ml.evaluate --model fusion --metric macro-f1
    uv run python -m scripts.ml.evaluate --model all    --metric macro-f1
"""

import argparse
import copy
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold

from scripts.ml.fusion_surrogate import (
    compute_gold_set_sha256,
    default_cache_dir,
)

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from niamoto.core.imports.ml.alias_registry import _normalize
from niamoto.core.imports.ml.fusion_features import is_code_like_header

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
PRIMARY_LANG_HOLDOUTS = ("fr", "es", "de")
INFO_STDERR_ENABLED = True
PROGRESS_ENABLED = False
FAST_PRODUCT_FAMILIES = ("tropical_field", "research_traits")
FAST_FAST_PRODUCT_FAMILIES = ("tropical_field", "research_traits")
PRODUCT_SCORE_WEIGHTS = {
    "tropical_field": 0.30,
    "research_traits": 0.15,
    "gbif_core_standard": 0.20,
    "gbif_extended": 0.10,
    "en_field": 0.15,
    "anonymous": 0.10,
}
FAST_FAST_PRODUCT_SCORE_WEIGHTS = {
    "tropical_field": 0.35,
    "research_traits": 0.20,
    "en_field": 0.20,
    "gbif_core_standard": 0.15,
    "anonymous": 0.10,
}
SURROGATE_FAST_WEIGHTS = FAST_FAST_PRODUCT_SCORE_WEIGHTS
SURROGATE_MID_WEIGHTS = PRODUCT_SCORE_WEIGHTS
SURROGATE_FAST_BUCKETS = (
    "tropical_field",
    "research_traits",
    "en_field",
    "gbif_core_standard",
    "anonymous",
)
SURROGATE_MID_BUCKETS = (
    "tropical_field",
    "research_traits",
    "gbif_core_standard",
    "gbif_extended",
    "en_field",
    "anonymous",
)
GBIF_CORE_STANDARD_HEADERS = {
    "acceptedScientificName",
    "basisOfRecord",
    "catalogNumber",
    "class",
    "collectionCode",
    "continent",
    "country",
    "countryCode",
    "day",
    "decimalLatitude",
    "decimalLongitude",
    "eventDate",
    "family",
    "gbifID",
    "genus",
    "institutionCode",
    "kingdom",
    "license",
    "locality",
    "month",
    "occurrenceID",
    "occurrenceStatus",
    "order",
    "phylum",
    "recordedBy",
    "scientificName",
    "specificEpithet",
    "taxonRank",
    "year",
}
_ANONYMOUS_NAME_POOL = (
    [f"col_{i}" for i in range(1, 1000)]
    + [f"X{i}" for i in range(1, 1000)]
    + [f"V{i}" for i in range(1, 1000)]
    + [f"field_{i}" for i in range(1, 1000)]
)


def _stderr(message: str) -> None:
    if INFO_STDERR_ENABLED:
        print(message, file=sys.stderr)


def _format_duration(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _format_metric(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _compute_weighted_score(
    values: dict[str, float | None], weights: dict[str, float]
) -> float:
    active = {
        name: (value, weights[name])
        for name, value in values.items()
        if name in weights and value is not None
    }
    if not active:
        return 0.0
    total_weight = sum(weight for _value, weight in active.values())
    if total_weight <= 0:
        return 0.0
    weighted_sum = sum(value * weight for value, weight in active.values())
    return weighted_sum / total_weight


def _compute_product_score(bucket_scores: dict[str, float | None]) -> float:
    return _compute_weighted_score(bucket_scores, PRODUCT_SCORE_WEIGHTS)


def _compute_product_score_fast_fast(bucket_scores: dict[str, float | None]) -> float:
    return _compute_weighted_score(bucket_scores, FAST_FAST_PRODUCT_SCORE_WEIGHTS)


def _compute_fusion_surrogate_fast_score(
    bucket_scores: dict[str, float | None],
) -> float:
    return _compute_weighted_score(bucket_scores, SURROGATE_FAST_WEIGHTS)


def _compute_fusion_surrogate_mid_score(
    bucket_scores: dict[str, float | None],
) -> float:
    return _compute_weighted_score(bucket_scores, SURROGATE_MID_WEIGHTS)


def _format_product_score_summary(
    final_score: float,
    bucket_scores: dict[str, float | None],
    *,
    label: str = "ProductScore",
) -> str:
    parts = [
        f"{label}={final_score:.3f}",
        f"tropical={_format_metric(bucket_scores.get('tropical_field'))}",
        f"research={_format_metric(bucket_scores.get('research_traits'))}",
        f"gbif_core={_format_metric(bucket_scores.get('gbif_core_standard'))}",
        f"gbif_ext={_format_metric(bucket_scores.get('gbif_extended'))}",
        f"en_field={_format_metric(bucket_scores.get('en_field'))}",
        f"anonymous={_format_metric(bucket_scores.get('anonymous'))}",
    ]
    return "  ".join(parts)


def _format_surrogate_score_summary(
    final_score: float,
    bucket_scores: dict[str, float | None],
    *,
    label: str,
    overall_macro_f1: float,
    false_count_rate: float | None,
) -> str:
    parts = [
        f"{label}={final_score:.3f}",
        f"overall_macro_f1={overall_macro_f1:.3f}",
        f"tropical={_format_metric(bucket_scores.get('tropical_field'))}",
        f"research={_format_metric(bucket_scores.get('research_traits'))}",
        f"gbif_core={_format_metric(bucket_scores.get('gbif_core_standard'))}",
        f"gbif_ext={_format_metric(bucket_scores.get('gbif_extended'))}",
        f"en_field={_format_metric(bucket_scores.get('en_field'))}",
        f"anonymous={_format_metric(bucket_scores.get('anonymous'))}",
        f"false_count_code_like={_format_metric(false_count_rate)}",
    ]
    return "  ".join(parts)


def _is_fast_product_objective(objective: str) -> bool:
    return objective in {
        "product-score-fast",
        "product-score-mid",
        "product-score-fast-fast",
    }


def _is_fastest_product_objective(objective: str) -> bool:
    return objective == "product-score-fast-fast"


def _is_mid_product_objective(objective: str) -> bool:
    return objective in {"product-score-fast", "product-score-mid"}


def _is_surrogate_objective(objective: str) -> bool:
    return objective in {"surrogate-fast", "surrogate-mid"}


class _ProgressTracker:
    """Small stderr progress logger with elapsed time and ETA."""

    def __init__(self, total_steps: int, label: str, *, enabled: bool | None = None):
        self.total_steps = max(total_steps, 1)
        self.label = label
        self.started_at = time.monotonic()
        self.completed_steps = 0
        self.enabled = PROGRESS_ENABLED if enabled is None else enabled

    def start(self, step_label: str) -> None:
        if not self.enabled:
            return
        elapsed = time.monotonic() - self.started_at
        _stderr(
            f"[{self.label}] step {self.completed_steps + 1}/{self.total_steps} "
            f"START {step_label} elapsed={_format_duration(elapsed)}"
        )

    def finish(self, step_label: str, detail: str = "") -> None:
        self.completed_steps += 1
        if not self.enabled:
            return
        elapsed = time.monotonic() - self.started_at
        avg = elapsed / self.completed_steps if self.completed_steps else 0.0
        remaining = max(self.total_steps - self.completed_steps, 0)
        eta = avg * remaining
        message = (
            f"[{self.label}] step {self.completed_steps}/{self.total_steps} "
            f"DONE {step_label} elapsed={_format_duration(elapsed)} "
            f"eta={_format_duration(eta)}"
        )
        if detail:
            message = f"{message} :: {detail}"
        _stderr(message)


def _load_records(gold_path: Path) -> list[dict]:
    with open(gold_path) as f:
        records = json.load(f)
    # Ignore persisted anonymous duplicates from older gold-set versions.
    return [r for r in records if not r.get("is_anonymous")]


def _is_real_record(record: dict) -> bool:
    quality = record.get("quality", "")
    source = record.get("source_dataset", "")
    return quality != "synthetic" and not str(source).startswith("synthetic_")


def _dataset_family(source_dataset: str) -> str:
    if source_dataset.startswith("gbif_"):
        return "dwc_gbif"
    if source_dataset.startswith(("ifn_", "fia_", "finland_")):
        return "forest_inventory"
    if source_dataset.startswith(("guyadiv_", "afrique_", "nc_", "pasoh_")):
        return "tropical_field"
    if source_dataset.startswith(("zenodo_", "berenty_", "iefc_", "afliber_")):
        return "research_traits"
    return "other"


def _forest_inventory_subfamily(source_dataset: str) -> str | None:
    if source_dataset.startswith("ifn_"):
        return "ifn_fr"
    if source_dataset.startswith("fia_"):
        return "fia_en"
    if source_dataset.startswith("finland_"):
        return "nordic_inventory"
    return None


def _is_gbif_core_standard_record(record: dict) -> bool:
    return str(record.get("source_dataset", "")).startswith("gbif_") and (
        record.get("column_name") in GBIF_CORE_STANDARD_HEADERS
    )


def _is_gbif_extended_record(record: dict) -> bool:
    return str(record.get("source_dataset", "")).startswith("gbif_") and not (
        _is_gbif_core_standard_record(record)
    )


def _is_coded_header_record(record: dict) -> bool:
    raw_name = str(record.get("column_name", ""))
    return bool(is_code_like_header(raw_name, _normalize(raw_name)))


def _is_en_standard_record(record: dict) -> bool:
    return record.get("language") == "en" and _is_gbif_core_standard_record(record)


def _is_en_field_record(record: dict) -> bool:
    return (
        record.get("language") == "en"
        and not record.get("is_anonymous", False)
        and not _is_en_standard_record(record)
    )


def _train_all_models(
    train_records: list[dict],
    all_concepts: list[str],
) -> tuple[object | None, object | None, object | None]:
    from scripts.ml.train_fusion import (
        build_fusion_model,
        extract_fusion_features_batch,
    )
    from scripts.ml.train_header_model import build_pipeline, prepare_data
    from scripts.ml.train_value_model import (
        build_model as build_value_model,
        extract_value_features,
    )

    header_records = [r for r in train_records if not r.get("is_anonymous")]
    header_model = None
    if header_records:
        names, concepts, _, _ = prepare_data(header_records)
        if names:
            header_model = build_pipeline()
            header_model.fit(names, concepts)

    value_model = None
    if train_records:
        X_val = np.array(
            [
                extract_value_features(
                    r.get("values_sample", []), r.get("values_stats", {})
                )
                for r in train_records
            ]
        )
        y_val = [r["concept_coarse"] for r in train_records]
        value_model = build_value_model()
        value_model.fit(X_val, y_val)

    fusion_model = None
    if train_records:
        X_fusion = extract_fusion_features_batch(
            train_records, header_model, value_model, all_concepts
        )
        y_fusion = [r["concept_coarse"] for r in train_records]
        fusion_model = build_fusion_model()
        fusion_model.fit(X_fusion, y_fusion)

    return header_model, value_model, fusion_model


def _predict_all_records(
    records: list[dict],
    *,
    header_model,
    value_model,
    fusion_model,
    all_concepts: list[str],
) -> tuple[list[str], list[float]]:
    from scripts.ml.train_fusion import extract_fusion_features_batch

    if not records or fusion_model is None:
        return [], []

    X = extract_fusion_features_batch(records, header_model, value_model, all_concepts)
    proba = fusion_model.predict_proba(X)
    classes = fusion_model.classes_
    indices = np.argmax(proba, axis=1)
    preds = [str(classes[idx]) for idx in indices]
    confidences = [float(proba[row, idx]) for row, idx in enumerate(indices)]
    return preds, confidences


def _to_labeled_columns(records: list[dict]):
    from scripts.ml.evaluation import LabeledColumn

    columns = []
    for record in records:
        concept = record["concept_coarse"]
        role = record.get("role_coarse") or (
            concept.split(".")[0] if "." in concept else concept
        )
        columns.append(
            LabeledColumn(
                column_name=record["column_name"],
                values=pd.Series(record.get("values_sample", [])),
                concept=concept,
                role=role,
                source_dataset=record["source_dataset"],
                language=record.get("language", "en"),
                is_anonymous=record.get("is_anonymous", False),
            )
        )
    return columns


def _build_anonymous_fold_records(
    test_records: list[dict],
    *,
    seed: int = 42,
) -> list[dict]:
    """Create anonymized copies of held-out records for leak-free evaluation."""
    if not test_records:
        return []

    rng = np.random.RandomState(seed)
    available_names = list(_ANONYMOUS_NAME_POOL)
    rng.shuffle(available_names)

    anonymized = []
    for idx, record in enumerate(test_records):
        clone = copy.deepcopy(record)
        clone["column_name"] = available_names[idx]
        clone["is_anonymous"] = True
        clone["quality"] = "eval_anonymous"
        clone["language"] = "en"
        anonymized.append(clone)
    return anonymized


def _report_subset_score(
    label: str,
    records: list[dict],
    preds: list[str],
    confs: list[float],
    predicate,
) -> float | None:
    from scripts.ml.evaluation import compute_niamoto_offline_score

    subset = [
        (record, pred, conf)
        for record, pred, conf in zip(records, preds, confs)
        if predicate(record)
    ]
    if not subset:
        return None

    subset_records = [record for record, _pred, _conf in subset]
    subset_preds = [pred for _record, pred, _conf in subset]
    subset_confs = [conf for _record, _pred, conf in subset]
    score = compute_niamoto_offline_score(
        _to_labeled_columns(subset_records), subset_preds, subset_confs
    )
    _stderr(f"{label}: {score.summary()}")
    return float(score.final_score)


def _evaluate_holdout_score(
    test_records: list[dict],
    train_records: list[dict],
    all_concepts: list[str],
    *,
    return_models: bool = False,
):
    from scripts.ml.evaluation import compute_niamoto_offline_score

    header_model, value_model, fusion_model = _train_all_models(
        train_records, all_concepts
    )
    preds, confs = _predict_all_records(
        test_records,
        header_model=header_model,
        value_model=value_model,
        fusion_model=fusion_model,
        all_concepts=all_concepts,
    )
    score = compute_niamoto_offline_score(
        _to_labeled_columns(test_records), preds, confs
    )
    if return_models:
        return score, preds, confs, (header_model, value_model, fusion_model)
    return score, preds, confs


def evaluate_niamoto_protocol(
    gold_path: Path,
    n_splits: int = 5,
    *,
    objective: str = "niamoto-score",
) -> float:
    """Evaluate the end-to-end stack with the Niamoto offline protocol."""
    from scripts.ml.evaluation import compute_niamoto_offline_score

    records = _load_records(gold_path)
    real_records = [
        r for r in records if _is_real_record(r) and not r.get("is_anonymous")
    ]
    synthetic_records = [
        r for r in records if not _is_real_record(r) and not r.get("is_anonymous")
    ]
    all_concepts = sorted(set(r["concept_coarse"] for r in records))

    if not real_records:
        return 0.0

    groups = np.array([r["source_dataset"] for r in real_records])
    unique = np.unique(groups)
    splits = min(n_splits, len(unique))
    if splits < 2:
        return 0.0

    fast_product = _is_fast_product_objective(objective)
    fast_fast_product = _is_fastest_product_objective(objective)
    mid_product = _is_mid_product_objective(objective)
    kfold = GroupKFold(n_splits=splits)
    indices = np.arange(len(real_records))
    families = sorted({_dataset_family(r["source_dataset"]) for r in real_records})
    families = [family for family in families if family != "other"]
    if fast_fast_product:
        families = [
            family for family in families if family in FAST_FAST_PRODUCT_FAMILIES
        ]
    elif fast_product:
        families = [family for family in families if family in FAST_PRODUCT_FAMILIES]
    available_langs = [
        lang
        for lang in PRIMARY_LANG_HOLDOUTS
        if any(r.get("language") == lang for r in real_records)
    ]
    if fast_product:
        available_langs = []
    has_anonymous = bool(real_records)
    has_synthetic = bool(synthetic_records)
    if fast_product:
        has_synthetic = False
    subset_holdouts = 0
    if fast_fast_product:
        subset_holdouts = 2
    total_steps = (
        (0 if fast_fast_product else splits)
        + len(available_langs)
        + len(families)
        + subset_holdouts
    )
    if has_anonymous:
        total_steps += 1
    if has_synthetic:
        total_steps += 1
    progress = _ProgressTracker(
        total_steps,
        "product-score-fast-fast"
        if fast_fast_product
        else (
            "product-score-mid"
            if mid_product
            else ("product-score-fast" if fast_product else "niamoto-score")
        ),
    )
    oof_records: list[dict] = []
    oof_preds: list[str] = []
    oof_confs: list[float] = []
    product_buckets: dict[str, float | None] = {
        "tropical_field": None,
        "research_traits": None,
        "gbif_core_standard": None,
        "gbif_extended": None,
        "en_field": None,
        "anonymous": None,
    }

    primary = None
    if not fast_fast_product:
        for fold_idx, (train_idx, test_idx) in enumerate(
            kfold.split(indices, groups=groups), start=1
        ):
            step_label = (
                f"primary_fold[{fold_idx}] train={len(train_idx)} test={len(test_idx)}"
            )
            progress.start(step_label)
            real_train = [real_records[i] for i in train_idx]
            real_test = [real_records[i] for i in test_idx]
            train_records = synthetic_records + real_train

            header_model, value_model, fusion_model = _train_all_models(
                train_records, all_concepts
            )
            preds, confs = _predict_all_records(
                real_test,
                header_model=header_model,
                value_model=value_model,
                fusion_model=fusion_model,
                all_concepts=all_concepts,
            )
            oof_records.extend(real_test)
            oof_preds.extend(preds)
            oof_confs.extend(confs)
            progress.finish(step_label, f"predictions={len(preds)}")

        primary = compute_niamoto_offline_score(
            _to_labeled_columns(oof_records), oof_preds, oof_confs
        )
        _stderr(f"primary: {primary.summary()}")
        _report_subset_score(
            "diagnostic_subset[en_standard]",
            oof_records,
            oof_preds,
            oof_confs,
            _is_en_standard_record,
        )
        product_buckets["en_field"] = _report_subset_score(
            "diagnostic_subset[en_field]",
            oof_records,
            oof_preds,
            oof_confs,
            _is_en_field_record,
        )
        _report_subset_score(
            "diagnostic_subset[coded_headers]",
            oof_records,
            oof_preds,
            oof_confs,
            _is_coded_header_record,
        )
        product_buckets["gbif_core_standard"] = _report_subset_score(
            "diagnostic_subset[gbif_core_standard]",
            oof_records,
            oof_preds,
            oof_confs,
            _is_gbif_core_standard_record,
        )
        product_buckets["gbif_extended"] = _report_subset_score(
            "diagnostic_subset[gbif_extended]",
            oof_records,
            oof_preds,
            oof_confs,
            _is_gbif_extended_record,
        )
    else:
        subset_specs = (
            ("holdout_subset[en_field]", "en_field", _is_en_field_record),
            (
                "holdout_subset[gbif_core_standard]",
                "gbif_core_standard",
                _is_gbif_core_standard_record,
            ),
        )
        for step_label, bucket_name, predicate in subset_specs:
            progress.start(step_label)
            test_records = [r for r in real_records if predicate(r)]
            train_records = synthetic_records + [
                r for r in real_records if not predicate(r)
            ]
            score, _preds, _confs = _evaluate_holdout_score(
                test_records,
                train_records,
                all_concepts,
            )
            product_buckets[bucket_name] = float(score.final_score)
            _stderr(f"{step_label}: {score.summary()}")
            progress.finish(step_label, score.summary())

    for lang in available_langs:
        step_label = f"holdout_lang[{lang}]"
        progress.start(step_label)
        test_records = [r for r in real_records if r.get("language") == lang]
        train_records = synthetic_records + [
            r for r in real_records if r.get("language") != lang
        ]
        score, preds, confs = _evaluate_holdout_score(
            test_records,
            train_records,
            all_concepts,
        )
        _stderr(f"holdout_lang[{lang}]: {score.summary()}")
        progress.finish(step_label, score.summary())

    for family in families:
        step_label = f"holdout_family[{family}]"
        progress.start(step_label)
        test_records = [
            r for r in real_records if _dataset_family(r["source_dataset"]) == family
        ]
        train_records = synthetic_records + [
            r for r in real_records if _dataset_family(r["source_dataset"]) != family
        ]
        score, preds, confs = _evaluate_holdout_score(
            test_records,
            train_records,
            all_concepts,
        )
        _stderr(f"holdout_family[{family}]: {score.summary()}")
        if family in {"research_traits", "tropical_field"}:
            product_buckets[family] = float(score.final_score)
        if family == "forest_inventory" and not fast_fast_product:
            for subfamily in ("ifn_fr", "fia_en", "nordic_inventory"):
                _report_subset_score(
                    f"holdout_family[{family}/{subfamily}]",
                    test_records,
                    preds,
                    confs,
                    lambda record, subfamily=subfamily: (
                        _forest_inventory_subfamily(record["source_dataset"])
                        == subfamily
                    ),
                )
        if family == "dwc_gbif" and not fast_fast_product:
            _report_subset_score(
                "holdout_family[dwc_gbif/core_standard]",
                test_records,
                preds,
                confs,
                _is_gbif_core_standard_record,
            )
            _report_subset_score(
                "holdout_family[dwc_gbif/extended]",
                test_records,
                preds,
                confs,
                _is_gbif_extended_record,
            )
        progress.finish(step_label, score.summary())

    if has_anonymous:
        step_label = "holdout_anonymous"
        progress.start(step_label)
        anon_oof_records: list[dict] = []
        anon_oof_preds: list[str] = []
        anon_oof_confs: list[float] = []
        anon_correct = 0
        anon_total = 0

        for fold_idx, (train_idx, test_idx) in enumerate(
            kfold.split(indices, groups=groups), start=1
        ):
            real_train = [real_records[i] for i in train_idx]
            real_test = [real_records[i] for i in test_idx]
            anonymous_test = _build_anonymous_fold_records(
                real_test, seed=42 + fold_idx
            )
            train_records = synthetic_records + real_train
            (
                _score,
                preds,
                confs,
                (_, value_model, _),
            ) = _evaluate_holdout_score(
                anonymous_test,
                train_records,
                all_concepts,
                return_models=True,
            )
            anon_oof_records.extend(anonymous_test)
            anon_oof_preds.extend(preds)
            anon_oof_confs.extend(confs)

            if value_model is not None:
                from scripts.ml.train_value_model import extract_value_features

                X_val_test = np.array(
                    [
                        extract_value_features(
                            r.get("values_sample", []), r.get("values_stats", {})
                        )
                        for r in anonymous_test
                    ]
                )
                y_true = [r["concept_coarse"] for r in anonymous_test]
                y_pred = value_model.predict(X_val_test)
                anon_correct += sum(1 for t, p in zip(y_true, y_pred) if t == p)
                anon_total += len(y_true)

        score = compute_niamoto_offline_score(
            _to_labeled_columns(anon_oof_records), anon_oof_preds, anon_oof_confs
        )
        _stderr(f"holdout_anonymous: {score.summary()}")
        product_buckets["anonymous"] = float(score.final_score)

        # Values-only diagnostic (not in ProductScore)
        if anon_total:
            values_accuracy = anon_correct / anon_total
            _stderr(
                f"holdout_anonymous_values_only: "
                f"accuracy={values_accuracy:.1%} "
                f"({anon_correct}/{anon_total})"
            )

        progress.finish(step_label, score.summary())

    if synthetic_records and not fast_product:
        step_label = "diagnostic_synthetic"
        progress.start(step_label)
        train_records = real_records
        header_model, value_model, fusion_model = _train_all_models(
            train_records, all_concepts
        )
        preds, confs = _predict_all_records(
            synthetic_records,
            header_model=header_model,
            value_model=value_model,
            fusion_model=fusion_model,
            all_concepts=all_concepts,
        )
        score = compute_niamoto_offline_score(
            _to_labeled_columns(synthetic_records), preds, confs
        )
        _stderr(f"diagnostic_synthetic: {score.summary()}")
        progress.finish(step_label, score.summary())

    product_score = (
        _compute_product_score_fast_fast(product_buckets)
        if fast_fast_product
        else _compute_product_score(product_buckets)
    )
    _stderr(
        _format_product_score_summary(
            product_score,
            product_buckets,
            label=(
                "ProductScoreFastFast"
                if fast_fast_product
                else (
                    "ProductScoreMid"
                    if objective == "product-score-mid"
                    else ("ProductScoreFast" if fast_product else "ProductScore")
                )
            ),
        )
    )

    if objective in {
        "product-score",
        "product-score-fast",
        "product-score-mid",
        "product-score-fast-fast",
    }:
        return float(product_score)
    return float(primary.final_score if primary is not None else 0.0)


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
    progress = _ProgressTracker(splits, "header")

    scores = []
    for fold_idx, (train_idx, test_idx) in enumerate(
        kfold.split(names_arr, groups=groups), start=1
    ):
        step_label = f"fold[{fold_idx}] train={len(train_idx)} test={len(test_idx)}"
        progress.start(step_label)
        pipe = build_pipeline()
        pipe.fit(names_arr[train_idx].tolist(), concepts_arr[train_idx].tolist())
        preds = pipe.predict(names_arr[test_idx].tolist())
        score = f1_score(
            concepts_arr[test_idx], preds, average="macro", zero_division=0
        )
        scores.append(score)
        progress.finish(step_label, f"macro_f1={score:.4f}")

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
    progress = _ProgressTracker(splits, "values")

    scores = []
    for fold_idx, (train_idx, test_idx) in enumerate(
        kfold.split(X, groups=groups), start=1
    ):
        step_label = f"fold[{fold_idx}] train={len(train_idx)} test={len(test_idx)}"
        progress.start(step_label)
        model = build_model()
        model.fit(X[train_idx], concepts_arr[train_idx])
        preds = model.predict(X[test_idx])
        score = f1_score(
            concepts_arr[test_idx], preds, average="macro", zero_division=0
        )
        scores.append(score)
        progress.finish(step_label, f"macro_f1={score:.4f}")

    return float(np.mean(scores))


def evaluate_fusion(gold_path: Path, n_splits: int = 5) -> float:
    """Evaluate fusion model via GroupKFold (leak-free).

    Re-trains header and value branch models inside each fold so that
    test-fold records are never seen by the branch models that produce
    the fusion input features.
    """
    from scripts.ml.train_fusion import (
        build_fusion_model,
        extract_fusion_features,
    )
    from scripts.ml.train_header_model import build_pipeline, prepare_data
    from scripts.ml.train_value_model import (
        build_model as build_value_model,
        extract_value_features,
    )

    with open(gold_path) as f:
        records = json.load(f)

    all_concepts = sorted(set(r["concept_coarse"] for r in records))
    y = np.array([r["concept_coarse"] for r in records])
    groups = np.array([r["source_dataset"] for r in records])

    unique = np.unique(groups)
    splits = min(n_splits, len(unique))
    if splits < 2:
        return 0.0

    kfold = GroupKFold(n_splits=splits)
    scores = []
    progress = _ProgressTracker(splits, "fusion")

    for fold_idx, (train_idx, test_idx) in enumerate(
        kfold.split(y, groups=groups), start=1
    ):
        step_label = f"fold[{fold_idx}] train={len(train_idx)} test={len(test_idx)}"
        progress.start(step_label)
        train_records = [records[i] for i in train_idx]
        test_records = [records[i] for i in test_idx]

        # Re-train header model on training fold only
        header_train = [r for r in train_records if not r.get("is_anonymous")]
        names, concepts, _, _ = prepare_data(header_train)
        if len(names) > 0:
            header_model = build_pipeline()
            header_model.fit(names, concepts)
        else:
            header_model = None

        # Re-train value model on training fold only
        X_val = np.array(
            [
                extract_value_features(
                    r.get("values_sample", []), r.get("values_stats", {})
                )
                for r in train_records
            ]
        )
        val_concepts = [r["concept_coarse"] for r in train_records]
        value_model = build_value_model()
        value_model.fit(X_val, val_concepts)

        # Extract fusion features with fold-specific branch models
        X_train = np.array(
            [
                extract_fusion_features(r, header_model, value_model, all_concepts)
                for r in train_records
            ]
        )
        X_test = np.array(
            [
                extract_fusion_features(r, header_model, value_model, all_concepts)
                for r in test_records
            ]
        )

        model = build_fusion_model()
        model.fit(X_train, y[train_idx])
        preds = model.predict(X_test)
        score = f1_score(y[test_idx], preds, average="macro", zero_division=0)
        scores.append(score)
        progress.finish(step_label, f"macro_f1={score:.4f}")

    return float(np.mean(scores))


def _compute_bucket_macro_f1(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    mask: np.ndarray,
) -> float | None:
    if mask.size == 0 or not np.any(mask):
        return None
    return float(
        f1_score(
            y_true[mask],
            y_pred[mask],
            average="macro",
            zero_division=0,
        )
        * 100.0
    )


def _compose_fusion_matrix(
    header_proba: np.ndarray,
    value_proba: np.ndarray,
    metadata: np.ndarray,
    all_concepts: list[str],
) -> np.ndarray:
    from scripts.ml.train_fusion import compose_fusion_features

    return np.array(
        [
            compose_fusion_features(h, v, meta, all_concepts)
            for h, v, meta in zip(header_proba, value_proba, metadata)
        ],
        dtype=float,
    )


def evaluate_fusion_surrogate(
    gold_path: Path,
    *,
    cache_dir: Path | None = None,
    n_splits: int = 3,
    objective: str = "surrogate-fast",
) -> float:
    from scripts.ml.train_fusion import build_fusion_model

    resolved_cache_dir = cache_dir or default_cache_dir(gold_path, n_splits)
    manifest_path = resolved_cache_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            "Fusion surrogate cache not found. Build it with: "
            "uv run python -m scripts.ml.build_fusion_surrogate_cache "
            f"--gold-set {gold_path} --splits {n_splits}"
        )

    with manifest_path.open() as handle:
        manifest = json.load(handle)

    current_hash = compute_gold_set_sha256(gold_path)
    if manifest.get("gold_sha256") != current_hash:
        raise ValueError(
            "Fusion surrogate cache is stale for this gold set. Rebuild it with: "
            "uv run python -m scripts.ml.build_fusion_surrogate_cache "
            f"--gold-set {gold_path} --splits {manifest.get('splits', n_splits)}"
        )

    all_concepts = list(manifest["all_concepts"])
    bucket_order = (
        SURROGATE_FAST_BUCKETS
        if objective == "surrogate-fast"
        else SURROGATE_MID_BUCKETS
    )
    progress = _ProgressTracker(
        len(manifest["folds"]),
        "surrogate-fast" if objective == "surrogate-fast" else "surrogate-mid",
    )
    y_true_parts: list[np.ndarray] = []
    y_pred_parts: list[np.ndarray] = []
    bucket_masks: dict[str, list[np.ndarray]] = {
        name: [] for name in (*SURROGATE_MID_BUCKETS, "coded_headers")
    }

    for fold in manifest["folds"]:
        step_label = str(fold["file"])
        progress.start(step_label)
        fold_path = resolved_cache_dir / fold["file"]
        data = np.load(fold_path, allow_pickle=True)
        X_train = _compose_fusion_matrix(
            data["train_header_proba"],
            data["train_value_proba"],
            data["train_metadata"],
            all_concepts,
        )
        X_test = _compose_fusion_matrix(
            data["test_header_proba"],
            data["test_value_proba"],
            data["test_metadata"],
            all_concepts,
        )
        y_train = data["train_labels"].astype(str)
        y_test = data["test_labels"].astype(str)
        model = build_fusion_model()
        model.fit(X_train, y_train)
        preds = model.predict(X_test).astype(str)
        y_true_parts.append(y_test)
        y_pred_parts.append(preds)
        for name in bucket_masks:
            bucket_masks[name].append(data[f"test_bucket_{name}"].astype(bool))
        fold_score = f1_score(y_test, preds, average="macro", zero_division=0)
        progress.finish(step_label, f"macro_f1={fold_score:.4f}")

    y_true = (
        np.concatenate(y_true_parts) if y_true_parts else np.array([], dtype=object)
    )
    y_pred = (
        np.concatenate(y_pred_parts) if y_pred_parts else np.array([], dtype=object)
    )
    overall_macro_f1 = (
        float(f1_score(y_true, y_pred, average="macro", zero_division=0) * 100.0)
        if len(y_true)
        else 0.0
    )
    bucket_scores = {
        name: _compute_bucket_macro_f1(
            y_true,
            y_pred,
            np.concatenate(bucket_masks[name]),
        )
        for name in bucket_order
    }
    coded_mask = np.concatenate(bucket_masks["coded_headers"])
    false_count_rate = None
    if coded_mask.size and np.any(coded_mask):
        coded_true = y_true[coded_mask]
        coded_pred = y_pred[coded_mask]
        false_count_rate = float(
            np.mean(
                (coded_pred == "statistic.count") & (coded_true != "statistic.count")
            )
        )

    final_score = (
        _compute_fusion_surrogate_fast_score(bucket_scores)
        if objective == "surrogate-fast"
        else _compute_fusion_surrogate_mid_score(bucket_scores)
    )
    _stderr(
        _format_surrogate_score_summary(
            final_score,
            bucket_scores,
            label=(
                "FusionSurrogateFast"
                if objective == "surrogate-fast"
                else "FusionSurrogateMid"
            ),
            overall_macro_f1=overall_macro_f1,
            false_count_rate=false_count_rate,
        )
    )
    return float(final_score)


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
        choices=[
            "macro-f1",
            "niamoto-score",
            "product-score",
            "product-score-fast",
            "product-score-mid",
            "product-score-fast-fast",
            "surrogate-fast",
            "surrogate-mid",
        ],
        default="macro-f1",
    )
    parser.add_argument(
        "--gold-set",
        type=Path,
        default=ROOT / "data" / "gold_set.json",
    )
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational stderr output and keep stdout score only",
    )
    parser.add_argument(
        "--verbose-progress",
        action="store_true",
        help="Force detailed progress logging on stderr",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Optional cache dir for fusion surrogate metrics",
    )
    args = parser.parse_args()

    global INFO_STDERR_ENABLED, PROGRESS_ENABLED
    INFO_STDERR_ENABLED = not args.quiet
    PROGRESS_ENABLED = args.verbose_progress or (
        INFO_STDERR_ENABLED and sys.stderr.isatty()
    )

    if not args.gold_set.exists():
        _stderr("0.0000")
        print("0.0000")
        sys.exit(1)

    if args.metric in {
        "niamoto-score",
        "product-score",
        "product-score-fast",
        "product-score-mid",
        "product-score-fast-fast",
    }:
        if args.model != "all":
            print(
                f"{args.metric} is currently only supported with --model all",
                file=sys.stderr,
            )
            sys.exit(2)
        score = evaluate_niamoto_protocol(
            args.gold_set,
            args.splits,
            objective=args.metric,
        )
    elif args.metric in {"surrogate-fast", "surrogate-mid"}:
        if args.model != "fusion":
            print(
                f"{args.metric} is currently only supported with --model fusion",
                file=sys.stderr,
            )
            sys.exit(2)
        score = evaluate_fusion_surrogate(
            args.gold_set,
            cache_dir=args.cache_dir,
            n_splits=args.splits,
            objective=args.metric,
        )
    else:
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
            _stderr(f"header={h:.4f} values={v:.4f} fusion={f:.4f}")

    print(f"{score:.4f}")


if __name__ == "__main__":
    main()
