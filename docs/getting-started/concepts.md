# Niamoto Core Concepts

This guide presents the key concepts to understand Niamoto's architecture and operation.

## Overview

Niamoto is an ecological data platform designed with a pipeline architecture:

```
┌─────────┐     ┌───────────┐     ┌────────┐
│ IMPORT  │ --> │ TRANSFORM │ --> │ EXPORT │
└─────────┘     └───────────┘     └────────┘
     ↓                ↓                ↓
[CSV Data]      [Statistics]    [Website]
[GIS Files]     [Aggregations]  [JSON API]
```

## 1. The Data Pipeline

### Import
The import phase loads your source data into a SQLite database:

- **Supported data**: CSV, GeoPackage, Shapefile
- **Entity types**: Taxonomy, Occurrences, Plots, Geographic shapes
- **Validation**: Automatic data consistency checking

### Transform
The transformation phase calculates statistics and prepares data for display:

- **Aggregations**: Grouping by taxon, plot, or geographic area
- **Calculations**: Ecological indices, descriptive statistics
- **Enrichment**: Adding data via external APIs

### Export
The export phase generates a static website and/or API:

- **Static site**: HTML/CSS/JS ready to deploy
- **Widgets**: Reusable visual components
- **Templates**: Complete rendering customization

## 2. Data Structure

### Taxonomy
The taxonomic hierarchy organizes species:

```
Family
└── Genus
    └── Species
        └── Subspecies (optional)
```

**Example**:
```
Araucariaceae
└── Araucaria
    ├── Araucaria columnaris
    └── Araucaria montana
```

### Occurrences
Occurrences represent individual observations:

```python
{
    "id": 12345,
    "taxon_ref_id": 1,
    "latitude": -22.2764,
    "longitude": 166.4580,
    "dbh": 45.5,  # Diameter at breast height
    "height": 12.3,
    "date_obs": "2024-03-15"
}
```

### Plots
Plots are delimited study areas:

```python
{
    "id": 1,
    "name": "Mont Panié Plot 01",
    "latitude": -20.5819,
    "longitude": 164.7672,
    "elevation": 1250,
    "area": 2500  # m²
}
```

### Shapes
Geographic shapes define zones (provinces, forests, etc.):

```python
{
    "id": 1,
    "name": "Northern Province",
    "type": "province",
    "geometry": "POLYGON(...)"  # WKT or GeoJSON format
}
```

## 3. Plugin System

Niamoto uses an extensible plugin system:

### Plugin Types

#### Loader
Load additional data into entities:
- `nested_set`: Manages hierarchies
- `spatial`: Calculates spatial relationships
- `api_taxonomy_enricher`: Enriches via API

#### Transformer
Transform and aggregate data:
- `field_aggregator`: Aggregates fields
- `species_richness`: Calculates species richness
- `shannon_diversity`: Calculates Shannon index

#### Widget
Generate visualizations:
- `interactive_map`: Interactive map
- `bar_plot`: Bar chart
- `summary_stats`: Summary statistics

#### Exporter
Export to different formats:
- `html_page_exporter`: HTML pages
- `json_api_exporter`: JSON API

### Creating a Plugin

```python
from niamoto.core.plugins.base import TransformerPlugin, register

@register("my_plugin", PluginType.TRANSFORMER)
class MyPlugin(TransformerPlugin):
    def transform(self, data, config):
        # Transformation logic
        return result
```

## 4. YAML Configuration

### File Structure

```
config/
├── config.yml      # General configuration
├── import.yml      # Data sources
├── transform.yml   # Transformation pipeline
└── export.yml      # Site generation
```

### References and Chains

Transformations can reference other results:

```yaml
- name: base_calculation
  plugin: species_count

- name: advanced_calculation
  plugin: normalize
  input: "@base_calculation"  # Reference to previous result
```

### Available Functions

In transformation chains:
- `@sum()`: Sum
- `@mean()`: Average
- `@count()`: Count
- `@unique()`: Unique values

## 5. Database

### SQLAlchemy Architecture

Niamoto uses SQLAlchemy with declarative models:

```python
# Simplified model
class Occurrence(Base):
    __tablename__ = 'occurrences'

    id = Column(Integer, primary_key=True)
    taxon_ref_id = Column(Integer, ForeignKey('taxon_ref.id'))
    geo_pt = Column(Geometry('POINT'))

    # Relationships
    taxon = relationship('TaxonRef')
```

### Spatial Extensions

GeoAlchemy2 enables spatial queries:

```python
# Find occurrences within radius
nearby = session.query(Occurrence).filter(
    func.ST_DWithin(
        Occurrence.geo_pt,
        center_point,
        1000  # meters
    )
)
```

## 6. Templates and Widgets

### Template System

Niamoto uses a **two-level template system**:

**Built-in Templates** (provided by Niamoto):
- `static_page.html` - All static pages
- `group_detail.html` - Individual entity pages (taxon, plot, shape)
- `group_index.html` - Entity list pages with search/filtering
- `_base.html` - Base layout with navigation

**Project Templates** (optional overrides):
```
templates/              # Your custom templates (optional)
├── custom_home.html    # Override static page template
├── assets/             # Your CSS, JS, images
│   ├── css/
│   └── js/
└── content/            # Markdown content files
    └── about.md
```

**Template Precedence**: Project templates override built-in templates automatically. No configuration needed - just create files to override defaults.

### Widgets

Widgets are rendered directly by their plugins and **do not use separate template files**. You can style widget output with CSS.

### Template Context

Templates receive:
- `entity`: Current entity (taxon, plot...)
- `widgets`: Rendered widget HTML
- `site`: Global configuration
- `navigation`: Menu structure

## 7. Typical Workflow

### 1. Data Preparation

```bash
# Check CSV format
head -5 imports/occurrences.csv

# Validate coordinates
ogr2ogr -f CSV /vsistdout/ imports/shapes/provinces.gpkg -sql "SELECT COUNT(*) FROM provinces"
```

### 2. Configuration

```yaml
# import.yml
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  mapping:
    # Map CSV columns to Niamoto fields
```

### 3. Execution

```bash
# Initial import
niamoto import

# Verification
niamoto stats

# Transformation
niamoto transform

# Export
niamoto export
```

### 4. Deployment

```bash
# Copy to server
rsync -avz exports/web/ user@server:/var/www/

# Or use GitHub Pages
niamoto deploy --github-pages
```

## 8. Best Practices

### Data Organization

1. **Identifier consistency**: Use unique IDs
2. **Normalization**: Separate taxonomy and occurrences
3. **Validation**: Check data before import

### Performance

1. **Indexes**: Create indexes on frequently queried fields
2. **Cache**: Enable cache for external APIs
3. **Pagination**: Limit number of entities per page

### Maintenance

1. **Versioning**: Tag your configurations
2. **Backup**: Back up database before updates
3. **Documentation**: Document your custom plugins

## Summary

Niamoto transforms your raw ecological data into an interactive website through:

1. A structured **pipeline** (Import → Transform → Export)
2. An extensible **plugin system**
3. Declarative **YAML configuration**
4. Reusable **visual widgets**
5. A **relational database** with spatial support

This modular architecture allows you to create biodiversity portals adapted to your specific needs while remaining maintainable and scalable.

## Next Steps

- [Detailed configuration](../guides/configuration.md)
- [Plugin development](../guides/custom_plugin.md)
- [Widget reference](../guides/plugin_reference.md)
