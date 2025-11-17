import os
import re
from string import Template
import yaml
from typing import Any, Dict, Optional, List

from niamoto.core.imports.config_models import GenericImportConfig
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
            self._generic_import_config: Optional[GenericImportConfig] = None

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
                    raw_content = f.read()
                resolved_content = Config._substitute_env_variables(
                    raw_content, source=file_path
                )
                try:
                    data = yaml.safe_load(resolved_content)
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
    def _substitute_env_variables(content: str, *, source: str) -> str:
        """Replace ${VAR} or ${VAR:-default} placeholders with environment values."""

        if "${" not in content:
            return content

        pattern = re.compile(r"\$\{([A-Z0-9_]+)(?::-(.*?))?\}")

        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default_value = match.group(2)
            env_value = os.environ.get(var_name)
            if env_value is not None:
                return env_value
            if default_value is not None:
                return default_value
            raise EnvironmentSetupError(
                message="Missing environment variable",
                details={"variable": var_name, "file": source},
            )

        substituted = pattern.sub(replace, content)

        # Support $VAR style via string.Template for backwards compatibility
        try:
            return Template(substituted).safe_substitute(os.environ)
        except (
            ValueError
        ) as exc:  # pragma: no cover - only triggered on malformed template
            raise FileFormatError(
                file_path=source,
                message="Invalid template syntax in configuration",
                details={"error": str(exc)},
            ) from exc

    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """
        Default content for config.yml (database, logs, outputs).
        """
        from datetime import datetime

        try:
            from niamoto.__version__ import __version__
        except ImportError:
            __version__ = "unknown"

        return {
            "project": {
                "name": "Niamoto Project",  # Default name, will be overridden
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "niamoto_version": __version__,
            },
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
        Default content for import.yml - EntityRegistry v2 format.

        Note: This is not used when creating import.yml files.
        The _write_import_yaml_with_comments() method writes the file directly
        with inline comments for better user experience.

        This method exists only for API compatibility when loading existing configs.
        """
        return {
            "version": "1.0",
            "entities": {"datasets": {}, "references": {}},
            "metadata": {},
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
        """Write import.yml with EntityRegistry v2 format and helpful comments."""
        content = """# Niamoto Import Configuration - EntityRegistry v2
# This file defines your data entities using the flexible EntityRegistry system
# Documentation: https://docs.niamoto.org/import-configuration

version: '1.0'

# =============================================================================
# ENTITIES DEFINITION
# =============================================================================
# Define your data model with two types of entities:
# - DATASETS: Observational/transactional data (occurrences, measurements, samples)
# - REFERENCES: Master/reference data (taxonomy, geography, classifications)

entities:

  # ---------------------------------------------------------------------------
  # DATASETS
  # ---------------------------------------------------------------------------
  # Datasets contain observational data that reference master data
  # Example use cases: species occurrences, environmental measurements, samples

  datasets:
    # Uncomment and customize the example below:
    #
    # my_occurrences:
    #   description: Species occurrence observations
    #
    #   # Data source configuration
    #   connector:
    #     type: file                          # Source type: 'file' or 'database'
    #     format: csv                         # File format: csv, excel, json, geojson
    #     path: imports/occurrences.csv       # Relative or absolute path
    #
    #   # Schema definition
    #   schema:
    #     id_field: id                        # Primary key field name
    #     fields:                             # List of fields to import
    #       - name: taxon_id
    #         type: integer
    #         description: Reference to taxonomy
    #       - name: plot_id
    #         type: string
    #         description: Reference to plot
    #       - name: date_observed
    #         type: date
    #       - name: latitude
    #         type: float
    #       - name: longitude
    #         type: float
    #       - name: geometry
    #         type: geometry
    #         description: Point geometry (WKT or GeoJSON)
    #
    #   # Link to reference entities
    #   links:
    #     - entity: taxonomy                  # Reference entity name
    #       field: taxon_id                   # Field in this dataset
    #       target_field: id                  # Field in reference entity
    #     - entity: plots
    #       field: plot_id
    #       target_field: plot_code
    #
    #   # Import options
    #   options:
    #     mode: replace                       # Import mode: replace, append, upsert
    #     chunk_size: 10000                   # Number of rows per batch
    #     geometry_field: geometry            # Name of geometry field (if spatial)

  # ---------------------------------------------------------------------------
  # REFERENCES
  # ---------------------------------------------------------------------------
  # References contain master data that datasets reference
  # Example use cases: taxonomy, geographic regions, classifications

  references:
    # Uncomment and customize the examples below:

    # Example 1: FLAT REFERENCE (simple list)
    # my_taxonomy:
    #   kind: flat                            # Reference type: flat, nested, spatial
    #   description: Taxonomic reference data
    #
    #   connector:
    #     type: file
    #     format: csv
    #     path: imports/taxonomy.csv
    #
    #   schema:
    #     id_field: id
    #     fields:
    #       - name: full_name
    #         type: string
    #       - name: family
    #         type: string
    #       - name: genus
    #         type: string
    #       - name: species
    #         type: string
    #
    #   options:
    #     mode: replace

    # Example 2: NESTED REFERENCE (hierarchical data)
    # my_taxonomy_nested:
    #   kind: nested                          # For hierarchical data
    #   description: Hierarchical taxonomy
    #
    #   connector:
    #     type: file
    #     format: csv
    #     path: imports/taxonomy.csv
    #
    #   schema:
    #     id_field: id
    #     fields:
    #       - name: full_name
    #         type: string
    #       - name: rank
    #         type: string
    #       - name: parent_id
    #         type: integer
    #
    #   # Hierarchy configuration
    #   hierarchy:
    #     parent_field: parent_id             # Field containing parent ID
    #     rank_field: rank                    # Field containing hierarchy level
    #     ranks: [family, genus, species]     # Hierarchy levels (top to bottom)
    #
    #   options:
    #     mode: replace

    # Example 3: SPATIAL REFERENCE (geographic features)
    # my_shapes:
    #   kind: spatial                         # For geographic data
    #   description: Geographic reference features
    #
    #   connector:
    #     type: file_multi_feature            # Special connector for multiple shapefiles
    #     sources:
    #       - name: Provinces
    #         path: imports/shapes/provinces.gpkg
    #         name_field: province_name
    #       - name: EcoZones
    #         path: imports/shapes/ecozones.shp
    #         name_field: zone_name
    #
    #   schema:
    #     id_field: id
    #     fields:
    #       - name: name
    #         type: string
    #       - name: location
    #         type: geometry
    #       - name: entity_type
    #         type: string
    #
    #   options:
    #     mode: replace

# =============================================================================
# METADATA (Optional)
# =============================================================================
# Add metadata about your import configuration

metadata:
  # project: My Biodiversity Project
  # author: Your Name
  # description: Import configuration for biodiversity monitoring data
  # created: 2025-01-22
  # version: 1.0

# =============================================================================
# QUICK START GUIDE
# =============================================================================
#
# 1. Define your entities:
#    - Start with references (master data)
#    - Then add datasets that link to references
#
# 2. Configure connectors:
#    - Specify source type and location
#    - Supported formats: CSV, Excel, JSON, GeoJSON, GeoPackage, Shapefile
#
# 3. Define schema:
#    - List fields to import with their types
#    - Supported types: string, integer, float, date, datetime, boolean, geometry
#
# 4. Set up links:
#    - Connect datasets to references via foreign keys
#    - Ensures data integrity and enables advanced queries
#
# 5. Run import:
#    niamoto import
#
# For more examples and documentation, visit: https://docs.niamoto.org

"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _write_transform_yaml_with_comments(file_path: str) -> None:
        """Write transform.yml with EntityRegistry-aware comments."""
        content = """# Niamoto Transform Configuration
# This file defines data transformations and statistical analyses
# Documentation: https://docs.niamoto.org/transform-configuration

# =============================================================================
# TRANSFORMATION GROUPS
# =============================================================================
# Each group processes data for a specific entity and generates widgets
# Groups reference entities defined in import.yml (can be any custom entity)

# ---------------------------------------------------------------------------
# Example 1: Hierarchical Reference Entity (e.g., Taxonomy, Classifications)
# ---------------------------------------------------------------------------
#
# - group_by: my_taxonomy              # Your reference entity name (from import.yml)
#   sources:
#     - name: obs_by_taxonomy          # Local source identifier
#       data: my_occurrences           # Your dataset entity (from import.yml)
#       grouping: my_taxonomy          # Entity to group by
#       relation:
#         plugin: nested_set           # For hierarchical data
#         key: taxon_id                # Foreign key in dataset
#         ref_key: id                  # Primary key in reference
#         fields:
#           parent: parent_id          # Parent field
#           left: lft                  # Left boundary
#           right: rght                # Right boundary
#
#   widgets_data:
#     general_info:
#       plugin: field_aggregator
#       params:
#         fields:
#           - source: my_taxonomy      # Reference entity
#             field: full_name
#             target: name
#           - source: my_taxonomy
#             field: rank
#             target: rank
#           - source: obs_by_taxonomy  # Source name (defined above)
#             field: id
#             target: observations_count
#             transformation: count
#
#     habitat_distribution:
#       plugin: categorical_distribution
#       params:
#         source: obs_by_taxonomy
#         field: habitat_type
#         target: by_habitat

# ---------------------------------------------------------------------------
# Example 2: Flat Entity (e.g., Sites, Plots, Stations)
# ---------------------------------------------------------------------------
#
# - group_by: my_sites                 # Your entity name (from import.yml)
#   sources:
#     - name: obs_by_site
#       data: my_occurrences
#       grouping: my_sites
#       relation:
#         plugin: direct_reference     # Simple foreign key
#         key: site_id
#         ref_key: site_code
#
#   widgets_data:
#     general_info:
#       plugin: field_aggregator
#       params:
#         fields:
#           - source: my_sites
#             field: name
#             target: site_name
#           - source: my_sites
#             field: elevation
#             target: elevation
#             units: m
#           - source: obs_by_site
#             field: id
#             target: species_count
#             transformation: count_distinct
#
#     statistics:
#       plugin: statistical_summary
#       params:
#         source: obs_by_site
#         field: diameter
#         target: dbh_stats
#         stats: [min, max, mean, median]

# ---------------------------------------------------------------------------
# Example 3: Spatial Reference Entity (e.g., Regions, Zones)
# ---------------------------------------------------------------------------
#
# - group_by: my_regions               # Your spatial entity (from import.yml)
#   sources:
#     - name: obs_by_region
#       data: my_occurrences
#       grouping: my_regions
#       relation:
#         plugin: spatial              # Spatial join
#         geometry_field: location
#         ref_geometry_field: boundary
#
#   widgets_data:
#     general_info:
#       plugin: field_aggregator
#       params:
#         fields:
#           - source: my_regions
#             field: name
#             target: region_name
#           - source: my_regions
#             field: area_km2
#             target: area
#           - source: obs_by_region
#             field: id
#             target: total_obs
#             transformation: count

# =============================================================================
# AVAILABLE TRANSFORMER PLUGINS
# =============================================================================

# --- DATA EXTRACTION ---
# field_aggregator         : Combine and transform fields from multiple sources
# direct_attribute         : Extract a single field value
# geospatial_extractor     : Extract and format spatial data (WKT, GeoJSON, coordinates)
# multi_column_extractor   : Extract multiple columns at once

# --- STATISTICAL ANALYSIS ---
# statistical_summary      : Calculate min, max, mean, median, std, percentiles
# binned_distribution      : Create histogram bins (e.g., diameter classes)
# categorical_distribution : Count occurrences by category
# top_ranking              : Find top N items (supports hierarchical data)
# binary_counter           : Count true/false, yes/no values

# --- TIME SERIES ---
# time_series_analysis     : Analyze temporal patterns (phenology, seasonality)

# --- AGGREGATION ---
# database_aggregator      : Complex SQL aggregations
# class_object_*           : Work with pre-computed class objects

# --- GEOSPATIAL ---
# shape_processor          : Simplify and process geometries
# raster_stats             : Extract statistics from raster layers
# vector_overlay           : Spatial overlay operations

# --- ADVANCED ---
# transform_chain          : Chain multiple transformations
# custom_calculator        : Apply custom formulas and calculations
# reference_resolver       : Resolve references between entities

# =============================================================================
# RELATION PLUGINS (for sources.relation)
# =============================================================================
# nested_set               : For hierarchical data (taxonomy, categories)
# direct_reference         : Simple foreign key relationship
# join_table               : Many-to-many via junction table
# spatial                  : Spatial join (point-in-polygon, intersects)
# stats_loader             : Load pre-computed statistics

# =============================================================================
# TIPS
# =============================================================================
# 1. Entity names (group_by, data, grouping) must match import.yml
# 2. Source names are local to each group (can be reused across groups)
# 3. Field references use source name, not entity name
# 4. Use descriptive widget_ids - they become keys in exported JSON
# 5. Start with empty list and add transformations as needed
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _write_export_yaml_with_comments(file_path: str) -> None:
        """Write export.yml with EntityRegistry-aware comments."""
        content = """# Niamoto Export Configuration
# This file defines how to export data and generate visualizations
# Documentation: https://docs.niamoto.org/export-configuration

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
  #   # Dynamic pages from transformation groups
  #   # Note: group_by must match a transformation group from transform.yml
  #   groups:
  #     - group_by: my_taxonomy          # Entity name (matches transform.yml)
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
    def get_imports_config(self) -> GenericImportConfig:
        """
        Get the generic import configuration from import.yml.

        Returns:
            GenericImportConfig: Typed import configuration with entities.references and entities.datasets

        Raises:
            ConfigurationError: If import.yml is missing or doesn't follow the entities schema
        """
        if not self.imports:
            raise ConfigurationError(
                config_key="imports",
                message="No import sources configured",
                details={"imports_file": "import.yml"},
            )

        # Return typed GenericImportConfig only
        if self._generic_import_config is not None:
            return self._generic_import_config

        if isinstance(self.imports, GenericImportConfig):
            self._generic_import_config = self.imports
            return self._generic_import_config

        if isinstance(self.imports, dict) and "entities" in self.imports:
            self._generic_import_config = GenericImportConfig.from_dict(self.imports)
            return self._generic_import_config

        raise ConfigurationError(
            config_key="imports",
            message="Invalid import configuration - must use entities.references/datasets schema",
            details={
                "current_type": type(self.imports).__name__,
                "required_schema": "entities: { references: {...}, datasets: {...} }",
            },
        )

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
