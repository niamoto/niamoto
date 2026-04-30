"""Validation reports for standard publication profiles."""

from __future__ import annotations

from typing import Any

from niamoto.core.standards.compatibility import StandardCompatibilityService
from niamoto.core.standards.models import (
    StandardProfileConfig,
    StandardProfileValidationStatus,
    StandardValidationChecklistItem,
    StandardValidationIssue,
    StandardValidationReport,
)
from niamoto.core.standards.rules import (
    recommended_term_item,
    required_term_item,
    validate_mapping_shape,
)


class StandardProfileValidationService:
    """Validate standard profiles with structured checklist and issue output."""

    def __init__(
        self,
        *,
        import_config: dict[str, Any] | None = None,
        transform_config: list[dict[str, Any]] | None = None,
    ) -> None:
        self.compatibility_service = StandardCompatibilityService(
            import_config=import_config,
            transform_config=transform_config,
        )

    def validate(self, profile: StandardProfileConfig) -> StandardValidationReport:
        """Validate a profile and return a report safe for API serialization."""
        compatibility = self.compatibility_service.evaluate(profile)
        checklist: list[StandardValidationChecklistItem] = []
        issues: list[StandardValidationIssue] = []

        if compatibility.status == "blocked":
            for blocker in compatibility.blockers:
                issues.append(
                    StandardValidationIssue(
                        code="compatibility_blocked",
                        severity="critical",
                        message=blocker,
                    )
                )
            checklist.append(
                StandardValidationChecklistItem(
                    code="grain_compatibility",
                    label="Source grain compatibility",
                    status="fail",
                    severity="critical",
                    message="Profile source cannot produce the requested standard grain.",
                )
            )
        else:
            checklist.append(
                StandardValidationChecklistItem(
                    code="grain_compatibility",
                    label="Source grain compatibility",
                    status="warn" if compatibility.status == "plausible" else "pass",
                    severity="warning"
                    if compatibility.status == "plausible"
                    else "info",
                    message="Compatibility is plausible but needs review."
                    if compatibility.status == "plausible"
                    else None,
                )
            )

        mapping_shape_issues = validate_mapping_shape(profile)
        issues.extend(mapping_shape_issues)
        if mapping_shape_issues:
            checklist.append(
                StandardValidationChecklistItem(
                    code="mapping_shape",
                    label="Mapping structure",
                    status="fail",
                    severity="critical",
                    message="One or more mappings have an invalid shape.",
                )
            )
        elif profile.standard == "darwin_core_occurrence":
            self._validate_darwin_core(profile, checklist, issues)
        else:
            self._validate_humboldt_event(profile, checklist, issues)

        summary = self._summary(issues)
        status = self._status(summary, compatibility.status, profile)
        return StandardValidationReport(
            profile_name=profile.name,
            standard=profile.standard,
            status=status,
            summary=summary,
            compatibility=compatibility,
            checklist=checklist,
            issues=issues,
        )

    def _validate_darwin_core(
        self,
        profile: StandardProfileConfig,
        checklist: list[StandardValidationChecklistItem],
        issues: list[StandardValidationIssue],
    ) -> None:
        item, item_issues = required_term_item(
            code="dwc_occurrence_id",
            label="Darwin Core occurrenceID",
            term="occurrenceID",
            mappings=profile.mappings,
        )
        checklist.insert(0, item)
        issues.extend(item_issues)

    def _validate_humboldt_event(
        self,
        profile: StandardProfileConfig,
        checklist: list[StandardValidationChecklistItem],
        issues: list[StandardValidationIssue],
    ) -> None:
        item, item_issues = required_term_item(
            code="humboldt_event_id",
            label="Humboldt/Event eventID",
            term="eventID",
            mappings=profile.mappings,
        )
        checklist.insert(0, item)
        issues.extend(item_issues)

        for code, label, term in (
            ("humboldt_event_date", "Event date", "eventDate"),
            ("humboldt_sampling_protocol", "Sampling protocol", "samplingProtocol"),
            ("humboldt_location_scope", "Location or site scope", "locationID"),
        ):
            recommended, recommended_issues = recommended_term_item(
                code=code,
                label=label,
                term=term,
                mappings=profile.mappings,
            )
            checklist.append(recommended)
            issues.extend(recommended_issues)

    def _summary(self, issues: list[StandardValidationIssue]) -> dict[str, int]:
        summary = {"critical": 0, "warning": 0, "recommended": 0, "info": 0}
        for issue in issues:
            summary[issue.severity] += 1
        return summary

    def _status(
        self,
        summary: dict[str, int],
        compatibility_status: str,
        profile: StandardProfileConfig,
    ) -> StandardProfileValidationStatus:
        if summary["critical"] > 0:
            return "invalid"
        if compatibility_status == "plausible":
            return "partial"
        if summary["warning"] > 0 or summary["recommended"] > 0:
            return "partial"
        if not profile.mappings:
            return "draft"
        return "conformant"
