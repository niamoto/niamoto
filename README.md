
[![PyPI - Version](https://img.shields.io/pypi/v/niamoto.svg)](https://pypi.org/project/niamoto)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/niamoto.svg)](https://pypi.org/project/niamoto)

-----

**Table of Contents**

- [Introduction](#introduction)
- [Installation](#installation)
- [Initial Configuration](#initial-configuration)
- [Development Environment Configuration](#development-environment-configuration)
- [CSV File Format for Import](#csv-file-format-for-import)
- [Niamoto CLI Commands](#niamoto-cli-commands)
  - [Environment Management](#environment-management)
  - [Data Import](#Data-Import)
  - [Statistics Generation](#Statistics-Generation)
  - [Content Generation and Deployment](#content-generation-and-deployment)
- [Niamoto Configuration Overview](#niamoto-configuration-overview)
- [Static Type Checking and Testing with mypy and pytest](#static-type-checking-and-testing-with-mypy-and-pytest)
  - [Using mypy for Static Type Checking](#using-mypy-for-static-type-checking)
  - [Running Tests with pytest](#running-tests-with-pytest)
- [License](#license)
- [Appendix](#appendix)
  - [Complete Configuration Examples](#complete-configuration-examples)

## Introduction

The Niamoto CLI is a tool designed to facilitate the configuration, initialization, and management of data for the Niamoto platform. This tool allows users to configure the database, import data from CSV files, and generate static websites.

## Installation

```console
pip install niamoto
```

## Initial Configuration

After installation, initialize the Niamoto environment using the command:

```
niamoto init
```

This command will create the default configuration necessary for Niamoto to operate. Use the `--reset` option to reset the environment if it already exists.


## Development Environment Configuration

To set up a development environment for Niamoto, you must have `Poetry` installed on your system. Poetry is a dependency management and packaging tool for Python.

1. **Poetry Installation**:

  To install Poetry, run the following command:

  ```bash
  curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
  ```

2. **Clone the Niamoto repository**:

  Clone the Niamoto repository on your system using `git`:

  ```bash
  git clone https://github.com/niamoto/niamoto.git
  ```

3. **Configure the development environment with Poetry**:

  Move into the cloned directory and install the dependencies with Poetry:
  ```bash
  cd niamoto
  poetry install
  ```

4. **Activate the virtual environment**:

  Activate the virtual environment created by Poetry:
  ```bash
  poetry shell
  ```

5. **Editable Installation**:

    If you want to install the project in editable mode (i.e., source code changes are immediately reflected without needing to reinstall the package), you can use the following command:

```console
pip install -e .
```

## CSV File Format for Taxonomy Import

To import taxonomic data into Niamoto, you must provide a structured CSV file with the following columns:

| Column         | Description                                           |
|----------------|-------------------------------------------------------|
| `id_taxon`     | Unique identifier of the taxon                        |
| `full_name`    | Full name of the taxon                                |
| `rank_name`    | Taxonomic rank (e.g., family, genus, species)         |
| `id_family`    | Identifier of the family to which the taxon belongs   |
| `id_genus`     | Identifier of the genus to which the taxon belongs    |
| `id_species`   | Identifier of the species to which the taxon belongs  |
| `id_infra`     | Infraspecific identifier of the taxon                 |
| `authors`      | Authors of the taxon name                             |


### Niamoto CLI Commands

This section describes the command-line interface (CLI) commands available in Niamoto for managing your environment, importing data, and generating content.

#### Environment Management

```bash
# Initialize new Niamoto environment
$ niamoto init setup

# Check environment status
$ niamoto init status

# Reset existing environment (use with caution)
$ niamoto init setup --reset
```

### Data Import

```bash
# Import taxonomy data
$ niamoto import taxonomy [<file>] [--ranks <ranks>]

# Import plot data
$ niamoto import plots [<file>] [--id-field <field>] [--location-field <field>]

# Import occurrence data
$ niamoto import occurrences [<file>] [--taxon-id <field>] [--location-field <field>]

# Import occurrence-plot links
$ niamoto import occurrence-plots [<file>]

# Import shape files (from config)
$ niamoto import shapes

# Import all data sources defined in config
$ niamoto import all
```

### Statistics Generation

```bash
# Calculate statistics for a specific group
$ niamoto stats calculate --group <group>

# Calculate statistics with custom data file
$ niamoto stats calculate --csv-file <file>
```

### Content Generation and Deployment

```bash
# Generate static site
$ niamoto generate site [--group <group>]

# Deploy to GitHub Pages
$ niamoto deploy github --repo <url> [--branch <branch>]
```


## Niamoto Configuration Overview

Niamoto uses **three** primary YAML files to handle data ingestion, stats calculation, and page presentation:

1. **`data_config.yaml`** (Data Sources): 
   - Lists and describes **where** to fetch the raw data (CSV paths, database tables, shapefiles, rasters, etc.).  
   - Each source can specify type (`csv`, `vector`, `raster`), path, and any special parameters (identifiers, location fields, etc.).  

2. **`stats_config.yaml`** (Data Calculations): 
   - Describes **what** computations or transformations to perform for each `group_by` (e.g., `taxon`, `plot`, `shape`).
   - Each block of `widgets_data` in the config defines **one output JSON field** (i.e., “widget data”) in the final stats table.
   - Transformations can be things like `count`, `bins`, `top`, `assemble_info`, or custom logic to produce aggregated results.

3. **`presentation_config.yaml`** (Widgets & Charts): 
   - Defines **which widgets** appear on the final pages and how they look (chart options, color schemes, labels, etc.).
   - Points to the JSON fields produced by the `stats_config` via `source: my_widget_field`.
   - Contains chart.js–style configurations (datasets, labels, axes, legends, etc.).

By splitting these responsibilities, Niamoto provides a more modular, maintainable, and scalable system.

---

### 1) `data_config.yaml` – Data Sources

The **data configuration** file focuses on **where** each data source resides and how to interpret it.  
Typical structure might look like:

```yaml
data_config:

  # Example data sources
  taxonomy:
    type: "csv"
    path: "data/sources/amap_data_taxa.csv"
    ranks: "id_famille,id_genre,id_espèce,id_sous-espèce"

  plots:
    type: "vector"          # e.g., a GeoPackage
    path: "data/sources/plots.gpkg"
    identifier: "id_locality"
    location_field: "geometry"

  occurrences:
    type: "csv"
    path: "data/sources/amap_data_occurrences.csv"
    identifier: "id_taxonref"
    location_field: "geo_pt"

  # Possibly multi-shapes
  shapes:
    - category: "provinces"
      type: "vector"
      path: "data/sources/shapes/provinces.zip"
      name_field: "nom"
      label: "Provinces"

  # Raster layers
  layers:
    - name: "forest_cover"
      type: "vector"
      path: "data/sources/layers/forest_cover.shp"
    - name: "elevation"
      type: "raster"
      path: "data/sources/layers/mnt100.tif"
```

### Key Points

- `type: "csv" | "vector" | "raster"` helps Niamoto decide which loader to use.  
- Additional fields like `identifier`, `location_field`, or `name_field` specify how the data is keyed or geo-located.  
- This config does **not** define transformations—just **data definitions** and **paths**.

---

## 2) `stats_config.yaml` – Calculations & Transformations

The **stats configuration** replaces the older notion of a single `fields:` mapping with a more flexible concept of **widgets_data**:

- **`group_by`:** Identifies the entity type (e.g., `"taxon"`, `"plot"`, `"shape"`).  
- **`identifier`:** The unique ID field for that entity.  
- **`widgets_data`:** A dictionary (or list) of “widget names” (e.g., `general_info`, `dbh_distribution`) where each widget yields **one JSON** field in the final stats table.  
- **`transformations`:** A list of steps used to compute or aggregate data for that widget.

### Example

```yaml
stats_config:
  - group_by: "taxon"
    identifier: "id_taxonref"
    source_table_name: "occurrences"

    widgets_data:
      general_info:
        transformations:
          - name: "collect_fields"
            fields:
              - { source_field: "taxon_name", key: "name" }
              - { transformation: "count", source: "occurrences", key: "occurrences_count" }
              # etc.

      dbh_distribution:
        transformations:
          - name: "bins"
            source_field: "dbh"
            bins: [10, 20, 30, 40, 50, 100]
            # Produces a JSON with bins & counts

      dbh_gauge:
        transformations:
          - name: "max_value"
            source_field: "dbh"
            # E.g., { "value": 210, "max": 500 }
```

Niamoto (or your stats calculator classes) will:

1. Load data from the sources defined in `data_config.yaml`.  
2. For each widget in `widgets_data`, run the transformations.  
3. Insert/Update a table named `{group_by}_stats` (e.g. `taxon_stats`) storing each widget’s output in a JSON field named after the widget (e.g. `general_info`, `dbh_distribution`, etc.).

---

## 3) `presentation_config.yaml` – Visualization

Lastly, the **presentation configuration** describes each **widget**’s **visual layout**:

- For a **given** `group_by`, we list multiple **widgets** (e.g., `general_info`, `map_panel`, `forest_cover`…).
- Each widget has:
  - **`type:`** – `bar_chart`, `doughnut_chart`, `gauge`, `info_panel`, `map_panel`, etc.
  - **`source:`** – The JSON field created by `stats_config`.  
  - Chart.js–style `datasets:`, `options:` for advanced styling.

### Example

```yaml
presentation_config:
  - group_by: "taxon"
    widgets:
      general_info:
        type: "info_panel"
        title: "Taxon Information"
        layout: grid
        fields:
          - source: "name"
            label: "Taxon Name"
          - source: "occurrences_count"
            label: "Occurrences"
      dbh_distribution:
        type: "bar_chart"
        title: "DBH Distribution"
        source: "dbh_distribution"
        datasets:
          - label: "Count"
            data_key: "counts"
        labels_key: "bins"
        options:
          indexAxis: "x"
```

**Key Takeaway**: The front-end or page generator uses these details to render each widget with the data from the corresponding JSON field (`source: dbh_distribution`).

---

## Migration from the Old “fields” Mapping

In the old approach, you likely had something like:

```yaml
- group_by: "taxon"
  fields:
    total_occurrences:
      source: "occurrences"
      transformations:
        - name: "count"
      chart_type: "text"
      chart_options:
        title: "Number of occurrences"
```

Now:

1. **Move** the actual **calculation** (`count`) to `stats_config.yaml` → `widgets_data: { total_occurrences: ... }`.
2. **Move** the **chart** or “text” logic to `presentation_config.yaml` (maybe `type: "text"`, `source: "total_occurrences"`).

Hence, each **“field”** becomes **one widget** that the front end can display.

---

## Special Fields & Transformations

### Calculated Fields

- Use transformations like `"count"`, `"mean"`, `"top"`, `"bins"` etc. in `stats_config`.
- They produce a JSON result stored in a single widget field.

### Boolean Fields

- A transformation can produce an object like `{ true: X, false: Y }`, which you can display with a pie chart, for instance.

### Geographical Fields

- A transformation `"coordinates"` or `"geometry_coords"` can produce a set of features.  
- The `presentation_config` might specify a `map_panel` widget referencing that JSON.

### Bins & Distribution

- If you want to discretize data (DBH, altitude, rainfall), use `"bins"` in `stats_config`.
- The resulting JSON (e.g., `{ bins: [...], counts: [...] }`) becomes the data for a bar or line chart in `presentation_config`.

---

## Summary

1. **`data_config.yaml`** – Where are the raw data sources? (CSV, shapefile, DB table, etc.)  
2. **`stats_config.yaml`** – For each `group_by` (taxon, shape, plot), define `widgets_data` with transformations. Each widget becomes a JSON column in `_stats` table.  
3. **`presentation_config.yaml`** – For each widget, define how it’s displayed (chart type, datasets, axes, etc.), referencing the JSON column by `source:`.

This **cleanly decouples** data sources, data calculations, and final presentation. You can **change** any of these layers independently:

- Modify a chart’s color or title? → `presentation_config`.
- Add a new computed field (like “mean DBH per species”)? → `stats_config`.
- Point Niamoto to a new CSV or raster? → `data_config`.

Such a separation simplifies maintenance, encourages reusability, and makes it easier for non-developers to tweak charts while developers handle transformations independently.

## Static Type Checking and Testing with mypy and pytest

### Using mypy for Static Type Checking

[mypy](http://mypy-lang.org/) is an optional static type checker for Python that aims to combine the benefits of dynamic (duck) typing and static typing. It checks the type annotations in your Python code to find common bugs as soon as possible during the development cycle.

To run mypy on your code:

```bash
mypy src/niamoto
```

### Running Tests with pytest

[pytest](https://docs.pytest.org/) is a framework that makes it easy to write simple tests, yet scales to support complex functional testing for applications and libraries.

To run your tests with pytest, use:

```bash
pytest --cov=src --cov-report html
```

## Documentation

The documentation for the Niamoto CLI tool is available in the `docs` directory. It includes information on the CLI commands, configuration options, and data import formats.

To build the documentation, you can use the following command:

```bash
cd docs
sphinx-apidoc -o . ../src/niamoto
make html
make markdown
```

## License

`niamoto` is distributed under the terms of the [GPL-3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later.html) license.


## Appendix

### Complete Configuration Examples
This appendix provides complete examples of the three main configuration files 
used in Niamoto: config.yml, sources.yml, stats.yml, and presentation.yml.
Complete Example 1: Species Distribution Analysis

### config.yml   
```yaml
database:
  path: data/db/niamoto.db
logs:
  path: logs
outputs:
  static_site: outputs
  static_api: outputs/api
```

### sources.yml
```yaml
# 1) The main basic "entities"
taxonomy:
  type: csv
  path: "data/sources/amap_data_taxa.csv"
  ranks: "id_famille,id_genre,id_espèce,id_sous-espèce"

plots:
  type: vector
  format: geopackage
  path: "data/sources/plots.gpkg"
  identifier: "id_locality"
  location_field: "geometry"

occurrences:
  type: csv
  path: "data/sources/amap_data_occurrences.csv"
  identifier: "id_taxonref"
  location_field: "geo_pt"

occurrence_plots:
  type: "csv"
  path: "data/sources/occurrence-plots.csv"
  role: "link"               
  left_key: "id_occurrence"  
  right_key: "id_plot"

# 2) Multiple shapes (administrative areas, substrates, etc.)
shapes:
  - category: "provinces"
    type: vector
    format: shapefile_zip
    path: "data/sources/shapes/provinces.zip"
    name_field: "nom"
    label: "Provinces"
    description: "Administrative boundaries of the provinces"

  - category: "communes"
    type: vector
    format: directory_shapefiles
    path: "data/sources/shapes/communes"
    name_field: "nom"
    label: "Communes"
    description: "Administrative boundaries of the communes"

  - category: "protected_areas"
    type: vector
    format: shapefile_zip
    path: "data/sources/shapes/protected_areas.zip"
    name_field: "libelle"
    label: "Aires protégées"
    description: "Protected areas"

  - category: "substrates"
    type: vector
    format: geopackage
    path: "data/sources/shapes/substrate.gpkg"
    name_field: "label"
    label: "Substrats"
    description: "Substrate types"

  - category: "holdridge"
    type: vector
    format: geopackage
    path: "data/sources/shapes/holdridge_zones.gpkg"
    name_field: "zone"
    label: "Zone de vie"
    description: "Holdridge life zones"

  - category: "water_catchments"
    type: vector
    format: shapefile_zip
    path: "data/sources/shapes/ppe.zip"
    name_field: "nom_ppe"
    label: "Captage"
    description: "Water catchment areas"

  - category: "mines"
    type: vector
    format: geopackage
    path: "data/sources/shapes/mines.gpkg"
    name_field: "region"
    label: "Emprises Minières"
    description: "Mining sites"

# 3) Layers: vectors, rasters...
layers:
  - name: "forest_cover"
    type: vector
    format: shapefile
    path: "data/sources/layers/amap_carto_3k_20240715/amap_carto_3k_20240715.shp"
    description: "Forest cover layer"

  - name: "elevation"
    type: raster
    path: "data/sources/layers/mnt100_epsg3163.tif"
    description: "Digital elevation model"

  - name: "rainfall"
    type: raster
    path: "data/sources/layers/rainfall_epsg3163.tif"
    description: "Annual rainfall distribution"

  - name: "holdridge"
    type: raster
    path: "data/sources/layers/amap_raster_holdridge_nc.tif"
    description: "Holdridge"
```

### stats.yml
```yaml
##################################################################
# 1) CONFIG POUR LES TAXONS
##################################################################
- group_by: taxon
  identifier: id_taxonref
  source_table_name: occurrences
  source_location_field: geo_pt
  reference_table_name: taxon_ref
  
  widgets_data:

    general_info:
      # On veut un champ JSON "general_info" qui combine plusieurs informations 
      # (ex: nom du taxon, rang, nombre d'occurrences…)
      transformations:
        - name: collect_fields
          items:
            - source: taxonomy
              field: full_name
              key: "name"
            - source: taxonomy
              field: rank_name
              key: "rank"
            - source: occurrences
              transformation: count
              key: "occurrences_count"

    distribution_map:
      # Doit contenir les coordonnées des occurrences, prêtes à être affichées
      # Sous forme d'un GeoJSON ou d'un array de points.
      transformations:
        - name: coordinates
          source: occurrences
          source_field: geo_pt

    top_species:
      transformations:
        - name: top
          source: occurrences
          target_ranks: ["espèce", "sous-espèce"]
          count: 10
          # ex: { "labels": [...], "values": [...], ... }

    distribution_substrat:
      # "Ultramafique vs Non‐UM"
      transformations:
        - name: count_bool
          source_field: in_um
          # ex: { "um": 30, "num": 50, ... }

    phenology_distribution:
      # Fleurs / Fruits par mois
      transformations:
        - name: temporal_phenology
          source_fields:
            fleur: flower
            fruit: fruit
          time_field: month_obs
          # ex: structure un objet : { "month_data": [...], "colors": {...} }

    dbh_distribution:
      # Distribution diamétrique + histogramme
      transformations:
        - name: dbh_bins
          source_field: dbh
          bins: [10, 20, 30, 40, 50, 75, 100, 200, 300, 400, 500]
          # ex: { "bins": [...], "counts": [...] }

    dbh:
      # Diamètre max (exemple)
      transformations:
        - name: max_value
          source_field: dbh
          units: "cm"
          max_value: 500
          # ex: { "value": 120, "max": 500, "units": "cm" }

    height_max:
      # Hauteur max
      transformations:
        - name: max_value
          source_field: height
          units: "m"
          max_value: 40
          # ex: { "value": 35, "max": 40, "units": "m" }

    elevation_distribution:
      # Bins altitudinaux
      transformations:
        - name: histogram
          source_field: elevation
          bins: [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1700]
          # ex: { "bins": [...], "counts": [...] }

    rainfall_distribution:
      transformations:
        - name: histogram
          source_field: rainfall
          bins: [1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]

    holdridge_distribution:
      transformations:
        - name: histogram
          source_field: holdridge
          bins: [1, 2, 3]
          labels: ["Sec", "Humide", "Très humide"]

    strata_distribution:
      transformations:
        - name: histogram
          source_field: strata
          bins: [1, 2, 3, 4]
          labels: ["Sous-bois", "Sous-Canopée", "Canopée", "Emergent"]

    wood_density:
      # On veut la densité moyenne & extrêmes par ex.
      transformations:
        - name: stats_min_mean_max
          source_field: wood_density
          units: "g/cm3"
          max_value: 1.2
          # ex: { "mean": 0.65, "max": 1.2, "min": 0.4 }

    bark_thickness:
      transformations:
        - name: stats_min_mean_max
          source_field: bark_thickness
          units: "mm"
          max_value: 80

    leaf_sla:
      transformations:
        - name: stats_min_mean_max
          source_field: leaf_sla
          units: "g/m2"
          max_value: 50

    leaf_area:
      transformations:
        - name: stats_min_mean_max
          source_field: leaf_area
          units: "cm2"
          max_value: 1500

    leaf_thickness:
      transformations:
        - name: stats_min_mean_max
          source_field: leaf_thickness
          units: "µm"
          max_value: 800


##################################################################
# 2) CONFIG POUR LES PLOTS
##################################################################
- group_by: plot
  identifier: id_source
  source_table_name: occurrences
  reference_table_name: plot_ref
  pivot_table_name: occurrences_plots
  filter: 
    field: source
    value: occ_ncpippn

  widgets_data:

    general_info:
      transformations:
        - name: collect_fields
          items:
            - source: plot_ref
              field: locality 
              key: "name"
            - source: plots
              field: elevation
              key: "elevation"
              units: "m"
            - source: plots
              field: rainfall
              key: "rainfall"
              units: "mm/an"
            - source: plots
              field: holdridge
              key: "holdridge"
              labels: ["Sec", "Humide", "Très humide"]
            - source: plots
              field: substrat
              key: "substrat"
              labels: 
                UM: "Substrat ultramafique"
                VS: "Substrat non ultramafique"
            - source: plots
              field: nb_families
              key: "nb_families"
            - source: plots
              field: nb_species
              key: "nb_species"
            - source: occurrences
              transformation: count
              key: "occurrences_count"

    map_panel:
      # Localisation de la parcelle
      transformations:
        - name: get_geometry
          source: plots
          source_field: geometry
        # ex: un JSON "map" : { "coordinates": [...], "label": ... }

    top_families:
      transformations:
        - name: top
          source: occurrences
          target_ranks: ["famille"]
          count: 10
        # ex: { "labels": [...], "values": [...] }

    top_species:
      transformations:
        - name: top
          source: occurrences
          target_ranks: ["espèce", "sous-espèce"]
          count: 10
        # ex: { "labels": [...], "values": [...] }
        

    dbh_distribution:
      transformations:
        - name: dbh_bins
          source_field: dbh
          bins: [10, 20, 30, 40, 50, 75, 100, 200, 300, 400, 500]
        # ex: { "bins": [...], "counts": [...], ... }

    strata_distribution:
      transformations:
        - name: histogram
          source_field: strata
          bins: [1, 2, 3, 4]
          labels: ["Sous-Bois", "Sous-Canopée", "Canopée", "Emergent"]
        # ex: { "bins": [...], "counts": [...], ... }

    height:
      transformations:
        - name: mean_value
          source_field: height
          units: "m"
          max_value: 40
        # ex: { "value": 25, "max": 40, "units": "m" }

    wood_density:
      transformations:
        - name: mean_value
          source_field: wood_density
          units: "g/cm3"
          max_value: 1.2
        # ex: { "value": 0.65, "max": 1.2, "units": "g/cm3" }

    basal_area:
      transformations:
        - name: identity_value
          source: plots
          source_field: basal_area
          units: "m²/ha"
          max_value: 100
        # ex: { "value": 25, "max": 100, "units": "m²/ha" }

    richness:
      transformations:
        - name: identity_value
          source: plots
          source_field: nb_species
          max_value: 50
        # ex: { "value": 25, "max": 50, "units": "" }

    shannon:
      transformations:
        - name: identity_value
          source: plots
          source_field: shannon
          max_value: 5
        # ex: { "value": 2.5, "max": 5, "units": "" }

    pielou:
      transformations:
        - name: identity_value
          source: plots
          source_field: pielou
          max_value: 1
        # ex: { "value": 0.5, "max": 1, "units": "" }

    simpson:
      transformations:
        - name: identity_value
          source: plots
          source_field: simpson
          max_value: 1
        # =>ex:{ "value": 0.5, "max": 1, "units": "" }
        

    biomass:
      transformations:
        - name: identity_value
          source: plots
          source_field: biomass
          units: "t/ha"
          max_value: 800
        # ex: { "value": 25, "max": 800, "units": "t/ha" }


##################################################################
# 3) CONFIG POUR LES SHAPES
##################################################################
- group_by: shape
  occurrence_location_field: geo_pt
  raw_data: data/sources/shapes/row_shape_stats.csv
  identifier: "id"
  # Les shapes ont déjà un table shape_ref + un champ "label" ?

  widgets_data:

    # 1) CHAMP "general_info"
    #    On assemble plusieurs champs (surface_totale, forest_area, pluviometrie, altitude, etc.)
    general_info:
      transformations:
        - name: collect_fields
          # À implémenter de manière générique.
          # On récupère dans row_shape_stats plusieurs class_object (land_area_ha, forest_area_ha, etc.)
          items:
            - source: shape_ref
              field: label
              key: "name"
            - source: raw_data
              class_object: "land_area_ha"
              key: "land_area_ha"
              units: "ha"
              format: "number"     
            - source: raw_data
              class_object: "forest_area_ha"
              key: "forest_area_ha"
              units: "ha"
              format: "number"
            - source: raw_data
              class_object: "forest_mining_ha"
              key: "forest_mining_ha"
              units: "ha"
              format: "number"
            - source: raw_data
              class_object: "forest_reserve_ha"
              key: "forest_reserve_ha"
              units: "ha"
              format: "number"
            - source: raw_data
              class_object: "forest_ppe_ha"
              key: "forest_ppe_ha"
              units: "ha"
              format: "number"
            - source: raw_data
              class_object: ["rainfall_min", "rainfall_max"]
              key: "rainfall"
              units: "mm/an"
              format: "range"
            - source: raw_data
              class_object: "elevation_median"
              key: "elevation_median"
              units: "m"
              format: "number"
            - source: raw_data
              class_object: "elevation_max"
              key: "elevation_max"
              units: "m"
              format: "number"
              # => ex. {"label": "PROVINCE NORD", "land_area_ha": 941252.41325591, "forest_area_ha": 321711.765827868, "forest_mining_ha": 21106, "forest_reserve_ha": 11800, "forest_ppe_ha": 48275, "rainfall": {"min": 510, "max": 4820}, "elevation_median": 214, "elevation_max": 1622}

    # 2) CHAMP "geography"
    #    On peut inclure la géométrie du shape + la géométrie "forest cover" si besoin
    geography:
      transformations:
        - name: geometry_coords
          # Filtrer le shape_gdf pour en extraire shape_coords
          # Filtrer forest_gdf pour en extraire forest_coords
          # Renvoyer un JSON { "shape_coords": ..., "forest_coords": ... }

    # 3) CHAMP "forest_cover"
    #    On veut faire un "pie" ou un "doughnut" => typiquement, on va chercher
    #    class_object = "cover_forest", "cover_forestum", "cover_forestnum"
    forest_cover:
      transformations:
        - name: extract_multi_class_object
          # Dans row_shape_stats, on a:
          #   cover_forest     => Forêt / Hors-Forêt
          #   cover_forestum   => Forêt / Hors-Forêt
          #   cover_forestnum  => Forêt / Hors-Forêt
          # L’idée est de regrouper ces 3 distributions dans un unique JSON, ex.:
          # {
          #   "emprise": { "forêt": 0.34, "hors_foret": 0.66 },
          #   "um": { "forêt": 0.23, "hors_foret": 0.77 },
          #   "num": { "forêt": 0.37, "hors_foret": 0.63 }
          # }
          params:
            # On peut paramétrer lister les "class_object" qu'on veut extraire
            - label: "emprise"
              class_object: "cover_forest"
            - label: "um"
              class_object: "cover_forestum"
            - label: "num"
              class_object: "cover_forestnum"
          # Ton code itère sur param et lit row_shape_stats[(class_object == ...)] 
          # pour "Forêt" et "Hors-forêt".

    # 4) CHAMP "land_use"
    land_use:
      transformations:
        - name: extract_by_class_object
          class_object: "land_use"
          categories_order: 
            - "NUM"
            - "UM"
            - "Sec"
            - "Humide"
            - "Très Humide"
            - "Réserve"
            - "PPE"
            - "Concessions"
            - "Forêt"
          # => parse la table row_shape_stats pour class_object = "land_use"
          # => {"categories": ["NUM", "UM", "Sec", "Humide", "Tr\u00e8s Humide", "R\u00e9serve", "PPE", "Concessions", "For\u00eat"], "values": [720516.368203804, 220736.045052106, 245865.633017676, 564601.884540423, 130784.895697811, 14272.8699792226, 94334.7084348428, 121703.503624097, 321711.765827868]}

    # 5) CHAMP "elevation_distribution"
    elevation_distribution:
      transformations:
        - name: extract_elevation_distribution
          # Dedans, tu peux soit réutiliser la fonction "calculate_elevation_distribution",
          # soit lire row_shape_stats "forest_elevation" / "land_elevation" / ...
          # L'idée : renvoyer un JSON type:
          # {
          #   "altitudes": [100,200,...,1700],
          #   "forest": [...],
          #   "non_forest": [...]
          # }

    # 6) CHAMP "holdridge"
    holdridge:
      transformations:
        - name: extract_holdridge
          # Ce param mappera holdridge_forest (Sec/Humide/Très Humide)
          # => ex. {"forest": {"sec": 0.0222477792523791, "humide": 0.2235085776628972, "tres_humide": 0.0960348154600766}, "non_forest": {"sec": 0.2389633789397109, "humide": 0.3763325240320183, "tres_humide": 0.0429129246529177}}

    # 7) CHAMP "forest_types"
    forest_types:
      transformations:
        - name: extract_by_class_object
          class_object: "cover_foresttype"
          # => ex. { "Forêt coeur": 0.064..., "Forêt mature": 0.51..., "Forêt secondaire": 0.42... }

    # 8) CHAMP "forest_cover_by_elevation"
    forest_cover_by_elevation:
      transformations:
        - name: extract_elevation_matrix
          # On peut imaginer qu’on lit forest_elevation, forest_um_elevation, forest_num_elevation,
          # => ex. { "altitudes": [...], "um": [...], "num": [...], "hors_foret_um": [...], "hors_foret_num": [...] }

    # 9) CHAMP "forest_types_by_elevation"
    forest_types_by_elevation:
      transformations:
        - name: extract_forest_types_by_elevation
          # Va lire:
          #   forest_secondary_elevation
          #   forest_mature_elevation
          #   forest_core_elevation
          # pour assembler un JSON:
          # {
          #   "altitudes": [...],
          #   "secondaire": [...],
          #   "mature": [...],
          #   "coeur": [...]
          # }

    # 10) CHAMP "fragmentation"
    fragmentation:
      transformations:
        - name: collect_fields
          # On veut juste lire 'fragment_meff_cbc' => ex. 189.98456266
          items:
            - source: raw_data
              class_object: fragment_meff_cbc
              key: "meff"

    # 11) CHAMP "fragmentation_distribution"
    fragmentation_distribution:
      transformations:
        - name: extract_distribution
          class_object: "forest_fragmentation"
          # => Sur row_shape_stats, on a "forest_fragmentation" + class_name = [10, 20, 30...], class_value = ...
          # => Produire { "sizes": [...], "values": [...] }

```

### presentation.yml
```yaml
##################################################################
# 1) PRÉSENTATION POUR LES TAXONS
##################################################################
- group_by: taxon
  widgets:
    general_info:
      type: info_panel
      title: "Informations générales"
      layout: grid
      fields:
        - source: rank
          label: "Rang"
        - source: occurrences_count
          label: "Nombre d'occurrences"
          format: "number"
      # => Ton JSON "general_info" pourrait contenir { "taxon_name": "...", "occurrences_count": 123, ... }

    distribution_map:
      type: map_panel
      title: "Distribution géographique"
      description: Distribution géographique des occurrences du taxon et de ses sous-taxons
      source: distribution_map
      layout: full_width
      layers:
        - id: "occurrences"
          source: coordinates
          style:
            color: "#1fb99d"
            weight: 1
            fillColor: "#00716b"
            fillOpacity: 0.5
            radius: 2000
      # => JSON { "coordinates": [...], "style": {...} } (selon le format produit)

    top_species:
      type: bar_chart
      title: "Sous-taxons principaux"
      description: "Principaux sous-taxons (espèce, sous-espèce)"
      source: top_species
      sortData: true
      datasets:
        - label: 'Occurrences'
          data_key: counts
          generateColors: true 
      labels_key: tops
      options:
        indexAxis: 'y'
        scales:
          x:
            beginAtZero: true
            grid: {
              display: true,
              drawBorder: true,
              drawOnChartArea: true,
              drawTicks: true
            }
            ticks: {
              stepSize: 5
            }
            title:
              display: true
              text: "Nombre d'occurrences"
          y:
            grid: {
              display: false
            }
        plugins:
          legend: {
            display: false
          }
        maintainAspectRatio: false
        responsive: true
      # => ex. JSON { "tops": [...], "counts": [...] }

    dbh_distribution:
      type: bar_chart
      title: "Distribution diamétrique (DBH)"
      description: Répartition des occurrences par classe de diamètre
      source: dbh_distribution
      datasets:
        - label: "Occurrences"
          data_key: "counts"
          backgroundColor: "#4CAF50"
      labels_key: "bins"
      options:
        scales:
          y:
            title:
              display: true
              text: "Nombre d'occurrences"
          x:
            title:
              display: true
              text: "DBH (cm)"

    phenology_distribution:
      type: line_chart   
      title: "Phénologie"
      description: Phénologie des états fertiles (fleur, fruit) du taxon et de ses sous-taxons
      source: phenology_distribution
      datasets:
        - label: "Fleur"
          data_key: "month_data.fleur"
          borderColor: "#FF9800"    
          backgroundColor: "transparent"
          tension: 0.4
          pointRadius: 4
        - label: "Fruit"
          data_key: "month_data.fruit"
          borderColor: "#4CAF50"    
          backgroundColor: "transparent"
          tension: 0.4
          pointRadius: 4
      labels: ["Jan", "Fev", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
      options:
        scales:
          y:
            title:
              display: true
              text: "Fréquence (%)"

    distribution_substrat:
      type: doughnut_chart
      title: "Distribution substrat"
      description: "Distribution des occurrences par substrat (= fréquence du taxon par substrat)"
      source: distribution_substrat
      datasets:
        - label: 'Distribution substrat'
          data_keys: ['um', 'num']
          backgroundColor: ['#b08d57', '#78909c']
          borderColor: '#ffffff'
          borderWidth: 2
      labels: ['Ultramafique (UM)', 'non-Ultramafique (NUM)']
      options:
        cutout: '1%'
        plugins:
          legend:
            display: true
            position: 'top'
            align: 'center'
            labels:
              usePointStyle: false
              padding: 20
              boxWidth: 30
              color: '#666666'
              font:
                size: 12
        layout:
          padding:
            top: 20

    holdridge_distribution:
      type: bar_chart
      title: "Milieu de vie"
      description: Fréquence des occurrences du taxon et de ses sous-taxons par milieu de vie
      source: holdridge_distribution
      datasets:
        - label: "Occurrences"
          data_key: "counts"
          backgroundColor: ["#8B0000", "#FFEB3B", "#1E88E5"]  # Rouge, Jaune, Bleu
      labels_key: "labels"
      options:
        scales:
          y:
            title:
              display: true
              text: "Altitude (m)"

    rainfall_distribution:
      type: bar_chart
      title: "Répartition pluviométrie"
      description: Distribution pluviométrique des occurrences du taxon (= fréquence par classe de pluviométrie)
      source: rainfall_distribution
      datasets:
        - label: "Occurrences"
          data_key: "counts"
          backgroundColor: "#2196F3"    # Bleu comme dans l'image
      labels_key: "bins"
      options:
        indexAxis: "y"
        scales:
          x:
            title:
              display: true
              text: "Occurrences"
          y:
            title:
              display: true
              text: "Pluviométrie (mm/an)"

    strata_distribution:
      type: bar_chart
      title: "Stratification"
      description: Répartition des occurrences par strate
      source: strata_distribution
      datasets:
        - label: "Occurrences"
          data_key: "counts"
          backgroundColor: ["#90A4AE", "#66BB6A", "#43A047", "#2E7D32"]  # Du plus clair au plus foncé
          borderWidth: 1
      labels_key: "labels"
      options:
        indexAxis: 'y'
        scales:
          x:
            title:
              display: true
              text: "Nombre d'occurrences"

    height_max:
      type: gauge
      title: "Hauteur maximale"
      description: Hauteur maximale atteint par le taxon et ses sous-taxons
      source: height_max
      value_key: "value"
      options:
        min: 0
        max: 40
        units: "m"
        sectors:
          - color: '#f02828'
            range: [0, 10]
          - color: '#fe6a00'
            range: [10, 18]
          - color: '#e8dd0f'
            range: [18, 25]
          - color: '#81e042'
            range: [25, 33]
          - color: '#049f50'
            range: [33, 40]

    wood_density:
      type: gauge
      title: "Densité de bois"
      description: Densité de bois moyenne mesuré avec une Tarière de Pressler
      source: wood_density
      value_key: "mean"
      options:
        min: 0
        max: 1.2
        units: "g/cm³"
        sectors:
          - color: '#f02828'
            range: [0.000, 0.240]
          - color: '#fe6a00'
            range: [0.240, 0.480]
          - color: '#e8dd0f'
            range: [0.480, 0.720]
          - color: '#81e042'
            range: [0.720, 0.960]
          - color: '#049f50'
            range: [0.960, 1.200]

    bark_thickness:
      type: gauge
      title: "Épaisseur d'écorce"
      description: Epaisseur moyenne de l'écorce mesurée à la jauge à écorce
      source: bark_thickness
      value_key: "mean"
      options:
        min: 0
        max: 80
        units: "mm"
        sectors:
          - color: '#f02828'
            range: [0, 16]
          - color: '#fe6a00'
            range: [16, 32]
          - color: '#e8dd0f'
            range: [32, 48]
          - color: '#81e042'
            range: [48, 64]
          - color: '#049f50'
            range: [64, 80]

    leaf_sla:
      type: gauge
      title: "Surface foliaire spécifique"
      description: Surface foliaire spécifique du taxon et de ses sous-taxons
      source: leaf_sla
      value_key: "mean"
      options:
        min: 0
        max: 50
        units: "m²·kg⁻¹"
        sectors:
          - color: '#f02828'
            range: [0, 10]
          - color: '#fe6a00'
            range: [10, 20]
          - color: '#e8dd0f'
            range: [20, 30]
          - color: '#81e042'
            range: [30, 40]
          - color: '#049f50'
            range: [40, 50]

    leaf_area:
      type: gauge
      title: "Surface foliaire"
      description: Surface foliaire du taxon et de ses sous-taxons
      source: leaf_area
      value_key: "mean"
      options:
        min: 0
        max: 1500
        units: "cm²"
        sectors:
          - color: '#f02828'
            range: [0, 300]
          - color: '#fe6a00'
            range: [300, 600]
          - color: '#e8dd0f'
            range: [600, 900]
          - color: '#81e042'
            range: [900, 1200]
          - color: '#049f50'
            range: [1200, 1500]

    leaf_thickness:
      type: gauge
      title: "Épaisseur des feuilles"
      description: Epaisseur moyenne des feuilles du taxon et de ses sous-taxons
      source: leaf_thickness
      value_key: "mean"
      options:
        min: 0
        max: 800
        units: "µm"
        sectors:
          - color: '#f02828'
            range: [0, 160]
          - color: '#fe6a00'
            range: [160, 320]
          - color: '#e8dd0f'
            range: [320, 480]
          - color: '#81e042'
            range: [480, 640]
          - color: '#049f50'
            range: [640, 800]

    


##################################################################
# 2) PRÉSENTATION POUR LES PLOTS
##################################################################
- group_by: plot
  widgets:
    general_info:
      type: info_panel
      title: "Informations générales"
      layout: grid
      fields:
        - source: elevation
          label: "altitudes"
        - source: rainfall
          label: "Précipitation annuelle moyenne"
        - source: holdridge
          label: "Milieu de vie"
        - source: substrat
          label: "Substrat"
        - source: nb_families
          label: "Nombre de familles"
        - source: nb_species
          label: "Nombre d'espèces"
        - source: occurrences_count
          label: "Nombre d'occurrences"
          format: "number"

      # => ex. { "plot_name": "Parcelle A", "basal_area": 25.3, "trees_count": 364, ... }

    map_panel:
      type: map_panel
      title: "Localisation de la parcelle"
      source: map_panel
      layout: full_width
      layers:
        - id: "plot"
          source: geometry
          style:
            color: "#1fb99d"
            weight: 2
            fillOpacity: 0
      # => ex. JSON { "coordinates": [...], "style": {...} }

    top_families:
      type: bar_chart
      title: "Familles dominantes"
      description: "Les dix familles botaniques les plus fréquentes de la parcelle"
      source: top_families
      sortData: true
      datasets:
        - label: 'Occurrences'
          data_key: counts
          generateColors: true 
      labels_key: tops
      options:
        indexAxis: 'y'
        scales:
          x:
            beginAtZero: true
            grid: {
              display: true,
              drawBorder: true,
              drawOnChartArea: true,
              drawTicks: true
            }
            ticks: {
              stepSize: 5
            }
            title:
              display: true
              text: "Nombre d'occurrences"
          y:
            grid: {
              display: false
            }
        plugins:
          legend: {
            display: false
          }
        maintainAspectRatio: false
        responsive: true
      # => ex. JSON { "labels": [...], "values": [...], ... }

    top_species:
      type: bar_chart
      title: "Sous-taxons principaux"
      description: "Les dix espèces botaniques les plus fréquentes de la parcelle"
      source: top_species
      sortData: true
      datasets:
        - label: 'Occurrences'
          data_key: counts
          generateColors: true 
      labels_key: tops
      options:
        indexAxis: 'y'
        scales:
          x:
            beginAtZero: true
            grid: {
              display: true,
              drawBorder: true,
              drawOnChartArea: true,
              drawTicks: true
            }
            ticks: {
              stepSize: 5
            }
            title:
              display: true
              text: "Nombre d'occurrences"
          y:
            grid: {
              display: false
            }
        plugins:
          legend: {
            display: false
          }
        maintainAspectRatio: false
        responsive: true
      # => ex. JSON { "tops": [...], "counts": [...] }

    dbh_distribution:
      type: bar_chart
      title: "Distribution diamétrique (DBH)"
      description: Répartition des occurrences par classe de diamètre
      source: dbh_distribution
      datasets:
        - label: "Occurrences"
          data_key: "counts"
          backgroundColor: "#4CAF50"
      labels_key: "bins"
      options:
        scales:
          y:
            title:
              display: true
              text: "Nombre d'occurrences"
          x:
            title:
              display: true
              text: "DBH (cm)"

    strata_distribution:
      type: bar_chart
      title: "Stratification"
      description: Répartition des occurrences par strate
      source: strata_distribution
      datasets:
        - label: "Occurrences"
          data_key: "counts"
          backgroundColor: ["#90A4AE", "#66BB6A", "#43A047", "#2E7D32"]  # Du plus clair au plus foncé
          borderWidth: 1
      labels_key: "labels"
      options:
        indexAxis: 'y'
        scales:
          x:
            title:
              display: true
              text: "Nombre d'occurrences"

    height:
      type: gauge
      title: "Hauteur moyenne"
      source: height
      value_key: "value"
      options:
        min: 0
        max: 40
        units: "m"
        sectors:
          - color: '#f02828'
            range: [0, 5]
          - color: '#fe6a00'
            range: [5, 10]
          - color: '#e8dd0f'
            range: [10, 15]
          - color: '#81e042'
            range: [15, 20]
          - color: '#049f50'
            range: [20, 25]

    wood_density:
      type: gauge
      title: "Densité de bois"
      description: Densité de bois moyenne mesuré avec une Tarière de Pressler
      source: wood_density
      value_key: "value"
      options:
        min: 0
        max: 1.2
        units: "g/cm³"
        sectors:
          - color: '#f02828'
            range: [0.000, 0.240]
          - color: '#fe6a00'
            range: [0.240, 0.480]
          - color: '#e8dd0f'
            range: [0.480, 0.720]
          - color: '#81e042'
            range: [0.720, 0.960]
          - color: '#049f50'
            range: [0.960, 1.200]

    basal_area:
      type: gauge
      title: "Aire basale"
      source: basal_area
      value_key: "value"
      options:
        min: 0
        max: 100
        units: "m²/ha"
        sectors:
          - color: '#f02828'
            range: [0, 15]
          - color: '#fe6a00'
            range: [15, 30]
          - color: '#e8dd0f'
            range: [30, 45]
          - color: '#81e042'
            range: [45, 60]
          - color: '#049f50'
            range: [60, 76]

    richness:
      type: gauge
      title: "Richesse"
      source: richness
      value_key: "value"
      options:
        min: 0
        max: 130
        units: ""
        sectors:
          - color: '#f02828'
            range: [0, 28]
          - color: '#fe6a00'
            range: [28, 52]
          - color: '#e8dd0f'
            range: [52, 78]
          - color: '#81e042'
            range: [78, 104]
          - color: '#049f50'
            range: [104, 130]
    shannon:
      type: gauge
      title: "Shannon"
      source: shannon
      value_key: "value"
      options:
        min: 0
        max: 5
        units: ""
        sectors:
          - color: '#f02828'
            range: [0.0, 1.0]
          - color: '#fe6a00'
            range: [1.0, 2.0]
          - color: '#e8dd0f'
            range: [2.0, 3.0]
          - color: '#81e042'
            range: [3.0, 4.0]
          - color: '#049f50'
            range: [4.0, 5.0]

    pielou:
      type: gauge
      title: "Pielou"
      source: pielou
      value_key: "value"
      options:
        min: 0
        max: 1
        units: ""
        sectors:
          - color: '#f02828'
            range: [0.00, 0.20]
          - color: '#fe6a00'
            range: [0.20, 0.40]
          - color: '#e8dd0f'
            range: [0.40, 0.60]
          - color: '#81e042'
            range: [0.60, 0.80]
          - color: '#049f50'
            range: [0.80, 1.0]

    simpson:
      type: gauge
      title: "Simpson"
      source: simpson
      value_key: "value"
      options:
        min: 0
        max: 1
        units: ""
        sectors:
          - color: '#f02828'
            range: [0.00, 0.20]
          - color: '#fe6a00'
            range: [0.20, 0.40]
          - color: '#e8dd0f'
            range: [0.40, 0.60]
          - color: '#81e042'
            range: [0.60, 0.80]
          - color: '#049f50'
            range: [0.80, 1.0]

    biomass:
      type: gauge
      title: "Biomasse"
      source: biomass
      value_key: "value"
      options:
        min: 0
        max: 800
        units: "t/ha"
        sectors:
          - color: '#f02828'
            range: [0, 160]
          - color: '#fe6a00'
            range: [160, 320]
          - color: '#e8dd0f'
            range: [320, 480]
          - color: '#81e042'
            range: [480, 640]
          - color: '#049f50'
            range: [640, 800]
      
##################################################################
# 3) PRÉSENTATION POUR LES SHAPES
##################################################################
- group_by: shape
  widgets:
    general_info:
      type: info_panel
      title: "Informations générales"
      layout: grid
      fields:
        - source: land_area_ha
          label: "Surface totale"
          suffix: " ha"
          format: "number"
        - source: forest_area_ha
          label: "Surface forêt"
          suffix: " ha"
          format: "number"
        - source: forest_mining_ha
          label: "Forêt sur mine"
          suffix: " ha"
          format: "number"
        - source: forest_reserve_ha
          label: "Forêt en réserve"
          suffix: " ha"
          format: "number"
        - source: forest_ppe_ha
          label: "Forêt sur captage (PPE)"
          suffix: " ha"
          format: "number"
        - source: rainfall
          label: "Pluviométrie"
          format: "range"
          suffix: " mm/an"
        - source: elevation_median
          label: "Altitude médiane"
          format: "number"
          suffix: " m"
        - source: elevation_max
          label: "Altitude maximale"
          format: "number"
          suffix: " m"

    map_panel:
      type: map_panel
      title: "Distribution de la forêt"
      description: "Distribution de la forêt dans l'emprise sélectionnée"
      source: geography
      layers:
        - id: shape
          source: geography.shape_coords
          style:
            color: "#1fb99d"
            weight: 2
            fillOpacity: 0
        - id: forest
          source: geography.forest_coords
          style:
            color: "#228b22"
            weight: 0.3
            fillColor: "#228b22cc"
            fillOpacity: 0.8

    forest_cover:
      type: doughnut_chart
      title: "Couverture forestière"
      description: "La couverture forestière (= superficie de forêt / superficie disponible) est un indicateur de l'importance de la forêt dans le paysage."
      source: forest_cover
      datasets:
        - label: 'Emprise'
          data_keys: ['emprise.foret', 'emprise.hors_foret']
          transformData: 'toPercentage'
          backgroundColors: ['#2E7D32', '#F4E4BC']
          borderColor: '#ffffff'
          borderWidth: 2
        - label: 'NUM'
          data_keys: ['num.foret', 'num.hors_foret']
          transformData: 'toPercentage'
          backgroundColors: ['#2E7D32', '#C5A98B']
          borderWidth: 2
          borderColor: '#ffffff'
        - label: 'UM'
          data_keys: ['um.foret', 'um.hors_foret']
          transformData: 'toPercentage'
          backgroundColors: ['#2E7D32', '#8B7355']
          borderColor: '#ffffff'
          borderWidth: 2
      labels: ['Forêt', 'Hors-forêt']
      options:
        cutout: '20%'
        rotation: -90
        plugins:
          legend:
            display: false
          tooltip:
            enabled: false
      customPlugin: 'customLabels'

    land_use:
      type: bar_chart
      title: "Occupation du sol"
      description: "Superficie occupée par le substrat, les milieux de vie de Holdridge, les limites administratives et la forêt dans l'emprise sélectionnée"
      source: land_use
      datasets:
        - label: 'Occupation du sol'
          data_key: 'values'
          color_mapping:
            NUM: "#8B4513"
            UM: "#CD853F"
            Sec: "#8B0000"
            Humide: "#FFEB3B"
            "Très Humide": "#1E88E5"
            Réserve: "#4CAF50"
            PPE: "#90CAF9"
            Concessions: "#E57373"
            Forêt: "#2E7D32"
      labels_key: 'categories'
      options:
        indexAxis: 'x'
        scales:
          x:
            title:
              display: true
              text: ''
          y:
            title:
              display: true
              text: 'Superficie (ha)'
            ticks:
              callback: 'formatSurfaceValue'

    elevation_distribution:
      type: bar_chart
      title: "Distribution altitudinale"
      description: "Distribution altitudinale de la forêt dans l'emprise"
      source: elevation_distribution
      datasets:
        - label: 'Forêt'
          data_key: 'forest'
          backgroundColor: '#2E7D32'
          stack: 'Stack 0'
        - label: 'Hors-forêt'
          data_key: 'non_forest'
          backgroundColor: '#F4E4BC'
          stack: 'Stack 0'
      labels_key: 'altitudes'
      options:
        indexAxis: 'y'
        scales:
          x:
            title:
              display: true
              text: 'Superficie (ha)'
          y:
            reverse: true
            title:
              display: true
              text: 'Altitude (m)'

    holdridge_distribution:
      type: bar_chart
      title: "Forêt et milieux de vie"
      description: "Distribution de la forêt selon les milieux de vie de Holdridge"
      source: holdridge
      datasets:
        - label: 'Forêt'
          transformData: 'toPercentage'
          data_keys: ['forest.sec', 'forest.humide', 'forest.tres_humide']
          backgroundColor: '#2E7D32'
          stack: 'Stack 0'
        - label: 'Hors-forêt'
          transformData: 'toPercentage'
          data_keys: ['non_forest.sec', 'non_forest.humide', 'non_forest.tres_humide']
          backgroundColor: '#F4E4BC'
          stack: 'Stack 0'
      labels: ['Sec', 'Humide', 'Très humide']
      options:
        indexAxis: 'x'
        scales:
          x:
            title:
              display: true
              text: 'Type de milieu'
          y:
            title:
              display: true
              text: 'Proportion (%)'

    forest_types:
      type: doughnut_chart
      title: "Types forestiers"
      description: "Répartition de la forêt selon les trois types de forêt"
      source: forest_types
      customPlugin: 'forestTypeLabelsPlugin'
      datasets:
        - label: 'Types de forêt'
          data_key: 'values'
          transformData: 'toPercentage'
          backgroundColor: ['#2E7D32', '#7CB342', '#C5E1A5']
          borderWidth: 2
          borderColor: '#ffffff'
      labels_key: 'categories'  # Utilise les catégories du JSON comme labels
      options:
        cutout: '60%'
        plugins:
          legend:
            position: 'bottom'
            labels:
              padding: 20
              font:
                size: 12
              usePointStyle: false
              boxWidth: 15
          tooltip:
            callbacks:
              label: 'formatForestTypeTooltip'

    forest_cover_by_elevation:
      type: bar_chart
      title: "Couverture forestière par altitude"
      description: "Distribution altitudinale de la couverture forestière en fonction du substrat"
      source: forest_cover_by_elevation
      datasets:
        - label: 'Forêt (UM)'
          data_key: 'um'
          backgroundColor: '#90EE90'
          stack: 'Stack 0'
          transformData: 'negateValues'
        - label: 'Forêt (NUM)'
          data_key: 'num'
          backgroundColor: '#2E7D32'
          stack: 'Stack 0'
      labels_key: 'altitudes'
      options:
        responsive: true
        maintainAspectRatio: false
        indexAxis: 'y'
        scales:
          x:
            stacked: true
            position: 'top'
            min: -100
            max: 100
            grid:
              lineWidth: 1
              drawTicks: false
              borderDash: [5, 5]
            ticks:
              callback: 'formatAbsoluteValue'
              stepSize: 20
              autoSkip: false
              maxRotation: 0
            border:
              display: false
          y:
            stacked: true
            position: 'left'
            reverse: true
            grid:
              display: true
              lineWidth: 1
              drawTicks: false
              borderDash: [5, 5]
            ticks:
              font:
                size: 12
            title:
              display: true
              text: 'Altitude (m)'
              font:
                size: 12
            border:
              display: false
        plugins:
          legend:
            position: 'bottom'
            align: 'center'
            labels:
              boxWidth: 10
              padding: 15
          title:
            display: true
            text: 'Couverture (%)'
            position: 'top'
            align: 'center'
          tooltip:
            mode: 'y'
            intersect: false
            callbacks:
              label: 'formatForestCoverTooltip'

    forest_types_by_elevation:
      type: line_chart
      title: "Types forestiers par altitude"
      description: "Distribution des types de forêts selon l'altitude"
      source: forest_types_by_elevation
      sortBy: 'altitudes'
      datasets:
        - label: 'Forêt secondaire'
          data_key: 'secondaire'
          transformData: 'stackedPercentage'
          backgroundColor: '#C5E1A5'
          borderColor: '#C5E1A5'
          fill: true
          pointStyle: 'circle'
          pointRadius: 0
          pointHoverRadius: 5
          pointHoverBackgroundColor: '#ffffff'
          tension: 0.4
          stack: 'Stack 0'
        - label: 'Forêt mature'
          data_key: 'mature'
          transformData: 'stackedPercentage'
          backgroundColor: '#7CB342'
          borderColor: '#7CB342'
          fill: true
          pointStyle: 'circle'
          pointRadius: 0
          pointHoverRadius: 5
          pointHoverBackgroundColor: '#ffffff'
          tension: 0.4
          stack: 'Stack 0'
        - label: 'Forêt de coeur'
          data_key: 'coeur'
          transformData: 'stackedPercentage'
          backgroundColor: '#2E7D32'
          borderColor: '#2E7D32'
          fill: true
          pointStyle: 'circle'
          pointRadius: 0
          pointHoverRadius: 5
          pointHoverBackgroundColor: '#ffffff'
          tension: 0.4
          stack: 'Stack 0'
      labels_key: 'altitudes'
      options:
        responsive: true
        maintainAspectRatio: false
        scales:
          x:
            title:
              display: true
              text: 'Altitude (m)'
              font:
                size: 12
            grid:
              display: false
            ticks:
              maxRotation: 0
          y:
            stacked: true
            grid:
              color: '#e5e5e5'
              borderDash: [2, 2]
            ticks:
              callback: 'formatPercentage'
            title:
              display: true
              text: 'Fréquence (%)'
              font:
                size: 12
            min: 0
            max: 100
        plugins:
          legend:
            position: 'bottom'
            labels:
              padding: 20
              usePointStyle: false
              boxWidth: 15
          tooltip:
            mode: 'index'
            intersect: false
            callbacks:
              label: 'formatForestTypeElevationTooltip'
        interaction:
          mode: 'nearest'
          axis: 'x'
          intersect: false

    fragmentation:
      type: gauge
      title: "Fragmentation"
      description: "La taille effective de maillage représente la probabilité que deux points appartiennent au même fragment de forêt"
      source: fragmentation
      value_key: 'meff'
      options:
        min: 0
        max: 1000
        units: 'km²'
        sectors:
          - color: '#f02828'
            range: [0, 200]
          - color: '#fe6a00'
            range: [200, 400]
          - color: '#e8dd0f'
            range: [400, 600]
          - color: '#81e042'
            range: [600, 800]
          - color: '#049f50'
            range: [800, 1000]

    fragmentation_distribution:
      type: line_chart
      title: "Fragments forestiers"
      description: "Aire cumulée de chaque fragment forestier classé du plus petit au plus grand"
      source: fragmentation_distribution
      sortData: true
      sortBy: 'sizes'
      datasets:
        - label: 'Aire Cumulée'
          data_key: 'values'
          backgroundColor: '#2E7D32'
          borderColor: '#2E7D32'
          fill: true
          tension: 0.3
          pointRadius: 0
          borderWidth: 2
          transformData: 'toPercentage'
      labels_key: 'sizes'
      options:
        scales:
          x:
            type: 'logarithmic'
            title:
              display: true
              text: 'Surface (ha)'
            grid:
              display: false
          y:
            title:
              display: true
              text: 'Fréquence (%)'
            grid:
              color: '#e5e5e5'
              borderDash: [2, 2]
            ticks:
              callback: 'formatPercentage'
            min: 0
            max: 100
            beginAtZero: true
        plugins:
          legend:
            position: 'bottom'
            labels:
              usePointStyle: false
              boxWidth: 15
              padding: 20
```