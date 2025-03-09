# Niamoto Configuration Reference

## Table of Contents

- [Niamoto Configuration Reference](#niamoto-configuration-reference)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Configuration Files Overview](#configuration-files-overview)
  - [config.yml](#configyml)
  - [import.yml](#importyml)
    - [Taxonomy Configuration](#taxonomy-configuration)
      - [Method 1: Dedicated Taxonomy CSV File](#method-1-dedicated-taxonomy-csv-file)
      - [Method 2: Extraction from Occurrences](#method-2-extraction-from-occurrences)
      - [API Enrichment (Optional)](#api-enrichment-optional)
    - [Plots Configuration](#plots-configuration)
    - [Occurrences Configuration](#occurrences-configuration)
    - [Shape Statistics Configuration](#shape-statistics-configuration)
    - [Shapes Configuration](#shapes-configuration)
    - [Layers Configuration](#layers-configuration)
  - [transform.yml](#transformyml)
    - [Group Configuration](#group-configuration)
    - [Source Configuration](#source-configuration)
    - [Transformation Plugins](#transformation-plugins)
    - [Plugin Reference](#plugin-reference)
      - [Example Configurations](#example-configurations)
  - [export.yml](#exportyml)
    - [Widget Types](#widget-types)
    - [Widget Options](#widget-options)
    - [Common Widget Configurations](#common-widget-configurations)
  - [Configuration Relationships](#configuration-relationships)
  - [Best Practices](#best-practices)
  - [FAQ](#faq)
  - [Diagrams](#diagrams)
    - [Configuration Overview](#configuration-overview)

## Introduction

Niamoto uses a "Configuration over code" philosophy, with YAML configuration files directing data import, transformation, and visualization. This reference document provides detailed information about each configuration file, its structure, and available options.

## Configuration Files Overview

Niamoto uses four main YAML configuration files:

- **config.yml**: Global configuration settings for the application
- **import.yml**: Data source definitions and import parameters
- **transform.yml**: Data transformation and calculation rules
- **export.yml**: Visualization and UI configuration

These files work together in a pipeline, where:
1. `import.yml` defines **where** to get data from
2. `transform.yml` defines **what** calculations to perform
3. `export.yml` defines **how** to present the results

## config.yml

The global configuration file contains system-level settings.

```yaml
database:
  path: db/niamoto.db
logs:
  path: logs
exports:
  web: exports      # web root directory
  api: exports/api  # api root directory
  files: exports/files # static files directory
plugins:
  path: plugins     # project plugins directory
```

| Section    | Option  | Description                          | Required | Default         |
| ---------- | ------- | ------------------------------------ | -------- | --------------- |
| `database` | `path`  | Path to SQLite database file         | Yes      | `db/niamoto.db` |
| `logs`     | `path`  | Directory for log files              | Yes      | `logs`          |
| `exports`  | `web`   | Root directory for generated website | Yes      | `exports`       |
| `exports`  | `api`   | Directory for API JSON files         | Yes      | `exports/api`   |
| `exports`  | `files` | Directory for other exported files   | Yes      | `exports/files` |
| `plugins`  | `path`  | Directory for custom plugins         | Yes      | `plugins`       |

## import.yml

This file defines data sources for import into the Niamoto system.

### Taxonomy Configuration

Niamoto offers two methods for importing taxonomy data:

#### Method 1: Dedicated Taxonomy CSV File

```yaml
taxonomy:
  type: csv
  path: "imports/taxonomy.csv"
  source: "file"  # Explicit but optional as it's the default value
  identifier: "id_taxon"
  ranks: "id_famille,id_genre,id_espèce,id_sous-espèce"
```

This method requires a structured CSV file with the following columns:

| Column           | Description                                          |
| ---------------- | ---------------------------------------------------- |
| `id_taxon`       | Unique identifier of the taxon                       |
| `full_name`      | Full name of the taxon                               |
| `rank_name`      | Taxonomic rank (e.g., famille, genre, espèce)        |
| `id_famille`     | Identifier of the family to which the taxon belongs  |
| `id_genre`       | Identifier of the genus to which the taxon belongs   |
| `id_espèce`      | Identifier of the species to which the taxon belongs |
| `id_sous-espèce` | Infraspecific identifier of the taxon                |
| `authors`        | Authors of the taxon name                            |

#### Method 2: Extraction from Occurrences

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

This method extracts taxonomy directly from the occurrences file, with mappings defined in `occurrence_columns`.

#### API Enrichment (Optional)

For detailed information about the API taxonomy enrichment features, refer to the [API Taxonomy Enrichment Guide](api_taxonomy_enrichment.md).

```yaml
api_enrichment:
  enabled: true
  plugin: "api_taxonomy_enricher"
  api_url: "https://api.example.com/v1/taxons"
  auth_method: "api_key"
  auth_params:
    key: "your-api-key"
    location: "header"
    name: "apiKey"
  # Additional configuration...
```

### Plots Configuration

Options for importing plot data.

```yaml
plots:
  type: csv  # or vector
  path: "imports/plots.csv"
  identifier: "id_plot"
  locality_field: "plot"
  location_field: "geo_pt"
  link_field: "locality"
  occurrence_link_field: "plot_name"
```

| Option                  | Description                          | Required | Example               |
| ----------------------- | ------------------------------------ | -------- | --------------------- |
| `type`                  | Data source type (`csv` or `vector`) | Yes      | `csv`                 |
| `path`                  | Path to source file                  | Yes      | `"imports/plots.csv"` |
| `identifier`            | Field with plot identifier           | Yes      | `"id_plot"`           |
| `locality_field`        | Field with locality name             | Yes      | `"plot"`              |
| `location_field`        | Field with geometry data             | Yes      | `"geo_pt"`            |
| `link_field`            | Field in plot_ref for links          | No       | `"locality"`          |
| `occurrence_link_field` | Field in occurrences for links       | No       | `"plot_name"`         |

### Occurrences Configuration

Options for importing occurrence data.

```yaml
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  identifier: "id_taxonref"
  location_field: "geo_pt"
```

| Option           | Description                 | Required | Example                     |
| ---------------- | --------------------------- | -------- | --------------------------- |
| `type`           | Data source type            | Yes      | `csv`                       |
| `path`           | Path to source file         | Yes      | `"imports/occurrences.csv"` |
| `identifier`     | Field with taxon identifier | Yes      | `"id_taxonref"`             |
| `location_field` | Field with geometry data    | Yes      | `"geo_pt"`                  |

### Shape Statistics Configuration

```yaml
shape_stats:
  type: csv
  path: "imports/row_shape_stats.csv"
  identifier: "id"
```

| Option       | Description                 | Required | Example                         |
| ------------ | --------------------------- | -------- | ------------------------------- |
| `type`       | Data source type            | Yes      | `csv`                           |
| `path`       | Path to source file         | Yes      | `"imports/row_shape_stats.csv"` |
| `identifier` | Field with shape identifier | Yes      | `"id"`                          |

### Shapes Configuration

List of vector shapes to import.

```yaml
shapes:
  - category: "provinces"
    type: vector
    format: directory_shapefiles
    path: "imports/shapes/provinces"
    name_field: "nom"
    label: "Provinces"
    description: "Administrative boundaries of the provinces"
  # Additional shapes...
```

| Option        | Description          | Required | Example                          |
| ------------- | -------------------- | -------- | -------------------------------- |
| `category`    | Category identifier  | Yes      | `"provinces"`                    |
| `type`        | Data type            | Yes      | `vector`                         |
| `format`      | Vector format        | Yes      | `directory_shapefiles`           |
| `path`        | Path to source file  | Yes      | `"imports/shapes/provinces"`     |
| `name_field`  | Field with name      | Yes      | `"nom"`                          |
| `label`       | Human-readable label | Yes      | `"Provinces"`                    |
| `description` | Description          | No       | `"Administrative boundaries..."` |

### Layers Configuration

List of raster and vector layers to import.

```yaml
layers:
  - name: "forest_cover"
    type: vector
    format: shapefile
    path: "imports/layers/forest_cover.shp"
    description: "Forest cover layer"

  - name: "elevation"
    type: raster
    path: "imports/layers/mnt100.tif"
    description: "Digital elevation model"
  # Additional layers...
```

| Option        | Description                | Required | Example                     |
| ------------- | -------------------------- | -------- | --------------------------- |
| `name`        | Layer name                 | Yes      | `"forest_cover"`            |
| `type`        | Layer type                 | Yes      | `raster` or `vector`        |
| `format`      | Format (for vector layers) | No       | `shapefile`                 |
| `path`        | Path to source file        | Yes      | `"imports/layers/file.tif"` |
| `description` | Description                | No       | `"Forest cover layer"`      |

## transform.yml

This file defines data transformations that process the imported data.

### Group Configuration

Each transformation group begins with:

```yaml
- group_by: taxon  # or plot, shape
  source:
    # Source configuration
  widgets_data:
    # Transformation definitions
```

| Option         | Description             | Required | Example                     |
| -------------- | ----------------------- | -------- | --------------------------- |
| `group_by`     | Group type              | Yes      | `taxon`, `plot`, or `shape` |
| `source`       | Source configuration    | Yes      | See below                   |
| `widgets_data` | List of transformations | Yes      | See below                   |

### Source Configuration

```yaml
source:
  data: occurrences       # Source data table
  grouping: taxon_ref     # Table for grouping
  relation:
    plugin: nested_set    # Relation plugin
    key: taxon_ref_id     # Key field
    fields:               # Optional fields
      parent: parent_id
      left: lft
      right: rght
```

| Option            | Description        | Required | Example        |
| ----------------- | ------------------ | -------- | -------------- |
| `data`            | Source data table  | Yes      | `occurrences`  |
| `grouping`        | Table for grouping | Yes      | `taxon_ref`    |
| `relation.plugin` | Relation plugin    | Yes      | `nested_set`   |
| `relation.key`    | Key field          | Yes      | `taxon_ref_id` |
| `relation.fields` | Additional fields  | No       | See above      |

### Transformation Plugins

Each transformation is defined by a plugin and its parameters:

```yaml
widget_name:
  plugin: plugin_name
  params:
    # Plugin-specific parameters
```

### Plugin Reference

The following table lists common transformation plugins:

| Plugin                              | Description                              | Key Parameters                                   | Example Use                  |
| ----------------------------------- | ---------------------------------------- | ------------------------------------------------ | ---------------------------- |
| `field_aggregator`                  | Aggregates fields from different sources | `fields`                                         | General information          |
| `geospatial_extractor`              | Extracts geospatial data                 | `source`, `field`, `format`                      | Distribution maps            |
| `binary_counter`                    | Counts binary values                     | `source`, `field`, `true_label`, `false_label`   | Distribution by substrate    |
| `top_ranking`                       | Identifies top items in a dataset        | `source`, `field`, `target_ranks`, `count`       | Most common species          |
| `binned_distribution`               | Creates histogram data                   | `source`, `field`, `bins`                        | DBH distribution             |
| `statistical_summary`               | Calculates statistics                    | `source`, `field`, `stats`, `units`, `max_value` | Maximum height, wood density |
| `categorical_distribution`          | Distribution of categorical values       | `source`, `field`, `categories`, `labels`        | Life zone distribution       |
| `transform_chain`  | Chains multiple transformations ([detailed guide](../guides/transform_chain_guide.md))| `steps`              | Complex transformations      |
| `class_object_field_aggregator`     | Aggregates class object fields           | `fields`                                         | Shape statistics             |
| `class_object_binary_aggregator`    | Aggregates binary class objects          | `groups`                                         | Forest cover                 |
| `class_object_categories_extractor` | Extracts categories from class objects   | `class_object`, `categories_order`               | Land use                     |

For detailed documentation on each plugin, refer to the [Plugin Reference Guide](plugin_reference.md).

#### Example Configurations

**field_aggregator**:
```yaml
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
```

**binned_distribution**:
```yaml
dbh_distribution:
  plugin: binned_distribution
  params:
    source: occurrences
    field: dbh
    bins: [10, 20, 30, 40, 50, 75, 100, 200, 300, 400, 500]
```

**transform_chain**:
```yaml
phenology:
  plugin: "transform_chain"
  params:
    steps:
      - plugin: "time_series_analysis"
        params:
          source: occurrences
          fields:
            fleur: flower
            fruit: fruit
          time_field: month_obs
          labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        output_key: "phenology_raw"

      - plugin: "custom_calculator"
        params:
          operation: "peak_detection"
          time_series: "@phenology_raw.month_data"
          threshold: 30
        output_key: "phenology_peaks"
```
For a comprehensive explanation of the transform chain system, including advanced reference resolution, function application, and best practices, see the [Transform Chain Guide](../guides/transform_chain_guide.md).

## export.yml

This file defines how transformed data is visualized and exported.

Each export group starts with:

```yaml
- group_by: taxon  # or plot, shape
  widgets:
    # Widget definitions
```

### Widget Types

Each widget is defined by a type and its parameters:

```yaml
widget_name:
  type: widget_type
  title: "Widget Title"
  description: "Widget description"
  source: data_source
  # Additional options
```

| Type             | Description                     | Example Use             |
| ---------------- | ------------------------------- | ----------------------- |
| `info_panel`     | Displays information in a panel | General information     |
| `map_panel`      | Displays a map                  | Distribution maps       |
| `bar_chart`      | Bar chart visualization         | Species distribution    |
| `doughnut_chart` | Donut chart visualization       | Substrate distribution  |
| `gauge`          | Gauge visualization             | Maximum height, density |
| `line_chart`     | Line chart visualization        | Time series data        |

### Widget Options

Common widget options include:

| Option        | Description        | Required | Applies To   |
| ------------- | ------------------ | -------- | ------------ |
| `type`        | Widget type        | Yes      | All widgets  |
| `title`       | Widget title       | Yes      | All widgets  |
| `description` | Widget description | No       | All widgets  |
| `source`      | Data source        | Yes      | All widgets  |
| `layout`      | Layout type        | No       | `info_panel` |
| `fields`      | Fields to display  | Yes      | `info_panel` |
| `layers`      | Map layers         | Yes      | `map_panel`  |
| `datasets`    | Chart datasets     | Yes      | Charts       |
| `labels_key`  | Field for labels   | Yes      | Charts       |
| `value_key`   | Field for value    | Yes      | `gauge`      |
| `options`     | Chart.js options   | No       | Charts       |

### Common Widget Configurations

**info_panel**:
```yaml
general_info:
  type: info_panel
  title: "General Information"
  layout: grid
  fields:
    - source: name
      label: "Taxon"
    - source: rank
      label: "Rank"
      format: "map"
      mapping:
        "family": "Family"
        "genus": "Genus"
        "species": "Species"
    - source: occurrences_count
      label: "Number of occurrences"
      format: "number"
```

**bar_chart**:
```yaml
dbh_distribution:
  type: bar_chart
  title: "DBH Distribution"
  description: "Distribution of tree diameters"
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
          text: "Number of occurrences"
      x:
        title:
          display: true
          text: "DBH (cm)"
```

**gauge**:
```yaml
height_max:
  type: gauge
  title: "Maximum Height"
  description: "Maximum height reached by the taxon"
  source: height_max
  value_key: "max"
  options:
    min: 0
    max: 40
    units: "m"
    sectors:
      - color: '#f02828'
        range: [0, 10]
      - color: '#fe6a00'
        range: [10, 18]
      # Additional sectors...
```

## Configuration Relationships

The three main configuration files work together in a pipeline:

1. **import.yml** defines data sources:
   - `taxonomy`, `plots`, `occurrences`, etc.

2. **transform.yml** processes these sources with plugins:
   - References source tables from import.yml
   - Produces JSON data structures as output

3. **export.yml** visualizes the transformed data:
   - References output data by the `source` field
   - Creates visual representations of the data

For example:
- A `top_ranking` transformation in transform.yml produces data with `tops` and `counts` fields
- A `bar_chart` in export.yml references this with `source: top_species` and maps `tops` to labels and `counts` to values

## Best Practices

1. **Consistent naming**: Use consistent naming throughout your configuration files
2. **Comment your configuration**: Add comments to explain complex transformations
3. **Keep transformations focused**: Each transformation should do one thing well
4. **Start simple**: Begin with simple transformations and build complexity gradually
5. **Validate your data**: Ensure your source data meets the expected format
6. **Test incrementally**: Test each step of your configuration pipeline independently

## FAQ

**Q: Can I use multiple data sources in a single transformation?**
A: Yes, many plugins like `field_aggregator` can reference multiple sources.

**Q: How do I debug a transformation that isn't working?**
A: Use `niamoto transform --verbose` to see detailed logs.

**Q: Can I extend Niamoto with custom transformations?**
A: Yes, you can create custom plugins in the `plugins/` directory.

**Q: How do widget names relate to transformation outputs?**
A: The widget name in transform.yml becomes the JSON field name in the database, which is then referenced by the `source` field in export.yml.

**Q: Can I change the appearance of widgets without changing the data?**
A: Yes, modify export.yml to change visualization without affecting data transformations.


## Diagrams

### Configuration Overview

![Niamoto Configuration Workflow](../assets/images/configuration-workflow-diagram.svg)

![Niamoto Plugin Architecture](../assets/images/plugin-system-architecture.svg)

![Niamoto Plugin Lifecycle](../assets/images/plugin-lifecycle-diagram.svg)
