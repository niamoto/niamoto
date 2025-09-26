# Configuration

Complete guide to configuring Niamoto for your needs.

## 📚 Documents in this Section

- **[Configuration Guide](configuration-guide.md)** - Comprehensive configuration reference
- **[YAML Strategies](yaml-strategies.md)** - Simplifying YAML configurations
- **[Templates Hierarchy](templates-hierarchy.md)** - Hierarchical template system
- **[Auto-Config Roadmap](auto-config-roadmap.md)** - Automatic configuration generation

## 🔧 Configuration Files

Niamoto uses three main configuration files:

### import.yml
```yaml
sources:
  - name: occurrences
    type: csv
    path: data/occurrences.csv
    mapping:
      taxon: species_name
      location: site_id
```

### transform.yml
```yaml
pipeline:
  - plugin: enrich_taxonomy
    params:
      source: gbif
  - plugin: calculate_diversity
    params:
      index: shannon
```

### export.yml
```yaml
site:
  title: "My Biodiversity Site"
  output: dist/
  widgets:
    - type: map
    - type: charts
```

## 🎯 Configuration Strategies

1. **Start Simple** - Use minimal configs
2. **Use Templates** - Leverage built-in templates
3. **Hierarchical Override** - Layer configurations
4. **Auto-Generation** - Let ML suggest configs

## 🚀 Quick Tips

- Use environment variables for paths
- Validate configs with `niamoto validate`
- Keep sensitive data in `.env` files
- Version control your configurations

## 🔗 Related Documentation

- [Data Pipeline](../02-data-pipeline/) - Using configurations
- [ML Detection](../03-ml-detection/) - Auto-configuration
- [Plugin Development](../04-plugin-development/) - Plugin configs

---
*For examples, see [Tutorials](../07-tutorials/)*
