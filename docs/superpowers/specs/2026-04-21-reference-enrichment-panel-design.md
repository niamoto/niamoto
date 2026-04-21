# Reference Enrichment Panel Design

## Summary

Add a new enrichment-oriented content widget to Niamoto so users can exploit reference enrichment data without manually knowing `extra_data.api_enrichment.sources.*` field paths.

The design introduces a new transformer-widget pair:

- `reference_enrichment_profile`
- `enrichment_panel`

The product intent is to keep `info_grid` simple and editorial, while adding a richer widget that can be suggested automatically, configured with source-aware defaults, and refined through sections and fields rather than raw path editing.

The recommended user experience is:

- users open `Add widget`
- Niamoto suggests one enrichment panel per detected enrichment source
- each suggestion starts as a compact, useful panel for one source
- users can then refine the panel by removing sections, adding fields, or mixing fields from other sources if they want

This preserves a simple entry point while supporting more advanced composition later in the editing flow.

## Problem Statement

Reference enrichment is now functional and can store structured summaries under `extra_data.api_enrichment.sources.*`, but the current collection configuration workflow does not make that data easy to use.

Today, users typically need to:

- know that enrichment data lives in `extra_data`
- know the exact provider path to the desired field
- manually configure `info_grid.items[].source`
- understand provider-specific field names that are not obvious from the content UI

This creates several product problems:

- enrichment is technically available but practically hard to exploit
- `info_grid` asks users to think in storage paths rather than display concepts
- provider-specific structures leak into collection editing
- the add-widget suggestion flow cannot currently surface a coherent enrichment profile
- users who want only a few highlighted facts and users who want a more complete enrichment profile are forced into the same simple widget model

The core design problem is not enrichment persistence. It is the missing layer between stored enrichment payloads and usable collection widgets.

## Goals

- Let users add an enrichment-driven widget without typing `extra_data.*` paths manually
- Keep `info_grid` simple and focused on short editorial selections
- Provide automatic widget suggestions for enrichment content in the existing `Add widget` flow
- Start from a single-source default suggestion, because it is easier to understand and explain
- Allow later multi-source composition inside the widget editor
- Keep the visual structure predictable across sources
- Support generic fallback behavior for unknown or custom sources
- Use compact default rendering with a short summary and collapsible details
- Keep preview and export behavior aligned

## Non-Goals

- Turn `info_grid` into a full enrichment browser
- Expose full raw provider payloads directly in the default widget experience
- Build provider-specific custom widgets for every source in the first iteration
- Add semantic deduplication across providers in V1
- Create a new standalone collection configuration flow just for enrichment
- Replace the existing enrichment workspace or quick panel UX

## Design Principles

- Keep entry simple, allow refinement later
- Separate editorial widgets from enrichment profile widgets
- Preserve source provenance at the field level
- Prefer stable normalized display structures over direct raw payload rendering
- Make unknown sources usable through fallback heuristics
- Avoid exposing internal storage paths in the default UI
- Keep suggestion logic strict enough to avoid noisy low-value panels
- Reuse the existing widget suggestion, preview, and editing flow where possible

## Proposed Product Shape

### Two Distinct Widget Roles

The design keeps two complementary widget families.

`info_grid` remains:

- short
- manual
- editorial
- ideal for 3 to 8 curated facts

`enrichment_panel` becomes:

- profile-oriented
- suggestion-friendly
- source-aware
- capable of rendering a compact summary plus optional detail sections

This separation is important. If `info_grid` absorbs enrichment profile behavior, it stops being simple and becomes a generic catch-all widget.

### Entry Point: Add Widget Suggestions

The `Add widget` flow remains the main entry point.

When Niamoto detects exploitable enrichment data for a reference, it should suggest one `enrichment_panel` per source, for example:

- `GBIF profile`
- `Endemia profile`
- `TAXREF profile`
- `Custom source profile`

Each suggested panel initially targets one source only.

This keeps the suggestion understandable:

- clear provenance
- clear scope
- easy to remove
- easy to preview

### Advanced Composition After Addition

Once added, an enrichment panel may evolve beyond its original source.

The editor should allow:

- removing sections
- adding sections
- removing fields
- adding fields from the original source
- adding fields from other sources
- renaming labels
- reordering sections and items

This means the product model is:

- single-source by default
- multi-source possible after editing

This matches the need for a simple starting point without blocking richer compositions.

### Default Panel Anatomy

The default `enrichment_panel` should render:

- a compact summary of 3 to 6 facts at the top
- 2 to 4 sections visible by default at most
- additional sections as collapsible blocks

This makes the widget useful immediately without becoming a large undifferentiated data dump.

Recommended common sections:

- `Highlights`
- `Links`
- `Media`
- `Details`
- `Provenance`

Profiles may choose which of these exist, but the overall structure should stay familiar.

## Why Not Extend Info Grid

There are three broad options:

1. extend `info_grid`
2. create a source-bound enrichment widget
3. create an enrichment widget with source-based suggestions and multi-source editing

The recommended design is option `3`.

Extending `info_grid` too far would force one widget to handle:

- hand-picked editorial metrics
- provider payload exploration
- section-level grouping
- source-aware defaults
- advanced fallback logic

That would increase configuration complexity and blur the mental model.

The new widget keeps the product model clearer:

- `info_grid` for concise editorial display
- `enrichment_panel` for structured enrichment display

## Architecture

### Recommended Pair

The design introduces:

- transformer: `reference_enrichment_profile`
- widget: `enrichment_panel`

The transformer is responsible for:

- reading enrichment data from `extra_data.api_enrichment.sources.*`
- applying known source profiles
- applying generic fallback heuristics when no profile exists
- producing a normalized intermediate structure

The widget is responsible for:

- rendering the normalized profile
- handling compact summary display
- handling collapsible sections
- rendering supported field formats consistently

This separation is recommended because it keeps provider-specific interpretation out of the widget and makes preview behavior more stable.

### Why Not Render Directly From Raw Enrichment Payloads

Direct raw rendering would make the widget responsible for:

- provider-specific structures
- nested payload traversal
- fallback grouping
- label humanization
- type guessing
- format inference

That would make the widget brittle and hard to test.

Normalizing first through a transformer has several advantages:

- better reuse in preview and export
- stable rendering contract
- easier test boundaries
- simpler widget editor model

## Transformer Contract

### Input

The transformer receives a configuration that describes which summary items and sections to build from enrichment sources.

Recommended shape:

```yaml
plugin: reference_enrichment_profile
params:
  source: taxons
  summary_items:
    - source_id: gbif
      path: match.canonical_name
      label: Canonical name
      format: text
    - source_id: gbif
      path: occurrence_summary.occurrence_count
      label: Occurrences
      format: number
  sections:
    - id: gbif_identity
      title: Identity
      source_id: gbif
      collapsed: false
      items:
        - path: match.scientific_name
          label: Scientific name
        - path: match.rank
          label: Rank
          format: badge
    - id: gbif_links
      title: Links
      source_id: gbif
      collapsed: true
      items:
        - path: links.species
          label: GBIF page
          format: link
```

Paths are relative to the selected source payload under `extra_data.api_enrichment.sources.<source_id>.data`.

At configuration level:

- `summary_items` always declare their own `source_id`
- a section may declare a default `source_id`
- items inside a section may inherit that section-level `source_id`
- an item may override the section-level `source_id` when the panel becomes multi-source

Each item keeps explicit provenance through:

- `source_id`
- `path`
- `label`
- optional `format`

This makes single-source and multi-source cases use the same model.

### Output

The transformer should output a normalized structure that the widget can render without knowing provider internals.

Recommended shape:

```json
{
  "summary": [
    {
      "id": "gbif_occurrences",
      "source_id": "gbif",
      "label": "Occurrences",
      "value": 324,
      "format": "number"
    }
  ],
  "sections": [
    {
      "id": "gbif_identity",
      "title": "Identity",
      "source_id": "gbif",
      "collapsed": false,
      "items": [
        {
          "id": "gbif_rank",
          "source_id": "gbif",
          "label": "Rank",
          "value": "species",
          "format": "badge"
        }
      ]
    }
  ],
  "sources": [
    {
      "id": "gbif",
      "label": "GBIF"
    }
  ],
  "meta": {
    "visible_sections": 2,
    "has_hidden_items": false
  }
}
```

This contract should be treated as the stable display model.

## Widget Contract

The widget should only receive the normalized profile data.

It should not be responsible for:

- inspecting `extra_data` directly
- discovering provider schemas
- classifying nested raw objects
- reconstructing sections on the fly

It should be responsible for rendering:

- summary items
- sections
- empty states
- collapsible groups
- supported formats

Recommended supported formats in V1:

- `text`
- `number`
- `badge`
- `link`
- `image`
- `list`

Additional formats can be added later without changing the overall model.

## Source Profiles And Generic Fallback

### Known Source Profiles

The transformer should support a small registry of known source profiles.

A profile defines:

- preferred summary items
- preferred section layout
- preferred human labels
- preferred formats
- field priority rules
- exclusion rules

Examples of profile intent:

- `GBIF`: identity, occurrences, media, links, provenance
- `Endemia`: endemicity, status, media, links
- `TAXREF`: rank, accepted status, synonymy, habitats, links

The goal is not fully custom rendering per provider. The goal is better defaults while keeping the visible structure uniform.

### Generic Fallback

Unknown and custom sources still need to produce useful panels.

The generic fallback should:

- detect scalar values
- detect booleans suitable for badges
- detect URLs suitable for links
- detect image-like structures
- detect short lists suitable for compact list display
- ignore technical metadata and noisy deep objects by default

The generic fallback should then build:

- a short `Highlights` summary
- a minimal set of generic sections
- stable labels based on humanized paths

Recommended generic sections:

- `Highlights`
- `Links`
- `Media`
- `Details`
- `Provenance`

This keeps the fallback usable without inventing provider-specific UX.

## Suggestion Rules

### When To Suggest An Enrichment Panel

The suggestion engine should create `enrichment_panel` suggestions only when a source has enough useful display content.

Recommended high-level rule:

- suggest when there are enough displayable fields to create a compact summary and at least one meaningful section

Useful display content should prioritize:

- stable scalars
- counts
- links
- booleans or statuses
- image references
- short lists

The suggestion engine should deprioritize or exclude:

- empty fields
- highly technical metadata
- large raw nested payloads
- debug structures
- repeated provider plumbing keys

### Suggestion Output

Each suggestion should already contain:

- a `template_id`
- transformer config for `reference_enrichment_profile`
- widget plugin `enrichment_panel`
- widget params if needed
- human-readable name and description
- confidence score

This should fit the existing suggestion pipeline, which already carries transformer config plus widget override data.

### Suggestion Priority

Known profiles should receive higher confidence when their expected structures are present.

Generic fallback suggestions should still be available, but with lower confidence than a well-matched known profile.

This keeps the gallery helpful without hiding custom-source usefulness.

## Editing Model

### Primary Editing Units

The editor should expose two levels:

1. sections
2. fields within sections

This is the recommended default editing model because it maps well to the intended widget structure.

### Section Operations

Users should be able to:

- add a section
- remove a section
- rename a section
- reorder sections
- collapse a section by default
- hide a section without deleting it

### Field Operations

Within a section, users should be able to:

- add a field
- remove a field
- reorder fields
- rename the label
- override the display format

### Source Selection In The Editor

When adding a field, the default UI should not expose raw storage paths first.

Recommended interaction:

1. choose a source
2. choose a target section
3. choose from suggested fields with human labels and inferred formats

Raw path editing may exist in an advanced mode, but it should not be the default experience.

## Multi-Source Behavior

The product should remain single-source by default at suggestion time, but it should support multi-source composition after editing.

This means:

- a panel can start from `GBIF profile`
- the user can later add one `Endemia` field to `Highlights`
- the same panel can mix sources as needed

The normalized model supports this because each item keeps its own `source_id`.

This approach avoids the UX ambiguity of a multi-source suggestion while preserving flexibility later.

## Rendering Behavior

### Default Density

The widget should remain compact by default.

Recommended soft limits:

- summary: 3 to 6 items
- visible sections: 2 to 4
- additional sections: collapsed

If configuration exceeds that density, the editor may show a lightweight warning, but the system should still render the widget.

### Empty And Partial States

The widget should degrade gracefully.

Rules:

- if a field is missing, skip it silently
- if all items in a section are missing, hide the section
- if a known profile becomes too sparse, fall back to generic grouping instead of erroring
- if no section has content, render a short empty state instead of a broken widget

This is especially important for heterogeneous and partially successful enrichment runs.

## Preview And Export Alignment

Preview should use the same conceptual path as export:

- resolve enrichment data
- run `reference_enrichment_profile`
- render with `enrichment_panel`

The preview engine should not use a different interpretation model than export.

This avoids a class of regressions where:

- the widget looks correct in the GUI preview
- but renders differently in the final page

The normalized transformer output is the key mechanism that makes this alignment practical.

## Configuration Persistence

The suggested widget should integrate with the existing transform and export configuration pattern.

Recommended storage pattern:

- `transform.yml` stores a `widgets_data` entry using `reference_enrichment_profile`
- `export.yml` stores a widget entry using `enrichment_panel`

This follows the existing template suggestion flow, where one suggestion can generate both the transformer-side and widget-side config.

The widget suggestion should remain compatible with:

- `template_id`
- `widget_plugin`
- `widget_params`
- `export_override`

## V1 Scope

Version 1 should include:

- new widget `enrichment_panel`
- new transformer `reference_enrichment_profile`
- one suggestion per exploitable enrichment source
- known source profiles for a small set of already stabilized providers
- generic fallback for unknown and custom sources
- compact summary plus collapsible sections
- editor support for section and field customization
- multi-source composition in the editor

V1 should explicitly exclude:

- raw provider JSON editing as the default mode
- advanced cross-source semantic merging
- provider-specific fully custom layouts
- sophisticated deduplication across sources
- automatic merging of several source suggestions into one suggestion card

## Testing Strategy

### Suggestion Tests

Add tests for:

- known-source suggestion generation
- generic-source fallback suggestion generation
- low-signal sources that should not produce a suggestion
- confidence ordering between known profiles and generic fallback

### Transformer Tests

Add tests for:

- normalization of a known source
- fallback grouping for an unknown source
- mixed-source summaries and sections
- missing field handling
- hidden empty sections

### Widget Tests

Add tests for:

- summary rendering
- collapsible section rendering
- supported field formats
- compact empty state
- partial data rendering

### GUI Tests

Add tests for:

- enrichment panel visibility in `Add widget`
- inline preview behavior
- section-level editing
- field-level editing
- persistence of updated widget config

## Risks And Trade-Offs

### Main Risk

The main risk is creating a configuration model that becomes too powerful and therefore too complex to understand.

The design mitigates that by:

- keeping suggestion-time scope single-source
- keeping `info_grid` separate
- making sections the primary organizing unit
- hiding raw paths in the default editor flow

### Secondary Risk

The second risk is weak generic fallback quality for unknown providers.

The design mitigates that by:

- keeping fallback structure simple
- restricting default formats to a small stable set
- allowing known profile overrides where data quality matters most

## Decision Summary

The recommended design is:

- keep `info_grid` as a short editorial widget
- add `reference_enrichment_profile` to normalize enrichment data
- add `enrichment_panel` to render normalized enrichment profiles
- suggest one panel per source in the existing widget gallery
- allow later multi-source editing inside the widget editor
- use a small registry of known source profiles plus a generic fallback

This provides a coherent and ergonomic way to exploit enrichment data while staying aligned with Niamoto's existing widget suggestion and configuration model.
