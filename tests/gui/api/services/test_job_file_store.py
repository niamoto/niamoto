"""Tests unitaires pour JobFileStore."""

import json
import os
import threading
from pathlib import Path

import pytest

from niamoto.gui.api.services.job_file_store import JobFileStore


@pytest.fixture
def store(tmp_path: Path) -> JobFileStore:
    """Crée un JobFileStore dans un répertoire temporaire."""
    return JobFileStore(tmp_path)


@pytest.fixture
def active_path(store: JobFileStore) -> Path:
    return store._active_path


@pytest.fixture
def history_path(store: JobFileStore) -> Path:
    return store._history_path


# --- create_job ---


class TestCreateJob:
    def test_creates_running_job(self, store: JobFileStore):
        job = store.create_job("transform", group_by="taxons")
        assert job["status"] == "running"
        assert job["type"] == "transform"
        assert job["group_by"] == "taxons"
        assert job["progress"] == 0
        assert job["pid"] == os.getpid()
        assert job["id"]

    def test_persists_to_file(self, store: JobFileStore, active_path: Path):
        job = store.create_job("export")
        assert active_path.exists()
        data = json.loads(active_path.read_text())
        assert data["id"] == job["id"]

    def test_rejects_when_job_running(self, store: JobFileStore):
        store.create_job("transform")
        with pytest.raises(RuntimeError, match="déjà en cours"):
            store.create_job("export")

    def test_archives_terminal_job_before_creating_new(
        self, store: JobFileStore, history_path: Path
    ):
        job1 = store.create_job("transform")
        store.complete_job(job1["id"])
        job2 = store.create_job("export")
        assert job2["type"] == "export"
        # job1 doit être dans l'historique
        assert history_path.exists()
        lines = history_path.read_text().strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["id"] == job1["id"]


# --- update_progress ---


class TestUpdateProgress:
    def test_updates_progress_and_message(self, store: JobFileStore):
        job = store.create_job("transform")
        store.update_progress(job["id"], 45, "En cours...")
        updated = store.get_active_job()
        assert updated["progress"] == 45
        assert updated["message"] == "En cours..."

    def test_updates_phase(self, store: JobFileStore):
        job = store.create_job("export")
        store.update_progress(job["id"], 30, "Transform", phase="transform")
        updated = store.get_active_job()
        assert updated["phase"] == "transform"

    def test_updates_updated_at(self, store: JobFileStore):
        job = store.create_job("transform")
        initial_updated = job["updated_at"]
        store.update_progress(job["id"], 10, "msg")
        updated = store.get_active_job()
        assert updated["updated_at"] >= initial_updated

    def test_ignores_wrong_job_id(self, store: JobFileStore):
        store.create_job("transform")
        store.update_progress("wrong-id", 99, "hack")
        assert store.get_active_job()["progress"] == 0


# --- complete_job ---


class TestCompleteJob:
    def test_marks_completed(self, store: JobFileStore):
        job = store.create_job("transform")
        store.complete_job(job["id"], result={"count": 42})
        completed = store.get_active_job()
        assert completed["status"] == "completed"
        assert completed["progress"] == 100
        assert completed["result"] == {"count": 42}
        assert completed["completed_at"] is not None

    def test_stays_in_active_file(self, store: JobFileStore, active_path: Path):
        """Le job completed reste dans active_job.json (pas de 404 sur le dernier poll)."""
        job = store.create_job("transform")
        store.complete_job(job["id"])
        assert active_path.exists()
        data = json.loads(active_path.read_text())
        assert data["status"] == "completed"


# --- fail_job ---


class TestFailJob:
    def test_marks_failed(self, store: JobFileStore):
        job = store.create_job("export")
        store.fail_job(job["id"], "Erreur DuckDB")
        failed = store.get_active_job()
        assert failed["status"] == "failed"
        assert failed["error"] == "Erreur DuckDB"
        assert failed["completed_at"] is not None


# --- get_job ---


class TestGetJob:
    def test_finds_active_job(self, store: JobFileStore):
        job = store.create_job("transform")
        found = store.get_job(job["id"])
        assert found["id"] == job["id"]

    def test_finds_archived_job(self, store: JobFileStore):
        job1 = store.create_job("transform")
        store.complete_job(job1["id"])
        store.create_job("export")  # archive job1
        # job1 est archivé, le nouveau job est actif
        found = store.get_job(job1["id"])
        assert found is not None
        assert found["id"] == job1["id"]

    def test_returns_none_for_unknown(self, store: JobFileStore):
        assert store.get_job("unknown-id") is None


# --- get_running_job ---


class TestGetRunningJob:
    def test_returns_running_job(self, store: JobFileStore):
        job = store.create_job("transform")
        assert store.get_running_job()["id"] == job["id"]

    def test_returns_none_when_completed(self, store: JobFileStore):
        job = store.create_job("transform")
        store.complete_job(job["id"])
        assert store.get_running_job() is None

    def test_returns_none_when_empty(self, store: JobFileStore):
        assert store.get_running_job() is None


# --- get_history ---


class TestGetHistory:
    def test_empty_history(self, store: JobFileStore):
        assert store.get_history() == []

    def test_returns_archived_jobs(self, store: JobFileStore):
        job1 = store.create_job("transform")
        store.complete_job(job1["id"])
        job2 = store.create_job("export")
        store.complete_job(job2["id"])
        # job1 archivé quand job2 créé, job2 encore dans active
        history = store.get_history()
        assert len(history) == 1
        assert history[0]["id"] == job1["id"]

    def test_most_recent_first(self, store: JobFileStore):
        ids = []
        for i in range(3):
            job = store.create_job("transform")
            store.complete_job(job["id"])
            ids.append(job["id"])
        # Les 2 premiers sont archivés (le 3e est encore dans active)
        history = store.get_history()
        assert len(history) == 2
        assert history[0]["id"] == ids[1]  # Plus récent en premier
        assert history[1]["id"] == ids[0]


# --- get_last_run ---


class TestGetLastRun:
    def test_finds_active_terminal_job(self, store: JobFileStore):
        job = store.create_job("transform", group_by="taxons")
        store.complete_job(job["id"])
        last = store.get_last_run("transform", group_by="taxons")
        assert last is not None
        assert last["id"] == job["id"]

    def test_finds_in_history(self, store: JobFileStore):
        job1 = store.create_job("transform", group_by="taxons")
        store.complete_job(job1["id"])
        store.create_job("export")  # Crée un nouveau job (archive job1)
        last = store.get_last_run("transform", group_by="taxons")
        assert last is not None
        assert last["id"] == job1["id"]

    def test_filters_by_type(self, store: JobFileStore):
        job = store.create_job("transform")
        store.complete_job(job["id"])
        assert store.get_last_run("export") is None

    def test_filters_by_group(self, store: JobFileStore):
        job = store.create_job("transform", group_by="taxons")
        store.complete_job(job["id"])
        assert store.get_last_run("transform", group_by="plots") is None


# --- recover_on_startup ---


class TestRecoverOnStartup:
    def test_no_active_job(self, store: JobFileStore):
        assert store.recover_on_startup() is None

    def test_archives_terminal_job(
        self, store: JobFileStore, active_path: Path, history_path: Path
    ):
        job = store.create_job("transform")
        store.complete_job(job["id"])
        result = store.recover_on_startup()
        assert result is None
        assert not active_path.exists()
        assert history_path.exists()

    def test_marks_orphan_as_interrupted(self, store: JobFileStore, active_path: Path):
        # Simuler un job orphelin avec un PID mort
        job_data = {
            "id": "orphan-123",
            "type": "transform",
            "group_by": None,
            "status": "running",
            "progress": 45,
            "message": "En cours...",
            "phase": None,
            "pid": 99999999,  # PID qui n'existe pas
            "started_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "completed_at": None,
            "result": None,
            "error": None,
        }
        active_path.write_text(json.dumps(job_data))
        result = store.recover_on_startup()
        assert result is not None
        assert result["status"] == "interrupted"
        assert not active_path.exists()


# --- purge_history ---


class TestPurgeHistory:
    def test_purge_when_empty(self, store: JobFileStore):
        assert store.purge_history(keep_last=5) == 0

    def test_purge_under_threshold(self, store: JobFileStore):
        # Créer 3 jobs archivés
        for _ in range(3):
            job = store.create_job("transform")
            store.complete_job(job["id"])
        # Le 3e est encore dans active, donc 2 archivés
        assert store.purge_history(keep_last=10) == 0

    def test_purge_over_threshold(self, store: JobFileStore, history_path: Path):
        # Écrire directement dans l'historique
        for i in range(10):
            entry = {"id": f"job-{i}", "type": "transform", "status": "completed"}
            with history_path.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        removed = store.purge_history(keep_last=3)
        assert removed == 7
        lines = history_path.read_text().strip().splitlines()
        assert len(lines) == 3


# --- Écriture atomique ---


class TestAtomicWrite:
    def test_no_tmp_file_left(self, store: JobFileStore):
        store.create_job("transform")
        tmp = store._active_path.with_suffix(".tmp")
        assert not tmp.exists()


# --- Corruption handling ---


class TestCorruptionHandling:
    def test_corrupt_json_returns_none(self, store: JobFileStore, active_path: Path):
        active_path.write_text("{invalid json!!!")
        assert store.get_active_job() is None
        # Le fichier doit avoir été renommé en .corrupt
        assert active_path.with_suffix(".corrupt").exists()

    def test_can_create_after_corruption(self, store: JobFileStore, active_path: Path):
        active_path.write_text("not json")
        job = store.create_job("transform")
        assert job["status"] == "running"


# --- Thread safety ---


class TestThreadSafety:
    def test_concurrent_create_only_one_succeeds(self, store: JobFileStore):
        """Deux threads tentent de créer un job simultanément → un seul réussit."""
        results = {"success": 0, "error": 0}
        barrier = threading.Barrier(2)

        def try_create():
            barrier.wait()
            try:
                store.create_job("transform")
                results["success"] += 1
            except RuntimeError:
                results["error"] += 1

        t1 = threading.Thread(target=try_create)
        t2 = threading.Thread(target=try_create)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["success"] == 1
        assert results["error"] == 1
