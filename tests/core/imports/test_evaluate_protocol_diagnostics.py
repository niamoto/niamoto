import json

import numpy as np
import pytest

from scripts.ml.evaluate import (
    _compute_fusion_surrogate_fast_score,
    _compute_fusion_surrogate_mid_score,
    _compute_product_score,
    _compute_product_score_fast_fast,
    _forest_inventory_subfamily,
    _format_product_score_summary,
    _is_fastest_product_objective,
    _is_fast_product_objective,
    _is_mid_product_objective,
    _is_coded_header_record,
    _is_en_field_record,
    _is_en_standard_record,
    _is_gbif_core_standard_record,
    _is_gbif_extended_record,
    _is_surrogate_objective,
    evaluate_fusion_surrogate,
)
from scripts.ml.fusion_surrogate import compute_gold_set_sha256


def test_forest_inventory_subfamily_mapping():
    assert _forest_inventory_subfamily("ifn_arbre") == "ifn_fr"
    assert _forest_inventory_subfamily("fia_tree") == "fia_en"
    assert _forest_inventory_subfamily("finland_trees") == "nordic_inventory"
    assert _forest_inventory_subfamily("gbif_france_ifn") is None


def test_gbif_core_vs_extended_record_detection():
    core = {
        "source_dataset": "gbif_china_herbarium",
        "column_name": "acceptedScientificName",
        "language": "en",
    }
    extended = {
        "source_dataset": "gbif_china_herbarium",
        "column_name": "habitat",
        "language": "en",
    }

    assert _is_gbif_core_standard_record(core) is True
    assert _is_gbif_extended_record(core) is False
    assert _is_gbif_core_standard_record(extended) is False
    assert _is_gbif_extended_record(extended) is True


def test_english_standard_vs_field_detection():
    en_standard = {
        "source_dataset": "gbif_china_herbarium",
        "column_name": "eventDate",
        "language": "en",
        "is_anonymous": False,
    }
    en_field = {
        "source_dataset": "fia_tree",
        "column_name": "AGENTCD",
        "language": "en",
        "is_anonymous": False,
    }

    assert _is_en_standard_record(en_standard) is True
    assert _is_en_field_record(en_standard) is False
    assert _is_en_standard_record(en_field) is False
    assert _is_en_field_record(en_field) is True


def test_coded_header_detection_for_record():
    coded = {"column_name": "COUNTYCD"}
    readable = {"column_name": "acceptedScientificName"}

    assert _is_coded_header_record(coded) is True
    assert _is_coded_header_record(readable) is False


def test_product_score_uses_target_buckets():
    bucket_scores = {
        "tropical_field": 60.0,
        "research_traits": 70.0,
        "gbif_core_standard": 90.0,
        "gbif_extended": 80.0,
        "en_field": 75.0,
        "anonymous": 100.0,
    }

    score = _compute_product_score(bucket_scores)

    assert score == pytest.approx(75.75)


def test_product_score_reweights_when_bucket_missing():
    bucket_scores = {
        "tropical_field": 60.0,
        "research_traits": None,
        "gbif_core_standard": 90.0,
        "gbif_extended": 80.0,
        "en_field": 75.0,
        "anonymous": 100.0,
    }

    score = _compute_product_score(bucket_scores)

    assert score == pytest.approx(76.76470588235294)


def test_product_score_summary_format():
    summary = _format_product_score_summary(
        77.25,
        {
            "tropical_field": 60.0,
            "research_traits": 70.0,
            "gbif_core_standard": 90.0,
            "gbif_extended": 80.0,
            "en_field": 75.0,
            "anonymous": 100.0,
        },
    )

    assert "ProductScore=77.250" in summary
    assert "tropical=60.000" in summary
    assert "anonymous=100.000" in summary


def test_product_score_fast_objective_detection():
    assert _is_fast_product_objective("product-score-fast") is True
    assert _is_fast_product_objective("product-score-mid") is True
    assert _is_fast_product_objective("product-score-fast-fast") is True
    assert _is_fast_product_objective("product-score") is False


def test_product_score_fast_fast_objective_detection():
    assert _is_fastest_product_objective("product-score-fast-fast") is True
    assert _is_fastest_product_objective("product-score-fast") is False


def test_product_score_mid_objective_detection():
    assert _is_mid_product_objective("product-score-mid") is True
    assert _is_mid_product_objective("product-score-fast") is True
    assert _is_mid_product_objective("product-score-fast-fast") is False


def test_product_score_fast_fast_uses_target_buckets():
    bucket_scores = {
        "tropical_field": 60.0,
        "research_traits": 70.0,
        "en_field": 75.0,
        "gbif_core_standard": 90.0,
        "anonymous": 100.0,
    }

    score = _compute_product_score_fast_fast(bucket_scores)

    assert score == pytest.approx(73.5)


def test_surrogate_objective_detection():
    assert _is_surrogate_objective("surrogate-fast") is True
    assert _is_surrogate_objective("surrogate-mid") is True
    assert _is_surrogate_objective("product-score") is False


def test_fusion_surrogate_scores_use_expected_weights():
    fast_buckets = {
        "tropical_field": 60.0,
        "research_traits": 70.0,
        "en_field": 75.0,
        "gbif_core_standard": 90.0,
        "anonymous": 100.0,
    }
    mid_buckets = {
        "tropical_field": 60.0,
        "research_traits": 70.0,
        "gbif_core_standard": 90.0,
        "gbif_extended": 80.0,
        "en_field": 75.0,
        "anonymous": 100.0,
    }

    assert _compute_fusion_surrogate_fast_score(fast_buckets) == pytest.approx(73.5)
    assert _compute_fusion_surrogate_mid_score(mid_buckets) == pytest.approx(75.75)


def test_evaluate_fusion_surrogate_reads_cached_folds(tmp_path):
    gold_path = tmp_path / "gold_set.json"
    gold_path.write_text(json.dumps([{"concept_coarse": "measurement.height"}]))
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    manifest = {
        "gold_sha256": compute_gold_set_sha256(gold_path),
        "all_concepts": ["measurement.height", "taxonomy.species"],
        "folds": [{"file": "fold_01.npz"}],
    }
    (cache_dir / "manifest.json").write_text(json.dumps(manifest))

    train_header = np.array(
        [[0.99, 0.01], [0.95, 0.05], [0.01, 0.99], [0.05, 0.95]],
        dtype=float,
    )
    train_value = train_header.copy()
    train_meta = np.array(
        [
            [0.0, 0.0, 0.2, 0.0],
            [0.0, 0.1, 0.3, 0.0],
            [0.0, 0.0, 0.2, 0.0],
            [1.0, 0.0, 0.9, 1.0],
        ],
        dtype=float,
    )
    train_labels = np.array(
        [
            "measurement.height",
            "measurement.height",
            "taxonomy.species",
            "taxonomy.species",
        ],
        dtype=object,
    )
    test_header = np.array([[0.97, 0.03], [0.02, 0.98]], dtype=float)
    test_value = test_header.copy()
    test_meta = np.array([[0.0, 0.0, 0.2, 0.0], [1.0, 0.0, 0.9, 1.0]], dtype=float)
    test_labels = np.array(
        ["measurement.height", "taxonomy.species"],
        dtype=object,
    )
    np.savez_compressed(
        cache_dir / "fold_01.npz",
        train_header_proba=train_header,
        train_value_proba=train_value,
        train_metadata=train_meta,
        train_labels=train_labels,
        test_header_proba=test_header,
        test_value_proba=test_value,
        test_metadata=test_meta,
        test_labels=test_labels,
        test_bucket_tropical_field=np.array([True, False]),
        test_bucket_research_traits=np.array([False, False]),
        test_bucket_en_field=np.array([True, True]),
        test_bucket_gbif_core_standard=np.array([False, True]),
        test_bucket_gbif_extended=np.array([False, False]),
        test_bucket_anonymous=np.array([False, True]),
        test_bucket_coded_headers=np.array([False, True]),
    )

    score = evaluate_fusion_surrogate(
        gold_path,
        cache_dir=cache_dir,
        objective="surrogate-fast",
    )

    assert score == pytest.approx(100.0)
