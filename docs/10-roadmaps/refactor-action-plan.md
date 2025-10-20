# Plan d'Action - Refactorisation Import Générique

**Version**: 1.0
**Date Création**: 20 janvier 2025
**Instance de Test**: `test-instance/niamoto-nc`
**Document Détaillé**: [refactor-status-2025-01-20.md](./refactor-status-2025-01-20.md)

---

## 🎯 OBJECTIF GLOBAL

Finaliser la migration vers le système d'import générique en:
1. Migrant 27 plugins critiques vers EntityRegistry
2. Construisant un Entity Manager GUI complet
3. Adaptant configs transform/export
4. Documentant le tout

**Statut Actuel**: 14% plugins migrés (7/49), GUI 0%
**Cible**: 100% plugins critiques, GUI fonctionnel
**Timeline**: 3-4 semaines (fin mi-février 2025)

---

## 📅 PLANNING HEBDOMADAIRE

### Semaine 1: PLUGINS (20-26 Jan) 🔴

| Jour | Tâches | Fichiers | Validation |
|------|--------|----------|------------|
| **Lun 20** | Setup + `nested_set.py` | `loaders/nested_set.py` | Test transform.yml OK |
| **Mar 21** | Loaders restants | `spatial.py`, `adjacency_list.py` | Tests unitaires |
| **Mer 22** | Class Objects (5 plugins) | `categories_extractor.py`, `series_extractor.py`, etc. | Tests custom entities |
| **Jeu 23** | Distribution (3 plugins) | `categorical_distribution.py`, etc. | Transform avec dataset custom |
| **Ven 24** | Aggregation (3 plugins) | `top_ranking.py`, `binary_counter.py`, etc. | Coverage >90% |

**Livrable Semaine 1**: ✅ 14 plugins migrés, tests passants

---

### Semaine 2: GUI (27 Jan - 2 Fév) 🔴

| Jour | Tâches | Composants | Validation |
|------|--------|------------|------------|
| **Lun 27** | API Endpoints | `api/routers/entities.py` | Tests API (pytest) |
| **Mar 28** | EntityManagerPage | `pages/entities/index.tsx` | Liste entities affichée |
| **Mer 29** | EntityFormDialog | `components/entities/EntityFormDialog.tsx` | Créer dataset fonctionne |
| **Jeu 30** | HierarchyBuilder | `components/entities/HierarchyBuilderDialog.tsx` | Drag-and-drop levels |
| **Ven 31** | FieldMapping | `components/entities/FieldMappingComponent.tsx` | Auto-détection colonnes |
| **Sam 1** | YAML + Selector | `YamlPreviewComponent.tsx`, `EntitySelector.tsx` | Copy/download YAML |
| **Dim 2** | Integration | Polish, responsive, i18n | Tests E2E (Playwright) |

**Livrable Semaine 2**: ✅ Entity Manager complet, 7 composants React

---

### Semaine 3: CONFIG + DOCS (3-9 Fév) 🟡

| Jour | Tâches | Fichiers | Validation |
|------|--------|----------|------------|
| **Lun 3** | Transform Service | `services/transformer.py` | Registry resolution OK |
| **Mar 4** | Transform Editor GUI | `pages/transform/editor.tsx` | Éditer group avec EntitySelector |
| **Mer 5** | Export Service | `services/exporter.py` | Audit + migration si nécessaire |
| **Jeu 6** | Tests Transform/Export | E2E tests | Pipeline complet fonctionne |
| **Ven 7** | Docs ADR/Roadmap | ADR 0004, roadmap | Status réel documenté |
| **Sam 8** | Guides | Migration, Config, Plugin, GUI | Exemples validés |
| **Dim 9** | Review Docs | Relecture complète | Cohérence, clarté |

**Livrable Semaine 3**: ✅ Transform/Export adaptés, 5 docs créés/mis à jour

---

### Semaine 4: VALIDATION (10-11 Fév) 🟢

| Jour | Tâches | Cible | Validation |
|------|--------|-------|------------|
| **Lun 10** | Tests custom entities + GUI E2E | Tests complets | >90% coverage |
| **Mar 11** | Tests migration + Benchmarks | Script conversion validé | Perf documentée |

**Livrable Semaine 4**: ✅ Release candidate, validation complète

---

## 📋 CHECKLIST QUOTIDIENNE

### Avant de Commencer
- [ ] `cd test-instance/niamoto-nc`
- [ ] `git status` - Vérifier branch `feat/pipeline-editor-unified`
- [ ] `uv run pytest` - Baseline tests OK
- [ ] Consulter tâches du jour (tableau ci-dessus)

### Pendant le Travail
- [ ] Coder changements (plugin/composant du jour)
- [ ] Écrire tests unitaires (coverage >80%)
- [ ] `uv run pytest tests/...` - Valider nouveau code
- [ ] Tester dans instance: `cd test-instance/niamoto-nc && niamoto import/transform/export`
- [ ] Documenter écarts/blockers dans [refactor-status-2025-01-20.md](./refactor-status-2025-01-20.md)

### Fin de Journée
- [ ] Commit changes: `git commit -m "feat: migrate X plugin to EntityRegistry"`
- [ ] Mettre à jour métriques (tableaux ce document)
- [ ] Cocher tâche terminée dans planning
- [ ] Brief rapide: Ce qui marche, blockers, next steps

---

## 🎯 CRITÈRES DE SUCCÈS PAR PHASE

### Phase 1 - Plugins (Semaine 1)
- [ ] 14 plugins migrés (nested_set, spatial, adjacency_list, 5 class_objects, 3 distribution, 3 aggregation)
- [ ] Tests unitaires pour chaque plugin (>80% coverage)
- [ ] Test avec entity custom (ex: "flora" au lieu de "taxonomy")
- [ ] `transform.yml` fonctionne avec nouveau `nested_set.py`
- [ ] Aucune référence hardcodée `taxon_ref`, `plot_ref`, `shape_ref` dans plugins migrés

### Phase 2 - GUI (Semaine 2)
- [ ] 7 composants React fonctionnels (Manager, Form, Hierarchy, Mapping, Preview, Selector, Integration)
- [ ] API endpoints CRUD entities (`/api/entities/*`)
- [ ] Créer dataset via GUI → Import fonctionne
- [ ] Créer reference derived via GUI → Extraction fonctionne
- [ ] EntitySelector utilisable dans toute l'app
- [ ] Tests E2E (Playwright) passants (scénario complet create → import)

### Phase 3 - Transform/Export (Semaine 3)
- [ ] `TransformerService` résout entities via EntityRegistry
- [ ] `transform.yml` migré vers nouvelle syntaxe (`entity:` au lieu de `data:`)
- [ ] Transform Editor GUI avec EntitySelector
- [ ] `ExporterService` audité et adapté si nécessaire
- [ ] Pipeline complet fonctionne: import → transform → export
- [ ] Tests end-to-end avec entities custom

### Phase 4 - Documentation (Semaine 3)
- [ ] ADR 0004 corrigé (status réel plugins)
- [ ] Roadmap mise à jour (progression réelle)
- [ ] Migration Guide créé (v1 → v2 avec script)
- [ ] Entity Configuration Guide créé (syntaxe import.yml complète)
- [ ] Plugin Migration Guide créé (pattern before/after)
- [ ] GUI User Guide créé (walkthroughs avec screenshots)

### Phase 5 - Validation (Semaine 4)
- [ ] Tests custom entities (ex: "habitats", "sites", "observations")
- [ ] Tests GUI E2E (Playwright, 10+ scenarios)
- [ ] Tests migration v1→v2 (script conversion validé)
- [ ] Performance benchmarks (1k, 100k, 1M rows)
- [ ] Coverage globale >90%
- [ ] Release notes rédigées

---

## 📊 MÉTRIQUES DE PROGRESSION

### Plugins (Cible: 27/27 critiques migrés)

**Loaders**: 6/7 → 7/7 ✅
- [x] direct_reference.py
- [x] join_table.py
- [x] stats_loader.py
- [x] nested_set.py ✅ (2025-01-20)
- [x] spatial.py ✅ (2025-01-20)
- [x] adjacency_list.py ✅ (2025-01-20)
- [~] api_taxonomy_enricher.py (optionnel - pas d'interaction DB)

**Transformers - Aggregation**: 1/5 → 5/5
- [x] field_aggregator.py
- [ ] top_ranking.py 🔴 PRIORITÉ 1
- [ ] database_aggregator.py (optionnel)
- [ ] binary_counter.py
- [ ] statistical_summary.py

**Transformers - Extraction**: 3/3 ✅
- [x] direct_attribute.py
- [x] multi_column_extractor.py
- [x] geospatial_extractor.py

**Transformers - Class Objects**: 5/5 ✅
- [x] categories_extractor.py ✅ (2025-01-20)
- [x] series_extractor.py ✅ (2025-01-20)
- [x] binary_aggregator.py ✅ (2025-01-20)
- [x] series_ratio_aggregator.py ✅ (2025-01-20)
- [x] field_aggregator.py (class_objects) ✅ (2025-01-20)

**Transformers - Distribution**: 3/3 ✅
- [x] categorical_distribution.py ✅ (2025-01-20)
- [x] binned_distribution.py ✅ (2025-01-20)
- [x] time_series_analysis.py ✅ (2025-01-20)

**Transformers - Autres**: 0/4+ → 4+/4+
- [ ] niamoto_to_dwc_occurrence.py
- [ ] shape_processor.py
- [ ] Autres (formats, geospatial)

**Total Critique**: **15/27 (56%)** → **27/27 (100%)**

---

### GUI (Cible: 7/7 composants)

- [ ] EntityManagerPage (0% → 100%)
- [ ] EntityFormDialog (0% → 100%)
- [ ] HierarchyBuilderDialog (0% → 100%)
- [ ] FieldMappingComponent (0% → 100%)
- [ ] YamlPreviewComponent (0% → 100%)
- [ ] EntitySelector (0% → 100%)
- [ ] Transform Editor (0% → 100%)

**Total GUI**: **0/7 (0%)** → **7/7 (100%)**

---

### Configuration

- [ ] `transform.yml` migré (⚠️ → ✅)
- [ ] `export.yml` validé (⚠️ → ✅)
- [ ] Transform Editor GUI (❌ → ✅)
- [ ] Export config UI (❌ → ✅ optionnel)

---

### Documentation

- [ ] ADR 0004 mis à jour (⚠️ → ✅)
- [ ] Roadmap corrigée (⚠️ → ✅)
- [ ] Migration Guide (❌ → ✅)
- [ ] Entity Config Guide (❌ → ✅)
- [ ] Plugin Migration Guide (❌ → ✅)
- [ ] GUI User Guide (❌ → ✅)

**Total Docs**: **0/6 (0%)** → **6/6 (100%)**

---

## ⚠️ BLOCKERS & RISQUES

### Blockers Actifs
_Aucun pour le moment_

### Risques à Surveiller

1. **Scope Creep** 🔴
   - Symptôme: Découverte plugins additionnels nécessitant migration
   - Action: Documenter dans "Future Work", pas bloquer release

2. **Tests Insuffisants** 🔴
   - Symptôme: Plugins migrés mais bugs avec entities custom
   - Action: Tests custom entities OBLIGATOIRES avant merge

3. **GUI Complexity** 🟡
   - Symptôme: Interface trop complexe, feedback négatif utilisateurs
   - Action: Itérations UX, wizard simplifié en fallback

---

## 💬 NOTES QUOTIDIENNES

### Lundi 20 Janvier 2025
- [x] Audit complet effectué (plugins, GUI, configs)
- [x] Document status créé ([refactor-status-2025-01-20.md](./refactor-status-2025-01-20.md))
- [x] Plan d'action créé (ce document)
- [ ] **Next**: Migrer `nested_set.py` (PRIORITÉ 1)

---

### Mardi 21 Janvier 2025
_Session de travail complétée_

**Tâches réalisées**:
- [x] Migration de 3 distribution transformers vers EntityRegistry
  - [x] `categorical_distribution.py`
  - [x] `binned_distribution.py`
  - [x] `time_series_analysis.py`
- [x] Tests des plugins migrés (22 tests passent)
- [x] Commit "feat: migrate distribution transformers to EntityRegistry"
- [x] Vérification complète des résultats transform en base de données

**Résultats**:
- Statut: ✅ **Succès complet** - 3/3 distribution transformers migrés et vérifiés
- Tests: 22 tests passent (13 categorical + 9 binned, pas de test pour time_series)
- Vérification DB:
  - ✅ taxons: dbh_distribution, elevation_distribution, rainfall_distribution (binned)
  - ✅ taxons: holdridge_distribution, strata_distribution (categorical)
  - ✅ taxons: phenology_distribution (time_series)
  - ✅ shapes: land_use (categorical pour PPE Nord, PPE Sud, Ultramafique)
  - ⚠️  shapes: Certaines shapes ont NULL car ce sont des entités "type" (catégories), pas de géométries
- Progression: 15/27 plugins critiques migrés (56%)
- Blockers: Aucun

**Notes**:
- Vérification exhaustive de la base de données test-instance/niamoto-nc/db/niamoto.duckdb
- Les 3 shapes géographiques importées (PPE Nord, PPE Sud, Ultramafique) ont des données complètes
- Les plugins migrés fonctionnent correctement avec EntityRegistry
- Le CSV raw_shape_stats.csv contient des données pour beaucoup plus de shapes que celles importées
- Pattern de migration cohérent: EntityRegistry dans __init__, _resolve_table_name() en fallback

---

### Mercredi 22 Janvier 2025
_À remplir en fin de journée_

**Tâches prévues**:
- [ ] Migrer `spatial.py` et `adjacency_list.py`
- [ ] Tests loaders

**Résultats**:
- Statut:
- Blockers:
- Notes:

---

### Jeudi 23 Janvier 2025
_À remplir en fin de journée_

**Tâches prévues**:
- [ ] Migrer 5 class_objects transformers

**Résultats**:
- Statut:
- Blockers:
- Notes:

---

### Vendredi 24 Janvier 2025
_À remplir en fin de journée_

**Tâches prévues**:
- [ ] Migrer 3 distribution transformers
- [ ] Review semaine 1

**Résultats**:
- Statut:
- Blockers:
- Notes:

---

## 🔗 LIENS RAPIDES

### Documents
- [Status Détaillé](./refactor-status-2025-01-20.md) - Analyse complète avec détails techniques
- [ADR 0004](../09-architecture/adr/0004-generic-import-system.md) - Architecture décision record
- [Roadmap](./generic-import-refactor-roadmap.md) - Roadmap originale (à mettre à jour)

### Instance de Test
- **Chemin**: `/Users/julienbarbe/Dev/Niamoto/Niamoto/test-instance/niamoto-nc`
- **Import Config**: `config/import.yml` (v2 fonctionnel)
- **Transform Config**: `config/transform.yml` (à migrer)
- **Export Config**: `config/export.yml` (à valider)
- **Database**: `db/niamoto.duckdb`

### Commandes Utiles

```bash
# Tests
uv run pytest                           # Tous tests
uv run pytest tests/core/plugins/      # Tests plugins
uv run pytest -v -k "test_nested_set"  # Test spécifique

# Import/Transform/Export
cd test-instance/niamoto-nc
niamoto import                          # Importer entities
niamoto transform                       # Générer stats
niamoto export                          # Exporter site

# Database queries
uv run python scripts/query_db.py --list-tables
uv run python scripts/query_db.py "SELECT * FROM entity_taxons LIMIT 5"

# GUI dev
cd src/niamoto/gui/ui
npm run dev                            # Dev server (port 5173)
npm run build                          # Build production
```

---

## 📈 DASHBOARD VISUEL

```
PROGRESSION GLOBALE: ████████░░░░░░░░░░ 40%

PHASES:
✅ Core Backend       ████████████████████ 100%
🟡 Plugins Critiques  █████░░░░░░░░░░░░░░░  26%
❌ GUI Frontend       ░░░░░░░░░░░░░░░░░░░░   0%
⚠️  Transform/Export  █████████░░░░░░░░░░░  50%
❌ Documentation      ░░░░░░░░░░░░░░░░░░░░   0%

TIMELINE: [Semaine 1] ────> [Semaine 2] ────> [Semaine 3] ────> [Semaine 4]
          Plugins 🔴       GUI 🔴              Config/Docs 🟡    Tests 🟢
          20-26 Jan        27 Jan-2 Fév        3-9 Fév           10-11 Fév
```

---

**Maintenu par**: Julien Barbe
**Dernière mise à jour**: 20 janvier 2025, 15:30
**Prochaine review**: 24 janvier 2025 (fin Semaine 1)
