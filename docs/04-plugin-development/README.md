# Plugin Development

Create custom plugins to extend Niamoto's functionality.

## 📚 Documents in this Section

- **[Architecture](architecture.md)** - Plugin system architecture
- **[Creating Transformers](creating-transformers.md)** - Build data transformers
- **[Building Widgets](building-widgets.md)** - Create visualization widgets
- **[Custom Exporters](custom-exporters.md)** - Develop export plugins
- **[Database Aggregator](database-aggregator.md)** - Database plugin example

## 🔌 Plugin Types

Niamoto supports four types of plugins:

1. **Loaders**: Import data from various sources
2. **Transformers**: Process and transform data
3. **Exporters**: Generate outputs
4. **Widgets**: Create interactive visualizations

## 🎯 Getting Started

```python
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register

@register("my_plugin", PluginType.TRANSFORMER)
class MyPlugin(TransformerPlugin):
    def transform(self, data, config):
        # Your transformation logic
        return processed_data
```

## 🛠️ Development Workflow

1. Choose plugin type: [Architecture](architecture.md)
2. Implement plugin class: See type-specific guides
3. Register with decorator: `@register()`
4. Configure in YAML: Add to pipeline config
5. Test thoroughly: Unit and integration tests

## 📖 Examples

- Simple transformer: [Creating Transformers](creating-transformers.md)
- Chart widget: [Building Widgets](building-widgets.md)
- CSV exporter: [Custom Exporters](custom-exporters.md)
- Complex example: [Database Aggregator](database-aggregator.md)

## 🔗 Related Documentation

- [Data Pipeline](../02-data-pipeline/README.md) - Using plugins in pipelines
- [API Reference](../05-api-reference/plugin-api.md) - Plugin API documentation
- [Configuration](../08-configuration/README.md) - Plugin configuration

---
*For real examples, see [Tutorials](../07-tutorials/README.md)*
