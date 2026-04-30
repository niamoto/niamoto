"""Grain compatibility analysis for standard publication profiles."""

from __future__ import annotations

from typing import Any

from niamoto.core.collections import CollectionCatalogService
from niamoto.core.collections.models import CollectionCatalogEntry
from niamoto.core.standards.models import (
    StandardCompatibilityStatus,
    StandardCompatibilityReport,
    StandardProfileConfig,
    StandardProfileEvidence,
    StandardProfileSource,
)


class StandardCompatibilityService:
    """Evaluate whether a source can legitimately produce a standard profile."""

    def __init__(
        self,
        *,
        import_config: dict[str, Any] | None = None,
        transform_config: list[dict[str, Any]] | None = None,
    ) -> None:
        self.import_config = import_config or {}
        self.transform_config = transform_config or []
        self.catalog = CollectionCatalogService(
            import_config=self.import_config,
            transform_config=self.transform_config,
        ).list_collections()

    def evaluate(self, profile: StandardProfileConfig) -> StandardCompatibilityReport:
        """Build a compatibility report for the given standard profile."""
        source_grain = self._source_grain(profile.source)
        if profile.standard == "darwin_core_occurrence":
            return self._evaluate_darwin_core_occurrence(profile, source_grain)
        return self._evaluate_humboldt_event(profile, source_grain)

    def _evaluate_darwin_core_occurrence(
        self, profile: StandardProfileConfig, source_grain: str
    ) -> StandardCompatibilityReport:
        evidence: list[StandardProfileEvidence] = []
        warnings: list[str] = []
        blockers: list[str] = []

        if profile.target_grain != "occurrence":
            blockers.append(
                "Darwin Core Occurrence profiles must target occurrence grain."
            )

        if source_grain == "occurrence":
            evidence.append(
                StandardProfileEvidence(
                    kind="source_grain",
                    message="Source is occurrence-grain data.",
                    confidence=0.9,
                    details={"source": profile.source.model_dump(mode="json")},
                )
            )
            status: StandardCompatibilityStatus = "compatible"
            confidence = 0.9
        else:
            relation = self._find_occurrence_relation(profile.source, profile.context)
            if relation:
                evidence.append(
                    StandardProfileEvidence(
                        kind="occurrence_relation",
                        message=(
                            "Source collection is related to occurrence-grain data."
                        ),
                        confidence=0.82,
                        details=relation,
                    )
                )
                status = "compatible"
                confidence = 0.82
            else:
                blockers.append(
                    "Darwin Core Occurrence requires occurrence-grain data or an explicit relation to occurrence data."
                )
                status = "blocked"
                confidence = 0.3

        if blockers:
            status = "blocked"
            confidence = min(confidence, 0.3)

        return StandardCompatibilityReport(
            standard=profile.standard,
            target_grain=profile.target_grain,
            source=profile.source,
            source_grain=source_grain,
            context=profile.context,
            status=status,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            blockers=blockers,
        )

    def _evaluate_humboldt_event(
        self, profile: StandardProfileConfig, source_grain: str
    ) -> StandardCompatibilityReport:
        evidence: list[StandardProfileEvidence] = []
        warnings: list[str] = []
        blockers: list[str] = []

        if profile.target_grain not in {"event", "inventory"}:
            blockers.append(
                "Humboldt/Event profiles must target event or inventory grain."
            )

        if source_grain in {"event", "inventory"}:
            evidence.append(
                StandardProfileEvidence(
                    kind="source_grain",
                    message="Source has Event or inventory grain evidence.",
                    confidence=0.85,
                )
            )
            status: StandardCompatibilityStatus = "compatible"
            confidence = 0.85
        elif source_grain == "site":
            evidence.append(
                StandardProfileEvidence(
                    kind="site_context",
                    message="Site collection may provide inventory context.",
                    confidence=0.62,
                )
            )
            warnings.append(
                "Site-grain collection can start a Humboldt/Event profile, but Event or inventory evidence is still required."
            )
            status = "plausible"
            confidence = 0.62
        else:
            blockers.append(
                "Humboldt/Event requires Event, inventory, site, or sampling evidence."
            )
            status = "blocked"
            confidence = 0.25

        if blockers:
            status = "blocked"
            confidence = min(confidence, 0.25)

        return StandardCompatibilityReport(
            standard=profile.standard,
            target_grain=profile.target_grain,
            source=profile.source,
            source_grain=source_grain,
            context=profile.context,
            status=status,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            blockers=blockers,
        )

    def _source_grain(self, source: StandardProfileSource) -> str:
        if source.type == "collection":
            collection = self._find_collection(source.name)
            return collection.grain if collection else "unknown"
        if source.type == "reference":
            collection = self._find_collection(source.name)
            return collection.grain if collection else "reference"
        if source.type == "dataset":
            return self._infer_dataset_grain(
                source.name, self._datasets().get(source.name)
            )
        if source.type == "transform_group":
            return "aggregate"

    def _find_collection(self, name: str) -> CollectionCatalogEntry | None:
        for collection in self.catalog.collections:
            if collection.name == name:
                return collection
        return None

    def _find_occurrence_relation(
        self,
        source: StandardProfileSource,
        context: StandardProfileSource | None,
    ) -> dict[str, Any] | None:
        candidate_names = [source.name]
        if context is not None:
            candidate_names.append(context.name)

        for dataset_name, dataset_config in self._datasets().items():
            if self._infer_dataset_grain(dataset_name, dataset_config) != "occurrence":
                continue
            if not isinstance(dataset_config, dict):
                continue
            for link in dataset_config.get("links", []) or []:
                if not isinstance(link, dict):
                    continue
                if link.get("entity") in candidate_names:
                    return {
                        "occurrence_dataset": dataset_name,
                        "relation_entity": link.get("entity"),
                        "foreign_key": link.get("field"),
                        "target_field": link.get("target_field"),
                    }

        for reference_name, reference_config in self._references().items():
            if reference_name not in candidate_names or not isinstance(
                reference_config, dict
            ):
                continue
            relation = reference_config.get("relation")
            if not isinstance(relation, dict):
                continue
            dataset_name = str(relation.get("dataset") or "")
            if (
                self._infer_dataset_grain(
                    str(dataset_name), self._datasets().get(str(dataset_name))
                )
                == "occurrence"
            ):
                return {
                    "occurrence_dataset": dataset_name,
                    "relation_entity": reference_name,
                    "foreign_key": relation.get("foreign_key"),
                    "target_field": relation.get("reference_key"),
                }
        return None

    def _infer_dataset_grain(self, name: str, config: Any) -> str:
        haystack = [name]
        if isinstance(config, dict):
            schema = config.get("schema")
            if isinstance(schema, dict):
                fields = schema.get("fields", [])
                if isinstance(fields, dict):
                    haystack.extend(fields.keys())
                elif isinstance(fields, list):
                    haystack.extend(
                        str(field.get("name"))
                        for field in fields
                        if isinstance(field, dict) and field.get("name")
                    )
        text = " ".join(haystack).lower()
        if any(token in text for token in ("occurrence", "observation", "record")):
            return "occurrence"
        if any(token in text for token in ("event", "inventory", "sampling")):
            return "event"
        if any(token in text for token in ("plot", "site", "station")):
            return "site"
        return "dataset"

    def _references(self) -> dict[str, Any]:
        entities = self.import_config.get("entities")
        if not isinstance(entities, dict):
            return {}
        references = entities.get("references")
        return references if isinstance(references, dict) else {}

    def _datasets(self) -> dict[str, Any]:
        entities = self.import_config.get("entities")
        if not isinstance(entities, dict):
            return {}
        datasets = entities.get("datasets")
        return datasets if isinstance(datasets, dict) else {}
