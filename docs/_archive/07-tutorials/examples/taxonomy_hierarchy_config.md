# Niamoto Taxonomy Hierarchy Configuration

This document explains how to configure taxonomic hierarchies in Niamoto using the flexible hierarchy system.

## Basic Configuration

Taxonomy is always extracted from occurrences data. The configuration allows you to define any taxonomic hierarchy levels:

```yaml
taxonomy:
  path: "imports/occurrences.csv"  # Path to occurrences file
  hierarchy:
    levels:
      - name: "family"
        column: "tax_fam"
      - name: "genus"
        column: "tax_gen"
      - name: "species"
        column: "tax_sp_level"
      - name: "infra"
        column: "tax_infra_level"
    taxon_id_column: "idtax_individual_f"
    authors_column: "tax_infra_level_auth"
```

## Extended Hierarchy Example

You can add any taxonomic levels your data requires:

```yaml
taxonomy:
  path: "imports/occurrences.csv"
  hierarchy:
    levels:
      - name: "kingdom"
        column: "tax_kingdom"
      - name: "phylum"
        column: "tax_phylum"
      - name: "class"
        column: "tax_class"
      - name: "order"
        column: "tax_order"
      - name: "family"
        column: "tax_fam"
      - name: "subfamily"
        column: "tax_subfam"
      - name: "tribe"
        column: "tax_tribe"
      - name: "genus"
        column: "tax_gen"
      - name: "subgenus"
        column: "tax_subgen"
      - name: "species"
        column: "tax_sp_level"
      - name: "subspecies"
        column: "tax_subsp"
      - name: "variety"
        column: "tax_var"
      - name: "form"
        column: "tax_form"
    taxon_id_column: "idtax_individual_f"
    authors_column: "tax_authors"
```

## Key Features

1. **Flexible Levels**: Define any number of taxonomic levels in any order
2. **Custom Names**: Use any names for your levels (not limited to standard ranks)
3. **Column Mapping**: Map each level to a specific column in your data
4. **Automatic Hierarchy**: The system automatically builds parent-child relationships based on the order of levels
5. **Missing Data Handling**: If intermediate levels are missing, the system will create placeholder entries


## API Enrichment

API enrichment works the same way with the new configuration:

```yaml
taxonomy:
  hierarchy:
    # ... levels configuration ...
  api_enrichment:
    enabled: true
    plugin: "gbif_api"
    params:
      base_url: "https://api.gbif.org/v1"
      timeout: 10
```

## Best Practices

1. **Order Matters**: List levels from highest (most general) to lowest (most specific)
2. **Consistent Naming**: Use consistent names across your configuration and transformations
3. **Complete Hierarchy**: Include all levels present in your data to avoid missing relationships
4. **Column Validation**: Ensure the specified columns exist in your occurrence data
