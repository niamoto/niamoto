"""Collection-scoped data output options for the GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from niamoto.core.collections import CollectionCatalogService
from niamoto.core.collections.models import CollectionCatalogEntry
from niamoto.core.standards import StandardProfileStore
from niamoto.core.standards.auto_config import StandardProfileAutoConfigService
from niamoto.core.standards.compatibility import StandardCompatibilityService
from niamoto.core.standards.models import (
    StandardCompatibilityReport,
    StandardProfileConfig,
    StandardProfileEvidence,
    StandardProfileSource,
    StandardProfileType,
    StandardValidationReport,
)
from niamoto.core.standards.validation import StandardProfileValidationService

DataOutputFamily = Literal["simple_json", "standard"]
DataConfiguredOutputKind = Literal[
    "api_json", "standard_profile", "legacy_standard_hint"
]
DataOptionSuitability = Literal["recommended", "possible", "not_recommended"]
DataOptionsState = Literal["configured", "recommended", "needs_intent"]


class CollectionDataSourceSummary(BaseModel):
    """Safe source summary for the active collection."""

    type: str
    name: str


class CollectionDataSummary(BaseModel):
    """Collection metadata needed by the Data workspace."""

    name: str
    label: str
    grain: str
    roles: list[str] = Field(default_factory=list)
    source: CollectionDataSourceSummary
    review_status: str


class CollectionDataEvidence(BaseModel):
    """Evidence behind an output option or configured output."""

    kind: str
    message: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)


class CollectionDataAction(BaseModel):
    """Action descriptor interpreted by the collection Data UI."""

    type: str
    label: str
    target: dict[str, Any] = Field(default_factory=dict)


class CollectionDataConfiguredOutput(BaseModel):
    """Configured or legacy data output scoped to one collection."""

    id: str
    kind: DataConfiguredOutputKind
    name: str
    label: str
    enabled: bool = True
    status: str
    family: DataOutputFamily
    source: CollectionDataSourceSummary | None = None
    standard: StandardProfileType | None = None
    target_grain: str | None = None
    validation_status: str | None = None
    actions: list[CollectionDataAction] = Field(default_factory=list)
    evidence: list[CollectionDataEvidence] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class CollectionDataOption(BaseModel):
    """Available data output option for a collection."""

    id: str
    family: DataOutputFamily
    label: str
    suitability: DataOptionSuitability
    confidence: float = Field(ge=0.0, le=1.0)
    standard: StandardProfileType | None = None
    target_grain: str | None = None
    reasons: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    evidence: list[CollectionDataEvidence] = Field(default_factory=list)
    action: CollectionDataAction | None = None


class CollectionDataOptionsResponse(BaseModel):
    """Read model for the collection Data workspace."""

    collection: CollectionDataSummary
    state: DataOptionsState
    configured_outputs: list[CollectionDataConfiguredOutput] = Field(
        default_factory=list
    )
    available_options: list[CollectionDataOption] = Field(default_factory=list)
    primary_action: CollectionDataAction | None = None
    missing_evidence: list[str] = Field(default_factory=list)
    sensitivity: dict[str, Any] = Field(default_factory=dict)


class CollectionDataOptionsService:
    """Build a collection-scoped read model for reusable data outputs."""

    def __init__(
        self,
        *,
        work_dir: str | Path,
        db_path: str | Path | None = None,
        import_config: dict[str, Any] | None = None,
        transform_config: list[dict[str, Any]] | None = None,
        export_config: dict[str, Any] | None = None,
    ) -> None:
        self.work_dir = Path(work_dir)
        self.db_path = Path(db_path) if db_path is not None else None
        self.import_config = import_config or {}
        self.transform_config = transform_config or []
        self.export_config = export_config or {}
        self.catalog_service = CollectionCatalogService(
            import_config=self.import_config,
            transform_config=self.transform_config,
            export_config=self.export_config,
        )
        self.catalog = self.catalog_service.list_collections()
        self.profile_store = StandardProfileStore(
            self.export_config,
            known_sources=self._known_sources(),
        )
        self.compatibility_service = StandardCompatibilityService(
            import_config=self.import_config,
            transform_config=self.transform_config,
        )
        self.validation_service = StandardProfileValidationService(
            import_config=self.import_config,
            transform_config=self.transform_config,
        )
        self.auto_config_service = StandardProfileAutoConfigService(
            self.work_dir,
            db_path=self.db_path,
            import_config=self.import_config,
            transform_config=self.transform_config,
        )

    def get_options(self, collection_name: str) -> CollectionDataOptionsResponse:
        """Return the Data workspace state for a collection."""
        collection = self.catalog_service.get_collection(collection_name)
        configured_outputs = self._configured_outputs(collection)
        available_options = self._available_options(collection)
        primary_action = self._primary_action(configured_outputs, available_options)
        state: DataOptionsState = (
            "configured"
            if configured_outputs
            else "recommended"
            if primary_action is not None
            else "needs_intent"
        )

        return CollectionDataOptionsResponse(
            collection=self._collection_summary(collection),
            state=state,
            configured_outputs=configured_outputs,
            available_options=available_options,
            primary_action=primary_action,
            missing_evidence=self._missing_evidence(available_options),
            sensitivity=self._sensitivity_summary(collection),
        )

    def _configured_outputs(
        self, collection: CollectionCatalogEntry
    ) -> list[CollectionDataConfiguredOutput]:
        outputs = self._configured_api_outputs(collection)
        outputs.extend(self._configured_standard_profiles(collection))
        outputs.extend(self._legacy_standard_hints(collection))
        return outputs

    def _configured_api_outputs(
        self, collection: CollectionCatalogEntry
    ) -> list[CollectionDataConfiguredOutput]:
        outputs: list[CollectionDataConfiguredOutput] = []
        for export_entry in self._api_export_targets():
            export_name = str(export_entry.get("name") or "json_api")
            for group in export_entry.get("groups", []) or []:
                if not isinstance(group, dict):
                    continue
                if group.get("group_by") != collection.name:
                    continue
                target_enabled = bool(export_entry.get("enabled", True))
                group_enabled = bool(group.get("enabled", True))
                enabled = target_enabled and group_enabled
                outputs.append(
                    CollectionDataConfiguredOutput(
                        id=f"api_json:{export_name}:{collection.name}",
                        kind="api_json",
                        name=export_name,
                        label=export_name,
                        enabled=enabled,
                        status="enabled" if enabled else "disabled",
                        family="simple_json",
                        source=self._collection_source_summary(collection),
                        actions=[
                            CollectionDataAction(
                                type="edit_api_output",
                                label="Edit JSON output",
                                target={
                                    "export_name": export_name,
                                    "collection": collection.name,
                                },
                            ),
                            CollectionDataAction(
                                type="preview_api_output",
                                label="Preview JSON output",
                                target={
                                    "export_name": export_name,
                                    "collection": collection.name,
                                },
                            ),
                        ],
                        evidence=[
                            CollectionDataEvidence(
                                kind="configured_api_group",
                                message=(
                                    "A static JSON API target is configured for this collection."
                                ),
                                details={"export_name": export_name},
                            )
                        ],
                        summary={
                            "transformer_plugin": group.get("transformer_plugin"),
                            "has_detail": isinstance(group.get("detail"), dict),
                            "has_index": isinstance(group.get("index"), dict),
                        },
                    )
                )
        return outputs

    def _configured_standard_profiles(
        self, collection: CollectionCatalogEntry
    ) -> list[CollectionDataConfiguredOutput]:
        outputs: list[CollectionDataConfiguredOutput] = []
        for profile in self.profile_store.list_profiles():
            if not self._profile_belongs_to_collection(profile, collection):
                continue
            validation, validation_error = self._safe_validation_result(profile)
            evidence = [
                CollectionDataEvidence(
                    kind="configured_standard_profile",
                    message=(
                        "A standard publication profile uses this collection as its source."
                    ),
                    details={"profile_name": profile.name},
                )
            ]
            if validation_error:
                evidence.append(
                    CollectionDataEvidence(
                        kind="validation_error",
                        message=f"Profile validation could not be evaluated: {validation_error}",
                        confidence=0.0,
                        details={"profile_name": profile.name},
                    )
                )
            outputs.append(
                CollectionDataConfiguredOutput(
                    id=f"standard_profile:{profile.name}",
                    kind="standard_profile",
                    name=profile.name,
                    label=profile.name,
                    enabled=profile.enabled,
                    status=validation.status
                    if validation
                    else profile.validation_status,
                    family="standard",
                    source=CollectionDataSourceSummary(
                        type=profile.source.type,
                        name=profile.source.name,
                    ),
                    standard=profile.standard,
                    target_grain=profile.target_grain,
                    validation_status=validation.status
                    if validation
                    else profile.validation_status,
                    actions=[
                        CollectionDataAction(
                            type="edit_standard_profile",
                            label="Edit standard profile",
                            target={"profile_name": profile.name},
                        ),
                        CollectionDataAction(
                            type="validate_standard_profile",
                            label="Validate standard profile",
                            target={"profile_name": profile.name},
                        ),
                    ],
                    evidence=evidence,
                    summary={
                        "mapped_terms": len(profile.mappings),
                        "enabled_outputs": sum(
                            1 for output in profile.outputs if output.enabled
                        ),
                    },
                )
            )
        return outputs

    def _legacy_standard_hints(
        self, collection: CollectionCatalogEntry
    ) -> list[CollectionDataConfiguredOutput]:
        outputs: list[CollectionDataConfiguredOutput] = []
        for hint in self.profile_store.list_legacy_hints():
            source = hint.get("source")
            if not isinstance(source, dict):
                continue
            if not self._source_belongs_to_collection(source, collection):
                continue
            standard = hint.get("standard")
            outputs.append(
                CollectionDataConfiguredOutput(
                    id=f"legacy_standard_hint:{hint.get('export_name')}",
                    kind="legacy_standard_hint",
                    name=str(hint.get("export_name") or "legacy_standard_export"),
                    label=str(hint.get("export_name") or "Legacy standard export"),
                    enabled=True,
                    status="legacy",
                    family="standard",
                    source=CollectionDataSourceSummary(
                        type=str(source.get("type") or "collection"),
                        name=str(source.get("name") or collection.name),
                    ),
                    standard=standard
                    if standard in {"darwin_core_occurrence", "humboldt_event"}
                    else None,
                    evidence=[
                        CollectionDataEvidence(
                            kind="legacy_standard_hint",
                            message=str(
                                hint.get("message")
                                or "A legacy export resembles a standard output."
                            ),
                            details={"export_name": hint.get("export_name")},
                        )
                    ],
                    summary={"migration_available": False},
                )
            )
        return outputs

    def _available_options(
        self, collection: CollectionCatalogEntry
    ) -> list[CollectionDataOption]:
        standard_options = [
            self._standard_option(collection, "darwin_core_occurrence", "occurrence"),
            self._standard_option(collection, "humboldt_event", "event"),
        ]
        simple_option = self._simple_json_option(collection, standard_options)
        return [simple_option, *standard_options]

    def _simple_json_option(
        self,
        collection: CollectionCatalogEntry,
        standard_options: list[CollectionDataOption],
    ) -> CollectionDataOption:
        standard_recommended = any(
            option.suitability == "recommended" for option in standard_options
        )
        known_source = collection.source_type in {
            "reference",
            "dataset",
            "transform_group",
        }
        known_grain = bool(collection.grain and collection.grain != "unknown")
        suitability: DataOptionSuitability = (
            "possible" if standard_recommended or not known_grain else "recommended"
        )
        confidence = (
            0.55
            if not known_grain
            else 0.72
            if standard_recommended
            else 0.86
            if known_source
            else 0.55
        )
        missing = [] if known_source else ["Collection source is not recognized."]
        if not known_grain:
            missing.append("Collection grain is unknown.")
        return CollectionDataOption(
            id="simple_json",
            family="simple_json",
            label="Reusable JSON",
            suitability=suitability,
            confidence=confidence,
            reasons=[
                "Simple JSON is the lowest-friction reusable data output.",
            ],
            missing_evidence=missing,
            evidence=[
                CollectionDataEvidence(
                    kind="collection_source",
                    message=(
                        "Collection has a known source."
                        if known_source
                        else "Collection source evidence is incomplete."
                    ),
                    confidence=0.8 if known_source else 0.4,
                    details={
                        "source_type": collection.source_type,
                        "source_name": collection.source_name,
                    },
                )
            ],
            action=CollectionDataAction(
                type="create_api_output",
                label="Create reusable JSON",
                target={"collection": collection.name, "template": "simple"},
            ),
        )

    def _standard_option(
        self,
        collection: CollectionCatalogEntry,
        standard: StandardProfileType,
        target_grain: str,
    ) -> CollectionDataOption:
        source = StandardProfileSource(type="collection", name=collection.name)
        profile = StandardProfileConfig(
            name=f"{self._standard_prefix(standard)}_{collection.name}",
            enabled=True,
            standard=standard,
            target_grain=target_grain,
            source=source,
            mappings={},
            outputs=[],
        )
        compatibility, compatibility_error = self._safe_compatibility_result(profile)
        source_fields_total, source_fields_error = self._source_fields_total_result(
            standard=standard,
            target_grain=target_grain,
            source=source,
        )
        if compatibility is None:
            return self._standard_option_from_error(
                collection,
                standard,
                target_grain,
                f"Compatibility could not be evaluated: {compatibility_error}",
            )

        missing_evidence: list[str] = []
        reasons = [*compatibility.warnings]
        if compatibility.status == "blocked":
            suitability: DataOptionSuitability = "not_recommended"
            reasons.extend(compatibility.blockers)
        elif compatibility.status == "plausible":
            suitability = "possible"
            missing_evidence.append("Standard compatibility still needs review.")
        elif source_fields_total <= 0:
            suitability = "possible"
            missing_evidence.append(
                f"Source fields could not be inspected: {source_fields_error}"
                if source_fields_error
                else "No source fields were available for mapping."
            )
        elif compatibility.confidence >= 0.8:
            suitability = "recommended"
        else:
            suitability = "possible"
            missing_evidence.append(
                "Compatibility confidence is below the primary action threshold."
            )

        return CollectionDataOption(
            id=standard,
            family="standard",
            label=self._standard_label(standard),
            suitability=suitability,
            confidence=compatibility.confidence,
            standard=standard,
            target_grain=target_grain,
            reasons=reasons or [self._standard_reason(standard, compatibility)],
            missing_evidence=missing_evidence,
            evidence=[
                self._standard_evidence(evidence) for evidence in compatibility.evidence
            ]
            + [
                CollectionDataEvidence(
                    kind="source_fields",
                    message=(
                        f"{source_fields_total} source field(s) are available for mapping."
                        if source_fields_total > 0
                        else f"Source fields could not be inspected: {source_fields_error}"
                        if source_fields_error
                        else "No source fields are available for mapping."
                    ),
                    confidence=1.0
                    if source_fields_total > 0
                    else 0.0
                    if source_fields_error
                    else 0.3,
                    details={
                        "total": source_fields_total,
                        **(
                            {"error": source_fields_error}
                            if source_fields_error
                            else {}
                        ),
                    },
                )
            ],
            action=CollectionDataAction(
                type="create_standard_profile",
                label=f"Create {self._standard_label(standard)}",
                target={
                    "collection": collection.name,
                    "standard": standard,
                    "target_grain": target_grain,
                },
            ),
        )

    def _standard_option_from_error(
        self,
        collection: CollectionCatalogEntry,
        standard: StandardProfileType,
        target_grain: str,
        message: str,
    ) -> CollectionDataOption:
        return CollectionDataOption(
            id=standard,
            family="standard",
            label=self._standard_label(standard),
            suitability="not_recommended",
            confidence=0.0,
            standard=standard,
            target_grain=target_grain,
            reasons=[message],
            missing_evidence=[message],
            action=CollectionDataAction(
                type="create_standard_profile",
                label=f"Create {self._standard_label(standard)}",
                target={
                    "collection": collection.name,
                    "standard": standard,
                    "target_grain": target_grain,
                },
            ),
        )

    def _primary_action(
        self,
        configured_outputs: list[CollectionDataConfiguredOutput],
        available_options: list[CollectionDataOption],
    ) -> CollectionDataAction | None:
        if configured_outputs:
            return None
        recommended = [
            option
            for option in available_options
            if option.suitability == "recommended"
            and option.action is not None
            and not option.missing_evidence
        ]
        if not recommended:
            return None
        recommended.sort(key=lambda option: option.confidence, reverse=True)
        top = recommended[0]
        if top.confidence < 0.8:
            return None
        return top.action

    def _missing_evidence(
        self, available_options: list[CollectionDataOption]
    ) -> list[str]:
        messages: list[str] = []
        for option in available_options:
            messages.extend(option.missing_evidence)
        return sorted(set(messages))

    def _safe_compatibility(
        self, profile: StandardProfileConfig
    ) -> StandardCompatibilityReport | None:
        report, _error = self._safe_compatibility_result(profile)
        return report

    def _safe_compatibility_result(
        self, profile: StandardProfileConfig
    ) -> tuple[StandardCompatibilityReport | None, str | None]:
        try:
            return self.compatibility_service.evaluate(profile), None
        except Exception as exc:
            return None, str(exc)

    def _safe_validation(
        self, profile: StandardProfileConfig
    ) -> StandardValidationReport | None:
        report, _error = self._safe_validation_result(profile)
        return report

    def _safe_validation_result(
        self, profile: StandardProfileConfig
    ) -> tuple[StandardValidationReport | None, str | None]:
        try:
            return self.validation_service.validate(profile), None
        except Exception as exc:
            return None, str(exc)

    def _source_fields_total(
        self,
        *,
        standard: StandardProfileType,
        target_grain: str,
        source: StandardProfileSource,
    ) -> int:
        total, _error = self._source_fields_total_result(
            standard=standard,
            target_grain=target_grain,
            source=source,
        )
        return total

    def _source_fields_total_result(
        self,
        *,
        standard: StandardProfileType,
        target_grain: str,
        source: StandardProfileSource,
    ) -> tuple[int, str | None]:
        try:
            result = self.auto_config_service.source_fields(
                standard=standard,
                target_grain=target_grain,
                source=source,
            )
            return result.total, None
        except Exception as exc:
            return 0, str(exc)

    def _api_export_targets(self) -> list[dict[str, Any]]:
        return [
            export_entry
            for export_entry in self.export_config.get("exports", []) or []
            if isinstance(export_entry, dict)
            and export_entry.get("exporter") == "json_api_exporter"
        ]

    def _profile_belongs_to_collection(
        self,
        profile: StandardProfileConfig,
        collection: CollectionCatalogEntry,
    ) -> bool:
        return self._source_belongs_to_collection(
            profile.source.model_dump(mode="json"), collection
        )

    def _source_belongs_to_collection(
        self,
        source: dict[str, Any],
        collection: CollectionCatalogEntry,
    ) -> bool:
        source_type = source.get("type")
        source_name = source.get("name")
        if source_type == "collection" and source_name == collection.name:
            return True
        return (
            source_type == collection.source_type
            and source_name == collection.source_name
        )

    def _known_sources(self) -> list[dict[str, str]]:
        sources = [
            {"type": "collection", "name": collection.name}
            for collection in self.catalog.collections
        ]
        sources.extend(
            {"type": source.type, "name": source.name}
            for source in self.catalog.sources
        )
        return sources

    def _collection_summary(
        self, collection: CollectionCatalogEntry
    ) -> CollectionDataSummary:
        return CollectionDataSummary(
            name=collection.name,
            label=collection.label,
            grain=collection.grain,
            roles=list(collection.roles),
            source=self._collection_source_summary(collection),
            review_status=collection.review_status,
        )

    def _collection_source_summary(
        self, collection: CollectionCatalogEntry
    ) -> CollectionDataSourceSummary:
        return CollectionDataSourceSummary(
            type=collection.source_type,
            name=collection.source_name,
        )

    def _sensitivity_summary(
        self, collection: CollectionCatalogEntry
    ) -> dict[str, Any]:
        source_config = self._source_config(collection)
        metadata = (
            source_config.get("metadata") if isinstance(source_config, dict) else None
        )
        sensitivity = (
            metadata.get("sensitivity")
            if isinstance(metadata, dict)
            and isinstance(metadata.get("sensitivity"), dict)
            else None
        )
        return {
            "metadata_available": sensitivity is not None,
            "message": (
                "Sensitivity metadata is available for this collection source."
                if sensitivity is not None
                else "No sensitivity metadata is configured; review fields before publishing shareable outputs."
            ),
        }

    def _source_config(self, collection: CollectionCatalogEntry) -> dict[str, Any]:
        entities = self.import_config.get("entities")
        if not isinstance(entities, dict):
            return {}
        if collection.source_type == "reference":
            references = entities.get("references")
            if isinstance(references, dict):
                return references.get(collection.source_name) or {}
        if collection.source_type == "dataset":
            datasets = entities.get("datasets")
            if isinstance(datasets, dict):
                return datasets.get(collection.source_name) or {}
        return {}

    def _standard_evidence(
        self, evidence: StandardProfileEvidence
    ) -> CollectionDataEvidence:
        return CollectionDataEvidence(
            kind=evidence.kind,
            message=evidence.message,
            confidence=evidence.confidence,
            details=evidence.details,
        )

    def _standard_reason(
        self,
        standard: StandardProfileType,
        compatibility: StandardCompatibilityReport,
    ) -> str:
        if compatibility.status == "compatible":
            return f"{self._standard_label(standard)} is compatible with this collection grain."
        if compatibility.status == "plausible":
            return (
                f"{self._standard_label(standard)} is possible but needs verification."
            )
        return (
            f"{self._standard_label(standard)} is not recommended for this collection."
        )

    def _standard_label(self, standard: StandardProfileType) -> str:
        if standard == "darwin_core_occurrence":
            return "Darwin Core Occurrence"
        return "Humboldt/Event"

    def _standard_prefix(self, standard: StandardProfileType) -> str:
        if standard == "darwin_core_occurrence":
            return "dwc"
        return "humboldt"
