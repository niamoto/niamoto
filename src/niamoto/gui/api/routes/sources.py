"""
API routes for pre-calculated data sources management.

Provides endpoints for:
- Uploading and validating pre-calculated CSV files
- Listing configured sources for a reference group
- Saving source configuration to transform.yml
- Removing source configuration
"""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from niamoto.core.imports.class_object_analyzer import ClassObjectAnalyzer
from niamoto.gui.api.context import get_working_directory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class ClassObjectInfo(BaseModel):
    """Information about a detected class_object type."""

    name: str
    cardinality: int
    class_names: list[str]
    value_type: str  # "numeric" or "categorical"
    suggested_plugin: Optional[str] = None
    confidence: float = 0.0


class UploadValidationResponse(BaseModel):
    """Response after uploading and validating a CSV file."""

    success: bool
    source_name: str
    file_name: str
    path: str
    delimiter: str
    row_count: int
    entity_column: Optional[str]
    entity_count: int
    columns: list[str]
    class_objects: list[ClassObjectInfo]
    validation_errors: list[str]


class ConfiguredSource(BaseModel):
    """A source already configured in transform.yml."""

    name: str
    data_path: str
    grouping: str
    relation_plugin: str
    class_object_count: Optional[int] = None


class SourcesListResponse(BaseModel):
    """Response listing configured sources for a group."""

    group_name: str
    sources: list[ConfiguredSource]
    total: int


class SaveSourceRequest(BaseModel):
    """Request to save a source configuration."""

    source_name: str = Field(..., description="Name for the source")
    file_path: str = Field(
        ..., description="Path to the CSV file (relative to imports/)"
    )
    entity_id_column: str = Field(..., description="Column linking to group entities")


class SaveSourceResponse(BaseModel):
    """Response after saving source configuration."""

    success: bool
    message: str
    source_name: str


class RemoveSourceResponse(BaseModel):
    """Response after removing a source."""

    success: bool
    message: str


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _load_transform_config(work_dir: Path) -> dict[str, Any]:
    """Load transform.yml configuration.

    Converts the list-based YAML format to internal dict format:
    YAML: [{"group_by": "taxons", "sources": [...]}]
    Internal: {"groups": {"taxons": {"sources": [...]}}}
    """
    transform_path = work_dir / "config" / "transform.yml"
    if not transform_path.exists():
        return {"groups": {}}

    with open(transform_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    if raw_config is None:
        return {"groups": {}}

    # If it's already a dict with "groups", return as-is
    if isinstance(raw_config, dict) and "groups" in raw_config:
        return raw_config

    # Convert list format to dict format
    if isinstance(raw_config, list):
        groups = {}
        for item in raw_config:
            if isinstance(item, dict) and "group_by" in item:
                group_name = item["group_by"]
                # Copy all keys except "group_by"
                group_config = {k: v for k, v in item.items() if k != "group_by"}
                groups[group_name] = group_config
        return {"groups": groups}

    return {"groups": {}}


def _save_transform_config(work_dir: Path, config: dict[str, Any]) -> None:
    """Save transform.yml configuration.

    Converts internal dict format back to list-based YAML format:
    Internal: {"groups": {"taxons": {"sources": [...]}}}
    YAML: [{"group_by": "taxons", "sources": [...]}]
    """
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Convert dict format to list format for YAML
    yaml_config = []
    if "groups" in config:
        for group_name, group_config in config["groups"].items():
            item = {"group_by": group_name}
            item.update(group_config)
            yaml_config.append(item)

    transform_path = config_dir / "transform.yml"
    with open(transform_path, "w", encoding="utf-8") as f:
        yaml.dump(
            yaml_config,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


def _get_reference_kind(work_dir: Path, reference_name: str) -> str:
    """Get the kind of a reference from import.yml."""
    import_path = work_dir / "config" / "import.yml"
    if not import_path.exists():
        return "flat"  # Default

    with open(import_path, "r", encoding="utf-8") as f:
        import_config = yaml.safe_load(f) or {}

    references = import_config.get("entities", {}).get("references", {})
    ref_config = references.get(reference_name, {})
    return ref_config.get("kind", "flat")


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("/{reference_name}/upload", response_model=UploadValidationResponse)
async def upload_precalc_source(
    reference_name: str,
    file: UploadFile = File(...),
    source_name: str = Query(..., description="Name for this source"),
):
    """
    Upload and validate a pre-calculated CSV file.

    The CSV must follow the class_object format:
    - Required columns: class_object, class_name, class_value
    - Entity column: One of plot_id, shape_id, taxon_id, entity_id, id

    The file is stored in imports/ directory and analyzed for structure.
    Delimiter is auto-detected (comma or semicolon).

    This endpoint validates but does NOT save to transform.yml.
    Use POST /{reference_name}/save to persist the configuration.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)
    imports_dir = work_dir / "imports"
    imports_dir.mkdir(parents=True, exist_ok=True)

    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    # Generate unique filename
    file_name = f"raw_{source_name}.csv"
    file_path = imports_dir / file_name

    # Save uploaded file
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        logger.exception(f"Error saving uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Analyze the CSV
    try:
        analyzer = ClassObjectAnalyzer(file_path)
        analysis = analyzer.analyze()

        class_objects_info = [
            ClassObjectInfo(
                name=co.name,
                cardinality=co.cardinality,
                class_names=co.class_names,
                value_type=co.value_type,
                suggested_plugin=co.suggested_plugin,
                confidence=co.confidence,
            )
            for co in analysis.class_objects
        ]

        return UploadValidationResponse(
            success=analysis.is_valid,
            source_name=source_name,
            file_name=file_name,
            path=f"imports/{file_name}",
            delimiter=analysis.delimiter,
            row_count=analysis.row_count,
            entity_column=analysis.entity_column,
            entity_count=analysis.entity_count,
            columns=analysis.columns,
            class_objects=class_objects_info,
            validation_errors=analysis.validation_errors,
        )

    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        logger.exception(f"Error analyzing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze file: {str(e)}")


@router.get("/{reference_name}/sources", response_model=SourcesListResponse)
async def get_group_sources(reference_name: str):
    """
    List pre-calculated data sources configured for a reference group.

    Reads the sources section from transform.yml for the specified group
    and returns only CSV-based sources (not occurrences).
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)
    config = _load_transform_config(work_dir)

    # Get group config (now always normalized to dict format with 'groups' key)
    group_config = config.get("groups", {}).get(reference_name, {})
    sources_config = group_config.get("sources", [])

    # Filter to only CSV sources (exclude occurrences)
    csv_sources = []
    for source in sources_config:
        data_path = source.get("data", "")
        # Skip non-CSV sources (like 'occurrences' table reference)
        if not data_path.endswith(".csv"):
            continue

        relation = source.get("relation", {})
        csv_sources.append(
            ConfiguredSource(
                name=source.get("name", "unknown"),
                data_path=data_path,
                grouping=source.get("grouping", reference_name),
                relation_plugin=relation.get("plugin", "stats_loader"),
            )
        )

    return SourcesListResponse(
        group_name=reference_name,
        sources=csv_sources,
        total=len(csv_sources),
    )


@router.post("/{reference_name}/save", response_model=SaveSourceResponse)
async def save_source_config(
    reference_name: str,
    request: SaveSourceRequest,
):
    """
    Save a pre-calculated source configuration to transform.yml.

    Adds the source to the group's sources section:
    ```yaml
    sources:
      - name: plot_stats
        data: imports/raw_plot_stats.csv
        grouping: plots
        relation:
          plugin: stats_loader
          key: id
          ref_field: id_plot
          match_field: plot_id
    ```
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)

    # Verify the CSV file exists
    csv_path = work_dir / request.file_path
    if not csv_path.exists():
        raise HTTPException(
            status_code=404, detail=f"CSV file not found: {request.file_path}"
        )

    # Load existing config
    config = _load_transform_config(work_dir)

    # Ensure groups structure exists
    if "groups" not in config:
        config["groups"] = {}
    if reference_name not in config["groups"]:
        config["groups"][reference_name] = {}

    group_config = config["groups"][reference_name]

    # Ensure sources list exists
    if "sources" not in group_config:
        group_config["sources"] = []

    # Check if source with same name already exists
    existing_idx = None
    for idx, source in enumerate(group_config["sources"]):
        if source.get("name") == request.source_name:
            existing_idx = idx
            break

    # Build source configuration
    # Determine ref_field based on entity_id_column and reference name
    ref_field = f"id_{reference_name}"  # Default: id_plots, id_shapes, etc.
    if reference_name.endswith("s"):
        ref_field = f"id_{reference_name[:-1]}"  # id_plot, id_shape (singular)

    new_source = {
        "name": request.source_name,
        "data": request.file_path,
        "grouping": reference_name,
        "relation": {
            "plugin": "stats_loader",
            "key": "id",
            "ref_field": ref_field,
            "match_field": request.entity_id_column,
        },
    }

    # Update or add source
    if existing_idx is not None:
        group_config["sources"][existing_idx] = new_source
        message = f"Source '{request.source_name}' updated"
    else:
        group_config["sources"].append(new_source)
        message = f"Source '{request.source_name}' added"

    # Save config
    try:
        _save_transform_config(work_dir, config)
        logger.info(f"{message} for group '{reference_name}'")
        return SaveSourceResponse(
            success=True,
            message=message,
            source_name=request.source_name,
        )
    except Exception as e:
        logger.exception(f"Error saving transform config: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to save configuration: {str(e)}"
        )


@router.delete(
    "/{reference_name}/sources/{source_name}", response_model=RemoveSourceResponse
)
async def remove_source_config(
    reference_name: str,
    source_name: str,
):
    """
    Remove a pre-calculated source configuration from transform.yml.

    This removes only the configuration, not the CSV file itself.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)

    # Load existing config (now always normalized to dict format with 'groups' key)
    config = _load_transform_config(work_dir)

    # Find group config
    groups = config.get("groups", {})
    if reference_name not in groups:
        raise HTTPException(
            status_code=404,
            detail=f"Group '{reference_name}' not found in configuration",
        )
    group_config = groups[reference_name]

    sources = group_config.get("sources", [])

    original_count = len(sources)
    group_config["sources"] = [s for s in sources if s.get("name") != source_name]

    if len(group_config["sources"]) == original_count:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{source_name}' not found in group '{reference_name}'",
        )

    # Save config
    try:
        _save_transform_config(work_dir, config)
        logger.info(f"Source '{source_name}' removed from group '{reference_name}'")
        return RemoveSourceResponse(
            success=True,
            message=f"Source '{source_name}' removed from configuration",
        )
    except Exception as e:
        logger.exception(f"Error saving transform config: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to save configuration: {str(e)}"
        )


@router.get("/{reference_name}/analyze/{source_name}")
async def analyze_existing_source(
    reference_name: str,
    source_name: str,
):
    """
    Analyze an existing configured source CSV file.

    Returns the same analysis as upload endpoint, but for a file
    already configured in transform.yml.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    work_dir = Path(work_dir)

    # Get source config (now always normalized to dict format with 'groups' key)
    config = _load_transform_config(work_dir)
    group_config = config.get("groups", {}).get(reference_name, {})
    sources = group_config.get("sources", [])

    # Find source
    source_config = None
    for source in sources:
        if source.get("name") == source_name:
            source_config = source
            break

    if not source_config:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{source_name}' not found in group '{reference_name}'",
        )

    # Get file path
    data_path = source_config.get("data", "")
    csv_path = work_dir / data_path

    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"CSV file not found: {data_path}")

    # Analyze
    try:
        analyzer = ClassObjectAnalyzer(csv_path)
        analysis = analyzer.analyze()

        return {
            "source_name": source_name,
            "file_path": data_path,
            "is_valid": analysis.is_valid,
            "delimiter": analysis.delimiter,
            "row_count": analysis.row_count,
            "entity_column": analysis.entity_column,
            "entity_count": analysis.entity_count,
            "class_objects": [
                {
                    "name": co.name,
                    "cardinality": co.cardinality,
                    "value_type": co.value_type,
                    "suggested_plugin": co.suggested_plugin,
                    "confidence": co.confidence,
                }
                for co in analysis.class_objects
            ],
            "validation_errors": analysis.validation_errors,
        }
    except Exception as e:
        logger.exception(f"Error analyzing source: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze source: {str(e)}"
        )
