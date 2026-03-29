"""Tests for project-scoped job store resolution."""

import tempfile
from pathlib import Path

from fastapi import FastAPI

from niamoto.gui.api.services.job_store_runtime import resolve_job_store


def test_resolve_job_store_switches_with_working_directory(monkeypatch):
    app = FastAPI()

    with tempfile.TemporaryDirectory() as temp1, tempfile.TemporaryDirectory() as temp2:
        work_dir_1 = Path(temp1)
        work_dir_2 = Path(temp2)

        monkeypatch.setattr(
            "niamoto.gui.api.services.job_store_runtime.get_working_directory",
            lambda: work_dir_1,
        )
        store_1 = resolve_job_store(app)
        job_1 = store_1.create_job("export")
        store_1.complete_job(job_1["id"], result={"metrics": {"generated_pages": 12}})

        assert store_1.get_last_run("export", status="completed") is not None
        assert app.state.job_store_work_dir == work_dir_1

        monkeypatch.setattr(
            "niamoto.gui.api.services.job_store_runtime.get_working_directory",
            lambda: work_dir_2,
        )
        store_2 = resolve_job_store(app)

        assert store_2 is not store_1
        assert app.state.job_store_work_dir == work_dir_2
        assert store_2.get_last_run("export", status="completed") is None

        job_2 = store_2.create_job("export")
        store_2.complete_job(job_2["id"], result={"metrics": {"generated_pages": 3}})

        assert store_2.get_last_run("export", status="completed")["id"] == job_2["id"]
