"""Package-level export contract tests for transformer plugins."""

from niamoto.core.plugins.transformers.chains.transform_chain import TransformChain


EXPECTED_PUBLIC_EXPORTS = {"TransformChain"}


def test_transformers_all_exports_are_bound():
    import niamoto.core.plugins.transformers as transformers

    assert EXPECTED_PUBLIC_EXPORTS <= set(transformers.__all__)
    missing = [name for name in transformers.__all__ if not hasattr(transformers, name)]

    assert missing == []
    assert transformers.TransformChain is TransformChain


def test_transformers_import_star_exports_public_names():
    namespace = {}

    exec("from niamoto.core.plugins.transformers import *", namespace)

    import niamoto.core.plugins.transformers as transformers

    for name in transformers.__all__:
        assert name in namespace
