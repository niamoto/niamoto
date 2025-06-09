# Database Schema Reference

This document describes the Niamoto database schema, including core models and dynamically generated tables.

## Overview

Niamoto uses a **hybrid database approach**:

1. **Core Models** (defined in code): Fixed reference tables for taxonomy, plots, and shapes
2. **User Data Tables** (dynamic): Generated from user CSV imports (occurrences, custom data)
3. **Transform Results** (dynamic): Generated from `transform.yml` configuration

## Database Technology

- **Engine**: SQLite with spatial extensions (SpatiaLite)
- **ORM**: SQLAlchemy with declarative base
- **Spatial Support**: GeoAlchemy2 for geometric operations

## Core Models (Fixed Schema)

These tables are always created and have predefined structures:

### taxon_ref

Stores taxonomic hierarchy using nested set model for efficient tree operations.

```sql
CREATE TABLE taxon_ref (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name VARCHAR(255),           -- Complete scientific name
    authors VARCHAR(255),             -- Taxonomic authority
    rank_name VARCHAR(50),            -- Taxonomic rank (family, genus, species, etc.)
    lft INTEGER,                      -- Nested set left boundary
    rght INTEGER,                     -- Nested set right boundary
    level INTEGER,                    -- Hierarchy depth level
    taxon_id INTEGER,                 -- External/original taxon identifier
    parent_id INTEGER,                -- Self-referencing foreign key
    extra_data JSON,                  -- Additional fields as JSON

    FOREIGN KEY (parent_id) REFERENCES taxon_ref(id)
);

-- Indexes for performance
CREATE INDEX ix_taxon_ref_id ON taxon_ref(id);
CREATE INDEX ix_taxon_ref_rank_name ON taxon_ref(rank_name);
CREATE INDEX ix_taxon_ref_full_name ON taxon_ref(full_name);
```

**Key Features:**
- **Nested Set Model**: Enables efficient subtree queries
- **Self-referencing**: Parent-child relationships
- **Flexible Extra Data**: JSON field for additional attributes
- **External ID Mapping**: Links to original data sources

**Example Data:**
```sql
INSERT INTO taxon_ref VALUES
(1, 'Araucariaceae', NULL, 'family', 1, 10, 1, NULL, NULL, '{}'),
(2, 'Araucaria', NULL, 'genus', 2, 9, 2, NULL, 1, '{}'),
(3, 'Araucaria columnaris', '(G.Forst.) Hook.', 'species', 3, 4, 3, 123, 2, '{"endemic": true}');
```

### plot_ref

Stores plot/locality hierarchy with spatial information.

```sql
CREATE TABLE plot_ref (
    id INTEGER PRIMARY KEY,           -- Manual ID assignment allowed
    id_locality INTEGER NOT NULL,    -- Locality identifier
    locality VARCHAR NOT NULL,       -- Locality name
    geometry VARCHAR,                -- Spatial geometry as WKT
    lft INTEGER,                     -- Nested set left boundary
    rght INTEGER,                    -- Nested set right boundary
    level INTEGER,                   -- Hierarchy depth
    plot_type VARCHAR(50),           -- Type: 'plot', 'locality', 'country'
    parent_id INTEGER,               -- Self-referencing foreign key
    extra_data JSON,                 -- Additional plot attributes

    FOREIGN KEY (parent_id) REFERENCES plot_ref(id)
);

-- Indexes
CREATE INDEX ix_plot_ref_id ON plot_ref(id);
CREATE INDEX ix_plot_ref_locality ON plot_ref(locality);
CREATE INDEX ix_plot_ref_plot_type ON plot_ref(plot_type);
CREATE INDEX ix_plot_ref_parent_id ON plot_ref(parent_id);
```

**Key Features:**
- **Hierarchical Plots**: Support for plot → locality → country hierarchy
- **Spatial Data**: Geometry stored as WKT (Well-Known Text)
- **Flexible Types**: Different plot types for various scales
- **Manual IDs**: Allows preservation of original plot identifiers

**Example Data:**
```sql
INSERT INTO plot_ref VALUES
(1, 1, 'New Caledonia', 'POLYGON(...)', 1, 4, 1, 'country', NULL, '{}'),
(101, 1, 'Mont Panié', 'POLYGON(...)', 2, 3, 2, 'locality', 1, '{"elevation": 1628}'),
(1001, 1, 'Plot MP-01', 'POINT(164.7672 -20.5819)', NULL, NULL, 3, 'plot', 101, '{"area_m2": 2500}');
```

### shape_ref

Stores geographic reference shapes (administrative boundaries, environmental zones).

```sql
CREATE TABLE shape_ref (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label VARCHAR(50) NOT NULL,       -- Shape name/identifier
    type VARCHAR(50),                 -- Shape category
    type_label VARCHAR(50),           -- Human-readable type
    location VARCHAR NOT NULL,        -- Geometry as WKT

    UNIQUE(label, type)
);

-- Indexes
CREATE INDEX ix_shape_ref_id ON shape_ref(id);
CREATE INDEX ix_shape_ref_label ON shape_ref(label);
CREATE INDEX ix_shape_ref_type ON shape_ref(type);
CREATE INDEX ix_shape_ref_type_label ON shape_ref(type_label);
CREATE UNIQUE INDEX ix_shape_ref_label_type ON shape_ref(label, type);
```

**Key Features:**
- **Geographic Boundaries**: Administrative and environmental zones
- **Type Classification**: Categorized shapes (provinces, forests, etc.)
- **Unique Constraints**: Prevents duplicate label-type combinations
- **Spatial Queries**: Enables geographic intersections and overlays

**Example Data:**
```sql
INSERT INTO shape_ref VALUES
(1, 'Province Nord', 'province', 'Administrative Province', 'MULTIPOLYGON(...)'),
(2, 'Province Sud', 'province', 'Administrative Province', 'MULTIPOLYGON(...)'),
(3, 'Humid Forest', 'forest_type', 'Forest Classification', 'MULTIPOLYGON(...)');
```

## Dynamic Tables (User Data)

These tables are created from user CSV imports:

### occurrences

Generated from occurrence CSV imports based on `import.yml` mapping.

**Typical Structure:**
```sql
CREATE TABLE occurrences (
    id INTEGER PRIMARY KEY,
    taxon_ref_id INTEGER,             -- Foreign key to taxon_ref
    plot_ref_id INTEGER,              -- Foreign key to plot_ref (optional)
    geo_pt GEOMETRY(POINT),           -- Spatial point location

    -- User-defined properties (examples)
    dbh REAL,                         -- Diameter at breast height
    height REAL,                      -- Tree height
    date_observed DATE,               -- Observation date
    observer VARCHAR(100),            -- Observer name
    status VARCHAR(50),               -- Health status

    FOREIGN KEY (taxon_ref_id) REFERENCES taxon_ref(id),
    FOREIGN KEY (plot_ref_id) REFERENCES plot_ref(id)
);

-- Spatial index
CREATE INDEX idx_occurrences_geo_pt ON occurrences USING GIST (geo_pt);
```

**Notes:**
- Structure varies based on user's CSV columns
- Property columns created automatically from `import.yml` mapping
- Spatial indexing for efficient geographic queries
- Foreign key relationships maintain referential integrity

### plots

Generated from plot CSV imports (separate from plot_ref hierarchy).

**Typical Structure:**
```sql
CREATE TABLE plots (
    id INTEGER PRIMARY KEY,
    plot_id VARCHAR(50),              -- Original plot identifier
    plot_name VARCHAR(100),           -- Plot name
    geo_pt GEOMETRY(POINT),           -- Plot center point

    -- User-defined properties (examples)
    elevation REAL,                   -- Elevation in meters
    slope_percent REAL,               -- Slope percentage
    aspect_degrees REAL,              -- Aspect in degrees
    area_m2 REAL,                     -- Plot area in square meters
    forest_type VARCHAR(50),          -- Forest classification
    establishment_date DATE           -- Plot establishment date
);
```

## Transform Result Tables

Generated dynamically from `transform.yml` configuration:

### {group}_stats

Created for each group defined in transform.yml (e.g., `taxon_stats`, `plot_stats`).

**Example for taxon_stats:**
```sql
CREATE TABLE taxon_stats (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER,                -- Foreign key to taxon_ref.id

    -- Widget data columns (from transform.yml)
    general_info JSON,                -- Field aggregator results
    distribution_map JSON,            -- Geospatial data
    top_species JSON,                 -- Ranking results
    morphology_stats JSON,            -- Statistical calculations

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Notes:**
- One table per group_by configuration
- JSON columns store widget data for export
- Column names match `widgets_data` keys in transform.yml
- Automatically updated when transformations run

## Spatial Features

Niamoto uses SpatiaLite extensions for spatial operations:

### Spatial Reference Systems

```sql
-- Default CRS: WGS84 (EPSG:4326)
SELECT InitSpatialMetaData();
INSERT INTO spatial_ref_sys (srid, proj4text) VALUES
(4326, '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs');
```

### Spatial Indexes

```sql
-- Create spatial indexes for performance
SELECT CreateSpatialIndex('occurrences', 'geo_pt');
SELECT CreateSpatialIndex('plots', 'geo_pt');
```

### Common Spatial Queries

```sql
-- Find occurrences within 1km of a point
SELECT o.* FROM occurrences o
WHERE ST_DWithin(o.geo_pt, ST_MakePoint(166.4580, -22.2764), 1000);

-- Find occurrences within a shape
SELECT o.* FROM occurrences o, shape_ref s
WHERE s.label = 'Province Nord'
AND ST_Contains(ST_GeomFromText(s.location), o.geo_pt);

-- Calculate distance between occurrences and plots
SELECT o.id, p.plot_name, ST_Distance(o.geo_pt, p.geo_pt) as distance_m
FROM occurrences o, plots p
WHERE ST_DWithin(o.geo_pt, p.geo_pt, 5000);
```

## Database Indexes

### Performance Indexes

```sql
-- Core model indexes (automatically created)
CREATE INDEX ix_taxon_ref_full_name ON taxon_ref(full_name);
CREATE INDEX ix_taxon_ref_rank_name ON taxon_ref(rank_name);
CREATE INDEX ix_plot_ref_locality ON plot_ref(locality);
CREATE INDEX ix_shape_ref_type ON shape_ref(type);

-- User data indexes (created during import)
CREATE INDEX ix_occurrences_taxon_ref_id ON occurrences(taxon_ref_id);
CREATE INDEX ix_occurrences_date_observed ON occurrences(date_observed);
CREATE INDEX ix_plots_plot_id ON plots(plot_id);

-- Transform result indexes
CREATE INDEX ix_taxon_stats_entity_id ON taxon_stats(entity_id);
CREATE INDEX ix_taxon_stats_updated_at ON taxon_stats(updated_at);
```

### Spatial Indexes

```sql
-- Spatial indexes for geometric operations
SELECT CreateSpatialIndex('occurrences', 'geo_pt');
SELECT CreateSpatialIndex('plots', 'geo_pt');
SELECT CreateSpatialIndex('shape_ref', 'location');
```

## JSON Schema Examples

### extra_data in taxon_ref

```json
{
  "endemic": true,
  "iucn_status": "LC",
  "family_id": 123,
  "vernacular_names": ["Pin colonnaire", "Cook Pine"],
  "images": ["species_123_01.jpg", "species_123_02.jpg"],
  "traits": {
    "max_height": 30,
    "leaf_type": "needle",
    "growth_rate": "slow"
  }
}
```

### Widget data in transform results

```json
{
  "general_info": {
    "name": {"value": "Araucaria columnaris", "type": "string"},
    "rank": {"value": "species", "type": "string"},
    "count": {"value": 1247, "type": "integer"},
    "endemic": {"value": true, "type": "boolean"}
  },
  "distribution_map": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [166.4580, -22.2764]},
        "properties": {"count": 5, "plot_id": "P001"}
      }
    ]
  }
}
```

## Database Utilities

### Backup and Restore

```bash
# Backup database
sqlite3 db/niamoto.db ".backup backup.db"

# Restore database
sqlite3 db/niamoto.db ".restore backup.db"

# Export as SQL
sqlite3 db/niamoto.db ".dump" > backup.sql
```

### Database Inspection

```sql
-- List all tables
.tables

-- Show table schema
.schema taxon_ref

-- Table statistics
SELECT name, COUNT(*) as row_count
FROM (
    SELECT 'taxon_ref' as name UNION
    SELECT 'plot_ref' UNION
    SELECT 'shape_ref' UNION
    SELECT 'occurrences' UNION
    SELECT 'plots'
) t
JOIN sqlite_master m ON m.name = t.name
WHERE m.type = 'table';

-- Check spatial metadata
SELECT * FROM spatial_ref_sys WHERE srid = 4326;
```

### Performance Monitoring

```sql
-- Query execution plan
EXPLAIN QUERY PLAN
SELECT t.full_name, COUNT(o.id)
FROM taxon_ref t
LEFT JOIN occurrences o ON t.id = o.taxon_ref_id
GROUP BY t.id;

-- Database size
SELECT
    name,
    ROUND(SUM(length(sql))/1024.0/1024.0, 2) as size_mb
FROM sqlite_master
WHERE type = 'table'
GROUP BY name;
```

## Best Practices

### Data Integrity

1. **Foreign Key Constraints**: Always enabled for referential integrity
2. **Spatial Validation**: Coordinates validated during import
3. **Transaction Safety**: All operations wrapped in transactions
4. **Backup Strategy**: Regular automated backups before major operations

### Performance Optimization

1. **Appropriate Indexes**: Created based on query patterns
2. **Spatial Indexes**: Essential for geographic operations
3. **Query Optimization**: Use EXPLAIN QUERY PLAN for complex queries
4. **Batch Operations**: Large imports processed in chunks

### Schema Evolution

1. **Migration Scripts**: Handle schema changes between versions
2. **Backward Compatibility**: Maintain support for existing data
3. **Validation**: Check data integrity after schema changes
4. **Documentation**: Update schema docs with changes

## Related Documentation

- [Data Import Guide](../guides/data-import.md) - How user data becomes database tables
- [Transform Chain Guide](../guides/transform_chain_guide.md) - How transform results are generated
- [CLI Commands Reference](cli-commands.md) - Database-related commands (`niamoto stats`)
- [Common Issues](../troubleshooting/common-issues.md) - Database troubleshooting
