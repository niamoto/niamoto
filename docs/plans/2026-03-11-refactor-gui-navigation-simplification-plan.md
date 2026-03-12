---
title: "Simplification de la navigation GUI Niamoto"
type: refactor
date: 2026-03-11
updated: 2026-03-12
---

# Simplification de la navigation GUI Niamoto

## Overview

L'interface Niamoto a accumulé **6 sections sidebar avec sous-menus, ~30 routes, 25+ items dynamiques** sur **3-4 niveaux de nesting**. Le créateur lui-même s'y perd.

Le problème va au-delà de la navigation : **le pipeline Import → Transform → Site → Publish est invisible**, il n'y a **aucun tracking de fraîcheur** (quand un dataset est réimporté, l'interface ne montre pas que les transforms sont périmées), et la sidebar essaie d'être à la fois un menu de navigation ET un navigateur de contenu.

La recherche UX converge vers un modèle **"asset-aware"** (inspiré de Dagster/dbt) : organiser par **objets avec indicateurs de fraîcheur**, pas par étapes de pipeline. Le pipeline linéaire est utile pour l'onboarding mais inutile pour l'usage quotidien où l'utilisateur pense "j'ai modifié X, qu'est-ce qui doit être recalculé ?"

Ce plan propose **5 approches à prototyper** avant implémentation, avec un nettoyage immédiat comme prérequis.

---

## Problem Statement

### Deux modes d'utilisation, un seul problème

| Mode | Ce que fait l'utilisateur | Ce dont il a besoin |
|------|--------------------------|-------------------|
| **Premier setup** | Import → configurer groupes → configurer site → build → deploy | Un **guide linéaire** (pipeline stepper/checklist) |
| **Usage quotidien** | Mettre à jour des données, modifier un widget, éditer une page | Savoir **ce qui est périmé** et pouvoir **relancer ce qui est affecté** |

Le plan initial (v1) ne traitait que le premier setup. L'usage quotidien est le vrai enjeu.

### Problèmes structurels

| Problème | Détail | Pourquoi c'est grave |
|----------|--------|---------------------|
| **Sidebar = navigateur de contenu** | Chaque dataset/référence/groupe est un sous-item | Mode compact inutilisable (3 items max). La sidebar grossit avec les données. |
| **Duplication sidebar ↔ contenu** | `GroupsPage` affiche des cards cliquables ET la sidebar liste les mêmes items | Deux chemins pour la même chose, confusion |
| **Pipeline invisible** | Aucun élément ne montre Import → Transform → Site → Publish | Nouvel utilisateur ne sait pas quoi faire |
| **Aucun tracking de fraîcheur** | Quand un dataset est réimporté, les transforms ne savent pas qu'elles sont périmées | L'utilisateur doit "se souvenir" de ce qu'il faut relancer |
| **Pas de cascade** | Modifier un widget → il faut manuellement relancer le bon groupe → puis rebuilder le site | Process manuel, sujet à erreur |
| **TOOLS = fourre-tout** | 6 items sans rapport | Anti-pattern UX |
| **LABS obsolète** | 3 mockups widgets en production | Bruit |

### État technique du pipeline (découverte importante)

```
Import (full regeneration)
    │
    ▼
Transform (séquentiel, groupe par groupe, full regeneration)
    │
    ▼
Export (full regeneration, Jinja2 templates → HTML)
```

**Ce qui existe** :
- Job store (`job_file_store.py`) avec timestamps `started_at`/`completed_at`
- `niamoto_metadata_entities` avec colonnes `created_at`/`updated_at` (mais non consultées)
- API transform qui accepte un filtre par `group_by` (run un seul groupe possible)

**Ce qui manque** :
- ❌ Aucune comparaison "données importées à T1" vs "transform exécuté à T0"
- ❌ Aucun hash de config pour détecter les changements de widgets
- ❌ Aucune cascade automatique

### Recherche UX — Principes appliqués

| Principe | Source | Application |
|----------|--------|-------------|
| **Noun-first navigation** | OOUX (A List Apart), Linear | La sidebar montre des objets (Données, Groupes, Site), pas des verbes (Importer, Transformer) |
| **Asset model avec fraîcheur** | Dagster, dbt | Chaque objet porte un statut : frais ✅, périmé ⚠️, erreur ❌ |
| **Actions contextuelles** | LukeW, NNGroup | L'action pertinente est visible quand c'est le moment (pas cachée dans un menu) |
| **Dashboard adaptatif** | Notion, Vercel, Linear | La home page change selon l'état du projet (vide → setup, mature → statuts) |
| **Cascade preview** | Terraform plan/apply | Montrer ce qui sera affecté avant d'exécuter |
| **3 niveaux de fraîcheur** | dbt, Dagster | Vert = à jour, Jaune = périmé, Rouge = erreur |
| **Max 2 niveaux de nav** | NNGroup Progressive Disclosure | Sidebar flat → page avec contenu navigable |

---

## Proposed Solutions — 5 Approches à Prototyper

### Prérequis commun : Sidebar plate (tous les prototypes)

Quelle que soit l'approche retenue, la sidebar devient un **rail plat** :

```
┌────┐
│ 🏠 │  Home / Dashboard
│ 📦 │  Données
│ ⚙  │  Groupes
│ 🌐 │  Site
│ 🚀 │  Publication
│────│
│ ⚙  │  Paramètres
│ 👁 │  Aperçu
└────┘
```

**Règle absolue** : zéro sous-menu, zéro expansion, zéro item dynamique dans la sidebar. Identique en mode full, compact et caché. Les datasets, groupes, pages sont accessibles uniquement via la zone de contenu (cards, listes, recherche).

En mode full, les labels texte apparaissent à côté des icônes. En mode compact, icônes seules. C'est tout.

---

### Approche A : Pipeline Rail

**Inspiration** : Vercel, Netlify, dbt Cloud

Un **bandeau horizontal pipeline** sous le TopBar montre les 4 étapes avec statut. Chaque section est une page autonome avec son contenu navigable.

```
┌──────────────────────────────────────────────────────────────────┐
│  [≡] Niamoto — mon-projet                                [⌘ K] │
│  ① Données ✅ ──→ ② Groupes ⚠️ ──→ ③ Site ✅ ──→ ④ Publier ○  │
├────┬─────────────────────────────────────────────────────────────┤
│ 🏠 │                                                             │
│[📦]│  Données                               [▶ Importer]        │
│ ⚙  │                                                             │
│ 🌐 │  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│ 🚀 │  │ occurr.  │  │ plots    │  │ shapes   │                 │
│    │  │ 12,453   │  │ 234      │  │ 45       │                 │
│    │  │ ✅ frais  │  │ ⚠️ modif │  │ ✅ frais  │                 │
│────│  └──────────┘  └──────────┘  └──────────┘                 │
│ ⚙  │  ┌──────────┐  ┌──────────┐                               │
│ 👁 │  │ taxon    │  │ communes │                                │
│    │  │ ref hier.│  │ ref spat.│                                │
│    │  └──────────┘  └──────────┘                                │
└────┴─────────────────────────────────────────────────────────────┘
```

**Pour le premier setup** : Le bandeau guide — les étapes non complétées sont grises.
**Pour l'usage quotidien** : Le bandeau montre ce qui est périmé (⚠️) — cliquer sur une étape jaune va à la section concernée.

**Forces** : Pipeline toujours visible. Pages existantes réutilisées directement. Fonctionne en compact.
**Faiblesses** : Le bandeau prend de la place. L'aspect "étapes" peut paraître rigide pour un usage quotidien.

---

### Approche B : Hub Dashboard Adaptatif

**Inspiration** : Notion home, Linear, Vercel project dashboard

Un **dashboard central** qui change selon l'état du projet. C'est la page d'accueil. Les sections restent accessibles via la sidebar.

**Projet vide (onboarding)** :
```
┌────┬─────────────────────────────────────────────────────────────┐
│    │                                                             │
│ 🏠 │   Bienvenue sur Niamoto                                    │
│ 📦 │                                                             │
│ ⚙  │   Pour commencer, importez vos données :                   │
│ 🌐 │                                                             │
│ 🚀 │   ☐  ① Importer vos fichiers              [▶ Commencer]   │
│    │   ☐  ② Configurer les groupes d'analyse                    │
│────│   ☐  ③ Personnaliser le site web                           │
│ ⚙  │   ☐  ④ Publier                                             │
│ 👁 │                                                             │
└────┴─────────────────────────────────────────────────────────────┘
```

**Projet configuré, tout à jour** :
```
┌────┬─────────────────────────────────────────────────────────────┐
│    │                                                             │
│[🏠]│  Tout est à jour                  Publié il y a 2 jours    │
│ 📦 │                                                             │
│ ⚙  │  ┌─ Données ────────┐  ┌─ Groupes ─────────┐             │
│ 🌐 │  │ 3 jeux, 2 réfs   │  │ 3/3 à jour ✅     │             │
│ 🚀 │  │ Import: il y a 3j│  │ Calcul: il y a 2j │             │
│    │  │ [Mettre à jour]   │  │ [Configurer]       │             │
│────│  └───────────────────┘  └────────────────────┘             │
│ ⚙  │  ┌─ Site ───────────┐  ┌─ Publication ──────┐             │
│ 👁 │  │ 5 pages, forest  │  │ Déployé ✅         │             │
│    │  │ [Éditer]          │  │ [Republier]         │             │
│    │  └───────────────────┘  └────────────────────┘             │
│    │                                                             │
│    │  ── Activité récente ──────────────────────────────────    │
│    │  • Import occurrences il y a 3j                     ✅     │
│    │  • Calcul tous les groupes il y a 2j                ✅     │
│    │  • Build + deploy Cloudflare il y a 2j              ✅     │
└────┴─────────────────────────────────────────────────────────────┘
```

**Quelque chose est périmé** :
```
┌────┬─────────────────────────────────────────────────────────────┐
│    │                                                             │
│[🏠]│  ⚠️  Mises à jour nécessaires     [▶ Tout mettre à jour]  │
│ 📦 │                                                             │
│ ⚙  │  ┌─ Données ⚠️──────┐  ┌─ Groupes ⚠️───────┐             │
│ 🌐 │  │ plots modifié     │→ │ plots périmé       │             │
│ 🚀 │  │ il y a 5 min      │  │ communes périmé    │             │
│    │  │                   │  │ taxon ✅ à jour     │             │
│────│  │ [Voir les données] │  │ [▶ Recalculer 2]   │             │
│ ⚙  │  └───────────────────┘  └────────────────────┘             │
│ 👁 │  ┌─ Site ✅──────────┐  ┌─ Publication ⚠️────┐             │
│    │  │ Pas de changement │  │ Périmée             │             │
│    │  │                   │  │ (groupes modifiés)  │             │
│    │  └───────────────────┘  │ [▶ Rebuilder]       │             │
│    │                         └────────────────────┘             │
│    │                                                             │
│    │  Cascade : Recalculer plots+communes → Rebuilder → Publier │
└────┴─────────────────────────────────────────────────────────────┘
```

**Forces** : Vue d'ensemble immédiate. L'interface s'adapte à l'état. Les actions les plus pertinentes sont au premier plan. Onboarding intégré. Cascade visible.
**Faiblesses** : Nécessite un système de tracking de fraîcheur (nouveau développement backend). La home page peut devenir verbeuse.

---

### Approche C : Activity Bar (style IDE)

**Inspiration** : VS Code, Figma, JetBrains

*(Décrite dans la v1 du plan — layout 3 colonnes avec activity bar, panneau liste, zone détail.)*

**Évaluation** : Trop technique pour le public cible (botanistes, chercheurs). Layout responsive complexe. **Recommandé de ne pas prototyper** sauf si A et B sont insuffisants.

---

### Approche D : Object-Centric avec Dépendances Visuelles

**Inspiration** : Dagster Asset Lineage, dbt Explorer, GitHub Actions workflow graph

Au lieu de sections pipeline, la home page montre le **graphe de dépendances** du projet : quels datasets alimentent quels groupes, quels groupes produisent quelles pages.

```
┌────┬─────────────────────────────────────────────────────────────┐
│    │                                                             │
│[🏠]│  Projet mon-projet            [▶ Tout mettre à jour]       │
│ 📦 │                                                             │
│ ⚙  │  DONNÉES              GROUPES              SITE            │
│ 🌐 │                                                             │
│ 🚀 │  ┌────────────┐       ┌────────────┐       ┌───────────┐  │
│    │  │ occurrences │──────→│ taxon  ✅  │──────→│ index     │  │
│    │  │ ✅ 12,453   │─┐    └────────────┘   ┌──→│ taxon.html│  │
│────│  └────────────┘  │    ┌────────────┐   │   └───────────┘  │
│ ⚙  │  ┌────────────┐  ├───→│ plots  ⚠️  │───┤                  │
│ 👁 │  │ plots      │──┘    └────────────┘   │   ┌───────────┐  │
│    │  │ ⚠️ modifié  │       ┌────────────┐   └──→│ plots.html│  │
│    │  └────────────┘  ┌───→│ communes❌ │       └───────────┘  │
│    │  ┌────────────┐  │    └────────────┘                      │
│    │  │ shapes     │──┘                          ┌───────────┐  │
│    │  │ ✅         │                              │ team.html │  │
│    │  └────────────┘                              │ biblio... │  │
│    │                                              └───────────┘  │
│    │                                                             │
│    │  Cascade : plots modifié → recalculer plots, communes →    │
│    │            rebuilder → publier                     [▶ Go]  │
└────┴─────────────────────────────────────────────────────────────┘
```

**Interaction** : Cliquer sur un nœud ouvre son détail. Les nœuds périmés ont un contour jaune. Le bouton "Tout mettre à jour" exécute la cascade. On peut aussi cliquer individuellement "Recalculer" sur un seul groupe.

**Forces** : Montre explicitement les dépendances. L'utilisateur comprend POURQUOI quelque chose est périmé. Inspiré des meilleurs outils data (Dagster, dbt).
**Faiblesses** : Graphe complexe si beaucoup de nœuds. Nécessite un moteur de layout de graphe. Peut intimider un botaniste.

---

### Approche E : Contextual Actions (la plus minimaliste)

**Inspiration** : Terraform plan/apply, Netlify status, GitHub PR merge button

Pas de dashboard sophistiqué. La sidebar est plate, chaque section a sa page, mais un **bandeau contextuel** en haut de chaque page montre les actions pertinentes selon l'état.

```
┌────┬─────────────────────────────────────────────────────────────┐
│    │ ⚠️ Données modifiées — 2 groupes à recalculer              │
│ 🏠 │      [▶ Recalculer les groupes affectés]   [Ignorer]       │
│[📦]│─────────────────────────────────────────────────────────────│
│ ⚙  │                                                             │
│ 🌐 │  Données                               [▶ Importer]        │
│ 🚀 │                                                             │
│    │  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│    │  │ occurr.  │  │ plots    │  │ shapes   │                 │
│────│  │ 12,453   │  │ ⚠️ modif │  │ 45       │                 │
│ ⚙  │  │ il y a 3j│  │ 5 min    │  │ il y a 3j│                 │
│ 👁 │  └──────────┘  └──────────┘  └──────────┘                 │
│    │                                                             │
│    │  ┌──────────┐  ┌──────────┐                                │
│    │  │ taxon    │  │ communes │                                │
│    │  │ ref hier.│  │ ref spat.│                                │
│    │  └──────────┘  └──────────┘                                │
└────┴─────────────────────────────────────────────────────────────┘
```

Le même bandeau apparaît partout, adapté au contexte :
- Sur la page Groupes : "Config modifiée pour taxon — [▶ Relancer le calcul]"
- Sur la page Site : "Groupes recalculés — [▶ Rebuilder le site]"
- Sur la page Publication : "Site rebuilded — [▶ Déployer]"

Quand tout est à jour, pas de bandeau — juste une ligne subtile "✅ Tout est à jour".

**Forces** : Minimal — peu de développement UI. Les pages existantes restent inchangées. L'action pertinente est toujours visible. Pas de dashboard supplémentaire.
**Faiblesses** : Moins de vue d'ensemble. L'utilisateur doit naviguer dans chaque section pour voir l'état. Pas d'onboarding guidé.

---

## Comparatif des 5 Approches

| Critère | A: Pipeline Rail | B: Hub Adaptatif | C: Activity Bar | D: Graph Dép. | E: Contextuel |
|---------|:---:|:---:|:---:|:---:|:---:|
| **Onboarding (1er setup)** | ★★★ | ★★★★ | ★★ | ★★ | ★ |
| **Usage quotidien** | ★★ | ★★★★ | ★★★ | ★★★ | ★★★★ |
| **Fraîcheur visible** | ★★★ | ★★★★ | ★★ | ★★★★★ | ★★★ |
| **Cascade visible** | ★ | ★★★ | ★ | ★★★★★ | ★★ |
| **Effort de proto** | Faible | Moyen | Élevé | Élevé | Faible |
| **Réutilise l'existant** | ★★★★ | ★★★ | ★ | ★★ | ★★★★★ |
| **Golden Rule botaniste** | ★★★ | ★★★★ | ★★ | ★★★ | ★★★★ |
| **Mode compact** | ★★★★ | ★★★★ | ★★ | ★★★★ | ★★★★ |

### Recommandation : Prototyper B et E, puis potentiellement D

- **B (Hub Adaptatif)** : La meilleure balance entre onboarding, usage quotidien, et visibilité de l'état. C'est la solution la plus complète.
- **E (Contextuel)** : La plus simple à implémenter. Si B semble trop ambitieux, E est un excellent fallback pragmatique.
- **D (Graph)** : Intéressant pour un V2 futur, ou comme composant intégré dans B (un mini-graphe dans le dashboard).
- **A (Pipeline Rail)** : Peut être combiné avec B comme bandeau compact.

### Approche hybride B+E (recommandée)

Combiner les deux : Hub adaptatif comme **page Home** + bandeaux contextuels dans **chaque section**. L'utilisateur a la vue d'ensemble sur Home et les actions pertinentes dans chaque page.

---

## Concept transversal : Système de Fraîcheur

Quelle que soit l'approche retenue, un **tracking de fraîcheur** est nécessaire côté backend pour alimenter les indicateurs visuels.

### Données nécessaires

| Entité | Timestamp | Hash |
|--------|-----------|------|
| Dataset (import) | `last_imported_at` | `data_hash` (checksum du fichier importé) |
| Référence (import) | `last_imported_at` | `data_hash` |
| Groupe (transform) | `last_transformed_at` | `config_hash` (hash de la section transform.yml du groupe) |
| Site (export) | `last_exported_at` | — |
| Build | `last_built_at` | — |
| Deploy | `last_deployed_at` | `deploy_url` |

### Logique de péremption

```python
# Un groupe est périmé si :
group_stale = (
    group.last_transformed_at < any_source_dataset.last_imported_at  # données modifiées
    or group.config_hash != current_config_hash(group)                # config modifiée
    or group.last_transformed_at is None                               # jamais calculé
)

# Le site est périmé si :
site_stale = (
    any_group.last_transformed_at > site.last_exported_at  # groupes recalculés
    or site_config_changed                                  # pages/nav modifiées
)

# La publication est périmée si :
publish_stale = (
    site.last_exported_at > deploy.last_deployed_at  # site rebuilded
)
```

### Impact backend

- [ ] Ajouter `last_imported_at` dans `niamoto_metadata_entities` (utiliser le `updated_at` existant, déjà en place)
- [ ] Ajouter une table/colonne `transform_runs` : `group_name`, `completed_at`, `config_hash`
- [ ] Ajouter un endpoint API `GET /api/pipeline/status` qui retourne le statut de fraîcheur de chaque étape
- [ ] Calculer les `config_hash` via un hash des sections pertinentes de `transform.yml`

Cet investissement backend (~2-3h) est le socle pour TOUTES les approches visuelles.

---

## Technical Approach

### Phase 0 : Nettoyage immédiat (~1h)

- [ ] Supprimer le contenu des 3 mockups Labs actuels
- [ ] Supprimer Showcase et TOOLS de la sidebar
- [ ] Déplacer Data Explorer, Config Editor, Plugins, Docs dans la Command Palette
- [ ] Garder `/labs/*` pour les nouveaux prototypes
- [ ] Route catch-all 404

**Fichiers** : `navigationStore.ts`, `App.tsx`, `CommandPalette.tsx`, `NavigationSidebar.tsx`

---

### Phase 0.5 : Sidebar plate (~1h)

Transformer la sidebar actuelle (sections collapsibles avec sous-items) en rail plat.

- [ ] Remplacer les `navigationSections` par un tableau simple de 5-6 items (Home, Données, Groupes, Site, Publication)
- [ ] Supprimer toute la logique `Collapsible` dans `NavigationSidebar.tsx`
- [ ] Chaque item = icône + label (mode full) ou icône seule (mode compact)
- [ ] Highlight de l'item actif basé sur la route (`/sources/*` → Données, `/groups/*` → Groupes, etc.)
- [ ] Footer : Paramètres + Aperçu site (inchangé)

Ce rail plat est le socle pour tous les prototypes.

---

### Phase 1 : Backend fraîcheur (~2-3h)

- [ ] Endpoint `GET /api/pipeline/status` retournant :
  ```json
  {
    "data": {
      "status": "fresh",
      "datasets": [
        {"name": "occurrences", "status": "fresh", "last_imported": "2026-03-10T14:00:00"},
        {"name": "plots", "status": "stale", "last_imported": "2026-03-12T09:00:00"}
      ],
      "references": [...]
    },
    "groups": {
      "status": "stale",
      "items": [
        {"name": "taxon", "status": "fresh", "last_transformed": "2026-03-10T15:00:00"},
        {"name": "plots", "status": "stale", "reason": "source_data_changed"},
        {"name": "communes", "status": "never_run"}
      ]
    },
    "site": {"status": "fresh", "last_exported": "2026-03-10T16:00:00"},
    "publication": {"status": "stale", "last_deployed": "2026-03-08T10:00:00"}
  }
  ```
- [ ] Hook React `usePipelineStatus()` qui consomme cet endpoint
- [ ] Logique de calcul de fraîcheur (comparaison timestamps, config hashes)

---

### Phase 2 : Prototypage (~3-4 sessions)

#### Prototype B : Hub Adaptatif (`/labs/proto-hub`)

- [ ] Page `ProjectHub.tsx` avec 3 états :
  - **Vide** : checklist onboarding
  - **Configuré, tout frais** : 4 cards statut + activité récente
  - **Quelque chose périmé** : bandeau d'alerte + cards avec indicateurs + cascade suggérée
- [ ] Utiliser `usePipelineStatus()` pour déterminer l'état
- [ ] Boutons d'action contextuels : "Tout mettre à jour", "Recalculer 2 groupes", "Rebuilder"
- [ ] Intégrer le rail plat de la Phase 0.5

#### Prototype E : Contextual Actions (`/labs/proto-contextual`)

- [ ] Composant `StalenessBanner.tsx` — bandeau conditionnel en haut de chaque page
- [ ] S'affiche uniquement quand une action est pertinente
- [ ] Variantes par section :
  - Données : "2 groupes utilisent ces données — [▶ Recalculer]"
  - Groupes : "Config modifiée depuis le dernier calcul — [▶ Relancer]"
  - Site : "Groupes recalculés — [▶ Rebuilder le site]"
  - Publication : "Site rebuilded — [▶ Déployer]"
- [ ] Quand tout est à jour : ligne subtile "✅ À jour" avec timestamp

#### Prototype A : Pipeline Rail (`/labs/proto-pipeline`) — si temps disponible

- [ ] Composant `PipelineBar.tsx` — barre horizontale ① → ② → ③ → ④
- [ ] Statut par étape via `usePipelineStatus()`
- [ ] Cliquable : navigue vers la section

---

### Phase 3 : Évaluation (~1 session)

Tester les prototypes sur les 4 flux d'usage réels :

| Flux | Actions | Ce qu'on évalue |
|------|---------|-----------------|
| **1. Premier setup** | Import → configurer un groupe → configurer site → build → deploy | Est-ce que l'utilisateur sait quoi faire ensuite ? |
| **2. Mise à jour données** | Réimport CSV → voir ce qui est périmé → recalculer → rebuild | Est-ce que le périmé est visible ? L'action est-elle claire ? |
| **3. Modification widget** | Changer un widget dans un groupe → relancer ce groupe → rebuild | L'utilisateur sait-il que seul ce groupe doit être relancé ? |
| **4. Édition site seule** | Modifier une page → rebuild → deploy | Pas de recalcul nécessaire — est-ce clair ? |

**Golden Rule test** : montrer l'interface à quelqu'un qui ne connaît pas Niamoto. Comprend-il en 2 minutes ?

---

### Phase 4 : Implémentation finale (~2-3 sessions)

- [ ] Implémenter l'approche retenue (ou hybride B+E) comme navigation principale
- [ ] Remplacer le redirect `/` → `/sources` par `/` → `/home` (si Hub retenu)
- [ ] Supprimer les prototypes Labs et la section Labs
- [ ] Redirects pour les anciennes routes
- [ ] Migration localStorage
- [ ] Enrichir la Command Palette avec les outils déplacés

---

## Acceptance Criteria

- [ ] **Sidebar plate** : 5-6 icônes, **zéro sous-menu**, identique full/compact
- [ ] **Fraîcheur visible** : chaque entité montre si elle est à jour, périmée, ou en erreur
- [ ] **Actions contextuelles** : l'action la plus pertinente est visible au bon moment
- [ ] **Cascade** : quand des données changent, l'interface montre ce qui doit être recalculé
- [ ] **Onboarding** : un projet vide guide l'utilisateur vers sa première action
- [ ] **Golden Rule** : compréhensible en 2 minutes par un non-technique
- [ ] **Cmd+K enrichi** : Data Explorer, Config Editor, Plugins, Docs accessibles
- [ ] **Aucune fonctionnalité perdue**
- [ ] Build frontend réussit, aucune route cassée

---

## Calendrier

```
Phase 0 + 0.5 (Nettoyage + Sidebar plate)    ─── 1 session ──→  Base prête
         │
         ▼
Phase 1 (Backend fraîcheur)                   ─── 1 session ──→  API /pipeline/status
         │
         ▼
Phase 2 (Prototypes B + E)                    ─── 2-3 sessions → Prototypes navigables
         │
         ▼
Phase 3 (Évaluation)                          ─── 1 session ──→  Décision prise
         │
         ▼
Phase 4 (Implémentation finale)               ─── 2-3 sessions → Navigation production
```

**Total estimé** : 7-9 sessions de travail

**Ordre critique** :
1. Phase 0 d'abord (nettoyage, zéro risque)
2. Phase 0.5 et Phase 1 en parallèle (sidebar et backend indépendants)
3. Phase 2 après Phase 1 (les prototypes ont besoin du `usePipelineStatus`)

---

## Dependencies

| Dépendance | Statut |
|------------|--------|
| `cmdk` pour Command Palette | ✅ Existant |
| Zustand stores | ✅ Existant |
| Hooks data (`useDatasets`, `useReferences`, etc.) | ✅ Existant |
| Job store timestamps | ✅ Existant (`job_file_store.py`) |
| `niamoto_metadata_entities.updated_at` | ✅ Existant mais non exploité |
| Endpoint `/api/pipeline/status` | ❌ À créer (Phase 1) |
| Config hash (transform.yml) | ❌ À créer (Phase 1) |

---

## Risk Analysis

| Risque | Probabilité | Mitigation |
|--------|-------------|------------|
| Le tracking de fraîcheur est imprécis (faux positifs "périmé") | Moyenne | Commencer avec les timestamps simples, affiner avec les config hashes |
| Le Hub Dashboard est trop verbeux | Moyenne | Prototype d'abord, itérer sur le contenu des cards |
| "Tout mettre à jour" échoue partiellement | Moyenne | Cascade step-by-step avec feedback par étape (pas un job monolithique) |
| Cmd+K non découvert | Élevée | Indicateur visible + tooltip first-run |
| Le botaniste ne comprend pas "périmé" | Faible | Utiliser un vocabulaire concret : "données modifiées, calculs à refaire" |

---

## References

### Internal
- `docs/10-roadmaps/gui-finalization/00-overview.md` — État des lieux GUI
- `src/niamoto/gui/ui/src/stores/navigationStore.ts` — Sections sidebar actuelles
- `src/niamoto/gui/ui/src/pages/groups/index.tsx:47-84` — GroupsPage avec cards (pattern à généraliser)
- `src/niamoto/gui/ui/src/pages/publish/index.tsx:74-276` — PublishOverview avec status cards
- `src/niamoto/gui/api/services/job_file_store.py` — Job store avec timestamps
- `src/niamoto/core/services/transformer.py` — Transform execution (séquentiel)
- `src/niamoto/core/imports/registry.py` — Entity registry avec `updated_at`

### External (UX Research)
- [Dagster Asset Model & Freshness](https://docs.dagster.io/concepts/assets/software-defined-assets)
- [dbt Source Freshness & Data Health](https://docs.getdbt.com/docs/deploy/source-freshness)
- [Progressive Disclosure — NNGroup](https://www.nngroup.com/articles/progressive-disclosure/)
- [Object-Oriented UX — A List Apart](https://alistapart.com/article/ooux-a-foundation-for-interaction-design/)
- [Hick's Law — Dovetail](https://dovetail.com/ux/hicks-law/)
- [Visibility Drives Engagement — LukeW](https://www.lukew.com/ff/entry.asp?1945)
- [Command-K Bars — Maggie Appleton](https://maggieappleton.com/command-bar)
- [Dagster UI Navigation — GitHub Discussion](https://github.com/dagster-io/dagster/discussions/21370)
- [Navigation UX for SaaS — Pencil & Paper](https://www.pencilandpaper.io/articles/ux-pattern-analysis-navigation)
