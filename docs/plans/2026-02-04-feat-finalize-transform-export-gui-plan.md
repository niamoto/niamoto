---
title: "Finalisation GUI Transform/Export - Support Complet Plots et Shapes"
type: feat
date: 2026-02-04
status: in-progress
priority: P1
estimated_complexity: high
groups: [plots, shapes, taxons]
tags: [gui, transform, export, widgets, yaml-config, forms]
---

# Finalisation GUI Transform/Export - Support Complet Plots et Shapes

## Overview

Reprise du développement interrompu sur la phase Transform/Export du GUI Niamoto. L'objectif principal est de permettre la **reproduction fidèle** des fichiers de configuration `transform.yml` et `export.yml` de l'instance de référence (`test-instance/niamoto-nc/`) via l'interface graphique.

**Critère de validation principal** : Les formulaires du GUI doivent permettre de reproduire exactement les configurations YAML existantes pour les 3 groupes (taxons, plots, shapes), avec possibilité de simplification si pertinent.

### État actuel (Février 2026) - Mis à jour après tests

| Groupe | Sources | Transform | Export | Index Generator | Tests |
|--------|---------|-----------|--------|-----------------|-------|
| **Taxons** | ✅ | ✅ Fonctionnel | ✅ Fonctionnel | ✅ Complet | ✅ Validé |
| **Plots** | ✅ CSV stats | ✅ Fonctionnel | ✅ Fonctionnel | ✅ Basique | ✅ Validé (04/02/2026) |
| **Shapes** | ✅ CSV stats | ✅ Fonctionnel | ✅ Fonctionnel | ✅ Basique | ✅ Validé (04/02/2026) |

### Résultats des tests GUI (04/02/2026)

**Instance de test** : `test-instance/niamoto-test/`

#### Plots ✅
- Sources : 2 sources configurées (plots builtin + plot_stats CSV)
- Widgets : 6 widgets avec previews fonctionnels
- Suggestions : 100 suggestions générées automatiquement
- Patterns combinés : Phénologie (3), Dimensions (2), Traits fonctionnels (6)
- Formulaires : JsonSchemaForm génère correctement les paramètres (FieldConfig)

#### Shapes ✅
- Sources : 2 sources configurées (shapes builtin + shape_stats CSV)
- Widgets : 4 widgets configurés
- Suggestions : 84 suggestions générées
- Formulaires : Fonctionnels

### Problèmes identifiés (résolus ou en cours)

1. ~~**Plugins `class_object_*`**~~ ✅ **RÉSOLU** : Tous les plugins existent avec config_model, formulaires fonctionnels
2. ~~**Sources externes**~~ ✅ **RÉSOLU** : L'onglet Sources permet d'ajouter des CSV avec détection automatique des relations
3. **Layers géographiques** : Pas de sélecteur de fichiers raster/vector pour `shape_processor`, `raster_stats`
4. **Transformations complexes** : `transform_chain` (P3 - interface dédiée à créer ultérieurement)
5. **Widgets avancés** : `concentric_rings`, `stacked_area_plot` avec transformations spéciales

### Ce qui fonctionne déjà

1. **Sources Tab** : Upload CSV, validation, détection automatique des colonnes et class_objects
2. **Smart Relation Detection** : Détection automatique de `ref_field` et `match_field` par intersection
3. **Suggestions de widgets** : Prennent en compte les sources CSV configurées
4. **TransformSourceSelectField** : Dropdown pour sélectionner la source dans les formulaires widgets

---

## Contrainte Architecturale Fondamentale

> **GENERICITY FIRST — NO HARDCODING**

Niamoto est une **plateforme générique** pour données écologiques. Le code doit fonctionner pour n'importe quel dataset, n'importe quelle taxonomie, n'importe quels noms de champs.

### Ce qui est autorisé
- Standards bien connus (Darwin Core: `scientificName`, `decimalLatitude`)
- Tables internes (`niamoto_metadata_*`)
- Conventions framework (Pydantic `model_config`, plugin `config_model`)

### Ce qui est INTERDIT
- Hardcoder des noms de tables (`dataset_occurrences`, `taxon`)
- Hardcoder des noms de champs (`id_taxonref`, `dbh`, `height`)
- Hardcoder des noms d'entités (`occurrences`, `plots`, `shapes`)
- Hardcoder des valeurs de domaine (`endemic`, `native`)

### Pattern obligatoire

```python
# ❌ INTERDIT - Hardcodé
for table in ["dataset_occurrences", "occurrences"]:
    cols = get_columns(table)

# ✅ CORRECT - Générique via EntityRegistry
registry = EntityRegistry(db)
for entity in registry.list_entities(kind=EntityKind.DATASET):
    cols = get_columns(entity.table_name)
```

### Implications pour le GUI

- Les formulaires doivent proposer des **sélecteurs dynamiques** basés sur les données réelles
- Pas de liste prédéfinie de groupes ou champs
- La configuration YAML fait le mapping entre données et visualisation
- Le code GUI reste agnostique des domaines métier

---

## Problem Statement

Le GUI Niamoto permet actuellement de visualiser et exécuter les transformations/exports, mais **ne permet pas de créer ou modifier** les configurations de manière visuelle pour les groupes `plots` et `shapes`. Les utilisateurs doivent éditer manuellement le YAML, ce qui :

- Nécessite une connaissance approfondie de la structure YAML
- Est source d'erreurs (typos, mauvaises clés, formats incorrects)
- Ne bénéficie pas des suggestions intelligentes implémentées pour les taxons
- Rend l'outil inaccessible aux utilisateurs non-techniques

L'instance de référence `niamoto-nc` contient des configurations avancées qui démontrent les capacités du système mais ne peuvent pas être reproduites via l'interface.

---

## Proposed Solution

### Approche en 3 phases

```
Phase 1: Audit & Fondations
├── Inventaire complet des plugins utilisés par groupe
├── Création des `config_model` Pydantic manquants
└── Tests de validation groupe par groupe

Phase 2: Formulaires & UI
├── Extension JsonSchemaForm pour paramètres complexes
├── Sélecteurs de fichiers (raster, vector, CSV)
└── Preview temps réel des widgets

Phase 3: Validation & Polish
├── Tests end-to-end avec instance de référence
├── Simplifications de configuration identifiées
└── Documentation utilisateur
```

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GUI (React/TypeScript)                   │
├─────────────────────────────────────────────────────────────┤
│  ContentTab.tsx                                              │
│  ├── WidgetListPanel (liste widgets configurés)             │
│  ├── WidgetDetailPanel                                       │
│  │   ├── Preview (iframe rendu)                             │
│  │   ├── Parameters (JsonSchemaForm)                        │
│  │   └── YAML (export readonly)                             │
│  └── AddWidgetModal                                          │
│      ├── Suggestions (patterns détectés)                    │
│      ├── Combined (multi-champs)                            │
│      └── Custom (wizard 4 étapes)                           │
├─────────────────────────────────────────────────────────────┤
│                     API (FastAPI)                            │
├─────────────────────────────────────────────────────────────┤
│  /api/plugins                                                │
│  ├── GET /{type}/{category} → Liste plugins + schémas       │
│  └── GET /{plugin_name}/schema → JSON Schema complet        │
│                                                              │
│  /api/config                                                 │
│  ├── GET /widgets/{group} → Widgets configurés              │
│  ├── PUT /widgets/{group} → Sauvegarde config               │
│  └── POST /validate/{group} → Validation YAML               │
│                                                              │
│  /api/files                                                  │
│  ├── GET /list/{type} → Liste fichiers (raster, csv, gpkg)  │
│  └── GET /preview/{path} → Preview données fichier          │
├─────────────────────────────────────────────────────────────┤
│                  Plugins (Python/Pydantic)                   │
├─────────────────────────────────────────────────────────────┤
│  Transformers                    Exporters/Widgets           │
│  ├── class_object_*             ├── bar_plot                │
│  ├── shape_processor            ├── concentric_rings        │
│  ├── raster_stats               ├── stacked_area_plot       │
│  └── multi_column_extractor     └── interactive_map         │
└─────────────────────────────────────────────────────────────┘
```

### Audit des Plugins Transformers

#### Résultat de l'audit : Tous les plugins class_object_* EXISTENT

**Bonne nouvelle** : Les 8 plugins `class_object_*` utilisés par shapes sont tous implémentés avec `config_model` Pydantic. Le problème n'est pas l'absence des plugins mais **l'absence de formulaires UI adaptés** pour les configurer.

#### Plugins utilisés par `shapes` (transform.yml:619-901)

| Plugin | config_model | UI Support | Suggestion Auto | Action |
|--------|--------------|------------|-----------------|--------|
| `class_object_field_aggregator` | ✅ Oui | ❌ Manque | ✅ Single fields/ranges | Formulaire + suggestions |
| `class_object_binary_aggregator` | ✅ Oui | ❌ Manque | ✅ Détecte 2 classes | Formulaire + suggestions |
| `class_object_categories_extractor` | ✅ Oui | ❌ Manque | ✅ Auto-détecte catégories | Formulaire + suggestions |
| `class_object_series_ratio_aggregator` | ✅ Oui | ❌ Manque | ✅ Détecte pairs total/subset | Formulaire + suggestions |
| `class_object_categories_mapper` | ✅ Oui | ❌ Manque | ✅ Mapping nested | Formulaire + suggestions |
| `class_object_series_matrix_extractor` | ✅ Oui | ❌ Manque | ✅ Multiple séries | Formulaire + suggestions |
| `class_object_series_by_axis_extractor` | ✅ Oui | ❌ Manque | ✅ Séries indexées | Formulaire + suggestions |
| `class_object_series_extractor` | ✅ Oui | ❌ Manque | ✅ Pattern numérique | Formulaire + suggestions |
| `shape_processor` | ✅ Oui | ❌ Manque | ✅ Geo field → topojson | Formulaire + layer picker |

#### Plugins utilisés par `plots` (transform.yml:371-617)

| Plugin | config_model | UI Support | Suggestion Auto | Action |
|--------|--------------|------------|-----------------|--------|
| `class_object_series_extractor` | ✅ Oui | ❌ Manque | ✅ | Voir shapes |
| `multi_column_extractor` | ✅ Oui | ❌ Manque | ✅ Groupes colonnes | Formulaire + suggestions |
| `direct_attribute` | ✅ Oui | ⚠️ Basique | ✅ Single field | Améliorer |

#### Critères de suggestion automatique par catégorie

| Catégorie | Critère de détection | Plugins concernés |
|-----------|---------------------|-------------------|
| **Binary** | 2 classes distinctes | `class_object_binary_aggregator`, `binary_counter` |
| **Categorical** | 3-12 catégories | `class_object_categories_extractor`, `categorical_distribution` |
| **Numeric bins** | Valeurs numériques continues | `class_object_series_extractor`, `binned_distribution` |
| **Ranges** | Pairs min/max détectées | `class_object_field_aggregator` (format: range) |
| **Ratios** | Pairs total/subset | `class_object_series_ratio_aggregator` |
| **Nested mapping** | Structure catégories imbriquées | `class_object_categories_mapper` |
| **Matrix** | Multiple séries, axe commun | `class_object_series_matrix_extractor` |
| **Time series** | Champ temporel (month, year) | `time_series_analysis` |
| **Geo** | Champ géométrie (geo_pt, location) | `geospatial_extractor`, `shape_processor` |

#### Plugins sans suggestion auto (P3)

Ces plugins nécessitent une configuration manuelle et ne peuvent pas être suggérés automatiquement :

- `transform_chain` - Composition de plugins
- `custom_calculator` - Logique personnalisée
- `database_aggregator` - Requêtes SQL custom
- `raster_stats`, `vector_overlay` - Dépendent de fichiers externes spécifiques

#### Widgets à supporter (export.yml)

| Widget | Utilisé par | Transformations | Action |
|--------|-------------|-----------------|--------|
| `concentric_rings` | shapes | Données imbriquées | Ajouter support |
| `stacked_area_plot` | shapes | normalize, series_to_df | Ajouter transformations |
| `bar_plot` pyramid | shapes | pyramid_chart transform | Ajouter mode pyramid |

---

## Implementation Phases

### Phase 1: Audit & Fondations

**Durée estimée** : Non applicable (pas d'estimation de temps)

#### 1.1 Audit des plugins et UI hints ✅ COMPLÉTÉ (04/02/2026)

L'audit a révélé que **tous les plugins `class_object_*` existent avec `config_model`** et ont déjà des hints UI partiels.

##### État des UI hints par plugin

| Plugin | Niveau racine | Modèles imbriqués | Score |
|--------|--------------|-------------------|-------|
| `series_extractor` | ✅ Complet | N/A | ⭐⭐⭐ |
| `categories_extractor` | ✅ Complet | N/A | ⭐⭐⭐ |
| `binary_aggregator` | ✅ source, groups | ✅ GroupConfig | ⭐⭐⭐ |
| `categories_mapper` | ✅ source, categories | ✅ CategoryMappingDetail | ⭐⭐⭐ |
| `field_aggregator` | ✅ source, fields | ❌ FieldConfig | ⭐⭐ |
| `series_by_axis_extractor` | ✅ source, axis, types | ✅ AxisConfig | ⭐⭐⭐ |
| `series_matrix_extractor` | ✅ source, axis, series | ✅ SeriesConfig, AxisConfig | ⭐⭐⭐ |
| `series_ratio_aggregator` | ✅ source, distributions | ✅ DistributionConfig | ⭐⭐⭐ |

##### Problème identifié : Modèles imbriqués sans hints

Les champs au niveau racine ont des `ui:widget` mais **les modèles imbriqués n'en ont pas** :

```python
# Exemple actuel (GroupConfig dans binary_aggregator)
class GroupConfig(BaseModel):
    label: str  # ❌ Pas de ui:widget
    field: str  # ❌ Pas de ui:widget
    classes: List[str]  # ❌ Pas de ui:widget
    class_mapping: Dict[str, str]  # ❌ Pas de ui:widget
```

Ces modèles imbriqués utilisent `ui:widget: "json"` ce qui affiche un éditeur JSON brut au lieu de formulaires structurés.

##### Décision : Option A - Enrichir les modèles Pydantic

**Approche retenue** : Ajouter `json_schema_extra` aux champs des modèles imbriqués pour que `JsonSchemaForm` génère des formulaires structurés au lieu d'éditeurs JSON bruts.

**Avantages** :
- Solution alignée avec l'architecture Niamoto (plugins définissent tout)
- Travail localisé côté backend
- `JsonSchemaForm` gère déjà les schémas riches
- Généricité préservée (pas de hardcoding)

##### Plan d'action par phases

**Phase 1 (prioritaire) - Modèles les plus utilisés** :
- [x] `FieldConfig` (dans aggregation/field_aggregator.py) - ✅ Déjà enrichi avec `entity-select` sur source
- [x] `GroupConfig` (dans class_objects/binary_aggregator.py) - ✅ Enrichi (04/02/2026)
- [x] `AxisConfig` (dans class_objects/series_by_axis_extractor.py) - ✅ Enrichi (04/02/2026)

**Phase 2 - Modèles secondaires** :
- [x] `SeriesConfig` (dans series_matrix_extractor) - ✅ Enrichi (04/02/2026)
- [x] `AxisConfig` (dans series_matrix_extractor) - ✅ Enrichi (04/02/2026)
- [x] `DistributionConfig` (dans series_ratio_aggregator) - ✅ Enrichi (04/02/2026)
- [x] `CategoryMappingDetail` (dans categories_mapper) - ✅ Enrichi (04/02/2026)

**Phase 3 - Validation** (✅ 04/02/2026) :
- [x] Tester que le schéma JSON généré est exploitable par `JsonSchemaForm` - ✅ Schémas corrects avec tous les hints UI
- [x] Vérifier le rendu des formulaires imbriqués - ⚠️ Fonctionne mais ObjectField ne propage pas les hints UI
- [x] S'assurer que le widget `json` reste disponible comme fallback - ✅ Fallback fonctionne

**Limitations identifiées** :
- ~~`ObjectField.tsx` (ligne 41-91) n'exploite pas `ui:widget` des sous-champs~~ ✅ RÉSOLU (04/02/2026) - ObjectField propage maintenant les hints UI
- ~~Widgets non implémentés : `key-value-pairs`, `tags` → fallback vers TextField~~ ✅ RÉSOLU (04/02/2026) - KeyValuePairsField et TagsField créés avec détection auto
- ~~Bug React : `Select.Item` avec valeur vide dans TransformSourceSelectField~~ ✅ RÉSOLU (04/02/2026) - Filtrage des valeurs vides

**Fichiers à modifier** :
```
src/niamoto/core/plugins/transformers/
├── class_object_binary_aggregator.py     # Enrichir GroupConfig
├── class_object_categories_mapper.py     # Enrichir CategoryMappingDetail
├── class_object_field_aggregator.py      # Enrichir FieldConfig
├── class_object_series_by_axis_extractor.py # Enrichir AxisConfig
├── class_object_series_matrix_extractor.py # Enrichir SeriesConfig, AxisConfig
├── class_object_series_ratio_aggregator.py # Enrichir DistributionConfig
└── shape_processor.py                     # Ajouter layer picker
```

**Widgets UI existants utilisés** :
- `transform-source-select` : Sélecteur de source dynamique
- `json` : Éditeur JSON (pour structures complexes)
- `text` : Champ texte simple
- `tags` : Liste de chaînes (chips) ✅ TagsField créé (04/02/2026)
- `key-value-pairs` : Mapping clé/valeur ✅ KeyValuePairsField créé (04/02/2026)
- `number` : Entier avec min/max (ge/le)
- `checkbox` : Booléen
- `ui:quick_edit` : Édition rapide dans la liste
- `ui:placeholder` : Texte indicatif

#### 1.2 Création des config_model manquants

Pour chaque plugin `class_object_*`, créer un modèle Pydantic avec hints UI **génériques** :

```python
# Exemple: class_object_field_aggregator.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class ClassObjectFieldAggregatorParams(BaseModel):
    """Paramètres pour class_object_field_aggregator.

    IMPORTANT: Aucun nom de champ ou de source hardcodé.
    Les widgets UI chargent dynamiquement les options disponibles.
    """

    source: str = Field(
        ...,
        description="Source de données (nom de la source définie dans sources)",
        json_schema_extra={
            "ui:widget": "source_select",
            # Le composant charge dynamiquement les sources depuis /api/transform/sources
        }
    )

    fields: List[FieldConfig] = Field(
        ...,
        description="Liste des champs à agréger",
        json_schema_extra={
            "ui:widget": "field_list",
            # Chaque champ permet de sélectionner un class_object détecté dynamiquement
        }
    )

class FieldConfig(BaseModel):
    """Configuration d'un champ - entièrement dynamique."""

    class_object: str | List[str] = Field(
        ...,
        description="Nom du class_object (détecté depuis le CSV source)",
        json_schema_extra={
            "ui:widget": "class_object_select",
            # Options chargées depuis analyse CSV, pas hardcodées
            "ui:depends": {"source": True}  # Dépend de la source sélectionnée
        }
    )
    target: str = Field(
        ...,
        description="Nom du champ de sortie (libre, défini par l'utilisateur)"
    )
    units: Optional[str] = Field(
        None,
        description="Unité (libre, ex: 'ha', 'm', 'mm/an')"
    )
    format: Optional[Literal["range", "number", "text"]] = Field(
        None,
        description="Format d'affichage"
    )
```

**Règles de conception des config_model** :

1. **Pas de valeurs par défaut spécifiques au domaine** (ex: pas de `default="dbh"`)
2. **Les `ui:widget` personnalisés chargent dynamiquement** leurs options
3. **Utiliser `ui:depends`** pour les dépendances entre champs
4. **Les descriptions expliquent** ce que fait le champ, pas quelles valeurs mettre

#### 1.3 Tests de validation par groupe ✅ FAIT

Tests créés dans `tests/gui/test_transform_config_validation.py` (56 tests, tous verts) :
1. ✅ Parsée correctement (structure YAML, clés requises)
2. ✅ Validée par le config_model/param_schema Pydantic
3. ✅ validate_config() accepte les configs de référence
4. ✅ JSON Schema généré correctement pour le GUI
5. ✅ API /api/layers testée (listing, filtrage, récursif)
6. ✅ API /api/plugins/{id}/schema testée (10 plugins transformer)

```python
# tests/gui/test_transform_config_validation.py

@pytest.mark.parametrize("group", ["taxons", "plots", "shapes"])
def test_transform_config_validates(group, reference_transform_yml):
    """Vérifie que la config transform.yml est valide pour chaque groupe."""
    config = reference_transform_yml[group]
    for widget_name, widget_config in config["widgets_data"].items():
        plugin = get_plugin(widget_config["plugin"])
        # Le plugin doit avoir un config_model
        assert hasattr(plugin, "config_model")
        # Les params doivent valider contre le modèle
        plugin.config_model(**widget_config.get("params", {}))
```

---

### Phase 2: Formulaires & UI

#### 2.1 Extension JsonSchemaForm

Ajouter support pour nouveaux types de widgets UI :

| Widget UI | Description | Composant React | Généricité |
|-----------|-------------|-----------------|------------|
| `source_select` | Sélecteur de source (parmi celles définies) | `<SourceSelectField />` | ✅ Dynamique depuis config |
| `class_object_select` | Sélecteur de class_object (depuis stats CSV) | `<ClassObjectSelectField />` | ✅ Dynamique depuis CSV analysé |
| `field_select` | Sélecteur de champ (depuis source sélectionnée) | `<FieldSelectField />` | ✅ Dynamique depuis schéma source |
| `field_list` | Liste éditable de configurations de champs | `<FieldListEditor />` | ✅ Champs libres |
| `file_picker` | Sélecteur de fichier (raster, vector, csv) | `<FilePickerField />` | ✅ Liste fichiers imports/ |
| `layer_config` | Configuration de couche géo (style, clip, simplify) | `<LayerConfigField />` | ✅ Colonnes dynamiques |
| `categories_mapping` | Mapping catégories → labels | `<CategoriesMappingField />` | ✅ Valeurs détectées depuis données |

**Principe clé** : Tous les sélecteurs doivent être **alimentés dynamiquement** depuis :
- Les sources configurées (pas de liste hardcodée de sources)
- Les colonnes détectées dans les fichiers (pas de liste hardcodée de champs)
- Les valeurs uniques dans les données (pas de liste hardcodée de catégories)

**Fichiers à créer/modifier** :
```
src/niamoto/gui/ui/src/components/forms/
├── JsonSchemaForm.tsx (modifier)
├── fields/
│   ├── SourceSelectField.tsx (créer)
│   ├── ClassObjectSelectField.tsx (créer)
│   ├── FieldListEditor.tsx (créer)
│   ├── FilePickerField.tsx (créer)
│   ├── LayerConfigField.tsx (créer)
│   └── CategoriesMappingField.tsx (créer)
```

#### 2.2 Sélecteur de fichiers

Créer un composant permettant de sélectionner des fichiers dans le projet :

```typescript
// FilePickerField.tsx
interface FilePickerFieldProps {
  value: string;
  onChange: (path: string) => void;
  accept: 'raster' | 'vector' | 'csv' | 'all';
  basePath?: string; // Ex: "imports/"
}

// API Backend
// GET /api/files/list?type=raster&base_path=imports/
// Response: [
//   { path: "imports/mnt100_epsg3163.tif", size: "45MB", crs: "EPSG:3163" },
//   { path: "imports/rainfall.tif", size: "12MB", crs: "EPSG:3163" }
// ]
```

#### 2.3 Preview temps réel des widgets

Améliorer le système de preview pour :
- Limiter les données à 100 records pour performance
- Afficher un indicateur de chargement
- Gérer les erreurs gracieusement
- Permettre la sélection d'une entité spécifique pour preview

```typescript
// WidgetPreview.tsx
const WidgetPreview = ({ groupName, widgetId, entityId }) => {
  const { data, isLoading, error } = useWidgetPreview(
    groupName,
    widgetId,
    entityId,
    { limit: 100 } // Limiter pour performance
  );

  if (isLoading) return <Skeleton />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <iframe
      srcDoc={data.html}
      className="w-full h-[400px] border rounded"
    />
  );
};
```

---

### Phase 2.5: Exploitation des Layers Géographiques

**Contexte** : Les layers géo (raster et vector) sont importés via l'interface mais ne sont pas exploités pour le croisement de données. C'est pourtant une fonctionnalité clé pour les analyses spatiales (stats d'altitude, couverture forestière, etc.).

#### 2.5.1 Inventaire des layers disponibles

Les layers sont stockés dans `imports/` après l'import :

| Type | Exemples | Utilisations possibles |
|------|----------|------------------------|
| **Raster** | `mnt100_epsg3163.tif` (MNT), `rainfall.tif` | Stats zonales (min, max, mean, median, histogram) |
| **Vector** | `forest_cover.gpkg`, `protected_areas.gpkg` | Intersection, clip, surface par catégorie |

#### 2.5.2 Patterns de croisement récurrents

Analyser les configurations existantes pour identifier les "recettes" :

**Pattern 1: Stats raster sur polygone (shapes)**
```yaml
# Exemple: distribution altitudinale par shape
plugin: raster_stats
params:
  raster_path: imports/mnt100_epsg3163.tif
  shape_field: geometry  # Polygone de la shape
  stats: [min, max, mean, median, histogram]
```

**Pattern 2: Intersection vector (shapes)**
```yaml
# Exemple: surface forestière par shape
plugin: vector_intersection
params:
  layer_path: imports/forest_cover.gpkg
  shape_field: geometry
  category_field: forest_type
  area_unit: ha
```

**Pattern 3: Combiné raster + vector**
```yaml
# Exemple: forêt par altitude (shape_processor actuel)
plugin: shape_processor
params:
  layers:
    - name: forest_cover
      clip: true
      simplify: true
```

#### 2.5.3 Interface proposée

**Étape 1: Listing des layers importés**
- API: `GET /api/layers` → Liste fichiers raster/vector dans `imports/`
- Métadonnées: CRS, extent, colonnes (vector), bandes (raster)

**Étape 2: Suggestions automatiques**
- Détecter automatiquement les layers compatibles avec le groupe courant
- Proposer des "recettes" basées sur le type de layer:
  - Raster → suggérer `raster_stats`
  - Vector avec catégories → suggérer distribution par catégorie
  - Vector polygone → suggérer intersection/clip

**Étape 3: Formulaire de configuration**
- Nouveau widget UI: `LayerSelectField`
- Sélecteur de statistiques (checkbox: min, max, mean, etc.)
- Preview des résultats sur un échantillon

#### 2.5.4 Scope initial (Shapes uniquement)

Pour la première itération, se concentrer sur les shapes car :
- Les shapes ont une géométrie (polygone) permettant les croisements
- Les configurations de référence (`transform.yml`) montrent des exemples concrets
- Extension future possible vers plots (points → extraction valeur) et taxons (via occurrences)

**Actions requises** :

| Priorité | Action | Complexité | Status |
|----------|--------|------------|--------|
| P1 | API `/api/layers` listing des layers importés | Faible | ✅ (04/02/2026) |
| P1 | Métadonnées layers (CRS, extent, colonnes) | Moyenne | ✅ (04/02/2026) |
| P2 | `LayerSelectField` composant UI | Moyenne | ✅ (04/02/2026) |
| P2 | Enrichir plugins `raster_stats` et `land_use` avec `layer-select` | Faible | ✅ (04/02/2026) |
| P2 | Suggestions automatiques basées sur le type de layer | Moyenne | Backlog |
| P3 | Interface générique pour tous les groupes | Élevée | Backlog |

---

### Phase 3: Validation & Polish

#### 3.1 Tests end-to-end avec instance de référence ✅ FAIT

Tests créés dans `tests/e2e/test_gui_config_generation.py` (30 tests, tous verts) :

1. ✅ **TestConfigSaveLoadRoundTrip** (9 tests) — Round-trip save/load pour les 3 groupes : widgets préservés, params préservés, sources préservées
2. ✅ **TestSchemaCoversReferenceParams** (6 tests) — Schema JSON couvre les params de référence (tolère `additionalProperties` de `BasePluginParams(extra="allow")`)
3. ✅ **TestLayersWithRealFiles** (5 tests) — API layers avec vrais fichiers raster/vector via symlinks
4. ✅ **TestTransformConfigEndpoint** (3 tests) — GET /api/transform/config retourne tous les groupes, bon comptage
5. ✅ **TestTransformSourcesEndpoint** (4 tests) — GET /api/transform/sources par groupe
6. ✅ **TestConfigMergeMode** (2 tests) — Mode merge ajoute sans supprimer, mode replace remplace
7. ✅ **TestExportConfigGeneration** (1 test) — save-config génère aussi export.yml

#### 3.2 Simplifications identifiées ✅ FAIT

Analyse complète documentée dans `docs/10-roadmaps/gui-finalization/03-simplifications-config.md`.

6 simplifications identifiées, triées par priorité :

| # | Simplification | Gain | Priorité |
|---|----------------|------|----------|
| 1 | `field_aggregator` raccourci (source implicite quand field=target) | -45 lignes YAML | P1 |
| 2 | `stats_loader` auto-discovery CSV par convention de nommage | -10 lignes, zéro config | P1 |
| 3 | `statistical_summary` batch (template → expansion GUI) | -72 lignes | P2 |
| 4 | Palette couleurs centralisée (`#10b981` dupliqué 5×) | -9 doublons | P2 |
| 5 | `class_object` inféré depuis le nom du widget | -5 params explicites | P3 |
| 6 | Normalisation noms loaders (ref_key/ref_field/match_field) | Cohérence API | P3 |

**Gain total estimé** : -127 lignes sur transform.yml (-71% sur les sections concernées).
**Note** : Les chemins fichiers sont déjà relatifs (`imports/`), pas d'action requise.

#### 3.3 Documentation utilisateur

Créer une documentation interactive dans l'app :
- Tooltips sur chaque champ de formulaire
- Exemples de configurations pour chaque type de widget
- Guide "Comment ajouter un widget pour shapes"

---

## Acceptance Criteria

### Critères fonctionnels

- [ ] **Taxons** : Tous les widgets de l'instance de référence sont reproductibles via GUI
- [ ] **Plots** : Tous les widgets de l'instance de référence sont reproductibles via GUI
- [ ] **Shapes** : Tous les widgets de l'instance de référence sont reproductibles via GUI
- [ ] Les formulaires valident les paramètres avant sauvegarde
- [ ] Le YAML généré est équivalent au YAML de référence
- [ ] Les previews fonctionnent pour tous les types de widgets

### Critères techniques

- [ ] Tous les plugins `class_object_*` ont un `config_model` Pydantic
- [ ] JsonSchemaForm supporte tous les widgets UI requis
- [ ] Les tests de validation passent pour les 3 groupes
- [ ] Le sélecteur de fichiers liste correctement les fichiers raster/vector/csv

### Critères de qualité

- [ ] Pas de régression sur les fonctionnalités existantes (taxons)
- [ ] Performance : preview en < 2s pour 100 records
- [ ] Accessibilité : tous les formulaires navigables au clavier
- [ ] Erreurs claires en cas de configuration invalide

---

## Success Metrics

| Métrique | Cible | Méthode de mesure |
|----------|-------|-------------------|
| Couverture plugins | 100% | Plugins avec config_model / Total plugins |
| Widgets reproductibles | 100% | Widgets créables via GUI / Widgets référence |
| Tests validation | 100% | Tests passants / Total tests |
| Temps preview | < 2s | Mesure temps chargement iframe |

---

## Dependencies & Prerequisites

### Dépendances techniques

- JsonSchemaForm fonctionnel (✅ existant)
- API `/api/plugins` avec schémas (✅ existant)
- Système de preview widgets (✅ existant, à améliorer)

### Données requises

- Instance de référence `test-instance/niamoto-nc/` avec :
  - `config/transform.yml` (✅ 901 lignes)
  - `config/export.yml` (✅ 1604 lignes)
  - `imports/raw_plot_stats.csv` (à vérifier)
  - `imports/raw_shape_stats.csv` (à vérifier)
  - Fichiers raster (MNT, pluviométrie)
  - Fichiers vector (forest_cover, etc.)

---

## Risk Analysis & Mitigation

### Risque 1: Plugins sans schéma Pydantic

**Impact** : Élevé - Impossible de générer formulaires
**Probabilité** : Moyenne - Plusieurs plugins `class_object_*` suspectés
**Mitigation** :
- Audit exhaustif en Phase 1
- Créer les schémas manquants avant Phase 2

### Risque 2: Configurations YAML trop complexes

**Impact** : Moyen - Certains cas non gérables via formulaires
**Probabilité** : Faible - L'instance de référence est représentative
**Mitigation** :
- Permettre édition YAML directe en fallback
- Mode hybride : formulaire + YAML avancé

### Risque 3: Performance previews

**Impact** : Moyen - UX dégradée
**Probabilité** : Moyenne - Certains widgets lourds (cartes, aires)
**Mitigation** :
- Limiter données à 100 records
- Cache côté serveur
- Lazy loading des previews

### Risque 4: Complexité croisement layers géo

**Impact** : Élevé - Fonctionnalité différenciante mais complexe
**Probabilité** : Moyenne - Nombreux cas d'usage possibles
**Mitigation** :
- Commencer par shapes uniquement
- Identifier les patterns de croisement récurrents (stats raster sur polygone, intersection vector)
- Proposer des "recettes" prédéfinies avant interface générique

### Risque 5: Régression taxons

**Impact** : Élevé - Fonctionnalité existante cassée
**Probabilité** : Faible - Tests existants
**Mitigation** :
- Exécuter tests existants avant chaque PR
- Review code ciblée sur composants partagés

---

## Alternative Approaches Considered

### Alternative 1: YAML-only avec validation améliorée

**Description** : Ne pas créer de formulaires, améliorer l'éditeur YAML avec :
- Autocomplétion basée sur schémas
- Validation temps réel
- Snippets pour configurations communes

**Avantages** :
- Développement plus rapide
- Flexibilité totale

**Inconvénients** :
- Barrière d'entrée élevée pour non-devs
- Erreurs de syntaxe fréquentes

**Décision** : Rejeté - L'objectif est de rendre l'outil accessible

### Alternative 2: Wizard de configuration

**Description** : Interface pas-à-pas guidée plutôt que formulaires

**Avantages** :
- UX guidée pour débutants
- Moins d'erreurs

**Inconvénients** :
- Plus lent pour utilisateurs expérimentés
- Complexité de développement

**Décision** : Rejeté partiellement - Garder AddWidgetModal en mode wizard, mais permettre édition directe

### Alternative 3: Import de configuration externe

**Description** : Permettre d'importer des configurations YAML d'autres projets

**Avantages** :
- Réutilisation de configurations
- Partage entre équipes

**Inconvénients** :
- Ne résout pas le problème de création
- Compatibilité entre versions

**Décision** : À considérer en Phase 3 comme amélioration future

---

## Future Considerations

### Extensibilité

- Système de templates de widgets partageables
- Marketplace de configurations pré-faites
- Export/import de configurations entre projets

### Long-term Vision

- Détection automatique du type de données et suggestions intelligentes
- IA assistant pour la création de widgets (LLM-powered suggestions)
- Preview temps réel pendant l'édition (hot-reload)

---

## Documentation Plan

### À créer

1. **Guide utilisateur** : "Configurer des widgets pour shapes"
2. **Guide développeur** : "Créer un config_model Pydantic pour un plugin"
3. **Référence** : Liste complète des widgets UI supportés par JsonSchemaForm

### À mettre à jour

1. `docs/10-roadmaps/gui-finalization/02-phase-transform-export.md` - Marquer sections complétées
2. `CLAUDE.md` - Ajouter contexte sur les nouveaux composants

---

## References & Research

### Internal References

- Architecture Transform/Export : `docs/10-roadmaps/gui-finalization/02-phase-transform-export.md`
- Configuration référence transform : `test-instance/niamoto-nc/config/transform.yml`
- Configuration référence export : `test-instance/niamoto-nc/config/export.yml`
- JsonSchemaForm existant : `src/niamoto/gui/ui/src/components/forms/JsonSchemaForm.tsx`
- Plugins transformers : `src/niamoto/core/plugins/transformers/`

### Patterns documentés

- Pattern Detection (7 types) : `docs/10-roadmaps/gui-finalization/02-phase-transform-export.md:159-176`
- Class Object Types scoring : `docs/10-roadmaps/gui-finalization/02-phase-transform-export.md:179-199`
- Layout hybride ContentTab : `docs/10-roadmaps/gui-finalization/02-phase-transform-export.md:47-73`

### Configurations shapes à supporter

```yaml
# Transformers shapes complexes (transform.yml:619-901)
- class_object_field_aggregator (general_info)
- class_object_binary_aggregator (forest_cover)
- class_object_categories_extractor (land_use, forest_types)
- class_object_series_ratio_aggregator (elevation_distribution)
- class_object_categories_mapper (holdridge)
- class_object_series_matrix_extractor (forest_cover_by_elevation)
- class_object_series_by_axis_extractor (forest_types_by_elevation)
- class_object_series_extractor (fragmentation_distribution)
- shape_processor (geography - TopoJSON + layers)

# Widgets shapes complexes (export.yml:903-1257)
- concentric_rings (forest_cover - anneaux imbriqués)
- bar_plot pyramid (forest_cover_by_elevation - barmode relative)
- stacked_area_plot (forest_types_by_elevation, fragmentation_distribution)
```

---

## Checklist de Validation Finale

### Configuration Transform.yml reproductible

#### Groupe Taxons (25 widgets) ✅ Baseline
- [x] general_info (field_aggregator)
- [x] distribution_map (geospatial_extractor)
- [x] top_species (top_ranking)
- [x] distribution_substrat (binary_counter)
- [x] phenology (transform_chain) → **P3 : interface dédiée à créer ultérieurement**
- [x] dbh_distribution (binned_distribution)
- [x] ... (tous validés)

#### Groupe Plots (19 widgets)
- [ ] general_info (field_aggregator)
- [ ] map_panel (geospatial_extractor)
- [ ] top_families (class_object_series_extractor)
- [ ] top_species (class_object_series_extractor)
- [ ] dbh_distribution (class_object_series_extractor)
- [ ] strata_distribution (multi_column_extractor)
- [ ] taxonomic_distribution (multi_column_extractor)
- [ ] species_level (direct_attribute)
- [ ] living_dead_distribution (multi_column_extractor + derived)
- [ ] height (direct_attribute)
- [ ] wood_density (direct_attribute)
- [ ] basal_area (direct_attribute)
- [ ] richness (direct_attribute)
- [ ] shannon (direct_attribute)
- [ ] pielou (direct_attribute)
- [ ] simpson (direct_attribute)
- [ ] biomass (direct_attribute)

#### Groupe Shapes (12 widgets)
- [ ] shape_info (field_aggregator)
- [ ] general_info (class_object_field_aggregator)
- [ ] geography (shape_processor)
- [ ] forest_cover (class_object_binary_aggregator)
- [ ] land_use (class_object_categories_extractor)
- [ ] elevation_distribution (class_object_series_ratio_aggregator)
- [ ] holdridge (class_object_categories_mapper)
- [ ] forest_types (class_object_categories_extractor)
- [ ] forest_cover_by_elevation (class_object_series_matrix_extractor)
- [ ] forest_types_by_elevation (class_object_series_by_axis_extractor)
- [ ] fragmentation (class_object_field_aggregator)
- [ ] fragmentation_distribution (class_object_series_extractor)

### Configuration Export.yml reproductible

- [ ] index_generator pour chaque groupe (taxons, plots, shapes)
- [ ] Tous les widgets avec leurs paramètres de visualisation
- [ ] Transformations de données (bins_to_df, monthly_data, nested_dict_to_long, etc.)
- [ ] Couleurs et styles configurables
