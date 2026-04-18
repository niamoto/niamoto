# Widgets and Transform Workflow

Widgets in the GUI combine three layers: data selection, transform logic, and
rendering.

## Pipeline

A GUI widget usually combines:

- a data source
- a transformer or extractor
- a widget renderer

In simplified form:

```text
source data -> transformer -> structured output -> widget renderer -> preview / publish output
```

## In the editor

Inside the collection configuration flow, the user typically:

1. chooses a group
2. adds or edits a widget
3. selects a transformer and widget pairing
4. fills in plugin-backed parameters
5. previews the result
6. saves the configuration

## Data sources

Widgets may operate on:

- primary imported entities
- aggregation references
- auxiliary supporting sources
- raster or spatial layers depending on plugin type

## Related docs

- [Collections (user guide)](../02-user-guide/collections.md)
- [GUI preview system (architecture)](../07-architecture/gui-preview-system.md)
