"""
Domain-specific anomaly detection rules for ecological data.

Deterministic, explainable validators — no Isolation Forest.
Each rule returns a boolean mask of anomalous values.
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Anomaly rules by concept ────────────────────────────────────

ANOMALY_RULES: dict[str, dict] = {
    "location.latitude": {
        "rule": lambda s: (s < -90) | (s > 90) | (s.abs() < 0.001),
        "description": "Latitude must be between -90 and 90, non-zero",
    },
    "location.longitude": {
        "rule": lambda s: (s < -180) | (s > 180) | (s.abs() < 0.001),
        "description": "Longitude must be between -180 and 180, non-zero",
    },
    "measurement.diameter": {
        "rule": lambda s: (s < 0) | (s > 500),
        "description": "DBH must be 0-500 cm",
    },
    "measurement.height": {
        "rule": lambda s: (s < 0) | (s > 150),
        "description": "Tree height must be 0-150 m",
    },
    "measurement.wood_density": {
        "rule": lambda s: (s < 0.05) | (s > 1.5),
        "description": "Wood density must be 0.05-1.5 g/cm³",
    },
    "measurement.cover": {
        "rule": lambda s: (s < 0) | (s > 100),
        "description": "Cover percentage must be 0-100%",
    },
    "location.elevation": {
        "rule": lambda s: (s < -500) | (s > 9000),
        "description": "Elevation must be -500 to 9000 m",
    },
    "location.depth": {
        "rule": lambda s: s > 0,
        "description": "Depth should be negative (below surface)",
    },
    "environment.ph": {
        "rule": lambda s: (s < 0) | (s > 14),
        "description": "pH must be 0-14",
    },
    "environment.temperature": {
        "rule": lambda s: (s < -90) | (s > 60),
        "description": "Temperature must be -90 to 60°C",
    },
    "environment.precipitation": {
        "rule": lambda s: (s < 0) | (s > 15000),
        "description": "Precipitation must be 0-15000 mm",
    },
    "measurement.leaf_area": {
        "rule": lambda s: (s < 0) | (s > 10000),
        "description": "Leaf area must be 0-10000 cm²",
    },
}


def detect_anomalies(
    series: pd.Series,
    concept: Optional[str],
) -> pd.Series:
    """Detect anomalous values in a column using domain rules.

    Args:
        series: Column values
        concept: Semantic concept (e.g. "measurement.diameter")

    Returns:
        Boolean series: True for anomalous values
    """
    clean = series.dropna()
    if len(clean) == 0:
        return pd.Series(False, index=series.index)

    # Try concept-specific rule
    if concept and concept in ANOMALY_RULES:
        rule_spec = ANOMALY_RULES[concept]
        try:
            numeric = pd.to_numeric(clean, errors="coerce").dropna()
            if len(numeric) > 0:
                mask = pd.Series(False, index=series.index)
                mask.loc[numeric.index] = rule_spec["rule"](numeric)
                n_anomalies = mask.sum()
                if n_anomalies > 0:
                    logger.debug(
                        "%s: %d anomalies detected (%s)",
                        concept,
                        n_anomalies,
                        rule_spec["description"],
                    )
                return mask
        except Exception:
            pass

    # Fallback: IQR × 3 for numeric columns
    if pd.api.types.is_numeric_dtype(clean):
        q1, q3 = clean.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr > 0:
            mask = pd.Series(False, index=series.index)
            mask.loc[clean.index] = (clean < q1 - 3 * iqr) | (clean > q3 + 3 * iqr)
            return mask

    return pd.Series(False, index=series.index)


def summarize_anomalies(
    series: pd.Series,
    concept: Optional[str],
) -> Optional[dict]:
    """Get a summary of anomalies for a column.

    Returns None if no anomalies, otherwise a dict with count and details.
    """
    mask = detect_anomalies(series, concept)
    n = mask.sum()
    if n == 0:
        return None

    rule_desc = ""
    if concept and concept in ANOMALY_RULES:
        rule_desc = ANOMALY_RULES[concept]["description"]

    return {
        "n_anomalies": int(n),
        "pct_anomalies": round(float(n / len(series) * 100), 2),
        "rule": rule_desc or "IQR × 3 outlier detection",
        "concept": concept,
    }
