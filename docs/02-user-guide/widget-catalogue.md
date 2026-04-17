# Collections and Widget Catalogue

Collections is where you configure transform-backed outputs and browse
available widgets. In the code this lives under `features/collections`; in the
GUI the route still appears as `/groups`.

## Entry points

- `src/niamoto/gui/ui/src/features/collections/components/CollectionsModule.tsx`
- `src/niamoto/gui/ui/src/features/collections/components/CollectionsOverview.tsx`
- `src/niamoto/gui/ui/src/features/collections/components/CollectionPanel.tsx`
- `src/niamoto/gui/ui/src/components/widgets/WidgetGallery.tsx`
- `src/niamoto/gui/ui/src/components/widgets/AddWidgetModal.tsx`

## Use this area to

- browse the reference collections created by import
- inspect freshness and computation state
- configure widget-backed content blocks
- manage index/list configuration
- manage API export configuration for a collection

## Typical workflow

1. Open the collections overview.
2. Pick a collection.
3. Use the collection tabs to edit sources, content blocks, list pages, or API exports.
4. Add widgets through the gallery.
5. Preview the result.
6. Recompute the collection when needed.

## Widget gallery

The widget gallery groups suggestions by field. It also supports:

- field-grouped suggestions
- semantic multi-field suggestions
- inline preview
- combined widget proposals
- plugin-backed parameter forms

## Related documents

- [transform.md](transform.md)
- [preview.md](preview.md)
- [../06-reference/transform-plugins.md](../06-reference/transform-plugins.md)
- [../06-reference/widgets-and-transform-workflow.md](../06-reference/widgets-and-transform-workflow.md)
