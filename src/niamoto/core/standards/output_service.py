"""Profile-owned standard output generation."""

from __future__ import annotations

import csv
import json
import math
import os
import re
import shutil
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, cast

from sqlalchemy import text

from niamoto.common.database import Database
from niamoto.common.table_resolver import resolve_entity_table
from niamoto.core.collections import CollectionCatalogService
from niamoto.core.imports.registry import EntityKind, EntityRegistry
from niamoto.core.plugins.exporters.dwc_archive_exporter import (
    DwcArchiveExporter,
    DwcArchiveExporterParams,
)
from niamoto.core.plugins.transformers.formats.niamoto_to_humboldt_event import (
    NiamotoHumboldtEventTransformer,
)
from niamoto.core.standards.models import (
    StandardCompatibilityReport,
    StandardProfileConfig,
    StandardProfileOutput,
    StandardProfileOutputPreviewResult,
    StandardProfileOutputResult,
    StandardProfileOutputType,
    StandardProfileSource,
)
from niamoto.core.standards.validation import StandardProfileValidationService


class StandardProfileOutputService:
    """Generate files owned by a standard publication profile."""

    def __init__(
        self,
        work_dir: str | Path,
        *,
        db_path: str | Path | None = None,
        import_config: dict[str, Any] | None = None,
        transform_config: list[dict[str, Any]] | None = None,
    ) -> None:
        self.work_dir = Path(work_dir)
        self.db_path = Path(db_path) if db_path is not None else None
        self.import_config = import_config or {}
        self.transform_config = transform_config or []
        self.collection_catalog = CollectionCatalogService(
            import_config=self.import_config,
            transform_config=self.transform_config,
        ).list_collections()
        self.validation_service = StandardProfileValidationService(
            import_config=self.import_config,
            transform_config=self.transform_config,
        )

    def execute_profile(
        self,
        profile: StandardProfileConfig,
        *,
        output_type: StandardProfileOutputType | None = None,
        records: Iterable[dict[str, Any]] | None = None,
        draft: bool = False,
    ) -> StandardProfileOutputResult:
        """Generate one configured output for a standard profile."""
        if not profile.enabled:
            raise ValueError(f"Profile '{profile.name}' is disabled")

        output = self._select_output(profile, output_type)
        if draft:
            output = self._draft_output(output, profile)
        validation = self.validation_service.validate(profile)
        if not draft:
            self._ensure_publication_output_allowed(output, validation)
        record_source = self._record_source_for_profile(
            profile, validation.compatibility
        )
        self._reject_unsupported_context_mappings(profile, record_source)
        output_source_grain = self._output_source_grain(
            profile, validation.compatibility, record_source
        )
        metadata = self._build_metadata(
            profile=profile,
            output=output,
            validation_status=validation.status,
            source_grain=output_source_grain,
            records_count=0,
            record_source=record_source
            if not _same_source(profile.source, record_source)
            else None,
            draft=draft,
        )
        source_records = (
            records if records is not None else self._iter_records(record_source)
        )
        mapped_records = self._iter_mapped_records(profile, source_records)

        if output.type == "api_json":
            files, output_path, records_count = self._write_api_json(
                profile, output, mapped_records, metadata
            )
        elif output.type == "dwc_archive":
            files, output_path, records_count = self._write_dwc_archive(
                profile, output, mapped_records
            )
        else:
            files, output_path, records_count = self._write_standard_files(
                profile, output, mapped_records, metadata
            )
        metadata["records_count"] = records_count

        warnings = [
            *validation.compatibility.warnings,
            *(
                issue.message
                for issue in validation.issues
                if issue.severity in {"warning", "recommended"}
            ),
        ]
        errors = [
            issue.message for issue in validation.issues if issue.severity == "critical"
        ]

        return StandardProfileOutputResult(
            profile_name=profile.name,
            standard=profile.standard,
            output_type=output.type,
            status="success",
            validation_status=validation.status,
            source_grain=output_source_grain,
            output_path=str(output_path) if output_path is not None else None,
            files_generated=len(files),
            files=files,
            errors=errors,
            warnings=warnings,
            metadata=metadata,
        )

    def preview_profile(
        self,
        profile: StandardProfileConfig,
        *,
        output_type: StandardProfileOutputType = "api_json",
    ) -> StandardProfileOutputPreviewResult:
        """Build a representative JSON preview without writing output files."""
        if not profile.enabled:
            raise ValueError(f"Profile '{profile.name}' is disabled")

        output = self._select_output(profile, output_type)
        validation = self.validation_service.validate(profile)
        record_source = self._record_source_for_profile(
            profile, validation.compatibility
        )
        self._reject_unsupported_context_mappings(profile, record_source)
        output_source_grain = self._output_source_grain(
            profile, validation.compatibility, record_source
        )
        raw_records = self._load_records(record_source, limit=100)
        if not raw_records:
            raise ValueError(f"No data found for source '{record_source.name}'")

        source_record, mapped_record = self._select_preview_record(profile, raw_records)
        mapped_records = [mapped_record]

        metadata = self._build_metadata(
            profile=profile,
            output=output,
            validation_status=validation.status,
            source_grain=output_source_grain,
            records_count=len(mapped_records),
            record_source=record_source
            if not _same_source(profile.source, record_source)
            else None,
            draft=True,
            sample_basis="representative_record",
            rows_sampled=len(raw_records),
            source_record_id=_record_item_id(source_record, record_source),
        )
        preview: Any
        if output.type == "api_json":
            preview = {"metadata": metadata, "records": mapped_records}
        else:
            preview = mapped_records

        warnings = [
            *validation.compatibility.warnings,
            *(
                issue.message
                for issue in validation.issues
                if issue.severity in {"warning", "recommended"}
            ),
        ]
        errors = [
            issue.message for issue in validation.issues if issue.severity == "critical"
        ]

        return StandardProfileOutputPreviewResult(
            profile_name=profile.name,
            standard=profile.standard,
            output_type=output.type,
            validation_status=validation.status,
            source_grain=output_source_grain,
            item_id=_record_item_id(source_record, record_source),
            preview=_json_safe_value(preview),
            source=cast(
                dict[str, Any],
                _json_safe_value(_preview_source_values(profile, source_record)),
            ),
            warnings=warnings,
            errors=errors,
            metadata=cast(dict[str, Any], _json_safe_value(metadata)),
        )

    def _select_output(
        self,
        profile: StandardProfileConfig,
        output_type: StandardProfileOutputType | None,
    ) -> StandardProfileOutput:
        if output_type is None:
            for output in profile.outputs:
                if output.enabled:
                    return output
            raise ValueError(f"Profile '{profile.name}' has no enabled outputs")

        for output in profile.outputs:
            if output.type != output_type:
                continue
            if not output.enabled:
                raise ValueError(
                    f"Output '{output_type}' is disabled for profile '{profile.name}'"
                )
            return output

        raise ValueError(
            f"Output '{output_type}' is not configured for profile '{profile.name}'"
        )

    def _draft_output(
        self,
        output: StandardProfileOutput,
        profile: StandardProfileConfig,
    ) -> StandardProfileOutput:
        profile_name = _safe_path_segment(profile.name, "profile name")
        draft_params = {
            **output.params,
            "output_dir": f"exports/.draft/profiles/{profile_name}/{output.type}",
        }
        return output.model_copy(update={"params": draft_params})

    def _ensure_publication_output_allowed(
        self,
        output: StandardProfileOutput,
        validation: Any,
    ) -> None:
        if output.type == "api_json":
            return

        critical_count = validation.summary.get("critical", 0)
        if validation.status == "invalid" or critical_count > 0:
            raise ValueError(
                "Publication outputs require a profile without critical validation issues"
            )

    def _record_source_for_profile(
        self,
        profile: StandardProfileConfig,
        compatibility: StandardCompatibilityReport,
    ) -> StandardProfileSource:
        occurrence_dataset = self._occurrence_dataset_from_compatibility(compatibility)
        if profile.standard == "darwin_core_occurrence" and occurrence_dataset:
            return StandardProfileSource(
                type="dataset",
                name=occurrence_dataset,
            )

        return self._backing_source_for_profile_source(profile.source)

    def _occurrence_dataset_from_compatibility(
        self, compatibility: StandardCompatibilityReport
    ) -> str | None:
        for evidence in compatibility.evidence:
            if evidence.kind != "occurrence_relation":
                continue
            occurrence_dataset = evidence.details.get("occurrence_dataset")
            if isinstance(occurrence_dataset, str) and occurrence_dataset:
                return occurrence_dataset
        return None

    def _backing_source_for_profile_source(
        self,
        source: StandardProfileSource,
    ) -> StandardProfileSource:
        if source.type != "collection":
            return source

        for collection in self.collection_catalog.collections:
            if collection.name != source.name:
                continue
            return StandardProfileSource(
                type=collection.source_type,
                name=collection.source_name,
            )

        return source

    def _reject_unsupported_context_mappings(
        self,
        profile: StandardProfileConfig,
        record_source: StandardProfileSource,
    ) -> None:
        if profile.standard != "darwin_core_occurrence":
            return
        if _same_source(profile.source, record_source):
            return

        for term, mapping in profile.mappings.items():
            source = _mapping_source(mapping)
            if source is None or not _is_context_reference(source):
                continue
            raise ValueError(
                f"Context mapping for term '{term}' is not supported by profile output generation yet"
            )

    def _output_source_grain(
        self,
        profile: StandardProfileConfig,
        compatibility: StandardCompatibilityReport,
        record_source: StandardProfileSource,
    ) -> str:
        occurrence_dataset = self._occurrence_dataset_from_compatibility(compatibility)
        if (
            occurrence_dataset
            and record_source.type == "dataset"
            and record_source.name == occurrence_dataset
        ):
            return "occurrence"
        return compatibility.source_grain

    def _load_records(
        self,
        source: StandardProfileSource,
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return list(self._iter_records(source, limit=limit))

    def _iter_records(
        self,
        source: StandardProfileSource,
        *,
        limit: int | None = None,
        batch_size: int = 1000,
    ) -> Iterable[dict[str, Any]]:
        if self.db_path is None or not self.db_path.exists():
            raise ValueError(
                f"Cannot load source '{source.type}:{source.name}': project database was not found"
            )

        database = Database(str(self.db_path), optimize=False, read_only=True)
        try:
            table_name = self._resolve_source_table(database, source)
            if table_name is None:
                raise ValueError(
                    f"Cannot load source '{source.type}:{source.name}': no imported table was found"
                )
            escaped_table = table_name.replace('"', '""')
            limit_clause = ""
            if limit is not None:
                safe_limit = max(1, int(limit))
                limit_clause = f" LIMIT {safe_limit}"
            with database.connection() as connection:
                result = connection.execute(
                    text(f'SELECT * FROM "{escaped_table}"{limit_clause}')
                )
                columns = list(result.keys())
                while rows := result.fetchmany(batch_size):
                    for row in rows:
                        yield dict(zip(columns, row))
        finally:
            database.close_db_session()
            database.engine.dispose()

    def _resolve_source_table(
        self,
        database: Database,
        source: StandardProfileSource,
    ) -> str | None:
        return resolve_entity_table(
            database,
            source.name,
            registry=self._entity_registry(database),
            kind=_entity_kind_for_source(source),
        )

    def _entity_registry(self, database: Database) -> EntityRegistry | None:
        if not database.has_table(EntityRegistry.ENTITIES_TABLE):
            return None
        return EntityRegistry(database)

    def _map_records(
        self,
        profile: StandardProfileConfig,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return list(self._iter_mapped_records(profile, records))

    def _iter_mapped_records(
        self,
        profile: StandardProfileConfig,
        records: Iterable[dict[str, Any]],
    ) -> Iterable[dict[str, Any]]:
        if profile.standard == "humboldt_event":
            transformer = NiamotoHumboldtEventTransformer(cast(Any, None))
            for record in records:
                yield transformer.transform(record, {"mapping": profile.mappings})
            return

        for index, record in enumerate(records, start=1):
            yield {
                term: _resolve_mapping_value(record, mapping, index=index)
                for term, mapping in profile.mappings.items()
            }

    def _select_preview_record(
        self,
        profile: StandardProfileConfig,
        records: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Choose the candidate with the most populated mapped standard terms."""
        best_source = records[0]
        best_mapped = self._map_records(profile, [best_source])[0]
        best_score = _score_preview_record(best_mapped)

        for source_record in records[1:]:
            mapped_record = self._map_records(profile, [source_record])[0]
            score = _score_preview_record(mapped_record)
            if score > best_score:
                best_source = source_record
                best_mapped = mapped_record
                best_score = score

        return best_source, best_mapped

    def _build_metadata(
        self,
        *,
        profile: StandardProfileConfig,
        output: StandardProfileOutput,
        validation_status: str,
        source_grain: str,
        records_count: int,
        record_source: StandardProfileSource | None = None,
        draft: bool = False,
        sample_basis: str | None = None,
        rows_sampled: int | None = None,
        source_record_id: Any | None = None,
    ) -> dict[str, Any]:
        metadata = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "profile_name": profile.name,
            "standard": profile.standard,
            "output_type": output.type,
            "source": profile.source.model_dump(mode="json"),
            "source_grain": source_grain,
            "validation_status": validation_status,
            "conformant": validation_status == "conformant",
            "records_count": records_count,
            "draft": draft,
            "publication_output": not draft,
        }
        if record_source is not None:
            metadata["record_source"] = record_source.model_dump(mode="json")
        if sample_basis is not None:
            metadata["sample_basis"] = sample_basis
        if rows_sampled is not None:
            metadata["rows_sampled"] = rows_sampled
        if source_record_id is not None:
            metadata["source_record_id"] = source_record_id
        if draft:
            metadata["retention_policy"] = {
                "type": "manual_cleanup",
                "location": "exports/.draft/profiles",
            }
        return metadata

    def _write_api_json(
        self,
        profile: StandardProfileConfig,
        output: StandardProfileOutput,
        records: Iterable[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> tuple[list[Path], Path, int]:
        output_dir = self._resolve_output_dir(output, profile)
        output_dir.mkdir(parents=True, exist_ok=True)
        profile_filename = _safe_path_segment(profile.name, "profile name")
        output_path = output_dir / f"{profile_filename}.json"
        records_tmp_path = output_path.with_name(f".{output_path.stem}.records.tmp")
        output_tmp_path = output_path.with_name(f".{output_path.name}.tmp")
        records_count = 0
        try:
            with records_tmp_path.open("w", encoding="utf-8") as handle:
                handle.write("[")
                for record in records:
                    if records_count > 0:
                        handle.write(",")
                    handle.write("\n  ")
                    json.dump(record, handle, ensure_ascii=False, default=str)
                    records_count += 1
                if records_count > 0:
                    handle.write("\n")
                handle.write("]")

            metadata["records_count"] = records_count
            with output_tmp_path.open("w", encoding="utf-8") as handle:
                handle.write('{\n  "metadata": ')
                json.dump(metadata, handle, ensure_ascii=False, indent=2, default=str)
                handle.write(',\n  "records": ')
                with records_tmp_path.open("r", encoding="utf-8") as records_handle:
                    while chunk := records_handle.read(1024 * 1024):
                        handle.write(chunk)
                handle.write("\n}\n")
            os.replace(output_tmp_path, output_path)
        finally:
            for tmp_path in (records_tmp_path, output_tmp_path):
                if tmp_path.exists():
                    tmp_path.unlink()

        return [output_path], output_path, records_count

    def _write_dwc_archive(
        self,
        profile: StandardProfileConfig,
        output: StandardProfileOutput,
        records: Iterable[dict[str, Any]],
    ) -> tuple[list[Path], Path, int]:
        if profile.standard != "darwin_core_occurrence":
            raise ValueError("DwC-A output requires a Darwin Core Occurrence profile")

        mapped_records = list(records)
        output_dir = self._resolve_output_dir(output, profile)
        params_payload = {**output.params, "output_dir": str(output_dir)}
        params = DwcArchiveExporterParams.model_validate(params_payload)
        output_dir.mkdir(parents=True, exist_ok=True)

        staging_dir = output_dir / f".{params.archive_name}.tmp"
        if staging_dir.exists():
            if staging_dir.is_dir():
                shutil.rmtree(staging_dir)
            else:
                staging_dir.unlink()
        staging_dir.mkdir(parents=True)

        exporter = DwcArchiveExporter(db=cast(Any, None))
        try:
            staging_params = params.model_copy(update={"output_dir": str(staging_dir)})
            staging_files = exporter.generate_archive_from_occurrences(
                mapped_records,
                staging_dir,
                staging_params,
            )
            staging_archive_path = staging_dir / params.archive_name
            if not staging_files or not staging_archive_path.exists():
                raise ValueError("DwC-A output generated no archive files")

            final_files: list[Path] = []
            for staging_file in staging_files:
                final_path = output_dir / staging_file.name
                os.replace(staging_file, final_path)
                final_files.append(final_path)

            archive_path = output_dir / params.archive_name
            return final_files, archive_path, len(mapped_records)
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)

    def _write_standard_files(
        self,
        profile: StandardProfileConfig,
        output: StandardProfileOutput,
        records: Iterable[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> tuple[list[Path], Path, int]:
        if profile.standard != "humboldt_event":
            raise ValueError(
                "Standard files output currently supports Humboldt/Event profiles"
            )

        output_dir = self._resolve_output_dir(output, profile)
        output_dir.mkdir(parents=True, exist_ok=True)
        event_path = output_dir / "event.csv"
        terms = sorted(profile.mappings.keys())

        event_tmp_path = event_path.with_name(f".{event_path.name}.tmp")
        records_count = 0
        try:
            with event_tmp_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=terms, extrasaction="ignore")
                writer.writeheader()
                for record in records:
                    records_count += 1
                    writer.writerow(
                        {
                            term: "" if record.get(term) is None else record.get(term)
                            for term in terms
                        }
                    )
            os.replace(event_tmp_path, event_path)
        finally:
            if event_tmp_path.exists():
                event_tmp_path.unlink()

        metadata_path = output_dir / "metadata.json"
        metadata["records_count"] = records_count
        _atomic_write_text(
            metadata_path,
            json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
        )
        return [event_path, metadata_path], event_path, records_count

    def _resolve_output_dir(
        self,
        output: StandardProfileOutput,
        profile: StandardProfileConfig,
    ) -> Path:
        profile_name = _safe_path_segment(profile.name, "profile name")
        output_dir = output.params.get(
            "output_dir", f"exports/profiles/{profile_name}/{output.type}"
        )
        raw_path = str(output_dir).strip()
        if not raw_path:
            raise ValueError("output_dir must not be empty")
        path = Path(raw_path)
        if path.is_absolute():
            raise ValueError("output_dir must be relative to the project directory")
        if ".." in path.parts:
            raise ValueError("output_dir must not contain parent directory segments")

        work_dir = self.work_dir.resolve()
        resolved = (work_dir / path).resolve()
        if not resolved.is_relative_to(work_dir):
            raise ValueError("output_dir must stay within the project directory")
        return resolved


def _resolve_mapping_value(
    record: dict[str, Any],
    mapping: Any,
    *,
    index: int,
) -> Any:
    if isinstance(mapping, str):
        return _read_path(record, _normalize_source_path(mapping))

    if not isinstance(mapping, dict):
        raise ValueError(f"Unsupported mapping shape: {mapping!r}")

    if mapping.get("source"):
        return _read_path(record, _normalize_source_path(str(mapping["source"])))

    if mapping.get("generator"):
        return _generate_value(
            str(mapping["generator"]), mapping.get("params") or {}, record, index
        )

    raise ValueError(f"Unsupported mapping shape: {mapping!r}")


def _mapping_source(mapping: Any) -> str | None:
    if isinstance(mapping, str):
        return mapping
    if isinstance(mapping, dict) and mapping.get("source"):
        return str(mapping["source"])
    return None


def _preview_source_values(
    profile: StandardProfileConfig,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Return only source values that participate in the preview mapping."""
    values: dict[str, Any] = {}
    for reference in _mapping_source_references(profile.mappings.values()):
        path = _normalize_source_path(reference)
        if not path or path in values:
            continue
        values[path] = _read_path(record, path)
    return values


def _mapping_source_references(mappings: Iterable[Any]) -> list[str]:
    references: list[str] = []
    for mapping in mappings:
        if isinstance(mapping, str):
            references.append(mapping)
            continue
        if not isinstance(mapping, dict):
            continue
        source = mapping.get("source")
        if isinstance(source, str):
            references.append(source)
        params = mapping.get("params")
        if mapping.get("generator") and isinstance(params, dict):
            references.extend(_generator_param_source_references(params))
    return references


def _generator_param_source_references(params: dict[str, Any]) -> list[str]:
    references: list[str] = []
    for key in ("source", "source_field", "source_list"):
        value = params.get(key)
        if isinstance(value, str):
            references.append(value)

    fields = params.get("fields")
    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, str):
                references.append(field)
            elif isinstance(field, dict) and isinstance(field.get("field"), str):
                references.append(str(field["field"]))

    return references


def _is_context_reference(source: str) -> bool:
    return source.startswith("@") and not source.startswith("@source.")


def _normalize_source_path(source: str) -> str:
    if source.startswith("@source."):
        return source.removeprefix("@source.")
    if source.startswith("@"):
        path = source.removeprefix("@")
        if "." in path:
            return path.split(".", 1)[1]
        return path
    return source


def _read_path(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _generate_value(
    generator: str,
    params: dict[str, Any],
    record: dict[str, Any],
    index: int,
) -> Any:
    if generator == "constant":
        return params.get("value")
    if generator == "current_date":
        return date.today().isoformat()
    if generator == "unique_occurrence_id":
        source = params.get("source") or params.get("source_field")
        if isinstance(source, str) and source.strip():
            source_value = _read_path(record, _normalize_source_path(source))
            if source_value not in (None, ""):
                prefix = params.get("prefix")
                return f"{prefix}{source_value}" if prefix is not None else source_value
        prefix = str(params.get("prefix", "occurrence_"))
        return f"{prefix}{index}"
    if generator == "extract_geometry_coordinate":
        return _extract_geometry_coordinate(record, params)
    if generator in {"format_measurements", "dynamic_properties"}:
        return _format_dynamic_properties(record, params)
    raise ValueError(f"Unknown generator '{generator}'")


def _extract_geometry_coordinate(
    record: dict[str, Any],
    params: dict[str, Any],
) -> float | None:
    source = params.get("source") or params.get("source_field")
    if not source:
        return None
    value = _read_path(record, _normalize_source_path(str(source)))
    coordinate = str(params.get("coordinate") or params.get("axis") or "").lower()
    parsed = _parse_point_geometry(value)
    if parsed is None:
        return None
    longitude, latitude = parsed
    if coordinate in {"latitude", "lat", "y"}:
        return latitude
    if coordinate in {"longitude", "lon", "lng", "x"}:
        return longitude
    return None


def _parse_point_geometry(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        coordinates = value.get("coordinates")
        if (
            isinstance(coordinates, list)
            and len(coordinates) >= 2
            and _is_number(coordinates[0])
            and _is_number(coordinates[1])
        ):
            return float(coordinates[0]), float(coordinates[1])
        return None
    text_value = str(value).strip()
    match = re.search(
        r"POINT\s*(?:Z|M|ZM)?\s*\(\s*([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)",
        text_value,
        flags=re.IGNORECASE,
    )
    if match:
        return float(match.group(1)), float(match.group(2))
    return None


def _format_dynamic_properties(
    record: dict[str, Any],
    params: dict[str, Any],
) -> str | None:
    raw_fields = params.get("fields")
    if not isinstance(raw_fields, list):
        return None
    properties: dict[str, Any] = {}
    for raw_field in raw_fields:
        field = str(raw_field)
        value = _read_path(record, _normalize_source_path(field))
        if value is not None:
            properties[field] = value
    if not properties:
        return None
    return json.dumps(properties, ensure_ascii=False, default=str, sort_keys=True)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _score_preview_record(record: dict[str, Any]) -> int:
    return sum(1 for value in record.values() if _value_is_populated(value))


def _value_is_populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list)):
        return bool(value)
    return True


def _record_item_id(record: dict[str, Any], source: StandardProfileSource) -> Any:
    source_id_key = f"{source.name}_id"
    for key in ("id", source_id_key, "entity_id", "record_id"):
        value = record.get(key)
        if value is not None:
            return value
    return None


def _json_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return float(value) if value.is_finite() else None
    if isinstance(value, bytes):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe_value(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe_value(nested) for nested in value]
    return str(value)


def _safe_path_segment(value: str, label: str) -> str:
    segment = value.strip()
    if not segment:
        raise ValueError(f"{label} must not be empty")
    if segment in {".", ".."} or "/" in segment or "\\" in segment:
        raise ValueError(f"{label} must be a safe path segment")
    return segment


def _entity_kind_for_source(source: StandardProfileSource) -> str | None:
    if source.type == "dataset":
        return EntityKind.DATASET.value
    if source.type == "reference":
        return EntityKind.REFERENCE.value
    return None


def _atomic_write_text(path: Path, content: str) -> None:
    tmp_path = path.with_name(f".{path.name}.tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _same_source(
    left: StandardProfileSource,
    right: StandardProfileSource,
) -> bool:
    return left.type == right.type and left.name == right.name
