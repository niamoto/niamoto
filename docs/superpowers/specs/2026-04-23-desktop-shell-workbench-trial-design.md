---
title: "Desktop shell workbench trial design"
type: docs
date: 2026-04-23
---

# Desktop shell workbench trial design

## Summary

Run a conservative desktop-only shell experiment to make Niamoto feel more
like a native workbench and less like a routed web dashboard.

The trial keeps the current product workflows, routes, and business features,
but changes the presentation of the shared desktop chrome:

- denser shell layout
- lighter top chrome
- stronger desktop status surface
- cleaner startup paint
- less visual separation between navigation and workspace

This is an evaluation pass, not a product-wide redesign.

## Problem statement

Niamoto already has a solid desktop base:

- Tauri shell
- pre-mount theme bootstrap in `index.html`
- dedicated startup loader in Rust
- desktop-aware sidebar and drag regions

But the main application shell still reads primarily as a web app:

- a distinct top bar plus breadcrumb bar creates stacked chrome
- the navigation rail feels like a SaaS sidebar rather than an app workspace
- the current shell emphasizes routed sections over a persistent desktop frame
- the window background is not explicitly aligned with the app theme in
  `src-tauri/tauri.conf.json`

The result is not “bad UI”; it is a mismatch between the current desktop
runtime and the visual grammar of the shell.

## Goals

- Make the desktop shell feel denser and more intentional
- Reduce the “website inside a webview” impression without changing workflows
- Preserve all existing route structure and feature entry points
- Keep web and smaller responsive layouts functional
- Limit the work to a reversible shell-layer experiment

## Non-goals

- No refactor of import, collections, site, tools, or publish features
- No new backend routes or API contract changes
- No navigation model rewrite
- No Tolaria-style four-pane architecture transplant
- No theme-system rewrite
- No startup process rewrite away from the Python sidecar in this pass

## Chosen direction

### Desktop

Keep the existing shell composition from `MainLayout`, but rebalance it into a
more desktop-like frame:

- navigation remains on the left
- the top chrome becomes more compact
- breadcrumbs become less dominant
- a new bottom desktop status bar carries persistent global context
- the content surface reads as the primary workspace, not as a page inside a
  marketing-style frame

### Web and responsive behavior

Do not introduce a second shell architecture.

The same components continue to work in web mode and on smaller widths, but the
strongest visual changes are scoped to desktop mode so the experiment stays low
risk.

## Shell changes

### `MainLayout`

`MainLayout` remains the shell coordinator.

It will be updated to:

- treat the middle application area as a single desktop workspace surface
- reduce visual stacking between `TopBar`, `BreadcrumbNav`, and page content
- render a dedicated desktop status bar below the main content when running in
  desktop mode

The routed `Outlet` and `PageTransition` behavior stay unchanged.

### `TopBar`

`TopBar` should become quieter and more utility-oriented.

Changes:

- reduce visual weight of borders and button grouping
- remove the wide “search input imitation” treatment in favor of a more
  compact command action
- keep the sidebar toggle, command palette trigger, notifications, and help
  entry points

The top bar should read as window chrome, not as a full product header.

### `BreadcrumbNav`

`BreadcrumbNav` should stay functional but become secondary.

Changes:

- reduce height and contrast
- keep the freshness indicator
- avoid presenting it as a second prominent toolbar

The goal is not to remove route context, only to stop over-framing it.

### `NavigationSidebar`

`NavigationSidebar` keeps the same destinations and responsive modes, but its
desktop presentation should feel more like an app rail.

Changes:

- denser spacing
- less isolated “section” feel around the header and footer
- stronger relationship between project switcher, navigation, and footer tools
- more restrained active-state treatment

The route model and stored sidebar mode remain unchanged.

### New desktop status bar

Introduce a new desktop-only shared component at the shell layer.

It should expose compact global information already available in the current
frontend state, such as:

- current project label
- command palette hint
- current route or workspace label
- pipeline freshness summary when available
- settings or utility access

This bar is not a duplicate toolbar. It is a low-height persistent context
surface modeled after desktop application status bars.

It must remain compact: contextual information first, actions second. It should
not replicate the full top bar or absorb the existing project switcher menu.

## Startup and window treatment

### Tauri window background

Set an explicit `backgroundColor` in `src-tauri/tauri.conf.json` to align the
window paint with the desktop shell before React finishes mounting.

This change is intentionally small, but it directly improves perceived polish
on launch and during reload.

### Existing startup loader

Keep the current Rust startup loader and sidecar boot sequence.

This trial does not attempt to remove the Python/FastAPI dependency. It only
improves the visual continuity between:

- Tauri window paint
- startup loader
- pre-mounted themed shell
- final application chrome

## Data flow and architecture impact

No backend changes are required.

The trial should only compose data that already exists in the frontend:

- runtime mode from `useRuntimeMode`
- project state from existing desktop/project hooks
- pipeline freshness from `usePipelineStatus`
- command palette state from `navigationStore`

The new shell components must remain presentation-layer only.

## Error handling and fallback behavior

- If runtime mode is unavailable, the shell falls back to its existing web-safe
  behavior
- If project metadata is missing, the status bar shows a neutral placeholder
  rather than hiding the whole bar
- If pipeline freshness is unavailable, the shell still renders without status
  chips
- If the new desktop status bar causes layout issues at smaller widths, it may
  be hidden outside desktop mode rather than forced to collapse awkwardly

## Testing

### Manual

- Desktop app opens with a window background visually aligned with the app
- Startup transition from loader to mounted shell feels continuous
- Top chrome feels denser and less web-like
- Navigation, command palette, notifications, help, and settings remain usable
- Breadcrumbs and pipeline freshness remain visible and readable
- Desktop status bar remains stable across key routes
- Web mode still renders correctly
- Responsive sidebar behavior still works at the current breakpoints

### Automated

At minimum:

- frontend build passes

If shell behavior is extracted into small helpers, add focused unit tests only
for the extracted logic. This trial does not justify broad snapshot testing.

## Acceptance criteria

The experiment is considered successful if it produces a visibly more desktop
native shell while preserving current workflows and without causing routing,
responsive, or startup regressions.

The experiment is considered unsuccessful if the result only adds more chrome,
duplicates existing controls, or makes the shell feel busier rather than more
focused.

## Out of scope follow-ups

If this trial works well, later phases may explore:

- deeper keyboard-first shell behavior
- a native Tauri menu bar for desktop commands
- better desktop-global command surfacing
- more structural boot improvements around the Python sidecar

Those topics are explicitly outside this design.
