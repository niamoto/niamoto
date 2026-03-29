# Sources Mission Control Design

## Summary

Refactor the GUI `Data` / `Sources` overview at `/sources` into a durable workspace with two clearly distinct states:

1. An initial empty state with a dropzone for first launch and pre-import use
2. A post-import `Mission control` workspace organized around the three real user intentions that follow import:
   - verify imported data
   - enrich references
   - prepare static pages

This design keeps `/sources` as the single entry point of the `Data` module while making the page immediately understandable for first-time users and still useful when they come back later to review, enrich, or continue configuration.

## Problem Statement

The current `/sources` overview has improved compared to the older import flow, but it still presents the workspace too much from the system structure rather than from the user task:

- aggregation groups are the main visual object before the user understands what they should do next
- analysis tools are visible, but not clearly framed as a single “verify data” job
- enrichment is important, but remains partially hidden behind reference detail screens
- the page tries to serve as both a post-import recap and an ongoing workspace without a strong hierarchy between those roles
- group cards carry too much information and too many actions at once

For first-time users, the page does not immediately answer:

- what should I do now?
- what is optional versus recommended?
- where do I enrich?
- when do I move to `Groups`?

## Goals

- Make `/sources` understandable on first use without prior knowledge of Niamoto’s internal concepts
- Keep `/sources` useful as a durable workspace after the first import
- Present the three primary post-import jobs explicitly
- Allow enrichment to be configured and launched directly from `/sources`
- Keep imported groups visible without making them the only top-level mental model
- Preserve the existing import review flow and reference detail screens where they still add value

## Non-Goals

- Rebuild the import wizard from scratch
- Move page configuration into `/sources`
- Remove dataset or reference detail screens
- Redesign the whole `DataTree` navigation in the same iteration
- Replace the existing analysis views themselves

## Design Principles

- One entry point for the whole `Data` module
- Two radically different states are better than one overloaded hybrid
- Show user jobs before system objects
- Keep the workspace useful on return visits, not just right after import
- Use secondary panels for complex detail instead of expanding the main page
- Keep group summaries compact and intentional

## Target Information Architecture

### State 1: No imported data

If no dataset or reference is available, `/sources` shows an initial landing state for the module.

This state contains:

- page title and short explanation
- a large dropzone
- a `Choose files` fallback button
- short help text about supported formats
- three short reassurance points:
  - automatic detection of datasets, references, and layers
  - review before final import
  - ability to update files later

This is not a dashboard. It is a focused entry screen for getting files into the project.

Dropping files here does not replace the import workflow. It is only the entry point into the existing upload / review / import flow.

### State 2: Imported workspace

Once data exists, `/sources` becomes a durable `Mission control` workspace.

The page is organized into the following sections:

1. Workspace header
2. `Verify data`
3. `Enrich references`
4. `Prepare static pages`
5. `Groups overview`
6. `Supporting sources`

## User Experience

### Workspace header

The header keeps a light workspace identity:

- badge such as `Imported workspace`
- page title
- short explanatory sentence
- secondary actions such as `Refresh` and `Re-import`

The header should remain concise. It should not try to summarize every count or every system state.

### Section 1: Verify data

This section reframes the existing analysis tools as one coherent job: validating the imported data before proceeding.

It contains:

- a summary state:
  - `No issue detected`
  - or `2 things to review`
- short explanatory text
- compact access to existing analysis views:
  - field availability
  - validation
  - taxonomy checks
  - spatial coverage
- a main action such as `Open checks`

The analysis tools should no longer appear as a generic band of equally weighted technical tiles. They become one quality-control surface.

Warnings remain visible, but they should support this section rather than compete with the whole page hierarchy.

### Section 2: Enrich references

This section makes enrichment a first-class workflow visible directly from `/sources`.

It contains:

- a compact global summary:
  - how many references can be enriched
  - how many are already configured
- a short list of relevant references with per-reference state:
  - `Not configured`
  - `Configured`
  - `Ready to run`
  - `Last run failed`
- a primary action per listed reference:
  - `Configure`
  - `Run now`
  - `Manage`

The section must support direct work from the page, not just redirection.

#### Enrichment interaction model

Detailed enrichment setup and execution opens in a secondary panel, not inline in the main page.

Recommended interaction:

- user clicks `Configure` / `Run now` / `Manage`
- a right-side sheet opens for the selected reference
- the sheet contains:
  - enable/disable controls
  - API / plugin configuration
  - save action
  - run action if already configured
  - recent status when available
- after save or run, the `Enrich references` section refreshes and reflects the new state

This keeps enrichment actionable from `/sources` without turning the page into a configuration wall.

Reference detail pages remain useful as deeper detail surfaces, but they are no longer the primary entry point for enrichment.

### Section 3: Prepare static pages

This section explicitly bridges the user from imported data into the `Groups` module.

It contains:

- a summary such as `3 groups available for page configuration`
- a short explanatory sentence:
  - choose widgets, data sources, and index pages for each group
- a compact list of groups with high-level readiness state:
  - `Ready`
  - `Enrichment recommended`
  - `Needs review`
- a primary action:
  - `Open Groups`

This section does not reimplement `Groups`. Its role is to frame the transition clearly.

### Section 4: Groups overview

Groups remain visible because they are central project resources, but they are demoted from “main cards that try to do everything” to a compact overview block.

The purpose of this section is:

- show what is available
- show each group’s main state
- provide only the most relevant next action

Each group summary should include:

- group name
- kind
- compact metrics:
  - row count
  - field count
- one main status:
  - `Needs review`
  - `Enrichment available`
  - `Enrichment configured`
  - `Ready for pages`
- two or three actions maximum

Recommended actions:

- `Check`
- `Configure enrichment` or `Manage enrichment`
- `Open in Groups`

Current card elements that should be removed from the first level:

- large field preview blocks
- duplicate “next step” content areas
- too many badges in parallel
- long action bars with many equivalent choices

### Section 5: Supporting sources

Supporting datasets and layers remain useful, but this section is explicitly secondary.

It should stay below the mission-control actions and the group overview.

Its role is:

- confirm which source files and tables support the workspace
- allow updates or detail access when needed

This section should not compete visually with the three primary jobs above.

## Component and Interaction Design

### `DataModule`

Current responsibility:

- route orchestration for overview, dataset detail, reference detail, and import wizard

Target responsibility after this design:

- continue routing as today
- keep `/sources` as the single entry point
- render either:
  - an empty-state import landing page
  - or the imported `Mission control` page

### Initial import landing surface

Recommended implementation shape:

- a dedicated component such as `SourcesEmptyState`
- reuse the existing upload mechanics where possible
- do not duplicate all of `ImportWizard` inside this component

The empty state only starts the import flow. Review and confirmation remain in the current import workflow.

### `ImportDashboard`

Current responsibility:

- post-import summary page centered on aggregation groups

Target responsibility:

- become the `Mission control` workspace
- reorganize its hierarchy around the three primary jobs
- simplify group summaries
- reduce the visual prominence of supporting sources

### Enrichment secondary surface

Recommended implementation shape:

- a dedicated sheet component such as `EnrichmentWorkspaceSheet`
- fed from the same backend capabilities currently used by the reference enrichment tab

This surface should reuse existing enrichment form logic where possible, but the user should not have to navigate to reference detail just to access it.

## Navigation Model

### First launch

The user enters `/sources` and sees:

- a dropzone
- basic reassurance about the workflow

After files are dropped:

- existing upload / analysis / review flow begins

After successful import:

- the user lands back on `/sources`
- the page is now the imported `Mission control` workspace

### Return visits

When users come back later, `/sources` is no longer a recap screen. It is the control surface for:

- re-checking imported data
- configuring or running enrichment
- moving into `Groups`
- confirming available groups and supporting sources

## Copy Strategy

The page should use product language before technical language.

Preferred user-facing framing:

- `Verify data`
- `Enrich references`
- `Prepare static pages`

Avoid making words like `dataset`, `reference`, `layer`, or `aggregation group` the first concepts users must understand on this page.

These concepts still exist, but should appear lower in the visual hierarchy or in detail views.

## Migration Strategy

### Phase 1

- Introduce the explicit two-state `/sources` entry:
  - dropzone state
  - imported workspace state

### Phase 2

- Reorganize `ImportDashboard` into the three mission-control zones
- keep existing backend calls and side sheets where possible

### Phase 3

- Add direct enrichment sheet entry from `/sources`
- simplify group cards and supporting source presentation

### Phase 4

- Review sidebar and terminology alignment if needed
- remove any now-redundant call-to-action duplication

## Validation Criteria

The design is successful if:

- a first-time user can understand where to start without prior explanation
- after import, the user can identify the three available next jobs immediately
- enrichment is discoverable and actionable from `/sources`
- the page still feels useful when revisited later
- the transition to `Groups` is explicit and understandable
- the page no longer feels like a recap plus an unrelated cluster of cards

## Risks and Watchouts

- The three top sections must remain compact. If they become large dashboards themselves, the page will regress into visual sprawl.
- The enrichment secondary panel must reuse existing logic carefully to avoid drifting behavior between `/sources` and reference detail.
- Group summaries should be simplified aggressively, or the page will still feel overloaded even if the top hierarchy improves.
- The empty import landing state must not accidentally fork the import flow into a second inconsistent implementation.
