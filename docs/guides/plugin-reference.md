# Plugin System Reference

Niamoto's plugin system is organized into four main types, each serving a specific purpose in the data pipeline. This comprehensive reference guide explains each plugin type, configuration schemas, and provides examples of both built-in and custom implementations.

## Overview

The Niamoto plugin architecture enables extensible data processing through four plugin types:

1. **Loader Plugins**: Import and load data from various sources
2. **Transformer Plugins**: Process and analyze data
3. **Exporter Plugins**: Generate outputs and exports
4. **Widget Plugins**: Create visualizations and UI components

Each plugin type has specific configuration patterns and capabilities designed for different stages of the data pipeline.

## 1. Loader Plugins

Loader plugins are responsible for retrieving and loading data from various sources into Niamoto.

### Purpose

- Load data from CSV files, databases, GIS formats, etc.
- Convert raw data into standardized formats
- Handle data source connections and queries
- Manage data validation and cleaning during import

### Configuration Schema (import.yml)

```yaml
# Example: Loading taxonomy data
taxonomy:
  type: csv
  path: "imports/taxonomy.csv"
  source: "file"
  identifier: "id_taxon"
  ranks: "family,genus,species,infra"

# Example: Loading vector data
plots:
  type: vector
  format: geopackage
  path: "imports/plots.gpkg"
  identifier: "id_locality"
  location_field: "geometry"
```

### Built-in Loader Plugins

| Plugin Name | Purpose | Parameters |
|-------------|---------|------------|
| `direct_reference` | Simple direct reference loading | `key` |
| `join_table` | Load data with joins | `left_key`, `right_key` |
| `nested_set` | Load hierarchical data | `key`, `fields.left`, `fields.right` |
| `spatial` | Load spatial data | `geometry_field`, `crs` |

### Example: Custom Loader Plugin

```python
from niamoto.core.plugins.base import (
    LoaderPlugin,
    PluginType,
    register
)

@register("remote_api_loader", PluginType.LOADER)
class RemoteAPILoader(LoaderPlugin):
    """Load data from a remote API"""

    def validate_config(self, config):
        # Validate required config parameters
        if "api_url" not in config:
            raise ValueError("API URL is required")
        return config

    def load_data(self, group_id, config):
        """Load data from remote API"""
        import requests
        import pandas as pd

        # Get config parameters
        api_url = config["api_url"]
        endpoint = config.get("endpoint", "data")

        # Call API with group_id as parameter
        response = requests.get(f"{api_url}/{endpoint}?id={group_id}")

        # Convert to DataFrame
        data = response.json()
        return pd.DataFrame(data)
```

## 2. Transformer Plugins

Transformer plugins perform calculations, transformations, and analyses on loaded data.

### Purpose

- Calculate statistics and metrics from data
- Transform data for visualization
- Perform specialized domain-specific analyses
- Generate aggregations and summaries

### Configuration Schema (transform.yml)

```yaml
- group_by: taxon
  widgets_data:
    dbh_distribution:
      plugin: binned_distribution
      params:
        source: occurrences
        field: dbh
        bins: [10, 20, 30, 40, 50, 75, 100]

    species_counts:
      plugin: statistical_summary
      params:
        source: occurrences
        field: species_id
        stats: ["count", "unique"]
```

### Built-in Transformer Plugins

| Plugin Name | Purpose | Parameters |
|-------------|---------|------------|
| `binned_distribution` | Create histograms | `source`, `field`, `bins`, `labels` |
| `categorical_distribution` | Analyze categories | `source`, `field`, `categories` |
| `statistical_summary` | Calculate statistics | `source`, `field`, `stats` |
| `top_ranking` | Find top N items | `source`, `field`, `count`, `mode` |
| `field_aggregator` | Aggregate fields | `fields` (array of mappings) |
| `geospatial_extractor` | Extract spatial data | `source`, `field`, `format` |
| `transform_chain` | Chain transformations | `steps` (array of plugins) |

### Top Ranking Plugin (Detailed)

The `top_ranking` plugin is a flexible transformer that calculates top N items using three different modes:

#### Common Parameters

```yaml
plugin: top_ranking
params:
  source: string        # Source data table/collection
  field: string         # Field to analyze
  count: integer        # Number of top items to return (default: 10)
  mode: string          # One of: 'direct', 'hierarchical', 'join'
  aggregate_function: string  # 'count', 'sum', 'avg' (default: 'count')
```

#### Mode 1: Direct Counting
The simplest mode - counts occurrences of values directly.

```yaml
top_plots:
  plugin: top_ranking
  params:
    source: plots
    field: locality_name
    count: 10
    mode: direct
```

#### Mode 2: Hierarchical Navigation
Navigates a hierarchy to find items at a specific rank.

```yaml
top_families:
  plugin: top_ranking
  params:
    source: occurrences
    field: taxon_ref_id
    count: 10
    mode: hierarchical
    hierarchy_table: taxon_ref
    hierarchy_columns:
      id: id
      name: full_name
      rank: rank_name
      parent_id: parent_id
    target_ranks: ["family"]
```

#### Mode 3: Join-Based Counting
Performs joins between tables to count related items.

```yaml
top_species_by_plot:
  plugin: top_ranking
  params:
    source: plots
    field: plot_id
    count: 10
    mode: join
    join_table: occurrences
    join_columns:
      source_id: plot_ref_id
      hierarchy_id: taxon_ref_id
    hierarchy_table: taxon_ref
    hierarchy_columns:
      id: id
      name: full_name
      rank: rank_name
      left: lft
      right: rght
    target_ranks: ["species", "subspecies"]
```

#### Advanced Features

**Custom Aggregation Functions**:
```yaml
params:
  aggregate_function: sum
  aggregate_field: stem_diameter
```

**Nested Set Model Support**:
```yaml
hierarchy_columns:
  left: lft
  right: rght
```

**Output Format**:
```json
{
  "tops": ["Item1", "Item2", "Item3"],
  "counts": [100, 85, 72]
}
```

### Example: Custom Transformer Plugin

```python
from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig
)
from pydantic import Field
import pandas as pd
import numpy as np

class DiversityIndexConfig(PluginConfig):
    """Configuration for diversity index calculation"""
    plugin: str = "diversity_index"
    params: dict = Field(default_factory=lambda: {
        "source": "occurrences",
        "species_field": "species_id",
        "index_type": "shannon"
    })

@register("diversity_index", PluginType.TRANSFORMER)
class DiversityIndexCalculator(TransformerPlugin):
    """Calculate biodiversity indices"""

    config_model = DiversityIndexConfig

    def transform(self, data, config):
        """Calculate diversity index"""
        validated_config = self.validate_config(config)
        params = validated_config.params

        # Get parameters
        species_field = params["species_field"]
        index_type = params.get("index_type", "shannon")

        # Count species occurrences
        species_counts = data[species_field].value_counts()
        total = species_counts.sum()

        # Calculate proportions
        proportions = species_counts / total

        # Calculate requested index
        if index_type == "shannon":
            # Shannon diversity: -sum(p_i * ln(p_i))
            shannon = -np.sum(proportions * np.log(proportions))
            return {
                "value": float(shannon),
                "max_value": np.log(len(species_counts)),
                "species_count": len(species_counts),
                "formula": "H' = -sum(p_i * ln(p_i))"
            }
        elif index_type == "simpson":
            # Simpson diversity: 1 - sum(p_i^2)
            simpson = 1 - np.sum(proportions ** 2)
            return {
                "value": float(simpson),
                "max_value": 1.0,
                "species_count": len(species_counts),
                "formula": "D = 1 - sum(p_i^2)"
            }
        else:
            raise ValueError(f"Unsupported index type: {index_type}")
```

## 3. Exporter Plugins

Exporter plugins handle the output generation from transformed data.

### Purpose

- Generate static websites, reports, and data files
- Format data for external consumption
- Create visualizations and interactive displays
- Produce downloadable exports

### Configuration Schema (export.yml)

```yaml
exports:
  - name: website_export
    exporter: html_page_exporter
    params:
      output_dir: "exports/web"
      base_url: "/"

      static_pages:
        - name: home
          output_file: "index.html"
          template: "home.html"

      entity_pages:
        - group: taxon
          template: "taxon_detail.html"
          output_pattern: "taxon/{{ id }}.html"

  - name: api_export
    exporter: api_generator
    params:
      output_dir: "exports/api"
      format: "json"
```

### Built-in Exporter Plugins

| Plugin Name | Purpose | Parameters |
|-------------|---------|------------|
| `html_page_exporter` | Generate HTML websites | `output_dir`, `base_url`, `static_pages`, `entity_pages` |
| `api_generator` | Generate API data | `output_dir`, `format` |
| `index_generator` | Generate search indexes | `output_dir`, `groups` |

### Example: Custom Exporter Plugin

```python
from niamoto.core.plugins.base import (
    ExporterPlugin,
    PluginType,
    register
)
import json
import os

@register("excel_exporter", PluginType.EXPORTER)
class ExcelExporter(ExporterPlugin):
    """Export data to Excel format"""

    def validate_config(self, config):
        # Validate required config parameters
        if "output_path" not in config:
            raise ValueError("output_path is required")
        return config

    def export(self, data, config):
        """Export data to Excel format"""
        import pandas as pd

        # Get config parameters
        output_path = config["output_path"]
        sheet_name = config.get("sheet_name", "Data")

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Convert data to DataFrame if needed
        if isinstance(data, dict):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])

        # Export to Excel
        df.to_excel(output_path, sheet_name=sheet_name, index=False)

        return {"status": "success", "path": output_path}
```

## 4. Widget Plugins

Widget plugins create visualizations and UI components for displaying data.

### Purpose

- Create interactive visualizations
- Build UI components for data display
- Render charts, maps, and other graphics
- Generate embeddable widgets

### Configuration Schema (export.yml)

```yaml
widgets:
  - plugin: interactive_map
    data_source: distribution_data
    params:
      title: "Geographic Distribution"
      map_type: "scatter_map"
      latitude_field: "lat"
      longitude_field: "lon"
      color_field: "species_count"
      hover_name: "location_name"
      zoom: 9.0
      center_lat: -21.5
      center_lon: 165.5

  - plugin: bar_plot
    data_source: species_counts
    params:
      title: "Species Distribution"
      x_axis: "species"
      y_axis: "count"
      auto_color: true
```

### Built-in Widget Plugins

| Plugin Name | Purpose | Key Parameters |
|-------------|---------|--------------|
| `info_grid` | Display grid of metrics and info | `items`, `grid_columns`, `title` |
| `interactive_map` | Create interactive Plotly maps | `map_type`, `latitude_field`, `longitude_field`, `color_field` |
| `bar_plot` | Create bar charts | `x_axis`, `y_axis`, `color_field`, `barmode` |
| `donut_chart` | Create donut/pie charts | `labels_field`, `values_field`, `hole_size` |
| `radial_gauge` | Display gauge visualizations | `value_field`, `min_value`, `max_value`, `unit` |
| `line_plot` | Create line charts | `x_axis`, `y_axis`, `color_field`, `line_shape` |
| `stacked_area_plot` | Create stacked area charts | `x_field`, `y_fields`, `colors` |
| `sunburst_chart` | Create hierarchical sunburst charts | `category_labels`, `leaf_labels`, `leaf_colors` |
| `hierarchical_nav_widget` | Interactive tree navigation | `referential_data`, `id_field`, `name_field`, `base_url` |
| `diverging_bar_plot` | Bar plots with positive/negative values | `x_axis`, `y_axis`, `zero_line` |
| `scatter_plot` | Create scatter plots | `x_axis`, `y_axis`, `color_field`, `size_field` |
| `summary_stats` | Display statistical summaries | `fields`, `statistics` |
| `table_view` | Display tabular data | `columns`, `pagination`, `sorting` |

For detailed widget documentation, see the [Widget Reference Guide](widget-reference.md).

### Example: Custom Widget Plugin

```python
from niamoto.core.plugins.base import (
    WidgetPlugin,
    PluginType,
    register
)
import json

@register("heatmap_widget", PluginType.WIDGET)
class HeatmapWidget(WidgetPlugin):
    """Create heatmap visualizations"""

    def get_dependencies(self):
        """Return required JS/CSS dependencies"""
        return [
            "https://cdn.jsdelivr.net/npm/d3@7",
            "https://cdn.jsdelivr.net/npm/d3-heatmap@1"
        ]

    def validate_config(self, config):
        # Validate required config parameters
        if "data_key" not in config:
            raise ValueError("data_key is required")
        return config

    def render(self, data, config):
        """Render heatmap visualization"""
        container_id = f"heatmap-{hash(json.dumps(config))}"
        data_key = config["data_key"]
        colorscheme = config.get("colorscheme", "YlOrRd")

        # Get data
        heatmap_data = data.get(data_key, {})
        if not heatmap_data:
            return "<div>No data available</div>"

        # Convert data to JSON for JS
        json_data = json.dumps(heatmap_data)

        # Create HTML/JS for the heatmap
        html = f"""
        <div id="{container_id}" class="heatmap-container" style="width:100%;height:300px;"></div>
        <script>
            (function() {{
                const data = {json_data};
                const colorScale = d3.scaleSequential(d3.interpolate{colorscheme})
                    .domain([0, d3.max(data.values)]);

                // D3 code to render heatmap
                const margin = {{top: 20, right: 20, bottom: 30, left: 40}};
                const width = document.getElementById('{container_id}').clientWidth - margin.left - margin.right;
                const height = document.getElementById('{container_id}').clientHeight - margin.top - margin.bottom;

                const svg = d3.select('#{container_id}')
                    .append('svg')
                        .attr('width', width + margin.left + margin.right)
                        .attr('height', height + margin.top + margin.bottom)
                    .append('g')
                        .attr('transform', `translate(${{margin.left}},${{margin.top}})`);

                // Render heatmap cells
                // ... (D3 code to render cells)
            }})();
        </script>
        """

        return html
```

## Plugin Development Best Practices

### 1. Configuration Validation

Always validate configuration parameters:

```python
def validate_config(self, config):
    required_params = ["source", "field"]
    for param in required_params:
        if param not in config:
            raise ValueError(f"Missing required parameter: {param}")
    return config
```

### 2. Error Handling

Implement robust error handling:

```python
def transform(self, data, config):
    try:
        # Plugin logic here
        result = self.process_data(data, config)
        return result
    except Exception as e:
        logger.error(f"Plugin {self.__class__.__name__} failed: {str(e)}")
        raise
```

### 3. Data Validation

Validate input data:

```python
def transform(self, data, config):
    if data is None or data.empty:
        return {"error": "No data provided"}

    required_fields = config.get("required_fields", [])
    missing_fields = [f for f in required_fields if f not in data.columns]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")
```

### 4. Performance Optimization

For large datasets, implement chunking:

```python
def transform(self, data, config):
    chunk_size = config.get("chunk_size", 1000)
    results = []

    for chunk in pd.read_csv(data_source, chunksize=chunk_size):
        chunk_result = self.process_chunk(chunk, config)
        results.append(chunk_result)

    return self.combine_results(results)
```

### 5. Documentation

Document plugin parameters and usage:

```python
class MyPlugin(TransformerPlugin):
    """
    Calculate species diversity metrics.

    Parameters:
        source (str): Source data table
        species_field (str): Column containing species names
        index_type (str): Type of diversity index ('shannon', 'simpson')

    Returns:
        dict: Dictionary containing diversity metrics

    Example:
        ```yaml
        diversity:
          plugin: diversity_calculator
          params:
            source: occurrences
            species_field: species_name
            index_type: shannon
        ```
    """
```

## Troubleshooting

### Common Issues

#### Plugin Not Found
```bash
# Check plugin registration
niamoto plugins --type transformer
```

#### Configuration Errors
```yaml
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/transform.yml'))"
```

#### Data Issues
```bash
# Check data availability
niamoto stats --detailed
```

### Performance Issues

#### Top Ranking Plugin Performance

- **Direct mode** is fastest for simple counting
- **Hierarchical mode** performance depends on hierarchy depth
- **Join mode** can be slow for large datasets; ensure proper indexes exist

#### General Performance Tips

- Add database indexes on frequently used join columns
- Use chunked processing for large datasets
- Implement caching for expensive calculations
- Use nested set columns (left/right) for hierarchical data

### Debugging

Enable verbose logging:

```bash
niamoto transform --verbose
export NIAMOTO_LOG_LEVEL=DEBUG
```

Check plugin-specific logs:

```bash
tail -f logs/niamoto.log | grep "plugin"
```

## Plugin Registry

### Registration

Plugins are automatically registered using decorators:

```python
@register("my_plugin", PluginType.TRANSFORMER)
class MyPlugin(TransformerPlugin):
    pass
```

### Discovery

Niamoto discovers plugins in:

1. Built-in plugin directories
2. `plugins/` directory in your project
3. Installed Python packages with `niamoto_` prefix

### Listing Plugins

```bash
# List all plugins
niamoto plugins

# List by type
niamoto plugins --type transformer
niamoto plugins --type widget

# Show plugin details
niamoto plugins --plugin top_ranking --details
```

## Related Documentation

- [Widget Reference Guide](widget-reference.md) - Detailed widget documentation
- [Custom Plugin Development](custom-plugin.md) - Creating custom plugins
- [Transform Chain Guide](transform-chain-guide.md) - Chaining transformations
- [Configuration Guide](configuration.md) - YAML configuration reference

For troubleshooting plugin issues, see the [Common Issues Guide](../troubleshooting/common-issues.md).
