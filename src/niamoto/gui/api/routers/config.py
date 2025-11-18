"""Configuration management API endpoints for reading and updating YAML configs."""

from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import yaml
import shutil
from datetime import datetime

from ..context import get_working_directory

router = APIRouter()


class ConfigUpdate(BaseModel):
    """Request body for updating configuration."""

    content: Dict[str, Any]
    backup: bool = True


class ConfigResponse(BaseModel):
    """Response model for configuration operations."""

    success: bool
    message: str
    content: Optional[Dict[str, Any]] = None
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
