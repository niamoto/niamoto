import numpy as np
import pandas as pd

from niamoto.core.imports.ml.fusion_features import (
    branch_confidence_stats,
    dampen_code_like_false_counts,
    is_code_like_header,
    top_concept_flags,
)
from scripts.ml.train_fusion import (
    extract_fusion_branch_probabilities,
    extract_fusion_branch_probabilities_batch,
    extract_fusion_metadata,
    extract_fusion_metadata_batch,
)
from niamoto.core.imports.ml.value_features import (
    FEATURE_NAMES,
    extract_value_features_from_sample,
    extract_value_features_from_series,
)


def _feature_index(name: str) -> int:
    return FEATURE_NAMES.index(name)


def test_value_feature_extractors_are_runtime_train_aligned():
    values = ["A1", "B2", "A1", "C3", "B2", "C3"]
    stats = {"dtype": "object", "unique_ratio": 0.5, "null_ratio": 0.0}

    train_features = extract_value_features_from_sample(values, stats)
    runtime_features = extract_value_features_from_series(pd.Series(values))

    assert train_features.shape == runtime_features.shape
    assert train_features.shape[0] == len(FEATURE_NAMES)
    assert train_features[_feature_index("short_code_ratio")] > 0.5
    assert runtime_features[_feature_index("short_code_ratio")] > 0.5


def test_value_features_capture_dense_tiny_integer_domains():
    values = [1, 2, 3, 2, 1, 3, 2, 1]
    stats = {"dtype": "int64", "unique_ratio": 3 / 8, "null_ratio": 0.0}

    features = extract_value_features_from_sample(values, stats)

    assert features[_feature_index("dense_integer_domain")] > 0.9
    assert features[_feature_index("tiny_integer_domain")] == 1.0


def test_code_like_header_detection():
    assert is_code_like_header("COUNTYCD", "countycd") == 1.0
    assert is_code_like_header("PEUPNR", "peupnr") == 1.0
    assert is_code_like_header("diameter", "diameter") == 0.0


def test_fusion_meta_feature_helpers():
    concepts = ["statistic.count", "measurement.height", "category.damage"]
    header = np.array([0.1, 0.8, 0.1])
    value = np.array([0.7, 0.2, 0.1])

    header_max, header_margin, header_entropy = branch_confidence_stats(header)
    value_max, value_margin, value_entropy = branch_confidence_stats(value)
    agree, value_stat_count, header_stat_count = top_concept_flags(
        header, value, concepts
    )

    assert header_max == 0.8
    assert value_max == 0.7
    assert header_margin > 0.0
    assert value_margin > 0.0
    assert header_entropy > 0.0
    assert value_entropy > 0.0
    assert agree == 0.0
    assert value_stat_count == 1.0
    assert header_stat_count == 0.0


def test_code_like_headers_dampen_false_stat_count():
    concepts = ["statistic.count", "measurement.height", "category.damage"]
    header = np.array([0.7, 0.2, 0.1])
    value = np.array([0.9, 0.05, 0.05])

    new_header, new_value = dampen_code_like_false_counts(
        header,
        value,
        concepts,
        raw_name="COUNTYCD",
        norm_name="countycd",
    )

    assert new_header[0] < header[0]
    assert new_value[0] < value[0]


class _DummyBranch:
    def __init__(self, classes, outputs):
        self.classes_ = np.array(classes)
        self._outputs = np.array(outputs, dtype=float)

    def predict_proba(self, inputs):
        return self._outputs[: len(inputs)]


def test_batch_branch_probability_extraction_matches_single_record_path():
    records = [
        {
            "column_name": "HEIGHT",
            "values_stats": {
                "dtype": "float64",
                "null_ratio": 0.0,
                "unique_ratio": 1.0,
            },
            "values_sample": [1.1, 2.2, 3.3],
            "is_anonymous": False,
        },
        {
            "column_name": "COUNTYCD",
            "values_stats": {"dtype": "int64", "null_ratio": 0.0, "unique_ratio": 0.7},
            "values_sample": [1, 2, 3, 4],
            "is_anonymous": False,
        },
    ]
    all_concepts = ["statistic.count", "measurement.height"]
    header_model = _DummyBranch(
        ["measurement.height", "statistic.count"],
        [[0.9, 0.1], [0.9, 0.1]],
    )
    value_model = _DummyBranch(
        ["measurement.height", "statistic.count"],
        [[0.8, 0.2], [0.8, 0.2]],
    )

    batch_header, batch_value = extract_fusion_branch_probabilities_batch(
        records,
        header_model,
        value_model,
        all_concepts,
    )

    single = [
        extract_fusion_branch_probabilities(
            record,
            header_model,
            value_model,
            all_concepts,
        )
        for record in records
    ]
    single_header = np.array([header for header, _value in single])
    single_value = np.array([value for _header, value in single])

    np.testing.assert_allclose(batch_header, single_header)
    np.testing.assert_allclose(batch_value, single_value)


def test_batch_metadata_extraction_matches_single_record_path():
    records = [
        {
            "column_name": "HEIGHT",
            "values_stats": {"null_ratio": 0.1, "unique_ratio": 0.8},
            "is_anonymous": False,
        },
        {
            "column_name": "COUNTYCD",
            "values_stats": {"null_ratio": 0.0, "unique_ratio": 0.5},
            "is_anonymous": True,
        },
    ]

    batch_meta = extract_fusion_metadata_batch(records)
    single_meta = np.array([extract_fusion_metadata(record) for record in records])

    np.testing.assert_allclose(batch_meta, single_meta)
