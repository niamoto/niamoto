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
pnpm test
pnpm lint
pnpm preview
```

## Runtime modes

The frontend runs in two contexts:

- Web mode: standard Vite app in the browser
- Desktop mode: embedded in the Niamoto Tauri application

Some behavior differs by runtime. Example: theme fonts are loaded from Google Fonts in web mode, but from local files in desktop mode for offline support.

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
- Avoid adding new feature logic to root `src/hooks` unless it is genuinely cross-feature
- Avoid adding new feature API clients to root `src/lib/api` unless they are genuinely shared
- `src/components` is still partly transitional; prefer feature-local components for new work

## Notes for maintainers

- `dist/` is build output from Vite and is ignored by Git
- `.ruff_cache/` and `.DS_Store` should not be committed
- Large frontend refactor notes live in:
  - [docs/plans/2026-03-25-refactor-frontend-feature-architecture-plan.md](/Users/julienbarbe/Dev/clients/niamoto/docs/plans/2026-03-25-refactor-frontend-feature-architecture-plan.md)
