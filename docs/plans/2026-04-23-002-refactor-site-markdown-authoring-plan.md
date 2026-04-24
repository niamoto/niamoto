---
title: refactor: Improve Site markdown authoring flow
type: refactor
status: active
date: 2026-04-23
origin: docs/superpowers/specs/2026-04-23-site-markdown-authoring-design.md
---

# refactor: Improve Site markdown authoring flow

## Overview

Refine markdown page editing inside the `Site` feature so writing becomes the
primary activity instead of one mode inside a broader page-configuration form.

The approved design focuses on three visible outcomes:

- a more structured and trustworthy slash-command menu in the shared markdown
  editor
- a clearer local editing shell in `MarkdownContentField`
- a content-first composition in `StaticPageEditor` for markdown-backed pages

This work stays entirely in the frontend `Site` feature. It does not change the
markdown storage model, backend APIs, or editor engine.

## Problem Frame

The approved spec
`docs/superpowers/specs/2026-04-23-site-markdown-authoring-design.md`
identifies two interacting problems in the current implementation:

- the slash-command menu in
  `src/niamoto/gui/ui/src/features/site/components/MarkdownEditor.tsx` is a
  flat list with limited structure and moderate affordance quality
- the authoring surface in
  `src/niamoto/gui/ui/src/features/site/components/StaticPageEditor.tsx` and
  `src/niamoto/gui/ui/src/features/site/components/forms/MarkdownContentField.tsx`
  gives too much weight to file plumbing and configuration before writing

There is also one important implementation constraint:

- `MarkdownContentField` is shared by multiple dedicated template forms
  (`IndexPageForm`, `GlossaryForm`, `BibliographyForm`, `TeamForm`,
  `ResourcesForm`, `ContactForm`), so the trial must not accidentally impose a
  heavy “content-first page shell” on those embedded uses

This plan therefore treats the work as a bounded frontend refactor with an
explicit separation between:

- shared editor improvements that can safely benefit all usages
- static-page-only shell changes that should stay local to `StaticPageEditor`

## Requirements Trace

- R1. Markdown-backed static pages must surface content before secondary page
  settings.
- R2. When a source markdown file is selected, the user must land directly in
  an editable writing mode.
- R3. `MarkdownContentField` must expose a cleaner local toolbar with
  `Write`/`Preview`/`Source` modes and quieter source-management controls.
- R4. The slash menu in `MarkdownEditor` must become grouped, more scannable,
  and better prioritized without changing the editor engine.
- R5. Existing file-based and multilingual content workflows must remain
  compatible.
- R6. The refactor must be protected by targeted frontend tests and `pnpm run
  build`.

## Scope Boundaries

- Do not replace `Novel`/`Tiptap`.
- Do not introduce backend or config-schema changes.
- Do not redesign dedicated template forms as content-first pages.
- Do not alter autosave semantics or remove the current explicit-save behavior
  for single-file editing.
- Do not change the image upload/insertion pipeline beyond whatever is needed to
  keep the existing slash command wired.
- Do not add an entirely new markdown raw-editing engine; `Source` remains a
  read-only raw inspection mode in this pass.

### Deferred to Separate Tasks

- A stronger media flow that avoids the current image modal.
- Richer block types or new slash commands beyond the current core set.
- A broader cleanup of dedicated template forms that embed markdown sections.
- Any future evaluation of replacing the editor stack itself.

## Context & Research

### Relevant Code and Patterns

- `src/niamoto/gui/ui/src/features/site/components/MarkdownEditor.tsx` already
  owns markdown serialization, slash-command registration, and the current menu
  rendering.
- `src/niamoto/gui/ui/src/features/site/components/forms/MarkdownContentField.tsx`
  already owns file selection, upload, single-vs-multilingual mode, and the
  current preview-or-edit flow.
- `src/niamoto/gui/ui/src/features/site/components/StaticPageEditor.tsx`
  currently renders page settings before markdown content for non-form
  templates.
- `src/niamoto/gui/ui/src/features/site/components/MultilingualMarkdownEditor.tsx`
  provides the current multilingual editing shell and should remain compatible.
- `src/niamoto/gui/ui/src/components/ui/toggle-group.tsx` is the existing local
  pattern for compact mode switches.
- `src/niamoto/gui/ui/src/components/ui/collapsible.tsx` is the existing local
  pattern for secondary disclosure.
- `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx` is the
  only current `Site` component test entry point; no targeted coverage exists
  yet for `MarkdownContentField`, `MarkdownEditor`, or `StaticPageEditor`.

### Institutional Learnings

- No current `docs/solutions/` learning covers markdown authoring UX in the
  `Site` feature.

### External References

- None. Local code and the approved design are sufficient for this refactor.

## Key Technical Decisions

- Use a small extracted slash-menu data layer instead of leaving command
  metadata inline inside `MarkdownEditor`.
  Rationale: grouping, ordering, and aliases become testable without coupling
  tests to the editor runtime.
- Introduce an explicit local `viewMode` model in `MarkdownContentField`
  (`write`, `preview`, `source`) instead of the current `isEditing` plus
  `showRawContent` split.
  Rationale: the UX should be readable and deterministic.
- Add a presentation variant to `MarkdownContentField` so
  `StaticPageEditor` can opt into a stronger authoring shell without forcing the
  same chrome onto embedded uses in dedicated forms.
  Rationale: the component is shared; the trial must stay scoped.
- Keep source-file management visible but secondary through a collapsible row
  directly under the local toolbar.
  Rationale: file plumbing must remain available without dominating the
  interface.
- Keep `Source` as a read-only raw view in this pass.
  Rationale: the goal is authoring-shell refinement, not a second editable
  markdown engine.

## Open Questions

### Resolved During Planning

- Should the trial replace the editor engine? No. The purpose is to test the
  shell and slash-menu quality first.
- Should the new content-first shell apply to all `MarkdownContentField`
  consumers? No. Shared improvements are acceptable, but the stronger page-level
  treatment stays opt-in from `StaticPageEditor`.
- Should `Source` become a second editable mode? No. It remains inspection-only
  to avoid save-flow complexity.

### Deferred to Implementation

- Whether the slash-menu grouping is best represented as flat items with group
  metadata or as a pre-grouped data structure. This is an implementation detail
  as long as rendering and tests stay simple.
- Whether the shared component variant should be named `authoring`/`embedded`
  or `primary`/`default`. The behavior matters; the prop spelling does not.

## High-Level Technical Design

> This section is directional guidance for review and implementation planning,
> not code to reproduce literally.

### Responsibility split

- `MarkdownEditor` owns editor-engine integration and menu rendering.
- A small extracted helper owns command metadata, grouping, order, and aliases.
- `MarkdownContentField` owns local writing modes and source-management chrome.
- `StaticPageEditor` owns page-level composition and the decision to place
  content before settings for markdown-backed pages.

### Authoring surface behavior

| Situation | Result |
| --- | --- |
| Single-file source selected | Open directly in `Write` mode |
| User switches to `Preview` | Show read-only rendered view |
| User switches to `Source` | Show read-only raw markdown |
| No source selected | Show clear empty-state guidance plus secondary source controls |
| Multilingual mode active | Keep existing multilingual editor, with only minimal chrome alignment if needed |

## Implementation Units

- [ ] **Unit 1: Extract and strengthen slash-menu metadata**

**Goal:** Make slash-menu behavior testable and improve scannability without
changing the editor engine or command wiring.

**Requirements:** R4, R6

**Dependencies:** None

**Files:**
- Create: `src/niamoto/gui/ui/src/features/site/lib/markdownCommandMenu.ts`
- Create: `src/niamoto/gui/ui/src/features/site/lib/markdownCommandMenu.test.ts`
- Modify: `src/niamoto/gui/ui/src/features/site/components/MarkdownEditor.tsx`

**Approach:**
- Extract the current command catalog from `MarkdownEditor` into a small helper
  that defines:
  - stable command keys
  - group labels
  - display order
  - titles and descriptions derived from `t(...)`
  - richer English/French aliases
- Keep the executable command handlers in `MarkdownEditor`, but have the render
  path consume grouped metadata rather than a plain flat list.
- Update the command menu rendering so groups are visually separated and the
  selected item reads more clearly.
- Preserve the existing command set unless a command proves obviously redundant.

**Patterns to follow:**
- Existing pure-helper test style in
  `src/niamoto/gui/ui/src/features/site/lib/siteWorkbenchPreferences.test.ts`

**Test scenarios:**
- Happy path — the helper returns the expected visible groups and stable command
  order.
- Happy path — French and English aliases both map to the intended command
  entries.
- Edge case — unknown or empty translation output does not break grouping or
  command availability.
- Integration — `MarkdownEditor` still wires slash commands to the same command
  keys after the extraction.

**Verification:**
- The slash menu looks grouped and the command catalog is pinned by unit tests
  instead of only through editor snapshots.

- [ ] **Unit 2: Refactor `MarkdownContentField` around explicit view modes**

**Goal:** Replace the current preview-or-edit gate with a local authoring shell
that makes writing the default when a file is present, while keeping embedded
usages safe.

**Requirements:** R2, R3, R5, R6

**Dependencies:** Unit 1 can land first or in parallel conceptually, but this
unit does not depend on its code.

**Files:**
- Modify: `src/niamoto/gui/ui/src/features/site/components/forms/MarkdownContentField.tsx`
- Modify: `src/niamoto/gui/ui/src/features/site/components/MultilingualMarkdownEditor.tsx`
- Create: `src/niamoto/gui/ui/src/features/site/components/forms/MarkdownContentField.test.tsx`

**Approach:**
- Replace `isEditing` and `showRawContent` with a single `viewMode` state.
- When a single-file source exists, default the component to `write`.
- Introduce a compact local toolbar built from existing UI primitives such as
  `ToggleGroup` for:
  - `Write`
  - `Preview`
  - `Source`
  - save state / save action in single-file mode
- Move source-file selection, upload, clear, and multilingual switching into a
  collapsible secondary row under that toolbar.
- Add a presentation variant prop so `StaticPageEditor` can request a stronger
  authoring shell while dedicated forms can stay visually lighter.
- Keep multilingual mode behavior functionally unchanged; only align its local
  shell if needed so it does not feel inconsistent next to the new toolbar
  vocabulary.

**Patterns to follow:**
- `src/niamoto/gui/ui/src/components/ui/toggle-group.tsx`
- `src/niamoto/gui/ui/src/components/ui/collapsible.tsx`

**Test scenarios:**
- Happy path — when a file exists, the component starts in `write` mode and
  exposes the editor immediately.
- Happy path — switching between `write`, `preview`, and `source` swaps the
  correct surface without losing the current draft.
- Happy path — save remains enabled only when the single-file content is dirty.
- Edge case — no selected file shows guidance plus access to source-management
  controls.
- Edge case — embedded/default variant does not render the stronger authoring
  chrome intended for static pages.
- Regression — multilingual mode still renders and can be selected without
  falling back to the old single-file assumptions.

**Verification:**
- The shared markdown field has one clear local state model and the static-page
  writing flow no longer depends on an extra `Edit` click.

- [ ] **Unit 3: Recompose `StaticPageEditor` for markdown-backed pages**

**Goal:** Make markdown-backed static pages content-first without affecting the
dedicated-template editing path.

**Requirements:** R1, R5, R6

**Dependencies:** Unit 2

**Files:**
- Modify: `src/niamoto/gui/ui/src/features/site/components/StaticPageEditor.tsx`
- Create: `src/niamoto/gui/ui/src/features/site/components/StaticPageEditor.test.tsx`

**Approach:**
- For markdown-backed pages only:
  - move the content surface ahead of page settings
  - pass the stronger authoring variant into `MarkdownContentField`
  - place page settings and additional context inside a secondary collapsible
    section below the editor
- Keep the dedicated-template branch untouched except for any shared component
  prop adjustments required by Unit 2.
- Keep the page header compact and focused on navigation, identity, preview
  restore if applicable, and destructive actions.

**Test scenarios:**
- Happy path — markdown-backed pages render the content section before settings.
- Happy path — the secondary settings section can expand and collapse without
  losing current page state.
- Regression — dedicated template forms still render through their existing
  branch.
- Regression — additional context fields remain writable when expanded.

**Verification:**
- A markdown-backed static page now reads as a writing surface first and a page
  configuration second.

- [ ] **Unit 4: Final regression pass and implementation closure**

**Goal:** Prove that the refactor works across the changed surfaces and leave
the feature in a shippable state.

**Requirements:** R5, R6

**Dependencies:** Units 1-3

**Files:**
- Modify as needed: targeted tests created in Units 1-3

**Approach:**
- Run the narrowest useful frontend tests first, then the frontend build.
- Fix any type, lazy-loading, or test harness issues exposed by the new shared
  component variant and extracted slash-menu helper.
- Verify that no unrelated `SiteBuilder` preview or desktop-shell behavior was
  regressed by the authoring changes.

**Verification commands:**
- `pnpm exec vitest run src/features/site/lib/markdownCommandMenu.test.ts src/features/site/components/forms/MarkdownContentField.test.tsx src/features/site/components/StaticPageEditor.test.tsx`
- `pnpm run build`

## Suggested Execution Order

1. Land the slash-menu extraction first so command metadata and UI grouping are
   isolated before touching the page shell.
2. Refactor `MarkdownContentField` next because it defines the new local
   authoring behavior.
3. Recompose `StaticPageEditor` last so it consumes the new shared-field API
   instead of inventing extra one-off logic.
4. Finish with the targeted Vitest pass and frontend build.

## Risks & Mitigations

- **Risk:** shared changes in `MarkdownContentField` unintentionally degrade
  embedded uses inside dedicated forms.
  **Mitigation:** keep the stronger shell behind an explicit variant and cover
  both the authoring and embedded/default cases in tests.

- **Risk:** the grouped slash menu becomes more attractive visually but less
  compatible with the underlying `novel` command filtering.
  **Mitigation:** keep command keys stable, keep the suggestion registration
  path intact, and test the pure command catalog separately from the editor
  runtime.

- **Risk:** replacing `isEditing` with `viewMode` could introduce save-state or
  content-sync regressions.
  **Mitigation:** add direct component tests around mode switching and dirty
  state before relying on manual verification.
