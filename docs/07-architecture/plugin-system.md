# Plugin System

Niamoto uses plugins for the parts of the pipeline that change from one project
to another: loading data, computing grouped outputs, rendering widgets,
exporting files, and publishing artifacts.

## Plugin families

The runtime defines five plugin types in `src/niamoto/core/plugins/base.py`:

- loaders
- transformers
- widgets
- exporters
- deployers

Each family has its own abstract base class and its own execution contract.

## Registration

Built-in and custom plugins register through `PluginRegistry` in
`src/niamoto/core/plugins/registry.py`.

The registry stores plugins by type and name. Services resolve the plugin they
need from that registry instead of importing implementations directly.

## Loading and override order

`PluginLoader.load_plugins_with_cascade()` loads plugins from three scopes:

1. project-local plugins in `<project>/plugins`
2. user plugins in `~/.niamoto/plugins`
3. built-in plugins in `src/niamoto/core/plugins`

Higher-priority scopes win. If a project plugin and a built-in plugin share the
same name, Niamoto keeps the project plugin and skips the lower-priority one.

The loader uses `ResourcePaths` so the CLI and the desktop runtime apply the
same lookup rules.

## Config validation

Plugins validate their own parameters with Pydantic models. In practice this
means:

- import services validate loader config before loading data
- transform services validate transformer params before computing outputs
- export services validate widget and exporter config before rendering or writing files
- deploy services validate platform-specific deployment settings before publishing

That contract keeps YAML errors close to the plugin that owns them.

## Where plugins run

- CLI commands call plugins through core services
- FastAPI routes in the GUI call the same services
- the preview engine uses transformer and widget plugins to render HTML previews
- deployment commands and routes call deployer plugins

The plugin layer stays shared across entry points. The CLI, desktop app, and
web UI change how users trigger work, not which plugin contracts they use.

## Related docs

- [../04-plugin-development/README.md](../04-plugin-development/README.md): authoring guides
- [../06-reference/plugin-api.md](../06-reference/plugin-api.md): source-level reference
- [gui-preview-system.md](gui-preview-system.md): transformer and widget use in preview rendering
- [adr/0002-retire-legacy-importers.md](adr/0002-retire-legacy-importers.md): import system transition
