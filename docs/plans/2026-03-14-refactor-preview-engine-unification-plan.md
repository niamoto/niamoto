---
title: "Unification du Preview Engine — éliminer la duplication et les incohérences"
type: refactor
date: 2026-03-14
---

# Unification du Preview Engine

## Overview

Le système de preview des widgets a deux pipelines parallèles qui produisent des résultats différents pour le même widget :

- **Chemin "configuré"** : `TransformerService.transform_single_widget()` — le vrai pipeline, partagé avec `niamoto transform`. Fonctionne toujours.
- **Chemin "suggestion"** : `execute_transformer()` ad-hoc — pipeline simplifié avec config minimale, chargement de données différent. Produit des erreurs de validation et des rendus incohérents.

En plus, un système legacy complet dans `templates.py` (~3700 lignes) duplique tout le preview engine avec ses propres caches.

## Problème

### Symptômes observés
- Erreurs de validation (`bins missing`, `x_axis missing`) dans les previews de suggestions
- Widget qui fonctionne une fois ajouté à la config mais pas en suggestion
- Rendus différents entre la vue d'ensemble et la vue détail
- Cache qui sert des réponses périmées après import/save

### Cause racine
**6 couches de cache** et **2 systèmes de preview** avec **4 chemins d'exécution du transformer** qui ne partagent pas le même code de chargement de données ni de construction de config.

## Architecture actuelle (à nettoyer)

### Fichiers impliqués

| Fichier | Lignes | Rôle | Statut |
|---------|--------|------|--------|
| `preview_engine/engine.py` | 1785 | Preview engine unifié | À simplifier |
| `routers/templates.py` | ~3700 | Legacy preview (endpoints dupliqués) | Legacy à supprimer |
| `routers/preview.py` | 155 | Router unifié (GET + POST) | OK — garder |
| `services/preview_utils.py` | 267 | Utilitaires partagés | OK — enrichir |
| `services/preview_service.py` | ~577 | Wrapper legacy → preview_utils | À supprimer |
| `templates/suggestion_service.py` | ~1100 | Génération de suggestions | À nettoyer (duplication config) |

### 6 couches de cache

1. **TTLCache** (`templates.py:177`) — 128 entrées, TTL 5min, POST legacy uniquement
2. **ETag preview.py** — fingerprint pré-calculé (`engine._compute_etag`)
3. **ETag templates.py** — stat() des fichiers à chaque requête (calcul différent !)
4. **TransformerService singleton** (`engine.py:79`) — module-level, invalidé par `engine.invalidate()`
5. **PreviewEngine singleton** (`engine.py:1747`) — module-level, porte le `_data_fingerprint`
6. **WidgetGenerator._widget_cache** — per-instance, SmartMatcher results

### 4 duplications majeures

1. **`_render_occurrence` ≈ `_render_entity_source`** — même structure, ~70 lignes chacun
2. **`_build_transformer_config` ≈ `_build_widget_params_for_preview`** — même reconstruction de `EnrichedColumnProfile` (~30 lignes identiques)
3. **engine.py vs templates.py** — 5 méthodes dupliquées (navigation, general_info, entity_map, configured widget, dynamic preview)
4. **`_preprocess_data_for_widget`** — logique identique dans engine.py et class_object_rendering.py

## Solution proposée

### Principe : un seul pipeline

Toutes les previews (suggestions ET configurés) passent par `TransformerService.transform_single_widget()`. Pour les suggestions (pas encore dans transform.yml), on construit un `group_config` synthétique à partir de la config réelle du groupe + la config du transformer générée par `WidgetGenerator`.

### Phase 1 : Extractions (safe, aucune régression)

- [x] **`EnrichedColumnProfile.from_stored_dict(col_data)`** — classmethod dans `data_analyzer.py`
  - Remplace les 4 blocs identiques de reconstruction (~30 lignes chacun)
  - Fichiers touchés : `engine.py`, `templates.py:get_reference_suggestions`

- [x] **`_preprocess_data_for_widget` → `preview_utils.py`**
  - Extraire depuis `engine.py` vers le module utilitaire partagé
  - Supprimer le doublon dans `class_object_rendering.py`

- [x] **Fusionner `_render_occurrence` et `_render_entity_source`**
  - En une seule méthode `_render_dynamic_preview(template_id, column, transformer, widget, data_source, group_by, entity_id, export_params, db, warnings)`
  - La seule différence est le fallback sans group_config (SQL direct vs load_sample_data)

### Phase 2 : Pipeline unique (fix principal)

- [x] **`_render_dynamic_preview` utilise toujours `transform_single_widget`**
  - Récupérer le `group_config` réel via `_load_group_config(group_by)`
  - Construire un `widgets_data` synthétique avec la config de `_build_transformer_config()`
  - Appeler `svc.transform_single_widget(temp_group_config, template_id, gid)`
  - Fallback : si pas de `group_config` (premier init, pas de transform.yml), construire un `group_config` synthétique complet à partir de `import.yml` (les `sources` sont dans import.yml via les relations dataset→reference)

- [x] **Widget params : lire depuis `param_schema` defaults**
  - Ne plus utiliser `_build_widget_params_for_preview` (qui reconstruit un profil pour appeler WidgetGenerator)
  - Utiliser directement les defaults du `param_schema` du widget plugin
  - Seul override : `export_params` depuis export.yml (quand ils existent)

### Phase 3 : Suppression du legacy

- [x] **Supprimer les endpoints preview dans `templates.py`**
  - `preview_template` (GET), `preview_inline` (POST)
  - `_preview_configured_widget`, `_preview_navigation_widget`, `_preview_general_info_widget`, `_preview_entity_map`
  - `_build_dynamic_template_info` (la config hardcodée par transformer)
  - `_compute_preview_etag`, `_preview_cache`, `invalidate_preview_cache`
  - Garder un shim `POST /api/templates/preview` → redirige vers `POST /api/preview` avec traduction de schema

- [x] **Supprimer `PreviewService` (classe)**
  - Ses méthodes sont des wrappers vers `preview_utils.py`
  - Mettre à jour les imports restants

- [x] **Mettre à jour le frontend**
  - `AddWidgetModal.tsx` : migrer de `/api/templates/preview` vers `/api/preview` POST
  - Vérifier `usePreviewFrame.ts` : déjà sur `/api/preview`, OK

### Phase 4 : Cache simplifié

- [x] **Un seul mécanisme ETag** : celui de `PreviewEngine` (fingerprint pré-calculé)
  - Supprimer `_compute_preview_etag` de templates.py
  - Supprimer TTLCache de templates.py

- [x] **Inventaire complet des triggers d'invalidation**
  - Import de données → `engine.invalidate()` ✅ (déjà fait dans imports.py)
  - Save config (transform.yml, export.yml) → `engine.invalidate()` ✅ (déjà fait)
  - Changement de projet → `reset_preview_engine()` ✅ (déjà fait)
  - Ajout/suppression de plugin → à ajouter si nécessaire

- [x] **Documenter le contrat de cache**
  - ETag = `md5(template_id:group_by:source:entity_id:data_fingerprint)`
  - `data_fingerprint` = `md5(db_mtime + config_mtimes)`
  - Invalidation = recalcul du fingerprint via `engine.invalidate()`

## Acceptance Criteria

- [x] Toutes les previews de suggestions produisent le même résultat que le widget une fois configuré
- [x] Aucun endpoint preview dans `templates.py` (sauf shim de redirection)
- [x] `PreviewService` class supprimée
- [x] `EnrichedColumnProfile.from_stored_dict()` utilisé partout
- [x] `_preprocess_data_for_widget` dans un seul fichier
- [x] Un seul mécanisme de cache ETag
- [x] Tests de non-régression : comparer la sortie transformer pour 5+ template_ids entre l'ancien et le nouveau chemin

## Risques

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Frontend utilise encore l'ancien endpoint | Preview cassé | Shim de redirection temporaire |
| `transform_single_widget` sans group_config | Suggestions cassées sur instance vierge | Fallback : construire group_config depuis import.yml |
| Cache périmé après refactor | Previews incohérents | Forcer `invalidate()` au démarrage du serveur |

## Références

- `src/niamoto/gui/api/services/preview_engine/engine.py` — engine unifié
- `src/niamoto/core/services/transformer.py:117` — `transform_single_widget`
- `src/niamoto/core/imports/widget_generator.py:359` — `_generate_transformer_config`
- `src/niamoto/gui/api/routers/templates.py:3442` — `_build_dynamic_template_info` (legacy)
- `docs/06-gui/preview-architecture.md` — documentation architecture preview
- `docs/06-gui/preview-api.md` — contrat API preview
