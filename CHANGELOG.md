# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.5.4] - 2025-06-10

### Features

- Enhance Tailwind CSS configuration and implement image gallery features
- Major documentation overhaul and database aggregator plugin

### Refactoring

- Remove deprecated template compatibility test from IndexGenerator

## [v0.5.3] - 2025-06-07

### Features

- Enhance template handling and CLI options in Niamoto
- Add run and stats commands to Niamoto CLI
- Integrate Tailwind CSS for enhanced styling and remove legacy assets

### Refactoring

- Update asset paths and enhance static page layout

## [v0.5.2] - 2025-06-04

### Features

- Add bump2version to development dependencies
- Update dependencies and enhance project configuration
- Enhance widget tooltips and JSON parsing capabilities
- Refactor Plotly widgets to utilize shared utility functions for layout and rendering
- Enhance widget styling and structure for modern design
- Enhance InteractiveMapWidget with loading indicator and improved error handling
- Adjust positioning and rotation in ConcentricRingsWidget for improved label visibility
- Update ConcentricRingsWidget to use annotations for segment labels and percentages
- Add stacked area normalized transformation and concentric rings widget
- Enhance data transformation and radial gauge widget functionality
- Add gradient color generation to BarPlotWidget
- Enhance data transformation and bar plot widget functionality
- Enhance InteractiveMapWidget with TopoJSON support and optimize GeoJSON handling
- Enhance HtmlPageExporter with field selection and navigation data extraction

### Bug Fixes

- Add ORDER BY clause to SQL queries in HtmlPageExporter for consistent result ordering

### Refactoring

- Modernize export system with configurable IndexGeneratorPlugin and reorganize templates                                                                             │ │                                                                                                                                                                                                │ │   - Add new IndexGeneratorPlugin for configurable index page generation with filtering, custom display fields, and multiple views                                                              │ │   - Update HtmlPageExporter to integrate new plugin with fallback to traditional generation                                                                                                    │ │   - Add comprehensive configuration models for index generation (IndexGeneratorConfig, IndexGeneratorDisplayField, etc.)                                                                       │ │   - Reorganize template structure: move legacy templates to niamoto-legacy/ folder for backward compatibility                                                                                  │ │   - Modernize base templates with Tailwind CSS v4, improved responsive design, and configurable theming                                                                                        │ │   - Update template references to use simplified paths (group_detail.html instead of _layouts/group_detail_with_sidebar.html)

## [v0.5.1] - 2025-05-29

### Features

- Add auto-zoom capability and improve empty state handling in map and info grid widgets
- - improve test isolation and prevent config file creation during tests  - simplify nested field handling by using existing _get_field_from_table method -improve JSON field handling and use temporary directories for tests
- Enhance taxonomy import to handle family and genus level entries with taxon IDs
- Add PyPI token authentication support and release documentation

### Bug Fixes

- Correct quotation marks in LICENSE and update Plotly version in pyproject.toml for Scattermap support; enhance README with instructions for managing multiple Niamoto installations

### Refactoring

- Improve plugin test reliability by reloading modules and fixing imports
- Consolidate plugin system mocking with contextmanager in tests

### Chores

- Bump niamoto version from 0.4.2 to 0.5.0

## [v0.5.0] - 2025-05-28

### Features

- Add plugins command to list and inspect available plugins
- Add auto-color feature to bar plots and enhance hierarchical navigation tests
- Add auto-color generation for bar plots and simplify widget layout template
- Add map attribution toggle and improve progress tracking in HTML export
- Add hierarchical configuration support for plot imports
- Implement configurable top ranking plugin with direct, hierarchical and join modes
- Add hierarchical plot structure with nested set model support
- Improve hierarchical navigation with auto-scroll and enhanced styling
- Implement hierarchical navigation widget with Tailwind CSS styling
- Add PyPI token authentication support and release documentation
- Implement HTML page exporter with configurable widgets
- Remove config files and add config folder to gitignore

### Bug Fixes

- Fix interactive map widget for all groups

### Refactoring

- Improve plugin test structure with mock registry helper and better error handling
- Migrate from mapbox to standard plotly map types and remove token requirement
- Optimize hierarchical navigation by loading data from external JS files
- Centralize config models and restructure tests
- Improve error handling, validation, and tests

## [v0.4.2] - 2025-04-27

### Features

- Major core refactoring, taxonomy implementation, and testing overhaul
- Add support for creating named fields from labels in MultiColumnExtractor
- Add 'nb_species' to plot information and improve value handling in templates and data extraction, redising the shape_index page
- Update links in forests, plots, and trees templates to point to index pages
- Refactor data import process to use ImporterService and improve error handling
- Enhance GitHub deployment with configurable user identity and improved branch handling
- Update page generator and template for improved data handling and localization
- Add index page generation for taxons, plots, and shapes; update navigation links
- Add Endemia logo to footer and index templates
- Enhance node opening functionality with smooth scrolling effect
- Add API taxonomy enricher and enhance plugin documentation

### Bug Fixes

- Enhance info panel rendering by adding support for external data sources and improving value checks
- Improve error handling in page generation and refactor UICN translation function in taxon index template

### Documentation

- Reorganize documentation structure and improve formatting
- Add API documentation for plugin system

### Tests

- Enhance GitHub deployment tests with branch existence checks

## [v0.4.1] - 2025-03-03

### Features

- Enhance plugin architecture and add direct reference loader

### Bug Fixes

- Fix commited mock files

### Refactoring

- Improve plugin architecture with enhanced registry and tests
- Optimize test suite performance and fix environment test

## [v0.4.0] - 2025-02-27

### Features

- Add ecological transformer plugins for biodiversity analysis
- Update shape processor and add forest cover layer
- Ci: configure Codecov upload with token and add HTML coverage artifact

### Bug Fixes

- Fix test suite to handle exceptions properly in test environment
- Improve third-party plugin loading and configuration handling
- Use unique artifact name to avoid conflict in GitHub Actions
- Remove unused variable `simplified_utm`
- Create uv-managed virtual environment before installing dependencies

### Improvements

- Refactor!: introduce plugin-based architecture

### Refactoring

- Reorganize transformer plugins architecture and improve geospatial processing
- Reorganize plugin architecture and improve error handling
- Move source and field into params for consistency
- Improve code organization and naming consistency

### Style

- Fix formatting issues and pre-commit config

### Chores

- Simplify pre-commit config using hooks file
- Add pre-commit-hooks.yaml for local hooks

### Other Changes

- Ci: specify Codecov slug to resolve repository not found error
- Build(ci): run Ruff, Mypy, and Pytest within uv-managed environment

## [v0.3.11] - 2025-02-12

### Bug Fixes

- Update generate-requirements hook stage to pre-commit

### Refactoring

- Restructure project architecture and testing framework

## [v0.3.10] - 2025-01-23

### Features

- Add deployment tools

### Bug Fixes

- Add UTF-8 encoding for file operations
- Force UTF-8 encoding for API JSON files
- Force UTF-8 encoding for JavaScript files

### Updates

- Update conf.py

## [v0.3.9] - 2025-01-23

### Bug Fixes

- Force UTF-8 encoding for config files

## [v0.3.8] - 2025-01-23

### Bug Fixes

- Fix niamoto configuration overview

### Refactoring

- Update project metadata and version detection

## [v0.3.7] - 2025-01-23

### Features

- Ci(docs): add Read the Docs configuration
- Ci(docs): add Read the Docs configuration
- Ci(docs): add Read the Docs configuration

### Bug Fixes

- Resolve theme and static directory issues
- Switch to pip for RTD installation
- Correct poetry configuration in RTD yaml
- Update RTD configuration for poetry and Python 3.11

### Other Changes

- Remove old files

## [v0.3.6] - 2025-01-23

### Performance

- Optimize geometry storage with TopoJSON conversion

## [v0.3.5] - 2025-01-22

### Documentation

- Update README with new Niamoto CLI commands

## [v0.3.4] - 2025-01-22

### Improvements

- **feat(cli): overhaul commands, integrate configs, and improve help output**

## [v0.3.3] - 2025-01-14

### Bug Fixes

- Resolve Windows encoding issues in CLI output

## [v0.3.2] - 2025-01-14

### Updates

- Update python versio requirements

### Documentation

- Update CLI documentation with new command structure

## [v0.3.1] - 2025-01-14

### Features

- Move all js dependencies locally for offline static pages

### Refactoring

- Adopt multi-file config, update templates, reorganize CLI, and switch from DuckDB to SQLite

## [v0.3.0] - 2025-01-14

### Bug Fixes

- Improve resources page layout and code readability
- Update resources.html -- fix description

### Updates

- Update forests.html -- typos
- Update plots.html -- typos
- Update index.html -- Upcase acronyms
- Update methodology.html -- typos
- Update index.html -- Typos

### Chores

- Resolve merge conflicts

## [v0.2.6] - 2024-11-29

### Features

- Standardize widgets across all view types
- Updated navigation links in _nav.html and index.html, faq in methodology.html.html
- Update shape statistics calculations and template
- Add legacy forest statistics support

### Bug Fixes

- Improve navigation and data handling
- Fix _nav.html and resources.html

### Improvements

- Refactor `transform_geometry` method to guarantee output is in MultiPolygon format regardless of input geometry type. The method now: - Wraps `Polygon` geometries within a `MultiPolygon` to ensure consistency. - Iterates over individual geometries in `MultiPolygon` inputs, transforming each polygon separately. - Raises a `ValueError` for unsupported geometry types.

### Updates

- Update resources.html
- Update resources.html
- Update resources.html

### Refactoring

- Migrate from specific to configuration-based widget system

## [v0.2.5] - 2024-09-14

### Bug Fixes

- Improve navigation and data display

### Refactoring

- Improve shape rendering and update static pages

## [v0.2.4] - 2024-08-24

### Bug Fixes

- Increase HTTP buffer size for large commits

### Improvements

- Refactor spatial coordinate extraction and indexing methods to handle WKB, WKT, and POINT string formats

## [v0.2.3] - 2024-08-20

### Bug Fixes

- Ensure button container becomes fixed on scroll
- Make "access data" button always visible, reduce menu banner height, enable click on logos on the first page

## [v0.2.2] - 2024-08-07

### Features

- Improve chart configurations for Holdridge, Strates and phenology data
- Add unit tests for Config and ImporterService classes

### Bug Fixes

- Ensure correct sorting order for horizontal bar charts
- Improve chart displays for top species and substrate distribution
- Change subtitle of static site. Fixes #9

### Updates

- - Update dependencies - Applied ruff formatting corrections

## [v0.2.1] - 2024-07-21

### Features

- Enhance taxonomy tree with search and instant scroll
- Add extra_data to TaxonRef in API generator
- Add validation and handling for standard fields and ranks in taxonomy import
- Add static pages for tree, plot, and forest presentations

### Updates

- Update templates and structure in _base.html, index.html, and methodology.html

## [v0.2.0] - 2024-07-15

### Features

- Add functionality for dynamic plot ID extraction and handling
- Enhance map and chart display for shape pages, improve UI/UX
- Optimize ShapeStatsCalculator
- Implement global exception handling and logging
- Calculate elevation distribution and refactor layer processing for shape statistics calculation
- Update configuration and refactor shape import process
- Enhance PlotStatsCalculator to support optional source filtering
- Add dynamic link adjustments and depth variable for static page navigation; Refactor API generation
- Add presentation pages to Niamoto static site, redesign menu and footer
- Revamped configuration system, added plot and shape calculations, static plot page generation, and updated taxon pages.
- Add tests datas to gitignore

### Bug Fixes

- Fix deploy-static-content command Update version
- Fix command.py

### Improvements

- Enhance CLI with dynamic link adjustments, depth variable, and main command segregation
- Refactored database reset and import commands
- Refactor: Updated all code comments to Google Docstring style for improved readability and consistency. Documentation : Enhanced Sphinx documentation generation for better project understanding.
- Refactor: Overhaul code architecture for dynamic data handling and enhanced modularity

### Updates

- Update database system from SQLite to DuckDB
- Update version number in pyproject.toml
- Update readme import_data command signature

### Other Changes

- Remove unnecessary JSON parsing in static/js/index.js
- Initial commit
- Initial commit
