# iNaturalist Rich Enrichment Design

## Summary

Add a richer iNaturalist integration to Niamoto as a single enrichment source in the existing multi-source enrichment workflow.

The user-facing model stays simple:

- one source named `iNaturalist`
- one workspace entry in the enrichment UI
- one quick-panel summary

Behind that source, iNaturalist is treated as a structured observations pipeline instead of a flat generic API lookup. The integration should help users retrieve a taxon match, a lightweight taxon card, a summary of community observations, a selection of media, and a compact places summary, while keeping the stored enrichment reusable and readable.

The design goal is to produce a durable field-and-community summary in `extra_data`, while keeping heavy observation detail and raw payloads available on demand in preview and results views rather than storing them permanently.

## Problem Statement

The current generic preset model is sufficient for simple APIs, but it underuses providers such as iNaturalist.

iNaturalist is not only a taxon lookup. It exposes:

- taxon-level metadata
- observation search
- media embedded in observations
- place-oriented filters and geographic context
- strong community evidence via recent and research-grade observations

Without a structured profile, Niamoto would either show a weak result or force users into manual response mapping that is not appropriate for an observations source.

This creates three product problems:

- iNaturalist would look weaker in the enrichment UI than it actually is
- the flat mapping model would make preview and results harder to understand
- the enriched data model would not separate stable summary data from exploratory observation detail

Niamoto needs an iNaturalist integration that behaves like a structured observations source, complementary to `GBIF Rich`, `Tropicos Rich`, `Catalogue of Life Rich`, and `BHL References`.

## Goals

- Keep iNaturalist as a single enrichment source in the UI
- Produce a readable summary from taxon and observation data
- Store a concise, reusable iNaturalist summary in `extra_data`
- Expose raw and sectional preview data in the workspace to help users inspect results
- Preserve the current multi-source enrichment model and quick panel / workspace split
- Keep the first iteration read-only and based on public API endpoints

## Non-Goals

- Create a dedicated `inaturalist_enricher` plugin in this iteration
- Store all observations or all photos permanently in `extra_data`
- Split iNaturalist into multiple UI sources such as `iNaturalist Taxon` and `iNaturalist Observations`
- Support user-authenticated write operations such as posting observations or identifications
- Build advanced maps, timelines, or observation browsing in the first implementation pass

## Design Principles

- Keep the user-facing source model simple
- Treat iNaturalist as a structured observations source, not as a flat generic API response
- Store summaries permanently, fetch heavy detail on demand
- Prefer partial success over all-or-nothing failure
- Favor readable biological context over raw API exhaustiveness
- Keep the persisted result understandable to domain users

## Proposed Product Shape

### One Rich iNaturalist Source

iNaturalist remains a single source in `entities.references.<ref>.enrichment`.

Example:

```yaml
- id: inaturalist
  label: iNaturalist
  plugin: api_taxonomy_enricher
  enabled: true
  config:
    profile: inaturalist_rich
    include_observations: true
    include_media: true
    include_places: true
    media_limit: 3
    observation_limit: 5
```

The UI still presents one source card, one source editor, one test surface, and one result group.

### Structured Result Model

The iNaturalist source result is internally organized into six blocks:

- `match`
- `taxon`
- `observation_summary`
- `media_summary`
- `places`
- `links`

This is the key product change. iNaturalist is no longer treated as one response mapped into a flat table.

## Authentication Model

The first version is read-only and uses public iNaturalist endpoints.

Behavior rules:

- no API key is required for normal read-only use
- preview and execution should work without user credentials
- the integration must stay compatible with future authenticated extensions, but no OAuth flow is added in this iteration

Official reference:

- [iNaturalist API Reference](https://www.inaturalist.org/pages/api+reference)

## Data Model

iNaturalist summaries are stored under:

`extra_data.api_enrichment.sources.inaturalist.data`

Recommended structure:

```json
{
  "match": {
    "taxon_id": 12345,
    "scientific_name": "Alphitonia neocaledonica",
    "preferred_common_name": null,
    "rank": "species",
    "iconic_taxon_name": "Plantae",
    "matched_name": "Alphitonia neocaledonica"
  },
  "taxon": {
    "observations_count": 84,
    "wikipedia_url": "https://en.wikipedia.org/wiki/...",
    "default_photo": {
      "square_url": "https://static.inaturalist.org/photos/....jpg",
      "medium_url": "https://static.inaturalist.org/photos/....jpg",
      "attribution": "(c) Example User, some rights reserved"
    },
    "conservation_status": null,
    "iconic_taxon_name": "Plantae"
  },
  "observation_summary": {
    "observations_count": 84,
    "research_grade_count": 61,
    "casual_count": 12,
    "needs_id_count": 11,
    "recent_observations": [
      {
        "observation_id": 123456,
        "observed_on": "2026-01-17",
        "quality_grade": "research",
        "place_guess": "Nouméa, Nouvelle-Calédonie",
        "observation_url": "https://www.inaturalist.org/observations/123456"
      }
    ]
  },
  "media_summary": {
    "media_count": 3,
    "sample": [
      {
        "observation_id": 123456,
        "medium_url": "https://static.inaturalist.org/photos/....jpg",
        "square_url": "https://static.inaturalist.org/photos/....jpg",
        "attribution": "(c) Example User, some rights reserved",
        "license_code": "cc-by-nc"
      }
    ]
  },
  "places": {
    "top_places": [
      {
        "name": "Nouvelle-Calédonie",
        "count": 12
      }
    ]
  },
  "links": {
    "taxon": "https://www.inaturalist.org/taxa/12345",
    "observations": "https://www.inaturalist.org/observations?taxon_id=12345"
  },
  "provenance": {
    "endpoints": [
      "/v1/taxa",
      "/v1/observations"
    ],
    "enriched_at": "2026-04-10T00:00:00Z",
    "profile_version": "inaturalist-rich-v1"
  }
}
```

### What Is Stored Permanently

- taxon match summary
- lightweight taxon card
- compact observation counts
- a limited sample of recent observations
- a limited media sample
- a short places summary
- provenance metadata

### What Is Not Stored Permanently

- full observation result sets
- full photo sets
- raw API payloads
- large place aggregations
- comments, identifications, or social activity details

These remain available on demand through preview and detailed results surfaces.

## Runtime Pipeline

The iNaturalist source runs as a five-step pipeline with partial success support.

### Step 1: Taxon Match

Call the taxon search endpoint to resolve the submitted scientific name into a usable iNaturalist taxon.

This step provides:

- the best matching taxon id
- canonical scientific name
- preferred common name when available
- rank and iconic taxon

This step is required.

### Step 2: Taxon Card

Hydrate a lightweight taxon card from the selected taxon result.

This step provides:

- default photo
- wikipedia url when available
- observation count
- conservation status if available

This step is best effort but normally expected to succeed with the match.

### Step 3: Observation Summary

Query observations for the selected `taxon_id`.

This step provides:

- observation counts
- research-grade vs casual vs needs-id summary
- a short sample of recent observations

This is the main value block of the source.

### Step 4: Media Summary

Extract a small number of representative photos from the observation results, and use the taxon default photo as fallback when useful.

This step provides:

- media count
- a small, licensed media sample with attribution

### Step 5: Places Summary

Build a compact place summary from recent observations.

This step provides:

- top places or place guesses
- a short geographic context for the taxon in iNaturalist

## Runtime Rules

- the taxon match is mandatory
- all other blocks are best effort
- if the taxon exists but there are few or no observations, the source remains valid
- if media or places fail, the result is `partial`, not `failed`
- raw payloads remain available in preview but are not persisted into `extra_data`

## UI and UX

### Configuration

The existing preset list should expose `iNaturalist` as a structured provider.

Configuration for this profile should include:

- `include_observations`
- `include_media`
- `include_places`
- `media_limit`
- `observation_limit`

Manual field mapping should not be shown for this structured profile.

### Tester l’API

The preview surface should expose these sections:

- `Match`
- `Taxon`
- `Observations`
- `Médias`
- `Lieux`

It should also keep the existing `Réponse brute API` surface.

### Résultats

The stored result view should show:

- taxon retained
- counts and status summary
- a small media selection
- top places
- direct links to iNaturalist

It should not display long observation tables in the persisted results view.

### Quick Panel

The quick panel should stay compact and show only:

- taxon match state
- observation count
- media count
- top places count or short label

The detailed blocks remain in the workspace.

## Error Handling

The source should fail clearly when:

- no taxon match can be found
- the API request fails entirely

The source should degrade gracefully when:

- observations are empty
- media extraction yields no usable photos
- place summaries are incomplete

Preview and result blocks should indicate `partial` state rather than collapsing into a generic error when only one sub-block fails.

## Testing Strategy

Add targeted tests for:

- config validation for `inaturalist_rich` without flat `response_mapping`
- taxon match and observation summary happy path
- no-match behavior
- partial success when observations exist but media or places are missing
- service normalization and config transport
- structured rendering in preview/results

Frontend validation should include:

- `pnpm build`

Backend validation should include:

- targeted `pytest` modules for loader and enrichment service

## Sources

- [iNaturalist API Reference](https://www.inaturalist.org/pages/api+reference)
