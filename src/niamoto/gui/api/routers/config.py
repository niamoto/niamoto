"""Configuration management API endpoints for reading and updating YAML configs."""

from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, Literal, Optional, List, Union
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
import re
import yaml
import shutil
from datetime import datetime

from ..context import get_working_directory
from niamoto.gui.api.services.templates.config_service import (
    load_transform_config as _load_transform_config_impl,
    save_transform_config as _save_transform_config_impl,
    load_export_config as _load_export_config_impl,
    save_export_config as _save_export_config_impl,
    find_transform_group as _find_transform_group_impl,
    find_export_group as _find_export_group_impl,
    find_or_create_transform_group as _find_or_create_transform_group_impl,
)
from niamoto.core.plugins.models import ExportConfig as ExportConfigModel
from niamoto.common.hierarchy_context import (
    build_hierarchy_contexts,
    detect_hierarchy_metadata,
    normalize_hierarchy_key,
)
from niamoto.common.i18n import LocalizedString

router = APIRouter()


# Wrapper functions for backward compatibility (use get_working_directory)
def _load_transform_config() -> List[Dict[str, Any]]:
    """Load transform.yml using centralized service."""
    return _load_transform_config_impl(get_working_directory())


def _save_transform_config(groups: List[Dict[str, Any]]) -> None:
    """Save transform.yml using centralized service with backup."""
    _save_transform_config_impl(get_working_directory(), groups, create_backup=True)


def _load_export_config() -> Dict[str, Any]:
    """Load export.yml using centralized service."""
    return _load_export_config_impl(get_working_directory())


def _save_export_config(config: Dict[str, Any]) -> None:
    """Save export.yml using centralized service with backup."""
    _save_export_config_impl(get_working_directory(), config, create_backup=True)


def _find_transform_group(
    groups: List[Dict[str, Any]], group_by: str
) -> Optional[Dict[str, Any]]:
    """Find a group by group_by value using centralized service."""
    return _find_transform_group_impl(groups, group_by)


def _find_export_group(
    export_config: Dict[str, Any], group_by: str
) -> Optional[Dict[str, Any]]:
    """Find export group by group_by value using centralized service."""
    return _find_export_group_impl(export_config, group_by)


def _list_api_export_targets(export_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List export targets backed by the JSON API exporter."""
    return [
        export_entry
        for export_entry in export_config.get("exports", [])
        if export_entry.get("exporter") == "json_api_exporter"
    ]


def _find_api_export_target(
    export_config: Dict[str, Any], export_name: str
) -> Optional[Dict[str, Any]]:
    """Find a JSON API export target by name."""
    for export_entry in _list_api_export_targets(export_config):
        if export_entry.get("name") == export_name:
            return export_entry
    return None


def _find_target_group(
    export_target: Dict[str, Any], group_by: str
) -> Optional[Dict[str, Any]]:
    """Find a group configuration inside a specific export target."""
    for group in export_target.get("groups", []) or []:
        if group.get("group_by") == group_by:
            return group
    return None


def _default_dwc_transformer_params(group_by: str) -> Dict[str, Any]:
    """Provide safe defaults when enabling a new DwC target for a group."""
    return {
        "occurrence_list_source": "occurrences",
        "occurrence_table": "occurrences",
        "taxonomy_entity": group_by,
        "taxon_id_column": "id_taxonref",
        "taxon_id_field": "id",
        "mapping": {},
    }


def _build_default_api_group_config(export_name: str, group_by: str) -> Dict[str, Any]:
    """Build the default group payload returned to the UI."""
    return {
        "enabled": False,
        "group_by": group_by,
        "detail": {"pass_through": True},
        "index": {"fields": []},
    }


def _validate_export_config_or_raise(export_config: Dict[str, Any]) -> None:
    """Validate export.yml against typed exporter models."""
    try:
        ExportConfigModel.model_validate(export_config)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid export configuration: {str(exc)}",
        ) from exc


def _is_known_reference(group_by: str) -> bool:
    """Vérifie que group_by correspond à une référence déclarée dans import.yml."""
    try:
        work_dir = get_working_directory()
        import_path = work_dir / "config" / "import.yml"
        if not import_path.exists():
            return False
        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}
        references = import_config.get("entities", {}).get("references", {}) or {}
        return group_by in references
    except Exception:
        return False


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
        with open(config_path, "r", encoding="utf-8") as f:
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
    kind: str  # "hierarchical" | "generic" | "spatial"
    description: Optional[str] = None
    schema_fields: List[Dict[str, Any]] = []
    entity_count: Optional[int] = None
    can_enrich: bool = False
    enrichment_enabled: bool = False
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

            kind = ref_config.get("kind", "generic")
            description = ref_config.get("description")
            enrichment_config = ref_config.get("enrichment") or []
            enrichment_enabled = any(
                isinstance(item, dict) and item.get("enabled")
                for item in enrichment_config
            )
            can_enrich = kind == "hierarchical" or bool(enrichment_config)

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
                    can_enrich=can_enrich,
                    enrichment_enabled=enrichment_enabled,
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
        with open(config_path, "r", encoding="utf-8") as f:
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
        with open(config_path, "w", encoding="utf-8") as f:
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
        with open(config_path, "r", encoding="utf-8") as f:
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
                        "generic",
                    ]:
                        entity_errors.append(
                            "Kind must be 'hierarchical', 'spatial', or 'generic'"
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
                        "enum": ["hierarchical", "spatial", "generic"],
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


# =============================================================================
# Widget CRUD Endpoints for Transform and Export configurations
# =============================================================================


class TransformWidgetUpdate(BaseModel):
    """Request body for updating a transform widget."""

    plugin: str
    params: Dict[str, Any] = {}


class ExportWidgetUpdate(BaseModel):
    """Request body for updating an export widget."""

    plugin: str
    data_source: str
    title: Optional[str] = None
    description: Optional[str] = None
    params: Dict[str, Any] = {}


class WidgetSummary(BaseModel):
    """Summary of a widget configuration."""

    id: str
    plugin: str
    params: Dict[str, Any] = {}


def _resolve_export_widget_id(group_by: str, widget: Dict[str, Any]) -> Optional[str]:
    """Return the frontend identifier used for an export widget."""
    data_source = widget.get("data_source")
    if data_source:
        return str(data_source)
    if widget.get("plugin") == "hierarchical_nav_widget":
        return f"{group_by}_hierarchical_nav_widget"
    return None


@router.get("/transform/{group_by}/widgets")
async def list_transform_widgets(group_by: str) -> List[WidgetSummary]:
    """
    List all widgets in transform.yml for a specific group.

    Args:
        group_by: The group name (e.g., 'taxons', 'plots', 'shapes')

    Returns:
        List of widget summaries
    """
    try:
        groups = _load_transform_config()
        group = _find_transform_group(groups, group_by)

        if not group:
            return []

        widgets_data = group.get("widgets_data", {})
        widgets = []

        for widget_id, widget_config in widgets_data.items():
            widgets.append(
                WidgetSummary(
                    id=widget_id,
                    plugin=widget_config.get("plugin", ""),
                    params=widget_config.get("params", {}),
                )
            )

        return widgets

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing widgets: {str(e)}")


@router.get("/transform/{group_by}/widgets/{widget_id}")
async def get_transform_widget(group_by: str, widget_id: str) -> WidgetSummary:
    """
    Get a specific widget from transform.yml.

    Args:
        group_by: The group name
        widget_id: The widget identifier

    Returns:
        Widget summary
    """
    try:
        groups = _load_transform_config()
        group = _find_transform_group(groups, group_by)

        if not group:
            raise HTTPException(status_code=404, detail=f"Group '{group_by}' not found")

        widgets_data = group.get("widgets_data", {})
        if widget_id not in widgets_data:
            raise HTTPException(
                status_code=404,
                detail=f"Widget '{widget_id}' not found in group '{group_by}'",
            )

        widget_config = widgets_data[widget_id]
        return WidgetSummary(
            id=widget_id,
            plugin=widget_config.get("plugin", ""),
            params=widget_config.get("params", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting widget: {str(e)}")


@router.put("/transform/{group_by}/widgets/{widget_id}")
async def update_transform_widget(
    group_by: str, widget_id: str, update: TransformWidgetUpdate
) -> WidgetSummary:
    """
    Create or update a widget in transform.yml.

    Args:
        group_by: The group name
        widget_id: The widget identifier
        update: Widget configuration

    Returns:
        Updated widget summary
    """
    try:
        groups = _load_transform_config()
        group = _find_transform_group(groups, group_by)

        if not group:
            # Auto-créer seulement si le group_by est une référence connue
            if not _is_known_reference(group_by):
                raise HTTPException(
                    status_code=404,
                    detail=f"Group '{group_by}' not found and is not a known reference in import.yml",
                )
            group = _find_or_create_transform_group_impl(groups, group_by)

        if "widgets_data" not in group:
            group["widgets_data"] = {}

        group["widgets_data"][widget_id] = {
            "plugin": update.plugin,
            "params": update.params,
        }

        _save_transform_config(groups)

        return WidgetSummary(
            id=widget_id,
            plugin=update.plugin,
            params=update.params,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating widget: {str(e)}")


@router.delete("/transform/{group_by}/widgets/{widget_id}")
async def delete_transform_widget(group_by: str, widget_id: str) -> Dict[str, bool]:
    """
    Delete a widget from transform.yml.

    Args:
        group_by: The group name
        widget_id: The widget identifier

    Returns:
        Success status
    """
    try:
        groups = _load_transform_config()
        group = _find_transform_group(groups, group_by)

        if not group:
            raise HTTPException(status_code=404, detail=f"Group '{group_by}' not found")

        widgets_data = group.get("widgets_data", {})
        if widget_id not in widgets_data:
            raise HTTPException(
                status_code=404,
                detail=f"Widget '{widget_id}' not found in group '{group_by}'",
            )

        del widgets_data[widget_id]
        _save_transform_config(groups)

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting widget: {str(e)}")


@router.get("/export/{group_by}/widgets")
async def list_export_widgets(group_by: str) -> List[Dict[str, Any]]:
    """
    List all widgets in export.yml for a specific group.

    Args:
        group_by: The group name (e.g., 'taxons', 'plots', 'shapes')

    Returns:
        List of widget configurations
    """
    try:
        export_config = _load_export_config()
        group = _find_export_group(export_config, group_by)

        if not group:
            return []

        return group.get("widgets", [])

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing export widgets: {str(e)}"
        )


@router.put("/export/{group_by}/widgets/{widget_id}")
async def update_export_widget(
    group_by: str, widget_id: str, update: ExportWidgetUpdate
) -> Dict[str, Any]:
    """
    Create or update a widget in export.yml.

    The widget_id corresponds to the data_source field.

    Args:
        group_by: The group name
        widget_id: The widget identifier (data_source)
        update: Widget configuration

    Returns:
        Updated widget configuration
    """
    try:
        export_config = _load_export_config()

        # Find the export entry with groups
        target_group = None

        for export_entry in export_config.get("exports", []):
            groups = export_entry.get("groups") or export_entry.get("params", {}).get(
                "groups", []
            )
            for group in groups:
                if group.get("group_by") == group_by:
                    target_group = group
                    break
            if target_group:
                break

        if not target_group:
            # Auto-créer seulement si le group_by est une référence connue
            if not _is_known_reference(group_by):
                raise HTTPException(
                    status_code=404,
                    detail=f"Group '{group_by}' not found in export config and is not a known reference in import.yml",
                )
            exports = export_config.setdefault("exports", [])
            web_export = None
            for entry in exports:
                if isinstance(entry, dict) and entry.get("name") == "web_pages":
                    web_export = entry
                    break
            if not web_export:
                web_export = {
                    "name": "web_pages",
                    "enabled": True,
                    "exporter": "html_page_exporter",
                    "groups": [],
                }
                exports.append(web_export)
            target_group = {"group_by": group_by, "widgets": []}
            web_export.setdefault("groups", []).append(target_group)

        # Ensure widgets list exists
        if "widgets" not in target_group:
            target_group["widgets"] = []

        # Find existing widget by data_source or synthetic navigation id
        existing_idx = None
        for idx, widget in enumerate(target_group["widgets"]):
            if _resolve_export_widget_id(group_by, widget) == widget_id:
                existing_idx = idx
                break

        new_widget = {
            "plugin": update.plugin,
            "data_source": (
                "" if update.plugin == "hierarchical_nav_widget" else update.data_source
            ),
            "params": update.params,
        }
        if update.title:
            new_widget["title"] = update.title
        if update.description:
            new_widget["description"] = update.description

        if existing_idx is not None:
            target_group["widgets"][existing_idx] = new_widget
        else:
            target_group["widgets"].append(new_widget)

        _save_export_config(export_config)

        return new_widget

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating export widget: {str(e)}"
        )


@router.delete("/export/{group_by}/widgets/{widget_id}")
async def delete_export_widget(group_by: str, widget_id: str) -> Dict[str, bool]:
    """
    Delete a widget from export.yml.

    The widget_id corresponds to the data_source field.

    Args:
        group_by: The group name
        widget_id: The widget identifier (data_source)

    Returns:
        Success status
    """
    try:
        export_config = _load_export_config()

        # Find the group
        target_group = None
        for export_entry in export_config.get("exports", []):
            groups = export_entry.get("groups") or export_entry.get("params", {}).get(
                "groups", []
            )
            for group in groups:
                if group.get("group_by") == group_by:
                    target_group = group
                    break
            if target_group:
                break

        if not target_group:
            raise HTTPException(
                status_code=404, detail=f"Group '{group_by}' not found in export config"
            )

        widgets = target_group.get("widgets", [])
        original_len = len(widgets)

        # Filter out the widget
        target_group["widgets"] = [
            w for w in widgets if _resolve_export_widget_id(group_by, w) != widget_id
        ]

        if len(target_group["widgets"]) == original_len:
            raise HTTPException(
                status_code=404,
                detail=f"Widget '{widget_id}' not found in group '{group_by}'",
            )

        _save_export_config(export_config)

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting export widget: {str(e)}"
        )


# =============================================================================
# Index Generator Configuration Endpoints
# =============================================================================


class IndexGeneratorPageConfigUpdate(BaseModel):
    """Page configuration for index generator."""

    title: LocalizedString
    description: Optional[LocalizedString] = None
    items_per_page: int = 24


class IndexGeneratorFilterUpdate(BaseModel):
    """Filter configuration for index generator."""

    field: str
    values: List[Any]
    operator: str = "in"


class IndexGeneratorDisplayFieldUpdate(BaseModel):
    """Display field configuration for index generator."""

    name: str
    source: str
    fallback: Optional[str] = None
    type: str = "text"
    label: Optional[LocalizedString] = None
    searchable: bool = False
    format: Optional[str] = None
    mapping: Optional[Dict[str, str]] = None
    filter_options: Optional[List[Dict[str, str]]] = None
    dynamic_options: bool = False
    inline_badge: bool = False
    true_label: Optional[LocalizedString] = None
    false_label: Optional[LocalizedString] = None
    badge_color: Optional[str] = None
    badge_style: Optional[str] = None
    badge_colors: Optional[Dict[str, str]] = None
    badge_styles: Optional[Dict[str, str]] = None
    tooltip_mapping: Optional[Dict[str, str]] = None
    display: Optional[str] = None
    link_label: Optional[LocalizedString] = None
    link_template: Optional[str] = None
    link_title: Optional[LocalizedString] = None
    link_target: Optional[str] = None
    css_class: Optional[str] = None
    css_style: Optional[str] = None
    image_fields: Optional[Dict[str, str]] = None


class IndexGeneratorViewUpdate(BaseModel):
    """View configuration for index generator."""

    type: str
    default: bool = False


class IndexGeneratorConfigUpdate(BaseModel):
    """Complete index generator configuration."""

    enabled: bool = True
    template: str = "group_index.html"
    page_config: IndexGeneratorPageConfigUpdate
    filters: Optional[List[IndexGeneratorFilterUpdate]] = None
    display_fields: List[IndexGeneratorDisplayFieldUpdate]
    views: Optional[List[IndexGeneratorViewUpdate]] = None


@router.get("/export/{group_by}/index-generator")
async def get_index_generator(group_by: str) -> Dict[str, Any]:
    """
    Get index_generator configuration for a group.

    Args:
        group_by: The group name (e.g., 'taxons', 'plots', 'shapes')

    Returns:
        Index generator configuration

    Raises:
        HTTPException 404: If group not found or no index_generator configured
    """
    try:
        export_config = _load_export_config()
        group = _find_export_group(export_config, group_by)

        if not group:
            raise HTTPException(
                status_code=404, detail=f"Group '{group_by}' not found in export config"
            )

        index_generator = group.get("index_generator")
        if not index_generator:
            raise HTTPException(
                status_code=404,
                detail=f"No index_generator configuration for group '{group_by}'",
            )

        return index_generator

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting index generator config: {str(e)}"
        )


@router.put("/export/{group_by}/index-generator")
async def update_index_generator(
    group_by: str, config: IndexGeneratorConfigUpdate
) -> Dict[str, Any]:
    """
    Update index_generator configuration for a group.

    Args:
        group_by: The group name
        config: Index generator configuration

    Returns:
        Updated configuration
    """
    try:
        export_config = _load_export_config()

        # Find the group
        target_group = None
        for export_entry in export_config.get("exports", []):
            groups = export_entry.get("groups") or export_entry.get("params", {}).get(
                "groups", []
            )
            for group in groups:
                if group.get("group_by") == group_by:
                    target_group = group
                    break
            if target_group:
                break

        if not target_group:
            raise HTTPException(
                status_code=404, detail=f"Group '{group_by}' not found in export config"
            )

        # Convert Pydantic model to dict
        config_dict = config.model_dump(exclude_none=True)

        # Convert nested models
        if "page_config" in config_dict:
            config_dict["page_config"] = {
                k: v for k, v in config_dict["page_config"].items() if v is not None
            }

        if "filters" in config_dict:
            config_dict["filters"] = [
                {k: v for k, v in f.items() if v is not None}
                for f in config_dict["filters"]
            ]

        if "display_fields" in config_dict:
            config_dict["display_fields"] = [
                {k: v for k, v in f.items() if v is not None}
                for f in config_dict["display_fields"]
            ]

        if "views" in config_dict:
            config_dict["views"] = [
                {k: v for k, v in v.items() if v is not None}
                for v in config_dict["views"]
            ]

        # Insert index_generator before widgets if widgets exists
        if "widgets" in target_group:
            # Reorder keys: everything before widgets, then index_generator, then widgets
            new_group = {}
            for key in target_group:
                if key == "widgets":
                    new_group["index_generator"] = config_dict
                    new_group["widgets"] = target_group["widgets"]
                elif key != "index_generator":
                    new_group[key] = target_group[key]
            # If widgets wasn't in the loop (shouldn't happen), add index_generator
            if "index_generator" not in new_group:
                new_group["index_generator"] = config_dict
            target_group.clear()
            target_group.update(new_group)
        else:
            target_group["index_generator"] = config_dict

        _save_export_config(export_config)

        return config_dict

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating index generator config: {str(e)}"
        )


# =============================================================================
# Static API Export Configuration Endpoints
# =============================================================================


class ApiExportGroupEntry(BaseModel):
    """Minimal info about a group inside a target."""

    group_by: str
    enabled: bool = True


class ApiExportTargetSummary(BaseModel):
    """Summary for a JSON API export target."""

    name: str
    enabled: bool = True
    exporter: str = "json_api_exporter"
    group_names: List[str] = Field(default_factory=list)
    groups: List[ApiExportGroupEntry] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)


class ApiExportTargetSettingsUpdate(BaseModel):
    """Target-level static API settings."""

    enabled: bool = True
    params: Dict[str, Any] = Field(default_factory=dict)


class ApiExportTargetCreate(BaseModel):
    """Create a new JSON API export target."""

    name: str = Field(..., pattern=r"^[a-z][a-z0-9_]{2,30}$")
    template: Literal["simple", "dwc"] = Field(
        ..., description="Export template: simple JSON or Darwin Core"
    )
    params: Dict[str, Any] = Field(default_factory=dict)


class ApiExportGroupConfigUpdate(BaseModel):
    """Per-group configuration for a static API export target."""

    enabled: bool = True
    data_source: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    index: Optional[Dict[str, Any]] = None
    json_options: Optional[Dict[str, Any]] = None
    transformer_plugin: Optional[str] = None
    transformer_params: Optional[Dict[str, Any]] = None


@router.get("/export/api-targets", response_model=List[ApiExportTargetSummary])
async def list_api_export_targets() -> List[ApiExportTargetSummary]:
    """List all configured static API export targets."""
    try:
        export_config = _load_export_config()
        return [
            ApiExportTargetSummary(
                name=export_entry.get("name", ""),
                enabled=export_entry.get("enabled", True),
                exporter=export_entry.get("exporter", "json_api_exporter"),
                group_names=[
                    group.get("group_by")
                    for group in export_entry.get("groups", []) or []
                    if group.get("group_by")
                ],
                groups=[
                    ApiExportGroupEntry(
                        group_by=group.get("group_by", ""),
                        enabled=group.get("enabled", True),
                    )
                    for group in export_entry.get("groups", []) or []
                    if group.get("group_by")
                ],
                params=deepcopy(export_entry.get("params", {}) or {}),
            )
            for export_entry in _list_api_export_targets(export_config)
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing API export targets: {str(e)}"
        )


@router.post("/export/api-targets", response_model=ApiExportTargetSummary)
async def create_api_export_target(
    body: ApiExportTargetCreate,
) -> ApiExportTargetSummary:
    """Create a new JSON API export target from a template."""
    import re

    try:
        if not re.match(r"^[a-z][a-z0-9_]{2,30}$", body.name):
            raise HTTPException(
                status_code=422,
                detail="Name must be 3-31 lowercase chars (letters, digits, underscores)",
            )

        export_config = _load_export_config()
        if _find_api_export_target(export_config, body.name):
            raise HTTPException(
                status_code=409,
                detail=f"Target '{body.name}' already exists",
            )

        # Build new target from template
        new_target: Dict[str, Any] = {
            "name": body.name,
            "exporter": "json_api_exporter",
            "enabled": True,
            "groups": [],
            "params": {},
        }

        if body.template == "simple":
            new_target["params"] = {
                "output_dir": f"exports/{body.name}",
                "detail_output_pattern": "{group}/{id}.json",
                "index_output_pattern": "all_{group}.json",
                **body.params,
            }
        elif body.template == "dwc":
            new_target["params"] = {
                "output_dir": f"exports/{body.name}",
                "detail_output_pattern": "{group}/{id}_dwc.json",
                "index_output_pattern": "all_{group}_dwc.json",
                **body.params,
            }
        else:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown template '{body.template}'. Use: simple, dwc",
            )

        export_config.setdefault("exports", []).append(new_target)
        _validate_export_config_or_raise(export_config)
        _save_export_config(export_config)

        return ApiExportTargetSummary(
            name=body.name,
            enabled=True,
            exporter="json_api_exporter",
            group_names=[],
            groups=[],
            params=new_target["params"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating API export target: {str(e)}"
        )


@router.get("/export/api-targets/{export_name}/settings")
async def get_api_export_target_settings(export_name: str) -> Dict[str, Any]:
    """Get global settings for a static API export target."""
    try:
        export_config = _load_export_config()
        export_target = _find_api_export_target(export_config, export_name)
        if not export_target:
            raise HTTPException(
                status_code=404, detail=f"API export target '{export_name}' not found"
            )

        return {
            "name": export_name,
            "enabled": export_target.get("enabled", True),
            "params": deepcopy(export_target.get("params", {}) or {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting API export target settings: {str(e)}",
        )


@router.put("/export/api-targets/{export_name}/settings")
async def update_api_export_target_settings(
    export_name: str, config: ApiExportTargetSettingsUpdate
) -> Dict[str, Any]:
    """Update target-level settings for a static API export target."""
    try:
        export_config = _load_export_config()
        export_target = _find_api_export_target(export_config, export_name)
        if not export_target:
            raise HTTPException(
                status_code=404, detail=f"API export target '{export_name}' not found"
            )

        export_target["enabled"] = config.enabled
        export_target["params"] = config.params

        _validate_export_config_or_raise(export_config)
        _save_export_config(export_config)

        return {
            "name": export_name,
            "enabled": export_target.get("enabled", True),
            "params": deepcopy(export_target.get("params", {}) or {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating API export target settings: {str(e)}",
        )


@router.get("/export/api-targets/{export_name}/groups/{group_by}")
async def get_api_export_group_config(
    export_name: str, group_by: str
) -> Dict[str, Any]:
    """Get per-group settings for a specific static API export target."""
    try:
        export_config = _load_export_config()
        export_target = _find_api_export_target(export_config, export_name)
        if not export_target:
            raise HTTPException(
                status_code=404, detail=f"API export target '{export_name}' not found"
            )

        group = _find_target_group(export_target, group_by)
        payload = (
            deepcopy(group)
            if group is not None
            else _build_default_api_group_config(export_name, group_by)
        )
        payload["enabled"] = group is not None and group.get("enabled", True)
        payload.setdefault("group_by", group_by)
        payload.setdefault("detail", {"pass_through": True})
        payload.setdefault("index", {"fields": []})
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting API group config: {str(e)}"
        )


@router.put("/export/api-targets/{export_name}/groups/{group_by}")
async def update_api_export_group_config(
    export_name: str, group_by: str, config: ApiExportGroupConfigUpdate
) -> Dict[str, Any]:
    """Update per-group settings for a static API export target."""
    try:
        export_config = _load_export_config()
        export_target = _find_api_export_target(export_config, export_name)
        if not export_target:
            raise HTTPException(
                status_code=404, detail=f"API export target '{export_name}' not found"
            )

        groups = export_target.setdefault("groups", [])
        existing_group = _find_target_group(export_target, group_by)

        if not config.enabled:
            if existing_group:
                existing_group["enabled"] = False
            else:
                groups.append({"group_by": group_by, "enabled": False})
            _validate_export_config_or_raise(export_config)
            _save_export_config(export_config)
            result = deepcopy(existing_group or {"group_by": group_by})
            result["enabled"] = False
            return result

        next_group: Dict[str, Any] = {"group_by": group_by}
        payload = config.model_dump(exclude_none=True)
        payload.pop("enabled", None)

        for key in (
            "data_source",
            "detail",
            "index",
            "json_options",
            "transformer_plugin",
            "transformer_params",
        ):
            if key in payload:
                next_group[key] = payload[key]

        next_group.setdefault("detail", {"pass_through": True})

        # If no transformer_plugin was specified, inherit from existing
        # sibling groups in the same target (e.g. activating a DwC target
        # for a new group should copy the transformer from its siblings).
        if "transformer_plugin" not in next_group:
            for sibling in groups:
                sibling_plugin = sibling.get("transformer_plugin")
                if sibling_plugin and sibling.get("group_by") != group_by:
                    next_group["transformer_plugin"] = sibling_plugin
                    break

        if next_group.get("transformer_plugin") == "niamoto_to_dwc_occurrence":
            next_group.setdefault(
                "transformer_params", _default_dwc_transformer_params(group_by)
            )

        if existing_group is None:
            export_target["groups"].append(next_group)
        else:
            existing_group.clear()
            existing_group.update(next_group)

        _validate_export_config_or_raise(export_config)
        _save_export_config(export_config)

        response = deepcopy(next_group)
        response["enabled"] = True
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating API group config: {str(e)}"
        )


# =============================================================================
# Index Generator Field Suggestions
# =============================================================================


class SuggestedDisplayField(BaseModel):
    """Suggested display field configuration."""

    name: str
    source: str
    type: str  # text, select, boolean, json_array
    label: str
    searchable: bool = False
    cardinality: Optional[int] = None  # Number of distinct values
    sample_values: Optional[List[str]] = None  # Sample of values
    suggested_as_filter: bool = False
    format: Optional[str] = None
    dynamic_options: bool = False
    priority: str = "high"  # high, low - indicates importance for index display
    display: Optional[str] = None
    inline_badge: bool = False
    link_label: Optional[str] = None
    link_title: Optional[str] = None
    link_target: Optional[str] = None
    image_fields: Optional[Dict[str, str]] = None


class SuggestedFilter(BaseModel):
    """Suggested filter configuration."""

    field: str
    source: str
    label: str
    type: str
    values: List[Any]
    operator: str = "in"


class IndexFieldSuggestions(BaseModel):
    """Response with suggested fields for index generator."""

    display_fields: List[SuggestedDisplayField]
    filters: List[SuggestedFilter]
    total_entities: int


def _looks_like_url(value: Any) -> bool:
    """Return whether a sample value looks like a URL or image data URI."""
    return isinstance(value, str) and value.startswith(
        ("http://", "https://", "/", "data:image/")
    )


def _get_field_leaf_name(path: str) -> str:
    """Return the meaningful field name for a dotted path."""
    parts = path.split(".")
    if (
        path.startswith("hierarchy_context.")
        and len(parts) >= 3
        and parts[-1] == "name"
    ):
        return parts[-2]
    if len(parts) >= 2 and parts[-1] == "value":
        return parts[-2]
    return parts[-1] if parts else path


def _humanize_identifier(identifier: str) -> str:
    """Turn snake/kebab-case identifiers into compact labels."""
    tokens = [token for token in re.split(r"[_\-]+", identifier) if token]
    if not tokens:
        return identifier.title()

    ignored_prefixes = {"api", "provider", "source"}
    while tokens and tokens[0].lower() in ignored_prefixes:
        tokens = tokens[1:]

    if not tokens:
        tokens = [identifier]

    acronyms = {"gbif", "iucn", "nc", "url", "api", "id", "ui", "dwc"}
    return " ".join(
        token.upper() if token.lower() in acronyms else token.capitalize()
        for token in tokens
    )


def _extract_enrichment_provider(path: str) -> Optional[str]:
    """Extract the enrichment provider slug from an extra_data path."""
    parts = path.split(".")
    if "sources" not in parts:
        return None

    source_index = parts.index("sources")
    if source_index + 1 >= len(parts):
        return None
    return parts[source_index + 1]


def _detect_image_variant(
    path: str, sample_values: Optional[List[str]]
) -> Optional[str]:
    """Classify flattened image fields into thumbnail/full/url variants."""
    values = sample_values or []
    if not any(_looks_like_url(value) for value in values):
        return None

    lower_path = path.lower()
    leaf = lower_path.split(".")[-1]

    if "image_big" in leaf or "big_thumb" in leaf or "full" in leaf or "large" in leaf:
        return "full"

    if (
        "image_small" in leaf
        or "small_thumb" in leaf
        or "thumbnail" in leaf
        or ("thumb" in leaf and "big" not in leaf)
        or "preview" in leaf
    ):
        return "thumbnail"

    if "image" in lower_path and "url" in leaf:
        return "url"

    return None


def _build_link_display_metadata(
    path: str, info: Dict[str, Any]
) -> Optional[Dict[str, str]]:
    """Build display metadata for URL-like fields."""
    if info.get("type") != "text":
        return None

    sample_values = info.get("sample_values") or []
    if not sample_values or not any(_looks_like_url(value) for value in sample_values):
        return None
    if _detect_image_variant(path, sample_values):
        return None

    leaf_name = _get_field_leaf_name(path)
    lower_leaf = leaf_name.lower()
    url_tokens = ("url", "uri", "link", "href", "website", "webpage", "permalink")
    if not any(token in lower_leaf for token in url_tokens):
        return None

    provider_slug = _extract_enrichment_provider(path)
    provider_label = _humanize_identifier(provider_slug) if provider_slug else None

    base_name = leaf_name
    for suffix in (
        "_url",
        "_uri",
        "_link",
        "_href",
        "_website",
        "_webpage",
        "_permalink",
    ):
        if lower_leaf.endswith(suffix):
            base_name = leaf_name[: -len(suffix)]
            break

    generic_names = {
        "url",
        "uri",
        "link",
        "href",
        "website",
        "webpage",
        "permalink",
        "external",
        "external_url",
    }

    if not base_name or base_name.lower() in generic_names:
        base_name = provider_slug or "external_link"

    link_label = _humanize_identifier(base_name)
    if provider_label and lower_leaf in generic_names:
        link_label = provider_label

    link_target = (
        "_blank"
        if any(
            isinstance(value, str) and value.startswith(("http://", "https://"))
            for value in sample_values
        )
        else None
    )

    return {
        "name": re.sub(r"[^a-z0-9]+", "_", base_name.lower()).strip("_")
        or "external_link",
        "label": link_label,
        "link_label": link_label,
        "link_title": f"Voir sur {link_label}",
        "link_target": link_target or "",
    }


def _should_inline_boolean_badge(path: str) -> bool:
    """Promote high-signal boolean fields to inline badges."""
    badge_tokens = {
        "endemic",
        "endemicity",
        "protected",
        "native",
        "introduced",
        "invasive",
        "threatened",
        "endangered",
        "rare",
        "vulnerable",
        "extinct",
        "flagship",
    }
    lower_name = _get_field_leaf_name(path).lower()
    return any(token in lower_name for token in badge_tokens)


def _is_image_collection_path(path: str, info: Dict[str, Any]) -> bool:
    """Detect array-like image collections already present in transformed data."""
    if info.get("type") != "json_array":
        return False

    lower_path = path.lower()
    return any(
        token in lower_path
        for token in ("image", "images", "photo", "photos", "picture", "gallery")
    )


def _build_image_display_field_suggestions(
    field_analysis: Dict[str, Dict[str, Any]],
) -> tuple[List[SuggestedDisplayField], set[str]]:
    """Create synthetic image-preview fields from flattened image URLs."""
    suggestions: List[SuggestedDisplayField] = []
    consumed_paths: set[str] = set()

    for path, info in field_analysis.items():
        if not _is_image_collection_path(path, info):
            continue

        suggestions.append(
            SuggestedDisplayField(
                name="images",
                source=path,
                type="json_array",
                label="Images",
                searchable=False,
                cardinality=info.get("cardinality"),
                sample_values=info.get("sample_values"),
                suggested_as_filter=False,
                dynamic_options=False,
                priority=info.get("priority", "high"),
                display="image_preview",
            )
        )
        consumed_paths.add(path)

    grouped_variants: Dict[str, Dict[str, Any]] = {}

    for path, info in field_analysis.items():
        variant = _detect_image_variant(path, info.get("sample_values"))
        if not variant:
            continue

        parent_path = path.rsplit(".", 1)[0]
        group = grouped_variants.setdefault(
            parent_path,
            {
                "priority": info.get("priority", "high"),
                "paths": set(),
                "variants": {},
            },
        )
        group["paths"].add(path)
        if info.get("priority", "low") == "high":
            group["priority"] = "high"
        group["variants"].setdefault(variant, path)

    for parent_path, group in grouped_variants.items():
        variant_paths = group["variants"]
        if not variant_paths:
            continue

        image_fields: Dict[str, str] = {}
        if "thumbnail" in variant_paths:
            image_fields["thumbnail"] = variant_paths["thumbnail"].split(".")[-1]
        if "full" in variant_paths:
            image_fields["full"] = variant_paths["full"].split(".")[-1]
        if "url" in variant_paths:
            image_fields["url"] = variant_paths["url"].split(".")[-1]
        elif "full" in variant_paths:
            image_fields["url"] = variant_paths["full"].split(".")[-1]
        elif "thumbnail" in variant_paths:
            image_fields["url"] = variant_paths["thumbnail"].split(".")[-1]

        suggestions.append(
            SuggestedDisplayField(
                name="images",
                source=parent_path,
                type="json_array",
                label="Images",
                searchable=False,
                suggested_as_filter=False,
                dynamic_options=False,
                priority=group["priority"],
                display="image_preview",
                image_fields=image_fields or None,
            )
        )
        consumed_paths.update(group["paths"])

    suggestions.sort(
        key=lambda field: (
            0 if not field.source.startswith("extra_data.") else 1,
            0 if field.priority == "high" else 1,
            field.source,
        )
    )

    return suggestions, consumed_paths


@router.get("/export/api-targets/{export_name}/groups/{group_by}/suggestions")
async def suggest_api_export_index_fields(
    export_name: str, group_by: str
) -> IndexFieldSuggestions:
    """Reuse index field suggestions for static API export indexes."""
    export_config = _load_export_config()
    export_target = _find_api_export_target(export_config, export_name)
    if not export_target:
        raise HTTPException(
            status_code=404, detail=f"API export target '{export_name}' not found"
        )
    return await suggest_index_fields(group_by)


def _extract_json_paths(
    data: Dict[str, Any], prefix: str = "", max_depth: int = 4
) -> List[tuple]:
    """
    Extract all JSON paths from a nested dictionary.
    Returns list of (path, value) tuples.
    """
    paths = []
    if max_depth <= 0:
        return paths

    for key, value in data.items():
        current_path = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            # Check if it's a {value: X, label: Y} pattern (common in Niamoto)
            if "value" in value:
                paths.append((f"{current_path}.value", value.get("value")))
            else:
                # Recurse into nested dict
                paths.extend(_extract_json_paths(value, current_path, max_depth - 1))
        elif isinstance(value, list):
            # For arrays, note the path but don't recurse
            paths.append((current_path, value))
        else:
            paths.append((current_path, value))

    return paths


def _detect_field_type(values: List[Any]) -> str:
    """Detect the field type based on sample values."""
    if not values:
        return "text"

    # Filter out None values
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "text"

    # Check for boolean
    bool_values = {True, False, "true", "false", "True", "False", 1, 0}
    if all(v in bool_values for v in non_null):
        return "boolean"

    # Check for arrays
    if any(isinstance(v, list) for v in non_null):
        return "json_array"

    # Check for numeric
    try:
        for v in non_null[:10]:  # Check first 10
            if isinstance(v, (int, float)):
                continue
            float(v)
        return "number"
    except (ValueError, TypeError):
        pass

    # Check cardinality for select vs text
    unique = set(str(v) for v in non_null if v is not None)
    if len(unique) <= 20 and len(non_null) > len(unique) * 2:
        return "select"

    return "text"


def _generate_label(path: str) -> str:
    """Generate a human-readable label from a JSON path."""
    if path.startswith("hierarchy_context."):
        parts = path.split(".")
        if len(parts) >= 3 and parts[-1] == "name":
            return _humanize_identifier(parts[-2])

    # Extract the meaningful part
    parts = path.split(".")

    # Common patterns to handle
    if parts[-1] == "value":
        parts = parts[:-1]

    # Take the last meaningful part
    name = parts[-1] if parts else path

    # Convert to human readable
    label = name.replace("_", " ").replace("-", " ")
    return label.title()


def _get_suggestion_label(path: str, info: Dict[str, Any]) -> str:
    """Return the preferred label for an inferred display field."""
    if info.get("synthetic_label"):
        return str(info["synthetic_label"])
    return _generate_label(path)


def _is_name_field(path: str) -> bool:
    """Check if this is likely a name/title field."""
    if path.startswith("hierarchy_context."):
        return False
    name_indicators = ["name", "title", "label", "full_name", "nom"]
    lower_path = path.lower()
    return any(ind in lower_path for ind in name_indicators)


def _is_category_field(path: str) -> bool:
    """Check if this is likely a category field."""
    cat_indicators = [
        "type",
        "category",
        "rank",
        "status",
        "class",
        "kind",
        "famille",
        "family",
        "genus",
    ]
    lower_path = path.lower()
    return any(ind in lower_path for ind in cat_indicators)


def _is_rank_field(path: str) -> bool:
    """Check if this is likely a taxonomic rank field."""
    rank_indicators = ["rank_name", "rank", "rang", "niveau"]
    lower_path = path.lower()
    return any(ind in lower_path for ind in rank_indicators)


def _is_metadata_field(path: str) -> bool:
    """Skip technical timestamps and sync metadata from auto-config."""
    metadata_indicators = {
        "created_at",
        "updated_at",
        "enriched_at",
        "modified_at",
        "imported_at",
        "synced_at",
        "fetched_at",
        "last_updated",
        "last_synced",
    }
    lower_path = path.lower()
    leaf = lower_path.split(".")[-1]
    return leaf in metadata_indicators


def _is_parent_context_field(path: str) -> bool:
    """Identify ancestor context fields that are only useful if populated."""
    lower_path = path.lower()
    return "parent_" in lower_path or ".parent." in lower_path


def _is_identifier_field(path: str, group_by: Optional[str] = None) -> bool:
    """Skip internal identifier fields from index suggestions."""
    lower_path = path.lower()
    leaf = _get_field_leaf_name(lower_path)
    if leaf in {"id", "uuid"}:
        return True
    if leaf.endswith("_id") or leaf.startswith("id_"):
        return True
    if group_by and lower_path == f"{group_by.lower()}_id":
        return True
    return False


def _is_enrichment_metadata_field(path: str) -> bool:
    """Skip API-enrichment bookkeeping fields that are not user-facing content."""
    lower_path = path.lower()
    if "api_enrichment.sources" not in lower_path:
        return False

    leaf = lower_path.split(".")[-1]
    if leaf in {"label", "status", "source", "provider"}:
        return True
    if leaf.endswith("_id") or leaf.startswith("id_") or leaf == "api_id":
        return True
    return False


def _detect_terminal_ranks(values: List[str]) -> List[str]:
    """
    Detect terminal/leaf ranks from a list of rank values.

    Works with multiple languages and naming conventions:
    - French: Espèce, Sous-espèce, Variété, Forme
    - English: Species, Subspecies, Variety, Form
    - Latin abbreviations: sp., subsp., var., f.
    - Numeric levels: higher numbers = more specific
    """
    # Known terminal rank patterns (case-insensitive)
    terminal_patterns = [
        # French
        "espèce",
        "espece",
        "sous-espèce",
        "sous-espece",
        "variété",
        "variete",
        "forme",
        "cultivar",
        "sous-variété",
        "sous-variete",
        # English
        "species",
        "subspecies",
        "infra",
        "infraspecies",
        "infra-specific",
        "variety",
        "form",
        "cultivar",
        "subvariety",
        # Latin/abbreviations
        "sp.",
        "sp",
        "subsp.",
        "subsp",
        "var.",
        "var",
        "f.",
        "cv.",
        # Generic
        "leaf",
        "terminal",
        "feuille",
    ]

    terminal_values = []
    seen_values = set()
    for val in values:
        if val is None:
            continue
        lower_val = str(val).lower().strip()
        # Check if value matches any terminal pattern
        if (
            any(
                pattern in lower_val or lower_val == pattern
                for pattern in terminal_patterns
            )
            and val not in seen_values
        ):
            seen_values.add(val)
            terminal_values.append(val)

    return terminal_values


def _extract_path_value_from_record(record: Dict[str, Any], path: str) -> Any:
    """Extract a dotted path value from a DB record with JSON columns."""
    import json

    parts = path.split(".")
    if not parts:
        return None

    current: Any = record.get(parts[0])
    if isinstance(current, str):
        stripped = current.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                current = json.loads(stripped)
            except json.JSONDecodeError:
                pass

    for key in parts[1:]:
        if isinstance(current, str):
            stripped = current.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    current = json.loads(stripped)
                except json.JSONDecodeError:
                    return None
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None

    return current


def _load_table_records(db_path: Path, table_name: str) -> List[Dict[str, Any]]:
    """Load full table records for richer suggestion heuristics."""
    from niamoto.common.database import Database
    from niamoto.common.table_resolver import quote_identifier
    from sqlalchemy import text

    db = Database(str(db_path), read_only=True)
    try:
        quoted_table = quote_identifier(db, table_name)
        rows = (
            db.session.execute(text(f"SELECT * FROM {quoted_table}")).mappings().all()
        )
        return [dict(row) for row in rows]
    finally:
        db.close_db_session()


def _get_distinct_values_for_path(
    records: List[Dict[str, Any]], path: str
) -> List[Any]:
    """Return distinct non-null values for a dotted path while preserving order."""
    values: List[Any] = []
    seen: set[str] = set()

    for record in records:
        value = _extract_path_value_from_record(record, path)
        if value is None or isinstance(value, (dict, list)):
            continue
        normalized = str(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        values.append(value)

    return values


def _filter_records_by_path_values(
    records: List[Dict[str, Any]], path: str, allowed_values: List[Any]
) -> List[Dict[str, Any]]:
    """Filter records by a dotted path value."""
    allowed = {str(value) for value in allowed_values}
    return [
        record
        for record in records
        if str(_extract_path_value_from_record(record, path)) in allowed
    ]


def _get_path_coverage(records: List[Dict[str, Any]], path: str) -> float:
    """Return the ratio of records with a non-empty scalar value for the path."""
    if not records:
        return 0.0

    populated = 0
    for record in records:
        value = _extract_path_value_from_record(record, path)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (dict, list)) and not value:
            continue
        populated += 1

    return populated / len(records)


def _resolve_join_column_for_records(
    records: List[Dict[str, Any]], item_ids: set[Any], candidate_columns: List[str]
) -> Optional[str]:
    """Pick the record column whose values overlap the transformed IDs the best."""
    best_column: Optional[str] = None
    best_overlap = 0

    for candidate in candidate_columns:
        overlap = sum(1 for record in records if record.get(candidate) in item_ids)
        if overlap > best_overlap:
            best_column = candidate
            best_overlap = overlap

    return best_column


def _build_hierarchy_context_field_analysis(
    source_records: List[Dict[str, Any]],
    transformed_records: List[Dict[str, Any]],
    id_column: str,
    terminal_item_ids: set[Any],
    terminal_rank_values: List[Any],
) -> Dict[str, Dict[str, Any]]:
    """Create synthetic ancestor fields from the source hierarchy context."""
    if not source_records or not transformed_records:
        return {}

    item_ids = {record.get(id_column) for record in transformed_records}
    item_ids.discard(None)
    if not item_ids:
        return {}

    join_column = _resolve_join_column_for_records(
        source_records, item_ids, [id_column, "id"]
    )
    if not join_column:
        return {}

    hierarchy_metadata = detect_hierarchy_metadata(
        source_records[0].keys(), join_field=join_column
    )
    if hierarchy_metadata is None:
        return {}

    hierarchy_contexts = build_hierarchy_contexts(source_records, hierarchy_metadata)
    if not hierarchy_contexts:
        return {}

    relevant_item_ids = terminal_item_ids or set(hierarchy_contexts)
    terminal_rank_keys = {
        normalize_hierarchy_key(value)
        for value in terminal_rank_values
        if value is not None
    }

    values_by_rank: Dict[str, List[str]] = {}
    labels_by_rank: Dict[str, str] = {}
    distances_by_rank: Dict[str, List[int]] = {}

    for item_id in relevant_item_ids:
        context = hierarchy_contexts.get(item_id) or {}
        for rank_key, entry in context.items():
            if rank_key in terminal_rank_keys:
                continue

            name_value = entry.get("name")
            if name_value in (None, ""):
                continue

            values_by_rank.setdefault(rank_key, []).append(str(name_value))
            labels_by_rank.setdefault(rank_key, str(entry.get("rank") or rank_key))
            distances_by_rank.setdefault(rank_key, []).append(
                int(entry.get("distance", 0))
            )

    if not values_by_rank:
        return {}

    ordered_rank_keys = sorted(
        values_by_rank,
        key=lambda rank_key: (
            sum(distances_by_rank.get(rank_key, [99]))
            / max(len(distances_by_rank.get(rank_key, [])), 1),
            -len(values_by_rank[rank_key]),
            rank_key,
        ),
    )

    synthetic_fields: Dict[str, Dict[str, Any]] = {}
    for rank_key in ordered_rank_keys[:3]:
        values = values_by_rank[rank_key]
        if not values:
            continue

        unique_values = list(dict.fromkeys(values))
        coverage = len(values) / max(len(relevant_item_ids), 1)
        if coverage < 0.4:
            continue

        synthetic_fields[f"hierarchy_context.{rank_key}.name"] = {
            "type": "select" if 1 < len(unique_values) <= 20 else "text",
            "cardinality": len(set(unique_values)),
            "sample_values": unique_values[:10],
            "total_values": len(values),
            "priority": "high",
            "synthetic_label": _humanize_identifier(labels_by_rank[rank_key]),
        }

    return synthetic_fields


def _detect_hierarchical_structure(df: Any) -> Dict[str, Any]:
    """
    Detect if a dataframe represents hierarchical data.

    Returns info about the hierarchy:
    - has_nested_set: bool (lft/rght columns)
    - has_level: bool (level column)
    - has_parent: bool (parent_id column)
    - level_column: str or None
    - max_level: int or None
    """
    columns = [c.lower() for c in df.columns]

    result = {
        "is_hierarchical": False,
        "has_nested_set": False,
        "has_level": False,
        "has_parent": False,
        "level_column": None,
        "max_level": None,
    }

    # Check for nested set
    if "lft" in columns and "rght" in columns:
        result["has_nested_set"] = True
        result["is_hierarchical"] = True

    # Check for level column
    level_names = ["level", "niveau", "depth", "profondeur"]
    for col in df.columns:
        if col.lower() in level_names:
            result["has_level"] = True
            result["level_column"] = col
            result["is_hierarchical"] = True
            try:
                result["max_level"] = int(df[col].max())
            except (ValueError, TypeError):
                pass
            break

    # Check for parent reference
    parent_names = ["parent_id", "parent", "id_parent"]
    for col in df.columns:
        if col.lower() in parent_names:
            result["has_parent"] = True
            result["is_hierarchical"] = True
            break

    return result


def _extract_extra_data_fields(
    source_df: Any,
) -> Dict[str, Dict[str, Any]]:
    """
    Extract fields from extra_data column (API enrichment data).

    These are high priority fields for index display.
    Handles both dict and JSON string formats.
    """
    import json

    schema = {}

    if "extra_data" not in source_df.columns:
        return schema

    # Sample extra_data values
    extra_data_values = source_df["extra_data"].dropna().tolist()
    if not extra_data_values:
        return schema

    def collect_scalar_paths(value: Any, prefix: str = "") -> List[tuple[str, Any]]:
        """Flatten nested dict values into scalar dotted paths."""

        collected: List[tuple[str, Any]] = []

        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                next_prefix = f"{prefix}.{nested_key}" if prefix else str(nested_key)
                collected.extend(collect_scalar_paths(nested_value, next_prefix))
            return collected

        if isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list)):
                    continue
                collected.append((prefix, item))
            return collected

        collected.append((prefix, value))
        return collected

    # Extract all keys from extra_data (including nested api_enrichment)
    all_keys = set()
    sample_values = {}

    for data in extra_data_values[:50]:
        # Parse JSON string if needed
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                continue

        if not isinstance(data, dict):
            continue

        # Extract nested api_enrichment fields, including namespaced sources.
        if "api_enrichment" in data and isinstance(data["api_enrichment"], dict):
            for full_key, value in collect_scalar_paths(
                data["api_enrichment"], "api_enrichment"
            ):
                if not full_key:
                    continue
                all_keys.add(full_key)
                if full_key not in sample_values:
                    sample_values[full_key] = []
                if value is not None:
                    sample_values[full_key].append(value)

        # Also extract top-level keys outside api_enrichment.
        for key, value in data.items():
            if key == "api_enrichment":
                continue
            for full_key, nested_value in collect_scalar_paths(value, str(key)):
                if not full_key:
                    continue
                all_keys.add(full_key)
                if full_key not in sample_values:
                    sample_values[full_key] = []
                if nested_value is not None:
                    sample_values[full_key].append(nested_value)

    # Create schema entries for each key
    for key in all_keys:
        values = sample_values.get(key, [])
        if values:
            field_type = _detect_field_type(values)
            unique_vals = list(set(str(v) for v in values if v is not None))[:10]
            schema[f"extra_data.{key}"] = {
                "type": field_type,
                "sample_values": unique_vals,
                "cardinality": len(set(str(v) for v in values if v is not None)),
                "total_values": len(values),
                "priority": "high",  # API enrichment data is high priority
                "source": "extra_data",
            }

    return schema


def _infer_schema_from_transform_config(
    group_config: Dict[str, Any],
    source_df: Any,
) -> Dict[str, Dict[str, Any]]:
    """
    Infer the output schema from transform.yml configuration.

    Analyzes transformer configurations to predict what columns and JSON
    structures will be created during transformation.

    Priority levels:
    - "high": field_aggregator, class_object_field_aggregator, extra_data
    - "medium": statistical_summary with simple stats
    - "low": distributions, rankings, complex transformers

    Handles both:
    - Old format: transformers: [{name, plugin, params}, ...]
    - New format: widgets_data: {widget_name: {plugin, params}, ...}

    Returns:
        Dict mapping JSON paths to their inferred properties
    """
    schema = {}

    # First, extract extra_data fields (high priority)
    extra_data_schema = _extract_extra_data_fields(source_df)
    schema.update(extra_data_schema)

    # Handle new widgets_data format
    widgets_data = group_config.get("widgets_data", {})
    transformers = []

    if widgets_data:
        # Convert widgets_data format to transformers format
        for widget_name, widget_config in widgets_data.items():
            if isinstance(widget_config, dict):
                transformers.append(
                    {
                        "name": widget_name,
                        "plugin": widget_config.get("plugin", ""),
                        "params": widget_config.get("params", {}),
                    }
                )
    else:
        # Use old transformers format
        transformers = group_config.get("transformers", [])

    # High priority plugins (good for index display)
    HIGH_PRIORITY_PLUGINS = {"field_aggregator", "class_object_field_aggregator"}

    for transformer in transformers:
        name = transformer.get("name", "")
        plugin = transformer.get("plugin", "")
        params = transformer.get("params", {})

        # Determine priority based on plugin type
        priority = "high" if plugin in HIGH_PRIORITY_PLUGINS else "low"

        # Handle field_aggregator - creates {name}.{field}.value structure
        if plugin in ["field_aggregator", "class_object_field_aggregator"]:
            fields = params.get("fields", [])
            for field_config in fields:
                # Handle both old format (source=column) and new format (source=ref, field=column)
                if "field" in field_config:
                    # New format: {source: ref_name, field: column_name, target: output_name}
                    source_col = field_config.get("field", "")
                else:
                    # Old format: {source: column_name, target: output_name}
                    source_col = field_config.get("source", "")

                target = field_config.get("target", source_col)
                path = f"{name}.{target}.value"

                # Handle nested field paths like "extra_data.enriched_at"
                if "." in source_col:
                    # For nested paths, try to extract from extra_data
                    parts = source_col.split(".")
                    if parts[0] == "extra_data" and len(parts) > 1:
                        extra_key = parts[1]
                        # Get values from extra_data
                        values = []
                        for _, row in source_df.iterrows():
                            if isinstance(row.get("extra_data"), dict):
                                val = row["extra_data"].get(extra_key)
                                if val is not None:
                                    values.append(val)
                        if values:
                            schema[path] = {
                                "type": _detect_field_type(values),
                                "sample_values": list(
                                    set(str(v) for v in values if v is not None)
                                )[:10],
                                "cardinality": len(
                                    set(str(v) for v in values if v is not None)
                                ),
                                "total_values": len(values),
                                "source_column": source_col,
                                "priority": priority,
                            }
                        else:
                            schema[path] = {
                                "type": "text",
                                "sample_values": [],
                                "cardinality": 0,
                                "total_values": 0,
                                "source_column": source_col,
                                "priority": priority,
                            }
                    else:
                        schema[path] = {
                            "type": "text",
                            "sample_values": [],
                            "cardinality": 0,
                            "total_values": 0,
                            "source_column": source_col,
                            "priority": priority,
                        }
                elif source_col in source_df.columns:
                    # Try to get sample values from source column
                    values = source_df[source_col].dropna().tolist()
                    if values:
                        schema[path] = {
                            "type": _detect_field_type(values),
                            "sample_values": list(
                                set(str(v) for v in values if v is not None)
                            )[:10],
                            "cardinality": len(
                                set(str(v) for v in values if v is not None)
                            ),
                            "total_values": len(values),
                            "source_column": source_col,
                            "priority": priority,
                        }
                else:
                    # Column not in source, but still add the path
                    schema[path] = {
                        "type": "text",
                        "sample_values": [],
                        "cardinality": 0,
                        "total_values": 0,
                        "source_column": source_col,
                        "priority": priority,
                    }

        # Handle statistical_summary - creates {name}.{stat} structure (medium priority)
        elif plugin == "statistical_summary":
            stats = params.get("stats", ["mean", "min", "max", "count"])
            source_field = params.get("source_field", params.get("field", ""))
            for stat in stats:
                path = f"{name}.{stat}"
                schema[path] = {
                    "type": "number",
                    "sample_values": [],
                    "cardinality": 0,
                    "total_values": 0,
                    "source_column": source_field,
                    "priority": "low",  # Stats are less useful for index display
                }

        # Handle distribution transformers - creates {name}.bins, {name}.counts (low priority)
        elif plugin in [
            "binned_distribution",
            "dbh_distribution",
            "elevation_distribution",
            "categorical_distribution",
        ]:
            schema[f"{name}.bins"] = {
                "type": "json_array",
                "sample_values": [],
                "cardinality": 0,
                "total_values": 0,
                "priority": "low",
            }
            schema[f"{name}.counts"] = {
                "type": "json_array",
                "sample_values": [],
                "cardinality": 0,
                "total_values": 0,
                "priority": "low",
            }

        # Skip other complex transformers for suggestions (they're not useful for index)
        # Users can still add them manually if needed

    return schema


@router.get("/export/{group_by}/index-generator/suggestions")
async def suggest_index_fields(group_by: str) -> IndexFieldSuggestions:
    """
    Analyze transformed data and suggest display fields and filters.

    This endpoint:
    1. First tries to load the transformed stats table (if transform was already run)
    2. If not available, infers the schema from transform.yml configuration
    3. Uses source data to detect field types and sample values
    4. Suggests fields for display and filtering based on cardinality

    Args:
        group_by: The group name (e.g., 'taxons', 'plots', 'shapes')

    Returns:
        Suggested display_fields and filters
    """
    try:
        import pandas as pd
        from niamoto.common.database import Database
        from niamoto.common.table_resolver import quote_identifier, resolve_entity_table
        from niamoto.core.imports.registry import EntityRegistry
        from sqlalchemy import text

        db_path = get_working_directory() / "db" / "niamoto.duckdb"
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        # Load transform config
        transform_config = []
        transform_path = get_working_directory() / "config" / "transform.yml"
        if transform_path.exists():
            with open(transform_path, "r", encoding="utf-8") as f:
                transform_config = yaml.safe_load(f) or []

        # Find the group config
        group_config = None
        for group in transform_config:
            if group.get("group_by") == group_by:
                group_config = group
                break

        if not group_config:
            raise HTTPException(
                status_code=404, detail=f"Group '{group_by}' not found in transform.yml"
            )

        # Get source entity name from transform config
        source_entity = group_config.get("source", group_by)

        # Find source table from EntityRegistry
        source_table = None
        db = Database(str(db_path), read_only=True)
        try:
            if db.has_table(EntityRegistry.ENTITIES_TABLE):
                registry = EntityRegistry(db)
                for entity in registry.list_entities():
                    if entity.name == source_entity:
                        source_table = entity.table_name
                        break
        finally:
            db.close_db_session()

        # Fallback to common patterns
        if not source_table:
            db = Database(str(db_path), read_only=True)
            try:
                source_table = resolve_entity_table(db, source_entity)
            finally:
                db.close_db_session()

        if not source_table:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find source table for '{source_entity}'",
            )

        # Prefer the actual transformed output table when available.
        transformed_table = None

        db = Database(str(db_path), read_only=True)
        try:
            for candidate in (group_by, f"{group_by}_stats"):
                if db.has_table(candidate):
                    transformed_table = candidate
                    break
        finally:
            db.close_db_session()

        field_analysis = {}
        source_df = None
        source_records: List[Dict[str, Any]] = []
        total_count = 0

        if transformed_table:
            # Use the actual transformed data
            db = Database(str(db_path), read_only=True)
            try:
                quoted_transformed_table = quote_identifier(db, transformed_table)
                df = pd.read_sql(
                    text(f"SELECT * FROM {quoted_transformed_table} LIMIT 100"),
                    db.engine,
                )
                total_count = pd.read_sql(
                    text(f"SELECT COUNT(*) as cnt FROM {quoted_transformed_table}"),
                    db.engine,
                ).iloc[0]["cnt"]

                # Analyze each column
                for col in df.columns:
                    if col.startswith("_") or col in ["created_at", "updated_at"]:
                        continue

                    values = df[col].dropna().tolist()
                    if not values:
                        continue

                    sample_value = values[0] if values else None

                    if isinstance(sample_value, dict):
                        # Extract paths from JSON column
                        all_paths = []
                        for row_value in values:
                            if isinstance(row_value, dict):
                                paths = _extract_json_paths(row_value, col)
                                all_paths.extend(paths)

                        # Group by path and collect values
                        path_values = {}
                        for path, value in all_paths:
                            if path not in path_values:
                                path_values[path] = []
                            if value is not None and not isinstance(
                                value, (dict, list)
                            ):
                                path_values[path].append(value)

                        for path, vals in path_values.items():
                            if not vals:
                                continue
                            field_type = _detect_field_type(vals)
                            unique_vals = list(
                                set(str(v) for v in vals if v is not None)
                            )[:10]
                            field_analysis[path] = {
                                "type": field_type,
                                "cardinality": len(set(str(v) for v in vals)),
                                "sample_values": unique_vals,
                                "total_values": len(vals),
                                "priority": "high",
                            }
                    else:
                        field_type = _detect_field_type(values)
                        unique_vals = list(
                            set(str(v) for v in values if v is not None)
                        )[:10]
                        field_analysis[col] = {
                            "type": field_type,
                            "cardinality": len(set(str(v) for v in values)),
                            "sample_values": unique_vals,
                            "total_values": len(values),
                            "priority": "high",
                        }

                if source_table and source_table != transformed_table:
                    quoted_source_table = quote_identifier(db, source_table)
                    source_df = pd.read_sql(
                        text(f"SELECT * FROM {quoted_source_table} LIMIT 100"),
                        db.engine,
                    )
                    field_analysis.update(_extract_extra_data_fields(source_df))
            finally:
                db.close_db_session()
        else:
            # Infer schema from transform.yml using source data
            db = Database(str(db_path), read_only=True)
            try:
                quoted_source_table = quote_identifier(db, source_table)
                source_df = pd.read_sql(
                    text(f"SELECT * FROM {quoted_source_table} LIMIT 100"),
                    db.engine,
                )
                total_count = pd.read_sql(
                    text(f"SELECT COUNT(*) as cnt FROM {quoted_source_table}"),
                    db.engine,
                ).iloc[0]["cnt"]

                # Infer schema from transform config
                field_analysis = _infer_schema_from_transform_config(
                    group_config, source_df
                )

            finally:
                db.close_db_session()

        if source_df is not None:
            inferred_schema = _infer_schema_from_transform_config(
                group_config, source_df
            )
            has_declared_transformed_paths = any(
                not path.startswith("extra_data.") for path in inferred_schema
            )
            if has_declared_transformed_paths:
                for path, info in field_analysis.items():
                    if path in inferred_schema:
                        info["priority"] = inferred_schema[path].get(
                            "priority", info.get("priority", "high")
                        )
                    elif not path.startswith(("extra_data.", "hierarchy_context.")):
                        info["priority"] = "low"

        if not field_analysis:
            return IndexFieldSuggestions(
                display_fields=[], filters=[], total_entities=int(total_count)
            )

        # Detect hierarchical structure for smart filtering
        hierarchy_info = {"is_hierarchical": False}
        db = Database(str(db_path), read_only=True)
        try:
            quoted_source_table = quote_identifier(db, source_table)
            check_df = pd.read_sql(
                text(f"SELECT * FROM {quoted_source_table} LIMIT 10"), db.engine
            )
            hierarchy_info = _detect_hierarchical_structure(check_df)
        except Exception:
            pass
        finally:
            db.close_db_session()

        transformed_records: Optional[List[Dict[str, Any]]] = None
        terminal_rank_path: Optional[str] = None
        terminal_rank_values: List[Any] = []
        terminal_records: List[Dict[str, Any]] = []
        group_id_column = f"{group_by}_id"

        if transformed_table and hierarchy_info["is_hierarchical"]:
            rank_paths = [path for path in field_analysis if _is_rank_field(path)]
            if rank_paths:
                transformed_records = _load_table_records(db_path, transformed_table)
                terminal_rank_path = sorted(
                    rank_paths, key=lambda path: (".value" not in path, path)
                )[0]
                all_rank_values = _get_distinct_values_for_path(
                    transformed_records, terminal_rank_path
                )
                terminal_rank_values = _detect_terminal_ranks(all_rank_values)
                if terminal_rank_values:
                    terminal_records = _filter_records_by_path_values(
                        transformed_records, terminal_rank_path, terminal_rank_values
                    )

        if (
            transformed_table
            and hierarchy_info["is_hierarchical"]
            and source_table
            and source_table != transformed_table
        ):
            if transformed_records is None:
                transformed_records = _load_table_records(db_path, transformed_table)
            source_records = _load_table_records(db_path, source_table)
            terminal_item_ids = {
                record.get(group_id_column)
                for record in terminal_records
                if record.get(group_id_column) is not None
            }
            field_analysis.update(
                _build_hierarchy_context_field_analysis(
                    source_records=source_records,
                    transformed_records=transformed_records,
                    id_column=group_id_column,
                    terminal_item_ids=terminal_item_ids,
                    terminal_rank_values=terminal_rank_values,
                )
            )

        # Generate suggestions
        image_display_fields, consumed_image_paths = (
            _build_image_display_field_suggestions(field_analysis)
        )
        display_fields = list(image_display_fields)
        filters = []

        # Track if we found a rank field with terminal values for hierarchical entities
        rank_filter_added = False

        # Sort fields by relevance: priority first, then name fields, then category fields
        sorted_fields = sorted(
            field_analysis.items(),
            key=lambda x: (
                # Priority: high priority first
                0 if x[1].get("priority", "low") == "high" else 1,
                # Then name fields
                0 if _is_name_field(x[0]) else 1,
                # Then category fields
                0 if _is_category_field(x[0]) else 1,
                # Then by cardinality for select types
                x[1]["cardinality"] if x[1]["type"] == "select" else 1000,
            ),
        )

        for path, info in sorted_fields:
            if path in consumed_image_paths:
                continue

            priority = info.get("priority", "low")
            field_type = info["type"]
            link_display_metadata = _build_link_display_metadata(path, info)

            if _is_metadata_field(path):
                continue
            if _is_enrichment_metadata_field(path):
                continue
            if _is_identifier_field(path, group_by):
                continue

            if (
                field_type == "text"
                and _is_category_field(path)
                and 1 < info["cardinality"] <= 20
            ):
                field_type = "select"

            if (
                terminal_records
                and path != terminal_rank_path
                and _is_parent_context_field(path)
                and _get_path_coverage(terminal_records, path) < 0.4
            ):
                continue

            # For initial suggestions, only include high priority fields
            # Low priority fields are skipped (user can add manually)
            if priority == "low":
                continue

            # Skip if cardinality is too high for meaningful display
            if field_type == "text" and info["cardinality"] > 50:
                if (
                    not _is_name_field(path)
                    and not link_display_metadata
                    and not path.startswith("hierarchy_context.")
                ):
                    continue

            # Skip json_array types (not useful for index display)
            if field_type == "json_array":
                continue

            # Create display field suggestion
            is_searchable = _is_name_field(path) and not link_display_metadata
            is_filter_candidate = (
                field_type in ["select", "boolean"]
                and info["cardinality"] <= 20
                and info["cardinality"] >= 2
            )

            # Determine format
            format_hint = None
            if field_type == "select":
                format_hint = "map"
            elif field_type == "boolean":
                format_hint = "badge"

            field_name = _get_field_leaf_name(path)
            field_label = _get_suggestion_label(path, info)
            display_hint = None
            inline_badge = False
            link_label = None
            link_title = None
            link_target = None

            if link_display_metadata:
                field_name = link_display_metadata["name"]
                field_label = link_display_metadata["label"]
                display_hint = "link"
                link_label = link_display_metadata["link_label"]
                link_title = link_display_metadata["link_title"]
                link_target = link_display_metadata["link_target"] or None
            elif field_type == "boolean" and _should_inline_boolean_badge(path):
                inline_badge = True

            display_field = SuggestedDisplayField(
                name=field_name,
                source=path,
                type=field_type,
                label=field_label,
                searchable=is_searchable,
                cardinality=info["cardinality"],
                sample_values=info["sample_values"],
                suggested_as_filter=is_filter_candidate,
                format=format_hint,
                dynamic_options=is_filter_candidate and info["cardinality"] > 5,
                priority=priority,
                display=display_hint,
                inline_badge=inline_badge,
                link_label=link_label,
                link_title=link_title,
                link_target=link_target,
            )
            display_fields.append(display_field)

            # Create filter suggestion if appropriate (only for high priority fields)
            if is_filter_candidate:
                filter_values = info["sample_values"][:20]  # Limit filter values

                # For hierarchical entities, check if this is a rank field
                # and pre-select terminal ranks (species, subspecies, etc.)
                is_rank = _is_rank_field(path)
                if (
                    hierarchy_info["is_hierarchical"]
                    and is_rank
                    and not rank_filter_added
                ):
                    terminal_values = (
                        terminal_rank_values if path == terminal_rank_path else []
                    )
                    if not terminal_values:
                        terminal_values = _detect_terminal_ranks(filter_values)
                    if terminal_values:
                        # Add rank filter with terminal values pre-selected
                        filters.insert(
                            0,  # Insert at beginning (priority filter)
                            SuggestedFilter(
                                field=path,
                                source=path,
                                label=_get_suggestion_label(path, info)
                                + " (terminaux)",
                                type=field_type,
                                values=terminal_values,  # Only terminal ranks
                                operator="in",
                            ),
                        )
                        rank_filter_added = True
                        continue  # Don't add the regular filter

                filters.append(
                    SuggestedFilter(
                        field=path,
                        source=path,
                        label=_get_suggestion_label(path, info),
                        type=field_type,
                        values=filter_values,
                        operator="in",
                    )
                )

        # Deduplicate fields by name, preferring transformation sources over extra_data
        deduplicated_fields = []
        seen_names: Dict[str, int] = {}  # name -> index in deduplicated_fields

        for field in display_fields:
            field_name = field.name
            is_extra_data_source = field.source.startswith("extra_data.")

            if field_name in seen_names:
                # We have a duplicate name
                existing_idx = seen_names[field_name]
                existing_field = deduplicated_fields[existing_idx]
                existing_is_extra_data = existing_field.source.startswith("extra_data.")

                # Prefer transformation source over extra_data
                if existing_is_extra_data and not is_extra_data_source:
                    # Replace the extra_data version with the transformation version
                    deduplicated_fields[existing_idx] = field
                # else: keep the existing one (either it's from transformation, or both are extra_data)
            else:
                seen_names[field_name] = len(deduplicated_fields)
                deduplicated_fields.append(field)

        # Also deduplicate filters by field name
        deduplicated_filters = []
        seen_filter_names: set = set()

        for flt in filters:
            filter_name = _get_field_leaf_name(flt.field)
            is_extra_data_source = flt.source.startswith("extra_data.")

            if filter_name not in seen_filter_names:
                seen_filter_names.add(filter_name)
                deduplicated_filters.append(flt)
            elif not is_extra_data_source:
                # Replace extra_data filter with transformation filter
                for i, existing_flt in enumerate(deduplicated_filters):
                    existing_name = _get_field_leaf_name(existing_flt.field)
                    if existing_name == filter_name and existing_flt.source.startswith(
                        "extra_data."
                    ):
                        deduplicated_filters[i] = flt
                        break

        return IndexFieldSuggestions(
            display_fields=deduplicated_fields[
                :15
            ],  # Limit to top 15 high priority fields
            filters=deduplicated_filters[:5],  # Limit to top 5 filters
            total_entities=int(total_count),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing data: {str(e)}")


@router.post("/scaffold")
async def scaffold_configs_endpoint() -> Dict[str, Any]:
    """Scaffold les configs transform.yml et export.yml à partir de import.yml.

    Crée des groupes minimaux pour chaque référence absente.
    Idempotent : les groupes existants ne sont pas modifiés.
    Utile après ajout d'une nouvelle référence dans import.yml.
    """
    from niamoto.gui.api.services.templates.config_scaffold import scaffold_configs

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not configured")

    try:
        changed, message = scaffold_configs(work_dir)
        return {
            "success": True,
            "changed": changed,
            "message": message,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scaffold error: {str(e)}",
        )
