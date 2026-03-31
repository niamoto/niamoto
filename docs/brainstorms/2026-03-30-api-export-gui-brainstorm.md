# API Export Configuration in GUI

**Date**: 2026-03-30
**Status**: Ready for planning
**Scope**: Add GUI configuration for `json_api` and `dwc_occurrence_json` exports

## What We're Building

A 4th tab **"API Export"** in the GroupPanel, allowing users to configure `json_api` and `dwc_occurrence_json` exports directly from the GUI instead of editing raw YAML.

Currently, the GroupPanel has 3 tabs:
- **Sources** — data sources (occurrences + stats files)
- **Contenu** — widget management (list + layout/details)
- **Index** — index/listing page configuration

The new tab handles all non-web_pages exports that use the `json_api_exporter` plugin.

## Why This Approach

- **Co-located with group context**: Export config is per-group, so it belongs where users already manage their groups
- **Consistent pattern**: Follows the same tab-based model as Sources/Content/Index
- **Discoverable**: Always visible (even for unconfigured groups), with enable/disable toggle
- **Progressive complexity**: Simple toggle for json_api, full table for DwC mapping

Alternatives considered:
- SiteBuilder section — rejected because SiteBuilder is about the website, not API exports
- Top-level module — overkill, the config is naturally group-scoped
- YAML-only — the whole point is to make this accessible without YAML editing

## Key Decisions

### 1. Tab always visible for all groups
The "API Export" tab appears for every group. If an export isn't configured for a particular group (e.g. DwC only applies to taxons), show a disabled state with an "Enable for this group" button.

### 2. Global params in collapsible header
Export-level params (output_dir, patterns, json_options defaults) appear in a collapsible section at the top of the tab. They're shared across groups but shown in each group's tab for discoverability. Editing them from any group updates the same global config.

### 3. json_api per-group config
- **Detail mode**: Toggle switch — pass_through ON (default) exports all transformed data; OFF reveals a field selector with checkboxes
- **Index fields**: List editor with auto-suggestion from transformed data (reuse existing suggestion API pattern from IndexConfigEditor)
- **Per-group json_options**: Optional overrides (collapsible, advanced)

### 4. DwC mapping as editable table
The Darwin Core mapping is displayed as a table with columns:
| DwC Field | Source | Generator |
Each row is editable. Generators with params expand into a detail form. An "Add field" button at the bottom allows extending the mapping. This keeps the complex mapping visual and manageable.

### 5. Enable/disable per export per group
Each export (json_api, dwc_occurrence_json) has a checkbox toggle per group. Disabling removes the group entry from the export config; enabling creates a default entry.

## UI Structure

```
GroupPanel > API Export tab
├── [collapsible] Global Settings (per export)
│   ├── json_api
│   │   ├── output_dir: exports/api
│   │   ├── detail_output_pattern: {group}/{id}.json
│   │   ├── index_output_pattern: all_{group}.json
│   │   └── json_options: indent, minify, compress...
│   └── dwc_occurrence_json
│       ├── output_dir: exports/dwc/occurrence_json
│       ├── detail_output_pattern: {group}/{id}_occurrences_dwc.json
│       └── json_options: indent, ensure_ascii
│
├── json_api (for this group)
│   ├── ☑ Enabled
│   ├── Detail: [pass_through toggle]
│   │   └── (if OFF) Field selector with checkboxes
│   ├── Index fields: drag-and-drop list with auto-suggest
│   │   └── Each field: { output_name: source_path } or { generator + params }
│   └── [collapsible] JSON options override
│
└── dwc_occurrence_json (for this group)
    ├── ☑ Enabled / ☐ Not configured [+ Enable]
    ├── Transformer: niamoto_to_dwc_occurrence
    ├── Transformer params:
    │   ├── occurrence_table, taxonomy_entity, etc.
    │   └── Mapping table:
    │       ┌─────────────────┬──────────────┬────────────┐
    │       │ DwC Field       │ Source       │ Generator  │
    │       ├─────────────────┼──────────────┼────────────┤
    │       │ scientificName  │ @src.taxonref│ -          │
    │       │ eventDate       │ @src.month   │ format_..  │
    │       │ decimalLatitude  │ @src.geo_pt  │ format_..  │
    │       └─────────────────┴──────────────┴────────────┘
    │       [+ Add field]
    └── Index fields (same pattern as json_api)
```

## Backend API Design

New endpoints needed (following existing patterns from site.py and config.py):

```
GET  /config/export/api-exports
     → Returns all json_api_exporter exports with their groups

GET  /config/export/api-exports/{export_name}/groups/{group_by}
     → Returns per-group config for a specific export

PUT  /config/export/api-exports/{export_name}/groups/{group_by}
     → Updates per-group config

PUT  /config/export/api-exports/{export_name}/params
     → Updates global params for an export

GET  /config/export/api-exports/{export_name}/groups/{group_by}/suggestions
     → Returns available fields from transformed data (reuse existing logic)
```

## Implementation Considerations

- **Reuse**: Index fields editor can share components with IndexConfigEditor (field list, drag-and-drop, auto-suggest)
- **Genericity**: The tab should work for any `json_api_exporter` export, not just the two current ones. Discover exports dynamically from export.yml.
- **Save pattern**: Follow existing useSiteConfig/useIndexConfig pattern — local state + save/reset buttons
- **i18n**: Add translation keys in `export.json` locale files

## Open Questions

1. Should the global settings section default to collapsed (to reduce noise) or expanded on first visit?
2. For the DwC mapping table, should generator params be inline or in a popover/dialog?
3. Should we support adding entirely new json_api_exporter exports from the GUI, or only edit existing ones?

## Scope for V1

**In scope:**
- 4th tab in GroupPanel
- json_api: enable/disable, pass_through toggle, index fields with suggestions
- dwc_occurrence_json: enable/disable, mapping table, index fields
- Global settings (collapsible)
- Backend API endpoints

**Out of scope (future):**
- Creating new json_api_exporter exports from GUI
- Drag-and-drop reordering of DwC mapping fields
- Visual preview of JSON output
- Validation/test run of export from the tab
