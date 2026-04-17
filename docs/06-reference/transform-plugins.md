# Transform Plugins Reference

This document explains how transform plugins fit into the GUI.

It is not intended to be the exhaustive canonical specification of every transformer parameter. The source code and plugin schemas remain the final source of truth.

## What the GUI uses

The GUI consumes transform plugins to:

- generate parameter forms
- power widget suggestions
- validate transform-backed widget configuration
- produce previewable outputs

## Main areas involved

Frontend:

- [src/niamoto/gui/ui/src/features/groups](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/groups)
- [src/niamoto/gui/ui/src/components/widgets](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/components/widgets)

Backend:

- plugin implementations under [src/niamoto/core/plugins/transformers](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/plugins/transformers)

## Common plugin families

Examples of plugin families surfaced in the GUI include:

- aggregation plugins
- statistical summary plugins
- distribution plugins
- extraction plugins
- geospatial and raster-oriented plugins

## Recommended documentation strategy

When a plugin changes:

1. update the plugin implementation and schema
2. update the GUI forms if needed
3. update user-facing guidance only when behavior or expected usage changes materially

Keeping a hand-maintained full catalog in this folder is fragile. Prefer linking directly to the relevant plugin or schema when precision matters.
