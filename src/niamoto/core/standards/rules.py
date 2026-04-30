"""First-pass structural rules for standard profile validation."""

from __future__ import annotations

from typing import Any

from niamoto.core.standards.models import (
    StandardProfileConfig,
    StandardValidationChecklistItem,
    StandardValidationIssue,
)


def validate_mapping_shape(
    profile: StandardProfileConfig,
) -> list[StandardValidationIssue]:
    """Validate generic mapping entry shapes without invoking exporters."""
    for term, mapping in profile.mappings.items():
        if isinstance(mapping, str):
            continue
        if isinstance(mapping, dict):
            has_source = bool(mapping.get("source"))
            has_generator = bool(mapping.get("generator"))
            if has_source != has_generator:
                continue
        return [
            StandardValidationIssue(
                code="mapping_invalid",
                severity="critical",
                message=(
                    f"Mapping for '{term}' must be a source string or an object "
                    "with exactly one of source or generator."
                ),
                path=f"mappings.{term}",
            )
        ]
    return []


def required_term_item(
    *,
    code: str,
    label: str,
    term: str,
    mappings: dict[str, Any],
) -> tuple[StandardValidationChecklistItem, list[StandardValidationIssue]]:
    """Build a checklist item for a critical required mapping term."""
    if term in mappings:
        return (
            StandardValidationChecklistItem(
                code=code,
                label=label,
                status="pass",
                severity="critical",
            ),
            [],
        )
    message = f"Required mapping '{term}' is missing."
    return (
        StandardValidationChecklistItem(
            code=code,
            label=label,
            status="fail",
            severity="critical",
            message=message,
        ),
        [
            StandardValidationIssue(
                code=code,
                severity="critical",
                message=message,
                path=f"mappings.{term}",
            )
        ],
    )


def recommended_term_item(
    *,
    code: str,
    label: str,
    term: str,
    mappings: dict[str, Any],
) -> tuple[StandardValidationChecklistItem, list[StandardValidationIssue]]:
    """Build a checklist item for a recommended mapping term."""
    if term in mappings:
        return (
            StandardValidationChecklistItem(
                code=code,
                label=label,
                status="pass",
                severity="recommended",
            ),
            [],
        )
    message = f"Recommended mapping '{term}' is missing."
    return (
        StandardValidationChecklistItem(
            code=code,
            label=label,
            status="warn",
            severity="recommended",
            message=message,
        ),
        [
            StandardValidationIssue(
                code=code,
                severity="recommended",
                message=message,
                path=f"mappings.{term}",
            )
        ],
    )
