"""
Transformer plugins for Niamoto.
"""

from .aggregation.binary_counter import BinaryCounter
from .aggregation.database_aggregator import DatabaseAggregatorPlugin
from .aggregation.field_aggregator import FieldAggregator
from .aggregation.statistical_summary import StatisticalSummary
from .aggregation.top_ranking import TopRanking
from .analysis.boolean_comparison import BooleanComparison
from .analysis.scatter_analysis import ScatterAnalysis
from .chains.transform_chain import TransformChain
from .class_objects.binary_aggregator import ClassObjectBinaryAggregator
from .class_objects.categories_extractor import ClassObjectCategoriesExtractor
from .class_objects.categories_mapper import ClassObjectCategoriesMapper
from .class_objects.field_aggregator import ClassObjectFieldAggregator
from .class_objects.series_by_axis_extractor import ClassObjectSeriesByAxisExtractor
from .class_objects.series_extractor import ClassObjectSeriesExtractor
from .class_objects.series_matrix_extractor import ClassObjectSeriesMatrixExtractor
from .class_objects.series_ratio_aggregator import ClassObjectSeriesRatioAggregator
from .distribution.binned_distribution import BinnedDistribution
from .distribution.categorical_distribution import CategoricalDistribution
from .distribution.time_series_analysis import TimeSeriesAnalysis
from .extraction.direct_attribute import DirectAttribute
from .extraction.geospatial_extractor import GeospatialExtractor
from .formats.niamoto_to_dwc_occurrence import NiamotoDwCTransformer
from .geospatial.raster_stats import RasterStats
from .geospatial.shape_processor import ShapeProcessor
from .geospatial.vector_overlay import VectorOverlay

DatabaseAggregator = DatabaseAggregatorPlugin
BinaryAggregator = ClassObjectBinaryAggregator
CategoriesExtractor = ClassObjectCategoriesExtractor
CategoriesMapper = ClassObjectCategoriesMapper
SeriesByAxisExtractor = ClassObjectSeriesByAxisExtractor
SeriesExtractor = ClassObjectSeriesExtractor
SeriesMatrixExtractor = ClassObjectSeriesMatrixExtractor
SeriesRatioAggregator = ClassObjectSeriesRatioAggregator
NiamotoToDwcOccurrenceTransformer = NiamotoDwCTransformer

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
    # Analysis
    "ScatterAnalysis",
    "BooleanComparison",
    # Format conversion transformers
    "NiamotoToDwcOccurrenceTransformer",
]
