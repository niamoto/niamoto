"""Tests for batched ML column classification."""

import numpy as np
import pandas as pd

from niamoto.core.imports.ml.classifier import ColumnClassifier


class _RecordingHeaderModel:
    classes_ = np.array(["taxonomy.family"])

    def __init__(self):
        self.calls = 0
        self.batch_sizes = []

    def predict_proba(self, inputs):
        self.calls += 1
        self.batch_sizes.append(len(inputs))
        return np.tile([[0.91]], (len(inputs), 1))


class _RecordingValueModel:
    classes_ = np.array(["taxonomy.family"])

    def __init__(self):
        self.calls = 0
        self.batch_shapes = []

    def predict_proba(self, features):
        self.calls += 1
        self.batch_shapes.append(features.shape)
        return np.tile([[0.82]], (features.shape[0], 1))


def test_classify_many_batches_header_and_value_predictions():
    classifier = ColumnClassifier()
    header_model = _RecordingHeaderModel()
    value_model = _RecordingValueModel()
    classifier._loaded = True
    classifier._header_model = header_model
    classifier._value_model = value_model
    classifier._header_class_index = {"taxonomy.family": 0}
    classifier._value_class_index = {"taxonomy.family": 0}

    results = classifier.classify_many(
        [
            ("family", pd.Series(["Araucariaceae", "Myrtaceae"])),
            ("genus", pd.Series(["Araucaria", "Syzygium"])),
        ]
    )

    assert results == [("taxonomy.family", 0.91), ("taxonomy.family", 0.91)]
    assert header_model.calls == 1
    assert header_model.batch_sizes == [2]
    assert value_model.calls == 1
    assert value_model.batch_shapes[0][0] == 2
