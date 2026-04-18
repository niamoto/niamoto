# Preview System

The preview system renders widgets in the GUI before publication.

It is used for:

- lightweight preview tiles in lists and grids
- full preview panes in detailed editors
- inline validation of widget and transform combinations

## High-level model

The preview flow is:

```text
resolve -> load -> transform -> render -> wrap
```

The backend has specialized branches depending on widget type, but the same
flow still applies:

1. resolve the requested widget/template
2. load the relevant source data
3. run the transformer if needed
4. render the widget output
5. wrap it into safe HTML for iframe display

## Backend pieces

Main backend files:

- `src/niamoto/gui/api/services/preview_engine/engine.py`
- `src/niamoto/gui/api/services/preview_engine/models.py`
- `src/niamoto/gui/api/services/preview_engine/plotly_bundle_resolver.py`
- `src/niamoto/gui/api/routers/preview.py`

The engine returns:

- a complete HTML document for `iframe srcDoc`
- an `etag` for conditional cache handling
- a preview key and optional warnings

## Frontend pieces

Main frontend files:

- `src/niamoto/gui/ui/src/lib/preview/types.ts`
- `src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts`
- `src/niamoto/gui/ui/src/components/preview`

The frontend layer handles:

- query caching and deduplication
- thumbnail vs full preview modes
- visibility-aware loading
- iframe lifecycle and error display

## Plotly bundles

The preview system uses custom Plotly bundles instead of the full Plotly distribution.

That split keeps preview payloads smaller:

- chart previews and map previews do not need the same payload
- the GUI can choose a smaller bundle for non-map widgets
- bundle selection is resolved automatically by the backend

## Security model

Preview HTML is rendered in sandboxed iframes.

The backend and frontend keep three rules in place:

- isolate preview content from the parent UI
- avoid direct DOM access from preview code
- escape dynamic content before interpolation

## Related docs

- [GUI preview API reference](../06-reference/gui-preview-api.md)
