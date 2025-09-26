# Data Preparation Guide

This guide helps you prepare your ecological data for import into Niamoto, ensuring data quality and optimal performance.

## Overview

Proper data preparation is crucial for successful Niamoto projects. This guide covers:

1. Data format requirements
2. Quality checks and validation
3. Coordinate system handling
4. File organization best practices
5. Common data issues and solutions

## Data Types and Formats

### Taxonomy Data

**Purpose**: Hierarchical classification of species
**Format**: CSV file with taxonomic hierarchy

**Required columns:**
- `id_taxon` - Unique identifier for each taxon
- `rank_name` - Taxonomic rank (family, genus, species, subspecies)
- `full_name` - Complete scientific name

**Optional columns:**
- `family`, `genus`, `species`, `subspecies` - Individual hierarchy levels
- `authors` - Taxonomic authority
- `common_name` - Vernacular names
- `synonyms` - Alternative scientific names

**Example structure:**
```csv
id_taxon,family,genus,species,rank_name,full_name,authors
1,Araucariaceae,,,family,Araucariaceae,
2,Araucariaceae,Araucaria,,genus,Araucaria,
3,Araucariaceae,Araucaria,columnaris,species,Araucaria columnaris,"(G.Forst.) Hook."
4,Araucariaceae,Araucaria,montana,species,Araucaria montana,"Brongn. & Gris"
```

**Best practices:**
- Use consistent naming conventions
- Include taxonomic authorities when available
- Maintain hierarchical relationships
- Avoid special characters in IDs

### Occurrence Data

**Purpose**: Individual observations of species
**Format**: CSV file with observation records

**Required columns:**
- `id` - Unique occurrence identifier
- `id_taxon` - Link to taxonomy (foreign key)
- `latitude`, `longitude` - Geographic coordinates (WGS84)

**Recommended columns:**
- `plot_id` - Link to study plots
- `date_observed` - Observation date (YYYY-MM-DD)
- `observer` - Collector/observer name
- `dbh` - Diameter at breast height (cm)
- `height` - Tree height (m)
- `status` - Health status (alive, dead, damaged)

**Example structure:**
```csv
id,id_taxon,latitude,longitude,plot_id,date_observed,observer,dbh,height,status
1,3,-22.2764,166.4580,P001,2024-03-15,J.Smith,45.5,12.3,alive
2,3,-22.2765,166.4582,P001,2024-03-15,J.Smith,52.1,14.1,alive
3,4,-20.5819,164.7672,P002,2024-03-16,M.Johnson,38.2,18.5,alive
```

**Data validation tips:**
- Coordinates should be in decimal degrees
- DBH values typically range from 1-500 cm
- Height values typically range from 0.5-80 m
- Dates should use ISO format (YYYY-MM-DD)

### Plot Data

**Purpose**: Study areas or sampling locations
**Format**: CSV file with plot information

**Required columns:**
- `plot_id` - Unique plot identifier
- `plot_name` - Descriptive name
- `latitude`, `longitude` - Plot center coordinates

**Recommended columns:**
- `elevation` - Elevation above sea level (m)
- `slope_percent` - Slope percentage
- `aspect_degrees` - Slope aspect (0-360°)
- `area_m2` - Plot area in square meters
- `forest_type` - Vegetation classification
- `establishment_date` - When plot was established

**Example structure:**
```csv
plot_id,plot_name,latitude,longitude,elevation,slope_percent,aspect_degrees,area_m2,forest_type
P001,Mont Panié Plot 1,-20.5819,164.7672,1250,15.5,180,2500,cloud_forest
P002,Rivière Bleue Plot 2,-22.0943,166.6421,450,8.2,90,2500,humid_forest
```

### Shape Data

**Purpose**: Geographic boundaries and administrative areas
**Formats**: GeoPackage (.gpkg), Shapefile (.shp), or GeoJSON

**Required attributes:**
- Unique ID field
- Name field
- Valid geometry (polygon or point)

**Common shape types:**
- **Administrative boundaries**: Provinces, communes, districts
- **Environmental zones**: Forest types, climate zones, soil types
- **Conservation areas**: National parks, reserves, protected areas
- **Infrastructure**: Roads, settlements, mining areas

**File organization:**
```
imports/shapes/
├── administrative/
│   ├── provinces.gpkg
│   └── communes.gpkg
├── environmental/
│   ├── forest_types.gpkg
│   ├── climate_zones.gpkg
│   └── elevation_zones.gpkg
└── conservation/
    ├── protected_areas.gpkg
    └── world_heritage_sites.gpkg
```

## Data Quality Checks

### Pre-import Validation

#### 1. File Structure Validation

```bash
# Check CSV headers
head -1 imports/occurrences.csv

# Count records
wc -l imports/*.csv

# Check for empty files
find imports/ -name "*.csv" -empty
```

#### 2. Coordinate Validation

```bash
# Check coordinate ranges (example for New Caledonia)
awk -F',' 'NR>1 && ($3<-25 || $3>-19 || $4<163 || $4>168) {
    print "Row " NR ": Invalid coordinates: " $3 "," $4
}' imports/occurrences.csv

# Check for missing coordinates
awk -F',' 'NR>1 && ($3=="" || $4=="") {
    print "Row " NR ": Missing coordinates"
}' imports/occurrences.csv
```

#### 3. Data Type Validation

```bash
# Check for non-numeric values in numeric fields
awk -F',' 'NR>1 && $5 !~ /^[0-9.]+$/ && $5 != "" {
    print "Row " NR ": Invalid DBH value: " $5
}' imports/occurrences.csv

# Check date formats
awk -F',' 'NR>1 && $6 !~ /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/ && $6 != "" {
    print "Row " NR ": Invalid date format: " $6
}' imports/occurrences.csv
```

#### 4. Referential Integrity

```bash
# Check taxonomy references
awk -F',' 'FNR==NR{taxon_ids[$1]=1; next}
           FNR>1 && !($2 in taxon_ids) {
               print "Row " FNR ": Invalid taxon ID: " $2
           }' imports/taxonomy.csv imports/occurrences.csv

# Check plot references
awk -F',' 'FNR==NR{plot_ids[$1]=1; next}
           FNR>1 && $5!="" && !($5 in plot_ids) {
               print "Row " FNR ": Invalid plot ID: " $5
           }' imports/plots.csv imports/occurrences.csv
```

### Python Data Validation Script

Create a comprehensive validation script:

```python
# scripts/validate_data.py
import pandas as pd
import numpy as np
from pathlib import Path
import sys

def validate_coordinates(df, lat_col, lon_col, bounds=None):
    """Validate geographic coordinates."""
    errors = []

    # Check for missing coordinates
    missing_lat = df[lat_col].isna().sum()
    missing_lon = df[lon_col].isna().sum()
    if missing_lat > 0 or missing_lon > 0:
        errors.append(f"Missing coordinates: {missing_lat} lat, {missing_lon} lon")

    # Check coordinate ranges
    if bounds:
        min_lat, max_lat, min_lon, max_lon = bounds
        invalid_coords = df[
            (df[lat_col] < min_lat) | (df[lat_col] > max_lat) |
            (df[lon_col] < min_lon) | (df[lon_col] > max_lon)
        ]
        if len(invalid_coords) > 0:
            errors.append(f"Invalid coordinates: {len(invalid_coords)} records")
            for idx, row in invalid_coords.iterrows():
                errors.append(f"  Row {idx+2}: {row[lat_col]}, {row[lon_col]}")

    return errors

def validate_numeric_ranges(df, field, min_val=None, max_val=None):
    """Validate numeric field ranges."""
    errors = []

    # Check for non-numeric values
    numeric_vals = pd.to_numeric(df[field], errors='coerce')
    non_numeric = df[numeric_vals.isna() & df[field].notna()]
    if len(non_numeric) > 0:
        errors.append(f"Non-numeric values in {field}: {len(non_numeric)} records")

    # Check ranges
    if min_val is not None:
        below_min = df[numeric_vals < min_val]
        if len(below_min) > 0:
            errors.append(f"{field} below minimum ({min_val}): {len(below_min)} records")

    if max_val is not None:
        above_max = df[numeric_vals > max_val]
        if len(above_max) > 0:
            errors.append(f"{field} above maximum ({max_val}): {len(above_max)} records")

    return errors

def validate_taxonomy(taxonomy_file):
    """Validate taxonomy data."""
    print("Validating taxonomy data...")
    df = pd.read_csv(taxonomy_file)
    errors = []

    # Check required columns
    required_cols = ['id_taxon', 'rank_name', 'full_name']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return errors

    # Check for duplicate IDs
    duplicates = df[df['id_taxon'].duplicated()]
    if len(duplicates) > 0:
        errors.append(f"Duplicate taxon IDs: {len(duplicates)} records")

    # Check for missing names
    missing_names = df[df['full_name'].isna()]
    if len(missing_names) > 0:
        errors.append(f"Missing full_name: {len(missing_names)} records")

    return errors

def validate_occurrences(occurrence_file, taxonomy_file=None, plots_file=None):
    """Validate occurrence data."""
    print("Validating occurrence data...")
    df = pd.read_csv(occurrence_file)
    errors = []

    # Check required columns
    required_cols = ['id', 'id_taxon', 'latitude', 'longitude']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return errors

    # Validate coordinates (New Caledonia bounds)
    coord_errors = validate_coordinates(
        df, 'latitude', 'longitude',
        bounds=(-25, -19, 163, 168)
    )
    errors.extend(coord_errors)

    # Validate measurements
    if 'dbh' in df.columns:
        dbh_errors = validate_numeric_ranges(df, 'dbh', min_val=0.1, max_val=500)
        errors.extend(dbh_errors)

    if 'height' in df.columns:
        height_errors = validate_numeric_ranges(df, 'height', min_val=0.1, max_val=80)
        errors.extend(height_errors)

    # Check taxonomy references
    if taxonomy_file and Path(taxonomy_file).exists():
        taxonomy_df = pd.read_csv(taxonomy_file)
        valid_taxon_ids = set(taxonomy_df['id_taxon'])
        invalid_refs = df[~df['id_taxon'].isin(valid_taxon_ids)]
        if len(invalid_refs) > 0:
            errors.append(f"Invalid taxon references: {len(invalid_refs)} records")

    return errors

def main():
    """Run all validations."""
    data_dir = Path("imports")

    # Validate taxonomy
    taxonomy_file = data_dir / "taxonomy.csv"
    if taxonomy_file.exists():
        taxonomy_errors = validate_taxonomy(taxonomy_file)
        if taxonomy_errors:
            print("Taxonomy errors:")
            for error in taxonomy_errors:
                print(f"  - {error}")

    # Validate occurrences
    occurrences_file = data_dir / "occurrences.csv"
    if occurrences_file.exists():
        occurrence_errors = validate_occurrences(
            occurrences_file,
            taxonomy_file if taxonomy_file.exists() else None
        )
        if occurrence_errors:
            print("Occurrence errors:")
            for error in occurrence_errors:
                print(f"  - {error}")

    print("Validation complete!")

if __name__ == "__main__":
    main()
```

Run the validation:

```bash
python scripts/validate_data.py
```

## Coordinate System Management

### Understanding Coordinate Systems

**WGS84 (EPSG:4326)** - Recommended for Niamoto:
- Global standard for GPS coordinates
- Latitude/longitude in decimal degrees
- Example: -22.2764, 166.4580

**UTM (Universal Transverse Mercator)**:
- Grid-based system in meters
- Higher precision for regional data
- New Caledonia: UTM Zone 58S (EPSG:3163)

### Converting Coordinate Systems

#### Using GDAL/OGR tools:

```bash
# Convert shapefile from UTM to WGS84
ogr2ogr -t_srs EPSG:4326 -s_srs EPSG:3163 \
    output_wgs84.gpkg input_utm.shp

# Check coordinate system of existing file
ogrinfo -al -so input.gpkg | grep -E "(Geometry|SRS)"
```

#### Using Python (GeoPandas):

```python
import geopandas as gpd

# Read file with original CRS
gdf = gpd.read_file("imports/shapes/plots_utm.gpkg")

# Set CRS if not defined
gdf = gdf.set_crs("EPSG:3163")

# Convert to WGS84
gdf_wgs84 = gdf.to_crs("EPSG:4326")

# Save converted file
gdf_wgs84.to_file("imports/shapes/plots_wgs84.gpkg", driver="GPKG")
```

#### CSV Coordinate Conversion:

```python
import pandas as pd
from pyproj import Transformer

# Read CSV with UTM coordinates
df = pd.read_csv("imports/occurrences_utm.csv")

# Create transformer (UTM Zone 58S to WGS84)
transformer = Transformer.from_crs("EPSG:3163", "EPSG:4326", always_xy=True)

# Transform coordinates
lon, lat = transformer.transform(df['x_utm'].values, df['y_utm'].values)

# Add new columns
df['longitude'] = lon
df['latitude'] = lat

# Save updated file
df.to_csv("imports/occurrences_wgs84.csv", index=False)
```

## Data Cleaning and Standardization

### Taxonomic Name Standardization

```python
import pandas as pd
import re

def clean_scientific_name(name):
    """Standardize scientific names."""
    if pd.isna(name):
        return name

    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name.strip())

    # Standardize author formatting
    name = re.sub(r'\s*\([^)]+\)\s*', ' ', name)  # Remove parenthetical authors

    # Capitalize first letter of each word
    parts = name.split()
    if len(parts) >= 2:
        parts[0] = parts[0].capitalize()  # Genus
        parts[1] = parts[1].lower()      # Species

    return ' '.join(parts)

# Apply to taxonomy data
df = pd.read_csv("imports/taxonomy.csv")
df['full_name_clean'] = df['full_name'].apply(clean_scientific_name)
```

### Measurement Unit Standardization

```python
def standardize_measurements(df):
    """Convert measurements to standard units."""

    # Convert DBH to centimeters if needed
    if 'dbh_mm' in df.columns:
        df['dbh'] = df['dbh_mm'] / 10  # mm to cm
    elif 'dbh_m' in df.columns:
        df['dbh'] = df['dbh_m'] * 100  # m to cm

    # Convert height to meters if needed
    if 'height_cm' in df.columns:
        df['height'] = df['height_cm'] / 100  # cm to m
    elif 'height_ft' in df.columns:
        df['height'] = df['height_ft'] * 0.3048  # feet to m

    return df
```

### Date Standardization

```python
import pandas as pd
from datetime import datetime

def standardize_dates(df, date_column):
    """Convert various date formats to ISO format."""

    # Try multiple date formats
    date_formats = [
        '%Y-%m-%d',      # 2024-03-15
        '%d/%m/%Y',      # 15/03/2024
        '%m/%d/%Y',      # 03/15/2024
        '%d-%m-%Y',      # 15-03-2024
        '%Y%m%d',        # 20240315
    ]

    def parse_date(date_str):
        if pd.isna(date_str):
            return None

        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_str), fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue

        print(f"Warning: Could not parse date: {date_str}")
        return None

    df[date_column] = df[date_column].apply(parse_date)
    return df
```

## File Organization Best Practices

### Recommended Directory Structure

```
project/
├── imports/
│   ├── raw/                    # Original, unmodified data
│   │   ├── field_data_2024.xlsx
│   │   └── survey_plots.shp
│   ├── processed/              # Cleaned and standardized data
│   │   ├── taxonomy.csv
│   │   ├── occurrences.csv
│   │   └── plots.csv
│   ├── shapes/                 # Spatial data
│   │   ├── administrative/
│   │   ├── environmental/
│   │   └── conservation/
│   └── assets/                 # Images, documents
│       ├── images/
│       └── documents/
├── scripts/                    # Data processing scripts
│   ├── validate_data.py
│   ├── clean_taxonomy.py
│   └── convert_coordinates.py
├── config/                     # Niamoto configuration
└── docs/                       # Data documentation
    ├── data_dictionary.md
    ├── collection_methods.md
    └── coordinate_systems.md
```

### File Naming Conventions

**Use descriptive, standardized names:**
- `occurrences_2024_validated.csv`
- `taxonomy_standardized.csv`
- `plots_forest_inventory.csv`
- `provinces_administrative_boundaries.gpkg`

**Include version control:**
- `occurrences_v1.0.csv` (original)
- `occurrences_v1.1.csv` (cleaned coordinates)
- `occurrences_v1.2.csv` (validated measurements)

### Data Documentation

Create a data dictionary (`docs/data_dictionary.md`):

```markdown
# Data Dictionary

## Taxonomy (taxonomy.csv)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id_taxon | integer | Unique taxon identifier | 123 |
| full_name | string | Complete scientific name | Araucaria columnaris |
| rank_name | string | Taxonomic rank | species |
| family | string | Family name | Araucariaceae |
| authors | string | Taxonomic authority | (G.Forst.) Hook. |

## Occurrences (occurrences.csv)

| Field | Type | Description | Unit | Range |
|-------|------|-------------|------|-------|
| id | integer | Unique occurrence ID | - | 1+ |
| latitude | decimal | Latitude coordinate | degrees | -25 to -19 |
| longitude | decimal | Longitude coordinate | degrees | 163 to 168 |
| dbh | decimal | Diameter at breast height | cm | 1-500 |
| height | decimal | Tree height | m | 0.5-80 |
```

## Common Data Issues and Solutions

### Issue 1: Inconsistent Species Names

**Problem**: Same species with different names
```csv
Araucaria columnaris
Araucaria columnaris (G.Forst.) Hook.
A. columnaris
```

**Solution**: Create name standardization rules
```python
def standardize_species_names(df):
    # Create mapping dictionary
    name_mapping = {
        'A. columnaris': 'Araucaria columnaris',
        'Araucaria columnaris (G.Forst.) Hook.': 'Araucaria columnaris',
    }

    df['full_name'] = df['full_name'].replace(name_mapping)
    return df
```

### Issue 2: Mixed Coordinate Systems

**Problem**: Some coordinates in degrees, others in meters

**Solution**: Detect and convert coordinate systems
```python
def detect_coordinate_system(lat, lon):
    """Detect if coordinates are in degrees or meters."""
    if (-90 <= lat <= 90) and (-180 <= lon <= 180):
        return "degrees"
    elif (100000 <= lat <= 800000) and (300000 <= lon <= 500000):
        return "utm"  # Example for New Caledonia UTM
    else:
        return "unknown"
```

### Issue 3: Duplicate Records

**Problem**: Same observation recorded multiple times

**Solution**: Identify and remove duplicates
```python
def remove_duplicates(df):
    # Define fields that identify unique records
    key_fields = ['id_taxon', 'latitude', 'longitude', 'date_observed']

    # Find duplicates
    duplicates = df[df.duplicated(subset=key_fields, keep=False)]
    print(f"Found {len(duplicates)} duplicate records")

    # Keep first occurrence
    df_clean = df.drop_duplicates(subset=key_fields, keep='first')
    return df_clean
```

### Issue 4: Missing Plot Information

**Problem**: Occurrences reference non-existent plots

**Solution**: Create plot records from occurrence data
```python
def create_plots_from_occurrences(occurrence_df):
    """Generate plot data from occurrence coordinates."""

    # Group occurrences by plot_id
    plot_data = occurrence_df.groupby('plot_id').agg({
        'latitude': 'mean',    # Plot center
        'longitude': 'mean',
        'date_observed': 'min'  # First observation date
    }).reset_index()

    # Add plot names
    plot_data['plot_name'] = plot_data['plot_id'].apply(
        lambda x: f"Plot {x}"
    )

    return plot_data
```

## Quality Assurance Checklist

Before importing data, verify:

### Data Completeness
- [ ] All required files present
- [ ] Required columns exist
- [ ] No completely empty files
- [ ] Reasonable record counts

### Data Consistency
- [ ] Consistent field names across files
- [ ] Standardized units of measurement
- [ ] Uniform date formats
- [ ] Consistent taxonomy names

### Data Accuracy
- [ ] Coordinates within expected bounds
- [ ] Measurements within realistic ranges
- [ ] Valid taxonomy references
- [ ] Proper plot linkages

### Data Documentation
- [ ] Data dictionary created
- [ ] Collection methods documented
- [ ] Known issues documented
- [ ] Processing steps recorded

## Next Steps

After preparing your data:

1. **Test import** with a small subset first
2. **Run validation** scripts before full import
3. **Monitor import logs** for errors
4. **Verify statistics** after import
5. **Document any issues** found

For detailed import procedures, see:
- [Data Import Guide](data-import.md)
- [Quick Start Guide](../getting-started/quickstart.md)
- [Common Issues](../troubleshooting/common-issues.md)
