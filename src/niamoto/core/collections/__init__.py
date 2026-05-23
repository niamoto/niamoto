"""Collection catalog services and widget proposal models."""

from niamoto.core.collections.catalog import CollectionCatalogService
from niamoto.core.collections.chart_fit import evaluate_chart_fit, get_chart_descriptors
from niamoto.core.collections.models import (
    CollectionCatalog,
    CollectionCatalogEntry,
    CollectionEvidence,
    CollectionSourceOption,
)
from niamoto.core.collections.widget_proposal_models import (
    ChartFitResult,
    MissingChartOpportunity,
    ProposalScore,
    ProposalSkipReason,
    ProposalWarning,
    TransformedShape,
    TransformationCandidate,
    WidgetProposal,
    WidgetProposalGroups,
)
from niamoto.core.collections.widget_proposal_service import WidgetProposalService
from niamoto.core.collections.widget_recipe_compatibility import (
    IncomingColumnProfile,
    IncomingDataProfile,
    WidgetCompatibilityReport,
    WidgetRecipeCompatibilityService,
    WidgetRecipeImpact,
)

__all__ = [
    "ChartFitResult",
    "CollectionCatalog",
    "CollectionCatalogEntry",
    "CollectionCatalogService",
    "CollectionEvidence",
    "CollectionSourceOption",
    "MissingChartOpportunity",
    "ProposalScore",
    "ProposalSkipReason",
    "ProposalWarning",
    "TransformedShape",
    "TransformationCandidate",
    "WidgetProposal",
    "WidgetProposalGroups",
    "WidgetProposalService",
    "IncomingColumnProfile",
    "IncomingDataProfile",
    "WidgetCompatibilityReport",
    "WidgetRecipeCompatibilityService",
    "WidgetRecipeImpact",
    "evaluate_chart_fit",
    "get_chart_descriptors",
]
