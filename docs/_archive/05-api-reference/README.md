# API Reference

Complete technical documentation for Niamoto's APIs and interfaces.

## 📚 Documents in this Section

- **[Core API](core-api.md)** - Main Niamoto API (coming soon)
- **[Plugin API](plugin-api.md)** - Plugin development interfaces
- **[Database Schema](database-schema.md)** - Database structure and models
- **[CLI Commands](cli-commands.md)** - Command-line interface reference
- **[External APIs](external-apis.md)** - Third-party API integrations

## 🔧 Quick Reference

### CLI Commands
```bash
niamoto init          # Initialize project
niamoto import        # Run import pipeline
niamoto transform     # Execute transformations
niamoto export        # Generate exports
niamoto gui           # Launch web interface
```

### Plugin Registration
```python
@register("plugin_name", PluginType.TRANSFORMER)
class MyPlugin(TransformerPlugin):
    pass
```

### Database Models
- `TaxonOccurrence` - Species occurrences
- `TaxonRef` - Taxonomic references
- `Location` - Geographic data
- `Shape` - Spatial geometries

## 📖 API Categories

1. **Core Services** - Data management and processing
2. **Plugin System** - Extension interfaces
3. **Database Layer** - SQLAlchemy models and queries
4. **CLI Interface** - Command-line tools
5. **REST API** - HTTP endpoints (GUI backend)

## 🔗 Related Documentation

- [Plugin Development](../04-plugin-development/README.md) - Create plugins
- [Configuration](../08-configuration/README.md) - API configuration
- [GUI Documentation](../06-gui/README.md) - Web interface APIs

---
*For usage examples, see [Tutorials](../07-tutorials/README.md)*
