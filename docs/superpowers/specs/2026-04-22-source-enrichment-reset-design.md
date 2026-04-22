# Source Enrichment Reset Design

**Date**: 2026-04-22
**Status**: Approved design
**Scope**: Add a source-scoped "restart from zero" enrichment flow that overwrites existing data for one selected source

## Summary

Add a new source-level enrichment action that reruns the currently selected source across all entities, even when that source already has stored enrichment data.

The product intent is:

- keep the current resume behavior as the default start action
- add a second explicit action for "restart from zero"
- scope the reset strictly to the selected source
- replace stored source data when fresh data is returned
- remove stored source data when the new run returns no usable data
- preserve existing source data on technical errors

This design does not reset other sources, does not add a global reset-all flow, and does not change the current pause/resume/cancel model.

## Problem Statement

Today, starting enrichment for a selected source resumes from the remaining pending entities only.

That is correct for incremental completion, but it prevents a user from intentionally refreshing one source when:

- the external API content changed
- field mappings changed
- a provider improved or removed matches
- the user wants to revalidate old stored data against the current remote source

The current runtime also treats "already enriched" as a hard skip. As a result, users cannot ask Niamoto to recompute one source end to end without manually altering stored data outside the workflow.

## Goals

- Let users rerun the selected source across all entities
- Replace existing stored data for that source when new valid data is returned
- Remove existing stored data for that source when the new run returns no usable data
- Keep other enrichment sources untouched
- Keep the current resume behavior available and unchanged
- Make the reset action explicit enough that users understand it is destructive for that source only
- Clarify the difference between run completion and persisted enrichment counts

## Non-Goals

- Reset all sources for a reference in V1
- Add a global destructive "wipe enrichment" action
- Change the existing default start button into destructive behavior
- Modify provider-specific enrichment logic beyond the source reset orchestration
- Redesign the whole enrichment workspace

## Product Decision

The approved product behavior is:

- the selected source gets a dedicated `Restart from zero` action
- the existing play action remains the normal non-destructive resume/completion flow
- restart from zero affects only the selected source
- when the new run returns valid data, the old payload for that source is replaced
- when the new run returns no usable data, the old payload for that source is deleted
- when the new run fails due to a technical error, the old payload for that source is kept

This preserves safe defaults while making a full source refresh intentionally available.

## User Experience

### Source Toolbar

For the selected source in the enrichment workspace:

- keep the existing start action for the normal resume/completion flow
- add a second source-level action: `Restart from zero`

The new action should live next to the existing run controls in the active source toolbar, not in a distant overflow menu.

### Confirmation

`Restart from zero` must open a confirmation dialog before the job starts.

Confirmation copy:

- title: `Restart this source from zero?`
- body: `This reruns the selected source for all entities. Existing data for this source will be replaced when new data is found, and removed when no result is returned. Other sources are not affected.`

This confirmation is required because the action can remove previously stored source data.

### Runtime Wording

The UI currently mixes two concepts:

- run progress for the current attempt
- persisted enrichment counts stored in the database

This becomes more visible during reset runs, especially when some entities produce no data.

The design therefore requires clearer wording:

- run progress labels should describe `attempts completed`
- persisted source progress should continue to describe `stored enriched entities`

The design does not require a full new counter model in V1, but it does require avoiding wording that implies every completed attempt produced stored data.

## API Design

Add a dedicated route:

- `POST /enrichment/restart/{reference_name}/{source_id}`

Reasons for a dedicated route instead of a hidden query parameter or boolean:

- the action is materially different from the normal start flow
- the destructive semantics are easier to reason about
- logs, tests, and UI intent are clearer

The route starts a single-source job that uses reset behavior for that source.

## Runtime Model

### Job Scope

This remains a single-source enrichment job.

Existing `mode = single` behavior should be preserved. The reset behavior must be represented separately from `mode` through a dedicated job strategy field.

- keep `mode` as `all | single`
- add `strategy` with:
  - `resume`
  - `reset`

This keeps current consumers stable while making the new behavior explicit.

### Row Selection

Normal single-source jobs currently skip rows that already have completed source data.

Reset jobs must not skip those rows.

For a reset job:

- all entities for the selected source are candidates
- existing stored source payloads do not exclude a row from processing

## Persistence Rules

Persistence is the core behavior of the feature.

For each processed entity of the selected source:

### 1. New valid source data returned

- replace the existing payload for `api_enrichment.sources.<source_id>`
- keep all other source payloads unchanged

### 2. No usable source data returned

- delete `api_enrichment.sources.<source_id>` for that entity
- keep all other source payloads unchanged

### 3. Technical error

- do not modify the existing stored payload for that source
- record the run failure in runtime results

This distinction is essential:

- empty result is a meaningful product outcome and must clear stale data
- technical failure is not evidence that the old data is invalid

## Data Update Helpers

The backend should add source-scoped helpers instead of overloading the current merge-only path.

Required helper responsibilities:

- `replace_source_enrichment_data(...)`
- `delete_source_enrichment_data(...)`

Deletion must remove only the targeted source payload. If the deleted source was the last stored source, cleanup should also remove empty enrichment containers so the stored JSON remains tidy and semantically clear.

## Stats and Progress

### Persisted Source Stats

Persisted source stats must continue to reflect only entities that currently store valid data for that source.

After a reset run completes, the source bar and per-source counts must be recomputed from persisted state, so the final `X / Y` count reflects the new database state.

### Run Progress

Reset runs operate over all entities of the selected source.

Therefore:

- the run total should be based on the full entity count for that source
- the run progress should describe processed attempts
- it should not imply that all processed attempts produced stored enrichment

This matters because a reset can validly end with:

- all attempts completed
- fewer stored enriched entities than before

## Backend Design

### Router

Add a new source-scoped restart route in the enrichment router and map it to a dedicated service entry point.

### Service Entry Point

Add a new service function:

- `restart_reference_enrichment(reference_name, source_id)`

Responsibilities:

- reject restart when a non-terminal job is already active
- validate that the requested source exists and is enabled
- create a single-source job with reset strategy
- start the background task with reset behavior enabled

### Background Worker

The worker should support two execution strategies:

- `resume`: current behavior
- `reset`: process all rows for the selected source

For `reset`:

- do not use `_has_completed_source(...)` as a skip gate
- still use current provider execution and rate limiting
- branch persistence by outcome:
  - valid data -> replace
  - empty usable response -> delete
  - exception -> preserve existing data

## Frontend Design

### Source-Level Action

In the enrichment workspace header for the active source:

- keep the existing start action
- add a dedicated `Restart from zero` action
- disable it under the same runtime constraints as other job actions

### Confirmation Flow

The frontend should show a confirmation dialog before calling the new route.

Once confirmed:

- call `POST /enrichment/restart/{reference_name}/{source_id}`
- start polling as with the existing run actions
- refresh stats after terminal completion

### User Feedback

Toast wording should distinguish the reset flow from the normal start flow.

Toast copy:

- title: `Restart started`
- description: `The selected source is being recomputed from zero. Existing stored data for this source may be replaced or removed.`

## Results and Error Semantics

The recent results area should continue to show runtime outcomes, but the implementation must preserve the semantic difference between:

- successful enrichment with stored data
- completed attempt with no result
- technical failure

The design does not require a full new UI results taxonomy in V1, but backend result creation must make it possible to distinguish empty-result outcomes from technical exceptions if the UI is later refined.

## Testing Strategy

### Backend Tests

Add targeted tests for:

- source restart starts a single-source reset job
- reset processing does not skip already-enriched rows
- valid data replaces existing source payloads
- empty result deletes existing source payloads
- technical exception preserves existing source payloads
- reset completion recomputes persisted source stats correctly
- other source payloads remain untouched

### Router Tests

Add route coverage for:

- successful `POST /enrichment/restart/{reference_name}/{source_id}`
- invalid source
- disabled source
- active-job conflict

### Frontend Tests

Add tests for:

- `Restart from zero` action visibility on the active source
- confirmation dialog before API call
- call to the new restart route
- polling and final stats refresh after restart
- UI wording that separates completed attempts from persisted enriched counts

## Rollout Notes

This feature should be implemented as an additive path:

- current start/resume behavior remains untouched for existing users
- reset is explicit and opt-in
- the backend route and runtime strategy can land before any broader enrichment analytics work

That keeps the change narrowly focused on the real product need: refreshing one source completely without manual data surgery.
