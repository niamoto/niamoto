# Publish UI Simplification Design

## Summary

Refactor the GUI `Publish` module from a four-view sidebar-driven mini-dashboard into a single workflow-oriented desktop screen for Tauri.

The new primary flow is:

1. Generate site
2. Preview site
3. Put site online

Advanced concerns such as deployment destination management, full history, logs, health checks, and destructive actions remain available, but move out of the primary path into secondary panels or dialogs.

This design is intended to improve comprehension for non-technical users while preserving the existing backend capabilities and most of the current state model.

## Problem Statement

The current `Publish` module exposes internal system structure rather than the user task:

- a dedicated sidebar with `Overview`, `Build`, `Deploy`, and `History`
- duplicated preview surfaces
- a build screen that mixes generation, output education, metrics, and preview
- a deploy screen that foregrounds multi-platform operations before the user has completed the basic publish task
- a history screen elevated to the same navigation level as the main workflow

For a desktop app, this reads more like an operations console than a guided publication workflow.

## Goals

- Make the primary user path obvious on first visit
- Reduce top-level navigation inside `Publish`
- Keep advanced actions available without forcing them into the main screen
- Reuse as much existing logic as possible
- Preserve compatibility with existing backend endpoints and existing publish state
- Keep old URLs functional during migration

## Non-Goals

- Rebuild deployment logic or backend job orchestration
- Change the export pipeline semantics
- Change deployment platform support
- Redesign the entire application shell outside the `Publish` module

## Design Principles

- Workflow first: show the next meaningful action before secondary data
- One preview surface only
- One primary CTA per section
- Progressive disclosure for technical detail
- Desktop-friendly vertical flow instead of a nested module dashboard

## Target Information Architecture

### Primary surface

`/publish` becomes the single primary screen.

It contains five ordered sections:

1. `PublishStatusHeader`
2. `GenerateSection`
3. `PreviewSection`
4. `DeploymentSection`
5. `RecentActivitySection`

### Secondary surfaces

Secondary functionality moves into non-primary surfaces:

- `ManageDestinationsDialog`
- `PublishHistoryDialog`
- `DeploymentLogsDialog`

These surfaces are opened from the main `/publish` screen via buttons or query-param controlled panels.

## User Experience

### Top header

The header answers one question: is the site ready to publish?

Displayed state examples:

- `Never generated`
- `Generating…`
- `Up to date`
- `Out of date`
- `Deploying…`

It also keeps the page title and one-line explanation:

- Title: `Publish`
- Subtitle: `Generate your site, review it, and put it online.`

### Section 1: Generate Site

This section contains:

- the last generation summary
- the single primary generation action
- a compact progress state
- optional advanced generation settings

Visible information:

- last generation time
- file count
- duration
- export directory

Visible actions:

- `Generate Site`
- `Regenerate Site`

Advanced options are collapsed by default and contain:

- `Recompute statistics before generation`

Detailed target breakdown such as website/API/Darwin Core stays hidden behind a disclosure area instead of occupying first-level space.

### Section 2: Preview Site

This section becomes the only preview surface in the module.

If no build exists:

- empty state explaining that a generated site is required

If a build exists:

- generated-site iframe preview
- device switcher
- `Open in New Tab`

No duplicate preview remains in separate `overview` and `build` screens.

### Section 3: Put Online

This section focuses on the next publication action, not on the full deployment configuration matrix.

If no destination is configured:

- empty state
- `Set Up a Destination`

If at least one destination exists:

- one primary destination card
- status
- last deployment time
- live URL when available

Primary actions:

- `Deploy`
- `View Live Site`
- `Manage Destinations`

If the site is stale or not generated, the section blocks deployment and points back to generation with a single clear CTA.

### Section 4: Recent Activity

This section shows only a short recent activity summary, for example:

- last build
- last deploy
- last failure

It ends with:

- `View Full History`

The full tabular history moves out of the main page.

## Component Design

### `PublishModule`

Current responsibility:

- route-to-view orchestration for four sub-pages
- sidebar-driven module layout

Target responsibility:

- bootstrap publish state
- render a single main publish page
- optionally open secondary panels from URL query state

### `PublishTree`

Current responsibility:

- top-level navigation between overview/build/deploy/history

Target:

- remove from the main publish flow
- optionally keep only during migration, then delete

### `GenerateSection`

Source logic to reuse:

- build action
- build progress state
- build success/error handling
- include-transform option

Source file:

- `src/niamoto/gui/ui/src/features/publish/views/build.tsx`

### `PreviewSection`

Source logic to reuse:

- exported preview iframe helpers
- dynamic preview fallback already present in the current overview

Source files:

- `src/niamoto/gui/ui/src/features/publish/views/index.tsx`
- `src/niamoto/gui/ui/src/features/publish/views/build.tsx`

### `DeploymentSection`

Source logic to reuse:

- deploy action
- destination state
- URL/state display

Source file:

- `src/niamoto/gui/ui/src/features/publish/views/deploy.tsx`

Target scope on the main page:

- primary destination card
- deploy CTA
- access to destination management

Advanced operations stay in dialogs:

- add/edit destination
- delete destination
- unpublish
- health checks
- logs

### `PublishHistoryDialog`

Source logic to reuse:

- history tables
- clear history actions

Source file:

- `src/niamoto/gui/ui/src/features/publish/views/history.tsx`

## Routing Strategy

Primary route remains:

- `/publish`

Old routes stay temporarily compatible and redirect:

- `/publish/build` -> `/publish`
- `/publish/deploy` -> `/publish?panel=destinations`
- `/publish/history` -> `/publish?panel=history`

This preserves external links and user habits during migration.

## State Strategy

The existing `publishStore` remains the source of truth for:

- current build
- current deploy
- build history
- deploy history
- configured deployment platforms

Small additions are allowed for derived selectors, for example:

- last build
- last deploy
- has fresh build
- primary destination

No major store rewrite is required in the first iteration.

## Content Strategy

Preferred wording for the new flow:

- `Generate Site` instead of `Build`
- `Preview Site`
- `Put Online` or `Deploy Site` instead of raw `Deploy`
- `Recent Activity` instead of top-level `History`

The UI should prefer user-task language over infrastructure language.

## Migration Plan

### Phase 1: structural refactor

- create the new single-page composition
- reuse current logic from `build`, `deploy`, and `history`
- keep old routes working via redirects

### Phase 2: reduce duplication

- remove duplicate preview surfaces
- move advanced deployment operations into dialogs
- simplify the main page to one primary action per section

### Phase 3: cleanup

- remove obsolete sidebar navigation
- remove dead standalone views if no longer needed
- clean up i18n keys and intermediate compatibility code

## Risks

- deploy view extraction may be noisy because the current file mixes simple and advanced concerns
- preview logic currently lives in more than one place and needs careful consolidation
- route compatibility must be preserved during migration to avoid broken links inside the app

## Validation Plan

### Functional checks

- user can generate, preview, and deploy from `/publish` without navigating elsewhere
- old `/publish/build`, `/publish/deploy`, and `/publish/history` URLs still resolve correctly
- preview appears in one place only
- advanced deployment configuration remains accessible

### UX checks

- first-time user can identify the next action within a few seconds
- stale state clearly directs the user to regenerate before deploying
- history does not dominate the main screen

### Technical checks

- `pnpm build`
- targeted tests for publish routing and publish UI behavior
- smoke test for preview, build, deploy, and history dialogs

## Acceptance Criteria

- `Publish` no longer behaves as a four-view dashboard module
- the main publish workflow is readable as a single vertical sequence
- preview duplication is removed
- destination management and full history are secondary, not primary
- the refactor preserves existing backend APIs and publish capabilities
