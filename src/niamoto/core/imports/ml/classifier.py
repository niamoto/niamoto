"""
Runtime column classifier using trained ML models.

Loads the 3-branch pipeline (header + values + fusion) and classifies
columns by combining name-based and value-based signals.

The AliasRegistry remains as a fast-path for exact matches.
The ML models handle fuzzy names, anonymous columns, and value-based detection.
"""

import logging
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from niamoto.core.imports.ml.header_features import build_header_text_from_series
from niamoto.core.imports.ml.fusion_features import (
    branch_confidence_stats,
    dampen_code_like_false_counts,
    is_code_like_header,
    top_concept_flags,
)
from niamoto.core.imports.ml.value_features import extract_value_features_from_series

logger = logging.getLogger(__name__)

# Patterns for anonymous/auto-generated column names (X1, col_3, var_a, V1, Unnamed: 0…)
_ANONYMOUS_RE = re.compile(
    r"^(x|col|var|v|unnamed|field|column|f|c)\s*[_:\-]?\s*\d*$", re.IGNORECASE
)


def _get_resource_path(relative: str) -> Path:
    """Get path to a bundled resource.

    Resolution order:
    1. bundle.py (PyInstaller frozen → sys._MEIPASS, source → project root)
    2. Package-relative (pip install → niamoto/ package directory)
    """
    try:
        from niamoto.common.bundle import get_resource_path

        path = get_resource_path(relative)
        if path.exists():
            return path
    except Exception:
        pass

    # Fallback: package-relative (pip install with models in niamoto/models/)
    # From niamoto/core/imports/ml/classifier.py → parents[3] = niamoto/
    return Path(__file__).resolve().parents[3] / relative


class ColumnClassifier:
    """3-branch column classifier using trained ML models.

    Branch 1 (header): TF-IDF char n-grams + LogReg on column name
    Branch 2 (values): HistGradientBoosting on statistical features
    Branch 3 (fusion): LogReg combining both branch probabilities
    """

    def __init__(self):
        self._header_model = None
        self._value_model = None
        self._fusion_model = None
        self._fusion_concepts = None
        self._loaded = False

    def _ensure_loaded(self) -> bool:
        """Lazy-load models on first use."""
        if self._loaded:
            return self._header_model is not None

        self._loaded = True
        try:
            import joblib

            header_path = _get_resource_path("models/header_model.joblib")
            value_path = _get_resource_path("models/value_model.joblib")
            fusion_path = _get_resource_path("models/fusion_model.joblib")

            if header_path.exists():
                self._header_model = joblib.load(header_path)
                logger.debug("Loaded header model from %s", header_path)

            if value_path.exists():
                value_data = joblib.load(value_path)
                self._value_model = value_data["model"]
                logger.debug("Loaded value model from %s", value_path)

            if fusion_path.exists():
                fusion_data = joblib.load(fusion_path)
                self._fusion_model = fusion_data["model"]
                self._fusion_concepts = fusion_data["all_concepts"]
                logger.debug("Loaded fusion model from %s", fusion_path)

            return self._header_model is not None
        except Exception as e:
            logger.warning("Could not load ML models: %s", e)
            return False

    def classify(
        self,
        col_name: str,
        series: pd.Series,
        *,
        name_normalized: Optional[str] = None,
    ) -> tuple[Optional[str], float]:
        """Classify a column using the 3-branch pipeline.

        Args:
            col_name: Raw column name
            series: Column values
            name_normalized: Pre-normalized name (optional, avoids double work)

        Returns:
            (concept, confidence) or (None, 0.0) if no model available
        """
        if not self._ensure_loaded():
            return None, 0.0

        # Prepare name for header model (same preprocessing as training)
        from niamoto.core.imports.ml.alias_registry import _normalize

        norm = name_normalized or _normalize(col_name)

        # Get header probabilities
        header_proba = self._predict_header(norm, series)

        # Get value probabilities
        value_proba = self._predict_values(series)

        # Detect anonymous column names
        is_anonymous = bool(_ANONYMOUS_RE.match(norm.strip())) if norm else False

        # If we have a fusion model, combine
        if self._fusion_model is not None and self._fusion_concepts is not None:
            return self._predict_fusion(
                header_proba,
                value_proba,
                series,
                norm_name=norm,
                raw_name=col_name,
                is_anonymous=is_anonymous,
            )

        # Fallback: use header model alone
        if header_proba is not None:
            idx = np.argmax(header_proba)
            classes = self._header_model.classes_
            return classes[idx], float(header_proba[idx])

        return None, 0.0

    def _predict_header(
        self, norm_name: str, series: pd.Series
    ) -> Optional[np.ndarray]:
        """Run the header branch (name-based)."""
        if self._header_model is None or not norm_name:
            return None

        try:
            name = build_header_text_from_series(norm_name, series)
            return self._header_model.predict_proba([name])[0]
        except Exception as e:
            logger.debug("Header prediction failed: %s", e)
            return None

    def _predict_values(self, series: pd.Series) -> Optional[np.ndarray]:
        """Run the values branch (statistics-based)."""
        if self._value_model is None:
            return None

        try:
            features = _extract_value_features(series)
            return self._value_model.predict_proba(features.reshape(1, -1))[0]
        except Exception as e:
            logger.debug("Value prediction failed: %s", e)
            return None

    def _predict_fusion(
        self,
        header_proba: Optional[np.ndarray],
        value_proba: Optional[np.ndarray],
        series: pd.Series,
        *,
        norm_name: str,
        raw_name: str,
        is_anonymous: bool = False,
    ) -> tuple[Optional[str], float]:
        """Combine header + value probabilities via fusion model."""
        n_concepts = len(self._fusion_concepts)
        features = []
        aligned_header = np.zeros(n_concepts)
        aligned_value = np.zeros(n_concepts)

        # Align header probabilities to fusion concept space
        if header_proba is not None:
            header_classes = list(self._header_model.classes_)
            for i, c in enumerate(self._fusion_concepts):
                if c in header_classes:
                    aligned_header[i] = header_proba[header_classes.index(c)]
        if value_proba is not None:
            value_classes = list(self._value_model.classes_)
            for i, c in enumerate(self._fusion_concepts):
                if c in value_classes:
                    aligned_value[i] = value_proba[value_classes.index(c)]
        aligned_header, aligned_value = dampen_code_like_false_counts(
            aligned_header,
            aligned_value,
            self._fusion_concepts,
            raw_name=raw_name,
            norm_name=norm_name,
        )
        features.extend(aligned_header)
        features.extend(aligned_value)

        # Meta features
        header_max, header_margin, header_entropy = branch_confidence_stats(
            aligned_header
        )
        value_max, value_margin, value_entropy = branch_confidence_stats(aligned_value)
        agree, value_stat_count, header_stat_count = top_concept_flags(
            aligned_header, aligned_value, self._fusion_concepts
        )
        anonymous = 1.0 if is_anonymous else 0.0
        code_like_header = is_code_like_header(raw_name, norm_name)
        header_missing = 1.0 if header_max <= 0.0 else 0.0
        value_missing = 1.0 if value_max <= 0.0 else 0.0
        value_when_header_weak = value_max * (1.0 - header_max)
        value_margin_when_header_weak = value_margin * (1.0 - header_margin)
        anonymous_value_max = anonymous * value_max
        anonymous_value_margin = anonymous * value_margin
        confidence_product = header_max * value_max
        agreement_strength = agree * min(header_max, value_max)
        features.append(anonymous)
        features.append(float(series.isnull().mean()))
        features.append(float(series.nunique() / max(len(series), 1)))
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
        h_arr = np.asarray(aligned_header, dtype=float)
        v_arr = np.asarray(aligned_value, dtype=float)
        n_c = len(h_arr)
        h_active = float(h_arr.sum()) > 0
        v_active = float(v_arr.sum()) > 0

        h_order = np.argsort(-h_arr)
        v_order = np.argsort(-v_arr)

        if h_active and v_active:
            v_ranks = np.argsort(np.argsort(-v_arr))
            header_top1_value_rank = float(v_ranks[h_order[0]]) / max(n_c - 1, 1)
        else:
            header_top1_value_rank = 1.0

        if v_active and h_active:
            h_ranks = np.argsort(np.argsort(-h_arr))
            value_top1_header_rank = float(h_ranks[v_order[0]]) / max(n_c - 1, 1)
        else:
            value_top1_header_rank = 1.0

        h_top1 = int(h_order[0]) if h_active else -1
        v_top1 = int(v_order[0]) if v_active else -1
        h_top2 = int(h_order[1]) if h_active and n_c > 1 else -1
        v_top2 = int(v_order[1]) if v_active and n_c > 1 else -1
        top2_cross_match = (
            1.0
            if (
                (h_top2 >= 0 and h_top2 == v_top1) or (v_top2 >= 0 and v_top2 == h_top1)
            )
            else 0.0
        )

        both_weak = 1.0 if header_max < 0.3 and value_max < 0.3 else 0.0

        features.append(header_top1_value_rank)
        features.append(value_top1_header_rank)
        features.append(top2_cross_match)
        features.append(both_weak)

        try:
            X = np.array(features, dtype=float).reshape(1, -1)
            proba = self._fusion_model.predict_proba(X)[0]
            idx = np.argmax(proba)
            concept = self._fusion_model.classes_[idx]
            confidence = float(proba[idx])
            return concept, confidence
        except Exception as e:
            logger.debug("Fusion prediction failed: %s", e)
            return None, 0.0


def _extract_value_features(series: pd.Series) -> np.ndarray:
    """Extract the same value features used by the trained value model."""
    return extract_value_features_from_series(series)
