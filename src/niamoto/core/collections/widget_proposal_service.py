"""Transformation-first widget proposal service."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Sequence

from niamoto.core.collections.chart_fit import ChartFitEvaluation, evaluate_chart_fit
from niamoto.core.collections.widget_proposal_models import (
    ChartFitResult,
    ProposalProvenance,
    ProposalScore,
    ProposalSkipReason,
    ProposalWarning,
    TransformedShape,
    TransformationCandidate,
    WidgetProposal,
    WidgetProposalGroups,
)
from niamoto.core.imports.class_object_analyzer import (
    ClassObjectCategory,
    ClassObjectStats,
)
from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)
from niamoto.core.imports.multi_field_detector import (
    MultiFieldPattern,
    MultiFieldPatternType,
)

SCORE_WEIGHTS = {
    "utility": 1.3,
    "evidence": 1.2,
    "coverage": 1.0,
    "cardinality": 1.0,
    "chart_fit": 1.4,
    "provenance": 0.8,
    "reconstructability": 1.0,
}


class WidgetProposalService:
    """Collect and rank collection-scoped widget proposals."""

    def __init__(
        self,
        *,
        max_combined_candidates: int = 5,
        max_scalar_metrics: int = 12,
    ) -> None:
        self.max_combined_candidates = max_combined_candidates
        self.max_scalar_metrics = max_scalar_metrics

    def generate_for_collection(
        self,
        *,
        collection: str,
        source_name: str,
        profiles: Sequence[EnrichedColumnProfile] = (),
        class_objects: Sequence[ClassObjectStats] = (),
        multi_field_patterns: Sequence[MultiFieldPattern] = (),
        existing_proposal_keys: Iterable[str] = (),
    ) -> WidgetProposalGroups:
        """Generate grouped proposals for one collection."""

        existing_keys = set(existing_proposal_keys)
        proposals: list[WidgetProposal] = []

        for profile in profiles:
            proposals.append(
                self._proposal_from_profile(
                    collection=collection,
                    source_name=source_name,
                    profile=profile,
                    existing_keys=existing_keys,
                )
            )

        proposals.extend(
            self._proposals_from_class_objects(
                collection=collection,
                source_name=source_name,
                class_objects=class_objects,
                existing_keys=existing_keys,
            )
        )
        proposals.extend(
            self._proposals_from_multi_field_patterns(
                collection=collection,
                source_name=source_name,
                patterns=multi_field_patterns,
                existing_keys=existing_keys,
            )
        )

        deduped = self._deduplicate(proposals)
        return self._group(collection, deduped)

    def _proposal_from_profile(
        self,
        *,
        collection: str,
        source_name: str,
        profile: EnrichedColumnProfile,
        existing_keys: set[str],
    ) -> WidgetProposal:
        transformer, intent, shape, skip_reason = self._shape_from_profile(profile)
        provenance = ProposalProvenance(
            source="raw_field",
            source_name=source_name,
            field_names=[profile.name],
            evidence=[
                f"data_category={profile.data_category.value}",
                f"cardinality={profile.cardinality}",
            ],
        )
        candidate = TransformationCandidate(
            id=self._candidate_id(
                collection,
                "raw_field",
                source_name,
                [profile.name],
                transformer or "unsupported",
                intent,
            ),
            collection=collection,
            origin="raw_field",
            source_name=source_name,
            field_names=[profile.name],
            transformer_plugin=transformer,
            transformer_config=self._transformer_config_for_profile(
                source_name, profile, transformer
            ),
            intent=intent,
            shape=shape,
            provenance=provenance,
            freshness="current",
            reconstructability="full" if transformer else "evidence_only",
            skip_reasons=[skip_reason] if skip_reason else [],
        )

        return self._proposal_from_candidate(
            candidate,
            existing_keys=existing_keys,
            score_dimensions=self._score_dimensions_for_profile(profile),
        )

    def _shape_from_profile(
        self, profile: EnrichedColumnProfile
    ) -> tuple[str | None, str, TransformedShape, ProposalSkipReason | None]:
        category = profile.data_category

        if profile.field_purpose in {
            FieldPurpose.PRIMARY_KEY,
            FieldPurpose.FOREIGN_KEY,
        }:
            reason = ProposalSkipReason(
                code="low_utility_identifier",
                message=f"{profile.name} is an identifier field, not a useful standalone widget source.",
                details={"field_purpose": profile.field_purpose.value},
            )
            return (
                None,
                f"Skip identifier field {profile.name}",
                TransformedShape(
                    kind="unsupported",
                    columns=[profile.name],
                    unsupported_reason=reason.message,
                ),
                reason,
            )

        if category in {
            DataCategory.NUMERIC_CONTINUOUS,
            DataCategory.NUMERIC_DISCRETE,
        }:
            bins = _bins_for_profile(profile)
            if len(bins) < 2:
                reason = ProposalSkipReason(
                    code="numeric_bins_unavailable",
                    message=f"{profile.name} needs at least two numeric bin edges before a histogram can be generated.",
                    details={"value_range": profile.value_range},
                )
                return (
                    None,
                    f"Skip numeric field without bins {profile.name}",
                    TransformedShape(
                        kind="unsupported",
                        columns=[profile.name],
                        unsupported_reason=reason.message,
                    ),
                    reason,
                )

            return (
                "binned_distribution",
                f"Bin numeric values from {profile.name}",
                TransformedShape(
                    kind="binned_numeric_distribution",
                    bin_count=len(bins) - 1,
                    columns=[profile.name],
                    value_field=profile.name,
                ),
                None,
            )

        if category == DataCategory.CATEGORICAL:
            return (
                "categorical_distribution",
                f"Count records by {profile.name}",
                TransformedShape(
                    kind="category_distribution",
                    category_count=profile.cardinality,
                    label_max_length=_max_label_length(profile.suggested_labels),
                    has_labels=bool(profile.suggested_labels),
                    columns=[profile.name],
                    label_field=profile.name,
                ),
                None,
            )

        if category == DataCategory.CATEGORICAL_HIGH_CARD:
            return (
                "top_ranking",
                f"Rank most common values for {profile.name}",
                TransformedShape(
                    kind="category_ranking",
                    category_count=profile.cardinality,
                    label_max_length=_max_label_length(profile.suggested_labels),
                    has_labels=bool(profile.suggested_labels),
                    columns=[profile.name],
                    label_field=profile.name,
                ),
                None,
            )

        if category == DataCategory.BOOLEAN:
            return (
                "binary_counter",
                f"Count true and false values for {profile.name}",
                TransformedShape(
                    kind="boolean_split",
                    category_count=2,
                    columns=[profile.name],
                    label_field=profile.name,
                ),
                None,
            )

        if category == DataCategory.GEOGRAPHIC:
            return (
                "geospatial_extractor",
                f"Build map features from {profile.name}",
                TransformedShape(kind="map_layer", columns=[profile.name]),
                None,
            )

        reason = ProposalSkipReason(
            code="unsupported_raw_field",
            message=f"{profile.name} is not a useful standalone widget source.",
            details={"data_category": category.value},
        )
        return (
            None,
            f"Skip unsupported field {profile.name}",
            TransformedShape(
                kind="unsupported",
                columns=[profile.name],
                unsupported_reason=reason.message,
            ),
            reason,
        )

    def _transformer_config_for_profile(
        self,
        source_name: str,
        profile: EnrichedColumnProfile,
        transformer: str | None,
    ) -> dict[str, Any]:
        if transformer is None:
            return {}

        base = {"source": source_name, "field": profile.name}
        if transformer == "binned_distribution":
            base["bins"] = _bins_for_profile(profile)
        if transformer == "binary_counter":
            base["include_percentages"] = True
        if transformer == "top_ranking":
            base["count"] = 10
        return base

    def _score_dimensions_for_profile(
        self, profile: EnrichedColumnProfile
    ) -> dict[str, float]:
        coverage = 1.0 - min(max(profile.null_ratio, 0.0), 1.0)
        return {
            "utility": _purpose_utility(profile.field_purpose),
            "evidence": profile.confidence,
            "coverage": coverage,
            "cardinality": _cardinality_score(profile),
            "provenance": 0.72,
            "reconstructability": 1.0,
        }

    def _proposals_from_class_objects(
        self,
        *,
        collection: str,
        source_name: str,
        class_objects: Sequence[ClassObjectStats],
        existing_keys: set[str],
    ) -> list[WidgetProposal]:
        scalar_objects = [
            item
            for item in class_objects
            if item.category == ClassObjectCategory.SCALAR or item.cardinality == 0
        ]
        proposals: list[WidgetProposal] = []

        if len(scalar_objects) > 1:
            selected = scalar_objects[: self.max_scalar_metrics]
            warnings = []
            if len(scalar_objects) > self.max_scalar_metrics:
                warnings.append(
                    ProposalWarning(
                        code="scalar_metric_limit",
                        message="Only the strongest scalar metrics are proposed by default.",
                        details={
                            "available": len(scalar_objects),
                            "selected": len(selected),
                        },
                    )
                )
            shape = TransformedShape(
                kind="metric_group",
                metric_count=len(selected),
                columns=[item.name for item in selected],
            )
            candidate = TransformationCandidate(
                id=self._candidate_id(
                    collection,
                    "class_object",
                    source_name,
                    [item.name for item in selected],
                    "class_object_field_aggregator",
                    "Group scalar class_object metrics",
                ),
                collection=collection,
                origin="class_object",
                source_name=source_name,
                field_names=[item.name for item in selected],
                transformer_plugin="class_object_field_aggregator",
                transformer_config={
                    "source": source_name,
                    "fields": [
                        {"class_object": item.name, "target": item.name}
                        for item in selected
                    ],
                },
                intent="Group scalar class_object metrics",
                shape=shape,
                freshness="current",
                reconstructability="full",
                warnings=warnings,
                metadata={
                    "widget_params": _info_grid_params_for_class_objects(selected)
                },
                provenance=ProposalProvenance(
                    source="class_object",
                    source_name=source_name,
                    field_names=[item.name for item in selected],
                    evidence=["class_object scalar metrics"],
                ),
            )
            proposals.append(
                self._proposal_from_candidate(
                    candidate,
                    existing_keys=existing_keys,
                    score_dimensions={
                        "utility": 0.82,
                        "evidence": _average_confidence(selected),
                        "coverage": 1.0,
                        "cardinality": 0.95,
                        "provenance": 0.9,
                        "reconstructability": 1.0,
                    },
                )
            )

        scalar_names = (
            {item.name for item in scalar_objects} if len(scalar_objects) > 1 else set()
        )
        for item in class_objects:
            if item.name in scalar_names:
                continue
            proposals.append(
                self._proposal_from_class_object(
                    collection=collection,
                    source_name=source_name,
                    class_object=item,
                    existing_keys=existing_keys,
                )
            )

        return proposals

    def _proposal_from_class_object(
        self,
        *,
        collection: str,
        source_name: str,
        class_object: ClassObjectStats,
        existing_keys: set[str],
    ) -> WidgetProposal:
        transformer = class_object.suggested_plugin or "class_object_series_extractor"
        shape = _shape_from_class_object(class_object)
        transformer_config = _class_object_transformer_config(
            source_name,
            class_object,
            transformer,
        )
        widget_params = _class_object_widget_params(class_object, shape)
        candidate = TransformationCandidate(
            id=self._candidate_id(
                collection,
                "class_object",
                source_name,
                [class_object.name],
                transformer,
                f"Use class_object {class_object.name}",
            ),
            collection=collection,
            origin="class_object",
            source_name=source_name,
            field_names=[class_object.name],
            transformer_plugin=transformer,
            transformer_config=transformer_config,
            intent=f"Use class_object {class_object.name}",
            shape=shape,
            freshness="current",
            reconstructability="full",
            metadata={"widget_params": widget_params} if widget_params else {},
            provenance=ProposalProvenance(
                source="class_object",
                source_name=source_name,
                field_names=[class_object.name],
                evidence=[
                    f"category={class_object.category.value}",
                    f"cardinality={class_object.cardinality}",
                ],
            ),
        )
        return self._proposal_from_candidate(
            candidate,
            existing_keys=existing_keys,
            score_dimensions={
                "utility": 0.78,
                "evidence": class_object.confidence,
                "coverage": 1.0,
                "cardinality": _class_object_cardinality_score(class_object),
                "provenance": 0.9,
                "reconstructability": 1.0,
            },
        )

    def _proposals_from_multi_field_patterns(
        self,
        *,
        collection: str,
        source_name: str,
        patterns: Sequence[MultiFieldPattern],
        existing_keys: set[str],
    ) -> list[WidgetProposal]:
        proposals: list[WidgetProposal] = []
        for index, pattern in enumerate(patterns):
            if index >= self.max_combined_candidates:
                proposals.append(
                    self._skipped_combined_pattern(collection, source_name, pattern)
                )
                continue

            shape = _shape_from_multi_field_pattern(pattern)
            candidate = TransformationCandidate(
                id=self._candidate_id(
                    collection,
                    "combined_fields",
                    source_name,
                    pattern.fields,
                    pattern.transformer_plugin,
                    pattern.pattern_type.value,
                ),
                collection=collection,
                origin="combined_fields",
                source_name=source_name,
                field_names=list(pattern.fields),
                transformer_plugin=pattern.transformer_plugin,
                transformer_config=pattern.transformer_params,
                intent=pattern.description,
                shape=shape,
                freshness="current",
                reconstructability="partial",
                metadata={
                    "widget_plugin": pattern.widget_plugin,
                    "widget_params": pattern.widget_params,
                },
                provenance=ProposalProvenance(
                    source="combined_fields",
                    source_name=source_name,
                    field_names=list(pattern.fields),
                    evidence=[pattern.pattern_type.value],
                    details={"field_roles": pattern.field_roles},
                ),
            )
            proposals.append(
                self._proposal_from_candidate(
                    candidate,
                    existing_keys=existing_keys,
                    score_dimensions={
                        "utility": 0.72,
                        "evidence": pattern.confidence,
                        "coverage": 0.8,
                        "cardinality": 0.75,
                        "provenance": 0.66,
                        "reconstructability": 0.55,
                    },
                    force_review_only=True,
                )
            )
        return proposals

    def _skipped_combined_pattern(
        self,
        collection: str,
        source_name: str,
        pattern: MultiFieldPattern,
    ) -> WidgetProposal:
        reason = ProposalSkipReason(
            code="combined_candidate_limit",
            message="Combined candidate skipped because the collection limit was reached.",
            details={"limit": self.max_combined_candidates},
        )
        candidate = TransformationCandidate(
            id=self._candidate_id(
                collection,
                "combined_fields",
                source_name,
                pattern.fields,
                pattern.transformer_plugin,
                f"skipped:{pattern.pattern_type.value}",
            ),
            collection=collection,
            origin="combined_fields",
            source_name=source_name,
            field_names=list(pattern.fields),
            transformer_plugin=pattern.transformer_plugin,
            intent=pattern.description,
            shape=TransformedShape(
                kind="unsupported",
                columns=list(pattern.fields),
                unsupported_reason=reason.message,
            ),
            reconstructability="evidence_only",
            skip_reasons=[reason],
        )
        return self._proposal_from_candidate(
            candidate,
            existing_keys=set(),
            score_dimensions={"utility": 0.4, "evidence": pattern.confidence},
        )

    def _proposal_from_candidate(
        self,
        candidate: TransformationCandidate,
        *,
        existing_keys: set[str],
        score_dimensions: dict[str, float],
        force_review_only: bool = False,
    ) -> WidgetProposal:
        chart_fit = evaluate_chart_fit(candidate.shape)
        score = ProposalScore(
            dimensions={
                **score_dimensions,
                "chart_fit": chart_fit.primary.score if chart_fit.primary else 0.0,
            },
            weights=SCORE_WEIGHTS,
        )
        fingerprint = self._fingerprint(candidate, chart_fit.primary)
        status = self._status_for(candidate, chart_fit, fingerprint, existing_keys)
        applyability = self._applyability_for(status, candidate, force_review_only)
        title = self._title_for(candidate, chart_fit.primary)

        return WidgetProposal(
            id=fingerprint,
            collection=candidate.collection,
            title=title,
            status=status,
            candidate=candidate,
            shape=candidate.shape,
            primary_fit=chart_fit.primary,
            alternatives=chart_fit.alternatives,
            suppressed_fits=chart_fit.suppressed,
            missing_chart=chart_fit.missing_chart,
            score=score,
            warnings=[*candidate.warnings, *chart_fit.warnings],
            skip_reasons=list(candidate.skip_reasons),
            applyability=applyability,
            fingerprint=fingerprint,
            recipe=self._recipe_for(candidate, chart_fit.primary),
        )

    def _status_for(
        self,
        candidate: TransformationCandidate,
        chart_fit: ChartFitEvaluation,
        fingerprint: str,
        existing_keys: set[str],
    ) -> str:
        if fingerprint in existing_keys:
            return "already_configured"
        if candidate.skip_reasons:
            return "skipped"
        if chart_fit.missing_chart is not None:
            return "missing_chart"
        if candidate.reconstructability in {"partial", "evidence_only", "unknown"}:
            return "review_only"
        if candidate.warnings or chart_fit.warnings:
            return "warning"
        return "recommended"

    def _applyability_for(
        self,
        status: str,
        candidate: TransformationCandidate,
        force_review_only: bool,
    ) -> str:
        if status in {"missing_chart", "skipped"}:
            return "not_applicable"
        if force_review_only or candidate.reconstructability != "full":
            return "review_only"
        if status == "already_configured":
            return "not_applicable"
        return "applicable"

    def _recipe_for(
        self,
        candidate: TransformationCandidate,
        primary_fit: ChartFitResult | None,
    ) -> dict[str, Any]:
        if primary_fit is None or not candidate.transformer_plugin:
            return {}
        widget_plugin = str(
            candidate.metadata.get("widget_plugin") or primary_fit.widget
        )
        widget_params = candidate.metadata.get("widget_params")
        if not isinstance(widget_params, dict):
            widget_params = primary_fit.params
        return {
            "transformer": {
                "plugin": candidate.transformer_plugin,
                "params": candidate.transformer_config,
            },
            "widget": {
                "plugin": widget_plugin,
                "params": widget_params,
            },
        }

    def _deduplicate(self, proposals: Sequence[WidgetProposal]) -> list[WidgetProposal]:
        by_fingerprint: dict[str, WidgetProposal] = {}
        for proposal in proposals:
            fingerprint = proposal.fingerprint or proposal.id
            current = by_fingerprint.get(fingerprint)
            if current is None:
                by_fingerprint[fingerprint] = proposal
                continue
            if proposal.score.weighted_total() > current.score.weighted_total():
                alternatives = [*proposal.alternatives, *current.alternatives]
                by_fingerprint[fingerprint] = proposal.model_copy(
                    update={"alternatives": alternatives}
                )
            else:
                current.alternatives.extend(proposal.alternatives)

        return sorted(
            by_fingerprint.values(),
            key=lambda item: (-item.score.weighted_total(), item.title, item.id),
        )

    def _group(
        self,
        collection: str,
        proposals: Sequence[WidgetProposal],
    ) -> WidgetProposalGroups:
        groups = WidgetProposalGroups(collection=collection)
        for proposal in proposals:
            if proposal.status == "recommended":
                groups.recommended.append(proposal)
            elif proposal.status == "warning":
                groups.warnings.append(proposal)
            elif proposal.status == "missing_chart":
                groups.missing_chart.append(proposal)
            elif proposal.status == "skipped":
                groups.skipped.append(proposal)
            elif proposal.status == "already_configured":
                groups.already_configured.append(proposal)
            else:
                groups.review_only.append(proposal)
        groups.partial = bool(groups.skipped or groups.missing_chart)
        return groups

    def _candidate_id(
        self,
        collection: str,
        origin: str,
        source_name: str,
        fields: Sequence[str],
        transformer: str,
        intent: str,
    ) -> str:
        return ":".join(
            [
                collection,
                origin,
                source_name,
                ",".join(sorted(fields)),
                transformer,
                _slug(intent),
            ]
        )

    def _fingerprint(
        self,
        candidate: TransformationCandidate,
        primary_fit: ChartFitResult | None,
    ) -> str:
        parts = [
            candidate.collection,
            candidate.origin,
            candidate.source_name or "",
            ",".join(sorted(candidate.field_names)),
            candidate.transformer_plugin or "",
            primary_fit.widget if primary_fit else "",
            candidate.intent,
            candidate.shape.kind,
        ]
        digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
        return f"wp_{digest}"

    def _title_for(
        self,
        candidate: TransformationCandidate,
        primary_fit: ChartFitResult | None,
    ) -> str:
        if candidate.shape.kind == "metric_group":
            return "Class object metrics"
        if candidate.field_names:
            return _humanize(candidate.field_names[0])
        if primary_fit is not None:
            return _humanize(primary_fit.widget)
        return "Widget proposal"


def _shape_from_class_object(class_object: ClassObjectStats) -> TransformedShape:
    if (
        class_object.category == ClassObjectCategory.SCALAR
        or class_object.cardinality == 0
    ):
        return TransformedShape(
            kind="scalar_metric",
            columns=[class_object.name],
            value_field=class_object.name,
        )

    if (
        class_object.value_type == "numeric"
        or class_object.category == ClassObjectCategory.NUMERIC_BINS
    ):
        return TransformedShape(
            kind="binned_numeric_distribution",
            bin_count=max(class_object.cardinality, 1),
            columns=[class_object.name],
            has_labels=bool(class_object.class_names),
            label_max_length=_max_label_length(class_object.class_names),
        )

    if (
        class_object.cardinality == 2
        or class_object.category == ClassObjectCategory.BINARY
    ):
        return TransformedShape(
            kind="boolean_split",
            category_count=2,
            columns=[class_object.name],
            has_labels=bool(class_object.class_names),
            label_max_length=_max_label_length(class_object.class_names),
        )

    if (
        class_object.cardinality > 15
        or class_object.category == ClassObjectCategory.LARGE_CATEGORY
    ):
        return TransformedShape(
            kind="category_ranking",
            category_count=class_object.cardinality,
            columns=[class_object.name],
            has_labels=bool(class_object.class_names),
            label_max_length=_max_label_length(class_object.class_names),
        )

    return TransformedShape(
        kind="category_distribution",
        category_count=class_object.cardinality,
        columns=[class_object.name],
        has_labels=bool(class_object.class_names),
        label_max_length=_max_label_length(class_object.class_names),
    )


def _shape_from_multi_field_pattern(pattern: MultiFieldPattern) -> TransformedShape:
    if pattern.pattern_type in {
        MultiFieldPatternType.ALLOMETRY,
        MultiFieldPatternType.NUMERIC_CORRELATION,
    }:
        return TransformedShape(kind="numeric_pair", columns=list(pattern.fields[:2]))
    if pattern.pattern_type in {
        MultiFieldPatternType.PHENOLOGY,
        MultiFieldPatternType.TEMPORAL_SERIES,
    }:
        return TransformedShape(
            kind="time_series",
            columns=list(pattern.fields),
            series_count=max(len(pattern.fields) - 1, 1),
        )
    return TransformedShape(
        kind="category_ranking",
        category_count=len(pattern.fields),
        columns=list(pattern.fields),
        has_labels=True,
    )


def _bins_for_profile(profile: EnrichedColumnProfile) -> list[float]:
    """Return deterministic, strictly ascending bins for a numeric profile."""

    if profile.suggested_bins:
        bins = sorted({float(value) for value in profile.suggested_bins})
        if len(bins) >= 2:
            return bins

    if not profile.value_range:
        return []

    minimum, maximum = profile.value_range
    if minimum is None or maximum is None or maximum <= minimum:
        return []

    steps = 5
    width = (float(maximum) - float(minimum)) / steps
    bins = [float(minimum) + width * index for index in range(steps + 1)]
    return [_round_bin_edge(value) for value in bins]


def _round_bin_edge(value: float) -> float:
    rounded = round(value, 6)
    if rounded == int(rounded):
        return float(int(rounded))
    return rounded


def _class_object_transformer_config(
    source_name: str,
    class_object: ClassObjectStats,
    transformer: str,
) -> dict[str, Any]:
    """Build a valid config for the suggested class_object transformer."""

    auto_config = dict(class_object.auto_config or {})
    if auto_config:
        auto_config["source"] = source_name
        if "fields" in auto_config:
            for field_cfg in auto_config.get("fields") or []:
                if isinstance(field_cfg, dict):
                    field_cfg.setdefault("source", source_name)
        if "groups" in auto_config:
            for group_cfg in auto_config.get("groups") or []:
                if isinstance(group_cfg, dict):
                    group_cfg.setdefault("label", class_object.name)
        return auto_config

    if transformer == "class_object_field_aggregator":
        return {
            "source": source_name,
            "fields": [
                {"class_object": class_object.name, "target": class_object.name}
            ],
        }

    if transformer == "class_object_binary_aggregator":
        mapping = class_object.mapping_hints or {
            str(name): str(name) for name in class_object.class_names
        }
        classes = list(dict.fromkeys(mapping.values())) or [
            str(name) for name in class_object.class_names
        ]
        return {
            "source": source_name,
            "groups": [
                {
                    "label": class_object.name,
                    "field": class_object.name,
                    "classes": classes,
                    "class_mapping": {
                        str(name): mapping.get(str(name), str(name))
                        for name in class_object.class_names
                    },
                }
            ],
        }

    return {
        "source": source_name,
        "class_object": class_object.name,
        "size_field": {
            "input": "class_name",
            "output": "tops",
            "numeric": class_object.value_type == "numeric",
            "sort": class_object.value_type == "numeric",
        },
        "value_field": {
            "input": "class_value",
            "output": "counts",
            "numeric": True,
        },
    }


def _class_object_widget_params(
    class_object: ClassObjectStats,
    shape: TransformedShape,
) -> dict[str, Any]:
    if shape.kind == "scalar_metric":
        return _info_grid_params_for_class_objects([class_object])

    if shape.kind == "boolean_split":
        return {
            "subplots": [
                {
                    "name": _humanize(class_object.name),
                    "data_key": class_object.name,
                }
            ],
            "show_legend": True,
        }

    if shape.kind in {
        "category_distribution",
        "category_ranking",
        "binned_numeric_distribution",
    }:
        if shape.kind == "category_ranking":
            return {
                "x_axis": "counts",
                "y_axis": "tops",
                "orientation": "h",
            }
        return {
            "x_axis": "tops",
            "y_axis": "counts",
            "orientation": "v",
        }

    return {}


def _info_grid_params_for_class_objects(
    class_objects: Sequence[ClassObjectStats],
) -> dict[str, Any]:
    selected = list(class_objects)
    return {
        "items": [
            {
                "label": _humanize(item.name),
                "source": f"{item.name}.value",
                "unit": item.auto_config.get("units") if item.auto_config else None,
                "format": "number",
            }
            for item in selected
        ],
        "grid_columns": min(max(len(selected), 1), 3),
    }


def _purpose_utility(purpose: FieldPurpose) -> float:
    return {
        FieldPurpose.MEASUREMENT: 0.9,
        FieldPurpose.CLASSIFICATION: 0.86,
        FieldPurpose.LOCATION: 0.76,
        FieldPurpose.METADATA: 0.58,
        FieldPurpose.DESCRIPTION: 0.35,
        FieldPurpose.FOREIGN_KEY: 0.25,
        FieldPurpose.PRIMARY_KEY: 0.1,
    }.get(purpose, 0.5)


def _cardinality_score(profile: EnrichedColumnProfile) -> float:
    if profile.data_category == DataCategory.CATEGORICAL_HIGH_CARD:
        return 0.62
    if profile.data_category == DataCategory.CATEGORICAL:
        if profile.cardinality <= 0:
            return 0.45
        if profile.cardinality <= 12:
            return 0.95
        if profile.cardinality <= 30:
            return 0.75
        return 0.55
    if profile.data_category in {
        DataCategory.NUMERIC_CONTINUOUS,
        DataCategory.NUMERIC_DISCRETE,
    }:
        return 0.88
    return 0.7


def _class_object_cardinality_score(class_object: ClassObjectStats) -> float:
    if class_object.cardinality <= 2:
        return 0.92
    if class_object.cardinality <= 15:
        return 0.82
    return 0.65


def _average_confidence(class_objects: Sequence[ClassObjectStats]) -> float:
    if not class_objects:
        return 0.0
    return sum(item.confidence for item in class_objects) / len(class_objects)


def _max_label_length(labels: Sequence[str] | None) -> int | None:
    if not labels:
        return None
    return max(len(str(label)) for label in labels)


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _slug(value: str) -> str:
    return "_".join(value.lower().split())[:48] or "proposal"
