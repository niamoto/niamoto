
[![PyPI - Version](https://img.shields.io/pypi/v/niamoto.svg)](https://pypi.org/project/niamoto)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/niamoto.svg)](https://pypi.org/project/niamoto)

-----

**Table of Contents**

- [Introduction](#introduction)
- [Installation](#installation)
- [Initial Configuration](#initial-configuration)
- [Available Commands](#available-commands)
  - [`niamoto init [--reset]`](#niamoto-init---reset)
  - [`niamoto import_data <csvfile>`](#niamoto-import_data-csvfile)
  - [`niamoto generate_static_site`](#niamoto-generate_static_site)
- [Development Environment Configuration](#development-environment-configuration)
- [CSV File Format for Import](#csv-file-format-for-import)
- [Static Type Checking and Testing with mypy and pytest](#static-type-checking-and-testing-with-mypy-and-pytest)
  - [Using mypy for Static Type Checking](#using-mypy-for-static-type-checking)
  - [Running Tests with pytest](#running-tests-with-pytest)
- [License](#license)
- [Contribution](#contribution)

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

## Available Commands

### `niamoto init [--reset]`
Initializes or resets the Niamoto environment.

### `niamoto import_data <csvfile>`
Imports data from a CSV file into the specified table in the database.

### `niamoto generate_static_site`
Generates static web pages for each taxon in the database.

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

## CSV File Format for Import

For data import, Niamoto expects structured CSV files with the following columns:

| Column          | Description |
|-----------------|-------------|
| `id_source`     | Data source identifier |
| `source`        | Data source name |
| `original_name` | Original species name |
| `family`        | Taxonomic family of the species |
| `taxaname`      | Taxonomic name of the species |
| `taxonref`      | Complete taxonomic reference of the species |
| `rank`          | Taxonomic rank |
| `dbh`           | Tree diameter at breast height |
| `height`        | Tree height |
| `flower`        | Presence of flowers (boolean value) |
| `fruit`         | Presence of fruits (boolean value) |
| `month_obs`     | Month of observation |
| `wood_density`  | Wood density |
| `leaf_sla`      | Specific leaf area |
| `bark_thickness`| Bark thickness |
| `leaf_area`     | Leaf area |
| `leaf_thickness`| Leaf thickness |
| `leaf_ldmc`     | Leaf dry matter content |
| `strate`        | Vegetation stratum |
| `elevation`     | Elevation |
| `rainfall`      | Rainfall |
| `holdridge`     | Holdridge life zone |
| `province`      | Province |
| `in_forest`     | Presence in a forest (boolean value) |
| `in_um`         | Presence on ultramafic substrate (boolean value) |
| `is_tree`       | Indicates if the organism is a tree (boolean value) |
| `id_taxonref`   | Taxonomic reference identifier |
| `id_family`     | Taxonomic family identifier |
| `id_genus`      | Taxonomic genus identifier |
| `id_species`    | Taxonomic species identifier |
| `id_infra`      | Infraspecific taxonomic identifier |
| `geo_pt`        | Geographic point (coordinates) |
| `plot`          | Plot identifier |


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


## License

`niamoto` is distributed under the terms of the [GPL-3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later.html) license.

## Contribution

Instructions for contributing to the Niamoto project.
