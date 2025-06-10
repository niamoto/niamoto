import os
import yaml
from typing import Any, Dict, Optional, List
from niamoto.common.exceptions import (
    ConfigurationError,
    FileReadError,
    FileWriteError,
    FileFormatError,
    EnvironmentSetupError,
)
from niamoto.common.utils import error_handler


class Config:
    """
    Class to manage all Niamoto configuration files:
     - config.yml (global env settings: database, logs, outputs, etc.)
     - import.yml (data sources)
     - transform.yml (transformations)
     - export.yml (widgets)
    """

    @error_handler(log=True, raise_error=True)
    def __init__(
        self, config_dir: Optional[str] = None, create_default: bool = True
    ) -> None:
        """
        Initialize the Config manager by loading multiple YAML files from config_dir.

        Args:
            config_dir (str): Path to the directory containing the 4 config files.
            create_default (bool): If True, create default configs if not found.
        """
        try:
            if not config_dir:
                config_dir = os.path.join(self.get_niamoto_home(), "config")
            self.config_dir = config_dir
            self.config: Dict[str, Any] = {}
            self.imports: Dict[str, Any] = {}
            self.transforms: Any = {}
            self.exports: Any = {}

            self._load_files(create_default)

            # Define plugins directory - default is next to config directory
            # Check if there's a custom plugins path in config.yml
            plugins_path = "plugins"  # default path
            if "plugins" in self.config and "path" in self.config["plugins"]:
                plugins_path = self.config["plugins"]["path"]

            # If plugins_path is absolute, use it directly, otherwise join with project_root
            if os.path.isabs(plugins_path):
                self.plugins_dir = plugins_path
            else:
                project_root = os.path.dirname(config_dir)
                self.plugins_dir = os.path.join(project_root, plugins_path)

        except Exception as e:
            raise ConfigurationError(
                config_key="initialization",
                message="Failed to initialize configuration",
                details={"config_dir": config_dir, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def _load_files(self, create_default: bool) -> None:
        """Load or create the config files."""
        config_files = {
            "config.yml": (self._default_config, "config"),
            "import.yml": (self._default_imports, "imports"),
            "transform.yml": (self._default_transforms, "transforms"),
            "export.yml": (self._default_exports, "exports"),
        }

        for filename, (default_func, attr_name) in config_files.items():
            file_path = os.path.join(self.config_dir, filename)
            try:
                file_path = os.path.join(self.config_dir, filename)
                config_data = self._load_yaml_with_defaults(
                    file_path, default_func(), create_default
                )
                setattr(self, attr_name, config_data)
            except Exception as e:
                raise ConfigurationError(
                    config_key=filename,
                    message="Failed to load configuration file",
                    details={"file": file_path, "error": str(e)},
                )

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def get_niamoto_home() -> str:
        """
        Return the Niamoto home directory.

        This method checks if the 'NIAMOTO_HOME' environment variable is set.
        If it is, returns that path; otherwise, falls back to the current working directory.
        """
        niamoto_home = os.environ.get("NIAMOTO_HOME")
        if not niamoto_home:
            niamoto_home = os.getcwd()
        if not os.path.exists(niamoto_home):
            raise EnvironmentSetupError(
                message="NIAMOTO_HOME directory not found",
                details={"path": niamoto_home},
            )
        return niamoto_home

    @staticmethod
    @error_handler(log=True, raise_error=True)
    def _load_yaml_with_defaults(
        file_path: str, default_data: Dict[str, Any], create_if_missing: bool
    ) -> Dict[str, Any]:
        """
        Loads a YAML file or creates it from defaults if not found.
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        data = yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        raise FileFormatError(
                            file_path=file_path,
                            message="Invalid YAML format",
                            details={"error": str(e)},
                        )
                    return data or {}
            elif create_if_missing:
                # Check if we're in a test environment
                if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get(
                    "NIAMOTO_TEST_MODE"
                ):
                    # In test mode, don't create files, just return defaults
                    return default_data
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    # Special handling for import.yml and transform.yml to include helpful comments
                    if file_path.endswith("import.yml"):
                        Config._write_import_yaml_with_comments(file_path)
                        return default_data
                    elif file_path.endswith("transform.yml"):
                        Config._write_transform_yaml_with_comments(file_path)
                        return []  # transform.yml is a list, not a dict
                    elif file_path.endswith("export.yml"):
                        Config._write_export_yaml_with_comments(file_path)
                        return {"exports": []}  # export.yml has exports key with list
                    else:
                        with open(file_path, "w", encoding="utf-8") as f:
                            yaml.dump(
                                default_data,
                                f,
                                default_flow_style=False,
                                sort_keys=False,
                            )
                        return default_data
                except Exception as e:
                    raise FileWriteError(
                        file_path=file_path,
                        message="Failed to create config file",
                        details={"error": str(e)},
                    )
            else:
                # If file doesn't exist and we're not creating it, raise an error
                raise FileReadError(
                    file_path=file_path,
                    message="Configuration file not found",
                    details={"create_default": create_if_missing},
                )
        except OSError as e:
            raise FileReadError(
                file_path=file_path,
                message="Failed to access config file",
                details={"error": str(e)},
            )

    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """
        Default content for config.yml (database, logs, outputs).
        """
        return {
            "database": {"path": "db/niamoto.db"},
            "logs": {"path": "logs"},
            "exports": {
                "web": "exports/web",
                "api": "exports/api",
            },
            "plugins": {"path": "plugins"},
            "templates": {"path": "templates"},
        }

    @staticmethod
    def _default_imports() -> Dict[str, Any]:
        """
        Default content for import.yml (taxonomy, occurrences, etc.).
        """
        return {
            "taxonomy": {"type": "csv", "path": "imports/taxonomy.csv"},
            "plots": {"type": "csv", "path": "imports/plots.csv"},
            "occurrences": {"type": "csv", "path": "imports/occurrences.csv"},
        }

    @staticmethod
    def _default_transforms() -> List[Dict[str, Any]]:
        """
        Default transformations. Returns an empty list.
        """
        return []

    @staticmethod
    def _default_exports() -> Dict[str, Any]:
        """
        Default export config. Returns exports key with empty list.
        """
        return {"exports": []}

    # ===============================
    # PROPERTIES / GETTERS
    # ===============================

    @staticmethod
    def _write_import_yaml_with_comments(file_path: str) -> None:
        """Write import.yml with helpful comments."""
        content = """# Niamoto Import Configuration
# This file defines data sources for importing into Niamoto

# TAXONOMY CONFIGURATION
# Import taxonomic reference data
taxonomy:
  type: csv                              # File type: csv
  path: imports/taxonomy.csv             # Path to taxonomy file
  # source: file                         # Options: 'file' or 'occurrence' (extract from occurrences)
  # ranks: family,genus,species,infra    # When source is 'occurrence', specify ranks to extract

  # Optional: Enrich taxonomy with external API
  # api_enrichment:
  #   enabled: true
  #   plugin: api_taxonomy_enricher
  #   api_url: https://api.example.com/taxons
  #   auth_method: api_key               # Options: 'api_key', 'basic', 'bearer'
  #   auth_params:
  #     key: your-api-key
  #     location: header                 # Options: 'header' or 'query'
  #     name: apiKey                     # Parameter name for the API key
  #   query_field: full_name             # Field to use for API queries
  #   rate_limit: 2.0                    # Requests per second
  #   cache_results: true                # Cache API responses
  #   response_mapping:                  # Map API response fields to database columns
  #     conservation_status: status
  #     endemic: is_endemic

# PLOT CONFIGURATION
# Import plot/site data
plots:
  type: csv                              # Options: 'csv' or 'vector'
  path: imports/plots.csv                # Path to plots file
  # identifier: id                       # Column containing plot ID
  # locality_field: name                 # Column for plot name/locality
  # location_field: geometry             # Column for spatial data (WKT or coordinates)
  # format: csv                          # For vector type: 'shapefile', 'geopackage', 'geojson'

# OCCURRENCE CONFIGURATION
# Import species occurrence data
occurrences:
  type: csv
  path: imports/occurrences.csv
  # identifier: id                       # Column for occurrence ID
  # location_field: geometry             # Column for spatial data
  # taxon_field: taxon_id                # Column linking to taxonomy
  # plot_field: plot_id                  # Column linking to plots

# SHAPE CONFIGURATION (Optional)
# Import geographic boundaries and zones
# shapes:
#   - category: provinces                # Shape category identifier
#     type: vector
#     format: shapefile                  # Options: 'shapefile', 'geopackage', 'geojson'
#     path: imports/shapes/provinces.shp
#     name_field: name                   # Field containing shape names
#     label: Provinces                   # Display label
#     description: Administrative boundaries
#
#   - category: ecological_zones
#     type: vector
#     format: geopackage
#     path: imports/shapes/eco_zones.gpkg
#     name_field: zone_name
#     label: Ecological Zones
#     description: Ecological classification zones

# LAYER CONFIGURATION (Optional)
# Import additional spatial layers (rasters, vectors)
# layers:
#   - name: elevation
#     type: raster
#     path: imports/layers/elevation.tif
#     description: Digital elevation model
#
#   - name: rainfall
#     type: raster
#     path: imports/layers/rainfall.tif
#     description: Annual rainfall distribution
#
#   - name: forest_cover
#     type: vector
#     format: shapefile
#     path: imports/layers/forest.shp
#     description: Forest coverage

# STATISTICS IMPORTS (Optional)
# Import pre-calculated statistics
# plot_stats:
#   type: csv
#   path: imports/plot_stats.csv
#   identifier: plot_id                  # Column linking to plots
#
# shape_stats:
#   type: csv
#   path: imports/shape_stats.csv
#   identifier: shape_id                 # Column linking to shapes
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _write_transform_yaml_with_comments(file_path: str) -> None:
        """Write transform.yml with helpful comments."""
        content = """# Niamoto Transform Configuration
# This file defines data transformations and statistical analyses
# Each transformation group creates widgets for visualization

# Transformations are defined as a list of groups
# Each group processes data for a specific entity type (taxon, plot, shape)

# EXAMPLE: Taxon transformations
# - group_by: taxon                    # Entity type: 'taxon', 'plot', or 'shape'
#   source:
#     data: occurrences                # Main data source table
#     grouping: taxon_ref              # Reference table for grouping
#     relation:                        # How to relate data to reference
#       plugin: nested_set             # Plugin for hierarchical data
#       key: taxon_ref_id              # Foreign key field
#       fields:                        # Additional fields for hierarchy
#         parent: parent_id
#         left: lft
#         right: rght
#
#   widgets_data:                      # Define widgets for visualization
#     general_info:                    # Widget identifier
#       plugin: field_aggregator       # Plugin to aggregate fields
#       params:
#         fields:
#           - source: taxon_ref        # Source table
#             field: full_name         # Source field
#             target: name             # Output field name
#           - source: occurrences
#             field: id
#             target: count
#             transformation: count    # Count occurrences
#
#     distribution_map:
#       plugin: geospatial_extractor
#       params:
#         source: occurrences
#         field: geo_pt                # Geometry field
#         format: geojson              # Output format

# EXAMPLE: Plot transformations
# - group_by: plot
#   source:
#     data: plot_stats                 # Pre-calculated statistics
#     grouping: plot_ref
#     relation:
#       plugin: stats_loader           # Load pre-calculated stats
#       key: plot_id
#
#   widgets_data:
#     general_info:
#       plugin: field_aggregator
#       params:
#         fields:
#           - source: plots
#             field: name
#             target: plot_name
#           - source: plots
#             field: elevation
#             target: elevation
#             units: m                 # Add units for display
#
#     top_species:
#       plugin: class_object_series_extractor
#       params:
#         source: plot_stats
#         class_object: top10_species  # Extract top 10 species
#         size_field:
#           input: class_name
#           output: species
#         value_field:
#           input: class_value
#           output: counts

# AVAILABLE PLUGINS:
# Data extraction:
# - field_aggregator: Combine fields from different sources
# - direct_attribute: Extract single field value
# - geospatial_extractor: Extract and format spatial data
# - multi_column_extractor: Extract multiple columns

# Statistical analysis:
# - statistical_summary: Calculate statistics (min, max, mean, etc.)
# - binned_distribution: Create histogram bins
# - categorical_distribution: Count by categories
# - top_ranking: Find top N items
# - binary_counter: Count true/false values

# Time series:
# - time_series_analysis: Analyze temporal data (e.g., phenology)

# Complex transformations:
# - transform_chain: Chain multiple transformations
# - class_object_series_extractor: Extract series from class objects
# - custom_calculator: Apply custom formulas

# Shape-specific:
# - shape_processor: Process and simplify geometries
# - class_object_categories_mapper: Map categories from stats

# Start with an empty list and add transformations as needed
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _write_export_yaml_with_comments(file_path: str) -> None:
        """Write export.yml with helpful comments."""
        content = """# Niamoto Export Configuration
# This file defines how to export data and generate visualizations

exports:

  # EXAMPLE: Static Website Export
  # - name: website                      # Export identifier
  #   enabled: true                      # Enable/disable this export
  #   exporter: html_page_exporter       # Plugin to use
  #
  #   params:                            # Exporter parameters
  #     template_dir: "templates/"       # Where to find templates
  #     output_dir: "exports/web"        # Where to generate files
  #
  #     # Site-wide configuration (available in all templates)
  #     site:
  #       title: "My Niamoto Site"
  #       logo: "assets/logo.png"
  #       lang: "en"
  #       primary_color: "#228b22"
  #
  #     # Navigation menu
  #     navigation:
  #       - text: "Home"
  #         url: "/index.html"
  #       - text: "About"
  #         url: "/about.html"
  #
  #     # Copy asset directories
  #     copy_assets_from:
  #       - "templates/assets/"
  #
  #   # Static pages (home, about, etc.)
  #   static_pages:
  #     - name: home
  #       template: "index.html"         # Template file
  #       output_file: "index.html"      # Output file
  #
  #   # Dynamic pages from data groups
  #   groups:
  #     - group_by: taxon                # Entity type
  #       output_pattern: "taxon/{id}.html"
  #       index_output_pattern: "taxon/index.html"
  #
  #       # Index page configuration
  #       index_generator:
  #         enabled: true
  #         template: "group_index.html"
  #         page_config:
  #           title: "Taxa List"
  #           items_per_page: 20
  #
  #         # Fields to display in index
  #         display_fields:
  #           - name: "name"
  #             source: "general_info.name.value"
  #             type: "text"
  #             label: "Scientific Name"
  #             searchable: true
  #
  #       # Widgets for detail pages
  #       widgets:
  #         - plugin: info_grid
  #           title: "General Information"
  #           data_source: general_info
  #           params:
  #             grid_columns: 2
  #             items:
  #               - {label: "Name", source: "name"}
  #               - {label: "Family", source: "family"}

# AVAILABLE EXPORTERS:
# - html_page_exporter: Generate static HTML website
# - api_exporter: Generate JSON API files
# - csv_exporter: Export data as CSV files
# - report_exporter: Generate PDF/Word reports

# AVAILABLE WIDGETS FOR HTML PAGES:
# Information display:
# - info_grid: Display key-value information in a grid
# - table_view: Display tabular data
# - raw_data_widget: Display raw JSON data

# Maps and spatial:
# - interactive_map: Interactive leaflet map
# - static_map: Static map image

# Charts and visualizations:
# - bar_plot: Bar charts (horizontal/vertical, grouped/stacked)
# - line_plot: Line charts
# - scatter_plot: Scatter plots
# - donut_chart: Donut/pie charts
# - radial_gauge: Circular gauges for single values
# - stacked_area_plot: Area charts
# - sunburst_chart: Hierarchical sunburst
# - concentric_rings: Nested ring charts

# Navigation:
# - hierarchical_nav_widget: Tree navigation for hierarchical data

# Statistics:
# - summary_stats: Statistical summary cards
# - distribution_chart: Distribution visualizations

# Start with an empty exports list and add configurations as needed
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    @property
    @error_handler(log=True, raise_error=True)
    def database_path(self) -> str:
        """
        Get the database path from config.yml.
        Returns:
            str: database path
        """
        path = self.config.get("database", {}).get("path")
        if not path:
            raise ConfigurationError(
                config_key="database.path",
                message="Database path not configured",
                details={"config": self.config.get("database", {})},
            )
        return path

    @property
    @error_handler(log=True, raise_error=True)
    def logs_path(self) -> str:
        """
        Get the logs path from config.yml.
        Returns:
            str: logs path

        """
        path = self.config.get("logs", {}).get("path")
        if not path:
            raise ConfigurationError(
                config_key="logs.path",
                message="Logs path not configured",
                details={"config": self.config.get("logs", {})},
            )
        return path

    @property
    @error_handler(log=True, raise_error=True)
    def get_export_config(self) -> Dict[str, str]:
        """
        Get the output paths from config.yml.
        Returns:
            Dict[str, str]: output paths
        """
        exports = self.config.get("exports", {})
        if not exports:
            raise ConfigurationError(
                config_key="exports",
                message="No export paths configured",
                details={"config": self.config},
            )
        return exports

    @property
    @error_handler(log=True, raise_error=True)
    def get_imports_config(self) -> Dict[str, Any]:
        """
        Get the data sources from import.yml.
        Returns:
            Dict[str, Any]: data sources

        """
        if not self.imports:
            raise ConfigurationError(
                config_key="imports",
                message="No import sources configured",
                details={"imports_file": "import.yml"},
            )
        return self.imports

    @error_handler(log=True, raise_error=True)
    def get_transforms_config(self) -> List[Dict[str, Any]]:
        """
        Get the transformations config from transform.yml.
        Returns:
            List[Dict[str, Any]]: transformations config
        """

        if not self.transforms:
            raise ConfigurationError(
                config_key="transforms",
                message="No transforms configuration found",
                details={"transforms_file": "transform.yml"},
            )
        return self.transforms

    @error_handler(log=True, raise_error=True)
    def get_exports_config(self) -> List[Dict[str, Any]]:
        """
        Get the transforms config from export.yml.
        Returns:
            List[Dict[str, Any]]: transforms config
        """
        if not self.exports:
            raise ConfigurationError(
                config_key="exports",
                message="No exports configuration found",
                details={"exports": "export.yml"},
            )
        return self.exports
