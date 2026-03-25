# GUI Architecture Overview

Niamoto GUI is the interactive layer used to configure, inspect, and operate a Niamoto project.

It combines:

- a Python backend built with FastAPI
- a React frontend built with Vite
- an optional desktop runtime through Tauri

## Main responsibilities

### Backend

The backend is responsible for:

- resolving the active project instance
- exposing configuration and data APIs
- orchestrating import, transform, preview, and publish jobs
- serving the built frontend in packaged mode

Key entry points:

- [src/niamoto/gui/api/app.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/api/app.py)
- [src/niamoto/gui/api/context.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/api/context.py)

### Frontend

The frontend is responsible for:

- import and auto-configuration review
- dataset and reference exploration
- group configuration
- site editing
- publish workflows
- desktop onboarding and project switching

The current frontend structure is feature-oriented:

- [src/app](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/app)
- [src/features](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features)
- [src/shared](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/shared)

## Main GUI domains

- `dashboard`: home route and project hub
- `import`: file upload, auto-configuration, import execution, enrichment entry points
- `groups`: group and widget configuration
- `site`: site builder and content configuration
- `publish`: build and deploy workflows
- `tools`: utility screens such as preview, explorer, plugins, settings
- `welcome`: desktop onboarding and project selection

## Source of truth

For low-level structure and conventions, prefer the code-level READMEs:

- [src/niamoto/gui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/README.md)
- [src/niamoto/gui/ui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/README.md)
