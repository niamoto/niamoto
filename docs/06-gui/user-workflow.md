# Parcours Utilisateur - Interface GUI Niamoto

Ce document détaille le parcours complet d'un utilisateur créant un projet de données écologiques avec l'interface Niamoto, depuis l'initialisation jusqu'à la publication.

## Scénario : Créer un portail de la flore endémique

Marie est une botaniste qui veut créer un site web présentant la flore endémique de sa région. Elle a des données d'occurrences et un référentiel taxonomique.

### 📁 Étape 1 : Préparation des données

Marie organise ses fichiers :

```
flore-endemique/
├── donnees_sources/
│   ├── taxonomie_complete.csv
│   ├── observations_terrain.csv
│   └── parcelles_inventaire.csv
```

**Format des données :**

`taxonomie_complete.csv` :
```csv
id_taxonref,family,genus,species,authors,endemic
1,Araucariaceae,Araucaria,columnaris,(Forster) Hooker,true
2,Cunoniaceae,Cunonia,macrophylla,Brongn. & Gris,true
```

`observations_terrain.csv` :
```csv
id,taxonref,geo_pt,date_obs,observateur
1,Araucaria columnaris,"POINT(166.5 -22.3)",2024-03-15,M. Dupont
2,Cunonia macrophylla,"POINT(166.4 -22.2)",2024-03-16,M. Dupont
```

### 🚀 Étape 2 : Initialisation du projet

```bash
cd flore-endemique
niamoto init
```

**Ce qui se passe :**
1. Niamoto crée la structure de base du projet
2. L'interface GUI s'ouvre automatiquement
3. Marie voit l'écran d'accueil avec les options de configuration

### ⚙️ Étape 3 : Configuration via l'interface

#### 3.1 Import des données

Marie remplit la section **Import Configuration** :

1. **Taxonomy CSV Path** : `donnees_sources/taxonomie_complete.csv`
2. **Occurrences CSV Path** : `donnees_sources/observations_terrain.csv`
3. Elle coche **Include Plot Data** et ajoute : `donnees_sources/parcelles_inventaire.csv`

L'interface détecte automatiquement :
- Le type de fichier (CSV)
- L'encodage (UTF-8)
- Les colonnes disponibles

#### 3.2 Configuration des transformations

Marie active les analyses suivantes :

- ✅ **Enable Top Species Analysis** : Pour identifier les espèces dominantes
- ✅ **Generate Distribution Maps** : Pour visualiser la répartition géographique

Dans une version future, elle pourra aussi :
- Calculer des indices de diversité
- Analyser la phénologie
- Générer des statistiques par habitat

#### 3.3 Personnalisation de l'export

Marie configure son site web :

- **Website Title** : "Flore Endémique de Province Sud"
- **Primary Color** : "#2E7D32" (vert forêt)
- ✅ **Generate Static Website**

### 💾 Étape 4 : Génération de la configuration

Marie clique sur **"🚀 Generate YAML Configuration"**

L'interface :
1. Valide la configuration
2. Affiche un message de succès
3. Génère et affiche les fichiers YAML

**Résultat affiché :**

```yaml
# import.yml
taxonomy:
  type: csv
  path: donnees_sources/taxonomie_complete.csv
  source: direct
  ranks: family,genus,species

occurrences:
  type: csv
  path: donnees_sources/observations_terrain.csv
  identifier: id
  location_field: geo_pt

plots:
  type: csv
  path: donnees_sources/parcelles_inventaire.csv
  identifier: id_plot
  locality_field: plot
  location_field: geo_pt

# transform.yml
top_species:
  plugin: top_ranking
  params:
    source: occurrences
    field: taxon_ref_id
    count: 10
    mode: hierarchical

distribution_map:
  plugin: geospatial_extractor
  params:
    source: occurrences
    field: geo_pt
    format: geojson

# export.yml
site:
  title: Flore Endémique de Province Sud
  lang: fr
  primary_color: '#2E7D32'

exports:
- name: web_pages
  enabled: true
  exporter: html_page_exporter
  params:
    output_dir: exports/web
    site:
      title: Flore Endémique de Province Sud
      primary_color: '#2E7D32'
```

### 🔄 Étape 5 : Exécution du pipeline

Marie copie les configurations générées dans les fichiers appropriés, puis :

```bash
# Import des données dans la base
niamoto import
# ✓ Imported taxonomy: 1,247 taxa
# ✓ Imported occurrences: 15,832 records
# ✓ Imported plots: 45 plots

# Calcul des transformations
niamoto transform
# ✓ Calculated top species rankings
# ✓ Generated distribution maps
# ✓ Computed statistics for 1,247 taxa

# Génération du site web
niamoto export
# ✓ Generated 1,247 taxon pages
# ✓ Generated 45 plot pages
# ✓ Created index and navigation
# ✓ Site ready at: exports/web/
```

### 🌐 Étape 6 : Visualisation et ajustements

```bash
# Servir le site localement
cd exports/web
python -m http.server 8000
```

Marie visite http://localhost:8000 et voit :
- Page d'accueil avec statistiques générales
- Liste des taxons avec filtres
- Cartes de distribution interactives
- Fiches détaillées par espèce

### 🔧 Étape 7 : Itérations et améliorations

Après visualisation, Marie veut ajuster :

1. **Retour dans l'interface** : `niamoto gui`
2. **Modifications** :
   - Change le titre en "Atlas de la Flore Endémique"
   - Active plus de transformations
   - Ajuste les couleurs

3. **Régénération** : Un seul clic pour mettre à jour

### 📤 Étape 8 : Publication

Une fois satisfaite :

```bash
# Déployer sur GitHub Pages
niamoto deploy github --repo marie/flore-endemique

# Ou sur un serveur
rsync -av exports/web/ server:/var/www/flore/
```

## Cas d'usage avancés

### Upload de fichiers (fonctionnalité future)

Dans la prochaine version, Marie pourra :

1. **Glisser-déposer ses fichiers** directement dans l'interface
2. **Prévisualiser les données** dans un tableau
3. **Mapper automatiquement** les colonnes
4. **Valider la qualité** des données

### Workflow collaboratif

Pour un projet d'équipe :

1. **Créer un template** de configuration
2. **Partager via Git** ou l'interface
3. **Chaque membre** peut contribuer ses données
4. **Fusion automatique** des contributions

### Intégration avec des APIs

Configuration avancée pour enrichir les données :

```yaml
taxonomy:
  api_enrichment:
    enabled: true
    plugin: "api_taxonomy_enricher"
    api_url: "https://api.biodiversite.nc/v1/taxons"
    auth_method: "api_key"
```

## Bonnes pratiques

### Organisation des fichiers

```
projet/
├── imports/          # Données sources
├── config/           # Configurations YAML
├── exports/          # Résultats générés
├── logs/             # Journaux d'exécution
└── backups/          # Sauvegardes
```

### Versioning

```bash
# Sauvegarder les configurations
git add config/*.yml
git commit -m "Configuration initiale flore endémique"

# Taguer les versions
git tag -a v1.0 -m "Première version du site"
```

### Performance

Pour de gros volumes :
- Diviser les imports en lots
- Utiliser le mode `--parallel` pour les transformations
- Optimiser les requêtes spatiales

## Dépannage courant

### Données non reconnues

**Problème** : L'import échoue avec "Format non reconnu"

**Solution** :
1. Vérifier l'encodage (UTF-8 requis)
2. Valider les en-têtes de colonnes
3. Supprimer les caractères spéciaux

### Transformations lentes

**Problème** : Le calcul prend trop de temps

**Solution** :
1. Activer le mode verbose : `niamoto transform -v`
2. Identifier l'étape lente
3. Optimiser ou diviser les données

### Export incomplet

**Problème** : Des pages manquent dans le site

**Solution** :
1. Vérifier les logs : `tail -f logs/export.log`
2. Relancer avec `--force` pour régénérer
3. Vérifier l'espace disque disponible

## Évolutions futures

L'interface GUI évoluera pour offrir :

1. **Éditeur visuel de pipeline** avec React Flow
2. **Preview en temps réel** des transformations
3. **Bibliothèque de widgets** personnalisables
4. **Templates communautaires** partageables
5. **Mode collaboratif** avec gestion des conflits
6. **Export multi-formats** (PDF, DOCX, etc.)

Ce parcours utilisateur illustre comment Niamoto simplifie la création de portails de données écologiques, rendant accessible à tous la publication de données scientifiques de qualité.
