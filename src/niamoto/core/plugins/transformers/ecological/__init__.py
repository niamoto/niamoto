"""
Ecological transformer plugins.

This package contains transformer plugins related to ecological analysis.
"""

# Define the modules that should be considered part of the public API
__all__ = [
    "custom_calculator",
    "custom_formatter",
    "elevation_profile",
    "forest_elevation",
    "forest_holdridge",
    "fragmentation",
    "land_use",
    "biodiversity_index",
]

# Import all modules to ensure plugins are registered
from . import (
    custom_calculator,
    custom_formatter,
    elevation_profile,
    forest_elevation,
    forest_holdridge,
    fragmentation,
    land_use,
    biodiversity_index,
)
