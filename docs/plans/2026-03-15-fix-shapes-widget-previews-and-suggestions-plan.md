---
title: Fix Shapes Widget Previews and Suggestions Integration
type: fix
date: 2026-03-15
---

# Fix Shapes Widget Previews and Suggestions Integration

## Overview

Les widgets du groupe **shapes** (12 transform + 13 export) affichent des erreurs dans l'interface GUI. Le pipeline de preview class_object ne couvre que 4 des 8 types de transformateurs utilisés, et le système de suggestions n'intègre pas les widgets shapes spécifiques. Ce plan corrige d'abord les previews configurés (le plus urgent), puis intègre progressivement les shapes dans le système de suggestions.

## Problem Statement

### Diagnostic des 12 widgets shapes (transform.yml)

| Widget | Transformer | Preview Status | Cause racine |
|--------|------------|---------------|--------------|
| `shape_info` | `field_aggregator` (non-class_object) | ❓ À vérifier | Pas de chemin class_object → TransformerService path |
| `general_info` | `class_object_field_aggregator` | ❓ À vérifier | Géré dans `_execute_configured_transformer` |
| `geography` | `shape_processor` (non-class_object) | ❓ À vérifier | Pas de chemin class_object → renderer séparé |
| `forest_cover` | `class_object_binary_aggregator` | ❓ À vérifier | Géré mais `concentric_rings` widget pas dans `_build_widget_params` |
| `land_use` | `class_object_categories_extractor` | ❓ À vérifier | Géré dans `_execute_configured_transformer` |
| `elevation_distribution` | `class_object_series_ratio_aggregator` | ❌ Probable | **Pas de branche** dans `_execute_configured_transformer` |
| `holdridge` | `class_object_categories_mapper` | ❌ Probable | **Pas de branche** dans `_execute_configured_transformer` |
| `forest_types` | `class_object_categories_extractor` | ❓ À vérifier | Géré |
| `forest_cover_by_elevation` | `class_object_series_matrix_extractor` | ❌ Probable | **Pas de branche** dans `_execute_configured_transformer` |
| `forest_types_by_elevation` | `class_object_series_by_axis_extractor` | ❌ Probable | **Pas de branche** dans `_execute_configured_transformer` |
| `fragmentation` | `class_object_field_aggregator` | ❓ À vérifier | Géré |
| `fragmentation_distribution` | `class_object_series_extractor` | ❓ À vérifier | Géré |

### Causes racines identifiées

1. **4 transformateurs manquants** dans `_execute_configured_transformer` (class_object_rendering.py) — ces transformateurs tombent dans le catch-all `return {"data": class_object_data}` au lieu d'être correctement exécutés
2. **Widget `concentric_rings` absent** de `_build_widget_params_for_configured` — le `forest_cover` ne reçoit pas ses paramètres (ring_order, ring_labels, category_colors)
3. **`shape_processor` et `field_aggregator`** (non-class_object) nécessitent un chemin de rendu différent
4. **`CLASS_OBJECT_EXTRACTORS`** (widget_utils.py) incomplet — 4 extracteurs manquants, affecte le routage des previews suggestions
5. **Pas de filtrage per-entity** dans `load_class_object_data_for_preview` — toutes les shapes montrent les mêmes données agrégées

## Proposed Solution

### Stratégie : corriger les previews d'abord, suggestions ensuite

**Phase 1** — Diagnostic automatisé (rapide, 0 risque)
**Phase 2** — Correction des previews configurés (4 sous-étapes)
**Phase 3** — Intégration suggestions (optionnelle, plus complexe)

---

## Phase 1 : Diagnostic — Tester chaque widget, cataloguer les erreurs

### 1.1 Script de test batch shapes

Créer un script `scripts/dev/test_shapes_previews.py` qui :
- Lance l'API FastAPI en mode test
- Appelle `GET /api/preview/{widget_id}?group_by=shapes` pour chacun des 12 widgets
- Capture le status HTTP, le content-type, et le body (HTML ou erreur)
- Produit un tableau récapitulatif : ✅ OK / ❌ erreur + message

```python
# scripts/dev/test_shapes_previews.py
SHAPES_WIDGETS = [
    "shape_info", "general_info", "geography", "forest_cover",
    "land_use", "elevation_distribution", "holdridge", "forest_types",
    "forest_cover_by_elevation", "forest_types_by_elevation",
    "fragmentation", "fragmentation_distribution"
]
# Pour chaque widget : GET /api/preview/{w}?group_by=shapes
# Classifier : OK / warning (info_html) / error (exception)
```

### 1.2 Test manual GUI

- Lancer `niamoto gui` sur niamoto-subset
- Naviguer vers shapes → cliquer chaque widget
- Faire une capture d'écran de chaque erreur
- Comparer avec le tableau du script

**Critère de sortie Phase 1 :** Tableau complet des 12 widgets avec statut et cause racine confirmée.

---

## Phase 2 : Correction des previews configurés

### 2.1 Ajouter les 4 transformateurs manquants dans `_execute_configured_transformer`

**Fichier :** `src/niamoto/gui/api/services/templates/utils/class_object_rendering.py`

Au lieu d'émuler chaque transformateur, appeler directement la méthode `.transform()` du plugin réel. C'est plus robuste et évite de maintenir deux implémentations.

```python
# Pattern unifié pour les class_object transformers non-gérés
elif transformer_plugin in (
    "class_object_series_ratio_aggregator",
    "class_object_categories_mapper",
    "class_object_series_matrix_extractor",
    "class_object_series_by_axis_extractor",
):
    # Charger le plugin réel et l'appeler avec les données CSV préparées
    plugin = PluginRegistry.get(transformer_plugin, PluginType.TRANSFORMER)
    result = plugin.transform(class_object_data, transformer_config)
    return result
```

**4 transformateurs à gérer :**
- `class_object_series_ratio_aggregator` → produit `{classes: [], subset: [], complement: []}`
- `class_object_categories_mapper` → produit `{tops: [], counts: []}` avec mapping catégories
- `class_object_series_matrix_extractor` → produit matrice `{x_axis: [], series: [{name, values}]}`
- `class_object_series_by_axis_extractor` → produit séries par axe

**Tests :** Vérifier chaque transformateur avec les données CSV de niamoto-subset.

### 2.2 Ajouter `concentric_rings` au widget param builder

**Fichier :** `src/niamoto/gui/api/services/templates/utils/class_object_rendering.py`
**Fonction :** `_build_widget_params_for_configured`

```python
elif widget_plugin == "concentric_rings":
    params["ring_order"] = widget_params.get("ring_order", [])
    params["ring_labels"] = widget_params.get("ring_labels", {})
    params["category_colors"] = widget_params.get("category_colors", {})
```

Aussi vérifier que `stacked_area_plot` est géré (utilisé par `forest_types_by_elevation` et `fragmentation_distribution`).

### 2.3 Gérer les widgets non-class_object du groupe shapes

**Widgets concernés :**
- `shape_info` → transformer `field_aggregator` (source: shapes entity table)
- `geography` → transformer `shape_processor` (source: shapes geometry)

**Fichier :** `src/niamoto/gui/api/services/preview_engine/engine.py`

Ces widgets ne commencent pas par `class_object_` donc le routage `_render_configured_class_object` ne s'applique pas. Ils tombent dans `_render_configured_widget` qui utilise `TransformerService.transform_single_widget()`.

**Vérifier que :**
- `TransformerService.transform_single_widget()` fonctionne pour le groupe shapes (pas seulement taxons)
- Le `field_aggregator` peut lire les champs de la table `entity_shapes`
- Le `shape_processor` peut lire la géométrie de la table `entity_shapes`

Si ces transformateurs échouent via `TransformerService`, envisager un rendu spécial (comme `_handle_entity_map` pour geography).

### 2.4 Mettre à jour `CLASS_OBJECT_EXTRACTORS`

**Fichier :** `src/niamoto/gui/api/services/templates/utils/widget_utils.py`

```python
CLASS_OBJECT_EXTRACTORS = {
    "series_extractor",
    "binary_aggregator",
    "categories_extractor",
    "field_aggregator",
    # Ajouts pour shapes
    "series_ratio_aggregator",
    "categories_mapper",
    "series_matrix_extractor",
    "series_by_axis_extractor",
}
```

Ceci corrige le routage `is_class_object_template()` pour les previews inline (suggestions).

**Critère de sortie Phase 2 :** Les 12 widgets shapes affichent un preview correct (ou un message d'info clair si les données manquent).

---

## Phase 3 : Intégration suggestions (optionnelle, complexe)

> Cette phase est plus lourde. Le système de suggestions actuel (`ClassObjectWidgetSuggester`) ne peut proposer que `bar_plot`, `donut_chart`, `radial_gauge`. Les widgets shapes nécessitent `concentric_rings`, `stacked_area_plot`, `interactive_map`, `info_grid`.

### 3.1 Dédupliquer suggestions vs widgets configurés

**Problème :** Si `forest_cover` est déjà configuré, le système ne doit pas proposer une suggestion pour les mêmes class_objects.

**Fichier :** `src/niamoto/gui/api/services/templates/suggestion_service.py`
**Fonction :** `get_class_object_suggestions`

Ajouter un filtre : lire les `widgets_data` du transform.yml pour le groupe shapes, extraire les class_objects déjà utilisés, les exclure des suggestions.

### 3.2 Enrichir `ClassObjectWidgetSuggester` (optionnel)

**Fichier :** `src/niamoto/core/imports/class_object_suggester.py`

Ajouter la capacité de suggérer :
- `concentric_rings` pour les groupes binaires (quand 2-3 class_objects binaires existent)
- `stacked_area_plot` pour les séries par axe
- `info_grid` pour les scalaires multiples

C'est le plus complexe car ces widgets agrègent plusieurs class_objects — le suggester actuel fonctionne class_object par class_object.

### 3.3 Ajouter `output_structure` aux class_object transformers (optionnel)

**Fichiers :** `src/niamoto/core/plugins/transformers/class_objects/*.py`

Déclarer `output_structure` sur chaque transformateur pour que SmartMatcher puisse les découvrir automatiquement. C'est un investissement pour le futur mais pas bloquant pour les corrections immédiates.

---

## Acceptance Criteria

### Phase 1
- [x] Script `test_shapes_previews.py` créé et exécuté
- [x] Tableau complet des 12 widgets avec statut et cause racine

### Phase 2
- [x] Les 4 transformateurs manquants sont gérés via `_transform_with_real_plugin` (raw CSV DataFrame)
- [x] `concentric_rings` et `stacked_area_plot` fonctionnent via export.yml params (pas de branche nécessaire)
- [x] `CLASS_OBJECT_EXTRACTORS` contient les 8 extracteurs
- [x] `shape_info` fonctionne en preview (via TransformerService)
- [x] `binary_aggregator` migré vers real plugin (corrige `concentric_rings`)
- [x] Remapping `tops/counts` → noms de champs export.yml (corrige `land_use`, `forest_types`)
- [x] Filtrage par entité représentative dans `load_class_object_csv_dataframe` (corrige `elevation_distribution`)
- [x] Relancer le script de test → 11/12 OK (`geography` = données map non disponibles en preview, pas un bug de code)

### Phase 3 (si décidé)
- [ ] Les suggestions shapes ne dupliquent pas les widgets déjà configurés
- [ ] Au moins les widgets simples (bar_plot, donut) sont proposés en suggestion

## Dependencies & Risks

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Appeler `.transform()` directement sur les plugins class_object avec données CSV préparées | Les plugins attendent un format précis de données | Tester avec les données réelles de niamoto-subset |
| `shape_processor` et `field_aggregator` peuvent échouer via `TransformerService` pour shapes | Le code a été testé surtout avec taxons | Isoler le test, prévoir un fallback |
| Modifier `CLASS_OBJECT_EXTRACTORS` pourrait impacter le routage des suggestions taxons | Régression possible | Tester les suggestions taxons après modification |
| Phase 3 (`ClassObjectWidgetSuggester` enrichi) est structurellement complexe | Widgets multi-class_objects pas supportés par le pattern actuel | Reporter si complexe, garder simple |

## Fichiers impactés

| Fichier | Modifications |
|---------|--------------|
| `src/niamoto/gui/api/services/templates/utils/class_object_rendering.py` | Ajouter 4 branches transformateur + concentric_rings widget params |
| `src/niamoto/gui/api/services/templates/utils/widget_utils.py` | Mettre à jour `CLASS_OBJECT_EXTRACTORS` |
| `src/niamoto/gui/api/services/preview_engine/engine.py` | Vérifier routage shape_processor et field_aggregator |
| `src/niamoto/gui/api/services/templates/utils/data_loader.py` | Éventuellement ajouter filtrage entity_id |
| `src/niamoto/gui/api/services/templates/suggestion_service.py` | Phase 3 : dédupliquer suggestions |
| `scripts/dev/test_shapes_previews.py` | Nouveau script de diagnostic |

## References

- Preview engine unification : `docs/plans/2026-03-14-refactor-preview-engine-unification-plan.md`
- Battle-test SmartMatcher : `docs/plans/2026-03-13-feat-battle-test-smartmatcher-import-suggestions-plan.md`
- Shapes integration : `docs/plans/2026-02-23-feat-integration-shapes-config-workflow-complet-plan.md`
- Config NC : `test-instance/niamoto-nc/config/transform.yml` (L620-900)
- Config subset : `test-instance/niamoto-subset/config/transform.yml`
- Class object rendering : `src/niamoto/gui/api/services/templates/utils/class_object_rendering.py`
