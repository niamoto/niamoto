# Import Workflow

Use import to add source files, review detected roles, and launch the import
from the same workspace.

The import flow combines:

- file upload
- live analysis
- auto-configuration review
- in-context import execution
- post-import exploration and enrichment

## Entry points

Frontend:

- `src/niamoto/gui/ui/src/features/import/module/DataModule.tsx`
- `src/niamoto/gui/ui/src/features/import/components/ImportWizard.tsx`
- `src/niamoto/gui/ui/src/features/import/components/review/AutoConfigDisplay.tsx`
- `src/niamoto/gui/ui/src/features/import/components/dashboard/SourcesOverview.tsx`

Frontend job hooks:

- `src/niamoto/gui/ui/src/features/import/hooks/useAutoConfigureJob.ts`
- `src/niamoto/gui/ui/src/features/import/hooks/useImportJob.ts`

Backend:

- `src/niamoto/gui/api/routers/imports.py`
- `src/niamoto/gui/api/routers/smart_config.py`
- `src/niamoto/core/imports/auto_config_service.py`

## Workflow

### 1. File selection

Add files through the upload surface.

Supported project inputs typically include:

- CSV tables
- GeoPackage / GeoJSON layers
- TIFF rasters

The file list stays visible during analysis, with live status for each file.

### 2. Review live analysis

Niamoto starts an auto-configuration job and streams analysis events.

The GUI shows that state in place:

- file queued
- file under analysis
- detected as dataset / reference / auxiliary source / layer
- review or notice status when needed

### 3. Auto-configuration review

When analysis finishes, the GUI shows a review focused on:

- aggregation candidates
- supporting sources
- notices and review-required cases
- inline editing of the generated configuration

The YAML view stays available if you want to edit the generated config directly.

### 4. Import execution

Niamoto keeps import state attached to the reviewed entities and references:

- queued
- importing
- done
- failed

### 5. Continue from the workspace

After import, the workspace shifts to exploration:

- collections and references
- supporting datasets and layers
- next actions such as enrichment

## Auto-configuration

The current auto-config distinguishes between:

- datasets
- references
- auxiliary sources
- metadata layers

Some files become primary entities. Others stay attached to a reference group as
supporting sources.

## Enrichment

If a reference supports API enrichment, the workspace exposes `Enrich now` as a
next step.

The reference detail flow owns enrichment setup and execution, not the import
wizard.
