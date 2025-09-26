# API Export Guide

This guide covers Niamoto's JSON API export capabilities, including standard data APIs and specialized exports like Darwin Core for biodiversity data sharing.

## Overview

The JSON API export system transforms your ecological data into machine-readable JSON files that can be consumed by applications, research tools, and data aggregation platforms. Unlike HTML exports which generate human-readable websites, API exports focus on data serialization and interoperability.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Transformed │ →  │ JSON API     │ →  │ Static JSON │
│ Data        │    │ Exporter     │    │ Files       │
│ (Database)  │    │ + Optional   │    │ + Index     │
└─────────────┘    │ Transformer  │    │ Files       │
                   └──────────────┘    └─────────────┘
```

The system supports two main output patterns:

1. **Detail Files**: Individual JSON files per entity (`taxon/123.json`, `plot/5.json`)
2. **Index Files**: Summary lists with key information (`all_taxon.json`, `taxon_index.json`)

## Basic Configuration

### Simple Data API Export

```yaml
exports:
  - name: json_api
    enabled: true
    exporter: json_api_exporter

    params:
      # Output configuration
      output_dir: "exports/api"
      detail_output_pattern: "{group}/{id}.json"
      index_output_pattern: "all_{group}.json"

      # JSON formatting options
      json_options:
        indent: 4
        ensure_ascii: false
        minify: false
        exclude_null: false

      # Index structure
      index_structure:
        total_key: "total"
        list_key: "{group}"  # becomes "taxon", "plot", etc.
        include_total: true

    groups:
      - group_by: taxon
        # Detail files: Include all transformed data
        detail:
          pass_through: true

        # Index files: Select specific fields only
        index:
          fields:
            - id: taxon_id                           # Use taxon_id field as 'id'
            - name: general_info.name.value          # Nested JSON field access
            - rank: general_info.rank.value
            - occurrences_count: general_info.occurrences_count.value
            - endpoint:                              # Generated field
                generator: endpoint_url
                params:
                  base_path: "/api"
```

This configuration generates:
- `api/taxon/1.json` - Full taxon data
- `api/taxon/2.json` - Full taxon data
- `api/all_taxon.json` - Index with selected fields only

## Database Integration

### Table and ID Field Mapping

The JSON API exporter automatically maps database tables and ID fields:

```yaml
# Configuration uses group names that match database tables
groups:
  - group_by: taxon     # → queries 'taxon' table, uses 'taxon_id' field
  - group_by: plot      # → queries 'plot' table, uses 'plot_id' field
  - group_by: shape     # → queries 'shape' table, uses 'shape_id' field
```

**Important**: The field mapping configuration must use the actual database field names:

```yaml
index:
  fields:
    - id: taxon_id        # Correct: references actual database column
    - id: id              # Incorrect: this field doesn't exist in taxon table
```

### JSON Column Processing

Niamoto stores complex transformed data as JSON in database columns. The exporter automatically:

1. **Parses JSON columns** into accessible data structures
2. **Flattens nested data** for template compatibility
3. **Preserves original column structure** alongside flattened access

Example database structure:
```sql
-- Taxon table with JSON columns
CREATE TABLE taxon (
    taxon_id INTEGER PRIMARY KEY,
    general_info JSON,           -- {"name": {"value": "Species name"}, ...}
    distribution_map JSON,       -- Geographic data
    dbh_distribution JSON        -- Size distribution data
);
```

Accessing nested JSON data in configuration:
```yaml
fields:
  - name: general_info.name.value          # Access nested JSON: general_info.name.value
  - family: general_info.parent_family.value
  - endemic: general_info.endemic.value
```

## Field Mapping System

### Basic Field Mapping

```yaml
index:
  fields:
    # Simple mapping: output_name: source_field
    - id: taxon_id
    - scientific_name: general_info.name.value
    - rank: general_info.rank.value

    # Direct field copy (output name = field name)
    - locality
    - elevation
```

### Generator Functions

Generators create calculated fields:

```yaml
fields:
  # Generate API endpoint URLs
  - endpoint:
      generator: endpoint_url
      params:
        base_path: "/api"
        pattern: "taxon/{id}.json"  # Uses the mapped 'id' field

  # Generate unique identifiers
  - occurrence_id:
      generator: unique_occurrence_id
      params:
        prefix: "niaocc_"
        source_field: "id"

  # Extract parts of scientific names
  - genus:
      generator: extract_specific_epithet
      params:
        source_field: "scientific_name"
        part: "genus"
```

**Available built-in generators:**
- `endpoint_url` - Generate API URLs
- `unique_occurrence_id` - Create prefixed unique IDs
- `unique_event_id` - Event identifiers
- `unique_identification_id` - Identification identifiers
- `extract_specific_epithet` - Parse scientific names
- `format_media_urls` - Process image/media arrays

### Complex Field Selection

```yaml
# Select specific subfields from JSON data
- metadata:
    source: "general_info"
    fields: ["endemic", "parent_family", "redlist_cat"]

# Reference data from other tables (future feature)
- full_scientific_name:
    source: "taxon_ref"
    field: "full_name"
```

## Performance Options

### JSON Optimization

```yaml
params:
  json_options:
    # Minify for production
    minify: true                    # Remove whitespace
    indent: null                    # No indentation when minified

    # Size reduction
    exclude_null: true              # Skip null values
    geometry_precision: 6           # Limit coordinate precision
    max_array_length: 1000          # Limit array sizes

    # Compression
    compress: true                  # Generate .gz files alongside .json
    ensure_ascii: false             # Allow unicode characters
```

### Parallel Processing

```yaml
params:
  performance:
    parallel: true                  # Enable parallel processing
    max_workers: 4                  # Number of worker threads
    batch_size: 50                  # Switch to parallel above this threshold
```

### Group-Specific Options

```yaml
groups:
  - group_by: shape
    # Override global options for large geometric data
    json_options:
      minify: true
      geometry_precision: 4         # Lower precision for shapes
      compress: true                # Always compress shape data

    detail:
      pass_through: true
```

## Error Handling

### Configuration

```yaml
params:
  error_handling:
    continue_on_error: true         # Don't stop on individual item failures
    log_errors: true                # Log detailed error information
    error_file: "export_errors.json" # Save error summary to file
```

### Common Issues

**Missing ID Fields**:
```
Item in group taxon has no 'taxon_id' or 'id' field
```
Solution: Ensure your field mapping uses the correct database column names.

**Nested Field Access Errors**:
```
Cannot access 'general_info.name.value': field not found
```
Solution: Verify the JSON structure in your database and adjust field paths accordingly.

**Large File Performance**:
```
Export taking too long for large datasets
```
Solution: Enable parallel processing and optimize JSON options.

## Multiple Groups Example

```yaml
exports:
  - name: biodiversity_api
    exporter: json_api_exporter

    params:
      output_dir: "exports/api"
      detail_output_pattern: "{group}/{id}.json"
      index_output_pattern: "all_{group}.json"

      # Global JSON settings
      json_options:
        indent: 2
        ensure_ascii: false

    groups:
      # Taxonomic data
      - group_by: taxon
        detail:
          pass_through: true
        index:
          fields:
            - id: taxon_id
            - scientific_name: general_info.name.value
            - rank: general_info.rank.value
            - family: general_info.parent_family.value
            - endemic: general_info.endemic.value
            - occurrences_count: general_info.occurrences_count.value
            - endpoint:
                generator: endpoint_url
                params:
                  base_path: "/api"

      # Plot/locality data
      - group_by: plot
        detail:
          pass_through: true
        index:
          fields:
            - id: plot_id
            - name: locality
            - elevation: general_info.elevation.value
            - rainfall: general_info.rainfall.value
            - coordinate_url:
                generator: endpoint_url
                params:
                  base_path: "/api"
                  pattern: "plot/{id}.json"

      # Geographic areas
      - group_by: shape
        # Optimize for large geometric data
        json_options:
          minify: true
          geometry_precision: 4
          compress: true

        detail:
          pass_through: true
        index:
          fields:
            - id: shape_id
            - name: name
            - type: type
            - area_ha: general_info.land_area_ha.value
```

This generates a complete API structure:
```
exports/api/
├── taxon/
│   ├── 1.json, 2.json, ...
├── plot/
│   ├── 1.json, 2.json, ...
├── shape/
│   ├── 1.json, 2.json, ...
├── all_taxon.json
├── all_plot.json
├── all_shape.json
└── metadata.json
```

## Using the Generated API

### Index Files

Index files provide quick access to summary information:

```json
{
  "total": 1250,
  "taxon": [
    {
      "id": 1,
      "scientific_name": "Araucaria columnaris",
      "rank": "species",
      "family": "Araucariaceae",
      "endemic": true,
      "occurrences_count": 145,
      "endpoint": "/api/taxon/1.json"
    },
    ...
  ]
}
```

### Detail Files

Detail files contain complete transformed data:

```json
{
  "taxon_id": 1,
  "general_info": {
    "name": {"value": "Araucaria columnaris"},
    "rank": {"value": "species"},
    "endemic": {"value": true},
    "parent_family": {"value": "Araucariaceae"}
  },
  "distribution_map": {
    "coordinates": [...],
    "bounds": {...}
  },
  "dbh_distribution": {
    "bins": [10, 20, 30, 40],
    "counts": [15, 25, 8, 2]
  }
}
```

## Next Steps

- [Darwin Core Export Guide](darwin-core-export.md) - Biodiversity data standards
- [API Deployment Guide](api-deployment.md) - Hosting and accessing your APIs
- [Data Integration Guide](api-integration.md) - Consuming the APIs in applications
