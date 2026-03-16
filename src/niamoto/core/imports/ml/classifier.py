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

logger = logging.getLogger(__name__)

# Patterns for anonymous/auto-generated column names (X1, col_3, var_a, V1, Unnamed: 0…)
_ANONYMOUS_RE = re.compile(
    r"^(x|col|var|v|unnamed|field|column|f|c)\s*[_:\-]?\s*\d*$", re.IGNORECASE
)


def _get_resource_path(relative: str) -> Path:
    """Get path to a bundled resource (works in source and frozen modes)."""
    try:
        from niamoto.common.bundle import get_resource_path

        return get_resource_path(relative)
    except Exception:
        # Fallback: relative to project root
        return Path(__file__).parent.parent.parent.parent.parent / relative


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
                header_proba, value_proba, series, is_anonymous=is_anonymous
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
            # Enrich name with metadata (same as training preprocessing)
            name = norm_name.replace("_", " ")

            dtype = str(series.dtype)
            if dtype in ("float64", "float32"):
                name = f"float {name}"
            elif dtype in ("int64", "int32"):
                name = f"int {name}"
            elif dtype == "object":
                name = f"str {name}"

            clean = series.dropna()
            null_ratio = series.isnull().mean()
            if null_ratio > 0.5:
                name = f"sparse {name}"

            if len(clean) > 0 and dtype == "object":
                mean_len = clean.astype(str).str.len().mean()
                if mean_len < 3:
                    name = f"short {name}"
                elif mean_len > 50:
                    name = f"long {name}"

            if len(clean) < 100:
                name = f"small {name}"

            name = f"{name} {name} {name}"

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
        is_anonymous: bool = False,
    ) -> tuple[Optional[str], float]:
        """Combine header + value probabilities via fusion model."""
        n_concepts = len(self._fusion_concepts)
        features = []

        # Align header probabilities to fusion concept space
        if header_proba is not None:
            aligned = np.zeros(n_concepts)
            header_classes = list(self._header_model.classes_)
            for i, c in enumerate(self._fusion_concepts):
                if c in header_classes:
                    aligned[i] = header_proba[header_classes.index(c)]
            features.extend(aligned)
        else:
            features.extend(np.zeros(n_concepts))

        # Align value probabilities
        if value_proba is not None:
            aligned = np.zeros(n_concepts)
            value_classes = list(self._value_model.classes_)
            for i, c in enumerate(self._fusion_concepts):
                if c in value_classes:
                    aligned[i] = value_proba[value_classes.index(c)]
            features.extend(aligned)
        else:
            features.extend(np.zeros(n_concepts))

        # Meta features
        features.append(1.0 if is_anonymous else 0.0)
        features.append(float(series.isnull().mean()))
        features.append(float(series.nunique() / max(len(series), 1)))

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
    """Extract the same 37 features used by the trained value model."""
    import scipy.stats

    features = np.zeros(37)
    clean = series.dropna()
    if len(clean) == 0:
        return features

    is_numeric = pd.api.types.is_numeric_dtype(clean)
    str_vals = clean.astype(str)

    # Numeric stats (14)
    if is_numeric:
        try:
            features[0] = float(clean.mean())
            features[1] = float(clean.std()) if len(clean) > 1 else 0
            features[2] = float(clean.min())
            features[3] = float(clean.max())
            features[4] = float(clean.skew()) if len(clean) > 2 else 0
            features[5] = float(clean.kurtosis()) if len(clean) > 3 else 0
            features[6] = float(clean.quantile(0.25))
            features[7] = float(clean.median())
            features[8] = float(clean.quantile(0.75))
            features[9] = float(clean.max() - clean.min())
            features[10] = float(clean.std() / clean.mean()) if clean.mean() != 0 else 0
            features[11] = float((clean < 0).mean())
            features[12] = float((clean == clean.astype(int)).mean())
            features[13] = float((clean == 0).mean())
        except Exception:
            pass

    # Uniqueness + distribution (3)
    features[14] = float(series.nunique() / max(len(series), 1))
    features[15] = float(series.isnull().mean())
    vc = clean.value_counts(normalize=True)
    features[16] = float(scipy.stats.entropy(vc)) if len(vc) > 1 else 0

    # Character features (6)
    if len(str_vals) > 0:
        lengths = str_vals.str.len()
        features[17] = float(lengths.mean())
        features[18] = float(lengths.std()) if len(lengths) > 1 else 0
        total = max(lengths.sum(), 1)
        features[19] = float(str_vals.str.count(r"\d").sum() / total)
        features[20] = float(str_vals.str.count(r"[a-zA-Z]").sum() / total)
        features[21] = float(str_vals.str.count(r"\s").sum() / total)
        features[22] = float(str_vals.str.split().str.len().mean())

    # Regex patterns (4)
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

    # Biological patterns (2)
    if len(str_vals) > 0:
        n = len(str_vals)
        features[27] = float(str_vals.str.match(r"^[A-Z][a-z]+ [a-z]+").sum() / n)
        features[28] = float(
            str_vals.str.match(r".*(?:aceae|idae|ales|ineae)$").sum() / n
        )

    # Numeric patterns (1) - mean decimals
    if is_numeric:
        try:
            str_nums = clean.astype(str)
            dec_counts = str_nums.str.extract(r"\.(\d+)$")[0].str.len()
            features[29] = float(dec_counts.mean()) if dec_counts.notna().any() else 0
        except Exception:
            pass

    # Range indicators (5)
    if is_numeric:
        try:
            features[30] = float(((clean >= -90) & (clean <= 90)).mean())
            features[31] = float(((clean >= -180) & (clean <= 180)).mean())
            features[32] = float(((clean >= 0) & (clean <= 1)).mean())
            features[33] = float(
                ((clean >= 0) & (clean <= 100) & (clean == clean.astype(int))).mean()
            )
        except Exception:
            pass

    # Text pattern (1)
    if len(str_vals) > 0:
        features[34] = float(str_vals.str.match(r"^[A-Z]").sum() / len(str_vals))

    # Meta (2)
    features[35] = 1.0 if is_numeric else 0.0
    features[36] = len(clean)

    return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
