# Tropicos Rich Enrichment Design

## Summary

Add a richer Tropicos integration to Niamoto as a single enrichment source in the existing multi-source enrichment workflow.

The user-facing model stays simple:

- one source named `Tropicos`
- one workspace entry in the enrichment UI
- one quick-panel summary

Behind that source, Tropicos is treated as a structured enrichment pipeline instead of a flat `Name/Search` mapping. The integration should prioritize nomenclatural authority, accepted-name resolution, references, distributions, and images while still fitting the current generic enrichment architecture.

The design goal is to produce a stable, reusable Tropicos summary in `extra_data`, while keeping heavy raw payloads and long lists available on demand in preview and results views rather than storing them permanently.

## Problem Statement

The current Tropicos preset behaves like a single-request generic lookup over `Name/Search` and only returns a flat subset of fields. That is not enough for a source that is valuable mainly because it can resolve a matched name into richer nomenclatural, bibliographic, distribution, and media context through additional endpoints.

This creates four product problems:

- Tropicos looks weaker than it is because the UI only reflects the first search response
- users cannot benefit from accepted-name resolution, synonymy, or references without manually stitching requests together
- the current flat mapping model is a poor fit for a provider whose useful data lives behind multiple follow-up endpoints
- the old `tropicos_enricher` path has effectively disappeared from the active architecture, but the current preset does not replace it with an equally capable structured source

Niamoto needs a Tropicos integration that demonstrates real value:

- accepted-name resolution and nomenclatural context
- taxonomic context beyond the search hit
- bibliographic references
- distribution summary
- media summary
- clear, inspectable blocks in the GUI

## Goals

- Keep Tropicos as a single enrichment source in the UI
- Replace the current flat Tropicos preset with a structured `Tropicos Rich` behavior
- Store a concise, reusable Tropicos summary in `extra_data`
- Expose raw and sectional preview data in the workspace to help users understand what Tropicos returned
- Include images and distributions in the first implementation lot
- Preserve the current multi-source enrichment model and quick panel / workspace split
- Provide a migration path from legacy Tropicos configurations toward the generic loader profile

## Non-Goals

- Reintroduce a dedicated `tropicos_enricher` plugin in this iteration
- Store complete reference lists, complete distribution records, or full image galleries in `extra_data`
- Split Tropicos into multiple UI sources such as `Tropicos References` and `Tropicos Media`
- Build a provider-specific visual explorer or map widget in the first pass
- Rewrite the full enrichment runtime around provider-specific plugins

## Design Principles

- Keep the user-facing source model simple
- Treat Tropicos as a structured source, not as a larger flat mapping
- Store summaries permanently, fetch heavy detail on demand
- Prefer partial success over all-or-nothing failure
- Make accepted-name resolution explicit
- Make provenance explicit
- Keep the design generic enough to inform future structured presets

## Proposed Product Shape

### One Rich Tropicos Source

Tropicos remains a single source in `entities.references.<ref>.enrichment`.

Example:

```yaml
- id: tropicos
  label: Tropicos
  plugin: api_taxonomy_enricher
  enabled: true
  config:
    profile: tropicos_rich
    include_references: true
    include_distributions: true
    include_media: true
    media_limit: 3
```

The UI still presents one source card, one source editor, one test surface, and one result group.

### Structured Result Model

The Tropicos source result is internally organized into six blocks:

- `match`
- `nomenclature`
- `taxonomy`
- `references`
- `distribution_summary`
- `media_summary`

This is the key product change. Tropicos is no longer treated as one search response mapped into a flat table.

## Data Model

Tropicos summaries are stored under:

`extra_data.api_enrichment.sources.tropicos.data`

Recommended structure:

```json
{
  "match": {
    "name_id": "25509881",
    "scientific_name": "Poa annua",
    "scientific_name_with_authors": "Poa annua L.",
    "family": "Poaceae",
    "rank": "Sp.",
    "nomenclature_status": "Legitimate",
    "matched_name": "Poa annua"
  },
  "nomenclature": {
    "accepted_name_id": "25509881",
    "accepted_name": "Poa annua",
    "accepted_name_with_authors": "Poa annua L.",
    "synonyms_count": 78,
    "accepted_name_count": 0,
    "selected_synonyms": []
  },
  "taxonomy": {
    "family": "Poaceae",
    "higher_taxa": []
  },
  "references": {
    "references_count": 12,
    "items": []
  },
  "distribution_summary": {
    "distribution_count": 8,
    "countries": [
      "Austria"
    ],
    "regions": [
      "Europe"
    ]
  },
  "media_summary": {
    "media_count": 4,
    "items": []
  },
  "links": {
    "record": "https://www.tropicos.org/name/25509881"
  },
  "provenance": {
    "profile": "tropicos_rich",
    "profile_version": "tropicos-rich-v1",
    "endpoints": [
      "Name/Search",
      "Name/{id}",
      "Name/{id}/AcceptedNames",
      "Name/{id}/Synonyms",
      "Name/{id}/References",
      "Name/{id}/Distributions",
      "Name/{id}/Images"
    ],
    "query": "Poa annua"
  }
}
```

`name_id` must be stored and transported as a string.

### What Is Stored Permanently

- matched name summary
- accepted-name and synonymy summary
- normalized family and higher-taxa summary
- compact reference summary
- compact distribution summary
- compact media summary
- external links and provenance metadata

### What Is Not Stored Permanently

- full raw Tropicos JSON payloads
- complete reference lists
- complete distribution records
- complete image galleries
- request-by-request debug payloads

These remain available on demand through preview and detailed results surfaces.

## Runtime Pipeline

The Tropicos source runs as a six-step pipeline with partial success support.

### Step 1: Match

Call `Name/Search` using `type=exact` by default and the configured taxon name query parameter.

This step is mandatory and provides the candidate list from which the runtime chooses a working `NameId`.

Selection rules:

- prefer an exact normalized `ScientificName` match to the query
- then prefer results that expose a stable `NameId`
- then prefer results with richer core fields such as family and nomenclatural status
- otherwise fall back to the first returned result

If no usable result is found, the enrichment should stop with a clear `no_match` outcome, not with a generic failure.

### Step 2: Summary

Call `Name/{id}` for the selected `NameId`.

This step is mandatory once a match exists and provides the core summary used to build:

- `match`
- part of `nomenclature`
- part of `taxonomy`

### Step 3: Accepted Names and Synonyms

Call:

- `Name/{id}/AcceptedNames`
- `Name/{id}/Synonyms`

This step resolves accepted-name context and synonymy. It fills:

- accepted-name identity
- accepted-name authorship when available
- synonym count
- a short selected synonym subset for durable storage

### Step 4: References

Call `Name/{id}/References`.

This step builds a compact bibliographic summary:

- total reference count
- a small selected subset of references with title, abbreviated source, year, and full citation when available

Only the compact summary is stored. The full list remains preview-only.

### Step 5: Distribution Summary

Call `Name/{id}/Distributions`.

This step builds a compact geographic summary:

- total distribution count
- distinct countries
- distinct regions
- a small selected subset of raw distribution rows for preview only

The durable result should emphasize normalized country and region names rather than storing every distribution record permanently.

### Step 6: Media Summary

Call `Name/{id}/Images`.

This step builds a compact media summary:

- media count
- up to `media_limit` selected items
- attribution, caption, and licensing fields when available

Only the compact summary is stored. Larger galleries remain preview-only.

### Partial Success Rules

- `match` and `summary` must succeed for the source to be usable
- `accepted names`, `synonyms`, `references`, `distributions`, and `images` are best-effort
- a source with a valid match and one missing secondary block is considered `partial`, not `failed`
- source status in UI should distinguish:
  - `no match`
  - `partial`
  - `complete`
  - `rate limited`
  - `provider error`

## Backend Design

### Configuration Model

Do not reintroduce a separate top-level source or dedicated plugin for Tropicos in this iteration.

Instead, extend the source configuration with a structured profile concept:

- `profile: tropicos_rich`
- `include_references`
- `include_distributions`
- `include_media`
- `media_limit`

This keeps the current multi-source enrichment model intact while allowing richer provider behavior than simple `response_mapping`.

### Runtime Strategy

The existing `api_taxonomy_enricher` should remain the public plugin entry point for this iteration, but Tropicos should no longer be implemented as a flat preset only.

Recommended internal approach:

- keep the source contract generic
- add a structured profile runner for `tropicos_rich`
- let the profile runner orchestrate the Tropicos calls and normalize the summary blocks
- continue to expose raw payloads and mapped summaries to preview surfaces

This avoids introducing a dedicated `tropicos_enricher` plugin immediately while still acknowledging that Tropicos needs richer behavior than the current generic mapper.

### Legacy Migration

The new implementation should support a migration path for legacy Tropicos configurations.

Recommended behavior:

- if a source already uses `api_taxonomy_enricher` with a Tropicos `Name/Search` URL and no profile, normalize it to `profile: tropicos_rich`
- if a source still references `plugin: tropicos_enricher`, normalize it into the generic loader shape during config loading when enough information is available
- the UI should surface the source as `Tropicos` rather than preserving a dead plugin identity

This keeps existing instances usable without forcing the user to recreate Tropicos sources manually.

### API Contract Changes

Preview and results payloads for structured sources should expose both:

- `summary` blocks for normal display
- `raw` payloads for inspection

For Tropicos preview specifically, the frontend should receive:

- `match`
- `nomenclature`
- `taxonomy`
- `references`
- `distribution_summary`
- `media_summary`
- `raw_data`
- per-block status or error information

## UI Design

### Configuration

The workspace should expose a `Tropicos` preset that now represents the structured `tropicos_rich` profile.

The configuration surface should stay compact:

- API key
- include references
- include distributions
- include media
- media item limit

Manual mapping should be minimized or hidden for `tropicos_rich`, following the same pattern as `gbif_rich`.

### Test API

`Test API` should stop rendering Tropicos as a flat key-value table only.

For Tropicos, the tester should render six sections:

- `Match`
- `Nomenclature`
- `Taxonomy`
- `References`
- `Distribution`
- `Media`

It should still preserve the raw payload tab so the user can inspect the complete response shape when needed.

The preview should emphasize summary comprehension over manual mapping.

### Results

The `Results` tab should present the saved enrichment by block:

- matched name and selected record
- accepted-name resolution
- taxonomic context
- references summary
- distribution summary
- media summary
- provenance and links

If one block failed, the result view should show that block as unavailable without making the whole source look broken.

### Quick Panel

The quick panel should stay compact.

For Tropicos, it should show only:

- source state
- last resolved name or accepted name
- one or two summary badges such as reference count, distribution count, or media count
- access to the full workspace for detail

## Error Handling

The design should distinguish between provider and interpretation states instead of collapsing them into one generic error.

Important cases:

- no match
- multiple ambiguous matches where the first selection is only a heuristic
- accepted-name endpoint unavailable
- references endpoint temporary failure
- distributions endpoint temporary failure
- images endpoint temporary failure
- provider rate limiting
- malformed or unexpected payload

Errors should be stored and surfaced per block where possible.

The source should remain usable when only secondary blocks fail.

## Testing Strategy

### Backend

Add targeted tests for:

- `tropicos_rich` config validation
- Tropicos legacy config upgrade
- match parsing and candidate selection
- no-match outcomes
- accepted-name and synonym normalization
- reference summary truncation
- distribution summary normalization
- media summary truncation
- partial success behavior
- preview payload shape including raw payload fallback

### Frontend

At minimum:

- `pnpm build`
- workspace rendering for Tropicos structured preview
- quick panel rendering with compact Tropicos summary
- result rendering with partial block failure states
- preset selection and structured options behavior

### Integration

Use a test instance to validate:

- one rich Tropicos source beside Endemia or GBIF
- preview behavior with real Tropicos payloads
- persistence of the summary structure in `extra_data`
- UI behavior when Tropicos returns sparse or ambiguous matches

## Rollout Notes

This design is intentionally scoped as a product-quality improvement to the existing enrichment system, not as a full provider framework rewrite.

If Tropicos proves strategic beyond this iteration, a later step can extract the structured provider runtime into a dedicated enrichment-provider layer or a dedicated `tropicos_enricher` plugin. That is explicitly deferred.

The old flat Tropicos preset should be considered replaced by this new structured behavior.

## References

- Official Tropicos Web Services overview: [https://services.tropicos.org/](https://services.tropicos.org/)
- Official Tropicos name search documentation: [https://services.tropicos.org/help?method=SearchNameXml](https://services.tropicos.org/help?method=SearchNameXml)
- Official Tropicos name summary documentation: [https://services.tropicos.org/help?method=GetNameXml](https://services.tropicos.org/help?method=GetNameXml)
- Official Tropicos accepted names documentation: [https://services.tropicos.org/help?method=GetNameAcceptedNamesXml](https://services.tropicos.org/help?method=GetNameAcceptedNamesXml)
- Official Tropicos references documentation: [https://services.tropicos.org/help?method=GetNameReferencesXml](https://services.tropicos.org/help?method=GetNameReferencesXml)
- Official Tropicos images documentation: [https://services.tropicos.org/help?method=GetNameImagesXml](https://services.tropicos.org/help?method=GetNameImagesXml)
- Official Tropicos distributions documentation: [https://services.tropicos.org/help?method=GetNameDistributionsXml](https://services.tropicos.org/help?method=GetNameDistributionsXml)
