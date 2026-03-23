"""Shared value feature extraction for training and runtime inference."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import scipy.stats

FEATURE_NAMES = [
    # Numeric stats (14)
    "num_mean",
    "num_std",
    "num_min",
    "num_max",
    "num_skew",
    "num_kurtosis",
    "num_q25",
    "num_q50",
    "num_q75",
    "num_range",
    "num_cv",
    "num_negative_ratio",
    "num_integer_ratio",
    "num_zero_ratio",
    # Uniqueness and distribution (3)
    "unique_ratio",
    "null_ratio",
    "entropy",
    # Character features (6)
    "mean_length",
    "std_length",
    "digit_ratio",
    "alpha_ratio",
    "space_ratio",
    "mean_word_count",
    # Regex patterns (4)
    "pct_date_iso",
    "pct_coordinate",
    "pct_boolean",
    "pct_uuid",
    # Biological patterns (2)
    "binomial_score",
    "family_suffix",
    # Numeric patterns (6)
    "mean_decimals",
    "in_lat_range",
    "in_lon_range",
    "in_01_range",
    "small_int_ratio",
    "pct_starts_upper",
    # Meta (2)
    "is_numeric",
    "n_values",
    # Code/category diagnostics (6)
    "n_unique_values",
    "dominant_ratio",
    "fixed_length_ratio",
    "short_code_ratio",
    "dense_integer_domain",
    "tiny_integer_domain",
]

_BOOLEAN_VALUES = {"true", "false", "yes", "no", "0", "1", "oui", "non"}


def _fixed_length_ratio(lengths: pd.Series) -> float:
    if len(lengths) == 0:
        return 0.0
    counts = lengths.value_counts(normalize=True)
    return float(counts.iloc[0]) if len(counts) > 0 else 0.0


def _short_code_ratio(str_vals: pd.Series) -> float:
    if len(str_vals) == 0:
        return 0.0
    pattern = r"^[A-Z0-9][A-Z0-9_/-]{0,7}$"
    return float(str_vals.str.match(pattern).mean())


def _dense_integer_domain(num_series: pd.Series) -> tuple[float, float]:
    if len(num_series) == 0:
        return 0.0, 0.0
    if not bool((num_series == num_series.astype(int)).all()):
        return 0.0, 0.0
    domain = int(num_series.max() - num_series.min()) + 1
    if domain <= 0:
        return 0.0, 0.0
    dense = min(float(num_series.nunique() / domain), 1.0)
    tiny = 1.0 if domain <= 10 else 0.0
    return dense, tiny


def extract_value_features_from_sample(
    values_sample: Sequence[Any],
    stats: Mapping[str, Any],
) -> np.ndarray:
    """Extract value features from serialized training data."""
    series = pd.Series(list(values_sample))
    is_numeric = (
        str(stats.get("dtype", "")).startswith(("int", "float")) or "mean" in stats
    )
    unique_ratio = float(stats.get("unique_ratio", 0) or 0.0)
    null_ratio = float(stats.get("null_ratio", 0) or 0.0)
    return _extract_value_features(
        series,
        is_numeric=is_numeric,
        unique_ratio=unique_ratio,
        null_ratio=null_ratio,
    )


def extract_value_features_from_series(series: pd.Series) -> np.ndarray:
    """Extract value features from a runtime pandas series."""
    return _extract_value_features(
        series,
        is_numeric=bool(pd.api.types.is_numeric_dtype(series.dropna())),
        unique_ratio=float(series.nunique() / max(len(series), 1)),
        null_ratio=float(series.isnull().mean()),
    )


def _extract_value_features(
    series: pd.Series,
    *,
    is_numeric: bool,
    unique_ratio: float,
    null_ratio: float,
) -> np.ndarray:
    """Shared implementation for train/runtime value feature extraction."""
    features = np.zeros(len(FEATURE_NAMES))
    if len(series) == 0:
        features[14] = unique_ratio
        features[15] = null_ratio
        return features

    clean = series.dropna()
    if len(clean) == 0:
        features[14] = unique_ratio
        features[15] = null_ratio
        return features

    str_vals = clean.astype(str)

    # Numeric features
    if is_numeric:
        try:
            num_series = pd.to_numeric(clean, errors="coerce").dropna()
            if len(num_series) > 0:
                features[0] = float(num_series.mean())
                features[1] = float(num_series.std()) if len(num_series) > 1 else 0.0
                features[2] = float(num_series.min())
                features[3] = float(num_series.max())
                features[4] = float(num_series.skew()) if len(num_series) > 2 else 0.0
                features[5] = (
                    float(num_series.kurtosis()) if len(num_series) > 3 else 0.0
                )
                features[6] = float(num_series.quantile(0.25))
                features[7] = float(num_series.median())
                features[8] = float(num_series.quantile(0.75))
                features[9] = float(num_series.max() - num_series.min())
                features[10] = (
                    float(num_series.std() / num_series.mean())
                    if num_series.mean() != 0
                    else 0.0
                )
                features[11] = float((num_series < 0).mean())
                features[12] = float((num_series == num_series.astype(int)).mean())
                features[13] = float((num_series == 0).mean())
                dense_domain, tiny_domain = _dense_integer_domain(num_series)
                features[41] = dense_domain
                features[42] = tiny_domain
        except Exception:
            pass

    # Uniqueness and distribution
    features[14] = unique_ratio
    features[15] = null_ratio
    vc = clean.value_counts(normalize=True)
    features[16] = float(scipy.stats.entropy(vc)) if len(vc) > 1 else 0.0

    # Character features
    lengths = str_vals.str.len()
    features[17] = float(lengths.mean())
    features[18] = float(lengths.std()) if len(lengths) > 1 else 0.0
    total_chars = max(lengths.sum(), 1)
    features[19] = float(str_vals.str.count(r"\d").sum() / total_chars)
    features[20] = float(str_vals.str.count(r"[a-zA-Z]").sum() / total_chars)
    features[21] = float(str_vals.str.count(r"\s").sum() / total_chars)
    features[22] = float(str_vals.str.split().str.len().mean())

    # Regex patterns
    n = len(str_vals)
    features[23] = float(str_vals.str.match(r"^\d{4}-\d{2}-\d{2}").sum() / n)
    features[24] = float(str_vals.str.match(r"^-?\d{1,3}\.\d{4,}$").sum() / n)
    features[25] = float(str_vals.str.lower().isin(_BOOLEAN_VALUES).sum() / n)
    features[26] = float(str_vals.str.match(r"^[0-9a-f]{8}-[0-9a-f]{4}").sum() / n)

    # Biological patterns
    features[27] = float(str_vals.str.match(r"^[A-Z][a-z]+ [a-z]+").sum() / n)
    features[28] = float(str_vals.str.match(r".*(?:aceae|idae|ales|ineae)$").sum() / n)

    # Numeric patterns
    if is_numeric:
        try:
            num_series = pd.to_numeric(clean, errors="coerce").dropna()
            if len(num_series) > 0:
                str_nums = num_series.astype(str)
                dec_counts = str_nums.str.extract(r"\.(\d+)$")[0].str.len()
                features[29] = (
                    float(dec_counts.mean()) if dec_counts.notna().any() else 0.0
                )
                features[30] = float(((num_series >= -90) & (num_series <= 90)).mean())
                features[31] = float(
                    ((num_series >= -180) & (num_series <= 180)).mean()
                )
                features[32] = float(((num_series >= 0) & (num_series <= 1)).mean())
                features[33] = float(
                    (
                        (num_series >= 0)
                        & (num_series <= 100)
                        & (num_series == num_series.astype(int))
                    ).mean()
                )
        except Exception:
            pass

    # Text/code diagnostics
    features[34] = float(str_vals.str.match(r"^[A-Z]").sum() / len(str_vals))
    features[35] = 1.0 if is_numeric else 0.0
    features[36] = len(clean)
    features[37] = float(clean.nunique())
    features[38] = float(vc.iloc[0]) if len(vc) > 0 else 0.0
    features[39] = _fixed_length_ratio(lengths)
    features[40] = _short_code_ratio(str_vals)

    return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
