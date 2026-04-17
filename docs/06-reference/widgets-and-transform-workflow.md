# Widgets and Transform Workflow

This document explains how widgets, transformers, and group configuration relate inside the GUI.

## Core idea

A GUI widget usually combines:

- a data source
- a transformer or extractor
- a widget renderer

In simplified form:

```text
source data -> transformer -> structured output -> widget renderer -> preview / publish output
```

## User-facing workflow

Inside the group configuration flow, the user typically:

1. chooses a group
2. adds or edits a widget
3. selects a transformer and widget pairing
4. fills in plugin-backed parameters
5. previews the result
6. saves the configuration

## Source types

Widgets may operate on:

- primary imported entities
- aggregation references
- auxiliary supporting sources
- raster or spatial layers depending on plugin type

## Why this document exists

Earlier documentation described this area through outdated tab-based or wizard-based screens. The current product is better understood through the relationship between:

- groups
- widgets
- transformer-backed configuration
- preview and publish flows

## Related docs

- [../operations/transform.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/operations/transform.md)
- [../architecture/preview-system.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/architecture/preview-system.md)
