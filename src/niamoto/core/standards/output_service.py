"""Profile-owned standard output generation."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, cast

from sqlalchemy import text

from niamoto.common.database import Database
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
    ) -> StandardProfileOutputResult:
        """Generate one configured output for a standard profile."""
        if not profile.enabled:
            raise ValueError(f"Profile '{profile.name}' is disabled")

        output = self._select_output(profile, output_type)
        validation = self.validation_service.validate(profile)
        record_source = self._record_source_for_profile(
            profile, validation.compatibility
        )
        output_source_grain = self._output_source_grain(
            profile, validation.compatibility, record_source
        )
        raw_records = (
            list(records) if records is not None else self._load_records(record_source)
        )
        mapped_records = self._map_records(profile, raw_records)

        metadata = self._build_metadata(
            profile=profile,
            output=output,
            validation_status=validation.status,
            source_grain=output_source_grain,
            records_count=len(mapped_records),
            record_source=record_source
            if not _same_source(profile.source, record_source)
            else None,
        )

        if output.type == "api_json":
            files, output_path = self._write_api_json(
                profile, output, mapped_records, metadata
            )
        elif output.type == "dwc_archive":
            files, output_path = self._write_dwc_archive(
                profile, output, mapped_records
            )
        else:
            files, output_path = self._write_standard_files(
                profile, output, mapped_records, metadata
            )

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

    def _record_source_for_profile(
        self,
        profile: StandardProfileConfig,
        compatibility: StandardCompatibilityReport,
    ) -> StandardProfileSource:
        if profile.standard != "darwin_core_occurrence":
            return profile.source

        for evidence in compatibility.evidence:
            if evidence.kind != "occurrence_relation":
                continue
            occurrence_dataset = evidence.details.get("occurrence_dataset")
            if isinstance(occurrence_dataset, str) and occurrence_dataset:
                return StandardProfileSource(
                    type="dataset",
                    name=occurrence_dataset,
                )

        return profile.source

    def _output_source_grain(
        self,
        profile: StandardProfileConfig,
        compatibility: StandardCompatibilityReport,
        record_source: StandardProfileSource,
    ) -> str:
        if not _same_source(profile.source, record_source):
            return "occurrence"
        return compatibility.source_grain

    def _load_records(self, source: StandardProfileSource) -> list[dict[str, Any]]:
        if self.db_path is None or not self.db_path.exists():
            return []

        database = Database(str(self.db_path), optimize=False, read_only=True)
        try:
            table_name = self._resolve_source_table(database, source)
            if table_name is None:
                return []
            escaped_table = table_name.replace('"', '""')
            with database.connection() as connection:
                result = connection.execute(text(f'SELECT * FROM "{escaped_table}"'))
                columns = list(result.keys())
                return [dict(zip(columns, row)) for row in result.fetchall()]
        finally:
            database.close_db_session()
            database.engine.dispose()

    def _resolve_source_table(
        self,
        database: Database,
        source: StandardProfileSource,
    ) -> str | None:
        for candidate in self._source_table_candidates(source):
            if database.has_table(candidate):
                return candidate
        return None

    def _source_table_candidates(self, source: StandardProfileSource) -> list[str]:
        if source.type == "dataset":
            return [f"dataset_{source.name}", source.name]
        if source.type in {"collection", "reference"}:
            return [f"entity_{source.name}", f"reference_{source.name}", source.name]
        return [source.name]

    def _map_records(
        self,
        profile: StandardProfileConfig,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if profile.standard == "humboldt_event":
            transformer = NiamotoHumboldtEventTransformer(cast(Any, None))
            return [
                transformer.transform(record, {"mapping": profile.mappings})
                for record in records
            ]

        return [
            {
                term: _resolve_mapping_value(record, mapping, index=index)
                for term, mapping in profile.mappings.items()
            }
            for index, record in enumerate(records, start=1)
        ]

    def _build_metadata(
        self,
        *,
        profile: StandardProfileConfig,
        output: StandardProfileOutput,
        validation_status: str,
        source_grain: str,
        records_count: int,
        record_source: StandardProfileSource | None = None,
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
        }
        if record_source is not None:
            metadata["record_source"] = record_source.model_dump(mode="json")
        return metadata

    def _write_api_json(
        self,
        profile: StandardProfileConfig,
        output: StandardProfileOutput,
        records: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> tuple[list[Path], Path]:
        output_dir = self._resolve_output_dir(output, profile)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{profile.name}.json"
        output_path.write_text(
            json.dumps(
                {"metadata": metadata, "records": records},
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return [output_path], output_path

    def _write_dwc_archive(
        self,
        profile: StandardProfileConfig,
        output: StandardProfileOutput,
        records: list[dict[str, Any]],
    ) -> tuple[list[Path], Path]:
        if profile.standard != "darwin_core_occurrence":
            raise ValueError("DwC-A output requires a Darwin Core Occurrence profile")

        output_dir = self._resolve_output_dir(output, profile)
        params_payload = {**output.params, "output_dir": str(output_dir)}
        params = DwcArchiveExporterParams.model_validate(params_payload)
        exporter = DwcArchiveExporter(db=cast(Any, None))
        files = exporter.generate_archive_from_occurrences(records, output_dir, params)
        return files, output_dir / params.archive_name

    def _write_standard_files(
        self,
        profile: StandardProfileConfig,
        output: StandardProfileOutput,
        records: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> tuple[list[Path], Path]:
        if profile.standard != "humboldt_event":
            raise ValueError(
                "Standard files output currently supports Humboldt/Event profiles"
            )

        output_dir = self._resolve_output_dir(output, profile)
        output_dir.mkdir(parents=True, exist_ok=True)
        event_path = output_dir / "event.csv"
        terms = sorted({term for record in records for term in record.keys()})
        if not terms:
            terms = sorted(profile.mappings.keys())

        with event_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=terms, extrasaction="ignore")
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        term: "" if record.get(term) is None else record.get(term)
                        for term in terms
                    }
                )

        metadata_path = output_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return [event_path, metadata_path], event_path

    def _resolve_output_dir(
        self,
        output: StandardProfileOutput,
        profile: StandardProfileConfig,
    ) -> Path:
        output_dir = output.params.get(
            "output_dir", f"exports/profiles/{profile.name}/{output.type}"
        )
        path = Path(str(output_dir))
        if path.is_absolute():
            return path
        return self.work_dir / path


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
            str(mapping["generator"]), mapping.get("params") or {}, index
        )

    raise ValueError(f"Unsupported mapping shape: {mapping!r}")


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


def _generate_value(generator: str, params: dict[str, Any], index: int) -> Any:
    if generator == "constant":
        return params.get("value")
    if generator == "current_date":
        return date.today().isoformat()
    if generator == "unique_occurrence_id":
        prefix = str(params.get("prefix", "occurrence_"))
        return f"{prefix}{index}"
    raise ValueError(f"Unknown generator '{generator}'")


def _same_source(
    left: StandardProfileSource,
    right: StandardProfileSource,
) -> bool:
    return left.type == right.type and left.name == right.name
