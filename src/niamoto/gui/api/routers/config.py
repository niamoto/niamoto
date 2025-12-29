"""Configuration management API endpoints for reading and updating YAML configs."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import yaml
import shutil
from datetime import datetime

from ..context import get_working_directory

router = APIRouter()


class ConfigUpdate(BaseModel):
    """Request body for updating configuration."""

    content: Union[
        Dict[str, Any], List[Any]
    ]  # Accept both dict and list for transform.yml
    backup: bool = True


class ConfigResponse(BaseModel):
    """Response model for configuration operations."""

    success: bool
    message: str
    content: Optional[Union[Dict[str, Any], List[Any]]] = None
    backup_path: Optional[str] = None


def ensure_config_dir():
    """Ensure the config directory exists."""
    config_dir = get_working_directory() / "config"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def create_backup(config_path: Path) -> Optional[Path]:
    """Create a backup of the configuration file."""
    if not config_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = get_working_directory() / "config" / "backups"
    backup_dir.mkdir(exist_ok=True)

    backup_path = backup_dir / f"{config_path.stem}_{timestamp}.yml"
    shutil.copy2(config_path, backup_path)
    return backup_path


@router.get("/project")
async def get_project_info() -> Dict[str, Any]:
    """
    Get project information from config.yml.

    Returns:
        Project information including name, version, etc.
    """
    config_path = get_working_directory() / "config" / "config.yml"

    if not config_path.exists():
        # Return default project info
        return {"name": "Niamoto Project", "version": "1.0.0"}

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}

        # Extract project section
        project_info = config.get("project", {})
        return {
            "name": project_info.get("name", "Niamoto Project"),
            "version": project_info.get("version", "1.0.0"),
            "niamoto_version": project_info.get("niamoto_version"),
            "created_at": project_info.get("created_at"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading project info: {str(e)}"
        )


# =============================================================================
# References Discovery Endpoint (MUST be before /{config_name} route)
# =============================================================================


class HierarchyFields(BaseModel):
    """Detected hierarchy fields in a reference table."""

    has_nested_set: bool = False  # lft/rght columns present
    has_parent: bool = False  # parent_id column present
    has_level: bool = False  # level column present
    lft_field: Optional[str] = None
    rght_field: Optional[str] = None
    parent_id_field: Optional[str] = None
    level_field: Optional[str] = None
    id_field: Optional[str] = None  # Detected primary key
    name_field: Optional[str] = None  # Detected display name field


class ReferenceInfo(BaseModel):
    """Information about a reference entity from import.yml."""

    name: str
    table_name: str  # Actual table name from EntityRegistry
    kind: str  # "hierarchical" | "flat" | "spatial"
    description: Optional[str] = None
    schema_fields: List[Dict[str, Any]] = []
    entity_count: Optional[int] = None
    is_hierarchical: bool = (
        False  # True if has hierarchy structure (lft/rght or parent_id)
    )
    hierarchy_fields: Optional[HierarchyFields] = None  # Detected hierarchy columns


class ReferencesResponse(BaseModel):
    """Response for listing references."""

    references: List[ReferenceInfo]
    total: int


@router.get("/references", response_model=ReferencesResponse)
async def get_references():
    """
    List all reference entities discovered from import.yml.

    This endpoint dynamically discovers references (group_by targets)
    from the import configuration. No hardcoded entity names.

    Returns:
        List of references with their kind, schema, and entity count.
    """
    config_path = get_working_directory() / "config" / "import.yml"

    if not config_path.exists():
        return ReferencesResponse(references=[], total=0)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        references = []
        entities = import_config.get("entities") or {}
        refs_section = entities.get("references") or {}

        # Early return if no references configured
        if not refs_section:
            return ReferencesResponse(references=[], total=0)

        # Try to get entity info from database (table names and counts)
        db_path = get_working_directory() / "db" / "niamoto.duckdb"
        entity_counts = {}
        table_name_map = {}

        if db_path.exists():
            try:
                from niamoto.common.database import Database
                from niamoto.core.imports.registry import EntityRegistry

                db = Database(str(db_path), read_only=True)
                try:
                    # Get table names from EntityRegistry (if table exists)
                    if db.has_table(EntityRegistry.ENTITIES_TABLE):
                        registry = EntityRegistry(db)
                        for entity in registry.list_entities():
                            table_name_map[entity.name] = entity.table_name

                    # Get counts for each reference
                    for ref_name in refs_section.keys():
                        actual_table = table_name_map.get(
                            ref_name, f"reference_{ref_name}"
                        )
                        if db.has_table(actual_table):
                            import pandas as pd

                            result = pd.read_sql(
                                f"SELECT COUNT(*) as cnt FROM {actual_table}",
                                db.engine,
                            )
                            entity_counts[ref_name] = int(result.iloc[0]["cnt"])
                finally:
                    db.close_db_session()
            except Exception:
                pass  # Continue without counts if DB access fails

        for ref_name, ref_config in refs_section.items():
            if not isinstance(ref_config, dict):
                continue

            kind = ref_config.get("kind", "flat")
            description = ref_config.get("description")

            # Get actual table name from registry, fallback to convention
            actual_table_name = table_name_map.get(ref_name, f"reference_{ref_name}")

            # Extract schema fields
            schema = ref_config.get("schema", {})
            schema_fields = schema.get("fields", [])
            if isinstance(schema_fields, dict):
                # Convert dict format to list format
                schema_fields = [
                    {"name": k, **v} if isinstance(v, dict) else {"name": k, "type": v}
                    for k, v in schema_fields.items()
                ]

            # Detect hierarchy fields from actual table columns
            hierarchy_fields = None
            is_hierarchical = False

            if db_path and db_path.exists():
                try:
                    from niamoto.common.database import Database

                    db = Database(str(db_path), read_only=True)
                    try:
                        if db.has_table(actual_table_name):
                            # Get column names from the table
                            columns_df = pd.read_sql(
                                f"SELECT * FROM {actual_table_name} LIMIT 0",
                                db.engine,
                            )
                            columns = set(columns_df.columns.tolist())

                            # Detect hierarchy structure
                            has_nested_set = "lft" in columns and "rght" in columns
                            has_parent = "parent_id" in columns
                            has_level = "level" in columns

                            is_hierarchical = has_nested_set or (
                                has_parent and has_level
                            )

                            # Detect ID field
                            id_candidates = [f"id_{ref_name}", f"{ref_name}_id", "id"]
                            id_field = next(
                                (c for c in id_candidates if c in columns), None
                            )
                            if not id_field:
                                # Fallback: first column containing 'id'
                                id_field = next(
                                    (c for c in columns if "id" in c.lower()), "id"
                                )

                            # Detect name field
                            name_candidates = [
                                "full_name",
                                "name",
                                "plot",
                                "label",
                                "title",
                                ref_name,
                            ]
                            name_field = next(
                                (c for c in name_candidates if c in columns), None
                            )
                            if not name_field:
                                # Fallback: first string column that's not id
                                name_field = next(
                                    (
                                        c
                                        for c in columns
                                        if c != id_field and "name" in c.lower()
                                    ),
                                    id_field,
                                )

                            hierarchy_fields = HierarchyFields(
                                has_nested_set=has_nested_set,
                                has_parent=has_parent,
                                has_level=has_level,
                                lft_field="lft" if has_nested_set else None,
                                rght_field="rght" if has_nested_set else None,
                                parent_id_field="parent_id" if has_parent else None,
                                level_field="level" if has_level else None,
                                id_field=id_field,
                                name_field=name_field,
                            )
                    finally:
                        db.close_db_session()
                except Exception:
                    pass  # Continue without hierarchy detection if DB access fails

            references.append(
                ReferenceInfo(
                    name=ref_name,
                    table_name=actual_table_name,
                    kind=kind,
                    description=description,
                    schema_fields=schema_fields,
                    entity_count=entity_counts.get(ref_name),
                    is_hierarchical=is_hierarchical,
                    hierarchy_fields=hierarchy_fields,
                )
            )

        return ReferencesResponse(references=references, total=len(references))

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading references: {str(e)}"
        )


# =============================================================================
# Datasets Discovery Endpoint
# =============================================================================


class DatasetInfo(BaseModel):
    """Information about a dataset entity from import.yml."""

    name: str
    table_name: str  # Actual table name from EntityRegistry
    description: Optional[str] = None
    schema_fields: List[Dict[str, Any]] = []
    entity_count: Optional[int] = None


class DatasetsResponse(BaseModel):
    """Response for listing datasets."""

    datasets: List[DatasetInfo]
    total: int


@router.get("/references/{reference_name}/config")
async def get_reference_config(reference_name: str):
    """Get full configuration for a specific reference from import.yml."""
    config_path = get_working_directory() / "config" / "import.yml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="import.yml not found")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        entities = import_config.get("entities") or {}
        refs_section = entities.get("references") or {}

        if reference_name not in refs_section:
            raise HTTPException(
                status_code=404,
                detail=f"Reference '{reference_name}' not found in import.yml",
            )

        return {"name": reference_name, "config": refs_section[reference_name]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading config: {str(e)}")


@router.put("/references/{reference_name}/config")
async def update_reference_config(
    reference_name: str, config: Dict[str, Any] = Body(...)
):
    """Update configuration for a specific reference in import.yml."""
    config_path = get_working_directory() / "config" / "import.yml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="import.yml not found")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        entities = import_config.get("entities") or {}
        refs_section = entities.get("references") or {}

        if reference_name not in refs_section:
            raise HTTPException(
                status_code=404, detail=f"Reference '{reference_name}' not found"
            )

        # Backup before modifying
        create_backup(config_path)

        # Update the reference config
        refs_section[reference_name] = config
        import_config["entities"]["references"] = refs_section

        # Write back
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, default_flow_style=False, sort_keys=False)

        return {
            "success": True,
            "message": f"Reference '{reference_name}' configuration updated",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")


@router.get("/datasets/{dataset_name}/config")
async def get_dataset_config(dataset_name: str):
    """Get full configuration for a specific dataset from import.yml."""
    config_path = get_working_directory() / "config" / "import.yml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="import.yml not found")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        entities = import_config.get("entities") or {}
        datasets_section = entities.get("datasets") or {}

        if dataset_name not in datasets_section:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{dataset_name}' not found in import.yml",
            )

        return {"name": dataset_name, "config": datasets_section[dataset_name]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading config: {str(e)}")


@router.put("/datasets/{dataset_name}/config")
async def update_dataset_config(dataset_name: str, config: Dict[str, Any] = Body(...)):
    """Update configuration for a specific dataset in import.yml."""
    config_path = get_working_directory() / "config" / "import.yml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="import.yml not found")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        entities = import_config.get("entities") or {}
        datasets_section = entities.get("datasets") or {}

        if dataset_name not in datasets_section:
            raise HTTPException(
                status_code=404, detail=f"Dataset '{dataset_name}' not found"
            )

        # Backup before modifying
        create_backup(config_path)

        # Update the dataset config
        datasets_section[dataset_name] = config
        import_config["entities"]["datasets"] = datasets_section

        # Write back
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(import_config, f, default_flow_style=False, sort_keys=False)

        return {
            "success": True,
            "message": f"Dataset '{dataset_name}' configuration updated",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")


@router.get("/datasets", response_model=DatasetsResponse)
async def get_datasets():
    """
    List all dataset entities discovered from import.yml.

    Returns:
        List of datasets with their schema and entity count.
    """
    config_path = get_working_directory() / "config" / "import.yml"

    if not config_path.exists():
        return DatasetsResponse(datasets=[], total=0)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        datasets = []
        entities = import_config.get("entities") or {}
        datasets_section = entities.get("datasets") or {}

        if not datasets_section:
            return DatasetsResponse(datasets=[], total=0)

        # Get entity info from database
        db_path = get_working_directory() / "db" / "niamoto.duckdb"
        entity_counts = {}
        table_name_map = {}

        if db_path.exists():
            try:
                from niamoto.common.database import Database
                from niamoto.core.imports.registry import EntityRegistry
                import pandas as pd

                db = Database(str(db_path), read_only=True)
                try:
                    if db.has_table(EntityRegistry.ENTITIES_TABLE):
                        registry = EntityRegistry(db)
                        for entity in registry.list_entities():
                            table_name_map[entity.name] = entity.table_name

                    for ds_name in datasets_section.keys():
                        actual_table = table_name_map.get(ds_name, f"dataset_{ds_name}")
                        if db.has_table(actual_table):
                            result = pd.read_sql(
                                f"SELECT COUNT(*) as cnt FROM {actual_table}",
                                db.engine,
                            )
                            entity_counts[ds_name] = int(result.iloc[0]["cnt"])
                finally:
                    db.close_db_session()
            except Exception:
                pass

        for ds_name, ds_config in datasets_section.items():
            if not isinstance(ds_config, dict):
                continue

            description = ds_config.get("description")
            actual_table_name = table_name_map.get(ds_name, f"dataset_{ds_name}")

            schema = ds_config.get("schema", {})
            schema_fields = schema.get("fields", [])
            if isinstance(schema_fields, dict):
                schema_fields = [
                    {"name": k, **v} if isinstance(v, dict) else {"name": k, "type": v}
                    for k, v in schema_fields.items()
                ]

            datasets.append(
                DatasetInfo(
                    name=ds_name,
                    table_name=actual_table_name,
                    description=description,
                    schema_fields=schema_fields,
                    entity_count=entity_counts.get(ds_name),
                )
            )

        return DatasetsResponse(datasets=datasets, total=len(datasets))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading datasets: {str(e)}")


# =============================================================================
# Configuration CRUD Endpoints
# =============================================================================


@router.get("/{config_name}")
async def get_config(config_name: str):
    """
    Get a configuration file by name.

    Args:
        config_name: Name of the configuration (import, transform, export, config)

    Returns:
        The configuration content as a dictionary
    """
    # Validate config name
    valid_configs = ["import", "transform", "export", "config"]
    if config_name not in valid_configs:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid configuration name. Must be one of: {valid_configs}",
        )

    # Check in config/ directory
    config_path = get_working_directory() / "config" / f"{config_name}.yml"

    if not config_path.exists():
        # Return empty config structure based on type
        default_configs = {
            "import": {},  # Will be populated with taxonomy, plots, occurrences, shapes as needed
            "transform": {"groups": {}},
            "export": {"exports": [], "static_pages": []},
            "config": {
                "project": {"name": "niamoto-project", "version": "1.0.0"},
                "database": {"path": "db/niamoto.duckdb"},
            },
        }
        return default_configs.get(config_name, {})

    try:
        with open(config_path, "r") as f:
            content = yaml.safe_load(f) or {}
        return content
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading configuration: {str(e)}"
        )


@router.put("/{config_name}")
async def update_config(config_name: str, update: ConfigUpdate) -> ConfigResponse:
    """
    Update a configuration file.

    Args:
        config_name: Name of the configuration (import, transform, export, config)
        update: Configuration update with new content and backup option

    Returns:
        Success response with backup path if created
    """
    # Validate config name
    valid_configs = ["import", "transform", "export", "config"]
    if config_name not in valid_configs:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid configuration name. Must be one of: {valid_configs}",
        )

    # Ensure config directory exists
    ensure_config_dir()

    config_path = get_working_directory() / "config" / f"{config_name}.yml"

    try:
        # Create backup if requested and file exists
        backup_path = None
        if update.backup and config_path.exists():
            backup_path = create_backup(config_path)

        # Write new configuration
        with open(config_path, "w") as f:
            yaml.safe_dump(update.content, f, default_flow_style=False, sort_keys=False)

        return ConfigResponse(
            success=True,
            message=f"Configuration '{config_name}' updated successfully",
            content=update.content,
            backup_path=str(backup_path) if backup_path else None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating configuration: {str(e)}"
        )


@router.post("/{config_name}/validate")
async def validate_config(
    config_name: str, content: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Validate a configuration without saving it.

    Args:
        config_name: Name of the configuration (import, transform, export)
        content: Configuration content to validate

    Returns:
        Validation result with any errors or warnings
    """
    validation_result = {"valid": True, "errors": [], "warnings": []}

    try:
        if config_name == "import":
            # Validate import configuration (Niamoto format)
            if not content:
                validation_result["errors"].append("Configuration is empty")
                validation_result["valid"] = False
            else:
                has_data_sources = False
                # Check for standard import keys
                for key in ["taxonomy", "plots", "occurrences", "shapes"]:
                    if key in content:
                        has_data_sources = True
                        value = content[key]
                        if isinstance(value, dict):
                            if "path" not in value and "file" not in value:
                                validation_result["warnings"].append(
                                    f"{key} has no path or file specified"
                                )
                        elif key == "shapes" and isinstance(value, list):
                            for idx, shape in enumerate(value):
                                if "path" not in shape and "file" not in shape:
                                    validation_result["warnings"].append(
                                        f"Shape {idx} has no path or file specified"
                                    )

                if not has_data_sources:
                    validation_result["errors"].append(
                        "No data sources defined (taxonomy, plots, occurrences, or shapes)"
                    )
                    validation_result["valid"] = False

        elif config_name == "transform":
            # Validate transform configuration
            if "groups" not in content:
                validation_result["warnings"].append("No transform groups defined")
            elif not isinstance(content["groups"], dict):
                validation_result["errors"].append("'groups' must be an object")
                validation_result["valid"] = False
            else:
                for group_name, group_config in content["groups"].items():
                    if not isinstance(group_config, dict):
                        validation_result["errors"].append(
                            f"Group '{group_name}' must be an object"
                        )
                        validation_result["valid"] = False
                    elif "source" not in group_config:
                        validation_result["errors"].append(
                            f"Group '{group_name}' missing 'source' field"
                        )
                        validation_result["valid"] = False

        elif config_name == "export":
            # Validate export configuration
            has_exports = "exports" in content and content["exports"]
            has_static = "static_pages" in content and content["static_pages"]

            if not has_exports and not has_static:
                validation_result["warnings"].append(
                    "No exports or static pages defined"
                )

            if "exports" in content and not isinstance(content["exports"], list):
                validation_result["errors"].append("'exports' must be a list")
                validation_result["valid"] = False

            if "static_pages" in content and not isinstance(
                content["static_pages"], list
            ):
                validation_result["errors"].append("'static_pages' must be a list")
                validation_result["valid"] = False

        elif config_name == "config":
            # Validate main configuration
            if "project" not in content:
                validation_result["warnings"].append("Missing 'project' section")
            elif "name" not in content.get("project", {}):
                validation_result["warnings"].append("Missing project name")

            if "database" not in content:
                validation_result["errors"].append("Missing 'database' section")
                validation_result["valid"] = False
            elif "path" not in content.get("database", {}):
                validation_result["errors"].append("Missing database path")
                validation_result["valid"] = False

        return validation_result

    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Validation error: {str(e)}"],
            "warnings": [],
        }


@router.get("/{config_name}/backup/list")
async def list_backups(config_name: str) -> Dict[str, Any]:
    """
    List all backups for a configuration.

    Args:
        config_name: Name of the configuration

    Returns:
        List of backup files with metadata
    """
    backup_dir = get_working_directory() / "config" / "backups"

    if not backup_dir.exists():
        return {"backups": []}

    backups = []
    for backup_file in backup_dir.glob(f"{config_name}_*.yml"):
        stat = backup_file.stat()
        backups.append(
            {
                "filename": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )

    # Sort by modification time, newest first
    backups.sort(key=lambda x: x["modified"], reverse=True)

    return {"backups": backups}


@router.post("/{config_name}/backup/restore")
async def restore_backup(
    config_name: str, backup_filename: str = Body(..., embed=True)
) -> ConfigResponse:
    """
    Restore a configuration from a backup.

    Args:
        config_name: Name of the configuration
        backup_filename: Name of the backup file to restore

    Returns:
        Success response
    """
    backup_path = get_working_directory() / "config" / "backups" / backup_filename

    if not backup_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Backup file not found: {backup_filename}"
        )

    # Validate that this is a backup for the correct config
    if not backup_filename.startswith(f"{config_name}_"):
        raise HTTPException(
            status_code=400,
            detail=f"Backup file does not match configuration type: {config_name}",
        )

    config_path = get_working_directory() / "config" / f"{config_name}.yml"

    try:
        # Create a backup of current config before restoring
        current_backup = None
        if config_path.exists():
            current_backup = create_backup(config_path)

        # Restore from backup
        shutil.copy2(backup_path, config_path)

        # Read the restored content
        with open(config_path, "r") as f:
            content = yaml.safe_load(f)

        return ConfigResponse(
            success=True,
            message=f"Configuration restored from {backup_filename}",
            content=content,
            backup_path=str(current_backup) if current_backup else None,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restoring backup: {str(e)}")


# ============================================================================
# EntityRegistry v2 Endpoints
# ============================================================================


class ImportConfigValidateRequest(BaseModel):
    """Request body for validating EntityRegistry v2 import config."""

    config: str  # YAML string


class ImportConfigValidateResponse(BaseModel):
    """Response for validation request."""

    valid: bool
    errors: Dict[str, list]  # entity_id -> list of errors
    warnings: Dict[str, list]  # entity_id -> list of warnings


class ImportConfigSaveRequest(BaseModel):
    """Request body for saving import config."""

    config: str  # YAML string


class ImportConfigSaveResponse(BaseModel):
    """Response for save request."""

    success: bool
    message: str
    path: str
    backup_path: Optional[str] = None


@router.post("/import/v2/validate", response_model=ImportConfigValidateResponse)
async def validate_import_v2(request: ImportConfigValidateRequest):
    """
    Validate EntityRegistry v2 import configuration.

    This endpoint validates the YAML structure and EntityRegistry v2 compliance
    without saving the configuration. It checks:
    - YAML syntax validity
    - EntityRegistry v2 structure (version, entities, datasets, references)
    - Entity names (unique, snake_case)
    - Required fields per entity type
    - Connector configurations
    - Schema field mappings
    - Entity links and references

    Args:
        request: Validation request with YAML config string

    Returns:
        Validation result with errors and warnings per entity
    """
    try:
        # Parse YAML
        try:
            config_dict = yaml.safe_load(request.config)
        except yaml.YAMLError as e:
            return ImportConfigValidateResponse(
                valid=False,
                errors={"_global": [f"Invalid YAML syntax: {str(e)}"]},
                warnings={},
            )

        # Guard: Check if config_dict is a valid dictionary
        if not isinstance(config_dict, dict):
            return ImportConfigValidateResponse(
                valid=False,
                errors={
                    "_global": [
                        "Invalid YAML: configuration must be a valid YAML object, not empty or null"
                    ]
                },
                warnings={},
            )

        errors = {}
        warnings = {}

        # Check version
        if "version" not in config_dict:
            errors["_global"] = errors.get("_global", [])
            errors["_global"].append("Missing 'version' field")

        # Check entities structure
        if "entities" not in config_dict:
            errors["_global"] = errors.get("_global", [])
            errors["_global"].append("Missing 'entities' section")
            return ImportConfigValidateResponse(
                valid=False, errors=errors, warnings=warnings
            )

        entities_section = config_dict["entities"]
        if not isinstance(entities_section, dict):
            errors["_global"] = errors.get("_global", [])
            errors["_global"].append("'entities' must be an object")
            return ImportConfigValidateResponse(
                valid=False, errors=errors, warnings=warnings
            )

        # Validate datasets
        datasets = entities_section.get("datasets", {})
        if not isinstance(datasets, dict):
            errors["_datasets"] = ["'datasets' must be an object"]
        else:
            for entity_name, entity_config in datasets.items():
                entity_errors = []
                entity_warnings = []

                # Validate entity name format
                if not entity_name or not isinstance(entity_name, str):
                    entity_errors.append("Entity name is required")
                elif not entity_name.replace("_", "").replace("-", "").isalnum():
                    entity_errors.append(
                        "Entity name must be alphanumeric with underscores/hyphens"
                    )

                # Validate connector
                if not isinstance(entity_config, dict):
                    entity_errors.append("Entity configuration must be an object")
                elif "connector" not in entity_config:
                    entity_errors.append("Missing 'connector' field")
                else:
                    connector = entity_config["connector"]
                    if "type" not in connector:
                        entity_errors.append("Missing connector type")
                    elif connector["type"] == "file":
                        if "format" not in connector:
                            entity_errors.append("Missing file format")
                        if "path" not in connector:
                            entity_warnings.append("No file path specified")

                # Validate schema
                if "schema" not in entity_config:
                    entity_warnings.append("Missing schema configuration")
                elif not isinstance(entity_config["schema"], dict):
                    entity_errors.append("Schema must be an object")

                if entity_errors:
                    errors[f"dataset.{entity_name}"] = entity_errors
                if entity_warnings:
                    warnings[f"dataset.{entity_name}"] = entity_warnings

        # Validate references
        references = entities_section.get("references", {})
        if not isinstance(references, dict):
            errors["_references"] = ["'references' must be an object"]
        else:
            for entity_name, entity_config in references.items():
                entity_errors = []
                entity_warnings = []

                # Validate entity name format
                if not entity_name or not isinstance(entity_name, str):
                    entity_errors.append("Entity name is required")
                elif not entity_name.replace("_", "").replace("-", "").isalnum():
                    entity_errors.append(
                        "Entity name must be alphanumeric with underscores/hyphens"
                    )

                if not isinstance(entity_config, dict):
                    entity_errors.append("Entity configuration must be an object")
                else:
                    # Validate kind
                    if "kind" not in entity_config:
                        entity_errors.append("Missing 'kind' field for reference")
                    elif entity_config["kind"] not in [
                        "hierarchical",
                        "spatial",
                        "flat",
                    ]:
                        entity_errors.append(
                            "Kind must be 'hierarchical', 'spatial', or 'flat'"
                        )

                    # Validate hierarchical specific
                    if entity_config.get("kind") == "hierarchical":
                        if "hierarchy" not in entity_config:
                            entity_errors.append(
                                "Missing 'hierarchy' configuration for hierarchical reference"
                            )
                        elif not isinstance(entity_config["hierarchy"], dict):
                            entity_errors.append(
                                "Hierarchy configuration must be an object"
                            )
                        else:
                            hierarchy = entity_config["hierarchy"]
                            if "levels" not in hierarchy:
                                entity_errors.append(
                                    "Missing 'levels' in hierarchy configuration"
                                )
                            elif not isinstance(hierarchy["levels"], list):
                                entity_errors.append("Hierarchy levels must be a list")
                            elif len(hierarchy["levels"]) < 2:
                                entity_warnings.append(
                                    "Hierarchy should have at least 2 levels"
                                )

                    # Validate spatial specific
                    if entity_config.get("kind") == "spatial":
                        if "connector" in entity_config:
                            connector = entity_config["connector"]
                            if connector.get("type") != "file_multi_feature":
                                entity_errors.append(
                                    "Spatial references must use 'file_multi_feature' connector"
                                )

                    # Validate connector
                    if "connector" not in entity_config:
                        entity_errors.append("Missing 'connector' field")

                if entity_errors:
                    errors[f"reference.{entity_name}"] = entity_errors
                if entity_warnings:
                    warnings[f"reference.{entity_name}"] = entity_warnings

        # Global validation
        if not datasets and not references:
            warnings["_global"] = warnings.get("_global", [])
            warnings["_global"].append("No datasets or references configured")

        return ImportConfigValidateResponse(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    except Exception as e:
        return ImportConfigValidateResponse(
            valid=False,
            errors={"_global": [f"Validation error: {str(e)}"]},
            warnings={},
        )


@router.put("/import/v2", response_model=ImportConfigSaveResponse)
async def save_import_v2(request: ImportConfigSaveRequest):
    """
    Save EntityRegistry v2 import configuration to import.yml.

    This endpoint:
    1. Validates the YAML syntax
    2. Creates a backup of the existing import.yml (if it exists)
    3. Writes the new configuration to config/import.yml

    Args:
        request: Save request with YAML config string

    Returns:
        Success response with file path and backup path

    Raises:
        HTTPException: If YAML is invalid or file operation fails
    """
    try:
        # Validate YAML syntax first
        try:
            yaml.safe_load(request.config)
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid YAML syntax: {str(e)}"
            )

        # Ensure config directory exists
        config_dir = ensure_config_dir()
        config_path = config_dir / "import.yml"

        # Create backup if file exists
        backup_path = None
        if config_path.exists():
            backup_path = create_backup(config_path)

        # Write new configuration
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(request.config)

        return ImportConfigSaveResponse(
            success=True,
            message="Import configuration saved successfully",
            path=str(config_path),
            backup_path=str(backup_path) if backup_path else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving configuration: {str(e)}"
        )


@router.get("/import/v2/schema")
async def get_import_v2_schema():
    """
    Get JSON Schema for EntityRegistry v2 import configuration.

    Returns a JSON Schema that describes the structure of a valid
    EntityRegistry v2 import.yml file. This schema can be used for:
    - Frontend validation
    - IDE autocompletion
    - Documentation generation

    Returns:
        JSON Schema object
    """
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "EntityRegistry v2 Import Configuration",
        "type": "object",
        "required": ["version", "entities"],
        "properties": {
            "version": {
                "type": "string",
                "description": "Configuration version",
                "const": "1.0",
            },
            "entities": {
                "type": "object",
                "description": "Entity definitions",
                "properties": {
                    "datasets": {
                        "type": "object",
                        "description": "Dataset entities (observations, occurrences, etc.)",
                        "additionalProperties": {"$ref": "#/definitions/DatasetEntity"},
                    },
                    "references": {
                        "type": "object",
                        "description": "Reference entities (taxonomy, locations, etc.)",
                        "additionalProperties": {
                            "$ref": "#/definitions/ReferenceEntity"
                        },
                    },
                },
            },
        },
        "definitions": {
            "DatasetEntity": {
                "type": "object",
                "required": ["connector", "schema"],
                "properties": {
                    "description": {"type": "string"},
                    "connector": {"$ref": "#/definitions/Connector"},
                    "schema": {"$ref": "#/definitions/Schema"},
                    "links": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/Link"},
                    },
                    "options": {"$ref": "#/definitions/Options"},
                },
            },
            "ReferenceEntity": {
                "type": "object",
                "required": ["kind", "connector"],
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["hierarchical", "spatial", "flat"],
                    },
                    "description": {"type": "string"},
                    "connector": {"$ref": "#/definitions/Connector"},
                    "schema": {"$ref": "#/definitions/Schema"},
                    "hierarchy": {"$ref": "#/definitions/Hierarchy"},
                    "enrichment": {"$ref": "#/definitions/Enrichment"},
                },
            },
            "Connector": {
                "type": "object",
                "required": ["type"],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "file",
                            "derived",
                            "file_multi_feature",
                            "database",
                            "api",
                        ],
                    },
                    "format": {
                        "type": "string",
                        "enum": ["csv", "excel", "json", "geojson"],
                    },
                    "path": {"type": "string"},
                    "source": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "path", "name_field"],
                            "properties": {
                                "name": {"type": "string"},
                                "path": {"type": "string"},
                                "name_field": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "Schema": {
                "type": "object",
                "properties": {
                    "id_field": {"type": "string"},
                    "fields": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "geometry_field": {"type": "string"},
                },
            },
            "Link": {
                "type": "object",
                "required": ["entity", "field", "target_field"],
                "properties": {
                    "entity": {"type": "string"},
                    "field": {"type": "string"},
                    "target_field": {"type": "string"},
                },
            },
            "Options": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["replace", "append"]},
                    "chunk_size": {"type": "integer"},
                },
            },
            "Hierarchy": {
                "type": "object",
                "required": ["strategy", "levels"],
                "properties": {
                    "strategy": {
                        "type": "string",
                        "enum": ["adjacency_list", "nested_set"],
                    },
                    "levels": {"type": "array", "items": {"type": "string"}},
                    "incomplete_rows": {"type": "string", "enum": ["skip", "keep"]},
                    "id_strategy": {"type": "string", "enum": ["hash", "auto"]},
                    "id_column": {"type": "string"},
                    "name_column": {"type": "string"},
                },
            },
            "Enrichment": {
                "type": "object",
                "required": ["plugin", "enabled"],
                "properties": {
                    "plugin": {"type": "string"},
                    "enabled": {"type": "boolean"},
                    "config": {"type": "object"},
                },
            },
        },
    }

    return schema
