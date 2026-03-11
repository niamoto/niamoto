# Guide : Configurer les widgets Transform via le GUI

Ce guide explique comment ajouter et configurer des widgets de transformation pour chaque groupe (taxons, plots, shapes) via l'interface graphique Niamoto.

## Lancer le GUI

```bash
niamoto gui                    # Port par défaut (5000)
niamoto gui --port 8080        # Changer le port
```

L'interface s'ouvre dans le navigateur avec 3 onglets principaux : **Import**, **Transform**, **Export**.

---

## Concepts

### Groupes

Un **groupe** (`group_by`) est une entité de référence autour de laquelle les données sont agrégées :

| Groupe | Description | Exemple |
|--------|-------------|---------|
| `taxons` | Espèces/taxons dans la taxonomie | Distribution d'altitude par espèce |
| `plots` | Parcelles d'inventaire | Richesse spécifique par parcelle |
| `shapes` | Zones géographiques (provinces, communes) | Couvert forestier par province |

### Sources

Chaque groupe a une ou plusieurs **sources** de données :

- **Source principale** : entité de la base (occurrences, plots, shapes)
- **Source CSV** : fichier statistique externe (`imports/raw_plot_stats.csv`)

### Widgets

Un **widget** combine un **transformer** (calcul) et un **widget de visualisation** (affichage) :

```
Source données → Transformer → Résultat JSON → Widget export → Visualisation HTML
```

---

## Ajouter un widget

### Depuis l'onglet Transform

1. Sélectionner le groupe dans le menu latéral
2. Cliquer sur **"+ Ajouter un widget"**
3. Choisir une des 3 méthodes :

#### Suggestions (recommandé)

Le GUI analyse les données disponibles et propose des widgets adaptés :

- Champ numérique continu ? Distribution par intervalles (`binned_distribution`)
- Champ avec 2 valeurs ? Compteur binaire (`binary_counter`)
- Champ catégoriel (3-12 valeurs) ? Distribution catégorielle (`categorical_distribution`)
- Champ géographique ? Carte interactive (`geospatial_extractor`)

Cliquer sur une suggestion pour la personnaliser puis l'ajouter.

#### Widget combiné

Pour créer des widgets multi-champs :

1. Choisir un groupe sémantique (ex: "Données spatiales", "Traits fonctionnels")
2. Sélectionner les champs à inclure
3. Le GUI génère un widget combiné adapté

#### Widget personnalisé (wizard 4 étapes)

1. **Transformer** : choisir le plugin de calcul
2. **Paramètres transformer** : configurer les champs, sources, options
3. **Widget** : choisir le type de visualisation
4. **Paramètres widget** : couleurs, titres, axes

---

## Configurer un widget existant

Cliquer sur un widget dans la liste de gauche pour afficher ses détails :

### Onglet Preview

Aperçu en direct du rendu HTML. Utile pour vérifier la configuration avant export.

### Onglet Paramètres

Formulaire généré automatiquement depuis le schéma du plugin :

| Type de champ | Description | Exemple |
|---------------|-------------|---------|
| Texte | Saisie libre | Titre, labels d'axes |
| Nombre | Avec bornes min/max | `max_value`, `count` |
| Case à cocher | Booléen | `include_percentages` |
| Sélecteur de source | Dropdown dynamique | `source: occurrences` |
| Sélecteur d'entité | Dropdown des entités importées | `source: taxons` |
| Sélecteur de layer | Fichiers raster/vector dans imports/ | `raster_path: imports/mnt.tif` |
| Liste de tags | Chips avec auto-complétion | `categories`, `stats` |
| Paires clé-valeur | Mapping éditable | `labels`, `class_mapping` |
| JSON | Éditeur brut pour structures complexes | `hierarchy_config` |

### Onglet YAML

Aperçu en lecture seule du YAML qui sera écrit dans `transform.yml` et `export.yml`.

---

## Exemples par groupe

### Taxons : distribution d'altitude

Transformer `binned_distribution` + Widget `bar_plot` :

```yaml
# transform.yml
elevation_binned_distribution_bar_plot:
  plugin: binned_distribution
  params:
    source: occurrences
    field: elevation
    bins: [0, 200, 400, 600, 800, 1000, 1200, 1400, 1600]
    include_percentages: true
    x_label: "ELEVATION (m)"
    y_label: "%"
```

Dans le GUI :
1. Suggestions > choisir "Distribution d'élévation"
2. Modifier les intervalles (`bins`) via le formulaire
3. Ajouter des labels d'axes

### Taxons : statistiques par jauge

Transformer `statistical_summary` + Widget `radial_gauge` :

```yaml
# transform.yml
dbh_statistical_summary_radial_gauge:
  plugin: statistical_summary
  params:
    source: occurrences
    field: dbh
    stats: [max, mean, min]
    units: cm
    max_value: 500
```

Dans le GUI :
1. Widget personnalisé > Transformer: `statistical_summary`
2. Champ: `dbh`, Stats: cocher max/mean/min
3. Widget: `radial_gauge`, max_value: 500

### Plots : top 10 familles (depuis CSV)

Transformer `class_object_series_extractor` + Widget `bar_plot` :

```yaml
# transform.yml
top10_family_series_extractor_bar_plot:
  plugin: class_object_series_extractor
  params:
    source: plot_stats           # Source CSV (pas occurrences)
    class_object: top10_family
    size_field:
      input: class_name
      output: tops
      numeric: false
      sort: false
    value_field:
      input: class_value
      output: counts
      numeric: true
    count: 10
    orientation: h
    x_axis: counts
    y_axis: tops
    sort_order: descending
    auto_color: true
```

**Pré-requis** : avoir ajouté une source CSV dans l'onglet Sources :
1. Onglet Sources > "Ajouter une source CSV"
2. Sélectionner `imports/raw_plot_stats.csv`
3. Le GUI détecte automatiquement les `class_objects` disponibles

### Shapes : couvert forestier binaire

Transformer `binary_aggregator` + Widget `donut_chart` :

```yaml
# transform.yml
cover_forest_binary_aggregator_donut_chart:
  plugin: binary_aggregator
  params:
    source: shape_stats
    class_object: cover_forest
    true_label: "Forêt"
    false_label: "Hors-forêt"
```

### Shapes : analyse raster (altitude)

Transformer `raster_stats` :

```yaml
# transform.yml
elevation_raster_stats:
  plugin: raster_stats
  params:
    raster_path: imports/mnt100_epsg3163.tif
    stats: [min, max, mean, median]
    units: m
    area_unit: ha
```

Dans le GUI :
1. Widget personnalisé > Transformer: `raster_stats`
2. Cliquer sur le sélecteur de layer > choisir le fichier .tif
3. Cocher les statistiques voulues

---

## Opérations sur les widgets

| Action | Comment |
|--------|---------|
| **Réordonner** | Glisser-déposer dans la liste de gauche |
| **Dupliquer** | Survol > icone de copie (le GUI demande un nouvel identifiant) |
| **Supprimer** | Survol > icone poubelle (confirmation demandée) |
| **Rechercher** | Barre de recherche en haut de la liste (filtre par titre, ID, plugin) |

---

## Sources de données

### Ajouter une source CSV

Nécessaire pour les groupes `plots` et `shapes` qui utilisent des statistiques pré-calculées :

1. Onglet **Sources** du groupe
2. Cliquer **"Ajouter une source CSV"**
3. Sélectionner le fichier dans `imports/`
4. Le GUI détecte automatiquement :
   - Les colonnes disponibles
   - Les `class_objects` (pour les plugins `class_object_*`)
   - La relation avec l'entité de référence

### Convention de nommage

| Fichier | Source auto-détectée | Grouping |
|---------|---------------------|----------|
| `imports/raw_plot_stats.csv` | `plot_stats` | `plots` |
| `imports/raw_shape_stats.csv` | `shape_stats` | `shapes` |

---

## Layers géographiques

Les fichiers raster (.tif) et vector (.gpkg) dans `imports/` sont automatiquement détectés par le GUI.

### Utilisation dans les formulaires

Les plugins `raster_stats` et `land_use_analysis` proposent un **sélecteur de layer** :

- Filtre par type (raster ou vector)
- Affiche les métadonnées (CRS, dimensions, colonnes)
- Chemin relatif automatique (`imports/fichier.tif`)

### Types supportés

| Extension | Type | Utilisation |
|-----------|------|-------------|
| `.tif`, `.tiff` | Raster | Stats zonales (altitude, pluviométrie) |
| `.gpkg` | Vector | Intersection, surface par catégorie |
| `.shp` | Vector | Intersection (déconseillé, préférer .gpkg) |
| `.geojson` | Vector | Petites couches, visualisation |

---

## Sauvegarder

Le bouton **"Sauvegarder"** écrit simultanément :

- `config/transform.yml` : configuration des transformations
- `config/export.yml` : configuration de l'export (widgets de visualisation)

Le GUI crée automatiquement un backup avant chaque sauvegarde dans `config/backups/`.

### Modes de sauvegarde

| Mode | Comportement |
|------|-------------|
| **Replace** (défaut) | Remplace tous les widgets du groupe |
| **Merge** | Ajoute les nouveaux widgets sans toucher les existants |

---

## Exécuter la transformation

Après configuration :

```bash
niamoto transform    # Exécute toutes les transformations
niamoto export       # Génère le site statique
```

Ou via le GUI : onglet Transform > bouton "Exécuter".
