"""Runtime resolver for project-scoped JobFileStore instances."""

import logging
from pathlib import Path
from typing import Any

from niamoto.gui.api.context import get_working_directory
from niamoto.gui.api.services.job_file_store import JobFileStore

logger = logging.getLogger(__name__)


def resolve_job_store(app: Any) -> JobFileStore:
    """Return the JobFileStore for the current working directory.

    The desktop app can switch projects at runtime without restarting the API.
    This helper keeps ``app.state.job_store`` aligned with the current project
    and recreates the file-backed store whenever the working directory changes.
    """

    work_dir = Path(get_working_directory())
    current_store = getattr(app.state, "job_store", None)
    current_store_work_dir = getattr(app.state, "job_store_work_dir", None)

    if current_store is not None and current_store_work_dir == work_dir:
        return current_store

    job_store = JobFileStore(work_dir)
    orphan = job_store.recover_on_startup()
    if orphan:
        logger.warning(
            "Recovered orphan job on project switch/startup: %s", orphan["id"]
        )

    app.state.job_store = job_store
    app.state.job_store_work_dir = work_dir
    return job_store
