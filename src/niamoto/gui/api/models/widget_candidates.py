"""API models for unified collection widget candidates."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from niamoto.core.collections.widget_candidate_models import WidgetCandidateGroups

ReplacementChoice = Literal["add", "replace", "skip"]
WidgetCandidateChangeAction = Literal["add", "replace", "conflict", "skip", "invalid"]


class WidgetCandidateSelection(BaseModel):
    """Selected candidate and conflict decision from the unified picker."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    replacement: ReplacementChoice = "add"


class WidgetCandidatePreviewRequest(BaseModel):
    """Preview request for selected widget candidates."""

    model_config = ConfigDict(extra="forbid")

    selections: list[WidgetCandidateSelection] = Field(default_factory=list)


class WidgetCandidateApplyRequest(WidgetCandidatePreviewRequest):
    """Apply request for selected widget candidates."""

    preview_token: str = Field(min_length=1)


class WidgetCandidateConfigChange(BaseModel):
    """One proposed transform/export config change for a candidate."""

    candidate_id: str
    widget_id: str
    title: str
    action: WidgetCandidateChangeAction
    reason: str | None = None
    transform_widget: dict[str, Any] | None = None
    export_widget: dict[str, Any] | None = None


class WidgetCandidatePreviewResponse(BaseModel):
    """Preview of selected candidate config changes."""

    collection: str
    writes_files: bool = False
    preview_token: str
    changes: list[WidgetCandidateConfigChange] = Field(default_factory=list)
    conflicts: list[WidgetCandidateConfigChange] = Field(default_factory=list)
    invalid: list[WidgetCandidateConfigChange] = Field(default_factory=list)


class WidgetCandidateApplyResponse(BaseModel):
    """Result of applying selected candidate config changes."""

    collection: str
    success: bool
    applied: list[WidgetCandidateConfigChange] = Field(default_factory=list)
    skipped: list[WidgetCandidateConfigChange] = Field(default_factory=list)
    message: str
    preview_token: str | None = None
    written_files: list[str] = Field(default_factory=list)
    backup_files: list[str] = Field(default_factory=list)


__all__ = [
    "WidgetCandidateApplyRequest",
    "WidgetCandidateApplyResponse",
    "WidgetCandidateConfigChange",
    "WidgetCandidateGroups",
    "WidgetCandidatePreviewRequest",
    "WidgetCandidatePreviewResponse",
    "WidgetCandidateSelection",
]
