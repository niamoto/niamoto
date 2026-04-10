# Enrichment Tab UX Consolidation Design

**Date**: 2026-04-10
**Status**: Approved design
**Scope**: Consolidate the enrichment workspace UX around a disciplined three-column layout

## Goal

Refactor the enrichment workspace so it stays dense and efficient without reintroducing the nested scroll, overflow, and compression problems already observed in the current implementation.

This design keeps the preferred `A` direction:

- left column for sources
- center column for source configuration
- right column for testing and results

But it constrains that layout so it remains usable on real desktop widths.

## Product Decision

The enrichment workspace will use a **disciplined three-column layout** with these rules:

- the three columns are always visible only on large screens
- each column has a single vertical scroll context
- the right column is an inspection panel, not a second full workspace
- the center column remains the primary editing surface
- below a width threshold, the layout degrades to two columns instead of squeezing three columns indefinitely

This preserves the fast config → test loop while avoiding the "everything open everywhere" failure mode.

## Layout

### Global structure

- sticky summary bar at the top
- horizontal `ResizablePanelGroup` below the summary
- three panels on large screens:
  - `SourcesPanel`
  - `ConfigPanel`
  - `InspectorPanel`

### Panel sizing

- `SourcesPanel`
  - default: `22%`
  - min: `18%`
  - max: `28%`
- `ConfigPanel`
  - default: `46%`
  - min: `34%`
- `InspectorPanel`
  - default: `32%`
  - min: `24%`
  - max: `40%`

The center panel is the priority panel. Resizing must never make it collapse into a narrow form layout.

### Breakpoint behavior

- `>= 1440px`
  - full three-column layout
- `~1100px - 1439px`
  - still three columns, but with bounded widths
- `< 1100px`
  - collapse to two columns:
    - left `SourcesPanel`
    - right `MainPanel`
  - inside `MainPanel`, `Configuration / Tester / Results` become top-level tabs

This fallback is required. The design must not force the three-column mode on medium desktop widths.

## Column Responsibilities

### 1. SourcesPanel

Purpose: navigation and high-level per-source status.

Contains:

- list of configured sources
- compact badges for status
- mini progress bars
- add source action

Does not contain:

- large action toolbars
- detailed config
- preview payloads
- long textual descriptions

Each source row should behave like a navigational item first, not like a dashboard card.

### 2. ConfigPanel

Purpose: edit the active source.

Contains:

- source header
- collapsible config sections
- save/apply actions close to the edited content

Config sections:

1. `Connection`
2. `Authentication`
3. `Profile options`
4. `Advanced mapping`

Default open state:

- `Connection`: open
- `Profile options`: open
- `Authentication`: closed unless auth is required
- `Advanced mapping`: closed

This panel owns configuration. It should not also own result rendering.

### 3. InspectorPanel

Purpose: inspect the active source without leaving the editing flow.

Contains, in order:

1. test input area
2. last preview result
3. recent persisted results
4. compact runtime stats

Important constraint:

This panel is **not** a second primary screen. It should show:

- the latest useful inspection state
- a short recent-results view
- enough context to decide the next edit

It should not try to render the entire historical result workspace inside a narrow column.

## Scroll Rules

This is the core non-negotiable part of the redesign.

### Allowed

- one scroll container for `SourcesPanel`
- one scroll container for `ConfigPanel`
- one scroll container for `InspectorPanel`

### Forbidden

- fixed-height cards with internal scrolling inside those panels
- `ScrollArea` inside another `ScrollArea`
- `overflow-auto` blocks nested inside panel scroll roots, except for very small bounded widgets such as code/raw JSON viewers

### Height policy

Panel height should be derived from viewport height minus the sticky header area.

Do not use hard-coded heights like:

- `220px`
- `360px`
- `420px`
- `620px`

If a section grows, the panel scrolls. The section itself should not become a new scroll region.

## Interaction Model

### Source selection

- selecting a source updates center and right panels immediately
- source selection state is the main workspace state

### Testing

- testing from the right panel always targets the active source
- the latest test result replaces the previous preview in place
- persisted results remain separate from transient preview

### Results

- the right panel shows a compact recent-results view
- if deeper exploration is needed, the full results view can still open as a dedicated mode or route later

### Saving

- source config changes are saved from the center panel
- testing should continue to support unsaved draft config for the active source

## Component Boundaries

`EnrichmentTab.tsx` must be decomposed.

Target extraction:

- `EnrichmentSummaryBar`
- `SourceSidebar`
- `ActiveSourceHeader`
- `SourceConfigPanel`
- `InspectorPanel`
- `PreviewPanel`
- `RecentResultsPanel`

`ApiEnrichmentConfig.tsx` remains the source editor but will be hosted inside `SourceConfigPanel` instead of continuing to own layout behavior directly.

## Technical Direction

### Use

- `ResizablePanelGroup`
- `ResizablePanel`
- `ResizableHandle`
- `Collapsible` or accordion primitives for config sections
- one `ScrollArea` or one native scroll root per panel

### Avoid

- CSS grid layouts that lock widths too early
- mixed scroll strategies in the same panel
- provider-specific layout branches where a structural component would be enough

## Refactor Plan

Implementation should happen in phases.

### Phase 1

- extract structural components without changing behavior too much
- isolate summary bar, source list, config pane, inspector pane

### Phase 2

- introduce `ResizablePanelGroup`
- move to three-panel structure with one scroll root per panel

### Phase 3

- replace current inline config layout with collapsible sections
- simplify preview/results rendering inside the inspector

### Phase 4

- add the medium-width fallback to two columns + tabs
- refine sizing defaults and breakpoint behavior

## Success Criteria

The redesign is successful if:

- no nested scroll behavior is needed for normal use
- the active source can be configured and tested without context loss
- the workspace remains readable on a standard desktop width
- the right panel helps inspection instead of becoming another cluttered workspace
- `EnrichmentTab.tsx` becomes structurally smaller and easier to reason about

## Out of Scope

- changing backend enrichment APIs
- redesigning the quick sheet mode in the same pass
- adding new enrichment providers
- changing the meaning of provider-specific result blocks
