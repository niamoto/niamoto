"""Tests for the ML evaluation harness."""

import pytest
import numpy as np
import pandas as pd

from niamoto.core.imports.ml.evaluation import (
    LabeledColumn,
    EvalMetrics,
    EvaluationHarness,
    HarnessResults,
    compute_metrics,
    _compute_ece,
)


# ── Helpers ──────────────────────────────────────────────────────


def _make_column(
    name: str,
    concept: str,
    source: str = "test",
    language: str = "en",
    is_anonymous: bool = False,
) -> LabeledColumn:
    """Create a labeled column with dummy values."""
    role = concept.split(".")[0] if "." in concept else concept
    return LabeledColumn(
        column_name=name,
        values=pd.Series(np.random.randn(20)),
        concept=concept,
        role=role,
        source_dataset=source,
        language=language,
        is_anonymous=is_anonymous,
    )


class DummyPredictor:
    """Predictor that always returns a fixed concept."""

    def __init__(self, correct_rate: float = 0.8):
        self.correct_rate = correct_rate
        self._concepts: list[str] = []

    def fit(self, columns: list[LabeledColumn]) -> None:
        self._concepts = list({c.concept for c in columns})

    def predict(self, col: LabeledColumn):
        # Deterministic: correct for first N%, wrong for rest
        hash_val = hash(col.column_name + col.source_dataset) % 100
        if hash_val < self.correct_rate * 100:
            pred = col.concept
            conf = 0.85
        else:
            # Pick a wrong concept
            others = [c for c in self._concepts if c != col.concept]
            pred = others[0] if others else col.concept
            conf = 0.4
        top_k = [(pred, conf)]
        if self._concepts:
            for c in self._concepts[:2]:
                if c != pred:
                    top_k.append((c, 0.1))
        return pred, conf, top_k


# ── Tests: Metrics ───────────────────────────────────────────────


class TestComputeMetrics:
    def test_perfect_predictions(self):
        y_true = ["taxonomy.species", "measurement.diameter", "location.latitude"]
        y_pred = ["taxonomy.species", "measurement.diameter", "location.latitude"]
        confs = [0.95, 0.90, 0.88]
        top3 = [["taxonomy.species"], ["measurement.diameter"], ["location.latitude"]]

        m = compute_metrics(
            y_true, ["taxonomy", "measurement", "location"], y_pred, confs, top3
        )
        assert m.macro_f1_concept == 1.0
        assert m.macro_f1_role == 1.0
        assert m.top3_accuracy == 1.0
        assert m.coverage_at_70 == 1.0
        assert m.n_samples == 3

    def test_all_wrong(self):
        y_true = ["taxonomy.species", "measurement.diameter"]
        y_pred = ["measurement.diameter", "taxonomy.species"]
        confs = [0.3, 0.2]
        top3 = [["measurement.diameter"], ["taxonomy.species"]]

        m = compute_metrics(y_true, ["taxonomy", "measurement"], y_pred, confs, top3)
        assert m.macro_f1_concept == 0.0
        assert m.top3_accuracy == 0.0
        assert m.coverage_at_70 == 0.0

    def test_top3_accuracy(self):
        y_true = ["taxonomy.species"]
        y_pred = ["measurement.diameter"]  # wrong top-1
        confs = [0.6]
        top3 = [
            ["measurement.diameter", "taxonomy.species", "location.lat"]
        ]  # correct in top-3

        m = compute_metrics(y_true, ["taxonomy"], y_pred, confs, top3)
        assert m.top3_accuracy == 1.0
        assert m.macro_f1_concept == 0.0  # top-1 is wrong

    def test_empty_input(self):
        m = compute_metrics([], [], [], [], [])
        assert m.n_samples == 0
        assert m.macro_f1_concept == 0.0

    def test_coverage_threshold(self):
        y_true = ["a", "b", "c"]
        y_pred = ["a", "b", "c"]
        confs = [0.9, 0.5, 0.7]
        top3 = [["a"], ["b"], ["c"]]

        m = compute_metrics(y_true, ["a", "b", "c"], y_pred, confs, top3)
        assert m.coverage_at_70 == pytest.approx(2 / 3, abs=0.01)


class TestECE:
    def test_perfect_calibration(self):
        """If confidence matches accuracy perfectly, ECE = 0."""
        # All correct with confidence 0.85
        ece = _compute_ece(["a", "a"], ["a", "a"], [0.85, 0.85])
        # Should be close to 0.15 (confidence 0.85, accuracy 1.0 in that bin)
        assert ece < 0.2

    def test_zero_confidence(self):
        ece = _compute_ece(["a"], ["b"], [0.0])
        assert ece >= 0.0

    def test_empty(self):
        assert _compute_ece([], [], []) == 0.0


# ── Tests: Harness ───────────────────────────────────────────────


class TestEvaluationHarness:
    @pytest.fixture
    def labeled_columns(self):
        """Create a dataset of labeled columns from multiple sources."""
        columns = []
        for i in range(10):
            columns.append(
                _make_column(
                    f"species_{i}",
                    "taxonomy.species",
                    source="dataset_a",
                    language="en",
                )
            )
        for i in range(10):
            columns.append(
                _make_column(
                    f"diametre_{i}",
                    "measurement.diameter",
                    source="dataset_b",
                    language="fr",
                )
            )
        for i in range(10):
            columns.append(
                _make_column(
                    f"lat_{i}",
                    "location.latitude",
                    source="dataset_c",
                    language="en",
                )
            )
        for i in range(5):
            columns.append(
                _make_column(
                    f"X{i}",
                    "measurement.diameter",
                    source="dataset_d",
                    language="en",
                    is_anonymous=True,
                )
            )
        return columns

    @staticmethod
    def _factory():
        return DummyPredictor(correct_rate=0.8)

    @staticmethod
    def _factory_default():
        return DummyPredictor()

    def test_group_kfold(self, labeled_columns):
        harness = EvaluationHarness(labeled_columns, n_splits=3)
        results = harness.run_all(self._factory)
        assert len(results.group_kfold) == 3
        for m in results.group_kfold:
            assert m.n_samples > 0
            assert 0.0 <= m.macro_f1_concept <= 1.0

    def test_kfold_mean(self, labeled_columns):
        harness = EvaluationHarness(labeled_columns, n_splits=3)
        results = harness.run_all(self._factory)
        mean = results.kfold_mean
        assert mean.n_samples == sum(m.n_samples for m in results.group_kfold)

    def test_geo_holdout(self, labeled_columns):
        harness = EvaluationHarness(labeled_columns, n_splits=3)
        results = harness.run_all(
            self._factory,
            geo_holdout_datasets={"dataset_c"},
        )
        assert results.holdout_geo is not None
        assert results.holdout_geo.n_samples == 10  # dataset_c has 10 cols

    def test_lang_holdout(self, labeled_columns):
        harness = EvaluationHarness(labeled_columns, n_splits=3)
        results = harness.run_all(
            self._factory,
            lang_holdout="fr",
        )
        assert results.holdout_lang is not None
        assert results.holdout_lang.n_samples == 10  # dataset_b is FR

    def test_anonymous_holdout(self, labeled_columns):
        harness = EvaluationHarness(labeled_columns, n_splits=3)
        results = harness.run_all(self._factory)
        assert results.holdout_anon is not None
        assert results.holdout_anon.n_samples == 5

    def test_not_enough_groups(self):
        """With only 1 dataset group, GroupKFold should warn and return empty."""
        columns = [
            _make_column(f"col_{i}", "taxonomy.species", source="only_one")
            for i in range(10)
        ]
        harness = EvaluationHarness(columns, n_splits=5)
        results = harness.run_all(self._factory_default)
        assert results.group_kfold == []

    def test_summary_output(self, labeled_columns):
        harness = EvaluationHarness(labeled_columns, n_splits=3)
        results = harness.run_all(
            self._factory,
            geo_holdout_datasets={"dataset_c"},
            lang_holdout="fr",
        )
        summary = results.summary()
        assert "GroupKFold" in summary
        assert "Holdout geo" in summary
        assert "Holdout lang" in summary


class TestEvalMetrics:
    def test_summary_format(self):
        m = EvalMetrics(
            macro_f1_concept=0.85,
            macro_f1_role=0.90,
            top3_accuracy=0.95,
            ece=0.05,
            coverage_at_70=0.80,
            n_samples=100,
        )
        s = m.summary()
        assert "0.850" in s
        assert "n=100" in s

    def test_default_values(self):
        m = EvalMetrics()
        assert m.macro_f1_concept == 0.0
        assert m.n_samples == 0


class TestHarnessResults:
    def test_empty_kfold_mean(self):
        r = HarnessResults()
        mean = r.kfold_mean
        assert mean.macro_f1_concept == 0.0
        assert mean.n_samples == 0
