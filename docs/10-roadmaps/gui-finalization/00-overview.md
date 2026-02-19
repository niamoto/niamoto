# Niamoto GUI - Etat des Lieux et Axes d'Amelioration

**Date** : 2026-02-05
**Branche** : `feature/enhanced-user-experience`

## Resume executif

Le GUI Niamoto est **largement fonctionnel**. Le pipeline complet Import → Transform → Export → Deploy est operationnel via l'interface. Ce document dresse un inventaire precis de l'existant et identifie les axes d'amelioration restants pour un nouveau plan d'implementation.

---

## 1. Matrice de Fonctionnalites — Etat Actuel

### 1.1 Frontend (~43k lignes, ~60 pages .tsx)

| Domaine | Composants | Etat | Notes |
|---------|-----------|------|-------|
| **Import** | ImportWizard, FileUploadZone, ImportProgress | ✅ Complet | Upload, auto-config, progression polling |
| **Enrichissement** | ApiEnrichmentConfig (~600 lignes) | ✅ Complet | Presets GBIF/Endemia/WFO, custom, start/pause/resume |
| **Sources** | SourcesList, AddSourceDialog, DatasetConfigForm | ✅ Complet | Config datasets et references |
| **Groups/Transform** | GroupPanel (3 tabs), ContentTab, WidgetGallery | ✅ Complet | Suggestions, drag-drop, JsonSchemaForm |
| **Widget Detail** | WidgetDetailPanel (Preview/Params/YAML) | ✅ Complet | Formulaires Pydantic, preview iframe |
| **Site Builder** | SiteBuilder (1453 lignes), tree view, editors | ✅ Complet | Markdown, navigation, templates, multilingue |
| **Publish** | PublishOverview, PublishBuild, PublishDeploy, History | ✅ Complet | Zustand store persistant, progression |
| **Outils** | DataExplorer, LivePreview, ConfigEditor, Plugins | ✅ Complet | Exploration donnees, preview site, editeur YAML |
| **Formulaires** | JsonSchemaForm + 20 types de champs | ✅ Complet | entity-select, layer-select, tags, key-value, etc. |
| **Layout** | MainLayout, TopBar, CommandPalette, BreadcrumbNav | ✅ Complet | Sidebar, Cmd+K, theme clair/sombre |
| **i18n** | LanguageContext, TranslationKeys | ✅ Complet | FR/EN via i18next |
| **Desktop** | WelcomeScreen, ProjectSwitcher, file pickers | ✅ Complet | Integration Tauri |
| **Dashboard post-import** | ImportDashboard, DataCompletenessView, SpatialDistributionMap | ⚠️ Partiel | Composants existent, integration a verifier |
| **Index generator editor** | IndexTab dans GroupPanel | ⚠️ Partiel | Lecture OK, edition a verifier |
| **Notifications** | sonner (toasts ad-hoc) | ⚠️ Basique | Pas de systeme centralise |

### 1.2 Backend (19 routers, tous fonctionnels)

| Router | Endpoints | Etat |
|--------|----------|------|
| **imports.py** | execute/all, execute/reference, jobs, status | ✅ Background jobs + polling |
| **transform.py** | execute, status, config, metrics, sources | ✅ Background jobs + polling |
| **export.py** | execute, status, config, metrics, execute-cli | ✅ Background jobs + polling |
| **enrichment.py** | start, pause, resume, cancel, preview, results | ✅ Complet (per-reference scope) |
| **deploy.py** | cloudflare/deploy (SSE), cloudflare/check | ⚠️ Cloudflare uniquement |
| **config.py** | project, references, datasets, validate, save | ✅ YAML read/write complet |
| **recipes.py** | sources, save, validate, transformer-schema | ✅ Config widgets |
| **site.py** | config, groups, templates, files | ✅ Site complet |
| **layers.py** | list, details (raster/vector metadata) | ✅ Recent (Phase 2.5) |
| **plugins.py** | list, details, categories, compatibility | ✅ Registry complet |
| **database.py** | schema, preview, stats, query | ✅ Introspection |
| **data_explorer.py** | tables, query, columns, enrichment/preview | ✅ Explorer |
| **stats.py** | summary, completeness, spatial, geo-coverage | ✅ Stats import |
| **smart_config.py** | upload-files, analyze-file, auto-configure | ✅ Auto-detection |
| **files.py** | analyze, browse, exports/list/read/structure | ✅ Fichiers |
| **layout.py** | get/put layout, preview | ✅ Persistance layout |
| **templates.py** | suggestions, generate-config, preview | ✅ Templates |
| **transformer_suggestions.py** | suggestions par entite | ✅ Suggestions intelligentes |
| **health.py** | health, runtime-mode, reload-project | ✅ Diagnostics |
| **sources.py** | upload, list, save par reference | ✅ Sources |

### 1.3 Services Core

| Service | Etat | Notes |
|---------|------|-------|
| **importer.py** | ✅ | 3 phases (datasets → derived refs → direct refs) |
| **transformer.py** | ✅ | Plugin cascade, progress callback |
| **exporter.py** | ✅ | Multi-target, stats collection |
| **Job management** | ⚠️ In-memory | Dicts locaux, perdus au redemarrage |
| **SSE/Streaming** | ⚠️ Deploy seul | Polling pour import/transform/export |

---

## 2. Ce qui Manque Reellement

### 2.1 Lacunes Techniques (Infrastructure)

| # | Lacune | Impact | Effort |
|---|--------|--------|--------|
| T1 | **Jobs non persistants** : redemarrage = perte de l'etat | Fiabilite | Moyen |
| T2 | **Pas de SSE unifie** : polling partout sauf deploy | UX (delai feedback) | Moyen |
| T3 | **Deploy limite a Cloudflare** : GitHub Pages, Netlify, SSH non wires | Flexibilite | Moyen |

### 2.2 Lacunes UX (Experience utilisateur)

| # | Lacune | Impact | Effort |
|---|--------|--------|--------|
| U1 | **Notifications ad-hoc** : pas de centre de notifications | UX coherence | Faible |
| U2 | **Dashboard post-import incomplet** : composants existent mais integration partielle | Qualite donnees | Moyen |
| U3 | **Index generator** : lecture OK, edition limitee (filtres, display_fields) | Config site | Moyen |
| U4 | **Pas de preview globale du site** avant build | Confiance utilisateur | Moyen |

### 2.3 Lacunes Config/Simplification

| # | Lacune | Impact | Effort |
|---|--------|--------|--------|
| C1 | **field_aggregator verbeux** : 3 lignes par champ quand source=field=target | DX config | Faible |
| C2 | **stats_loader** : 8 lignes de config pour un pattern previsible | DX config | Moyen |
| C3 | **statistical_summary** : 88 lignes pour 8 gauges quasi-identiques | DX config | Moyen |
| C4 | **Couleurs dupliquees** dans export.yml (13 hex, 4 uniques) | Maintenance | Faible |

*Detail dans `03-simplifications-config.md`*

### 2.4 Lacunes Tests

| # | Lacune | Impact | Effort |
|---|--------|--------|--------|
| X1 | **Pas de tests e2e GUI** : le frontend n'a pas de tests | Regression | Eleve |
| X2 | **Datasets synthetiques** : pas de fixtures edge cases | Couverture | Moyen |
| X3 | **Garde-fous import** : pas de limites sur nulls, taille, doublons | Robustesse | Faible |

---

## 3. Routes Frontend — Cartographie Complete

```
/                          → redirect /sources
/sources                   → SourcesPage (liste entites importees)
/sources/import            → ImportPage (wizard import)
/sources/dataset/:name     → DatasetPage (detail dataset)
/sources/reference/:name   → ReferencePage (detail reference)
/groups                    → GroupsPage (liste groupes)
/groups/:name              → GroupDetailPage → GroupPanel (Sources|Content|Index)
/site                      → redirect /site/pages
/site/pages                → SitePagesPage (SiteBuilder)
/site/navigation           → SiteNavigationPage
/site/general              → SiteGeneralPage
/site/appearance           → SiteAppearancePage
/tools/explorer            → DataExplorer
/tools/preview             → LivePreview
/tools/settings            → Settings
/tools/plugins             → Plugins
/tools/docs                → ApiDocs
/tools/config-editor       → ConfigEditor
/publish                   → PublishOverview
/publish/build             → PublishBuild
/publish/deploy            → PublishDeploy
/publish/history           → PublishHistory
/showcase                  → Showcase (demo composants)
/labs/*                    → Prototypes UX (non production)
```

---

## 4. Flux Utilisateur Principaux

### A. Import
```
SourcesPage → ImportWizard
  ├─ FileUploadZone (drag & drop)
  ├─ Auto-configuration (smart_config)
  ├─ Review config (tabs Config/YAML)
  ├─ ImportProgress (polling job status)
  └─ [Optionnel] Enrichissement API (start/pause/resume)
```

### B. Configuration Widgets
```
GroupsPage → GroupPanel
  ├─ SourcesTab (config sources donnees)
  ├─ ContentTab (layout hybride)
  │   ├─ WidgetListPanel (gauche: liste + recherche)
  │   ├─ WidgetDetailPanel (droite: Preview|Params|YAML)
  │   ├─ AddWidgetModal (Suggestions|Combined|Custom)
  │   └─ LayoutOverview (grille drag-drop si rien selectionne)
  └─ IndexTab (config index_generator)
```

### C. Site Builder
```
SitePanel → SiteBuilder (tree | editor | preview)
  ├─ SiteTreeView (arborescence)
  ├─ Editeur contextuel (Markdown, Theme, Navigation, etc.)
  └─ Preview panel
```

### D. Publish
```
PublishOverview → PublishBuild → PublishDeploy
  ├─ Build: executeExportAndWait (progress callback)
  ├─ Deploy: Cloudflare Pages (SSE streaming)
  └─ History: liste builds/deploys (Zustand persistant)
```

---

## 5. Suggestions pour le Plan d'Implementation

### Tier 1 — Quick Wins (effort faible, impact visible)

| Ref | Action | Justification |
|-----|--------|---------------|
| U1 | **Notifications centralisees** : NotificationContext + NotificationCenter | Prerequis UX pour toutes les operations |
| C1 | **Raccourci field_aggregator** : accepter string quand field=target | -45 lignes YAML, retrocompatible |
| X3 | **Garde-fous import** : limites nulls, taille fichier, unicite ID | Erreurs silencieuses actuellement |

### Tier 2 — Ameliorations Structurantes (effort moyen)

| Ref | Action | Justification |
|-----|--------|---------------|
| T1 | **Jobs persistants** : table SQLite `jobs` + API `/jobs` | Fiabilite, prerequis pour reprise |
| T3 | **Deploy multi-plateforme** : wirer GitHub Pages + SSH | Les pages Publish existent deja |
| U2 | **Dashboard post-import** : integrer les composants existants | Composants la, juste a assembler |
| C2+C3 | **stats_loader convention + batch statistical_summary** | -82 lignes config, GUI seul pour C3 |

### Tier 3 — Finitions (effort eleve, important pour la polish)

| Ref | Action | Justification |
|-----|--------|---------------|
| T2 | **SSE unifie** : remplacer polling par streaming sur import/transform/export | UX temps reel |
| U3 | **Index generator editor** : formulaire edition filtres et display_fields | Config site complete |
| U4 | **Preview site globale** : iframe ou build partiel | Confiance avant deploy |
| X1 | **Tests e2e frontend** : Playwright ou Cypress sur les flux principaux | Non-regression |
| X2 | **Datasets synthetiques** : fixtures edge cases avec correlations ecologiques | Robustesse |

### Tier 4 — Vision Long Terme

| Action | Justification |
|--------|---------------|
| Import/export de configurations entre projets | Reutilisabilite |
| Reprise des traitements interrompus (checkpoints) | Robustesse gros datasets |
| Generalisation enrichissement aux plots/shapes | Completude |
| Templates Jinja editables via GUI | Personnalisation avancee |

---

## 6. Stack et Architecture

### Frontend
- **React 18** + TypeScript
- **Tailwind CSS** + shadcn/ui
- **Zustand** (3 stores: publish, navigation, theme)
- **React Query** (TanStack) pour le fetching
- **i18next** pour l'internationalisation
- **@dnd-kit** pour le drag & drop
- **Tauri 2** pour le desktop

### Backend
- **FastAPI** (19 routers)
- **BackgroundTasks** pour les jobs
- **Pydantic v2** pour la validation
- **DuckDB** pour les donnees
- **Polling HTTP** pour le suivi (SSE sur deploy uniquement)

### Decisions Architecturales Actees

| Decision | Choix |
|----------|-------|
| State management | Zustand (persist localStorage) |
| Formulaires plugins | JsonSchemaForm depuis Pydantic `param_schema` |
| Job tracking | In-memory dicts (a migrer vers SQLite) |
| Streaming | SSE sur deploy, polling ailleurs |
| Config persistence | YAML read/write via API |
| Plugin discovery | Registry + Loader avec cascade (system → user → project) |

---

## 7. Fichiers de Reference

| Document | Contenu |
|----------|---------|
| `01-phase-import.md` | Specs formulaires import, enrichissement, dashboard validation |
| `02-phase-transform-export.md` | Architecture widgets, suggestions, formulaires dynamiques |
| `03-simplifications-config.md` | 6 axes de simplification config (-127 lignes YAML) |
| `docs/06-gui/guide-transform-widgets.md` | Guide utilisateur widgets transform |
| `docs/06-gui/reference-plugins-transform.md` | Reference plugins avec params et YAML |
| `docs/04-plugin-development/creating-transformers.md` | Guide dev : creer un plugin avec config_model |

---

## 8. Questions Ouvertes

1. **Priorite deploy** : Faut-il wirer les 4 plateformes ou se concentrer sur Cloudflare + SSH ?
2. **Tests frontend** : Playwright (e2e navigateur) ou Vitest (composants unitaires) en priorite ?
3. **Dashboard post-import** : Les composants existants sont-ils suffisants ou faut-il revoir ?
4. **Offline** : Le desktop app doit-il fonctionner sans connexion internet ?
