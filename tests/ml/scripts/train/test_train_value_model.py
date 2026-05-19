from ml.scripts.train.train_value_model import build_model


def test_build_model_applies_hyperparameter_overrides():
    model = build_model(max_iter=1, max_depth=2)

    assert model.max_iter == 1
    assert model.max_depth == 2
