"""Persistence helpers for standard publication profiles."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from niamoto.core.standards.models import (
    LegacyStandardProfileHint,
    StandardProfileConfig,
    StandardProfileSource,
)


class StandardProfileStore:
    """Manage ``standard_profiles`` entries in export.yml."""

    def __init__(
        self,
        export_config: dict[str, Any],
        *,
        known_sources: list[dict[str, str]] | None = None,
    ) -> None:
        self.export_config = export_config
        self.known_sources = {
            (source["type"], source["name"])
            for source in known_sources or []
            if isinstance(source, dict) and source.get("type") and source.get("name")
        }

    def list_profiles(self) -> list[StandardProfileConfig]:
        """Return all configured standard profiles."""
        return [
            StandardProfileConfig.model_validate(profile)
            for profile in self._raw_profiles()
            if isinstance(profile, dict)
        ]

    def get_profile(self, name: str) -> StandardProfileConfig:
        """Return one configured standard profile by name."""
        for profile in self.list_profiles():
            if profile.name == name:
                return profile
        raise KeyError(f"Standard profile '{name}' not found")

    def create_profile(self, payload: dict[str, Any]) -> StandardProfileConfig:
        """Create a new standard profile."""
        profile = self._validate_profile(payload)
        if any(existing.name == profile.name for existing in self.list_profiles()):
            raise ValueError(f"Standard profile '{profile.name}' already exists")

        profiles = self._ensure_profiles()
        profiles.append(profile.model_dump(mode="json"))
        return profile

    def update_profile(
        self, name: str, updates: dict[str, Any]
    ) -> StandardProfileConfig:
        """Update an existing standard profile."""
        profiles = self._ensure_profiles()
        for index, raw_profile in enumerate(profiles):
            if not isinstance(raw_profile, dict) or raw_profile.get("name") != name:
                continue
            merged = {**raw_profile, **updates, "name": name}
            profile = self._validate_profile(merged)
            profiles[index] = profile.model_dump(mode="json")
            return profile
        raise KeyError(f"Standard profile '{name}' not found")

    def delete_profile(self, name: str) -> None:
        """Delete a standard profile."""
        profiles = self._ensure_profiles()
        for index, raw_profile in enumerate(profiles):
            if isinstance(raw_profile, dict) and raw_profile.get("name") == name:
                profiles.pop(index)
                return
        raise KeyError(f"Standard profile '{name}' not found")

    def list_legacy_hints(self) -> list[dict[str, Any]]:
        """Return legacy Darwin Core API targets without mutating export.yml."""
        hints: list[LegacyStandardProfileHint] = []
        for export_entry in self.export_config.get("exports", []) or []:
            if not isinstance(export_entry, dict):
                continue
            if not self._is_legacy_dwc_occurrence_target(export_entry):
                continue
            hints.append(
                LegacyStandardProfileHint(
                    export_name=export_entry.get("name", "dwc_occurrence_json"),
                    standard="darwin_core_occurrence",
                    message=(
                        "Legacy JSON API target can be reviewed as a "
                        "Darwin Core Occurrence profile."
                    ),
                    source=self._legacy_source(export_entry),
                )
            )
        return [hint.model_dump(mode="json") for hint in hints]

    def _validate_profile(self, payload: dict[str, Any]) -> StandardProfileConfig:
        try:
            profile = StandardProfileConfig.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        self._validate_source(profile.source)
        if profile.context is not None:
            self._validate_source(profile.context)
        return profile

    def _validate_source(self, source: StandardProfileSource) -> None:
        if not self.known_sources:
            return
        source_key = (source.type, source.name)
        if source_key not in self.known_sources:
            raise ValueError(f"Unknown {source.type} source '{source.name}'")

    def _is_legacy_dwc_occurrence_target(self, export_entry: dict[str, Any]) -> bool:
        if export_entry.get("exporter") != "json_api_exporter":
            return False
        if export_entry.get("name") == "dwc_occurrence_json":
            return True
        for group in export_entry.get("groups", []) or []:
            if (
                isinstance(group, dict)
                and group.get("transformer_plugin") == "niamoto_to_dwc_occurrence"
            ):
                return True
        return False

    def _legacy_source(
        self, export_entry: dict[str, Any]
    ) -> StandardProfileSource | None:
        for group in export_entry.get("groups", []) or []:
            if not isinstance(group, dict):
                continue
            group_by = group.get("group_by")
            if isinstance(group_by, str) and group_by:
                return StandardProfileSource(type="collection", name=group_by)
        return None

    def _raw_profiles(self) -> list[Any]:
        profiles = self.export_config.get("standard_profiles")
        return profiles if isinstance(profiles, list) else []

    def _ensure_profiles(self) -> list[Any]:
        profiles = self.export_config.get("standard_profiles")
        if not isinstance(profiles, list):
            profiles = []
            self.export_config["standard_profiles"] = profiles
        return profiles
