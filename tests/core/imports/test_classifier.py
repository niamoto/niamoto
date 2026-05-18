from pathlib import Path

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
