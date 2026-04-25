"""Persistance légère des jobs via fichiers JSON.

- active_job.json : état du job en cours (un seul à la fois)
- job_history.jsonl : historique append-only (1 ligne JSON par job terminé)

Design notes (revue Codex) :
- threading.Lock protège toutes les lectures/écritures (multi-onglets)
- Les jobs terminés restent dans active_job.json (status terminal)
  jusqu'au prochain create_job() → évite le 404 sur le dernier poll
- updated_at tracké pour détecter les jobs bloqués
"""

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = ("completed", "failed", "cancelled", "interrupted")


class JobFileStore:
    """Store de jobs persistant basé sur des fichiers JSON."""

    def __init__(self, work_dir: Path):
        self._dir = work_dir / ".niamoto"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._active_path = self._dir / "active_job.json"
        self._history_path = self._dir / "job_history.jsonl"
        self._lock = threading.Lock()

    # --- Cycle de vie ---

    def create_job(
        self,
        job_type: str,
        group_by: str | None = None,
        group_bys: list[str] | None = None,
    ) -> dict:
        """Crée un job. Échoue si un job non-terminal est déjà actif."""
        with self._lock:
            existing = self._read_active()
            if existing and existing["status"] not in TERMINAL_STATUSES:
                raise RuntimeError("Un job est déjà en cours")

            # Si un job terminal traîne, l'archiver d'abord
            if existing and existing["status"] in TERMINAL_STATUSES:
                self._archive(existing)

            job = {
                "id": str(uuid4()),
                "type": job_type,
                "group_by": group_by,
                "group_bys": group_bys,
                "status": "running",
                "progress": 0,
                "message": "",
                "phase": None,
                "pid": os.getpid(),
                "started_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "completed_at": None,
                "result": None,
                "error": None,
            }
            self._write_active(job)
            return job

    def update_progress(
        self,
        job_id: str,
        progress: int,
        message: str,
        phase: str | None = None,
    ) -> None:
        """Met à jour la progression du job actif."""
        with self._lock:
            job = self._read_active()
            if not job or job["id"] != job_id:
                return
            job["progress"] = progress
            job["message"] = message
            job["updated_at"] = datetime.now().isoformat()
            if phase:
                job["phase"] = phase
            self._write_active(job)

    def complete_job(self, job_id: str, result: dict | None = None) -> None:
        """Marque le job comme terminé. Reste dans active_job.json
        pour que le dernier poll puisse lire 'completed'."""
        with self._lock:
            job = self._read_active()
            if not job or job["id"] != job_id:
                return
            job["status"] = "completed"
            job["progress"] = 100
            job["completed_at"] = datetime.now().isoformat()
            job["updated_at"] = datetime.now().isoformat()
            job["result"] = result
            self._write_active(job)

    def fail_job(self, job_id: str, error: str, result: dict | None = None) -> None:
        """Marque le job comme échoué. Reste dans active_job.json."""
        with self._lock:
            job = self._read_active()
            if not job or job["id"] != job_id:
                return
            job["status"] = "failed"
            job["completed_at"] = datetime.now().isoformat()
            job["updated_at"] = datetime.now().isoformat()
            job["error"] = error
            job["result"] = result
            self._write_active(job)

    # --- Lecture ---

    def get_active_job(self, job_type: str | None = None) -> dict | None:
        """Retourne le job courant (actif ou terminal en attente d'archivage).
        Si job_type est spécifié, ne retourne le job que s'il correspond."""
        with self._lock:
            job = self._read_active()
            if job and job_type and job.get("type") != job_type:
                return None
            return job

    def get_job(self, job_id: str) -> dict | None:
        """Retourne un job par son ID (actif ou dans l'historique)."""
        with self._lock:
            active = self._read_active()
            if active and active["id"] == job_id:
                return active
            # Chercher dans l'historique
            if not self._history_path.exists():
                return None
            for line in reversed(
                self._history_path.read_text(encoding="utf-8").strip().splitlines()
            ):
                try:
                    entry = json.loads(line)
                    if entry.get("id") == job_id:
                        return entry
                except json.JSONDecodeError:
                    continue
            return None

    def get_running_job(self, job_type: str | None = None) -> dict | None:
        """Retourne le job seulement s'il est en cours (pas terminal).
        Si job_type est spécifié, ne retourne le job que s'il correspond."""
        with self._lock:
            job = self._read_active()
            if job and job["status"] not in TERMINAL_STATUSES:
                if job_type and job.get("type") != job_type:
                    return None
                return job
            return None

    def get_history(
        self,
        limit: int = 20,
        include_active_terminal: bool = False,
    ) -> list[dict]:
        """Retourne les N derniers jobs terminés (plus récent en premier).

        Le dernier job terminal peut encore être dans ``active_job.json`` pour
        permettre au poll final de le lire. On l'inclut quand même dans
        l'historique utilisateur seulement quand l'appelant le demande, afin de
        ne pas dupliquer les endpoints qui lisent déjà ``get_active_job()``.
        """
        with self._lock:
            entries = []
            seen_ids = set()

            if include_active_terminal:
                active = self._read_active()
                if active and active["status"] in TERMINAL_STATUSES:
                    entries.append(active)
                    seen_ids.add(active.get("id"))

            if not self._history_path.exists():
                return entries[:limit]

            lines = self._history_path.read_text(encoding="utf-8").strip().splitlines()
            for line in reversed(lines):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_id = entry.get("id")
                if entry_id in seen_ids:
                    continue

                entries.append(entry)
                seen_ids.add(entry_id)

                if len(entries) >= limit:
                    break

            return entries[:limit]

    def get_last_run(
        self,
        job_type: str,
        group_by: str | None = None,
        status: str | None = None,
    ) -> dict | None:
        """Retourne le dernier job terminé pour un type/groupe donné.
        Si *status* est spécifié (ex. "completed"), ne retourne que ce statut."""
        with self._lock:
            # D'abord vérifier le job actif (peut être completed mais pas encore archivé)
            active = self._read_active()
            if active and active["status"] in TERMINAL_STATUSES:
                if active["type"] == job_type:
                    active_groups = active.get("group_bys") or []
                    if (
                        group_by is None
                        or active.get("group_by") == group_by
                        or group_by in active_groups
                    ):
                        if status is None or active["status"] == status:
                            return active

            # Sinon chercher dans l'historique
            if not self._history_path.exists():
                return None
            lines = self._history_path.read_text(encoding="utf-8").strip().splitlines()
            for line in reversed(lines):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry["type"] == job_type:
                    entry_groups = entry.get("group_bys") or []
                    if (
                        group_by is None
                        or entry.get("group_by") == group_by
                        or group_by in entry_groups
                    ):
                        if status is None or entry.get("status") == status:
                            return entry
            return None

    # --- Startup : détection de jobs orphelins ---

    def recover_on_startup(self) -> dict | None:
        """Au démarrage, détecte un job orphelin (PID mort ou job non-terminal).
        Retourne le job marqué 'interrupted' ou None."""
        with self._lock:
            job = self._read_active()
            if not job:
                return None

            # Job terminal en attente d'archivage → archiver simplement
            if job["status"] in TERMINAL_STATUSES:
                self._archive(job)
                self._active_path.unlink(missing_ok=True)
                return None

            # Job non-terminal → vérifier si le process est vivant
            pid = job.get("pid")
            if pid and pid == os.getpid():
                return None  # Même process
            if pid and self._is_pid_alive(pid):
                return None  # Process encore vivant

            # PID mort ou absent → marquer comme interrupted
            job["status"] = "interrupted"
            job["completed_at"] = datetime.now().isoformat()
            job["updated_at"] = datetime.now().isoformat()
            job["error"] = "Interrompu par un arrêt du serveur"
            self._archive(job)
            self._active_path.unlink(missing_ok=True)
            logger.warning("Job orphelin détecté et marqué interrupted: %s", job["id"])
            return job

    # --- Maintenance ---

    def purge_history(self, keep_last: int = 100) -> int:
        """Supprime les entrées les plus anciennes au-delà du seuil."""
        with self._lock:
            if not self._history_path.exists():
                return 0
            lines = self._history_path.read_text(encoding="utf-8").strip().splitlines()
            if len(lines) <= keep_last:
                return 0
            removed = len(lines) - keep_last
            kept = lines[-keep_last:]
            self._history_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
            return removed

    def clear_history(self, job_type: str | None = None) -> int:
        """Supprime l'historique, optionnellement filtré par type de job."""
        with self._lock:
            removed = 0

            active = self._read_active()
            if (
                active
                and active["status"] in TERMINAL_STATUSES
                and (job_type is None or active.get("type") == job_type)
            ):
                self._active_path.unlink(missing_ok=True)
                removed += 1

            if not self._history_path.exists():
                return removed

            lines = self._history_path.read_text(encoding="utf-8").strip().splitlines()
            if not lines:
                self._history_path.unlink(missing_ok=True)
                return removed

            if job_type is None:
                self._history_path.unlink(missing_ok=True)
                return removed + len(lines)

            kept: list[str] = []
            for line in lines:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    kept.append(line)
                    continue

                if entry.get("type") == job_type:
                    removed += 1
                    continue
                kept.append(line)

            if kept:
                self._history_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
            else:
                self._history_path.unlink(missing_ok=True)

            return removed

    # --- Internals ---

    def _read_active(self) -> dict | None:
        """Lecture sans lock (le lock est pris par l'appelant)."""
        if not self._active_path.exists():
            return None
        try:
            data = json.loads(self._active_path.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, OSError):
            # Fichier corrompu → backup et retourner None
            backup = self._active_path.with_suffix(".corrupt")
            try:
                self._active_path.rename(backup)
                logger.warning("active_job.json corrompu, sauvegardé dans %s", backup)
            except OSError:
                pass
            return None

    def _write_active(self, job: dict) -> None:
        """Écriture atomique (write tmp + os.replace). Sans lock."""
        tmp = self._active_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(job, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        os.replace(str(tmp), str(self._active_path))

    def _archive(self, job: dict) -> None:
        """Append dans l'historique JSONL. Sans lock."""
        archived = {k: v for k, v in job.items() if k != "pid"}
        with self._history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(archived, ensure_ascii=False) + "\n")

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
