# Niamoto Plugin Types Reference

Niamoto's plugin system is organized into four main types, each serving a specific purpose in the data pipeline. This reference guide explains each plugin type, its configuration schema, and provides examples of both built-in and custom implementations.

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
| `top_ranking` | Find top N items | `source`, `field`, `count` |
| `field_aggregator` | Aggregate fields | `fields` (array of mappings) |
| `geospatial_extractor` | Extract spatial data | `source`, `field`, `format` |
| `transform_chain` | Chain transformations | `steps` (array of plugins) |

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
- group_by: taxon
  widgets:
    dbh_distribution:
      type: bar_chart
      title: "DBH Distribution"
      source: dbh_distribution
      datasets:
        - label: "Occurrences"
          data_key: "counts"
          backgroundColor: "#4CAF50"
      labels_key: "bins"
```

### Built-in Exporter Plugins

| Plugin Name | Purpose | Parameters |
|-------------|---------|------------|
| `html` | Generate HTML exports | `template`, `output_dir` |
| `api_generator` | Generate API data | `output_dir`, `format` |
| `page_generator` | Generate static pages | `template`, `output_dir` |

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
- group_by: taxon
  widgets:
    distribution_map:
      type: map_panel
      title: "Geographic Distribution"
      source: distribution_map
      layers:
        - id: "occurrences"
          source: coordinates
          style:
            color: "#1fb99d"
            fillOpacity: 0.5
```

### Built-in Widget Plugins

| Plugin Name | Purpose | Parameters |
|-------------|---------|------------|
| `bar_chart` | Create bar charts | `datasets`, `labels_key`, `options` |
| `line_chart` | Create line charts | `datasets`, `labels_key`, `options` |
| `doughnut_chart` | Create doughnut charts | `datasets`, `labels`, `options` |
| `map_panel` | Create interactive maps | `layers`, `center`, `zoom` |
| `info_panel` | Display information panels | `fields`, `layout` |
| `gauge` | Display gauge charts | `value_key`, `min`, `max`, `sectors` |

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
