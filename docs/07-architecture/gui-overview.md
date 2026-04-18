# GUI Architecture Overview

Niamoto GUI is the interactive layer used to configure, inspect, and operate a
Niamoto project.

It combines:

- a Python backend built with FastAPI
- a React frontend built with Vite
- an optional desktop runtime through Tauri

## Main responsibilities

### Backend

The backend is responsible for:

- resolving the active project instance
- exposing configuration and data APIs
- orchestrating import, transform, preview, build, and deploy jobs
- serving the built frontend in packaged mode

Key entry points:

- `src/niamoto/gui/api/app.py`
- `src/niamoto/gui/api/context.py`

### Frontend

The frontend is responsible for:

- import and auto-configuration review
- dataset and reference exploration
- group configuration
- site editing and layout work
- build and deployment workflows
- desktop onboarding and project switching

The frontend uses a feature-oriented structure:

- `src/niamoto/gui/ui/src/app`
- `src/niamoto/gui/ui/src/features`
- `src/niamoto/gui/ui/src/shared`

Some root folders still hold compatibility code, but they are no longer the
default extension points:

- `src/niamoto/gui/ui/src/hooks`: compatibility façades for hooks that are being moved into `src/features` or `src/shared`
- `src/niamoto/gui/ui/src/lib/api`: compatibility façades for feature APIs that are being moved closer to their domain
- `src/niamoto/gui/ui/src/components`: shared UI primitives plus cross-feature components that have not moved into a feature yet

Current architecture guardrails:

- new domain logic should land in a feature folder first
- only truly cross-feature code should land in `src/shared`
- route modules should be imported by leaf path instead of feature barrels to preserve lazy chunk boundaries
- feature APIs and query keys should live next to the feature they serve
- large optional editors or third-party modules should remain behind lazy boundaries

## Main GUI domains

- `dashboard`: home route and project hub
- `import`: file upload, auto-configuration, import execution, enrichment entry points
- `collections`: collection and widget configuration, still routed under `/groups`
- `site`: page, navigation, and appearance editing
- `publish`: build and deploy workflows
- `tools`: utility screens such as preview, explorer, plugins, settings
- `welcome`: desktop onboarding and project selection

## Code entry points

For the concrete route map and backend wiring, inspect:

- `src/niamoto/gui/ui/src/app/router.tsx`
- `src/niamoto/gui/api/app.py`
