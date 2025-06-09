# Database Aggregator Plugin Guide

The `database_aggregator` plugin enables direct SQL queries against the Niamoto database for complex aggregations and site-wide analytics that don't fit standard group-by transformation patterns.

## Overview

This plugin is particularly useful for:
- **Site-wide dashboards**: Overall statistics across all data
- **Complex analytics**: Multi-table joins and advanced calculations
- **Data quality reports**: Validation and completeness metrics
- **Performance monitoring**: Database size and usage statistics
- **Custom reporting**: Domain-specific calculations

## Basic Usage

### Simple Configuration

```yaml
# In transform.yml
groups:
  - group_by: global  # Special group for site-wide data
    widgets_data:
      site_stats:
        plugin: database_aggregator
        params:
          queries:
            species_count: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
            occurrence_count: "SELECT COUNT(*) FROM occurrences"
```

### Using in Widgets

```yaml
# In export.yml
widgets:
  - plugin: info_grid
    title: "Site Overview"
    data_source: site_stats
    params:
      items:
        - label: "Total Species"
          source: "species_count"
        - label: "Total Occurrences"
          source: "occurrence_count"
```

## Configuration Reference

### Query Types

#### 1. Simple String Queries

```yaml
queries:
  total_species: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
```

#### 2. Detailed Query Configuration

```yaml
queries:
  species_by_province:
    sql: |
      SELECT
        s.label as province,
        COUNT(DISTINCT t.id) as species_count
      FROM shape_ref s
      LEFT JOIN occurrences o ON ST_Contains(ST_GeomFromText(s.location), o.geo_pt)
      LEFT JOIN taxon_ref t ON o.taxon_ref_id = t.id
      WHERE s.type = 'province' AND t.rank_name = 'species'
      GROUP BY s.label
      ORDER BY species_count DESC
    format: "table"
    description: "Species count by province"
    timeout: 60
```

### Output Formats

| Format | Description | Returns |
|--------|-------------|---------|
| `scalar` | Single value (default) | `42` |
| `table` | Multiple rows as list of dicts | `[{"name": "A", "count": 10}, ...]` |
| `series` | Single column as list | `[10, 20, 30]` |
| `single_row` | Single row as dict | `{"total": 100, "avg": 25.5}` |

### Query Templates

Create reusable query patterns:

```yaml
templates:
  count_by_field:
    sql: "SELECT {field}, COUNT(*) as count FROM {table} GROUP BY {field} ORDER BY count DESC LIMIT {limit}"
    params: ["field", "table", "limit"]
    description: "Count records by any field"

queries:
  species_by_family:
    template: "count_by_field"
    template_params:
      field: "family"
      table: "taxon_ref"
      limit: "10"
    format: "table"
```

### Computed Fields

Calculate derived values from query results:

```yaml
computed_fields:
  endemic_percentage:
    expression: "(endemic_count * 100.0) / total_species if total_species > 0 else 0"
    dependencies: ["endemic_count", "total_species"]
    description: "Percentage of endemic species"

  biodiversity_index:
    expression: "sqrt(species_count * occurrences_per_species)"
    dependencies: ["species_count", "occurrences_per_species"]
```

**Available functions in expressions:**
- Math: `abs`, `round`, `min`, `max`, `sum`, `sqrt`, `ceil`, `floor`, `pow`
- Type conversion: `int`, `float`
- Collections: `len`

### Validation Options

```yaml
validation:
  check_referential_integrity: true    # Validate required tables exist
  max_execution_time: 30              # Query timeout in seconds
  required_tables: ["taxon_ref", "occurrences", "plot_ref"]
```

## Advanced Examples

### Site Dashboard

```yaml
site_overview:
  plugin: database_aggregator
  params:
    queries:
      # Basic counts
      total_species:
        sql: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
        description: "Total species count"

      total_occurrences:
        sql: "SELECT COUNT(*) FROM occurrences"
        description: "Total occurrence records"

      endemic_species:
        sql: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species' AND JSON_EXTRACT(extra_data, '$.endemic') = 'true'"
        description: "Endemic species count"

      # Data quality metrics
      spatial_completeness:
        sql: |
          SELECT
            COUNT(CASE WHEN geo_pt IS NOT NULL THEN 1 END) as with_coords,
            COUNT(*) as total,
            ROUND(COUNT(CASE WHEN geo_pt IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as percentage
          FROM occurrences
        format: "single_row"
        description: "Spatial data completeness"

    computed_fields:
      endemic_percentage:
        expression: "round((endemic_species * 100.0) / total_species, 1) if total_species > 0 else 0"
        dependencies: ["endemic_species", "total_species"]

      occurrences_per_species:
        expression: "round(total_occurrences / total_species, 1) if total_species > 0 else 0"
        dependencies: ["total_occurrences", "total_species"]
```

### Forest Analysis

```yaml
forest_analysis:
  plugin: database_aggregator
  params:
    templates:
      spatial_summary:
        sql: |
          SELECT
            s.label as area_name,
            s.type_label as area_type,
            COUNT(DISTINCT t.id) as species_count,
            COUNT(o.id) as occurrence_count,
            ROUND(AVG(CAST(JSON_EXTRACT(o.extra_data, '$.dbh') AS FLOAT)), 2) as avg_dbh
          FROM shape_ref s
          LEFT JOIN occurrences o ON ST_Contains(ST_GeomFromText(s.location), o.geo_pt)
          LEFT JOIN taxon_ref t ON o.taxon_ref_id = t.id AND t.rank_name = 'species'
          WHERE s.type = '{shape_type}'
          GROUP BY s.id, s.label, s.type_label
          ORDER BY species_count DESC
        params: ["shape_type"]

    queries:
      forest_types:
        template: "spatial_summary"
        template_params:
          shape_type: "forest_type"
        format: "table"

      provinces:
        template: "spatial_summary"
        template_params:
          shape_type: "province"
        format: "table"
```

### Data Quality Report

```yaml
data_quality:
  plugin: database_aggregator
  params:
    queries:
      taxonomy_completeness:
        sql: |
          SELECT
            COUNT(CASE WHEN parent_id IS NOT NULL OR rank_name = 'kingdom' THEN 1 END) as complete,
            COUNT(*) as total,
            ROUND(COUNT(CASE WHEN parent_id IS NOT NULL OR rank_name = 'kingdom' THEN 1 END) * 100.0 / COUNT(*), 1) as percentage
          FROM taxon_ref
        format: "single_row"

      missing_coordinates:
        sql: |
          SELECT
            t.full_name as species,
            COUNT(o.id) as occurrences_without_coords
          FROM taxon_ref t
          JOIN occurrences o ON t.id = o.taxon_ref_id
          WHERE o.geo_pt IS NULL AND t.rank_name = 'species'
          GROUP BY t.id, t.full_name
          ORDER BY occurrences_without_coords DESC
          LIMIT 10
        format: "table"
        description: "Species with most occurrences missing coordinates"
```

## Integration with Widgets

The plugin outputs can be used with any Niamoto widget:

### Info Grid

```yaml
- plugin: info_grid
  data_source: site_overview
  params:
    items:
      - label: "Total Species"
        source: "total_species"
      - label: "Endemic Rate"
        source: "endemic_percentage"
        unit: "%"
      - label: "Data Quality"
        source: "spatial_completeness.percentage"
        unit: "%"
```

### Charts

```yaml
- plugin: bar_plot
  data_source: forest_analysis
  params:
    data_key: "forest_types"  # Use table format data
    x_axis: "area_name"
    y_axis: "species_count"

- plugin: table_view
  data_source: data_quality
  params:
    data_key: "missing_coordinates"
    columns: ["species", "occurrences_without_coords"]
```

## Security Features

### SQL Validation

The plugin automatically validates SQL for security:

- ✅ **Allowed**: `SELECT` statements only
- ❌ **Forbidden**: `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `CREATE`
- ❌ **Forbidden**: SQL comments (`--`, `/* */`)
- ❌ **Forbidden**: Multiple statements

### Access Control

- **Read-only access**: Only SELECT operations allowed
- **Query timeout**: Configurable execution limits
- **Table validation**: Verify required tables exist
- **Parameter validation**: Template parameters are validated

## Performance Considerations

### Query Optimization

```yaml
queries:
  # Good: Specific columns and conditions
  optimized_query:
    sql: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"

  # Avoid: SELECT * on large tables
  slow_query:
    sql: "SELECT * FROM occurrences"  # Can be very slow
```

### Indexing

Ensure database indexes exist for frequently queried columns:

```sql
-- These indexes should exist for good performance
CREATE INDEX idx_taxon_ref_rank_name ON taxon_ref(rank_name);
CREATE INDEX idx_occurrences_taxon_ref_id ON occurrences(taxon_ref_id);
CREATE INDEX idx_shape_ref_type ON shape_ref(type);
```

### Timeout Management

```yaml
validation:
  max_execution_time: 30  # Seconds - adjust based on data size

queries:
  slow_query:
    sql: "SELECT ... complex query ..."
    timeout: 120  # Override default timeout for specific queries
```

## Troubleshooting

### Common Issues

#### Table Not Found
```
Error: no such table: my_table
```
**Solution**: Ensure table exists and is spelled correctly. Add to `required_tables` for validation.

#### SQL Syntax Error
```
Error: near "FROM": syntax error
```
**Solution**: Check SQL syntax. Test queries directly in SQLite browser first.

#### Security Validation Error
```
Error: SQL contains forbidden pattern: DROP
```
**Solution**: Only SELECT statements are allowed. Remove any data modification commands.

#### Template Parameter Error
```
Error: Missing template parameters: ['field', 'table']
```
**Solution**: Provide all required template parameters in `template_params`.

#### Computed Field Error
```
Error: Missing dependencies for computed field: ['missing_field']
```
**Solution**: Ensure all dependencies are defined in queries before computed fields.

### Debugging Tips

1. **Test queries separately**: Run SQL in database browser first
2. **Use simple queries first**: Start with basic SELECT, add complexity gradually
3. **Check data types**: Ensure computed field dependencies return expected types
4. **Enable verbose logging**: Use `--verbose` flag to see detailed execution logs
5. **Validate templates**: Test template formatting with sample parameters

## Best Practices

### Query Organization

```yaml
# Group related queries logically
site_statistics:
  plugin: database_aggregator
  params:
    queries:
      # Basic counts first
      total_species: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
      total_occurrences: "SELECT COUNT(*) FROM occurrences"

      # Complex aggregations after
      species_by_province: |
        SELECT s.label, COUNT(DISTINCT t.id) as species_count
        FROM shape_ref s ...

    # Computed fields depend on queries
    computed_fields:
      calculated_metric:
        expression: "total_occurrences / total_species"
        dependencies: ["total_occurrences", "total_species"]
```

### Template Reuse

```yaml
# Define templates once, use multiple times
templates:
  spatial_analysis:
    sql: "SELECT {fields} FROM {table} WHERE {condition}"
    params: ["fields", "table", "condition"]

queries:
  forest_summary:
    template: "spatial_analysis"
    template_params:
      fields: "COUNT(*) as count"
      table: "occurrences o JOIN shape_ref s ON ST_Contains(s.location, o.geo_pt)"
      condition: "s.type = 'forest'"
```

### Documentation

```yaml
queries:
  complex_analysis:
    sql: |
      -- Calculate species richness by elevation bands
      SELECT
        CASE
          WHEN elevation < 500 THEN 'Lowland'
          WHEN elevation < 1000 THEN 'Montane'
          ELSE 'Highland'
        END as elevation_band,
        COUNT(DISTINCT species_id) as species_count
      FROM plot_occurrence_view
      GROUP BY elevation_band
    description: "Species richness across elevation gradients"
    format: "table"
```

## Related Documentation

- [Plugin Reference Guide](plugin-reference.md) - Complete plugin system overview
- [Widget Reference Guide](widget-reference.md) - Using aggregated data in widgets
- [Export Guide](export-guide.md) - Configuring website exports
- [Database Schema Reference](../references/database-schema.md) - Available tables and columns
