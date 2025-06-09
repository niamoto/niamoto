# Widget Reference Guide

This comprehensive guide covers all available Niamoto widgets for creating interactive visualizations and data displays in your static website exports.

## Overview

Niamoto widgets are modular visualization components that transform your ecological data into interactive charts, maps, and information displays. Each widget is designed to work seamlessly with the data pipeline and can be configured through YAML files without writing code.

## Widget Architecture

### Base Structure

All widgets inherit from the `WidgetPlugin` base class and follow these patterns:

- **Registration**: Plugins are registered with unique names using decorators
- **Configuration**: Parameters are validated using Pydantic schemas
- **Data Processing**: Flexible input handling with automatic data transformation
- **HTML Output**: Consistent container structure with title, description, and content
- **Dependencies**: Automatic inclusion of required CSS/JS assets

### Common Parameters

Most widgets support these base parameters:

```yaml
widgets:
  - plugin: widget_name
    data_source: source_key  # References transform.yml output
    params:
      title: "Widget Title"           # Optional display title
      description: "Widget purpose"   # Optional description
      width: 800                      # Optional width in pixels
      height: 600                     # Optional height in pixels
      class_name: "custom-class"      # Optional CSS class
```

### Data Input Formats

Widgets accept multiple data formats:

- **DataFrames**: Standard pandas DataFrame structure
- **Dictionaries**: Nested dicts with dot notation access (e.g., `"stats.elevation"`)
- **Lists**: List of records for tabular data
- **GeoJSON/TopoJSON**: Geospatial data for maps
- **Scalar Values**: Single numbers or strings

## Visualization Widgets

### Bar Plot Widget

**Plugin Name**: `bar_plot`

Create customizable bar charts with advanced styling and automatic color generation.

**Key Parameters**:
```yaml
- plugin: bar_plot
  params:
    x_axis: "field_name"              # Required: X-axis field
    y_axis: "value_field"             # Required: Y-axis field
    color_field: "category"           # Optional: Color grouping field
    barmode: "group"                  # group, stack, relative
    orientation: "v"                  # v (vertical), h (horizontal)
    auto_color: true                  # Automatic harmonious colors
    gradient_color: false             # Gradient color scheme
    sort_order: "asc"                 # asc, desc, none
    filter_zero_values: true          # Remove zero values
    show_legend: true                 # Display legend
```

**Data Format**:
```python
# DataFrame example
{
  "species": ["Araucaria columnaris", "Agathis ovata", "Podocarpus"],
  "count": [1247, 856, 543],
  "province": ["North", "South", "North"]
}
```

**Use Cases**:
- Species occurrence counts by location
- Plot statistics by forest type
- Taxonomic rank distributions

### Interactive Map Widget

**Plugin Name**: `interactive_map`

Create interactive maps with point data, choropleth layers, and multi-layer support.

**Key Parameters**:
```yaml
- plugin: interactive_map
  params:
    map_type: "scatter_map"           # scatter_map, choropleth_map
    latitude_field: "latitude"        # Required for scatter maps
    longitude_field: "longitude"      # Required for scatter maps
    geojson_source: "shapes.geojson"  # Required for choropleth
    color_field: "value"              # Coloring field
    size_field: "count"               # Point size field
    hover_data: ["species", "date"]   # Hover information
    map_style: "open-street-map"      # Base map style
    auto_zoom: true                   # Automatic zoom to data
    use_topojson: true                # Use TopoJSON optimization
    layers:                           # Multi-layer configuration
      - name: "boundaries"
        geojson_source: "provinces"
        fill_color: "lightblue"
      - name: "forest_cover"
        geojson_source: "forests"
        fill_color: "green"
```

**Data Formats**:

*Scatter map*:
```python
{
  "latitude": [-22.2764, -21.1234],
  "longitude": [166.4580, 165.2345],
  "species": ["Araucaria", "Agathis"],
  "count": [15, 8]
}
```

*Choropleth map*:
```geojson
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"name": "Province Nord", "forest_area": 12500},
      "geometry": {"type": "Polygon", "coordinates": [...]}
    }
  ]
}
```

**Dependencies**:
- Plotly library
- TopoJSON library (when `use_topojson: true`)

### Line Plot Widget

**Plugin Name**: `line_plot`

Display time series and continuous data with multiple line support.

**Key Parameters**:
```yaml
- plugin: line_plot
  params:
    x_axis: "date"                    # X-axis field (auto-detects dates)
    y_axis: "value"                   # Y-axis field (can be list)
    color_field: "species"            # Line grouping field
    line_group: "plot_id"             # Alternative grouping
    markers: true                     # Show/hide markers
    line_shape: "linear"              # linear, spline, hv, vh
    log_y: false                      # Logarithmic Y-axis
```

**Data Format**:
```python
{
  "date": ["2020-01-01", "2020-02-01", "2020-03-01"],
  "dbh": [15.2, 15.8, 16.1],
  "height": [12.1, 12.5, 12.8],
  "species": ["Araucaria", "Araucaria", "Araucaria"]
}
```

### Scatter Plot Widget

**Plugin Name**: `scatter_plot`

Multi-dimensional scatter plots with trend analysis and faceting.

**Key Parameters**:
```yaml
- plugin: scatter_plot
  params:
    x_axis: "dbh"                     # Required: X-axis field
    y_axis: "height"                  # Required: Y-axis field
    color_field: "species"            # Point coloring
    size_field: "age"                 # Point sizing
    symbol_field: "status"            # Point symbols
    trendline: "ols"                  # ols, lowess, none
    facet_col: "province"             # Column faceting
    facet_row: "forest_type"          # Row faceting
    log_x: false                      # Logarithmic X-axis
    log_y: false                      # Logarithmic Y-axis
```

**Use Cases**:
- Allometric relationships (DBH vs Height)
- Species distribution patterns
- Multi-variate ecological analysis

### Donut Chart Widget

**Plugin Name**: `donut_chart`

Pie and donut charts with multi-subplot support.

**Key Parameters**:
```yaml
- plugin: donut_chart
  params:
    labels_field: "species"           # Label field for DataFrame
    values_field: "count"             # Value field for DataFrame
    hole_size: 0.3                    # 0-1, donut hole size (0=pie)
    text_info: "label+percent"        # label, percent, value combinations
    subplots:                         # Multi-donut configuration
      - title: "Province Nord"
        data_key: "north_data"
      - title: "Province Sud"
        data_key: "south_data"
```

**Data Format**:
```python
# Simple format
{
  "species": ["Araucaria", "Agathis", "Podocarpus"],
  "count": [45, 30, 25]
}

# Subplot format
{
  "north_data": {"Araucaria": 60, "Agathis": 40},
  "south_data": {"Podocarpus": 70, "Calophyllum": 30}
}
```

### Stacked Area Plot Widget

**Plugin Name**: `stacked_area_plot`

Multi-series area charts for showing composition over time or space.

**Key Parameters**:
```yaml
- plugin: stacked_area_plot
  params:
    x_field: "elevation"              # X-axis field
    y_fields: ["species1", "species2"] # Multiple Y-series
    colors: ["#1f77b4", "#ff7f0e"]   # Color list for series
    fill_type: "tonexty"              # tonexty, tozeroy
```

**Use Cases**:
- Species composition by elevation
- Forest cover change over time
- Habitat distribution patterns

### Sunburst Chart Widget

**Plugin Name**: `sunburst_chart`

Hierarchical visualization for nested categories.

**Key Parameters**:
```yaml
- plugin: sunburst_chart
  params:
    category_labels:                  # Category display mapping
      "family": "Family"
      "genus": "Genus"
    leaf_labels:                      # Leaf display mapping
      "species1": "Species 1"
    leaf_colors:                      # Color configuration
      "endemic": "#2E7D32"
      "native": "#66BB6A"
    branchvalues: "total"             # total, remainder
    text_info: "label+percent"        # Display format
```

**Data Format**:
```python
{
  "Araucariaceae": {
    "Araucaria columnaris": 45,
    "Araucaria biramulata": 23
  },
  "Podocarpaceae": {
    "Podocarpus decumbens": 67
  }
}
```

### Concentric Rings Widget

**Plugin Name**: `concentric_rings`

Specialized widget for forest cover visualization with concentric pie charts.

**Key Parameters**:
```yaml
- plugin: concentric_rings
  params:
    ring_order: ["um", "num", "emprise"]  # Inside to outside
    ring_labels:                          # Ring display names
      "um": "Ultramafic"
      "num": "Non-ultramafic"
      "emprise": "Total emprise"
    category_colors:                      # Category colors
      "forest": "#2E7D32"
      "non_forest": "#FFC107"
    border_width: 2                       # Ring spacing
```

**Data Format**:
```python
{
  "um": {"forest": 1250, "non_forest": 750},
  "num": {"forest": 2340, "non_forest": 1560},
  "emprise": {"forest": 3590, "non_forest": 2310}
}
```

### Diverging Bar Plot Widget

**Plugin Name**: `diverging_bar_plot`

Horizontal/vertical bars with positive/negative value distinction.

**Key Parameters**:
```yaml
- plugin: diverging_bar_plot
  params:
    x_axis: "change"                  # Value field
    y_axis: "species"                 # Category field
    color_positive: "#2E7D32"         # Color for positive values
    color_negative: "#D32F2F"         # Color for negative values
    threshold: 0.0                    # Zero line position
    orientation: "h"                  # h (horizontal), v (vertical)
```

**Use Cases**:
- Population change analysis
- Species gain/loss comparisons
- Environmental impact assessment

### Radial Gauge Widget

**Plugin Name**: `radial_gauge`

Circular gauges for displaying single key metrics.

**Key Parameters**:
```yaml
- plugin: radial_gauge
  params:
    value_field: "diversity_index"    # Required: Value field
    min_value: 0                      # Gauge minimum
    max_value: 100                    # Gauge maximum
    unit: "%"                         # Display unit
    style_mode: "contextual"          # classic, minimal, gradient, contextual
    steps:                            # Color steps (classic mode)
      - range: [0, 30]
        color: "red"
      - range: [30, 70]
        color: "yellow"
      - range: [70, 100]
        color: "green"
    threshold: 50                     # Threshold line
```

**Style Modes**:
- **classic**: Multi-color steps with configurable ranges
- **minimal**: Clean single-color design
- **gradient**: Smooth color transition
- **contextual**: Automatic coloring based on value position

## Information Display Widgets

### Info Grid Widget

**Plugin Name**: `info_grid`

Display key metrics and information in a responsive grid layout.

**Key Parameters**:
```yaml
- plugin: info_grid
  params:
    grid_columns: 3                   # Responsive grid columns
    items:
      - label: "Total Species"
        source: "stats.species_count" # Dot notation data access
        unit: "species"
        icon: "fa-leaf"
        description: "Number of recorded species"
      - label: "Forest Area"
        source: "area.forest"
        unit: "km²"
        format: "number"              # Formatting type
      - label: "Conservation Status"
        source: "status.category"
        format: "map"                 # Use mapping
        mapping:
          "LC": "Least Concern"
          "NT": "Near Threatened"
          "VU": "Vulnerable"
```

**InfoItem Properties**:
- `label`: Display name
- `source`: Data field path (supports dot notation)
- `value`: Direct value (alternative to source)
- `unit`: Unit suffix
- `description`: Tooltip text
- `icon`: Font Awesome icon class
- `format`: number, map, or none
- `mapping`: Value transformation map

### Table View Widget

**Plugin Name**: `table_view`

Advanced tabular data display with sorting and filtering.

**Key Parameters**:
```yaml
- plugin: table_view
  params:
    columns: ["species", "count", "status"]  # Column selection
    sort_by: ["count"]                       # Initial sort column(s)
    ascending: false                         # Sort direction
    max_rows: 100                           # Row limit
    table_classes: "table table-striped"    # CSS classes
    index: false                            # Show DataFrame index
    escape: false                           # HTML escaping
    border: 1                               # Table border
```

### Raw Data Widget

**Plugin Name**: `raw_data_widget`

Simple tabular data display for debugging and data exploration.

**Key Parameters**:
```yaml
- plugin: raw_data_widget
  params:
    max_rows: 50                      # Maximum rows to display
    columns: ["id", "species", "dbh"] # Column selection
    sort_by: "species"                # Sort column
    ascending: true                   # Sort direction
```

### Summary Stats Widget

**Plugin Name**: `summary_stats`

Statistical summary tables for numeric data analysis.

**Key Parameters**:
```yaml
- plugin: summary_stats
  params:
    numeric_columns: ["dbh", "height", "age"]  # Columns to analyze
    percentiles: [0.25, 0.5, 0.75, 0.95]      # Percentile list
    include_stats: ["count", "mean", "std", "min", "max"]  # Stat selection
```

**Output Statistics**:
- count, mean, std, min, max
- 25%, 50%, 75% percentiles (configurable)
- Properly formatted HTML table

## Navigation Widgets

### Hierarchical Navigation Widget

**Plugin Name**: `hierarchical_nav_widget`

Interactive tree navigation for taxonomies and hierarchical data structures.

**Key Parameters**:
```yaml
- plugin: hierarchical_nav_widget
  params:
    referential_data: "taxon_ref"     # Data source identifier
    id_field: "id"                    # Required: Record ID field
    name_field: "full_name"           # Required: Display name field
    parent_id_field: "parent_id"      # Parent-child hierarchy
    # OR nested set model:
    lft_field: "lft"                  # Left boundary
    rght_field: "rght"                # Right boundary
    # Configuration:
    base_url: "/taxon/{{ id }}.html"  # Link pattern
    show_search: true                 # Enable search functionality
    max_depth: 5                      # Maximum tree depth
    collapsed_by_default: true       # Start collapsed
```

**Hierarchy Models**:

1. **Parent-Child**: Uses `parent_id_field`
2. **Nested Set**: Uses `lft_field` and `rght_field`
3. **Flat Grouping**: Groups by field values

**Data Format**:
```python
[
  {"id": 1, "full_name": "Araucariaceae", "parent_id": None, "lft": 1, "rght": 10},
  {"id": 2, "full_name": "Araucaria", "parent_id": 1, "lft": 2, "rght": 9},
  {"id": 3, "full_name": "Araucaria columnaris", "parent_id": 2, "lft": 3, "rght": 4}
]
```

**Dependencies**:
- `/assets/js/niamoto_hierarchical_nav.js`
- `/assets/css/niamoto_hierarchical_nav.css`

**Features**:
- JavaScript-based tree rendering
- Search and filter functionality
- External data source support
- Responsive design

## Configuration Examples

### Basic Widget Configuration

```yaml
# In transform.yml
widgets_data:
  species_chart:
    plugin: bar_plot
    params:
      source: occurrences
      group_by: species
      aggregation: count

# In export.yml
widgets:
  - plugin: bar_plot
    data_source: species_chart
    params:
      title: "Species Distribution"
      x_axis: "species"
      y_axis: "count"
      auto_color: true
```

### Multi-Widget Page

```yaml
widgets:
  - plugin: info_grid
    data_source: summary_stats
    params:
      title: "Key Metrics"
      items:
        - label: "Total Species"
          source: "species_count"
        - label: "Total Plots"
          source: "plot_count"

  - plugin: interactive_map
    data_source: distribution_map
    params:
      title: "Species Distribution"
      map_type: "scatter_map"
      auto_zoom: true

  - plugin: bar_plot
    data_source: rank_distribution
    params:
      title: "Taxonomic Ranks"
      x_axis: "rank"
      y_axis: "count"
      orientation: "h"
```

### Advanced Map Configuration

```yaml
- plugin: interactive_map
  data_source: forest_analysis
  params:
    title: "Forest Cover Analysis"
    map_type: "choropleth_map"
    geojson_source: "provinces"
    color_field: "forest_percentage"
    hover_data: ["province_name", "total_area", "forest_area"]
    use_topojson: true
    layers:
      - name: "administrative_boundaries"
        geojson_source: "admin_boundaries"
        line_color: "black"
        line_width: 2
        fill_opacity: 0
      - name: "protected_areas"
        geojson_source: "protected_areas"
        fill_color: "green"
        fill_opacity: 0.3
```

## Styling and Customization

### CSS Classes

Widgets generate HTML with consistent CSS classes:

```html
<div class="niamoto-widget widget-bar_plot">
  <div class="widget-header">
    <h3 class="widget-title">Chart Title</h3>
    <p class="widget-description">Description text</p>
  </div>
  <div class="widget-content">
    <!-- Widget-specific content -->
  </div>
</div>
```

### Custom Styling

Override widget styling with custom CSS:

```css
/* Target specific widget types */
.widget-bar_plot .widget-content {
  border: 1px solid #ddd;
  border-radius: 8px;
}

/* Target specific widgets by title */
.niamoto-widget:has(.widget-title:contains("Species Distribution")) {
  background-color: #f8f9fa;
}

/* Responsive design */
@media (max-width: 768px) {
  .widget-content {
    padding: 1rem;
  }
}
```

### Color Schemes

Consistent color schemes across widgets:

```yaml
# Define color palette
color_scheme:
  primary: "#2E7D32"      # Forest green
  secondary: "#66BB6A"    # Light green
  accent: "#FFC107"       # Amber
  danger: "#D32F2F"       # Red
  info: "#1976D2"         # Blue

# Use in widgets
- plugin: bar_plot
  params:
    auto_color: true
    color_palette: ["#2E7D32", "#66BB6A", "#FFC107"]
```

## Data Processing

### Data Transformation

Widgets support automatic data transformation:

```yaml
- plugin: bar_plot
  data_source: raw_occurrences
  params:
    # Data will be automatically transformed
    x_axis: "species"
    y_axis: "count"
    transform:
      group_by: "species"
      aggregation: "count"
      sort_by: "count"
      ascending: false
```

### Nested Data Access

Access nested data using dot notation:

```yaml
- plugin: info_grid
  params:
    items:
      - label: "Mean DBH"
        source: "statistics.morphology.dbh.mean"
      - label: "Max Height"
        source: "statistics.morphology.height.max"
      - label: "Species Count"
        source: "diversity.species.total"
```

### Data Validation

Widgets perform automatic data validation:

- **Type checking**: Ensures numeric fields contain numbers
- **Required fields**: Validates presence of required data
- **Range validation**: Checks coordinate bounds for maps
- **Format validation**: Ensures proper date formats

## Performance Optimization

### Large Datasets

For large datasets, consider:

```yaml
- plugin: table_view
  params:
    max_rows: 1000        # Limit displayed rows
    columns: ["id", "species", "count"]  # Select specific columns

- plugin: interactive_map
  params:
    use_topojson: true    # Reduce file sizes
    auto_zoom: true       # Optimize zoom level
```

### Caching

Widget outputs are cached during export:

- Data processing results are cached
- Plotly figures are cached
- Static HTML content is cached

### Dependencies

Minimize JavaScript dependencies:

- Plotly widgets share a single Plotly.js file
- CSS is minified and combined
- External libraries are loaded conditionally

## Troubleshooting

### Common Issues

#### Widget Not Displaying

```yaml
# Check data source exists
niamoto stats --group taxon

# Verify widget configuration
- plugin: bar_plot
  data_source: species_stats  # Must match transform.yml key
  params:
    x_axis: "species_name"    # Must exist in data
    y_axis: "count"           # Must exist in data
```

#### Data Format Errors

```python
# Ensure proper data format
{
  "species_name": ["Species A", "Species B"],  # String list
  "count": [45, 67]                            # Numeric list
}
```

#### Missing Dependencies

```bash
# Check for missing JavaScript/CSS files
ls exports/web/assets/js/
ls exports/web/assets/css/

# Regenerate if missing
niamoto export
```

### Debugging

Enable verbose output for widget debugging:

```bash
niamoto export --verbose
```

Check widget-specific logs:

```bash
tail -f logs/niamoto.log | grep "widget"
```

## Best Practices

### Widget Selection

- **Bar plots**: Categorical comparisons, species counts
- **Maps**: Spatial distribution, geographic analysis
- **Line plots**: Time series, growth trends
- **Scatter plots**: Relationships, correlations
- **Gauges**: Key performance indicators
- **Info grids**: Summary statistics, quick facts
- **Tables**: Detailed data exploration

### Data Preparation

1. **Clean data** before widget configuration
2. **Aggregate appropriately** for visualization scale
3. **Use meaningful field names** for readability
4. **Validate coordinate systems** for maps
5. **Format dates consistently** for time series

### Performance

1. **Limit data size** for client-side widgets
2. **Use appropriate widget types** for data size
3. **Enable compression** for large datasets
4. **Cache static content** when possible

### User Experience

1. **Provide clear titles** and descriptions
2. **Use consistent color schemes** across widgets
3. **Ensure responsive design** for mobile users
4. **Include interactive elements** where beneficial
5. **Test on various devices** and browsers

## Next Steps

For more advanced widget usage:

- [Plugin Development Guide](plugin-development.md) - Create custom widgets
- [Export Configuration](export-guide.md) - Configure widget exports
- [Styling Guide](styling-guide.md) - Custom CSS and themes
- [Performance Guide](performance-optimization.md) - Optimize large datasets

For troubleshooting widget issues:

- [Common Issues](../troubleshooting/common-issues.md) - Widget-specific troubleshooting
- [Data Validation](data-preparation.md) - Ensure proper data formats
- [Export Problems](../troubleshooting/export-issues.md) - Export-related problems
