import logging

import numpy as np

from ml.scripts.train.train_header_model import evaluate_kfold


def test_evaluate_kfold_skips_single_class_training_folds(caplog):
    names = ["height", "diameter", "species", "taxon"]
    concepts = ["measurement", "measurement", "taxonomy", "taxonomy"]
    groups = np.array(["dataset_a", "dataset_a", "dataset_b", "dataset_b"])

    with caplog.at_level(logging.WARNING):
        score = evaluate_kfold(names, concepts, groups, n_splits=2)

    assert score == 0.0
    assert "training split has only one class" in caplog.text
    assert "No evaluable folds" in caplog.text
