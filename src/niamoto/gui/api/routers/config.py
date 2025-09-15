"""Configuration management API endpoints for reading and updating YAML configs."""

from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import yaml
import shutil
from datetime import datetime

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
    config_dir = Path.cwd() / "config"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def create_backup(config_path: Path) -> Optional[Path]:
    """Create a backup of the configuration file."""
    if not config_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path.cwd() / "config" / "backups"
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
    config_path = Path.cwd() / "config" / "config.yml"

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
async def get_config(config_name: str) -> Dict[str, Any]:
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
    config_path = Path.cwd() / "config" / f"{config_name}.yml"

    if not config_path.exists():
        # Return empty config structure based on type
        default_configs = {
            "import": {},  # Will be populated with taxonomy, plots, occurrences, shapes as needed
            "transform": {"groups": {}},
            "export": {"exports": [], "static_pages": []},
            "config": {
                "project": {"name": "niamoto-project", "version": "1.0.0"},
                "database": {"path": "db/niamoto.db"},
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

    config_path = Path.cwd() / "config" / f"{config_name}.yml"

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
    backup_dir = Path.cwd() / "config" / "backups"

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
    backup_path = Path.cwd() / "config" / "backups" / backup_filename

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

    config_path = Path.cwd() / "config" / f"{config_name}.yml"

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
