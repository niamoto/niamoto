"""Package-level export contract tests for transformer plugins."""


def test_transformers_all_exports_are_bound():
    import niamoto.core.plugins.transformers as transformers

    missing = [name for name in transformers.__all__ if not hasattr(transformers, name)]

    assert missing == []


def test_transformers_import_star_exports_public_names():
    namespace = {}

    exec("from niamoto.core.plugins.transformers import *", namespace)

    import niamoto.core.plugins.transformers as transformers

    for name in transformers.__all__:
        assert name in namespace
