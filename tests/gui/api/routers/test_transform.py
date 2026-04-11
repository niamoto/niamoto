"""Regression tests for transform route group filtering."""

from pathlib import Path

import pytest

from niamoto.gui.api.routers import transform as transform_router


class _DummyJobStore:
    def __init__(self) -> None:
        self.completed_result = None
        self.failed_error = None

    def update_progress(self, job_id: str, progress: int, message: str) -> None:
        return None

    def complete_job(self, job_id: str, result: dict) -> None:
        self.completed_result = result

    def fail_job(self, job_id: str, error: str) -> None:
        self.failed_error = error


@pytest.mark.anyio
async def test_execute_transform_background_filters_requested_group_bys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_group_names: list[str] = []

    class DummyTransformerService:
        def __init__(self, db_path: str, config, enable_cli_integration: bool = False):
            self.transforms_config = []
            self.config = type("DummyConfig", (), {"transforms": []})()

        def transform_data(self, group_by, csv_file, recreate_table, progress_callback):
            captured_group_names.extend(
                [group["group_by"] for group in self.transforms_config]
            )
            return {
                group["group_by"]: {
                    "widgets": {name: 1 for name in group["widgets_data"]}
                }
                for group in self.transforms_config
            }

    transform_config = [
        {"group_by": "taxons", "widgets_data": {"widget_a": {"plugin": "foo"}}},
        {
            "group_by": "plots_hierarchy",
            "widgets_data": {"widget_b": {"plugin": "bar"}},
        },
        {"group_by": "shapes", "widgets_data": {"widget_c": {"plugin": "baz"}}},
    ]

    monkeypatch.setattr(
        transform_router, "get_transform_config", lambda path: transform_config
    )
    monkeypatch.setattr(
        transform_router, "get_database_path", lambda: tmp_path / "db.duckdb"
    )
    monkeypatch.setattr(transform_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        transform_router, "Config", lambda config_dir, create_default=False: object()
    )
    monkeypatch.setattr(transform_router, "TransformerService", DummyTransformerService)

    job_store = _DummyJobStore()

    await transform_router.execute_transform_background(
        "job-1",
        job_store,
        "config/transform.yml",
        None,
        None,
        ["taxons", "shapes"],
    )

    assert job_store.failed_error is None
    assert captured_group_names == ["taxons", "shapes"]
    assert job_store.completed_result is not None
    assert set(job_store.completed_result["transformations"].keys()) == {
        "widget_a",
        "widget_c",
    }
