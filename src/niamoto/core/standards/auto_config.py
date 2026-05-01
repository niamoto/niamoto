"""Reviewable auto-configuration for standard publication profiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import text
from unidecode import unidecode

from niamoto.common.database import Database
from niamoto.core.imports.ml.alias_registry import AliasRegistry
from niamoto.core.imports.ml.classifier import ColumnClassifier
from niamoto.core.standards.compatibility import StandardCompatibilityService
from niamoto.core.standards.models import (
    StandardProfileConfig,
    StandardProfileOutput,
    StandardProfileSource,
    StandardProfileType,
)
from niamoto.core.standards.output_service import StandardProfileOutputService

AutoConfigTermStatus = Literal["mapped", "unresolved"]

DWC_TERM_ALIASES: dict[str, set[str]] = {
    "occurrenceID": {
        "id",
        "occurrenceid",
        "occurrence_id",
        "occurrence_code",
        "recordid",
        "record_id",
        "gbifid",
        "gbif_id",
    },
    "scientificName": {
        "scientificname",
        "scientific_name",
        "taxonname",
        "taxon_name",
        "taxaname",
        "taxa_name",
        "taxonref",
        "full_name",
    },
    "eventDate": {
        "eventdate",
        "event_date",
        "observationdate",
        "observation_date",
        "date_obs",
        "date",
    },
    "decimalLatitude": {
        "decimallatitude",
        "decimal_latitude",
        "latitude",
        "lat",
        "y",
    },
    "decimalLongitude": {
        "decimallongitude",
        "decimal_longitude",
        "longitude",
        "long",
        "lon",
        "lng",
        "x",
    },
    "basisOfRecord": {
        "basisofrecord",
        "basis_of_record",
        "record_basis",
    },
    "country": {"country", "pays"},
    "countryCode": {"countrycode", "country_code", "iso_country", "iso2"},
    "family": {"family", "family_name", "famille"},
    "genus": {"genus", "genus_name", "genre"},
    "specificEpithet": {"specificepithet", "specific_epithet", "species"},
    "infraspecificEpithet": {
        "infraspecificepithet",
        "infraspecific_epithet",
        "infra",
        "subspecies",
    },
    "locality": {"locality", "localite", "location", "site", "station"},
    "locationID": {"locationid", "location_id", "plot", "plot_name", "plot_id"},
    "month": {"month", "month_obs", "mois", "mois_obs"},
    "recordedBy": {"recordedby", "recorded_by", "observer", "collector"},
    "catalogNumber": {"catalognumber", "catalog_number", "collection_code"},
    "institutionCode": {"institutioncode", "institution_code", "institution"},
    "collectionCode": {"collectioncode", "collection_code", "collection"},
    "taxonID": {"taxonid", "taxon_id", "tax_id"},
    "verbatimElevation": {"elevation", "altitude", "elev", "alt"},
    "year": {"year", "annee"},
}

CONCEPT_TO_DWC_TERM: dict[str, str] = {
    "identifier.record": "occurrenceID",
    "identifier.plot": "locationID",
    "identifier.taxon": "taxonID",
    "identifier.collection": "collectionCode",
    "identifier.institution": "institutionCode",
    "taxonomy.species": "scientificName",
    "taxonomy.name": "scientificName",
    "taxonomy.family": "family",
    "taxonomy.genus": "genus",
    "event.date": "eventDate",
    "event.year": "year",
    "location.latitude": "decimalLatitude",
    "location.longitude": "decimalLongitude",
    "location.locality": "locality",
    "location.country": "country",
    "location.elevation": "verbatimElevation",
    "category.basis": "basisOfRecord",
    "text.observer": "recordedBy",
}

DWC_REVIEW_TERMS = [
    "occurrenceID",
    "scientificName",
    "decimalLatitude",
    "decimalLongitude",
    "eventDate",
    "basisOfRecord",
]

DWC_TERM_ORDER = [
    "occurrenceID",
    "scientificName",
    "taxonID",
    "decimalLatitude",
    "decimalLongitude",
    "eventDate",
    "month",
    "year",
    "basisOfRecord",
    "family",
    "genus",
    "specificEpithet",
    "infraspecificEpithet",
    "locality",
    "locationID",
    "country",
    "countryCode",
    "recordedBy",
    "catalogNumber",
    "institutionCode",
    "collectionCode",
    "verbatimElevation",
    "dynamicProperties",
    "modified",
]

DYNAMIC_PROPERTY_COLUMN_ALIASES = {
    "dbh",
    "diameter",
    "diameter_at_breast_height",
    "height",
    "tree_height",
    "strata",
    "flower",
    "fruit",
    "bark_thickness",
    "leaf_area",
    "leaf_ldmc",
    "leaf_sla",
    "leaf_thickness",
    "wood_density",
    "rainfall",
    "holdridge",
    "in_forest",
    "in_um",
}


class StandardProfileAutoConfigTerm(BaseModel):
    """One proposed or unresolved standard term."""

    term: str
    status: AutoConfigTermStatus
    mapping: dict[str, Any] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source_column: str | None = None
    evidence: list[str] = Field(default_factory=list)


class StandardProfileAutoConfigResult(BaseModel):
    """Reviewable profile proposal returned by auto-configuration."""

    profile: StandardProfileConfig
    terms: list[StandardProfileAutoConfigTerm]
    unresolved: list[str]
    notes: list[str]
    record_source: StandardProfileSource | None = None
    rows_sampled: int = 0
    columns_inspected: int = 0


class StandardProfileSourceField(BaseModel):
    """One source field available for manual standard term mapping."""

    name: str
    type: str | None = None


class StandardProfileSourceFieldsResult(BaseModel):
    """Fields available for the record source used by a standard profile."""

    source: StandardProfileSource
    record_source: StandardProfileSource
    fields: list[StandardProfileSourceField]
    total: int


@dataclass(frozen=True)
class _TermCandidate:
    term: str
    column: str
    confidence: float
    evidence: str


class StandardProfileAutoConfigService:
    """Infer a draft standard profile from imported columns and labels."""

    def __init__(
        self,
        work_dir: str | Path,
        *,
        db_path: str | Path | None = None,
        import_config: dict[str, Any] | None = None,
        transform_config: list[dict[str, Any]] | None = None,
        enable_ml: bool = False,
    ) -> None:
        self.work_dir = Path(work_dir)
        self.db_path = Path(db_path) if db_path is not None else None
        self.import_config = import_config or {}
        self.transform_config = transform_config or []
        self.output_service = StandardProfileOutputService(
            self.work_dir,
            db_path=self.db_path,
            import_config=self.import_config,
            transform_config=self.transform_config,
        )
        self.compatibility_service = StandardCompatibilityService(
            import_config=self.import_config,
            transform_config=self.transform_config,
        )
        self.alias_registry = _safe_alias_registry()
        self.column_classifier = _safe_column_classifier() if enable_ml else None

    def propose(
        self,
        *,
        name: str | None,
        standard: StandardProfileType,
        source: StandardProfileSource,
        target_grain: str | None = None,
    ) -> StandardProfileAutoConfigResult:
        """Build a reviewable standard profile proposal without persisting it."""
        profile_name = _safe_profile_name(
            name or f"{_standard_prefix(standard)}_{source.name}"
        )
        profile = StandardProfileConfig(
            name=profile_name,
            enabled=True,
            standard=standard,
            target_grain=target_grain or _default_target_grain(standard),
            source=source,
            mappings={},
            outputs=_default_outputs(profile_name, standard),
            validation_status="draft",
            metadata={},
        )

        if standard == "darwin_core_occurrence":
            return self._propose_darwin_core(profile)
        return self._propose_humboldt_event(profile)

    def source_fields(
        self,
        *,
        standard: StandardProfileType,
        source: StandardProfileSource,
        target_grain: str | None = None,
    ) -> StandardProfileSourceFieldsResult:
        """Return inspected source fields for the effective profile record source."""
        profile = StandardProfileConfig(
            name="_source_fields",
            enabled=True,
            standard=standard,
            target_grain=target_grain or _default_target_grain(standard),
            source=source,
            mappings={},
            outputs=[],
            validation_status="draft",
            metadata={},
        )
        notes: list[str] = []
        record_source = self._record_source_for_profile(profile, notes)
        _records, loaded_columns = self._load_record_sample(record_source, notes)
        columns = loaded_columns or self._schema_columns(record_source)
        fields = [StandardProfileSourceField(name=column) for column in columns]
        return StandardProfileSourceFieldsResult(
            source=source,
            record_source=record_source,
            fields=fields,
            total=len(fields),
        )

    def _propose_darwin_core(
        self,
        profile: StandardProfileConfig,
    ) -> StandardProfileAutoConfigResult:
        notes: list[str] = []
        record_source = self._record_source_for_profile(profile, notes)
        if record_source != profile.source:
            notes.append(
                f"Output rows will be read from {record_source.type}:{record_source.name} "
                f"because the selected source is related to occurrence data."
            )

        records, loaded_columns = self._load_record_sample(record_source, notes)
        columns = loaded_columns or self._schema_columns(record_source)
        if not columns:
            notes.append(
                "No imported columns were available; only safe generator mappings were proposed."
            )

        mapped_terms = self._infer_darwin_core_terms(columns, records)
        self._add_geometry_coordinate_terms(mapped_terms, columns, records)
        self._add_basis_of_record_term(mapped_terms)
        self._add_dynamic_properties_term(mapped_terms, columns)
        if "occurrenceID" not in mapped_terms:
            mapped_terms["occurrenceID"] = StandardProfileAutoConfigTerm(
                term="occurrenceID",
                status="mapped",
                mapping={
                    "generator": "unique_occurrence_id",
                    "params": {
                        "prefix": f"{profile.name}-",
                        "source_field": _preferred_identifier_column(columns),
                    },
                },
                confidence=0.72,
                evidence=[
                    "Generated because no explicit occurrence identifier was found."
                ],
            )

        mapped_terms["modified"] = StandardProfileAutoConfigTerm(
            term="modified",
            status="mapped",
            mapping={"generator": "current_date"},
            confidence=0.9,
            evidence=["Generated from the current date at export time."],
        )

        unresolved = [term for term in DWC_REVIEW_TERMS if term not in mapped_terms]
        terms = _ordered_terms(mapped_terms, unresolved)
        proposal = profile.model_copy(
            update={
                "mappings": {
                    term.term: term.mapping
                    for term in terms
                    if term.status == "mapped" and term.mapping is not None
                },
                "metadata": {
                    "auto_config": {
                        "record_source": record_source.model_dump(mode="json"),
                        "rows_sampled": len(records),
                        "unresolved": unresolved,
                    }
                },
            }
        )
        notes.append(
            f"Mapped {sum(1 for term in terms if term.status == 'mapped')} Darwin Core term(s)."
        )
        if unresolved:
            notes.append(
                "Review unresolved recommended terms before generating publication files."
            )

        return StandardProfileAutoConfigResult(
            profile=proposal,
            terms=terms,
            unresolved=unresolved,
            notes=notes,
            record_source=record_source,
            rows_sampled=len(records),
            columns_inspected=len(columns),
        )

    def _propose_humboldt_event(
        self,
        profile: StandardProfileConfig,
    ) -> StandardProfileAutoConfigResult:
        records, loaded_columns = self._load_record_sample(profile.source, [])
        columns = loaded_columns or self._schema_columns(profile.source)
        event_id_column = _best_direct_column(columns, {"eventid", "event_id", "id"})
        mapping = (
            {"source": event_id_column}
            if event_id_column
            else {
                "generator": "constant",
                "params": {"value": profile.name},
            }
        )
        term = StandardProfileAutoConfigTerm(
            term="eventID",
            status="mapped",
            mapping=mapping,
            confidence=0.8 if event_id_column else 0.55,
            source_column=event_id_column,
            evidence=[
                "Mapped from an event identifier column."
                if event_id_column
                else "Generated as a placeholder event identifier."
            ],
        )
        proposal = profile.model_copy(
            update={
                "mappings": {"eventID": mapping},
                "metadata": {
                    "auto_config": {
                        "record_source": profile.source.model_dump(mode="json"),
                        "rows_sampled": len(records),
                        "unresolved": ["eventDate", "samplingProtocol", "locationID"],
                    }
                },
            }
        )
        return StandardProfileAutoConfigResult(
            profile=proposal,
            terms=[
                term,
                *[
                    StandardProfileAutoConfigTerm(
                        term=term_name,
                        status="unresolved",
                        confidence=0.0,
                    )
                    for term_name in ("eventDate", "samplingProtocol", "locationID")
                ],
            ],
            unresolved=["eventDate", "samplingProtocol", "locationID"],
            notes=[
                "Humboldt/Event auto-configuration is conservative; review inventory context before saving."
            ],
            record_source=profile.source,
            rows_sampled=len(records),
            columns_inspected=len(columns),
        )

    def _record_source_for_profile(
        self,
        profile: StandardProfileConfig,
        notes: list[str],
    ) -> StandardProfileSource:
        if profile.standard != "darwin_core_occurrence":
            return self.output_service._backing_source_for_profile_source(
                profile.source
            )

        try:
            compatibility = self.compatibility_service.evaluate(profile)
        except Exception as exc:
            notes.append(f"Could not evaluate source compatibility: {exc}")
            return self.output_service._backing_source_for_profile_source(
                profile.source
            )

        return self.output_service._record_source_for_profile(profile, compatibility)

    def _infer_darwin_core_terms(
        self,
        columns: list[str],
        records: list[dict[str, Any]],
    ) -> dict[str, StandardProfileAutoConfigTerm]:
        mapped: dict[str, StandardProfileAutoConfigTerm] = {}
        for column in columns:
            for candidate in self._column_candidates(column, records):
                current = mapped.get(candidate.term)
                if current is not None and current.confidence >= candidate.confidence:
                    continue
                mapped[candidate.term] = StandardProfileAutoConfigTerm(
                    term=candidate.term,
                    status="mapped",
                    mapping={"source": candidate.column},
                    confidence=round(candidate.confidence, 3),
                    source_column=candidate.column,
                    evidence=[candidate.evidence],
                )
        return mapped

    def _add_geometry_coordinate_terms(
        self,
        mapped_terms: dict[str, StandardProfileAutoConfigTerm],
        columns: list[str],
        records: list[dict[str, Any]],
    ) -> None:
        if "decimalLatitude" in mapped_terms and "decimalLongitude" in mapped_terms:
            return
        geometry_column = _best_geometry_column(columns, records)
        if geometry_column is None:
            return

        if "decimalLatitude" not in mapped_terms:
            mapped_terms["decimalLatitude"] = StandardProfileAutoConfigTerm(
                term="decimalLatitude",
                status="mapped",
                mapping={
                    "generator": "extract_geometry_coordinate",
                    "params": {
                        "source": geometry_column,
                        "coordinate": "latitude",
                    },
                },
                confidence=0.9,
                source_column=geometry_column,
                evidence=["Extracted latitude from a point geometry column."],
            )
        if "decimalLongitude" not in mapped_terms:
            mapped_terms["decimalLongitude"] = StandardProfileAutoConfigTerm(
                term="decimalLongitude",
                status="mapped",
                mapping={
                    "generator": "extract_geometry_coordinate",
                    "params": {
                        "source": geometry_column,
                        "coordinate": "longitude",
                    },
                },
                confidence=0.9,
                source_column=geometry_column,
                evidence=["Extracted longitude from a point geometry column."],
            )

    def _add_basis_of_record_term(
        self,
        mapped_terms: dict[str, StandardProfileAutoConfigTerm],
    ) -> None:
        if "basisOfRecord" in mapped_terms:
            return
        mapped_terms["basisOfRecord"] = StandardProfileAutoConfigTerm(
            term="basisOfRecord",
            status="mapped",
            mapping={
                "generator": "constant",
                "params": {"value": "HumanObservation"},
            },
            confidence=0.55,
            evidence=[
                "Proposed as HumanObservation because no basisOfRecord column was found."
            ],
        )

    def _add_dynamic_properties_term(
        self,
        mapped_terms: dict[str, StandardProfileAutoConfigTerm],
        columns: list[str],
    ) -> None:
        if "dynamicProperties" in mapped_terms:
            return
        used_columns = {
            term.source_column
            for term in mapped_terms.values()
            if term.source_column is not None
        }
        property_columns = [
            column
            for column in columns
            if column not in used_columns
            and _normalize_column(column) in DYNAMIC_PROPERTY_COLUMN_ALIASES
        ]
        if not property_columns:
            return
        mapped_terms["dynamicProperties"] = StandardProfileAutoConfigTerm(
            term="dynamicProperties",
            status="mapped",
            mapping={
                "generator": "format_measurements",
                "params": {"fields": property_columns},
            },
            confidence=0.64,
            evidence=[
                "Grouped measurement and environmental columns into dynamicProperties."
            ],
        )

    def _column_candidates(
        self,
        column: str,
        records: list[dict[str, Any]],
    ) -> list[_TermCandidate]:
        normalized = _normalize_column(column)
        candidates: list[_TermCandidate] = []

        for term, aliases in DWC_TERM_ALIASES.items():
            if normalized in aliases:
                adjusted_term = _adjust_dwc_term_for_column(term, normalized)
                candidates.append(
                    _TermCandidate(
                        term=adjusted_term,
                        column=column,
                        confidence=1.0,
                        evidence=(
                            f"Column name matches Darwin Core alias '{adjusted_term}'."
                        ),
                    )
                )

        alias_concept, alias_confidence = (
            self.alias_registry.match(column)
            if self.alias_registry is not None
            else (None, 0.0)
        )
        if alias_concept and alias_concept in CONCEPT_TO_DWC_TERM:
            term = _adjust_dwc_term_for_column(
                CONCEPT_TO_DWC_TERM[alias_concept], normalized
            )
            candidates.append(
                _TermCandidate(
                    term=term,
                    column=column,
                    confidence=max(0.86, alias_confidence),
                    evidence=f"Column alias matched semantic concept '{alias_concept}'.",
                )
            )

        ml_concept, ml_confidence = self._ml_concept(column, records)
        if ml_concept and ml_confidence >= 0.65 and ml_concept in CONCEPT_TO_DWC_TERM:
            term = _adjust_dwc_term_for_column(
                CONCEPT_TO_DWC_TERM[ml_concept], normalized
            )
            candidates.append(
                _TermCandidate(
                    term=term,
                    column=column,
                    confidence=ml_confidence,
                    evidence=f"ML classified the column as '{ml_concept}'.",
                )
            )

        return candidates

    def _ml_concept(
        self,
        column: str,
        records: list[dict[str, Any]],
    ) -> tuple[str | None, float]:
        if self.column_classifier is None:
            return None, 0.0
        try:
            import pandas as pd

            values = [record.get(column) for record in records[:200]]
            concept, confidence = self.column_classifier.classify(
                column,
                pd.Series(values),
                name_normalized=_normalize_column(column),
            )
            return concept, confidence
        except Exception:
            return None, 0.0

    def _load_record_sample(
        self,
        source: StandardProfileSource,
        notes: list[str],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        if self.db_path is None or not self.db_path.exists():
            return [], []

        database = Database(str(self.db_path), optimize=False, read_only=True)
        try:
            table_name = self.output_service._resolve_source_table(database, source)
            if table_name is None:
                return [], []
            escaped_table = table_name.replace('"', '""')
            with database.connection() as connection:
                result = connection.execute(
                    text(f'SELECT * FROM "{escaped_table}" LIMIT 200')
                )
                columns = list(result.keys())
                records = [dict(zip(columns, row)) for row in result.fetchall()]
                return records, columns
        except Exception as exc:
            notes.append(f"Could not inspect imported rows: {exc}")
            return [], []
        finally:
            database.close_db_session()
            database.engine.dispose()

    def _schema_columns(self, source: StandardProfileSource) -> list[str]:
        entity_group = "datasets" if source.type == "dataset" else "references"
        entities = self.import_config.get("entities")
        if not isinstance(entities, dict):
            return []
        group = entities.get(entity_group)
        if not isinstance(group, dict):
            return []
        config = group.get(source.name)
        if not isinstance(config, dict):
            return []
        schema = config.get("schema")
        if not isinstance(schema, dict):
            return []
        fields = schema.get("fields")
        if isinstance(fields, dict):
            return [str(name) for name in fields.keys()]
        if isinstance(fields, list):
            return [
                str(field["name"])
                for field in fields
                if isinstance(field, dict) and field.get("name")
            ]
        return []


def _ordered_terms(
    mapped_terms: dict[str, StandardProfileAutoConfigTerm],
    unresolved: list[str],
) -> list[StandardProfileAutoConfigTerm]:
    ordered_names = [
        *[term for term in DWC_TERM_ORDER if term in mapped_terms],
        *sorted(term for term in mapped_terms if term not in DWC_TERM_ORDER),
        *[term for term in DWC_TERM_ORDER if term in unresolved],
        *sorted(term for term in unresolved if term not in DWC_TERM_ORDER),
    ]
    terms: list[StandardProfileAutoConfigTerm] = []
    for term_name in ordered_names:
        terms.append(
            mapped_terms.get(term_name)
            or StandardProfileAutoConfigTerm(
                term=term_name,
                status="unresolved",
                confidence=0.0,
            )
        )
    return terms


def _best_direct_column(columns: list[str], aliases: set[str]) -> str | None:
    for column in columns:
        if _normalize_column(column) in aliases:
            return column
    return None


def _best_geometry_column(
    columns: list[str],
    records: list[dict[str, Any]],
) -> str | None:
    normalized_by_column = {column: _normalize_column(column) for column in columns}
    preferred_aliases = (
        "geo_pt",
        "geometry",
        "geom",
        "point",
        "coordinates",
        "geo_pt_geom",
    )
    candidates: list[str] = []
    for alias in preferred_aliases:
        for column, normalized in normalized_by_column.items():
            if normalized == alias:
                candidates.append(column)
    for column, normalized in normalized_by_column.items():
        if "geom" in normalized or normalized.startswith("geo_"):
            candidates.append(column)
    deduplicated_candidates = list(dict.fromkeys(candidates))
    for column in deduplicated_candidates:
        if _column_has_parseable_point(column, records):
            return column
    return deduplicated_candidates[0] if deduplicated_candidates else None


def _column_has_parseable_point(
    column: str,
    records: list[dict[str, Any]],
) -> bool:
    for record in records:
        value = record.get(column)
        if isinstance(value, dict) and isinstance(value.get("coordinates"), list):
            return True
        if isinstance(value, str) and "POINT" in value.upper():
            return True
    return False


def _preferred_identifier_column(columns: list[str]) -> str:
    return (
        _best_direct_column(
            columns,
            DWC_TERM_ALIASES["occurrenceID"] | {"identifier", "objectid"},
        )
        or "id"
    )


def _default_outputs(
    profile_name: str,
    standard: StandardProfileType,
) -> list[StandardProfileOutput]:
    output_dir = f"exports/profiles/{profile_name}"
    if standard == "darwin_core_occurrence":
        return [
            StandardProfileOutput(
                type="api_json",
                enabled=True,
                params={"output_dir": output_dir},
            ),
            StandardProfileOutput(
                type="dwc_archive",
                enabled=True,
                params={
                    "output_dir": output_dir,
                    "archive_name": f"{profile_name}-dwc.zip",
                },
            ),
        ]
    return [
        StandardProfileOutput(
            type="api_json",
            enabled=True,
            params={"output_dir": output_dir},
        ),
        StandardProfileOutput(
            type="standard_files",
            enabled=True,
            params={"output_dir": output_dir},
        ),
    ]


def _default_target_grain(standard: StandardProfileType) -> str:
    return "occurrence" if standard == "darwin_core_occurrence" else "event"


def _standard_prefix(standard: StandardProfileType) -> str:
    return "dwc" if standard == "darwin_core_occurrence" else "humboldt"


def _safe_profile_name(value: str) -> str:
    normalized = _normalize_column(value)
    sanitized = "_".join(part for part in normalized.split("_") if part)
    return sanitized or "standard_profile"


def _normalize_column(value: str) -> str:
    normalized = unidecode(value).lower().strip()
    for separator in (" ", "-", ".", ":"):
        normalized = normalized.replace(separator, "_")
    return "".join(
        character for character in normalized if character.isalnum() or character == "_"
    )


def _adjust_dwc_term_for_column(term: str, normalized_column: str) -> str:
    tokens = normalized_column.split("_")
    if term == "eventDate" and any(token in tokens for token in ("month", "mois")):
        return "month"
    if term == "locality" and "plot" in tokens:
        return "locationID"
    return term


def _safe_alias_registry() -> AliasRegistry | None:
    try:
        return AliasRegistry()
    except Exception:
        return None


def _safe_column_classifier() -> ColumnClassifier | None:
    try:
        return ColumnClassifier()
    except Exception:
        return None
