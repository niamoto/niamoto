# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.20.0] - 2026-06-02

### Features

- Unify automatic widget recommendations (#172)
- Streamline import cockpit workflow
- Guide users before import uploads
- Show collection computation progress in sidebar
- Allow custom API export data source
- Streamline collection data outputs
- Refine collection data outputs
- Complete standard profile workflows
- Add standardized export profiles
- Improve API export auto-configuration
- Support auxiliary source review editing
- Add data source inspection tabs (#142)
- Improve index field selection
- Add workflow history details
- Add workflow history view
- Add list performance diagnostics
- Add workflow commands to palette
- Remember desktop view preferences
- Remember desktop route per project
- Improve site builder authoring workflow
- Persist site workbench preview state
- Add native desktop menu shell
- Refine desktop shell and export toggles
- Add source enrichment reset mode
- Add enrichment panel workflow
- Add script to revert Tauri updater manifest to a previous version
- Add AST-based plugin manifest extractor
- Redesign pipeline overview (#125)
- Migrate from ReadTheDocs to GitHub Pages
- Add landing teaser with Niamoto product mocks
- Add Niamoto marketing site plan with partner assets
- Improve index generator configuration workflow
- Build remotion product demo
- Wire Intro/Outro scenes and add TransitionLabels
- Add Acts 4-6 (Collections, Site Builder, Publish)
- Add UI components, cursor system, and Acts 1-3
- Bootstrap Remotion demo video project
- Unify desktop and app startup loaders
- Add desktop debug mode and feedback fallback
- Improve collections computation feedback
- Replace collection select with custom dropdown
- Restore collection selector in CollectionPanel toolbar
- Add logos for BHL and spatial providers
- Add spatial enrichment v1
- Add inaturalist rich enrichment
- Add BHL references enrichment
- Add shared name verifier for rich enrichers
- Add catalogue of life rich enrichment
- Expand enrichment provider integrations
- Redesign enrichment workspace
- Add multi-source enrichment workflow
- Surface enrichment progress on dashboard cards
- Add desktop update test harness
- Improve publish workspace and desktop window state
- Refine panel navigation and transitions
- Html2canvas-pro screenshot + enriched debug context
- Add in-app feedback system with CF Worker proxy
- Add page transition and card entrance animations
- Add 8 new theme presets
- Extend style categories and add theme fallback logic
- Tauri desktop release readiness (#65)
- Add collapsible widget list panel
- Merge Sources tab into Blocs as dialog overlay
- Add enriched collections overview with status cards
- Simplify API export UX for non-technical users (#61)
- Extend pre-import impact checks (#60)
- Add iOS and Android icon sets
- Replace logo with new N lettermark design
- Add release automation infrastructure (#58)
- Show live import progress events
- Stream auto-config analysis events
- Classify auxiliary stats sources separately
- Improve semantic relationship detection
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
- Add PyInstaller support and resource cascade system
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
- Enhance API enrichment with chained requests and improve GUI packaging
- Add support for binomial naming in TaxonomyImporter
- Enhance taxonomy name generation logic in TaxonomyImporter
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
- Enhance ShapeProcessor to support group_id configuration
- Update documentation and configuration for multiple data sources
- Enhance StatsLoader to support dynamic key field lookup
- Enhance import functionality with progress tracking and hierarchy configuration
- Add support for multiple data sources in transformations
- Implement new import-v2 interface with enhanced functionality
- Introduce taxonomy hierarchy configuration and streamline import process
- Integrate httpx for enhanced API interactions and improve import functionality
- Enhance import wizard and API integration for improved data handling
- Add React-based GUI configuration interface for Niamoto
- Enhance export command output and improve plot importer functionality
- Enhance console output utilities
- Implement JSON API exporter and enhance data access utilities
- Enhance configuration file handling and directory setup
- Add screenshots to README and enhance data availability checks in widgets
- Enhance Tailwind CSS configuration and implement image gallery features
- Major documentation overhaul and database aggregator plugin
- Enhance template handling and CLI options in Niamoto
- Add run and stats commands to Niamoto CLI
- Integrate Tailwind CSS for enhanced styling and remove legacy assets
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
- Add auto-zoom capability and improve empty state handling in map and info grid widgets
- - improve test isolation and prevent config file creation during tests  - simplify nested field handling by using existing _get_field_from_table method -improve JSON field handling and use temporary directories for tests
- Enhance taxonomy import to handle family and genus level entries with taxon IDs
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
- Add PyPI token authentication support and release documentation
- Implement HTML page exporter with configurable widgets
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
- Enhance plugin architecture and add direct reference loader

### Performance

- Speed up import auto-configuration
- Optimize data explorer table rendering
- Lazy load collection previews
- Speed up reference field suggestions
- Streamline transform and export pipelines (#59)
- Add pytest-xdist parallel execution and mark slow benchmarks
- Batch fusion features in evaluate.py — ProductScore 14h → 42min
- Batch fusion feature extraction — training 5h → 15min, identical results
- Reduce binary size by 43% through dependency optimization

### Bug Fixes

- Keep uv run checks frozen
- Preserve uv lock resolution options in releases
- Narrow import status badge variants
- Preserve export cancellation fallback
- Address PR review blockers
- Harden publish and import dashboard flows
- Gate desktop releases on sidecar startup
- Polish dark mode branding and sidebar state
- Tighten import file handling
- Harden import cockpit file matching
- Preserve duckdb resolution cutoff
- Stabilize desktop API auth client test
- Keep missing DuckDB read-only connections lazy
- Stabilize DuckDB access in GUI previews
- Eliminate pytest warnings
- Stabilize plugin loading and test cleanup
- Resolve high clawpatch findings
- Resolve clawpatch review findings
- Resolve clawpatch high findings
- Resolve clawpatch findings
- Close remaining clawpatch low findings
- Stabilize preview and overlay regressions
- Stabilize collection and index workflows
- Stabilize API route regressions
- Authorize desktop API requests
- Preserve profiler total row count
- Infer legacy top ranking mode
- Resolve spatial preview geometry
- Preserve group index generator fields
- Discover recipe widget schemas
- Align import v2 validation with model
- Validate relationship CSV inputs
- Escape BibTeX export values
- Offload enrichment preview loading
- Bound index suggestion record loads
- Enforce query result limits
- Preserve duplicate transform widgets
- Fail transform jobs for unknown groups
- Count hierarchical representatives from relation
- Preserve registry plugin type
- Translate standard compatibility errors
- Translate enrichment preview errors
- Mark publication stale after site config changes
- Offload smart auto configure
- Analyze spatial shape uploads
- Drop registered import tables
- Scope combined suggestions sources
- Translate enrichment config errors
- Honor configured spatial geometry fields
- Bound csv import uploads
- Hide non-transform job status
- Parse underscored entity map references
- Bound time series presence percentages
- Resolve repository ml models
- Aggregate duplicate class object rows
- Validate outlier export thresholds
- Reload desktop projects through native bridge
- Bound retained import jobs
- Validate stats validation rules
- Bound data explorer query limits
- Expose cli export jobs
- Validate dataset config updates
- Respect cleared preview fields
- Align import v2 schema contract
- Enforce export widget identifiers
- Load all recipe widget plugins
- Cancel export jobs
- Validate canonical transform lists
- Stream site file uploads
- Align index generator group lookup
- Read root transform source configs
- Limit feedback screenshot uploads
- Prefer explicit spatial coordinate columns
- Preserve import status setup errors
- Validate config updates before writing
- Bind transformer package exports
- Securely open exported files
- Write validation rules atomically
- Avoid leaking config file paths
- Validate backup config names
- Parameterize archive preview validation query
- Escape Rich markup in stats output
- Escape Rich markup in plugin listing
- Escape Rich markup in direct CLI errors
- Escape Rich markup in progress output
- Escape Rich markup in CLI output
- Block unsafe outbound test redirects
- Write source transform config atomically
- Use read-only table preview connection
- Open table preview database read-only
- Require auth for credential mutations
- Serialize API export target updates
- Escape formulas in outlier CSV exports
- Validate API export target paths
- Require auth for validation rule updates
- Serialize config scaffolding updates
- Serialize source config updates
- Share transform config write lock
- Serialize transform widget updates
- Avoid orphan recipe transforms
- Serialize collection metadata updates
- Write data content atomically
- Restrict data content writes
- Serve uploaded SVGs as attachments
- Create valid web export targets
- Validate widget dependency scripts
- Open template lookups read-only
- Scope recipe widget deletion
- Require desktop auth for import mutations
- Write bulk import config atomically
- Serialize index generator updates
- Constrain backup restore paths
- Stabilize pipeline history import snapshot
- Write config updates atomically
- Serialize reference config updates
- Quote Darwin Core group queries
- Merge enrichment updates with current data
- Validate Darwin Core query identifiers
- Resolve entity tables before querying
- Restrict derived column formulas
- Restrict custom formula evaluation
- Resolve archived test fixture paths
- Hide absolute export list paths
- Guard widget suggestions without project
- Preserve group index preview footers
- Quote dataset count tables
- Accept uppercase upload extensions
- Hide combined suggestion internals
- Hide backup filesystem paths
- Avoid GUI backup collisions
- Record JSON export metadata duration
- Register plugins with correct arguments
- Preserve benchmark logs
- Escape class object CSV paths
- Bound GBIF request timeouts
- Open entity reads read-only
- Limit BibTeX upload size
- Constrain saved source paths
- Restrict served project files
- Tolerate empty BibTeX fields
- Restrict API test targets
- Constrain site file listing paths
- Validate recipe plugin params
- Preserve static page extensions
- Limit extracted upload archives
- Preserve uploads on failed overwrite
- Preserve API export group settings
- Preserve unresolved widgets on reorder
- Return all recipe source columns
- Ignore invalid WKT in shape distribution
- Preserve deploy validation extras
- Validate dataset config shape
- Count dangling taxonomy orphans
- Paginate valid WKT map features
- Constrain configured source paths
- Escape render widget messages
- Restrict site file content access
- Stream terminal auto config events
- Reject concurrent import all jobs
- Validate current import config schema
- Preserve zero medians in validation stats
- Include max values in validation histograms
- Redact listed import job tracebacks
- Redact import job tracebacks
- Guard debug health error route
- Tolerate invalid WKT in coverage analysis
- Reject duplicate normalized CSV headers
- Preserve layout widget index identity
- Validate plugin compatibility requests
- Include datasets for reference-only recipes
- Reject colliding source uploads
- Limit source upload memory use
- Avoid backup filename collisions
- Preserve upper edge in smart bins
- Keep top ranking suggestion counts positive
- Resolve humboldt collection backing sources
- Filter horizontal bar zeros by value axis
- Handle zero-width contextual gauge ranges
- Render dictionary line plots with multiple y axes
- Constrain exporter output paths
- Sanitize leaflet map rendering
- Use advanced transform chain references
- Default static page context to none
- Escape widget container metadata
- Validate archived shapefile zip extraction
- Resolve archived debug script roots
- Run archived test helper from repo root
- Resolve dev script repository root
- Clean untracked autoresearch directories
- Preserve fusion surrogate cache on rebuild failure
- Handle help sections without index pages
- Validate template config before export update
- Surface geospatial source failures
- Honor geospatial registry id fields
- Copy semantic affordance sets
- Calculate edge density per area unit
- Align class object series by axis
- Round scalar gauge maximums upward
- Handle deployer unpublish network errors
- Reject disjoint relationship samples
- Project vector overlay feature areas
- Honor raster nodata metadata
- Convert table view data before empty check
- Mark uvloop as non-windows dependency
- Ignore invalid summary stat filters
- Convert summary stats data before empty check
- Handle plot import removal
- Resolve query db paths from repo root
- Use configured spatial preview dataset
- Preserve DuckDB mode during selects
- Substitute plain config env vars
- Expand configured database paths
- Tolerate partial UI builds
- Fail plugin manifest on syntax errors
- Validate aggregation SQL identifiers
- Sanitize markdown preview html
- Validate import v2 saves
- Quote entity route identifiers
- Constrain site uploads to files
- Constrain preview source paths
- Require desktop auth for project reload
- Block private URL health checks
- Use typed ecological transformer params
- Preserve nojekyll in GitHub API deploys
- Restrict file browser to project root
- Keep desktop auth token private
- Prevent docs help output deletion
- Avoid export cwd lock deadlock
- Preserve existing zip upload components
- Skip empty product holdouts
- Support validated query templates
- Honor adjacency hierarchy id field
- Validate loader SQL identifiers
- Enforce GUI API path containment
- Escape user values in CLI console output
- Clean MagicMock artifacts between tests
- Preserve unowned root databases in tests
- Export transformer suggestion model
- Match plugin structures by descriptor
- Support empty widget transform tables
- Honor top-level widget source
- Prompt for deployment credentials
- Fail pipeline on transform config errors
- Prevent silent CLI startup failures
- Use dropdown for export data sources
- Improve export labels and warning handling
- Harden generated exports and enrichment configs
- Harden standard profile exports and tooling
- Harden export profile fallbacks
- Render void html tags without children
- Address React Doctor UI findings
- Address enrichment review feedback
- Improve enrichment previews
- Stabilize enrichment jobs
- Scan full CSV during DuckDB imports
- Allow adding import files incrementally
- Handle missing data preview tables
- Prevent recipe editor crashes
- Stabilize index field editor
- Preserve markdown content on page switch
- Persist desktop route memory natively
- Prevent collections preview update loops
- Address site editor review feedback
- Restore export config path hook
- Place preview restore next to delete
- Keep desktop project context in sync
- Soften project switcher hover states
- Preserve static site path for html exports
- Pin codecov cli version
- Harden release staging flow
- Update rustls webpki lockfile
- Harden export and enrichment jobs
- Split codecov checks by coverage area
- Align vitest config typing
- Address enrichment polling review feedback
- Stabilize frontend coverage tests
- Install pnpm before node cache
- Refine enrichment workflow reliability and UX
- Stage plugin manifest during releases
- Polish export format wizard
- Stabilize index config preview and actions
- Honor taxon stats relation fields
- Avoid welcome screen flicker on desktop
- Avoid recreating missing desktop project dirs
- Use native macOS traffic light placement
- Stabilize create project button hover
- Remove stale docs toctree entry
- Stabilize table preview pagination
- Harden release artifact publishing
- Restore macos executable permissions
- Harden release automation flows
- Accept flattened macos release app artifacts
- Resolve frontend lint warnings
- Surface pipeline status failures in publish
- Restrict publish gate to fresh sites
- Fail closed while publish gate resolves
- Gate publish on site configuration
- Restore site setup for unconfigured sites
- Tighten site root detection
- Base site readiness on a real root page
- Keep default web exports empty
- Stop scaffolding a synthetic home page
- Remove default home injection from site config
- Consolidate release automation flow
- Pass updater signing password explicitly
- Pass updater signing key path to macos finalizer
- Resolve downloaded macos app bundle in release finalizer
- Finalize macos release artifacts after notarization
- Repair macos signing pipeline for tauri bundles
- Sign versioned python framework bundle
- Bundle-sign python framework entrypoints
- Resolve versioned python path dynamically
- Sign flattened macos python entrypoints
- Sign embedded Python frameworks in CI
- Codesign macOS sidecar binaries in CI
- Pre-import Apple signing certificate in CI
- Recheck connectivity on startup
- Include trained ml models in desktop bundles
- Align mac traffic lights vertically
- Allow accented project names in wizard
- Point help output to the new GitHub Pages docs URL
- Exclude internal design system from Sphinx build
- Avoid duplicate help_content entries in wheel
- Harden config suggestions and uv dev workflow
- Stabilize collection auto-detect and desktop tools
- Resolve site builder lint warning
- Polish demo video interactions
- Refine demo video transitions
- Bind geospatial extractor to runtime config
- Stabilize previews and GitHub Pages deployment
- Prevent desktop preview request storms
- Harden desktop connectivity and updates
- Disable in-app windows updates
- Reduce collections preview load on low-power devices
- Preserve collection tab navigation
- Tighten publish readiness flow
- Improve UI rendering smoothness
- Smooth import query refresh states
- Improve linux updater install flow
- Prevent duplicate update toasts
- Repair packaged desktop widgets and feedback
- Enable tauri devtools feature for desktop debug mode
- Clarify collection batch progress
- Clear stale widget suggestion caches after import
- Hide sidebar branding in desktop builds
- Force bash shell for Tauri build on Windows
- Resolve typescript errors across forms and views
- Ensure site configs include a home page
- Auto fit map previews to data
- Stabilize tauri dev startup
- Reduce redundant frontend polling
- Harden widget previews and config inference
- Harden tauri desktop runtime
- Resolve frontend context split regressions
- Harden desktop update and packaging flows
- Improve Windows desktop compatibility
- Disable Windows sidecar console for desktop builds
- Limit entity list to 15 items with max-height cap
- Polish enrichment workspace and preview
- Use native linux titlebar chrome
- Streamline widget detail preview and forms
- Correct language switcher paths in exports
- Harden desktop update relaunch flow
- Simplify theme picker cards
- Open preview in browser from desktop
- Stabilize gui import and publishing workflows
- Harden gui runtime diagnostics
- Improve widget and transformer form handling
- Tighten desktop settings behavior
- Recover offline indicator on reconnect
- Align widget previews and layout config
- Hide legends in layout overview miniatures via Plotly relayout
- Improve preview engine resilience and health endpoint
- Improve Tauri startup, updater UX, and collections UI
- Disable RUSTSEC issue creation and improve desktop startup
- Address user findings — form reset, cooldown enforcement, screenshot capture, error sanitization
- Address code review findings
- Refine mac desktop header alignment
- Restore dev hot reload workflow
- Wire theme polish review fixes
- Isolate scroll zones and harmonize tab headers
- Move collapse toggle to right, fix scrollbar and scroll issues
- Use i18n for relative time in collections overview
- Resolve tab mismatch, API settings access, and stale i18n keys
- Correct stale i18n keys and tab value mismatch
- Enforce canonical home page export
- Improve desktop startup recovery
- Add unittest to PyInstaller hidden imports
- Polish publish workflow panels
- Stabilize publish previews and history
- Harden import and widget flows
- Harden import summary navigation
- Stabilize gui startup context
- Preserve enrichment tab state in onboarding UI
- Make pyinstaller install portable in CI
- Restore binary build packaging
- Increase auto-configure job polling timeout for CI with xdist
- Add --clear flag to uv venv to handle cached virtualenv
- Use correct codecov-action v5 parameter name
- Skip subset benchmark tests in CI when instance unavailable
- Skip benchmark tests when subset instance is unavailable
- Translate api enrichment UI
- Support reference-only spatial widgets
- Restore map suggestions for coordinate fields
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
- Add monaco-editor types as dev dependency
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
- Correction de 13 bugs dans les plugins transformers et l'API smart_config
- Preserve large integer ID precision and load group_by dynamically
- Preserve large integer IDs precision in index generation
- Fix pytest collection and test database artifacts
- Update instance initialization to EntityRegistry v2 format
- Improve fallback logic for displaying configuration path or file in ImportDemo component
- Update file count logic to handle edge cases and reorder sections in showcase store
- Resolve CI/CD build issues with GUI dist directory
- Restore .gitkeep file for CI/CD builds
- Update Tropicos API name in enrichment configuration
- Improve API enrichment field translations
- Simplify publish script to handle GUI packaging properly
- Ensure GUI dist directory exists for CI/CD builds
- Resolve CI/CD build issue with GUI dist directory
- Correct caching logic in api_taxonomy_enricher
- Refine entity existence check in PlotImporter
- Update API URL and enhance drag-and-drop functionality in import wizard
- Prevent rendering of empty widgets in WidgetPlugin and RadialGaugeWidget
- Improve zoom level calculation in InteractiveMapWidget
- Update parent linking logic in TaxonomyImporter
- Update drag-and-drop cursor styles and hierarchy level descriptions
- Correct hierarchy level description in PlotHierarchyConfig component
- Standardize field naming in advanced options for import functionality
- Update bar plot widget to handle cases with no meaningful y-axis data
- Add ORDER BY clause to SQL queries in HtmlPageExporter for consistent result ordering
- Correct quotation marks in LICENSE and update Plotly version in pyproject.toml for Scattermap support; enhance README with instructions for managing multiple Niamoto installations
- Fix interactive map widget for all groups
- Enhance info panel rendering by adding support for external data sources and improving value checks
- Improve error handling in page generation and refactor UICN translation function in taxon index template

### Refactoring

- Reduce UI dead code
- Prune unused UI code
- Add shell-neutral desktop bridge
- Replace screencast architecture with motion graphics foundation
- Compact desktop UI density
- Overhaul theme system — consolidate to 6 themes, unique fonts, offline fonts, font selector
- Unify collection transform state
- Reorganize sidebar navigation and header
- Stabilize frontend lint architecture
- Enforce frontend architecture boundaries
- Split site config hooks
- Lazy load monaco editors
- Standardize frontend data queries
- Consolidate frontend theme state
- Consolidate enrichment configuration workflow
- Add ARIA region labels to enrichment panel columns
- Replace enrichment config tabs with accordion sections
- Replace enrichment 2-col grid with 3-col ResizablePanelGroup
- Extract enrichment render helpers to separate file
- Extract useEnrichmentState hook from EnrichmentTab
- Polish publish preview copy and layout
- Improve collection layout overview
- Compact source cards with consistent icon-only actions
- Migrate shell components to theme-aware utilities
- Redesign sources dashboard workflow (#64)
- Site module UX revamp — unified view + first-launch experience (#63)
- Merge header and tabs into single compact toolbar
- Move pipeline status from banner to breadcrumb
- Flatten collections sidebar with status dots
- Rename Groups module to Collections in GUI
- Redesign sources workspace
- Simplify publish workflow
- Migrate geospatial I/O to pyogrio
- Remove publish.sh, move scripts to dev/, update docs for CI-based PyPI publish
- Clean up scripts directory, archive obsolete utilities
- Close ui architecture review findings
- Move home route into dashboard feature
- Finalize frontend feature architecture cleanup
- Simplify import flow react architecture
- Streamline reference enrichment flow
- Keep import workflow in context
- Polish import analysis flow
- Simplify import configuration review UX
- Remove misleading data quality dashboard score
- Move plotly-bundles to scripts/build/ and add CSS assets
- Harden and centralize auto-config rules
- Calibrate enriched reference classification
- Extract smart auto-config decision layer
- Centralize offline ML workspace under ml
- Simplify FK heuristic, delegate specific id types to alias registry
- Address P3 review findings
- Address P2 review findings
- Replace old pattern matching with alias registry, remove old MLColumnDetector
- Declarative registries, POST inline, smart entity selection (#55)
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
- Prepare EntityRegistry v2 migration
- Improve geospatial data handling in GeospatialExtractor
- Unify source configuration structure across documentation and code
- Remove taxon estimation logic from OccurrencesStep and SummaryStep
- Streamline import wizard and remove deprecated components
- Standardize success and error indicators in console output
- Clean up imports and enhance progress tracking
- Simplify value formatting logic in RadialGaugeWidget
- Remove deprecated template compatibility test from IndexGenerator
- Update asset paths and enhance static page layout
- Modernize export system with configurable IndexGeneratorPlugin and reorganize templates                                                                             │ │                                                                                                                                                                                                │ │   - Add new IndexGeneratorPlugin for configurable index page generation with filtering, custom display fields, and multiple views                                                              │ │   - Update HtmlPageExporter to integrate new plugin with fallback to traditional generation                                                                                                    │ │   - Add comprehensive configuration models for index generation (IndexGeneratorConfig, IndexGeneratorDisplayField, etc.)                                                                       │ │   - Reorganize template structure: move legacy templates to niamoto-legacy/ folder for backward compatibility                                                                                  │ │   - Modernize base templates with Tailwind CSS v4, improved responsive design, and configurable theming                                                                                        │ │   - Update template references to use simplified paths (group_detail.html instead of _layouts/group_detail_with_sidebar.html)
- Improve plugin test reliability by reloading modules and fixing imports
- Consolidate plugin system mocking with contextmanager in tests
- Improve plugin test structure with mock registry helper and better error handling
- Migrate from mapbox to standard plotly map types and remove token requirement
- Optimize hierarchical navigation by loading data from external JS files
- Centralize config models and restructure tests
- Improve error handling, validation, and tests
- Improve plugin architecture with enhanced registry and tests
- Optimize test suite performance and fix environment test

### Documentation

- Fix plugin registry docstring
- Refresh agent and GUI documentation
- Update institutional site wording
- Drop golden rule line from CLAUDE.md
- Add site markdown authoring plan
- Add site markdown authoring design
- Add site workbench preview plan
- Add site workbench preview design
- Add native menu shortcuts design
- Add desktop shell workbench trial design
- Add source enrichment reset design
- Add enrichment panel design spec
- Include release retrospective in docs toctree
- Add site builder empty-state implementation plan
- Add collection transform/export auto-config to ROADMAP
- Connect MCP server to local SLM fine-tuning and eval harness in ROADMAP
- Add Niamoto MCP server for AI-agent-driven instance setup to ROADMAP
- Add plugin platform overhaul (marketplace, R support, in-app creator) to ROADMAP
- Add desktop shell evaluation (Tauri vs Electron) to ROADMAP
- Move hosted Niamoto from not-planned to later in ROADMAP
- Add site builder empty-state design
- Link ROADMAP.md from README
- Add not-planned and contribute sections to ROADMAP.md
- Add Now/Soon/Later horizons to ROADMAP.md
- Add GBIF Challenge 2026 milestone to ROADMAP.md
- Add vision and recently shipped to ROADMAP.md
- Scaffold root ROADMAP.md
- Add ROADMAP.md implementation plan
- Add ROADMAP.md design spec
- Refresh README hero screenshots
- Refresh README visuals
- Rewrite contributing guide
- Reorganize and refresh desktop-first documentation (#123)
- Move DESIGN_SYSTEM.md to docs/ for project-wide visibility
- Add DESIGN_SYSTEM.md documenting the visual system
- Add motion graphics brainstorm and implementation plan
- Mark Phase 0+1 checkboxes as complete in demo video plan
- Add enrichment tab ux consolidation design
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
- Add desktop update harness design
- Add publish layout redesign spec
- Add sources mission control design
- Add publish ui simplification design
- Add ml model regeneration design
- Refine repository guidance for coding agents
- Rewrite gui documentation in english
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
- Alléger le plan transform trigger + corrections revue Codex
- Ajouter les plans shapes config et transform trigger + jobs robustes
- Add preview architecture, API reference, and widget thumbnail guide
- Mark all acceptance criteria as validated
- Add architecture docs, v1 release plan and config contract
- Rewrite plugin dev guide with modern Pydantic patterns + update plan
- Add Phase 3.3 user documentation for transform widgets
- Add Phase 3.2 config simplification analysis (6 axes identified)
- Update plan - mark Phase 2.5 layers as completed
- Add comprehensive git tag management commands
- Reorganize and fix Sphinx documentation structure
- Reorganize documentation structure and add ML detection system
- Reorganize documentation structure and improve formatting
- Add API documentation for plugin system

### Other

- Cover release lock resolution args
- Use PyPI Codecov CLI
- Snapshot fresh clawpatch review
- Harden clawpatch regression coverage
- Stabilize publication freshness check
- Cover fragmentation metric calculations
- Assert elevation profile calculations
- Isolate nested axis config mutations
- Restore plugin registry fixture state
- Assert pipeline option propagation
- Exercise layout preview delegation
- Make pattern matching checks collectable
- Enforce explicit schema fields
- Assert json api security guards
- Require template endpoint success
- Cover field aggregator registration
- Cover multi-group transform last run
- Cover plugin list registry types
- Cover index generator params groups
- Cover export widgets params groups
- Collect dev preview smoke scripts
- Cover read-only entity listing
- Fail plugin discovery regressions
- Fail stale plugin sample imports
- Preserve base test setup
- Fail on plugin discovery errors
- Tighten geospatial error contracts
- Isolate shape processor fixtures
- Assert import phase order
- Assert raw data error rendering
- Bump duckdb to 1.5.2
- Fix pnpm build approvals
- Avoid compatibility test module collision
- Untrack planning notes from gitignored dirs
- Gitignore skill working dirs (plans, brainstorms, superpowers, ideation)
- Archive internal planning docs and tidy AI-related tracking
- Fix collection block previews (#156)
- Update GitHub Actions to Node 24 (#143)
- Add file consistency pre-commit checks
- Enforce UI lint checks
- Ignore frontend coverage output
- Expand coverage baseline
- Strengthen enrichment regression coverage
- Sync plugin manifest and auto-regenerate via pre-commit
- Refresh release metadata
- Fail loudly instead of auto-committing blocked by branch rules (#130)
- Sync tauri cargo lock version
- Cover site builder readiness regressions
- Refine site readiness regressions
- Use Tailscale GitHub Action to reach Coolify on tailnet (#129)
- Add marketing-sync workflow (triggers niamoto-site redeploy)
- Initial .marketing/plugins.json
- Ignore local worktree and pnpm cache artifacts
- Wire Apple signing secrets into Tauri builds
- Sync release lockfiles
- Sync desktop planning and version metadata
- Remove retired design-system exclusions
- Add English desktop screenshots and dashboard polish
- Bump rustls-webpki to 0.103.12 (RUSTSEC-2026-0098)
- Apply rounded corners for Windows/Linux and macOS HIG padding
- Update lock files for v0.14.7
- Update uv.lock
- Update tauri lockfile version
- Desaturate herbier accent color — subtler stone tone
- Update uv.lock for 0.14.1
- Fix desktop project reload fixture
- Compact enrichment workspace layout
- Update lockfiles for 0.13.2
- Refresh uv.lock
- Drop macOS Intel matrix (macos-13 runner retired)
- Add macOS Intel and Linux arm64 to release builds
- Update tauri lockfile for 0.12.4
- Bump node to 22 for publish and binaries workflows
- Refresh safe dependencies
- Compact widget list items in collection panel
- Darken sidebar across all 10 themes
- Regenerate ml models for sklearn 1.8
- Pin pyinstaller and update desktop packaging
- Realign dependencies and raise minimum python to 3.12
- Replace battle test phases with focused import suites
- Clean unused ui public assets
- Add ablation runner and tune header convergence
- Macro-F1 0.3522 → 0.3527 (+0.05 pts)
- Macro-F1 0.3433 → 0.3522 (+0.89 pts)
- Macro-F1 0.3403 → 0.3433 (+0.30 pts)
- Macro-F1 0.3370 → 0.3403 (+0.33 pts)
- Macro-F1 0.2877 → 0.3068 (+1.91 pts)
- Macro-F1 0.3063 → 0.3257 (+1.9 pts)
- Macro-F1 0.3005 → 0.3063 (+0.6 pts)
- Macro-F1 0.2877 → 0.3005 (+1.3 pts)
- Macro-F1 0.5640 → 0.5641 (+0.01 pts)
- Macro-F1 0.5591 → 0.5640 (+0.49 pts)
- Macro-F1 0.5529 → 0.5591 (+0.62 pts)
- Macro-F1 0.5497 → 0.5529 (+0.32 pts)
- Macro-F1 0.5470 → 0.5497 (+0.27 pts)
- Macro-F1 0.5383 → 0.5470 (+0.87 pts)
- Macro-F1 0.5375 → 0.5383 (+0.08 pts)
- Macro-F1 0.5370 → 0.5375 (+0.05 pts)
- Macro-F1 0.5283 → 0.5370 (+0.87 pts)
- Macro-F1 0.4937 → 0.5283 (+3.46 pts)
- Macro-F1 0.4931 → 0.4937 (+0.06 pts)
- Macro-F1 0.4864 → 0.4931 (+0.67 pts)
- Macro-F1 0.4763 → 0.4864 (+1.01 pts)
- Macro-F1 0.4455 → 0.4763 (+3.08 pts)
- Macro-F1 0.3658 → 0.4455 (+7.97 pts)
- Update uv.lock for 0.8.1
- Sync tauri version to 0.7.5 and add it to bumpversion config
- Replace Rocket icon with Send and Menu with PanelLeft
- Redesign command palette with grouped layout and descriptions
- Upgrade GitHub Actions to Node.js 24 compatible versions
- Add preview engine tests and update layout tests
- Add e2e, data explorer, stats and service tests
- Add Phase 3.1 end-to-end tests for GUI config generation (30 tests)
- Add Phase 1.3 transform config validation tests (56 tests)
- Update npm dependencies to fix security vulnerabilities
- Remove macOS Intel build to save GitHub Actions quota
- Move Claude Code config files to gitignore
- Amélioration de la couverture de tests de 60% à 68%
- Upgrade minimum Python version from 3.10 to 3.11
- Fix test assertions and add auxiliary file cleanup
- Upgrade all dependencies to latest versions
- Remove old pipeline editor and dead import code
- Refactor code structure for improved readability and maintainability
- Update CHANGELOG for version 0.7.0 release
- Update versioning configuration and bump version to 0.7.0
- Update uv.lock to include upload times for package distributions and bump revision to 2
- Update shape import configuration and enhance testing
- Update version to 0.5.6, enhance installation and quickstart documentation, and refine configuration handling in tests. Added templates directory to documentation and improved export configuration assertions in tests.
- Update pyproject.toml for wheel packaging and modify README for asset links
- Update CHANGELOG.md
- Bump niamoto version from 0.4.2 to 0.5.0
- Remove config files and add config folder to gitignore
- Add requests-mock to dev dependencies and bump version to 0.4.2
- Enhance GitHub deployment tests with branch existence checks
- Fix commited mock files

## [v0.19.1] - 2026-05-22

### Features

- Streamline import cockpit workflow
- Guide users before import uploads

### Bug Fixes

- Preserve uv lock resolution options in releases
- Narrow import status badge variants
- Preserve export cancellation fallback
- Address PR review blockers
- Harden publish and import dashboard flows
- Gate desktop releases on sidecar startup
- Polish dark mode branding and sidebar state
- Tighten import file handling
- Harden import cockpit file matching
- Preserve duckdb resolution cutoff

### Other

- Cover release lock resolution args
- Use PyPI Codecov CLI

## [v0.19.0] - 2026-05-21

### Features

- Show collection computation progress in sidebar
- Allow custom API export data source
- Streamline collection data outputs
- Refine collection data outputs
- Complete standard profile workflows
- Add standardized export profiles

### Performance

- Speed up import auto-configuration

### Bug Fixes

- Stabilize desktop API auth client test
- Keep missing DuckDB read-only connections lazy
- Stabilize DuckDB access in GUI previews
- Eliminate pytest warnings
- Stabilize plugin loading and test cleanup
- Resolve high clawpatch findings
- Resolve clawpatch review findings
- Resolve clawpatch high findings
- Resolve clawpatch findings
- Close remaining clawpatch low findings
- Stabilize preview and overlay regressions
- Stabilize collection and index workflows
- Stabilize API route regressions
- Authorize desktop API requests
- Preserve profiler total row count
- Infer legacy top ranking mode
- Resolve spatial preview geometry
- Preserve group index generator fields
- Discover recipe widget schemas
- Align import v2 validation with model
- Validate relationship CSV inputs
- Escape BibTeX export values
- Offload enrichment preview loading
- Bound index suggestion record loads
- Enforce query result limits
- Preserve duplicate transform widgets
- Fail transform jobs for unknown groups
- Count hierarchical representatives from relation
- Preserve registry plugin type
- Translate standard compatibility errors
- Translate enrichment preview errors
- Mark publication stale after site config changes
- Offload smart auto configure
- Analyze spatial shape uploads
- Drop registered import tables
- Scope combined suggestions sources
- Translate enrichment config errors
- Honor configured spatial geometry fields
- Bound csv import uploads
- Hide non-transform job status
- Parse underscored entity map references
- Bound time series presence percentages
- Resolve repository ml models
- Aggregate duplicate class object rows
- Validate outlier export thresholds
- Reload desktop projects through native bridge
- Bound retained import jobs
- Validate stats validation rules
- Bound data explorer query limits
- Expose cli export jobs
- Validate dataset config updates
- Respect cleared preview fields
- Align import v2 schema contract
- Enforce export widget identifiers
- Load all recipe widget plugins
- Cancel export jobs
- Validate canonical transform lists
- Stream site file uploads
- Align index generator group lookup
- Read root transform source configs
- Limit feedback screenshot uploads
- Prefer explicit spatial coordinate columns
- Preserve import status setup errors
- Validate config updates before writing
- Bind transformer package exports
- Securely open exported files
- Write validation rules atomically
- Avoid leaking config file paths
- Validate backup config names
- Parameterize archive preview validation query
- Escape Rich markup in stats output
- Escape Rich markup in plugin listing
- Escape Rich markup in direct CLI errors
- Escape Rich markup in progress output
- Escape Rich markup in CLI output
- Block unsafe outbound test redirects
- Write source transform config atomically
- Use read-only table preview connection
- Open table preview database read-only
- Require auth for credential mutations
- Serialize API export target updates
- Escape formulas in outlier CSV exports
- Validate API export target paths
- Require auth for validation rule updates
- Serialize config scaffolding updates
- Serialize source config updates
- Share transform config write lock
- Serialize transform widget updates
- Avoid orphan recipe transforms
- Serialize collection metadata updates
- Write data content atomically
- Restrict data content writes
- Serve uploaded SVGs as attachments
- Create valid web export targets
- Validate widget dependency scripts
- Open template lookups read-only
- Scope recipe widget deletion
- Require desktop auth for import mutations
- Write bulk import config atomically
- Serialize index generator updates
- Constrain backup restore paths
- Stabilize pipeline history import snapshot
- Write config updates atomically
- Serialize reference config updates
- Quote Darwin Core group queries
- Merge enrichment updates with current data
- Validate Darwin Core query identifiers
- Resolve entity tables before querying
- Restrict derived column formulas
- Restrict custom formula evaluation
- Resolve archived test fixture paths
- Hide absolute export list paths
- Guard widget suggestions without project
- Preserve group index preview footers
- Quote dataset count tables
- Accept uppercase upload extensions
- Hide combined suggestion internals
- Hide backup filesystem paths
- Avoid GUI backup collisions
- Record JSON export metadata duration
- Register plugins with correct arguments
- Preserve benchmark logs
- Escape class object CSV paths
- Bound GBIF request timeouts
- Open entity reads read-only
- Limit BibTeX upload size
- Constrain saved source paths
- Restrict served project files
- Tolerate empty BibTeX fields
- Restrict API test targets
- Constrain site file listing paths
- Validate recipe plugin params
- Preserve static page extensions
- Limit extracted upload archives
- Preserve uploads on failed overwrite
- Preserve API export group settings
- Preserve unresolved widgets on reorder
- Return all recipe source columns
- Ignore invalid WKT in shape distribution
- Preserve deploy validation extras
- Validate dataset config shape
- Count dangling taxonomy orphans
- Paginate valid WKT map features
- Constrain configured source paths
- Escape render widget messages
- Restrict site file content access
- Stream terminal auto config events
- Reject concurrent import all jobs
- Validate current import config schema
- Preserve zero medians in validation stats
- Include max values in validation histograms
- Redact listed import job tracebacks
- Redact import job tracebacks
- Guard debug health error route
- Tolerate invalid WKT in coverage analysis
- Reject duplicate normalized CSV headers
- Preserve layout widget index identity
- Validate plugin compatibility requests
- Include datasets for reference-only recipes
- Reject colliding source uploads
- Limit source upload memory use
- Avoid backup filename collisions
- Preserve upper edge in smart bins
- Keep top ranking suggestion counts positive
- Resolve humboldt collection backing sources
- Filter horizontal bar zeros by value axis
- Handle zero-width contextual gauge ranges
- Render dictionary line plots with multiple y axes
- Constrain exporter output paths
- Sanitize leaflet map rendering
- Use advanced transform chain references
- Default static page context to none
- Escape widget container metadata
- Validate archived shapefile zip extraction
- Resolve archived debug script roots
- Run archived test helper from repo root
- Resolve dev script repository root
- Clean untracked autoresearch directories
- Preserve fusion surrogate cache on rebuild failure
- Handle help sections without index pages
- Validate template config before export update
- Surface geospatial source failures
- Honor geospatial registry id fields
- Copy semantic affordance sets
- Calculate edge density per area unit
- Align class object series by axis
- Round scalar gauge maximums upward
- Handle deployer unpublish network errors
- Reject disjoint relationship samples
- Project vector overlay feature areas
- Honor raster nodata metadata
- Convert table view data before empty check
- Mark uvloop as non-windows dependency
- Ignore invalid summary stat filters
- Convert summary stats data before empty check
- Handle plot import removal
- Resolve query db paths from repo root
- Use configured spatial preview dataset
- Preserve DuckDB mode during selects
- Substitute plain config env vars
- Expand configured database paths
- Tolerate partial UI builds
- Fail plugin manifest on syntax errors
- Validate aggregation SQL identifiers
- Sanitize markdown preview html
- Validate import v2 saves
- Quote entity route identifiers
- Constrain site uploads to files
- Constrain preview source paths
- Require desktop auth for project reload
- Block private URL health checks
- Use typed ecological transformer params
- Preserve nojekyll in GitHub API deploys
- Restrict file browser to project root
- Keep desktop auth token private
- Prevent docs help output deletion
- Avoid export cwd lock deadlock
- Preserve existing zip upload components
- Skip empty product holdouts
- Support validated query templates
- Honor adjacency hierarchy id field
- Validate loader SQL identifiers
- Enforce GUI API path containment
- Escape user values in CLI console output
- Clean MagicMock artifacts between tests
- Preserve unowned root databases in tests
- Export transformer suggestion model
- Match plugin structures by descriptor
- Support empty widget transform tables
- Honor top-level widget source
- Prompt for deployment credentials
- Fail pipeline on transform config errors
- Prevent silent CLI startup failures
- Use dropdown for export data sources
- Improve export labels and warning handling
- Harden generated exports and enrichment configs
- Harden standard profile exports and tooling
- Harden export profile fallbacks
- Render void html tags without children
- Address React Doctor UI findings

### Refactoring

- Reduce UI dead code
- Prune unused UI code

### Documentation

- Fix plugin registry docstring
- Refresh agent and GUI documentation
- Update institutional site wording
- Drop golden rule line from CLAUDE.md

### Other

- Snapshot fresh clawpatch review
- Harden clawpatch regression coverage
- Stabilize publication freshness check
- Cover fragmentation metric calculations
- Assert elevation profile calculations
- Isolate nested axis config mutations
- Restore plugin registry fixture state
- Assert pipeline option propagation
- Exercise layout preview delegation
- Make pattern matching checks collectable
- Enforce explicit schema fields
- Assert json api security guards
- Require template endpoint success
- Cover field aggregator registration
- Cover multi-group transform last run
- Cover plugin list registry types
- Cover index generator params groups
- Cover export widgets params groups
- Collect dev preview smoke scripts
- Cover read-only entity listing
- Fail plugin discovery regressions
- Fail stale plugin sample imports
- Preserve base test setup
- Fail on plugin discovery errors
- Tighten geospatial error contracts
- Isolate shape processor fixtures
- Assert import phase order
- Assert raw data error rendering
- Bump duckdb to 1.5.2
- Fix pnpm build approvals
- Avoid compatibility test module collision
- Untrack planning notes from gitignored dirs
- Gitignore skill working dirs (plans, brainstorms, superpowers, ideation)
- Archive internal planning docs and tidy AI-related tracking

## [v0.18.1] - 2026-04-29

### Other

- Fix collection block previews (#156)

## [v0.18.0] - 2026-04-29

### Features

- Improve API export auto-configuration

## [v0.17.1] - 2026-04-28

### Features

- Support auxiliary source review editing

### Bug Fixes

- Address enrichment review feedback
- Improve enrichment previews
- Stabilize enrichment jobs
- Scan full CSV during DuckDB imports
- Allow adding import files incrementally
- Handle missing data preview tables
- Prevent recipe editor crashes
- Stabilize index field editor
- Preserve markdown content on page switch

### Other

- Update GitHub Actions to Node 24 (#143)

## [v0.17.0] - 2026-04-28

### Features

- Add data source inspection tabs (#142)

### Bug Fixes

- Persist desktop route memory natively

## [v0.16.3] - 2026-04-25

### Features

- Improve index field selection
- Add workflow history details
- Add workflow history view
- Add list performance diagnostics
- Add workflow commands to palette
- Remember desktop view preferences
- Remember desktop route per project

### Performance

- Optimize data explorer table rendering

## [v0.16.2] - 2026-04-24

### Bug Fixes

- Prevent collections preview update loops
- Address site editor review feedback

## [v0.16.1] - 2026-04-24

### Features

- Improve site builder authoring workflow
- Persist site workbench preview state
- Add native desktop menu shell
- Refine desktop shell and export toggles

### Bug Fixes

- Restore export config path hook
- Place preview restore next to delete
- Keep desktop project context in sync
- Soften project switcher hover states
- Preserve static site path for html exports
- Pin codecov cli version
- Harden release staging flow

### Documentation

- Add site markdown authoring plan
- Add site markdown authoring design
- Add site workbench preview plan
- Add site workbench preview design
- Add native menu shortcuts design
- Add desktop shell workbench trial design

### Other

- Add file consistency pre-commit checks
- Enforce UI lint checks

## [v0.16.0] - 2026-04-23

### Features

- Add source enrichment reset mode
- Add enrichment panel workflow

### Bug Fixes

- Update rustls webpki lockfile
- Harden export and enrichment jobs
- Split codecov checks by coverage area
- Align vitest config typing
- Address enrichment polling review feedback
- Stabilize frontend coverage tests
- Install pnpm before node cache
- Refine enrichment workflow reliability and UX
- Stage plugin manifest during releases

### Documentation

- Add source enrichment reset design
- Add enrichment panel design spec

### Other

- Ignore frontend coverage output
- Expand coverage baseline
- Strengthen enrichment regression coverage

## [v0.15.9] - 2026-04-21

### Features

- Add script to revert Tauri updater manifest to a previous version

### Bug Fixes

- Polish export format wizard
- Stabilize index config preview and actions
- Honor taxon stats relation fields
- Avoid welcome screen flicker on desktop
- Avoid recreating missing desktop project dirs
- Use native macOS traffic light placement
- Stabilize create project button hover
- Remove stale docs toctree entry
- Stabilize table preview pagination
- Harden release artifact publishing

### Other

- Sync plugin manifest and auto-regenerate via pre-commit

## [v0.15.8] - 2026-04-20

### Bug Fixes

- Restore macos executable permissions
- Harden release automation flows

### Documentation

- Include release retrospective in docs toctree

## [v0.15.7] - 2026-04-20

### Bug Fixes

- Accept flattened macos release app artifacts

### Other

- Refresh release metadata
- Fail loudly instead of auto-committing blocked by branch rules (#130)

## [v0.15.6] - 2026-04-20

### Features

- Add AST-based plugin manifest extractor

### Bug Fixes

- Resolve frontend lint warnings
- Surface pipeline status failures in publish
- Restrict publish gate to fresh sites
- Fail closed while publish gate resolves
- Gate publish on site configuration
- Restore site setup for unconfigured sites
- Tighten site root detection
- Base site readiness on a real root page
- Keep default web exports empty
- Stop scaffolding a synthetic home page
- Remove default home injection from site config
- Consolidate release automation flow
- Pass updater signing password explicitly
- Pass updater signing key path to macos finalizer
- Resolve downloaded macos app bundle in release finalizer

### Documentation

- Add site builder empty-state implementation plan
- Add collection transform/export auto-config to ROADMAP
- Connect MCP server to local SLM fine-tuning and eval harness in ROADMAP
- Add Niamoto MCP server for AI-agent-driven instance setup to ROADMAP
- Add plugin platform overhaul (marketplace, R support, in-app creator) to ROADMAP
- Add desktop shell evaluation (Tauri vs Electron) to ROADMAP
- Move hosted Niamoto from not-planned to later in ROADMAP
- Add site builder empty-state design
- Link ROADMAP.md from README
- Add not-planned and contribute sections to ROADMAP.md
- Add Now/Soon/Later horizons to ROADMAP.md
- Add GBIF Challenge 2026 milestone to ROADMAP.md
- Add vision and recently shipped to ROADMAP.md
- Scaffold root ROADMAP.md
- Add ROADMAP.md implementation plan
- Add ROADMAP.md design spec

### Other

- Sync tauri cargo lock version
- Cover site builder readiness regressions
- Refine site readiness regressions
- Use Tailscale GitHub Action to reach Coolify on tailnet (#129)
- Add marketing-sync workflow (triggers niamoto-site redeploy)
- Initial .marketing/plugins.json

## [v0.15.5] - 2026-04-20

### Bug Fixes

- Repair the macOS desktop signing and notarization pipeline, including post-build bundle finalization
- Include trained ML models in desktop bundles
- Recheck desktop connectivity on startup before surfacing offline failures

### Refactoring

- Add a shell-neutral desktop bridge for desktop renderer integrations

### Other

- Wire Apple signing secrets into Tauri builds
- Sync release lockfiles and release helper tooling
- Ignore local worktree and pnpm cache artefacts
- Refresh the local `niamoto-release` skill to match the tag-driven GitHub release flow

## [v0.15.4] - 2026-04-19

### Features

- Redesign the desktop dashboard: horizontal pipeline bar, contextual quick actions, entity stats and recent activity feed

### Bug Fixes

- Localize dashboard summary strings and activity type/status labels for non-French locales
- Tone down saturated backgrounds on the pipeline bar and make button subtitles legible on dark variants
- Drop the spurious "primary" highlight on the Import quick action

### Other

- Validate `/api/pipeline/history` limit parameter (clamped to 1–100) and cover the endpoint with regression tests

## [v0.15.3] - 2026-04-18

### Bug Fixes

- Allow accented project names in GUI wizard
- Point CLI help output to the new GitHub Pages docs URL
- Exclude internal design system from Sphinx build

### Documentation

- Migrate from ReadTheDocs to GitHub Pages
- Refresh README hero screenshots
- Refresh README visuals
- Rewrite contributing guide

### Other

- Remove retired design-system exclusions
- Add English desktop screenshots and dashboard polish

## [v0.15.2] - 2026-04-18

### Features

- Embed public documentation inside the desktop app
- Refresh app about content with the new docs structure

### Bug Fixes

- Harden config suggestions and uv dev workflow
- Avoid duplicate help_content entries in wheel (fixes PyPI 400 upload)

### Documentation

- Reorganize and refresh project docs with a desktop-first layout
- Reboot structure for desktop-first refonte
- Add brainstorm and plan for documentation refonte

### Refactoring

- Apply code review findings before shipping docs refonte
- Exclude superpowers/ from Sphinx and strip stale absolute paths
- Migrate section content to the desktop-first layout
- Refresh desktop-first README, style guide, and hero assets

### Other

- Refresh lockfiles for docs toolchain

## [v0.15.1] - 2026-04-16

### Bug Fixes

- Stabilize collection auto-detect and desktop tools

### Other

- Bump rustls-webpki to 0.103.12 (RUSTSEC-2026-0098)

## [v0.15.0] - 2026-04-15

### Features

- Add landing teaser with Niamoto product mocks (demo-video)
- Add Niamoto marketing site plan with partner assets
- Improve index generator configuration workflow
- Build Remotion product demo
- Wire Intro/Outro scenes and add TransitionLabels (demo-video)
- Add Acts 4-6 — Collections, Site Builder, Publish (demo-video)
- Add UI components, cursor system, and Acts 1-3 (demo-video)
- Bootstrap Remotion demo video project (media)

### Bug Fixes

- Resolve site builder lint warning
- Polish demo video interactions
- Refine demo video transitions
- Bind geospatial extractor to runtime config
- Stabilize previews and GitHub Pages deployment

### Refactoring

- Replace screencast architecture with motion graphics foundation (demo-video)

### Documentation

- Move DESIGN_SYSTEM.md to docs/ for project-wide visibility
- Add DESIGN_SYSTEM.md documenting the visual system (demo-video)
- Add motion graphics brainstorm and implementation plan
- Mark Phase 0+1 checkboxes as complete in demo video plan

### Other

- Apply rounded corners for Windows/Linux and macOS HIG padding (icons)
- Update lock files for v0.14.7

## [v0.14.8] - 2026-04-13

### Bug Fixes

- Prevent desktop preview request storms

## [v0.14.7] - 2026-04-13

### Bug Fixes

- Harden desktop connectivity and updates
- Disable in-app windows updates
- Reduce collections preview load on low-power devices

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
