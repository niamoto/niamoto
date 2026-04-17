# Preview Workflow

Niamoto shows preview in three parts of the desktop workflow.

## Preview surfaces

### 1. Widget preview inside collections

The widget editor can render the current widget configuration before you save or
recompute everything.

Main code paths:

- `src/niamoto/gui/ui/src/components/widgets/WidgetPreviewPanel.tsx`
- `src/niamoto/gui/ui/src/components/widgets/AddWidgetModal.tsx`
- `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts`
- `src/niamoto/gui/api/routers/preview.py`

### 2. Site preview while editing pages

The site area previews templates and page configuration while you edit the site.

Main code paths:

- `src/niamoto/gui/ui/src/features/site/components/SiteBuilderPreview.tsx`
- `src/niamoto/gui/ui/src/features/site/views/SitePagesPage.tsx`

### 3. Generated-site preview in publish

The publish area can display the generated site in a device frame after a build.

Main code paths:

- `src/niamoto/gui/ui/src/features/publish/views/index.tsx`
- `src/niamoto/gui/ui/src/components/ui/preview-frame`

## What each preview is for

Each preview answers a different question:

- widget preview checks a block before you save or recompute it
- site preview checks layout, navigation, and page composition
- generated-site preview checks the built portal before or after deployment

## Related documents

- [transform.md](transform.md)
- [widget-catalogue.md](widget-catalogue.md)
- [export.md](export.md)
- [../06-reference/gui-preview-api.md](../06-reference/gui-preview-api.md)
