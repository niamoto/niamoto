"""
Evaluation harness for ML column detection models.

Provides GroupKFold cross-validation, geographic and linguistic holdouts,
and standard metrics (macro-F1, top-3 accuracy, ECE, coverage).

Usage:
    harness = EvaluationHarness(labeled_columns)
    results = harness.run_all()
    print(results.summary())
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold

logger = logging.getLogger(__name__)

CRITICAL_CONCEPTS = {
    "location.latitude",
    "location.longitude",
    "location.elevation",
    "event.date",
    "event.year",
    "taxonomy.species",
    "taxonomy.family",
    "identifier.plot",
    "identifier.record",
    "measurement.diameter",
    "measurement.height",
}

STRUCTURAL_FAMILIES = {
    "coordinates": {"location.latitude", "location.longitude"},
    "taxonomy_lineage": {"taxonomy.family", "taxonomy.genus", "taxonomy.species"},
    "temporal": {"event.date", "event.year"},
    "identifiers": {"identifier.plot", "identifier.record"},
}


# ── Types ────────────────────────────────────────────────────────


@dataclass
class LabeledColumn:
    """A single labeled column for training/evaluation."""

    column_name: str
    values: pd.Series
    concept: str  # e.g. "taxonomy.species", "measurement.diameter"
    role: str  # e.g. "taxonomy", "measurement", "location"
    source_dataset: str  # e.g. "guyadiv", "gbif_marine_001", "fixture_forest"
    language: str = "en"  # header language: en, fr, es, pt, de, id
    is_anonymous: bool = False  # True if column_name is meaningless (X1, col_3)


@dataclass
class EvalMetrics:
    """Evaluation metrics for a single split or overall."""

    macro_f1_concept: float = 0.0
    macro_f1_role: float = 0.0
    top3_accuracy: float = 0.0
    ece: float = 0.0
    coverage_at_70: float = 0.0
    n_samples: int = 0

    def summary(self) -> str:
        return (
            f"macro-F1 concept={self.macro_f1_concept:.3f}  "
            f"role={self.macro_f1_role:.3f}  "
            f"top3={self.top3_accuracy:.3f}  "
            f"ECE={self.ece:.3f}  "
            f"coverage@0.70={self.coverage_at_70:.3f}  "
            f"(n={self.n_samples})"
        )


@dataclass
class HarnessResults:
    """Full results from the evaluation harness."""

    group_kfold: list[EvalMetrics] = field(default_factory=list)
    holdout_geo: Optional[EvalMetrics] = None
    holdout_lang: Optional[EvalMetrics] = None
    holdout_anon: Optional[EvalMetrics] = None
    ablations: dict[str, EvalMetrics] = field(default_factory=dict)

    @property
    def kfold_mean(self) -> EvalMetrics:
        """Mean metrics across k folds."""
        if not self.group_kfold:
            return EvalMetrics()
        return EvalMetrics(
            macro_f1_concept=float(
                np.mean([m.macro_f1_concept for m in self.group_kfold])
            ),
            macro_f1_role=float(np.mean([m.macro_f1_role for m in self.group_kfold])),
            top3_accuracy=float(np.mean([m.top3_accuracy for m in self.group_kfold])),
            ece=float(np.mean([m.ece for m in self.group_kfold])),
            coverage_at_70=float(np.mean([m.coverage_at_70 for m in self.group_kfold])),
            n_samples=sum(m.n_samples for m in self.group_kfold),
        )

    def summary(self) -> str:
        lines = ["=== Evaluation Results ==="]
        lines.append(f"GroupKFold mean: {self.kfold_mean.summary()}")
        for i, m in enumerate(self.group_kfold):
            lines.append(f"  Fold {i}: {m.summary()}")
        if self.holdout_geo:
            lines.append(f"Holdout geo:  {self.holdout_geo.summary()}")
        if self.holdout_lang:
            lines.append(f"Holdout lang: {self.holdout_lang.summary()}")
        if self.holdout_anon:
            lines.append(f"Holdout anon: {self.holdout_anon.summary()}")
        for name, m in self.ablations.items():
            lines.append(f"Ablation [{name}]: {m.summary()}")
        return "\n".join(lines)


@dataclass
class NiamotoOfflineScore:
    """Composite offline score aligned with the import product behavior."""

    final_score: float = 0.0
    role_macro_f1: Optional[float] = None
    critical_concept_macro_f1: Optional[float] = None
    anonymous_role_macro_f1: Optional[float] = None
    pair_consistency: Optional[float] = None
    confidence_quality: Optional[float] = None
    dataset_outcome: Optional[float] = None
    high_confidence_error_rate: Optional[float] = None
    n_samples: int = 0
    n_datasets: int = 0

    def summary(self) -> str:
        return (
            f"NiamotoOfflineScore={self.final_score:.3f}  "
            f"role={_fmt_metric(self.role_macro_f1)}  "
            f"critical={_fmt_metric(self.critical_concept_macro_f1)}  "
            f"anon={_fmt_metric(self.anonymous_role_macro_f1)}  "
            f"pairs={_fmt_metric(self.pair_consistency)}  "
            f"confQ={_fmt_metric(self.confidence_quality)}  "
            f"dataset={_fmt_metric(self.dataset_outcome)}  "
            f"hc_err={_fmt_metric(self.high_confidence_error_rate)}  "
            f"(n={self.n_samples}, datasets={self.n_datasets})"
        )


class Predictor(Protocol):
    """Protocol for a model that can be trained and predict."""

    def fit(self, columns: list[LabeledColumn]) -> None: ...

    def predict(self, col: LabeledColumn) -> tuple[str, float, list[tuple[str, float]]]:
        """Predict concept for a column.

        Returns:
            (predicted_concept, confidence, top_k_concepts_with_proba)
        """
        ...


# ── Metrics computation ──────────────────────────────────────────


def compute_metrics(
    y_true_concept: list[str],
    y_true_role: list[str],
    y_pred_concept: list[str],
    confidences: list[float],
    top3_predictions: list[list[str]],
) -> EvalMetrics:
    """Compute all evaluation metrics from predictions."""
    n = len(y_true_concept)
    if n == 0:
        return EvalMetrics()

    # macro-F1 concept
    mf1_concept = float(
        f1_score(y_true_concept, y_pred_concept, average="macro", zero_division=0)
    )

    # macro-F1 role (extract role from concept: "taxonomy.species" → "taxonomy")
    pred_roles = [c.split(".")[0] if "." in c else c for c in y_pred_concept]
    mf1_role = float(
        f1_score(y_true_role, pred_roles, average="macro", zero_division=0)
    )

    # top-3 accuracy
    top3_hits = sum(
        1 for true, preds in zip(y_true_concept, top3_predictions) if true in preds
    )
    top3_acc = top3_hits / n

    # ECE (Expected Calibration Error) — 10 bins
    ece = _compute_ece(y_true_concept, y_pred_concept, confidences, n_bins=10)

    # Coverage@0.70 — fraction of samples with confidence >= 0.70
    coverage = sum(1 for c in confidences if c >= 0.70) / n

    return EvalMetrics(
        macro_f1_concept=mf1_concept,
        macro_f1_role=mf1_role,
        top3_accuracy=top3_acc,
        ece=ece,
        coverage_at_70=coverage,
        n_samples=n,
    )


def _compute_ece(
    y_true: list[str],
    y_pred: list[str],
    confidences: list[float],
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error.

    Measures how well confidence scores match actual accuracy.
    Perfect calibration: ECE = 0.
    """
    if not confidences:
        return 0.0

    conf_arr = np.array(confidences)
    correct = np.array([t == p for t, p in zip(y_true, y_pred)], dtype=float)
    bin_boundaries = np.linspace(0, 1, n_bins + 1)

    ece = 0.0
    for i in range(n_bins):
        mask = (conf_arr > bin_boundaries[i]) & (conf_arr <= bin_boundaries[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = correct[mask].mean()
        bin_conf = conf_arr[mask].mean()
        ece += mask.sum() / len(conf_arr) * abs(bin_acc - bin_conf)

    return float(ece)


def _fmt_metric(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _weighted_mean(
    values: dict[str, Optional[float]],
    weights: dict[str, float],
) -> float:
    active = {
        name: (values[name], weights[name])
        for name in weights
        if values.get(name) is not None
    }
    if not active:
        return 0.0
    total_weight = sum(weight for _value, weight in active.values())
    if total_weight <= 0:
        return 0.0
    return float(
        sum(value * weight for value, weight in active.values()) / total_weight
    )


def _macro_f1_for_subset(
    y_true: list[str],
    y_pred: list[str],
    allowed_concepts: set[str],
) -> Optional[float]:
    indices = [i for i, concept in enumerate(y_true) if concept in allowed_concepts]
    if not indices:
        return None
    true_subset = [y_true[i] for i in indices]
    pred_subset = [y_pred[i] for i in indices]
    labels = sorted(set(true_subset))
    return float(
        f1_score(
            true_subset, pred_subset, labels=labels, average="macro", zero_division=0
        )
    )


def compute_high_confidence_error_rate(
    y_true: list[str],
    y_pred: list[str],
    confidences: list[float],
    threshold: float = 0.70,
) -> Optional[float]:
    if not y_true:
        return None
    high_conf = [i for i, conf in enumerate(confidences) if conf >= threshold]
    if not high_conf:
        return 0.0
    errors = sum(1 for i in high_conf if y_true[i] != y_pred[i])
    return errors / len(high_conf)


def _infer_dataset_type(concepts: set[str]) -> str:
    if (
        "geometry" in concepts
        or "location.geometry" in concepts
        or ("location.latitude" in concepts and "location.longitude" in concepts)
    ):
        return "spatial"

    taxonomy_count = sum(1 for c in concepts if c.startswith("taxonomy."))
    measurement_like = sum(
        1
        for c in concepts
        if c.startswith(("measurement.", "environment.", "statistic."))
    )
    has_location = any(c.startswith("location.") for c in concepts)
    has_time = any(c.startswith("event.") for c in concepts)

    if (
        taxonomy_count >= 2
        and not measurement_like
        and not has_location
        and not has_time
    ):
        return "hierarchical"
    if measurement_like >= max(2, len(concepts) // 2):
        return "statistical"
    return "factual"


def _dataset_affordances(concepts: set[str]) -> set[str]:
    try:
        from niamoto.core.imports.ml.semantic_profile import get_affordances
    except Exception:
        return set()

    affordances = set()
    for concept in concepts:
        role = concept.split(".")[0] if "." in concept else concept
        affordances.update(get_affordances(concept, role))
    return affordances


def compute_pair_consistency(
    columns: list[LabeledColumn],
    y_pred_concept: list[str],
) -> Optional[float]:
    by_dataset: dict[str, dict[str, set[str]]] = {}
    for col, pred in zip(columns, y_pred_concept):
        bucket = by_dataset.setdefault(
            col.source_dataset, {"true": set(), "pred": set()}
        )
        bucket["true"].add(col.concept)
        bucket["pred"].add(pred)

    scores = []
    for dataset in by_dataset.values():
        true_set = dataset["true"]
        pred_set = dataset["pred"]
        for family in STRUCTURAL_FAMILIES.values():
            true_present = true_set & family
            if not true_present:
                continue
            pred_present = pred_set & family
            if pred_present == true_present:
                scores.append(1.0)
            elif pred_present and pred_present.issubset(true_present):
                scores.append(0.5)
            else:
                scores.append(0.0)

    if not scores:
        return None
    return float(np.mean(scores))


def compute_dataset_outcome(
    columns: list[LabeledColumn],
    y_pred_concept: list[str],
) -> Optional[float]:
    by_dataset: dict[str, dict[str, set[str]]] = {}
    for col, pred in zip(columns, y_pred_concept):
        bucket = by_dataset.setdefault(
            col.source_dataset, {"true": set(), "pred": set()}
        )
        bucket["true"].add(col.concept)
        bucket["pred"].add(pred)

    if not by_dataset:
        return None

    scores = []
    for dataset in by_dataset.values():
        true_set = dataset["true"]
        pred_set = dataset["pred"]

        dataset_type_correct = float(
            _infer_dataset_type(true_set) == _infer_dataset_type(pred_set)
        )

        true_keys = true_set & CRITICAL_CONCEPTS
        key_coverage = len(true_keys & pred_set) / len(true_keys) if true_keys else None

        true_affordances = _dataset_affordances(true_keys or true_set)
        pred_affordances = _dataset_affordances(pred_set)
        affordance_coverage = (
            len(true_affordances & pred_affordances) / len(true_affordances)
            if true_affordances
            else None
        )

        dataset_score = _weighted_mean(
            {
                "dataset_type": dataset_type_correct,
                "key_coverage": key_coverage,
                "affordance_coverage": affordance_coverage,
            },
            {
                "dataset_type": 0.4,
                "key_coverage": 0.4,
                "affordance_coverage": 0.2,
            },
        )
        scores.append(dataset_score)

    return float(np.mean(scores))


def compute_niamoto_offline_score(
    columns: list[LabeledColumn],
    y_pred_concept: list[str],
    confidences: list[float],
) -> NiamotoOfflineScore:
    """Compute the product-oriented offline score used by autoresearch."""
    if not columns:
        return NiamotoOfflineScore()

    y_true_concept = [c.concept for c in columns]
    y_true_role = [c.role for c in columns]
    y_pred_role = [c.split(".")[0] if "." in c else c for c in y_pred_concept]

    role_macro_f1 = float(
        f1_score(y_true_role, y_pred_role, average="macro", zero_division=0)
    )
    critical_concept_macro_f1 = _macro_f1_for_subset(
        y_true_concept, y_pred_concept, CRITICAL_CONCEPTS
    )

    anon_indices = [i for i, col in enumerate(columns) if col.is_anonymous]
    if anon_indices:
        anon_true = [y_true_role[i] for i in anon_indices]
        anon_pred = [y_pred_role[i] for i in anon_indices]
        anonymous_role_macro_f1 = float(
            f1_score(anon_true, anon_pred, average="macro", zero_division=0)
        )
    else:
        anonymous_role_macro_f1 = None

    pair_consistency = compute_pair_consistency(columns, y_pred_concept)
    high_confidence_error_rate = compute_high_confidence_error_rate(
        y_true_concept, y_pred_concept, confidences
    )
    confidence_quality = (
        None if high_confidence_error_rate is None else 1.0 - high_confidence_error_rate
    )
    dataset_outcome = compute_dataset_outcome(columns, y_pred_concept)

    final_score = 100.0 * _weighted_mean(
        {
            "role": role_macro_f1,
            "critical": critical_concept_macro_f1,
            "anonymous": anonymous_role_macro_f1,
            "pairs": pair_consistency,
            "confidence": confidence_quality,
            "dataset": dataset_outcome,
        },
        {
            "role": 0.35,
            "critical": 0.20,
            "anonymous": 0.15,
            "pairs": 0.10,
            "confidence": 0.10,
            "dataset": 0.10,
        },
    )

    return NiamotoOfflineScore(
        final_score=final_score,
        role_macro_f1=role_macro_f1,
        critical_concept_macro_f1=critical_concept_macro_f1,
        anonymous_role_macro_f1=anonymous_role_macro_f1,
        pair_consistency=pair_consistency,
        confidence_quality=confidence_quality,
        dataset_outcome=dataset_outcome,
        high_confidence_error_rate=high_confidence_error_rate,
        n_samples=len(columns),
        n_datasets=len({c.source_dataset for c in columns}),
    )


# ── Harness ──────────────────────────────────────────────────────


class EvaluationHarness:
    """Run standardized evaluations on a column classifier."""

    def __init__(
        self,
        labeled_columns: list[LabeledColumn],
        n_splits: int = 5,
    ):
        self.columns = labeled_columns
        self.n_splits = n_splits

    def run_all(
        self,
        predictor_factory: Callable[[], Predictor],
        *,
        geo_holdout_datasets: Optional[set[str]] = None,
        lang_holdout: Optional[str] = None,
    ) -> HarnessResults:
        """Run full evaluation suite.

        Args:
            predictor_factory: Callable that returns a fresh predictor instance.
            geo_holdout_datasets: Dataset sources to hold out for geographic test.
                e.g. {"guyadiv", "guyane_001"} to test generalization to Guyane.
            lang_holdout: Language code to hold out for linguistic test.
                e.g. "fr" to test generalization to French headers.
        """
        results = HarnessResults()

        # 1. GroupKFold cross-validation
        results.group_kfold = self._run_group_kfold(predictor_factory)

        # 2. Geographic holdout
        if geo_holdout_datasets:
            results.holdout_geo = self._run_holdout(
                predictor_factory,
                holdout_fn=lambda c: c.source_dataset in geo_holdout_datasets,
                name="geo",
            )

        # 3. Linguistic holdout
        if lang_holdout:
            results.holdout_lang = self._run_holdout(
                predictor_factory,
                holdout_fn=lambda c: c.language == lang_holdout,
                name=f"lang_{lang_holdout}",
            )

        # 4. Anonymous header holdout
        anon_cols = [c for c in self.columns if c.is_anonymous]
        if anon_cols:
            results.holdout_anon = self._run_holdout(
                predictor_factory,
                holdout_fn=lambda c: c.is_anonymous,
                name="anonymous",
            )

        return results

    def _run_group_kfold(
        self,
        predictor_factory: Callable[[], Predictor],
    ) -> list[EvalMetrics]:
        """GroupKFold CV — split by source_dataset to prevent data leakage."""
        groups = np.array([c.source_dataset for c in self.columns])
        unique_groups = np.unique(groups)

        # Need at least n_splits groups
        actual_splits = min(self.n_splits, len(unique_groups))
        if actual_splits < 2:
            logger.warning(
                "Not enough dataset groups (%d) for %d-fold CV. Need >= 2.",
                len(unique_groups),
                self.n_splits,
            )
            return []

        kfold = GroupKFold(n_splits=actual_splits)
        indices = np.arange(len(self.columns))

        fold_metrics = []
        for fold_idx, (train_idx, test_idx) in enumerate(
            kfold.split(indices, groups=groups)
        ):
            train = [self.columns[i] for i in train_idx]
            test = [self.columns[i] for i in test_idx]

            predictor = predictor_factory()
            predictor.fit(train)
            metrics = self._evaluate(predictor, test)
            fold_metrics.append(metrics)

            logger.info("Fold %d: %s", fold_idx, metrics.summary())

        return fold_metrics

    def _run_holdout(
        self,
        predictor_factory: Callable[[], Predictor],
        holdout_fn: Callable[[LabeledColumn], bool],
        name: str,
    ) -> Optional[EvalMetrics]:
        """Train on non-holdout, evaluate on holdout."""
        train = [c for c in self.columns if not holdout_fn(c)]
        test = [c for c in self.columns if holdout_fn(c)]

        if not test:
            logger.warning("Holdout '%s': no test samples found.", name)
            return None
        if not train:
            logger.warning("Holdout '%s': no training samples left.", name)
            return None

        predictor = predictor_factory()
        predictor.fit(train)
        metrics = self._evaluate(predictor, test)
        logger.info("Holdout %s: %s", name, metrics.summary())
        return metrics

    def _evaluate(
        self,
        predictor: Predictor,
        test_columns: list[LabeledColumn],
    ) -> EvalMetrics:
        """Evaluate a trained predictor on test columns."""
        y_true_concept = []
        y_true_role = []
        y_pred_concept = []
        confidences = []
        top3_preds = []

        for col in test_columns:
            concept, confidence, top_k = predictor.predict(col)
            y_true_concept.append(col.concept)
            y_true_role.append(col.role)
            y_pred_concept.append(concept)
            confidences.append(confidence)
            top3_preds.append([c for c, _ in top_k[:3]])

        return compute_metrics(
            y_true_concept,
            y_true_role,
            y_pred_concept,
            confidences,
            top3_preds,
        )
