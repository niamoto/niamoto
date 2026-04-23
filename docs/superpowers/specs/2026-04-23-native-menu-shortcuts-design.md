---
title: "Native menu and desktop shortcuts design"
type: docs
date: 2026-04-23
---

# Native menu and desktop shortcuts design

## Summary

Add a minimal native desktop menu for the Tauri app and centralize a small set
of shell-level shortcuts so Niamoto feels more like a desktop application and
less like a web UI with local packaging.

This pass is intentionally conservative:

- add a native menu bar for desktop only
- expose a short list of global shell actions through that menu
- unify the existing keyboard entry points for those same actions
- keep current product routes and flows unchanged

This is a desktop shell improvement, not a full command system redesign.

## Problem statement

Niamoto already runs inside a Tauri desktop shell, but global actions still
live mostly inside React controls and ad hoc keyboard listeners.

Current issues:

- there is no real native application menu in the Tauri shell
- shell shortcuts are scattered across components
- the command palette shortcut and the desktop devtools shortcut are handled in
  separate places
- common desktop actions such as opening a project or reopening a recent
  project do not feel native

Compared to Tolaria, the missing desktop feel is not only visual. It also comes
from the absence of native chrome conventions such as menu structure,
accelerators, and centralized shell commands.

## Goals

- Add a native menu bar for desktop mode
- Make a small set of global actions accessible from both menu and keyboard
- Centralize shell-level command handling instead of spreading it across
  unrelated components
- Preserve current workflows and avoid any route or backend API rewrite
- Improve desktop feel with minimal implementation risk

## Non-goals

- No full command bus for every feature in the product
- No new workflow architecture for import, collections, site, tools, or publish
- No global shortcut plugin rollout beyond this minimal shell pass
- No Electron parity work
- No multi-window design
- No context menus or native inspector panels in this pass

## Options considered

### Option A: native menu mirror

Add a native menu that mirrors a small set of existing shell actions and routes.
Rust owns menu construction, while React remains the source of product actions.

Pros:

- lowest implementation risk
- preserves current UI flows
- easy to rollback

Cons:

- still needs a bridging layer between menu events and frontend actions

### Option B: hybrid native actions

Let Rust own native actions such as project opening and recent project
selection, while React handles route and shell actions.

Pros:

- stronger desktop feel
- good fit for project and file actions

Cons:

- responsibility split between Rust and React is harder to reason about

### Option C: lightweight native shell only

Add only a very small standard menu with little functional depth.

Pros:

- very safe

Cons:

- weaker user-visible gain
- does not solve the scattered shortcuts problem

## Chosen direction

Use **Option A** as the primary direction, with a small controlled use of
**Option B** for truly native project actions.

That means:

- Rust owns the native menu definition
- React owns product-level shell actions such as command palette, settings, and
  route navigation
- project-open actions can stay native in Rust when they naturally depend on
  desktop dialogs or recent-project state

The main architectural rule for this pass is:

**one shell action registry in the frontend, one menu definition in Rust**

The menu should call into those actions rather than duplicating logic in
multiple components.

## Proposed menu structure

The first pass should provide four top-level menus.

### File

- `Open Project…`
- `Open Recent`
- separator
- `Settings`

Notes:

- `Open Project…` should use the existing desktop folder-selection flow
- `Open Recent` should be built from current recent-project state already stored
  in desktop config
- if there are no recent projects, the submenu is disabled rather than hidden

### View

- `Command Palette`
- `Toggle Sidebar`
- separator
- `Reload UI`
- `Toggle DevTools` when desktop debug mode allows it

### Window

Use standard native window roles where supported by Tauri and the platform.

The goal here is not custom behavior. It is to restore expected desktop
conventions.

### Help

- `Documentation`
- `Keyboard Shortcuts`
- separator
- `About Niamoto`

## Action model

### Frontend shell actions

Create a single shared frontend layer that exposes the small set of shell
actions used by menu items and keyboard shortcuts.

These actions should cover:

- open command palette
- navigate to settings
- toggle sidebar
- navigate to documentation
- open keyboard shortcuts entry point

This layer should become the single source of truth for shell commands that are
already duplicated between:

- `TopBar`
- `CommandPalette`
- the desktop-specific shortcut logic in `App`

### Native project actions

Keep project-opening actions native where that is already the natural desktop
boundary.

Rust can directly handle:

- `Open Project…`
- building the `Open Recent` submenu

The action outcome should remain aligned with the existing project-switching
behavior. The menu must not introduce a second project-loading flow.

## Event bridge

Rust menu items that need product-level UI behavior should emit a single menu
action event into the webview instead of hardcoding route logic in Rust.

Example actions:

- `command_palette.open`
- `shell.toggle_sidebar`
- `settings.open`
- `help.documentation`
- `help.shortcuts`

The frontend listens once at the app-shell layer and dispatches those actions
through the shared shell action registry.

This keeps the integration explicit and avoids coupling Rust to frontend route
details.

## Shortcut model

This pass should centralize only the shell shortcuts already justified by the
menu.

Initial set:

- `CmdOrCtrl+K` for command palette
- `CmdOrCtrl+,` for settings
- existing devtools shortcut kept for debug builds or enabled desktop debug mode

The native menu should display accelerators for the actions it exposes.

Important constraint:

- do not add a large new shortcut taxonomy in this pass
- do not redefine feature-specific editing shortcuts
- do not attempt to solve all keyboard consistency gaps at once

## UI impact

Minimal visible UI changes are expected inside the webview.

Expected changes:

- the top bar and help dropdown can stay as-is initially
- some duplicate shell wiring will move behind the shared action registry
- command palette opening should no longer depend on a component-local keyboard
  listener alone

This means the first pass improves desktop feel mostly through native chrome and
shared action handling, not through visible layout change.

## Error handling and fallback behavior

- if native menu construction fails, the desktop app should still launch without
  blocking the main UI
- if a frontend menu action is received before the relevant shell is mounted,
  the event should be ignored safely rather than throwing
- if there are no recent projects, `Open Recent` remains disabled
- if desktop debug mode is unavailable, `Toggle DevTools` should be omitted or
  disabled rather than failing at runtime

## Testing

### Manual

- desktop app shows a native menu bar
- `Command Palette` opens from both menu and shortcut
- `Settings` opens from both menu and shortcut
- `Open Project…` uses the existing native folder-selection flow
- `Open Recent` reflects current recent projects
- `Toggle Sidebar` works from the menu
- `Documentation` and `About Niamoto` still route correctly
- debug-only devtools action behaves correctly when enabled

### Automated

At minimum:

- frontend build passes
- targeted Rust build passes
- add focused frontend tests for the shell action registry if extracted as a
  helper
- add focused Rust tests only for menu event mapping if the mapping logic is
  separated into testable functions

This pass does not justify broad end-to-end automation by itself.

## Acceptance criteria

The experiment is successful if:

- Niamoto gains a real native menu with meaningful desktop actions
- the command palette and a small set of shell commands are driven from a
  central action layer
- the result feels more desktop-native without altering the product model

The experiment is unsuccessful if:

- the menu duplicates logic without reducing shortcut fragmentation
- Rust and React end up owning the same actions in incompatible ways
- the result adds desktop chrome but does not improve usability

## Follow-up opportunities

If this pass works well, later iterations may explore:

- a richer keyboard shortcut registry
- menu state that reflects route and selection context
- native menu roles for project and workspace actions beyond opening
- a more keyboard-first shell model closer to Tolaria
