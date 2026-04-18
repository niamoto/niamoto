# Transform Plugins Reference

Transformer schemas drive several parts of the GUI. The source code and config
models remain the source of truth for exact parameters and validation rules.

## What the GUI reads from plugins

The GUI consumes transform plugins to:

- generate parameter forms
- power widget suggestions
- validate transform-backed widget configuration
- produce previewable outputs

## Main code areas

- frontend: `src/niamoto/gui/ui/src/features/collections`
- frontend widgets: `src/niamoto/gui/ui/src/components/widgets`
- backend plugins: `src/niamoto/core/plugins/transformers`

## Plugin families commonly surfaced in the GUI

- aggregation plugins
- statistical summary plugins
- distribution plugins
- extraction plugins
- geospatial and raster-oriented plugins

## When a plugin changes

1. update the plugin implementation and schema
2. update the GUI forms if needed
3. update user-facing guidance only when behavior or expected usage changes materially
