# Plugin Development

> Status: Active
> Audience: Python developers extending Niamoto.
> Purpose: Write transformers, loaders, widgets, and exporters.

Niamoto supports four plugin types that plug into the pipeline:

| Type         | Registered with              | Purpose                                   |
| ------------ | ---------------------------- | ----------------------------------------- |
| Loaders      | `PluginType.LOADER`          | Read data from CSVs, GIS files, APIs.     |
| Transformers | `PluginType.TRANSFORMER`     | Compute statistics, aggregates, indices.  |
| Exporters    | `PluginType.EXPORTER`        | Produce HTML, JSON, or file artifacts.    |
| Widgets      | `PluginType.WIDGET`          | Render interactive charts, maps, tables.  |

## Start here

- [architecture.md](architecture.md) — how plugins plug into the
  import / transform / export pipeline.
- [creating-transformers.md](creating-transformers.md) — build a
  transformer, register it, validate its config.
- [building-widgets.md](building-widgets.md) — render a custom widget,
  wire it to a transformer, preview it in the GUI.
- [custom-exporters.md](custom-exporters.md) — generate custom
  output artifacts.
- [database-aggregator-guide.md](database-aggregator-guide.md) — a
  worked example combining several plugin types.

## If you want to…

- **Add a new statistic** — write a transformer
  ([creating-transformers.md](creating-transformers.md)).
- **Render data in a new way** — write a widget
  ([building-widgets.md](building-widgets.md)).
- **Ingest a new file format** — write a loader
  (see [architecture.md](architecture.md) for the base class).
- **Emit a new export artifact** — write an exporter
  ([custom-exporters.md](custom-exporters.md)).
- **Look at a complex real plugin** — read
  [database-aggregator.md](database-aggregator.md).

## Skeleton

```python
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register


@register("my_plugin", PluginType.TRANSFORMER)
class MyPlugin(TransformerPlugin):
    config_model = MyPluginConfig  # Pydantic model

    def transform(self, data, config):
        # compute and return
        return processed
```

## Workflow

1. Pick the plugin type.
2. Implement the plugin class and its Pydantic `config_model`.
3. Register with `@register("name", PluginType.X)`.
4. Configure it in `transform.yml` or `export.yml`.
5. Add unit and integration tests under `tests/plugins/`.

## Related

- [../06-reference/README.md](../06-reference/README.md) — API and
  schema references.
- [../05-ml-detection/README.md](../05-ml-detection/README.md) — how
  the ML classifier plugs into the import workflow.
- [../09-architecture/README.md](../09-architecture/README.md) — the
  plugin system in context.
