---
title: "Site workbench preview design"
type: docs
date: 2026-04-23
---

# Site workbench preview design

## Summary

Make the `Site` module feel more like a persistent desktop workbench by
turning the existing right-hand preview into a more central and stable part of
the editing flow.

This pass is intentionally narrow:

- keep the current left tree, center editor, and right preview structure
- make preview behavior more persistent and more predictable
- remember a few local workbench preferences per project
- simplify the `SiteBuilder` header so the module feels less like a routed
  admin page

This is a workbench UX refinement, not a `Site` architecture rewrite.

## Problem statement

Niamoto already has most of the structural ingredients needed for a Tolaria-like
editing surface inside [SiteBuilder.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx):

- left navigation tree
- center editor
- optional right preview
- resizable horizontal panels

The weakness is not the absence of a workbench. It is that the preview still
behaves like a secondary optional tool rather than a first-class editing
surface.

Current friction:

- the preview must often be re-enabled manually
- the module does not preserve a clear per-project preview preference
- preview controls still compete with the main header for attention
- the overall `Site` surface still reads more like a page with tools than a
  stable desktop workspace

Compared to Tolaria, the missing quality is mostly continuity: editing and
reading do not yet feel like two persistent halves of the same workflow.

## Goals

- Make the preview feel like a normal part of the `Site` workbench
- Open the preview automatically for previewable selections when appropriate
- Respect the user choice when they explicitly close the preview
- Persist a minimal set of workbench preferences locally per project
- Reduce visual noise in the `Site` header
- Keep implementation local to the frontend `Site` feature

## Non-goals

- No new inspector panel
- No backend or config schema changes
- No rewrite of `UnifiedSiteTree`
- No changes to the site data model or save flow
- No attempt to persist full editing session state
- No large visual redesign of the whole module
- No performance initiative beyond normal UI behavior in this pass

## Options considered

### Option A: preview-first workbench

Keep the existing three-panel structure and make the preview behave like a
stable companion to editing.

Pros:

- best impact-to-risk ratio
- reuses the existing layout and preview components
- most clearly improves desktop feel

Cons:

- requires careful rules so auto-open behavior does not feel intrusive

### Option B: focus editor with preview peek

Keep the editor as the dominant surface and treat preview as a temporary panel.

Pros:

- safest interaction change
- minimal behavioral change for current users

Cons:

- weaker desktop-workbench gain
- keeps preview in a secondary role

### Option C: broader `Site` shell refactor

Push `Site` toward a more route-less and fully persistent shell.

Pros:

- strongest resemblance to Tolaria

Cons:

- too large for a diagnostic trial
- higher regression risk

## Chosen direction

Use **Option A**.

This trial should not invent a new module structure. It should strengthen the
one that already exists.

The main rule for this pass is:

**preview is part of the normal `Site` working surface, not a detachable extra**

That means:

- preview opens automatically for previewable selections when no explicit user
  preference says otherwise
- preview controls live in the preview surface itself
- the `SiteBuilder` header carries only the minimum global context and actions
- preferences stay local to the UI and scoped to the current project

## UX design

### Layout behavior

The existing three-panel structure remains:

- left: tree and navigation
- center: editor
- right: preview

Behavior changes:

- selecting a previewable page opens the preview automatically
- selecting a previewable group index opens the preview automatically
- selecting a non-previewable surface such as general settings, navigation, or
  footer hides the preview panel cleanly
- if the user explicitly closes the preview, that choice is respected instead of
  being undone on every subsequent selection

The preview remains docked on the right. This pass does not add floating,
overlay, or bottom-docked preview modes.

### Header simplification

The `SiteBuilder` header becomes quieter and more workbench-like.

Expected behavior:

- keep module identity and current site title
- keep save affordance
- remove preview controls from the main header
- avoid adding new global actions in this pass

The goal is to make the top bar feel more like stable desktop chrome and less
like a control surface for every local mode.

### Preview panel responsibilities

The preview panel becomes the home for preview-specific controls:

- device switch
- refresh
- loading state
- preview error state
- optional close action if the current `PreviewFrame` contract keeps it

This reduces split ownership between the main header and the preview itself.

## Persistence model

The preferences introduced in this pass are local UI preferences, not project
configuration. They must not be written into `site.yml`, API config payloads, or
backend state.

Persist locally, scoped to the current project:

- whether the preview is open
- current preview device
- preview panel size

Optional but still in scope if trivial:

- overview preview mode for the no-selection state

Out of scope for persistence:

- full tree expansion state
- current selection
- unsaved draft recovery
- editor form state

The storage key must be project-scoped so that one project does not force its
workbench habits onto another project.

## Technical design

### `SiteBuilder`

[SiteBuilder.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx)
remains the orchestration point.

New responsibilities:

- derive whether the current selection is previewable
- decide when preview should auto-open
- respect a persisted local close/open preference
- wire a project-scoped preference hook into the current layout
- simplify the top header so preview actions leave the global toolbar

This file should still own workbench coordination, but not raw persistence
details.

### Workbench preferences hook

Add a small dedicated hook under `features/site/hooks`, for example
`useSiteWorkbenchPreferences`.

Responsibilities:

- read and write local preferences
- scope them to the current project
- expose a small typed API to `SiteBuilder`

State surface for the hook:

- `previewOpen`
- `setPreviewOpen`
- `previewDevice`
- `setPreviewDevice`
- preview panel layout value plus setter

This hook should stay deliberately small and should not become a generic site UI
state store.

### Preview components

[SiteBuilderPreview.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/SiteBuilderPreview.tsx)
already holds the preview-specific UI boundary.

This pass should reinforce that responsibility:

- keep preview controls inside the preview surface
- preserve refresh behavior for page preview and group index preview
- continue routing preview link clicks back through `SiteBuilder`

No new preview mode is introduced. This is about ownership and persistence, not
about redesigning preview rendering.

### Panel layout persistence

The current `ResizablePanelGroup` should keep handling the horizontal split.

This pass should add only the minimal persistence needed to remember the preview
panel width between visits for the same project. If the existing panel library
supports persisted layout directly, use that instead of inventing a custom drag
state model.

## Testing and validation

### Automated checks

Minimum checks:

- `pnpm run build`
- targeted tests in
  [SiteBuilder.test.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx)

Minimum regression coverage to add:

- preview auto-opens for a previewable page when no prior preference exists
- preview stays closed when the stored preference for the current project says it
  is closed
- preview disappears cleanly for non-previewable selections

### Manual validation

Manual desktop pass:

1. Open `Site`
2. Select a previewable page
3. Confirm the preview appears without manual toggling
4. Close the preview
5. Navigate to another previewable page
6. Confirm the close preference is respected
7. Reopen the preview and resize it
8. Leave and reopen the module or relaunch the desktop app
9. Confirm preview open state, device, and width are restored for the same
   project

## Risks and mitigations

- **Risk: auto-open feels pushy**
  Mitigation: auto-open only when no explicit local close preference is in
  effect.

- **Risk: persistence leaks across projects**
  Mitigation: require a project-scoped storage key from the start.

- **Risk: header simplification hides useful actions**
  Mitigation: remove only preview-local actions from the header in this pass and
  keep save intact.

- **Risk: panel width persistence becomes more complex than expected**
  Mitigation: use the panel library's persisted layout capability if available;
  otherwise keep the first pass to a simple stored width value.

## Rollout boundaries

This trial is successful if `Site` feels more continuous and more desktop-like
without changing the module's information architecture.

If the result is positive, likely follow-up directions are:

- persist a little more workbench context
- extend the same workbench logic to another module
- revisit whether a contextual inspector is useful after preview has been made
  first-class

If the result is weak, the next conclusion should not be "add more controls". It
should be that preview persistence alone is insufficient and that a deeper shell
change would be needed.
