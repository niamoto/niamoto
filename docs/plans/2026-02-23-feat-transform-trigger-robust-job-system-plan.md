---
title: "feat: Déclenchement transform dans l'UI + système de jobs robuste"
type: feat
date: 2026-02-23
---

# Déclenchement transform dans l'UI + système de jobs robuste

## Overview

Le workflow Niamoto suit le pipeline **Import → Transform → Export → Deploy**. Actuellement, l'import a ses boutons d'exécution, l'export a son bouton "Générer le site" dans Publish/Build, et le deploy Cloudflare fonctionne en SSE. **Mais le transform n'a aucun déclencheur dans l'UI** : l'utilisateur peut configurer les widgets dans `/groups/:name` mais ne peut pas lancer le calcul.

De plus, les processus transform et export peuvent durer **30 à 60+ minutes**. Le système actuel (jobs en mémoire + polling HTTP 1s) est fragile : un redémarrage serveur perd tout l'état, aucune annulation possible, pas de reconnexion après fermeture d'onglet.

Ce plan adresse deux problèmes :
1. **Ajouter le déclenchement transform** dans Groupes + option combinée dans Publish
2. **Implémenter un système de jobs robuste** : SSE, persistance SQLite, annulation, historique

> **Hors scope** : La simplification globale de l'interface (trop d'écrans/onglets, workflow pas clair) fera l'objet d'un plan dédié avec brainstorm UX. Ce plan se concentre sur les fondations techniques.

## Problem Statement

### Ce qui manque

1. **Pas de bouton "Lancer le transform"** — L'endpoint `POST /api/transform/execute` existe, le code frontend `executeTransformAndWait()` existe, mais aucune page UI ne l'appelle
2. **Pas de paramètre `group_by`** dans `TransformRequest` — Le bouton Groupes ne pourrait pas filtrer par groupe même s'il existait
3. **Le bouton "Générer le site" dans Publish ne lance que l'export** — Il devrait lancer transform → export en séquence
4. **Jobs en mémoire (`dict`)** — Perdus au redémarrage, pas d'historique, pas d'annulation réelle
5. **Polling HTTP 1s** — Gaspille des requêtes, pas de push temps réel (sauf deploy SSE)
6. **`os.chdir()` thread-unsafe** dans le router export — Dangereux en cas de jobs concurrents
7. **Pas d'invalidation croisée** — L'utilisateur ne sait pas si les données export sont périmées après un nouveau transform

### Ce qui fonctionne déjà

- Pipeline CLI complet (import/transform/export)
- Configuration des widgets dans GroupPanel (3 onglets : Sources, Contenu, Index)
- SSE pour le deploy Cloudflare (pattern réutilisable)
- Frontend API `executeTransformAndWait()` et `executeExportAndWait()` (à migrer vers SSE)
- 147+ tests GUI API verts

---

## Proposed Solution

### Décisions architecturales

| Décision | Choix | Justification |
|----------|-------|---------------|
| **Stockage jobs** | SQLite séparé (`niamoto_jobs.sqlite`) | DuckDB a un verrou single-writer ; le job store doit écrire pendant que le transform écrit dans DuckDB |
| **Concurrence transforms** | Rejet avec erreur explicite | DuckDB single-writer interdit les écritures parallèles ; un seul transform à la fois |
| **Progression** | SSE (Server-Sent Events) | Pattern déjà implémenté pour le deploy ; push temps réel sans WebSocket |
| **Job composite** | Un seul job avec 2 phases | Plus simple pour l'utilisateur : une barre de progression, un statut |
| **Récupération après crash** | Marquer comme `interrupted` | Pas de restart automatique (risque de données partielles) ; l'utilisateur relance manuellement |
| **Annulation** | `threading.Event` vérifié entre widgets | Point d'interruption naturel : entre chaque widget du transform |
| **Config pendant exécution** | Warning non-bloquant | L'utilisateur peut éditer mais voit un bandeau "les changements ne s'appliqueront qu'au prochain lancement" |

---

## Technical Approach

### Architecture du système de jobs

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React)                                            │
│                                                              │
│  GroupPanel ─── "Run transform" ──┐                          │
│                                   │  POST /api/jobs/start    │
│  Build Page ── "Générer le site" ─┤  { type, group_by }     │
│                                   │                          │
│  Import Page ── "Importer" ───────┘                          │
│                                                              │
│  ← SSE: GET /api/jobs/{id}/stream ──────────────────────     │
│                                                              │
│  JobStore (zustand) ── état local + reconnexion              │
└─────────────────────────────────────────────────────────────┘
           │                    ▲
           ▼                    │ SSE events
┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                           │
│                                                              │
│  /api/jobs/start ── crée job SQLite ── lance BackgroundTask  │
│  /api/jobs/{id}/stream ── SSE endpoint (poll SQLite)         │
│  /api/jobs/{id}/cancel ── set cancel flag                    │
│  /api/jobs/active ── jobs en cours                           │
│  /api/jobs/history ── historique paginé                      │
│                                                              │
│  JobService ── lit/écrit niamoto_jobs.sqlite                 │
│  BackgroundTask ── exécute transform/export dans thread      │
│               ── met à jour SQLite via callback              │
│               ── vérifie cancel_event entre widgets          │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐  ┌──────────────────────┐
│  niamoto_jobs.sqlite │  │  niamoto.duckdb      │
│  (état des jobs)     │  │  (données métier)    │
└──────────────────────┘  └──────────────────────┘
```

---

### Implementation Phases

#### Phase 1 : Système de jobs persistant (backend)

**Objectif** : Remplacer les dicts en mémoire par un service de jobs SQLite.

##### 1.1 Schéma `niamoto_jobs.sqlite`

**Fichier** : `src/niamoto/gui/api/services/job_service.py`

```sql
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,           -- UUID
    type TEXT NOT NULL,            -- 'transform' | 'export' | 'import' | 'composite'
    status TEXT NOT NULL DEFAULT 'queued',
                                   -- 'queued' | 'running' | 'completed' | 'failed'
                                   -- | 'cancelled' | 'interrupted'
    group_by TEXT,                 -- null pour export/import, nom du groupe pour transform
    progress INTEGER DEFAULT 0,   -- 0-100
    phase TEXT,                    -- 'transform' | 'export' (pour les jobs composites)
    message TEXT,                  -- message de progression lisible
    config_snapshot TEXT,          -- JSON snapshot de la config utilisée
    result_json TEXT,              -- JSON résultat (métriques, fichiers générés)
    error TEXT,                    -- message d'erreur si failed
    created_at TEXT NOT NULL,      -- ISO 8601
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
```

##### 1.2 JobService

**Fichier** : `src/niamoto/gui/api/services/job_service.py`

```python
class JobService:
    """Service de gestion des jobs avec persistance SQLite."""

    def __init__(self, db_path: Path):
        """Initialise avec le chemin vers niamoto_jobs.sqlite."""

    def create_job(self, job_type: str, group_by: str | None = None,
                   config_snapshot: dict | None = None) -> str:
        """Crée un job en statut 'queued', retourne l'id."""

    def update_progress(self, job_id: str, progress: int,
                        message: str, phase: str | None = None) -> None:
        """Met à jour la progression (appelé par le callback du worker)."""

    def complete_job(self, job_id: str, result: dict) -> None:
        """Marque un job comme terminé avec ses résultats."""

    def fail_job(self, job_id: str, error: str) -> None:
        """Marque un job comme échoué."""

    def cancel_job(self, job_id: str) -> bool:
        """Marque un job comme annulé. Retourne False si déjà terminé."""

    def get_job(self, job_id: str) -> dict | None:
        """Récupère l'état complet d'un job."""

    def get_active_jobs(self) -> list[dict]:
        """Retourne les jobs en cours (queued + running)."""

    def get_history(self, job_type: str | None = None,
                    limit: int = 50, offset: int = 0) -> list[dict]:
        """Retourne l'historique paginé."""

    def mark_interrupted_on_startup(self) -> int:
        """Au démarrage du serveur, marque tous les jobs 'running' comme 'interrupted'.
        Retourne le nombre de jobs affectés."""

    def cleanup_old_jobs(self, keep_last: int = 100) -> int:
        """Supprime les jobs les plus anciens au-delà du seuil."""
```

##### 1.3 Registre d'annulation

**Fichier** : `src/niamoto/gui/api/services/job_service.py` (dans la même classe ou module)

```python
# Registre en mémoire des events d'annulation (non persisté)
_cancel_events: dict[str, threading.Event] = {}

def register_cancel_event(job_id: str) -> threading.Event:
    """Crée et enregistre un Event pour ce job."""

def request_cancellation(job_id: str) -> bool:
    """Set l'event d'annulation. Retourne False si pas trouvé."""

def is_cancelled(job_id: str) -> bool:
    """Vérifie si l'annulation a été demandée."""

def unregister_cancel_event(job_id: str) -> None:
    """Nettoie après fin du job."""
```

##### 1.4 Migration des routers existants

Remplacer les `transform_jobs`, `export_jobs`, `import_jobs` (dicts en mémoire) par des appels à `JobService`. Conserver la compatibilité des endpoints existants le temps de la migration.

**Fichiers impactés** :
- `src/niamoto/gui/api/routers/transform.py` — remplacer `transform_jobs` dict
- `src/niamoto/gui/api/routers/export.py` — remplacer `export_jobs` dict
- `src/niamoto/gui/api/routers/imports.py` — remplacer `import_jobs` dict
- `src/niamoto/gui/api/app.py` — initialiser `JobService` au démarrage, appeler `mark_interrupted_on_startup()`

**Tests** :
- `tests/gui/api/services/test_job_service.py` — tests unitaires CRUD, concurrence, cleanup
- `tests/gui/api/routers/test_transform.py` — vérifier que les endpoints utilisent JobService
- `tests/gui/api/routers/test_export.py` — idem

---

#### Phase 2 : Endpoints SSE + API jobs unifiée (backend)

**Objectif** : Créer un router `/api/jobs` centralisé avec SSE.

##### 2.1 Router jobs

**Fichier** : `src/niamoto/gui/api/routers/jobs.py`

```python
# POST /api/jobs/start
# Body: { type: "transform"|"export"|"composite", group_by?: string }
# Response: { job_id: string, status: "queued" }

# GET /api/jobs/{job_id}/stream
# Response: SSE stream
# Events:
#   data: {"status":"running","progress":25,"message":"Calcul widget forest_cover...","phase":"transform"}
#   data: {"status":"completed","progress":100,"result":{...}}
#   data: {"status":"failed","error":"..."}
#   data: {"status":"cancelled"}

# POST /api/jobs/{job_id}/cancel
# Response: { cancelled: true } ou 409 si déjà terminé

# GET /api/jobs/active
# Response: [{ id, type, status, progress, message, group_by, started_at }]

# GET /api/jobs/history?type=transform&limit=50&offset=0
# Response: { items: [...], total: int }

# GET /api/jobs/{job_id}
# Response: { id, type, status, progress, message, result_json, error, ... }
```

##### 2.2 SSE endpoint (pattern)

```python
@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str):
    """Stream SSE pour suivre la progression d'un job."""

    async def event_generator():
        last_progress = -1
        while True:
            job = job_service.get_job(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                return

            # N'émettre que si changement
            if job["progress"] != last_progress or job["status"] in TERMINAL_STATES:
                yield f"id: {job['id']}-{job['progress']}\n"
                yield f"data: {json.dumps(job)}\n\n"
                last_progress = job["progress"]

            if job["status"] in ("completed", "failed", "cancelled", "interrupted"):
                return

            await asyncio.sleep(0.5)  # poll SQLite toutes les 500ms

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

##### 2.3 Job composite (transform → export)

```python
async def execute_composite_job(job_id: str, cancel_event: threading.Event):
    """Exécute transform puis export en séquence."""

    # Phase 1 : Transform
    job_service.update_progress(job_id, 0, "Démarrage des transformations...", phase="transform")
    try:
        await asyncio.to_thread(
            run_transform_with_progress,
            job_id, cancel_event, phase_offset=0, phase_weight=60
        )
    except CancelledException:
        job_service.cancel_job(job_id)
        return

    if cancel_event.is_set():
        job_service.cancel_job(job_id)
        return

    # Phase 2 : Export
    job_service.update_progress(job_id, 60, "Génération du site statique...", phase="export")
    try:
        await asyncio.to_thread(
            run_export_with_progress,
            job_id, cancel_event, phase_offset=60, phase_weight=40
        )
    except CancelledException:
        job_service.cancel_job(job_id)
        return

    job_service.complete_job(job_id, result={...})
```

##### 2.4 Annulation via `threading.Event`

Modifier le callback de progression pour vérifier le flag d'annulation :

```python
def make_progress_callback(job_id: str, cancel_event: threading.Event,
                            phase_offset: int, phase_weight: int):
    """Crée un callback compatible TransformerService.transform_data()."""

    def callback(current: int, total: int, message: str):
        if cancel_event.is_set():
            raise CancelledException(f"Job {job_id} annulé par l'utilisateur")

        progress = phase_offset + int((current / max(total, 1)) * phase_weight)
        job_service.update_progress(job_id, progress, message)

    return callback
```

**Tests** :
- `tests/gui/api/routers/test_jobs.py` — tests endpoints, SSE, annulation
- `tests/gui/api/services/test_job_composite.py` — test du pipeline composite

---

#### Phase 3 : Bouton "Run transform" dans GroupPanel (frontend)

**Objectif** : Ajouter le déclenchement transform dans chaque page de groupe.

##### 3.1 Ajouter `group_by` à `TransformRequest`

**Fichier** : `src/niamoto/gui/api/routers/transform.py`

```python
class TransformRequest(BaseModel):
    config_path: str | None = None
    transformations: list[str] | None = None
    group_by: str | None = None  # ← AJOUT : filtrer par groupe
```

Propager vers `TransformerService.transform_data(group_by=request.group_by)`.

##### 3.2 Bouton dans le header de GroupPanel

**Fichier** : `src/niamoto/gui/ui/src/components/panels/GroupPanel.tsx`

Ajouter dans le header (à côté du nom du groupe) :
- Bouton **"Lancer le calcul"** (icône Play)
- Indicateur d'état : dernier run (date + statut) ou "Jamais exécuté"
- Quand un job est en cours : barre de progression + bouton "Annuler"
- Quand le job est terminé : résumé (durée, widgets traités, erreurs éventuelles)

```
┌──────────────────────────────────────────────────────────┐
│  Taxons                          [▶ Lancer le calcul]    │
│  Dernier calcul : il y a 2h ✓   ────────────────────    │
│                                                          │
│  ┌─────────┬──────────┬────────┐                         │
│  │ Sources │ Contenu  │ Index  │                         │
│  └─────────┴──────────┴────────┘                         │
│  ...                                                     │
└──────────────────────────────────────────────────────────┘
```

Pendant l'exécution :

```
┌──────────────────────────────────────────────────────────┐
│  Taxons                          [⏹ Annuler]             │
│  Calcul en cours... 45%          ████████░░░░░░░░░░░░    │
│  Widget forest_cover (3/12)                              │
│  ┌─────────┬──────────┬────────┐                         │
│  │ Sources │ Contenu  │ Index  │  (édition désactivée)   │
│  └─────────┴──────────┴────────┘                         │
└──────────────────────────────────────────────────────────┘
```

##### 3.3 Hook `useJobStream`

**Fichier** : `src/niamoto/gui/ui/src/hooks/useJobStream.ts`

```typescript
interface UseJobStreamOptions {
  jobId: string | null;
  onProgress?: (data: JobEvent) => void;
  onComplete?: (data: JobEvent) => void;
  onError?: (data: JobEvent) => void;
}

function useJobStream({ jobId, onProgress, onComplete, onError }: UseJobStreamOptions) {
  // Ouvre EventSource vers /api/jobs/{jobId}/stream
  // Gère reconnexion automatique
  // Retourne { status, progress, message, phase, isConnected }
}
```

##### 3.4 Store jobs (zustand)

**Fichier** : `src/niamoto/gui/ui/src/stores/jobStore.ts`

```typescript
interface JobState {
  activeJobs: Record<string, JobInfo>;    // jobs en cours
  lastRuns: Record<string, JobInfo>;      // dernier run par type+group
  startJob: (type: string, groupBy?: string) => Promise<string>;
  cancelJob: (jobId: string) => Promise<void>;
  fetchActiveJobs: () => Promise<void>;   // appelé au chargement de l'app
}
```

Remplace `publishStore.buildState` et les équivalents transform/import.

**Fichiers impactés (frontend)** :
- `src/niamoto/gui/ui/src/components/panels/GroupPanel.tsx` — bouton + barre progression
- `src/niamoto/gui/ui/src/hooks/useJobStream.ts` — nouveau hook SSE
- `src/niamoto/gui/ui/src/stores/jobStore.ts` — nouveau store
- `src/niamoto/gui/ui/src/lib/api/jobs.ts` — nouveau client API
- `src/niamoto/gui/ui/src/lib/api/transform.ts` — adapter pour utiliser le nouveau système

---

#### Phase 4 : Job composite dans Publish/Build (frontend)

**Objectif** : Le bouton "Générer le site" lance transform → export en séquence.

##### 4.1 Modifier la page Build

**Fichier** : `src/niamoto/gui/ui/src/pages/publish/build.tsx`

Remplacer l'appel à `executeExportAndWait()` par :

```typescript
const runBuild = async () => {
  const jobId = await jobStore.startJob('composite');
  // Le hook useJobStream gère le suivi SSE
  // La barre de progression montre 2 phases :
  //   0-60% : Transform (phase="transform")
  //   60-100% : Export (phase="export")
};
```

Affichage de la progression en 2 phases :

```
┌──────────────────────────────────────────────────────────┐
│  Génération du site                                      │
│                                                          │
│  Phase 1/2 : Transformations                             │
│  ████████████████████░░░░░░░░░░  60%                     │
│  Widget fragmentation (11/12)                            │
│                                                          │
│  Phase 2/2 : Export               (en attente)           │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%                     │
│                                                          │
│  [⏹ Annuler]                                             │
└──────────────────────────────────────────────────────────┘
```

##### 4.2 Indicateur de fraîcheur des données

Ajouter dans le dashboard Publish (`/publish`) un indicateur visuel :

```
Import ──✓──→ Transform ──⚠──→ Export ──○──→ Deploy
  il y a 3h      il y a 1h      périmé       jamais
```

- ✓ = à jour (exécuté après l'étape précédente)
- ⚠ = exécuté mais l'étape précédente a été relancée depuis
- ○ = jamais exécuté ou périmé

Basé sur les timestamps `completed_at` des derniers jobs réussis de chaque type.

**Fichiers impactés** :
- `src/niamoto/gui/ui/src/pages/publish/build.tsx` — refactor build
- `src/niamoto/gui/ui/src/pages/publish/index.tsx` — indicateur pipeline
- `src/niamoto/gui/ui/src/stores/publishStore.ts` — migration vers jobStore

---

#### Phase 5 : Reconnexion et robustesse (frontend + backend)

**Objectif** : Gérer les déconnexions, redémarrages, et cas limites.

##### 5.1 Reconnexion SSE

Le hook `useJobStream` doit :
- Reconnecter automatiquement si `EventSource` est fermé (avec backoff exponentiel)
- Sur reconnexion, recevoir l'état courant du job (le SSE endpoint envoie l'état immédiatement)
- Si le job est déjà terminé quand le client se connecte, recevoir l'événement final directement

##### 5.2 Détection de jobs actifs au chargement

Au chargement de l'app (`App.tsx` ou `MainLayout.tsx`) :
1. Appeler `GET /api/jobs/active`
2. Si un job est en cours, ouvrir le stream SSE
3. Afficher un bandeau global : "Un calcul est en cours (Taxons — 45%)" avec lien vers la page concernée

##### 5.3 Indicateur dans la sidebar

**Fichier** : `src/niamoto/gui/ui/src/stores/navigationStore.ts`

Ajouter un badge animé (spinner ou pulsation) sur la section Groupes ou Publish quand un job est en cours.

##### 5.4 Verrou de concurrence côté UI

Quand un job transform/export est en cours :
- Désactiver les boutons "Lancer" sur les autres groupes
- Afficher un message : "Un calcul est déjà en cours. Attendez sa fin ou annulez-le."
- Le bouton "Générer le site" dans Publish est également grisé

##### 5.5 Startup serveur

**Fichier** : `src/niamoto/gui/api/app.py`

Au démarrage du serveur FastAPI :
1. Initialiser `JobService` avec le chemin SQLite
2. Appeler `mark_interrupted_on_startup()` pour marquer les jobs orphelins
3. Appeler `cleanup_old_jobs(keep_last=100)` pour purger l'historique

---

## Alternative Approaches Considered

### 1. WebSocket au lieu de SSE

**Rejeté** : SSE est plus simple (unidirectionnel, reconnexion native), suffisant pour du push de progression. WebSocket serait over-engineering pour ce cas. De plus, le pattern SSE est déjà implémenté pour le deploy Cloudflare.

### 2. Jobs dans DuckDB au lieu de SQLite séparé

**Rejeté** : DuckDB a un verrou single-writer. Pendant le transform, le worker écrit dans DuckDB (données métier). Si le job store est aussi dans DuckDB, les mises à jour de progression seraient bloquées par le verrou du transform. SQLite séparé évite ce conflit.

### 3. Queue de messages (Redis, Celery)

**Rejeté** : Trop lourd pour une app desktop/locale. Niamoto doit fonctionner offline sans dépendances externes. SQLite + threading.Event est la solution la plus légère.

### 4. Ne rien persister, améliorer le polling

**Rejeté** : L'utilisateur veut de la robustesse (choix explicite). Le polling ne résout pas la perte d'état au redémarrage ni l'historique. SSE + SQLite est un investissement modéré pour un gain significatif.

### 5. Transforms parallèles sur différents groupes

**Rejeté pour v1** : DuckDB single-writer rend ça impossible sans architecture complexe (file d'attente, connection pooling). On sérialise : un seul transform à la fois. Les transforms par groupe sont un mode "itération rapide", pas un mode "batch parallèle".

---

## Acceptance Criteria

### Functional Requirements

- [ ] Un bouton "Lancer le calcul" est visible dans chaque page `/groups/:name`
- [ ] Cliquer sur le bouton lance le transform pour ce groupe uniquement
- [ ] La progression s'affiche en temps réel via SSE (pas de polling)
- [ ] Le bouton "Générer le site" dans Publish lance transform → export en séquence
- [ ] La progression composite montre les 2 phases distinctement
- [ ] Un job en cours peut être annulé via un bouton "Annuler"
- [ ] L'annulation est gracieuse (termine le widget en cours, puis s'arrête)
- [ ] L'historique des jobs est consultable (type, statut, durée, date)
- [ ] Fermer l'onglet et le rouvrir reconnecte au job en cours
- [ ] Redémarrer le serveur marque les jobs orphelins comme "interrompus"
- [ ] Un seul transform/export peut tourner à la fois (les boutons sont grisés sinon)
- [ ] Le dernier statut transform est visible dans GroupPanel (date + résultat)

### Non-Functional Requirements

- [ ] Les mises à jour SSE arrivent en < 1s (latence perçue)
- [ ] Le fichier `niamoto_jobs.sqlite` ne dépasse pas 10 MB (auto-purge)
- [ ] L'annulation prend effet en < 5s (fin du widget en cours)
- [ ] La reconnexion SSE fonctionne en < 3s après perte de connexion

### Quality Gates

- [ ] Tests unitaires `JobService` : CRUD, concurrence, cleanup
- [ ] Tests d'intégration : endpoints jobs (start, stream, cancel, history)
- [ ] Test de reconnexion SSE (simuler déconnexion/reconnexion)
- [ ] Pas de régression sur les 147+ tests GUI API existants
- [ ] `os.chdir()` remplacé par chemins absolus dans le router export

---

## Dependencies & Prerequisites

| Dépendance | Statut | Impact |
|---|---|---|
| Endpoint `POST /api/transform/execute` | ✅ Existe | À migrer vers JobService |
| Frontend `executeTransformAndWait()` | ✅ Existe | À remplacer par SSE |
| SSE pattern (deploy Cloudflare) | ✅ Implémenté | À généraliser |
| GroupPanel composant | ✅ Existe | À enrichir avec bouton + progression |
| `TransformerService.transform_data(group_by)` | ✅ Accepte `group_by` | Juste exposer dans l'API |
| Plan shapes config workflow | ✅ Plan du jour | Indépendant, pas de conflit |

---

## Risk Analysis & Mitigation

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| DuckDB lock conflict entre transform et job updates | Faible (SQLite séparé) | Élevé | SQLite séparé élimine le risque |
| SSE bloqué par proxy/reverse-proxy | Moyenne | Moyen | Headers `X-Accel-Buffering: no`, `Cache-Control: no-cache` |
| `os.chdir()` race condition pendant migration | Élevée | Élevé | Corriger en priorité (Phase 2) : chemins absolus |
| threading.Event non détecté si widget très long | Faible | Faible | Certains plugins peuvent prendre plusieurs minutes par widget ; acceptable |
| Migration PublishStore → JobStore casse l'UI | Moyenne | Moyen | Migration progressive : les deux stores coexistent pendant la transition |
| Tauri webview SSE incompatible | Faible | Élevé | Tester tôt ; fallback polling si nécessaire (mais Tauri 2 supporte EventSource) |

---

## Estimation d'effort par phase

| Phase | Effort estimé | Priorité |
|---|---|---|
| Phase 1 : JobService SQLite | ~1 jour | P0 — fondation |
| Phase 2 : Router jobs + SSE | ~1 jour | P0 — fondation |
| Phase 3 : Bouton transform GroupPanel | ~0.5 jour | P0 — feature principale |
| Phase 4 : Composite dans Publish/Build | ~0.5 jour | P1 — complète le workflow |
| Phase 5 : Reconnexion + robustesse | ~1 jour | P1 — robustesse |
| **Total** | **~4 jours** | |

---

## Future Considerations (hors scope)

- **Simplification UX** : Plan dédié avec brainstorm pour réduire les écrans/onglets et clarifier le workflow (stepper, wizard, fusion de sections). Nécessite des tests utilisateur.
- **Pipeline visuel** : Vue "canvas" avec nœuds import → transform → export (actuellement en Labs). Pourrait remplacer la navigation par sections.
- **Transforms parallèles** : Si DuckDB évolue vers le multi-writer, ou si on partitionne par groupe dans des fichiers séparés.
- **Jobs persistants avec reprise** : Reprendre un transform interrompu là où il s'est arrêté (nécessite un checkpoint par widget).
- **Notifications desktop** : Via Tauri notifications API quand un job long se termine.
- **Estimation temps restant** : Basée sur l'historique des durées passées par widget.

---

## Documentation Plan

| Document | Action | Priorité |
|---|---|---|
| Guide utilisateur "Lancer un calcul" | Créer | P1 |
| API reference `/api/jobs/*` | Créer | P1 |
| Architecture job system (ADR) | Créer dans `docs/09-architecture/adr/` | P2 |
| Migration guide (polling → SSE) | Interne dev | P2 |

---

## References & Research

### Internal References

- Plan release v1 : `docs/plans/2026-02-19-feat-release-v1-desktop-app-publication-plan.md`
- Contrat config v1 : `docs/plans/2026-02-19-contrat-configuration-v1.md`
- Transform router : `src/niamoto/gui/api/routers/transform.py`
- Export router : `src/niamoto/gui/api/routers/export.py`
- Deploy SSE (pattern) : `src/niamoto/gui/api/routers/deploy.py`
- GroupPanel : `src/niamoto/gui/ui/src/components/panels/GroupPanel.tsx`
- Build page : `src/niamoto/gui/ui/src/pages/publish/build.tsx`
- Frontend transform API : `src/niamoto/gui/ui/src/lib/api/transform.ts`
- Frontend export API : `src/niamoto/gui/ui/src/lib/api/export.ts`
- Navigation store : `src/niamoto/gui/ui/src/stores/navigationStore.ts`
- Publish store : `src/niamoto/gui/ui/src/stores/publishStore.ts`
- Phase transform/export (roadmap) : `docs/10-roadmaps/gui-finalization/02-phase-transform-export.md`
- Architecture cible 2026 : `docs/09-architecture/target-architecture-2026.md`
- Error handling roadmap : `docs/10-roadmaps/error-handling.md`

### Architecture Decisions clés

- SQLite séparé pour les jobs (pas DuckDB) → évite le conflit single-writer
- SSE (pas WebSocket) → plus simple, pattern existant
- Un seul job à la fois (pas de concurrence) → contrainte DuckDB
- Annulation via `threading.Event` → point d'interruption naturel entre widgets
- Job composite = 1 job avec 2 phases (pas 2 jobs liés)
