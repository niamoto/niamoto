"""
ColumnSemanticProfile: rich semantic description of a column.

Replaces flat `semantic_type` strings with a 3-axis description:
- role: what the column IS (measurement, taxonomy, location, time, category...)
- concept: what it MEANS (measurement.diameter, taxonomy.species, location.latitude...)
- affordances: what it CAN DO (numeric_continuous, histogrammable, mappable, join_key...)

The affordances drive transformer→widget matching: a column that is
`numeric_continuous + histogrammable` gets a histogram regardless of whether
it's a diameter or a height.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ColumnSemanticProfile:
    """Rich semantic profile for a column."""

    role: (
        str  # identifier, measurement, category, time, location, taxonomy, text, other
    )
    concept: Optional[str] = (
        None  # measurement.diameter, taxonomy.species, None if uncertain
    )
    affordances: set[str] = field(default_factory=set)
    confidence: float = 0.0  # 0.0-1.0, calibrated
    evidence: dict[str, float] = field(
        default_factory=dict
    )  # header_score, value_score...

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "concept": self.concept,
            "affordances": sorted(self.affordances),
            "confidence": round(self.confidence, 3),
            "evidence": {k: round(v, 3) for k, v in self.evidence.items()},
        }

    @property
    def semantic_type(self) -> Optional[str]:
        """Backward-compatible flat semantic type string."""
        return self.concept


# ── Affordance mappings ──────────────────────────────────────────

CONCEPT_AFFORDANCES: dict[str, set[str]] = {
    # Measurements
    "measurement.diameter": {
        "numeric_continuous",
        "histogrammable",
        "unit_bearing",
        "scatterable",
    },
    "measurement.height": {
        "numeric_continuous",
        "histogrammable",
        "unit_bearing",
        "scatterable",
    },
    "measurement.biomass": {
        "numeric_continuous",
        "histogrammable",
        "unit_bearing",
        "scatterable",
    },
    "measurement.wood_density": {
        "numeric_continuous",
        "histogrammable",
        "unit_bearing",
        "scatterable",
    },
    "measurement.leaf_area": {
        "numeric_continuous",
        "histogrammable",
        "unit_bearing",
        "scatterable",
    },
    "measurement.cover": {"numeric_continuous", "histogrammable", "percentage"},
    "measurement.canopy": {"numeric_continuous", "histogrammable", "unit_bearing"},
    "measurement.growth": {"numeric_continuous", "histogrammable", "temporal_change"},
    "measurement.terrain": {"numeric_continuous", "histogrammable"},
    "measurement.dimension": {"numeric_continuous", "unit_bearing"},
    "measurement.uncertainty": {"numeric_continuous"},
    "measurement.volume": {"numeric_continuous", "histogrammable", "unit_bearing"},
    "measurement.trait": {"numeric_continuous", "histogrammable", "scatterable"},
    "measurement.soil": {"numeric_continuous", "histogrammable"},
    "measurement.quality": {"numeric_continuous"},
    # Location
    "location.latitude": {"numeric_continuous", "coordinate", "mappable"},
    "location.longitude": {"numeric_continuous", "coordinate", "mappable"},
    "location.coordinate": {"numeric_continuous", "coordinate", "mappable"},
    "location.elevation": {
        "numeric_continuous",
        "histogrammable",
        "unit_bearing",
        "mappable",
    },
    "location.depth": {"numeric_continuous", "histogrammable", "unit_bearing"},
    "location.locality": {"categorical", "filterable"},
    "location.country": {"categorical", "filterable", "mappable"},
    "location.admin_area": {"categorical", "filterable"},
    "location.continent": {"categorical", "filterable"},
    # Taxonomy
    "taxonomy.species": {"categorical", "rankable", "hierarchy_level", "searchable"},
    "taxonomy.family": {"categorical", "rankable", "hierarchy_level"},
    "taxonomy.genus": {"categorical", "rankable", "hierarchy_level"},
    "taxonomy.rank": {"categorical"},
    "taxonomy.name": {"categorical", "searchable"},
    "taxonomy.kingdom": {"categorical", "hierarchy_level"},
    "taxonomy.phylum": {"categorical", "hierarchy_level"},
    "taxonomy.class": {"categorical", "hierarchy_level"},
    "taxonomy.order": {"categorical", "hierarchy_level"},
    # Time
    "event.date": {"temporal", "sortable", "filterable"},
    "event.year": {"temporal", "sortable", "filterable", "numeric_discrete"},
    # Legacy profiler returns temporal.* instead of event.*
    "temporal.date": {"temporal", "sortable", "filterable"},
    "temporal.year": {"temporal", "sortable", "filterable", "numeric_discrete"},
    # Identifiers
    "identifier.record": {"join_key", "unique"},
    "identifier.plot": {"join_key", "filterable"},
    "identifier.collection": {"categorical"},
    "identifier.institution": {"categorical"},
    "identifier.taxon": {"join_key"},
    # Categories
    "category.status": {"categorical", "filterable"},
    "category.basis": {"categorical"},
    "category.habitat": {"categorical", "filterable"},
    "category.vegetation": {"categorical", "filterable"},
    "category.tree_condition": {"categorical", "filterable"},
    "category.management": {"categorical", "filterable"},
    "category.ecology": {"categorical", "filterable"},
    "category.growth_form": {"categorical", "filterable"},
    "category.soil": {"categorical"},
    "category.light": {"categorical"},
    "category.quality": {"categorical"},
    "category.damage": {"categorical", "filterable"},
    # Environment
    "environment.temperature": {"numeric_continuous", "histogrammable", "unit_bearing"},
    "environment.precipitation": {
        "numeric_continuous",
        "histogrammable",
        "unit_bearing",
    },
    "environment.water": {"numeric_continuous", "histogrammable"},
    # Statistics
    "statistic.count": {"numeric_discrete", "histogrammable", "summable"},
    # Text
    "text.observer": {"categorical", "searchable"},
    "text.source": {"categorical"},
    "text.metadata": {"searchable"},
}

# Fallback affordances by role (when concept is unknown or abstained)
ROLE_AFFORDANCES: dict[str, set[str]] = {
    "measurement": {"numeric_continuous", "histogrammable"},
    "location": {"filterable"},
    "taxonomy": {"categorical", "rankable"},
    "time": {"temporal", "sortable"},
    "identifier": {"join_key"},
    "category": {"categorical", "filterable"},
    "environment": {"numeric_continuous", "histogrammable"},
    "statistic": {"numeric_discrete", "histogrammable"},
    "text": {"searchable"},
    "other": set(),
}


def get_affordances(concept: Optional[str], role: str) -> set[str]:
    """Get affordances for a concept, falling back to role defaults."""
    if concept and concept in CONCEPT_AFFORDANCES:
        return CONCEPT_AFFORDANCES[concept]
    return ROLE_AFFORDANCES.get(role, set())
