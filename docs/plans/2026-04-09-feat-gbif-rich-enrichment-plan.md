---
title: "feat: implement rich GBIF enrichment pipeline"
type: feat
date: 2026-04-09
spec: docs/superpowers/specs/2026-04-09-gbif-rich-enrichment-design.md
---

# feat: implement rich GBIF enrichment pipeline

## Overview

Implement the `GBIF Rich` enrichment profile described in the approved design spec while preserving the existing multi-source enrichment workflow.

The implementation should keep GBIF as a single source in the UI and configuration model, but upgrade its runtime behavior from a flat one-request mapping to a structured four-block pipeline:

- `match`
- `taxonomy`
- `occurrence_summary`
- `media_summary`

The main product outcome is a GBIF source that produces durable, reusable summaries in `extra_data`, richer preview output in the workspace, and a much stronger value proposition for the 2026 GBIF challenge.

## Constraints

- Do not split GBIF into multiple UI sources
- Do not introduce a dedicated `gbif_enricher` plugin in this iteration
- Do not store full occurrence lists or full raw payloads permanently in `extra_data`
- Keep the current `api_taxonomy_enricher` entry point as the public source plugin
- Preserve backward compatibility for existing enrichment sources and existing result views

## Files in Scope

### Backend

- `src/niamoto/core/plugins/loaders/api_taxonomy_enricher.py`
- `src/niamoto/core/imports/config_models.py`
- `src/niamoto/gui/api/services/enrichment_service.py`
- `src/niamoto/gui/api/routers/enrichment.py`

### Frontend

- `src/niamoto/gui/ui/src/features/import/components/enrichment/ApiEnrichmentConfig.tsx`
- `src/niamoto/gui/ui/src/features/import/components/enrichment/EnrichmentTab.tsx`
- `src/niamoto/gui/ui/src/features/import/components/enrichment/enrichmentSources.ts`
- `src/niamoto/gui/ui/src/i18n/locales/fr/sources.json`
- `src/niamoto/gui/ui/src/i18n/locales/en/sources.json`

### Tests

- `tests/core/imports/test_config_models.py`
- `tests/gui/api/services/test_enrichment_service.py`
- `tests/gui/api/routers/test_enrichment.py`

## Technical Approach

### Architecture Decision

GBIF should be implemented as a structured provider profile inside the existing generic enrichment source model.

The implementation will add a `profile: gbif_rich` path to the current loader and service pipeline instead of introducing a separate provider plugin.

This gives us:

- a single GBIF source in the UI
- richer provider-specific runtime behavior
- minimal churn in the multi-source orchestration layer
- a migration path to a dedicated provider layer later if needed

## Implementation Phases

### Phase 1: Extend the config model for structured profiles

**Goal**

Allow source configs to declare a richer provider profile and GBIF-specific block toggles without breaking existing flat sources.

**Tasks**

- Add optional structured profile fields to the source config normalization path
  - `profile`
  - `taxonomy_source`
  - `include_taxonomy`
  - `include_occurrences`
  - `include_media`
  - `media_limit`
- Ensure `EnrichmentSourceConfig` in `enrichment_service.py` carries these fields
- Ensure serialization back to `import.yml` preserves these fields
- Update `config_models.py` so the underlying loader config validates the structured GBIF fields
- Keep all fields optional so existing sources continue to normalize unchanged

**Verification**

- targeted config model tests
- normalization tests for legacy and new configs

### Phase 2: Implement `gbif_rich` runtime in the loader

**Goal**

Teach `api_taxonomy_enricher` to recognize `profile: gbif_rich` and run a multi-step GBIF pipeline instead of the current flat request + `response_mapping` flow.

**Tasks**

- Add a profile dispatch path in `ApiTaxonomyEnricher.load_data`
- Keep the current flat request flow as the default for non-GBIF sources
- Implement a private GBIF pipeline with explicit steps:
  - `_gbif_match`
  - `_gbif_taxonomy`
  - `_gbif_occurrence_summary`
  - `_gbif_media_summary`
- Normalize all GBIF identifiers as strings
- Use `v2/species/match` as the match endpoint
- Prefer `COL XR` by default when the source does not override `taxonomy_source`
- Return a structured payload with:
  - `api_enrichment`
  - `api_response_raw`
  - optional `api_response_processed`
- Shape `api_enrichment` as the final summary object stored in `extra_data`
- Shape `api_response_raw` as the preview-oriented debug payload, grouped by GBIF block

**Important behavior**

- `match` is mandatory
- `taxonomy`, `occurrences`, and `media` are best-effort
- no-match returns a structured `no_match` outcome, not a generic exception
- partial secondary failure still returns a usable summary

**Verification**

- unit-style loader tests for:
  - successful structured result
  - no match
  - partial taxonomy failure
  - partial occurrence failure
  - media truncation
  - non-numeric or alphanumeric key handling

### Phase 3: Upgrade the service layer to understand structured source summaries

**Goal**

Preserve the existing multi-source orchestration while teaching preview, results, and persisted enrichment handling to work with structured GBIF blocks.

**Tasks**

- Update `_merge_source_enrichment_data` in `enrichment_service.py` if needed so structured GBIF summaries are stored as-is under `sources.<source_id>.data`
- Preserve source-local status and error metadata
- Extend `PreviewSourceResult` usage so the preview can carry:
  - `data` as structured summary
  - `raw_data` as grouped raw payload
  - block-level error/status info where needed
- Make sure `get_results()` and persisted fallbacks return structured `data` for GBIF without flattening it
- Add any small router updates in `enrichment.py` needed to preserve request/response compatibility

**Verification**

- service tests for preview and result payload shapes
- router tests for preview endpoint behavior

### Phase 4: Add the `GBIF Rich` preset and source options in the UI

**Goal**

Expose the structured GBIF source in the existing workspace configuration flow without introducing a new interaction model.

**Tasks**

- Replace or upgrade the current GBIF preset in `ApiEnrichmentConfig.tsx`
- Add preset fields for:
  - `profile: gbif_rich`
  - `taxonomy_source`
  - `include_taxonomy`
  - `include_occurrences`
  - `include_media`
  - `media_limit`
- Ensure preset selection renames the source label consistently to `GBIF`
- Decide which knobs are shown by default versus under an advanced section
- Keep the source visually aligned with the current source editor and workspace layout

**Verification**

- manual preset selection check
- saved config roundtrip
- `pnpm build`

### Phase 5: Render structured GBIF previews and results in the workspace

**Goal**

Make `Tester l’API` and `Résultats` display GBIF as a structured, high-value enrichment source rather than a flat key-value dump.

**Tasks**

- In `EnrichmentTab.tsx`, detect structured GBIF payloads and render dedicated sections:
  - `Match`
  - `Taxonomy`
  - `Occurrences`
  - `Media`
- Keep `Réponse brute API` as a separate view
- Do not remove the existing generic mapped/raw rendering path used by Endemia and other sources
- Add partial-state rendering:
  - show missing blocks as unavailable
  - do not present the entire source as broken when only a secondary block failed
- Keep the quick panel compact:
  - last resolved name or status
  - occurrence count badge when available
  - country count badge when available
- Avoid overloading the quick panel with all GBIF blocks

**Verification**

- render check with one GBIF source beside Endemia
- `pnpm build`

### Phase 6: Final tests and docs touch-up

**Goal**

Ship the feature with targeted regression coverage and enough documentation for future maintainers.

**Tasks**

- Update or add targeted backend tests in:
  - `tests/core/imports/test_config_models.py`
  - `tests/gui/api/services/test_enrichment_service.py`
  - `tests/gui/api/routers/test_enrichment.py`
- Validate with the subset instance config
- Update docs only if the user-facing enrichment workflow changed materially
  - likely `docs/06-gui/operations/import.md` only if the richer GBIF behavior needs explicit mention

**Verification commands**

- `uv run pytest tests/core/imports/test_config_models.py tests/gui/api/services/test_enrichment_service.py tests/gui/api/routers/test_enrichment.py -q`
- `cd src/niamoto/gui/ui && pnpm build`

## Suggested Commit Breakdown

Keep commits scoped by concern:

1. `feat: add gbif rich profile config and runtime`
2. `feat: expose structured gbif previews and results`
3. `test: cover gbif rich enrichment flow`
4. `docs: document gbif rich enrichment behavior`

This can collapse to fewer commits if the implementation is tightly coupled, but the boundaries above are the intended shape.

## Acceptance Criteria

- A source configured with the GBIF preset no longer relies on the old flat `species/match` mapping only
- GBIF summaries are stored under the existing namespaced source path in `extra_data`
- `usage_key` is handled as a string-compatible identifier
- Preview exposes structured GBIF blocks plus raw payload inspection
- Results render meaningful GBIF summaries without flattening the source back into a generic table
- Existing non-GBIF sources still work
- Existing enrichment quick panel and workspace continue to build and run

## Risks

- GBIF endpoints are more modular than Endemia, so the runtime can become too provider-specific if the helper layer is not kept disciplined
- The current loader was designed for flat mappings, so the new profile path must not make the generic code path harder to reason about
- Preview and results rendering can regress other sources if GBIF-specific branching is too broad
- High-level taxa may still return sparse GBIF summaries; the UI must communicate that this is a valid provider outcome, not necessarily a bug

## Notes for Implementation

- Prefer extracting small GBIF-specific helpers over expanding one very large method in `api_taxonomy_enricher.py`
- Keep the generic rendering path intact in `EnrichmentTab.tsx`
- Use the subset instance config as the working test case
- Do not touch unrelated enrichment sources while implementing the GBIF profile
