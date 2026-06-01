"""Collection-scoped widget candidate API service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from niamoto.core.collections.widget_candidate_models import (
    WidgetCandidate,
    WidgetCandidateCategory,
    WidgetCandidateDetail,
    WidgetCandidateGroups,
    WidgetCandidateRecommendation,
    WidgetCandidateStatus,
)
from niamoto.core.collections.widget_proposal_models import WidgetProposal
from niamoto.gui.api.models.widget_candidates import (
    WidgetCandidateApplyResponse,
    WidgetCandidateConfigChange,
    WidgetCandidatePreviewResponse,
    WidgetCandidateSelection,
)
from niamoto.gui.api.services.collection_widget_proposal_models import (
    WidgetProposalApplyResponse,
    WidgetProposalConfigChange,
    WidgetProposalPreviewResponse,
    WidgetProposalSelection,
)
from niamoto.gui.api.services.collection_widget_proposals import (
    CollectionWidgetProposalService,
)


class CollectionWidgetCandidateService:
    """Build, preview, and apply unified widget candidates for Collections."""

    def __init__(
        self,
        *,
        work_dir: str | Path,
        db_path: str | Path | None,
        import_config: dict[str, Any],
        transform_config: list[dict[str, Any]],
        export_config: dict[str, Any],
    ) -> None:
        self.proposal_service = CollectionWidgetProposalService(
            work_dir=work_dir,
            db_path=db_path,
            import_config=import_config,
            transform_config=transform_config,
            export_config=export_config,
        )

    def get_candidates(self, collection_name: str) -> WidgetCandidateGroups:
        """Return grouped widget candidates for a collection."""

        proposals = self.proposal_service.get_proposals(collection_name)
        groups = WidgetCandidateGroups(
            collection=proposals.collection,
            partial=proposals.partial,
            messages=list(proposals.messages),
        )
        for proposal in proposals.all_proposals():
            self._append_candidate(groups, candidate_from_proposal(proposal))
        return groups

    def preview_apply(
        self,
        collection_name: str,
        selections: Sequence[WidgetCandidateSelection],
    ) -> WidgetCandidatePreviewResponse:
        """Build a side-effect-free preview for selected candidates."""

        proposal_preview = self.proposal_service.preview_apply(
            collection_name,
            self._proposal_selections(selections),
        )
        return self._preview_response(proposal_preview)

    def apply(
        self,
        collection_name: str,
        selections: Sequence[WidgetCandidateSelection],
        *,
        preview_token: str | None = None,
    ) -> WidgetCandidateApplyResponse:
        """Apply selected candidates through the locked proposal apply path."""

        proposal_result = self.proposal_service.apply(
            collection_name,
            self._proposal_selections(selections),
            preview_token=preview_token,
        )
        return self._apply_response(proposal_result)

    def _append_candidate(
        self,
        groups: WidgetCandidateGroups,
        candidate: WidgetCandidate,
    ) -> None:
        if candidate.status == "recommended":
            groups.recommended.append(candidate)
        elif candidate.status == "available":
            groups.available.append(candidate)
        elif candidate.status == "needs_review":
            groups.needs_review.append(candidate)
        elif candidate.status == "missing_chart":
            groups.missing_chart.append(candidate)
        elif candidate.status == "skipped":
            groups.skipped.append(candidate)
        else:
            groups.configured.append(candidate)

    def _proposal_selections(
        self,
        selections: Sequence[WidgetCandidateSelection],
    ) -> list[WidgetProposalSelection]:
        return [
            WidgetProposalSelection(
                proposal_id=selection.candidate_id,
                replacement=selection.replacement,
            )
            for selection in selections
        ]

    def _preview_response(
        self,
        response: WidgetProposalPreviewResponse,
    ) -> WidgetCandidatePreviewResponse:
        return WidgetCandidatePreviewResponse(
            collection=response.collection,
            writes_files=response.writes_files,
            preview_token=response.preview_token,
            changes=[self._candidate_change(change) for change in response.changes],
            conflicts=[self._candidate_change(change) for change in response.conflicts],
            invalid=[self._candidate_change(change) for change in response.invalid],
        )

    def _apply_response(
        self,
        response: WidgetProposalApplyResponse,
    ) -> WidgetCandidateApplyResponse:
        return WidgetCandidateApplyResponse(
            collection=response.collection,
            success=response.success,
            applied=[self._candidate_change(change) for change in response.applied],
            skipped=[self._candidate_change(change) for change in response.skipped],
            message=response.message,
            preview_token=response.preview_token,
            written_files=response.written_files,
            backup_files=response.backup_files,
        )

    def _candidate_change(
        self,
        change: WidgetProposalConfigChange,
    ) -> WidgetCandidateConfigChange:
        return WidgetCandidateConfigChange(
            candidate_id=change.proposal_id,
            widget_id=change.widget_id,
            title=change.title,
            action=change.action,
            reason=change.reason,
            transform_widget=change.transform_widget,
            export_widget=change.export_widget,
        )


def candidate_from_proposal(proposal: WidgetProposal) -> WidgetCandidate:
    """Project a transformation-first proposal into the unified GUI candidate contract."""

    widget_plugin = proposal.primary_fit.widget if proposal.primary_fit else None
    recipe_summary = {
        "transformer": _plugin_summary(proposal.recipe.get("transformer")),
        "widget": _plugin_summary(proposal.recipe.get("widget")),
    }
    recommendation = None
    if proposal.status == "recommended":
        recommendation = WidgetCandidateRecommendation(
            reason=proposal.primary_fit.reason
            if proposal.primary_fit
            else proposal.candidate.intent,
            score=proposal.primary_fit.score if proposal.primary_fit else None,
        )
    elif proposal.status == "already_configured":
        recommendation = WidgetCandidateRecommendation(
            reason="This candidate is already configured for the collection.",
            score=proposal.primary_fit.score if proposal.primary_fit else None,
        )

    return WidgetCandidate(
        id=proposal.id,
        collection=proposal.collection,
        title=proposal.title,
        subtitle=proposal.candidate.intent,
        origin=proposal.candidate.origin,
        category=_candidate_category(proposal),
        status=_candidate_status(proposal),
        applyability=proposal.applyability,
        default_selected=(
            proposal.status == "recommended" and proposal.applyability == "applicable"
        ),
        recommendation=recommendation,
        source_fields=list(proposal.candidate.field_names),
        source_name=proposal.candidate.source_name,
        transformer_plugin=proposal.candidate.transformer_plugin,
        widget_plugin=widget_plugin,
        detail=WidgetCandidateDetail(
            shape=proposal.shape.model_dump(),
            warnings=[warning.model_dump() for warning in proposal.warnings],
            skip_reasons=[
                skip_reason.model_dump() for skip_reason in proposal.skip_reasons
            ],
            score=proposal.score.model_dump(),
            provenance=proposal.candidate.provenance.model_dump()
            if proposal.candidate.provenance
            else {},
            recipe_summary=recipe_summary,
        ),
        recipe_summary=recipe_summary,
        fingerprint=proposal.fingerprint,
    )


def _candidate_status(proposal: WidgetProposal) -> WidgetCandidateStatus:
    if proposal.status == "recommended":
        return "recommended"
    if proposal.status == "warning":
        return "needs_review"
    if proposal.status == "review_only":
        return "needs_review"
    if proposal.status == "missing_chart":
        return "missing_chart"
    if proposal.status == "skipped":
        return "skipped"
    return "configured"


def _candidate_category(proposal: WidgetProposal) -> WidgetCandidateCategory:
    if proposal.primary_fit and proposal.primary_fit.widget in {
        "hierarchical_nav_widget",
        "info_grid",
    }:
        return "structure"

    shape_kind = proposal.shape.kind
    if shape_kind == "map_layer":
        return "map"
    if shape_kind in {"scalar_metric", "metric_group"}:
        return "metric"
    if shape_kind in {
        "category_distribution",
        "category_ranking",
        "binned_numeric_distribution",
        "boolean_split",
        "time_series",
        "numeric_pair",
    }:
        return "chart"
    if shape_kind == "table":
        return "table"
    return "unsupported"


def _plugin_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "plugin": value.get("plugin"),
        "params": value.get("params") or {},
    }
