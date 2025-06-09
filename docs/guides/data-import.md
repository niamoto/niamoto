# Data Import Guide

This comprehensive guide covers importing various data types into Niamoto, from basic CSV files to complex spatial datasets.

## Overview

Niamoto supports importing four main types of ecological data:

1. **Taxonomy** - Species hierarchical classification
2. **Occurrences** - Individual observations of species
3. **Plots** - Delimited study areas or forest plots
4. **Shapes** - Geographic boundaries and administrative areas

## Supported Formats

### File Types
- **CSV** - Comma-separated values with headers
- **GeoPackage** (.gpkg) - Modern spatial data format
- **Shapefile** (.shp + .dbf + .prj + .shx) - Traditional GIS format
- **GeoJSON** - Web-friendly spatial format

### Coordinate Systems
- **WGS84** (EPSG:4326) - Recommended for global data
- **UTM** zones - For regional high-precision data
- **Local projections** - Automatically reprojected to WGS84

## Import Configuration Structure

All imports are configured in `config/import.yml`:

```yaml
# Taxonomy import
taxonomy:
  type: csv
  path: "imports/taxonomy.csv"
  # ... specific options

# Occurrence import
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  # ... mapping configuration

# Plot import
plots:
  type: csv
  path: "imports/plots.csv"
  # ... spatial configuration

# Shape imports (multiple allowed)
shapes:
  - name: "provinces"
    type: geopackage
    path: "imports/shapes/provinces.gpkg"
    # ... shape-specific options
```

## 1. Taxonomy Import

### From Dedicated CSV File

```yaml
taxonomy:
  type: csv
  path: "imports/taxonomy.csv"
  source: "file"  # Default value
  identifier: "id_taxon"
  ranks: "id_family,id_genus,id_species,id_subspecies"
```

**Required CSV Structure:**
```csv
id_taxon,id_family,id_genus,id_species,id_subspecies,full_name,rank_name
1,1,NULL,NULL,NULL,Araucariaceae,family
2,1,1,NULL,NULL,Araucaria,genus
3,1,1,1,NULL,Araucaria columnaris,species
4,1,1,1,1,Araucaria columnaris var. cookii,subspecies
```

### From Occurrence Data

Extract taxonomy directly from occurrence records:

```yaml
taxonomy:
  type: csv
  path: "imports/occurrences.csv"
  source: "occurrence"
  ranks: "family,genus,species,infra"
  occurrence_columns:
    taxon_id: "id_taxonref"
    family: "family"
    genus: "genus"
    species: "species"
    infra: "subspecies"
    authors: "authors"
```

### API Enrichment

Enrich taxonomy with external API data:

```yaml
taxonomy:
  # ... base configuration
  api_enrichment:
    enabled: true
    plugin: "api_taxonomy_enricher"
    api_url: "https://api.endemia.nc/v1/taxons"
    auth_method: "api_key"
    auth_params:
      key: "your-api-key"
      location: "header"
      name: "apiKey"
    query_field: "full_name"
    rate_limit: 2.0
    cache_results: true
    response_mapping:
      endemic: "endemique"
      protected: "protected"
      iucn_status: "iucn_category"
```

## 2. Occurrence Import

Occurrences represent individual observations of species in the field.

### Basic CSV Import

```yaml
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  mapping:
    id_occurrence: "id"
    taxon_ref_id: "id_taxon"
    geo_pt:
      x: "longitude"
      y: "latitude"
    properties:
      - dbh
      - height
      - date_observed
      - observer
      - plot_id
```

**Required CSV Structure:**
```csv
id,id_taxon,longitude,latitude,dbh,height,date_observed,observer,plot_id
1,3,166.4580,-22.2764,45.5,12.3,2024-03-15,J.Smith,P001
2,3,166.4582,-22.2765,52.1,14.1,2024-03-15,J.Smith,P001
```

### Advanced Property Mapping

Map complex properties with transformations:

```yaml
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  mapping:
    id_occurrence: "occurrence_id"
    taxon_ref_id: "taxon_id"
    geo_pt:
      x: "coord_x"
      y: "coord_y"
      crs: "EPSG:3163"  # Source coordinate system
    properties:
      - name: "dbh_cm"
        source: "diameter"
        type: "float"
        unit: "cm"
      - name: "height_m"
        source: "height"
        type: "float"
        unit: "m"
      - name: "observation_date"
        source: "date"
        type: "date"
        format: "%Y-%m-%d"
      - name: "health_status"
        source: "status"
        type: "string"
        mapping:
          "H": "healthy"
          "D": "damaged"
          "DE": "dead"
```

### Validation Rules

Add validation to ensure data quality:

```yaml
occurrences:
  # ... mapping configuration
  validation:
    required_fields:
      - taxon_ref_id
      - geo_pt
    coordinate_bounds:
      min_lat: -25.0
      max_lat: -19.0
      min_lon: 163.0
      max_lon: 168.0
    value_ranges:
      dbh:
        min: 0.1
        max: 300.0
      height:
        min: 0.1
        max: 80.0
```

## 3. Plot Import

Plots represent study areas where occurrences were collected.

### CSV with Point Coordinates

```yaml
plots:
  type: csv
  path: "imports/plots.csv"
  mapping:
    id_plot: "plot_id"
    name: "plot_name"
    geo_pt:
      x: "center_longitude"
      y: "center_latitude"
    properties:
      - elevation
      - slope_percent
      - aspect_degrees
      - area_m2
      - forest_type
      - establishment_date
```

**Example CSV:**
```csv
plot_id,plot_name,center_longitude,center_latitude,elevation,slope_percent,aspect_degrees,area_m2,forest_type
P001,Mont Panié Plot 1,164.7672,-20.5819,1250,15.5,180,2500,cloud_forest
P002,Rivière Bleue Plot 2,166.6421,-22.0943,450,8.2,90,2500,humid_forest
```

### Spatial Polygon Import

Import plots as polygons from spatial files:

```yaml
plots:
  type: geopackage
  path: "imports/plots.gpkg"
  mapping:
    id_plot: "id"
    name: "name"
    geometry: "geom"  # Use polygon geometry
    properties:
      - elevation
      - area_ha
      - vegetation_type
```

## 4. Shape Import

Import administrative boundaries and environmental zones.

### Single Shape Import

```yaml
shapes:
  - name: "provinces"
    type: geopackage
    path: "imports/shapes/provinces.gpkg"
    id_field: "id_province"
    name_field: "province_name"
    properties:
      - area_km2
      - population
      - capital_city
```

### Multiple Shapes

```yaml
shapes:
  - name: "provinces"
    type: geopackage
    path: "imports/shapes/provinces.gpkg"
    id_field: "id"
    name_field: "nom"

  - name: "forest_types"
    type: shapefile
    path: "imports/shapes/forest_classification.shp"
    id_field: "forest_id"
    name_field: "forest_name"
    properties:
      - forest_type
      - canopy_cover
      - dominant_species

  - name: "protected_areas"
    type: geojson
    path: "imports/shapes/protected_areas.geojson"
    id_field: "pa_id"
    name_field: "pa_name"
    properties:
      - protection_level
      - area_hectares
      - creation_date
```

### Shapefile Import Considerations

When importing shapefiles, ensure all required files are present:

```
imports/shapes/
├── boundaries.shp      # Geometry
├── boundaries.dbf      # Attributes
├── boundaries.prj      # Projection
├── boundaries.shx      # Spatial index
└── boundaries.cpg      # Character encoding (optional)
```

## Data Validation and Quality Control

### Pre-import Validation

Check your data before importing:

```bash
# Check CSV structure
head -5 imports/occurrences.csv
csvstat imports/occurrences.csv

# Validate coordinates
awk -F',' 'NR>1 && ($3<-30 || $3>30 || $4<-180 || $4>180) {print NR": Invalid coordinates"}' imports/occurrences.csv

# Check for duplicates
sort imports/occurrences.csv | uniq -d
```

### Post-import Verification

```bash
# Run import and check statistics
niamoto import
niamoto stats

# Check for import errors in logs
tail -f logs/niamoto.log | grep ERROR
```

### Common Data Issues

#### Missing Coordinates
```yaml
occurrences:
  mapping:
    # Handle missing coordinates
    geo_pt:
      x: "longitude"
      y: "latitude"
      default_x: 0.0  # Default longitude
      default_y: 0.0  # Default latitude
      skip_missing: true  # Skip records with missing coordinates
```

#### Character Encoding Issues
```yaml
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  encoding: "utf-8"  # or "latin1", "cp1252"
  delimiter: ","
  quotechar: '"'
```

#### Date Format Variations
```yaml
occurrences:
  mapping:
    properties:
      - name: "observation_date"
        source: "date"
        type: "date"
        formats:  # Try multiple formats
          - "%Y-%m-%d"
          - "%d/%m/%Y"
          - "%m/%d/%Y"
```

## Advanced Import Scenarios

### Incremental Updates

Import only new records:

```yaml
occurrences:
  type: csv
  path: "imports/new_occurrences.csv"
  mode: "append"  # Don't overwrite existing data
  update_strategy: "skip_existing"  # or "update_existing"
  key_fields:
    - id_occurrence
```

### Multi-file Import

Import from multiple source files:

```yaml
occurrences:
  type: multi_csv
  paths:
    - "imports/occurrences_2023.csv"
    - "imports/occurrences_2024.csv"
  mapping:
    # ... common mapping for all files
```

### Custom Data Transformations

Apply transformations during import:

```yaml
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  transformations:
    - field: "dbh"
      operation: "convert_units"
      from: "mm"
      to: "cm"
    - field: "coordinates"
      operation: "reproject"
      from_crs: "EPSG:3163"
      to_crs: "EPSG:4326"
    - field: "species_name"
      operation: "clean_text"
      rules:
        - "strip_whitespace"
        - "title_case"
```

## Troubleshooting Import Issues

### File Not Found
```bash
# Check file paths relative to project root
ls -la imports/
ls -la imports/shapes/
```

### Permission Errors
```bash
# Fix file permissions
chmod 644 imports/*.csv
chmod 644 imports/shapes/*
```

### Memory Issues with Large Files
```yaml
occurrences:
  type: csv
  path: "imports/large_file.csv"
  chunk_size: 10000  # Process in chunks
  memory_limit: "1GB"
```

### Coordinate System Issues
```bash
# Check spatial file CRS
ogrinfo -so imports/shapes/provinces.gpkg provinces

# Reproject if needed
ogr2ogr -t_srs EPSG:4326 output.gpkg input.gpkg
```

## Best Practices

### File Organization
```
imports/
├── occurrences/
│   ├── occurrences_2023.csv
│   └── occurrences_2024.csv
├── plots/
│   └── study_plots.csv
├── shapes/
│   ├── administrative/
│   │   ├── provinces.gpkg
│   │   └── communes.gpkg
│   └── environmental/
│       ├── forest_types.gpkg
│       └── protected_areas.gpkg
└── taxonomy/
    ├── base_taxonomy.csv
    └── synonyms.csv
```

### Performance Optimization
1. **Use appropriate data types** in CSV headers
2. **Pre-sort large files** by key fields
3. **Remove unnecessary columns** before import
4. **Use spatial indexes** for GIS files
5. **Validate data** before importing large datasets

### Data Quality Standards
1. **Consistent naming** across all files
2. **Standardized coordinate systems**
3. **Complete metadata** for all fields
4. **Documented data sources** and collection methods
5. **Regular validation** of imported data

## Next Steps

After successful import:

1. **Verify data**: Run `niamoto stats` to check import results
2. **Configure transformations**: Set up data processing in `transform.yml`
3. **Test exports**: Generate sample pages to verify data display
4. **Document your schema**: Keep track of field meanings and units

For more advanced import scenarios, see:
- [Data Preparation Guide](data-preparation.md)
- [Transform Chain Guide](transform_chain_guide.md)
- [API Taxonomy Enricher](api_taxonomy_enricher.md)
