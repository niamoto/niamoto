# Phase 1 - Import : Enrichissement, Formulaires et Validation

## Vue d'ensemble

La phase Import constitue le point d'entrée des données dans Niamoto. Au-delà de l'import brut, cette phase doit offrir :

1. **Gestion via formulaire** : Édition visuelle de `import.yml` sans YAML
2. **Enrichissement** : Augmentation des données via APIs externes
3. **Dashboard de validation** : Exploration et détection d'anomalies post-import

---

## 1. Gestion de l'Import via Formulaires

### 1.1 État actuel

L'import.yml de référence définit trois types d'entités :

```yaml
entities:
  datasets:           # Données principales (occurrences)
  references:         # Référentiels (taxons, plots, shapes)
metadata:
  layers:             # Couches géographiques (rasters, vectors)
```

### 1.2 Architecture des Formulaires

#### Formulaire Principal - Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│  Configuration Import                                    [YAML] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─── Datasets ─────────────────────────────────────────────┐  │
│  │  occurrences                              [CSV] ✓ Configuré │
│  │    → imports/occurrences.csv (12,345 lignes)              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─── Référentiels ─────────────────────────────────────────┐  │
│  │  taxons          [Dérivé] ✓   plots     [CSV] ✓           │  │
│  │  shapes          [Multi-GeoPackage] ✓                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─── Couches Géographiques ────────────────────────────────┐  │
│  │  forest_cover [Vector]  elevation [Raster]  rainfall ... │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [+ Ajouter Dataset]  [+ Ajouter Référentiel]  [+ Ajouter Couche] │
└─────────────────────────────────────────────────────────────────┘
```

#### Formulaire Dataset (Occurrences)

```typescript
interface DatasetFormProps {
  name: string
  connector: {
    type: 'file' | 'database' | 'api'
    format: 'csv' | 'xlsx' | 'parquet' | 'geojson'
    path: string
    // Options CSV
    delimiter?: string
    encoding?: string
    skip_rows?: number
  }
  // Preview des premières lignes
  preview?: DataPreview
}
```

**Champs du formulaire :**
- Nom du dataset
- Source : Fichier local / URL / Base de données
- Format avec options spécifiques (délimiteur CSV, feuille Excel)
- Encodage (auto-détection + override manuel)
- Preview des 10 premières lignes

#### Formulaire Référentiel Taxonomique (Dérivé)

Le cas `taxons` est particulier : extraction hiérarchique depuis les occurrences.

```
┌─────────────────────────────────────────────────────────────────┐
│  Référentiel Taxonomique                                        │
├─────────────────────────────────────────────────────────────────┤
│  Type: ● Dérivé (extrait du dataset)  ○ Fichier externe        │
│                                                                 │
│  Source: [occurrences ▼]                                        │
│                                                                 │
│  Niveaux hiérarchiques:                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. family    ← Colonne: [family ▼]                      │  │
│  │  2. genus     ← Colonne: [genus ▼]                       │  │
│  │  3. species   ← Colonne: [species ▼]                     │  │
│  │  4. infra     ← Colonne: [infra ▼]                       │  │
│  │  [+ Ajouter niveau]                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Identifiant: [id_taxonref ▼]   Nom: [taxaname ▼]              │
│  Stratégie ID: ● Hash  ○ Séquence  ○ Colonne existante         │
│  Lignes incomplètes: ● Ignorer  ○ Erreur  ○ Valeur par défaut  │
│                                                                 │
│  ┌─── Enrichissement API ───────────────────────────────────┐  │
│  │  [✓] Activer l'enrichissement                            │  │
│  │  → Voir section Enrichissement                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### Formulaire Référentiel Shapes (Multi-sources)

```
┌─────────────────────────────────────────────────────────────────┐
│  Référentiel Géographique                                       │
├─────────────────────────────────────────────────────────────────┤
│  Type: spatial                                                  │
│                                                                 │
│  Sources:                                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Nom            Fichier                    Champ nom     │  │
│  │  ─────────────────────────────────────────────────────── │  │
│  │  Provinces      imports/shapes/provinces.gpkg    nom     │  │
│  │  Communes       imports/shapes/communes.gpkg     nom     │  │
│  │  Aires protégées imports/shapes/protected.gpkg  libelle  │  │
│  │  Substrats      imports/shapes/substrate.gpkg   label    │  │
│  │  ...                                                     │  │
│  │  [+ Ajouter source]                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Schéma de sortie:                                              │
│  - id (auto)                                                    │
│  - name (string) ← champ nom de chaque source                   │
│  - location (geometry) ← géométrie WKT                          │
│  - entity_type (string) ← nom de la source                      │
└─────────────────────────────────────────────────────────────────┘
```

#### Formulaire Couches Géographiques (Metadata)

```
┌─────────────────────────────────────────────────────────────────┐
│  Couches Géographiques                                          │
├─────────────────────────────────────────────────────────────────┤
│  Ces couches sont utilisées pour l'extraction de valeurs        │
│  lors des transformations (altitude, pluviométrie, etc.)        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Nom           Type      Fichier              Description │  │
│  │  ─────────────────────────────────────────────────────── │  │
│  │  elevation     Raster    mnt100_epsg3163.tif  MNT 100m   │  │
│  │  rainfall      Raster    rainfall_epsg3163.tif Pluie     │  │
│  │  holdridge     Raster    holdridge_nc.tif     Zones vie  │  │
│  │  forest_cover  Vector    amap_carto.gpkg      Forêt      │  │
│  │  [+ Ajouter couche]                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ⓘ Les couches raster doivent être en projection compatible    │
│    avec les données (EPSG:3163 pour NC ou WGS84)               │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Actions Requises - Formulaires

| Priorité | Action | Complexité |
|----------|--------|------------|
| P1 | Composant `ImportConfigForm` avec tabs par type d'entité | Moyenne |
| P1 | Formulaire dataset avec sélection fichier + preview | Moyenne |
| P1 | Formulaire référentiel dérivé (taxons) avec mapping colonnes | Moyenne |
| P1 | API backend pour lecture/écriture import.yml | Faible |
| P2 | Formulaire shapes multi-sources avec drag & drop réordonnancement | Moyenne |
| P2 | Formulaire metadata layers avec validation type/projection | Moyenne |
| P2 | Auto-complétion des noms de colonnes depuis preview | Faible |
| P3 | Import de configuration depuis un autre projet | Faible |

---

## 2. Enrichissement API

### 2.1 État actuel

Le plugin `ApiTaxonomyEnricher` existe et supporte :
- Authentification multi-méthodes (API key, Bearer, OAuth)
- Cache des résultats
- Rate limiting
- Mapping de réponse flexible (dot notation)

Configuration actuelle dans import.yml :
```yaml
enrichment:
  - plugin: api_taxonomy_enricher
    enabled: false
    config:
      api_url: https://api.endemia.nc/v1/taxons
      auth_method: api_key
      # ... mapping des champs
```

### 2.2 Interface d'Enrichissement

```
┌─────────────────────────────────────────────────────────────────┐
│  Enrichissement Taxonomique                          [Désactivé]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─── Source API ───────────────────────────────────────────┐  │
│  │  API: [Endemia NC ▼]  (+ Ajouter API personnalisée)      │  │
│  │  URL: https://api.endemia.nc/v1/taxons                   │  │
│  │                                                          │  │
│  │  Authentification: [API Key ▼]                           │  │
│  │  Clé: [••••••••••••]  Location: [Header ▼] Nom: [apiKey] │  │
│  │                                                          │  │
│  │  [Tester la connexion]  ✓ Connexion OK                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─── Mapping des Champs ───────────────────────────────────┐  │
│  │  Champ local         ←  Champ API                        │  │
│  │  ─────────────────────────────────────────────────────── │  │
│  │  endemic             ←  endemique                        │  │
│  │  protected           ←  protected                        │  │
│  │  redlist_cat         ←  categorie_uicn                   │  │
│  │  image_thumb         ←  image.small_thumb                │  │
│  │  [+ Ajouter mapping]                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─── Options ──────────────────────────────────────────────┐  │
│  │  Champ de requête: [taxaname ▼]                          │  │
│  │  Rate limit: [2] req/sec   [✓] Cache résultats           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [Prévisualiser sur 5 taxons]  [Enrichir maintenant]           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Chaînage d'APIs

Pour certains cas, plusieurs APIs doivent être appelées en séquence :

```
┌─────────────────────────────────────────────────────────────────┐
│  Chaîne d'Enrichissement                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. [Endemia NC]  → endemic, protected, images                  │
│         ↓                                                       │
│  2. [GBIF Species] → gbifKey, synonyms                          │
│         ↓                                                       │
│  3. [IUCN RedList] → redlist_status, population_trend           │
│                                                                 │
│  [+ Ajouter étape]  [↑↓ Réordonner]                             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Actions Requises - Enrichissement

| Priorité | Action | Complexité |
|----------|--------|------------|
| P1 | Intégrer `ApiEnrichmentConfig` dans le nouveau workflow `/flow` | Moyenne |
| P1 | Bouton "Enrichir maintenant" sur référentiels existants | Faible |
| P1 | Preview enrichissement sur N taxons avant validation | Moyenne |
| P2 | Templates d'APIs préconfigurés (Endemia, GBIF, IUCN) | Moyenne |
| P2 | Interface de chaînage d'APIs | Moyenne |
| P3 | Généralisation aux autres référentiels (plots, shapes) | Élevée |

---

## 3. Dashboard Post-Import : Exploration et Validation

### 3.1 Objectif

Une fois toutes les sources importées, proposer un dashboard permettant de :
- **Explorer** les données de façon interactive
- **Détecter** les anomalies et incohérences
- **Valider** la qualité avant transformation

### 3.2 Vue d'Ensemble du Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Dashboard Import                                    Dernière MàJ: 23/12/24 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─── Résumé ──────────────────────────────────────────────────────────┐   │
│  │  Occurrences: 12,345    Taxons: 1,234    Plots: 48    Shapes: 156   │   │
│  │  Qualité globale: ████████████░░░░ 78%                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [Distribution] [Complétude] [Taxonomie] [Validation] [Couverture]         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Vue active                                  │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─── Alertes ─────────────────────────────────────────────────────────┐   │
│  │  ⚠ 23 occurrences hors limites NC  │  ⚠ 12 taxons orphelins        │   │
│  │  ⚠ Colonne 'dbh' : 5% valeurs nulles                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Vues du Dashboard

#### Vue 1 : Distribution Spatiale

Carte interactive des occurrences avec :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Distribution Spatiale des Occurrences                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────┐  Filtres:                   │
│  │                                            │  Taxon: [Tous ▼]            │
│  │       [Carte Leaflet]                      │  Plot: [Tous ▼]             │
│  │                                            │  Année: [2020-2024]         │
│  │    • Points occurrences                    │                             │
│  │    ■ Shapes de référence                   │  Coloration:                │
│  │    ○ Plots                                 │  ● Densité                  │
│  │                                            │  ○ Par taxon                │
│  │    [Zoom NC]                               │  ○ Par année                │
│  │                                            │  ○ Par plot                 │
│  └────────────────────────────────────────────┘                             │
│                                                                             │
│  Statistiques spatiales:                                                    │
│  - Étendue: 164.0°E - 167.5°E, 19.5°S - 22.7°S                             │
│  - Points hors NC: 23 (0.2%)  ⚠ [Voir liste]                               │
│  - Densité max: Montagne des Sources (342 occ/km²)                         │
│  - Zones sans données: [Voir carte]                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Détections pertinentes :**
- Points en mer (coordonnées invalides)
- Points hors de la Nouvelle-Calédonie
- Clusters anormaux (doublons potentiels)
- Zones vides (biais d'échantillonnage)

#### Vue 2 : Complétude des Données

Heatmap de complétude par colonne et par source :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Complétude des Données                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Occurrences (12,345 lignes)                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Colonne          Complétude    Unique     Type détecté             │   │
│  │  ───────────────────────────────────────────────────────────────── │   │
│  │  taxaname         ████████████ 100%  1,234   string                 │   │
│  │  id_taxonref      ████████████ 100%  1,234   identifier             │   │
│  │  lon              ████████████ 100%  8,456   numeric (coord)        │   │
│  │  lat              ████████████ 100%  8,234   numeric (coord)        │   │
│  │  dbh              ████████░░░░  95%  2,345   numeric (measure)      │   │
│  │  height           ████████░░░░  92%  456     numeric (measure)      │   │
│  │  strate           ██████░░░░░░  78%  5       categorical            │   │
│  │  phenology        ████░░░░░░░░  45%  8       categorical        ⚠  │   │
│  │  notes            ██░░░░░░░░░░  23%  1,234   text                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Seuils: ⚠ < 50%   ✗ < 10%                                                 │
│                                                                             │
│  [Exporter rapport] [Configurer seuils]                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Indicateurs clés :**
- Pourcentage de valeurs non-nulles
- Nombre de valeurs distinctes
- Type de données détecté
- Alertes sur colonnes critiques incomplètes

#### Vue 3 : Cohérence Taxonomique

Analyse de la hiérarchie taxonomique :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Cohérence Taxonomique                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Hiérarchie:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Niveau       Nombre    Orphelins   Occurrences                     │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  Famille      87        0           12,345                          │   │
│  │  ├─ Genre     342       3 ⚠         12,312                          │   │
│  │  │  ├─ Espèce 1,089     8 ⚠         12,156                          │   │
│  │  │  │  └─ Infra 156     1           3,421                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ⚠ Orphelins détectés (12 taxons):                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  - Psychotria sp. (genre sans famille)                              │   │
│  │  - Unknown genus (espèce sans genre)                                │   │
│  │  - [Voir tous...]                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Distribution des occurrences par rang:                                     │
│  Espèce ████████████████████████████████████ 89%                           │
│  Genre  ████████ 8%                                                        │
│  Famille ██ 2%                                                             │
│  Infra   █ 1%                                                              │
│                                                                             │
│  [Arbre taxonomique interactif]                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Détections pertinentes :**
- Taxons orphelins (sans parent)
- Synonymes potentiels (noms similaires)
- Incohérences de rang
- Taxons sans occurrences

#### Vue 4 : Validation des Valeurs

Détection d'outliers et valeurs aberrantes :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Validation des Valeurs                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Colonnes numériques:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  dbh (cm)                              height (m)                   │   │
│  │  ┌──────────────────────────┐          ┌──────────────────────────┐│   │
│  │  │     [Boxplot]            │          │     [Boxplot]            ││   │
│  │  │  Min: 0.5  Max: 245      │          │  Min: 0.3  Max: 45       ││   │
│  │  │  Médiane: 12.3           │          │  Médiane: 8.2            ││   │
│  │  │  ⚠ 3 outliers > 200      │          │  ⚠ 1 outlier > 40        ││   │
│  │  └──────────────────────────┘          └──────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Corrélations attendues:                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DBH vs Height: r=0.85 ✓ (attendu: >0.7)                            │   │
│  │  Altitude vs Précipitations: r=0.72 ✓                               │   │
│  │  [Scatter plot interactif]                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Valeurs suspectes (hors intervalles biologiques):                         │
│  - DBH > 200 cm : 3 enregistrements [Voir]                                 │
│  - Height > 40 m pour arbuste : 1 enregistrement [Voir]                    │
│  - Altitude négative : 0 enregistrement ✓                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Règles de Validation Configurables

Les règles de validation doivent être **adaptables au contexte** (région, type de végétation, protocole de collecte). Le système propose des seuils par défaut calculés automatiquement à partir des données, que l'utilisateur peut ajuster.

#### Interface de Configuration des Règles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Configuration des Règles de Validation                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Limites géographiques:                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ● Auto-détection depuis les données (bounding box + 10%)           │   │
│  │  ○ Depuis les shapes importés (union des géométries)                │   │
│  │  ○ Saisie manuelle:                                                 │   │
│  │    Lon: [-180.0] à [180.0]   Lat: [-90.0] à [90.0]                  │   │
│  │                                                                     │   │
│  │  Emprise détectée: 164.0°E - 167.5°E, 19.5°S - 22.7°S              │   │
│  │  [Visualiser sur carte]                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Seuils numériques (auto-calculés, modifiables):                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Colonne    Min valide    Max valide    Méthode outliers           │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  dbh        [0.1] cm      [500] cm      ● IQR ×1.5  ○ 3σ  ○ Manuel │   │
│  │  height     [0.1] m       [100] m       ● IQR ×1.5  ○ 3σ  ○ Manuel │   │
│  │  altitude   [-100] m      [auto] m      ○ IQR ×1.5  ● 3σ  ○ Manuel │   │
│  │                                                                     │   │
│  │  ⓘ "auto" = valeur max détectée dans les données                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Règles de cohérence (optionnelles):                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [✓] DBH vs Height : alerter si ratio hors [0.5 - 10]               │   │
│  │  [ ] Altitude vs couche raster : écart max [100] m                  │   │
│  │  [✓] Date : rejeter si future ou < [1900]                           │   │
│  │  [+ Ajouter règle personnalisée]                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [Réinitialiser aux valeurs auto]  [Sauvegarder]                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Stratégies de Détection d'Outliers

| Méthode | Description | Usage recommandé |
|---------|-------------|------------------|
| **IQR × 1.5** | Outliers si < Q1-1.5×IQR ou > Q3+1.5×IQR | Distributions asymétriques (DBH, biomasse) |
| **3 sigma** | Outliers si à plus de 3 écarts-types | Distributions normales (altitude, température) |
| **Manuel** | Seuils fixes définis par l'utilisateur | Protocoles stricts, données connues |
| **Percentile** | Outliers si < P1 ou > P99 | Grandes séries avec extrêmes attendus |

#### Profils de Validation Prédéfinis

Pour faciliter la configuration, proposer des profils adaptés aux contextes courants :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Profils de Validation                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Forêt tropicale]  [Forêt tempérée]  [Savane]  [Mangrove]  [Personnalisé] │
│                                                                             │
│  Profil sélectionné : Forêt tropicale                                       │
│  - DBH max attendu : 300 cm                                                 │
│  - Hauteur max attendue : 60 m                                              │
│  - Corrélation DBH/Hauteur typique : 0.7-0.9                               │
│                                                                             │
│  ⓘ Ces valeurs servent de référence initiale, ajustées selon vos données   │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Persistance des Règles

Les règles de validation sont stockées dans la configuration du projet :

```yaml
# config/validation.yml (nouveau fichier ou section dans import.yml)
validation:
  spatial:
    bounds_mode: auto  # auto | shapes | manual
    bounds_buffer: 0.1  # 10% de marge
    manual_bounds:
      min_lon: null
      max_lon: null
      min_lat: null
      max_lat: null

  numeric_rules:
    dbh:
      min: 0.1
      max: 500
      outlier_method: iqr
      iqr_multiplier: 1.5
    height:
      min: 0.1
      max: 100
      outlier_method: iqr
    altitude:
      min: -100
      max: auto
      outlier_method: sigma
      sigma_multiplier: 3

  coherence_rules:
    - type: ratio
      field_a: height
      field_b: dbh
      min_ratio: 0.5
      max_ratio: 10
      enabled: true
    - type: range
      field: date
      min: 1900-01-01
      max: today
      enabled: true

  profile: tropical_forest  # Profil de base utilisé
```

#### Vue 5 : Couverture Géographique

Croisement entre occurrences et shapes de référence (si des shapes sont importés) :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Couverture Géographique                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Répartition par type de shape:                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Sélectionner le type: [Régions administratives ▼]                  │   │
│  │                                                                     │   │
│  │  Région A        ████████████████████████████████ 8,234 (67%)       │   │
│  │  Région B        ██████████████████ 3,890 (31%)                     │   │
│  │  Région C        ██ 221 (2%)                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Autres types disponibles:                                                  │
│  [Zones écologiques]  [Substrats]  [Aires protégées]  [Communes]           │
│                                                                             │
│  Points hors de toute shape:                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ⚠ 300 occurrences (2.4%) ne sont dans aucune shape                │   │
│  │  [Voir sur carte]  [Exporter liste]                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [Matrice de croisement entre types de shapes]                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.5 Fonctionnalités Transversales

#### Export et Partage

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Exporter le Rapport de Qualité                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Format: ● PDF  ○ HTML  ○ Markdown                                          │
│                                                                             │
│  Sections à inclure:                                                        │
│  [✓] Résumé exécutif                                                        │
│  [✓] Distribution spatiale avec carte                                       │
│  [✓] Complétude des données                                                 │
│  [✓] Cohérence taxonomique                                                  │
│  [✓] Validation des valeurs                                                 │
│  [ ] Données brutes des alertes                                             │
│                                                                             │
│  [Générer rapport]                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Correction Interactive

Pour certaines anomalies, proposer des corrections :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Corrections Suggérées                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  23 points hors limites géographiques:                                                 │
│  ○ Supprimer les enregistrements                                            │
│  ○ Marquer comme "à vérifier"                                               │
│  ● Ignorer (conserver tel quel)                                             │
│                                                                             │
│  3 outliers DBH > 200 cm:                                                   │
│  [Voir détails] → Révision manuelle recommandée                             │
│                                                                             │
│  12 taxons orphelins:                                                       │
│  ○ Créer entrées parentes automatiquement                                   │
│  ● Assigner à "Incertae sedis"                                              │
│                                                                             │
│  [Appliquer corrections]  [Annuler]                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.6 Actions Requises - Dashboard

| Priorité | Action | Complexité |
|----------|--------|------------|
| P1 | Composant `ImportDashboard` avec résumé et alertes | Moyenne |
| P1 | Vue complétude des données (heatmap colonnes) | Moyenne |
| P1 | Vue distribution spatiale (carte Leaflet) | Moyenne |
| P1 | API backend `/stats/import-summary` | Moyenne |
| P2 | Vue cohérence taxonomique avec arbre interactif | Élevée |
| P2 | Vue validation des valeurs (boxplots, outliers) | Moyenne |
| P2 | Vue couverture géographique (croisement shapes) | Moyenne |
| P2 | Export rapport PDF/HTML | Moyenne |
| P3 | Corrections interactives (suppression, marquage) | Élevée |
| P3 | Historique des imports avec diff | Moyenne |

---

## 4. Architecture Technique

### 4.1 Composants Frontend

```
src/niamoto/gui/ui/src/
├── pages/
│   └── flow/
│       └── DataPanel.tsx          # Panel principal (existant)
├── components/
│   ├── import-config/             # Nouveaux composants
│   │   ├── ImportConfigForm.tsx   # Formulaire principal
│   │   ├── DatasetForm.tsx        # Config dataset
│   │   ├── TaxonRefForm.tsx       # Config référentiel dérivé
│   │   ├── ShapesRefForm.tsx      # Config multi-shapes
│   │   ├── LayersForm.tsx         # Config couches geo
│   │   └── EnrichmentForm.tsx     # Config enrichissement
│   └── import-dashboard/          # Dashboard validation
│       ├── ImportDashboard.tsx    # Vue principale
│       ├── SpatialDistribution.tsx
│       ├── DataCompleteness.tsx
│       ├── TaxonomicConsistency.tsx
│       ├── ValueValidation.tsx
│       └── GeoCoverage.tsx
```

### 4.2 Endpoints API

```python
# routers/imports.py (existant, à enrichir)

@router.get("/config")
async def get_import_config() -> ImportConfig:
    """Retourne la configuration import.yml parsée"""

@router.put("/config")
async def update_import_config(config: ImportConfig) -> ImportConfig:
    """Met à jour import.yml depuis le formulaire"""

@router.get("/stats/summary")
async def get_import_summary() -> ImportSummary:
    """Statistiques globales post-import"""

@router.get("/stats/completeness")
async def get_data_completeness(entity: str) -> CompletenessReport:
    """Complétude par colonne pour une entité"""

@router.get("/stats/spatial")
async def get_spatial_distribution() -> SpatialStats:
    """Distribution spatiale des occurrences"""

@router.get("/stats/taxonomy")
async def get_taxonomy_consistency() -> TaxonomyReport:
    """Cohérence de la hiérarchie taxonomique"""

@router.get("/stats/validation")
async def get_value_validation(columns: List[str]) -> ValidationReport:
    """Validation des valeurs numériques"""
```

### 4.3 Services Backend

```python
# services/import_stats.py (nouveau)

class ImportStatsService:
    def get_completeness_report(self, entity: str) -> CompletenessReport:
        """Calcule la complétude par colonne via DuckDB"""

    def get_spatial_outliers(self, bounds: BoundingBox) -> List[SpatialOutlier]:
        """Détecte les points hors limites"""

    def get_taxonomy_orphans(self) -> List[TaxonOrphan]:
        """Identifie les taxons sans parent valide"""

    def get_value_statistics(self, column: str) -> ValueStats:
        """Calcule min/max/median/outliers pour une colonne"""
```

---

## 5. Fichiers Concernés

### Existants à modifier
- `src/niamoto/gui/ui/src/pages/flow/DataPanel.tsx` - Intégration dashboard
- `src/niamoto/gui/api/routers/imports.py` - Nouveaux endpoints stats
- `src/niamoto/core/services/importer.py` - Hook post-import pour stats

### À créer
- `src/niamoto/gui/ui/src/components/import-config/` - Formulaires
- `src/niamoto/gui/ui/src/components/import-dashboard/` - Dashboard
- `src/niamoto/gui/api/routers/stats.py` - API statistiques
- `src/niamoto/core/services/import_stats.py` - Service stats

---

## 6. Dépendances

```
Formulaire Import ──► YAML Parser ──► import.yml
        │
        ▼
Import exécution ──► Dashboard Stats
        │
        ▼
Enrichissement ──► API externes ──► Données enrichies
```

Le dashboard de validation dépend de l'import réussi. L'enrichissement peut être exécuté à tout moment après l'import initial.
