# Niamoto Plugin System Overview

## Introduction

Niamoto's plugin system employs a "Configuration over Code" philosophy, allowing users to extend functionality through configuration rather than modifying core code. This architecture enables seamless integration of both built-in and custom functionalities while maintaining a clean separation between the core system and extensions.

## Key Components

### 1. Plugin Registry

The Plugin Registry is the central repository for all plugins in the system. It:

- Maintains a catalog of all available plugins organized by type
- Handles plugin registration and metadata storage
- Provides type-safe access to plugins
- Resolves plugin dependencies

```python
# Example: Getting a plugin from the registry
transformer = PluginRegistry.get_plugin("binned_distribution", PluginType.TRANSFORMER)
```

### 2. Plugin Loader

The Plugin Loader handles the dynamic discovery and loading of plugins:

- Loads core plugins bundled with Niamoto
- Discovers and loads project-specific plugins
- Manages plugin lifecycle (loading, unloading, reloading)
- Resolves import paths and handles module loading

```python
# Example: Loading project plugins
loader = PluginLoader()
loader.load_project_plugins("/path/to/project/plugins")
```

### 3. Plugin Types

Niamoto supports four main plugin types:

| Plugin Type | Purpose | Config File |
|-------------|---------|-------------|
| **Loader** | Data source loading | import.yml |
| **Transformer** | Data transformation and calculation | transform.yml |
| **Exporter** | Output generation | export.yml |
| **Widget** | Visualization components | export.yml |

### 4. Base Plugin Classes

Each plugin type inherits from a base abstract class that defines its interface and basic functionality:

- **Plugin**: Base class for all plugins
- **LoaderPlugin**: Interface for data loading plugins
- **TransformerPlugin**: Interface for data transformation plugins
- **ExporterPlugin**: Interface for data export plugins
- **WidgetPlugin**: Interface for visualization widgets

### 5. Configuration System

The configuration-driven approach uses YAML files to:

- Define which plugins to use
- Configure plugin parameters
- Establish plugin execution order
- Link plugins together in a workflow

## Plugin Lifecycle

1. **Discovery**: Plugin classes are discovered by scanning plugin directories
2. **Registration**: Plugins register themselves with the Plugin Registry
3. **Configuration**: Users configure plugins through YAML files
4. **Validation**: Plugin configurations are validated before execution
5. **Execution**: Plugins are executed according to the workflow
6. **Result Storage**: Plugin outputs are stored for further processing

## Configuration Files

Niamoto uses three main YAML configuration files:

### import.yml
Defines data sources and how they should be loaded.

```yaml
taxonomy:
  type: csv
  path: "imports/taxonomy.csv"
  source: "occurrence"
  ranks: "family,genus,species,infra"
```

### transform.yml
Defines data transformations and calculations.

```yaml
- group_by: taxon
  widgets_data:
    dbh_distribution:
      plugin: binned_distribution
      params:
        source: occurrences
        field: dbh
        bins: [10, 20, 30, 40, 50, 75, 100]
```

### export.yml
Defines widgets and export formats.

```yaml
- group_by: taxon
  widgets:
    dbh_distribution:
      type: bar_chart
      title: "DBH Distribution"
      source: dbh_distribution
      datasets:
        - label: "Occurrences"
          data_key: "counts"
```

## Extending Niamoto with Custom Plugins

Users can extend Niamoto by adding custom plugins to their project's `plugins` directory:

```
project/
  ├── plugins/
  │   ├── transformers/
  │   │   └── my_custom_transformer.py
  │   ├── loaders/
  │   │   └── my_custom_loader.py
  │   └── exporters/
  │       └── my_custom_exporter.py
  ├── config/
  │   ├── import.yml
  │   ├── transform.yml
  │   └── export.yml
  └── ...
```

These plugins will be automatically discovered and registered when Niamoto starts.
