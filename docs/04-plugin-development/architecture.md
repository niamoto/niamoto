# Plugin System Architecture

Niamoto discovers plugins, validates config with Pydantic, then calls the matching runtime hook.

## Discovery And Override Rules

`PluginLoader.load_plugins_with_cascade(project_path)` scans three locations in this order:

1. `project/plugins`
2. `~/.niamoto/plugins`
3. bundled plugins under `src/niamoto/core/plugins`

The first plugin name wins. A project plugin can override a user or bundled plugin with the same registered name.

```python
from pathlib import Path

from niamoto.core.plugins.plugin_loader import PluginLoader

loader = PluginLoader()
loader.load_plugins_with_cascade(Path("/path/to/project"))
```

## Registry

Each plugin registers itself with `@register("name", PluginType.X)`. Niamoto stores that class in `PluginRegistry` and looks it up by name and type.

```python
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry

widget_class = PluginRegistry.get_plugin("bar_plot", PluginType.WIDGET)
```

## Plugin Types

| Type | Base class | Typical config surface | Runtime hook |
| --- | --- | --- | --- |
| Loader | `LoaderPlugin` | `transform.yml` source relations | `load_data(...)` |
| Transformer | `TransformerPlugin` | `transform.yml` `widgets_data` entries | `transform(data, config)` |
| Widget | `WidgetPlugin` | `export.yml` widget entries | `render(data, params)` |
| Exporter | `ExporterPlugin` | `export.yml` targets | `export(target_config, repository, group_filter=None)` |
| Deployer | `DeployerPlugin` | `deploy.yml` and deploy commands | async deploy / unpublish methods |

## Config Models

Most plugins expose two pieces of validation:

- `config_model` validates the full config entry, usually `plugin + params`
- `param_schema` exposes typed params for GUI forms and runtime validation

Niamoto uses `BasePluginParams`, `PluginConfig`, `WidgetConfig`, and `TargetConfig` as the shared building blocks.

## Transform Config Shape

Transform groups live in a top-level list. Each widget entry points at one transformer plugin.

```yaml
- group_by: plots
  sources:
    - name: occurrences
      data: occurrences
      grouping: plots
      relation:
        plugin: direct_reference
        key: plot_id
  widgets_data:
    dbh_distribution:
      plugin: binned_distribution
      source: occurrences
      params:
        field: dbh
        bins: [10, 20, 30, 40, 50]
```

## Export Config Shape

Export targets live under `exports:`. Widgets belong inside `groups[*].widgets`.

```yaml
exports:
  - name: web_pages
    exporter: html_page_exporter
    params:
      template_dir: templates
      output_dir: exports/web
    groups:
      - group_by: plots
        widgets:
          - plugin: info_grid
            title: Plot summary
            data_source: general_info
            params:
              items:
                - label: Elevation
                  source: elevation
```

## Widget Runtime

Niamoto validates each widget entry as a `WidgetConfig`, instantiates the plugin, validates `params` with that widget's `param_schema`, then calls `render(data, params)`.

The widget config stores:

- `plugin`
- `data_source`
- `title`
- `description`
- `params`
- `layout`

`title` and `description` live at the widget level, not inside `params`.

## Exporter Runtime

`ExporterService` validates `export.yml` as an `ExportConfig`, loads the exporter plugin, and calls:

```python
exporter.export(target_config=target, repository=self.db, group_filter=group_filter)
```

A custom exporter therefore needs to accept `target_config`, `repository`, and the optional `group_filter`.

## Deployers

Deployers sit after export generation. The CLI and GUI register deployer plugins such as `github`, `netlify`, `cloudflare`, `vercel`, `render`, and `ssh`. You configure them in `deploy.yml` or with `niamoto deploy`.

## Project Layout

```text
project/
  plugins/
    loaders/
    transformers/
    widgets/
    exporters/
    deployers/
  config/
    import.yml
    transform.yml
    export.yml
    deploy.yml
```
