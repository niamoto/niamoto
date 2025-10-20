"""Pydantic models for the next-generation import configuration.

These models represent the declarative structure described in
``docs/10-roadmaps/generic-import-ultrathink.md``. They provide a typed view
over ``import.yml`` so other components (registry, engine, GUI) can reason
about entities, connectors, schemas, and relationships without relying on
ad-hoc dictionaries.

Phase 0 goal: offer a first pass of the schema with sensible defaults while
staying permissive enough for future iteration.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ConnectorType(str, Enum):
    """Supported connector kinds for data ingestion."""

    FILE = "file"
    DUCKDB_CSV = "duckdb_csv"
    VECTOR = "vector"
    API = "api"
    PLUGIN = "plugin"
    DERIVED = "derived"  # Derive reference from source dataset
    FILE_MULTI_FEATURE = (
        "file_multi_feature"  # Import multiple spatial files as features
    )


class MultiFeatureSource(BaseModel):
    """Single source file for multi-feature connector."""

    name: str  # Feature type name (e.g. "Provinces")
    path: str  # Path to spatial file
    name_field: str  # Field containing feature name


class ConnectorConfig(BaseModel):
    """Connector definition (file, API, plugin, …)."""

    type: ConnectorType
    path: Optional[str] = None
    format: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)

    # Fields for derived mode
    source: Optional[str] = None  # Source dataset name
    strategy: Optional[str] = None  # "hierarchy_builder"
    extraction: Optional["ExtractionConfig"] = None

    # Fields for file_multi_feature mode
    sources: Optional[List[MultiFeatureSource]] = None

    @model_validator(mode="after")
    def validate_path_requirement(self) -> "ConnectorConfig":
        if self.type in {
            ConnectorType.FILE,
            ConnectorType.DUCKDB_CSV,
            ConnectorType.VECTOR,
        }:
            if not self.path:
                msg = "Connector type requires a 'path' attribute"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_derived_requirements(self) -> "ConnectorConfig":
        """Validate derived connector requirements."""
        if self.type == ConnectorType.DERIVED:
            if not self.source:
                msg = "Derived connector requires 'source' (dataset name)"
                raise ValueError(msg)
            if not self.extraction:
                msg = "Derived connector requires 'extraction' configuration"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_multi_feature_requirements(self) -> "ConnectorConfig":
        """Validate file_multi_feature connector requirements."""
        if self.type == ConnectorType.FILE_MULTI_FEATURE:
            if not self.sources or len(self.sources) == 0:
                msg = "file_multi_feature connector requires 'sources' list"
                raise ValueError(msg)
        return self


class FieldType(str, Enum):
    """Baseline field types recognised by the generic importer."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    GEOMETRY = "geometry"
    JSON = "json"
    TEXT = "text"


class FieldConfig(BaseModel):
    """Description of a column belonging to an entity schema."""

    name: str
    type: FieldType
    semantic: Optional[str] = None
    reference: Optional[str] = None
    description: Optional[str] = None


class HierarchyStrategy(str, Enum):
    """Supported hierarchy storage strategies."""

    NESTED_SET = "nested_set"
    ADJACENCY_LIST = "adjacency_list"
    HYBRID = "hybrid"


class HierarchyLevel(BaseModel):
    """Single hierarchy level definition."""

    name: str
    column: Optional[str] = None
    semantic: Optional[str] = None


class ExtractionConfig(BaseModel):
    """Configuration for extracting hierarchy from source dataset."""

    levels: List[HierarchyLevel]
    id_column: Optional[str] = None  # External ID column (e.g., id_taxonref)
    name_column: Optional[str] = None  # Full name column (e.g., taxaname)
    additional_columns: List[str] = Field(default_factory=list)
    incomplete_rows: str = "skip"  # "skip" | "fill_unknown" | "error"
    id_strategy: str = "hash"  # "hash" | "sequence" | "external"

    @model_validator(mode="after")
    def validate_id_strategy(self) -> "ExtractionConfig":
        """Validate id_strategy requirements."""
        if self.id_strategy == "external" and not self.id_column:
            msg = "id_strategy 'external' requires 'id_column' to be specified"
            raise ValueError(msg)
        if self.incomplete_rows not in {"skip", "fill_unknown", "error"}:
            msg = f"incomplete_rows must be 'skip', 'fill_unknown', or 'error', got '{self.incomplete_rows}'"
            raise ValueError(msg)
        return self


class HierarchyConfig(BaseModel):
    """Hierarchy configuration for reference entities."""

    strategy: HierarchyStrategy = Field(
        default=HierarchyStrategy.ADJACENCY_LIST, alias="type"
    )
    levels: List[HierarchyLevel]
    aggregate_geometry: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalise_levels(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        raw_levels = values.get("levels", [])
        normalised: List[Dict[str, Any]] = []
        for item in raw_levels:
            if isinstance(item, str):
                normalised.append({"name": item, "column": item})
            elif isinstance(item, dict):
                normalised.append(item)
            elif isinstance(item, HierarchyLevel):
                normalised.append(item.model_dump())
            else:
                raise TypeError("Hierarchy level must be string or mapping")
        values["levels"] = normalised
        return values


class EnrichmentConfig(BaseModel):
    """Optional enrichment step executed after import."""

    plugin: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class EntitySchema(BaseModel):
    """Schema definition shared by references and datasets."""

    id_field: str = Field(alias="id")
    fields: List[FieldConfig] = Field(default_factory=list)
    extras: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def support_id_aliases(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "id_field" not in values and "id" in values:
            values["id_field"] = values["id"]
        if "id" not in values and "id_field" in values:
            values["id"] = values["id_field"]
        return values


class LinkConfig(BaseModel):
    """Describes linkage between a dataset and a reference entity."""

    entity: str
    field: str
    target_field: str
    relationship: Optional[str] = None


class DatasetOptions(BaseModel):
    """Dataset ingestion options."""

    mode: str = "replace"
    chunk_size: int = 10000
    only_existing_references: bool = False


class BaseEntityConfig(BaseModel):
    """Common attributes shared by reference/dataset entities."""

    connector: ConnectorConfig
    entity_schema: EntitySchema = Field(alias="schema")
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    @property
    def schema(self) -> EntitySchema:
        """Expose schema attribute for backward compatibility."""

        return self.entity_schema


class ReferenceKind(str, Enum):
    """Kind of reference entity."""

    HIERARCHICAL = "hierarchical"
    SPATIAL = "spatial"
    CATEGORICAL = "categorical"
    GENERIC = "generic"


class ReferenceEntityConfig(BaseEntityConfig):
    """Reference entity definition."""

    kind: Optional[ReferenceKind] = None
    hierarchy: Optional[HierarchyConfig] = None
    enrichment: List[EnrichmentConfig] = Field(default_factory=list)


class DatasetEntityConfig(BaseEntityConfig):
    """Dataset entity linked to references."""

    links: List[LinkConfig] = Field(default_factory=list)
    options: DatasetOptions = Field(default_factory=DatasetOptions)


class EntitiesConfig(BaseModel):
    """Container for references and datasets."""

    references: Dict[str, ReferenceEntityConfig] = Field(default_factory=dict)
    datasets: Dict[str, DatasetEntityConfig] = Field(default_factory=dict)


class GenericImportConfig(BaseModel):
    """Root configuration for the generic import system."""

    version: Optional[str] = None
    entities: EntitiesConfig
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericImportConfig":
        """Convenience helper mirroring ``Config`` style loaders."""

        if "entities" not in data:
            raise ValueError("Generic import config must define 'entities'")
        return cls(**data)
