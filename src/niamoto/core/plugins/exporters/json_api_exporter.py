# src/niamoto/core/plugins/exporters/json_api_exporter.py

"""
JSON API Exporter plugin for generating static JSON API files.

This exporter generates:
- Detail JSON files for individual entities (taxon/1.json, plot/2.json, etc.)
- Index JSON files listing all entities of a type (all_taxa.json, all_plots.json, etc.)
- Optional metadata files with export information

It supports flexible data mapping, field selection, and custom generators for calculated fields.
"""

import json
import logging
import gzip
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

# Check if we're in CLI context for progress display
try:
    from niamoto.cli.utils.progress import ProgressManager

    CLI_CONTEXT = True
except ImportError:
    CLI_CONTEXT = False
    ProgressManager = None

# Import Progress for type annotations
from rich.progress import Progress

from niamoto.common.database import Database
from niamoto.common.exceptions import ConfigurationError, ProcessError
from niamoto.core.plugins.base import ExporterPlugin, PluginType, register
from niamoto.core.plugins.models import TargetConfig
from niamoto.core.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


# Pydantic models for configuration validation
class JsonOptions(BaseModel):
    """Options for JSON file generation."""

    indent: Optional[int] = 4
    ensure_ascii: bool = False
    compress: bool = False
    minify: bool = False
    exclude_null: bool = False
    geometry_precision: Optional[int] = None
    max_array_length: Optional[int] = None

    @field_validator("minify")
    def validate_minify(cls, v, info):
        """Ensure minify and indent are not both set."""
        if v and info.data.get("indent"):
            raise ValueError("Cannot use both 'indent' and 'minify' options")
        return v


class ErrorHandling(BaseModel):
    """Error handling configuration."""

    continue_on_error: bool = True
    log_errors: bool = True
    error_file: Optional[str] = "export_errors.json"


class MetadataConfig(BaseModel):
    """Metadata generation configuration."""

    generate: bool = True
    include_stats: bool = True
    include_schema: bool = False


class IndexStructure(BaseModel):
    """Structure configuration for index files."""

    total_key: str = "total"
    list_key: str = "{group}"
    include_total: bool = True


class FieldMapping(BaseModel):
    """Configuration for a field mapping."""

    source: Optional[str] = None
    fields: Optional[List[Union[str, Dict[str, Any]]]] = None
    generator: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class DetailConfig(BaseModel):
    """Configuration for detail file generation."""

    pass_through: bool = True
    fields: Optional[List[Union[str, Dict[str, Any]]]] = None


class IndexConfig(BaseModel):
    """Configuration for index file generation."""

    fields: List[Union[str, Dict[str, Any]]]


class GroupConfig(BaseModel):
    """Configuration for a data group."""

    group_by: str
    data_source: Optional[str] = None
    detail: Optional[DetailConfig] = Field(default_factory=lambda: DetailConfig())
    index: Optional[IndexConfig] = None
    transformer_plugin: Optional[str] = None
    transformer_params: Optional[Dict[str, Any]] = None
    json_options: Optional[JsonOptions] = None


class JsonApiExporterParams(BaseModel):
    """Parameters for the JSON API exporter."""

    output_dir: str
    detail_output_pattern: str = "{group}/{id}.json"
    index_output_pattern: str = "all_{group}.json"
    index_structure: IndexStructure = Field(default_factory=IndexStructure)
    json_options: JsonOptions = Field(default_factory=JsonOptions)
    error_handling: ErrorHandling = Field(default_factory=ErrorHandling)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    size_optimization: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Dict[str, Any]]] = None


@register("json_api_exporter", PluginType.EXPORTER)
class JsonApiExporter(ExporterPlugin):
    """Generates static JSON API files based on the export configuration."""

    def __init__(self, db: Database):
        """Initialize the exporter with database connection."""
        super().__init__(db)
        self.errors: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {
            "start_time": None,
            "end_time": None,
            "groups_processed": {},
            "total_files_generated": 0,
            "errors_count": 0,
        }

    def export(
        self,
        target_config: TargetConfig,
        repository: Database,
        group_filter: Optional[str] = None,
    ) -> None:
        """
        Execute the JSON API export process.

        Args:
            target_config: The validated configuration for this export target
            repository: The Database instance to fetch data from
            group_filter: Optional filter to process only specific groups
        """
        logger.info(f"Starting JSON API export for target: '{target_config.name}'")
        self.stats["start_time"] = datetime.now()

        try:
            # Validate parameters
            params = JsonApiExporterParams.model_validate(target_config.params)
            output_dir = Path(params.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Process each group
            groups_to_process = target_config.groups or []
            if group_filter:
                groups_to_process = [
                    g for g in groups_to_process if g.group_by == group_filter
                ]

            if CLI_CONTEXT and ProgressManager:
                # Use unified progress manager when in CLI context
                progress_manager = ProgressManager()
                with progress_manager.progress_context() as pm:
                    for group_config in groups_to_process:
                        self._process_group_with_progress_manager(
                            group_config, params, repository, output_dir, pm
                        )
            else:
                # Fallback to rich progress for backwards compatibility
                from rich.progress import SpinnerColumn, BarColumn, TextColumn

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                ) as progress:
                    for group_config in groups_to_process:
                        self._process_group(
                            group_config, params, repository, output_dir, progress
                        )

            # Generate metadata if requested
            if params.metadata.generate:
                self._generate_metadata(output_dir, params, target_config)

            # Save errors if any
            if self.errors and params.error_handling.log_errors:
                self._save_errors(output_dir, params)

        except Exception as e:
            logger.error(f"JSON API export failed: {str(e)}")
            raise ProcessError(f"JSON API export failed: {str(e)}")
        finally:
            self.stats["end_time"] = datetime.now()
            logger.info(
                f"JSON API export completed. Stats: {json.dumps(self.stats, default=str)}"
            )

    def _process_group(
        self,
        group_config: GroupConfig,
        params: JsonApiExporterParams,
        repository: Database,
        output_dir: Path,
        progress: Progress,
    ) -> None:
        """Process a single data group."""
        group_name = group_config.group_by
        logger.info(f"Processing group: {group_name}")

        # Get data for this group
        data_source = group_config.data_source or f"{group_name}_data"
        group_data = self._fetch_group_data(repository, data_source, group_name)

        if not group_data:
            logger.warning(f"No data found for group: {group_name}")
            return

        # Apply filters if configured
        if params.filters and group_name in params.filters:
            group_data = self._apply_filters(group_data, params.filters[group_name])

        # Initialize stats for this group
        self.stats["groups_processed"][group_name] = {
            "total_items": len(group_data),
            "detail_files": 0,
            "index_generated": False,
            "errors": 0,
        }

        # Create mapper for this group
        mapper = DataMapper(group_config, params)

        # Process group data sequentially
        generated_items = self._process_group_sequential(
            group_data,
            group_name,
            group_config,
            params,
            output_dir,
            progress,
            mapper,
        )

        # Generate index file if configured, but only for items that generated files
        if (
            hasattr(group_config, "index")
            and group_config.index
            and params.index_output_pattern
        ):
            json_options = self._merge_json_options(
                group_config.json_options, params.json_options
            )
            self._generate_index_file(
                generated_items,
                group_name,
                group_config,
                params,
                output_dir,
                mapper,
                json_options,
            )

    def _process_group_sequential(
        self,
        group_data: List[Dict[str, Any]],
        group_name: str,
        group_config: GroupConfig,
        params: JsonApiExporterParams,
        output_dir: Path,
        progress: Progress,
        mapper: "DataMapper",
    ) -> List[Dict[str, Any]]:
        """Process group data sequentially. Returns items that generated files."""
        # Capture start time
        import time

        start_time = time.time()

        task = progress.add_task(
            f"[green]Generating {group_name} JSON files...[/green]",
            total=len(group_data),
        )

        generated_items = []

        for item in group_data:
            try:
                # Use group-specific JSON options if available
                json_options = self._merge_json_options(
                    group_config.json_options, params.json_options
                )
                file_generated = self._generate_detail_file(
                    item,
                    group_name,
                    group_config,
                    params,
                    output_dir,
                    mapper,
                    json_options,
                )
                if file_generated:
                    generated_items.append(item)
                    self.stats["groups_processed"][group_name]["detail_files"] += 1
            except Exception as e:
                self._handle_export_error(e, group_name, item, params)
            finally:
                current_duration = time.time() - start_time
                progress.update(
                    task,
                    advance=1,
                    description=f"[green]Generating {group_name} JSON files • {current_duration:.1f}s[/green]",
                )

        # Update task description to show completion
        duration = time.time() - start_time
        progress.update(
            task,
            description=f"[green][✓] {group_name} export completed • {duration:.1f}s[/green]",
        )

        return generated_items

    def _process_group_with_progress_manager(
        self,
        group_config: GroupConfig,
        params: JsonApiExporterParams,
        repository: Database,
        output_dir: Path,
        progress_manager: "ProgressManager",
    ) -> None:
        """Process a single data group using ProgressManager."""
        group_name = group_config.group_by
        logger.info(f"Processing group: {group_name}")

        # Get data for this group
        data_source = group_config.data_source or f"{group_name}_data"
        group_data = self._fetch_group_data(repository, data_source, group_name)

        if not group_data:
            logger.warning(f"No data found for group: {group_name}")
            progress_manager.add_warning(f"No data found for group: {group_name}")
            return

        # Apply filters if configured
        if params.filters and group_name in params.filters:
            group_data = self._apply_filters(group_data, params.filters[group_name])

        # Initialize stats for this group
        self.stats["groups_processed"][group_name] = {
            "total_items": len(group_data),
            "detail_files": 0,
            "index_generated": False,
            "errors": 0,
        }

        # Create mapper for this group
        mapper = DataMapper(group_config, params)

        # Add progress task
        task_name = f"export_{group_name}"
        progress_manager.add_task(
            task_name, f"Generating {group_name} JSON files", total=len(group_data)
        )

        # Process group data
        generated_items = []
        for item in group_data:
            try:
                # Use group-specific JSON options if available
                json_options = self._merge_json_options(
                    group_config.json_options, params.json_options
                )
                file_generated = self._generate_detail_file(
                    item,
                    group_name,
                    group_config,
                    params,
                    output_dir,
                    mapper,
                    json_options,
                )
                if file_generated:
                    generated_items.append(item)
                    self.stats["groups_processed"][group_name]["detail_files"] += 1
            except Exception as e:
                self._handle_export_error(e, group_name, item, params)
                progress_manager.add_error(
                    f"Error processing {group_name} item: {str(e)}"
                )

            progress_manager.update_task(task_name, advance=1)

        progress_manager.complete_task(
            task_name, f"Generated {len(generated_items)} {group_name} files"
        )

        # Generate index file if configured
        if (
            hasattr(group_config, "index")
            and group_config.index
            and params.index_output_pattern
        ):
            json_options = self._merge_json_options(
                group_config.json_options, params.json_options
            )
            self._generate_index_file(
                generated_items,
                group_name,
                group_config,
                params,
                output_dir,
                mapper,
                json_options,
            )

    def _generate_detail_file(
        self,
        item: Dict[str, Any],
        group_name: str,
        group_config: GroupConfig,
        params: JsonApiExporterParams,
        output_dir: Path,
        mapper: "DataMapper",
        json_options: JsonOptions,
    ) -> bool:
        """Generate a detail JSON file for a single item. Returns True if file was generated."""
        # Get item ID - try group-specific ID field first, then 'id'
        item_id = item.get(f"{group_name}_id") or item.get("id")
        if not item_id:
            raise ValueError(
                f"Item in group {group_name} has no '{group_name}_id' or 'id' field"
            )

        # Apply transformer if configured
        if (
            hasattr(group_config, "transformer_plugin")
            and group_config.transformer_plugin
        ):
            output_data = self._apply_transformer(item, group_config)
        else:
            # Map data if needed
            if group_config.detail and not group_config.detail.pass_through:
                output_data = mapper.map_detail_data(item)
            else:
                output_data = item

        # For transformer output that's a list (like DwC occurrences),
        # we still write it as the detail file content
        if isinstance(output_data, list):
            # Skip empty lists (e.g., taxons with no occurrences)
            if not output_data:
                logger.debug(f"Skipping empty output for {group_name} {item_id}")
                return False

            # Generate file path for the item
            file_path = output_dir / params.detail_output_pattern.format(
                group=group_name, id=item_id
            )
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the list as the file content
            self._write_json_file(file_path, output_data, json_options)
            self.stats["total_files_generated"] += 1
            return True
        else:
            # Normal single item output
            file_path = output_dir / params.detail_output_pattern.format(
                group=group_name, id=item_id
            )
            file_path.parent.mkdir(parents=True, exist_ok=True)

            self._write_json_file(file_path, output_data, json_options)
            self.stats["total_files_generated"] += 1
            return True

    def _apply_transformer(
        self, item: Dict[str, Any], group_config: GroupConfig
    ) -> Any:
        """Apply a transformer plugin to the data."""
        try:
            # Get the transformer plugin
            transformer_class = PluginRegistry.get_plugin(
                group_config.transformer_plugin, PluginType.TRANSFORMER
            )

            if not transformer_class:
                raise ConfigurationError(
                    f"Transformer plugin '{group_config.transformer_plugin}' not found"
                )

            # Instantiate and configure the transformer
            transformer = transformer_class(self.db)

            # Validate transformer params if provided
            if hasattr(transformer, "config_model") and group_config.transformer_params:
                validated_params = transformer.config_model.model_validate(
                    group_config.transformer_params
                )
            else:
                validated_params = group_config.transformer_params or {}

            # Apply transformation
            return transformer.transform(item, validated_params)

        except Exception as e:
            logger.error(f"Transformer error: {str(e)}")
            raise ProcessError(f"Failed to apply transformer: {str(e)}")

    def _generate_index_file(
        self,
        group_data: List[Dict[str, Any]],
        group_name: str,
        group_config: GroupConfig,
        params: JsonApiExporterParams,
        output_dir: Path,
        mapper: "DataMapper",
        json_options: JsonOptions,
    ) -> None:
        """Generate an index JSON file for a group."""
        logger.info(f"Generating index file for group: {group_name}")

        # Generate file path
        file_path = output_dir / params.index_output_pattern.format(group=group_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Map index data
        index_items = []
        for item in group_data:
            try:
                mapped_item = mapper.map_index_data(item, group_name, params)
                index_items.append(mapped_item)
            except Exception as e:
                self._handle_export_error(e, group_name, item, params)

        # Build index structure
        list_key = params.index_structure.list_key.format(group=group_name)
        index_data = {list_key: index_items}

        if params.index_structure.include_total:
            index_data[params.index_structure.total_key] = len(index_items)

        # Write JSON file
        self._write_json_file(file_path, index_data, json_options)
        self.stats["groups_processed"][group_name]["index_generated"] = True
        self.stats["total_files_generated"] += 1

    def _write_json_file(
        self, file_path: Path, data: Any, json_options: JsonOptions
    ) -> None:
        """Write data to a JSON file with specified options."""
        # Apply size optimizations
        if (
            json_options.exclude_null
            or json_options.geometry_precision
            or json_options.max_array_length
        ):
            data = self._optimize_data_size(data, json_options)

        # Prepare JSON dump kwargs
        dump_kwargs = {"ensure_ascii": json_options.ensure_ascii}

        if json_options.minify:
            dump_kwargs["separators"] = (",", ":")
        elif json_options.indent:
            dump_kwargs["indent"] = json_options.indent

        # Write file
        if json_options.compress:
            with gzip.open(f"{file_path}.gz", "wt", encoding="utf-8") as f:
                json.dump(data, f, **dump_kwargs)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, **dump_kwargs)

    def _optimize_data_size(self, data: Any, json_options: JsonOptions) -> Any:
        """Apply size optimizations to data before JSON serialization."""
        if isinstance(data, dict):
            optimized = {}
            for key, value in data.items():
                # Skip null values if requested
                if json_options.exclude_null and value is None:
                    continue
                optimized[key] = self._optimize_data_size(value, json_options)
            return optimized

        elif isinstance(data, list):
            # Limit array length if specified
            if (
                json_options.max_array_length
                and len(data) > json_options.max_array_length
            ):
                data = data[: json_options.max_array_length]

            return [self._optimize_data_size(item, json_options) for item in data]

        elif isinstance(data, float) and json_options.geometry_precision is not None:
            # Round floating point numbers for coordinates
            return round(data, json_options.geometry_precision)

        return data

    def _merge_json_options(
        self, group_options: Optional[Dict[str, Any]], default_options: JsonOptions
    ) -> JsonOptions:
        """Merge group-specific JSON options with default options."""
        if not group_options:
            return default_options

        # Start with default options as a dict
        merged = default_options.model_dump()

        # Override with group-specific options
        merged.update(group_options)

        # Convert back to JsonOptions object
        return JsonOptions.model_validate(merged)

    def _fetch_group_data(
        self, repository: Database, data_source: str, group_name: str
    ) -> List[Dict[str, Any]]:
        """Fetch data for a group from the repository."""
        try:
            # Use group_name as table name (assumes table exists with same name)
            table_name = group_name

            # Query all data from the table
            from sqlalchemy import text

            query = text(f"SELECT * FROM {table_name}")

            with repository.engine.connect() as connection:
                result_proxy = connection.execute(query)
                rows = result_proxy.fetchall()
                columns = result_proxy.keys()

                if rows:
                    result = []
                    for row in rows:
                        row_dict = dict(zip(columns, row))

                        # Start with an empty item - don't force ID mapping
                        item = {}

                        # Merge all columns into the item
                        for col_name, col_value in row_dict.items():
                            if col_value:  # If the column has data
                                try:
                                    # Try to parse as JSON first
                                    if isinstance(col_value, str):
                                        data = json.loads(col_value)
                                    else:
                                        data = col_value

                                    # Always preserve the original column data
                                    item[col_name] = data

                                    # If it's a dict, also merge its contents for backward compatibility
                                    if isinstance(data, dict):
                                        item.update(data)

                                except (json.JSONDecodeError, TypeError):
                                    # If not JSON, store as-is under column name
                                    item[col_name] = col_value

                        result.append(item)

                    logger.info(f"Fetched {len(result)} items for group: {group_name}")
                    return result
                else:
                    logger.warning(f"No data found for group: {group_name}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching data for group {group_name}: {str(e)}")
            return []

    def _apply_filters(
        self, data: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filters to data."""
        filtered_data = []

        for item in data:
            include = True
            for field, value in filters.items():
                item_value = item.get(field)

                # Handle list filters (item value must be in the list)
                if isinstance(value, list):
                    if item_value not in value:
                        include = False
                        break
                # Handle boolean filters
                elif isinstance(value, bool):
                    if bool(item_value) != value:
                        include = False
                        break
                # Handle exact match
                else:
                    if item_value != value:
                        include = False
                        break

            if include:
                filtered_data.append(item)

        return filtered_data

    def _handle_export_error(
        self,
        error: Exception,
        group_name: str,
        item: Dict[str, Any],
        params: JsonApiExporterParams,
    ) -> None:
        """Handle an error during export."""
        error_info = {
            "group": group_name,
            "item_id": item.get("id", "unknown"),
            "error": str(error),
            "timestamp": datetime.now().isoformat(),
        }

        self.errors.append(error_info)
        self.stats["errors_count"] += 1
        self.stats["groups_processed"][group_name]["errors"] += 1

        if params.error_handling.log_errors:
            logger.error(
                f"Export error for {group_name}/{item.get('id', 'unknown')}: {str(error)}"
            )

        if not params.error_handling.continue_on_error:
            raise error

    def _save_errors(self, output_dir: Path, params: JsonApiExporterParams) -> None:
        """Save error log to file."""
        if params.error_handling.error_file:
            error_file = output_dir / params.error_handling.error_file
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(self.errors, f, indent=2, default=str)

    def _generate_metadata(
        self,
        output_dir: Path,
        params: JsonApiExporterParams,
        target_config: TargetConfig,
    ) -> None:
        """Generate metadata file for the export."""
        metadata = {
            "export_name": target_config.name,
            "export_timestamp": datetime.now().isoformat(),
            "exporter": "json_api_exporter",
            "version": "1.0.0",
        }

        if params.metadata.include_stats:
            metadata["statistics"] = {
                "duration_seconds": (
                    self.stats["end_time"] - self.stats["start_time"]
                ).total_seconds()
                if self.stats["end_time"]
                else None,
                "groups_processed": self.stats["groups_processed"],
                "total_files_generated": self.stats["total_files_generated"],
                "errors_count": self.stats["errors_count"],
            }

        if params.metadata.include_schema:
            # TODO: Generate JSON Schema for exported data
            metadata["schema"] = {}

        metadata_file = output_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        self.stats["total_files_generated"] += 1


class DataMapper:
    """Handles data mapping and field generation for JSON export."""

    def __init__(self, group_config: GroupConfig, params: JsonApiExporterParams):
        """Initialize the mapper with configuration."""
        self.group_config = group_config
        self.params = params
        self._group_context = None
        self.generators = self._initialize_generators()

    def _initialize_generators(self) -> Dict[str, callable]:
        """Initialize field generators."""
        return {
            "endpoint_url": self._generate_endpoint_url,
            "unique_occurrence_id": self._generate_unique_id,
            "unique_event_id": self._generate_unique_id,
            "unique_identification_id": self._generate_unique_id,
            "extract_specific_epithet": self._extract_specific_epithet,
            "format_media_urls": self._format_media_urls,
        }

    def map_detail_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Map data for detail file generation."""
        if not self.group_config.detail or not self.group_config.detail.fields:
            return item

        return self._map_fields(item, self.group_config.detail.fields)

    def map_index_data(
        self, item: Dict[str, Any], group_name: str, params: JsonApiExporterParams
    ) -> Dict[str, Any]:
        """Map data for index file generation."""
        if not self.group_config.index:
            return item

        # Add group context for generators BEFORE mapping
        self._group_context = {"group_name": group_name, "params": params, "item": item}

        # Debug: log the first few items
        if item.get("id") in [1, 2, 3]:
            logger.info(
                f"DEBUG: Processing item {item.get('id')} with keys: {list(item.keys())}"
            )
            if "name" in item:
                logger.info(f"DEBUG: name field structure: {item['name']}")
            logger.info(f"DEBUG: field configs: {self.group_config.index.fields}")

        mapped = self._map_fields(item, self.group_config.index.fields)

        # Debug: log mapped result
        if item.get("id") in [1, 2, 3]:
            logger.info(f"DEBUG: Mapped result for item {item.get('id')}: {mapped}")

        return mapped

    def _map_fields(
        self, data: Dict[str, Any], field_configs: List[Any]
    ) -> Dict[str, Any]:
        """Map fields according to configuration."""
        result = {}

        for field_config in field_configs:
            # Handle IndexApiFieldMapping objects
            if hasattr(field_config, "mapping"):
                mapping = field_config.mapping
                self._process_complex_field(data, mapping, result)
            elif isinstance(field_config, str):
                # Simple field mapping: "field_name" or "out_name: source_name"
                if ":" in field_config:
                    out_name, source_name = field_config.split(":", 1)
                    result[out_name.strip()] = self._get_nested_value(
                        data, source_name.strip()
                    )
                else:
                    result[field_config] = self._get_nested_value(data, field_config)

            elif isinstance(field_config, dict):
                # Complex field mapping
                self._process_complex_field(data, field_config, result)

        return result

    def _process_complex_field(
        self, data: Dict[str, Any], field_config: Dict[str, Any], result: Dict[str, Any]
    ) -> None:
        """Process a complex field configuration."""
        try:
            for out_name, config in field_config.items():
                if isinstance(config, str):
                    # Direct mapping
                    result[out_name] = self._get_nested_value(data, config)

                elif isinstance(config, dict):
                    if "generator" in config:
                        # Use generator
                        generator_name = config["generator"]
                        if generator_name in self.generators:
                            result[out_name] = self.generators[generator_name](
                                data, config.get("params", {})
                            )
                        else:
                            logger.warning(f"Unknown generator: {generator_name}")

                    elif "source" in config:
                        # Handle different source types
                        source = config["source"]
                        field = config.get("field", out_name)

                        if source in ["taxon_ref", "plot_ref", "shape_ref"]:
                            # Reference table access - for now, log and skip
                            # TODO: Implement table joins
                            logger.warning(
                                f"Reference table access not yet implemented: {source}"
                            )
                            result[out_name] = None
                        else:
                            # Source from current data
                            source_data = self._get_nested_value(data, source)
                            if source_data is not None and "fields" in config:
                                # Select specific fields from source
                                selected = {}
                                for field_name in config["fields"]:
                                    if (
                                        isinstance(source_data, dict)
                                        and field_name in source_data
                                    ):
                                        selected[field_name] = source_data[field_name]
                                result[out_name] = selected
                            else:
                                result[out_name] = (
                                    self._get_nested_value(source_data, field)
                                    if source_data
                                    else None
                                )

                    elif "field" in config:
                        # Simple field access with alternative syntax
                        result[out_name] = self._get_nested_value(data, config["field"])
                    else:
                        # Fallback for unknown config structure
                        logger.warning(
                            f"Unknown field config structure for {out_name}: {config}"
                        )
                        result[out_name] = None
        except Exception as e:
            logger.error(f"Error in _process_complex_field: {e}")
            logger.error(f"Field config: {field_config}")
            logger.error(f"Data keys: {list(data.keys()) if data else 'None'}")
            raise

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        if not data or path.startswith("@"):
            # Handle special references or empty data
            return self._resolve_reference(data, path) if path.startswith("@") else None

        keys = path.split(".")
        current = data

        for i, key in enumerate(keys):
            if current is None:
                return None
            elif isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, str) and i < len(keys) - 1:
                # Try to parse JSON string if we need to go deeper
                try:
                    import json

                    current = json.loads(current)
                    if isinstance(current, dict):
                        current = current.get(key)
                    else:
                        return None
                except (json.JSONDecodeError, AttributeError):
                    return None
            else:
                return None

        return current

    def _resolve_reference(self, data: Dict[str, Any], reference: str) -> Any:
        """Resolve special @ references."""
        # Remove @ prefix
        ref_path = reference[1:]

        if ref_path.startswith("source."):
            # Reference to source data
            return self._get_nested_value(data, ref_path[7:])
        elif ref_path.startswith("taxon.") and hasattr(self, "_group_context"):
            # Reference to taxon data (for Darwin Core)
            # This would need access to the parent taxon data
            # Implementation depends on your data structure
            pass

        return None

    # Generator methods
    def _generate_endpoint_url(
        self, data: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Generate endpoint URL for an item."""
        base_path = params.get("base_path", "/api")
        group_name = self._group_context.get("group_name", "unknown")
        item_id = data.get("id", "unknown")

        pattern = self._group_context["params"].detail_output_pattern
        path = pattern.format(group=group_name, id=item_id)

        return f"{base_path}/{path}"

    def _generate_unique_id(self, data: Dict[str, Any], params: Dict[str, Any]) -> str:
        """Generate a unique ID with prefix."""
        prefix = params.get("prefix", "")
        source_field = params.get("source_field")

        if source_field:
            value = self._get_nested_value(data, source_field)
            if value:
                return f"{prefix}{value}"

        # Fallback to data ID
        return f"{prefix}{data.get('id', 'unknown')}"

    def _extract_specific_epithet(
        self, data: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Extract specific epithet from scientific name."""
        source_field = params.get("source_field", "full_name")
        full_name = self._get_nested_value(data, source_field)

        if full_name and isinstance(full_name, str):
            parts = full_name.split()
            if len(parts) >= 2:
                return parts[1]

        return ""

    def _format_media_urls(
        self, data: Dict[str, Any], params: Dict[str, Any]
    ) -> List[str]:
        """Format media URLs from a list of media objects."""
        source_list = params.get("source_list")
        url_key = params.get("url_key", "url")

        if source_list:
            media_list = self._get_nested_value(data, source_list)
            if isinstance(media_list, list):
                urls = []
                for media in media_list:
                    if isinstance(media, dict) and url_key in media:
                        urls.append(media[url_key])
                return urls

        return []
