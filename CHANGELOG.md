# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.14.6] - 2026-04-12

### Bug Fixes

- Preserve collection tab navigation
- Tighten publish readiness flow
- Improve UI rendering smoothness
- Smooth import query refresh states

## [v0.14.5] - 2026-04-12

### Bug Fixes

- Improve Linux updater install flow
- Prevent duplicate update toasts
- Repair packaged desktop widgets and feedback

## [v0.14.4] - 2026-04-12

### Bug Fixes

- Enable Tauri devtools feature for desktop debug mode

### Other

- Update uv.lock

## [v0.14.3] - 2026-04-12

### Refactoring

- Compact desktop UI density

### Other

- Update Tauri lockfile version

## [v0.14.2] - 2026-04-12

### Features

- Unify desktop and app startup loaders
- Add desktop debug mode and feedback fallback

### Bug Fixes

- Clarify collection batch progress
- Clear stale widget suggestion caches after import
- Hide sidebar branding in desktop builds

### Refactoring

- Overhaul theme system — consolidate to 6 themes, unique fonts, offline fonts, font selector
- Unify collection transform state

### Other

- Desaturate herbier accent color — subtler stone tone

## [v0.14.1] - 2026-04-11

### Bug Fixes

- Force bash shell for Tauri build on Windows (restores Windows desktop binaries)

## [v0.14.0] - 2026-04-11

### Features

- Add multi-source enrichment workflow
- Redesign enrichment workspace
- Expand enrichment provider integrations
- Add Catalogue of Life rich enrichment
- Add shared name verifier for rich enrichers
- Add BHL references enrichment
- Add iNaturalist rich enrichment
- Add spatial enrichment v1
- Add logos for BHL and spatial providers
- Restore collection selector in CollectionPanel toolbar
- Replace collection select with custom dropdown
- Improve collections computation feedback

### Performance

- Lazy load collection previews

### Bug Fixes

- Resolve TypeScript errors across forms and views
- Ensure site configs include a home page
- Auto fit map previews to data
- Stabilize Tauri dev startup
- Reduce redundant frontend polling
- Harden widget previews and config inference
- Harden Tauri desktop runtime
- Resolve frontend context split regressions
- Harden desktop update and packaging flows
- Improve Windows desktop compatibility
- Disable Windows sidecar console for desktop builds
- Limit entity list to 15 items with max-height cap
- Polish enrichment workspace and preview

### Refactoring

- Reorganize sidebar navigation and header
- Stabilize frontend lint architecture
- Enforce frontend architecture boundaries
- Split site config hooks
- Lazy load Monaco editors
- Standardize frontend data queries
- Consolidate frontend theme state
- Consolidate enrichment configuration workflow
- Add ARIA region labels to enrichment panel columns
- Replace enrichment config tabs with accordion sections
- Replace enrichment 2-col grid with 3-col ResizablePanelGroup
- Extract enrichment render helpers to separate file
- Extract useEnrichmentState hook from EnrichmentTab

### Documentation

- Add enrichment tab UX consolidation design
- Add spatial enrichment v1 design
- Add iNaturalist rich enrichment design
- Add BHL references enrichment design
- Add GN verifier shared design
- Add Catalogue of Life rich enrichment design
- Add demo video production plan
- Add GN-assisted TAXREF rich design
- Add Tropicos rich enrichment design
- Add GBIF rich enrichment implementation plan
- Add GBIF rich enrichment design

### Other

- Fix desktop project reload fixture
- Compact enrichment workspace layout
- Update lockfiles for 0.13.2

## [v0.13.2] - 2026-04-09

### Bug Fixes

- Use native Linux titlebar chrome

## [v0.13.1] - 2026-04-09

### Features

- Surface enrichment progress on dashboard cards
- Add desktop update test harness

### Documentation

- Add desktop update harness design

### Other

- Drop macOS Intel matrix (macos-13 runner retired)
- Add macOS Intel and Linux arm64 to release builds
- Refresh uv.lock

## [v0.13.0] - 2026-04-08

### Features

- Improve publish workspace and desktop window state
- Refine panel navigation and transitions

### Bug Fixes

- Streamline widget detail preview and forms
- Correct language switcher paths in exports
- Harden desktop update relaunch flow

### Refactoring

- Polish publish preview copy and layout

### Documentation

- Add publish layout redesign spec

### Other

- Update Tauri lockfile for 0.12.4

## [v0.12.4] - 2026-04-08

### Bug Fixes

- Simplify theme picker cards
- Open preview in browser from desktop
- Stabilize GUI import and publishing workflows

### Other

- Bump Node to 22 for publish and binaries workflows

## [v0.12.3] - 2026-04-07

### Bug Fixes

- Harden GUI runtime diagnostics

## [v0.12.2] - 2026-04-07

### Bug Fixes

- Improve widget and transformer form handling
- Tighten desktop settings behavior
- Recover offline indicator on reconnect
- Align widget previews and layout config
- Hide legends in layout overview miniatures via Plotly relayout
- Improve preview engine resilience and health endpoint
- Improve Tauri startup, updater UX, and collections UI

### Refactoring

- Improve collection layout overview
- Compact source cards with consistent icon-only actions

### Style

- Compact widget list items in collection panel

### Other

- Refresh safe dependencies

## [v0.12.1] - 2026-04-05

### Bug Fixes

- Disable automatic RUSTSEC issue creation in dependency audit workflow
- Fix NIAMOTO_PYINSTALLER_MODE env var passing in Tauri CI build
- Allow desktop startup without pre-selected project (welcome mode)
- Add --reset-user-config flag to dev_desktop.sh
- Fix WelcomeScreen button text color

## [v0.12.0] - 2026-04-05

### Features

- Add in-app feedback system with Cloudflare Worker proxy
- Add html2canvas-pro screenshot and enriched debug context for feedback
- Add page transition and card entrance animations
- Add 8 new theme presets with extended style categories and fallback logic
- Add Tauri desktop release readiness
- Add collapsible widget list panel
- Merge Sources tab into Blocs as dialog overlay
- Add enriched collections overview with status cards
- Simplify API export UX for non-technical users

### Bug Fixes

- Address feedback form reset, cooldown enforcement, screenshot capture, and error sanitization
- Refine macOS desktop header alignment
- Restore dev hot reload workflow
- Wire theme polish review fixes
- Isolate scroll zones and harmonize tab headers
- Move collapse toggle to right, fix scrollbar and scroll issues
- Use i18n for relative time in collections overview
- Resolve tab mismatch, API settings access, and stale i18n keys

### Refactoring

- Migrate shell components to theme-aware utilities
- Redesign sources dashboard workflow
- Site module UX revamp with unified view and first-launch experience
- Merge header and tabs into single compact toolbar
- Move pipeline status from banner to breadcrumb
- Flatten collections sidebar with status dots
- Rename Groups module to Collections in GUI

### Style

- Darken sidebar across all 10 themes

## [v0.11.0] - 2026-03-30

### Features

- Extend pre-import impact checks with data compatibility analysis
- Add iOS and Android icon sets
- Replace logo with new N lettermark design

### Performance

- Speed up reference field suggestions

### Bug Fixes

- Enforce canonical home page export
- Improve desktop startup recovery
- Add unittest to PyInstaller hidden imports
- Polish publish workflow panels
- Stabilize publish previews and history
- Harden import and widget flows
- Harden import summary navigation
- Stabilize GUI startup context
- Preserve enrichment tab state in onboarding UI
- Make PyInstaller install portable in CI
- Restore binary build packaging

### Refactoring

- Redesign sources workspace
- Simplify publish workflow

### Documentation

- Add sources mission control design
- Add publish UI simplification design

## [v0.10.0] - 2026-03-28

### Features

- Add release automation infrastructure (CI workflows, Trusted Publishers, skill)
- Show live import progress events
- Stream auto-config analysis events
- Classify auxiliary stats sources separately
- Improve semantic relationship detection

### Performance

- Streamline transform and export pipelines (parallel execution)
- Add pytest-xdist parallel execution and mark slow benchmarks

### Bug Fixes

- Fix auto-configure job polling timeout for CI with xdist
- Fix CI uv venv cached virtualenv handling
- Use correct codecov-action v5 parameter name
- Skip benchmark tests when subset instance is unavailable
- Translate api enrichment UI
- Support reference-only spatial widgets
- Restore map suggestions for coordinate fields

### Refactoring

- Migrate geospatial I/O to pyogrio
- Close UI architecture review findings
- Finalize frontend feature architecture cleanup
- Simplify import flow and configuration review UX
- Streamline reference enrichment flow
- Extract smart auto-config decision layer
- Harden and centralize auto-config rules
- Move plotly-bundles to scripts/build/
- Clean up scripts directory, archive obsolete utilities
- Remove publish.sh, move scripts to dev/, update docs for CI-based PyPI publish

### Documentation

- Rewrite GUI documentation in English
- Refine repository guidance for coding agents
- Add ML model regeneration design

### Other

- Realign dependencies and raise minimum Python to 3.12
- Regenerate ML models for sklearn 1.8
- Pin pyinstaller and update desktop packaging
- Replace battle test phases with focused import suites

## [v0.9.0] - 2026-03-23

### Features

- Integrate ML acquisition wave and retraining results
- Replace synthetic anonymous holdout with diversified real columns
- Retrained models on enriched gold set (2525 cols)
- Add niamoto-nc to gold set, fix basal_area merge
- Expand alias registry — 13 new concepts, 76.6% concept (+5.3)
- Multi-dataset eval suite — 418 cols, 7 datasets, 71% concept
- Full instance evaluation with annotations — 57 cols, alias 25% → ML 46% concept
- Retrain all models with cross-rank reciprocity features — ProductScore 79.25 → 80.04 (+0.79)
- Add fusion surrogate autoresearch runner
- Add product-oriented evaluation and surrogate fusion loop
- Complete Phase 3 — profiles, affordances, patterns, anomalies
- Concept taxonomy, enriched data, coarsened training (2231 cols)
- Add gold set builder, training scripts, and CLI metric
- Add alias registry, ml_mode API, and evaluation harness

### Bug Fixes

- Correct silver.yml ground-truth annotations for afrique dataset
- Broaden pre-commit large-file exclusion to cover ml/models/*.joblib
- Raise ML confidence threshold to 0.6 to prevent false positives
- Clean up stale paths and packaging after ml/ centralization
- Restore ml autoresearch and packaging entrypoints
- Skip pre-commit hooks in autoresearch runner commits
- Replace codex with claude cli in surrogate runner
- Defer stack validation in surrogate runner, add scope filter
- Harden surrogate autoresearch prompt
- Defer stack baseline in surrogate runner
- Address gpt-5.4 review — ship models, fix hierarchy ID, anonymous inference, coordinates
- Address codex review — align identifier namespace, geometry affordances, drop rapidfuzz
- Address P1 review findings — remove dead code and unsafe deserialization

### Refactoring

- Centralize offline ML workspace under ml
- Simplify FK heuristic, delegate specific id types to alias registry
- Address P3 review findings
- Address P2 review findings
- Replace old pattern matching with alias registry, remove old MLColumnDetector

### Performance

- Batch fusion features in evaluate.py — ProductScore 14h → 42min
- Batch fusion feature extraction — training 5h → 15min, identical results

### Documentation

- Update CHANGELOG for v0.9.0 release
- Fix CodeRabbit review findings — paths and changelog accuracy
- Reorganize ml detection knowledge base
- Add pertinence audit plan and update autoresearch programmes
- Add standards-based dataset acquisition plan
- Rename NiamotoOfflineScore → GlobalScore, remove CSV mention
- Add info tooltips to dashboard hero stat cards
- Update error patterns with fix status after session improvements
- Add workflow schema and improvement timeline to dashboard
- Add training & evaluation guide — complete workflow documentation
- Update dashboard and experiment doc with V5 results (77.5% concept)
- Rewrite ML detection dashboard with current data and new sections
- Remove archived obsolete documentation
- Translate all ML detection docs to English, rewrite index, fix cross-references
- Archive obsolete files and reorganize documentation structure
- Log retraining, ProductScore 80.04, batch optimization 20x, instance eval
- Log session 2026-03-19 — runner fixes, cross-rank gain, plateau
- Add integration status report, fix restore_paths for untracked files
- Rewrite overview for botanist audience
- Update roadmap with enriched dataset results

### Chores

- Add ablation runner and tune header convergence
- Update uv.lock for 0.8.1

### Other Changes

- Autoresearch(values): macro-F1 0.3522 → 0.3527 (+0.05 pts)
- Autoresearch(values): macro-F1 0.3433 → 0.3522 (+0.89 pts)
- Autoresearch(values): macro-F1 0.3403 → 0.3433 (+0.30 pts)
- Autoresearch(values): macro-F1 0.3370 → 0.3403 (+0.33 pts)
- Autoresearch(values): macro-F1 0.2877 → 0.3068 (+1.91 pts)
- Autoresearch(values): macro-F1 0.3063 → 0.3257 (+1.9 pts)
- Autoresearch(values): macro-F1 0.3005 → 0.3063 (+0.6 pts)
- Autoresearch(values): macro-F1 0.2877 → 0.3005 (+1.3 pts)
- Autoresearch(header): macro-F1 0.5640 → 0.5641 (+0.01 pts)
- Autoresearch(header): macro-F1 0.5591 → 0.5640 (+0.49 pts)
- Autoresearch(header): macro-F1 0.5529 → 0.5591 (+0.62 pts)
- Autoresearch(header): macro-F1 0.5497 → 0.5529 (+0.32 pts)
- Autoresearch(header): macro-F1 0.5470 → 0.5497 (+0.27 pts)
- Autoresearch(header): macro-F1 0.5383 → 0.5470 (+0.87 pts)
- Autoresearch(header): macro-F1 0.5375 → 0.5383 (+0.08 pts)
- Autoresearch(header): macro-F1 0.5370 → 0.5375 (+0.05 pts)
- Autoresearch(header): macro-F1 0.5283 → 0.5370 (+0.87 pts)
- Autoresearch(header): macro-F1 0.4937 → 0.5283 (+3.46 pts)
- Autoresearch(header): macro-F1 0.4931 → 0.4937 (+0.06 pts)
- Autoresearch(header): macro-F1 0.4864 → 0.4931 (+0.67 pts)
- Autoresearch(header): macro-F1 0.4763 → 0.4864 (+1.01 pts)
- Autoresearch(header): macro-F1 0.4455 → 0.4763 (+3.08 pts)
- Autoresearch(header): macro-F1 0.3658 → 0.4455 (+7.97 pts)

## [v0.8.1] - 2026-03-15

### Bug Fixes

- Add monaco-editor types as dev dependency

### Refactoring

- Declarative registries, POST inline, smart entity selection (#55)

## [v0.8.0] - 2026-03-14

### Features

- Add multi-platform deployment from GUI
- Add sidebar layout to Data, Groups and Publish modules
- Add pipeline status hooks, home page and staleness banner
- Simplify navigation, fix multi-lang export and map rendering
- Refactor footer as category-based sections with internal/external links
- Create niamoto-subset instance from niamoto-nc for fast testing
- Centre de notifications connecté aux jobs du pipeline
- Bouton transform dans GroupPanel + checkbox composite dans Build
- Ajouter group_by, endpoints active/last-run et job composite transform→export
- Ajouter JobFileStore + fix os.chdir() thread-unsafe
- Add shimmer loading skeleton with widget-type icons
- Add Plotly bundle splitting (core 1.3MB, maps 2.2MB)
- Migrate all preview components to unified engine and delete legacy queue
- Wire preview engine invalidation and migrate recipes (Phase 4)
- Add usePreviewFrame hook and shared preview components (Phase 3)
- Add unified preview engine (Phase 1)
- Add combined widget analysis previews
- Centralize table resolver and transform config models
- Full offline support for desktop application
- Enrich raster_stats and land_use with layer-select UI hints
- Add geographic layers API and LayerSelectField widget
- Add Phase 2.1 form widgets for transform configuration
- Add KeyValuePairsField and TagsField widgets with auto-detection
- Enrich Pydantic models with UI hints and fix Select.Item bug
- Use native macOS titlebar overlay instead of custom traffic lights
- Add multilingual support and i18n infrastructure
- Add MapRenderer service and fix layout preview issues
- Refactor index config with side panel editor and reusable preview
- Improve site preview navigation and widget suggestions
- Complete i18n migration for all UI components
- Enhance site builder with improved navigation and group preview
- Add x_label and y_label quick edit fields for axis customization
- Implement Option A hybrid layout with improved widget modal
- Add multi-field pattern detection for combined widgets
- Add drag-and-drop widget reordering and layout.order support
- Add specialized parameter editors and preview service
- Add unified widget recipe editor with wizard interface
- Enhance relation detection and support for class_object_field_aggregator
- Add index generator configuration and widget management
- Enhance desktop app with welcome screen, site config UI and layout editor
- Add advanced theme system with typography, shapes, and effects
- Replace bootstrap with intelligent widget suggestion system
- Integrate Tauri for desktop application support

### Bug Fixes

- Remove obsolete deploy CLI tests and fix SyntaxWarning
- Comprehensive i18n audit — replace all French fallbacks with English, fix namespace issues and add missing translation keys
- Add fixed seed to ML detector tests for cross-version reproducibility
- Remove duplicate legacy preview route that shadowed templates router
- Address PR #54 review comments (CI, build scripts, docs)
- Datetime serialization in job store and obsolete preview mount test
- Prevent duplicate toasts and wrong group name on transform completion
- Supprimer read_only=True des connexions DuckDB API
- Codex review #3 — conditional polling, strict types, i18n timeAgo
- Corrections revue Codex #2 — sécurité, i18n, robustesse
- Extraire les chaînes FR hardcodées vers i18n (sources + publish)
- Corrections revue Codex — filtrage job_type, progression monotone, polling reprise
- Résoudre le montage preview et les chemins relatifs export
- Resolve full export pipeline for taxons, plots, and shapes
- Ajouter skipif pour les tests dépendant des instances locales
- Corriger la génération de config des suggestions et les tests cassés
- Add html.escape() to all widget error messages and data interpolations
- Add padding to info_grid widget container
- Refresh button now bypasses browser cache and shows shimmer
- Categorical_distribution type coercion for YAML string categories
- Rewrite _render_entity_map and pass is_map=True to Plotly
- Series_extractor bar_plot field name mismatch and missing param forwarding
- Stabilize widget previews and shape scalar gauges
- Correct widget previews for entity and class_object sources
- Add minimal Tailwind classes and CSS chevron for navigation preview
- Remove CDN dependencies (Tailwind, Font Awesome) from previews
- Force iframe preview refresh after widget reorder
- Fix drag & drop snap-back and refresh layout after reorder
- Make request optional in preview_template for direct call from layout.py
- Exclude FastAPI-injected request parameter from signature test
- Fix TypeScript errors and preview refresh
- Finalize analysis transformer output and formatting
- Stabilize config scaffolding and import config access
- Formatting and remaining test updates for v1 config contract
- Handle inline content_markdown in static pages
- Update test assertions and mocks for recent changes
- Ensure gauge widget is proposed for all numeric columns
- Improve relation reference_key detection
- Handle identical values in distribution preview and fix binary counter
- Improve widget suggestions and fix geometry serialization errors
- Use working directory context for Config in GUI API
- Update tests for absolute database path and refine numeric/categorical detection

### Updates

- Ci: upgrade GitHub Actions to Node.js 24 compatible versions

### Refactoring

- Migrate deployers from services to plugins, add GUI deploy API with health check and unpublish
- Flatten sidebar navigation and remove Labs/Tools sections
- Delegate to TransformerService with shared code path
- Intégrer JobFileStore dans les routers transform et export
- Finalize preview engine — dead code removal, security hardening, ETag optimization
- Consolidate HTML wrappers, remove dead Plotly bundle, fix review findings
- Extract preview_utils and decouple engine from PreviewService
- Migrate hooks to React Query + debounce
- Optimize widget preview system performance
- Migrate npm to pnpm and update build scripts
- Update EntityKind types, config generator and components
- Harden routers, normalize YAML None values, migrate to table resolver
- Rename Index tab to Liste for better UX
- Reorganize components directory structure
- Reorganize routes and consolidate API structure
- Cleanup legacy code and reorganize components
- Separate data loading from transformation logic

### Documentation

- Alléger le plan transform trigger + corrections revue Codex
- Ajouter les plans shapes config et transform trigger + jobs robustes
- Add preview architecture, API reference, and widget thumbnail guide
- Mark all acceptance criteria as validated
- Add architecture docs, v1 release plan and config contract
- Rewrite plugin dev guide with modern Pydantic patterns + update plan
- Add Phase 3.3 user documentation for transform widgets
- Add Phase 3.2 config simplification analysis (6 axes identified)
- Update plan - mark Phase 2.5 layers as completed

### Tests

- Add preview engine tests and update layout tests
- Add e2e, data explorer, stats and service tests
- Add Phase 3.1 end-to-end tests for GUI config generation (30 tests)
- Add Phase 1.3 transform config validation tests (56 tests)

### Style

- Replace Rocket icon with Send and Menu with PanelLeft
- Redesign command palette with grouped layout and descriptions

### Chores

- Sync tauri version to 0.7.5 and add it to bumpversion config
- Update npm dependencies to fix security vulnerabilities

## [v0.7.5] - 2025-11-18

### Features

- Add PyInstaller support and resource cascade system

### Bug Fixes

- Correct PyInstaller settings to prevent numpy and DLL corruption
- Replace Unicode arrows and bullets with ASCII, fix run command description
- Replace all Unicode emojis with cross-platform emoji() function
- Replace Unicode characters with ASCII-only for Windows compatibility
- Replace Unicode characters with ASCII in spec file
- Commit package-lock.json for reproducible builds
- Actually check directory emptiness before blocking init
- Improve init command path handling and error messages
- Restore working directory after init command
- Handle Windows paths in project name extraction
- Correct project path derivation in plugins command
- Remove hard dependency on uv tool
- Flatten Windows zip structure for easier extraction

### Performance

- Reduce binary size by 43% through dependency optimization

### Documentation

- Add comprehensive git tag management commands

### Other Changes

- Ci: remove macOS Intel build to save GitHub Actions quota

## [v0.7.4-test] - 2025-11-15

### Bug Fixes

- Correction de 13 bugs dans les plugins transformers et l'API smart_config
- Preserve large integer ID precision and load group_by dynamically

### Updates

- Build: upgrade minimum Python version from 3.10 to 3.11

### Tests

- Amélioration de la couverture de tests de 60% à 68%
- Fix test assertions and add auxiliary file cleanup

### Chores

- Move Claude Code config files to gitignore

## [v0.7.4] - 2025-11-14

### Features

- Remove hardcoded table references in showcase metrics
- Remove hardcoded entity references in data explorer and showcase
- Complete EntityRegistry v2 migration for stats and entities
- Add development tooling with instance context management
- Add intelligent onboarding wizard with auto-configuration
- Add transform-source-select widget with group context
- Migrate 11 transformers to entity-select widget
- Add dynamic entity-select widget and update config templates
- Migrate aggregation transformers to EntityRegistry
- Migrate 3 distribution transformers to EntityRegistry
- Migrate remaining 3 class_objects transformers to EntityRegistry
- Migrate categories_extractor and series_extractor class_objects transformers to EntityRegistry
- Migrate loaders to EntityRegistry and create refactoring tracking system
- Add environment variable substitution and plugin config validation
- Add partners section to TeamSection component with logos and descriptions
- Add PerspectivesSection component and integrate into showcase page fix: update Rich version in StackTechSection fix: include 'perspectives' in showcase store sections
- Implement pipeline management with tabs and shared state
- Add Cloudflare deployment functionality and integrate into the GUI
- Add API demo component and integrate into showcase page
- Add exports structure API endpoint and update UI components for directory visualization
- Add YAML configuration editor and backup functionality
- Update API documentation page and navigation structure
- Add Plotly.js and react-plotly.js for data visualization
- Update GUI documentation and improve language switcher component
- Implement enrichment preview functionality in Data Explorer
- Add package.json to repo for Docker builds
- Enhance showcase components with improved YAML configuration display and updated use case statistics
- Implement interactive showcase pages with real data pipeline integration
- Expose plugin param schemas for dynamic gui config
- Implement unified pipeline editor with ReactFlow
- Improve Transform interface and add pipeline specifications
- Implement hierarchical navigation and transform pipeline interface
- Add SQLite performance optimizations
- Update CLAUDE.md for development guidelines and commands; update permissions in settings.local.json; refine error handling in bar_plot and donut_chart widgets

### Bug Fixes

- Preserve large integer IDs precision in index generation
- Fix pytest collection and test database artifacts
- Update instance initialization to EntityRegistry v2 format
- Improve fallback logic for displaying configuration path or file in ImportDemo component
- Update file count logic to handle edge cases and reorder sections in showcase store
- Resolve CI/CD build issues with GUI dist directory
- Restore .gitkeep file for CI/CD builds

### Improvements

- Refactor code structure for improved readability and maintainability

### Refactoring

- Prepare EntityRegistry v2 migration

### Documentation

- Reorganize and fix Sphinx documentation structure
- Reorganize documentation structure and add ML detection system

### Chores

- Upgrade all dependencies to latest versions
- Remove old pipeline editor and dead import code

## [v0.7.3] - 2025-08-06

### Features

- Enhance ShapeProcessor to support group_id configuration
- Update documentation and configuration for multiple data sources
- Enhance StatsLoader to support dynamic key field lookup

### Bug Fixes

- Update Tropicos API name in enrichment configuration
- Improve API enrichment field translations
- Simplify publish script to handle GUI packaging properly
- Ensure GUI dist directory exists for CI/CD builds
- Resolve CI/CD build issue with GUI dist directory
- Correct caching logic in api_taxonomy_enricher

## [v0.7.2] - 2025-08-06

### Features

- Enhance API enrichment with chained requests and improve GUI packaging

## [v0.7.1] - 2025-08-05

### Features

- Add support for binomial naming in TaxonomyImporter
- Enhance taxonomy name generation logic in TaxonomyImporter

### Bug Fixes

- Refine entity existence check in PlotImporter

### Chores

- Update CHANGELOG for version 0.7.0 release

## [v0.7.0] - 2025-07-31

### Features

- Introduce Tropicos enricher plugin for enhanced taxonomy data enrichment
- Enhance ShapeImporter and StatsLoader for improved feature handling and ID generation
- Introduce comprehensive GUI enhancements and CLI improvements
- Update CLI help message and initialization options
- Enhance interactive map functionality with Mapbox support
- Implement hierarchical shape support and enhancements
- Implement new Shape ID generation format in documentation and code
- Enhance geospatial extraction and interactive map functionality
- Enhance FieldAggregator to support JSON field access
- Add project initialization and metadata enhancements
- Integrate i18n support across components and add language switcher
- Enhance shape import functionality and configuration management
- Introduce faceted spinner and enhance circular progress component
- Enhance import process with progress tracking and new UI components
- Add table fields retrieval and enhance import field handling
- Enhance PlotImporter and import functionality
- Enhance ShapeProcessor to support group_id configuration
- Update documentation and configuration for multiple data sources
- Enhance import functionality with progress tracking and hierarchy configuration
- Implement new import-v2 interface with enhanced functionality
- Introduce taxonomy hierarchy configuration and streamline import process
- Integrate httpx for enhanced API interactions and improve import functionality
- Enhance import wizard and API integration for improved data handling
- Add React-based GUI configuration interface for Niamoto

### Bug Fixes

- Update API URL and enhance drag-and-drop functionality in import wizard
- Prevent rendering of empty widgets in WidgetPlugin and RadialGaugeWidget
- Improve zoom level calculation in InteractiveMapWidget
- Update parent linking logic in TaxonomyImporter
- Update drag-and-drop cursor styles and hierarchy level descriptions
- Correct hierarchy level description in PlotHierarchyConfig component
- Standardize field naming in advanced options for import functionality

### Refactoring

- Improve geospatial data handling in GeospatialExtractor
- Unify source configuration structure across documentation and code
- Remove taxon estimation logic from OccurrencesStep and SummaryStep
- Streamline import wizard and remove deprecated components

## [v0.6.2] - 2025-07-15

### Features

- Enhance ShapeProcessor to support group_id configuration
- Update documentation and configuration for multiple data sources
- Enhance StatsLoader to support dynamic key field lookup

### Updates

- Update uv.lock to include upload times for package distributions and bump revision to 2

## [v0.6.1] - 2025-07-09

### Features

- Add support for multiple data sources in transformations
- Enhance export command output and improve plot importer functionality
- Enhance console output utilities

### Refactoring

- Standardize success and error indicators in console output
- Clean up imports and enhance progress tracking

### Chores

- Update shape import configuration and enhance testing

## [v0.6.0] - 2025-06-13

### Features

- Implement JSON API exporter and enhance data access utilities

## [v0.5.7] - 2025-06-12

### Features

- Update version to 0.5.6, enhance installation and quickstart documentation, and refine configuration handling in tests. Added templates directory to documentation and improved export configuration assertions in tests.

### Refactoring

- Simplify value formatting logic in RadialGaugeWidget

## [v0.5.6] - 2025-06-10

### Features

- Enhance configuration file handling and directory setup

## [v0.5.5] - 2025-06-10

### Features

- Add screenshots to README and enhance data availability checks in widgets

### Bug Fixes

- Update bar plot widget to handle cases with no meaningful y-axis data

### Updates

- Update CHANGELOG.md

### Chores

- Update pyproject.toml for wheel packaging and modify README for asset links

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
