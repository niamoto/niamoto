---
title: "refactor: Rename Groups module to Collections"
type: refactor
date: 2026-03-31
brainstorm: docs/brainstorms/2026-03-31-collections-module-simplification-brainstorm.md
---

# refactor: Rename Groups module to Collections

## Overview

Refonte UX du module "Groupes" en "Collections" dans le GUI Niamoto. Renommage cosmétique GUI uniquement — aucun changement backend, YAML, ou API. L'objectif : un botaniste de terrain comprend le module en 2 minutes.

**Scope** : ~42 fichiers à modifier, ~6 fichiers à renommer, 1 répertoire à renommer. Trois phases séquentielles.

## Brainstorm Reference

Toutes les décisions UX sont documentées dans le [brainstorm](../brainstorms/2026-03-31-collections-module-simplification-brainstorm.md). Résumé :

| Décision | Choix |
|----------|-------|
| Nom module | Collections |
| Vocabulaire | Collection → Fiche → Blocs |
| Onglets | 4→3 : Blocs / Liste / Export |
| Sources aux. | Dialog dans onglet Blocs |
| Vue d'ensemble | Cartes enrichies (compteurs, statut, aperçu, raccourcis) |
| Routes URL | Inchangées (`/groups`) |
| Navigation | Sidebar légère pour switcher |
| API Settings | Bouton dans onglet Export |

## Règles critiques

### NE PAS MODIFIER (contrat API backend)

- `PipelineStatus.groups` / `StageStatus` — champs réponse API
- `GroupInfo`, `GroupsResponse` — interfaces API dans `useSiteConfig.ts`
- `ApiExportGroupConfig.group_by` — champ API
- URLs API : `/api/config/references`, `/api/site/groups`, etc.
- Paramètres YAML : `group_by`, `widgets_data`, `sources`
- `ExportGroupConfig.groups` dans `useWidgetConfig.ts`

### StalenessBanner — mapping nécessaire

Le composant utilise `pipeline[stage]` comme lookup dynamique. Le backend retourne `{ data, groups, site, publication }`. Garder `stage="groups"` en interne et ne changer que les labels affichés.

## Phase A — Renommage labels + onglets 4→3

Livre l'essentiel de la valeur UX. Commit atomique.

### A1. Renommer le répertoire feature

- [ ] `features/groups/` → `features/collections/`

### A2. Renommer les fichiers composants (dans features/collections/)

- [ ] `GroupsModule.tsx` → `CollectionsModule.tsx`
- [ ] `GroupsTree.tsx` → `CollectionsTree.tsx`
- [ ] `GroupPanel.tsx` → `CollectionPanel.tsx`
- [ ] `index.ts` — mettre à jour l'export : `CollectionsModule`

### A3. Renommer les exports et types internes

Dans `CollectionsModule.tsx` :
- [ ] `GroupsModule` → `CollectionsModule`
- [ ] i18n keys `groups.*` → `collections.*` (labels user-facing)
- [ ] Breadcrumb path label : "Groupes" → "Collections"
- [ ] `StalenessBanner stage="groups"` — garder tel quel (backend mapping)

Dans `CollectionsTree.tsx` :
- [ ] `GroupsSelection` → `CollectionsSelection`
- [ ] `type: 'group'` → `type: 'collection'`
- [ ] `GroupsTree` → `CollectionsTree`
- [ ] Accordion value `'groups'` → `'collections'`
- [ ] i18n keys `groups.overview`, `groups.title`, etc.

Dans `CollectionPanel.tsx` :
- [ ] `GroupPanel` → `CollectionPanel`
- [ ] `GroupPanelProps` → `CollectionPanelProps`
- [ ] Restructurer les onglets : supprimer Sources, renommer Content→Blocs, Index→Liste, API→Export
- [ ] i18n keys `groupPanel.*` → `collectionPanel.*`

### A4. Mettre à jour les imports dans les sous-composants

Tous les fichiers dans `features/collections/components/` et `features/collections/hooks/` :
- [ ] `api/ApiExportsTab.tsx` — import paths `@/features/collections/...`
- [ ] `api/ApiSettingsPanel.tsx` — import paths + navigation `/groups/...` (garder car route inchangée)
- [ ] `api/AddExportWizard.tsx` — import paths
- [ ] `api/ExportCard.tsx` — import paths
- [ ] `api/ApiFieldMappingsEditor.tsx` — import paths
- [ ] `api/DwcMappingEditor.tsx` — import paths
- [ ] `sources/SourcesList.tsx` — import paths
- [ ] `sources/AddSourceDialog.tsx` — import paths
- [ ] `hooks/useSources.ts` — JSDoc comments seulement
- [ ] `hooks/useApiExportConfigs.ts` — import paths si nécessaire

### A5. App routing & navigation

Dans `App.tsx` :
- [ ] Lazy import `CollectionsModule` depuis `@/features/collections`
- [ ] Route `path="groups/*"` — **garder** (routes inchangées par décision)
- [ ] Composant `<CollectionsModule />` dans la route

Dans `navigationStore.ts` :
- [ ] `id: 'groups'` — garder (clé interne)
- [ ] `labelKey: 'sidebar.nav.collections'`
- [ ] `fallbackLabel: 'Collections'`
- [ ] `path: '/groups'` — garder
- [ ] `matchPrefix: '/groups'` — garder
- [ ] Breadcrumb mapping `'/groups': 'Collections'`

Dans `CommandPalette.tsx` :
- [ ] `navIconMap` : clé `groups` → `collections` (si liée au labelKey)

### A6. Pipeline / StalenessBanner

Dans `StalenessBanner.tsx` :
- [ ] Garder `PipelineStage = 'data' | 'groups' | 'site' | 'publication'` — inchangé
- [ ] Changer seulement les labels i18n : `pipeline.groups_stale` → texte "Collections à recalculer"
- [ ] Changer les fallback strings : "groups need recomputing" → "collections need recomputing"

### A7. Dashboard

Dans `DashboardView.tsx` :
- [ ] Import `CollectionsSummary` (au lieu de `GroupsSummary`)
- [ ] Navigation `"/groups"` — garder (route inchangée)
- [ ] i18n key `sidebar.nav.groups` → `sidebar.nav.collections`
- [ ] `<CollectionsSummary>` au lieu de `<GroupsSummary>`

Dans `GroupsSummary.tsx` → `CollectionsSummary.tsx` :
- [ ] Renommer fichier et export
- [ ] i18n keys `pipeline.summary.groups_ratio` → `pipeline.summary.collections_ratio`

Dans `OnboardingView.tsx` :
- [ ] Texte "Configure groups" → "Configure collections"
- [ ] Navigation `"/groups"` — garder (route inchangée)

### A8. Import / Data module

Dans `DataModule.tsx` :
- [ ] Navigation `'/groups'` → garder (route inchangée)
- [ ] Props `onOpenGroups`, `onOpenGroup` — renommer en `onOpenCollections`, `onOpenCollection`

Dans `ImportDashboard.tsx` :
- [ ] `DashboardGroup` → `DashboardCollection`
- [ ] `getGroupIcon` → `getCollectionIcon`
- [ ] `getGroupStatus` → `getCollectionStatus`
- [ ] `CompactGroupOverviewItem` → `CompactCollectionOverviewItem`
- [ ] Props `onOpenGroups` → `onOpenCollections`, `onOpenGroup` → `onOpenCollection`
- [ ] i18n keys : `dashboard.groupOverview.*` → `dashboard.collectionOverview.*`
- [ ] i18n keys : `dashboard.actions.openGroup` → `dashboard.actions.openCollection`
- [ ] Variables `aggregationGroups` → `aggregationCollections`, etc.

Dans `AggregationGroupCard.tsx` → garder le nom de fichier (ou renommer en `AggregationCollectionCard.tsx`) :
- [ ] `AggregationGroupCardProps` → `AggregationCollectionCardProps`
- [ ] Export `AggregationGroupCard` → `AggregationCollectionCard`
- [ ] Props `onOpenGroup` → `onOpenCollection`

### A9. Site module (labels user-facing uniquement)

Dans `SiteBuilder.tsx` :
- [ ] Accordion value `'groups'` → `'collections'`
- [ ] i18n key `tree.groups` → `tree.collections`
- [ ] Les props `groups: GroupInfo[]` — **garder** (interface API)

Dans `SiteTreeView.tsx` :
- [ ] Commentaires "Group pages" → "Collection pages"
- [ ] Les props `groups` — **garder** (interface API)

Les autres fichiers site (`GroupPageViewer.tsx`, `FooterSectionsEditor.tsx`, `NavigationBuilder.tsx`) : pas de renommage car ils manipulent des données API `GroupInfo`.

### A10. i18n — 10 fichiers

#### `en/common.json` et `fr/common.json`
- [ ] `sidebar.nav.groups` → `sidebar.nav.collections` (valeur : "Collections")
- [ ] `pipeline.groups_stale` → `pipeline.collections_stale`
- [ ] `pipeline.groups_stale_count` → `pipeline.collections_stale_count`
- [ ] `pipeline.groups_fresh` → `pipeline.collections_fresh`
- [ ] `pipeline.data_stale` — texte : "groups" → "collections"
- [ ] `pipeline.publication_stale` — texte : "Groups" → "Collections"
- [ ] `pipeline.action_transform` — texte : "groups" → "collections"
- [ ] `pipeline.summary.groups_ratio` → `pipeline.summary.collections_ratio`
- [ ] `pipeline.summary.groups_stale_ratio` → `pipeline.summary.collections_stale_ratio`
- [ ] `pipeline.onboarding.step2` — texte : "groups" → "collections"

#### `en/sources.json` et `fr/sources.json`
- [ ] Section `"groups"` → `"collections"` (clé + tous les sous-labels)
- [ ] `groups.title` → `collections.title` (valeur : "Collections")
- [ ] `groups.noGroups` → `collections.noCollections`
- [ ] `groups.noGroupsHint` → `collections.noCollectionsHint`
- [ ] `groups.notFound` → `collections.notFound`
- [ ] `groups.backToGroups` → `collections.backToCollections`
- [ ] Section `"groupPanel"` → `"collectionPanel"` (toutes les clés dedans)
- [ ] `groupPanel.tabs.sources` — supprimer ou garder pour le dialog
- [ ] `groupPanel.tabs.content` → `collectionPanel.tabs.blocks` (valeur : "Blocs" / "Blocks")
- [ ] `groupPanel.tabs.index` → `collectionPanel.tabs.list` (valeur : "Liste" / "List")
- [ ] `groupPanel.tabs.api` → `collectionPanel.tabs.export` (valeur : "Export")
- [ ] Section `"dashboard"` — clés `aggregationGroupsTitle`, `groupOverview.*`, `openGroup`, `openGroups` → renommer
- [ ] Section `"groupStatus"` → `"collectionStatus"`
- [ ] Textes contenant "group(s)" / "groupe(s)" → "collection(s)"

#### `en/site.json` et `fr/site.json`
- [ ] Section `"groups"` → `"collections"`
- [ ] Clés `groupPages`, `groupDetailPage`, `groupViewer`, `groupIndexPreview` → renommer
- [ ] Textes user-facing contenant "group" → "collection"

#### `en/indexConfig.json` et `fr/indexConfig.json`
- [ ] `groupDescription` → `collectionDescription`
- [ ] Textes "group" → "collection"

#### `en/publish.json` et `fr/publish.json`
- [ ] Template `{{group}}` — **garder** (variable backend)
- [ ] Textes user-facing autour → adapter si nécessaire

### A11. Tests et validation

- [ ] `pnpm build` — vérifier que le build compile sans erreur
- [ ] Vérifier navigation sidebar → Collections
- [ ] Vérifier les 3 onglets (Blocs / Liste / Export) dans une collection
- [ ] Vérifier Dashboard : labels "Collections" corrects
- [ ] Vérifier StalenessBanner : messages corrects
- [ ] Vérifier Import Dashboard : liens vers collections fonctionnels

## Phase B — Vue d'ensemble enrichie

Après Phase A. Commit séparé.

### B1. Nouveau composant `CollectionsOverview.tsx`

Remplace la grille de cartes simple par des cartes enrichies :

- [ ] Créer `features/collections/components/CollectionsOverview.tsx`
- [ ] Pour chaque collection, afficher :
  - Nom + kind badge + nombre d'entités
  - Compteurs : blocs configurés, fiches, exports
  - Statut fraîcheur (vert/orange) via `usePipelineStatus`
  - Aperçu miniature : badges/icônes des types de blocs configurés
  - Date dernier calcul
  - Boutons raccourcis : Blocs / Liste / Export

### B2. Hooks pour données enrichies

- [ ] Enrichir les données existantes : `usePipelineStatus` fournit déjà le statut par groupe
- [ ] Ajouter un appel `useConfiguredWidgets(name)` par collection pour le compteur de blocs
- [ ] Combiner dans un hook `useCollectionSummary(name)` ou inline dans le composant

### B3. i18n pour la vue d'ensemble

- [ ] Ajouter les clés pour les labels : "blocs", "fiches", "exports", "À jour", "À recalculer", "Dernier calcul"
- [ ] `en/sources.json` et `fr/sources.json` — section `collections.overview.*`

### B4. Intégrer dans CollectionsModule

- [ ] Remplacer la vue grille existante (quand aucune collection sélectionnée) par `CollectionsOverview`
- [ ] Les raccourcis sur les cartes naviguent vers `/groups/:name` avec l'onglet approprié

### B5. Tests

- [ ] Build compile
- [ ] Vue d'ensemble affiche les cartes avec toutes les données
- [ ] Raccourcis naviguent correctement vers les onglets

## Phase C — Fusion Sources dans Blocs

Après Phase B. Commit séparé.

### C1. Dialog Sources

- [ ] Créer `features/collections/components/sources/SourcesDialog.tsx`
- [ ] Wrapper autour du contenu existant de `SourcesList` + `AddSourceDialog`
- [ ] Sheet/Dialog overlay déclenché par un bouton discret

### C2. Intégrer dans l'onglet Blocs

- [ ] Dans `CollectionPanel.tsx`, ajouter un bouton "Sources" dans le header de l'onglet Blocs
- [ ] Le bouton ouvre `SourcesDialog`
- [ ] Supprimer l'onglet Sources de la liste des tabs

### C3. Info source primaire dans le header

- [ ] Afficher l'info source primaire (read-only) dans le header de la collection
- [ ] À côté du kind badge et du nombre d'entités : "via nested_set depuis occurrences"

### C4. Bouton API Settings dans Export

- [ ] Dans l'onglet Export (`ApiExportsTab.tsx`), ajouter un bouton "Réglages globaux"
- [ ] Le bouton navigue vers `/groups/api-settings` (route existante)
- [ ] Retirer le lien API Settings du footer de la sidebar `CollectionsTree`

### C5. Tests

- [ ] Build compile
- [ ] Onglet Blocs affiche le bouton Sources
- [ ] Dialog Sources s'ouvre et permet d'ajouter/supprimer des CSV
- [ ] Onglet Export affiche le bouton Réglages globaux
- [ ] 3 onglets fonctionnels : Blocs / Liste / Export

## Fichiers impactés — inventaire complet

### À renommer

| Ancien | Nouveau |
|--------|---------|
| `features/groups/` | `features/collections/` |
| `GroupsModule.tsx` | `CollectionsModule.tsx` |
| `GroupsTree.tsx` | `CollectionsTree.tsx` |
| `GroupPanel.tsx` | `CollectionPanel.tsx` |
| `dashboard/summaries/GroupsSummary.tsx` | `CollectionsSummary.tsx` |
| `import/dashboard/AggregationGroupCard.tsx` | `AggregationCollectionCard.tsx` (optionnel) |

### À modifier (labels/imports)

| Fichier | Type de changement |
|---------|-------------------|
| `app/App.tsx` | Import path + composant |
| `stores/navigationStore.ts` | Labels sidebar |
| `components/layout/CommandPalette.tsx` | Icon map key |
| `components/pipeline/StalenessBanner.tsx` | Labels i18n seulement |
| `features/dashboard/DashboardView.tsx` | Import + labels |
| `features/dashboard/OnboardingView.tsx` | Labels |
| `features/import/module/DataModule.tsx` | Props + navigation |
| `features/import/dashboard/ImportDashboard.tsx` | Types + props + labels |
| `features/site/components/SiteBuilder.tsx` | Accordion value + labels |
| `features/site/components/SiteTreeView.tsx` | Commentaires |
| `i18n/locales/en/common.json` | Clés + valeurs |
| `i18n/locales/fr/common.json` | Clés + valeurs |
| `i18n/locales/en/sources.json` | Clés + valeurs |
| `i18n/locales/fr/sources.json` | Clés + valeurs |
| `i18n/locales/en/site.json` | Clés + valeurs |
| `i18n/locales/fr/site.json` | Clés + valeurs |
| `i18n/locales/en/indexConfig.json` | Clés + valeurs |
| `i18n/locales/fr/indexConfig.json` | Clés + valeurs |
| `i18n/locales/en/publish.json` | Évaluer |
| `i18n/locales/fr/publish.json` | Évaluer |
| ~12 fichiers dans `features/collections/` | Import paths internes |

### NE PAS MODIFIER

| Fichier | Raison |
|---------|--------|
| `hooks/usePipelineStatus.ts` | Interface API backend |
| `shared/hooks/useSiteConfig.ts` | Interface API backend |
| `components/widgets/*.ts` | Concept "group" générique (semantic groups) |
| `components/ui/toggle-group.tsx` | Composant shadcn |
| `components/ui/radio-group.tsx` | Composant shadcn |
| Backend Python (`src/niamoto/core/`, `src/niamoto/gui/api/`) | Hors scope |

## Risques et mitigations

| Risque | Mitigation |
|--------|-----------|
| Import path cassé après rename | `pnpm build` après chaque phase |
| i18n key manquante → texte brut affiché | Grep exhaustif `groups` dans les JSON i18n |
| Confusion `groups` API vs `collections` GUI | Règle claire : ne jamais toucher aux interfaces API |
| StalenessBanner cassé | Garder `stage="groups"` en interne, ne changer que les labels |

## Références

- Brainstorm : `docs/brainstorms/2026-03-31-collections-module-simplification-brainstorm.md`
- Frontend architecture : `docs/plans/2026-03-25-refactor-frontend-feature-architecture-plan.md`
- Sidebar layout : `docs/plans/2026-03-13-feat-sidebar-layout-publish-groups-data-plan.md`
- Navigation simplification : `docs/plans/2026-03-11-refactor-gui-navigation-simplification-plan.md`
