---
title: "feat: Centre de notifications connecté aux jobs du pipeline"
type: feat
date: 2026-02-24
---

# Centre de notifications connecté aux jobs du pipeline

## Overview

Remplacer le placeholder (bell icon + 2 notifications statiques) dans la TopBar par un **vrai centre de notifications** connecté aux 4 types de jobs longs du pipeline : import, enrichment, transform, export.

Le système est **frontend-only** : aucune modification backend. Un store Zustand persisté (localStorage) collecte les événements des jobs via polling des endpoints existants et les affiche dans un dropdown depuis l'icône cloche.

**Bonus critique** : fixer le `<Toaster />` de sonner qui n'est jamais rendu (22+ fichiers appellent `toast()` silencieusement).

---

## Problem Statement

### Ce qui ne fonctionne pas

1. **Bell icon 100% placeholder** — Pastille rouge permanente, 2 notifications hardcodées qui ne changent jamais (`TopBar.tsx:112-144`)
2. **`<Toaster />` jamais rendu** — Aucune instance de `<Toaster />` dans l'arbre React (`main.tsx`, `App.tsx`). Les 22+ fichiers qui appellent `toast()` sont silencieusement ignorés
3. **Aucun store de notifications** — Pas de Zustand store, pas de React context, pas de mécanisme pour collecter des événements
4. **Settings "Notifications" décoratifs** — Les 3 switches dans Settings sont `defaultChecked` mais pas câblés (`settings.tsx:188-226`)
5. **Pas de visibilité cross-page** — Si un job tourne pendant que l'utilisateur navigue, rien ne l'indique en dehors de la page d'origine

### Ce qui fonctionne déjà

- 4 systèmes de jobs avec endpoints de statut (import, enrichment, transform, export)
- Polling 1s côté frontend pour chaque type de job (dans les composants)
- `JobFileStore` pour transform/export avec persistance fichier
- Clés i18n existantes pour les notifications (`tools.json:105-112`)
- shadcn/ui DropdownMenu déjà utilisé dans TopBar

---

## Proposed Solution

### Architecture frontend-only

```
┌─────────────────────────────────────────────────────────┐
│  notificationStore (Zustand + persist)                   │
│                                                          │
│  trackedJobs: Map<jobId, TrackedJob>                     │
│  notifications: Notification[]                           │
│  unreadCount: number                                     │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Import   │  │ Enrichmt │  │Transform │  │ Export  │ │
│  │ Poller   │  │ Poller   │  │ Poller   │  │ Poller  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│       │              │             │              │      │
│       ▼              ▼             ▼              ▼      │
│  poll /api/     poll /api/    poll /api/     poll /api/  │
│  imports/jobs   enrichment/   transform/     export/     │
│  ?status=running job/{ref}    active         active      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  TopBar                                                  │
│  🔔 (3)  ← badge = unread count                         │
│  ┌────────────────────────┐                              │
│  │ ▶ Transform en cours…  │ ← section "En cours"        │
│  │   ████████░░░░ 67%     │                              │
│  │ ───────────────────── │                              │
│  │ ✅ Import terminé      │ ← section "Récents"         │
│  │    il y a 5 min        │                              │
│  │ ❌ Export échoué       │                              │
│  │    il y a 20 min       │                              │
│  │ ─── Tout effacer ──── │                              │
│  └────────────────────────┘                              │
└─────────────────────────────────────────────────────────┘
```

### Décisions architecturales

| Décision | Choix | Justification |
|----------|-------|---------------|
| **Modifications backend** | Aucune | Les endpoints existants suffisent. On branche dessus. |
| **Store** | Zustand persist (localStorage) | Même pattern que `publishStore.ts`. Survit au rechargement. |
| **Polling stratégie** | 2 niveaux : 1s si job actif, 15s en veille | Évite 4 req/s à vide tout en détectant les jobs externes |
| **Déduplication** | Par `jobId` + transition de status | On ne génère une notification que sur changement d'état terminal |
| **Toast vs Notification** | Les deux coexistent | Toast = feedback immédiat. Notification = historique. Pas de duplication car la notification est silencieuse (pas de toast si toast déjà émis par le composant local). |
| **Scope projet** | Clé localStorage inclut `projectPath` | Empêche les notifications croisées entre projets (Tauri) |

---

## Technical Approach

### Phase 0 : Fix `<Toaster />` manquant (~15 min)

**Fichier** : `src/niamoto/gui/ui/src/App.tsx`

Ajouter `<Toaster />` de sonner dans l'arbre React, juste après `<ThemeProvider>`. Les 22 fichiers qui appellent déjà `toast()` commenceront à fonctionner immédiatement.

```tsx
import { Toaster } from 'sonner'

// Dans le return, après <ThemeProvider> :
<ThemeProvider>
  <Toaster position="bottom-right" richColors />
  <BrowserRouter>
    ...
  </BrowserRouter>
</ThemeProvider>
```

**Impact** : Fix immédiat pour GroupPanel, EnrichmentTab, SiteBuilder, PublishBuild, PublishDeploy, etc.

**Tests** : Vérifier visuellement qu'un `toast.success("test")` s'affiche.

---

### Phase 1 : Notification Store (~0.5 jour)

**Fichier à créer** : `src/niamoto/gui/ui/src/stores/notificationStore.ts`

#### 1.1 Modèle de données

```typescript
// notificationStore.ts

export type JobType = 'import' | 'enrichment' | 'transform' | 'export'
export type NotificationStatus = 'running' | 'completed' | 'failed' | 'interrupted' | 'paused'

export interface TrackedJob {
  jobId: string
  jobType: JobType
  status: NotificationStatus
  progress: number
  message: string
  phase?: string | null
  startedAt: string
  // Pour enrichment : le reference_name nécessaire au polling
  meta?: { referenceName?: string }
}

export interface AppNotification {
  id: string                    // uuid
  jobId: string
  jobType: JobType
  status: 'completed' | 'failed' | 'interrupted'
  title: string                 // "Import terminé"
  message: string               // "3 entités, 1245 lignes"
  timestamp: string             // ISO
  read: boolean
  path?: string                 // lien de navigation optionnel
}

interface NotificationState {
  // Jobs en cours (pas persistés — reconstruits par polling)
  trackedJobs: TrackedJob[]

  // Notifications terminées (persistées dans localStorage)
  notifications: AppNotification[]
  unreadCount: number

  // Actions
  trackJob: (job: TrackedJob) => void
  updateTrackedJob: (jobId: string, updates: Partial<TrackedJob>) => void
  completeJob: (jobId: string, notification: Omit<AppNotification, 'id' | 'timestamp' | 'read'>) => void
  removeTrackedJob: (jobId: string) => void

  markAsRead: (notificationId: string) => void
  markAllAsRead: () => void
  clearNotifications: () => void
  clearOldNotifications: (maxAge: number) => void  // ms

  // Sélecteurs
  getActiveJobs: () => TrackedJob[]
  hasRunningJob: (jobType?: JobType) => boolean
}
```

#### 1.2 Comportement du store

- `trackJob()` : Enregistre un nouveau job en cours. Appelé par les composants qui démarrent un job OU par le poller de découverte.
- `updateTrackedJob()` : Met à jour progress/message d'un job traqué.
- `completeJob()` : Transfère un job de `trackedJobs` vers `notifications`, incrémente `unreadCount`.
- `clearOldNotifications(7 * 24 * 60 * 60 * 1000)` : Purge les notifications > 7 jours. Appelé au montage.

**Persistance** : Seul `notifications` et `unreadCount` sont persistés (via `partialize`). `trackedJobs` est volatile et reconstruit au démarrage par polling.

```typescript
export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      // ... implémentation
    }),
    {
      name: 'niamoto-notifications',  // clé localStorage
      partialize: (state) => ({
        notifications: state.notifications,
        unreadCount: state.unreadCount,
      }),
    }
  )
)
```

**Fichiers impactés** : Aucun fichier existant modifié dans cette phase.

---

### Phase 2 : Job Polling Service (~0.5 jour)

**Fichier à créer** : `src/niamoto/gui/ui/src/hooks/useJobPolling.ts`

Un hook React qui :
1. Au montage : vérifie chaque endpoint pour détecter des jobs en cours
2. Quand un job est traqué : poll son endpoint toutes les 1s
3. Quand aucun job actif : poll en mode "découverte" toutes les 15s
4. Détecte les transitions d'état et appelle `notificationStore.completeJob()`

#### 2.1 Stratégie de polling par type

| Type | Endpoint découverte | Endpoint statut | Particularité |
|------|---------------------|-----------------|---------------|
| **Import** | `GET /api/imports/jobs` (filtrer `status=running`) | `GET /api/imports/jobs/{jobId}` | Multi-job possible. Le dict backend retourne tous les jobs. |
| **Enrichment** | Aucun endpoint global | `GET /api/enrichment/job/{referenceName}` | Le store doit connaître le `referenceName` via `trackJob()`. Pas de découverte autonome. |
| **Transform** | `GET /api/transform/active` | `GET /api/transform/status/{jobId}` | Retourne `null` si pas de job actif. |
| **Export** | `GET /api/export/active` | `GET /api/export/status/{jobId}` | Retourne `null` si pas de job actif. |

#### 2.2 Gestion enrichment sans endpoint global

**Problème identifié (SpecFlow)** : L'enrichment n'a pas d'endpoint pour lister tous les jobs. L'endpoint est `GET /api/enrichment/job/{reference_name}` — il faut connaître le nom de la référence.

**Solution** : Le composant `EnrichmentTab` appelle `notificationStore.trackJob()` au démarrage de l'enrichment avec `meta: { referenceName: "taxonomy" }`. Le poller utilise ce `referenceName` pour interroger le bon endpoint. Si aucun enrichment n'est traqué, pas de polling enrichment.

```typescript
// Dans EnrichmentTab.tsx, au lancement de l'enrichment :
notificationStore.trackJob({
  jobId: response.job_id,
  jobType: 'enrichment',
  status: 'running',
  progress: 0,
  message: 'Enrichissement en cours...',
  startedAt: new Date().toISOString(),
  meta: { referenceName: reference.name },
})
```

#### 2.3 Déduplication et transitions

```
État du poll:
  T=0: status=running, progress=45  → updateTrackedJob()
  T=1: status=running, progress=67  → updateTrackedJob()
  T=2: status=completed             → completeJob() + removeTrackedJob()
  T=3: status=completed             → job déjà dans notifications, SKIP (dédup par jobId)
```

La déduplication se fait via `trackedJobs` : si le `jobId` n'est pas dans `trackedJobs`, le poller ne génère pas de nouvelle notification (il vérifie aussi dans `notifications` pour éviter les doublons au redémarrage).

#### 2.4 Réconciliation au démarrage

Au montage du hook :
1. Lire les `notifications` persistées dans localStorage
2. Vérifier s'il reste des jobs "running" dans le localStorage (ne devrait pas arriver grâce à `partialize`)
3. Interroger `/api/transform/active` et `/api/export/active` pour détecter des jobs en cours
4. Interroger `/api/imports/jobs` pour détecter des imports running
5. Pour chaque job détecté : l'ajouter à `trackedJobs` et commencer le polling actif

**Cas "job perdu"** : Si le localStorage référence un `jobId` dans les notifications mais le backend retourne 404 → rien à faire, la notification reste (c'est un historique).

**Fichiers impactés** :
- `src/niamoto/gui/ui/src/components/config/EnrichmentTab.tsx` — ajouter `trackJob()` au démarrage enrichment
- Les autres composants (GroupPanel, build.tsx) peuvent optionnellement appeler `trackJob()` aussi, mais le poller de découverte les trouvera de toute façon

---

### Phase 3 : Composant NotificationDropdown (~0.5 jour)

**Fichier à créer** : `src/niamoto/gui/ui/src/components/layout/NotificationDropdown.tsx`

Remplace le bloc `{/* Notifications */}` dans `TopBar.tsx` (lignes 112-144).

#### 3.1 Structure du composant

```
┌──────────────────────────────────────┐
│  Notifications                       │
│  ─────────────────────────────────── │
│                                      │
│  EN COURS                            │
│  🔄 Transform — taxons              │
│     ████████████░░░░░░ 67%           │
│     Widget forest_cover (8/12)       │
│                                      │
│  ─────────────────────────────────── │
│                                      │
│  RÉCENTS                             │
│  ✅ Import terminé                   │  ← non lu (fond subtle)
│     3 entités, 1245 lignes — 5 min   │
│  ❌ Export échoué                    │  ← non lu
│     Erreur template — 20 min         │
│  ✅ Enrichment terminé              │  ← lu (fond normal)
│     234 taxons enrichis — 2h         │
│                                      │
│  ─────────────────────────────────── │
│  Tout marquer comme lu    Effacer    │
│                                      │
└──────────────────────────────────────┘
```

#### 3.2 Badge logic

```typescript
// Badge sur l'icône cloche :
// - Nombre affiché = unreadCount (notifications non lues)
// - Pastille animée (pulse) si au moins un job en cours
// - Pastille statique si seulement des notifications non lues
// - Pas de pastille si tout est lu et rien ne tourne

const { unreadCount, trackedJobs } = useNotificationStore()
const hasActiveJob = trackedJobs.length > 0
const showBadge = unreadCount > 0 || hasActiveJob
```

#### 3.3 Icônes par type et statut

| Type | Running | Completed | Failed |
|------|---------|-----------|--------|
| Import | `Loader2` (spin) | `CheckCircle2` (vert) | `XCircle` (rouge) |
| Enrichment | `Loader2` (spin) | `CheckCircle2` (vert) | `XCircle` (rouge) |
| Transform | `Loader2` (spin) | `CheckCircle2` (vert) | `XCircle` (rouge) |
| Export | `Loader2` (spin) | `CheckCircle2` (vert) | `XCircle` (rouge) |

#### 3.4 Temps relatif

Utiliser un helper simple pour "il y a X min" sans dépendance externe :

```typescript
function timeAgo(isoDate: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000)
  if (seconds < 60) return 'à l\'instant'
  if (seconds < 3600) return `il y a ${Math.floor(seconds / 60)} min`
  if (seconds < 86400) return `il y a ${Math.floor(seconds / 3600)}h`
  return `il y a ${Math.floor(seconds / 86400)}j`
}
```

**Fichiers impactés** :
- `src/niamoto/gui/ui/src/components/layout/TopBar.tsx` — remplacer lignes 112-144 par `<NotificationDropdown />`

---

### Phase 4 : Intégration et câblage (~0.25 jour)

#### 4.1 Monter le hook de polling dans MainLayout

**Fichier** : `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`

Ajouter `useJobPolling()` dans le composant `MainLayout` pour que le polling soit actif sur toutes les pages.

```tsx
export function MainLayout() {
  useJobPolling()  // ← démarre le polling global
  // ... reste du composant
}
```

#### 4.2 Câbler les composants qui démarrent des jobs

Pour que le notification center détecte les jobs immédiatement (sans attendre le cycle de découverte 15s), chaque composant qui démarre un job appelle `trackJob()` :

**`GroupPanel.tsx`** (transform) :
```typescript
// Après le POST /api/transform/execute réussi :
useNotificationStore.getState().trackJob({
  jobId: response.job_id,
  jobType: 'transform',
  status: 'running',
  progress: 0,
  message: 'Transformations en cours...',
  startedAt: new Date().toISOString(),
})
```

**`build.tsx`** (export/composite) :
```typescript
useNotificationStore.getState().trackJob({
  jobId: response.job_id,
  jobType: 'export',  // même pour composite
  status: 'running',
  progress: 0,
  message: 'Génération en cours...',
  startedAt: new Date().toISOString(),
})
```

**`EnrichmentTab.tsx`** (enrichment) :
```typescript
useNotificationStore.getState().trackJob({
  jobId: response.job_id,
  jobType: 'enrichment',
  status: 'running',
  progress: 0,
  message: 'Enrichissement en cours...',
  startedAt: new Date().toISOString(),
  meta: { referenceName: reference.name },
})
```

**Import** — Détecté automatiquement par le poller (l'import a un endpoint `GET /api/imports/jobs` qui retourne tous les jobs). Optionnellement câbler dans `ImportPage` aussi.

#### 4.3 Clés i18n

**Fichiers** : `src/niamoto/gui/ui/src/i18n/locales/fr/common.json` et `en/common.json`

Ajouter les clés :

```json
{
  "notifications": {
    "title": "Notifications",
    "active_jobs": "En cours",
    "recent": "Récents",
    "no_notifications": "Aucune notification",
    "mark_all_read": "Tout marquer comme lu",
    "clear_all": "Effacer",
    "job_completed": "{{type}} terminé",
    "job_failed": "{{type}} échoué",
    "job_interrupted": "{{type}} interrompu",
    "time_just_now": "à l'instant",
    "time_minutes_ago": "il y a {{count}} min",
    "time_hours_ago": "il y a {{count}}h",
    "time_days_ago": "il y a {{count}}j",
    "import": "Import",
    "enrichment": "Enrichissement",
    "transform": "Transformation",
    "export": "Export"
  }
}
```

**Fichiers impactés dans cette phase** :
- `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx` — ajouter `useJobPolling()`
- `src/niamoto/gui/ui/src/components/panels/GroupPanel.tsx` — ajouter `trackJob()`
- `src/niamoto/gui/ui/src/pages/publish/build.tsx` — ajouter `trackJob()`
- `src/niamoto/gui/ui/src/components/config/EnrichmentTab.tsx` — ajouter `trackJob()`
- `src/niamoto/gui/ui/src/i18n/locales/fr/common.json` — clés i18n
- `src/niamoto/gui/ui/src/i18n/locales/en/common.json` — clés i18n

---

## Edge Cases identifiés (SpecFlow)

### 1. Transform/Export partagent le même JobFileStore

Transform et export utilisent un seul slot de job actif. Si un transform tourne, `GET /api/export/active` retourne `null` mais `POST /api/export/execute` retourne 409.

**Gestion** : Le poller de découverte interroge les deux endpoints. Si `/api/transform/active` retourne un job, pas besoin de poll `/api/export/active` (ils sont mutuellement exclusifs). Le badge affiche le job actif quel que soit son type.

### 2. Rechargement page pendant un long job

Le localStorage persiste les `notifications` mais pas les `trackedJobs`. Au rechargement :
1. Le hook `useJobPolling` se monte
2. Il interroge `/api/transform/active`, `/api/export/active`, `/api/imports/jobs`
3. S'il trouve un job `running`, il le remet dans `trackedJobs`
4. Le polling 1s reprend

Pour l'enrichment : si le localStorage n'a pas l'info du `referenceName`, le job enrichment est "perdu" au rechargement. **Mitigation** : persister aussi les `trackedJobs` enrichment dans un champ séparé du store.

### 3. Toast duplication

Les composants (GroupPanel, build.tsx) appellent déjà `toast.success()` quand un job se termine. Le notification center va aussi détecter la complétion.

**Règle** : Le notification center ne fire PAS de toast. Il ajoute seulement à `notifications[]`. Les toasts restent la responsabilité des composants locaux. L'intérêt du notification center est la persistance cross-page + le badge dans la TopBar.

### 4. Notifications d'un autre projet (Tauri)

Si l'utilisateur change de projet, le localStorage contient des notifications de l'ancien projet.

**Gestion** : La clé persist inclut le chemin du projet :
```typescript
name: `niamoto-notifications-${projectPath}`
```
Le `projectPath` est lu depuis `useProjectInfo()` ou `window.__NIAMOTO_PROJECT__`.

### 5. Job enrichment avec pause/resume/offline

L'enrichment a des états intermédiaires (`paused`, `paused_offline`). Le poller les traite comme "actif" (ni terminal ni running classique).

**Gestion** : `paused` → affiché avec icône pause dans le dropdown. `paused_offline` → affiché avec icône WifiOff. Ces états ne génèrent pas de notification tant que le job n'est pas terminé.

### 6. Imports multiples simultanés

Le backend import permet plusieurs jobs en parallèle (dict en mémoire). Le poller peut en trouver plusieurs.

**Gestion** : Chaque import est un `TrackedJob` distinct dans le store. Le dropdown les affiche tous dans la section "En cours".

---

## Acceptance Criteria

### Functional Requirements

- [x] Le `<Toaster />` de sonner est rendu dans `App.tsx` — les 22+ appels `toast()` existants fonctionnent
- [x] L'icône cloche dans TopBar affiche un badge avec le nombre de notifications non lues
- [x] Le badge pulse quand au moins un job est en cours
- [x] Cliquer sur la cloche ouvre un dropdown avec 2 sections : "En cours" et "Récents"
- [x] La section "En cours" montre chaque job actif avec barre de progression et message
- [x] La section "Récents" montre les 20 dernières notifications (succès/échec/interruption)
- [x] Les notifications non lues ont un fond distinct (subtle highlight)
- [x] "Tout marquer comme lu" remet `unreadCount` à 0
- [x] "Effacer" supprime toutes les notifications de l'historique
- [x] Un job qui se termine pendant que l'utilisateur est sur une autre page génère une notification visible dans la cloche
- [x] Au rechargement, le polling redécouvre automatiquement les jobs en cours (transform, export, import)
- [ ] Le changement de projet (Tauri) isole les notifications par projet

### Non-Functional Requirements

- [x] Polling actif (1s) uniquement quand un job est traqué
- [x] Polling découverte (5s) quand aucun job actif
- [x] Max 50 notifications en localStorage (purge FIFO des plus anciennes)
- [x] Purge automatique des notifications > 7 jours au montage
- [x] Pas de modification backend

### Quality Gates

- [ ] Tests unitaires `notificationStore` : trackJob, updateTrackedJob, completeJob, markAsRead, clearOldNotifications, déduplication
- [ ] Test de la logique polling : transitions d'état running→completed, running→failed
- [ ] Test de réconciliation : localStorage stale + backend actif → reconstruction correcte
- [ ] Test déduplication : même jobId terminé → 1 seule notification
- [x] Pas de régression sur les 235+ tests GUI API existants
- [x] Le `<Toaster />` fonctionne (rendu dans App.tsx)

---

## Fichiers créés et modifiés

### Fichiers à créer (3)

| Fichier | Description |
|---------|-------------|
| `src/niamoto/gui/ui/src/stores/notificationStore.ts` | Store Zustand : modèle de données, actions, persistance |
| `src/niamoto/gui/ui/src/hooks/useJobPolling.ts` | Hook de polling : découverte, suivi, transitions d'état |
| `src/niamoto/gui/ui/src/components/layout/NotificationDropdown.tsx` | Composant dropdown : badge, liste, actions |

### Fichiers à modifier (7)

| Fichier | Modification |
|---------|-------------|
| `src/niamoto/gui/ui/src/App.tsx` | Ajouter `<Toaster />` de sonner |
| `src/niamoto/gui/ui/src/components/layout/TopBar.tsx` | Remplacer placeholder par `<NotificationDropdown />` |
| `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx` | Ajouter `useJobPolling()` |
| `src/niamoto/gui/ui/src/components/panels/GroupPanel.tsx` | Ajouter `trackJob()` au démarrage transform |
| `src/niamoto/gui/ui/src/pages/publish/build.tsx` | Ajouter `trackJob()` au démarrage export |
| `src/niamoto/gui/ui/src/components/config/EnrichmentTab.tsx` | Ajouter `trackJob()` au démarrage enrichment |
| `src/niamoto/gui/ui/src/i18n/locales/fr/common.json` | Clés i18n notifications |
| `src/niamoto/gui/ui/src/i18n/locales/en/common.json` | Clés i18n notifications |

---

## Dependencies & Prerequisites

| Dépendance | Statut | Impact |
|---|---|---|
| `sonner` (toaster) | ✅ Installé (22 fichiers l'importent) | Juste ajouter `<Toaster />` |
| shadcn/ui DropdownMenu | ✅ Déjà utilisé dans TopBar | Réutiliser |
| shadcn/ui Progress | ✅ Disponible | Pour la barre de progression dans le dropdown |
| Zustand persist | ✅ Utilisé par publishStore | Même pattern |
| Endpoints import/transform/export | ✅ Existent | Polling sans modification |
| Endpoint enrichment global | ❌ N'existe pas | Contourné via `meta.referenceName` dans trackJob |

---

## Risk Analysis & Mitigation

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Toast duplication (composant + notification center) | Moyenne | Faible | Le notification center ne fire pas de toast, seulement badge + liste |
| Enrichment perdu au rechargement | Moyenne | Faible | Persister les `trackedJobs` enrichment séparément |
| Polling 4 endpoints simultanément en mode découverte | Faible | Faible | Sur loopback, 4 requêtes/15s est négligeable |
| localStorage plein | Très faible | Faible | Purge auto 50 items + 7 jours |
| Race condition polling vs composant local | Faible | Faible | Déduplication par jobId dans le store |
| Backend endpoint enrichment renvoie 404 quand pas de job | Moyenne | Faible | Attraper le 404 silencieusement, traiter comme "pas de job" |

---

## Estimation d'effort

| Phase | Effort | Priorité |
|---|---|---|
| Phase 0 : Fix `<Toaster />` | ~15 min | P0 — bug critique |
| Phase 1 : Notification Store | ~0.5 jour | P0 — fondation |
| Phase 2 : Job Polling Service | ~0.5 jour | P0 — le moteur |
| Phase 3 : NotificationDropdown | ~0.5 jour | P0 — l'interface |
| Phase 4 : Intégration + i18n | ~0.25 jour | P0 — câblage |
| **Total** | **~1.75 jour** | |

---

## Chemin vers v2

Ce notification center est conçu pour évoluer :

1. **Unification backend** : Quand imports/enrichment migreront vers JobFileStore, un seul endpoint `/api/jobs/active` suffira → simplifier le poller
2. **SSE** : Remplacer le polling par des Server-Sent Events → le store écoute un flux unique
3. **Notifications desktop** : Ajouter Tauri notification API quand un job long se termine et que l'app est en arrière-plan
4. **Indicateur pipeline** : Afficher Import ✓ → Transform ⚠ → Export ○ dans la sidebar
5. **Préférences** : Câbler les switches dans Settings pour activer/désactiver les notifications par type

---

## References

### Internal

- TopBar placeholder : `src/niamoto/gui/ui/src/components/layout/TopBar.tsx:112-144`
- Publish store (pattern Zustand persist) : `src/niamoto/gui/ui/src/stores/publishStore.ts`
- Transform API client : `src/niamoto/gui/ui/src/lib/api/transform.ts`
- Export API client : `src/niamoto/gui/ui/src/lib/api/export.ts`
- Import router (dict en mémoire) : `src/niamoto/gui/api/routers/imports.py:23`
- Enrichment router (job global) : `src/niamoto/gui/api/routers/enrichment.py`
- JobFileStore : `src/niamoto/gui/api/services/job_file_store.py`
- Plan job system : `docs/plans/2026-02-23-feat-transform-trigger-robust-job-system-plan.md`
- Architecture cible : `docs/09-architecture/target-architecture-2026.md` (Section 5.5)
- Roadmap GUI : `docs/10-roadmaps/gui-finalization/00-overview.md` (Lacune UX U1)
