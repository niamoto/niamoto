# GN-Assisted TAXREF Rich Enrichment Design

## Summary

Add a richer TAXREF integration to Niamoto as a single enrichment source in the existing multi-source enrichment workflow, with Global Names Parser and Global Names Verifier used as an internal name-resolution layer.

The user-facing model stays simple:

- one source named `TAXREF`
- one workspace entry in the enrichment UI
- one quick-panel summary

Behind that source, TAXREF is treated as a structured enrichment pipeline instead of a flat generic lookup, and Global Names tools improve name normalization and matching reliability without appearing as a separate UI source.

The design goal is to produce a stable, reusable TAXREF summary in `extra_data`, while keeping heavy raw payloads and long lists available on demand in preview and results views rather than storing them permanently.

## Problem Statement

Niamoto now supports richer provider profiles such as `GBIF Rich` and `Tropicos Rich`, but it still lacks a strong French and overseas taxonomic authority source. TAXREF is a strong candidate because it can provide taxonomic classification, statuses, distributions, habitats, traits, and references in a way that is directly useful to biodiversity workflows.

This creates four product problems today:

- users do not have a structured French and overseas authority source in the enrichment workspace
- name quality issues still reduce match reliability across providers
- the current generic mapping model is a poor fit for a provider whose value lives across multiple data blocks
- there is no shared name-resolution layer that can later improve multiple taxonomic providers

Niamoto needs a `TAXREF Rich` integration that demonstrates real value:

- better scientific-name normalization
- clearer taxonomic authority and statuses
- territorial distribution context
- ecological context through traits and habitats
- references and provenance
- inspectable resolution steps in the GUI

## Goals

- Keep TAXREF as a single enrichment source in the UI
- Use Global Names tools as an internal pre-resolution layer, not as a separate visible source
- Produce a richer TAXREF result than a flat generic lookup
- Store a concise, reusable TAXREF summary in `extra_data`
- Expose raw and sectional preview data in the workspace to help users understand both name resolution and TAXREF results
- Preserve the current multi-source enrichment model and quick panel / workspace split
- Establish a reusable pattern for GN-assisted structured providers

## Non-Goals

- Add a new visible source named `Global Names`
- Rewrite the enrichment runtime around provider-specific plugins in this iteration
- Store full raw TAXREF payloads, full references, or full habitat and trait lists in `extra_data`
- Build a dedicated visual explorer for TAXREF in the first pass
- Replace existing GBIF or Tropicos integrations

## Design Principles

- Keep the user-facing source model simple
- Treat TAXREF as a structured source, not as a larger flat mapping
- Store summaries permanently, fetch heavy detail on demand
- Prefer partial success over all-or-nothing failure
- Make name resolution inspectable without turning it into a full UI source
- Make provenance explicit
- Keep the GN layer reusable by future providers

## Proposed Product Shape

### One Rich TAXREF Source

TAXREF remains a single source in `entities.references.<ref>.enrichment`.

Example:

```yaml
- id: taxref
  label: TAXREF
  plugin: api_taxonomy_enricher
  enabled: true
  config:
    profile: taxref_rich
    use_name_verifier: true
    verifier_preferred_sources:
      - TAXREF
      - GBIF
      - Tropicos
      - IPNI
    include_statuses: true
    include_distributions: true
    include_traits: true
    include_habitats: true
    include_references: true
```

The UI still presents one source card, one source editor, one test surface, and one result group.

### Internal Name-Resolution Layer

Global Names Parser and Global Names Verifier are treated as internal helpers:

- not visible in the source list
- not independently executable by the user
- inspectable in preview and provenance
- reusable by future providers such as `GBIF`, `Tropicos`, and `Catalogue of Life`

### Structured Result Model

The TAXREF source result is internally organized into eight blocks:

- `name_resolution`
- `match`
- `taxonomy`
- `statuses`
- `distribution_summary`
- `traits`
- `habitats`
- `references`

This is the key product change. TAXREF is no longer treated as one generic response mapped into a flat table.

## Data Model

TAXREF summaries are stored under:

`extra_data.api_enrichment.sources.taxref.data`

Recommended structure:

```json
{
  "name_resolution": {
    "submitted_name": "Acacia spirorbis",
    "normalized_name": "Acacia spirorbis Labill.",
    "resolved_name": "Acacia spirorbis Labill.",
    "selected_source": "TAXREF",
    "confidence": 0.98,
    "corrected": true,
    "alternatives": [
      "Acacia spirorbis"
    ]
  },
  "match": {
    "taxref_id": "123456",
    "scientific_name": "Acacia spirorbis",
    "canonical_name": "Acacia spirorbis",
    "authorship": "Labill.",
    "rank": "Species",
    "status": "accepted",
    "matched_name": "Acacia spirorbis"
  },
  "taxonomy": {
    "kingdom": "Plantae",
    "phylum": "Tracheophyta",
    "class": "Magnoliopsida",
    "order": "Fabales",
    "family": "Fabaceae",
    "genus": "Acacia",
    "species": "Acacia spirorbis",
    "parent_chain": []
  },
  "statuses": {
    "items": [],
    "summary": []
  },
  "distribution_summary": {
    "territories": [],
    "territories_count": 0
  },
  "traits": {
    "items": [],
    "summary": []
  },
  "habitats": {
    "items": [],
    "summary": []
  },
  "references": {
    "references_count": 0,
    "items": []
  },
  "links": {
    "record": null
  },
  "provenance": {
    "profile": "taxref_rich",
    "profile_version": "taxref-rich-v1",
    "used_name_verifier": true,
    "endpoints": [],
    "query": "Acacia spirorbis"
  }
}
```

`taxref_id` must be stored and transported as a string.

### What Is Stored Permanently

- concise name-resolution summary
- taxonomic match summary
- normalized classification summary
- compact statuses summary
- compact territorial distribution summary
- compact traits summary
- compact habitats summary
- compact references summary
- external links and provenance metadata

### What Is Not Stored Permanently

- full raw TAXREF payloads
- complete references, habitat lists, or trait lists
- complete GN resolution payloads
- request-by-request debug payloads

These remain available on demand through preview and detailed results surfaces.

## Runtime Pipeline

The TAXREF source runs as a two-layer pipeline with partial success support.

### Layer 1: Name Resolution

#### Step 1: Parse

Use Global Names Parser to normalize the submitted scientific name and extract useful structure when available.

This step improves:

- authorship handling
- rank noise reduction
- consistent matching input

If parsing fails, the runtime continues with the original submitted name.

#### Step 2: Verify

Use Global Names Verifier to propose a best taxonomic candidate, preferring TAXREF and then other configured taxonomic sources.

This step produces:

- normalized working name
- selected source
- confidence
- alternative candidates
- correction or ambiguity hints

If verification fails or returns no useful candidate, the runtime continues with the original or parsed name instead of failing hard.

### Layer 2: TAXREF Enrichment

#### Step 3: Match

Use the best available working name from the name-resolution layer to query TAXREF and identify the working record.

This step is mandatory and provides:

- TAXREF identifier
- canonical and authored name
- rank
- accepted status

If no usable match is found, the enrichment stops with a clear `no_match` outcome, not with a generic failure.

#### Step 4: Taxonomy

Hydrate the taxonomic classification and parent context for the matched record.

This step fills the `taxonomy` block and enriches `links`.

#### Step 5: Statuses

Retrieve structured status information when available, such as:

- conservation or threat-related statuses
- regulatory or protection statuses
- other normalized status families exposed by TAXREF

#### Step 6: Distribution Summary

Build a compact territorial distribution summary optimized for Niamoto, including:

- territory labels
- territory counts
- a small summary suitable for quick-panel display

#### Step 7: Traits

Retrieve a compact set of ecological or descriptive traits when available and normalize them for durable storage.

#### Step 8: Habitats

Retrieve a compact habitat summary when available and normalize it for durable storage.

#### Step 9: References

Build a compact references block including:

- total reference count
- a short selected subset for durable storage

### Partial Success Rules

- `match` must succeed for the source to be usable
- `taxonomy`, `statuses`, `distributions`, `traits`, `habitats`, and `references` are best-effort
- a source with a valid match and one or more missing secondary blocks is considered `partial`, not `failed`
- source status in UI should distinguish:
  - `no match`
  - `partial`
  - `complete`
  - `provider error`

## Backend Design

### Structured Profile in the Generic Loader

Add `taxref_rich` to the structured profiles supported by `api_taxonomy_enricher`.

This keeps the current architecture consistent with:

- `gbif_rich`
- `tropicos_rich`

### Name Resolution as an Internal Service

The Global Names layer should be implemented as a shared helper that:

- accepts a submitted scientific name
- optionally parses it first
- optionally verifies it against preferred sources
- returns a normalized resolution summary

This helper must be reusable by future structured profiles.

### TAXREF-Rich Result Builder

The TAXREF profile should:

- orchestrate TAXREF calls after name resolution
- build the durable summary structure
- retain grouped raw sections for preview
- expose provider and resolution provenance

### Legacy Compatibility

Legacy TAXREF-like generic configurations may continue to load, but the structured TAXREF preset should become the preferred path.

No destructive migration is required. New writes should prefer the structured profile.

## API Contract Changes

The existing enrichment endpoints should continue to work with TAXREF as another structured source.

Preview responses should include:

- `mapped_data`
- `raw_data`
- provider-specific grouped sections
- `name_resolution` summary when available

Results responses should include:

- `source_id`
- structured `data`
- status and provenance

No new top-level enrichment endpoint family is required for this iteration.

## UI Design

### Configuration

Add a `TAXREF` preset to quick setup.

The structured TAXREF profile should expose:

- `use name verifier`
- `include statuses`
- `include distributions`
- `include traits`
- `include habitats`
- `include references`

The manual response-mapping editor should be hidden or reduced for this structured profile.

### Tester View

The `Tester l'API` view should render TAXREF as sectional blocks:

- `Name Resolution`
- `Match`
- `Taxonomy`
- `Statuses`
- `Distribution`
- `Traits`
- `Habitats`
- `References`

The existing `Raw API Response` view should remain available.

### Results View

The `Résultats` view should show the same sections in a more compact durable-summary form.

`Name Resolution` should remain visible but compact, because it explains why a given match was selected.

### Quick Panel

The quick panel should show a compact summary such as:

- selected match
- primary status
- territories count
- traits or habitats presence

It may also show a subtle indicator when the submitted name was corrected before matching.

## Error Handling

- Parser failure must not block TAXREF lookup
- Verifier failure must not block TAXREF lookup
- TAXREF `no_match` must be explicit
- Partial provider failures should degrade into `partial` results, not opaque failures
- Preview should clearly separate:
  - submitted name
  - normalized name
  - matched TAXREF record

## Testing Strategy

### Backend

- unit tests for GN parsing and verification fallback behavior
- unit tests for `taxref_rich` structured result building
- tests for partial success when statuses, habitats, or references fail
- tests for preview payload shape including `name_resolution`
- compatibility tests for legacy configurations

### Frontend

- preset selection and normalization behavior for `TAXREF`
- config toggles for structured TAXREF options
- tester rendering of all TAXREF blocks
- results rendering of TAXREF summaries
- quick-panel compact summary display

### Validation

- targeted pytest modules for loader, config models, and enrichment service
- `pnpm build` for the frontend

## Rollout Strategy

Implementation should proceed in this order:

1. add GN helper integration
2. add `taxref_rich` backend profile
3. expose TAXREF structured config in UI
4. render preview and results blocks
5. validate fallback and partial-success behavior

This keeps the risk concentrated in one new structured provider while laying groundwork for future GN-assisted providers.
