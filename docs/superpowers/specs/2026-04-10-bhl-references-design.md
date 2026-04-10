# BHL References Enrichment Design

## Summary

Add a richer Biodiversity Heritage Library integration to Niamoto as a single enrichment source in the existing multi-source enrichment workflow.

The user-facing model stays simple:

- one source named `BHL`
- one workspace entry in the enrichment UI
- one quick-panel summary

Behind that source, BHL is treated as a structured references pipeline instead of a flat generic API lookup. The integration should help users discover bibliographic evidence, title-level context, and representative pages for a scientific name, while keeping the stored enrichment compact and reusable.

The design goal is to produce a durable documentary summary in `extra_data`, while keeping heavy page-level detail and raw payloads available on demand in preview and results views rather than storing them permanently.

## Problem Statement

The current generic preset model is sufficient for simple APIs, but it underuses documentary providers such as BHL.

BHL exposes more than a plain name search:

- confirmed names and canonical forms
- title, item, and page metadata
- publication context
- page thumbnails and OCR endpoints
- direct links to BHL bibliography, items, and pages

Without a structured profile, Niamoto would either show a weak result or force users into manual response mapping that is not appropriate for a bibliographic source.

This creates three product problems:

- BHL would look weaker in the enrichment UI than it actually is
- the flat mapping model would make preview and results harder to understand
- the enriched data model would not separate stable reference summaries from heavy exploratory detail

Niamoto needs a BHL integration that behaves like a structured documentary source, complementary to `GBIF Rich`, `Tropicos Rich`, and `Catalogue of Life Rich`.

## Goals

- Keep BHL as a single enrichment source in the UI
- Require a user-supplied API key in source configuration
- Produce a readable bibliographic summary from BHL name metadata
- Store a concise, reusable BHL summary in `extra_data`
- Expose raw and sectional preview data in the workspace to help users inspect documentary evidence
- Preserve the current multi-source enrichment model and quick panel / workspace split

## Non-Goals

- Create a dedicated `bhl_enricher` plugin in this iteration
- Store all OCR text, all pages, or all titles permanently in `extra_data`
- Split BHL into multiple UI sources such as `BHL Titles` and `BHL Pages`
- Use BHL as a taxonomic authority or taxonomic match replacement
- Build advanced OCR exploration or in-app document reading in the first implementation pass

## Design Principles

- Keep the user-facing source model simple
- Treat BHL as a structured references source, not as a flat generic API response
- Store summaries permanently, fetch heavy detail on demand
- Prefer partial success over all-or-nothing failure
- Make authentication explicit and user-owned
- Keep the persisted result documentary and readable for domain users

## Proposed Product Shape

### One Rich BHL Source

BHL remains a single source in `entities.references.<ref>.enrichment`.

Example:

```yaml
- id: bhl
  label: BHL
  plugin: api_taxonomy_enricher
  enabled: true
  config:
    profile: bhl_references
    api_key: ${BHL_API_KEY}
    include_publication_details: true
    include_page_preview: true
    title_limit: 5
    page_limit: 5
```

The UI still presents one source card, one source editor, one test surface, and one result group.

### Structured Result Model

The BHL source result is internally organized into six blocks:

- `match`
- `title_summary`
- `publications`
- `name_mentions`
- `page_links`
- `references_count`

This is the key product change. BHL is no longer treated as one response mapped into a flat table.

## Authentication Model

BHL requires an API key for every request.

The source configuration must therefore include a user-provided key obtained from the official form:

- [BHL API key form](https://www.biodiversitylibrary.org/getapikey.aspx)

Behavior rules:

- the key is required to test or run the source
- the key is masked in the UI
- the key is never returned in preview, results, exports, or logs
- if the key is missing, the source remains configurable but cannot execute
- test and run errors should report missing or invalid credentials clearly without exposing the key value

## Data Model

BHL summaries are stored under:

`extra_data.api_enrichment.sources.bhl.data`

Recommended structure:

```json
{
  "match": {
    "submitted_name": "Alphitonia neocaledonica",
    "name_confirmed": "Alphitonia neocaledonica",
    "name_canonical": "Alphitonia neocaledonica",
    "namebank_id": "5775264",
    "match_status": "confirmed"
  },
  "title_summary": {
    "title_count": 3,
    "item_count": 4,
    "page_count": 6
  },
  "publications": {
    "sample": [
      {
        "title_id": 84482,
        "short_title": "Repertorium specierum novarum regni vegetabilis",
        "publication_date": "1911-1941",
        "publisher_name": "Verlag des Repertoriums",
        "title_url": "https://www.biodiversitylibrary.org/title/84482"
      }
    ]
  },
  "name_mentions": {
    "sample": [
      {
        "name_found": "Alphitonia neocaledonica",
        "name_confirmed": "Alphitonia neocaledonica"
      }
    ]
  },
  "page_links": {
    "sample": [
      {
        "page_id": 5904859,
        "page_url": "https://www.biodiversitylibrary.org/page/5904859",
        "thumbnail_url": "https://www.biodiversitylibrary.org/pagethumb/5904859",
        "page_type": "Text"
      }
    ]
  },
  "references_count": {
    "titles": 3,
    "items": 4,
    "pages": 6
  },
  "links": {
    "name_search": "https://www.biodiversitylibrary.org/name/Alphitonia%20neocaledonica"
  },
  "provenance": {
    "endpoints": [
      "NameSearch",
      "GetNameMetadata",
      "GetTitleMetadata",
      "PublicationSearch",
      "GetPageMetadata"
    ],
    "enriched_at": "2026-04-10T00:00:00Z",
    "profile_version": "bhl-references-v1"
  }
}
```

### What Is Stored Permanently

- confirmed/canonical name summary
- compact counts of titles, items, and pages
- a limited publication sample
- a limited page sample with direct BHL links
- documentary provenance metadata

### What Is Not Stored Permanently

- full OCR text
- full raw BHL JSON payloads
- all titles, items, and pages
- large lists of per-page mentions
- request-by-request debug payloads

These remain available on demand through preview and detailed results surfaces.

## Runtime Pipeline

The BHL source runs as a four-step pipeline with partial success support.

### Step 1: Name Search

Call [`NameSearch`](https://www.biodiversitylibrary.org/docs/api3/NameSearch.html) with the submitted scientific name.

This step is a lightweight confirmation layer and provides:

- whether BHL recognizes the submitted name
- likely confirmed/canonical variants
- a first signal of documentary coverage

This step is useful, but not sufficient on its own.

### Step 2: Name Metadata

Call [`GetNameMetadata`](https://www.biodiversitylibrary.org/docs/api3/GetNameMetadata.html) with the scientific name, or with an identifier if one becomes available later.

This is the core step. It returns:

- confirmed and canonical name information
- title metadata
- nested item metadata
- nested page metadata for matching pages

If this step returns no documentary result, the enrichment should stop with a clear `no_references_found` outcome rather than a generic failure.

### Step 3: Publication Enrichment

Hydrate the best matching publications using:

- [`GetTitleMetadata`](https://www.biodiversitylibrary.org/docs/api3/GetTitleMetadata.html)
- optionally [`PublicationSearch`](https://www.biodiversitylibrary.org/docs/api3/PublicationSearch.html) when additional bibliographic context is helpful

This step enriches the best titles with:

- cleaner publication metadata
- title-level links
- optional item summaries

This step is `best effort`.

### Step 4: Page Detail

For a limited number of representative pages, call [`GetPageMetadata`](https://www.biodiversitylibrary.org/docs/api3/GetPageMetadata.html).

This step enriches the page sample with:

- direct page links
- thumbnails
- page types
- OCR URLs or OCR text when explicitly requested for preview

This step is also `best effort`.

### Partial Success Rules

- missing API key stops execution cleanly with a credentials error
- `NameSearch` can fail softly if `GetNameMetadata` still succeeds
- `GetNameMetadata` is the minimum useful step
- publication and page enrichment are optional improvements
- if publication or page detail fails, the source should still return a partial documentary summary when name metadata exists

## UI and Interaction Design

### Configuration

The source appears as a single preset:

- `BHL`

Configuration should expose:

- `API key`
- `Include publication details`
- `Include page preview`
- `Title limit`
- `Page limit`

This profile should not expose a large manual mapping editor.

### Tester l'API

The test surface should render the BHL result in documentary sections:

- `Match`
- `Titles`
- `Mentions`
- `Pages`
- `Links`

And continue to expose:

- `Mapped fields`
- `Raw API response`

Each title card should show:

- short title
- publication date
- publisher when available
- BHL title link

Each page card should show:

- page id
- page type
- thumbnail when available
- direct BHL page link

### Results

The persisted results view should remain compact and readable:

- title count
- page count
- top references
- top page links

Heavy OCR or large page lists should stay out of the main persisted results surface.

### Quick Panel

The quick panel should only surface a compact summary:

- title count
- page count
- main BHL link

The detailed reading experience belongs in the workspace, not in the quick panel.

## Backend Design

Implementation should extend the existing generic loader architecture rather than create a new plugin.

Recommended shape:

- add `profile: bhl_references` to `api_taxonomy_enricher`
- implement a structured BHL pipeline inside the loader
- keep BHL raw payloads available for preview but out of permanent storage
- add configuration transport and normalization in the enrichment service
- support legacy-less initialization because BHL is a new structured source

### Config Surface

Expected config fields:

- `profile: "bhl_references"`
- `api_key: str`
- `include_publication_details: bool = true`
- `include_page_preview: bool = true`
- `title_limit: int = 5`
- `page_limit: int = 5`

### Security Handling

- treat `api_key` as sensitive configuration
- avoid echoing it into preview data
- avoid storing it inside raw response payloads
- avoid exposing it through result serialization

## Frontend Design

The frontend should follow the same structured-source model already used for `GBIF`, `Tropicos`, and `Catalogue of Life`.

Required work:

- add a `BHL` preset in quick configuration
- add provider description with links:
  - [BHL site](https://www.biodiversitylibrary.org/)
  - [BHL API docs](https://www.biodiversitylibrary.org/docs/api3.html)
  - [BHL API key form](https://www.biodiversitylibrary.org/getapikey.aspx)
- expose the `API key` field and BHL-specific options
- render structured `Tester l'API` and `Results` sections for BHL
- keep quick-panel summaries compact

## Error Handling

Expected error categories:

- missing API key
- invalid API key
- BHL rate limiting or upstream downtime
- no references found for the submitted name
- partial documentary result with missing publication or page detail

User-facing error handling should be explicit:

- credential issues should mention BHL authentication
- `no references found` should not look like a transport failure
- partial results should remain explorable instead of collapsing into a generic error state

## Testing Strategy

### Backend Tests

Add targeted tests for:

- config validation for `bhl_references`
- missing API key handling
- structured parsing of `GetNameMetadata`
- publication/page limiting
- partial success behavior when publication or page enrichment fails
- result serialization that excludes the API key

### Frontend Tests and Verification

At minimum:

- `pnpm build`

Manual verification should cover:

- configuring a BHL source with an API key
- running `Tester l'API`
- checking structured sections for titles and pages
- confirming that raw response does not expose the API key
- checking quick-panel summary rendering

## Rollout Notes

- BHL should be introduced as a new structured source, not as a flat generic preset
- the source should be optional and user-keyed
- documentation should explain where to obtain the key and what kind of result to expect from BHL

## References

- [BHL API v3](https://www.biodiversitylibrary.org/docs/api3.html)
- [BHL NameSearch](https://www.biodiversitylibrary.org/docs/api3/NameSearch.html)
- [BHL GetNameMetadata](https://www.biodiversitylibrary.org/docs/api3/GetNameMetadata.html)
- [BHL GetTitleMetadata](https://www.biodiversitylibrary.org/docs/api3/GetTitleMetadata.html)
- [BHL GetPageMetadata](https://www.biodiversitylibrary.org/docs/api3/GetPageMetadata.html)
- [BHL PublicationSearch](https://www.biodiversitylibrary.org/docs/api3/PublicationSearch.html)
- [BHL API key form](https://www.biodiversitylibrary.org/getapikey.aspx)
