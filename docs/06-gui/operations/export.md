# Export and Publish Workflow

The current GUI distinguishes between:

- site configuration
- publish/build operations

The older idea of a generic “export builder” is not the best description of the current product.

## Main entry points

- [src/niamoto/gui/ui/src/features/site](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/site)
- [src/niamoto/gui/ui/src/features/publish](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/publish)

## Current split

### Site

The site area covers:

- navigation
- pages
- appearance
- content editing
- references between content and generated group pages

### Publish

The publish area covers:

- build status
- deployment-oriented actions
- generated output lifecycle

## Product model

Users generally move through these stages:

1. Import and configure data
2. Configure groups and widgets
3. Configure the site
4. Build and publish

This is more accurate than a generic “export type selector” model.

## Why this matters

Earlier GUI notes described:

- dashboards as export types
- mobile app export
- a theme-first export builder
- a generic deploy wizard

Those descriptions were exploratory and should not be treated as the current implementation.
