# Frontend Feature Architecture Plan

Date: 2026-03-25
Scope: `src/niamoto/gui/ui/src`
Status: Active reference plan

## Objective

Evolve the frontend from a hybrid organization based on `pages/`, `components/`,
`hooks/`, and `lib/api/` into a more stable feature-oriented structure, without
changing public URLs or backend contracts.

The goal is not architectural purity. The goal is to make the codebase easier
to navigate, easier to extend, and harder to regress.

## Current Direction

The frontend now has a usable target structure:

- `app/` for application bootstrap, routing, and global providers
- `features/` for business workflows and routed domains
- `shared/` for truly cross-cutting UI, layout, theme, i18n, and low-level
  infrastructure

The migration is already advanced for:

- `import`
- `groups`
- `publish`
- `site`
- `tools`
- `welcome`

Legacy wrappers, dead pages, dead routes, and several unused dependencies have
already been removed.

## Architecture Principles

### 1. Features own business workflows

A file belongs in `features/<domain>` if it carries:

- a routed screen
- a business workflow
- a domain-specific editor
- a domain-specific API client
- a domain-specific hook

Examples:

- import analysis and import execution belong to `features/import`
- post-import exploration belongs to `features/import`
- site configuration routes belong to `features/site`
- developer tools pages belong to `features/tools`

### 2. Shared stays intentionally narrow

`shared/` should only contain code that is both:

- reusable across multiple domains
- not meaningfully tied to a single business workflow

Target contents for `shared/`:

- `shared/ui/`: generic UI primitives and wrappers
- `shared/layout/`: shell, layout containers, navigation scaffolding
- `shared/lib/`: low-level HTTP client and pure utilities
- `shared/theme/`
- `shared/i18n/`
- optionally `shared/hooks/` for purely technical hooks

`shared/` must not become a second generic dumping ground.

### 3. Avoid adding new business logic to horizontal roots

The following top-level folders still exist and are partly transitional:

- `hooks/`
- `lib/api/`
- `components/`

Rule:

- no new business workflow should start in those roots
- new workflow code goes into a feature
- shared technical code goes into `shared/`

## Target Directory Model

### app

`app/` contains:

- root `App.tsx`
- `main.tsx`
- global providers
- route composition

This is the only place where app-wide routing should be orchestrated.

### features

Each feature may contain:

- `components/`
- `views/`
- `hooks/`
- `api/`
- `store/`
- `types/`
- `utils/`

Not every feature needs all of these folders. The point is to colocate
workflow code rather than spread it across horizontal roots.

### shared

`shared/` should become the stable home for:

- common layout primitives
- app-wide providers and adapters
- HTTP client
- technical helpers
- cross-feature UI primitives

### pages

`pages/` should remain minimal.

Accepted use:

- route wrappers only, if still needed temporarily

Rejected use:

- real business logic
- duplicate routed screens
- feature implementations

## Domain Decisions

### Import

`features/import` is the reference implementation for the architecture.

It owns:

- upload flow
- auto-config analysis
- pre-import review
- import execution
- post-import data workspace
- reference enrichment entrypoints used from the import/data flow

This feature should continue to serve as the model for future migrations.

### Groups

`features/groups` owns:

- group pages
- group panel
- group-specific source management

No new code should be added under old `components/groups`.

### Publish

`features/publish` owns:

- publish workspace
- build/deploy/history views
- publish store

### Site

`features/site` now owns routed site views and the site panel entrypoint.

The deeper site builder internals still live under `components/site`, which is
acceptable for now. The next step is not to move everything immediately, but to
avoid creating new site workflow code outside `features/site`.

### Tools

`features/tools` now owns routed tool views such as:

- data explorer
- preview
- settings
- plugins
- API docs
- config editor

The `YamlEditor` used by the config editor has already been moved into this
feature.

### Welcome

`features/welcome` is already simple and aligned enough. No structural action is
needed unless the onboarding flow grows significantly.

## Remaining Structural Decisions

These are not cleanup tasks anymore. These are design choices.

### Decision 1: the future of `hooks/`

Current issue:

`hooks/` still mixes technical hooks and business-facing hooks.

Recommended rule:

- generic technical hooks move to `shared/hooks`
- business hooks move to `features/<domain>/hooks`
- root `hooks/` becomes transitional only

Recommended first candidates:

- move `useSiteConfig` to `features/site/hooks`
- move `useWelcomeScreen` to `features/welcome/hooks`
- move `usePlugins` to `features/tools/hooks`

Open question:

- `useDatasets`, `useReferences`, and `useProjectInfo` may deserve either
  `shared/` treatment or a future shared data-catalog feature

### Decision 2: the future of `lib/api/`

Current issue:

`lib/api/` remains horizontally organized while the rest of the application is
becoming feature-first.

Recommended rule:

- `shared/lib/api/client.ts` remains the common transport layer
- business API clients migrate gradually to feature-local `api/` folders
- `lib/api/` becomes transitional and eventually very small

Recommended migration path:

- new API clients must not be added to `lib/api/`
- existing clients move when the related feature is touched

### Decision 3: the status of large domain folders still under `components/`

Current issue:

The following folders still contain substantial domain logic:

- `components/site`
- `components/widgets`
- `components/content`
- `components/layout-editor`
- `components/plugins`

Recommended rule:

- do not migrate them all at once
- only promote one to a dedicated feature when it becomes necessary

Current recommendation:

- leave `widgets` and `content` where they are for now
- treat `site` as the next likely candidate for deeper feature colocation if it
  continues to grow

## Practical Rules for New Code

When adding code:

1. If it is part of a routed business flow, put it in a feature.
2. If it is reusable and domain-neutral, put it in `shared/`.
3. If it only exists because of old structure, do not add to it.
4. If unsure between `shared` and a feature, default to the feature.
5. Move code opportunistically when touching an area; do not perform large
   speculative migrations.

## Recommended Next Migrations

### Short-term

1. Keep `features/` as the only place for new workflow code.
2. Gradually drain `hooks/` into `shared/hooks` and `features/*/hooks`.
3. Gradually drain `lib/api/` into `shared/lib/api/client` plus feature-local
   API folders.

### Medium-term

1. Re-evaluate `components/site` as a possible deeper feature refactor.
2. Re-evaluate whether datasets/references/project metadata deserve a dedicated
   shared domain layer instead of generic hooks.
3. Continue splitting oversized files when touched, but only inside their
   owning feature.

## Anti-Goals

This plan does not aim to:

- rename the whole codebase for aesthetic reasons
- eliminate every top-level horizontal folder immediately
- force every reusable component into `shared/`
- migrate every legacy component in one big bang

The architecture should become clearer through steady constraints, not through
mass relocation for its own sake.

## Success Criteria

The frontend architecture is considered stable enough when:

- a new developer can find import-related code starting from `features/import`
- no new routed workflow is added outside `features/`
- `shared/` contains only truly transversal code
- `hooks/` and `lib/api/` stop growing horizontally
- legacy `components/*` folders shrink only when touched, without blocking
  feature work

## Current Assessment

As of this document:

- the codebase is structurally coherent enough
- the obvious cleanup phase is largely complete
- the remaining work is primarily about stabilizing boundaries, not deleting
  leftovers

This is a good stopping point for cleanup and a good starting point for
disciplined feature-first growth.
