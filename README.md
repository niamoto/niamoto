# Niamoto

[![PyPI - Version](https://img.shields.io/pypi/v/niamoto.svg)](https://pypi.org/project/niamoto)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/niamoto.svg)](https://pypi.org/project/niamoto)
[![Tests](https://github.com/niamoto/niamoto/workflows/Tests/badge.svg)](https://github.com/niamoto/niamoto/actions)
[![Documentation Status](https://readthedocs.org/projects/niamoto/badge/?version=latest)](https://niamoto.readthedocs.io/)
[![Code Coverage](https://codecov.io/gh/niamoto/niamoto/branch/main/graph/badge.svg)](https://codecov.io/gh/niamoto/niamoto)

Niamoto is a powerful CLI tool for managing and analyzing ecological data, with a focus on taxonomic data management, statistical analysis, and static website generation for ecological data visualization.

-----

## Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
- [Initial Configuration](#initial-configuration)
- [Development Environment Configuration](#development-environment-configuration)
- [CSV File Format for Taxonomy Import](#csv-file-format-for-taxonomy-import)
- [Niamoto CLI Commands](#niamoto-cli-commands)
  - [Environment Management](#1-initialize-or-check-your-environment)
  - [Data Import](#2-import-data)
  - [Data Transformation](#3-transform-data)
  - [Content Export](#4-export-content)
  - [Content Deployment](#5-deploy-content)
- [Project Structure](#project-structure)
- [Niamoto Configuration Overview](#niamoto-configuration-overview)
  - [Import Configuration](#1-import-configuration)
  - [Transform Configuration](#2-transform-configuration)
  - [Export Configuration](#3-export-configuration)
- [Static Type Checking and Testing with mypy and pytest](#static-type-checking-and-testing-with-mypy-and-pytest)
  - [Using mypy for Static Type Checking](#using-mypy-for-static-type-checking)
  - [Running Tests with pytest](#running-tests-with-pytest)
- [License](#license)

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

4. **Editable Installation**:

  The previous command already installed the project in editable mode (with the -e flag). This means source code changes are immediately reflected without needing to reinstall the package.

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

# Import plot data
$ niamoto import plots <file>

# Import occurrence data
$ niamoto import occurrences <file>

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

```config/``` - YAML configuration files for data pipeline:

- `config.yml`: Global configuration options
- `import.yml`: Data source definitions (CSV, vector, raster)
- `transform.yml`: Data transformation rules and calculations
- `export.yml`: Widget and chart configurations

```db/``` - Database files and schemas

```exports/``` - Generated widget data and statistics

```imports/``` - Raw data files (CSV, shapefiles, rasters)

```logs/``` - Application logs and debug information

## Niamoto Configuration Overview

Niamoto uses **three** primary YAML files to handle data ingestion, stats calculation, and page presentation:

1. **`import.yml`** (Data Sources):
   - Lists and describes **where** to fetch the raw data (CSV paths, database tables, shapefiles, rasters, etc.).
   - Each source can specify type (`csv`, `vector`, `raster`), path, and any special parameters (identifiers, location fields, etc.).

2. **`transform.yml`** (Data Calculations):
   - Describes **what** computations or transformations to perform for each `group_by` (e.g., `taxon`, `plot`, `shape`).
   - Each block of `widgets_data` in the config defines **one output JSON field** (i.e., “widget data”) in the final stats table.
   - Transformations can be things like `count`, `bins`, `top`, `assemble_info`, or custom logic to produce aggregated results.

3. **`export.yml`** (Widgets & Charts):
   - Defines **which widgets** appear on the final pages and how they look (chart options, color schemes, labels, etc.).
   - Points to the JSON fields produced by the `import` via `source: my_widget_field`.
   - Contains chart.js–style configurations (datasets, labels, axes, legends, etc.).

By splitting these responsibilities, Niamoto provides a more modular, maintainable, and scalable system.

-----

### 1. Import Configuration

The **data configuration** file focuses on **where** each data source resides and how to interpret it.
Typical structure might look like:

```yaml
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

-----

### 2. Transform Configuration

The **stats configuration** replaces the older notion of a single `fields:` mapping with a more flexible concept of **widgets_data**:

- **`group_by`:** Identifies the entity type (e.g., `"taxon"`, `"plot"`, `"shape"`).
- **`identifier`:** The unique ID field for that entity.
- **`widgets_data`:** A dictionary (or list) of “widget names” (e.g., `general_info`, `dbh_distribution`) where each widget yields **one JSON** field in the final stats table.
- **`transformations`:** A list of steps used to compute or aggregate data for that widget.

### import.yml Example

```yaml
  - group_by: "taxon"
    identifier: "id_taxonref"
    source_table_name: "occurrences"

    widgets_data:
      general_info:
        # On veut un champ JSON "general_info" qui combine plusieurs informations
        # (ex: nom du taxon, rang, nombre d'occurrences…)
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

1. Load data from the sources defined in `import.yml`.
2. For each widget in `widgets_data`, run the transformations.
3. Insert/Update a table named `{group_by}_stats` (e.g. `taxon_stats`) storing each widget’s output in a JSON field named after the widget (e.g. `general_info`, `dbh_distribution`, etc.).

-----

### 3. Export Configuration

Lastly, the **presentation configuration** describes each **widget**’s **visual layout**:

- For a **given** `group_by`, we list multiple **widgets** (e.g., `general_info`, `map_panel`, `forest_cover`…).
- Each widget has:
  - **`type:`** – `bar_chart`, `doughnut_chart`, `gauge`, `info_panel`, `map_panel`, etc.
  - **`source:`** – The JSON field created by `stats_config`.
  - Chart.js–style `datasets:`, `options:` for advanced styling.

### export.yml Example

```yaml
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

-----

### Special Fields & Transformations

#### Calculated Fields

- Use transformations like `"count"`, `"mean"`, `"top"`, `"bins"` etc. in `stats_config`.
- They produce a JSON result stored in a single widget field.

#### Boolean Fields

- A transformation can produce an object like `{ true: X, false: Y }`, which you can display with a pie chart, for instance.

#### Geographical Fields

- A transformation `"coordinates"` or `"geometry_coords"` can produce a set of features.
- The `presentation_config` might specify a `map_panel` widget referencing that JSON.

#### Bins & Distribution

- If you want to discretize data (DBH, altitude, rainfall), use `"bins"` in `stats_config`.
- The resulting JSON (e.g., `{ bins: [...], counts: [...] }`) becomes the data for a bar or line chart in `presentation_config`.

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

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes in each release.
