# Preview API Reference

The preview API generates HTML previews for widgets and related GUI preview surfaces.

## Endpoints

### `GET /api/preview/{template_id}`

Render the preview HTML for a widget identified by `template_id`.

Query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `group_by` | `string` | auto-resolved | Aggregation reference such as `taxons` or `plots` |
| `source` | `string` | `null` | Explicit data source |
| `entity_id` | `string` | `null` | Specific entity identifier |
| `mode` | `"thumbnail" \| "full"` | `"full"` | Preview rendering mode |

Responses:

- `200 OK`: full HTML document
- `304 Not Modified`: when the ETag still matches
- `500`: wrapped preview error HTML

Important headers:

- `ETag`
- `Cache-Control: no-cache`

Example:

```text
GET /api/preview/plots_dbh_distribution_bar_plot?group_by=plots&entity_id=2&mode=full
```

### `POST /api/preview`

Render a preview from an inline transformer/widget configuration.

Example body:

```json
{
  "template_id": null,
  "group_by": "taxons",
  "source": "plots",
  "entity_id": "5",
  "mode": "full",
  "inline": {
    "transformer_plugin": "categorical_distribution",
    "transformer_params": {
      "field": "strata",
      "categories": ["1", "2", "3"]
    },
    "widget_plugin": "bar_plot",
    "widget_params": {
      "x_axis": "categories",
      "y_axis": "counts"
    },
    "widget_title": "Strata distribution"
  }
}
```

If `inline` is omitted, `template_id` resolution is used instead.

### `GET /api/templates/preview/{template_id}`

Legacy compatibility alias for `GET /api/preview/{template_id}`.

## Response model

The response is a full HTML document suitable for `iframe srcDoc`.

The backend may inject:

- base styles
- preview metadata
- the appropriate Plotly bundle when needed

## Preview modes

| Aspect | `thumbnail` | `full` |
|--------|-------------|--------|
| Plotly `staticPlot` | `true` | `false` |
| Mode bar | hidden | visible |
| Interactivity | reduced | full |
| Intended use | tiles and lists | detailed preview |

## Cache model

There are two layers:

### HTTP cache

The backend returns an ETag derived from preview identity and data/config fingerprinting.

### Frontend cache

The frontend preview hook uses TanStack Query for:

- deduplication
- memory caching
- explicit invalidation after import or config updates

## Frontend usage

Main frontend files:

- [src/niamoto/gui/ui/src/lib/preview/types.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/lib/preview/types.ts)
- [src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/lib/preview/usePreviewFrame.ts)

## Related document

- [../architecture/preview-system.md](/Users/julienbarbe/Dev/clients/niamoto/docs/06-gui/architecture/preview-system.md)
