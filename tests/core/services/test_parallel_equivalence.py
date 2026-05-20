from __future__ import annotations

import os
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.core.services.exporter import ExporterService
from niamoto.core.services.transformer import TransformerService


_PLOTLY_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def _copy_instance(source: Path, destination: Path) -> Path:
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".ruff_cache", "__pycache__"),
    )
    return destination


@contextmanager
def _project_env(project_dir: Path):
    previous = os.environ.get("NIAMOTO_HOME")
    os.environ["NIAMOTO_HOME"] = str(project_dir)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("NIAMOTO_HOME", None)
        else:
            os.environ["NIAMOTO_HOME"] = previous


def _run_transform(project_dir: Path) -> None:
    config = Config(str(project_dir / "config"), create_default=False)
    service = TransformerService(
        config.database_path, config, enable_cli_integration=False
    )
    try:
        service.transform_data()
    finally:
        service.db.close_db_session()


def _load_transform_tables(project_dir: Path) -> dict[str, list[dict]]:
    config = Config(str(project_dir / "config"), create_default=False)
    db = Database(config.database_path, read_only=True)
    try:
        tables: dict[str, list[dict]] = {}
        for group_config in config.get_transforms_config():
            group_by = group_config.get("group_by")
            if not group_by:
                continue
            id_column = f"{group_by}_id"
            tables[group_by] = db.fetch_all(
                f"SELECT * FROM {group_by} ORDER BY {id_column}"
            )
        return tables
    finally:
        db.close_db_session()


def _run_export(project_dir: Path) -> dict[str, dict]:
    export_dir = project_dir / "exports" / "web"
    if export_dir.exists():
        shutil.rmtree(export_dir)

    config = Config(str(project_dir / "config"), create_default=False)
    service = ExporterService(config.database_path, config)
    try:
        result = service.run_export(target_name="web_pages")
    finally:
        service.db.close_db_session()
    return result


def _normalize_html(content: str) -> str:
    return _PLOTLY_UUID_RE.sub("PLOTLY_UUID", content)


def _collect_export_html(project_dir: Path) -> dict[str, str]:
    root = project_dir / "exports" / "web"
    html_files = sorted(root.rglob("*.html"))
    assert html_files, f"Expected exported HTML files under {root}"
    collected = {
        str(path.relative_to(root)): _normalize_html(path.read_text(encoding="utf-8"))
        for path in html_files
    }
    assert "index.html" in collected
    return collected


def _assert_successful_web_export(result: dict[str, dict]) -> None:
    web_result = result["web_pages"]
    assert web_result["status"] == "success"
    assert web_result["errors"] == 0
    assert web_result["files_generated"] > 0


@pytest.mark.slow
@pytest.mark.integration
def test_export_html_is_stable_across_independent_runs(
    tmp_path: Path,
    niamoto_subset_instance_dir: Path,
):
    first_project = _copy_instance(
        niamoto_subset_instance_dir, tmp_path / "subset-export-first"
    )
    second_project = _copy_instance(
        niamoto_subset_instance_dir, tmp_path / "subset-export-second"
    )

    with _project_env(first_project):
        first_result = _run_export(first_project)
    with _project_env(second_project):
        second_result = _run_export(second_project)

    _assert_successful_web_export(first_result)
    _assert_successful_web_export(second_result)

    first_html = _collect_export_html(first_project)
    second_html = _collect_export_html(second_project)

    assert second_html == first_html
