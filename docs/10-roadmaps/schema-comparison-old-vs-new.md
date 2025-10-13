# Schema Comparison: Old vs New System

**Date**: 2025-10-10
**Status**: Analysis Complete
**Purpose**: Comprehensive comparison of database schemas between old SQLite (niamoto-og) and new DuckDB (niamoto-nc) systems to inform restoration decisions.

---

## Executive Summary

### What Changed
The migration from the old SQLite-based system to the new DuckDB-based generic import system resulted in significant simplification of entity tables. While this improved maintainability and genericity, several key features were lost:

1. **Nested Sets Hierarchy** (lft/rght): Removed from taxonomy and shapes
2. **Extra Data Storage** (JSON): Removed from all entity types
3. **Unique Identifiers**: Replaced hash-based IDs with external IDs
4. **Hierarchical Structure**: Shapes lost two-level type/shape hierarchy
5. **Reference Separation**: Plots now mix reference and stats data

### Critical Impact
- ❌ **Nested Set Loader** (`nested_set.py`): Cannot function without lft/rght fields
- ❌ **Hierarchical Nav Widget** (`hierarchical_nav_widget.py`): Degraded performance without nested sets
- ❌ **API Taxonomy Enricher** (`api_taxonomy_enricher.py`): Cannot store enriched data without extra_data
- ❌ **Field Aggregator** (`field_aggregator.py`): Cannot access JSON metadata (e.g., "extra_data.endemic")
- ❌ **Shape Grouping**: Cannot distinguish between shape types and individual shapes
- ❌ **Hierarchical Plots**: Cannot support multi-level plot organization (method → country → plot) like nia_full_ca instance

---

## Detailed Schema Comparison

### 1. Taxonomy Reference

#### OLD: `taxon_ref` (SQLite)

```sql
CREATE TABLE taxon_ref (
    id INTEGER NOT NULL,
    taxon_id INTEGER,                  -- External ID for linking
    full_name VARCHAR(255),
    authors VARCHAR(255),
    rank_name VARCHAR(50),
    lft INTEGER,                       -- Nested set left
    rght INTEGER,                      -- Nested set right
    level INTEGER,                     -- Hierarchy depth
    extra_data JSON,                   -- Flexible metadata
    parent_id INTEGER,                 -- Parent reference
    PRIMARY KEY (id),
    FOREIGN KEY(parent_id) REFERENCES taxon_ref (id)
);
```

**Sample Data**:
```
id  | taxon_id | full_name            | rank_name | level | parent_id | lft | rght | extra_data
----|----------|----------------------|-----------|-------|-----------|-----|------|------------
1   |          | Acanthaceae          | family    | 0     | NULL      | 1   | 8    | {"auto_generated": true, "taxon_type": "family"}
132 |          | Avicennia            | genus     | 1     | 1         | 2   | 7    | {"auto_generated": true, "taxon_type": "genus"}
512 | 2054     | Avicennia marina     | species   | 2     | 132       | 3   | 6    | {"taxon_type": "species", "original_id": 2054}
```

**Statistics**:
- Total rows: 1,667 taxons
- Rows with extra_data: 1,670 (100%)
- Hierarchy: 3 levels (family → genus → species)
- Nested sets: Full coverage (lft/rght on all rows)

#### NEW: `entity_taxonomy` (DuckDB)

```sql
CREATE TABLE entity_taxonomy (
    id BIGINT,                         -- Hash-based ID
    parent_id DOUBLE,                  -- Parent reference
    level BIGINT,                      -- Hierarchy depth
    rank_name VARCHAR,
    rank_value VARCHAR,
    full_path VARCHAR,                 -- Materialized path
    taxon_id BIGINT,                   -- External ID preserved
    full_name VARCHAR
);
```

**Sample Data**:
```
id        | parent_id    | level | rank_name | full_name            | taxon_id | full_path
----------|--------------|-------|-----------|----------------------|----------|----------
3167473   | NULL         | 0     | family    | Meryta balansae      | 4268     | NULL
9145679   | 3474989336.0 | 2     | species   | Meryta balansae      | 4268     | NULL
150780    | 1994978278.0 | 2     | species   | Ochrosia balansae    | 4476     | NULL
```

**Statistics**:
- Total rows: 1,667 taxons
- Rows with extra_data: 0 (0%)
- Hierarchy: Same 3 levels
- Nested sets: None (no lft/rght columns)

#### What Was Lost

| Feature | Old System | New System | Impact |
|---------|------------|------------|--------|
| **Nested Sets** | ✅ lft, rght | ❌ None | Cannot use `nested_set.py` loader for efficient subtree queries |
| **Extra Data** | ✅ JSON field (100% populated) | ❌ None | Cannot store API enrichment data, metadata flags |
| **External IDs** | ✅ taxon_id | ✅ taxon_id | Preserved ✅ |
| **Materialized Path** | ❌ None | ✅ full_path | New feature (unused) |
| **Authors** | ✅ authors field | ❌ None | Lost taxonomic attribution |

---

### 2. Shapes Reference

#### OLD: `shape_ref` (SQLite)

```sql
CREATE TABLE shape_ref (
    id INTEGER NOT NULL,
    shape_id VARCHAR(100),             -- Unique identifier (e.g., "aires_proteg_es_22")
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),                  -- Category name (e.g., "Provinces")
    location VARCHAR NOT NULL,         -- WKT geometry
    extra_data JSON,                   -- Metadata
    lft INTEGER,                       -- Nested set left
    rght INTEGER,                      -- Nested set right
    level INTEGER,                     -- Hierarchy depth
    shape_type VARCHAR(50),            -- "type" or "shape"
    parent_id INTEGER,                 -- Parent reference
    PRIMARY KEY (id),
    FOREIGN KEY(parent_id) REFERENCES shape_ref (id)
);
```

**Sample Data** (Two-level hierarchy):
```
id | shape_id              | name                  | type            | shape_type | level | parent_id | lft | rght | extra_data
---|----------------------|----------------------|-----------------|-----------|-------|-----------|-----|------|------------
3  | NULL                 | Aires protégées      | Aires protégées | type      | 0     | NULL      | 1   | 70   | {"entity_type": "type", "auto_generated": true}
4  | aires_proteg_es_22   | Barrage de Yaté      | Aires protégées | shape     | 1     | 3         | 2   | 3    | {"entity_type": "shape"}
5  | aires_proteg_es_24   | Bois du Sud          | Aires protégées | shape     | 1     | 3         | 4   | 5    | {"entity_type": "shape"}
```

**Structure**:
- **Type rows** (level=0): Container categories like "Provinces", "Communes", "Aires protégées"
- **Shape rows** (level=1): Individual features within each type
- Each type is a parent with lft/rght spanning all its children

**Statistics**:
- Total rows: 96 (7 types + 89 shapes)
- Rows with extra_data: 96 (100%)
- Hierarchy: 2 levels (type → shape)
- Nested sets: Full coverage

#### NEW: `entity_shapes` (DuckDB)

```sql
CREATE TABLE entity_shapes (
    id BIGINT,                         -- Sequential ID
    name VARCHAR,                      -- Feature name
    location VARCHAR,                  -- WKT geometry
    entity_type VARCHAR                -- Source type name
);
```

**Sample Data** (Flat structure):
```
id | name                 | location       | entity_type
---|---------------------|----------------|-------------
1  | PROVINCE NORD       | MULTIPOLYGON() | Provinces
2  | PROVINCE SUD        | MULTIPOLYGON() | Provinces
3  | Nouméa              | MULTIPOLYGON() | Communes
4  | Barrage de Yaté     | MULTIPOLYGON() | Aires protégées
```

**Statistics**:
- Total rows: 89 (shapes only, no type rows)
- Rows with extra_data: 0
- Hierarchy: None (flat list)
- Nested sets: None

#### What Was Lost

| Feature | Old System | New System | Impact |
|---------|------------|------------|--------|
| **Nested Sets** | ✅ lft, rght | ❌ None | Cannot efficiently query shapes by type |
| **Hierarchy** | ✅ Type/Shape (2 levels) | ❌ Flat list | Cannot group shapes by type in navigation |
| **Unique IDs** | ✅ shape_id | ❌ None | Cannot reference specific shapes externally |
| **Extra Data** | ✅ JSON field (100% populated) | ❌ None | Cannot store shape metadata |
| **Type Rows** | ✅ Parent containers | ❌ None | Lost ability to navigate by shape type |

**Critical Issue**: The old system created **two rows per feature** - one type row (parent) and multiple shape rows (children). The new system only creates shape rows, losing the hierarchical grouping entirely.

---

### 3. Plots Reference

#### OLD: `plot_ref` (SQLite)

```sql
CREATE TABLE plot_ref (
    id INTEGER NOT NULL,
    plot_id INTEGER NOT NULL,          -- External ID
    locality VARCHAR NOT NULL,
    geometry VARCHAR,                  -- WKT geometry
    lft INTEGER,                       -- OPTIONAL (depends on use case)
    rght INTEGER,                      -- OPTIONAL
    level INTEGER,                     -- OPTIONAL
    plot_type VARCHAR(50),             -- OPTIONAL
    extra_data JSON,                   -- Metadata
    parent_id INTEGER,                 -- OPTIONAL
    PRIMARY KEY (id),
    FOREIGN KEY(parent_id) REFERENCES plot_ref (id)
);
```

**Key Finding**: Plots hierarchy is **OPTIONAL** - depends on use case:

**Case 1: Simple Plots** (niamoto-nc instance)
```
id | plot_id | locality  | lft  | rght | level | parent_id | extra_data
---|---------|-----------|------|------|-------|-----------|------------
2  | 2       | Aoupinié  | NULL | NULL | NULL  | NULL      | NULL
3  | 3       | Arago     | NULL | NULL | NULL | NULL      | NULL
```
- Total rows: 22 plots
- Hierarchy: None (flat structure)
- Nested sets: Not used

**Case 2: Hierarchical Plots** (nia_full_ca instance)
```
id       | plot_id  | locality         | level | parent_id | lft | rght | plot_type | extra_data
---------|----------|------------------|-------|-----------|-----|------|-----------|------------
18965853 | 18965853 | Long Transect    | 0     | NULL      | 1   | 56   | level_0   | {...}
47376938 | 47376938 | CONGO-BRAZZAVILLE| 1     | 18965853  | 2   | 23   | level_1   | {...}
677      | 677      | Ekagna1          | 2     | 47376938  | 3   | 4    | plot      | {"country": "CONGO-BRAZZAVILLE", "method": "Transect MBG style Large", ...}
678      | 678      | Ekagna2          | 2     | 47376938  | 5   | 6    | plot      | {"country": "CONGO-BRAZZAVILLE", "method": "Transect MBG style Large", ...}
```
- Total rows: 265 (6 methods + 9 countries + 250 plots)
- Hierarchy: 3 levels (method → country → plot)
- Nested sets: Fully used (lft/rght on all rows)
- Extra data: Rich metadata (coordinates, method, country, stats)

**Configuration** (nia_full_ca/config/import.yml):
```yaml
plots:
  hierarchy:
    enabled: true
    levels:
    - method      # Level 0
    - country     # Level 1
    - plot_name   # Level 2
    aggregate_geometry: true
```

**Statistics by Use Case**:

| Instance | Rows | Hierarchy | Nested Sets | Extra Data |
|----------|------|-----------|-------------|------------|
| niamoto-nc | 22 | None | Not used | Minimal |
| nia_full_ca | 265 | 3 levels | Full | Rich |

#### NEW: `entity_plots` (DuckDB)

```sql
CREATE TABLE entity_plots (
    id_plot BIGINT,                    -- External ID
    plot VARCHAR,                      -- Plot name
    elevation BIGINT,                  -- Calculated stat
    rainfall BIGINT,                   -- Calculated stat
    holdridge BIGINT,                  -- Calculated stat
    in_um BOOLEAN,                     -- Calculated stat
    species_level DOUBLE,              -- Calculated stat
    total_stems BIGINT,                -- Calculated stat
    -- ... 20+ more calculated fields
    geo_pt VARCHAR                     -- Geometry
);
```

**Sample Data**:
```
id_plot | plot      | elevation | rainfall | total_stems | nb_species | shannon | ...
--------|-----------|-----------|----------|-------------|------------|---------|----
2       | Aoupinié  | 906       | 2850     | 1247        | 201        | 4.42    | ...
3       | Arago     | 123       | 1200     | 892         | 156        | 3.98    | ...
```

**Statistics**:
- Total rows: 22 plots
- Columns: 28 (mostly calculated stats)
- Reference fields: id_plot, plot, geo_pt
- Stats fields: elevation, rainfall, shannon, simpson, basal_area, etc.

#### What Changed

| Feature | Old System (niamoto-nc) | Old System (nia_full_ca) | New System | Impact |
|---------|-------------------------|--------------------------|------------|--------|
| **Purpose** | ✅ Reference lookup | ✅ Hierarchical reference | ❌ Mixed reference + stats | Confuses reference vs derived data |
| **Nested Sets** | ❌ Not used (flat) | ✅ Full hierarchy (3 levels) | ❌ None | Cannot support hierarchical plots use case |
| **Extra Data** | ⚠️ Minimal | ✅ Rich metadata | ❌ None | Lost metadata storage capability |
| **External IDs** | ✅ plot_id | ✅ plot_id | ✅ id_plot | Preserved ✅ |
| **Stats Fields** | ❌ None | ❌ None | ✅ 25+ calculated fields | Now mixing concerns |
| **Hierarchy Config** | N/A | ✅ `hierarchy.enabled: true` | ❌ Not supported | Lost configurability |

**Critical Issues**:

1. **Mixed Concerns**: `entity_plots` is now **stats data**, not a reference hierarchy. The old `plot_ref` was either:
   - A simple lookup table (niamoto-nc case)
   - A hierarchical reference (nia_full_ca case)

2. **Lost Hierarchy Support**: The new system **cannot support hierarchical plots** like nia_full_ca (method → country → plot). This breaks use cases where plots need to be organized by:
   - Collection method (Transect, Quadrat, etc.)
   - Geographic grouping (Country, Region, Site)
   - Project organization (Campaign, Team, Plot)

3. **Solution Needed**: The new system should have:
   - `entity_plots` (reference) - plot metadata and geometry, **optionally hierarchical**
   - `plot_stats` (derived) - calculated statistics per plot

---

## Feature Analysis

### 1. Nested Sets (lft/rght)

#### What Are Nested Sets?
A hierarchical data model that assigns each node two numbers (left and right) representing its position in a tree. A node's descendants are those with lft values between the node's lft and rght.

**Example**:
```
Family (lft=1, rght=8)
  ├─ Genus (lft=2, rght=7)
  │   ├─ Species A (lft=3, rght=4)
  │   └─ Species B (lft=5, rght=6)
```

#### Why They Were Used

**Performance**: Single query to get entire subtree
```sql
-- Get all descendants of node with id=132
SELECT * FROM taxon_ref
WHERE lft >= (SELECT lft FROM taxon_ref WHERE id=132)
  AND rght <= (SELECT rght FROM taxon_ref WHERE id=132);
```

vs. **Adjacency List**: Recursive queries (slower)
```sql
-- Multiple queries needed
WITH RECURSIVE descendants AS (
  SELECT * FROM entity_taxonomy WHERE id = 132
  UNION ALL
  SELECT t.* FROM entity_taxonomy t
  JOIN descendants d ON t.parent_id = d.id
)
SELECT * FROM descendants;
```

#### Where They Were Used

1. **`nested_set.py` loader** (src/niamoto/core/plugins/loaders/nested_set.py:104-124)
   - Efficiently loads all data within a hierarchy subtree
   - Used for aggregating stats across taxonomic groups
   - **Status**: ❌ Broken without lft/rght

2. **`hierarchical_nav_widget.py` widget** (src/niamoto/core/plugins/widgets/hierarchical_nav_widget.py:71-80)
   - Supports BOTH nested sets and adjacency list
   - Nested sets provide better performance for deep trees
   - **Status**: ⚠️ Degraded (falls back to slower adjacency list)

#### Performance Comparison

| Operation | Nested Sets | Adjacency List | Difference |
|-----------|-------------|----------------|------------|
| Get subtree | 1 query | N queries (recursive) | 10-100x faster |
| Get ancestors | 1 query | N queries (recursive) | 10-100x faster |
| Get siblings | 1 query | 1 query | Same |
| Insert node | Update many rows | Update 1 row | Slower writes |
| Move subtree | Update many rows | Update 1 row | Slower writes |

**Recommendation**: Keep nested sets for **read-heavy** hierarchies (taxonomy, shapes, hierarchical plots). Make it **optional via config** to support both flat and hierarchical plots.

---

### 2. Extra Data (JSON)

#### What Is extra_data?
A JSON column for storing flexible metadata that doesn't fit into fixed schema columns.

**Example**:
```json
{
  "auto_generated": true,
  "taxon_type": "family",
  "original_id": null,
  "endemic": true,
  "protected": false,
  "redlist_cat": "VU",
  "image_url": "https://..."
}
```

#### Why It Was Used

1. **Flexibility**: Store variable metadata without schema changes
2. **API Enrichment**: Store data from external APIs (api_taxonomy_enricher.py)
3. **Import Metadata**: Track import provenance (auto_generated, original_id)
4. **Feature Flags**: Store boolean flags (endemic, protected)

#### Where It Was Used

1. **`api_taxonomy_enricher.py`** (src/niamoto/core/plugins/loaders/api_taxonomy_enricher.py:62-66)
   - Maps API response fields to extra_data
   - Example: `"response_mapping": {"endemic": "endemique"}`
   - **Status**: ❌ Broken (cannot store enriched data)

2. **`field_aggregator.py`** (src/niamoto/core/plugins/transformers/aggregation/field_aggregator.py:42-44)
   - Supports dot notation for JSON fields
   - Example: `"field": "extra_data.endemic"`
   - **Status**: ❌ Broken (no extra_data column)

3. **Transform configs** (test-instance/niamoto-nc/config/transform.yml)
   - Used in field mappings for stats calculations
   - **Status**: ❌ Broken

#### Usage Statistics

| Entity | Instance | Rows | With extra_data | Percentage |
|--------|----------|------|-----------------|------------|
| taxon_ref | niamoto-nc | 1,667 | 1,670 | 100% |
| shape_ref | niamoto-nc | 96 | 96 | 100% |
| plot_ref | niamoto-nc | 22 | ~0 | ~0% |
| plot_ref | nia_full_ca | 265 | 250 | 94% |

**Key Finding**: extra_data usage varies by entity and use case:
- **Always essential**: taxonomy (100%), shapes (100%)
- **Use case dependent**: plots (0% for simple, 94% for hierarchical)

---

### 3. Unique Identifiers

#### OLD: Entity-Specific IDs

| Entity | ID Field | Format | Example |
|--------|----------|--------|---------|
| Taxonomy | taxon_id | Integer | 2054 |
| Shapes | shape_id | String | "aires_proteg_es_22" |
| Plots | plot_id | Integer | 2 |

**Purpose**: External referencing, data linking, API queries

#### NEW: Hash-Based IDs

| Entity | ID Field | Format | Example |
|--------|----------|--------|---------|
| Taxonomy | id | Hash | 150780 |
| Shapes | id | Sequential | 1, 2, 3 |
| Plots | id_plot | Integer (preserved) | 2 |

**Issue**: Taxonomy lost stable IDs (hash changes on re-import). Shapes lost unique identifiers entirely.

---

## Impact Assessment

### Broken Features

1. ❌ **Nested Set Loader**: Cannot query hierarchical data efficiently
2. ❌ **API Taxonomy Enricher**: Cannot store enriched metadata
3. ❌ **Field Aggregator**: Cannot access JSON metadata in transforms
4. ❌ **Hierarchical Navigation**: Degraded performance (falls back to adjacency list)
5. ❌ **Shape Type Grouping**: Cannot distinguish shape types from shapes
6. ❌ **Transform Stats**: Cannot access metadata fields in calculations

### Working Features

1. ✅ **Basic Hierarchy**: Adjacency list (parent_id) still works
2. ✅ **Data Loading**: Import/export functions work
3. ✅ **Simple Queries**: Direct field access works

### Data Integrity

| Concern | Status | Notes |
|---------|--------|-------|
| Data loss | ⚠️ Metadata lost | extra_data not migrated |
| ID stability | ⚠️ Hash IDs change | taxon_id preserved but not primary |
| Hierarchy | ❌ Shapes broken | Flat instead of hierarchical |
| Reference separation | ❌ Plots mixed | Stats + reference combined |

---

## Recommendations

### Priority 1: Critical Restorations

#### 1.1 Add extra_data to All Entity Tables

**Rationale**: Required for API enrichment, flexible metadata, import tracking

**Implementation**:
```python
# In engine.py, add extra_data column to all tables
def _build_metadata(self, df, ...):
    # Add extra_data as JSON column
    if "extra_data" not in df.columns:
        df["extra_data"] = None

    metadata["schema"]["fields"].append({
        "name": "extra_data",
        "type": "json"
    })
```

**Impact**:
- ✅ Enables API enricher plugin
- ✅ Enables field aggregator dot notation
- ✅ Supports flexible metadata storage
- ⚠️ Requires migration of existing data

---

#### 1.2 Add Nested Sets to Hierarchical Entities

**Rationale**: Required for efficient hierarchical queries, nested set loader

**Implementation Option A: Always Generate** (Simple but inflexible)
```python
# In hierarchy_builder.py, always add lft/rght
from sqlalchemy_mptt import Node, Tree

def build_from_dataset(self, source_table, config):
    # ... existing code ...
    # Add nested set fields
    tree = Tree(hierarchy_df, parent_id_field="parent_id")
    hierarchy_df["lft"] = tree.left_values
    hierarchy_df["rght"] = tree.right_values
    return hierarchy_df
```

**Implementation Option B: Conditional via Config** (Generic approach)
```yaml
# In import.yml
entities:
  references:
    taxonomy:
      hierarchy:
        strategy: nested_set  # or "adjacency_list" or "hybrid"
        levels: [family, genus, species]
```

```python
# In engine.py
if hierarchy_config and hierarchy_config.strategy == "nested_set":
    # Generate lft/rght fields
    hierarchy_df = self._add_nested_sets(hierarchy_df)
```

**Recommendation**: **Option B** - Make it configurable to stay generic.

**Impact**:
- ✅ Enables nested_set.py loader
- ✅ Improves hierarchical_nav_widget performance
- ✅ Keeps system generic (optional feature)
- ⚠️ Slower writes for nested set tables

---

#### 1.3 Fix Shapes Hierarchical Structure

**Rationale**: Shapes need two-level hierarchy (type → shape) for grouping and navigation

**Current Issue**: Only shape rows are created, type rows are missing

**Solution**: Update `import_multi_feature()` to create type rows
```python
def import_multi_feature(self, ...):
    all_features = []
    feature_id = 1

    for source in sources:
        # 1. Create TYPE row (parent)
        type_row = {
            "id": feature_id,
            "name": source.name,  # "Provinces"
            "location": None,
            "entity_type": "type",
            "level": 0,
            "parent_id": None,
        }
        all_features.append(type_row)
        type_id = feature_id
        feature_id += 1

        # 2. Create SHAPE rows (children)
        gdf = gpd.read_file(source.path)
        for idx, row in gdf.iterrows():
            shape_row = {
                "id": feature_id,
                "shape_id": f"{source.name.lower()}_{feature_id}",
                "name": row[source.name_field],
                "location": row.geometry.wkt,
                "entity_type": "shape",
                "type": source.name,
                "level": 1,
                "parent_id": type_id,
            }
            all_features.append(shape_row)
            feature_id += 1
```

**Impact**:
- ✅ Restores type/shape hierarchy
- ✅ Enables grouping by shape type
- ✅ Matches old system structure

---

#### 1.4 Separate Plots Reference from Stats + Support Hierarchy

**Rationale**:
1. Mixing reference and stats violates separation of concerns
2. Need to support both flat and hierarchical plots (nia_full_ca use case)

**Solution**: Create two entities with optional hierarchy
1. `entity_plots` (reference): plot_id, locality, geometry, extra_data, **optional hierarchy**
2. `plot_stats` (derived): calculated statistics linked to plot_id

**Implementation Option A: Flat Plots** (niamoto-nc case)
```yaml
# In import.yml
entities:
  references:
    plots:
      kind: spatial
      connector:
        type: file
        path: imports/plots.csv
      schema:
        id_field: plot_id
        fields:
          - name: locality
            type: string
          - name: geo_pt
            type: geometry
      # No hierarchy config = flat structure
```

**Implementation Option B: Hierarchical Plots** (nia_full_ca case)
```yaml
# In import.yml
entities:
  references:
    plots:
      kind: hierarchical
      connector:
        type: file
        path: imports/plots.csv
      schema:
        id_field: plot_id
        fields:
          - name: locality
            type: string
          - name: geo_pt
            type: geometry
          - name: method
            type: string
          - name: country
            type: string
      hierarchy:
        strategy: nested_set  # Generate lft/rght
        levels:
          - name: method
            column: method
          - name: country
            column: country
          - name: plot
            column: locality
        aggregate_geometry: true  # Aggregate plot geometries to parent levels
```

**Stats Transform** (both cases):
```yaml
# In transform.yml
transforms:
  - name: plot_stats
    source: occurrences
    grouping: plots
    # ... existing stats calculations
```

**Impact**:
- ✅ Clear separation of reference vs derived data
- ✅ Supports both flat and hierarchical plots
- ✅ Backwards compatible with existing configs
- ✅ Follows generic import pattern

---

### Priority 2: Optional Enhancements

#### 2.1 Restore Unique Identifiers

**For Shapes**: Add shape_id generation
```python
shape_id = f"{source.name.lower().replace(' ', '_')}_{idx+1}"
```

**For Taxonomy**: Use external taxon_id as primary key option
```yaml
entities:
  references:
    taxonomy:
      connector:
        extraction:
          id_strategy: external  # Use id_column as primary key
          id_column: id_taxonref
```

---

#### 2.2 Add Materialized Path Support

**Current**: New system has `full_path` field (unused)

**Use Case**: Fast ancestor queries
```sql
-- Get all ancestors
SELECT * FROM entity_taxonomy WHERE 'Acanthaceae/Avicennia/Avicennia marina' LIKE full_path || '%';
```

**Implementation**: Generate path during hierarchy building
```python
def _build_full_path(row):
    path = []
    current = row
    while current:
        path.insert(0, current["name"])
        current = get_parent(current)
    return "/".join(path)
```

---

## Implementation Strategy

### Phase 1: Foundation (Week 1-2)
1. Add extra_data column to all entity imports
2. Migrate existing nested set logic from hierarchy_builder
3. Update config_models to support hierarchy strategies

### Phase 2: Restoration (Week 3-4)
1. Implement nested set generation (conditional)
2. Fix shapes two-level hierarchy
3. Separate plots reference from stats

### Phase 3: Enhancement (Week 5-6)
1. Restore unique identifier generation
2. Implement materialized path support
3. Update documentation and tests

### Phase 4: Migration (Week 7-8)
1. Migrate old extra_data to new schema
2. Validate all plugins work with new schema
3. Performance testing and optimization

---

## Trade-offs Analysis

### Option A: Restore Everything (Maximum Compatibility)
- ✅ All old features work
- ✅ No migration pain
- ❌ More complex system
- ❌ Harder to maintain
- ❌ Less generic

### Option B: Restore Critical Only (Balanced)
- ✅ Core features work (API enricher, hierarchical nav)
- ✅ Stays relatively generic
- ⚠️ Some features degraded (slower queries)
- ❌ Minor migration required

### Option C: Keep Simple (Maximum Simplicity)
- ✅ Very generic and maintainable
- ✅ Simple mental model
- ❌ Many plugins broken
- ❌ Performance issues
- ❌ Lost functionality

### Recommendation: **Option B - Restore Critical Only**

**What to restore**:
1. ✅ extra_data (JSON) - Critical for flexibility
2. ✅ Nested sets (lft/rght) - Optional via config
3. ✅ Shapes hierarchy - Fix type/shape structure
4. ✅ Plots separation - Split reference from stats
5. ✅ Plots hierarchy - Support optional hierarchical organization (method → country → plot)

**What to skip**:
1. ❌ Automatic unique ID generation - Use external IDs instead
2. ❌ Materialized path - Not currently used
3. ❌ Authors field - Can be in extra_data if needed

---

## Configuration Examples

### Generic Import Config with All Features

```yaml
entities:
  references:
    taxonomy:
      kind: hierarchical
      connector:
        type: derived
        source: occurrences
        extraction:
          levels:
            - {name: family, column: family}
            - {name: genus, column: genus}
            - {name: species, column: species}
          id_strategy: external  # Use id_column as primary key
          id_column: id_taxonref

      hierarchy:
        strategy: nested_set  # Generate lft/rght fields
        levels: [family, genus, species]

      enrichment:
        - plugin: api_taxonomy_enricher
          enabled: true
          config:
            response_mapping:
              endemic: endemique
              redlist: categorie_uicn
              # Stored in extra_data JSON

    shapes:
      kind: spatial
      connector:
        type: file_multi_feature
        sources:
          - {name: Provinces, path: imports/provinces.gpkg, name_field: nom}
          - {name: Communes, path: imports/communes.gpkg, name_field: nom}

      hierarchy:
        strategy: nested_set  # Two-level type/shape hierarchy
        levels: [type, shape]

    plots:
      kind: spatial  # or "hierarchical" for multi-level organization
      connector:
        type: file
        path: imports/plots.csv
      schema:
        id_field: plot_id
        fields:
          - name: locality
            type: string
          - name: geo_pt
            type: geometry
      # Optional hierarchy (for nia_full_ca-style cases)
      # hierarchy:
      #   strategy: nested_set
      #   levels: [method, country, plot_name]
      #   aggregate_geometry: true
```

---

## Conclusion

The migration to the generic import system achieved significant simplification but lost critical features needed for advanced use cases. The recommended approach is to **selectively restore** the most important features (extra_data, optional nested sets, shapes hierarchy) while maintaining the generic architecture.

**Key Decisions**:
1. ✅ Add extra_data to all entities (mandatory)
2. ✅ Make nested sets optional via hierarchy.strategy config
3. ✅ Fix shapes to create type/shape two-level hierarchy
4. ✅ Separate plots reference from stats tables
5. ❌ Skip automatic unique ID generation (use external IDs)

**Impact**: This restores ~80% of functionality while keeping ~90% of the new system's simplicity and genericity.

---

**Next Steps**: Review this analysis and decide which recommendations to implement. Priority should be given to extra_data and shapes hierarchy as they have the highest immediate impact.
