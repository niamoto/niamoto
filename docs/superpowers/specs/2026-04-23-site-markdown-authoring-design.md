---
title: "Site markdown authoring design"
type: docs
date: 2026-04-23
---

# Site markdown authoring design

## Summary

Improve markdown page editing inside the `Site` builder by making the authoring
surface feel more direct and less form-driven.

This trial is intentionally narrow:

- keep the current markdown stack based on `Novel`/`Tiptap`
- improve the slash command experience instead of replacing the editor
- make markdown-backed page editing content-first inside `StaticPageEditor`
- move content source and file-management controls into a secondary role
- keep storage, save semantics, and multilingual support compatible with the
  current implementation

This is an authoring UX refinement, not an editor migration.

## Problem statement

Niamoto already has a capable markdown editor in
[MarkdownEditor.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/MarkdownEditor.tsx),
but the full editing flow for static pages still feels heavier than it should.

Current friction comes from two layers.

First, the inline editing experience is only moderately polished:

- the slash menu is a flat list with limited visual structure
- commands do not feel strongly prioritized or grouped
- image insertion breaks the writing flow with a modal step
- the command surface looks functional, but not especially confident or fast

Second, the editor is framed by too much surrounding configuration in
[StaticPageEditor.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/StaticPageEditor.tsx)
and
[MarkdownContentField.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/forms/MarkdownContentField.tsx):

- page settings appear before content
- the content area opens in a view-or-edit workflow rather than an immediate
  writing workflow
- file source, upload, multilingual mode, preview, and raw view all compete for
  attention in the same band
- the page feels like a configuration form that happens to contain markdown,
  rather than a writing surface with supporting settings

Compared to Tolaria, the main gap is not editor capability alone. It is the
combination of a weaker inline command flow and a writing experience that is
not visually or behaviorally central enough.

## Goals

- Make markdown-backed page editing feel writing-first
- Improve the discoverability and confidence of the slash command menu
- Reduce the amount of configuration noise around the editor
- Keep page settings accessible without making them the primary surface
- Preserve the current content file model and backend APIs
- Keep the scope small enough for a focused UI trial

## Non-goals

- No migration away from `Novel`/`Tiptap`
- No replacement of markdown storage with another document model
- No backend or schema changes
- No autosave redesign in this pass
- No rewrite of dedicated template forms such as bibliography, team, or contact
- No full redesign of multilingual editing behavior
- No attempt to solve every media workflow problem inside the editor

## Options considered

### Option A: content-first refinement on top of the current editor

Keep the current editor stack and improve the authoring shell around it.

This includes:

- a stronger slash menu
- immediate writing mode for markdown-backed pages
- page settings demoted into a secondary section
- a cleaner local content toolbar

Pros:

- best impact-to-risk ratio
- preserves the existing storage and save model
- directly addresses the user-facing friction

Cons:

- still limited by the capabilities of the current editor stack
- does not fully eliminate all modal interactions such as image picking

### Option B: slash-menu-only polish

Only improve the inline command experience and leave the page editor layout
largely unchanged.

Pros:

- safest implementation
- smallest diff

Cons:

- leaves the larger writing-flow problem untouched
- likely improves the editor without fixing the feeling that the page is still a
  form first

### Option C: replace the editor stack

Adopt a different markdown editor with stronger block-authoring affordances.

Pros:

- biggest possible upside if the current stack is the real limit

Cons:

- high migration cost
- much higher regression risk
- premature before the current shell has been improved

## Chosen direction

Use **Option A**.

This trial should answer a practical question before any editor migration is
considered:

**Does the editing experience become good enough once the writing flow and slash
menu are treated properly?**

The design principle for this pass is:

**writing is the primary action, configuration is secondary support**

That means:

- markdown-backed pages should open into a clear writing flow
- the content area should appear before page settings
- the slash menu should look structured and intentional
- file and mode controls should be compact and local to the content surface

## UX design

### Scope of the trial

This pass only affects markdown-backed pages that currently use
`MarkdownContentField`.

Dedicated template forms remain unchanged in this trial.

### Static page layout

For markdown-backed pages, `StaticPageEditor` changes from a stack of equally
weighted cards to a content-first surface.

Expected behavior:

- the content section appears first and occupies the main visual weight
- page settings and additional context move into a secondary collapsible section
  below the editor
- the top header remains compact and keeps only page identity plus destructive
  or navigation actions

The intent is not to add a heavy new workbench shell. The intent is to stop
treating content as just one card among several peers.

### Local content toolbar

`MarkdownContentField` gets a small local toolbar that owns content-specific
controls.

The toolbar should include:

- current source file label
- mode switch for `Write`, `Preview`, and `Source`
- save action when the current single-file editor is dirty
- compact access to advanced content-source actions

The toolbar should not look like a settings strip. It should read as local
editor chrome.

### Default mode behavior

When a markdown file is already selected, the user should land in `Write` mode
by default instead of first seeing a passive preview with a separate `Edit`
action.

This is a key behavioral change in the trial.

Expected behavior:

- open page
- see editable content immediately
- type immediately
- switch to `Preview` or `Source` only when needed

Save behavior remains explicit for single-file editing in this pass.

### Secondary content-source controls

Source-file selection, upload, clear, and multilingual switching remain
available, but they move behind a quieter secondary affordance implemented as a
collapsible details row directly under the local content toolbar.

The default reading of the screen should be:

- page title and identity
- content editor
- content modes

Not:

- file plumbing
- source management
- then writing

### Slash menu improvements

The slash menu in `MarkdownEditor` should become more structured and more
scannable without changing the underlying command set drastically.

Expected improvements:

- visible groups such as `Text`, `Structure`, `Lists`, and `Media`
- clearer ranking of common commands
- shorter and more action-oriented descriptions
- stronger active-item styling
- better search aliases in English and French

This pass should favor clarity over command count. It is acceptable to keep the
same core commands if they become easier to find and easier to trust.

## Technical design

### `StaticPageEditor`

[StaticPageEditor.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/StaticPageEditor.tsx)
remains the orchestration point for page editing.

Responsibilities in this pass:

- reorder markdown-backed page sections so content comes first
- wrap page settings and additional context in a secondary collapsible section
- preserve the current dedicated-template path unchanged

This file should own page-level composition, not editor command details.

### `MarkdownContentField`

[MarkdownContentField.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/forms/MarkdownContentField.tsx)
absorbs most of the local UX changes.

Responsibilities in this pass:

- replace the current preview-or-edit gate with a stable mode model
- default to `Write` mode when a file is present
- surface save state near the content modes
- demote file-management actions into a quieter secondary area
- preserve multilingual mode support

Recommended internal model:

- `viewMode = 'write' | 'preview' | 'source'`
- file-management UI independent from `viewMode`
- existing explicit save flow retained for single-file editing
- `source` remains a read-only raw inspection mode in this pass

### `MarkdownEditor`

[MarkdownEditor.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/MarkdownEditor.tsx)
keeps the same editor engine and serialization pipeline.

Responsibilities in this pass:

- reorganize slash menu item metadata
- render grouped command sections
- improve labels, descriptions, and search aliases
- strengthen visual treatment of the active slash item

Out of scope here:

- new node types
- raw markdown editing mode
- image-upload pipeline changes

### `MultilingualMarkdownEditor`

[MultilingualMarkdownEditor.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site/components/MultilingualMarkdownEditor.tsx)
should stay behaviorally compatible.

Only minimal alignment changes are in scope if needed so that multilingual pages
still feel consistent with the new local toolbar vocabulary.

## Error handling and edge cases

- If no source file is selected, the content area should still explain the next
  action clearly without dropping back to a cluttered control surface.
- If file content is loading, the loading state should occupy the content area
  rather than fragmenting the toolbar.
- If the selected file is missing or upload fails, the error should remain near
  the content source controls, not in the main writing surface.
- Multilingual mode should not silently lose unsaved edits when switching tabs
  or leaving the page.

## Validation

The trial is successful if:

- opening a markdown-backed page feels immediately editable
- adding a block with `/` feels more obvious and more deliberate
- page settings no longer dominate the screen
- current file-based editing workflows still work
- multilingual editing still works without regression

Minimum validation expected during implementation:

- targeted frontend tests for the new `MarkdownContentField` mode behavior
- targeted frontend tests for slash-menu grouping logic if extracted into data
- `pnpm run build`

## Future follow-up if this works

If this pass produces a clear improvement, the next candidates become easier to
evaluate:

- richer slash commands
- better image insertion flow
- stronger preview coupling with page editing
- deeper cleanup of static-page settings layout

If this pass does not improve the authoring experience enough, then it becomes
reasonable to reassess the editor stack itself instead of the shell around it.
