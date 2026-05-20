from pathlib import Path

import numpy as np
import pandas as pd

from niamoto.common import bundle
from niamoto.core.imports.ml import classifier


def test_get_resource_path_finds_repository_ml_models(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    module_path = repo_root / "src" / "niamoto" / "core" / "imports" / "ml"
    module_path.mkdir(parents=True)
    model_path = repo_root / "ml" / "models" / "header_model.joblib"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"model")

    monkeypatch.setattr(classifier, "__file__", str(module_path / "classifier.py"))
    monkeypatch.setattr(
        bundle,
        "get_resource_path",
        lambda relative: tmp_path / "missing" / relative,
    )

    result = classifier._get_resource_path(
        "ml/models/header_model.joblib",
        "models/header_model.joblib",
    )

    assert result == model_path


def test_classify_many_uses_value_model_when_header_model_is_missing(monkeypatch):
    class FakeValueModel:
        classes_ = np.array(["measurement.count", "taxon.name"])

        def predict_proba(self, features):
            assert len(features) == 1
            return np.array([[0.82, 0.18]])

    value_path = Path("/tmp/value_model.joblib")

    def fake_get_resource_path(*relatives):
        if relatives[0] == "ml/models/value_model.joblib":
            return value_path
        return Path("/tmp/missing.joblib")

    def fake_exists(path):
        return path == value_path

    def fake_load(path):
        assert path == value_path
        return {"model": FakeValueModel()}

    monkeypatch.setattr(classifier, "_get_resource_path", fake_get_resource_path)
    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr("joblib.load", fake_load)

    model = classifier.ColumnClassifier()
    result = model.classify_many(
        [("anonymous", pd.Series([1, 2, 3]))],
        normalized_names=["x1"],
    )

    assert result == [("measurement.count", 0.82)]
