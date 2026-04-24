---
title: refactor: Strengthen Site workbench preview persistence
type: refactor
status: active
date: 2026-04-23
origin: docs/superpowers/specs/2026-04-23-site-workbench-preview-design.md
---

# refactor: Strengthen Site workbench preview persistence

## Overview

Refine the existing `Site` workbench so the right-hand preview behaves like a
stable part of the editing flow instead of a secondary optional panel. The work
stays entirely in the frontend `Site` feature and focuses on three visible
outcomes:

- preview opens more predictably for previewable selections
- explicit user preview choices are remembered per project
- the `SiteBuilder` header becomes quieter by removing preview-local controls

The goal is not to redesign `Site`. It is to make the current split layout feel
more like a desktop workbench.

## Problem Frame

The approved design in
`docs/superpowers/specs/2026-04-23-site-workbench-preview-design.md`
identifies that Niamoto already has the right structure in
`src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`: a left tree,
a center editor, and a right preview. The main gap is behavioral continuity.

Today:

- preview state is owned directly inside `SiteBuilder` and defaults to a local
  transient toggle
- there is no project-scoped memory for preview open/closed state, device, or
  width
- preview controls are split between the main header and the preview surface
- the existing tests cover empty-state regressions, but not workbench preview
  behavior

This plan therefore treats the work as a bounded frontend refactor that
stabilizes preview behavior without changing save flows, API contracts, or site
data structures.

## Requirements Trace

- R1. Open the preview automatically for previewable `Site` selections when no
  explicit local preference says otherwise.
- R2. Respect an explicit user close/open choice for the current project.
- R3. Persist the minimum useful workbench context locally per project:
  preview open state, preview device, and preview width.
- R4. Remove preview-local controls from the main `SiteBuilder` header while
  preserving save and current module context.
- R5. Keep the implementation local to the frontend `Site` surface and protect
  the behavior with targeted Vitest coverage.

## Scope Boundaries

- Do not add a new inspector panel.
- Do not change backend APIs, config models, or persisted site settings.
- Do not rewrite `useSiteBuilderState` into a new architecture.
- Do not redesign `UnifiedSiteTree`, page editors, or group editors.
- Do not add a large new desktop preference store for one feature.

### Deferred to Separate Tasks

- Reuse the same workbench persistence pattern in other modules only after this
  `Site` trial proves valuable.
- Revisit a contextual inspector only after preview-first behavior has been
  validated in real usage.

## Context & Research

### Relevant Code and Patterns

- `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx` already
  owns preview eligibility, layout composition with `ResizablePanelGroup`, and
  the top header that currently exposes preview toggle controls.
- `src/niamoto/gui/ui/src/features/site/components/SiteBuilderPreview.tsx`
  already isolates page and group preview rendering and forwards device and
  refresh controls to `PreviewFrame`.
- `src/niamoto/gui/ui/src/components/ui/preview-frame.tsx` already provides the
  right local preview contract: device switch, refresh button, loading state,
  close button, and empty state.
- `src/niamoto/gui/ui/src/components/content/previewPolicy.ts` and
  `src/niamoto/gui/ui/src/components/content/previewPolicy.test.ts` show the
  preferred pattern for small local-storage helpers: pure normalization and
  read/write functions with deterministic tests.
- `src/niamoto/gui/ui/src/shared/hooks/useProjectSwitcher.ts` shows how the
  desktop shell exposes the current project path via `get_current_project`, but
  the hook itself is broader than this feature needs.
- `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx` is the
  current entry point for `SiteBuilder` regression tests and can be extended for
  preview-state scenarios.

### Institutional Learnings

- No relevant `docs/solutions/` learning currently covers local workbench
  persistence or `Site` preview behavior.

### External References

- None. Local patterns are sufficient for this plan.

## Key Technical Decisions

- Use a small feature-local preference layer instead of a new global store.
  Rationale: this behavior is specific to `Site` and should stay cheap to
  reason about and test.
- Model preview openness as a persisted explicit preference plus an “unset”
  default path. Rationale: the feature must distinguish “auto-open by default”
  from “the user explicitly closed it”.
- Scope local storage keys to the current project identifier, preferring the
  desktop project path when available. Rationale: a preview habit in one project
  should not leak into another.
- Keep preview-specific controls in `PreviewFrame` / `SiteBuilderPreview`
  instead of the `SiteBuilder` header. Rationale: control ownership should match
  visual ownership.
- Treat preview-width persistence as a library-capability check during
  implementation. Rationale: if the installed panel library supports persisted
  layouts directly, use it; otherwise store a minimal width/layout value in the
  new preference layer.

## Open Questions

### Resolved During Planning

- Should this work introduce a right-hand inspector? No. The approved direction
  is preview-first, not inspector-first.
- Should these preferences be stored in backend config or `site.yml`? No. They
  are local workbench preferences and remain UI-only.
- Should `SiteBuilder` reuse `useProjectSwitcher` directly to build a storage
  scope? No. The feature should use a lighter current-project scope helper so it
  does not subscribe to recent-project management it does not need.

### Deferred to Implementation

- Whether the installed `react-resizable-panels` version exposes built-in layout
  persistence in a way compatible with the current wrapper component. This is a
  concrete code-level check, not a planning blocker.
- Whether `overviewPreview` is worth persisting in this first pass. The plan
  keeps it optional so the implementation can drop it if it adds noise without
  clear value.

## High-Level Technical Design

> This illustrates the intended approach and is directional guidance for review,
> not implementation specification. The implementing agent should treat it as
> context, not code to reproduce.

### Preview visibility decision table

| Current selection | Stored preference | Result |
| --- | --- | --- |
| Not previewable | any value | Preview hidden |
| Previewable | explicit open | Preview shown |
| Previewable | explicit closed | Preview hidden |
| Previewable | unset | Preview shown |

### Responsibility split

- `SiteBuilder` decides whether the current selection is previewable and whether
  the right panel should be mounted.
- `useSiteWorkbenchPreferences` owns local read/write behavior for project-scoped
  UI preferences.
- `SiteBuilderPreview` and `PreviewFrame` own preview-local controls and state
  presentation.

## Implementation Units

- [ ] **Unit 1: Add project-scoped workbench preference primitives**

**Goal:** Introduce a small, testable preference layer that can remember `Site`
preview state per project without dragging broader desktop state into the
feature.

**Requirements:** R2, R3, R5

**Dependencies:** None

**Files:**
- Create: `src/niamoto/gui/ui/src/features/site/lib/siteWorkbenchPreferences.ts`
- Create: `src/niamoto/gui/ui/src/features/site/lib/siteWorkbenchPreferences.test.ts`
- Create: `src/niamoto/gui/ui/src/features/site/hooks/useSiteWorkbenchPreferences.ts`
- Create: `src/niamoto/gui/ui/src/shared/hooks/useCurrentProjectScope.ts`
- Create: `src/niamoto/gui/ui/src/shared/hooks/useCurrentProjectScope.test.ts`

**Approach:**
- Add pure helper functions that:
  - build a stable local-storage key for the `Site` workbench
  - normalize stored preview openness into a tri-state form (`unset`,
    `open`, `closed`)
  - normalize stored preview device values
  - read and write the persisted preference payload safely
- Add a thin feature hook that exposes the normalized preference state and
  setter callbacks to `SiteBuilder`.
- Add a lightweight shared hook for current project scope lookup that prefers
  the desktop project path through the existing desktop bridge and falls back to
  a stable non-desktop identifier when the desktop path is unavailable.

**Execution note:** Start with the pure storage helper tests before wiring the
hook so normalization and key behavior are fixed first.

**Patterns to follow:**
- `src/niamoto/gui/ui/src/components/content/previewPolicy.ts`
- `src/niamoto/gui/ui/src/components/content/previewPolicy.test.ts`
- `src/niamoto/gui/ui/src/shared/hooks/useProjectSwitcher.ts`

**Test scenarios:**
- Happy path — reading an existing stored payload returns the expected explicit
  preview preference, device, and width for a given project scope.
- Happy path — writing preferences for one project does not overwrite another
  project’s storage entry.
- Edge case — unknown device or malformed open-state values normalize back to
  safe defaults instead of leaking invalid UI state.
- Edge case — missing storage or missing project scope falls back to an unset
  preference without throwing.
- Error path — malformed JSON in local storage is cleared or ignored cleanly and
  the helper returns normalized defaults.
- Integration — the hook surfaces stable setter functions and rehydrates the
  same normalized values that the pure helper reads from storage.

**Verification:**
- A feature component can consume one hook and receive normalized, project-scoped
  preview preferences without knowing about local-storage details.
- Pure storage helpers are pinned by deterministic tests instead of being
  exercised only indirectly through component behavior.

- [ ] **Unit 2: Refactor `SiteBuilder` to use persisted preview rules**

**Goal:** Replace the transient preview toggle logic in `SiteBuilder` with
preview behavior that auto-opens predictably, respects explicit closes, and
keeps the header focused on module-level actions.

**Requirements:** R1, R2, R4, R5

**Dependencies:** Unit 1

**Files:**
- Modify: `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`
- Modify: `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx`

**Approach:**
- Derive a previewability flag from the current `Site` selection as today, but
  stop treating preview visibility as a purely local toggle.
- Replace the current `previewEnabled` ownership with a resolved preview state
  based on:
  - whether the current selection is previewable
  - the persisted explicit open/closed preference
  - default auto-open behavior when no explicit preference exists
- Keep the preview hidden for non-previewable selections regardless of stored
  state.
- Remove preview toggle controls from the main header and keep only the actions
  that remain global to the module, such as save and contextual reconfigure when
  applicable.
- Keep all save, selection, and editor behavior unchanged outside the preview
  orchestration path.

**Execution note:** Extend the existing `SiteBuilder` regression tests before
moving the header and preview-state wiring so the behavioral shift is covered as
it lands.

**Patterns to follow:**
- `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`
- `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx`

**Test scenarios:**
- Happy path — a previewable page selection shows the preview automatically when
  no preference has been stored yet.
- Happy path — a previewable group selection shows the preview automatically
  under the same default conditions.
- Edge case — a non-previewable selection hides the preview even when the stored
  preference says it was previously open.
- Edge case — an explicit stored closed preference keeps the preview hidden when
  navigating between previewable pages.
- Integration — saving the site still works with the new header layout and does
  not depend on preview controls remaining in the header.
- Integration — site setup and overview flows continue to render correctly when
  the preview rules are re-evaluated across empty, configured, and draft states.

**Verification:**
- The right panel now behaves as a predictable workbench surface instead of a
  one-off toggle.
- The `SiteBuilder` header is visually quieter and no longer owns preview-local
  controls.

- [ ] **Unit 3: Wire preview-local controls and width persistence cleanly**

**Goal:** Make the right preview panel self-sufficient by forwarding close
behavior through the existing preview components and persisting width with the
smallest compatible mechanism.

**Requirements:** R2, R3, R4, R5

**Dependencies:** Units 1-2

**Files:**
- Modify: `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`
- Modify: `src/niamoto/gui/ui/src/features/site/components/SiteBuilderPreview.tsx`

**Approach:**
- Forward a preview close action from `SiteBuilder` into both `SitePreview` and
  `GroupIndexPreviewPanel` so the user can explicitly collapse the right panel
  from the preview surface itself.
- Keep device switching and refresh inside the preview panel where they already
  conceptually belong.
- Persist preview width through the lightest available mechanism:
  - if the installed panel library version supports compatible built-in layout
    persistence, thread that through the existing wrapper and scope it to the current
    project
  - otherwise store the resolved width/layout value through the new preference
    hook and reapply it when mounting the preview panel
- Avoid widening the generic `PreviewFrame` contract unless the current props are
  insufficient for the feature.

**Patterns to follow:**
- `src/niamoto/gui/ui/src/features/site/components/SiteBuilderPreview.tsx`
- `src/niamoto/gui/ui/src/components/ui/preview-frame.tsx`
- `src/niamoto/gui/ui/src/components/ui/resizable.tsx`

**Test scenarios:**
- Happy path — clicking the preview close control updates the stored preference
  and collapses the right panel.
- Happy path — reopening the preview restores the previously chosen device.
- Edge case — group-index preview forwards the same close behavior as static-page
  preview instead of becoming a special case.
- Edge case — a missing stored width falls back to a sensible default panel
  ratio.
- Integration — navigating away from `Site` and back restores the same preview
  width for the same project.

**Verification:**
- The preview panel is the single place where preview-local controls live.
- Width persistence feels stable without introducing a second layout system.

- [ ] **Unit 4: Close the regression gap with targeted Vitest coverage and a desktop smoke pass**

**Goal:** Prove that the new workbench behavior is stable enough to judge the
Tolaria-inspired trial on its real UX merits instead of on manual luck.

**Requirements:** R5

**Dependencies:** Units 1-3

**Files:**
- Modify: `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx`
- Modify: `src/niamoto/gui/ui/src/features/site/lib/siteWorkbenchPreferences.test.ts`

**Approach:**
- Expand `SiteBuilder.test.tsx` from empty-state coverage into workbench
  behavior coverage by stubbing the new preference hook and current-project scope
  hook.
- Keep pure persistence behavior in the storage-helper tests so component tests
  do not need to mock raw local storage extensively.
- Treat the desktop smoke pass as a required finish-line check because this
  feature is primarily about feel and continuity.

**Patterns to follow:**
- `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx`
- `src/niamoto/gui/ui/src/components/content/previewPolicy.test.ts`

**Test scenarios:**
- Happy path — first visit to a previewable page mounts the preview and shows the
  page preview component.
- Happy path — explicit close persists across another previewable selection in
  the same project.
- Edge case — switching project scope yields the other project’s persisted
  preview state instead of reusing the previous one.
- Error path — invalid stored preference payloads do not crash `SiteBuilder`.
- Integration — the same component tree handles static-page preview and
  group-index preview under the new preference model.

**Verification:**
- The main `Site` preview behaviors are proven in Vitest rather than relying on
  ad hoc manual clicking.
- Manual desktop review becomes a confirmation step, not the only source of
  confidence.

## Risks

### Main Risk

Auto-open behavior could feel too aggressive and make the preview seem to “fight
back” after the user hides it.

**Mitigation**

- Preserve an explicit stored closed state and give it precedence over default
  auto-open.

### Secondary Risk

Project-scoped storage could become unstable if the feature relies on a weak
identifier.

**Mitigation**

- Prefer the desktop project path when available and keep the fallback path
  explicit and centralized in one helper.

### Tertiary Risk

Panel-width persistence could become more complex than the UX value justifies.

**Mitigation**

- Use built-in panel persistence if the installed library supports it; otherwise
  keep the fallback implementation minimal and feature-local.

## Acceptance Criteria

- Selecting a previewable page or group shows the preview by default when no
  explicit preference has been stored.
- Closing the preview is respected for the current project instead of being
  undone on the next previewable selection.
- Preview device and width are restored for the same project after leaving and
  re-entering the module.
- Non-previewable selections still collapse the right side cleanly.
- The `SiteBuilder` header no longer carries preview-local controls.
- `pnpm build` and targeted Vitest coverage pass after the change.

## References

- Approved design:
  `docs/superpowers/specs/2026-04-23-site-workbench-preview-design.md`
- Current `Site` orchestrator:
  `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`
- Current preview boundary:
  `src/niamoto/gui/ui/src/features/site/components/SiteBuilderPreview.tsx`
- Current preview chrome:
  `src/niamoto/gui/ui/src/components/ui/preview-frame.tsx`
- Local storage helper pattern:
  `src/niamoto/gui/ui/src/components/content/previewPolicy.ts`
