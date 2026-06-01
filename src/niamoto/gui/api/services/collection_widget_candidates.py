"""Collection-scoped widget candidate API service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from niamoto.core.collections.widget_candidate_models import (
    WidgetCandidate,
    WidgetCandidateGroups,
    candidate_from_proposal,
)
from niamoto.gui.api.models.widget_candidates import (
    WidgetCandidateApplyResponse,
    WidgetCandidateConfigChange,
    WidgetCandidatePreviewResponse,
    WidgetCandidateSelection,
)
from niamoto.gui.api.models.widget_proposals import (
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
            proposal_id=change.proposal_id,
            widget_id=change.widget_id,
            title=change.title,
            action=change.action,
            reason=change.reason,
            transform_widget=change.transform_widget,
            export_widget=change.export_widget,
        )
