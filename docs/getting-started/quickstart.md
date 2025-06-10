# Quick Start Guide

This guide helps you create your first Niamoto project in less than 10 minutes. We'll create a website showcasing ecological data from New Caledonia.

## Prerequisites

- Niamoto installed (see [Installation Guide](installation.md))
- A terminal/console
- ~500 MB of free disk space

## Step 1: Create a New Project

```bash
# Create a folder for your project
mkdir my-niamoto-project
cd my-niamoto-project

# Initialize the project
niamoto init
```

This command creates the following structure:
```
my-niamoto-project/
├── config/          # YAML configuration files
│   ├── config.yml   # General configuration
│   ├── import.yml   # Import configuration
│   ├── transform.yml # Transform configuration
│   └── export.yml   # Export configuration
├── imports/         # Source data (CSV, GeoPackage...)
├── exports/         # Generated website
├── plugins/         # Custom plugins
├── plugins/         # Custom templates
├── db/             # SQLite database
└── logs/           # Log files
```

## Step 2: Download Example Data

For this guide, we use real data from New Caledonia:

```bash
# Download example data
git clone https://github.com/niamoto/niamoto-example-data.git temp-data

# Copy necessary files
cp temp-data/occurrences.csv imports/
cp temp-data/plots.csv imports/
cp -r temp-data/shapes imports/

# Clean up
rm -rf temp-data
```

## Step 3: Configure Data Import

Edit `config/import.yml`:

```yaml
# Import taxonomy from occurrences
taxonomy:
  type: csv
  path: "imports/occurrences.csv"
  source: "occurrence"
  ranks: "family,genus,species,infra"
  occurrence_columns:
    taxon_id: "id_taxon"
    family: "family"
    genus: "genus"
    species: "species"
    infra: "infra"

# Import occurrences (trees)
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  identifier: "id_taxonref"
  location_field: "geo_pt"

# Import plots
plots:
  type: csv
  path: "imports/plots.csv"
  identifier: "id_plot"
  locality_field: "plot"
  location_field: "geo_pt"
  link_field: "locality"
  occurrence_link_field: "plot_name"

# Import geographic shapes
shapes:
  - name: "provinces"
    type: geopackage
    path: "imports/shapes/provinces.gpkg"
    id_field: "id"
    name_field: "name"

  - name: "forests"
    type: geopackage
    path: "imports/shapes/forests.gpkg"
    id_field: "id"
    name_field: "forest_type"
```

## Step 4: Configure Transformations

Edit `config/transform.yml` to calculate statistics:

```yaml
# Transformations for taxa
- group_by: taxon
  source:
    data: occurrences
    grouping: taxon_ref

  widgets_data:
    # General information
    general_info:
      plugin: field_aggregator
      params:
        fields:
          - source: taxon_ref
            field: full_name
            target: name
          - source: occurrences
            field: id
            target: count
            transformation: count

    # Distribution map
    distribution_map:
      plugin: geospatial_extractor
      params:
        source: occurrences
        field: geo_pt
        format: geojson

    # Top 10 species
    top_species:
      plugin: top_ranking
      params:
        source: occurrences
        field: taxon_ref_id
        count: 10

# Transformations for plots
- group_by: plot
  source:
    data: plots

  widgets_data:
    # Species richness
    species_richness:
      plugin: species_richness
      params:
        occurrence_data: occurrences
        location_field: plot_id

    # Shannon index
    shannon_index:
      plugin: shannon_diversity
      params:
        occurrence_data: occurrences
        location_field: plot_id
```

## Step 5: Configure Export

Edit `config/export.yml`:

```yaml
# General site configuration
site:
  title: "New Caledonia Biodiversity"
  description: "Portal for New Caledonia flora data"
  base_url: "/"

# Pages to generate
pages:
  # Home page
  - name: "index"
    template: "index.html"
    title: "Home"

  # Taxon pages
  - name: "taxa"
    type: "group"
    template: "taxon_template.html"
    index_template: "taxon_index.html"
    group: "taxon"
    widgets:
      - type: info_grid
        data: general_info
        config:
          title: "General Information"

      - type: interactive_map
        data: distribution_map
        config:
          title: "Distribution"
          height: 400

      - type: bar_plot
        data: top_species
        config:
          title: "Top 10 Species"

  # Plot pages
  - name: "plots"
    type: "group"
    template: "plot_template.html"
    index_template: "plot_index.html"
    group: "plot"
    widgets:
      - type: summary_stats
        data: species_richness
        config:
          title: "Species Richness"

      - type: radial_gauge
        data: shannon_index
        config:
          title: "Diversity Index"
```

## Step 6: Run the Complete Pipeline

```bash
# Execute the entire pipeline (import + transform + export)
niamoto run

# Or run step by step:
niamoto import    # Import data
niamoto transform # Calculate statistics
niamoto export    # Generate website
```

## Step 7: View the Result

```bash
# Start a local web server
cd exports/web
python -m http.server 8000

# Open in browser
# http://localhost:8000
```

## Generated Site Structure

Your site will contain:

```
exports/web/
├── index.html           # Home page
├── taxon/              # Species pages
│   ├── index.html      # Taxa index
│   ├── 1.html          # Species 1 page
│   ├── 2.html          # Species 2 page
│   └── ...
├── plot/               # Plot pages
│   ├── index.html      # Plot index
│   ├── 1.html          # Plot 1 page
│   └── ...
└── assets/             # CSS, JS, images
    ├── css/
    └── js/
```

## Quick Customization

### Add a Logo

Place your logo in `imports/assets/logo.png` and reference it in `config/export.yml`:

```yaml
site:
  logo: "assets/logo.png"
```

### Change Colors

Create `templates/custom.css`:

```css
:root {
  --primary-color: #2e7d32;
  --secondary-color: #1976d2;
}
```

### Add a Static Page

In `config/export.yml`:

```yaml
pages:
  - name: "about"
    template: "about.html"
    title: "About"
    content_file: "content/about.md"
```

## Useful Commands

```bash
# View database statistics
niamoto stats

# Reload only transformations
niamoto transform --force

# Export with different template
niamoto export --template-dir ./my-templates

# Enable detailed logs
niamoto run --verbose
```

## Troubleshooting

### "File not found" Error
Check that paths in `import.yml` are relative to the project folder.

### "Invalid column" Error
Verify that column names in your CSV files match those in `import.yml`.

### Blank Page
Check logs in `logs/niamoto.log` to identify the error.

## Next Steps

1. **Customize templates**: See [Template Guide](../guides/templates.md)
2. **Add widgets**: See [Widget Reference](../guides/widget-reference.md)
3. **Create plugins**: See [Plugin Development](../guides/custom_plugin.md)
4. **Deploy the site**: See [Deployment Guide](../guides/deployment.md)

## Resources

- [Complete example data](https://github.com/niamoto/niamoto-example-data)
- [Custom templates](https://github.com/niamoto/niamoto-templates)
- [Community plugins](https://github.com/niamoto/niamoto-plugins)
