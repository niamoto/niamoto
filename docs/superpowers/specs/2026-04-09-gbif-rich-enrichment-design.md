# GBIF Rich Enrichment Design

## Summary

Add a richer GBIF integration to Niamoto as a single enrichment source in the existing multi-source enrichment workflow.

The user-facing model stays simple:

- one source named `GBIF`
- one workspace entry in the enrichment UI
- one quick-panel summary

Behind that source, GBIF is treated as a structured enrichment pipeline instead of a flat one-request mapping. The integration should prioritize geographic evidence and observation context for the 2026 GBIF challenge while still returning a usable taxonomic match summary.

The design goal is to produce a stable, reusable enrichment summary in `extra_data`, while keeping heavy raw payloads and long lists available on demand in preview and results views rather than storing them permanently.

## Problem Statement

The current GBIF preset behaves like a generic lookup over `species/match` and only returns a small flat subset of fields. Compared with Endemia, the result looks poor even though GBIF offers a much broader API surface.

This creates three product problems:

- GBIF looks weak in the enrichment UI even when it can provide valuable biodiversity evidence
- the current generic mapping model is better suited to simple APIs than to a modular source such as GBIF
- the enriched data model does not yet distinguish between a durable summary and heavy exploratory detail

For the challenge context, Niamoto needs a GBIF integration that demonstrates real value:

- taxonomic interpretation
- occurrence-based evidence
- media and provenance
- clear, inspectable summaries in the GUI

## Goals

- Keep GBIF as a single enrichment source in the UI
- Produce a richer GBIF result than the current flat `species/match` mapping
- Store a concise, reusable GBIF summary in `extra_data`
- Expose raw and sectional preview data in the workspace to help users understand what GBIF returned
- Prioritize occurrence and distribution evidence over purely taxonomic lookup
- Preserve the current multi-source enrichment model and quick panel / workspace split

## Non-Goals

- Rebuild the entire enrichment architecture around provider-specific plugins in this iteration
- Store full occurrence lists, full bibliographies, or full media galleries in `extra_data`
- Turn GBIF into multiple separate UI sources such as `GBIF Taxonomy` and `GBIF Media`
- Replace Endemia or other API presets
- Add map rendering in the first implementation pass

## Design Principles

- Keep the user-facing source model simple
- Treat GBIF as a structured source, not as a bigger flat mapping
- Store summaries permanently, fetch heavy detail on demand
- Prefer partial success over all-or-nothing failure
- Make provenance explicit
- Keep the design generic enough to inform future structured presets

## Proposed Product Shape

### One Rich GBIF Source

GBIF remains a single source in `entities.references.<ref>.enrichment`.

Example:

```yaml
- id: gbif
  label: GBIF
  plugin: api_taxonomy_enricher
  enabled: true
  config:
    profile: gbif_rich
    taxonomy_source: col_xr
    include_taxonomy: true
    include_occurrences: true
    include_media: true
    media_limit: 3
```

The UI still presents one source card, one source editor, one test surface, and one result group.

### Structured Result Model

The GBIF source result is internally organized into four blocks:

- `match`
- `taxonomy`
- `occurrence_summary`
- `media_summary`

This is the key product change. GBIF is no longer treated as one response mapped into a flat table.

## Data Model

GBIF summaries are stored under:

`extra_data.api_enrichment.sources.gbif.data`

Recommended structure:

```json
{
  "match": {
    "usage_key": "6",
    "scientific_name": "Plantae",
    "canonical_name": "Plantae",
    "rank": "KINGDOM",
    "status": "ACCEPTED",
    "confidence": 98,
    "match_type": "EXACT",
    "taxonomy_source": "COL_XR"
  },
  "taxonomy": {
    "kingdom": "Plantae",
    "phylum": null,
    "class": null,
    "order": null,
    "family": null,
    "genus": null,
    "species": null,
    "synonyms_count": 0,
    "vernacular_names": [],
    "iucn_category": null
  },
  "occurrence_summary": {
    "occurrence_count": 0,
    "countries": [],
    "datasets_count": 0,
    "basis_of_record": []
  },
  "media_summary": {
    "media_count": 0,
    "items": []
  },
  "links": {
    "species": "https://www.gbif.org/species/6",
    "occurrences": "https://www.gbif.org/occurrence/search?taxon_key=6"
  },
  "provenance": {
    "taxonomy_source": "COL_XR",
    "endpoints": [
      "v2/species/match",
      "v1/species/{usageKey}",
      "v1/occurrence/search",
      "v1/species/{usageKey}/media"
    ],
    "enriched_at": "2026-04-09T00:00:00Z",
    "profile_version": "gbif-rich-v1"
  }
}
```

`usage_key` must be stored and transported as a string. The implementation must not assume that GBIF or checklist identifiers are always numeric.

### What Is Stored Permanently

- taxonomic match summary
- normalized classification summary
- compact occurrence/distribution summary
- compact media summary
- external links and provenance metadata

### What Is Not Stored Permanently

- full raw GBIF JSON payloads
- full occurrence records
- full synonym, description, reference, or media lists
- request-by-request debug payloads

These remain available on demand through preview and detailed results surfaces.

## Runtime Pipeline

The GBIF source runs as a four-step pipeline with partial success support.

### Step 1: Match

Call `v2/species/match` using the configured taxonomic interpretation source, with `COL XR` as the default.

This step is mandatory and provides:

- interpreted taxon identity
- accepted or matched name
- confidence
- rank and status
- key and taxonomy provenance

If no reliable match is found, the enrichment should stop with a clear `no_match` outcome, not with a generic failure.

### Step 2: Taxonomy

Using the resolved GBIF identifier, hydrate the taxon profile through species endpoints such as:

- taxon detail
- vernacular names
- synonyms
- profiles
- distributions
- IUCN category when available

This step fills the `taxonomy` block and enriches `links`.

### Step 3: Occurrence Summary

Use occurrence search to produce a summary optimized for Niamoto, including:

- total occurrence count
- country coverage
- dataset count
- basis-of-record distribution
- optional sample evidence rows for preview only

This is the main value block for the challenge because it turns GBIF into an observation-backed enrichment rather than a name lookup.

### Step 4: Media Summary

Retrieve a small, curated media subset with:

- thumbnail URL
- original URL when available
- creator or attribution
- source link

Only the compact summary is stored. Larger galleries remain preview-only.

### Partial Success Rules

- `match` must succeed for the source to be usable
- `taxonomy`, `occurrences`, and `media` are best-effort
- a source with a valid match and one missing secondary block is considered `partial`, not `failed`
- source status in UI should distinguish:
  - `no match`
  - `partial`
  - `complete`
  - `rate limited`
  - `provider error`

## Backend Design

### Configuration Model

Do not introduce a separate top-level source in the UI for each GBIF subdomain.

Instead, extend the source configuration with a structured profile concept:

- `profile: gbif_rich`
- optional block toggles:
  - `include_taxonomy`
  - `include_occurrences`
  - `include_media`
- `taxonomy_source`
- `media_limit`

This keeps the current multi-source enrichment model intact while allowing richer provider behavior than simple `response_mapping`.

### Runtime Strategy

The existing `api_taxonomy_enricher` should remain the public plugin entry point for this iteration, but GBIF should no longer be implemented as a flat preset only.

Recommended internal approach:

- keep the source contract generic
- add a structured profile runner for `gbif_rich`
- let the profile runner orchestrate multiple GBIF calls and normalize the summary blocks
- continue to expose raw payloads and mapped summaries to preview surfaces

This avoids introducing a dedicated `gbif_enricher` plugin immediately while still acknowledging that GBIF needs richer behavior than the current generic mapper.

### API Contract Changes

Preview and results payloads for structured sources should expose both:

- `summary` blocks for normal display
- `raw` payloads for inspection

For GBIF preview specifically, the frontend should receive:

- `match`
- `taxonomy`
- `occurrence_summary`
- `media_summary`
- `raw_data`
- per-block status or error information

## UI Design

### Configuration

The workspace should expose a `GBIF Rich` preset with a compact set of provider-specific options:

- taxonomy source, defaulting to `COL XR`
- include taxonomy
- include occurrence summary
- include media summary
- media item limit

These options belong in the existing `Configuration` tab for the GBIF source.

### Test API

`Test API` should stop rendering GBIF as a flat key-value table only.

For GBIF, the tester should render four sections:

- `Match`
- `Taxonomy`
- `Occurrences`
- `Media`

It should still preserve the raw payload tab so the user can inspect the complete response shape when needed.

The preview should emphasize summary comprehension over manual mapping.

### Results

The `Results` tab should present the saved enrichment by block:

- match confidence and status
- resolved taxonomic summary
- occurrence evidence summary
- media summary
- provenance and links

If one block failed, the result view should show that block as unavailable without making the whole source look broken.

### Quick Panel

The quick panel should stay compact.

For GBIF, it should show only:

- source state
- last resolved name or status
- one or two evidence badges such as occurrence count or country count
- access to the full workspace for detail

## Error Handling

The design should distinguish between provider and interpretation states instead of collapsing them into one generic error.

Important cases:

- no match
- low-confidence match
- accepted match with missing secondary endpoints
- occurrence API temporary failure
- media API temporary failure
- provider rate limiting
- malformed or unexpected payload

Errors should be stored and surfaced per block where possible.

The source should remain usable when only secondary blocks fail.

## Testing Strategy

### Backend

Add targeted tests for:

- `gbif_rich` config validation
- match parsing including non-numeric keys
- no-match and low-confidence outcomes
- taxonomy normalization
- occurrence summary aggregation
- media summary truncation
- partial success behavior
- preview payload shape including raw payload fallback

### Frontend

At minimum:

- `pnpm build`
- workspace rendering for GBIF structured preview
- quick panel rendering with compact GBIF summary
- result rendering with partial block failure states

### Integration

Use the subset test instance to validate:

- one rich GBIF source beside Endemia
- preview behavior with real GBIF payloads
- persistence of the summary structure in `extra_data`
- UI behavior when GBIF returns sparse results for high-level taxa

## Rollout Notes

This design is intentionally scoped as a product-quality improvement to the existing enrichment system, not as a full provider framework rewrite.

If GBIF proves strategic beyond this iteration, a later step can extract the structured provider runtime into a dedicated enrichment-provider layer or a dedicated `gbif_enricher` plugin. That is explicitly deferred.

## References

- Official GBIF API reference
- Official GBIF taxonomy interpretation documentation
- Official GBIF occurrence image API documentation
- Official GBIF downloads documentation
- Official 2026 GBIF Ebbe Nielsen Challenge rules
