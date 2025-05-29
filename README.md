# Niamoto

[![PyPI - Version](https://img.shields.io/pypi/v/niamoto.svg)](https://pypi.org/project/niamoto)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/niamoto.svg)](https://pypi.org/project/niamoto)
[![Tests](https://github.com/niamoto/niamoto/workflows/Tests/badge.svg)](https://github.com/niamoto/niamoto/actions)
[![Documentation Status](https://readthedocs.org/projects/niamoto/badge/?version=latest)](https://niamoto.readthedocs.io/)
[![Code Coverage](https://codecov.io/gh/niamoto/niamoto/branch/main/graph/badge.svg)](https://codecov.io/gh/niamoto/niamoto)

Niamoto is a powerful CLI tool for managing and analyzing ecological data, with a focus on taxonomic data management, statistical analysis, and static website generation for ecological data visualization.

-----

## Table of Contents

- [Niamoto](#niamoto)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Installation](#installation)
  - [Initial Configuration](#initial-configuration)
  - [Development Environment Configuration](#development-environment-configuration)
  - [Taxonomy Data Import](#taxonomy-data-import)
    - [Method 1: Dedicated Taxonomy CSV File](#method-1-dedicated-taxonomy-csv-file)
    - [Method 2: Extraction from Occurrences](#method-2-extraction-from-occurrences)
    - [Niamoto CLI Commands](#niamoto-cli-commands)
      - [1. Initialize or Check Your Environment](#1-initialize-or-check-your-environment)
      - [2. Import Data](#2-import-data)
      - [3. Transform Data](#3-transform-data)
      - [4. Export Content](#4-export-content)
      - [5. Deploy Content](#5-deploy-content)
  - [Project Structure](#project-structure)
  - [Niamoto Configuration Overview](#niamoto-configuration-overview)
    - [1. Import Configuration](#1-import-configuration)
    - [Key Points](#key-points)
    - [2. Transform Configuration](#2-transform-configuration)
    - [import.yml Example](#importyml-example)
    - [3. Export Configuration](#3-export-configuration)
    - [export.yml Example](#exportyml-example)
  - [Plugin System](#plugin-system)
    - [Plugin Types](#plugin-types)
    - [Transformation Plugins](#transformation-plugins)
    - [Custom Plugin Development](#custom-plugin-development)
    - [Summary](#summary)
  - [Static Type Checking and Testing with mypy and pytest](#static-type-checking-and-testing-with-mypy-and-pytest)
    - [Using mypy for Static Type Checking](#using-mypy-for-static-type-checking)
    - [Running Tests with pytest](#running-tests-with-pytest)
  - [Documentation](#documentation)
  - [Contributing](#contributing)
  - [License](#license)
  - [Changelog](#changelog)

## Introduction

The Niamoto CLI is a tool designed to facilitate the configuration, initialization, and management of data for the Niamoto platform. This tool allows users to configure the database, import data from CSV files, and generate static websites.

## Installation

```bash
pip install niamoto
```

## Initial Configuration

After installation, initialize the Niamoto environment using the command:

```bash
niamoto init
```

This command will create the default configuration necessary for Niamoto to operate. Use the `--reset` option to reset the environment if it already exists.

## Development Environment Configuration

To set up a development environment for Niamoto, you must have `uv` installed on your system. UV is a fast Python package installer and resolver written in Rust.

1. **UV Installation**:

  To install UV, run the following command:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

2. **Clone the Niamoto repository**:

  Clone the Niamoto repository on your system using `git`:

  ```bash
  git clone https://github.com/niamoto/niamoto.git
  ```

3. **Configure the development environment with UV**:

  Move into the cloned directory and install the dependencies with UV:

  ```bash
  cd niamoto
  uv venv
  source .venv/bin/activate  # On Unix/macOS
  # or
  .venv\Scripts\activate  # On Windows
  uv pip install -e ".[dev]"
  ```

4. **Installation**:

  The previous command already installed the project in editable mode (with the -e flag). This means source code changes are immediately reflected without needing to reinstall the package.

5. **Managing Multiple Niamoto Installations**:

  When using `uv pip install -e .`, you may have multiple Niamoto installations on your system:

  - **Editable installation**: Installed in your project's virtual environment (e.g., `.venv/lib/python3.12/site-packages`)
  - **Global installation**: May exist if previously installed with `pip install niamoto` or `pipx install niamoto`

  To check which version you're using:
  ```bash
  # Check which niamoto executable is being used
  which niamoto

  # Check installed version with uv
  uv pip show niamoto
  ```

  If you have a global installation (e.g., via pipx in `~/.local/bin/niamoto`) that conflicts with your development version:

  - **Option 1**: Use `uv run niamoto` from your project directory to ensure the editable version is used
  - **Option 2**: Activate your virtual environment with `source .venv/bin/activate` before running `niamoto`
  - **Option 3**: Uninstall the global version with `pipx uninstall niamoto` to avoid confusion
  - **Option 4**: Reinstall globally from your local code with `pipx install --editable .`

## Taxonomy Data Import

Niamoto offers two methods for importing taxonomic data:

### Method 1: Dedicated Taxonomy CSV File

To import taxonomic data into Niamoto, you can provide a structured CSV file with the following columns:

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

Configuration in `import.yml`:

```yaml
taxonomy:
  type: csv
  path: "imports/taxonomy.csv"
  source: "file"  # Explicit but optional as it's the default value
  identifier: "id_taxon"
  ranks: "id_famille,id_genre,id_espèce,id_sous-espèce"
```

### Method 2: Extraction from Occurrences

Niamoto can now extract taxonomy directly from the occurrences file, which simplifies data management when taxonomic information is already present in this file.

Configuration in `import.yml`:

```yaml
taxonomy:
  type: csv
  path: "imports/occurrences.csv"  # Path to occurrences file
  source: "occurrence"  # Indicates to extract taxonomy from occurrences
  ranks: "family,genus,species,infra"
  occurrence_columns:
    taxon_id: "id_taxonref"
    family: "family"
    genus: "genus"
    species: "species"
    infra: "infra"
    authors: "taxonref"  # Can extract authors from taxonref
```

This method offers several advantages:

- Eliminates the need for a separate taxonomy file
- Ensures consistency between occurrences and taxonomy
- Provides flexibility in column mapping via `occurrence_columns`

### Niamoto CLI Commands

This section describes the command-line interface (CLI) commands available in Niamoto for managing your environment, importing data, transforming data, exporting content, and deploying.

#### 1. Initialize or Check Your Environment

```bash
# Initialize the environment (or check the current status)
$ niamoto init

# Reinitialize the database and remove generated files in the outputs directory
$ niamoto init --reset
```

#### 2. Import Data

```bash
# Import taxonomy data
$ niamoto import taxonomy <file>

# Import occurrence data
$ niamoto import occurrences <file>

# Import plot data
$ niamoto import plots <file>

# Import all sources defined in the configuration
$ niamoto import
```

#### 3. Transform Data

```bash
# Transform data by taxon
$ niamoto transform --group taxon

# Transform data by plot
$ niamoto transform --group plot

# Transform data by shape
$ niamoto transform --group shape

# Transform for all groups
$ niamoto transform
```

#### 4. Export Content

```bash
# Export static pages by taxon
$ niamoto export pages --group taxon

# Export static pages by plot
$ niamoto export pages --group plot

# Export static pages by shape
$ niamoto export pages --group shape

# Export for all groups
$ niamoto export
```

#### 5. Deploy Content

```bash
# Deploy to GitHub Pages
$ niamoto deploy github --repo <url>

# Deploy to Netlify
$ niamoto deploy netlify --site-id <id>
```

## Project Structure

```bash
config/          - YAML configuration files for data pipeline:
  config.yml     - Global configuration options
  import.yml     - Data source definitions (CSV, vector, raster)
  transform.yml  - Data transformation rules and calculations
  export.yml     - Widget and chart configurations

db/              - Database files and schemas

exports/         - Generated widget data and statistics

imports/         - Raw data files (CSV, shapefiles, rasters)

logs/            - Application logs and debug information

plugins/         - Custom plugin directory for extending functionality
```

## Niamoto Configuration Overview

Niamoto uses **three** primary YAML files to handle data ingestion, stats calculation, and page presentation:

- [config.yml](examples/config/config.yml) - Global configuration
- [import.yml](examples/config/import.yml) - Data import configuration
- [transform.yml](examples/config/transform.yml) - Data transformation configuration
- [export.yml](examples/config/export.yml) - Data export and visualization configuration

1. **`import.yml`** (Data Sources):
   - Lists and describes **where** to fetch the raw data (CSV paths, database tables, shapefiles, rasters, etc.).
   - Each source can specify type (`csv`, `vector`, `raster`), path, and any special parameters (identifiers, location fields, etc.).

2. **`transform.yml`** (Data Calculations):
   - Describes **what** computations or transformations to perform for each `group_by` (e.g., `taxon`, `plot`, `shape`).
   - Each block of `widgets_data` in the config defines **one output JSON field** (i.e., "widget data") in the final stats table.
   - Transformations can be things like `count`, `bins`, `top`, `assemble_info`, or custom logic to produce aggregated results.

3. **`export.yml`** (Widgets & Charts):
   - Defines **which widgets** appear on the final pages and how they look (chart options, color schemes, labels, etc.).
   - Points to the JSON fields produced by the `transform.yml` via `source: my_widget_field`.
   - Contains chart.js–style configurations (datasets, labels, axes, legends, etc.).

By splitting these responsibilities, Niamoto provides a more modular, maintainable, and scalable system.

-----

### 1. Import Configuration

The **data configuration** file focuses on **where** each data source resides and how to interpret it.
Typical structure might look like:

```yaml
# Example data sources
taxonomy:
  type: csv
  path: "imports/occurrences.csv"  # Chemin vers le fichier d'occurrences
  source: "occurrence"  # Indique d'extraire la taxonomie des occurrences
  ranks: "family,genus,species,infra"
  occurrence_columns:
    taxon_id: "id_taxonref"
    family: "family"
    genus: "genus"
    species: "species"
    infra: "infra"
    authors: "taxonref"  # On peut extraire les auteurs du taxonref

plots:
  type: vector
  format: geopackage
  path: "imports/plots.gpkg"
  identifier: "id_locality"
  location_field: "geometry"
  link_field: "locality"  # Champ à utiliser dans plot_ref pour le lien
  occurrence_link_field: "plot_name"  # Champ à utiliser dans occurrences pour le lien

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

-----

### 2. Transform Configuration

The **transform configuration** file (`transform.yml`) defines **what** computations to perform on the data. For each group type (taxon, plot, shape), it specifies:

- **Widgets data** to generate
- **Transformation plugins** to use
- **Parameters** for each transformation

### import.yml Example

```yaml
- group_by: taxon
  source:
    data: occurrences
    grouping: taxon_ref
    relation:
      plugin: nested_set
      key: taxon_ref_id

  widgets_data:
    general_info:
      plugin: field_aggregator
      params:
        fields:
          - source: taxon_ref
            field: full_name
            target: name
          - source: taxon_ref
            field: rank_name
            target: rank
          - source: occurrences
            field: id
            target: occurrences_count
            transformation: count
          # ex:
          # {
          #   "name": "Araucaria columnaris",
          #   "rank": "espèce",
          #   "occurrences_count": 325
          # }

      distribution_map:
        plugin: geospatial_extractor
        params:
          source: occurrences
          field: geo_pt
          format: geojson
          group_by_coordinates: true
          #properties: ["taxonref", "dbh", "height"]
        # ex:
        # {
        #   "type": "FeatureCollection",
        #   "features": [
        #     {
        #       "type": "Feature",
        #       "geometry": {
        #         "type": "Point",
        #         "coordinates": [166.45, -22.18]
        #       }
        #     }
        #   ]
        # }

      top_species:
        plugin: top_ranking
        params:
          source: occurrences
          field: taxon_ref_id
          target_ranks: ["species", "infra"]
          count: 10
        # ex:
        # {
        #   "tops": ["Taxon1", "Taxon2", "Taxon3"],
        #   "counts": [10, 5, 2]
        # }

      distribution_substrat:
        plugin: binary_counter
        params:
          source: occurrences
          field: in_um
          true_label: "um"
          false_label: "num"
        # ex:
        # {
        #   "um": 230,
        #   "num": 95
        # }
```

Niamoto (or your stats calculator classes) will:

1. Load data from the sources defined in `import.yml`.
2. For each widget in `widgets_data`, run the transformations.
3. Insert/Update a table named `{group_by}_stats` (e.g. `taxon_stats`) storing each widget’s output in a JSON field named after the widget (e.g. `general_info`, `dbh_distribution`, etc.).

-----

### 3. Export Configuration

The **export configuration** file (`export.yml`) defines **how** to present the transformed data as visual widgets, including:

- **Chart types** (bar chart, doughnut chart, gauge, etc.)
- **Styling options** (colors, labels, tooltips)
- **Layout settings** (grid, full-width)

### export.yml Example

```yaml
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
```

**Key Takeaway**: The front-end or page generator uses these details to render each widget with the data from the corresponding JSON field (`source: dbh_distribution`).

## Plugin System

Niamoto includes a plugin system that allows for extensibility and customization of its functionality. Plugins are registered with the system and can be used in configuration files.

### Plugin Types

Niamoto supports several types of plugins:

- **LOADER**: For loading data from different sources
- **TRANSFORMER**: For data transformation operations
- **EXPORTER**: For exporting data to different formats

### Transformation Plugins

The system includes several built-in transformation plugins:

- **binary_counter**: Counts binary values in a dataset
- **field_aggregator**: Aggregates fields from different sources
- **statistical_summary**: Calculates statistical summaries (min, mean, max)
- **top_ranking**: Identifies top N items in a dataset

Example plugin usage in `transform.yml`:

```yaml
widgets_data:
  distribution_substrat:
    plugin: binary_counter
    params:
      source: occurrences
      field: in_um
      true_label: "um"
      false_label: "num"
```

### Custom Plugin Development

You can develop custom plugins to extend Niamoto's functionality:

1. Create a new Python module in the `plugins/` directory
2. Implement a class that inherits from one of the base plugin classes
3. Use the `@register` decorator to register your plugin

Example of a custom transformer plugin:

```python
from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig
)

@register("my_custom_transformer", PluginType.TRANSFORMER)
class MyCustomTransformer(TransformerPlugin):
    """Custom transformer plugin"""

    def transform(self, data, config):
        # Implement your transformation logic
        return transformed_data
```

-----

### Summary

1. **`import.yml`** – Where are the raw data sources? (CSV, shapefile, DB table, etc.)
2. **`transform.yml`** – For each `group_by` (taxon, shape, plot), define `widgets_data` with transformations. Each widget becomes a JSON column in `_group_by` (taxon, shape, plot) table.
3. **`export.yml`** – For each widget, define how it’s displayed (chart type, datasets, axes, etc.), referencing the JSON column by `source:`.

This **cleanly decouples** data sources, data calculations, and final presentation. You can **change** any of these layers independently:

- Modify a chart’s color or title? → `export`.
- Add a new computed field (like “mean DBH per species”)? → `transform`.
- Point Niamoto to a new CSV or raster? → `import`.

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

## Contributing

We welcome contributions to Niamoto! Here's how you can help:

1. Check for open issues or open a new issue to start a discussion around a feature idea or a bug
2. Fork the repository on GitHub to start making your changes
3. Write one or more tests which shows that the bug was fixed or that the feature works as expected
4. Send a pull request and bug the maintainer until it gets merged and published 😉

Please make sure to follow our coding standards:

- Use [Black](https://github.com/psf/black) for code formatting
- Add type hints to all functions
- Write docstrings for all public functions
- Add tests for new features

## License

`niamoto` is distributed under the terms of the [GPL-3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later.html) license.

## Release and Publishing

To release a new version of Niamoto, follow these steps:

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with the changes in the new version
3. **Build and publish** to PyPI using the publish script:

```bash
# Option 1: Set token in environment (recommended)
export PYPI_TOKEN=your-pypi-token-here
bash scripts/publish.sh

# Option 2: Without environment variable
bash scripts/publish.sh
# Then enter "__token__" as username and your PyPI token as password when prompted
```

**Note**: PyPI no longer supports username/password authentication. You must use an API token, which you can generate at [PyPI Account Management](https://pypi.org/manage/account/) in the "API tokens" section.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes in each release.
