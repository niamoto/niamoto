# Database Aggregator

`database_aggregator` is a real transformer plugin. Niamoto ships it in `src/niamoto/core/plugins/transformers/aggregation/database_aggregator.py`.

## What It Does

The plugin executes read-only SQL queries against the project database and returns structured results that other widgets or exporters can consume.

It supports:

- direct SQL queries
- reusable SQL templates
- computed fields derived from query results
- basic database validation before execution

## Config Shape

The plugin expects a normal transformer entry:

```yaml
site_stats:
  plugin: database_aggregator
  params:
    queries:
      species_count:
        sql: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
      occurrence_count:
        sql: "SELECT COUNT(*) FROM occurrences"
    computed_fields:
      occurrences_per_species:
        expression: "round(occurrence_count / species_count, 1) if species_count else 0"
        dependencies: [occurrence_count, species_count]
```

Paste that block under a `widgets_data:` section in `transform.yml`.

## Output Formats

Each query can return one of four formats:

| Format | Result |
| --- | --- |
| `scalar` | single value |
| `table` | list of dictionaries |
| `series` | single-column list |
| `single_row` | one dictionary |

The plugin also adds `_metadata` with `computed_at`, `plugin`, and query counts.

## Safety

The plugin only accepts `SELECT` statements. It rejects patterns such as:

- `DROP`
- `DELETE`
- `INSERT`
- `UPDATE`
- SQL comments
- `EXEC`

## Current Limitation

`database_aggregator` does not inject the current `group_id` into your SQL. If you attach it to a transform group with many items and your query does not depend on that group, Niamoto will recompute the same result for every item in that group.

That means the plugin works best when you:

- need advanced SQL and accept repeated execution
- use a workflow that materializes one canonical result row
- keep the query cost low enough for repeated runs

Do not assume that `group_by: global` has special built-in behavior. The current transform runtime does not reserve that group name.

## When To Use It

Use `database_aggregator` when the standard transformers cannot express the query you need, especially for:

- multi-table joins
- SQL aggregations with custom grouping
- summary tables for dashboards
- derived metrics that combine several SQL results

If a regular transformer can compute the same result with structured inputs, use that transformer first.
