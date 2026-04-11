"""Tests for centralized domain vocabulary helpers."""

from niamoto.core.domain_vocabulary import (
    FALLBACK_ENTITY_SYNONYMS,
    STABLE_ENTITY_SYNONYMS,
    find_taxon_identifier_column,
    find_taxon_name_column,
    infer_entity_token,
    infer_taxonomy_reference_name,
    matches_entity_name,
)


def test_matches_entity_name_supports_domain_synonyms():
    assert matches_entity_name("sample_occurrences", "occurrence") is True
    assert matches_entity_name("raw_plot_stats", "plot") is True
    assert matches_entity_name("taxonomy_lookup", "plot") is False


def test_matches_entity_name_can_exclude_fallback_synonyms():
    assert matches_entity_name("sample_species", "taxon") is True
    assert (
        matches_entity_name("sample_species", "taxon", include_fallback=False) is False
    )


def test_infer_entity_token_prefers_allowed_domain_tokens():
    assert infer_entity_token("plot_name", allowed=("plot", "taxon")) == "plot"
    assert infer_entity_token("id_taxonref", allowed=("plot", "taxon")) == "taxon"


def test_infer_taxonomy_reference_name_uses_shared_vocabulary():
    assert (
        infer_taxonomy_reference_name("sample_occurrences", ["family", "species"])
        == "taxons"
    )
    assert infer_taxonomy_reference_name("forest_observations", ["locality"]) == "taxa"
    assert (
        infer_taxonomy_reference_name("inventory", ["locality"])
        == "inventory_hierarchy"
    )


def test_taxon_column_helpers_use_shared_patterns():
    columns = ["id_taxonref", "scientific_name", "plot_id"]

    assert find_taxon_identifier_column(columns) == "id_taxonref"
    assert find_taxon_name_column(columns) == "scientific_name"


def test_domain_vocabulary_exposes_stable_and_fallback_layers():
    assert "plot" in STABLE_ENTITY_SYNONYMS["plot"]
    assert "species" in FALLBACK_ENTITY_SYNONYMS["taxon"]
