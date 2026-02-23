---
title: "feat: Intégration config shapes NC → test instance pour workflow complet"
type: feat
date: 2026-02-23
---

# Intégration de la configuration shapes complète dans l'instance test

## Overview

L'instance test (`niamoto-test`) a la structure shapes en place (import configuré, sources transform définies) mais **aucun widget de transformation ni d'export** pour les shapes. L'instance de référence NC (`niamoto-nc`) possède une configuration shapes complète et opérationnelle avec 12 widgets transform + 13 widgets export (12 widgets + 1 nav).

L'objectif est d'adapter et copier la configuration NC vers l'instance test pour débloquer le pipeline complet **import → transform → export → génération de pages**.

### Trois flux de données alimentent le transform shapes

```
1. Entity data:     import.yml shapes → DuckDB entity_shapes → shape_info + geography
2. CSV stats:       imports/raw_shape_stats.csv → stats_loader → 10 widgets (general_info, forest_cover, etc.)
3. Metadata layer:  import.yml metadata.layers → shape_processor → geography (forest_cover overlay)
```

## Diagnostic de l'état actuel

| Couche | niamoto-test | niamoto-nc | Gap |
|--------|-------------|------------|-----|
| **Import shapes** | ✅ 7 sources configurées | ✅ 7 sources | Noms/chemins différents, OK |
| **Import metadata layers** | ✅ `amap_carto_3k_20240715` | ✅ `forest_cover` | Nom de layer différent ⚠️ |
| **Transform sources** | ✅ occurrences + shape_stats | ✅ shape_stats seul | Test a une source en plus, OK |
| **Transform widgets** | ❌ `widgets_data: {}` | ✅ 12 widgets | **Gap critique** |
| **Export index_generator** | ❌ absent | ✅ complet | **Gap critique** |
| **Export widgets** | ❌ `widgets: []` | ✅ 13 widgets (12 + nav) | **Gap critique** |
| **raw_shape_stats.csv** | ✅ 2.1M (21 fév) | ✅ 2.1M (30 jul) | Même fichier |
| **GeoPackage shapes** | ✅ 7 fichiers plats dans `imports/` | ✅ 7 fichiers dans `imports/shapes/` | Chemins déjà adaptés |

### Dépendance cross-layer identifiée

Le widget `geography` utilise le plugin `shape_processor` qui référence une **metadata layer** par nom :

```yaml
# NC : layer name = "forest_cover"
layers:
  - name: forest_cover
    clip: true
```

Dans l'instance test, cette layer s'appelle `amap_carto_3k_20240715`. Il faut renommer la layer dans `import.yml` pour cohérence.

## Proposed Solution

Adapter et copier la configuration shapes de NC en 4 phases séquentielles, sans toucher au GUI.

---

## Phase 1 : Harmoniser le nom de la metadata layer

**Fichier** : `test-instance/niamoto-test/config/import.yml`

Renommer la metadata layer `amap_carto_3k_20240715` → `forest_cover` pour que le `shape_processor` puisse la référencer par le même nom que dans NC.

```yaml
# AVANT (test)
metadata:
  layers:
  - name: amap_carto_3k_20240715    # ← nom auto-généré
    type: vector
    format: geopackage
    path: imports/amap_carto_3k_20240715.gpkg

# APRÈS (test)
metadata:
  layers:
  - name: forest_cover               # ← nom sémantique comme NC
    type: vector
    format: geopackage
    path: imports/amap_carto_3k_20240715.gpkg  # ← le path reste le même
```

**Impact** : Aucun autre fichier de config ne référence cette layer actuellement, donc pas de cascade à gérer.

---

## Phase 2 : Intégrer les 12 widgets transform shapes

**Fichier** : `test-instance/niamoto-test/config/transform.yml`

Remplacer `widgets_data: {}` dans la section `group_by: shapes` par les 12 widgets de NC.

**Sources conservées** (déjà définies dans le test) :
```yaml
sources:
  - name: occurrences        # Source supplémentaire du test (direct_reference)
    data: occurrences
    grouping: shapes
    relation:
      plugin: direct_reference
      key: shapes_id
      ref_key: id
  - name: shape_stats         # Identique à NC
    data: imports/raw_shape_stats.csv
    grouping: shapes
    relation:
      plugin: stats_loader
      key: id
      ref_field: name
      match_field: label
```

**12 widgets à ajouter** (copiés de NC, aucune adaptation nécessaire sauf geography qui dépend du renommage Phase 1) :

| # | Widget | Plugin | Source | Adaptation |
|---|--------|--------|--------|------------|
| 1 | `shape_info` | `field_aggregator` | shapes entity | Aucune |
| 2 | `general_info` | `class_object_field_aggregator` | shape_stats CSV | Aucune |
| 3 | `geography` | `shape_processor` | shapes entity + forest_cover layer | Layer renommée Phase 1 ✅ |
| 4 | `forest_cover` | `class_object_binary_aggregator` | shape_stats CSV | Aucune |
| 5 | `land_use` | `class_object_categories_extractor` | shape_stats CSV | Aucune |
| 6 | `elevation_distribution` | `class_object_series_ratio_aggregator` | shape_stats CSV | Aucune |
| 7 | `holdridge` | `class_object_categories_mapper` | shape_stats CSV | Aucune |
| 8 | `forest_types` | `class_object_categories_extractor` | shape_stats CSV | Aucune |
| 9 | `forest_cover_by_elevation` | `class_object_series_matrix_extractor` | shape_stats CSV | Aucune |
| 10 | `forest_types_by_elevation` | `class_object_series_by_axis_extractor` | shape_stats CSV | Aucune |
| 11 | `fragmentation` | `class_object_field_aggregator` | shape_stats CSV | Aucune |
| 12 | `fragmentation_distribution` | `class_object_series_extractor` | shape_stats CSV | Aucune |

**Note** : 11 des 12 widgets s'appuient sur le CSV `raw_shape_stats.csv` via le `stats_loader`. Seul `geography` a une dépendance cross-layer (metadata layer `forest_cover`). Le `shape_info` lit directement l'entité shapes.

**Source `occurrences` non utilisée** : Le test a une source `occurrences` (via `direct_reference`) dans la section shapes que NC n'a pas. Aucun des 12 widgets ne l'utilise — on la conserve pour usage futur potentiel.

---

## Phase 3 : Intégrer l'export shapes complet

**Fichier** : `test-instance/niamoto-test/config/export.yml`

Remplacer la section `group_by: shapes` minimale par la configuration complète de NC.

### 3a. Ajouter l'index_generator

```yaml
index_generator:
  enabled: true
  template: _group_index.html   # Template du test (avec underscore)
  page_config:
    title: "Liste des Zones d'étude"
    description: "Zones d'étude géographiques"
    items_per_page: 16
  filters:
    - field: "shape_info.type.value"
      values: ["shape"]
      operator: "in"
  display_fields:
    - name: "name"
      source: "shape_info.name.value"
      type: "text"
      label: "Nom de la zone"
      searchable: true
    - name: "type"
      source: "shape_info.type.value"
      type: "select"
      label: "Type de zone"
      dynamic_options: true
    - name: "land_area_ha"
      source: "general_info.land_area_ha.value"
      type: "text"
      label: "Surface totale (ha)"
      format: "number"
    - name: "forest_area_ha"
      source: "general_info.forest_area_ha.value"
      type: "text"
      label: "Surface forêt (ha)"
      format: "number"
    - name: "elevation_median"
      source: "general_info.elevation_median.value"
      type: "text"
      label: "Altitude médiane (m)"
      format: "number"
  views:
    - type: "grid"
      default: true
    - type: "list"
```

### 3b. Ajouter les 13 widgets export

Les widgets export référencent les widgets transform via `data_source`. Puisqu'on utilise les mêmes noms que NC, la correspondance est directe :

| # | Plugin export | data_source (→ widget transform) |
|---|---------------|----------------------------------|
| 1 | `hierarchical_nav_widget` | (referential_data: shapes) |
| 2 | `interactive_map` | `geography` |
| 3 | `info_grid` | `general_info` |
| 4 | `concentric_rings` | `forest_cover` |
| 5 | `bar_plot` (occupation sol) | `land_use` |
| 6 | `bar_plot` (altitude) | `elevation_distribution` |
| 7 | `bar_plot` (holdridge) | `holdridge` |
| 8 | `donut_chart` (types forestiers) | `forest_types` |
| 9 | `bar_plot` (couverture/altitude) | `forest_cover_by_elevation` |
| 10 | `stacked_area_plot` (types/altitude) | `forest_types_by_elevation` |
| 11 | `radial_gauge` (fragmentation) | `fragmentation` |
| 12 | `stacked_area_plot` (fragments) | `fragmentation_distribution` |

**Adaptation template** : Le test utilise `_group_index.html` (avec underscore) au lieu de `group_index.html` pour le template d'index. Vérifier et adapter si nécessaire.

---

## Phase 4 : Validation du pipeline complet

### 4a. Vérifier la cohérence des configs

- [ ] `import.yml` : layer `forest_cover` pointe vers le bon fichier
- [ ] `transform.yml` : les 13 widgets shapes sont présents, les sources sont correctes
- [ ] `export.yml` : les 13 widgets shapes sont présents, les `data_source` correspondent aux noms de widgets transform
- [ ] Pas de référence cassée entre les couches

### 4b. Exécuter le pipeline

```bash
cd test-instance/niamoto-test

# 1. Import (si pas déjà fait)
uv run niamoto import

# 2. Transform
uv run niamoto transform

# 3. Export
uv run niamoto export
```

### 4c. Vérifier la sortie

- [ ] Les fichiers `exports/web/shapes/*.html` sont générés
- [ ] L'index `exports/web/shapes/index.html` est généré
- [ ] Les pages shapes contiennent les 13 widgets avec données
- [ ] La carte interactive affiche le shape + forest_cover
- [ ] Les graphiques ont des données (pas vides)

---

## Risques et points d'attention

### 1. Compatibilité GUI ⚠️

Les widgets ajoutés manuellement avec des noms propres (`general_info`, `geography`) **ne suivent pas** la convention de nommage auto-générée du GUI (`general_info_shapes_field_aggregator_info_grid`). Le GUI devrait pouvoir les lire, mais si l'utilisateur ré-enregistre via le GUI, les noms pourraient être écrasés.

**Mitigation** : Ne pas modifier la section shapes via le GUI tant que le support n'est pas ajouté. Éditer le YAML directement.

### 2. Template shapes manquant

Le test instance utilise un template générique (`_group_index.html`). Les pages de détail shapes pourraient nécessiter un template spécifique si le template par défaut ne gère pas tous les widgets (concentric_rings, stacked_area_plot).

**Mitigation** : Vérifier que le template par défaut supporte tous les types de widgets utilisés, ou copier les templates de NC.

### 3. Matching CSV ↔ Shapes (noms de sources)

Le `stats_loader` fait correspondre le champ `name` de `entity_shapes` (extrait du GeoPackage via `name_field`) au champ `label` du CSV. Comme les GeoPackage sont identiques entre test et NC, les valeurs `name` seront les mêmes. Les noms de sources dans import.yml (`Substrate` vs `Substrats`) n'affectent que la colonne `entity_type`, pas le matching.

**Vérification requise** : Avant de lancer le pipeline, inspecter `entity_shapes` pour confirmer les valeurs de `name` et `entity_type`.

### 4. Champs hiérarchiques du nav widget

Le `hierarchical_nav_widget` dans l'export référence `lft`, `rght`, `level`, `parent_id`. L'import engine crée `level` et `parent_id` pour les shapes, mais les champs nested set (`lft`, `rght`) ne sont peut-être pas générés pour les shapes (ils le sont pour les taxonomies). Le nav widget devrait fonctionner en mode adjacency list (via `parent_id`), mais pourrait logger des warnings.

**Mitigation** : Vérifier la présence des colonnes `lft`/`rght` dans `entity_shapes` après import.

### 5. Source `occurrences` non utilisée dans le transform shapes

Le test a une source `occurrences` (direct_reference, key: shapes_id) que NC n'a pas. Aucun widget ne l'utilise. On la conserve car elle ne cause pas d'erreur et pourra servir pour de futurs widgets (ex: comptage d'occurrences par shape).

### 6. Régression taxons/plots

La modification de `import.yml` (renommage layer) ne devrait pas impacter les pipelines taxons et plots car aucun widget de ces groupes ne référence la metadata layer `forest_cover`. Mais une vérification post-pipeline est nécessaire.

---

## Phase 0 (pré-requis) : Vérifier l'état de la base

Avant toute modification, inspecter la base DuckDB pour confirmer :

```bash
cd test-instance/niamoto-test
uv run python -c "
import duckdb
db = duckdb.connect('db/niamoto.duckdb', read_only=True)
print('=== entity_shapes columns ===')
print(db.sql('DESCRIBE entity_shapes').fetchall())
print()
print('=== entity_shapes sample (name, entity_type) ===')
print(db.sql('SELECT name, entity_type, level FROM entity_shapes LIMIT 15').fetchdf())
"
```

Vérifier :
- [x] La colonne `name` contient des valeurs qui matchent le CSV `label`
- [x] `entity_type` = `"type"` pour les conteneurs, `"shape"` pour les features
- [x] Les colonnes `lft`, `rght` existent (ou pas — ajuster le nav widget si absent)

---

## Acceptance Criteria

- [x] Phase 0 : état de la base vérifié (colonnes, valeurs name/entity_type)
- [x] La metadata layer est renommée `forest_cover` dans import.yml
- [x] Les 12 widgets transform shapes sont présents dans transform.yml
- [x] Les 13 widgets export shapes (12 + nav) sont présents dans export.yml avec index_generator
- [x] Le pipeline `import → transform → export` s'exécute sans erreur
- [x] Les pages HTML shapes sont générées avec des données visibles
- [x] L'index shapes filtre correctement (exclut les conteneurs "type")
- [x] Aucune régression sur les pages taxons et plots existantes

## Dépendances

- Les fichiers de données (GeoPackage, CSV, rasters) sont déjà présents ✅
- Le plugin `shape_processor` est disponible dans le framework ✅
- Les plugins `class_object_*` sont disponibles ✅
- Les templates de base existent ✅

## MVP

L'implémentation consiste uniquement à éditer 3 fichiers YAML :

1. `config/import.yml` — renommer 1 layer
2. `config/transform.yml` — ajouter ~270 lignes de widgets_data
3. `config/export.yml` — ajouter ~350 lignes de widgets + index_generator

Aucun code Python ne doit être modifié.
