"""
API routes for transformer suggestions.

Provides endpoints to retrieve auto-generated transformer suggestions
from the semantic profile stored in EntityRegistry.
"""

import logging
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from niamoto.core.imports.registry import EntityRegistry
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.gui.api.utils.database import open_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transformer-suggestions", tags=["transformers"])


# Pydantic models for API responses
class ColumnProfile(BaseModel):
    """Column metadata from semantic profile."""

    name: str = Field(..., description="Column name")
    data_category: str = Field(
        ..., description="Data category (e.g., numeric_continuous)"
    )
    field_purpose: str = Field(..., description="Field purpose (e.g., measurement)")
    cardinality: int = Field(..., description="Number of unique values")
    suggested_bins: Optional[List[float]] = Field(
        None, description="Suggested bins for numeric data"
    )
    suggested_labels: Optional[List[str]] = Field(
        None, description="Suggested labels for categorical data"
    )
    value_range: Optional[tuple[float, float]] = Field(
        None, description="Min/max range as (min, max) tuple"
    )


class TransformerConfig(BaseModel):
    """Transformer configuration."""

    plugin: str = Field(..., description="Plugin name")
    params: Dict[str, Any] = Field(..., description="Plugin parameters")


class TransformerSuggestionItem(BaseModel):
    """Single transformer suggestion."""

    transformer: str = Field(..., description="Transformer name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reason: str = Field(..., description="Human-readable reason")
    config: TransformerConfig = Field(..., description="Pre-filled configuration")


class TransformerSuggestionsResponse(BaseModel):
    """Response model for transformer suggestions endpoint."""

    entity_name: str = Field(..., description="Name of the entity")
    analyzed_at: str = Field(
        ..., description="ISO timestamp of when analysis was performed"
    )
    columns: List[ColumnProfile] = Field(..., description="Column metadata")
    suggestions: Dict[str, List[TransformerSuggestionItem]] = Field(
        ..., description="Suggestions by column name"
    )


# Models for references endpoint
class NestedSetFields(BaseModel):
    """Fields mapping for nested set structure."""

    left: str = Field(default="lft", description="Left field name")
    right: str = Field(default="rght", description="Right field name")
    parent: str = Field(default="parent_id", description="Parent field name")


class RelationConfig(BaseModel):
    """Relation configuration for transform.yml sources."""

    plugin: str = Field(
        ..., description="Relation plugin (direct_reference, nested_set, etc.)"
    )
    key: str = Field(..., description="Foreign key field in source data")
    ref_key: Optional[str] = Field(None, description="Target field in reference table")
    fields: Optional[NestedSetFields] = Field(
        None, description="Field mapping for nested_set plugin"
    )


class ReferenceInfo(BaseModel):
    """Information about a reference entity that can be used as group_by target."""

    name: str = Field(..., description="Reference entity name")
    kind: str = Field(
        ..., description="Reference kind (hierarchical, spatial, generic)"
    )
    description: Optional[str] = Field(None, description="Reference description")
    relation: RelationConfig = Field(
        ..., description="Default relation config for transform.yml"
    )


class DatasetInfo(BaseModel):
    """Information about a dataset entity (source data)."""

    name: str = Field(..., description="Dataset entity name")
    description: Optional[str] = Field(None, description="Dataset description")


class ReferencesResponse(BaseModel):
    """Response model for available references endpoint."""

    references: List[ReferenceInfo] = Field(
        ..., description="Reference entities available as group_by targets"
    )
    datasets: List[DatasetInfo] = Field(
        ..., description="Dataset entities available as data sources"
    )


# ============================================================================
# IMPORTANT: Fixed routes (/, /references) must be defined BEFORE
# dynamic routes (/{entity_name}) to avoid FastAPI route matching issues
# ============================================================================


@router.get("/", response_model=List[str])
async def list_entities_with_suggestions():
    """
    List all entities that have transformer suggestions available.

    Returns:
        List of entity names with semantic profiles
    """
    try:
        db_path = get_database_path()
        with open_database(db_path) as db:
            registry = EntityRegistry(db)

            entities_with_suggestions = []
            for entity in registry.list_entities():
                try:
                    metadata = registry.get(entity.name)
                    if (
                        metadata
                        and metadata.config
                        and "semantic_profile" in metadata.config
                    ):
                        entities_with_suggestions.append(entity.name)
                except Exception:
                    continue

            return entities_with_suggestions

    except Exception as e:
        logger.exception(f"Error listing entities with suggestions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error listing entities: {str(e)}",
        )


@router.get("/references", response_model=ReferencesResponse)
async def get_available_references():
    """
    Get available reference entities from import.yml.

    Returns reference entities (taxons, plots, shapes) that can be used
    as group_by targets in transform.yml, and dataset entities (occurrences)
    that serve as data sources.

    This endpoint reads the import.yml configuration to understand the
    data model structure.

    Returns:
        ReferencesResponse with references and datasets

    Raises:
        HTTPException: 404 if import.yml not found
        HTTPException: 500 if parsing error
    """
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=404, detail="Working directory not found")

        import_config_path = work_dir / "config" / "import.yml"
        if not import_config_path.exists():
            raise HTTPException(
                status_code=404,
                detail="import.yml not found. Please configure imports first.",
            )

        with open(import_config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f)

        if not import_config:
            raise HTTPException(
                status_code=400,
                detail="import.yml is empty or invalid.",
            )

        references: List[ReferenceInfo] = []
        datasets: List[DatasetInfo] = []

        def build_relation_config(
            ref_name: str, kind: str, config: Optional[Dict[str, Any]] = None
        ) -> RelationConfig:
            """Build default relation config based on reference kind and config."""
            # Determine key field from config if available
            key_field = f"{ref_name}_id"  # Default pattern
            ref_field = "id"  # Default ref_key

            if config and isinstance(config, dict):
                # First check for explicit relation block in import.yml
                relation_config = config.get("relation", {})
                if relation_config:
                    # Use explicit relation from import.yml
                    foreign_key = relation_config.get("foreign_key")
                    reference_key = relation_config.get("reference_key")
                    if foreign_key:
                        key_field = foreign_key
                    if reference_key:
                        ref_field = reference_key

                # Check extraction.id_column for derived references (taxons)
                connector = config.get("connector", {})
                if connector.get("type") == "derived":
                    extraction = connector.get("extraction", {})
                    if extraction.get("id_column"):
                        key_field = extraction["id_column"]

                # Check schema.id_field for regular references (plots) - only as fallback
                if not relation_config:
                    schema = config.get("schema", {})
                    if schema.get("id_field"):
                        key_field = schema["id_field"]

            # Determine plugin based on kind
            if kind == "hierarchical":
                return RelationConfig(
                    plugin="nested_set",
                    key=key_field,
                    ref_key=f"{ref_name}_id",
                    fields=NestedSetFields(),  # Default nested set fields
                )
            else:  # generic/default
                return RelationConfig(
                    plugin="direct_reference",
                    key=key_field,
                    ref_key=ref_field,
                )

        # Handle EntityRegistry v2 format (version: "1.0", entities: {...})
        if "entities" in import_config:
            entities = import_config["entities"]

            # Extract datasets
            if "datasets" in entities and isinstance(entities["datasets"], dict):
                for name, config in entities["datasets"].items():
                    description = None
                    if isinstance(config, dict):
                        description = config.get("description")
                    datasets.append(DatasetInfo(name=name, description=description))

            # Extract references
            if "references" in entities and isinstance(entities["references"], dict):
                for name, config in entities["references"].items():
                    kind = "generic"  # default
                    description = None
                    if isinstance(config, dict):
                        kind = config.get("kind", "generic")
                        description = config.get("description")

                    relation = build_relation_config(name, kind, config)
                    references.append(
                        ReferenceInfo(
                            name=name,
                            kind=kind,
                            description=description,
                            relation=relation,
                        )
                    )

        # EntityRegistry v2 format is required
        else:
            raise HTTPException(
                status_code=400,
                detail="import.yml must use EntityRegistry v2 format (version: '1.0', entities: {...})",
            )

        return ReferencesResponse(references=references, datasets=datasets)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error reading references from import.yml: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error reading import configuration: {str(e)}",
        )


# ============================================================================
# Dynamic route - must be AFTER fixed routes
# ============================================================================


@router.get("/{entity_name}", response_model=TransformerSuggestionsResponse)
async def get_transformer_suggestions(entity_name: str):
    """
    Get transformer suggestions for an entity.

    Retrieves the semantic profile generated during import and returns
    transformer suggestions with pre-filled configurations.

    Args:
        entity_name: Name of the entity to get suggestions for

    Returns:
        TransformerSuggestionsResponse with suggestions

    Raises:
        HTTPException: 404 if entity not found or no semantic analysis available
        HTTPException: 500 if database context issues
    """
    try:
        # Get database using utility (same as other endpoints)
        db_path = get_database_path()
        with open_database(db_path) as db:
            registry = EntityRegistry(db)

            # Get entity metadata
            metadata = registry.get(entity_name)
            if not metadata or not metadata.config:
                raise HTTPException(
                    status_code=404, detail=f"Entity '{entity_name}' not found"
                )

            # Get semantic profile
            semantic_profile = metadata.config.get("semantic_profile")
            if not semantic_profile:
                raise HTTPException(
                    status_code=404,
                    detail=f"No semantic analysis available for entity '{entity_name}'. "
                    "The entity may have been imported before auto-suggestion was enabled.",
                )

            # Convert to response model
            columns = [ColumnProfile(**col) for col in semantic_profile["columns"]]

            # Convert suggestions
            suggestions = {}
            for col_name, col_suggestions in semantic_profile[
                "transformer_suggestions"
            ].items():
                suggestions[col_name] = [
                    TransformerSuggestionItem(**suggestion)
                    for suggestion in col_suggestions
                ]

            return TransformerSuggestionsResponse(
                entity_name=entity_name,
                analyzed_at=semantic_profile["analyzed_at"],
                columns=columns,
                suggestions=suggestions,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error retrieving transformer suggestions for '{entity_name}': {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal error retrieving suggestions: {str(e)}",
        )
