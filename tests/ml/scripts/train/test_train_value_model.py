import logging

import numpy as np

from ml.scripts.train.train_value_model import build_model, evaluate_kfold


def test_build_model_applies_hyperparameter_overrides():
    model = build_model(max_iter=1, max_depth=2)

    assert model.max_iter == 1
    assert model.max_depth == 2


def test_evaluate_kfold_skips_single_class_training_folds(caplog):
    x = np.array([[0.0], [1.0], [2.0], [3.0]])
    concepts = ["measurement", "measurement", "taxonomy", "taxonomy"]
    groups = np.array(["dataset_a", "dataset_a", "dataset_b", "dataset_b"])

    with caplog.at_level(logging.WARNING):
        score = evaluate_kfold(x, concepts, groups, n_splits=2)

    assert score == 0.0
    assert "training split has only one class" in caplog.text
    assert "No evaluable folds" in caplog.text
