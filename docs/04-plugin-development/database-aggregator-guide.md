# Database Aggregator Guide

Use `database_aggregator` when you need read-only SQL inside a transformer entry.

## Minimal Config Block

Place this block under `widgets_data:` in an existing transform group.

```yaml
site_stats:
  plugin: database_aggregator
  params:
    queries:
      species_count: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
      occurrence_count: "SELECT COUNT(*) FROM occurrences"
```

Niamoto validates the block as a normal transformer config:

- `plugin`
- `params.queries`
- `params.templates`
- `params.computed_fields`
- `params.validation`

## Query Forms

### String query

```yaml
queries:
  total_species: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
```

### Full query object

```yaml
queries:
  species_by_province:
    sql: |
      SELECT
        s.label AS province,
        COUNT(DISTINCT t.id) AS species_count
      FROM shape_ref s
      LEFT JOIN occurrences o ON ST_Contains(ST_GeomFromText(s.location), o.geo_pt)
      LEFT JOIN taxon_ref t ON o.taxon_ref_id = t.id
      WHERE s.type = 'province' AND t.rank_name = 'species'
      GROUP BY s.label
      ORDER BY species_count DESC
    format: table
    description: Species count by province
    timeout: 60
```

## Templates

Use templates when several queries share one SQL pattern.

```yaml
templates:
  count_by_field:
    sql: "SELECT {field}, COUNT(*) AS count FROM {table} GROUP BY {field} ORDER BY count DESC LIMIT {limit}"
    params: [field, table, limit]

queries:
  species_by_family:
    template: count_by_field
    template_params:
      field: family
      table: taxon_ref
      limit: "10"
    format: table
```

The plugin validates that every template parameter declared in `params` is present in `template_params`.

## Computed Fields

Computed fields run after SQL queries complete.

```yaml
computed_fields:
  endemic_percentage:
    expression: "round((endemic_species * 100.0) / total_species, 1) if total_species else 0"
    dependencies: [endemic_species, total_species]
```

Available helpers include:

- `abs`
- `round`
- `min`
- `max`
- `sum`
- `len`
- `int`
- `float`
- `pow`
- `sqrt`
- `ceil`
- `floor`

## Validation Options

```yaml
validation:
  check_referential_integrity: true
  max_execution_time: 30
  required_tables: [taxon_ref, occurrences, plot_ref]
```

## Output Examples

### Scalar result

```json
42
```

### Table result

```json
[
  {"province": "North", "species_count": 120},
  {"province": "South", "species_count": 98}
]
```

### Single-row result

```json
{"with_coords": 44500, "total": 45678, "percentage": 97.4}
```

## Consuming The Result In A Widget

Reference the transformer output through `data_source` in `export.yml`.

```yaml
- plugin: info_grid
  title: Site overview
  data_source: site_stats
  params:
    items:
      - label: Total species
        source: species_count
      - label: Total occurrences
        source: occurrence_count
```

This example is a widget snippet, not a full export target. Put it inside `exports[*].groups[*].widgets`.

## Practical Constraint

`database_aggregator` runs inside the transform pipeline. The current runtime does not provide a special site-wide `global` group and does not pass `group_id` into the SQL layer. If you bind this transformer to a normal group, Niamoto may execute the same query once per group item.

Use it when that tradeoff is acceptable. If you need one shared dashboard dataset, treat that as a workflow decision and verify the surrounding transform/export pipeline, not just the plugin config.
