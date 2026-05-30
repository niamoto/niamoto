"""Collection catalog inference and metadata overlay handling."""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Sequence
from typing import Any, cast

from niamoto.core.collections.models import (
    CollectionCatalog,
    CollectionCatalogEntry,
    CollectionEvidence,
    CollectionRole,
    CollectionSourceOption,
    CollectionSourceType,
)


class CollectionCatalogService:
    """Expose reviewable collection candidates from import and transform config."""

    VALID_ROLES = {"site", "api", "standard", "technical"}
    VALID_REVIEW_STATUSES = {"pending", "accepted", "deferred", "rejected"}
    VALID_SOURCE_TYPES = {"reference", "dataset", "transform_group"}

    def __init__(
        self,
        import_config: dict[str, Any] | None = None,
        transform_config: list[dict[str, Any]] | None = None,
        export_config: dict[str, Any] | None = None,
    ) -> None:
        self.import_config = import_config if import_config is not None else {}
        self.transform_config = transform_config or []
        self.export_config = export_config or {}

    def list_collections(self) -> CollectionCatalog:
        """Return reviewable collection candidates and manual source options."""
        entries: dict[str, CollectionCatalogEntry] = {}

        for name, config in self._references().items():
            if not isinstance(config, dict):
                continue
            entries[name] = self._reference_entry(name, config)

        for group_by in self._transform_group_names():
            if group_by in entries:
                continue
            entries[group_by] = self._transform_group_entry(group_by)

        for name, metadata in self._collection_metadata().items():
            if not isinstance(metadata, dict):
                continue
            if name in entries:
                entries[name] = self._apply_overlay(entries[name], metadata)
                continue
            entries[name] = self._manual_entry(name, metadata)

        collections = sorted(entries.values(), key=lambda entry: entry.name)
        return CollectionCatalog(
            collections=collections,
            sources=self.list_sources(),
            total=len(collections),
        )

    def list_sources(self) -> list[CollectionSourceOption]:
        """Return known sources that can back a manual collection."""
        sources: list[CollectionSourceOption] = []
        for name in self._references():
            sources.append(
                CollectionSourceOption(type="reference", name=name, label=name)
            )
        for name in self._datasets():
            sources.append(
                CollectionSourceOption(type="dataset", name=name, label=name)
            )
        for name in self._transform_group_names():
            sources.append(
                CollectionSourceOption(type="transform_group", name=name, label=name)
            )
        return sources

    def get_collection(self, name: str) -> CollectionCatalogEntry:
        """Return one collection by name."""
        for entry in self.list_collections().collections:
            if entry.name == name:
                return entry
        raise KeyError(f"Collection '{name}' not found")

    def update_collection(self, name: str, **updates: Any) -> CollectionCatalogEntry:
        """Persist review metadata for an existing collection candidate."""
        self.get_collection(name)
        normalized = self._normalized_update(updates)

        metadata = self._ensure_collection_metadata()
        entry = metadata.get(name)
        if not isinstance(entry, dict):
            entry = {}
            metadata[name] = entry
        entry.update(normalized)
        return self.get_collection(name)

    def create_collection(
        self,
        *,
        name: str,
        source_type: CollectionSourceType,
        source_name: str,
        grain: str,
        roles: list[CollectionRole],
        visible: bool = True,
        label: str | None = None,
    ) -> CollectionCatalogEntry:
        """Create a manual collection metadata entry."""
        if name in {entry.name for entry in self.list_collections().collections}:
            raise ValueError(f"Collection '{name}' already exists")
        self._validate_source(source_type, source_name)
        normalized_roles = self._validate_roles(roles)

        metadata = self._ensure_collection_metadata()
        entry: dict[str, Any] = {
            "source": {"type": source_type, "name": source_name},
            "grain": grain,
            "roles": normalized_roles,
            "visible": visible,
            "review_status": "accepted",
        }
        if label:
            entry["label"] = label
        metadata[name] = entry
        return self.get_collection(name)

    def _reference_entry(
        self, name: str, config: dict[str, Any]
    ) -> CollectionCatalogEntry:
        return CollectionCatalogEntry(
            name=name,
            label=name,
            source_type="reference",
            source_name=name,
            grain=self._infer_reference_grain(name, config),
            roles=["site", "api"],
            visible=True,
            review_status="pending",
            confidence=0.85,
            description=config.get("description"),
            evidence=[
                CollectionEvidence(
                    kind="import_reference",
                    message=f"Declared reference entity '{name}' in import.yml",
                    confidence=0.85,
                    details={"kind": config.get("kind")},
                )
            ],
        )

    def _transform_group_entry(self, group_by: str) -> CollectionCatalogEntry:
        return CollectionCatalogEntry(
            name=group_by,
            label=group_by,
            source_type="transform_group",
            source_name=group_by,
            grain="aggregate",
            roles=["technical"],
            visible=False,
            review_status="pending",
            confidence=0.65,
            evidence=[
                CollectionEvidence(
                    kind="transform_group",
                    message=f"Declared transform group '{group_by}'",
                    confidence=0.65,
                )
            ],
        )

    def _manual_entry(
        self, name: str, metadata: dict[str, Any]
    ) -> CollectionCatalogEntry:
        raw_source = metadata.get("source")
        source = raw_source if isinstance(raw_source, dict) else {}
        source_type = source.get("type", "dataset")
        source_name = source.get("name", name)
        self._validate_source(source_type, source_name)
        roles = self._validate_roles(metadata.get("roles", ["api"]))
        review_status = self._validate_review_status(
            metadata.get("review_status", "accepted"),
            collection_name=name,
        )
        return CollectionCatalogEntry(
            name=name,
            label=metadata.get("label") or name,
            source_type=source_type,
            source_name=source_name,
            grain=metadata.get("grain", "unknown"),
            roles=roles,
            visible=metadata.get("visible", True),
            review_status=review_status,
            confidence=metadata.get("confidence", 1.0),
            description=metadata.get("description"),
            evidence=[
                CollectionEvidence(
                    kind="manual_collection",
                    message=f"Explicit collection metadata '{name}'",
                    confidence=1.0,
                    details={"source": source},
                )
            ],
        )

    def _apply_overlay(
        self, entry: CollectionCatalogEntry, metadata: dict[str, Any]
    ) -> CollectionCatalogEntry:
        data = entry.model_dump()
        for key in (
            "label",
            "grain",
            "visible",
            "confidence",
            "description",
        ):
            if key in metadata:
                data[key] = deepcopy(metadata[key])

        if "review_status" in metadata:
            data["review_status"] = self._validate_review_status(
                metadata["review_status"],
                collection_name=entry.name,
            )

        if "roles" in metadata:
            data["roles"] = self._validate_roles(metadata["roles"])

        source = metadata.get("source")
        if isinstance(source, dict):
            data["source_type"] = source.get("type", data["source_type"])
            data["source_name"] = source.get("name", data["source_name"])
            self._validate_source(data["source_type"], data["source_name"])

        return CollectionCatalogEntry.model_validate(data)

    def _normalized_update(self, updates: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in updates.items():
            if value is None:
                continue
            if key == "roles":
                normalized[key] = self._validate_roles(value)
                continue
            if key == "review_status" and value not in self.VALID_REVIEW_STATUSES:
                self._raise_invalid_review_status(value)
            if key in {"label", "visible", "review_status", "grain", "description"}:
                normalized[key] = value
        return normalized

    def _validate_review_status(
        self, value: str, *, collection_name: str | None = None
    ) -> str:
        if value not in self.VALID_REVIEW_STATUSES:
            self._raise_invalid_review_status(value, collection_name=collection_name)
        return value

    def _raise_invalid_review_status(
        self, value: str, *, collection_name: str | None = None
    ) -> None:
        allowed = ", ".join(sorted(self.VALID_REVIEW_STATUSES))
        context = f" for collection '{collection_name}'" if collection_name else ""
        raise ValueError(
            f"Invalid review_status{context}: {value!r}. "
            f"review_status must be one of: {allowed}"
        )

    def _validate_source(self, source_type: str, source_name: str) -> None:
        if source_type not in self.VALID_SOURCE_TYPES:
            allowed = ", ".join(sorted(self.VALID_SOURCE_TYPES))
            raise ValueError(f"source_type must be one of: {allowed}")
        if source_type == "reference" and source_name not in self._references():
            raise ValueError(f"Unknown reference source '{source_name}'")
        if source_type == "dataset" and source_name not in self._datasets():
            raise ValueError(f"Unknown dataset source '{source_name}'")
        if (
            source_type == "transform_group"
            and source_name not in self._transform_group_names()
        ):
            raise ValueError(f"Unknown transform_group source '{source_name}'")

    def _validate_roles(self, roles: Sequence[str]) -> list[CollectionRole]:
        if not roles:
            raise ValueError("roles must not be empty")
        invalid = sorted({role for role in roles if role not in self.VALID_ROLES})
        if invalid:
            allowed = ", ".join(sorted(self.VALID_ROLES))
            raise ValueError(f"Invalid collection roles {invalid}; expected: {allowed}")
        return cast(list[CollectionRole], list(dict.fromkeys(roles)))

    def _infer_reference_grain(self, name: str, config: dict[str, Any]) -> str:
        kind = str(config.get("kind") or "").lower()
        if kind == "spatial":
            return "site"
        if self._has_taxonomic_signals(name, config):
            return "taxon"
        if kind == "hierarchical":
            return "hierarchy"
        return "reference"

    def _has_taxonomic_signals(self, name: str, config: dict[str, Any]) -> bool:
        haystack = [name, str(config.get("description") or "")]
        schema = config.get("schema") if isinstance(config.get("schema"), dict) else {}
        fields = schema.get("fields", []) if isinstance(schema, dict) else []
        if isinstance(fields, dict):
            haystack.extend(fields.keys())
        elif isinstance(fields, list):
            haystack.extend(
                str(field.get("name"))
                for field in fields
                if isinstance(field, dict) and field.get("name")
            )
        text = " ".join(haystack).lower()
        return any(
            token in text
            for token in ("taxon", "taxa", "taxonomy", "species", "genus", "family")
        )

    def _collection_metadata(self) -> dict[str, Any]:
        metadata = self.import_config.get("metadata")
        if not isinstance(metadata, dict):
            return {}
        collections = metadata.get("collections")
        return (
            cast(dict[str, Any], collections) if isinstance(collections, dict) else {}
        )

    def _ensure_collection_metadata(self) -> dict[str, Any]:
        metadata = self.import_config.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            self.import_config["metadata"] = metadata
        collections = metadata.get("collections")
        if not isinstance(collections, dict):
            collections = {}
            metadata["collections"] = collections
        return collections

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

    def _transform_group_names(self) -> list[str]:
        names: list[str] = []
        for group in self.transform_config:
            if isinstance(group, dict) and group.get("group_by"):
                names.append(str(group["group_by"]))
        return list(dict.fromkeys(names))
