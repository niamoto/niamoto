# Top Ranking Plugin Guide

The `top_ranking` plugin is a flexible transformer that can calculate top N items from your data using three different modes: direct, hierarchical, and join.

## Overview

This plugin provides a generic way to rank items by frequency, with support for:
- Direct counting of values
- Hierarchical navigation (e.g., finding top families from species)
- Join-based counting (e.g., finding top taxa within plots)

## Configuration Parameters

### Common Parameters

```yaml
plugin: top_ranking
params:
  source: string        # Source data table/collection
  field: string         # Field to analyze
  count: integer        # Number of top items to return (default: 10)
  mode: string          # One of: 'direct', 'hierarchical', 'join'
  aggregate_function: string  # 'count', 'sum', 'avg' (default: 'count')
```

### Mode-Specific Parameters

#### Direct Mode
The simplest mode - counts occurrences of values directly.

```yaml
mode: direct
# No additional parameters required
```

#### Hierarchical Mode
Navigates a hierarchy to find items at a specific rank.

```yaml
mode: hierarchical
hierarchy_table: string       # Table containing the hierarchy
hierarchy_columns:            # Column mappings
  id: string                  # ID column (default: 'id')
  name: string                # Name column (default: 'full_name')
  rank: string                # Rank column (default: 'rank_name')
  parent_id: string           # Parent ID column (default: 'parent_id')
  left: string                # Left boundary for nested set (optional)
  right: string               # Right boundary for nested set (optional)
target_ranks: [string]        # List of ranks to count
```

#### Join Mode
Performs joins between tables to count related items.

```yaml
mode: join
join_table: string            # Table to join with
join_columns:                 # Join column mappings
  source_id: string           # Column in join table matching source
  hierarchy_id: string        # Column in join table for hierarchy
hierarchy_table: string       # Hierarchy table
hierarchy_columns:            # Same as hierarchical mode
target_ranks: [string]        # Target ranks to count
```

## Examples

### Example 1: Direct Counting
Count top plot names directly:

```yaml
top_plots:
  plugin: top_ranking
  params:
    source: plots
    field: locality_name
    count: 10
    mode: direct
```

### Example 2: Hierarchical Navigation
Find top families from species occurrences:

```yaml
top_families:
  plugin: top_ranking
  params:
    source: occurrences
    field: taxon_ref_id
    count: 10
    mode: hierarchical
    hierarchy_table: taxon_ref
    hierarchy_columns:
      id: id
      name: full_name
      rank: rank_name
      parent_id: parent_id
    target_ranks: ["family"]
```

### Example 3: Join-Based Counting
Find top species within specific plots:

```yaml
top_species_by_plot:
  plugin: top_ranking
  params:
    source: plots
    field: plot_id
    count: 10
    mode: join
    join_table: occurrences
    join_columns:
      source_id: plot_ref_id
      hierarchy_id: taxon_ref_id
    hierarchy_table: taxon_ref
    hierarchy_columns:
      id: id
      name: full_name
      rank: rank_name
      left: lft
      right: rght
    target_ranks: ["species", "subspecies"]
```

## Advanced Features

### Custom Aggregation Functions
Instead of counting, you can use other aggregation functions:

```yaml
params:
  aggregate_function: sum
  aggregate_field: stem_diameter
```

### Nested Set Model Support
For hierarchical data using nested set model, include left/right columns:

```yaml
hierarchy_columns:
  left: lft
  right: rght
```

This enables more efficient hierarchy traversal for large datasets.

## Output Format

The plugin returns a dictionary with two arrays:
```json
{
  "tops": ["Item1", "Item2", "Item3"],
  "counts": [100, 85, 72]
}
```

## Performance Considerations

- **Direct mode** is the fastest for simple counting
- **Hierarchical mode** performance depends on hierarchy depth
- **Join mode** can be slow for large datasets; ensure proper indexes exist

## Troubleshooting

### Empty Results
- Verify that the field exists in your data
- Check that target_ranks match your hierarchy's rank values
- Ensure join columns are correctly mapped

### Slow Performance
- Add database indexes on join columns
- Consider reducing the dataset size before transformation
- Use nested set columns (left/right) for hierarchical data
