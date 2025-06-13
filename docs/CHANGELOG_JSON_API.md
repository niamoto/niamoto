# JSON API Exporter & Darwin Core Implementation

## Overview

This document details the implementation of the JSON API export system and Darwin Core transformer for Niamoto, enabling machine-readable data exports and biodiversity data standard compliance.

## New Features

### 1. JSON API Exporter Plugin (`json_api_exporter.py`)

**Purpose**: Generate static JSON API files from transformed Niamoto data.

**Key Features**:
- **Dual output modes**: Detail files (full data) and index files (summaries)
- **Flexible field mapping**: Selective field inclusion with dot-notation access
- **Generator functions**: Built-in functions for calculated fields (URLs, IDs, etc.)
- **Performance optimization**: Parallel processing, JSON compression, size limits
- **Robust error handling**: Continue-on-error with detailed logging
- **Database integration**: Automatic table/ID field mapping

**Configuration**:
```yaml
exports:
  - name: json_api
    exporter: json_api_exporter
    params:
      output_dir: "exports/api"
      detail_output_pattern: "{group}/{id}.json"
      index_output_pattern: "all_{group}.json"
    groups:
      - group_by: taxon
        detail: {pass_through: true}
        index:
          fields:
            - id: taxon_id
            - name: general_info.name.value
```

### 2. Darwin Core Occurrence Transformer (`niamoto_to_dwc_occurrence.py`)

**Purpose**: Convert Niamoto occurrence data to Darwin Core standard format.

**Key Features**:
- **Standards compliance**: Full Darwin Core Occurrence schema support
- **Reference system**: @source (occurrence data) vs @taxon (taxon data) references
- **Specialized generators**: Coordinate parsing, date formatting, scientific name parsing
- **Data validation**: Coordinate range checking, date validation, null handling
- **Empty filtering**: Automatically skips taxa with no occurrences

**Configuration**:
```yaml
groups:
  - group_by: taxon
    transformer_plugin: niamoto_to_dwc_occurrence
    transformer_params:
      occurrence_list_source: "occurrences"
      mapping:
        scientificName: "@source.taxonref"
        decimalLatitude:
          generator: format_coordinates
          params:
            source_field: "@source.geo_pt"
            type: "latitude"
```

## Architecture Improvements

### Database Integration

**Fixed ID Field Mapping**:
- Corrected automatic ID mapping to use actual database column names
- Supports flexible ID field configuration: `taxon_id`, `plot_id`, `shape_id`
- Transparent field mapping that respects user configuration

**JSON Column Processing**:
- Automatic parsing of JSON database columns
- Nested field access via dot notation (`general_info.name.value`)
- Fallback handling for malformed or missing data

### Configuration System Enhancements

**Pydantic v2 Integration**:
- Full validation of export configurations
- Type-safe parameter handling
- Improved error messages

**Generator Functions**:
- Extensible system for calculated fields
- Built-in generators for common transformations
- Parameter-driven customization

## File Generation Strategy

### Smart File Generation

**Index Filtering**: Only generates index entries for entities that produced output files
- Prevents empty file references in indexes
- Improves data quality and user experience
- Reduces storage overhead

**Empty Result Handling**:
- Darwin Core transformer returns empty lists for taxa without occurrences
- JSON API exporter skips empty lists automatically
- No empty files generated for entities without data

### Performance Optimizations

**Parallel Processing**:
- Configurable worker pools for large datasets
- Automatic batch size detection
- Thread-safe file generation

**JSON Optimization**:
- Minification and compression options
- Geometry precision limiting
- Array length restrictions
- Null value exclusion

## Database Schema Compatibility

### Table Structure Support

**Multi-table Integration**:
```sql
-- Core transformed data tables
taxon(taxon_id, general_info JSON, distribution_map JSON, ...)
plot(plot_id, general_info JSON, ...)
shape(shape_id, general_info JSON, ...)

-- Reference tables (taxonomy, hierarchy)
taxon_ref(id, full_name, rank_name, lft, rght, parent_id, ...)

-- Occurrence data (links to reference tables)
occurrences(id, taxon_ref_id, plot_ref_id, dbh, height, geo_pt, ...)
```

**Relationship Handling**:
- Complex join patterns: `taxon.taxon_id → taxon_ref.id → occurrences.taxon_ref_id`
- Multiple ID field variations supported
- Graceful handling of missing relationships

## Generated Output Structure

### API File Organization

```
exports/api/
├── taxon/
│   ├── 1.json          # Full taxon data
│   ├── 2.json
│   └── ...
├── plot/
│   ├── 1.json          # Full plot data
│   └── ...
├── all_taxon.json      # Taxon index with summaries
├── all_plot.json       # Plot index
└── metadata.json       # Export metadata
```

### Darwin Core Structure

```
exports/dwc/occurrence_json/
├── taxon/
│   ├── 1_occurrences_dwc.json    # DwC occurrences for taxon 1
│   ├── 2_occurrences_dwc.json    # DwC occurrences for taxon 2
│   └── ...
└── taxon_index.json              # Index of available files
```

## Standards Compliance

### Darwin Core Implementation

**Core Compliance**:
- Full Occurrence Core schema support
- Measurement and Media extensions
- GBIF-compatible format
- Validates required vs optional terms

**Field Mapping**:
- Comprehensive vocabulary coverage
- Biodiversity-specific data types
- Coordinate system standardization (WGS84)
- Date format standardization (ISO 8601)

### Data Quality Features

**Automatic Validation**:
- Coordinate range checking (-90 ≤ lat ≤ 90, -180 ≤ lng ≤ 180)
- Date format validation and conversion
- Scientific name parsing and validation
- Measurement unit standardization

**Error Recovery**:
- Graceful handling of missing data (null values)
- Malformed geometry parsing
- Invalid date handling
- Incomplete taxonomic information

## Configuration Examples

### Basic Data API

```yaml
exports:
  - name: json_api
    exporter: json_api_exporter
    params:
      output_dir: "exports/api"
      detail_output_pattern: "{group}/{id}.json"
      index_output_pattern: "all_{group}.json"
    groups:
      - group_by: taxon
        detail: {pass_through: true}
        index:
          fields:
            - id: taxon_id
            - name: general_info.name.value
            - endpoint:
                generator: endpoint_url
                params: {base_path: "/api"}
```

### Darwin Core Export

```yaml
exports:
  - name: dwc_occurrence_json
    exporter: json_api_exporter
    params:
      output_dir: "exports/dwc/occurrence_json"
      detail_output_pattern: "taxon/{id}_occurrences_dwc.json"
      index_output_pattern: "taxon_index.json"
    groups:
      - group_by: taxon
        transformer_plugin: niamoto_to_dwc_occurrence
        transformer_params:
          occurrence_list_source: "occurrences"
          mapping:
            type: "Occurrence"
            basisOfRecord: "HumanObservation"
            occurrenceID:
              generator: unique_occurrence_id
              params: {prefix: "niaocc_", source_field: "@source.id"}
            scientificName: "@source.taxonref"
            decimalLatitude:
              generator: format_coordinates
              params: {source_field: "@source.geo_pt", type: "latitude"}
            # ... complete mapping
```

### Performance-Optimized Export

```yaml
exports:
  - name: optimized_api
    exporter: json_api_exporter
    params:
      output_dir: "exports/api"
      json_options:
        minify: true
        exclude_null: true
        geometry_precision: 6
        compress: true
      performance:
        parallel: true
        max_workers: 6
        batch_size: 100
```

## Usage Patterns

### Research Applications

**Species Distribution Modeling**:
```python
import requests
import pandas as pd

# Load occurrence data
response = requests.get('/api/taxon/1_occurrences_dwc.json')
occurrences = response.json()
df = pd.DataFrame(occurrences)

# Extract coordinates
coords = df[['decimalLatitude', 'decimalLongitude']].dropna()
```

**Biodiversity Analysis**:
```r
library(jsonlite)

# Load species index
index <- fromJSON("/api/all_taxon.json")
species <- index$taxon[index$taxon$rank == "species",]
```

### Data Integration

**GBIF Publishing**: Direct compatibility with GBIF ingestion pipelines
**Research Networks**: Standard format for biodiversity data sharing
**Web Applications**: RESTful API structure for frontend consumption
**Data Aggregation**: Standardized format for multi-source analysis

## Future Enhancements

### Planned Features

1. **CSV Export Support**: Darwin Core CSV format alongside JSON
2. **Metadata Extensions**: Enhanced dataset metadata and provenance
3. **Spatial Filtering**: Geographic subset exports
4. **Temporal Filtering**: Time-based data selection
5. **Custom Vocabularies**: Institution-specific term extensions

### Performance Improvements

1. **Streaming Exports**: Memory-efficient processing for large datasets
2. **Incremental Updates**: Only re-export changed data
3. **Database Indexes**: Optimized query performance
4. **Caching Layer**: Reduce computation for repeated exports

## Testing and Validation

### Automated Testing

**Unit Tests**: Individual plugin functionality
**Integration Tests**: Full export pipeline validation
**Performance Tests**: Large dataset handling
**Compliance Tests**: Darwin Core schema validation

### Quality Assurance

**Data Validation**: Coordinate, date, and taxonomy checks
**Format Compliance**: JSON schema and Darwin Core standards
**File Integrity**: Completeness and consistency verification
**Error Handling**: Graceful failure and recovery testing

## Documentation

### New Documentation Files

1. **[API Export Guide](guides/api-export-guide.md)**: Comprehensive JSON API documentation
2. **[Darwin Core Export Guide](guides/darwin-core-export.md)**: Biodiversity standards implementation
3. **Updated [Export Guide](guides/export-guide.md)**: Includes JSON API overview
4. **Updated [Plugin Reference](guides/plugin-reference.md)**: New plugin documentation

### Configuration Reference

Complete YAML schema documentation with:
- Parameter descriptions and validation rules
- Configuration examples for common use cases
- Troubleshooting guides for common issues
- Best practices for performance and data quality

## Migration Guide

### From HTML-Only to API Exports

**Adding JSON API to Existing Configuration**:
```yaml
exports:
  # Existing HTML export
  - name: web_pages
    exporter: html_page_exporter
    # ... existing configuration

  # New JSON API export
  - name: json_api
    exporter: json_api_exporter
    params:
      output_dir: "exports/api"
    groups:
      - group_by: taxon
        detail: {pass_through: true}
        index:
          fields:
            - id: taxon_id  # Use actual database field
            - name: general_info.name.value
```

### Field Mapping Updates

**Critical Change**: ID field mapping now uses actual database column names:
```yaml
# Before (incorrect)
- id: id

# After (correct)
- id: taxon_id     # For taxon group
- id: plot_id      # For plot group
- id: shape_id     # For shape group
```

## Conclusion

The JSON API exporter and Darwin Core transformer provide Niamoto with comprehensive machine-readable data export capabilities. These features enable seamless integration with biodiversity research networks, data aggregation platforms, and analysis tools while maintaining high standards for data quality and format compliance.

The implementation prioritizes:
- **Standards compliance** for interoperability
- **Performance optimization** for large datasets
- **Error resilience** for production reliability
- **Configuration flexibility** for diverse use cases
- **Documentation completeness** for ease of adoption
