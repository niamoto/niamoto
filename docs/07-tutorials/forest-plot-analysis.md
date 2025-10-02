# Tutorial: Forest Plot Analysis Portal

This tutorial walks you through creating a comprehensive forest plot analysis portal using Niamoto. You'll learn to work with plot data, calculate forest metrics, and create spatial visualizations for ecological research.

## Overview

In this tutorial, you'll create a portal that analyzes forest inventory plots with:

- Plot location mapping and spatial analysis
- Forest structure metrics (basal area, density, diversity)
- Species composition analysis by plot
- Elevation and environmental gradients
- Plot comparison and clustering
- Interactive dashboards for researchers

**Estimated Time**: 45 minutes

**Difficulty**: Intermediate

## What You'll Learn

- Import and validate plot inventory data
- Calculate forest structural metrics
- Create spatial analysis workflows
- Build interactive plot comparison tools
- Generate research-ready visualizations
- Deploy a scientific portal

## Prerequisites

- Niamoto installed ([Installation Guide](../getting-started/installation.md))
- Basic understanding of forest inventory concepts
- Familiarity with CSV data formats

## Sample Dataset

We'll use forest inventory data from New Caledonia's monitoring network:

**Plots** (`plots.csv`):
```csv
plot_id,plot_name,latitude,longitude,elevation,slope,aspect,forest_type,area_m2,establishment_date
P001,Mont Panié - Plot 1,-20.5819,164.7672,850,15,180,humid_forest,2500,2018-03-15
P002,Mont Panié - Plot 2,-20.5825,164.7685,875,12,165,humid_forest,2500,2018-03-16
P003,Rivière Bleue - Plot 1,-22.0951,166.6489,450,8,90,dry_forest,2500,2018-04-10
P004,Rivière Bleue - Plot 2,-22.0958,166.6501,435,5,75,dry_forest,2500,2018-04-11
P005,Pic du Grand Kaori - Plot 1,-21.3456,165.9123,950,25,200,humid_forest,2500,2018-05-20
```

**Trees** (`trees.csv`):
```csv
tree_id,plot_id,taxon_id,species,dbh_cm,height_m,status,x_coord,y_coord
T001,P001,123,Araucaria columnaris,45.2,18.5,alive,12.5,15.3
T002,P001,124,Agathis ovata,38.7,16.2,alive,8.2,22.1
T003,P001,125,Montrouziera cauliflora,22.3,12.1,alive,35.4,18.9
T004,P002,123,Araucaria columnaris,52.1,21.3,alive,19.7,8.4
T005,P002,126,Calophyllum caledonicum,33.5,14.8,alive,28.1,31.2
```

**Environmental** (`plot_environment.csv`):
```csv
plot_id,soil_type,substrate,annual_rainfall_mm,mean_temp_c,humidity_percent,canopy_cover_percent
P001,ferralsol,ultramafic,2800,18.5,85,92
P002,ferralsol,ultramafic,2850,18.2,87,89
P003,vertisol,sedimentary,1200,22.1,65,78
P004,vertisol,sedimentary,1180,22.4,63,75
P005,ferralsol,ultramafic,3200,16.8,90,95
```

## Step 1: Project Setup

### Create Project Structure

```bash
# Create new project
mkdir forest-plots-portal
cd forest-plots-portal

# Initialize Niamoto project
niamoto init

# Create directory structure
mkdir -p imports/environmental
mkdir -p imports/spatial
mkdir -p templates/forest-plots
mkdir -p exports/research
```

### Download Sample Data

Create the sample data files:

```bash
# Create plot data
cat > imports/plots.csv << 'EOF'
plot_id,plot_name,latitude,longitude,elevation,slope,aspect,forest_type,area_m2,establishment_date
P001,Mont Panié - Plot 1,-20.5819,164.7672,850,15,180,humid_forest,2500,2018-03-15
P002,Mont Panié - Plot 2,-20.5825,164.7685,875,12,165,humid_forest,2500,2018-03-16
P003,Rivière Bleue - Plot 1,-22.0951,166.6489,450,8,90,dry_forest,2500,2018-04-10
P004,Rivière Bleue - Plot 2,-22.0958,166.6501,435,5,75,dry_forest,2500,2018-04-11
P005,Pic du Grand Kaori - Plot 1,-21.3456,165.9123,950,25,200,humid_forest,2500,2018-05-20
P006,Forêt de Saille - Plot 1,-21.1234,165.4567,650,18,145,humid_forest,2500,2019-02-12
P007,Col des Roussettes - Plot 1,-21.8765,166.2341,1100,30,220,montane_forest,2500,2019-03-08
P008,Bois du Sud - Plot 1,-22.1876,166.8901,380,7,60,dry_forest,2500,2019-04-15
EOF

# Create tree inventory data
cat > imports/trees.csv << 'EOF'
tree_id,plot_id,taxon_id,species,dbh_cm,height_m,status,x_coord,y_coord
T001,P001,123,Araucaria columnaris,45.2,18.5,alive,12.5,15.3
T002,P001,124,Agathis ovata,38.7,16.2,alive,8.2,22.1
T003,P001,125,Montrouziera cauliflora,22.3,12.1,alive,35.4,18.9
T004,P001,127,Cryptocarya obovata,19.8,9.5,alive,41.2,27.6
T005,P001,128,Callistemon pityoides,15.4,7.2,alive,6.8,35.1
T006,P002,123,Araucaria columnaris,52.1,21.3,alive,19.7,8.4
T007,P002,126,Calophyllum caledonicum,33.5,14.8,alive,28.1,31.2
T008,P002,124,Agathis ovata,41.2,17.8,alive,15.6,19.3
T009,P002,129,Dracophyllum verticillatum,18.6,8.9,alive,35.7,12.1
T010,P002,130,Metrosideros operculata,25.3,11.4,alive,42.1,38.9
T011,P003,131,Santalum austrocaledonicum,28.4,13.2,alive,22.3,16.7
T012,P003,132,Acacia spirorbis,21.7,10.5,alive,18.9,28.4
T013,P003,133,Grevillea exul,33.1,15.6,alive,31.5,21.8
T014,P003,134,Pittosporum tanianum,19.2,9.8,alive,8.7,33.2
T015,P003,135,Dodonaea viscosa,16.8,8.1,alive,37.4,14.5
T016,P004,131,Santalum austrocaledonicum,31.8,14.7,alive,14.2,22.1
T017,P004,136,Melaleuca quinquenervia,27.5,12.3,alive,26.8,18.9
T018,P004,133,Grevillea exul,29.7,13.8,alive,19.4,31.6
T019,P004,137,Corymbia citriodora,24.1,11.2,alive,33.7,25.4
T020,P004,138,Alphitonia zizyphoides,22.3,10.6,alive,12.5,37.8
T021,P005,123,Araucaria columnaris,38.9,16.8,alive,16.3,19.7
T022,P005,124,Agathis ovata,44.6,18.9,alive,24.1,28.5
T023,P005,139,Dacrydium guillauminii,35.2,15.4,alive,31.8,14.2
T024,P005,140,Libocedrus yateensis,29.7,13.1,alive,8.9,32.6
T025,P005,141,Arillastrum gummiferum,26.4,12.5,alive,38.5,21.3
EOF

# Create environmental data
cat > imports/environmental/plot_environment.csv << 'EOF'
plot_id,soil_type,substrate,annual_rainfall_mm,mean_temp_c,humidity_percent,canopy_cover_percent
P001,ferralsol,ultramafic,2800,18.5,85,92
P002,ferralsol,ultramafic,2850,18.2,87,89
P003,vertisol,sedimentary,1200,22.1,65,78
P004,vertisol,sedimentary,1180,22.4,63,75
P005,ferralsol,ultramafic,3200,16.8,90,95
P006,ferralsol,ultramafic,2650,19.1,83,88
P007,podzol,volcanic,3500,15.2,92,96
P008,vertisol,sedimentary,1050,23.2,60,72
EOF

# Create taxonomy reference
cat > imports/taxonomy.csv << 'EOF'
taxon_id,family,genus,species,full_name,rank,endemic,conservation_status
123,Araucariaceae,Araucaria,columnaris,Araucaria columnaris,species,true,LC
124,Araucariaceae,Agathis,ovata,Agathis ovata,species,true,VU
125,Clusiaceae,Montrouziera,cauliflora,Montrouziera cauliflora,species,true,NT
126,Calophyllaceae,Calophyllum,caledonicum,Calophyllum caledonicum,species,true,LC
127,Lauraceae,Cryptocarya,obovata,Cryptocarya obovata,species,true,LC
128,Myrtaceae,Callistemon,pityoides,Callistemon pityoides,species,true,LC
129,Ericaceae,Dracophyllum,verticillatum,Dracophyllum verticillatum,species,true,LC
130,Myrtaceae,Metrosideros,operculata,Metrosideros operculata,species,true,LC
131,Santalaceae,Santalum,austrocaledonicum,Santalum austrocaledonicum,species,true,VU
132,Fabaceae,Acacia,spirorbis,Acacia spirorbis,species,true,LC
133,Proteaceae,Grevillea,exul,Grevillea exul,species,true,NT
134,Pittosporaceae,Pittosporum,tanianum,Pittosporum tanianum,species,true,LC
135,Sapindaceae,Dodonaea,viscosa,Dodonaea viscosa,species,false,LC
136,Myrtaceae,Melaleuca,quinquenervia,Melaleuca quinquenervia,species,false,LC
137,Myrtaceae,Corymbia,citriodora,Corymbia citriodora,species,false,LC
138,Rhamnaceae,Alphitonia,zizyphoides,Alphitonia zizyphoides,species,true,LC
139,Podocarpaceae,Dacrydium,guillauminii,Dacrydium guillauminii,species,true,EN
140,Cupressaceae,Libocedrus,yateensis,Libocedrus yateensis,species,true,CR
141,Myrtaceae,Arillastrum,gummiferum,Arillastrum gummiferum,species,true,VU
EOF
```

## Step 2: Configure Data Import

### Configure Import Settings

```yaml
# config/import.yml
imports:
  # Plot reference data
  plots:
    type: csv
    path: "imports/plots.csv"
    mapping:
      geo_pt:
        x: "longitude"
        y: "latitude"
      properties:
        plot_id: "plot_id"
        plot_name: "plot_name"
        elevation: "elevation"
        slope: "slope"
        aspect: "aspect"
        forest_type: "forest_type"
        area_m2: "area_m2"
        establishment_date: "establishment_date"

  # Tree inventory (occurrences)
  trees:
    type: csv
    path: "imports/trees.csv"
    mapping:
      properties:
        tree_id: "tree_id"
        plot_id: "plot_id"
        taxon_id: "taxon_id"
        species: "species"
        dbh_cm: "dbh_cm"
        height_m: "height_m"
        status: "status"
        x_coord: "x_coord"
        y_coord: "y_coord"

  # Environmental data
  plot_environment:
    type: csv
    path: "imports/environmental/plot_environment.csv"
    mapping:
      properties:
        plot_id: "plot_id"
        soil_type: "soil_type"
        substrate: "substrate"
        annual_rainfall_mm: "annual_rainfall_mm"
        mean_temp_c: "mean_temp_c"
        humidity_percent: "humidity_percent"
        canopy_cover_percent: "canopy_cover_percent"

  # Taxonomy reference
  taxons:
    type: csv
    path: "imports/taxonomy.csv"
    mapping:
      taxon_id: "taxon_id"
      properties:
        family: "family"
        genus: "genus"
        species: "species"
        full_name: "full_name"
        rank: "rank"
        endemic: "endemic"
        conservation_status: "conservation_status"
```

### Import Data

```bash
# Import all data
niamoto import

# Verify import
niamoto stats
```

Expected output:
```
Import Summary:
- plots: 8 records imported
- trees: 25 records imported
- plot_environment: 8 records imported
- taxons: 19 records imported
```

## Step 3: Configure Forest Metrics Transformations

### Configure Analysis Pipeline

```yaml
# config/transform.yml
groups:
  # Plot-level analysis
  - group_by: plot
    data_source: plots
    join_data:
      - source: trees
        on: plot_id
        type: left
      - source: plot_environment
        on: plot_id
        type: left
      - source: taxons
        on: taxon_id
        type: left

    widgets_data:
      # Basic plot information
      plot_info:
        plugin: field_aggregator
        params:
          fields:
            - source: plots
              field: plot_name
              target: name
              aggregation: first
            - source: plots
              field: latitude
              target: latitude
              aggregation: first
            - source: plots
              field: longitude
              target: longitude
              aggregation: first
            - source: plots
              field: elevation
              target: elevation
              aggregation: first
            - source: plots
              field: forest_type
              target: forest_type
              aggregation: first
            - source: plots
              field: area_m2
              target: area_m2
              aggregation: first

      # Forest structure metrics
      forest_structure:
        plugin: forest_structure_calculator
        params:
          dbh_field: "dbh_cm"
          height_field: "height_m"
          plot_area_field: "area_m2"
          min_dbh: 10  # cm
          calculations:
            - basal_area_m2_ha
            - stem_density_ha
            - mean_dbh
            - mean_height
            - quadratic_mean_diameter
            - volume_m3_ha

      # Species diversity metrics
      diversity_metrics:
        plugin: diversity_calculator
        params:
          species_field: "species"
          count_field: "tree_id"
          calculations:
            - species_richness
            - shannon_diversity
            - simpson_diversity
            - evenness
            - dominance_index

      # Species composition
      species_composition:
        plugin: species_aggregator
        params:
          species_field: "full_name"
          dbh_field: "dbh_cm"
          basal_area_aggregation: true
          abundance_aggregation: true
          top_n: 10

      # Environmental summary
      environmental_data:
        plugin: field_aggregator
        params:
          fields:
            - source: plot_environment
              field: soil_type
              target: soil_type
              aggregation: first
            - source: plot_environment
              field: substrate
              target: substrate
              aggregation: first
            - source: plot_environment
              field: annual_rainfall_mm
              target: rainfall
              aggregation: first
            - source: plot_environment
              field: mean_temp_c
              target: temperature
              aggregation: first
            - source: plot_environment
              field: canopy_cover_percent
              target: canopy_cover
              aggregation: first

  # Species-level analysis across plots
  - group_by: species
    data_source: trees
    join_data:
      - source: taxons
        on: taxon_id
        type: left
      - source: plots
        on: plot_id
        type: left
      - source: plot_environment
        on: plot_id
        type: left

    widgets_data:
      # Species information
      species_info:
        plugin: field_aggregator
        params:
          fields:
            - source: taxons
              field: full_name
              target: name
              aggregation: first
            - source: taxons
              field: family
              target: family
              aggregation: first
            - source: taxons
              field: endemic
              target: endemic
              aggregation: first
            - source: taxons
              field: conservation_status
              target: conservation
              aggregation: first

      # Species distribution
      species_distribution:
        plugin: spatial_aggregator
        params:
          latitude_field: "latitude"
          longitude_field: "longitude"
          value_field: "dbh_cm"
          aggregation: mean
          include_plot_info: true

      # Ecological preferences
      ecological_preferences:
        plugin: environmental_aggregator
        params:
          environmental_fields:
            - annual_rainfall_mm
            - mean_temp_c
            - elevation
            - canopy_cover_percent
          aggregation: mean
          include_range: true

  # Forest type comparison
  - group_by: forest_type
    data_source: plots
    join_data:
      - source: trees
        on: plot_id
        type: left
      - source: plot_environment
        on: plot_id
        type: left

    widgets_data:
      # Forest type characteristics
      forest_type_metrics:
        plugin: forest_structure_calculator
        params:
          dbh_field: "dbh_cm"
          height_field: "height_m"
          plot_area_field: "area_m2"
          calculations:
            - basal_area_m2_ha
            - stem_density_ha
            - species_richness
            - mean_dbh
            - shannon_diversity

      # Environmental gradients
      environmental_gradients:
        plugin: field_aggregator
        params:
          fields:
            - source: plot_environment
              field: annual_rainfall_mm
              target: rainfall
              aggregation: mean
            - source: plot_environment
              field: mean_temp_c
              target: temperature
              aggregation: mean
            - source: plots
              field: elevation
              target: elevation
              aggregation: mean
            - source: plot_environment
              field: canopy_cover_percent
              target: canopy_cover
              aggregation: mean
```

### Create Custom Transform Plugins

Create forest-specific transform plugins:

```bash
mkdir -p plugins/transformers
```

```python
# plugins/transformers/forest_structure_calculator.py
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
import pandas as pd
import numpy as np

@register("forest_structure_calculator", PluginType.TRANSFORMER)
class ForestStructureCalculator(TransformerPlugin):
    """Calculate forest structural metrics."""

    def transform(self, data, config):
        """Calculate forest structure metrics for each group."""
        dbh_field = config.get('dbh_field', 'dbh_cm')
        height_field = config.get('height_field', 'height_m')
        plot_area_field = config.get('plot_area_field', 'area_m2')
        min_dbh = config.get('min_dbh', 10)

        results = {}

        for group_id, group_data in data.groupby(level=0):
            # Filter by minimum DBH
            trees = group_data[group_data[dbh_field] >= min_dbh]

            if len(trees) == 0:
                continue

            # Get plot area (convert m2 to hectares)
            plot_area_m2 = trees[plot_area_field].iloc[0]
            plot_area_ha = plot_area_m2 / 10000

            # Calculate metrics
            metrics = {}

            # Basal area (m2/ha)
            basal_areas = np.pi * (trees[dbh_field] / 200) ** 2  # DBH in cm to radius in m
            total_basal_area = basal_areas.sum()
            metrics['basal_area_m2_ha'] = total_basal_area / plot_area_ha

            # Stem density (stems/ha)
            metrics['stem_density_ha'] = len(trees) / plot_area_ha

            # Mean dimensions
            metrics['mean_dbh'] = trees[dbh_field].mean()
            metrics['mean_height'] = trees[height_field].mean()

            # Quadratic mean diameter
            metrics['quadratic_mean_diameter'] = np.sqrt((trees[dbh_field] ** 2).mean())

            # Estimated volume (simplified allometric equation)
            # Volume = 0.0001 * DBH^2 * Height (m3)
            volumes = 0.0001 * (trees[dbh_field] ** 2) * trees[height_field]
            metrics['volume_m3_ha'] = volumes.sum() / plot_area_ha

            # Standard deviations
            metrics['dbh_std'] = trees[dbh_field].std()
            metrics['height_std'] = trees[height_field].std()

            # Size class distribution
            dbh_classes = pd.cut(trees[dbh_field],
                               bins=[0, 20, 40, 60, 80, 100, np.inf],
                               labels=['10-20', '20-40', '40-60', '60-80', '80-100', '100+'])
            size_distribution = dbh_classes.value_counts().to_dict()
            metrics['size_distribution'] = size_distribution

            results[group_id] = metrics

        return results

@register("diversity_calculator", PluginType.TRANSFORMER)
class DiversityCalculator(TransformerPlugin):
    """Calculate species diversity metrics."""

    def transform(self, data, config):
        """Calculate diversity indices for each group."""
        species_field = config.get('species_field', 'species')

        results = {}

        for group_id, group_data in data.groupby(level=0):
            # Species abundance
            species_counts = group_data[species_field].value_counts()

            if len(species_counts) == 0:
                continue

            # Total individuals
            total_individuals = species_counts.sum()

            # Relative abundances
            proportions = species_counts / total_individuals

            metrics = {}

            # Species richness
            metrics['species_richness'] = len(species_counts)

            # Shannon diversity
            metrics['shannon_diversity'] = -(proportions * np.log(proportions)).sum()

            # Simpson diversity (1 - D)
            metrics['simpson_diversity'] = 1 - (proportions ** 2).sum()

            # Evenness (Shannon / log(S))
            if metrics['species_richness'] > 1:
                metrics['evenness'] = metrics['shannon_diversity'] / np.log(metrics['species_richness'])
            else:
                metrics['evenness'] = 1.0

            # Dominance (proportion of most abundant species)
            metrics['dominance_index'] = proportions.max()

            # Most abundant species
            metrics['dominant_species'] = species_counts.index[0]
            metrics['dominant_count'] = species_counts.iloc[0]

            results[group_id] = metrics

        return results
```

### Run Transformations

```bash
# Execute transformation pipeline
niamoto transform

# Check results
niamoto stats --detailed
```

## Step 4: Configure Website Export

### Configure Export Settings

```yaml
# config/export.yml
exports:
  - name: forest_plots_portal
    exporter: html_page_exporter
    params:
      output_dir: "exports/research"
      base_url: "/"

      # Portal pages
      static_pages:
        - name: home
          output_file: "index.html"
          template: "forest_home.html"

        - name: plots_overview
          output_file: "plots/index.html"
          template: "plots_overview.html"

        - name: species_analysis
          output_file: "species/index.html"
          template: "species_analysis.html"

        - name: forest_types
          output_file: "forest-types/index.html"
          template: "forest_types.html"

        - name: methodology
          output_file: "methodology.html"
          template: "methodology.html"

      # Individual plot pages
      entity_pages:
        - group: plot
          template: "plot_detail.html"
          output_pattern: "plot/{{ id }}.html"

        - group: species
          template: "species_detail.html"
          output_pattern: "species/{{ id }}.html"

      # Copy research assets
      copy_assets_from:
        - "templates/forest-plots/assets/"
```

### Create Custom Templates

Create the homepage template:

```html
<!-- templates/forest_home.html -->
{% extends "_base.html" %}

{% block title %}New Caledonia Forest Plot Network{% endblock %}

{% block content %}
<div class="hero-section bg-gradient-to-r from-green-600 to-green-800 text-white py-16">
    <div class="container mx-auto px-4">
        <div class="max-w-4xl mx-auto text-center">
            <h1 class="text-4xl md:text-6xl font-bold mb-6">
                Forest Plot Network
            </h1>
            <p class="text-xl md:text-2xl mb-8">
                Monitoring New Caledonia's unique forest ecosystems through standardized inventory plots
            </p>
            <div class="grid md:grid-cols-3 gap-6 mt-12">
                <div class="bg-white bg-opacity-20 rounded-lg p-6">
                    <h3 class="text-2xl font-bold mb-2">{{ plot_count }}</h3>
                    <p class="text-lg">Monitoring Plots</p>
                </div>
                <div class="bg-white bg-opacity-20 rounded-lg p-6">
                    <h3 class="text-2xl font-bold mb-2">{{ species_count }}</h3>
                    <p class="text-lg">Tree Species</p>
                </div>
                <div class="bg-white bg-opacity-20 rounded-lg p-6">
                    <h3 class="text-2xl font-bold mb-2">{{ tree_count }}</h3>
                    <p class="text-lg">Individual Trees</p>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="container mx-auto px-4 py-12">
    <!-- Network Overview Map -->
    <section class="mb-16">
        <h2 class="text-3xl font-bold text-gray-800 mb-8">Plot Network Overview</h2>
        {{ widget("plot_network_map") }}
    </section>

    <!-- Key Findings -->
    <section class="mb-16">
        <h2 class="text-3xl font-bold text-gray-800 mb-8">Key Findings</h2>
        <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {{ widget("forest_metrics_summary") }}
        </div>
    </section>

    <!-- Forest Types Comparison -->
    <section class="mb-16">
        <h2 class="text-3xl font-bold text-gray-800 mb-8">Forest Types</h2>
        <div class="grid lg:grid-cols-2 gap-8">
            {{ widget("forest_type_comparison") }}
            {{ widget("environmental_gradients") }}
        </div>
    </section>

    <!-- Species Diversity -->
    <section class="mb-16">
        <h2 class="text-3xl font-bold text-gray-800 mb-8">Species Diversity</h2>
        {{ widget("diversity_comparison") }}
    </section>

    <!-- Quick Access -->
    <section>
        <h2 class="text-3xl font-bold text-gray-800 mb-8">Explore Data</h2>
        <div class="grid md:grid-cols-3 gap-6">
            <a href="/plots/" class="block bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                <h3 class="text-xl font-bold text-green-600 mb-2">Plot Analysis</h3>
                <p class="text-gray-600">Detailed forest structure and composition analysis for each monitoring plot</p>
            </a>
            <a href="/species/" class="block bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                <h3 class="text-xl font-bold text-green-600 mb-2">Species Profiles</h3>
                <p class="text-gray-600">Ecological preferences and distribution patterns of forest tree species</p>
            </a>
            <a href="/forest-types/" class="block bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                <h3 class="text-xl font-bold text-green-600 mb-2">Forest Types</h3>
                <p class="text-gray-600">Comparative analysis of humid, dry, and montane forest ecosystems</p>
            </a>
        </div>
    </section>
</div>
{% endblock %}
```

Create plot detail template:

```html
<!-- templates/plot_detail.html -->
{% extends "_base.html" %}

{% block title %}{{ plot.name }} - Forest Plot Analysis{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <!-- Plot Header -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
        <div class="flex justify-between items-start">
            <div>
                <h1 class="text-3xl font-bold text-gray-800">{{ plot.name }}</h1>
                <p class="text-lg text-gray-600 mt-2">{{ plot.forest_type | title }} Forest</p>
                <div class="mt-4 text-sm text-gray-500">
                    <span>📍 {{ "%.4f"|format(plot.latitude) }}, {{ "%.4f"|format(plot.longitude) }}</span>
                    <span class="ml-4">⛰️ {{ plot.elevation }}m elevation</span>
                    <span class="ml-4">📅 Established {{ plot.establishment_date }}</span>
                </div>
            </div>
            <div class="text-right">
                <div class="bg-green-100 rounded-lg p-4">
                    <div class="text-2xl font-bold text-green-800">{{ plot.area_m2 / 10000 }} ha</div>
                    <div class="text-sm text-green-600">Plot Area</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Summary Metrics -->
    <div class="grid md:grid-cols-4 gap-6 mb-8">
        {{ widget("plot_summary_metrics") }}
    </div>

    <!-- Main Analysis Sections -->
    <div class="grid lg:grid-cols-2 gap-8 mb-8">
        <!-- Forest Structure -->
        <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">Forest Structure</h2>
            {{ widget("forest_structure_charts") }}
        </div>

        <!-- Species Composition -->
        <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">Species Composition</h2>
            {{ widget("species_composition_chart") }}
        </div>
    </div>

    <!-- Environmental Context -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 class="text-2xl font-bold text-gray-800 mb-4">Environmental Context</h2>
        <div class="grid md:grid-cols-2 gap-8">
            {{ widget("environmental_summary") }}
            {{ widget("plot_location_map") }}
        </div>
    </div>

    <!-- Detailed Species List -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 class="text-2xl font-bold text-gray-800 mb-4">Species Inventory</h2>
        {{ widget("species_table") }}
    </div>

    <!-- Tree Size Distribution -->
    <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-2xl font-bold text-gray-800 mb-4">Tree Size Distribution</h2>
        {{ widget("size_distribution_chart") }}
    </div>
</div>
{% endblock %}
```

### Configure Page Widgets

Add widget configurations to your export.yml:

```yaml
# Add to export.yml under static_pages
widgets:
  # Homepage widgets
  plot_network_map:
    plugin: interactive_map
    data_source: plot_info
    params:
      title: "Forest Plot Network"
      map_type: "scatter_map"
      latitude_field: "latitude"
      longitude_field: "longitude"
      color_field: "forest_type"
      size_field: "elevation"
      hover_data: ["name", "forest_type", "elevation"]
      auto_zoom: true

  forest_metrics_summary:
    plugin: info_grid
    data_source: forest_structure
    params:
      grid_columns: 4
      items:
        - label: "Mean Basal Area"
          source: "basal_area_m2_ha"
          unit: "m²/ha"
          format: "number"
        - label: "Stem Density"
          source: "stem_density_ha"
          unit: "stems/ha"
          format: "number"
        - label: "Mean DBH"
          source: "mean_dbh"
          unit: "cm"
          format: "number"
        - label: "Species Richness"
          source: "species_richness"
          unit: "species"

  forest_type_comparison:
    plugin: bar_plot
    data_source: forest_type_metrics
    params:
      title: "Forest Structure by Type"
      x_axis: "forest_type"
      y_axis: "basal_area_m2_ha"
      auto_color: true

  diversity_comparison:
    plugin: scatter_plot
    data_source: diversity_metrics
    params:
      title: "Species Richness vs Shannon Diversity"
      x_axis: "species_richness"
      y_axis: "shannon_diversity"
      color_field: "forest_type"
      size_field: "stem_density_ha"

  # Plot detail widgets
  plot_summary_metrics:
    plugin: info_grid
    data_source: forest_structure
    params:
      grid_columns: 4
      items:
        - label: "Basal Area"
          source: "basal_area_m2_ha"
          unit: "m²/ha"
          icon: "fa-tree"
        - label: "Stem Density"
          source: "stem_density_ha"
          unit: "stems/ha"
          icon: "fa-seedling"
        - label: "Species Count"
          source: "species_richness"
          unit: "species"
          icon: "fa-leaf"
        - label: "Shannon Index"
          source: "shannon_diversity"
          format: "number"
          icon: "fa-chart-line"

  species_composition_chart:
    plugin: donut_chart
    data_source: species_composition
    params:
      title: "Species Composition (by Basal Area)"
      values_field: "basal_area"
      labels_field: "species"
      hole_size: 0.4

  environmental_summary:
    plugin: info_grid
    data_source: environmental_data
    params:
      grid_columns: 2
      items:
        - label: "Annual Rainfall"
          source: "rainfall"
          unit: "mm"
        - label: "Mean Temperature"
          source: "temperature"
          unit: "°C"
        - label: "Canopy Cover"
          source: "canopy_cover"
          unit: "%"
        - label: "Substrate"
          source: "substrate"

  size_distribution_chart:
    plugin: bar_plot
    data_source: forest_structure
    params:
      title: "Tree Size Distribution"
      x_axis: "size_class"
      y_axis: "count"
      orientation: "v"
```

## Step 5: Generate Website

### Run Complete Pipeline

```bash
# Run full analysis pipeline
niamoto run

# Check output
ls -la exports/research/
```

### Test Website Locally

```bash
# Start local server
cd exports/research
python -m http.server 8000

# Visit http://localhost:8000
```

## Step 6: Advanced Analysis Features

### Add Plot Comparison Tool

Create an interactive plot comparison page:

```html
<!-- templates/plot_comparison.html -->
{% extends "_base.html" %}

{% block title %}Plot Comparison Tool{% endblock %}

{% block head %}
<script src="/assets/js/plot-comparison.js"></script>
{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-gray-800 mb-8">Plot Comparison Tool</h1>

    <!-- Plot Selection -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 class="text-xl font-bold mb-4">Select Plots to Compare</h2>
        <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {% for plot in plots %}
            <label class="flex items-center space-x-2">
                <input type="checkbox" value="{{ plot.id }}" class="plot-selector">
                <span class="text-sm">{{ plot.name }}</span>
            </label>
            {% endfor %}
        </div>
        <button id="compare-btn" class="mt-4 bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700">
            Compare Selected Plots
        </button>
    </div>

    <!-- Comparison Results -->
    <div id="comparison-results" class="hidden">
        <div class="grid lg:grid-cols-2 gap-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h3 class="text-lg font-bold mb-4">Forest Structure Comparison</h3>
                <div id="structure-comparison"></div>
            </div>
            <div class="bg-white rounded-lg shadow-md p-6">
                <h3 class="text-lg font-bold mb-4">Species Diversity Comparison</h3>
                <div id="diversity-comparison"></div>
            </div>
        </div>
    </div>
</div>

<script>
// Plot comparison functionality
document.getElementById('compare-btn').addEventListener('click', function() {
    const selectedPlots = Array.from(document.querySelectorAll('.plot-selector:checked'))
        .map(checkbox => checkbox.value);

    if (selectedPlots.length < 2) {
        alert('Please select at least 2 plots to compare');
        return;
    }

    // Fetch and display comparison data
    fetchPlotComparison(selectedPlots);
});

function fetchPlotComparison(plotIds) {
    // Implementation would fetch plot data and create comparison charts
    document.getElementById('comparison-results').classList.remove('hidden');
}
</script>
{% endblock %}
```

### Add Species Network Analysis

Create species co-occurrence network:

```python
# plugins/transformers/species_network.py
import pandas as pd
import numpy as np
from itertools import combinations

@register("species_network", PluginType.TRANSFORMER)
class SpeciesNetworkAnalyzer(TransformerPlugin):
    """Analyze species co-occurrence patterns."""

    def transform(self, data, config):
        """Calculate species co-occurrence network."""
        results = {}

        # Get species presence by plot
        plot_species = data.groupby(['plot_id', 'species']).size().unstack(fill_value=0)
        plot_species = (plot_species > 0).astype(int)  # Convert to presence/absence

        # Calculate co-occurrence matrix
        cooccurrence = plot_species.T.dot(plot_species)
        np.fill_diagonal(cooccurrence.values, 0)  # Remove self-connections

        # Create network edges
        edges = []
        for i, species1 in enumerate(cooccurrence.index):
            for j, species2 in enumerate(cooccurrence.columns[i+1:], i+1):
                weight = cooccurrence.iloc[i, j]
                if weight > 0:
                    edges.append({
                        'source': species1,
                        'target': species2,
                        'weight': weight,
                        'strength': weight / len(plot_species)  # Normalize by total plots
                    })

        # Node information
        nodes = []
        for species in cooccurrence.index:
            occurrence_count = plot_species[species].sum()
            nodes.append({
                'id': species,
                'label': species,
                'size': occurrence_count,
                'frequency': occurrence_count / len(plot_species)
            })

        results['network'] = {
            'nodes': nodes,
            'edges': edges,
            'plot_count': len(plot_species),
            'species_count': len(nodes)
        }

        return results
```

## Step 7: Deploy Research Portal

### Configure GitHub Actions for Automated Updates

```yaml
# .github/workflows/update-research-portal.yml
name: Update Forest Research Portal

on:
  schedule:
    # Update weekly on Sundays at 6 AM UTC
    - cron: '0 6 * * 0'
  workflow_dispatch:  # Manual trigger
  push:
    paths:
      - 'imports/**'
      - 'config/**'

jobs:
  update-portal:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install niamoto
        pip install -r requirements.txt

    - name: Download latest field data
      run: |
        # Add script to download fresh data from field databases
        python scripts/sync_field_data.py

    - name: Run analysis pipeline
      run: |
        niamoto run --verbose

    - name: Generate research reports
      run: |
        python scripts/generate_reports.py

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./exports/research
        cname: forest-research.example.com
```

### Create Data Synchronization Script

```python
# scripts/sync_field_data.py
"""Synchronize field data from external sources."""

import requests
import pandas as pd
from pathlib import Path

def sync_plot_data():
    """Download latest plot measurements."""
    # Example API call to field database
    api_url = "https://fielddata.example.com/api/plots"

    response = requests.get(api_url, headers={
        'Authorization': f'Bearer {os.getenv("FIELD_DATA_TOKEN")}'
    })

    if response.status_code == 200:
        plot_data = response.json()
        df = pd.DataFrame(plot_data)
        df.to_csv('imports/plots_updated.csv', index=False)
        print(f"Updated {len(df)} plot records")
    else:
        print(f"Failed to fetch plot data: {response.status_code}")

def sync_tree_inventory():
    """Download latest tree measurements."""
    # Similar implementation for tree data
    pass

if __name__ == "__main__":
    sync_plot_data()
    sync_tree_inventory()
    print("Data synchronization complete")
```

### Deploy to Research Platform

```bash
# Deploy to production
niamoto deploy github --repo https://github.com/username/forest-research-portal.git

# Configure custom domain
echo "forest-research.example.com" > exports/research/CNAME

# Enable HTTPS and configure DNS
# Point forest-research.example.com to GitHub Pages
```

## Summary

You've successfully created a comprehensive forest plot analysis portal! Here's what you've accomplished:

**✅ Data Pipeline**:
- Imported plot, tree, and environmental data
- Configured forest-specific transformations
- Calculated structural and diversity metrics

**✅ Interactive Portal**:
- Plot network overview with spatial mapping
- Individual plot detail pages
- Species analysis and ecological preferences
- Forest type comparisons

**✅ Advanced Features**:
- Custom forest structure calculations
- Species diversity indices
- Environmental gradient analysis
- Plot comparison tools

**✅ Research Tools**:
- Statistical summaries and visualizations
- Species co-occurrence networks
- Automated data updates
- Research-ready outputs

## Next Steps

### Extend Your Analysis

1. **Temporal Analysis**: Add repeat measurement data for growth analysis
2. **Biomass Estimation**: Implement allometric equations for carbon calculations
3. **Species Distribution Models**: Add environmental niche modeling
4. **Forest Dynamics**: Analyze recruitment, mortality, and succession

### Advanced Integrations

1. **Remote Sensing**: Integrate satellite data for landscape context
2. **Climate Data**: Add climate change projections and scenarios
3. **Field Apps**: Connect to mobile data collection apps
4. **Research Databases**: Link to taxonomic and trait databases

### Collaboration Features

1. **Data Sharing**: Export standardized formats for collaborators
2. **API Development**: Create data access APIs for researchers
3. **Annotation Systems**: Add field note and photo management
4. **Version Control**: Track data versions and analysis updates

This forest plot analysis portal provides a robust foundation for ecological research, monitoring, and conservation planning in New Caledonia's unique forest ecosystems.
