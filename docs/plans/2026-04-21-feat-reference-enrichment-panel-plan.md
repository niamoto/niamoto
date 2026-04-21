---
title: "feat: implement reference enrichment panel workflow"
type: feat
date: 2026-04-21
spec: docs/superpowers/specs/2026-04-21-reference-enrichment-panel-design.md
---

# feat: implement reference enrichment panel workflow

## Overview

Implement the approved `Reference Enrichment Panel` design so users can exploit `extra_data.api_enrichment.sources.*` from the collection widget workflow without manually typing provider-specific paths.

The implementation should introduce a new transformer-widget pair:

- `reference_enrichment_profile`
- `enrichment_panel`

and wire it into the existing suggestion, preview, export, and widget editing flows.

The intended product outcome is:

- `info_grid` stays simple and editorial
- `Add widget` can suggest one enrichment panel per detected source
- each suggested panel starts as a compact single-source profile
- users can later refine the panel by sections and fields, including multi-source composition

## Constraints

- Do not overload `info_grid` with enrichment-profile behavior
- Do not expose raw `extra_data.*` paths as the default editing experience
- Keep the existing widget suggestion flow and preview architecture when possible
- Preserve export/preview alignment by using the same transformer + widget path
- Support unknown or custom enrichment sources through a generic fallback
- Keep V1 scoped to a small stable set of display formats and known provider profiles

## Files in Scope

### Backend

- `src/niamoto/core/plugins/transformers/aggregation/reference_enrichment_profile.py` (new)
- `src/niamoto/core/plugins/widgets/enrichment_panel.py` (new)
- `src/niamoto/core/plugins/widgets/__init__.py`
- `src/niamoto/core/plugins/transformers/__init__.py`
- `src/niamoto/core/imports/widget_generator.py`
- `src/niamoto/gui/api/services/templates/suggestion_service.py`
- `src/niamoto/gui/api/services/templates/utils/widget_utils.py`
- `src/niamoto/gui/api/services/preview_engine/engine.py`
- `src/niamoto/gui/api/services/preview_engine/plotly_bundle_resolver.py`
- `src/niamoto/gui/api/routers/templates.py` or a nearby API router if a dedicated enrichment field-catalog endpoint is added

### Frontend

- `src/niamoto/gui/ui/src/components/widgets/types.ts`
- `src/niamoto/gui/ui/src/components/widgets/WidgetPreviewPanel.tsx`
- `src/niamoto/gui/ui/src/components/widgets/WidgetConfigForm.tsx`
- `src/niamoto/gui/ui/src/components/widgets/AddWidgetModal.tsx`
- `src/niamoto/gui/ui/src/components/widgets/useWidgetConfig.ts`
- `src/niamoto/gui/ui/src/components/content/LayoutOverview.tsx`
- `src/niamoto/gui/ui/src/lib/api/widget-suggestions.ts`
- `src/niamoto/gui/ui/src/lib/api/...` for a possible enrichment field-catalog query hook
- `src/niamoto/gui/ui/src/i18n/locales/fr/widgets.json`
- `src/niamoto/gui/ui/src/i18n/locales/en/widgets.json`

### Tests

- `tests/core/plugins/transformers/aggregation/test_reference_enrichment_profile.py` (new)
- `tests/core/plugins/widgets/test_enrichment_panel.py` (new)
- `tests/gui/api/services/templates/test_suggestion_service.py`
- `tests/gui/api/services/preview_engine/test_engine.py`
- `tests/gui/api/routers/test_config_extra_data.py` or a new router test file for field-catalog behavior
- `src/niamoto/gui/ui/...` frontend tests if the widget editor gets dedicated behavior

## Technical Approach

### Architecture Decision

Use a normalized intermediate profile instead of rendering directly from raw enrichment payloads.

The implementation should follow this chain:

1. inspect `extra_data.api_enrichment.sources.*`
2. apply a known provider profile or generic fallback
3. build a normalized structure with `summary`, `sections`, `sources`, `meta`
4. render that structure through `enrichment_panel`

This keeps:

- provider-specific interpretation in one place
- the widget contract stable
- preview and export easier to keep aligned

### Shared Data Profiling Layer

Do not scatter enrichment-path heuristics across:

- the transformer
- the suggestion service
- the future field picker

Instead, implement a reusable profiling layer that can:

- enumerate available enrichment sources for a reference
- inspect a source payload
- classify displayable fields
- apply known profile defaults
- generate generic fallback sections
- return a normalized field catalog with human labels and inferred formats

This can live in one new backend helper module if that keeps the transformer and suggestion service thin.

### GUI Editing Strategy

Do not try to force the full `enrichment_panel` editing UX through the generic `JsonSchemaForm` alone.

The generic form stack is useful for static scalar params, but the approved design needs:

- section-level editing
- source-aware field picking
- human labels instead of raw paths
- multi-source composition with provenance

The recommended implementation is a dedicated editor component used only when `widget.widgetPlugin === 'enrichment_panel'`.

This keeps the generic form pipeline intact for all other widgets.

## Implementation Phases

### Phase 1: Build the shared enrichment profiling and field-catalog layer

**Goal**

Create the reusable backend logic that understands enrichment payloads and can support both suggestions and runtime normalization.

**Tasks**

- Add a reusable helper module for enrichment source inspection and profile building
- Implement known-provider profile definitions for a small initial set
  - `gbif`
  - `endemia`
  - `taxref`
  - optionally one or two others only if already stable
- Implement generic fallback logic for unknown/custom sources
- Define a stable normalized item model with:
  - `source_id`
  - `path`
  - `label`
  - `format`
  - optional section metadata
- Add logic to classify displayable values:
  - scalar text
  - number
  - badge / boolean / status
  - link
  - image-like payload
  - short list
- Add exclusion rules for noisy fields:
  - large raw blobs
  - provider plumbing
  - debug blocks
  - overly deep nested objects

**Output of this phase**

- a source profile registry
- a generic fallback builder
- a field catalog structure reusable by both the transformer and the GUI

**Verification**

- targeted pure-unit tests for:
  - known profile extraction
  - generic fallback grouping
  - label humanization
  - field format inference
  - field exclusion rules

### Phase 2: Implement the `reference_enrichment_profile` transformer

**Goal**

Create the transformer that turns stored enrichment payloads into a normalized renderable profile.

**Tasks**

- Add `reference_enrichment_profile` under `core/plugins/transformers/aggregation`
- Define a config model for:
  - `source`
  - `summary_items`
  - `sections`
  - section-level default `source_id`
  - item-level `source_id` override
  - collapsed/hidden metadata where needed
- Make paths relative to `extra_data.api_enrichment.sources.<source_id>.data`
- Reuse the shared profiling layer from Phase 1
- Support two modes:
  - fully explicit config supplied by suggestions/editor
  - profile/fallback-driven config generation when needed
- Ensure missing fields are skipped without failing the whole widget
- Ensure empty sections disappear from output
- Emit a stable normalized structure:
  - `summary`
  - `sections`
  - `sources`
  - `meta`

**Important behavior**

- summary items always keep explicit provenance
- sections may have a default `source_id`
- items inside sections may override the section source for multi-source panels
- sparse known profiles may degrade to generic fallback instead of erroring

**Verification**

- transformer tests for:
  - known source
  - unknown source fallback
  - mixed-source summary
  - mixed-source section
  - missing-path handling
  - empty-section removal

### Phase 3: Implement the `enrichment_panel` widget

**Goal**

Render the normalized profile with compact summary cards plus collapsible sections.

**Tasks**

- Add `enrichment_panel` under `core/plugins/widgets`
- Define its param schema and compatible structure
- Render:
  - summary items
  - section headers
  - collapsible bodies
  - empty states
- Implement V1 format renderers for:
  - `text`
  - `number`
  - `badge`
  - `link`
  - `image`
  - `list`
- Keep the HTML output pure and preview-safe
- Add any lightweight styling helpers needed for compact display
- Register the widget where the preview/export stack expects known widgets
- Add it to any non-Plotly resolver tables so preview bundle logic stays correct

**Verification**

- widget tests for:
  - compact summary rendering
  - collapsed vs expanded sections
  - supported format rendering
  - empty state behavior
  - partial data rendering

### Phase 4: Add enrichment-panel suggestions to the backend suggestion flow

**Goal**

Make `Add widget` propose one enrichment panel per exploitable enrichment source.

**Tasks**

- Extend `suggestion_service.py` to inspect reference `extra_data.api_enrichment.sources.*`
- Reuse the shared field-catalog logic from Phase 1 instead of building ad hoc heuristics in the suggestion service
- Create one `TemplateSuggestion` per exploitable source
- Populate each suggestion with:
  - `template_id`
  - `name`
  - `description`
  - `plugin: reference_enrichment_profile`
  - `widget_plugin: enrichment_panel`
  - `transformer_config`
  - `widget_params`
  - confidence
- Keep the default suggestion single-source even though the saved config may later become multi-source
- Give known-provider suggestions higher confidence than generic fallback suggestions
- Add a guard so very weak/noisy sources do not produce low-value suggestions
- Update widget-plugin mapping helpers and known-widget lists where needed

**Preview note**

The current `AddWidgetModal` can already use inline preview when a suggestion provides full transformer + widget config. Prefer that path instead of adding a special preview shortcut for this widget in the first pass.

**Verification**

- suggestion-service tests for:
  - known source suggestion generation
  - unknown source fallback suggestion generation
  - no suggestion for low-signal sources
  - confidence ordering

### Phase 5: Add a dedicated enrichment-panel editor in the GUI

**Goal**

Let users refine sections and fields without editing raw `extra_data.*` paths.

**Tasks**

- Add a dedicated config editor component for `enrichment_panel`
- Branch in `WidgetConfigForm` so this widget uses the dedicated editor instead of the generic `JsonSchemaForm`
- Provide editing operations for:
  - add section
  - remove section
  - rename section
  - reorder section
  - add field
  - remove field
  - reorder field
  - rename label
  - override format
- Add a source-aware field picker backed by the shared field catalog
- Prefer a backend endpoint or query hook that returns:
  - source list
  - field labels
  - relative paths
  - inferred formats
  - grouping hints
- Keep raw path editing out of the default flow
- Allow multi-source panels by letting a field override section-level `source_id`

**Recommended UI shape**

- sections in a left or top list
- selected section editor in the main pane
- field picker that starts with source selection, not with raw path selection

**Verification**

- frontend tests or at minimum manual checks for:
  - section add/remove/reorder
  - field add/remove/reorder
  - source-aware field selection
  - multi-source override behavior

### Phase 6: Integrate the new widget cleanly into preview, labels, and layout helpers

**Goal**

Ensure the widget behaves like a first-class widget across the GUI.

**Tasks**

- Add plugin label/description/category metadata in `types.ts`
- Add preview fallbacks or metadata in `WidgetPreviewPanel.tsx` if needed
- Add layout sizing hints in `LayoutOverview.tsx`
- Add any query hooks needed for the dedicated config editor
- Ensure `useWidgetConfig` treats the widget as an `info`-style widget where appropriate
- Add translations for labels and editor actions

**Verification**

- `Add widget` gallery shows the widget cleanly
- inline preview renders without manual hacks
- saved widget can be re-opened and edited

### Phase 7: Harden preview/export parity and complete regression tests

**Goal**

Ship the feature with aligned runtime behavior and focused test coverage.

**Tasks**

- Verify that preview uses the same transformer + widget contract as export
- Add preview-engine tests for inline rendering of `reference_enrichment_profile` + `enrichment_panel`
- Add regression coverage for existing `info_grid` suggestion behavior
- Confirm the new widget does not disturb existing suggestion categories or preview bundle resolution
- Run targeted backend and frontend checks

**Verification commands**

- `uv run pytest tests/core/plugins/transformers/aggregation/test_reference_enrichment_profile.py tests/core/plugins/widgets/test_enrichment_panel.py tests/gui/api/services/templates/test_suggestion_service.py tests/gui/api/services/preview_engine/test_engine.py -q`
- `cd src/niamoto/gui/ui && pnpm build`

## Suggested Commit Breakdown

Keep commits scoped by concern:

1. `feat: add enrichment profile transformer and widget`
2. `feat: suggest enrichment panels from reference sources`
3. `feat: add enrichment panel editor workflow`
4. `test: cover enrichment panel suggestions and rendering`

This can collapse if the implementation is tightly coupled, but these are the intended review boundaries.

## Acceptance Criteria

- `Add widget` suggests one enrichment panel per exploitable enrichment source
- `info_grid` remains unchanged as the short editorial widget
- a suggested panel previews correctly through the existing modal flow
- `reference_enrichment_profile` emits normalized summary + sections data
- `enrichment_panel` renders compact summary items plus collapsible sections
- unknown/custom sources still get useful generic fallback suggestions
- users can refine a saved panel by sections and fields without defaulting to raw path editing
- a panel can start single-source and later include fields from other sources
- preview and export use the same logical transformer + widget contract
- existing widget suggestions and existing enrichment storage remain functional

## Risks

### Main Risk

The main risk is overbuilding the editor and turning V1 into a full enrichment browser.

**Mitigation**

- keep the suggestion model single-source
- keep the supported formats small
- use a dedicated editor only for the necessary section/field operations
- do not add semantic cross-source deduplication in V1

### Secondary Risk

The second risk is duplicating enrichment heuristics in too many places.

**Mitigation**

- invest early in one shared profiling/catalog layer
- make both the transformer and the suggestion service depend on it
- keep provider-specific defaults in a small registry

### Tertiary Risk

The third risk is trying to express the editing UX entirely through the generic schema form stack.

**Mitigation**

- use a dedicated editor component for `enrichment_panel`
- keep the generic schema form unchanged for other widgets

## Out of Scope For This Plan

- raw JSON enrichment editing as the default UI
- advanced semantic fusion across providers
- provider-specific custom layouts beyond known profile defaults
- automatic merging of several source suggestions into one suggestion card
- replacing the enrichment workspace itself

## References

- Approved spec: `docs/superpowers/specs/2026-04-21-reference-enrichment-panel-design.md`
- Existing reference-field suggestion baseline: `src/niamoto/gui/api/services/templates/suggestion_service.py`
- Existing `info_grid` widget: `src/niamoto/core/plugins/widgets/info_grid.py`
- Existing transform→widget mapping: `src/niamoto/gui/api/services/templates/utils/widget_utils.py`
- Existing inline preview path in add-widget modal: `src/niamoto/gui/ui/src/components/widgets/AddWidgetModal.tsx`
