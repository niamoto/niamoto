"""
Concept taxonomy: maps fine-grained concepts to coarser groups for training.

The gold set has 111 concepts, many with < 5 examples. This module provides
a mapping to reduce to ~45 concepts for better ML performance, plus utilities
to convert between fine and coarse levels.
"""

# Fine → Coarse mapping.
# Concepts not listed here keep their original name.
CONCEPT_MERGE = {
    # ── category: merge rare subtypes ──
    "category.succession": "category.ecology",
    "category.bioclimate": "category.ecology",
    "category.origin": "category.ecology",
    "category.life_stage": "category.ecology",
    "category.endemism": "category.ecology",
    "category.stem_type": "category.tree_condition",
    "category.form": "category.tree_condition",
    "category.pollard": "category.tree_condition",
    "category.target": "category.tree_condition",
    "category.cutting": "category.management",
    "category.pruning": "category.management",
    "category.stand_type": "category.management",
    "category.edge": "category.management",
    "category.mortality": "category.tree_condition",
    "category.tree_class": "category.tree_condition",
    "category.crown_class": "category.tree_condition",
    "category.tree_grade": "category.tree_condition",
    "category.decay_stage": "category.tree_condition",
    "category.phenology": "category.ecology",
    "category.topography": "category.soil",
    "category.humus": "category.soil",
    "category.soil_type": "category.soil",
    "category.soil_texture": "category.soil",
    "category.rock_type": "category.soil",
    "category.stone_size": "category.soil",
    "category.gley": "category.soil",
    "category.calcareous": "category.soil",
    "category.stratum": "category.vegetation",
    "category.forest_type": "category.vegetation",
    "category.sex": "category.ecology",
    # ── environment: merge all into environment ──
    "environment.salinity": "environment.water",
    "environment.ph": "environment.water",
    # ── identifier: merge rare subtypes ──
    "identifier.specimen": "identifier.record",
    "identifier.habitat": "identifier.record",
    # ── location: merge rare subtypes ──
    "location.x_coord": "location.coordinate",
    "location.y_coord": "location.coordinate",
    "location.geometry": "location.coordinate",
    "location.ecoregion": "location.admin_area",
    # ── measurement: merge rare subtypes ──
    "measurement.circumference": "measurement.diameter",
    "measurement.basal_area": "measurement.biomass",
    "measurement.crown": "measurement.canopy",
    "measurement.crown_ratio": "measurement.canopy",
    "measurement.length": "measurement.dimension",
    "measurement.area": "measurement.dimension",
    "measurement.distance": "measurement.dimension",
    "measurement.increment": "measurement.growth",
    "measurement.growth_rate": "measurement.growth",
    "measurement.age": "measurement.growth",
    "measurement.slope": "measurement.terrain",
    "measurement.aspect": "measurement.terrain",
    "measurement.rock_cover": "measurement.terrain",
    "measurement.depth": "measurement.terrain",
    "measurement.defect": "measurement.quality",
    "measurement.root_trait": "measurement.trait",
    "measurement.chlorophyll": "measurement.trait",
    "measurement.soil_organic": "measurement.soil",
    # ── statistic: merge ──
    "statistic.ratio": "statistic.count",
    "statistic.density": "statistic.count",
    # ── taxonomy: merge rare ──
    "taxonomy.group": "taxonomy.rank",
    "taxonomy.vernacular_name": "taxonomy.name",
    # ── text: merge rare ──
    "text.authority": "text.metadata",
    "text.notes": "text.metadata",
    "text.reference": "text.metadata",
    "text.license": "text.metadata",
}


def coarsen(concept: str) -> str:
    """Map a fine-grained concept to its coarser parent."""
    return CONCEPT_MERGE.get(concept, concept)


def coarsen_role(concept: str) -> str:
    """Extract the role from a (possibly coarsened) concept."""
    return concept.split(".")[0] if "." in concept else concept
