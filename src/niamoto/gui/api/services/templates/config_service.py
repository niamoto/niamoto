"""
Configuration loading and saving service for transform and export configs.

Centralizes all config file operations to avoid duplication across routers.
"""

import logging
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from niamoto.common.transform_config_models import validate_transform_config

logger = logging.getLogger(__name__)
TRANSFORM_CONFIG_WRITE_LOCK = threading.RLock()
EXPORT_CONFIG_WRITE_LOCK = threading.RLock()
TRANSFORM_EXPORT_TRANSACTION_MARKER = ".transform_export_write_pending.yml"
TRANSFORM_EXPORT_TRANSACTION_LOCK = ".transform_export_write.lock"
_ALLOWED_TRANSACTION_TARGETS = {
    Path("config/transform.yml"),
    Path("config/export.yml"),
}

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]


def _write_yaml_atomic(path: Path, payload: Any) -> None:
    """Write YAML through a same-directory temp file and atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Optional[Path] = None
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(
                payload,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=120,
            )
            f.flush()
            os.fsync(f.fileno())
        temp_path.replace(path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def _copy_file_atomic(source: Path, target: Path) -> None:
    """Copy a file to a same-directory temp path before atomically replacing target."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as temp_file:
            with source.open("rb") as source_file:
                shutil.copyfileobj(source_file, temp_file)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        shutil.copystat(source, temp_path)
        temp_path.replace(target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _relative_config_path(work_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(work_dir))
    except ValueError:
        return str(path)


def _resolve_under(base: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(base.resolve())
    except ValueError:
        return False
    return True


def _path_from_transaction(
    work_dir: Path,
    value: str | None,
    *,
    allowed_targets: set[Path] | None = None,
    required_parent: Path | None = None,
) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"Transaction path must be relative: {value}")

    resolved = (work_dir / path).resolve()
    work_root = work_dir.resolve()
    try:
        relative_path = resolved.relative_to(work_root)
    except ValueError as exc:
        raise ValueError(f"Transaction path escapes project: {value}") from exc

    if allowed_targets is not None and relative_path not in allowed_targets:
        raise ValueError(f"Unexpected transaction target path: {value}")

    if required_parent is not None and not _resolve_under(required_parent, resolved):
        raise ValueError(f"Transaction path is outside its snapshot directory: {value}")

    return resolved


def _transaction_dir_from_marker(work_dir: Path, marker: dict[str, Any]) -> Path | None:
    transaction_dir = _path_from_transaction(work_dir, marker.get("transaction_dir"))
    if transaction_dir is None:
        return None

    transactions_root = (work_dir / "config" / ".transactions").resolve()
    if transaction_dir == transactions_root or not _resolve_under(
        transactions_root,
        transaction_dir,
    ):
        raise ValueError("Transaction directory is outside config/.transactions")
    return transaction_dir


@contextmanager
def _paired_config_transaction_lock(work_dir: Path):
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    lock_path = config_dir / TRANSFORM_EXPORT_TRANSACTION_LOCK
    with TRANSFORM_CONFIG_WRITE_LOCK, EXPORT_CONFIG_WRITE_LOCK:
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _snapshot_transaction_target(
    path: Path, snapshot_dir: Path
) -> tuple[bool, Path | None]:
    if not path.exists():
        return False, None

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{path.name}.rollback"
    shutil.copy2(path, snapshot_path)
    return True, snapshot_path


def _restore_transaction_targets(work_dir: Path, marker: dict[str, Any]) -> None:
    transaction_dir = _transaction_dir_from_marker(work_dir, marker)
    for target in marker.get("targets", []):
        if not isinstance(target, dict):
            continue
        target_path = _path_from_transaction(
            work_dir,
            target.get("path"),
            allowed_targets=_ALLOWED_TRANSACTION_TARGETS,
        )
        if target_path is None:
            continue
        if transaction_dir is None and target.get("rollback_path"):
            raise ValueError("Rollback snapshot requires a transaction directory")
        snapshot_path = _path_from_transaction(
            work_dir,
            target.get("rollback_path"),
            required_parent=transaction_dir,
        )
        if target.get("existed") and snapshot_path and snapshot_path.exists():
            _copy_file_atomic(snapshot_path, target_path)
        elif not target.get("existed"):
            target_path.unlink(missing_ok=True)


def _recover_pending_config_transaction_locked(work_dir: Path) -> None:
    """Restore transform/export files if a previous paired write was interrupted."""

    config_dir = work_dir / "config"
    marker_path = config_dir / TRANSFORM_EXPORT_TRANSACTION_MARKER
    if not marker_path.exists():
        return

    marker: dict[str, Any] = {}
    try:
        with marker_path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        marker = loaded if isinstance(loaded, dict) else {}
        if marker.get("operation") == "transform_export_write":
            _restore_transaction_targets(work_dir, marker)
    except ValueError as exc:
        logger.warning("Ignoring invalid pending config transaction marker: %s", exc)
        marker_path.unlink(missing_ok=True)
        return
    except Exception:
        logger.exception("Failed to recover pending transform/export transaction")
        raise

    marker_path.unlink(missing_ok=True)
    transaction_dir = _transaction_dir_from_marker(work_dir, marker)
    if transaction_dir and transaction_dir.exists():
        shutil.rmtree(transaction_dir, ignore_errors=True)


def recover_pending_config_transaction(work_dir: Path) -> None:
    """Restore transform/export files if a previous paired write was interrupted."""
    with _paired_config_transaction_lock(work_dir):
        _recover_pending_config_transaction_locked(work_dir)


def save_transform_and_export_configs(
    work_dir: Path,
    transform_config: List[Dict[str, Any]],
    export_config: Dict[str, Any],
    create_backup: bool = False,
) -> tuple[Optional[Path], Optional[Path]]:
    """Save transform.yml and export.yml as one recoverable config update."""
    with _paired_config_transaction_lock(work_dir):
        config_dir = work_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        _recover_pending_config_transaction_locked(work_dir)

        transform_path = config_dir / "transform.yml"
        export_path = config_dir / "export.yml"
        canonical_transform = validate_transform_config(transform_config)

        transform_backup = None
        export_backup = None
        if create_backup and transform_path.exists():
            transform_backup = _create_backup_file(transform_path)
        if create_backup and export_path.exists():
            export_backup = _create_backup_file(export_path)

        transaction_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        transaction_dir = (
            config_dir / ".transactions" / f"transform_export_{transaction_id}"
        )
        transform_existed, transform_snapshot = _snapshot_transaction_target(
            transform_path,
            transaction_dir,
        )
        export_existed, export_snapshot = _snapshot_transaction_target(
            export_path,
            transaction_dir,
        )
        marker_path = config_dir / TRANSFORM_EXPORT_TRANSACTION_MARKER
        marker = {
            "operation": "transform_export_write",
            "transaction_dir": _relative_config_path(work_dir, transaction_dir),
            "targets": [
                {
                    "path": _relative_config_path(work_dir, transform_path),
                    "existed": transform_existed,
                    "rollback_path": _relative_config_path(work_dir, transform_snapshot)
                    if transform_snapshot
                    else None,
                },
                {
                    "path": _relative_config_path(work_dir, export_path),
                    "existed": export_existed,
                    "rollback_path": _relative_config_path(work_dir, export_snapshot)
                    if export_snapshot
                    else None,
                },
            ],
        }

        _write_yaml_atomic(marker_path, marker)
        try:
            _write_yaml_atomic(transform_path, canonical_transform)
            _write_yaml_atomic(export_path, export_config)
        except Exception:
            _restore_transaction_targets(work_dir, marker)
            marker_path.unlink(missing_ok=True)
            shutil.rmtree(transaction_dir, ignore_errors=True)
            raise

        marker_path.unlink(missing_ok=True)
        shutil.rmtree(transaction_dir, ignore_errors=True)

        return transform_backup, export_backup


def load_transform_config(work_dir: Path) -> List[Dict[str, Any]]:
    """Load canonical transform.yml configuration (list of groups).

    Args:
        work_dir: Working directory containing config/transform.yml

    Returns:
        List of validated transform group configurations
    """
    if not (work_dir / "config").exists():
        return []
    with _paired_config_transaction_lock(work_dir):
        _recover_pending_config_transaction_locked(work_dir)
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
) -> Optional[Path]:
    """Save transform.yml configuration in canonical list format.

    Args:
        work_dir: Working directory containing config/transform.yml
        config: Transform configuration as list of groups
        create_backup: Whether to create backup of existing file
    """
    with _paired_config_transaction_lock(work_dir):
        _recover_pending_config_transaction_locked(work_dir)
        config_dir = work_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        transform_path = config_dir / "transform.yml"

        # Optional backup creation
        backup_path = None
        if create_backup and transform_path.exists():
            backup_path = _create_backup_file(transform_path)

        canonical_config = validate_transform_config(config)

        _write_yaml_atomic(transform_path, canonical_config)
        return backup_path


def load_import_config(work_dir: Path) -> Dict[str, Any]:
    """Load import.yml configuration."""
    import_path = work_dir / "config" / "import.yml"
    if not import_path.exists():
        return {"entities": {"references": {}, "datasets": {}}}

    with open(import_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        return {"entities": {"references": {}, "datasets": {}}}

    entities = config.setdefault("entities", {})
    if isinstance(entities, dict):
        entities.setdefault("references", {})
        entities.setdefault("datasets", {})
    return config


def save_import_config(
    work_dir: Path,
    config: Dict[str, Any],
    create_backup: bool = False,
) -> None:
    """Save import.yml configuration."""
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    import_path = config_dir / "import.yml"

    if create_backup and import_path.exists():
        _create_backup_file(import_path)

    _write_yaml_atomic(import_path, config)


def load_export_config(work_dir: Path) -> Dict[str, Any]:
    """Load export.yml configuration.

    Args:
        work_dir: Working directory containing config/export.yml

    Returns:
        Export configuration dict, with empty exports list if file doesn't exist
    """
    if not (work_dir / "config").exists():
        return {"exports": []}
    with _paired_config_transaction_lock(work_dir):
        _recover_pending_config_transaction_locked(work_dir)
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
) -> Optional[Path]:
    """Save export.yml configuration.

    Args:
        work_dir: Working directory containing config/export.yml
        config: Export configuration dict
        create_backup: Whether to create backup of existing file
    """
    with _paired_config_transaction_lock(work_dir):
        _recover_pending_config_transaction_locked(work_dir)
        config_dir = work_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        export_path = config_dir / "export.yml"

        # Optional backup creation
        backup_path = None
        if create_backup and export_path.exists():
            backup_path = _create_backup_file(export_path)

        _write_yaml_atomic(export_path, config)
        return backup_path


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
        params = export_entry.get("params", {}) or {}
        for group in params.get("groups", []) or []:
            if isinstance(group, dict) and group.get("group_by") == group_by:
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


def _create_backup_file(file_path: Path) -> Path:
    """Create a numbered backup of a file.

    Args:
        file_path: Path to the file to backup
    """
    backup_dir = file_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for attempt in range(1000):
        suffix = "" if attempt == 0 else f"_{attempt}"
        backup_name = f"{file_path.stem}_{timestamp}{suffix}{file_path.suffix}"
        backup_path = backup_dir / backup_name
        try:
            with file_path.open("rb") as source, backup_path.open("xb") as backup:
                shutil.copyfileobj(source, backup)
            shutil.copystat(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
            return backup_path
        except FileExistsError:
            continue

    raise RuntimeError(f"Could not create a unique backup for {file_path.name}")
