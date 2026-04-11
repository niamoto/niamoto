# GUI Documentation

This directory documents the current Niamoto GUI as it exists today.

The GUI is split into:

- a FastAPI backend in [src/niamoto/gui/api](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/api)
- a React/Vite frontend in [src/niamoto/gui/ui](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui)

For code-level structure, see:

- [src/niamoto/gui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/README.md)
- [src/niamoto/gui/ui/README.md](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/README.md)

## Documentation map

### Architecture

- [architecture/overview.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/architecture/overview.md)
- [architecture/backend-frontend-runtime.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/architecture/backend-frontend-runtime.md)
- [architecture/preview-system.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/architecture/preview-system.md)

### Operations

- [operations/import.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/operations/import.md)
- [operations/transform.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/operations/transform.md)
- [operations/export.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/operations/export.md)
- [operations/desktop-smoke-tests.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/operations/desktop-smoke-tests.md)

### Reference

- [reference/preview-api.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/reference/preview-api.md)
- [reference/transform-plugins.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/reference/transform-plugins.md)
- [reference/widgets-and-transform-workflow.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/reference/widgets-and-transform-workflow.md)

## Scope

This folder should document:

- the current GUI architecture
- the current user-facing workflows
- stable API and preview concepts
- how GUI concepts map to the codebase

This folder should not be used for:

- outdated product plans presented as current behavior
- default framework boilerplate
- speculative UI designs without an explicit historical label

## Maintenance rules

- Prefer documenting the current implementation over aspirational designs
- Mark historical documents explicitly
- Link to source code when the code is the real source of truth
- Keep screenshots and diagrams optional; keep the text authoritative
