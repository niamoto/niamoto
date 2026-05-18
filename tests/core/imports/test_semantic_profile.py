from niamoto.core.imports.ml.semantic_profile import get_affordances


def test_get_affordances_returns_copy_for_concept_mapping():
    affordances = get_affordances("measurement.height", "measurement")

    affordances.add("mutated")

    assert "mutated" not in get_affordances("measurement.height", "measurement")


def test_get_affordances_returns_copy_for_role_fallback():
    affordances = get_affordances(None, "measurement")

    affordances.add("mutated")

    assert "mutated" not in get_affordances(None, "measurement")
