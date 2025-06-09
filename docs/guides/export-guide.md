# Export Guide

This comprehensive guide covers exporting your processed data into static websites, configuring pages, widgets, and customizing the final output.

## Overview

Niamoto's export system transforms your ecological data into interactive static websites that can be hosted anywhere. The system uses a plugin-based architecture with configurable templates, widgets, and layouts.

## Export Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Processed   │ →  │ Export       │ →  │ Static      │
│ Data        │    │ Configuration│    │ Website     │
│ (Database)  │    │ (export.yml) │    │ (HTML/CSS)  │
└─────────────┘    └──────────────┘    └─────────────┘
```

## Configuration Structure

All exports are configured in `config/export.yml`:

```yaml
exports:
  - name: web_pages
    enabled: true
    exporter: html_page_exporter

    params:
      # General settings
      template_dir: "templates/"
      output_dir: "exports/web"

      # Site configuration
      site:
        title: "My Biodiversity Portal"
        primary_color: "#228b22"

      # Static pages
      static_pages: [...]

      # Data-driven pages
      groups: [...]
```

## Site Configuration

### Basic Site Settings

```yaml
site:
  title: "New Caledonia Biodiversity"
  description: "Portal for New Caledonia flora data"
  lang: "en"
  primary_color: "#228b22"
  nav_color: "#2e7d32"
  logo_header: "files/logo.png"
  logo_footer: "files/logo_footer.png"
  github_url: "https://github.com/username/project"
```

### Navigation Menu

```yaml
navigation:
  - text: "Home"
    url: "/index.html"
  - text: "Methodology"
    url: "/methodology.html"
  - text: "Trees"
    url: "/trees.html"
  - text: "Plots"
    url: "/plots.html"
  - text: "Forest"
    url: "/forests.html"
  - text: "Resources"
    url: "/resources.html"
```

### Asset Management

```yaml
copy_assets_from:
  - "templates/assets/"          # Custom CSS, JS, images
  - "imports/documents/"         # PDFs, datasets
```

## Static Pages

Static pages are template-based pages with fixed content. **All static pages use the default `static_page.html` template** unless you provide a custom template in your project's `templates/` directory.

### Basic Static Page Configuration

```yaml
static_pages:
  # Uses default static_page.html template
  - name: home
    output_file: "index.html"

  # Uses default static_page.html template
  - name: methodology
    output_file: "methodology.html"

  # Uses default static_page.html template
  - name: about
    output_file: "about.html"
```

### Custom Static Page Templates

If you want custom layouts, create templates in your project's `templates/` directory:

```yaml
static_pages:
  # Custom template (must exist in templates/ directory)
  - name: home
    template: "custom_home.html"
    output_file: "index.html"

  # Uses default static_page.html template
  - name: methodology
    output_file: "methodology.html"
```

### Pages with Dynamic Content

Static pages can include dynamic data from your transformations:

```yaml
static_pages:
  - name: statistics
    template: "custom_stats.html"  # Optional custom template
    output_file: "statistics.html"
    widgets:
      - plugin: info_grid
        title: "Database Statistics"
        data_source: site_statistics  # Reference transform.yml data
        params:
          grid_columns: 2
          items:
            - label: "Total Species"
              source: "species_count"
              icon: "fa-leaf"
            - label: "Total Occurrences"
              source: "occurrence_count"
              icon: "fa-map-marker"
```

**Note**: Data for static pages comes from your `transform.yml` configuration, not direct database queries. For site-wide statistics, create a global transformation group.

## Data-Driven Groups

Groups generate multiple pages from your data (taxa, plots, shapes).

### Basic Group Configuration

```yaml
groups:
  - group_by: taxon
    output_pattern: "taxon/{id}.html"
    index_output_pattern: "taxon/index.html"
    page_template: "group_detail.html"

    widgets:
      - plugin: info_grid
        title: "General Information"
        data_source: general_info

      - plugin: interactive_map
        title: "Distribution"
        data_source: distribution_map
```

**Note**: Group pages use Niamoto's built-in templates:
- **Detail pages**: `group_detail.html` (default)
- **Index pages**: `group_index.html` (default)

You can override these by creating custom templates in your `templates/` directory.

### Advanced Group with Index Generation

```yaml
groups:
  - group_by: taxon
    output_pattern: "taxon/{id}.html"
    index_output_pattern: "taxon/index.html"
    page_template: "group_detail.html"

    # Index page configuration
    index_generator:
      enabled: true
      template: "group_index.html" # default template

      page_config:
        title: "Species List"
        description: "All species in New Caledonia"
        items_per_page: 24

      # Filter which items to include
      filters:
        - field: "general_info.rank.value"
          operator: "in"
          value: ["species", "subspecies"]

      # Sort items
      sort:
        - field: "general_info.name.value"
          direction: "asc"

      # Enable search
      search:
        enabled: true
        fields: ["general_info.name.value"]

    # Detail page widgets
    widgets:
      - plugin: hierarchical_nav_widget
        title: "Taxonomy"
        data_source: nav_tree

      - plugin: info_grid
        title: "General Information"
        data_source: general_info

      - plugin: interactive_map
        title: "Distribution Map"
        data_source: distribution_map
        params:
          height: 400
          zoom: 7
          map_style: "carto-positron"
```

## Widget System

Widgets are reusable components that visualize your data.

### Available Widget Types

#### Info Grid
Display structured information:

```yaml
- plugin: info_grid
  title: "Species Information"
  data_source: general_info
  params:
    layout: "two_column"  # or "single_column"
    show_empty: false
```

#### Interactive Map
Show geographic distributions:

```yaml
- plugin: interactive_map
  title: "Distribution Map"
  data_source: distribution_map
  params:
    height: 400
    zoom: 7
    center: [-22.0, 166.0]
    map_style: "carto-positron"
    layers:
      - name: "Provinces"
        data_source: provinces_geojson
        style:
          fillColor: "rgba(255,0,0,0.1)"
          weight: 2
```

#### Bar Plot
Create bar charts:

```yaml
- plugin: bar_plot
  title: "Top 10 Species"
  data_source: top_species
  params:
    x_field: "name"
    y_field: "count"
    color: "#228b22"
    orientation: "horizontal"  # or "vertical"
```

#### Donut Chart
Show proportional data:

```yaml
- plugin: donut_chart
  title: "Endemic vs Native"
  data_source: endemic_stats
  params:
    value_field: "count"
    label_field: "category"
    colors: ["#228b22", "#87ceeb"]
```

#### Summary Stats
Display key metrics:

```yaml
- plugin: summary_stats
  title: "Plot Statistics"
  data_source: plot_summary
  params:
    layout: "grid"  # or "list"
    format_large_numbers: true
```

#### Table View
Show tabular data:

```yaml
- plugin: table_view
  title: "Occurrence Data"
  data_source: occurrence_list
  params:
    columns:
      - field: "species_name"
        title: "Species"
      - field: "dbh"
        title: "DBH (cm)"
        format: "decimal:1"
      - field: "height"
        title: "Height (m)"
        format: "decimal:1"
    paginate: true
    page_size: 25
```

#### Raw Data Widget
Export data as downloadable files:

```yaml
- plugin: raw_data_widget
  title: "Download Data"
  data_source: occurrence_data
  params:
    formats: ["csv", "json", "geojson"]
    download_text: "Download occurrence data"
```

### Widget Data Sources

Widgets get their data from transformation results configured in `transform.yml`:

```yaml
# In transform.yml
- group_by: taxon
  widgets_data:
    general_info:
      plugin: field_aggregator
      params:
        fields:
          - source: taxon_ref
            field: full_name
            target: name

    distribution_map:
      plugin: geospatial_extractor
      params:
        source: occurrences
        field: geo_pt
        format: geojson

# In export.yml - reference the data source
widgets:
  - plugin: interactive_map
    data_source: distribution_map  # Matches transform.yml
```

## Template Customization

### Template System

Niamoto uses a **two-level template system**:

1. **Built-in templates** (in Niamoto core): Used by default
2. **Project templates** (in your `templates/` directory): Override defaults

#### Built-in Templates (Default)

Niamoto provides these templates automatically:
- `static_page.html` - For all static pages
- `group_detail.html` - For individual entity pages (taxon, plot, shape)
- `group_index.html` - For entity list pages with search/filtering
- `_base.html` - Base layout with navigation
- `_nav.html` - Navigation component
- `_footer.html` - Footer component

#### Project Template Directory (Optional)

Override defaults by creating templates in your project:

```
templates/                  # Your project templates (optional)
├── custom_home.html        # Custom static page template
├── custom_taxon_detail.html # Custom group detail template
├── assets/                 # Your custom assets
│   ├── css/
│   │   └── custom.css
│   ├── js/
│   │   └── custom.js
│   └── files/
│       └── logo.png
└── content/                # Markdown content for static pages
    ├── about.md
    └── methodology.md
```

#### Template Precedence

1. **Project templates** (if they exist) are used first
2. **Built-in templates** are used as fallback
3. **No configuration needed** - just create files to override

**Note**: Widgets are rendered directly by their plugins and do not use separate template files.

### Creating Custom Templates

#### Basic Template Structure

```html
<!-- templates/custom_page.html -->
{% extends "_base.html" %}

{% block title %}{{ page.title }} - {{ site.title }}{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">{{ page.title }}</h1>

    <!-- Your custom content -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        {% for widget_key, widget_html in widgets.items() %}
            <div class="widget-container">
                {{ widget_html|safe }}
            </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

#### Widget Styling

Widgets are rendered directly by their plugins. You can style them with CSS:

```css
/* templates/assets/css/custom.css */
.widget-container {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
}

.widget-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: #1f2937;
}

/* Style specific widget types */
.plotly-container {
    border-radius: 6px;
    overflow: hidden;
}

.info-grid {
    display: grid;
    gap: 1rem;
}
```

### Template Context Variables

Templates have access to these variables:

```python
# Available in all templates
{
    'site': {
        'title': 'Site Title',
        'primary_color': '#228b22',
        # ... other site config
    },
    'navigation': [
        {'text': 'Home', 'url': '/index.html'},
        # ... navigation items
    ]
}

# Available in group detail pages
{
    'entity': {
        'id': 123,
        'name': 'Araucaria columnaris',
        # ... entity data
    },
    'widgets': [
        {
            'plugin': 'interactive_map',
            'title': 'Distribution',
            'data': { /* widget data */ }
        }
    ]
}

# Available in group index pages
{
    'entities': [
        {'id': 1, 'name': 'Species 1'},
        {'id': 2, 'name': 'Species 2'},
        # ... filtered and paginated entities
    ],
    'pagination': {
        'current_page': 1,
        'total_pages': 5,
        'has_next': true,
        'has_prev': false
    }
}
```

## Advanced Features

### Multi-language Support

```yaml
site:
  lang: "en"
  languages:
    en:
      title: "New Caledonia Biodiversity"
      nav_home: "Home"
    fr:
      title: "Biodiversité de Nouvelle-Calédonie"
      nav_home: "Accueil"
```

### Custom CSS and Styling

```yaml
# Copy custom assets
copy_assets_from:
  - "templates/assets/"

# Reference in templates
{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/custom.css') }}">
{% endblock %}
```

**Custom CSS example** (`templates/assets/css/custom.css`):

```css
:root {
  --primary-color: #2e7d32;
  --secondary-color: #1976d2;
  --accent-color: #ff9800;
}

.widget-container {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
}

.custom-navigation {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
}
```

### JavaScript Enhancements

```javascript
// templates/assets/js/custom.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize custom widgets
    initializeSearchFilters();
    setupLazyLoading();

    // Custom map interactions
    function initializeMap(containerId, data) {
        // Custom Plotly.js configuration
        const layout = {
            mapbox: {
                style: 'carto-positron',
                center: { lat: -22.0, lon: 166.0 },
                zoom: 7
            }
        };

        Plotly.newPlot(containerId, data, layout);
    }
});
```

## Performance Optimization

### TopoJSON for Maps

Convert large GeoJSON files to TopoJSON for better performance:

```yaml
# In transformation
- plugin: geospatial_extractor
  params:
    format: "topojson"  # Instead of geojson
    simplify: 0.001     # Simplify geometries
    quantize: 1e4       # Reduce precision
```

### Asset Optimization

```yaml
copy_assets_from:
  - source: "templates/assets/"
    optimize: true
    minify_css: true
    minify_js: true
    compress_images: true
```

### Lazy Loading

```html
<!-- Templates with lazy loading -->
<div class="widget-container" data-lazy-load="true">
    <div class="loading-placeholder">Loading...</div>
</div>

<script>
// Lazy load widgets when they come into view
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            loadWidget(entry.target);
        }
    });
});
</script>
```

## Deployment Preparation

### Production Build

```bash
# Generate optimized production build
niamoto export --optimize

# Check output
ls -la exports/web/
```

### Testing Locally

```bash
# Start local server
cd exports/web
python -m http.server 8000

# Test in browser
open http://localhost:8000
```

### Static Hosting

The generated site is fully static and can be hosted on:

- **GitHub Pages**
- **Netlify**
- **Vercel**
- **AWS S3**
- **Any web server**

Example for GitHub Pages:

```bash
# Deploy using built-in command
niamoto deploy github --repo https://github.com/username/repo.git
```

## Troubleshooting

### Common Issues

#### Template Not Found
```
TemplateNotFound: group_detail.html
```
**Solution**: Ensure template exists in `templates/` directory or use default templates.

#### Widget Rendering Errors
```
Widget 'interactive_map' failed to render
```
**Solution**: Check that the data source exists in transform configuration and contains valid data.

#### Asset Loading Issues
```
Failed to load CSS/JS files
```
**Solution**: Verify asset paths and ensure `copy_assets_from` is correctly configured.

### Debugging Tips

1. **Use verbose output**: `niamoto export --verbose`
2. **Check logs**: `tail -f logs/niamoto.log`
3. **Validate templates**: Test with minimal configuration first
4. **Browser console**: Check for JavaScript errors
5. **Network tab**: Verify all assets load correctly

## Best Practices

### Template Organization
```
templates/
├── base/
│   ├── _base.html
│   ├── _nav.html
│   └── _footer.html
├── pages/
│   ├── index.html
│   ├── methodology.html
│   └── about.html
├── groups/
│   ├── taxon_detail.html
│   ├── plot_detail.html
│   └── group_index.html
└── widgets/
    ├── _widgets.html
    └── custom_widgets.html
```

### Configuration Management
1. **Modular configuration**: Split large export.yml into includes
2. **Environment-specific**: Use different configs for dev/prod
3. **Version control**: Track template and config changes
4. **Documentation**: Comment complex widget configurations

### Performance Guidelines
1. **Optimize images**: Use appropriate formats and sizes
2. **Minimize HTTP requests**: Combine CSS/JS files
3. **Use CDNs**: For common libraries like Plotly.js
4. **Enable compression**: Gzip static files
5. **Progressive enhancement**: Core content works without JavaScript

## Next Steps

- [Deployment Guide](deployment.md) - Publishing your site
- [Widget Reference](widget-reference.md) - Complete widget documentation
- [Template Development](template-development.md) - Advanced template customization
- [API Export](api-export.md) - Generating JSON APIs alongside HTML
