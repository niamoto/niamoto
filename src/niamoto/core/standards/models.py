"""Models for standard publication profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

StandardProfileType = Literal["darwin_core_occurrence", "humboldt_event"]
StandardProfileSourceType = Literal[
    "collection", "reference", "dataset", "transform_group"
]
StandardProfileOutputType = Literal["api_json", "dwc_archive", "standard_files"]
StandardProfileValidationStatus = Literal["draft", "partial", "invalid", "conformant"]
StandardProfileOutputStatus = Literal["success", "skipped", "error"]
StandardCompatibilityStatus = Literal["compatible", "plausible", "blocked"]
StandardValidationSeverity = Literal["critical", "warning", "recommended", "info"]
StandardChecklistStatus = Literal["pass", "warn", "fail"]


class StandardProfileSource(BaseModel):
    """Source or context used by a standard publication profile."""

    type: StandardProfileSourceType
    name: str


class StandardProfileOutput(BaseModel):
    """Output configuration owned by a standard profile."""

    model_config = ConfigDict(extra="allow")

    type: StandardProfileOutputType
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class StandardProfileConfig(BaseModel):
    """A standard publication profile persisted in export.yml."""

    model_config = ConfigDict(extra="allow")

    name: str
    enabled: bool = True
    standard: StandardProfileType
    target_grain: str
    source: StandardProfileSource
    context: StandardProfileSource | None = None
    mappings: dict[str, Any] = Field(default_factory=dict)
    outputs: list[StandardProfileOutput] = Field(default_factory=list)
    validation_status: StandardProfileValidationStatus = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)


class LegacyStandardProfileHint(BaseModel):
    """Legacy export target that can be interpreted as a standard profile."""

    export_name: str
    standard: StandardProfileType
    message: str
    source: StandardProfileSource | None = None


class StandardProfileEvidence(BaseModel):
    """Evidence used by standard compatibility and validation reports."""

    kind: str
    message: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)


class StandardCompatibilityReport(BaseModel):
    """Grain compatibility report for a standard profile."""

    standard: StandardProfileType
    target_grain: str
    source: StandardProfileSource
    source_grain: str
    context: StandardProfileSource | None = None
    status: StandardCompatibilityStatus
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[StandardProfileEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class StandardValidationIssue(BaseModel):
    """One validation issue for a standard profile."""

    code: str
    severity: StandardValidationSeverity
    message: str
    path: str | None = None


class StandardValidationChecklistItem(BaseModel):
    """Checklist item derived from the validation rules."""

    code: str
    label: str
    status: StandardChecklistStatus
    severity: StandardValidationSeverity
    message: str | None = None


class StandardValidationReport(BaseModel):
    """Structured validation report for a standard profile."""

    profile_name: str
    standard: StandardProfileType
    status: StandardProfileValidationStatus
    summary: dict[str, int]
    compatibility: StandardCompatibilityReport
    checklist: list[StandardValidationChecklistItem] = Field(default_factory=list)
    issues: list[StandardValidationIssue] = Field(default_factory=list)


class StandardProfileOutputResult(BaseModel):
    """Result of one profile-owned standard output execution."""

    profile_name: str
    standard: StandardProfileType
    output_type: StandardProfileOutputType
    status: StandardProfileOutputStatus
    validation_status: StandardProfileValidationStatus
    source_grain: str
    output_path: str | None = None
    files_generated: int = 0
    files: list[Path] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StandardProfileOutputPreviewResult(BaseModel):
    """Representative JSON preview for one profile-owned standard output."""

    profile_name: str
    standard: StandardProfileType
    output_type: StandardProfileOutputType
    validation_status: StandardProfileValidationStatus
    source_grain: str
    item_id: Any | None = None
    preview: Any
    source: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
