# CLI Commands Reference

This comprehensive reference covers all Niamoto command-line interface (CLI) commands, their options, and usage examples.

## Overview

The Niamoto CLI follows the data pipeline workflow:

```bash
niamoto init      # 1. Initialize project
niamoto import    # 2. Load data
niamoto transform # 3. Process and aggregate
niamoto export    # 4. Generate website
niamoto deploy    # 5. Publish online
```

## Global Options

All commands support these global options:

- `--help` - Show command help
- `--version` - Show Niamoto version
- `--verbose` - Enable detailed output
- `--quiet` - Suppress non-error output

## Command Reference

### `niamoto init`

Initialize or reset a Niamoto project environment.

```bash
niamoto init [OPTIONS]
```

**Options:**
- `--reset` - Reset existing environment

**Examples:**
```bash
# Initialize new project
niamoto init

# Reset existing project (WARNING: destroys data)
niamoto init --reset
```

**What it creates:**
```
project/
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

---

### `niamoto import`

Import data from various sources into the Niamoto database.

```bash
niamoto import [SUBCOMMAND] [OPTIONS]
```

#### Sub-commands

##### `niamoto import` (default)
Import all data sources according to `import.yml`:

```bash
niamoto import
```

##### `niamoto import taxonomy [CSVFILE]`
Import taxonomic hierarchy:

```bash
niamoto import taxonomy [OPTIONS] [CSVFILE]
```

**Options:**
- `--ranks RANKS` - Comma-separated hierarchy levels (e.g., "family,genus,species")
- `--source SOURCE` - Data source: `file` or `occurrence`
- `--with-api` / `--no-api` - Enable/disable API enrichment

**Examples:**
```bash
# Import from dedicated taxonomy file
niamoto import taxonomy imports/taxonomy.csv --ranks "family,genus,species"

# Extract taxonomy from occurrence data
niamoto import taxonomy --source occurrence --ranks "family,genus,species"

# Import with API enrichment
niamoto import taxonomy --with-api
```

##### `niamoto import occurrences [CSVFILE]`
Import species observations:

```bash
niamoto import occurrences [OPTIONS] [CSVFILE]
```

**Options:**
- `--taxon-id FIELD` - Column name for taxon identifier
- `--location-field FIELD` - Column name for location data

**Examples:**
```bash
niamoto import occurrences imports/occurrences.csv
niamoto import occurrences --taxon-id "species_id" --location-field "coordinates"
```

##### `niamoto import plots [FILE]`
Import study plots or forest stands:

```bash
niamoto import plots [OPTIONS] [FILE]
```

**Options:**
- `--id-field FIELD` - Plot identifier column
- `--location-field FIELD` - Location column
- `--locality-field FIELD` - Locality description column
- `--link-field FIELD` - Field for linking with occurrences
- `--occurrence-link-field FIELD` - Corresponding field in occurrences

**Examples:**
```bash
niamoto import plots imports/plots.csv
niamoto import plots --id-field "plot_id" --location-field "center_point"
```

##### `niamoto import shapes`
Import geographic shapes (administrative boundaries, forest types, etc.):

```bash
niamoto import shapes
```

Uses configuration from `import.yml` shapes section.

##### `niamoto import all`
Import all data types in sequence:

```bash
niamoto import all
```

---

### `niamoto transform`

Process and aggregate imported data according to transformation configurations.

```bash
niamoto transform [SUBCOMMAND] [OPTIONS]
```

#### Sub-commands

##### `niamoto transform` (default)
Run all transformations:

```bash
niamoto transform [OPTIONS]
```

**Options:**
- `--group GROUP` - Process specific group only (`taxon`, `plot`, `shape`)
- `--data FILE` - Use specific data file instead of database
- `--recreate-table` - Recreate output tables instead of updating
- `--verbose` - Show detailed processing information

**Examples:**
```bash
# Run all transformations
niamoto transform

# Process only taxon data
niamoto transform --group taxon

# Recreate all tables
niamoto transform --recreate-table

# Verbose output
niamoto transform --verbose
```

##### `niamoto transform run`
Explicit run command (same as default):

```bash
niamoto transform run [OPTIONS]
```

##### `niamoto transform list`
List available transformation configurations:

```bash
niamoto transform list
```

##### `niamoto transform check`
Validate transformation configuration without execution:

```bash
niamoto transform check
```

---

### `niamoto export`

Generate static website content from processed data.

```bash
niamoto export [SUBCOMMAND] [OPTIONS]
```

#### Sub-commands

##### `niamoto export` (default)
Generate all export content:

```bash
niamoto export [OPTIONS]
```

**Options:**
- `--target TARGET` - Export specific target only
- `--group GROUP` - Export specific group only (`taxon`, `plot`, `shape`)

**Examples:**
```bash
# Export everything
niamoto export

# Export only taxon pages
niamoto export --group taxon

# Export specific target
niamoto export --target "taxon_pages"
```

##### `niamoto export web_pages`
Generate static web pages:

```bash
niamoto export web_pages [OPTIONS]
```

---

### `niamoto deploy`

Deploy generated content to hosting platforms.

```bash
niamoto deploy [PLATFORM] [OPTIONS]
```

#### Platforms

##### `niamoto deploy github`
Deploy to GitHub Pages:

```bash
niamoto deploy github [OPTIONS]
```

**Options:**
- `--repo REPO` - GitHub repository URL (required)
- `--branch BRANCH` - Target branch (default: `gh-pages`)
- `--name NAME` - Git commit author name (default: `Niamoto Bot`)
- `--email EMAIL` - Git commit author email (default: `bot@niamoto.org`)

**Examples:**
```bash
# Deploy to GitHub Pages
niamoto deploy github --repo https://github.com/user/repo.git

# Deploy to custom branch
niamoto deploy github --repo https://github.com/user/repo.git --branch main

# Deploy with custom author
niamoto deploy github --repo https://github.com/user/repo.git \
  --name "John Doe" --email "john@example.com"
```

##### `niamoto deploy netlify`
Deploy to Netlify:

```bash
niamoto deploy netlify [OPTIONS]
```

**Options:**
- `--site-id SITE_ID` - Netlify site identifier (required)

**Examples:**
```bash
niamoto deploy netlify --site-id "12345678-abcd-efgh-ijkl-123456789012"
```

---

### `niamoto run`

Execute the complete Niamoto pipeline (import → transform → export).

```bash
niamoto run [OPTIONS]
```

**Options:**
- `--skip-import` - Skip data import phase
- `--skip-transform` - Skip transformation phase
- `--skip-export` - Skip export phase
- `--group GROUP` - Process specific group only
- `--target TARGET` - Export specific target only
- `--no-reset` - Skip automatic environment reset

**Examples:**
```bash
# Complete pipeline with reset
niamoto run

# Complete pipeline without reset
niamoto run --no-reset

# Skip import, run transform and export only
niamoto run --skip-import

# Process only taxon data
niamoto run --group taxon

# Transform and export to specific target
niamoto run --skip-import --target "taxon_pages"

# Export only
niamoto run --skip-import --skip-transform
```

---

### `niamoto stats`

Display database statistics and data summaries.

```bash
niamoto stats [OPTIONS]
```

**Options:**
- `--group GROUP` - Show statistics for specific group
- `--detailed` - Show detailed statistics including top items
- `--export FILE` - Export statistics to JSON or CSV file
- `--suggestions` - Show suggested data exploration queries

**Examples:**
```bash
# Basic statistics
niamoto stats

# Detailed statistics
niamoto stats --detailed

# Statistics for specific group
niamoto stats --group taxon

# Export statistics to file
niamoto stats --export stats.json
niamoto stats --export stats.csv

# Show query suggestions
niamoto stats --suggestions
```

**Sample Output:**
```
Niamoto Database Statistics
===========================

Taxonomy:
  Families: 45
  Genera: 156
  Species: 423

Occurrences:
  Total: 12,457
  Georeferenced: 12,234 (98.2%)

Plots:
  Total: 89
  With occurrences: 87 (97.8%)

Shapes:
  Provinces: 3
  Forest types: 8
  Protected areas: 15
```

---

### `niamoto plugins`

List and manage available Niamoto plugins.

```bash
niamoto plugins [OPTIONS]
```

**Options:**
- `--type TYPE` / `-t TYPE` - Filter by plugin type (`transformer`, `loader`, `exporter`, `widget`)
- `--format FORMAT` / `-f FORMAT` - Output format (`table`, `simple`)
- `--verbose` / `-v` - Show detailed plugin information

**Examples:**
```bash
# List all plugins
niamoto plugins

# List only transformer plugins
niamoto plugins --type transformer

# Simple format output
niamoto plugins --format simple

# Detailed information
niamoto plugins --verbose

# Combine filters
niamoto plugins --type widget --verbose
```

**Sample Output:**
```
Available Niamoto Plugins
=========================

Transformers:
  field_aggregator      - Aggregate fields from multiple sources
  species_richness      - Calculate species richness indices
  shannon_diversity     - Calculate Shannon diversity index
  top_ranking          - Generate top N rankings

Widgets:
  interactive_map      - Interactive maps with markers
  bar_plot            - Bar charts and histograms
  summary_stats       - Summary statistics displays
  table_view          - Tabular data presentations
```

---

## Configuration Files

Commands reference these configuration files:

- **`config/config.yml`** - General project settings
- **`config/import.yml`** - Data import configurations
- **`config/transform.yml`** - Transformation pipeline definitions
- **`config/export.yml`** - Website generation settings

## Exit Codes

- **0** - Success
- **1** - General error
- **2** - Configuration error
- **3** - Data validation error
- **4** - File system error

## Environment Variables

- **`NIAMOTO_HOME`** - Default project directory
- **`NIAMOTO_LOG_LEVEL`** - Logging level (DEBUG, INFO, WARNING, ERROR)
- **`NIAMOTO_CONFIG_DIR`** - Alternative configuration directory

## Common Workflows

### First-time Setup
```bash
# 1. Initialize project
niamoto init

# 2. Add your data files to imports/
cp your_data.csv imports/

# 3. Configure imports in config/import.yml
# 4. Run complete pipeline
niamoto run
```

### Iterative Development
```bash
# Make changes to transform.yml or export.yml
# Skip import to save time
niamoto run --skip-import
```

### Data Updates
```bash
# Update data files
# Run import and downstream processing
niamoto import
niamoto transform
niamoto export
```

### Debugging
```bash
# Check data statistics
niamoto stats --detailed

# Validate transformations without execution
niamoto transform check

# Run with verbose output
niamoto run --verbose
```

## Getting Help

- Use `--help` with any command for detailed options
- Check logs in `logs/niamoto.log` for error details
- Use `niamoto stats` to verify data after operations
- Run `niamoto transform check` to validate configurations

For more information, see:
- [Installation Guide](../getting-started/installation.md)
- [Quick Start Guide](../getting-started/quickstart.md)
- [Data Import Guide](../guides/data-import.md)
