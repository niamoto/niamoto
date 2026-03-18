#!/usr/bin/env python
"""Build cached branch outputs for the fusion-only surrogate loop."""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupKFold

from scripts.ml.evaluate import (
    _dataset_family,
    _is_en_field_record,
    _is_gbif_core_standard_record,
    _is_gbif_extended_record,
    _is_real_record,
    _load_records,
)
from scripts.ml.fusion_surrogate import (
    CACHE_VERSION,
    compute_gold_set_sha256,
    default_cache_dir,
)
from scripts.ml.train_fusion import (
    FUSION_META_FEATURE_NAMES,
    extract_fusion_branch_probabilities_batch,
    extract_fusion_metadata,
    extract_fusion_metadata_batch,
)
from scripts.ml.train_header_model import build_pipeline, prepare_data
from scripts.ml.train_value_model import (
    build_model as build_value_model,
    extract_value_features,
)


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
SURROGATE_BUCKETS = (
    "tropical_field",
    "research_traits",
    "en_field",
    "gbif_core_standard",
    "gbif_extended",
    "anonymous",
    "coded_headers",
)


def _bucket_flags(record: dict) -> dict[str, bool]:
    family = _dataset_family(str(record["source_dataset"]))
    return {
        "tropical_field": family == "tropical_field",
        "research_traits": family == "research_traits",
        "en_field": _is_en_field_record(record),
        "gbif_core_standard": _is_gbif_core_standard_record(record),
        "gbif_extended": _is_gbif_extended_record(record),
        "anonymous": bool(record.get("is_anonymous", False)),
        "coded_headers": bool(extract_fusion_metadata(record)[-1]),
    }


def _train_branch_models(train_records: list[dict]):
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
                    r.get("values_sample", []),
                    r.get("values_stats", {}),
                )
                for r in train_records
            ]
        )
        y_val = [r["concept_coarse"] for r in train_records]
        value_model = build_value_model()
        value_model.fit(X_val, y_val)

    return header_model, value_model


def _build_payload(
    records: list[dict],
    *,
    header_model,
    value_model,
    all_concepts: list[str],
    include_buckets: bool,
) -> dict[str, np.ndarray]:
    payload: dict[str, np.ndarray | list[bool] | list[str]] = {}
    bucket_values = {name: [] for name in SURROGATE_BUCKETS}

    header_proba, value_proba = extract_fusion_branch_probabilities_batch(
        records,
        header_model,
        value_model,
        all_concepts,
    )
    payload["header_proba"] = header_proba
    payload["value_proba"] = value_proba
    payload["metadata"] = extract_fusion_metadata_batch(records)
    payload["labels"] = np.array(
        [record["concept_coarse"] for record in records],
        dtype=object,
    )
    if include_buckets:
        for record in records:
            flags = _bucket_flags(record)
            for name in SURROGATE_BUCKETS:
                bucket_values[name].append(flags[name])
        for name, values in bucket_values.items():
            payload[f"bucket_{name}"] = np.array(values, dtype=bool)
    return payload  # type: ignore[return-value]


def build_cache(gold_path: Path, output_dir: Path, n_splits: int) -> Path:
    records = _load_records(gold_path)
    real_records = [r for r in records if _is_real_record(r)]
    synthetic_records = [r for r in records if not _is_real_record(r)]
    all_concepts = sorted(set(r["concept_coarse"] for r in records))

    if not real_records:
        raise ValueError("No real records available to build the surrogate cache")

    groups = np.array([r["source_dataset"] for r in real_records])
    unique_groups = np.unique(groups)
    splits = min(n_splits, len(unique_groups))
    if splits < 2:
        raise ValueError("Need at least 2 dataset groups to build surrogate cache")

    output_dir.mkdir(parents=True, exist_ok=True)
    for old_fold in output_dir.glob("fold_*.npz"):
        old_fold.unlink()

    kfold = GroupKFold(n_splits=splits)
    fold_summaries = []
    started_at = time.monotonic()

    for fold_idx, (train_idx, test_idx) in enumerate(
        kfold.split(np.arange(len(real_records)), groups=groups),
        start=1,
    ):
        fold_started_at = time.monotonic()
        real_train = [real_records[i] for i in train_idx]
        real_test = [real_records[i] for i in test_idx]
        train_records = synthetic_records + real_train
        logger.info(
            "Building fold %s/%s (train=%s test=%s)",
            fold_idx,
            splits,
            len(train_records),
            len(real_test),
        )
        header_model, value_model = _train_branch_models(train_records)

        train_payload = _build_payload(
            train_records,
            header_model=header_model,
            value_model=value_model,
            all_concepts=all_concepts,
            include_buckets=False,
        )
        test_payload = _build_payload(
            real_test,
            header_model=header_model,
            value_model=value_model,
            all_concepts=all_concepts,
            include_buckets=True,
        )

        fold_path = output_dir / f"fold_{fold_idx:02d}.npz"
        np.savez_compressed(
            fold_path,
            train_header_proba=train_payload["header_proba"],
            train_value_proba=train_payload["value_proba"],
            train_metadata=train_payload["metadata"],
            train_labels=train_payload["labels"],
            test_header_proba=test_payload["header_proba"],
            test_value_proba=test_payload["value_proba"],
            test_metadata=test_payload["metadata"],
            test_labels=test_payload["labels"],
            **{
                f"test_bucket_{name}": test_payload[f"bucket_{name}"]
                for name in SURROGATE_BUCKETS
            },
        )
        fold_summaries.append(
            {
                "file": fold_path.name,
                "train_samples": int(len(train_records)),
                "test_samples": int(len(real_test)),
                "elapsed_seconds": round(time.monotonic() - fold_started_at, 3),
            }
        )
        logger.info(
            "Built %s (train=%s test=%s elapsed=%0.1fs)",
            fold_path.name,
            len(train_records),
            len(real_test),
            time.monotonic() - fold_started_at,
        )

    manifest = {
        "cache_version": CACHE_VERSION,
        "gold_set": str(gold_path),
        "gold_sha256": compute_gold_set_sha256(gold_path),
        "splits": splits,
        "all_concepts": all_concepts,
        "metadata_features": list(FUSION_META_FEATURE_NAMES),
        "test_buckets": list(SURROGATE_BUCKETS),
        "folds": fold_summaries,
    }
    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("w") as handle:
        json.dump(manifest, handle, indent=2)
    logger.info(
        "Wrote manifest to %s (elapsed=%0.1fs)",
        manifest_path,
        time.monotonic() - started_at,
    )
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build fusion surrogate cache")
    parser.add_argument(
        "--gold-set",
        type=Path,
        default=ROOT / "data" / "gold_set.json",
    )
    parser.add_argument("--splits", type=int, default=3)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir or default_cache_dir(args.gold_set, args.splits)
    cache_dir = build_cache(args.gold_set, output_dir, args.splits)
    print(cache_dir)


if __name__ == "__main__":
    main()
