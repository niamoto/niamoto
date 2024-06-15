
[![PyPI - Version](https://img.shields.io/pypi/v/niamoto.svg)](https://pypi.org/project/niamoto)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/niamoto.svg)](https://pypi.org/project/niamoto)

-----

**Table of Contents**

- [Introduction](#introduction)
- [Installation](#installation)
- [Initial Configuration](#initial-configuration)
- [Development Environment Configuration](#development-environment-configuration)
- [CSV File Format for Import](#csv-file-format-for-import)
- [Niamoto CLI Command Examples](#niamoto-cli-command-examples)
  - [Initialize or Reset the Environment](#1-initialize-or-reset-the-environment)
  - [Import Taxonomy Data](#2-import-taxonomy-data)
  - [Import Plot Data](#3-import-plot-data)
  - [Import Occurrences Data](#4-import-occurrences-data)
  - [Import Occurrence-Plot Links](#5-import-occurrence-plot-links)
  - [Generate Mapping](#6-generate-mapping)
  - [Calculate Statistics](#7-calculate-statistics)
  - [Generate Static Site](#8-generate-static-site)
- [Mapping Configuration](#mapping-configuration)
  - [Structure of the Mapping](#structure-of-the-mapping)
  - [Field Configuration](#field-configuration)
  - [Special Fields](#special-fields)
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


### Niamoto CLI Command Examples

This markdown summarizes the command-line interface (CLI) commands available in the Niamoto system, which helps users manage database operations and data imports without direct code interaction.

#### 1. Initialize or Reset the Environment
**Command:**
```bash
$ niamoto init [--reset]
```
**Explanation:**
Initializes or resets the Niamoto environment. Use the `--reset` option to reset the environment if it already exists, clearing all data and configurations to start fresh.

#### 2. Import All Data
**Command:**
```bash
$ niamoto import-all
```

**Explanation:**
Imports all data from CSV files and GeoPackage files into the database. This command is a shortcut to import taxonomy, plot, occurrences, and occurrence-plot links data in one go.
Assuming the following files are present in the current source directory and specified in the configuration file

#### 3. Import Taxonomy Data
**Command:**
```bash
$ niamoto import-taxonomy <csvfile> [--ranks <ranks>]
```
**Explanation:**
Imports taxonomy data from a specified CSV file. The `--ranks` option allows specifying the order of taxonomic ranks as they appear in the CSV file.

#### 4. Import Plot Data
**Command:**
```bash
$ niamoto import-plots <gpkg_file>
```
**Explanation:**
Imports plot data from a GeoPackage file into the database, which should contain plot geometries and associated attributes.

#### 5. Import Occurrences Data
**Command:**
```bash
$ niamoto import-occurrences <csvfile> --taxon-id-column <column_name>
```
**Explanation:**
Imports occurrences data from a CSV file. The `--taxon-id-column` option specifies the CSV column containing the taxon IDs needed to link occurrences to taxons.

#### 6. Import Occurrence-Plot Links
**Command:**
```bash
$ niamoto import-occurrence-plots <csvfile>
```
**Explanation:**
Imports links between occurrences and plots from a CSV file, establishing relational data within the database.

#### 7. Generate Mapping
**Command:**
```bash
$ niamoto generate-mapping --data-source <csv_file> --mapping-group <group> [--reference-table-name <table_name> --reference-data-path <path>]
```
**Explanation:**
Generates mappings from a CSV file based on specified grouping criteria. Optional parameters allow linking to reference data for enhanced mapping accuracy.

#### 8. Calculate Statistics
**Command:**
```bash
$ niamoto calculate-statistics [--mapping-group <group> --csv-file <file>]
```
**Explanation:**
Calculates statistics based on the provided mapping file and optional group or CSV file specifics.

#### 9. Generate Static Site
**Command:**
```bash
$ niamoto generate-static_files-site
```
**Explanation:**
Generates a static website for each taxon in the database, providing a visual and informational representation of taxonomic data.


### Mapping Configuration
The mapping file defines the structure and transformations of data to be imported into the database. It is a YAML file that describes the different fields, their types, the transformations to apply, and visualization options.

#### Structure of the Mapping
The mapping consists of the following elements:

- `group_by`: The field used to group the data (e.g., "taxon").
- `identifier`: The unique identifier for each group (e.g., "id_taxonref").
- `source_table_name`: The name of the target table in the database (e.g., "occurrences").
- `reference_table_name`: The name of the reference table (e.g., "taxon_ref").
- `reference_data_path`: The path to the reference data (can be null).
- `fields`: A dictionary defining the different fields to import and their configurations.

#### Field Configuration
Each field in the `fields` dictionary is defined by the following elements:

- `source`: The source of the data (e.g., "occurrences", "plots")
- `source_field`: The name of the target field in the occurrences table. Can be null for calculated fields.
- `field_type`: The data type of the field (e.g., "INTEGER", "DOUBLE", "BOOLEAN", "GEOGRAPHY").
- `label`: The label of the field.
- `description`: A description of the field.
- `transformations`: A list of transformations to apply to the field. Each transformation is defined by:
  - `name`: The name of the transformation (e.g., "count", "mean", "max", "min", "coordinates").
  - `count` (for `top` transformations): The number of top values to retrieve.
  - `target_ranks` (for `top` transformations): A list of target ranks to consider (e.g., "id_species", "id_infra").
  - `chart_type`: The type of chart to generate (e.g., "text", "pie", "map", "gauge", "bar").
  - `chart_options`: Specific options for the chart type (e.g., "max", "title", "label", "color", "indexAxis", "stacked").
- `bins`: A dictionary defining the bins for the field. It contains:
  - `values`: A list of values to discretize continuous data.
  - `chart_type`: The type of chart to generate for the bins (e.g., "bar").
  - `chart_options`: Specific options for the bin chart (e.g., "title", "color").

#### Special Fields
Some fields may have specific configurations depending on their `source` and `field_type`:

- **Calculated field** (e.g., total number of occurrences):
  - `source`: "occurrences"
  - `source_field`: null
  - `field_type`: "INTEGER"
  - `transformations`: Must contain a "count" type transformation
- **Boolean field** (e.g., occurrence on a particular substrate):
  - `source`: "occurrences"
  - `source_field`: The name of the boolean field in the occurrences table
  - `field_type`: "BOOLEAN"
  - `transformations`: May contain a "count" type transformation
- **Geographical field** (e.g., location of the occurrence):
  - `source`: "occurrences"
  - `source_field`: The name of the geographical field in the occurrences table
  - `field_type`: "GEOGRAPHY"
  - `transformations`: May contain a "coordinates" type transformation

#### Note: The transformations and bins can be defined using two equivalent notations:

#### 1. **JSON Style Notation:**

```yaml
transformations:
  - {"name": "max", "chart_type": "gauge", "chart_options": {"max": 40, "title": "Maximum", "label": "units"}}
```

#### 1. **Standard YAML Style Notation:**
This format will display both YAML notations under a single Markdown box, keeping the explanation compact and the code examples clear and easy to compare.

```yaml
transformations:
  - name: max
    chart_type: gauge
    chart_options:
      max: 40
      title: Maximum
      label: units

   ```

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

## Contribution

Instructions for contributing to the Niamoto project.
