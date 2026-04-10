# GN Verifier Shared Name Resolution Design

## Summary

Add an optional shared Global Names resolution layer to Niamoto's structured taxonomy enrichers.

The user-facing model stays simple:

- no new source appears in the enrichment source list
- `GN Verifier` is exposed only as an advanced option on structured sources
- the visible source remains `GBIF`, `Tropicos`, or `Catalogue of Life`

The design goal is to improve name normalization and matching reliability before calling provider-specific pipelines, while keeping the UI focused on the real enrichment sources rather than on the resolution helper itself.

## Problem Statement

Niamoto now has several rich taxonomy providers with their own matching behavior:

- `GBIF Rich`
- `Tropicos Rich`
- `Catalogue of Life Rich`

Each of them receives a raw scientific name string from the entity data and then performs provider-specific matching.

This creates three recurring problems:

- names may contain authorship, lexical variants, or formatting noise that reduce match quality
- the same submitted name can match differently depending on the provider
- users currently have little visibility into whether a source used the submitted name as-is or a corrected name

Global Names provides a lightweight pre-resolution capability that can improve the initial query name without replacing the downstream provider as the authoritative source.

Niamoto needs a shared design that:

- keeps `GN Verifier` optional
- keeps it internal to the structured source workflow
- records enough provenance to explain name corrections
- never blocks enrichment if Global Names is unavailable or inconclusive

## Goals

- Add an optional pre-resolution layer for structured sources
- Keep `GN Verifier` hidden as an internal helper, not a standalone enrichment source
- Improve provider match quality for messy or variant scientific names
- Show compact name-resolution provenance in preview and results
- Allow per-source activation rather than enforcing a global switch
- Reuse one shared implementation across `GBIF`, `Tropicos`, and `Catalogue of Life`

## Non-Goals

- Add `GN Verifier` as a new source in the enrichment source list
- Make Global Names resolution mandatory
- Store full Global Names payloads permanently in `extra_data`
- Introduce a full debug UI for every candidate match returned by Global Names
- Add a separate parser-only configuration surface in the first iteration

## Design Principles

- Keep the visible product model centered on the real data provider
- Treat Global Names as advisory, not authoritative
- Prefer graceful fallback to the submitted name
- Store concise provenance, not heavy debugging detail
- Keep the option source-specific
- Reuse the same internal contract for all structured taxonomy sources

## Proposed Product Shape

### Shared Optional Helper

`GN Verifier` is implemented as an internal step that can be enabled on structured providers.

Example source configuration:

```yaml
- id: gbif
  label: GBIF
  plugin: api_taxonomy_enricher
  enabled: true
  config:
    profile: gbif_rich
    use_name_verifier: true
    name_verifier_preferred_sources:
      - Catalogue of Life
      - GBIF
      - Tropicos
```

The same pattern applies to `tropicos_rich` and `col_rich`.

### No Additional Source Card

Users should not see:

- a `GN Verifier` card in the quick panel
- a `GN Verifier` source in the workspace source list
- separate run controls for Global Names

Instead, the existing source keeps ownership of the workflow.

### Optional Resolution Block

When enabled, preview and results for a structured source gain one extra compact block:

- `Name resolution`

This block appears before the provider-specific `Match` block and explains how the submitted name was interpreted.

## Data Model

Name-resolution summaries live inside the source result, not as a sibling source.

Recommended structure:

```json
{
  "name_resolution": {
    "enabled": true,
    "status": "resolved",
    "submitted_name": "Alphitonia neocaledonica (Schltr.) Guillaumin",
    "parsed_name": "Alphitonia neocaledonica (Schltr.) Guillaumin",
    "query_name": "Alphitonia neocaledonica",
    "matched_name": "Alphitonia neocaledonica",
    "was_corrected": true,
    "best_result": "Alphitonia neocaledonica",
    "data_source_title": "Catalogue of Life",
    "score": 0.99,
    "alternatives": [
      "Alphitonia neocaledonica",
      "Alphitonia sp."
    ]
  }
}
```

### What Is Stored Permanently

- whether name resolution was enabled
- submitted name
- normalized or parsed query name actually used downstream
- best match label
- source title
- compact status and correction flag
- a short alternatives list

### What Is Not Stored Permanently

- full parser payloads
- full verifier payloads
- all candidate matches from all data sources
- low-level scoring diagnostics

These remain available only in raw preview payloads when returned.

## Configuration Model

Structured provider configs gain three new optional fields:

- `use_name_verifier: bool = false`
- `name_verifier_preferred_sources: list[str] = []`
- `name_verifier_threshold: float | null = null`

The first iteration should keep the UI surface minimal:

- expose `use_name_verifier`
- do not expose preferred-source controls in the first iteration
- keep any parser behavior internal

The implementation should be able to accept these fields for:

- `gbif_rich`
- `tropicos_rich`
- `col_rich`

It should ignore them for non-structured generic presets.

## Runtime Pipeline

The shared resolution pipeline runs before the provider-specific structured pipeline.

### Step 1: Submitted Name

Read the source query string exactly as today from the configured `query_field`.

### Step 2: Optional Global Names Resolution

If `use_name_verifier` is enabled:

- optionally parse or normalize the incoming name
- send the name to Global Names Verifier
- request a best match, with preferred sources if configured
- build a compact `name_resolution` summary

If the result is strong enough:

- use the resolved query name for the provider-specific pipeline

If the result is weak, ambiguous, unavailable, or failed:

- keep the original submitted name
- still record a compact resolution status when useful

### Step 3: Provider-Specific Enrichment

Call the downstream structured provider with the selected query name:

- `gbif_rich`
- `tropicos_rich`
- `col_rich`

The provider remains authoritative for the final taxonomic or enrichment result.

### Step 4: Output Assembly

The final enriched result contains:

- `name_resolution`
- the normal provider-specific structured blocks
- optional raw Global Names payload inside `api_response_raw` only

## Failure Model

Global Names must never be a hard blocker.

Rules:

- if Global Names is unavailable, continue with the submitted name
- if Global Names returns no usable result, continue with the submitted name
- if Global Names returns ambiguous or low-confidence output, continue with the submitted name unless the configured threshold is met
- if the downstream provider succeeds, the overall enrichment is successful even when Global Names failed

This keeps the helper valuable without turning it into an operational dependency.

## UI Design

### Configuration

Structured sources gain an advanced switch:

- `Name pre-resolution`

The first implementation may stop there.

If preferred-source controls are introduced in a later iteration, they should remain advanced and compact.

### Testing

When enabled, `Tester l'API` / `Test API` gains a new block:

- `Name resolution`

Recommended fields:

- submitted name
- query name actually used
- source title
- status
- correction flag
- short alternatives list

This block appears before `Match`.

### Results

The `Results` view mirrors the same compact block, but keeps it lighter than preview.

### Quick Panel

The quick panel should remain almost unchanged.

At most, a subtle badge may indicate that the submitted name was corrected during the last successful run.

## Provider Integration Rules

### GBIF Rich

Use the resolved query name for species matching.

The `name_resolution` block explains whether the submitted name was normalized before the GBIF match.

### Tropicos Rich

Use the resolved query name before the `Name/Search` step.

This is particularly useful because Tropicos often benefits from cleaner canonical names before secondary requests by `NameId`.

### Catalogue of Life Rich

Use the resolved query name before `nameusage/search`.

This helps align the initial ChecklistBank search with a cleaner canonical query string.

## Testing Strategy

Add targeted backend tests for:

- config validation and transport of `use_name_verifier`
- successful resolution with corrected query name
- fallback to submitted name when Global Names fails
- fallback to submitted name when Global Names returns no match
- propagation of compact `name_resolution` into structured source output
- source-specific behavior for at least one rich profile

Frontend coverage for this iteration can remain at:

- preset/config transport checks where applicable
- `pnpm build`

## Operational Notes

- Global Names is a network dependency and should be treated as best effort
- responses should be cached along the same lines as existing structured provider calls when caching is enabled
- provider pipelines should not need to know Global Names internals; they should only receive the selected query string and the compact resolution summary

## External References

- [Global Names Verifier API](https://resolver.globalnames.org/api)
- [Global Names Verifier overview](https://resolver.globalnames.org/about)
- [Global Names Parser API](https://parser.globalnames.org/doc/api)
