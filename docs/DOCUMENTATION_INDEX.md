# Niamoto Documentation Index

## Overview
This document serves as the main index to track the status and progress of the Niamoto project documentation.

**IMPORTANT**: All documentation must be written in English.

- ✅ Completed
- 🚧 In progress
- ❌ To do
- 📝 To review/update

---

## 1. User Documentation

### 1.1 Getting Started Guide
- ✅ **Installation** (`getting-started/installation.md`) - **TO TRANSLATE**
  - System requirements
  - Installation via pip/uv
  - Initial configuration
  - Installation verification

- ✅ **Quick Start** (`getting-started/quickstart.md`) - **TO TRANSLATE**
  - First Niamoto project
  - Import test data
  - First transformation
  - Website generation

- ✅ **Core Concepts** (`getting-started/concepts.md`) - **TO TRANSLATE**
  - Pipeline architecture (Import → Transform → Export)
  - Plugin system
  - YAML configuration
  - Data structure

### 1.2 Practical Guides

#### Configuration
- ✅ **General Configuration** (`guides/configuration.md`)
  - YAML file structure
  - Basic configuration
  - Advanced configuration

#### Data Import
- ✅ **Data Import Guide** (`guides/data-import.md`)
  - Supported formats (CSV, GeoPackage, Shapefile)
  - Expected file structure
  - Data validation
  - Error handling

- ✅ **Data Preparation** (`guides/data-preparation.md`)
  - Occurrence format
  - Plot format
  - Shape format
  - Taxonomy format

#### Transformations
- ✅ **Transform Chain Guide** (`guides/transform_chain_guide.md`)
  - Reference system
  - Available functions
  - Complex examples

#### Plugin Development
- ✅ **Plugin Development Guide** (`guides/custom_plugin.md`)
  - Plugin types
  - Plugin structure
  - Testing and debugging

- ✅ **Plugin Reference** (`guides/plugin-reference.md`)
  - Complete plugin system reference
  - All plugin types (Loader, Transformer, Exporter, Widget)
  - Built-in plugins including detailed top_ranking plugin
  - Configuration schemas and examples
  - Performance optimization and troubleshooting

- ✅ **API Taxonomy Enricher** (`guides/api_taxonomy_enricher.md`)
  - API configuration
  - Response mapping
  - Authentication

#### Export and Publishing
- ✅ **Export Guide** (`guides/export-guide.md`)
  - Export configuration
  - Custom templates
  - Available widgets
  - Assets and static files

- ✅ **Deployment Guide** (`guides/deployment.md`)
  - Static hosting
  - Web server configuration
  - Performance optimization
  - Data updates

### 1.3 Tutorials
- ✅ **Tutorial 1: Creating a Biodiversity Site** (`tutorials/biodiversity-site.md`)
  - Import occurrence data
  - Calculate ecological indices
  - Map visualization
  - Publishing

- ✅ **Tutorial 2: Forest Plot Analysis** (`tutorials/forest-plots.md`)
  - Import plots
  - Biomass calculations
  - Spatial analysis
  - Dashboards

- ❌ **Tutorial 3: External Data Integration** (`tutorials/external-data.md`)
  - API usage
  - Taxonomic enrichment
  - GIS data joins

## 2. Reference Documentation

### 2.1 Architecture
- ✅ **Plugin System Overview** (`references/plugin-system-overview.md`)
  - General architecture
  - Plugin lifecycle
  - Registry and discovery

- ✅ **Database Schema** (`references/database-schema.md`)
  - SQLAlchemy models
  - Table relationships
  - Spatial extensions

- ❌ **Pipeline Architecture** (`references/pipeline-architecture.md`)
  - Data flow
  - Services and components
  - Error handling

### 2.2 API Reference
- 🚧 **API Documentation** (`api/modules.rst`)
  - Auto-generated Sphinx documentation
  - Modules and classes
  - Utility functions

### 2.3 CLI Reference
- ✅ **CLI Commands** (`references/cli-commands.md`)
  - `niamoto init`
  - `niamoto import`
  - `niamoto transform`
  - `niamoto export`
  - `niamoto run`
  - `niamoto stats`
  - `niamoto deploy`
  - `niamoto plugins`

### 2.4 Configuration
- ❌ **Complete YAML Reference** (`references/yaml-reference.md`)
  - Detailed schemas
  - All options
  - Validation

## 3. Advanced Guides

### 3.1 Development
- ❌ **Contributor Guide** (`development/contributing.md`)
  - Environment setup
  - Code standards
  - Testing and CI/CD
  - Contribution process

- ❌ **Widget Development Guide** (`development/widget-development.md`)
  - Widget architecture
  - Creating custom widgets
  - Plotly integration
  - Interactive widgets

### 3.2 Performance and Optimization
- ❌ **Optimization Guide** (`advanced/optimization.md`)
  - Large dataset handling
  - Query optimization
  - Caching and indexing
  - Parallelization

### 3.3 Integration
- ❌ **GIS Integration** (`advanced/gis-integration.md`)
  - QGIS
  - PostGIS
  - WMS/WFS services

## 4. Troubleshooting and FAQ

### 4.1 Troubleshooting
- ✅ **General Troubleshooting Guide** (`troubleshooting/common-issues.md`)
  - Import errors
  - Transformation issues
  - Export errors
  - Performance problems

### 4.2 FAQ
- ❌ **General FAQ** (`faq/general.md`)
  - Frequently asked questions
  - Use cases
  - Limitations

## 5. Examples and Resources

### 5.1 Examples
- 🚧 **Example Configurations** (`examples/`)
  - Minimal configuration
  - Complete configuration
  - Specific use cases

### 5.2 Resources
- ❌ **Glossary** (`resources/glossary.md`)
  - Technical terms
  - Ecological concepts
  - Acronyms

- ❌ **Useful Links** (`resources/links.md`)
  - External documentation
  - Complementary tools
  - Community

## 6. Migration and Changelog

- ❌ **Migration Guide** (`migration/migration-guide.md`)
  - Migration from v0.4.x
  - Breaking changes
  - Migration scripts

- ❌ **Changelog** (`CHANGELOG.md`)
  - Version history
  - New features
  - Bug fixes

---

## Documentation Priorities

### Phase 1 - Fundamentals (High Priority)
1. Installation and Quick Start
2. Data Import Guide
3. CLI Commands
4. Export Guide
5. Database Architecture

### Phase 2 - Advanced Usage (Medium Priority)
1. Practical tutorials
2. Deployment Guide
3. Widget Development
4. Optimization Guide
5. General FAQ

### Phase 3 - Complete Reference (Low Priority)
1. GIS Integration
2. Contributor Guide
3. Glossary
4. Migration Guide
5. External resources

---

## Documentation Standards

### Standards to Follow
- Use concrete examples based on niamoto-og
- Include screenshots when relevant
- Provide tested code snippets
- Maintain terminology consistency
- Write everything in English

### Guide Structure
1. **Introduction** - Guide objective
2. **Prerequisites** - What you need to know/have
3. **Steps** - Detailed instructions
4. **Examples** - Concrete cases
5. **Troubleshooting** - Common problems
6. **References** - Links to other resources
