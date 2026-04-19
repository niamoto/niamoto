# Niamoto UI

Frontend React/TypeScript/Vite for the Niamoto desktop and web interface.

This UI powers:
- data import and auto-configuration
- group configuration
- site configuration
- publish workflows
- desktop onboarding and project switching

The codebase is no longer a default Vite scaffold. It follows a feature-oriented structure with shared app shell and utilities.

## Run locally

From this directory:

```bash
pnpm install
pnpm dev
```

Useful commands:

```bash
pnpm build
pnpm build:stats
pnpm test
pnpm lint
pnpm preview
```

## Runtime modes

The frontend runs in two contexts:

- Web mode: standard Vite app in the browser
- Desktop mode: embedded in a native shell, currently Tauri in production and Electron as an experimental parallel shell

Some behavior differs by runtime. Example: theme fonts are loaded from Google Fonts in web mode, but from local files in desktop mode for offline support.

The renderer now detects both the desktop mode and the active shell through the
shared runtime contract exposed by `/api/health/runtime-mode` and the bootstrap
attributes injected at startup. Shell-specific native capabilities flow through
`src/shared/desktop/bridge.ts` rather than through direct Tauri imports.

## Architecture

Main source layout:

- [src/app](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/app): bootstrap, routing, app shell wiring
- [src/features](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features): domain features
- [src/shared](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/shared): true cross-feature code
- [src/components](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/components): reusable UI and legacy/transverse domain components not yet moved into a feature
- [src/hooks](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/hooks): remaining shared hooks not yet feature-scoped
- [src/lib](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/lib): shared utilities and still-shared API modules
- [src/stores](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/stores): global Zustand stores
- [src/i18n](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/i18n): translations
- [src/themes](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/themes): theme registry and presets

Current feature folders:

- [src/features/dashboard](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/dashboard)
- [src/features/import](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import)
- [src/features/groups](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/groups)
- [src/features/site](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site)
- [src/features/publish](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/publish)
- [src/features/tools](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/tools)
- [src/features/welcome](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/welcome)

## Architecture guardrails

The frontend is still finishing a migration away from the legacy root folders. Treat these rules as current source of truth:

- New product code belongs in `src/features/<domain>`
- Put only genuinely cross-feature code in `src/shared`
- `src/hooks` is a transitional compatibility layer; do not add new hooks there
- `src/lib/api` is a transitional compatibility layer; new feature APIs belong in `src/features/<domain>/api`
- `src/components` is still partly legacy; new domain components should live inside their feature first
- Import route modules by leaf path, not by feature barrel, to preserve lazy chunk boundaries
- Put React Query keys next to the feature or shared API they belong to
- Heavy editors and other large third-party modules should stay behind lazy boundaries

Current transition examples:

- import data hooks now live under [src/features/import/hooks](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/hooks)
- publish export API now lives under [src/features/publish/api](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/publish/api)
- root modules under [src/hooks](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/hooks) and [src/lib/api](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/lib/api) remain as compatibility façades during the migration

ESLint now enforces part of these rules directly:

- feature barrels such as `@/features/import` are disallowed
- import feature code must use feature-local import hooks
- publish feature code must use the feature-local export API

## Bundle measurement

Use the bundle stats command after changes that affect routing, editors, or other large dependencies:

```bash
pnpm build:stats
```

This runs a production build and prints the heaviest JavaScript and CSS assets from `dist/assets`. It is the lightweight bundle check to use before and after larger UI refactors.

## Important flows

### Import workflow

Main entry points:

- [src/features/import/module/DataModule.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/module/DataModule.tsx)
- [src/features/import/components/ImportWizard.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/components/ImportWizard.tsx)
- [src/features/import/components/review/AutoConfigDisplay.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/components/review/AutoConfigDisplay.tsx)
- [src/features/import/components/dashboard/ImportDashboard.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/components/dashboard/ImportDashboard.tsx)

Job orchestration lives in:

- [src/features/import/hooks/useAutoConfigureJob.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/hooks/useAutoConfigureJob.ts)
- [src/features/import/hooks/useImportJob.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/hooks/useImportJob.ts)

### Home dashboard

The `/` route is implemented in:

- [src/features/dashboard/views/ProjectHub.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/dashboard/views/ProjectHub.tsx)

### Site builder

Main site configuration UI lives under:

- [src/features/site](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site)
- [src/components/site](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/components/site)

This area still mixes feature-scoped and older transverse components.

## Assets, public files, and fonts

- [src/assets](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/assets): imported assets bundled by Vite
- [public/favicon](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/public/favicon): static favicon files
- [public/fonts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/public/fonts): local desktop font files

Local fonts are referenced through:

- [public/fonts/fonts.css](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/public/fonts/fonts.css)
- [src/themes/index.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/themes/index.ts)

Do not remove `public/fonts` unless the desktop font-loading strategy changes.

## shadcn/ui

[components.json](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/components.json) configures shadcn/ui for this project. It is used by shadcn tooling to know:

- where components live
- which aliases are available
- which global CSS file the project uses

Keep it in sync with the actual UI structure if shadcn tooling is still used.

## Conventions

- New product workflows should go into `src/features/<domain>`
- Put only truly shared code in `src/shared`
- Avoid adding new feature logic to root `src/hooks`
- Avoid adding new feature API clients to root `src/lib/api`
- `src/components` is still partly transitional; prefer feature-local components for new work
- Avoid feature barrel imports on lazy route boundaries

## Notes for maintainers

- `dist/` is build output from Vite and is ignored by Git
- `.ruff_cache/` and `.DS_Store` should not be committed
- Large frontend refactor notes live in:
  - [docs/plans/2026-03-25-refactor-frontend-feature-architecture-plan.md](/Users/julienbarbe/Dev/clients/niamoto/docs/plans/2026-03-25-refactor-frontend-feature-architecture-plan.md)
