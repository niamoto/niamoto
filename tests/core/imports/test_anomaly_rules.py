import pandas as pd

from niamoto.core.imports.ml.anomaly_rules import detect_anomalies, summarize_anomalies


def test_detect_anomalies_skips_boolean_series_for_iqr_fallback():
    series = pd.Series([True, False, True, False, True], dtype="bool")

    mask = detect_anomalies(series, concept="attribute.presence")

    assert mask.tolist() == [False, False, False, False, False]


def test_summarize_anomalies_returns_none_for_boolean_series_without_rule():
    series = pd.Series([True, False, True, False], dtype="bool")

    summary = summarize_anomalies(series, concept="attribute.presence")

    assert summary is None
