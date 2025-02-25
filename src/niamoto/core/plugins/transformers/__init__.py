"""
Transformer plugins for Niamoto.
"""

# List of all available transformers
__all__ = [
    # Base
    "TransformChain",
    # Aggregation
    "FieldAggregator",
    "TopRanking",
    # Extraction
    "DirectAttribute",
    # Geospatial
    "GeospatialExtractor",
    "ShapeProcessor",
    # Statistical
    "BinnedDistribution",
    "CategoricalDistribution",
    "BinaryCounter",
    "StatisticalSummary",
    "TimeSeriesAnalysis",
    # Class Objects
    "BinaryAggregator",
    "CategoriesExtractor",
    "CategoriesMapper",
    "ClassObjectFieldAggregator",
    "SeriesByAxisExtractor",
    "SeriesExtractor",
    "SeriesMatrixExtractor",
    "SeriesRatioAggregator",
]
