"""Centralized domain vocabulary for import auto-configuration.

The product has explicit biodiversity and spatial concepts. This module keeps
that vocabulary in one place so heuristics and relationship rules can consume
shared definitions instead of scattering strings across the codebase.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence


STABLE_ENTITY_SYNONYMS = {
    "plot": ("plot", "parcelle", "quadrat", "transect"),
    "taxon": (
        "taxon",
        "taxa",
    ),
    "locality": ("locality", "location", "site", "localite", "lieu"),
}

FALLBACK_ENTITY_SYNONYMS = {
    "occurrence": ("occurrence", "occurrences"),
    "observation": ("observation", "observations"),
    "taxon": ("species", "genus", "family", "taxaname", "scientific"),
}

TAXONOMIC_HIERARCHY_PATTERNS = {
    "kingdom": ("kingdom", "regne", "regnum", "tax_kingdom"),
    "phylum": ("phylum", "embranchement", "division", "tax_phylum"),
    "class": ("class", "classe", "tax_class"),
    "order": ("order", "ordre", "ordo", "tax_order"),
    "family": ("family", "famille", "familia", "tax_fam", "tax_family"),
    "genus": ("genus", "genre", "tax_gen", "tax_genus"),
    "species": (
        "species",
        "espece",
        "epithet",
        "sp",
        "tax_sp",
        "tax_species",
        "tax_sp_level",
        "tax_esp",
    ),
    "subspecies": (
        "subspecies",
        "sous-espece",
        "infra",
        "var",
        "variety",
        "tax_infra",
        "tax_infra_level",
    ),
}

GEOGRAPHIC_HIERARCHY_PATTERNS = {
    "country": ("country", "pays", "nation", "pais"),
    "region": ("region", "province", "state", "etat", "territorio"),
    "locality": (
        "locality",
        "locality_name",
        "site",
        "location",
        "lieu",
        "localite",
        "local",
    ),
    "sublocality": ("sublocality", "subsite", "sublocation", "zone"),
    "plot": (
        "plot",
        "plot_name",
        "parcelle",
        "quadrat",
        "releve",
        "relevé",
        "transect",
    ),
}

TAXONOMIC_LEVELS = tuple(TAXONOMIC_HIERARCHY_PATTERNS.keys())
GEOGRAPHIC_LEVELS = tuple(GEOGRAPHIC_HIERARCHY_PATTERNS.keys())

GENERIC_NAME_PATTERNS = (
    "name",
    "nom",
    "label",
    "title",
    "titre",
    "designation",
    "full_name",
)
STABLE_DOMAIN_NAME_PATTERNS = (
    "scientific_name",
    "taxon_name",
    "plot",
    "site",
    "locality",
    "station",
)
FALLBACK_DOMAIN_NAME_PATTERNS = ("taxaname",)

STABLE_OBSERVATION_FIELD_MARKERS = (
    "dbh",
    "height",
    "diameter",
    "measurement",
    "stem_diameter",
)
FALLBACK_OBSERVATION_FIELD_MARKERS = ("value",)

RELATIONSHIP_IDENTIFIER_TARGETS = {
    "taxon": frozenset({"id", "taxon_id", "id_taxon", "id_taxonref"}),
    "plot": frozenset({"id", "plot_id", "id_plot"}),
}

STABLE_DERIVED_TAXON_NAME_PATTERNS = ("scientific_name", "taxon_name")
FALLBACK_DERIVED_TAXON_NAME_PATTERNS = ("taxaname",)

ENTITY_SYNONYMS = {
    entity: tuple(
        list(STABLE_ENTITY_SYNONYMS.get(entity, ()))
        + list(FALLBACK_ENTITY_SYNONYMS.get(entity, ()))
    )
    for entity in set(STABLE_ENTITY_SYNONYMS) | set(FALLBACK_ENTITY_SYNONYMS)
}

DOMAIN_NAME_PATTERNS = STABLE_DOMAIN_NAME_PATTERNS + FALLBACK_DOMAIN_NAME_PATTERNS
OBSERVATION_FIELD_MARKERS = (
    STABLE_OBSERVATION_FIELD_MARKERS + FALLBACK_OBSERVATION_FIELD_MARKERS
)
DERIVED_TAXON_NAME_PATTERNS = (
    STABLE_DERIVED_TAXON_NAME_PATTERNS + FALLBACK_DERIVED_TAXON_NAME_PATTERNS
)


def matches_entity_name(
    value: Optional[str], entity: str, *, include_fallback: bool = True
) -> bool:
    """Return True when text matches a known domain entity token."""
    if not value:
        return False

    normalized = value.lower().replace("-", "_")
    synonyms = list(STABLE_ENTITY_SYNONYMS.get(entity, ()))
    if include_fallback:
        synonyms.extend(FALLBACK_ENTITY_SYNONYMS.get(entity, ()))

    for synonym in synonyms:
        if synonym in normalized:
            return True
    return False


def infer_entity_token(
    value: Optional[str],
    *,
    allowed: Sequence[str] | None = None,
    include_fallback: bool = True,
) -> Optional[str]:
    """Infer a coarse entity token such as plot, taxon, or locality."""
    candidate_entities: Iterable[str] = allowed or ENTITY_SYNONYMS.keys()
    for entity in candidate_entities:
        if matches_entity_name(value, entity, include_fallback=include_fallback):
            return entity
    return None


def infer_taxonomy_reference_name(dataset_name: str, levels: Sequence[str]) -> str:
    """Infer a derived taxonomy reference name from dataset hints."""
    level_set = {level.lower() for level in levels}
    if matches_entity_name(dataset_name, "occurrence"):
        if level_set.intersection(TAXONOMIC_LEVELS):
            return "taxons"
        return "taxonomy"
    if matches_entity_name(dataset_name, "observation"):
        return "taxa"
    return f"{dataset_name}_hierarchy"


def find_taxon_identifier_column(columns: Sequence[str]) -> Optional[str]:
    """Find the most likely taxon identifier column in a source dataset."""
    for column in columns:
        lower = column.lower()
        if "id" in lower and matches_entity_name(lower, "taxon"):
            return column
    return None


def find_taxon_name_column(columns: Sequence[str]) -> Optional[str]:
    """Find the most likely taxon label column in a source dataset."""
    for column in columns:
        lower = column.lower()
        if any(pattern in lower for pattern in DERIVED_TAXON_NAME_PATTERNS):
            return column
    return None
