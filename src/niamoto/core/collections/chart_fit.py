"""Readability-aware chart-fit catalogue for widget proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from pydantic import BaseModel, Field

from niamoto.core.collections.widget_proposal_models import (
    ChartFitResult,
    MissingChartOpportunity,
    ProposalWarning,
    TransformedShape,
    TransformedShapeKind,
)

MAX_DONUT_CATEGORIES = 6
MAX_READABLE_BAR_CATEGORIES = 30
MAX_COMFORTABLE_LABEL_LENGTH = 24


@dataclass(frozen=True)
class ChartDescriptor:
    """Finite chart-fit rule for one widget."""

    widget: str
    readable_shapes: frozenset[TransformedShapeKind]
    default_score: float
    reason: str
    secondary_for: frozenset[TransformedShapeKind] = frozenset()


class ChartFitEvaluation(BaseModel):
    """All fit outcomes for one transformed shape."""

    shape: TransformedShape
    primary: ChartFitResult | None = None
    alternatives: list[ChartFitResult] = Field(default_factory=list)
    suppressed: list[ChartFitResult] = Field(default_factory=list)
    warnings: list[ProposalWarning] = Field(default_factory=list)
    missing_chart: MissingChartOpportunity | None = None


CHART_DESCRIPTORS: tuple[ChartDescriptor, ...] = (
    ChartDescriptor(
        widget="bar_plot",
        readable_shapes=frozenset(
            {
                "category_distribution",
                "category_ranking",
                "binned_numeric_distribution",
                "boolean_split",
            }
        ),
        secondary_for=frozenset({"boolean_split"}),
        default_score=0.88,
        reason="Readable for count, ranking, and distribution shapes.",
    ),
    ChartDescriptor(
        widget="donut_chart",
        readable_shapes=frozenset(
            {
                "category_distribution",
                "category_ranking",
                "boolean_split",
                "binned_numeric_distribution",
            }
        ),
        default_score=0.72,
        reason="Readable for binary or very small categorical splits.",
    ),
    ChartDescriptor(
        widget="radial_gauge",
        readable_shapes=frozenset({"scalar_metric"}),
        default_score=0.82,
        reason="Readable for a single scalar metric with clear bounds.",
    ),
    ChartDescriptor(
        widget="info_grid",
        readable_shapes=frozenset({"metric_group", "scalar_metric"}),
        secondary_for=frozenset({"scalar_metric"}),
        default_score=0.86,
        reason="Readable for grouped scalar facts and compact KPI sets.",
    ),
    ChartDescriptor(
        widget="interactive_map",
        readable_shapes=frozenset({"map_layer"}),
        default_score=0.9,
        reason="Readable for geographic feature collections.",
    ),
    ChartDescriptor(
        widget="line_plot",
        readable_shapes=frozenset({"time_series"}),
        default_score=0.86,
        reason="Readable for ordered temporal series.",
    ),
    ChartDescriptor(
        widget="stacked_area_plot",
        readable_shapes=frozenset({"time_series"}),
        secondary_for=frozenset({"time_series"}),
        default_score=0.72,
        reason="Readable for multi-series temporal composition.",
    ),
    ChartDescriptor(
        widget="scatter_plot",
        readable_shapes=frozenset({"numeric_pair"}),
        default_score=0.88,
        reason="Readable for paired numeric observations.",
    ),
    ChartDescriptor(
        widget="diverging_bar_plot",
        readable_shapes=frozenset({"category_ranking"}),
        secondary_for=frozenset({"category_ranking"}),
        default_score=0.7,
        reason="Readable when ranked categories compare two directions.",
    ),
    ChartDescriptor(
        widget="sunburst_chart",
        readable_shapes=frozenset({"category_distribution"}),
        secondary_for=frozenset({"category_distribution"}),
        default_score=0.62,
        reason="Readable only when categories represent a hierarchy.",
    ),
    ChartDescriptor(
        widget="table_view",
        readable_shapes=frozenset({"table"}),
        default_score=0.82,
        reason="Readable for tabular records.",
    ),
    ChartDescriptor(
        widget="raw_data_widget",
        readable_shapes=frozenset({"table"}),
        secondary_for=frozenset({"table"}),
        default_score=0.62,
        reason="Useful as an inspectable raw-data fallback.",
    ),
)


def get_chart_descriptors() -> tuple[ChartDescriptor, ...]:
    """Return the finite chart descriptor catalogue."""

    return CHART_DESCRIPTORS


def find_chart_descriptor(widget: str) -> ChartDescriptor | None:
    """Find a descriptor by widget plugin name."""

    return next(
        (descriptor for descriptor in CHART_DESCRIPTORS if descriptor.widget == widget),
        None,
    )


def evaluate_chart_fit(
    shape: TransformedShape,
    descriptors: Sequence[ChartDescriptor] = CHART_DESCRIPTORS,
) -> ChartFitEvaluation:
    """Evaluate readable widget fits for a transformed shape."""

    warnings = _shape_warnings(shape)

    if shape.kind == "unsupported":
        reason = (
            shape.unsupported_reason or "No readable widget is known for this shape"
        )
        return ChartFitEvaluation(
            shape=shape,
            warnings=warnings,
            missing_chart=MissingChartOpportunity(shape=shape, reason=reason),
        )

    fits: list[ChartFitResult] = []
    suppressed: list[ChartFitResult] = []

    for descriptor in descriptors:
        if shape.kind not in descriptor.readable_shapes:
            continue

        suppression_reason = _suppression_reason(shape, descriptor.widget)
        if suppression_reason is not None:
            suppressed.append(
                ChartFitResult(
                    widget=descriptor.widget,
                    status="suppressed",
                    score=0.0,
                    reason=suppression_reason,
                )
            )
            continue

        score = _score_for_shape(shape, descriptor)
        status = "secondary" if shape.kind in descriptor.secondary_for else "primary"
        if warnings and status == "primary":
            status = "warning"

        fits.append(
            ChartFitResult(
                widget=descriptor.widget,
                status=status,
                score=score,
                reason=descriptor.reason,
                warnings=warnings if status == "warning" else [],
                params=_params_for_fit(shape, descriptor.widget),
            )
        )

    fits.sort(key=lambda fit: (-fit.score, fit.widget))
    suppressed.sort(key=lambda fit: fit.widget)

    if not fits:
        return ChartFitEvaluation(
            shape=shape,
            suppressed=suppressed,
            warnings=warnings,
            missing_chart=MissingChartOpportunity(
                shape=shape,
                reason=f"No readable widget is known for {shape.kind}",
            ),
        )

    primary = fits[0].model_copy(update={"rank": 1})
    alternatives = [
        fit.model_copy(update={"rank": index})
        for index, fit in enumerate(fits[1:], start=2)
    ]

    return ChartFitEvaluation(
        shape=shape,
        primary=primary,
        alternatives=alternatives,
        suppressed=suppressed,
        warnings=warnings,
    )


def _shape_warnings(shape: TransformedShape) -> list[ProposalWarning]:
    warnings: list[ProposalWarning] = []

    if shape.kind in {"category_distribution", "category_ranking", "boolean_split"}:
        if not shape.has_labels:
            warnings.append(
                ProposalWarning(
                    code="missing_labels",
                    message="Source evidence does not provide display labels.",
                )
            )
        if (
            shape.label_max_length is not None
            and shape.label_max_length > MAX_COMFORTABLE_LABEL_LENGTH
        ):
            warnings.append(
                ProposalWarning(
                    code="long_labels",
                    message="Some labels may be too long for compact charts.",
                    details={"label_max_length": shape.label_max_length},
                )
            )

    if (
        shape.kind in {"category_distribution", "category_ranking"}
        and shape.category_count is not None
        and shape.category_count > MAX_READABLE_BAR_CATEGORIES
    ):
        warnings.append(
            ProposalWarning(
                code="high_cardinality",
                message="Many categories require ranking, grouping, or scrolling.",
                details={"category_count": shape.category_count},
            )
        )

    return warnings


def _suppression_reason(shape: TransformedShape, widget: str) -> str | None:
    if widget == "donut_chart":
        if shape.kind == "binned_numeric_distribution":
            return "Ordered numeric bins are not readable as donut slices."
        if (
            shape.kind == "category_distribution"
            and shape.category_count is not None
            and shape.category_count > MAX_DONUT_CATEGORIES
        ):
            return "Too many categories for a readable donut chart."
        if shape.kind == "category_ranking":
            return "Ranked categories are more readable as bars than donut slices."

    if widget == "sunburst_chart" and not shape.metadata.get("hierarchical"):
        return "Sunburst requires explicit hierarchical category evidence."

    if widget == "stacked_area_plot" and (shape.series_count or 0) <= 1:
        return "Stacked area requires multiple comparable time series."

    return None


def _score_for_shape(shape: TransformedShape, descriptor: ChartDescriptor) -> float:
    score = descriptor.default_score

    if descriptor.widget == "bar_plot":
        if shape.kind == "category_ranking":
            score = 0.92
        elif shape.kind == "binned_numeric_distribution":
            score = 0.9
        elif shape.kind == "boolean_split":
            score = 0.68
        elif (
            shape.kind == "category_distribution"
            and shape.category_count is not None
            and shape.category_count > MAX_READABLE_BAR_CATEGORIES
        ):
            score = 0.68

    if descriptor.widget == "donut_chart" and shape.kind == "boolean_split":
        score = 0.84

    if descriptor.widget == "info_grid" and shape.kind == "metric_group":
        metric_count = shape.metric_count or 0
        score = 0.9 if 1 <= metric_count <= 12 else 0.74

    if (
        shape.label_max_length is not None
        and shape.label_max_length > MAX_COMFORTABLE_LABEL_LENGTH
    ):
        score -= 0.08

    if not shape.has_labels and shape.kind.startswith("category"):
        score -= 0.08

    return max(0.0, min(score, 1.0))


def _params_for_fit(shape: TransformedShape, widget: str) -> dict:
    """Return safe default widget params for the transformed shape contract."""

    if widget == "bar_plot":
        if shape.kind == "binned_numeric_distribution":
            return {
                "transform": "bins_to_df",
                "transform_params": {
                    "bin_field": "bins",
                    "count_field": "counts",
                    "x_field": "bin",
                    "y_field": "count",
                },
                "x_axis": "bin",
                "y_axis": "count",
                "orientation": "v",
            }
        if shape.kind == "category_distribution":
            return {
                "transform": "category_with_labels",
                "transform_params": {
                    "category_field": "categories",
                    "count_field": "counts",
                    "label_field": "labels",
                    "x_field": "category_label",
                    "y_field": "value",
                },
                "x_axis": "category_label",
                "y_axis": "value",
                "orientation": "v",
            }
        if shape.kind == "category_ranking":
            return {
                "x_axis": "counts",
                "y_axis": "tops",
                "orientation": "h",
            }

    if widget == "donut_chart":
        if shape.kind in {"category_distribution", "category_ranking"}:
            labels_field = "labels" if shape.kind == "category_distribution" else "tops"
            values_field = "counts"
            return {
                "labels_field": labels_field,
                "values_field": values_field,
                "show_legend": bool(shape.category_count and shape.category_count > 3),
            }
        if shape.kind == "boolean_split":
            return {
                "label_mapping": {
                    "true": "True",
                    "false": "False",
                    "oui": "Oui",
                    "non": "Non",
                }
            }

    if widget == "info_grid":
        if shape.kind == "scalar_metric":
            field = shape.value_field or (
                shape.columns[0] if shape.columns else "value"
            )
            return {
                "items": [
                    {
                        "label": _humanize_label(field),
                        "source": f"{field}.value",
                        "format": "number",
                    }
                ],
                "grid_columns": 1,
            }
        if shape.kind == "metric_group":
            columns = shape.columns[:12]
            return {
                "items": [
                    {
                        "label": _humanize_label(column),
                        "source": f"{column}.value",
                        "format": "number",
                    }
                    for column in columns
                ],
                "grid_columns": min(max(len(columns), 1), 3),
            }

    if widget == "line_plot" and shape.kind == "time_series":
        x_axis = shape.label_field or (shape.columns[0] if shape.columns else "x")
        y_columns = [column for column in shape.columns if column != x_axis]
        return {"x_axis": x_axis, "y_axis": y_columns or "value"}

    if widget == "scatter_plot" and shape.kind == "numeric_pair":
        return {"x_axis": shape.columns[0], "y_axis": shape.columns[1]}

    if widget == "interactive_map" and shape.kind == "map_layer":
        return {
            "geojson_field": "features",
            "map_type": "scatter_map",
            "map_style": "carto-positron",
            "auto_zoom": True,
        }

    return {}


def _humanize_label(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()
