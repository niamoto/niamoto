# Référence des plugins Transform

Catalogue complet des plugins disponibles pour les transformations Niamoto, avec paramètres et exemples YAML.

## Agrégation

### field_aggregator

Agrège plusieurs champs de différentes sources en une sortie unifiée.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `fields` | Liste | _(requis)_ | Champs à agréger (min 1) |
| `fields[].source` | str | `"occurrences"` | Entité source |
| `fields[].field` | str | _(requis)_ | Nom du champ (notation pointée: `extra_data.image`) |
| `fields[].target` | str | _(requis)_ | Nom dans la sortie |
| `fields[].transformation` | str | `"direct"` | `direct`, `count`, `sum`, `stats` |
| `fields[].units` | str | `""` | Unité (`ha`, `m`, `km2`) |
| `fields[].format` | str | — | `boolean`, `url`, `text`, `number` |

```yaml
plugin: field_aggregator
params:
  fields:
    - source: taxons
      field: full_name
      target: full_name
    - source: occurrences
      field: id
      target: occurrences_count
      transformation: count
```

---

### statistical_summary

Calcule min, mean, max, median, std sur un champ numérique.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | `"occurrences"` | Entité source |
| `field` | str | _(requis)_ | Champ numérique |
| `stats` | Liste | `[min, mean, max]` | Statistiques à calculer |
| `units` | str | `""` | Unité (`cm`, `m`, `g/cm3`) |
| `max_value` | float | `100` | Valeur maximum pour les jauges |

```yaml
plugin: statistical_summary
params:
  source: occurrences
  field: dbh
  stats: [max, mean, min]
  units: cm
  max_value: 500
```

---

### binary_counter

Compte les valeurs binaires (0/1, true/false).

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | `"occurrences"` | Entité source |
| `field` | str | _(requis)_ | Champ binaire |
| `true_label` | str | `"oui"` | Label pour true/1 |
| `false_label` | str | `"non"` | Label pour false/0 |
| `include_percentages` | bool | `false` | Inclure les pourcentages |

```yaml
plugin: binary_counter
params:
  source: occurrences
  field: in_um
  true_label: UM
  false_label: NUM
  include_percentages: true
```

---

### top_ranking

Top N des valeurs les plus fréquentes.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | `"occurrences"` | Entité source |
| `field` | str | _(requis)_ | Champ à classer |
| `count` | int | `10` | Nombre de résultats (1-100) |
| `mode` | str | `"direct"` | `direct`, `hierarchical`, `join` |
| `hierarchy_table` | str | — | Table hiérarchique (requis pour les modes `hierarchical` et `join`) |
| `target_ranks` | Liste | — | Rangs cibles (`family`, `genus`) |

```yaml
plugin: top_ranking
params:
  source: occurrences
  field: species
  count: 10
  mode: direct
```

---

## Distribution

### binned_distribution

Distribution par intervalles sur un champ numérique.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | `"occurrences"` | Entité source |
| `field` | str | _(requis)_ | Champ numérique |
| `bins` | Liste float | _(requis)_ | Bornes des intervalles (min 2 valeurs, ordre croissant) |
| `labels` | Liste str | — | Labels (doit avoir `len(bins)-1` éléments) |
| `include_percentages` | bool | `false` | Inclure les pourcentages |
| `x_label` | str | — | Label axe X |
| `y_label` | str | — | Label axe Y |

```yaml
plugin: binned_distribution
params:
  source: occurrences
  field: elevation
  bins: [0, 200, 400, 600, 800, 1000, 1200, 1400, 1600]
  include_percentages: true
  x_label: "ELEVATION (m)"
  y_label: "%"
```

---

### categorical_distribution

Distribution catégorielle (comptage par catégorie).

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | `"occurrences"` | Entité source |
| `field` | str | _(requis)_ | Champ catégoriel |
| `categories` | Liste | `[]` | Catégories à inclure (auto-détection si vide) |
| `labels` | Liste str | `[]` | Labels personnalisés |
| `include_percentages` | bool | `false` | Inclure les pourcentages |

```yaml
plugin: categorical_distribution
params:
  source: occurrences
  field: holdridge
  categories: ["3.0", "2.0", "1.0"]
  include_percentages: true
```

---

### time_series_analysis

Analyse temporelle (phénologie, saisonnalité).

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | `"occurrences"` | Entité source |
| `field` | str | — | Champ unique à analyser |
| `fields` | Dict | `{}` | Plusieurs champs (`{label: field_name}`) |
| `time_field` | str | `"month_obs"` | Champ temporel |
| `labels` | Liste str | _(requis, 12 éléments)_ | Labels des périodes |

```yaml
plugin: time_series_analysis
params:
  source: occurrences
  fields:
    fleur: flower
    fruit: fruit
  time_field: month_obs
  labels: [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]
```

---

## Extraction

### geospatial_extractor

Extraction de données géospatiales en GeoJSON.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | `"occurrences"` | Entité source |
| `field` | str | _(requis)_ | Champ géométrie |
| `format` | str | `"geojson"` | Format de sortie |
| `properties` | Liste str | `[]` | Propriétés à inclure |
| `group_by_coordinates` | bool | `false` | Grouper les points identiques |
| `extract_children` | bool | `false` | Extraire les entités enfants |

```yaml
plugin: geospatial_extractor
params:
  source: occurrences
  field: geo_pt
  format: geojson
  group_by_coordinates: true
```

---

### direct_attribute

Extraction directe d'un attribut unique.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | `"occurrences"` | Entité source |
| `field` | str | _(requis)_ | Champ à extraire |
| `units` | str | `""` | Unité |
| `max_value` | float | — | Valeur maximum |
| `format` | str | — | `number`, `percentage`, `text` |
| `precision` | int | — | Décimales (0-10) |

```yaml
plugin: direct_attribute
params:
  source: plots
  field: shannon
  units: ""
  max_value: 5
  format: number
  precision: 2
```

---

## Géospatial

### raster_stats

Statistiques zonales sur un fichier raster.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `raster_path` | str | _(requis)_ | Chemin du fichier raster (.tif) |
| `shape_field` | str | `"geometry"` | Champ géométrie des zones |
| `stats` | Liste | toutes | `min`, `max`, `mean`, `median`, `sum`, `count`, `std`, `histogram` |
| `bins` | int | `10` | Nombre d'intervalles histogramme |
| `band` | int | `1` | Bande raster à utiliser |
| `units` | str | `""` | Unité des valeurs |
| `area_unit` | str | `"ha"` | Unité de surface (`ha`, `km2`, `m2`) |

```yaml
plugin: raster_stats
params:
  raster_path: imports/mnt100_epsg3163.tif
  stats: [min, max, mean, median]
  units: m
  area_unit: ha
```

---

### land_use_analysis

Analyse d'usage des sols par croisement de couches vectorielles.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `layers` | Liste | _(requis)_ | Couches à analyser |
| `layers[].path` | str | _(requis)_ | Chemin du fichier vector (.gpkg) |
| `layers[].field` | str | `""` | Champ catégorie |
| `layers[].categories` | Liste str | _(requis)_ | Catégories à analyser |
| `shape_field` | str | `"geometry"` | Champ géométrie des zones |
| `area_unit` | str | `"ha"` | Unité de surface |

```yaml
plugin: land_use_analysis
params:
  layers:
    - path: imports/substrates.gpkg
      field: type
      categories: [UM, NUM]
  shape_field: geometry
  area_unit: ha
```

---

## Class Objects (sources CSV)

Ces plugins extraient des données depuis des fichiers CSV de statistiques pré-calculées. Ils attendent un paramètre `class_object` qui identifie le groupe de colonnes dans le CSV.

### class_object_series_extractor

Extraction de séries numériques depuis les class objects.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | _(requis)_ | Source CSV (ex: `plot_stats`) |
| `class_object` | str | _(requis)_ | Nom du class object dans le CSV |
| `size_field.input` | str | — | Colonne d'entrée pour les catégories |
| `size_field.output` | str | — | Nom de sortie |
| `value_field.input` | str | — | Colonne d'entrée pour les valeurs |
| `value_field.output` | str | — | Nom de sortie |
| `orientation` | str | `"v"` | `v` (vertical) ou `h` (horizontal) |
| `sort_order` | str | — | `ascending` ou `descending` |

```yaml
plugin: class_object_series_extractor
params:
  source: plot_stats
  class_object: dbh
  size_field:
    input: class_name
    output: tops
    numeric: true
    sort: true
  value_field:
    input: class_value
    output: counts
    numeric: true
  orientation: v
  sort_order: descending
```

---

### binary_aggregator

Agrégation binaire depuis les class objects (forêt/hors-forêt).

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `source` | str | _(requis)_ | Source CSV |
| `class_object` | str | _(requis)_ | Nom du class object |
| `true_label` | str | `"oui"` | Label pour la valeur positive |
| `false_label` | str | `"non"` | Label pour la valeur négative |

```yaml
plugin: binary_aggregator
params:
  source: shape_stats
  class_object: cover_forest
  true_label: "Forêt"
  false_label: "Hors-forêt"
```

---

### class_object_categories_extractor

Extraction de valeurs pour des catégories ordonnées.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `class_object` | str | _(requis)_ | Nom du class object |
| `categories_order` | Liste str | — | Ordre des catégories (auto-détecté si absent) |
| `count` | int | `10` | Max catégories en auto-détection |

```yaml
plugin: class_object_categories_extractor
params:
  class_object: land_use
  categories_order: [NUM, UM, Sec, Humide]
```

---

## Widgets de visualisation

Les widgets ci-dessous sont configurés dans `export.yml` et déterminent le rendu HTML.

### bar_plot

Graphique en barres avec groupement, empilement, gradients.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `x_axis` | str | _(requis)_ | Champ axe X |
| `y_axis` | str | _(requis)_ | Champ axe Y |
| `barmode` | str | `"group"` | `group`, `stack`, `relative` |
| `orientation` | str | `"v"` | `v` ou `h` |
| `sort_order` | str | — | `ascending`, `descending` |
| `gradient_color` | str | — | Couleur de base hex (`#10b981`) |
| `auto_color` | bool | `false` | Couleurs automatiques harmonieuses |
| `transform` | str | — | `bins_to_df`, `monthly_data`, `pyramid_chart` |
| `title` | str | — | Titre du graphique |

---

### donut_chart

Graphique en anneau.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `labels_field` | str | — | Champ labels |
| `values_field` | str | — | Champ valeurs |
| `hole_size` | float | `0.3` | Taille du trou central (0-1) |
| `text_info` | str | — | `percent`, `label`, `value`, `percent+label` |
| `title` | str | — | Titre |

---

### radial_gauge

Jauge radiale pour afficher une valeur unique.

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `stat_to_display` | str | — | `mean`, `max`, `min`, `median` |
| `min_value` | float | `0` | Minimum de la jauge |
| `max_value` | float | — | Maximum de la jauge |
| `unit` | str | — | Symbole unité |
| `bar_color` | str | `"cornflowerblue"` | Couleur de la barre |
| `style_mode` | str | `"classic"` | `classic`, `minimal`, `gradient`, `contextual` |

---

### info_grid

Grille d'informations (KPI, métadonnées).

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `items` | Liste | _(requis)_ | Éléments à afficher |
| `items[].label` | str | _(requis)_ | Étiquette |
| `items[].source` | str | — | Chemin en notation pointée (`species_count.value`) |
| `items[].unit` | str | — | Unité |
| `items[].format` | str | — | `number`, `image`, `map`, `stats` |
| `grid_columns` | int | — | Nombre de colonnes (1-6) |

---

### interactive_map

Carte interactive (points scatter ou choroplèthe).

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `map_type` | str | `"scatter_map"` | `scatter_map` ou `choropleth_map` |
| `latitude_field` | str | — | Champ latitude (scatter) |
| `longitude_field` | str | — | Champ longitude (scatter) |
| `zoom` | float | `9.0` | Niveau de zoom initial |
| `auto_zoom` | bool | `false` | Ajuster le zoom automatiquement |
| `map_style` | str | `"carto-positron"` | Style de fond de carte |
| `use_topojson` | bool | `false` | Optimiser en TopoJSON |

---

## Types de champs du formulaire

Le GUI génère automatiquement les formulaires depuis le schéma Pydantic de chaque plugin :

| Indicateur `ui:widget` | Composant | Utilisation |
|------------------------|-----------|-------------|
| `text` | Champ texte | Titres, labels |
| `number` | Champ numérique | Bornes, compteurs |
| `checkbox` | Case à cocher | Booléens |
| `select` | Liste déroulante | Valeurs enum |
| `entity-select` | Sélecteur d'entité | Sources de données |
| `transform-source-select` | Sélecteur de source | Sources configurées |
| `layer-select` | Sélecteur de layer | Fichiers raster/vector |
| `tags` | Liste de tags | Catégories, statistiques |
| `key-value-pairs` | Paires clé-valeur | Mappings, labels |
| `json` | Éditeur JSON | Structures complexes |
| `array` | Liste éditable | Champs répétés |

> **Note :** En plus de `ui:widget`, le contrat de génération des formulaires GUI supporte également des clés `ui_component` pour des composants spécialisés : `field_selector`, `multi_select`, `array_number`, `array_text`. Ces clés peuvent être définies dans le `json_schema_extra` du modèle Pydantic du plugin.
