# Import Workflow

The import workflow is one of the main interactive flows of the Niamoto GUI.

It is no longer a static multi-step form. The current flow is built around:

- file upload
- live analysis
- auto-configuration review
- in-context import execution
- post-import exploration and enrichment

## Main entry points

Frontend:

- [src/niamoto/gui/ui/src/features/import/module/DataModule.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/module/DataModule.tsx)
- [src/niamoto/gui/ui/src/features/import/components/ImportWizard.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/components/ImportWizard.tsx)
- [src/niamoto/gui/ui/src/features/import/components/review/AutoConfigDisplay.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/components/review/AutoConfigDisplay.tsx)
- [src/niamoto/gui/ui/src/features/import/components/dashboard/ImportDashboard.tsx](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/components/dashboard/ImportDashboard.tsx)

Frontend job hooks:

- [src/niamoto/gui/ui/src/features/import/hooks/useAutoConfigureJob.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/hooks/useAutoConfigureJob.ts)
- [src/niamoto/gui/ui/src/features/import/hooks/useImportJob.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/import/hooks/useImportJob.ts)

Backend:

- [src/niamoto/gui/api/routers/imports.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/api/routers/imports.py)
- [src/niamoto/gui/api/routers/smart_config.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/api/routers/smart_config.py)
- [src/niamoto/core/imports/auto_config_service.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/auto_config_service.py)

## Current user flow

### 1. File selection

The user adds files through the upload surface.

Supported project inputs typically include:

- CSV tables
- GeoPackage / GeoJSON layers
- TIFF rasters

The file list stays visible during analysis, with per-file live status.

### 2. Live auto-analysis

The backend starts an auto-configuration job and streams real analysis events.

The frontend reflects this in-context:

- file queued
- file under analysis
- detected as dataset / reference / auxiliary source / layer
- review or notice status when needed

The user no longer waits behind a generic spinner without context.

### 3. Auto-configuration review

When analysis completes, the GUI shows a review focused on:

- aggregation candidates
- supporting sources
- notices and review-required cases
- inline editing of the generated configuration

The YAML view remains available for advanced users.

### 4. Import execution

Import execution now stays in the same context.

The GUI no longer switches to a detached import screen. Instead, import state is reflected directly on the reviewed entities and references:

- queued
- importing
- done
- failed

### 5. Post-import workspace

After import, the GUI moves to an exploration-oriented view centered on:

- aggregation groups
- supporting datasets and layers
- next actions such as enrichment

## Auto-configuration model

The current auto-config distinguishes between:

- datasets
- references
- auxiliary sources
- metadata layers

An important product concept is that not every file becomes a primary entity. Some files are detected as supporting sources and attached to a reference group.

## Enrichment

For references that support API enrichment, the import flow exposes `Enrich now` as a next step.

The enrichment setup and execution live in the reference detail flow, not inside the import wizard itself.

## What changed compared with earlier designs

Older design notes described:

- a fixed five-step wizard
- explicit field mapping as a central user task
- a separate import progress screen
- generic “data quality” scoring

These descriptions are no longer accurate and should not be used as the reference model for current GUI work.
