# Darwin Core Export Guide

This guide covers exporting biodiversity data in Darwin Core format, the global standard for sharing biological occurrence information. Niamoto's Darwin Core export enables seamless integration with GBIF, iDigBio, and other biodiversity data networks.

## Overview

Darwin Core (DwC) is a body of standards developed by the Biodiversity Information Standards organization (TDWG) for sharing information about biological diversity. The standard provides a stable, straightforward, and flexible framework for occurrence records.

### Key Principles

1. **Occurrence-Centric**: Each record represents a single observation or specimen
2. **Flat Structure**: Simple key-value pairs rather than nested hierarchies
3. **Standardized Terms**: Predefined vocabulary for field names and values
4. **Event-Based**: Links occurrences to collection/observation events
5. **Taxon-Linked**: References to taxonomic classification systems

## Darwin Core Export Configuration

### Basic Setup

```yaml
exports:
  - name: dwc_occurrence_json
    enabled: true
    exporter: json_api_exporter    # Reuses JSON API infrastructure

    params:
      output_dir: "exports/dwc/occurrence_json"

      # File naming patterns
      detail_output_pattern: "taxon/{id}_occurrences_dwc.json"
      index_output_pattern: "taxon_index.json"

      # JSON formatting
      json_options:
        indent: 2
        ensure_ascii: false

    groups:
      - group_by: taxon
        # Use Darwin Core transformer
        transformer_plugin: niamoto_to_dwc_occurrence

        # Index file configuration
        index:
          fields:
            - id: taxon_id
            - scientificName: general_info.name.value
            - taxonRank: general_info.rank.value
            - occurrences_count: general_info.occurrences_count.value
            - file_path:
                generator: endpoint_url
                params:
                  base_path: ""
                  pattern: "taxon/{id}_occurrences_dwc.json"

        # Darwin Core transformation parameters
        transformer_params:
          occurrence_list_source: "occurrences"
          mapping:
            # ... (detailed mapping configuration below)
```

### Generated File Structure

This configuration creates:
- `exports/dwc/occurrence_json/taxon/1_occurrences_dwc.json` - DwC occurrences for taxon 1
- `exports/dwc/occurrence_json/taxon/2_occurrences_dwc.json` - DwC occurrences for taxon 2
- `exports/dwc/occurrence_json/taxon_index.json` - Index of available taxon files

**Important**: Only taxa with actual occurrences generate files. Empty taxa are automatically skipped.

## Darwin Core Field Mapping

### Core Record Structure

Darwin Core groups fields into logical categories. Here's the complete mapping configuration:

```yaml
transformer_params:
  occurrence_list_source: "occurrences"
  mapping:
    # ============================================================
    # Record-Level Terms
    # ============================================================
    type: "Occurrence"
    language: "fr"
    license: "CC-BY-4.0"
    rightsHolder: "Niamoto - Nouvelle-Calédonie"
    datasetName: "Niamoto Export - Nouvelle-Calédonie Flore"
    basisOfRecord: "HumanObservation"

    # ============================================================
    # Occurrence Terms
    # ============================================================
    occurrenceID:
      generator: unique_occurrence_id
      params:
        prefix: "niaocc_"
        source_field: "@source.id"

    individualCount: "1"
    occurrenceStatus: "present"

    # ============================================================
    # Event Terms
    # ============================================================
    eventID:
      generator: unique_event_id
      params:
        prefix: "niaevt_"
        source_field: "@source.id"

    eventDate:
      generator: format_event_date
      params:
        source_field: "@source.month_obs"

    year:
      generator: extract_year
      params:
        source_field: "@source.month_obs"

    month:
      generator: extract_month
      params:
        source_field: "@source.month_obs"

    # ============================================================
    # Location Terms
    # ============================================================
    country: "New Caledonia"
    countryCode: "NC"
    stateProvince: "@source.province"

    minimumElevationInMeters: "@source.elevation"
    maximumElevationInMeters: "@source.elevation"

    decimalLatitude:
      generator: format_coordinates
      params:
        source_field: "@source.geo_pt"
        type: "latitude"

    decimalLongitude:
      generator: format_coordinates
      params:
        source_field: "@source.geo_pt"
        type: "longitude"

    geodeticDatum: "WGS84"

    # ============================================================
    # Identification Terms
    # ============================================================
    identificationID:
      generator: unique_identification_id
      params:
        prefix: "niaid_"
        source_field: "@source.id"

    # ============================================================
    # Taxon Terms
    # ============================================================
    taxonID: "@taxon.taxon_id"
    scientificName: "@source.taxonref"
    kingdom: "Plantae"
    family: "@source.family"
    genus: "@source.genus"

    specificEpithet:
      generator: extract_specific_epithet
      params:
        source_field: "@source.taxonref"

    infraspecificEpithet:
      generator: extract_infraspecific_epithet
      params:
        source_field: "@source.taxonref"

    taxonRank: "@taxon.general_info.rank.value"
    scientificNameAuthorship: "@source.taxonref"

    # ============================================================
    # Measurement Extensions
    # ============================================================
    dynamicProperties:
      generator: format_measurements
      params:
        measurements:
          - field: "@source.dbh"
            name: "diameterAtBreastHeight"
            unit: "cm"
          - field: "@source.height"
            name: "height"
            unit: "m"
          - field: "@source.wood_density"
            name: "woodDensity"
            unit: "g/cm³"
          - field: "@source.bark_thickness"
            name: "barkThickness"
            unit: "mm"
          - field: "@source.leaf_area"
            name: "leafArea"
            unit: "cm²"
          - field: "@source.leaf_thickness"
            name: "leafThickness"
            unit: "µm"
          - field: "@source.leaf_sla"
            name: "specificLeafArea"
            unit: "m²/kg"

    # ============================================================
    # Phenology
    # ============================================================
    reproductiveCondition:
      generator: format_phenology
      params:
        flower_field: "@source.flower"
        fruit_field: "@source.fruit"

    # ============================================================
    # Habitat
    # ============================================================
    habitat:
      generator: format_habitat
      params:
        holdridge_field: "@source.holdridge"
        rainfall_field: "@source.rainfall"
        substrate_field: "@source.in_um"
        forest_field: "@source.in_forest"

    # ============================================================
    # Establishment Means
    # ============================================================
    establishmentMeans:
      generator: map_establishment_means
      params:
        endemic_field: "@taxon.general_info.endemic.value"
```

## Reference System Explained

### @source vs @taxon References

The mapping uses a dual reference system:

**@source References**: Point to individual occurrence record data
```yaml
# These come from the 'occurrences' table
decimalLatitude: "@source.geo_pt"      # Individual occurrence location
dbh: "@source.dbh"                     # Tree diameter for this occurrence
month_obs: "@source.month_obs"         # When this occurrence was observed
```

**@taxon References**: Point to taxon-level data
```yaml
# These come from the 'taxon' table (transformed data)
taxonID: "@taxon.taxon_id"             # Taxon identifier
taxonRank: "@taxon.general_info.rank.value"  # Species, genus, etc.
endemic: "@taxon.general_info.endemic.value" # Species endemism status
```

This enables each occurrence record to include both observation-specific data and taxonomic metadata.

## Generator Functions

### Coordinate Processing

```yaml
decimalLatitude:
  generator: format_coordinates
  params:
    source_field: "@source.geo_pt"
    type: "latitude"
```

**Input**: `"POINT (165.7683 -21.6461)"` (PostGIS format)
**Output**: `-21.6461` (decimal degrees)

The generator:
- Parses POINT geometry strings
- Validates coordinate ranges (lat: -90 to 90, lng: -180 to 180)
- Returns null for invalid coordinates

### Date Formatting

```yaml
eventDate:
  generator: format_event_date
  params:
    source_field: "@source.month_obs"
```

**Input**: `3` (March)
**Output**: `"2023-03"` (ISO 8601 year-month format)

**Input**: `null` or missing
**Output**: `null`

### Scientific Name Parsing

```yaml
specificEpithet:
  generator: extract_specific_epithet
  params:
    source_field: "@source.taxonref"
```

**Input**: `"Araucaria columnaris (G.Forst.) Hook."`
**Output**: `"columnaris"`

The generator handles:
- Binomial nomenclature parsing
- Infraspecific epithets (subspecies, varieties)
- Author string removal
- Hybrid notation (×)

### Measurements Formatting

```yaml
dynamicProperties:
  generator: format_measurements
  params:
    measurements:
      - field: "@source.dbh"
        name: "diameterAtBreastHeight"
        unit: "cm"
      - field: "@source.height"
        name: "height"
        unit: "m"
```

**Output**:
```json
{
  "diameterAtBreastHeight": {"value": 45.2, "unit": "cm"},
  "height": {"value": 12.5, "unit": "m"}
}
```

Only includes measurements with non-null values.

### Phenology Formatting

```yaml
reproductiveCondition:
  generator: format_phenology
  params:
    flower_field: "@source.flower"
    fruit_field: "@source.fruit"
```

**Input**: `flower: 1, fruit: 0`
**Output**: `"flowering"`

**Input**: `flower: 1, fruit: 1`
**Output**: `"flowering, fruiting"`

**Input**: `flower: 0, fruit: 0`
**Output**: `null`

### Habitat Description

```yaml
habitat:
  generator: format_habitat
  params:
    holdridge_field: "@source.holdridge"
    rainfall_field: "@source.rainfall"
    substrate_field: "@source.in_um"
    forest_field: "@source.in_forest"
```

**Output**: `"Humid forest on ultramafic substrate, 2500mm annual rainfall"`

Combines multiple environmental variables into a human-readable habitat description.

## Generated Output Format

### Individual Occurrence Record

```json
{
  "type": "Occurrence",
  "language": "fr",
  "license": "CC-BY-4.0",
  "basisOfRecord": "HumanObservation",

  "occurrenceID": "niaocc_12345",
  "individualCount": "1",
  "occurrenceStatus": "present",

  "eventID": "niaevt_12345",
  "eventDate": "2023-03",
  "year": 2023,
  "month": 3,

  "country": "New Caledonia",
  "countryCode": "NC",
  "stateProvince": "Province Sud",
  "decimalLatitude": -21.6461,
  "decimalLongitude": 165.7683,
  "minimumElevationInMeters": 450,
  "maximumElevationInMeters": 450,
  "geodeticDatum": "WGS84",

  "taxonID": "1",
  "scientificName": "Araucaria columnaris (G.Forst.) Hook.",
  "kingdom": "Plantae",
  "family": "Araucariaceae",
  "genus": "Araucaria",
  "specificEpithet": "columnaris",
  "taxonRank": "species",
  "scientificNameAuthorship": "(G.Forst.) Hook.",

  "dynamicProperties": {
    "diameterAtBreastHeight": {"value": 45.2, "unit": "cm"},
    "height": {"value": 12.5, "unit": "m"},
    "woodDensity": {"value": 0.65, "unit": "g/cm³"}
  },

  "reproductiveCondition": "flowering",
  "habitat": "Humid forest on non-ultramafic substrate, 2500mm annual rainfall",
  "establishmentMeans": "native"
}
```

### Taxon Index File

```json
{
  "total": 850,
  "taxon": [
    {
      "id": 1,
      "scientificName": "Araucaria columnaris",
      "taxonRank": "species",
      "occurrences_count": 145,
      "file_path": "taxon/1_occurrences_dwc.json"
    },
    {
      "id": 2,
      "scientificName": "Agathis lanceolata",
      "taxonRank": "species",
      "occurrences_count": 78,
      "file_path": "taxon/2_occurrences_dwc.json"
    }
  ]
}
```

## Data Quality & Validation

### Automatic Data Cleaning

The Darwin Core transformer automatically:

1. **Validates coordinates**: Ensures lat/lng are within valid ranges
2. **Filters empty occurrences**: Skips taxa with no occurrence records
3. **Handles missing data**: Uses null values for missing Darwin Core terms
4. **Standardizes formats**: Converts dates, coordinates, and measurements to standard formats

### Quality Checks

Before export, verify your data quality:

```sql
-- Check for valid coordinates
SELECT COUNT(*) FROM occurrences
WHERE geo_pt IS NULL OR geo_pt = '';

-- Check taxonomic coverage
SELECT COUNT(DISTINCT taxon_ref_id) FROM occurrences;

-- Check temporal coverage
SELECT MIN(month_obs), MAX(month_obs) FROM occurrences
WHERE month_obs IS NOT NULL;
```

### Common Issues

**Missing Coordinates**:
```json
{
  "decimalLatitude": null,
  "decimalLongitude": null
}
```
Solution: Ensure geo_pt field contains valid POINT geometry.

**Invalid Dates**:
```json
{
  "eventDate": null,
  "year": null,
  "month": null
}
```
Solution: Check month_obs field contains valid month numbers (1-12).

**Missing Taxonomic Information**:
```json
{
  "family": null,
  "genus": null
}
```
Solution: Verify taxonref field contains complete scientific names.

## Darwin Core Standards Compliance

### Required vs Optional Terms

**Core Required Terms** (always included):
- `type`, `basisOfRecord`, `occurrenceID`, `occurrenceStatus`
- `eventID`, `country`, `countryCode`
- `scientificName`, `kingdom`

**Recommended Terms** (included when available):
- `decimalLatitude`, `decimalLongitude`, `geodeticDatum`
- `eventDate`, `year`, `month`
- `family`, `genus`, `specificEpithet`, `taxonRank`

**Extension Terms** (domain-specific):
- `dynamicProperties` - Measurements and morphological data
- `reproductiveCondition` - Phenology information
- `habitat` - Environmental context
- `establishmentMeans` - Native/introduced status

### GBIF Compatibility

The export format is fully compatible with GBIF ingestion:

1. **Occurrence Core**: Follows GBIF occurrence schema
2. **Measurement Extensions**: Uses GBIF measurement vocabulary
3. **Identification**: Includes identification metadata
4. **Data Quality**: Validates required fields and formats

### Publishing to GBIF

To publish your Darwin Core data to GBIF:

1. **Register as data publisher**: Create account at gbif.org
2. **Create dataset**: Register your dataset with metadata
3. **Upload data**: Use GBIF IPT or direct API upload
4. **Validate**: GBIF will validate your Darwin Core compliance
5. **Publish**: Data becomes available through GBIF network

## Advanced Configuration

### Custom Field Mapping

Add institution-specific fields:

```yaml
mapping:
  # Standard Darwin Core terms
  scientificName: "@source.taxonref"

  # Custom extensions
  institutionCode: "NC-NIAMOTO"
  collectionCode: "FOREST-PLOTS"

  # Additional measurements
  dynamicProperties:
    generator: format_measurements
    params:
      measurements:
        - field: "@source.custom_trait"
          name: "customMeasurement"
          unit: "unit"
```

### Multiple Export Formats

Export the same data in different Darwin Core formats:

```yaml
exports:
  # JSON format (current)
  - name: dwc_occurrence_json
    exporter: json_api_exporter
    # ... configuration above

  # CSV format (future)
  - name: dwc_occurrence_csv
    exporter: csv_exporter
    transformer_plugin: niamoto_to_dwc_occurrence
    # ... CSV-specific configuration
```

### Filtering Exports

Export specific subsets:

```yaml
transformer_params:
  # Only export certain taxonomic ranks
  filters:
    rank: ["species", "subspecies"]

  # Only export occurrences with coordinates
  required_fields: ["geo_pt"]

  # Date range filtering
  date_range:
    start_year: 2010
    end_year: 2023
```

## Performance Optimization

### Large Dataset Handling

For large occurrence datasets:

```yaml
params:
  # Enable parallel processing
  performance:
    parallel: true
    max_workers: 6
    batch_size: 100

  # Optimize JSON output
  json_options:
    minify: true
    exclude_null: true
    compress: true  # Generate .gz files
```

### Memory Management

Monitor memory usage during export:

```bash
# Run export with memory monitoring
niamoto export --target dwc_occurrence_json --verbose

# Check generated file sizes
ls -lh exports/dwc/occurrence_json/
```

For very large exports, consider chunking by taxonomic groups or geographic regions.

## Integration Examples

### Research Applications

**Ecological Modeling**:
```python
import requests
import pandas as pd

# Load occurrence data
response = requests.get('http://your-site.com/api/taxon/1_occurrences_dwc.json')
occurrences = response.json()

# Convert to pandas DataFrame
df = pd.DataFrame(occurrences)

# Extract coordinates for species distribution modeling
coordinates = df[['decimalLatitude', 'decimalLongitude']].dropna()
```

**Biodiversity Analysis**:
```r
library(jsonlite)
library(dplyr)

# Load all taxon data
index <- fromJSON("http://your-site.com/api/taxon_index.json")

# Get species with most occurrences
top_species <- index$taxon %>%
  filter(taxonRank == "species") %>%
  arrange(desc(occurrences_count)) %>%
  head(10)
```

### Data Aggregation Platforms

The Darwin Core export integrates seamlessly with:

- **GBIF**: Global biodiversity data network
- **iDigBio**: Integrated Digitized Biocollections
- **VertNet**: Vertebrate specimen networks
- **Regional nodes**: National and regional biodiversity portals

## Troubleshooting

### Common Export Issues

**No files generated**:
```
0 files generated for dwc_occurrence_json
```
- Check that taxa have associated occurrences
- Verify database relationships (taxon_id → taxon_ref_id → occurrences)
- Check transformer configuration syntax

**Malformed JSON output**:
```
JSON decode error in generated files
```
- Validate generator function outputs
- Check for circular references in data
- Verify field mapping syntax

**Performance issues**:
```
Export taking too long
```
- Enable parallel processing
- Add database indexes on join columns
- Consider chunking large exports

### Validation Tools

Validate generated Darwin Core data:

```bash
# Check JSON syntax
python -m json.tool taxon/1_occurrences_dwc.json

# Validate Darwin Core compliance (external tool)
dwca-validator validate-json taxon/1_occurrences_dwc.json
```

## Related Documentation

- [API Export Guide](api-export-guide.md) - General JSON API exports
- [Plugin Reference](plugin-reference.md) - Transformer plugin development
- [Configuration Guide](configuration.md) - YAML configuration syntax
- [Data Integration Guide](data-integration.md) - Using exported data

For GBIF-specific publishing guidance, see the [GBIF IPT User Manual](https://ipt.gbif.org/).
