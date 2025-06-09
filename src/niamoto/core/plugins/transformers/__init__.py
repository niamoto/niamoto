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
    "DatabaseAggregator",
    # Extraction
    "DirectAttribute",
    "GeospatialExtractor",
    # Geospatial
    "ShapeProcessor",
    "RasterStats",
    "VectorOverlay",
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
