# Catalogue of Life Rich Enrichment Design

## Summary

Add a richer Catalogue of Life integration to Niamoto as a single enrichment source in the existing multi-source enrichment workflow.

The user-facing model stays simple:

- one source named `Catalogue of Life`
- one workspace entry in the enrichment UI
- one quick-panel summary

Behind that source, Catalogue of Life is treated as a structured enrichment pipeline instead of a flat search-and-map lookup. The integration should prioritize taxonomic consolidation while also surfacing vernacular names and distribution data when they are available in the current release.

The design goal is to produce a stable, reusable enrichment summary in `extra_data`, while keeping large lists and raw payloads available on demand in preview and results views rather than storing them permanently.

## Problem Statement

The current generic API preset model is sufficient for simple one-request APIs, but it underuses modular providers such as Catalogue of Life.

Catalogue of Life exposes a much richer structure than a flat match response:

- accepted taxon status
- classification
- synonymy
- vernacular names
- distributions
- references

Without a structured profile, Niamoto would either show a poor result or force users into manual mapping work that is not appropriate for this provider.

This creates three product problems:

- Catalogue of Life would look weaker in the enrichment UI than it actually is
- the current flat mapping model would make preview and results harder to understand
- the enriched data model would not distinguish between a durable summary and heavy exploratory detail

Niamoto needs a Catalogue of Life integration that behaves like a real structured source, similar in quality to `GBIF Rich` and `Tropicos Rich`.

## Goals

- Keep Catalogue of Life as a single enrichment source in the UI
- Produce a richer result than a flat name search mapping
- Store a concise, reusable Catalogue of Life summary in `extra_data`
- Expose raw and sectional preview data in the workspace to help users understand what Catalogue of Life returned
- Include vernacular names and distributions when available
- Preserve the current multi-source enrichment model and quick panel / workspace split

## Non-Goals

- Create a dedicated `col_enricher` plugin in this iteration
- Store every vernacular name, distribution record, or reference permanently in `extra_data`
- Split Catalogue of Life into multiple separate UI sources such as `COL Taxonomy` and `COL References`
- Replace GBIF, Tropicos, or Endemia
- Build custom map rendering in the first implementation pass

## Design Principles

- Keep the user-facing source model simple
- Treat Catalogue of Life as a structured source, not as a bigger flat mapping
- Store summaries permanently, fetch heavy detail on demand
- Prefer partial success over all-or-nothing failure
- Make release provenance explicit
- Avoid locking the implementation to a single hardcoded Catalogue release

## Proposed Product Shape

### One Rich Catalogue of Life Source

Catalogue of Life remains a single source in `entities.references.<ref>.enrichment`.

Example:

```yaml
- id: col
  label: Catalogue of Life
  plugin: api_taxonomy_enricher
  enabled: true
  config:
    profile: col_rich
    dataset_key: 314774
    include_vernaculars: true
    include_distributions: true
    include_references: true
    reference_limit: 5
```

The UI still presents one source card, one source editor, one test surface, and one result group.

### Structured Result Model

The Catalogue of Life source result is internally organized into six blocks:

- `match`
- `taxonomy`
- `nomenclature`
- `vernaculars`
- `distribution_summary`
- `references`

This is the key product change. Catalogue of Life is no longer treated as one response mapped into a flat table.

## Data Model

Catalogue of Life summaries are stored under:

`extra_data.api_enrichment.sources.col.data`

Recommended structure:

```json
{
  "match": {
    "taxon_id": "C66X",
    "name_id": "3FNWHqciKg9O2_kT0ohQ8",
    "scientific_name": "Alphitonia neocaledonica",
    "authorship": "(Schltr.) Guillaumin",
    "canonical_name": "Alphitonia neocaledonica",
    "rank": "species",
    "status": "accepted",
    "matched_name": "Alphitonia neocaledonica",
    "dataset_key": 314774
  },
  "taxonomy": {
    "classification": [
      { "rank": "kingdom", "name": "Plantae" },
      { "rank": "family", "name": "Rhamnaceae" },
      { "rank": "genus", "name": "Alphitonia" }
    ],
    "kingdom": "Plantae",
    "phylum": "Tracheophyta",
    "class": "Magnoliopsida",
    "order": "Rosales",
    "family": "Rhamnaceae",
    "genus": "Alphitonia",
    "species": "Alphitonia neocaledonica"
  },
  "nomenclature": {
    "accepted_name": "Alphitonia neocaledonica",
    "synonyms_count": 2,
    "synonyms_sample": [
      "Pomaderris neocaledonica Schltr.",
      "Alphitonia vieillardii Lenorm. ex Braid"
    ]
  },
  "vernaculars": {
    "vernacular_count": 0,
    "by_language": {},
    "sample": []
  },
  "distribution_summary": {
    "distribution_count": 1,
    "areas": ["New Caledonia"],
    "gazetteers": ["text"]
  },
  "references": {
    "references_count": 1,
    "sample": [
      "Guillaumin. (1911). Notul. Syst. (Paris) 2: 99 (1911)."
    ]
  },
  "links": {
    "checklistbank_taxon": "https://www.checklistbank.org/dataset/314774/taxon/C66X"
  },
  "provenance": {
    "dataset_key": 314774,
    "release_label": "2026-04-07 XR",
    "endpoints": [
      "dataset/{key}/nameusage/search",
      "dataset/{key}/taxon/{id}",
      "dataset/{key}/taxon/{id}/classification",
      "dataset/{key}/taxon/{id}/synonyms",
      "dataset/{key}/taxon/{id}/vernacular",
      "dataset/{key}/taxon/{id}/distribution",
      "dataset/{key}/reference/{id}"
    ],
    "enriched_at": "2026-04-10T00:00:00Z",
    "profile_version": "col-rich-v1"
  }
}
```

### What Is Stored Permanently

- taxonomic match summary
- normalized classification summary
- compact synonym summary
- compact vernacular summary
- compact distribution summary
- compact reference summary
- external links and release provenance metadata

### What Is Not Stored Permanently

- full raw ChecklistBank JSON payloads
- full vernacular lists
- full distributions
- full reference lists
- request-by-request debug payloads

These remain available on demand through preview and detailed results surfaces.

## Runtime Pipeline

The Catalogue of Life source runs as a six-step pipeline with partial success support.

### Step 1: Search / Match

Call `dataset/{key}/nameusage/search?q=...` using the configured release dataset key.

This step is mandatory and provides:

- the best matching usage
- the working `taxon_id`
- the working `name_id`
- label, rank, status, authorship, and initial classification snippet

If no reliable match is found, the enrichment should stop with a clear `no_match` outcome, not with a generic failure.

### Step 2: Taxon Detail

Call `dataset/{key}/taxon/{id}` for the resolved taxon.

This step fills the core `match` block and provides:

- accepted status
- source link
- reference identifiers
- accepted taxon label

### Step 3: Classification

Call `dataset/{key}/taxon/{id}/classification`.

This fills `taxonomy` and normalizes the higher-rank shortcuts that are useful for Niamoto outputs.

### Step 4: Synonyms

Call `dataset/{key}/taxon/{id}/synonyms`.

This fills `nomenclature`, including:

- synonym counts
- homotypic and heterotypic samples
- accepted name recap when useful

### Step 5: Vernaculars and Distributions

Call:

- `dataset/{key}/taxon/{id}/vernacular`
- `dataset/{key}/taxon/{id}/distribution`

Both are `best effort`.

The implementation should summarize:

- vernacular count
- short vernacular sample
- language grouping
- distribution count
- short area list
- gazetteer summary when available

### Step 6: References

Use reference identifiers collected from the taxon and related summary blocks, then resolve a limited subset through:

- `dataset/{key}/reference/{id}`

This fills `references` with a small citation sample and a count.

## Dataset Key Strategy

Catalogue of Life releases are published regularly in ChecklistBank, and the active `dataset_key` changes with each release.

The implementation must therefore:

- allow `dataset_key` to be configured explicitly
- provide a sensible default matching the current XR release at the time the preset is added
- transport the selected `dataset_key` in provenance and preview data

The first implementation can ship with the then-current XR release key as the preset default, but the profile must not assume that key is permanent.

## Error Handling and Partial Success

`search` is required. All later steps are `best effort`.

Expected outcomes:

- no search match: return a structured `no_match`
- taxon detail failure after a search hit: return a provider error
- classification, synonym, vernacular, distribution, or reference failure: return a partial result with block-level gaps
- empty vernaculars or distributions: return valid empty summaries, not errors

The preview and result structures should retain enough metadata to show which blocks are populated and which ones are absent or failed.

## API and Backend Shape

### Loader Profile

Add a new structured profile in `api_taxonomy_enricher`:

- `col_rich`

Required config fields:

- `profile`
- `dataset_key`

Optional config fields:

- `include_vernaculars`
- `include_distributions`
- `include_references`
- `reference_limit`

As with `gbif_rich` and `tropicos_rich`, `response_mapping` is not required for this profile.

### Preview Payload

Preview results should include both:

- the structured mapped summary
- a grouped raw payload for debugging and mapping help

Recommended raw payload grouping:

```json
{
  "search": { "...": "..." },
  "taxon": { "...": "..." },
  "classification": [ "..."],
  "synonyms": { "...": "..." },
  "vernaculars": [ "..."],
  "distributions": [ "..."],
  "references": [ "..."]
}
```

## Frontend Shape

### Configuration

Add a new preset:

- `Catalogue of Life`

Configuration UI should expose:

- dataset key
- include vernaculars
- include distributions
- include references
- reference limit

This profile should behave like the other structured presets and avoid exposing manual mapping as the primary editing path.

### Tester View

The `Tester l'API` view should render six structured blocks:

- `Match`
- `Taxonomy`
- `Nomenclature`
- `Vernacular Names`
- `Distribution`
- `References`

The existing `Réponse brute API` view should show the grouped raw payload.

### Results View

The `Résultats` view should show the same sections with compact summaries:

- match status and chosen name
- classification recap
- synonym count and sample
- vernacular count and sample
- distribution count and sample
- reference count and sample

### Quick Panel

The quick panel should stay dense and only show a compact source summary:

- match status
- synonyms count
- vernacular count
- distribution count

## Legacy and Compatibility

- Existing simple Catalogue of Life-like configs can remain supported through the generic loader path
- The new preset should use `col_rich`
- The UI should normalize only the new structured fields for this profile
- The structured result model should align with the existing multi-source storage format under `extra_data.api_enrichment.sources.*`

## Testing Strategy

### Backend

Add targeted tests for:

- `col_rich` config validation
- no-match behavior
- structured summary generation from mocked ChecklistBank responses
- partial success behavior when vernaculars, distributions, or references are absent
- service transport of new config fields and preview payloads

### Frontend

Add or update targeted tests for:

- preset normalization
- structured section rendering
- grouped raw payload rendering

At minimum, run:

- targeted `pytest` modules for the loader, config model, and enrichment service
- `pnpm build` for the frontend

## Risks and Trade-Offs

- The active Catalogue of Life release key changes over time, so defaults can become stale
- Some taxa have rich vernacular data while others have none; the UI must avoid making empty results feel broken
- References, vernaculars, and distributions can become large quickly, so summary limits are important
- ChecklistBank evolves actively, so the implementation should prefer tolerant parsing over brittle field assumptions

## Sources

- [Catalogue of Life access guide](https://www.catalogueoflife.org/howto/access)
- [ChecklistBank API](https://api.checklistbank.org/)
- [Catalogue of Life releases](https://www.catalogueoflife.org/building/releases)
