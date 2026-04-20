---
title: "Site builder empty state and no auto-home design"
type: docs
date: 2026-04-20
---

# Site builder empty state and no auto-home design

## Summary

Remove the automatic creation and reinjection of the `home` page in `export.yml`.

The Site module must return to a true empty state:

- entering `Site` on a fresh project opens `Site Setup`
- no synthetic `home/index.html` is created during scaffold, read, or save
- `Publish` remains blocked until the project contains a real publishable site

This design also fixes the current deletion inconsistency where removing `Home`
does not actually persist because the backend silently recreates it.

## Problem statement

Recent fixes introduced a default root page:

- scaffold creates `static_pages: [home/index.html]`
- `GET /api/site/config` injects `home/index.html` when missing
- `PUT /api/site/config` recreates `home/index.html` when missing

That behavior solves one technical problem but creates three product problems:

1. Fresh projects no longer land in `Site Setup`; they land in the normal site
   builder with a fake `Home` page.
2. Deleting `Home` is misleading because the backend restores it on the next
   read or save.
3. The product signals that a site exists even when the user has never
   configured one.

The UI currently conflates three meanings:

- export HTML infrastructure exists
- a root page exists
- a user-configured site exists

These states must be separated again.

## Goals

- Restore a true empty-state experience in `Site`
- Make `Site Setup` the default entry point for unconfigured projects
- Stop creating `home/index.html` automatically anywhere in the stack
- Allow deleting the last home page and returning to the setup state
- Block `Publish` generation when no real site exists
- Preserve group scaffolding for `Collections` without pretending the site is configured

## Non-goals

- Redesign the Site Setup wizard itself
- Change collection index generation behavior
- Change the overall export pipeline semantics beyond site-readiness checks
- Perform aggressive auto-migration of user YAML files on open

## Decisions from brainstorming

- No automatic `Home` page at project creation, scaffold, API read, or API save
- Clicking `Site` on an empty project must open `Site Setup`
- `Publish` must not allow generation until there is something real to publish
- The primary guidance target from `Publish` is the general `Site Builder`
- Deleting `Home` when it is the last publishable root page returns the project
  to the unconfigured state

## Current code paths affected

The current auto-home behavior is spread across multiple layers:

- `src/niamoto/gui/api/routers/site.py`
  - `_normalize_static_pages()`
  - `get_site_config()`
  - `update_site_config()`
- `src/niamoto/gui/api/services/templates/config_scaffold.py`
  - `_add_export_group()`
- `src/niamoto/gui/api/routers/templates.py`
  - default `html_page_exporter` creation
- `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`
  - empty-state detection currently depends on `static_pages.length === 0`
- `src/niamoto/gui/api/routers/pipeline.py`
  - site stage status currently treats valid HTML exporter params as sufficient
- `src/niamoto/gui/ui/src/features/publish/views/index.tsx`
  - generation gating currently uses the pipeline site status

## Target state model

The product should use two explicit site states:

### 1. Unconfigured site

The project has no real root static page to publish.

Typical markers:

- `web_pages` may exist
- `template_dir` and `output_dir` may exist
- groups may exist
- `static_pages` is empty, or contains only a recognized legacy placeholder

User-facing consequences:

- `Site` opens `Site Setup`
- `Publish` generation is disabled

### 2. Configured site

The project has a real root static page that the user created through the setup
flow or the site builder.

Minimum technical marker:

- at least one static page resolves to the root output `index.html`

User-facing consequences:

- `Site` opens the normal builder
- `Publish` generation is enabled

## Site Builder behavior

### Empty project entry

When `static_pages` is empty, entering `Site` must show `Site Setup` directly.

The wizard remains the standard way to create the first `home/index.html`.
Presets continue to define the initial page set, including the root home page.

### Normal configured entry

When a real root page exists, `Site` opens the normal builder overview/editor.

The `Reconfigure` action remains available only in this state.

### Deleting the last root page

If the user deletes the last page that exports to `index.html`:

- the deletion must persist as-is
- the site returns to the unconfigured state
- the builder falls back to `Site Setup`

There must be no backend repair step that silently recreates `Home`.

## API behavior

### `GET /api/site/config`

Return the real YAML state.

Required changes:

- stop injecting `_default_root_index_page()` when `static_pages` is empty
- keep normal output alias normalization for legacy root paths
- keep duplicate validation rules

### `PUT /api/site/config`

Persist exactly the site structure sent by the UI.

Required changes:

- stop prepending `_default_root_index_page()` when no root page exists
- allow `static_pages: []`
- keep validation for duplicate `output_file`
- keep the rule that there can be at most one root `index.html`

### Validation

Validation must enforce structural correctness, not product assumptions.

Allowed:

- empty `static_pages`
- no root page

Rejected:

- multiple root `index.html` pages
- duplicate `output_file` values

## Scaffold and initial export config behavior

Scaffold may continue to create a minimal `web_pages` export target so the GUI
has a stable place to store future site configuration.

However, scaffold must not create a default root page.

Target scaffold shape:

```yaml
exports:
  - name: web_pages
    enabled: true
    exporter: html_page_exporter
    params:
      template_dir: templates/
      output_dir: exports/web
    static_pages: []
    groups: []
```

The same rule applies to any code path that creates the default
`html_page_exporter` entry.

When references exist, scaffold still appends group entries as it does today.

## Publish behavior

### Generation readiness

`Publish` generation is enabled only when the project contains a real root
static page exporting to `index.html`.

This is stricter than “HTML exporter exists” and more accurate than “groups
exist”.

### Blocked state

When no publishable root page exists:

- disable the generation CTA
- show a clear message that the site must be configured first
- provide a primary action back to the Site Builder

Recommended copy direction:

- title: `Site not configured`
- description: explain that a root page must be created in `Site` before
  generation can start

### Non-blocking quality warning

Once generation is allowed, `Publish` may still show a non-blocking warning if
the site has a root page but no visible navigation path to useful content.

This warning should not block generation. It addresses the user-value concern
without conflating it with base readiness.

## Legacy placeholder handling

Projects already touched by the previous behavior may contain an automatically
generated `Home` page that the user never configured.

The API should remain literal and return the YAML as stored. The readiness layer
used by `SiteBuilder` entry logic and by `pipeline.py` site-status computation
must recognize a narrow legacy placeholder case as unconfigured:

- exactly one static page
- page name `home`
- template `index.html`
- output `index.html`
- no meaningful context
- no navigation entry pointing to `/index.html`
- no footer link pointing to `/index.html`

In that case:

- `Site` opens `Site Setup`
- `Publish` remains blocked

This recognition should be narrow so that a legitimate minimal site with a real
home page and visible navigation is still treated as configured.

No background YAML rewrite is required for this design.

## Testing strategy

### API tests

Update or replace the existing tests that currently assert automatic home-page
injection:

- `tests/gui/api/routers/test_site.py`
  - remove expectations that `GET /api/site/config` injects `home`
  - remove expectations that `PUT /api/site/config` recreates `home`
- `tests/gui/api/routers/test_templates.py`
  - remove expectations that scaffold creates a default home page

Add tests for:

- empty `static_pages` returned unchanged by `GET /api/site/config`
- empty `static_pages` persisted unchanged by `PUT /api/site/config`
- scaffold creating `web_pages` with `static_pages: []`
- duplicate root/index validation still enforced

### Frontend tests

Add or update tests for:

- `SiteBuilder` opens the wizard for empty site config
- deleting the last root page returns the builder to the setup state
- legacy placeholder config is treated as unconfigured

### Publish tests

Add or update tests for:

- generation CTA disabled when no root static page exists
- blocked-state message points the user back to `Site`
- generation CTA enabled after a preset creates a real root page

## Success criteria

The design is successful when all of the following are true:

1. A fresh project enters `Site Setup` immediately on first visit to `Site`.
2. No code path silently creates `home/index.html`.
3. Deleting the last home page persists and returns the project to setup.
4. `Publish` cannot generate a site until a real root page exists.
5. Existing projects with only the legacy synthetic `Home` do not remain stuck
   in the configured state.
