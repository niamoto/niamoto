---
title: "feat: Déclenchement transform dans l'UI + jobs persistants légers"
type: feat
date: 2026-02-23
revised: true
revision_note: "Allégé après revue Codex — scope réduit, fichier JSON au lieu de SQLite, polling conservé"
---

# Déclenchement transform dans l'UI + jobs persistants légers

## Overview

Le workflow Niamoto suit le pipeline **Import → Transform → Export → Deploy**. Actuellement, l'import a ses boutons d'exécution, l'export a son bouton "Générer le site" dans Publish/Build. **Mais le transform n'a aucun déclencheur dans l'UI** : l'utilisateur peut configurer les widgets dans `/groups/:name` mais ne peut pas lancer le calcul.

Les processus transform et export peuvent durer **30 à 60+ minutes**. Le système actuel (jobs en mémoire + polling HTTP 1s) perd tout état au redémarrage serveur.

### Scope v1 (ce plan — ~1.5 jour)

1. **Ajouter le bouton "Lancer le calcul"** dans GroupPanel
2. **Ajouter le job composite transform→export** dans Publish/Build
3. **Persistance légère** via fichier JSON (survit aux redémarrages)
4. **Fix `os.chdir()`** thread-unsafe dans le router export

### Scope v2 (futur — quand nécessaire)

- Migration vers SQLite + SSE (quand on a besoin d'historique riche, queue, multi-process)
- Annulation fiable
- Reconnexion SSE cross-session
- Simplification UX globale (plan dédié avec brainstorm)

> **Principe directeur** : App desktop mono-utilisateur, un job à la fois. Pas besoin d'un orchestrateur distribué.

---

## Problem Statement

### Ce qui manque

1. **Pas de bouton "Lancer le transform"** — L'endpoint `POST /api/transform/execute` existe, le code frontend `executeTransformAndWait()` existe, mais aucune page UI ne l'appelle
2. **Pas de paramètre `group_by`** dans `TransformRequest` — Impossible de filtrer par groupe
3. **Le bouton "Générer le site" dans Publish ne lance que l'export** — Il devrait lancer transform → export en séquence
4. **Jobs en mémoire (`dict`)** — Perdus au redémarrage, pas d'historique
5. **`os.chdir()` thread-unsafe** dans le router export

### Ce qui fonctionne déjà (et qu'on garde)

- Pipeline CLI complet (import/transform/export)
- Configuration des widgets dans GroupPanel (3 onglets)
- Frontend API `executeTransformAndWait()` + `executeExportAndWait()` avec polling 1s
- Polling HTTP 1s → **suffisant sur loopback pour une app locale**
- 147+ tests GUI API verts

---

## Proposed Solution

### Décisions architecturales

| Décision | Choix v1 | Justification |
|----------|----------|---------------|
| **Stockage jobs** | Fichier JSON (`active_job.json` + `job_history.jsonl`) | Mono-utilisateur, un job à la fois. Un fichier JSON suffit. |
| **Progression** | Polling HTTP conservé (existant) | Sur loopback, 1 req/s est négligeable. Ça marche déjà. |
| **Concurrence** | Rejet avec erreur + verrou fichier | Un seul job à la fois (contrainte DuckDB single-writer) |
| **Récupération crash** | Détection PID mort au démarrage | Si `active_job.json` existe avec un PID non vivant → `interrupted` |
| **Annulation** | Best-effort (caché pour v1) | L'annulation coopérative entre widgets est trop lente pour être fiable. On ne montre pas de bouton "Annuler" pour l'instant. |
| **Job composite** | Séquence transform→export côté backend | Un seul endpoint qui enchaîne les deux |

---

## Technical Approach

### Architecture simplifiée

```
┌───────────────────────────────────────────────────────┐
│  Frontend (React)                                      │
│                                                        │
│  GroupPanel ── "Lancer le calcul" ─┐                   │
│                                    │ POST /api/transform/execute
│  Build Page ── "Générer le site" ──┤ POST /api/export/execute
│                                    │   (ou composite)  │
│  ← Polling 1s: GET /api/transform/status/{id} ──────  │
│  ← Polling 1s: GET /api/export/status/{id}   ──────   │
│                                                        │
└───────────────────────────────────────────────────────┘
         │                    ▲
         ▼                    │ JSON responses
┌───────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                      │
│                                                        │
│  Routers existants (transform.py, export.py)           │
│  + JobFileStore → lit/écrit active_job.json            │
│  + BackgroundTasks (existant, inchangé)                │
│                                                        │
└───────────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────┐  ┌──────────────────┐
│  .niamoto/         │  │  db/niamoto.duckdb│
│  active_job.json   │  │  (données métier) │
│  job_history.jsonl │  │                  │
└───────────────────┘  └──────────────────┘
```

---

### Phase 1 : JobFileStore — persistance fichier JSON (~0.5 jour)

**Objectif** : Remplacer les dicts en mémoire par un store fichier, sans changer l'API.

#### 1.1 JobFileStore

**Fichier** : `src/niamoto/gui/api/services/job_file_store.py`

```python
import json
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime


class JobFileStore:
    """Persistance légère des jobs via fichiers JSON.

    - active_job.json : état du job en cours (un seul à la fois)
    - job_history.jsonl : historique append-only (1 ligne JSON par job terminé)

    Design notes (revue Codex) :
    - threading.Lock protège toutes les lectures/écritures (multi-onglets)
    - Les jobs terminés restent dans active_job.json (status terminal)
      jusqu'au prochain create_job() → évite le 404 sur le dernier poll
    - updated_at tracké pour détecter les jobs bloqués
    """

    TERMINAL_STATUSES = ("completed", "failed", "cancelled", "interrupted")

    def __init__(self, work_dir: Path):
        self._dir = work_dir / ".niamoto"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._active_path = self._dir / "active_job.json"
        self._history_path = self._dir / "job_history.jsonl"
        self._lock = threading.Lock()

    # --- Cycle de vie ---

    def create_job(self, job_type: str, group_by: str | None = None) -> dict:
        """Crée un job. Échoue si un job non-terminal est déjà actif."""
        with self._lock:
            existing = self._read_active()
            if existing and existing["status"] not in self.TERMINAL_STATUSES:
                raise RuntimeError("Un job est déjà en cours")

            # Si un job terminal traîne, l'archiver d'abord
            if existing and existing["status"] in self.TERMINAL_STATUSES:
                self._archive(existing)

            job = {
                "id": str(uuid4()),
                "type": job_type,
                "group_by": group_by,
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

    def update_progress(self, job_id: str, progress: int,
                        message: str, phase: str | None = None) -> None:
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
        """Marque le job comme terminé. Le fichier reste en place
        pour que le dernier poll puisse lire le statut 'completed'.
        Il sera archivé au prochain create_job()."""
        with self._lock:
            job = self._read_active()
            if not job or job["id"] != job_id:
                return
            job["status"] = "completed"
            job["progress"] = 100
            job["completed_at"] = datetime.now().isoformat()
            job["updated_at"] = datetime.now().isoformat()
            job["result"] = result
            self._write_active(job)  # reste en place, pas de suppression

    def fail_job(self, job_id: str, error: str) -> None:
        """Marque le job comme échoué. Même logique : reste en place."""
        with self._lock:
            job = self._read_active()
            if not job or job["id"] != job_id:
                return
            job["status"] = "failed"
            job["completed_at"] = datetime.now().isoformat()
            job["updated_at"] = datetime.now().isoformat()
            job["error"] = error
            self._write_active(job)

    # --- Lecture ---

    def get_active_job(self) -> dict | None:
        """Retourne le job courant (actif ou terminal en attente d'archivage)."""
        with self._lock:
            return self._read_active()

    def get_running_job(self) -> dict | None:
        """Retourne le job seulement s'il est en cours (pas terminal)."""
        with self._lock:
            job = self._read_active()
            if job and job["status"] not in self.TERMINAL_STATUSES:
                return job
            return None

    def get_history(self, limit: int = 20) -> list[dict]:
        """Retourne les N derniers jobs terminés (plus récent en premier)."""
        with self._lock:
            if not self._history_path.exists():
                return []
            lines = self._history_path.read_text().strip().splitlines()
            entries = [json.loads(line) for line in lines[-limit:]]
            entries.reverse()
            return entries

    def get_last_run(self, job_type: str,
                     group_by: str | None = None) -> dict | None:
        """Retourne le dernier job terminé pour un type/groupe donné.
        Vérifie aussi le job actif s'il est terminal."""
        with self._lock:
            # D'abord vérifier le job actif (peut être completed mais pas encore archivé)
            active = self._read_active()
            if active and active["status"] in self.TERMINAL_STATUSES:
                if active["type"] == job_type:
                    if group_by is None or active.get("group_by") == group_by:
                        return active

            # Sinon chercher dans l'historique
            if not self._history_path.exists():
                return None
            lines = self._history_path.read_text().strip().splitlines()
            for line in reversed(lines):
                entry = json.loads(line)
                if entry["type"] == job_type:
                    if group_by is None or entry.get("group_by") == group_by:
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
            if job["status"] in self.TERMINAL_STATUSES:
                self._archive(job)
                self._active_path.unlink(missing_ok=True)
                return None

            # Job non-terminal → vérifier si le process est vivant
            pid = job.get("pid")
            if pid and pid == os.getpid():
                return None  # Même process (ne devrait pas arriver)
            if pid and self._is_pid_alive(pid):
                return None  # Process encore vivant

            # PID mort ou absent → marquer comme interrupted
            job["status"] = "interrupted"
            job["completed_at"] = datetime.now().isoformat()
            job["updated_at"] = datetime.now().isoformat()
            job["error"] = "Interrompu par un arrêt du serveur"
            self._archive(job)
            self._active_path.unlink(missing_ok=True)
            return job

    # --- Maintenance ---

    def purge_history(self, keep_last: int = 100) -> int:
        """Supprime les entrées les plus anciennes au-delà du seuil.
        Retourne le nombre d'entrées supprimées."""
        with self._lock:
            if not self._history_path.exists():
                return 0
            lines = self._history_path.read_text().strip().splitlines()
            if len(lines) <= keep_last:
                return 0
            removed = len(lines) - keep_last
            kept = lines[-keep_last:]
            self._history_path.write_text("\n".join(kept) + "\n")
            return removed

    # --- Internals ---

    def _read_active(self) -> dict | None:
        """Lecture sans lock (le lock est pris par l'appelant)."""
        if not self._active_path.exists():
            return None
        try:
            data = json.loads(self._active_path.read_text())
            return data
        except (json.JSONDecodeError, OSError):
            # Fichier corrompu → backup et retourner None
            backup = self._active_path.with_suffix(".corrupt")
            try:
                self._active_path.rename(backup)
            except OSError:
                pass
            return None

    def _write_active(self, job: dict) -> None:
        """Écriture atomique (write tmp + rename). Sans lock."""
        tmp = self._active_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2))
        tmp.rename(self._active_path)

    def _archive(self, job: dict) -> None:
        """Append dans l'historique JSONL. Sans lock."""
        archived = {k: v for k, v in job.items() if k != "pid"}
        with self._history_path.open("a") as f:
            f.write(json.dumps(archived, ensure_ascii=False) + "\n")

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
```

#### 1.2 Intégration dans les routers existants

Remplacer les dicts en mémoire par `JobFileStore` **sans changer les endpoints** (même API, même polling frontend).

**Fichier** : `src/niamoto/gui/api/routers/transform.py`

Changements :
- Remplacer `transform_jobs: Dict[str, Dict] = {}` par `job_store.create_job("transform", group_by=...)`
- `update_progress()` → `job_store.update_progress()`
- `complete/fail` → `job_store.complete_job()` / `job_store.fail_job()`
- Endpoint `GET /status/{job_id}` → `job_store.get_active_job()` (vérifier `id` match)

**Fichier** : `src/niamoto/gui/api/routers/export.py`

Mêmes changements. Remplacer `export_jobs` dict.

**Fichier** : `src/niamoto/gui/api/app.py`

Au démarrage :
1. Créer l'instance `JobFileStore(work_dir)`
2. Appeler `job_store.recover_on_startup()` pour détecter les jobs orphelins
3. Rendre le store accessible aux routers (via `app.state` ou dependency injection)

**Tests** :
- `tests/gui/api/services/test_job_file_store.py` — CRUD, récupération crash, historique, verrou
- Pas de régression sur les tests de routers existants

---

### Phase 2 : Bouton "Lancer le calcul" dans GroupPanel (~0.5 jour)

**Objectif** : Le déclenchement du transform depuis la page de configuration des groupes.

#### 2.1 Ajouter `group_by` à `TransformRequest`

**Fichier** : `src/niamoto/gui/api/routers/transform.py`

```python
class TransformRequest(BaseModel):
    config_path: str | None = None
    transformations: list[str] | None = None
    group_by: str | None = None  # ← AJOUT
```

Propager vers `TransformerService.transform_data(group_by=request.group_by)`.

#### 2.2 Vérifier qu'un job n'est pas déjà en cours

Dans le handler `POST /api/transform/execute` :

```python
active = job_store.get_active_job()
if active:
    raise HTTPException(
        status_code=409,
        detail=f"Un calcul est déjà en cours ({active['type']} — {active['progress']}%)"
    )
```

#### 2.3 Bouton dans le header de GroupPanel

**Fichier** : `src/niamoto/gui/ui/src/components/panels/GroupPanel.tsx`

Ajouter dans le header (à côté du nom du groupe) :

```
┌──────────────────────────────────────────────────────────┐
│  Taxons                          [▶ Lancer le calcul]    │
│  Dernier calcul : il y a 2h ✓                            │
│                                                          │
│  ┌─────────┬──────────┬────────┐                         │
│  │ Sources │ Contenu  │ Index  │                         │
│  └─────────┴──────────┴────────┘                         │
└──────────────────────────────────────────────────────────┘
```

Pendant l'exécution :

```
┌──────────────────────────────────────────────────────────┐
│  Taxons                                                  │
│  Calcul en cours... 45%          ████████░░░░░░░░░░░░    │
│  Widget forest_cover (3/12)                              │
│  ┌─────────┬──────────┬────────┐                         │
│  │ Sources │ Contenu  │ Index  │                         │
│  └─────────┴──────────┴────────┘                         │
└──────────────────────────────────────────────────────────┘
```

**Comportement** :
- Clic sur "Lancer le calcul" → `POST /api/transform/execute { group_by: "taxons" }`
- Reçoit `job_id` → lance le polling `GET /api/transform/status/{job_id}` toutes les secondes (utilise `executeTransformAndWait()` existant)
- Barre de progression shadcn/ui `<Progress>` dans le header
- Bouton grisé si un job est déjà actif (vérifier via `GET /api/transform/status` ou `GET /api/jobs/active`)
- Au succès : toast + mise à jour de l'indicateur "Dernier calcul"
- En cas d'erreur : toast d'erreur avec le message

#### 2.4 Endpoint "dernier run" et "job actif"

**Fichier** : `src/niamoto/gui/api/routers/transform.py` (ou nouveau router léger)

```python
@router.get("/active")
async def get_active_job():
    """Retourne le job actif ou null."""
    return job_store.get_active_job()

@router.get("/last-run/{group_by}")
async def get_last_run(group_by: str):
    """Retourne le dernier transform terminé pour ce groupe."""
    return job_store.get_last_run("transform", group_by=group_by)
```

**Frontend** : Hook simple `useTransformStatus(groupName)` qui poll `/api/transform/active` au chargement de la page GroupPanel et affiche le dernier run.

**Fichiers frontend impactés** :
- `src/niamoto/gui/ui/src/components/panels/GroupPanel.tsx` — bouton + barre progression
- `src/niamoto/gui/ui/src/lib/api/transform.ts` — ajouter `getActiveJob()`, `getLastRun(group)`

---

### Phase 3 : Job composite transform→export dans Publish/Build (~0.5 jour)

**Objectif** : Le bouton "Générer le site" lance transform → export en séquence.

#### 3.1 Endpoint composite

**Fichier** : `src/niamoto/gui/api/routers/export.py`

Ajouter un endpoint ou modifier l'existant pour accepter un flag `include_transform` :

```python
class ExportRequest(BaseModel):
    # ... champs existants ...
    include_transform: bool = False  # ← AJOUT

# Dans execute_export_background :
if request.include_transform:
    job_store.update_progress(job_id, 0, "Transformations en cours...", phase="transform")
    # Lancer transform_data() d'abord
    transformer_service = TransformerService(str(db_path), app_config)
    transformer_service.transform_data(progress_callback=make_callback(0, 60))

    # Si transform échoue → job_store.fail_job() → pas d'export
    job_store.update_progress(job_id, 60, "Génération du site...", phase="export")
    # Puis lancer l'export (NB: la vraie méthode est run_export(), pas export_data())
    exporter_service.run_export(progress_callback=make_callback(60, 40))
else:
    # Export seul (comportement actuel)
    exporter_service.run_export(progress_callback=make_callback(0, 100))
```

**Important** : si le transform échoue (exception), le `except` block doit appeler `job_store.fail_job()` et ne **pas** lancer l'export. Le résultat final doit indiquer clairement quelle phase a échoué via le champ `phase`.

#### 3.2 Modifier la page Build

**Fichier** : `src/niamoto/gui/ui/src/pages/publish/build.tsx`

Le bouton "Générer le site" envoie `include_transform: true` par défaut :

```
┌──────────────────────────────────────────────────────────┐
│  Génération du site                                      │
│                                                          │
│  [✓] Recalculer les transformations avant export         │
│                                                          │
│  [▶ Générer le site]                                     │
│                                                          │
│  Phase 1/2 : Transformations  ████████████░░░░  60%      │
│  Widget forest_cover (5/12)                              │
│                                                          │
│  Phase 2/2 : Export           ░░░░░░░░░░░░░░░░  —        │
└──────────────────────────────────────────────────────────┘
```

- Checkbox "Recalculer les transformations" cochée par défaut
- Le polling affiche la phase courante via le champ `phase` du job
- Le même `executeExportAndWait()` existant fonctionne (il poll `/api/export/status/{id}`)

**Fichiers impactés** :
- `src/niamoto/gui/ui/src/pages/publish/build.tsx` — checkbox + affichage phases
- `src/niamoto/gui/api/routers/export.py` — logique composite

---

### Phase 0 (immédiat) : Fix `os.chdir()` thread-unsafe

**Fichier** : `src/niamoto/gui/api/routers/export.py`

Remplacer `os.chdir(work_dir)` par des chemins absolus passés aux services. Si pas possible rapidement, ajouter au minimum un `threading.Lock()` global autour du bloc chdir/restore.

```python
# AVANT (dangereux)
os.chdir(work_dir)
try:
    exporter_service.export_data(...)
finally:
    os.chdir(original_cwd)

# APRÈS (sûr) — option A : chemins absolus
exporter_service.export_data(
    output_dir=str(work_dir / "exports" / "web"),
    template_dir=str(work_dir / "templates"),
    ...
)

# APRÈS (acceptable v1) — option B : lock global
_export_lock = threading.Lock()
with _export_lock:
    os.chdir(work_dir)
    try:
        exporter_service.export_data(...)
    finally:
        os.chdir(original_cwd)
```

---

## Alternative Approaches Considered

### 1. SQLite complet (JobService + table `jobs` + SSE + annulation fiable)

**Reporté en v2** : Over-engineered pour une app desktop mono-utilisateur. Le fichier JSON fait le même travail en 10x moins de code. Codex l'a confirmé : "Vous êtes en train de concevoir un mini orchestrateur distribué pour une app locale."

### 2. SSE au lieu du polling

**Reporté en v2** : Sur loopback, 1 req/s est négligeable. Le polling marche déjà côté frontend (`executeTransformAndWait`). Migrer vers SSE ajoute de la complexité sans gain mesurable pour v1.

### 3. Annulation fiable

**Reporté en v2** : L'annulation via `threading.Event` entre widgets est coopérative et lente (un widget peut durer 10 min). Plutôt que montrer un bouton "Annuler" qui ne répond pas pendant 10 min, on le cache pour v1.

### 4. Queue FIFO avec ordonnancement

**Reporté en v2** : Avec un seul job à la fois et une app mono-utilisateur, le rejet avec message d'erreur clair est suffisant.

---

## Acceptance Criteria

### Functional Requirements

- [ ] Un bouton "Lancer le calcul" est visible dans chaque page `/groups/:name`
- [ ] Cliquer sur le bouton lance le transform **pour ce groupe uniquement** (`group_by`)
- [ ] La progression s'affiche via la barre de progression (polling existant)
- [ ] Le bouton "Générer le site" dans Publish lance transform → export en séquence
- [ ] Une checkbox permet de skip le transform si déjà à jour
- [ ] Un seul job à la fois : le bouton est grisé si un job tourne (erreur 409)
- [ ] Le dernier statut transform est visible dans GroupPanel (date + succès/échec)
- [ ] Redémarrer le serveur détecte un job orphelin et le marque "interrompu"
- [ ] L'historique des derniers jobs est consultable (`job_history.jsonl`)

### Non-Functional Requirements

- [ ] Polling conservé à 1s (aucune régression de latence perçue)
- [ ] Fichiers JSON < 100 KB (auto-purge historique si > 100 entrées)
- [ ] Écriture atomique (`write tmp + rename`) pour éviter la corruption

### Quality Gates

- [ ] Tests unitaires `JobFileStore` : create, update, complete, fail, recover, history, purge
- [ ] Test thread-safety : appels concurrents à `create_job` → un seul réussit
- [ ] Test status post-completion : le polling lit `completed` (pas 404) après `complete_job()`
- [ ] Test JSON corrompu : fichier actif illisible → backup `.corrupt` + `None` retourné
- [ ] Test `updated_at` : vérifié présent et mis à jour à chaque `update_progress()`
- [ ] Tests d'intégration : `POST /api/transform/execute` avec `group_by`
- [ ] Test de verrou : `POST` quand un job est actif → 409
- [ ] Test de récupération : simuler un PID mort → job marqué `interrupted`
- [ ] Pas de régression sur les 147+ tests GUI API existants
- [ ] `os.chdir()` sécurisé (chemins absolus ou lock)

---

## Dependencies & Prerequisites

| Dépendance | Statut | Impact |
|---|---|---|
| Endpoint `POST /api/transform/execute` | ✅ Existe | Ajouter `group_by` |
| Frontend `executeTransformAndWait()` | ✅ Existe | Réutiliser tel quel |
| Frontend `executeExportAndWait()` | ✅ Existe | Ajouter `include_transform` |
| GroupPanel composant | ✅ Existe | Ajouter bouton + progression |
| `TransformerService.transform_data(group_by)` | ✅ Accepte `group_by` | Juste exposer dans l'API |

---

## Risk Analysis & Mitigation

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Corruption `active_job.json` (crash mid-write) | Faible | Moyen | Écriture atomique (tmp + rename) + backup `.corrupt` si JSON illisible |
| `os.chdir()` race condition | Élevée | Élevé | Fix immédiat (Phase 0) : chemins absolus ou lock |
| Double-clic "Lancer" → jobs dupliqués | Moyenne | Faible | `threading.Lock` + vérification `get_running_job()` + 409 |
| Polling reçoit 404 après completion | Moyenne | Moyen | Jobs terminés restent dans `active_job.json` jusqu'au prochain `create_job()` |
| PID réutilisé par l'OS après restart | Faible | Faible | Rare en pratique ; acceptable pour v1. Check `pid == os.getpid()` en garde |
| Polling 1s sur un job de 60 min = 3600 requêtes | Faible | Faible | Sur loopback, négligeable. Backoff possible en v2 |
| Job bloqué sans progression | Faible | Moyen | `updated_at` tracké → détection possible (timeout stale en v2) |

---

## Estimation d'effort

| Phase | Effort | Priorité |
|---|---|---|
| Phase 0 : Fix `os.chdir()` | ~1h | P0 — bug existant |
| Phase 1 : JobFileStore + intégration routers | ~0.5 jour | P0 — fondation |
| Phase 2 : Bouton transform GroupPanel | ~0.5 jour | P0 — feature principale |
| Phase 3 : Composite transform→export dans Build | ~0.5 jour | P1 — complète le workflow |
| **Total** | **~1.5 jour** | |

---

## Chemin vers v2 (quand le besoin apparaît)

Le `JobFileStore` est conçu pour être remplaçable. L'interface (`create_job`, `update_progress`, `complete_job`, `fail_job`, `get_active_job`, `get_history`) est la même qu'un futur `JobSQLiteStore`. La migration sera :

1. Créer `JobSQLiteStore` avec la même interface
2. Remplacer l'instanciation dans `app.py`
3. Ajouter les SSE endpoints (le store est déjà découplé)
4. Ajouter l'annulation (le store supporte déjà `cancel_job`)

**Signaux pour passer en v2** (au moins 2 parmi) :
- Besoin d'historique avec recherche/pagination
- Besoin de reprise cross-session
- Besoin de queue/ordonnancement
- Extension multi-processus/instances
- Observabilité détaillée par phase

---

## Future Considerations (hors scope)

- **Simplification UX** : Plan dédié avec brainstorm pour réduire les écrans/onglets et clarifier le workflow
- **SSE temps réel** : Remplacer le polling par des Server-Sent Events
- **Annulation fiable** : Bouton "Annuler" avec feedback < 5s
- **Notifications desktop** : Notification Tauri quand un job long se termine
- **Indicateur de fraîcheur pipeline** : Import ✓ → Transform ⚠ → Export ○ → Deploy

---

## References

### Internal

- Transform router : `src/niamoto/gui/api/routers/transform.py`
- Export router : `src/niamoto/gui/api/routers/export.py`
- GroupPanel : `src/niamoto/gui/ui/src/components/panels/GroupPanel.tsx`
- Build page : `src/niamoto/gui/ui/src/pages/publish/build.tsx`
- Frontend transform API : `src/niamoto/gui/ui/src/lib/api/transform.ts`
- Frontend export API : `src/niamoto/gui/ui/src/lib/api/export.ts`
- Plan release v1 : `docs/plans/2026-02-19-feat-release-v1-desktop-app-publication-plan.md`
- Contrat config v1 : `docs/plans/2026-02-19-contrat-configuration-v1.md`

### Revue Codex

- Revue initiale : architecture validée (SQLite séparé ✅, SSE ✅) mais over-engineered pour v1
- Suggestion retenue : "job runner minimal persistant sans SQLite" (fichier JSON)
- Suggestion retenue : "ajouter bouton + améliorer polling, reporter le reste"
- NFR "<5s annulation" déclaré irréaliste → reporté en v2
