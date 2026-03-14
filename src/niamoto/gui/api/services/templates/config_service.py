"""
Configuration loading and saving service for transform and export configs.

Centralizes all config file operations to avoid duplication across routers.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from niamoto.common.transform_config_models import validate_transform_config

logger = logging.getLogger(__name__)


def load_transform_config(work_dir: Path) -> List[Dict[str, Any]]:
    """Load canonical transform.yml configuration (list of groups).

    Args:
        work_dir: Working directory containing config/transform.yml

    Returns:
        List of validated transform group configurations
    """
    transform_path = work_dir / "config" / "transform.yml"
    if not transform_path.exists():
        return []

    with open(transform_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or []

    if not isinstance(config, list):
        raise ValueError("transform.yml must be a list of groups")

    return validate_transform_config(config)


def save_transform_config(
    work_dir: Path,
    config: List[Dict[str, Any]],
    create_backup: bool = False,
) -> None:
    """Save transform.yml configuration in canonical list format.

    Args:
        work_dir: Working directory containing config/transform.yml
        config: Transform configuration as list of groups
        create_backup: Whether to create backup of existing file
    """
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    transform_path = config_dir / "transform.yml"

    # Optional backup creation
    if create_backup and transform_path.exists():
        _create_backup_file(transform_path)

    canonical_config = validate_transform_config(config)

    with open(transform_path, "w", encoding="utf-8") as f:
        yaml.dump(
            canonical_config,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


def load_export_config(work_dir: Path) -> Dict[str, Any]:
    """Load export.yml configuration.

    Args:
        work_dir: Working directory containing config/export.yml

    Returns:
        Export configuration dict, with empty exports list if file doesn't exist
    """
    export_path = work_dir / "config" / "export.yml"
    if not export_path.exists():
        return {"exports": []}

    with open(export_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config if isinstance(config, dict) else {"exports": []}


def save_export_config(
    work_dir: Path,
    config: Dict[str, Any],
    create_backup: bool = False,
) -> None:
    """Save export.yml configuration.

    Args:
        work_dir: Working directory containing config/export.yml
        config: Export configuration dict
        create_backup: Whether to create backup of existing file
    """
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    export_path = config_dir / "export.yml"

    # Optional backup creation
    if create_backup and export_path.exists():
        _create_backup_file(export_path)

    with open(export_path, "w", encoding="utf-8") as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


def find_transform_group(
    groups: List[Dict[str, Any]], group_by: str
) -> Optional[Dict[str, Any]]:
    """Find a group in transform config by group_by value.

    Args:
        groups: List of transform group configurations
        group_by: The group_by value to search for (e.g., 'taxons', 'plots')

    Returns:
        The matching group dict, or None if not found
    """
    for group in groups:
        if group.get("group_by") == group_by:
            return group
    return None


def find_export_group(
    export_config: Dict[str, Any], group_by: str
) -> Optional[Dict[str, Any]]:
    """Find export group by group_by value.

    Args:
        export_config: Export configuration dict
        group_by: The group_by value to search for

    Returns:
        The matching group dict, or None if not found
    """
    exports = export_config.get("exports", [])
    for export_entry in exports:
        groups = export_entry.get("groups", [])
        for group in groups:
            if group.get("group_by") == group_by:
                return group
    return None


def find_or_create_transform_group(
    groups: List[Dict[str, Any]], group_by: str
) -> Dict[str, Any]:
    """Find or create a transform group for the given group_by.

    Args:
        groups: List of transform group configurations (modified in place)
        group_by: The group_by value to find or create

    Returns:
        The existing or newly created group dict
    """
    existing = find_transform_group(groups, group_by)
    if existing:
        return existing

    # Create new group
    new_group = {
        "group_by": group_by,
        "sources": [],
        "widgets_data": {},
    }
    groups.append(new_group)
    return new_group


def _create_backup_file(file_path: Path) -> None:
    """Create a numbered backup of a file.

    Args:
        file_path: Path to the file to backup
    """
    import shutil
    from datetime import datetime

    backup_dir = file_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
    backup_path = backup_dir / backup_name

    shutil.copy2(file_path, backup_path)
    logger.debug(f"Created backup: {backup_path}")
