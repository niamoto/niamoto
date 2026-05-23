"""API models for collection widget proposals."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ReplacementChoice = Literal["add", "replace", "skip"]
ProposalChangeAction = Literal["add", "replace", "conflict", "skip", "invalid"]


class WidgetProposalSelection(BaseModel):
    """Selected proposal and conflict decision from the review UI."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=1)
    replacement: ReplacementChoice = "add"


class WidgetProposalPreviewRequest(BaseModel):
    """Preview request for selected widget proposals."""

    model_config = ConfigDict(extra="forbid")

    selections: list[WidgetProposalSelection] = Field(default_factory=list)


class WidgetProposalApplyRequest(WidgetProposalPreviewRequest):
    """Apply request for selected widget proposals."""

    preview_token: str | None = None


class WidgetProposalConfigChange(BaseModel):
    """One proposed transform/export config change."""

    proposal_id: str
    widget_id: str
    title: str
    action: ProposalChangeAction
    reason: str | None = None
    transform_widget: dict[str, Any] | None = None
    export_widget: dict[str, Any] | None = None


class WidgetProposalPreviewResponse(BaseModel):
    """Preview of selected proposal config changes."""

    collection: str
    writes_files: bool = False
    preview_token: str
    changes: list[WidgetProposalConfigChange] = Field(default_factory=list)
    conflicts: list[WidgetProposalConfigChange] = Field(default_factory=list)
    invalid: list[WidgetProposalConfigChange] = Field(default_factory=list)


class WidgetProposalApplyResponse(BaseModel):
    """Result of applying selected proposal config changes."""

    collection: str
    success: bool
    applied: list[WidgetProposalConfigChange] = Field(default_factory=list)
    skipped: list[WidgetProposalConfigChange] = Field(default_factory=list)
    message: str
    preview_token: str | None = None
    written_files: list[str] = Field(default_factory=list)
    backup_files: list[str] = Field(default_factory=list)
