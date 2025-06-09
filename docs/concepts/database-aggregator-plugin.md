# Database Aggregator Plugin Concept

## Overview

The `database_aggregator` plugin would be a powerful transformer that allows direct SQL queries to aggregate data across the entire Niamoto database, particularly useful for site-wide statistics and cross-cutting analyses that don't fit into the standard group-by patterns.

## Why This Plugin Would Be Valuable

### Current Limitations
- Transformations are typically scoped to specific groups (taxon, plot, shape)
- Site-wide statistics require complex configurations
- No easy way to run custom SQL for complex aggregations
- Cross-table analytics are difficult to configure

### Use Cases
1. **Site-wide Dashboard**: Total counts, percentages, ratios across all data
2. **Complex Analytics**: Multi-table joins and advanced aggregations
3. **Performance Metrics**: Database size, data quality indicators
4. **Custom Reports**: Domain-specific calculations
5. **Data Quality**: Validation and completeness checks

## Plugin Design

### Configuration Schema

```yaml
# In transform.yml
groups:
  - group_by: global  # Special group for site-wide data
    widgets_data:
      site_statistics:
        plugin: database_aggregator
        params:
          queries:
            # Simple counts
            species_count:
              sql: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
              description: "Total number of species"

            occurrence_count:
              sql: "SELECT COUNT(*) FROM occurrences"
              description: "Total number of occurrences"

            # Complex aggregations
            forest_coverage:
              sql: |
                SELECT
                  s.type_label as forest_type,
                  COUNT(o.id) as occurrence_count,
                  ROUND(AVG(o.dbh_cm), 2) as avg_dbh
                FROM shape_ref s
                LEFT JOIN occurrences o ON ST_Contains(ST_GeomFromText(s.location), o.geo_pt)
                WHERE s.type = 'forest_type'
                GROUP BY s.type_label
              description: "Forest coverage analysis"
              format: "table"

            # Data quality metrics
            data_quality:
              sql: |
                SELECT
                  'Occurrences with coordinates' as metric,
                  COUNT(CASE WHEN geo_pt IS NOT NULL THEN 1 END) as count,
                  ROUND(COUNT(CASE WHEN geo_pt IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as percentage
                FROM occurrences
                UNION ALL
                SELECT
                  'Taxons with valid hierarchy' as metric,
                  COUNT(CASE WHEN parent_id IS NOT NULL OR rank_name = 'kingdom' THEN 1 END) as count,
                  ROUND(COUNT(CASE WHEN parent_id IS NOT NULL OR rank_name = 'kingdom' THEN 1 END) * 100.0 / COUNT(*), 1) as percentage
                FROM taxon_ref
              description: "Data completeness indicators"

          # Query templates for reusable patterns
          templates:
            count_by_field:
              sql: "SELECT {field}, COUNT(*) as count FROM {table} GROUP BY {field} ORDER BY count DESC"
              params: ["field", "table"]

            spatial_join_count:
              sql: |
                SELECT
                  s.label as area_name,
                  COUNT(o.id) as occurrence_count
                FROM shape_ref s
                LEFT JOIN occurrences o ON ST_Contains(ST_GeomFromText(s.location), o.geo_pt)
                WHERE s.type = '{shape_type}'
                GROUP BY s.id, s.label
                ORDER BY occurrence_count DESC
              params: ["shape_type"]

          # Use templates
          province_stats:
            template: "spatial_join_count"
            template_params:
              shape_type: "province"
            description: "Occurrence counts by province"

          # Computed fields
          computed_fields:
            endemic_percentage:
              expression: "(endemic_count * 100.0) / total_species"
              dependencies: ["endemic_count", "total_species"]

          # Data validation
          validation:
            check_referential_integrity: true
            max_execution_time: 30  # seconds
            required_tables: ["taxon_ref", "occurrences"]
```

### Output Format

The plugin would return structured data that widgets can consume:

```json
{
  "site_statistics": {
    "species_count": 1247,
    "occurrence_count": 45678,
    "forest_coverage": [
      {"forest_type": "Humid Forest", "occurrence_count": 25000, "avg_dbh": 32.5},
      {"forest_type": "Dry Forest", "occurrence_count": 15000, "avg_dbh": 28.3}
    ],
    "data_quality": [
      {"metric": "Occurrences with coordinates", "count": 44500, "percentage": 97.4},
      {"metric": "Taxons with valid hierarchy", "count": 1200, "percentage": 96.2}
    ],
    "endemic_percentage": 78.5,
    "computed_at": "2024-01-15T10:30:00Z"
  }
}
```

## Implementation Approach

### Plugin Structure

```python
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from sqlalchemy import text
import pandas as pd
from typing import Dict, Any, List

@register("database_aggregator", PluginType.TRANSFORMER)
class DatabaseAggregatorPlugin(TransformerPlugin):
    """Execute SQL queries for cross-cutting data aggregation."""

    def transform(self, data, config):
        """Execute configured SQL queries and return aggregated results."""
        results = {}
        queries = config.get('queries', {})
        templates = config.get('templates', {})
        computed_fields = config.get('computed_fields', {})

        # Execute direct SQL queries
        for key, query_config in queries.items():
            if isinstance(query_config, str):
                # Simple SQL string
                results[key] = self._execute_query(query_config)
            elif isinstance(query_config, dict):
                if 'sql' in query_config:
                    # Full query configuration
                    results[key] = self._execute_query(
                        query_config['sql'],
                        description=query_config.get('description'),
                        format_type=query_config.get('format', 'scalar')
                    )
                elif 'template' in query_config:
                    # Use template
                    results[key] = self._execute_template(
                        query_config, templates
                    )

        # Calculate computed fields
        for field_name, field_config in computed_fields.items():
            results[field_name] = self._calculate_computed_field(
                field_config, results
            )

        return results

    def _execute_query(self, sql: str, description: str = None, format_type: str = 'scalar'):
        """Execute a SQL query and format the result."""
        try:
            with self.db.get_session() as session:
                result = session.execute(text(sql))

                if format_type == 'scalar':
                    # Single value
                    return result.scalar()
                elif format_type == 'table':
                    # Multiple rows as list of dicts
                    return [dict(row._mapping) for row in result]
                elif format_type == 'series':
                    # Single column as list
                    return [row[0] for row in result]
                else:
                    # Default to scalar
                    return result.scalar()

        except Exception as e:
            self.logger.error(f"Query failed: {sql}\nError: {str(e)}")
            return None

    def _execute_template(self, query_config: dict, templates: dict):
        """Execute a templated query."""
        template_name = query_config['template']
        template_params = query_config.get('template_params', {})

        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' not found")

        template = templates[template_name]
        sql = template['sql'].format(**template_params)

        return self._execute_query(
            sql,
            query_config.get('description'),
            query_config.get('format', 'table')
        )

    def _calculate_computed_field(self, field_config: dict, results: dict):
        """Calculate computed fields from other results."""
        expression = field_config['expression']
        dependencies = field_config.get('dependencies', [])

        # Create a safe namespace for evaluation
        namespace = {dep: results.get(dep, 0) for dep in dependencies}

        try:
            return eval(expression, {"__builtins__": {}}, namespace)
        except Exception as e:
            self.logger.error(f"Computed field calculation failed: {str(e)}")
            return None
```

## Usage Examples

### 1. Site Dashboard

```yaml
# In transform.yml
groups:
  - group_by: global
    widgets_data:
      dashboard_stats:
        plugin: database_aggregator
        params:
          queries:
            total_species:
              sql: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
            total_occurrences:
              sql: "SELECT COUNT(*) FROM occurrences"
            endemic_species:
              sql: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species' AND JSON_EXTRACT(extra_data, '$.endemic') = 'true'"

          computed_fields:
            endemic_percentage:
              expression: "(endemic_species * 100.0) / total_species"
              dependencies: ["endemic_species", "total_species"]

# In export.yml
static_pages:
  - name: dashboard
    output_file: "index.html"
    widgets:
      - plugin: info_grid
        title: "Biodiversity Overview"
        data_source: dashboard_stats
        params:
          items:
            - label: "Total Species"
              source: "total_species"
            - label: "Endemic Species"
              source: "endemic_species"
            - label: "Endemism Rate"
              source: "endemic_percentage"
              unit: "%"
```

### 2. Data Quality Report

```yaml
data_quality_report:
  plugin: database_aggregator
  params:
    queries:
      coordinate_completeness:
        sql: |
          SELECT
            'Occurrences with coordinates' as check_name,
            COUNT(CASE WHEN geo_pt IS NOT NULL THEN 1 END) as valid_count,
            COUNT(*) as total_count,
            ROUND(COUNT(CASE WHEN geo_pt IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as percentage
          FROM occurrences
        format: "table"

      taxon_hierarchy_completeness:
        sql: |
          SELECT
            rank_name,
            COUNT(*) as total,
            COUNT(parent_id) as with_parent,
            ROUND(COUNT(parent_id) * 100.0 / COUNT(*), 1) as completeness_pct
          FROM taxon_ref
          WHERE rank_name != 'kingdom'
          GROUP BY rank_name
        format: "table"
```

### 3. Complex Analytics

```yaml
forest_analysis:
  plugin: database_aggregator
  params:
    queries:
      species_by_forest_type:
        sql: |
          SELECT
            s.type_label as forest_type,
            COUNT(DISTINCT t.id) as species_count,
            COUNT(o.id) as occurrence_count,
            ROUND(AVG(CAST(JSON_EXTRACT(o.extra_data, '$.dbh') AS FLOAT)), 2) as avg_dbh
          FROM shape_ref s
          JOIN occurrences o ON ST_Contains(ST_GeomFromText(s.location), o.geo_pt)
          JOIN taxon_ref t ON o.taxon_ref_id = t.id
          WHERE s.type = 'forest_type' AND t.rank_name = 'species'
          GROUP BY s.type_label
          ORDER BY species_count DESC
        format: "table"
        description: "Species diversity by forest type"
```

## Benefits

### 1. Flexibility
- Direct SQL access for complex queries
- No need to create custom transformer plugins for simple aggregations
- Template system for reusable query patterns

### 2. Performance
- Single queries can aggregate across multiple tables
- Optimized for site-wide statistics
- Reduced transformation pipeline complexity

### 3. Power User Features
- Access to full SQL capabilities
- Complex joins and window functions
- Statistical calculations at database level

### 4. Maintainability
- SQL queries are more readable than complex plugin code
- Templates reduce duplication
- Easy to modify without code changes

## Security Considerations

### 1. SQL Injection Prevention
- Use parameterized queries where possible
- Validate template parameters
- Restrict to read-only operations

### 2. Resource Management
- Query timeout limits
- Memory usage monitoring
- Query complexity analysis

### 3. Access Control
- Read-only database access
- Query whitelist for production
- Template validation

## Integration with Widget System

Widgets would consume the aggregated data seamlessly:

```yaml
widgets:
  - plugin: bar_plot
    title: "Species by Forest Type"
    data_source: forest_analysis
    params:
      data_key: "species_by_forest_type"
      x_field: "forest_type"
      y_field: "species_count"

  - plugin: table_view
    title: "Data Quality Report"
    data_source: data_quality_report
    params:
      data_key: "coordinate_completeness"
      columns: ["check_name", "valid_count", "total_count", "percentage"]
```

## Conclusion

The `database_aggregator` plugin would fill a crucial gap in Niamoto's transformation system, enabling:

- **Site-wide analytics** that don't fit group-by patterns
- **Complex SQL queries** without custom plugin development
- **Data quality monitoring** and reporting
- **Performance dashboards** and administrative views
- **Cross-cutting analyses** that span multiple data types

This plugin would significantly enhance Niamoto's analytical capabilities while maintaining the declarative, configuration-driven approach that makes the platform accessible to non-developers.
