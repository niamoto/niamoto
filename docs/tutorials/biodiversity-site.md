# Tutorial: Creating a Biodiversity Portal

This comprehensive tutorial guides you through creating a complete biodiversity portal using real ecological data from New Caledonia. You'll learn every step from data preparation to deployment.

## Overview

By the end of this tutorial, you'll have created a fully functional biodiversity website featuring:

- Interactive species distribution maps
- Hierarchical taxonomic navigation
- Ecological indices and statistics
- Responsive design for mobile and desktop
- Search and filtering capabilities

**Live Example**: [New Caledonia Biodiversity Portal](https://niamoto.github.io/example-site/)

**Time Required**: 2-3 hours
**Difficulty**: Beginner to Intermediate

## Prerequisites

- Niamoto installed ([Installation Guide](../getting-started/installation.md))
- Basic understanding of CSV files and ecological data
- Text editor for configuration files
- Web browser for testing

## Tutorial Overview

1. [Project Setup](#1-project-setup)
2. [Data Preparation](#2-data-preparation)
3. [Import Configuration](#3-import-configuration)
4. [Data Transformation](#4-data-transformation)
5. [Website Export](#5-website-export)
6. [Customization](#6-customization)
7. [Testing & Deployment](#7-testing--deployment)

---

## 1. Project Setup

### Create Your Project

```bash
# Create and navigate to project directory
mkdir caledonia-biodiversity
cd caledonia-biodiversity

# Initialize Niamoto project
niamoto init
```

This creates the following structure:
```
caledonia-biodiversity/
├── config/
│   ├── config.yml
│   ├── import.yml
│   ├── transform.yml
│   └── export.yml
├── imports/
├── exports/
├── plugins/
├── db/
└── logs/
```

### Download Tutorial Data

We'll use real biodiversity data from New Caledonia:

```bash
# Download the tutorial dataset
curl -L https://github.com/niamoto/tutorial-data/archive/main.zip -o tutorial-data.zip
unzip tutorial-data.zip
mv tutorial-data-main/data/* imports/
rm -rf tutorial-data.zip tutorial-data-main
```

Your `imports/` folder should now contain:
```
imports/
├── occurrences.csv          # 15,000+ tree observations
├── plots.csv               # 150 forest plots
├── taxonomy.csv            # 500+ species
└── shapes/
    ├── provinces.gpkg      # Administrative boundaries
    ├── forest_types.gpkg   # Forest classification
    └── protected_areas.gpkg # Conservation areas
```

### Examine the Data

Let's explore what we're working with:

```bash
# Look at the taxonomy structure
head -5 imports/taxonomy.csv

# Check occurrence data
head -5 imports/occurrences.csv

# Count records
wc -l imports/*.csv
```

**Taxonomy structure** (first few lines):
```csv
id_taxon,family,genus,species,authors,rank_name,full_name
1,Araucariaceae,Araucaria,columnaris,"(G.Forst.) Hook.",species,Araucaria columnaris
2,Araucariaceae,Araucaria,montana,"Brongn. & Gris",species,Araucaria montana
3,Myrtaceae,Syzygium,hancei,"(Hance) Merr. & L.M.Perry",species,Syzygium hancei
```

**Occurrence structure**:
```csv
id,id_taxon,plot_id,latitude,longitude,dbh,height,date_observed,observer
1,1,P001,-22.2764,166.4580,45.5,12.3,2024-03-15,J.Smith
2,1,P001,-22.2765,166.4582,52.1,14.1,2024-03-15,J.Smith
```

---

## 2. Data Preparation

### Understanding Your Data Schema

Before configuring imports, understand your data structure:

**Taxonomy Hierarchy:**
- Family → Genus → Species
- Each taxon has an ID and full scientific name
- Authors and publication information included

**Occurrence Records:**
- Individual tree observations
- Linked to taxonomy via `id_taxon`
- Geographic coordinates (WGS84)
- Measurements: DBH (diameter), height
- Collection metadata: date, observer, plot

**Study Plots:**
- Standardized sampling areas
- Environmental variables: elevation, slope
- Links to multiple occurrences

**Geographic Shapes:**
- Administrative boundaries (provinces)
- Environmental zones (forest types)
- Conservation areas (protected areas)

### Data Quality Checks

Before importing, let's validate our data:

```bash
# Check for missing coordinates
awk -F',' 'NR>1 && ($4=="" || $5=="") {print "Row " NR ": Missing coordinates"}' imports/occurrences.csv

# Verify coordinate ranges (New Caledonia bounds)
awk -F',' 'NR>1 && ($4<-25 || $4>-19 || $5<163 || $5>168) {print "Row " NR ": Invalid coordinates: " $4 "," $5}' imports/occurrences.csv

# Check taxonomy linkage
awk -F',' 'NR>1 {taxon_ids[$2]++} END {print "Unique taxa in occurrences:", length(taxon_ids)}' imports/occurrences.csv
```

---

## 3. Import Configuration

### Configure Taxonomy Import

Edit `config/import.yml` to set up taxonomy import:

```yaml
# Import taxonomic hierarchy
taxonomy:
  type: csv
  path: "imports/taxonomy.csv"
  source: "file"
  identifier: "id_taxon"
  ranks: "family,genus,species"
  mapping:
    full_name: "full_name"
    rank_name: "rank_name"
    authors: "authors"
    family: "family"
    genus: "genus"
    species: "species"
```

### Configure Occurrence Import

```yaml
# Import species observations
occurrences:
  type: csv
  path: "imports/occurrences.csv"
  mapping:
    id_occurrence: "id"
    taxon_ref_id: "id_taxon"
    geo_pt:
      x: "longitude"
      y: "latitude"
    properties:
      - dbh
      - height
      - date_observed
      - observer
      - plot_id

  # Data validation
  validation:
    required_fields:
      - taxon_ref_id
      - geo_pt
    coordinate_bounds:
      min_lat: -25.0
      max_lat: -19.0
      min_lon: 163.0
      max_lon: 168.0
    value_ranges:
      dbh:
        min: 1.0
        max: 500.0
      height:
        min: 0.5
        max: 80.0
```

### Configure Plot Import

```yaml
# Import study plots
plots:
  type: csv
  path: "imports/plots.csv"
  mapping:
    id_plot: "plot_id"
    name: "plot_name"
    geo_pt:
      x: "longitude"
      y: "latitude"
    properties:
      - elevation
      - slope_percent
      - aspect_degrees
      - area_m2
      - forest_type
      - establishment_date
```

### Configure Shape Import

```yaml
# Import geographic boundaries
shapes:
  - name: "provinces"
    type: geopackage
    path: "imports/shapes/provinces.gpkg"
    id_field: "id"
    name_field: "name"
    properties:
      - area_km2
      - population

  - name: "forest_types"
    type: geopackage
    path: "imports/shapes/forest_types.gpkg"
    id_field: "forest_id"
    name_field: "forest_name"
    properties:
      - canopy_cover
      - dominant_family

  - name: "protected_areas"
    type: geopackage
    path: "imports/shapes/protected_areas.gpkg"
    id_field: "pa_id"
    name_field: "pa_name"
    properties:
      - protection_level
      - area_hectares
      - creation_date
```

### Run the Import

```bash
# Import all data
niamoto import

# Check import results
niamoto stats
```

You should see output like:
```
Niamoto Database Statistics
===========================

Taxonomy:
  Families: 45
  Genera: 156
  Species: 423

Occurrences:
  Total: 15,247
  Georeferenced: 15,139 (99.3%)

Plots:
  Total: 150
  With occurrences: 148 (98.7%)

Shapes:
  Provinces: 3
  Forest types: 8
  Protected areas: 12
```

---

## 4. Data Transformation

Now we'll configure the transformations that calculate statistics and prepare data for visualization.

### Taxonomy Transformations

Edit `config/transform.yml`:

```yaml
# Transformations for species pages
- group_by: taxon
  source:
    data: occurrences
    grouping: taxon_ref
    relation:
      plugin: nested_set
      key: taxon_ref_id
      fields:
        parent: parent_id
        left: lft
        right: rght

  widgets_data:
    # Basic species information
    general_info:
      plugin: field_aggregator
      params:
        fields:
          - source: taxon_ref
            field: full_name
            target: name
          - source: taxon_ref
            field: rank_name
            target: rank
          - source: taxon_ref
            field: authors
            target: authors
          - source: taxon_ref
            field: family
            target: family
          - source: occurrences
            field: id
            target: occurrence_count
            transformation: count
          - source: occurrences
            field: plot_id
            target: plot_count
            transformation: count_unique

    # Geographic distribution
    distribution_map:
      plugin: geospatial_extractor
      params:
        source: occurrences
        field: geo_pt
        format: geojson
        group_by_coordinates: true
        properties: ["dbh", "height", "plot_id"]

    # Morphological statistics
    morphology_stats:
      plugin: field_aggregator
      params:
        fields:
          - source: occurrences
            field: dbh
            target: dbh_mean
            transformation: mean
            format: "decimal:1"
          - source: occurrences
            field: dbh
            target: dbh_max
            transformation: max
            format: "decimal:1"
          - source: occurrences
            field: height
            target: height_mean
            transformation: mean
            format: "decimal:1"
          - source: occurrences
            field: height
            target: height_max
            transformation: max
            format: "decimal:1"

    # Top plots for this species
    top_plots:
      plugin: top_ranking
      params:
        source: occurrences
        field: plot_id
        count: 10
        mode: direct
        join_fields:
          - field: plot_name
            from_table: plots
            on_field: id_plot

    # Conservation status
    conservation_info:
      plugin: spatial_aggregator
      params:
        occurrence_source: occurrences
        shape_source: protected_areas
        aggregation: intersection_count
        output_field: protected_area_count
```

### Plot Transformations

```yaml
# Transformations for plot pages
- group_by: plot
  source:
    data: plots

  widgets_data:
    # Plot basic information
    general_info:
      plugin: field_aggregator
      params:
        fields:
          - source: plots
            field: plot_name
            target: name
          - source: plots
            field: elevation
            target: elevation
            format: "integer"
            unit: "m"
          - source: plots
            field: area_m2
            target: area
            format: "integer"
            unit: "m²"
          - source: plots
            field: forest_type
            target: forest_type

    # Species diversity indices
    diversity_indices:
      plugin: ecological_indices
      params:
        occurrence_source: occurrences
        location_field: plot_id
        indices:
          - species_richness
          - shannon_diversity
          - simpson_diversity
          - pielou_evenness

    # Species composition
    species_composition:
      plugin: top_ranking
      params:
        source: occurrences
        field: taxon_ref_id
        count: 15
        mode: hierarchical
        hierarchy_table: taxon_ref
        join_fields:
          - field: full_name
            from_table: taxon_ref
            on_field: id

    # Size distribution
    size_distribution:
      plugin: histogram_generator
      params:
        source: occurrences
        field: dbh
        bins: 10
        range: [10, 200]
        title: "DBH Distribution"

    # Plot location map
    location_map:
      plugin: geospatial_extractor
      params:
        source: plots
        field: geo_pt
        format: geojson
        include_shapes: ["provinces", "forest_types"]
```

### Global Site Statistics

```yaml
# Site-wide statistics for home page
- group_by: site
  source:
    data: global

  widgets_data:
    # Overall summary statistics
    site_summary:
      plugin: database_aggregator
      params:
        queries:
          - name: total_species
            sql: "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
          - name: total_occurrences
            sql: "SELECT COUNT(*) FROM occurrences"
          - name: total_plots
            sql: "SELECT COUNT(*) FROM plots"
          - name: families_count
            sql: "SELECT COUNT(DISTINCT family) FROM taxon_ref WHERE rank_name = 'species'"

    # Most diverse families
    top_families:
      plugin: top_ranking
      params:
        source: taxon_ref
        field: family
        count: 10
        mode: direct
        filter:
          rank_name: "species"

    # Spatial coverage map
    coverage_map:
      plugin: geospatial_extractor
      params:
        source: occurrences
        field: geo_pt
        format: geojson
        density_map: true
        include_shapes: ["provinces", "protected_areas"]
```

### Run Transformations

```bash
# Process all transformations
niamoto transform

# Check results with detailed stats
niamoto stats --detailed
```

---

## 5. Website Export

Now configure the website generation in `config/export.yml`.

### Site Configuration

```yaml
exports:
  - name: web_pages
    enabled: true
    exporter: html_page_exporter

    params:
      template_dir: "templates/"
      output_dir: "exports/web"

      # Site branding and settings
      site:
        title: "New Caledonia Biodiversity Portal"
        description: "Explore the unique flora of New Caledonia through comprehensive biodiversity data"
        lang: "en"
        primary_color: "#2e7d32"
        nav_color: "#1976d2"
        logo_header: "files/nc_logo.png"
        github_url: "https://github.com/username/caledonia-biodiversity"

      # Main navigation menu
      navigation:
        - text: "Home"
          url: "/index.html"
        - text: "Species"
          url: "/taxon/index.html"
        - text: "Plots"
          url: "/plot/index.html"
        - text: "About"
          url: "/about.html"
        - text: "Methodology"
          url: "/methodology.html"

      # Copy project assets
      copy_assets_from:
        - "templates/assets/"
```

### Static Pages

```yaml
      # Fixed content pages
      static_pages:
        # Home page with site overview
        - name: home
          template: "index.html"
          output_file: "index.html"
          data_sources:
            - site_summary
            - top_families
            - coverage_map

        # About page
        - name: about
          template: "about.html"
          output_file: "about.html"

        # Methodology page
        - name: methodology
          template: "methodology.html"
          output_file: "methodology.html"
```

### Species Pages

```yaml
      # Data-driven pages
      groups:
        # Species/taxa pages
        - group_by: taxon
          output_pattern: "taxon/{id}.html"
          index_output_pattern: "taxon/index.html"

          # Species list/index configuration
          index_generator:
            enabled: true
            template: "group_index.html"

            page_config:
              title: "Species Explorer"
              description: "Browse all documented species in New Caledonia"
              items_per_page: 24

            # Show only species-level taxa
            filters:
              - field: "general_info.rank.value"
                operator: "equals"
                value: "species"

            # Sort alphabetically
            sort:
              - field: "general_info.name.value"
                direction: "asc"

            # Enable search functionality
            search:
              enabled: true
              fields: ["general_info.name.value", "general_info.family.value"]
              placeholder: "Search species..."

          # Individual species page widgets
          widgets:
            # Taxonomic navigation tree
            - plugin: hierarchical_nav_widget
              title: "Taxonomy"
              data_source: nav_tree
              params:
                max_depth: 4
                show_counts: true

            # Species basic information
            - plugin: info_grid
              title: "Species Information"
              data_source: general_info
              params:
                layout: "two_column"
                highlight_key: "name"

            # Distribution map
            - plugin: interactive_map
              title: "Geographic Distribution"
              data_source: distribution_map
              params:
                height: 400
                zoom: 8
                center: [-22.0, 166.0]
                map_style: "carto-positron"
                marker_color: "#2e7d32"
                cluster_markers: true

            # Morphological data
            - plugin: summary_stats
              title: "Morphological Statistics"
              data_source: morphology_stats
              params:
                layout: "grid"
                format_decimals: 1
                show_units: true

            # Plot occurrences
            - plugin: table_view
              title: "Plot Occurrences"
              data_source: top_plots
              params:
                columns:
                  - field: "plot_name"
                    title: "Plot"
                  - field: "count"
                    title: "Individuals"
                  - field: "percentage"
                    title: "% of Total"
                    format: "percentage:1"
                max_rows: 10

            # Conservation status
            - plugin: info_grid
              title: "Conservation"
              data_source: conservation_info
              params:
                show_empty: false
```

### Plot Pages

```yaml
        # Forest plot pages
        - group_by: plot
          output_pattern: "plot/{id}.html"
          index_output_pattern: "plot/index.html"

          # Plot list configuration
          index_generator:
            enabled: true
            template: "group_index.html"

            page_config:
              title: "Forest Plots"
              description: "Explore our network of permanent forest monitoring plots"
              items_per_page: 20

            sort:
              - field: "general_info.name.value"
                direction: "asc"

            search:
              enabled: true
              fields: ["general_info.name.value", "general_info.forest_type.value"]

          # Individual plot page widgets
          widgets:
            # Plot information
            - plugin: info_grid
              title: "Plot Information"
              data_source: general_info

            # Diversity indices
            - plugin: radial_gauge
              title: "Species Diversity"
              data_source: diversity_indices
              params:
                value_field: "shannon_diversity"
                max_value: 4.0
                color_scale: ["#ffcccc", "#ff0000"]

            # Species composition chart
            - plugin: bar_plot
              title: "Species Composition"
              data_source: species_composition
              params:
                x_field: "full_name"
                y_field: "count"
                orientation: "horizontal"
                max_bars: 15

            # Size distribution
            - plugin: bar_plot
              title: "DBH Distribution"
              data_source: size_distribution
              params:
                x_field: "bin_center"
                y_field: "count"
                x_title: "DBH (cm)"
                y_title: "Number of Trees"

            # Plot location
            - plugin: interactive_map
              title: "Plot Location"
              data_source: location_map
              params:
                height: 300
                zoom: 10
                show_shapes: true
```

### Generate the Website

```bash
# Generate complete website
niamoto export

# Check output
ls -la exports/web/
```

You should see:
```
exports/web/
├── index.html
├── about.html
├── methodology.html
├── taxon/
│   ├── index.html
│   ├── 1.html
│   ├── 2.html
│   └── ... (423 species pages)
├── plot/
│   ├── index.html
│   ├── 1.html
│   └── ... (150 plot pages)
└── assets/
    ├── css/
    ├── js/
    └── files/
```

---

## 6. Customization

### Create Custom Templates

Create a custom home page template:

```bash
mkdir -p templates/assets/css
```

**Create `templates/index.html`:**

```html
{% extends "_base.html" %}

{% block title %}{{ site.title }} - Biodiversity Portal{% endblock %}

{% block content %}
<!-- Hero Section -->
<div class="hero bg-gradient-to-r from-green-600 to-blue-600 text-white py-16">
    <div class="container mx-auto px-4 text-center">
        <h1 class="text-5xl font-bold mb-4">{{ site.title }}</h1>
        <p class="text-xl mb-8">{{ site.description }}</p>
        <a href="/taxon/index.html" class="bg-white text-green-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition">
            Explore Species
        </a>
    </div>
</div>

<!-- Statistics Overview -->
<div class="container mx-auto px-4 py-12">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
        {% for stat in site_summary %}
        <div class="bg-white rounded-lg shadow-lg p-6 text-center">
            <div class="text-3xl font-bold text-green-600 mb-2">{{ stat.value|number_format }}</div>
            <div class="text-gray-600">{{ stat.label }}</div>
        </div>
        {% endfor %}
    </div>

    <!-- Featured Content -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Coverage Map -->
        <div class="widget-container">
            <h2 class="text-2xl font-bold mb-4">Spatial Coverage</h2>
            {% include '_widgets.html' with widget=coverage_map %}
        </div>

        <!-- Top Families -->
        <div class="widget-container">
            <h2 class="text-2xl font-bold mb-4">Most Diverse Families</h2>
            {% include '_widgets.html' with widget=top_families %}
        </div>
    </div>
</div>
{% endblock %}
```

### Add Custom Styling

**Create `templates/assets/css/custom.css`:**

```css
/* Custom theme colors */
:root {
  --primary-green: #2e7d32;
  --secondary-blue: #1976d2;
  --accent-orange: #ff9800;
  --light-gray: #f5f5f5;
}

/* Hero section styling */
.hero {
  background: linear-gradient(135deg, var(--primary-green), var(--secondary-blue));
  min-height: 60vh;
  display: flex;
  align-items: center;
}

/* Widget containers */
.widget-container {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
  border-left: 4px solid var(--primary-green);
}

/* Species cards */
.species-card {
  transition: transform 0.2s ease-in-out;
  border: 1px solid #e5e7eb;
}

.species-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

/* Interactive map enhancements */
.map-container {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

/* Navigation improvements */
.taxonomic-nav {
  background: var(--light-gray);
  border-radius: 8px;
  padding: 1rem;
}

.taxonomic-nav .nav-item {
  padding: 0.5rem;
  border-radius: 4px;
  margin: 0.25rem 0;
}

.taxonomic-nav .nav-item:hover {
  background: var(--primary-green);
  color: white;
}

/* Responsive improvements */
@media (max-width: 768px) {
  .hero h1 {
    font-size: 2.5rem;
  }

  .widget-container {
    padding: 1rem;
  }
}
```

### Add Interactive Features

**Create `templates/assets/js/custom.js`:**

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize search functionality
    initializeSearch();

    // Setup lazy loading for images
    setupLazyLoading();

    // Enhanced map interactions
    setupMapEnhancements();

    // Statistics counter animation
    animateCounters();
});

function initializeSearch() {
    const searchInput = document.getElementById('species-search');
    if (!searchInput) return;

    const speciesCards = document.querySelectorAll('.species-card');

    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase();

        speciesCards.forEach(card => {
            const name = card.querySelector('.species-name').textContent.toLowerCase();
            const family = card.querySelector('.species-family').textContent.toLowerCase();

            if (name.includes(query) || family.includes(query)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });
}

function setupMapEnhancements() {
    // Add custom map controls
    const mapContainers = document.querySelectorAll('[id^="map-"]');

    mapContainers.forEach(container => {
        // Add fullscreen button
        const fullscreenBtn = document.createElement('button');
        fullscreenBtn.className = 'map-fullscreen-btn';
        fullscreenBtn.innerHTML = '⛶';
        fullscreenBtn.onclick = () => toggleMapFullscreen(container);

        container.appendChild(fullscreenBtn);
    });
}

function animateCounters() {
    const counters = document.querySelectorAll('.stat-counter');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
            }
        });
    });

    counters.forEach(counter => observer.observe(counter));
}

function animateCounter(element) {
    const target = parseInt(element.getAttribute('data-target'));
    const duration = 2000;
    const increment = target / (duration / 16);
    let current = 0;

    const timer = setInterval(() => {
        current += increment;
        element.textContent = Math.floor(current).toLocaleString();

        if (current >= target) {
            element.textContent = target.toLocaleString();
            clearInterval(timer);
        }
    }, 16);
}
```

---

## 7. Testing & Deployment

### Local Testing

```bash
# Start local development server
cd exports/web
python -m http.server 8000

# Open in browser
open http://localhost:8000
```

### Testing Checklist

Test these features:

- [ ] **Home page loads** with statistics
- [ ] **Species pages** display correctly
- [ ] **Search functionality** filters results
- [ ] **Maps render** with data points
- [ ] **Navigation works** between pages
- [ ] **Mobile responsive** design
- [ ] **Loading performance** acceptable

### Performance Optimization

```bash
# Optimize images
cd templates/assets/files/
mogrify -resize 800x600 -quality 85 *.jpg
mogrify -resize 400x300 -quality 85 *_thumb.jpg

# Check file sizes
du -sh exports/web/*
```

### Deploy to GitHub Pages

```bash
# Initialize git repository
git init
git add .
git commit -m "Initial biodiversity portal"

# Create GitHub repository (replace with your repo)
git remote add origin https://github.com/username/caledonia-biodiversity.git
git push -u origin main

# Deploy to GitHub Pages
niamoto deploy github --repo https://github.com/username/caledonia-biodiversity.git
```

### Alternative Deployment Options

**Netlify:**
```bash
# Deploy to Netlify
niamoto deploy netlify --site-id your-site-id
```

**Manual deployment:**
```bash
# Upload to any web server
rsync -avz exports/web/ user@server:/var/www/html/
```

---

## Next Steps

Congratulations! You've created a complete biodiversity portal. Here are ways to enhance it further:

### Advanced Features
1. **Add more ecological indices** (beta diversity, endemism)
2. **Implement user comments** and observations
3. **Create data download** functionality
4. **Add multi-language support**
5. **Integrate with iNaturalist** or GBIF APIs

### Data Enhancements
1. **Add plant traits** (leaf size, wood density)
2. **Include environmental variables** (climate, soil)
3. **Incorporate temporal data** (phenology, growth rates)
4. **Add conservation status** information

### Technical Improvements
1. **Implement Progressive Web App** features
2. **Add offline functionality**
3. **Optimize for search engines** (SEO)
4. **Set up automated data updates**

### Community Features
1. **Create species identification** tools
2. **Add photo galleries** and media
3. **Implement citizen science** data collection
4. **Build educational content** and quizzes

## Resources

- [Export Guide](../guides/export-guide.md) - Advanced website customization
- [Widget Reference](../guides/widget-reference.md) - All available widgets
- [Deployment Guide](../guides/deployment.md) - Hosting options
- [Transform Chain Guide](../guides/transform_chain_guide.md) - Advanced data processing

## Support

If you encounter issues:
- Check the [troubleshooting guide](../troubleshooting/common-issues.md)
- Search [GitHub issues](https://github.com/niamoto/niamoto/issues)
- Ask questions in [Discussions](https://github.com/niamoto/niamoto/discussions)

**Example Repository**: [Complete tutorial source code](https://github.com/niamoto/biodiversity-tutorial)
