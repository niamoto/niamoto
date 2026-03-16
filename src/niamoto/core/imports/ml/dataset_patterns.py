"""
Dataset Pattern Detector (M1).

Classifies an entire dataset based on the aggregate affordances of its columns.
Unlocks multi-column suggestions that single-column matching cannot provide.

Example: a dataset with coordinates + taxonomy → "occurrence inventory" →
suggest a distribution map AND a taxonomy breakdown.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DatasetPattern:
    """A detected dataset pattern with associated suggestions."""

    name: str
    description: str
    confidence: float
    suggestions: list[dict] = field(default_factory=list)


# ── Pattern definitions ──────────────────────────────────────────
# Each pattern checks for the presence of affordance-groups across columns.
# "requires" are boolean flags derived from the aggregate affordances.

PATTERNS = {
    "occurrence_inventory": {
        "description": "Occurrence/observation dataset with coordinates and taxonomy",
        "requires": ["has_coordinates", "has_taxonomy"],
        "suggests": [
            {
                "transformer": "geospatial_extractor",
                "widget": "interactive_map",
                "reason": "Distribution map of observations",
            },
            {
                "transformer": "categorical_distribution",
                "widget": "bar_plot",
                "reason": "Taxonomy breakdown",
            },
        ],
    },
    "forest_inventory": {
        "description": "Forest inventory with measurements and taxonomy",
        "requires": ["has_measurements", "has_taxonomy"],
        "suggests": [
            {
                "transformer": "binned_distribution",
                "widget": "bar_plot",
                "reason": "DBH/height distribution",
            },
            {
                "transformer": "scatter_analysis",
                "widget": "scatter_plot",
                "reason": "Allometric relationship",
            },
            {
                "transformer": "categorical_distribution",
                "widget": "donut_chart",
                "reason": "Family/genus breakdown",
            },
        ],
    },
    "spatial_inventory": {
        "description": "Inventory with coordinates and measurements",
        "requires": ["has_coordinates", "has_measurements"],
        "suggests": [
            {
                "transformer": "geospatial_extractor",
                "widget": "interactive_map",
                "reason": "Spatial distribution of measurements",
            },
            {
                "transformer": "binned_distribution",
                "widget": "bar_plot",
                "reason": "Measurement distribution",
            },
        ],
    },
    "taxonomic_checklist": {
        "description": "Taxonomy reference without coordinates",
        "requires": ["has_taxonomy", "not:has_coordinates"],
        "suggests": [
            {
                "transformer": "hierarchy_distribution",
                "widget": "sunburst",
                "reason": "Taxonomic hierarchy visualization",
            },
            {
                "transformer": "categorical_distribution",
                "widget": "donut_chart",
                "reason": "Family distribution",
            },
        ],
    },
    "trait_dataset": {
        "description": "Functional trait dataset with multiple measurements",
        "requires": ["has_many_measurements", "has_taxonomy"],
        "suggests": [
            {
                "transformer": "scatter_analysis",
                "widget": "scatter_plot",
                "reason": "Trait correlation analysis",
            },
            {
                "transformer": "statistical_summary",
                "widget": "info_block",
                "reason": "Trait summary statistics",
            },
        ],
    },
    "temporal_monitoring": {
        "description": "Monitoring dataset with temporal and measurement data",
        "requires": ["has_temporal", "has_measurements"],
        "suggests": [
            {
                "transformer": "temporal_aggregation",
                "widget": "line_plot",
                "reason": "Temporal trends",
            },
            {
                "transformer": "binned_distribution",
                "widget": "bar_plot",
                "reason": "Measurement distribution",
            },
        ],
    },
}


def detect_dataset_patterns(
    profiles: list,
) -> list[DatasetPattern]:
    """Detect dataset-level patterns from column profiles.

    Args:
        profiles: List of ColumnSemanticProfile from all columns in a dataset

    Returns:
        Matched patterns sorted by relevance
    """
    # Aggregate affordances and roles
    all_affordances: set[str] = set()
    all_roles: set[str] = set()
    measurement_count = 0

    for p in profiles:
        all_affordances.update(p.affordances)
        all_roles.add(p.role)
        if p.role == "measurement":
            measurement_count += 1

    # Compute boolean flags
    flags = {
        "has_coordinates": "coordinate" in all_affordances
        and "mappable" in all_affordances,
        "has_taxonomy": "taxonomy" in all_roles,
        "has_measurements": "measurement" in all_roles,
        "has_many_measurements": measurement_count >= 3,
        "has_temporal": "temporal" in all_affordances,
    }

    # Match patterns
    matched = []
    for pattern_name, spec in PATTERNS.items():
        requirements = spec["requires"]
        all_met = True

        for req in requirements:
            if req.startswith("not:"):
                flag_name = req[4:]
                if flags.get(flag_name, False):
                    all_met = False
                    break
            else:
                if not flags.get(req, False):
                    all_met = False
                    break

        if all_met:
            # Confidence based on how many flags are true
            n_true = sum(1 for v in flags.values() if v)
            confidence = min(1.0, n_true / len(flags))

            matched.append(
                DatasetPattern(
                    name=pattern_name,
                    description=spec["description"],
                    confidence=confidence,
                    suggestions=spec["suggests"],
                )
            )

    # Sort by confidence
    matched.sort(key=lambda p: -p.confidence)
    return matched
