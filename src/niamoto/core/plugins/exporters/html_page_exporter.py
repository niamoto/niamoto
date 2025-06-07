# src/niamoto/core/plugins/exporters/html_page_exporter.py

"""
Exporter plugin responsible for generating a static HTML website.

This exporter uses Jinja2 for templating and orchestrates the rendering of:
- Static pages (e.g., index.html, about.html).
- Index pages for data groups (e.g., list of taxa, list of plots).
- Detail pages for individual items within groups (e.g., details for a specific taxon).

It leverages WidgetPlugins to render specific data visualizations (charts, maps, etc.)
within the detail pages.
"""

import logging
import shutil
import json
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Set, Optional
import importlib.resources

from jinja2 import Environment, FileSystemLoader, select_autoescape, ChoiceLoader
from pydantic import ValidationError
from markdown_it import MarkdownIt
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)

from niamoto.common.database import Database
from niamoto.common.exceptions import ConfigurationError, ProcessError
from niamoto.common.config import Config
from niamoto.core.plugins.base import ExporterPlugin, PluginType, WidgetPlugin, register
from niamoto.core.plugins.models import (
    TargetConfig,
    HtmlExporterParams,
    StaticPageConfig,
    GroupConfigWeb,
)
from niamoto.core.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


@register("html_page_exporter", PluginType.EXPORTER)
class HtmlPageExporter(ExporterPlugin):
    """Generates a static HTML website based on the export configuration."""

    def __init__(self, db: Database):
        """Initialize the exporter with database connection."""
        super().__init__(db)
        self._navigation_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._navigation_js_generated: Set[str] = set()

    def _get_nested_data(
        self, data_dict: Dict[str, Any], key_path: str
    ) -> Optional[Any]:
        """Retrieves data from a nested dictionary using a dot-separated key path."""
        keys = key_path.split(".")
        current_data = data_dict
        for key in keys:
            if isinstance(current_data, dict):
                current_data = current_data.get(key)
                if current_data is None:
                    # logger.debug(f"Key '{key}' not found in path '{key_path}'")
                    return None  # Key not found at this level
            else:
                # logger.debug(f"Cannot access key '{key}' on non-dict element in path '{key_path}'")
                return None  # Tried to access key on non-dict
        return current_data

    def export(
        self,
        target_config: TargetConfig,
        repository: Database,
        group_filter: Optional[str] = None,
    ) -> None:
        """
        Executes the HTML export process.

        Args:
            target_config: The validated configuration for this HTML export target.
            repository: The Database instance to fetch data from.
            group_filter: Optional filter to apply to the groups.
        """
        logger.info(f"Starting HTML page export for target: '{target_config.name}'")

        try:
            # 1. Validate and parse specific HTML exporter parameters
            try:
                html_params = HtmlExporterParams.model_validate(target_config.params)
            except AttributeError:
                html_params = HtmlExporterParams.parse_obj(target_config.params)

            output_dir = Path(html_params.output_dir)
            user_template_dir = Path(html_params.template_dir)

            # --- Modified Directory Clearing Logic ---
            if (
                group_filter is None
            ):  # Only clear the whole directory if exporting everything
                if output_dir.exists() and any(output_dir.iterdir()):
                    try:
                        shutil.rmtree(output_dir)
                    except OSError as e:
                        logger.error(
                            f"Error removing directory {output_dir}: {e}", exc_info=True
                        )
                        raise ProcessError(
                            f"Failed to clear output directory {output_dir}"
                        ) from e
            # Always ensure the base output directory exists
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Output directory ensured: {output_dir}")
            except OSError as e:
                logger.error(
                    f"Error creating directory {output_dir}: {e}", exc_info=True
                )
                raise ProcessError(
                    f"Failed to create output directory {output_dir}"
                ) from e
            # --- End Modified Logic ---

            # 2. Setup Jinja2 environment with ChoiceLoader
            try:
                # Find the path to the default templates within the niamoto package
                default_template_path = (
                    importlib.resources.files("niamoto.publish") / "templates"
                )
            except (ImportError, ModuleNotFoundError):
                logger.error(
                    "Could not locate default Niamoto templates. Ensure 'niamoto.publish' package is correctly installed."
                )
                raise ProcessError("Default template path not found.")

            # Create loaders
            user_loader = FileSystemLoader(
                str(user_template_dir)
            )  # User templates first
            default_loader = FileSystemLoader(str(default_template_path))

            # Create ChoiceLoader
            choice_loader = ChoiceLoader([user_loader, default_loader])

            jinja_env = Environment(
                loader=choice_loader, autoescape=select_autoescape(["html", "xml"])
            )

            # --- Add relative_url filter ---
            def make_relative_url(url, depth=0):
                """Creates proper relative URLs based on page depth."""
                if not isinstance(url, str):
                    return url  # Return as is if not a string

                # Keep absolute URLs and anchors as is
                if url.startswith(
                    ("http://", "https://", "#", "mailto:", "javascript:")
                ):
                    return url

                # Handle root-relative URLs
                if url.startswith("/"):
                    # Convert to relative based on depth
                    # depth=0 means root level, depth=1 means one folder deep, etc.
                    if depth == 0:
                        return url[1:]  # Remove leading slash for root level
                    else:
                        return "../" * depth + url[1:]

                # Already relative URL
                return url

            jinja_env.filters["relative_url"] = make_relative_url
            # ---------------------------------

            logger.debug(
                f"Jinja environment set up with user dir '{user_template_dir}' and default dir '{default_template_path}'"
            )

            # Log available templates for debugging
            try:
                available_templates = jinja_env.list_templates()
                logger.debug(f"Available templates: {available_templates}")
            except Exception as e:
                logger.warning(f"Could not list available templates: {e}")

            # 3. Setup Markdown parser
            md = MarkdownIt()
            logger.debug("Markdown parser initialized.")

            # 4. Copy static assets (default and user-specified)
            self._copy_static_assets(html_params, output_dir)

            # 5. Process static pages defined in the target config
            logger.info(
                f"Processing {len(target_config.static_pages)} static page configurations..."
            )
            self._process_static_pages(
                target_config.static_pages, jinja_env, html_params, output_dir, md
            )

            # 6. Process data groups (index and detail pages)
            self._process_groups(
                target_config.groups,
                jinja_env,
                html_params,
                output_dir,
                repository,
                group_filter,
            )

            logger.info(
                f"HTML export finished successfully for target: '{target_config.name}'"
            )

        except ValidationError as val_err:
            logger.error(
                f"Configuration error in HTML exporter params for target '{target_config.name}': {val_err}"
            )
            raise ConfigurationError(
                config_key="params", message=f"Invalid params for {target_config.name}"
            ) from val_err
        except ProcessError as proc_err:
            logger.error(
                f"Processing error during HTML export for '{target_config.name}': {proc_err}"
            )
            raise  # Re-raise process errors
        except Exception as e:
            logger.error(
                f"Unexpected error during HTML export for target '{target_config.name}': {e}",
                exc_info=True,
            )
            raise ProcessError(
                f"HTML export failed unexpectedly for {target_config.name}"
            ) from e

    def _copy_static_assets(
        self, html_params: HtmlExporterParams, output_dir: Path
    ) -> None:
        """Copies default Niamoto assets (if enabled) and user-specified assets."""
        logger.info("Processing static assets...")
        # 1. Copy default assets if requested
        if html_params.include_default_assets:
            logger.info("Copying default Niamoto assets...")
            parent_module = "niamoto.publish"
            asset_dir_name = "assets"
            try:
                # Use importlib.resources to find the path to the parent module
                parent_module_path_traversable = importlib.resources.files(
                    parent_module
                )
                # Construct the full path to the assets directory
                source_path = Path(parent_module_path_traversable) / asset_dir_name

                if source_path.exists() and source_path.is_dir():
                    # Define target path *including* 'assets' subdirectory
                    target_assets_base_dir = (
                        output_dir / asset_dir_name
                    )  # e.g., exports/web/assets
                    target_assets_base_dir.mkdir(
                        parents=True, exist_ok=True
                    )  # Ensure it exists

                    logger.debug(
                        f"Copying default assets from {source_path} into {target_assets_base_dir}"
                    )

                    # Iterate through items in the source directory (css, js)
                    for item in source_path.iterdir():
                        target_item_path = (
                            target_assets_base_dir / item.name
                        )  # e.g., exports/web/assets/css
                        try:
                            if target_item_path.exists():
                                logger.debug(
                                    f"Removing existing default asset destination: {target_item_path}"
                                )
                                if target_item_path.is_dir():
                                    shutil.rmtree(target_item_path)
                                else:
                                    target_item_path.unlink()

                            if item.is_dir():
                                shutil.copytree(
                                    item, target_item_path, dirs_exist_ok=False
                                )
                            elif item.is_file():
                                shutil.copy2(item, target_item_path)
                        except Exception as copy_err:
                            logger.error(
                                f"Failed to copy default asset item {item.name} to {target_item_path}: {copy_err}",
                                exc_info=True,
                            )
                    logger.info("Default Niamoto assets copied.")
                else:
                    logger.warning(
                        f"Default asset directory '{parent_module}/{asset_dir_name}' resolved to '{source_path}', but it does not exist or is not a directory. Skipping default assets."
                    )

            except (ModuleNotFoundError, TypeError):
                logger.error(
                    f"Could not locate the parent module '{parent_module}' for default Niamoto assets. Skipping default assets."
                )
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred while copying default assets: {e}",
                    exc_info=True,
                )
                # Consider if this should be a fatal error
        else:
            logger.info("Skipping default Niamoto assets as per configuration.")

        # 2. Copy user-specified assets from 'copy_assets_from'
        user_asset_dirs = html_params.copy_assets_from
        if not user_asset_dirs:
            logger.debug("No user-specified asset directories/files to copy.")
            return  # Nothing more to do if no user assets

        logger.info(f"Copying {len(user_asset_dirs)} user-specified asset paths...")
        try:
            user_asset_base_path = Path(Config.get_niamoto_home())
        except Exception as e:
            logger.error(
                f"Could not determine project home directory (NIAMOTO_HOME): {e}. User asset paths may fail."
            )
            user_asset_base_path = Path.cwd()  # Fallback

        for asset_path_str in user_asset_dirs:
            source_path = user_asset_base_path / asset_path_str
            target_path = (
                output_dir / Path(asset_path_str).name
            )  # Copy relative to output root

            if not source_path.exists():
                logger.warning(
                    f"User asset source not found, skipping: {source_path} (relative to {user_asset_base_path})"
                )
                continue

            try:
                if target_path.exists():
                    logger.debug(
                        f"Target user asset directory {target_path} exists, merging contents."
                    )
                # else:
                #     target_path.unlink() # Unlink only relevant if it could be a file

                if source_path.is_dir():
                    logger.debug(
                        f"Copying user assets directory from {source_path} to {target_path}"
                    )
                    shutil.copytree(
                        source_path, target_path, dirs_exist_ok=True
                    )  # Allow merging
                elif source_path.is_file():
                    logger.debug(
                        f"Copying user asset file from {source_path} to {target_path}"
                    )
                    target_path.parent.mkdir(
                        parents=True, exist_ok=True
                    )  # Ensure parent exists for files
                    shutil.copy2(source_path, target_path)
                else:
                    logger.warning(
                        f"User asset source is neither a file nor a directory, skipping: {source_path}"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to copy user assets from {source_path} to {target_path}: {e}",
                    exc_info=True,
                )
                # Consider raising ProcessError

        logger.info("User-specified assets copy process finished.")

    def _process_static_pages(
        self,
        static_pages: List[StaticPageConfig],
        jinja_env: Environment,
        html_params: HtmlExporterParams,
        output_dir: Path,
        md: MarkdownIt,
    ) -> None:
        """Processes each static page configuration."""
        logger.info(f"Processing {len(static_pages)} static pages...")
        if not static_pages:
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(
                "[green]Generating static pages[/green]", total=len(static_pages)
            )

            for page_config in static_pages:
                progress.update(
                    task, description=f"[green]Generating {page_config.name}[/green]"
                )
                logger.debug(
                    f"Processing static page: '{page_config.name}' -> {page_config.output_file}"
                )
                try:
                    template = jinja_env.get_template(page_config.template)

                    # Prepare context
                    context = {
                        "site": html_params.site.model_dump()
                        if html_params.site
                        else {},
                        "navigation": html_params.navigation
                        if html_params.navigation
                        else [],
                        "page": page_config.context.model_dump()
                        if page_config.context
                        else {},
                        "output_file": page_config.output_file,
                    }

                    # Handle content source or markdown
                    page_content_html = None  # Initialize content variable
                    if page_config.context:
                        if page_config.context.content_markdown:
                            # Render Markdown content
                            try:
                                page_content_html = md.render(
                                    page_config.context.content_markdown
                                )
                            except Exception as md_err:
                                logger.error(
                                    f"Error rendering markdown for static page '{page_config.name}': {md_err}"
                                )
                                page_content_html = (
                                    "<p><em>Error rendering Markdown content.</em></p>"
                                )
                        elif page_config.context.content_source:
                            # Load content from file
                            # Assume content_source is relative to project/config or absolute
                            # A better approach might involve resolving paths relative to the config file location.
                            content_path = Path(page_config.context.content_source)
                            if content_path.is_file():
                                try:
                                    content_raw = content_path.read_text(
                                        encoding="utf-8"
                                    )
                                    # Check extension to decide if it needs markdown processing
                                    if content_path.suffix.lower() in [
                                        ".md",
                                        ".markdown",
                                    ]:
                                        page_content_html = md.render(content_raw)
                                    else:
                                        # Assume it's already HTML or text to be included directly
                                        page_content_html = content_raw  # Might need |safe in template if HTML
                                except Exception as read_err:
                                    logger.error(
                                        f"Error reading content file '{content_path}' for static page '{page_config.name}': {read_err}"
                                    )
                                    page_content_html = f"<p><em>Error loading content from {content_path}.</em></p>"
                            else:
                                logger.warning(
                                    f"Content source file not found for static page '{page_config.name}': {content_path}"
                                )
                                page_content_html = f"<p><em>Content file not found: {content_path}</em></p>"

                    context["page_content_html"] = (
                        page_content_html  # Pass rendered/loaded HTML to context
                    )

                    # Determine the template to use
                    template_name = (
                        page_config.template or "static_page.html"
                    )  # Fallback to default
                    try:
                        template = jinja_env.get_template(template_name)
                    except Exception as e:
                        logger.error(
                            f"Failed to process static page '{page_config.name}' ({page_config.template} -> {page_config.output_file}): {e}",
                            exc_info=True,
                        )
                        # Decide whether to raise or continue

                    rendered_html = template.render(context)
                    output_file_path = output_dir / page_config.output_file
                    output_file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_file_path, "w", encoding="utf-8") as f:
                        f.write(rendered_html)
                    logger.debug(f"Rendered static page: {output_file_path}")

                except Exception as e:
                    logger.error(
                        f"Failed to process static page '{page_config.name}' ({page_config.template} -> {page_config.output_file}): {e}",
                        exc_info=True,
                    )
                    # Decide whether to raise or continue

                # Update progress
                progress.update(task, advance=1)

        logger.info("Static pages processed.")

    def _process_groups(
        self,
        groups: List[GroupConfigWeb],
        jinja_env: Environment,
        html_params: HtmlExporterParams,
        output_dir: Path,
        repository: Database,
        group_filter: Optional[str] = None,
    ) -> None:
        """Processes each data group to generate index and detail pages."""
        logger.info(f"Processing {len(groups)} data groups...")
        if not groups:
            return

        plugin_registry = PluginRegistry()

        # Filter groups if needed
        groups_to_process = groups
        if group_filter:
            groups_to_process = [g for g in groups if g.group_by == group_filter]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(
                "[cyan]Processing groups[/cyan]", total=len(groups_to_process)
            )

            for group_config in groups:
                # Update progress with group name
                progress.update(
                    task,
                    description=f"[cyan]Processing group: {group_config.group_by}[/cyan]",
                )

                # Skip group if filter is set and doesn't match
                if group_filter and group_config.group_by != group_filter:
                    logger.debug(
                        f"Skipping group '{group_config.group_by}' due to filter '{group_filter}'."
                    )
                    continue

                group_by_key = group_config.group_by
                logger.info(f"Processing group: '{group_by_key}'")
                id_column = f"{group_by_key}_id"
                table_name = group_by_key

                # Generate navigation JS file for this group (only once)
                self._generate_navigation_js(group_config, output_dir)

                # Define the group-specific output directory prefix based on group_by_key
                group_output_path_prefix = group_by_key
                group_output_dir = output_dir / group_output_path_prefix

                # Clear group directory only if filter matches or no filter is set
                try:
                    if (
                        group_filter == group_by_key
                    ):  # Only clear if this specific group is targeted
                        if group_output_dir.exists() and any(
                            group_output_dir.iterdir()
                        ):
                            logger.warning(
                                f"Clearing specific group directory: {group_output_dir}"
                            )
                            shutil.rmtree(group_output_dir)

                    # Always ensure the group directory exists (might have been cleared or never existed)
                    group_output_dir.mkdir(parents=True, exist_ok=True)

                except OSError as e:
                    logger.error(
                        f"Error managing group directory {group_output_dir}: {e}",
                        exc_info=True,
                    )
                    continue  # Skip processing this group if directory management failed

                # --- Render Index Page ---
                # Check if group has index_generator configuration
                if (
                    hasattr(group_config, "index_generator")
                    and group_config.index_generator
                ):
                    try:
                        # Use new index generator plugin
                        from niamoto.core.plugins.exporters.index_generator import (
                            IndexGeneratorPlugin,
                        )
                        from niamoto.core.plugins.models import IndexGeneratorConfig

                        # Convert to dict if it's already a config object
                        if hasattr(group_config.index_generator, "model_dump"):
                            index_config_dict = (
                                group_config.index_generator.model_dump()
                            )
                        else:
                            index_config_dict = group_config.index_generator

                        # Validate and create config
                        index_config = IndexGeneratorConfig(**index_config_dict)

                        if index_config.enabled:
                            logger.info(
                                f"Using IndexGeneratorPlugin for group '{group_by_key}'"
                            )

                            # Create plugin instance
                            index_generator = IndexGeneratorPlugin(repository)

                            # Generate index page
                            index_generator.generate_index(
                                group_by_key,
                                index_config,
                                output_dir,
                                jinja_env,
                                html_params,
                            )
                            logger.debug(
                                f"Index page generated using IndexGeneratorPlugin for '{group_by_key}'"
                            )
                        else:
                            logger.info(
                                f"IndexGenerator disabled for group '{group_by_key}', skipping index generation"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error using IndexGeneratorPlugin for group '{group_by_key}': {e}",
                            exc_info=True,
                        )
                        # Fall back to traditional method
                        logger.info(
                            f"Falling back to traditional index generation for group '{group_by_key}'"
                        )
                        self._generate_traditional_index(
                            group_config,
                            group_by_key,
                            repository,
                            table_name,
                            id_column,
                            jinja_env,
                            html_params,
                            output_dir,
                            group_output_dir,
                        )
                else:
                    # Use traditional index generation
                    logger.debug(
                        f"Using traditional index generation for group '{group_by_key}'"
                    )
                    self._generate_traditional_index(
                        group_config,
                        group_by_key,
                        repository,
                        table_name,
                        id_column,
                        jinja_env,
                        html_params,
                        output_dir,
                        group_output_dir,
                    )

                # --- End Render Index Page ---

                # --- Render Detail Pages ---
                # Get index data for detail pages (needed for both traditional and new method)
                index_data = self._get_group_index_data(
                    repository, table_name, id_column
                )
                if not index_data:
                    logger.info(
                        f"No items found for group '{group_by_key}', skipping detail pages."
                    )
                    continue

                detail_template_name = group_config.page_template or "group_detail.html"

                # Outer try for the entire detail page generation process for this group
                try:
                    # Pre-load detail template once per group
                    detail_template = jinja_env.get_template(detail_template_name)
                    logger.info(
                        f"Generating detail pages for {len(index_data)} items in group '{group_by_key}' using template '{detail_template_name}'..."
                    )

                    # Loop through items to generate detail pages
                    # Add a sub-task for detail pages in the main progress
                    detail_task = progress.add_task(
                        f"[blue]Generating {group_by_key} detail pages[/blue]",
                        total=len(index_data),
                    )

                    for item_summary in index_data:
                        item_id = item_summary.get(id_column)
                        if item_id is None:
                            logger.warning(
                                f"Skipping item with missing ID in group '{group_by_key}' based on id_column '{id_column}'. Item data: {item_summary}"
                            )
                            progress.update(detail_task, advance=1)
                            continue

                        # Inner try for processing a single item
                        try:
                            # Get item data
                            item_data = self._get_item_detail_data(
                                repository, table_name, id_column, item_id
                            )
                            if not item_data:
                                # Warning already logged in _get_item_detail_data
                                progress.update(detail_task, advance=1)
                                continue

                            rendered_widgets: Dict[str, str] = {}
                            widget_dependencies: Set[str] = set()

                            # Process widgets for this item
                            for i, widget_config in enumerate(group_config.widgets):
                                # Create a unique key combining plugin type, data source, and index
                                widget_key = f"{widget_config.plugin}_{widget_config.data_source}_{i}"  # Unique key per widget instance

                                try:
                                    # Check if this is the hierarchical navigation widget
                                    is_hierarchical_nav = (
                                        widget_config.plugin
                                        == "hierarchical_nav_widget"
                                    )

                                    widget_plugin_class = plugin_registry.get_plugin(
                                        widget_config.plugin, PluginType.WIDGET
                                    )
                                    if not widget_plugin_class:
                                        raise ConfigurationError(
                                            config_key="widgets.plugin",
                                            message=f"Widget plugin '{widget_config.plugin}' not found.",
                                        )

                                    widget_instance: WidgetPlugin = widget_plugin_class(
                                        db=repository
                                    )

                                    deps = widget_instance.get_dependencies()
                                    if deps:
                                        widget_dependencies.update(deps)

                                    # Validate widget parameters
                                    validated_widget_params = widget_config.params
                                    if (
                                        hasattr(widget_instance, "param_schema")
                                        and widget_instance.param_schema
                                    ):
                                        try:
                                            validated_widget_params = widget_instance.param_schema.model_validate(
                                                widget_config.params
                                            )
                                        except Exception as validation_err:
                                            logger.error(
                                                f"Parameter validation failed for widget '{widget_config.plugin}' (ID: {widget_key}) "
                                                f"for {group_by_key} ID {item_id}: {validation_err}",
                                            )
                                            rendered_widgets[widget_key] = (
                                                f"<div id='{widget_key}' class='widget-error'>"
                                                f"Error validating parameters for widget '{widget_config.plugin}'. Check config."
                                                f"</div>"
                                            )
                                            continue  # Skip rendering this widget if validation fails

                                    # Handle data source differently for hierarchical nav widget
                                    if is_hierarchical_nav:
                                        # For hierarchical nav, we pass a flag to indicate data should be loaded from JS
                                        # The widget will check for this flag
                                        final_widget_data = {"load_from_js": True}

                                        # Inject current item ID into params
                                        if hasattr(
                                            validated_widget_params, "model_dump"
                                        ):
                                            params_dict = (
                                                validated_widget_params.model_dump()
                                            )
                                        else:
                                            params_dict = dict(validated_widget_params)

                                        params_dict["current_item_id"] = item_id

                                        # Re-validate with updated params
                                        try:
                                            validated_widget_params = widget_instance.param_schema.model_validate(
                                                params_dict
                                            )
                                        except Exception as e:
                                            logger.error(
                                                f"Failed to inject current_item_id for hierarchical nav: {e}"
                                            )
                                    else:
                                        # Get and process data source normally for other widgets
                                        data_source_key = widget_config.data_source
                                        raw_widget_data = self._get_nested_data(
                                            item_data, data_source_key
                                        )

                                        if raw_widget_data is None:
                                            logger.warning(
                                                f"Data source '{data_source_key}' not found for widget '{widget_config.plugin}' "
                                                f"in {group_by_key} ID {item_id}. Skipping widget."
                                            )
                                            rendered_widgets[widget_key] = (
                                                f"<!-- Widget Error: Data source '{data_source_key}' not found -->"
                                            )
                                            continue

                                        # Process data (JSON parse, DataFrame conversion)
                                        final_widget_data = raw_widget_data
                                        if isinstance(raw_widget_data, str):
                                            try:
                                                parsed_data = json.loads(
                                                    raw_widget_data
                                                )
                                                final_widget_data = parsed_data
                                                if (
                                                    isinstance(parsed_data, list)
                                                    and parsed_data
                                                ):
                                                    try:
                                                        df = pd.DataFrame(parsed_data)
                                                        final_widget_data = df
                                                        # logger.debug(f"Converted '{data_source_key}' to DataFrame for '{widget_config.plugin}'.")
                                                    except Exception as df_err:
                                                        logger.warning(
                                                            f"Could not convert parsed data from '{data_source_key}' to DataFrame for '{widget_config.plugin}'. Passing parsed list/dict. Error: {df_err}",
                                                            exc_info=False,
                                                        )
                                            except json.JSONDecodeError:
                                                logger.warning(
                                                    f"Data source '{data_source_key}' for '{widget_config.plugin}' in {group_by_key} ID {item_id} "
                                                    f"is string but not valid JSON. Passing raw string.",
                                                    exc_info=False,
                                                )
                                                # final_widget_data remains raw_widget_data
                                            except Exception as parse_err:
                                                logger.error(
                                                    f"Error processing data for '{widget_config.plugin}' (source: {data_source_key}): {parse_err}",
                                                    exc_info=True,
                                                )
                                                rendered_widgets[widget_key] = (
                                                    f"<!-- Widget Error: Failed to process data source '{data_source_key}' -->"
                                                )
                                                continue

                                    # Render the widget
                                    widget_content_html = widget_instance.render(
                                        final_widget_data, validated_widget_params
                                    )
                                    widget_html = widget_instance.get_container_html(
                                        widget_key, widget_content_html, widget_config
                                    )
                                    rendered_widgets[widget_key] = widget_html

                                except Exception as widget_err:
                                    logger.error(
                                        f"Failed to render widget '{widget_config.plugin}' (ID: {widget_key}, Source: {widget_config.data_source}) "
                                        f"for {group_by_key} ID {item_id}: {widget_err}",
                                        exc_info=True,
                                    )
                                    rendered_widgets[widget_key] = (
                                        f"<div id='{widget_key}' class='widget-error'>"
                                        f"Error rendering widget '{widget_config.plugin}': {widget_err}"
                                        f"</div>"
                                    )
                            # End widget loop for this item

                            # Prepare context and render detail page for this item
                            # Calculate depth based on output pattern
                            depth = group_config.output_pattern.count("/")

                            detail_context = {
                                "site": html_params.site.model_dump()
                                if html_params.site
                                else {},
                                "navigation": html_params.navigation
                                if html_params.navigation
                                else [],
                                "id_column": id_column,
                                "group_config": group_config,
                                "group_by": group_by_key,
                                "item": item_data,
                                "widgets": rendered_widgets,
                                "dependencies": list(widget_dependencies),
                                "depth": depth,  # Add depth for relative URLs
                            }
                            rendered_detail_html = detail_template.render(
                                detail_context
                            )

                            # Restore backslash replacement
                            safe_item_id = (
                                str(item_id).replace("/", "_").replace("\\", "_")
                            )

                            output_file_name = group_config.output_pattern.format(
                                group_by=group_by_key, id=safe_item_id
                            )

                            if (
                                f"{group_by_key}/" in group_config.output_pattern
                                or "{group_by}/" in group_config.output_pattern
                            ):
                                # Remove the group prefix from group_output_dir to avoid duplication
                                detail_output_path = output_dir / output_file_name
                            else:
                                # Keep current behavior for backward compatibility
                                detail_output_path = group_output_dir / output_file_name

                            detail_output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(detail_output_path, "w", encoding="utf-8") as f:
                                f.write(rendered_detail_html)
                            # logger.debug(f"Rendered detail page: {detail_output_path}")

                        except Exception as item_render_err:  # Catch errors specific to rendering this single item
                            logger.error(
                                f"Failed rendering detail page for item {item_id} in group '{group_by_key}': {item_render_err}",
                                exc_info=True,
                            )
                            # Continue to the next item even if one fails

                        # Update progress
                        progress.update(detail_task, advance=1)

                    # End item loop for this group

                # Corresponding except for the outer try block (template loading or other group-wide detail errors)
                except Exception as detail_group_err:
                    logger.error(
                        f"Failed processing detail pages for group '{group_by_key}': {detail_group_err}",
                        exc_info=True,
                    )
                    # Continue processing the next group if detail page generation fails for this one
                    continue

                # --- End Render Detail Pages ---

                # Update progress for group
                progress.update(task, advance=1)

        # End group loop
        logger.info("Data group processing finished.")

    def _validate_template_availability(
        self, jinja_env: Environment, template_name: str
    ) -> bool:
        """
        Validate that a template is available in the Jinja environment.

        Args:
            jinja_env: The Jinja2 environment
            template_name: Name of the template to check

        Returns:
            True if template is available, False otherwise
        """
        try:
            jinja_env.get_template(template_name)
            return True
        except Exception as e:
            logger.warning(f"Template '{template_name}' not available: {e}")
            return False

    def _load_and_cache_navigation_data(
        self, referential_data_source: str, required_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Load and cache navigation reference data.

        Args:
            referential_data_source: Name of the reference table (e.g., 'taxon_ref')
            required_fields: List of specific fields to select. If None, selects all fields.

        Returns:
            List of all items from the reference table
        """
        # Check cache first
        cache_key = f"{referential_data_source}:{','.join(required_fields) if required_fields else '*'}"
        if cache_key in self._navigation_cache:
            logger.debug(
                f"Using cached navigation data for '{referential_data_source}'"
            )
            return self._navigation_cache[cache_key]

        logger.info(f"Loading navigation data from table '{referential_data_source}'")

        try:
            # Verify table exists
            if not self.db.has_table(referential_data_source):
                logger.error(
                    f"Reference table '{referential_data_source}' does not exist"
                )
                return []

            # Build query with specific fields or all fields
            if required_fields:
                # Escape field names to prevent SQL injection
                escaped_fields = [f'"{field}"' for field in required_fields]
                fields_str = ", ".join(escaped_fields)
                query = f'SELECT {fields_str} FROM "{referential_data_source}" ORDER BY "id"'
            else:
                query = f'SELECT * FROM "{referential_data_source}" ORDER BY "id"'
            results = self.db.fetch_all(query)

            if results:
                # Convert to list of dicts and cache
                data_list = [dict(row) for row in results]
                self._navigation_cache[referential_data_source] = data_list
                logger.debug(
                    f"Loaded {len(data_list)} items from '{referential_data_source}'"
                )
                return data_list
            else:
                logger.warning(
                    f"No data found in reference table '{referential_data_source}'"
                )
                return []

        except Exception as e:
            logger.error(
                f"Error loading navigation data from '{referential_data_source}': {e}",
                exc_info=True,
            )
            return []

    def _extract_navigation_fields(self, group_config: "GroupConfigWeb") -> List[str]:
        """
        Extract required fields from hierarchical navigation widgets in the group.

        Args:
            group_config: The group configuration

        Returns:
            List of field names required for navigation
        """
        required_fields = set()

        # Look for hierarchical navigation widgets in the group
        for widget_config in group_config.widgets:
            if widget_config.plugin == "hierarchical_nav_widget":
                params = widget_config.params

                # Add all potential hierarchy fields
                if "id_field" in params:
                    required_fields.add(params["id_field"])
                if "name_field" in params:
                    required_fields.add(params["name_field"])
                if "parent_id_field" in params:
                    required_fields.add(params["parent_id_field"])
                if "lft_field" in params:
                    required_fields.add(params["lft_field"])
                if "rght_field" in params:
                    required_fields.add(params["rght_field"])
                if "level_field" in params:
                    required_fields.add(params["level_field"])
                if "group_by_field" in params:
                    required_fields.add(params["group_by_field"])
                if "group_by_label_field" in params:
                    required_fields.add(params["group_by_label_field"])

        # If no hierarchical widgets found, use default minimal set
        if not required_fields:
            required_fields = {"id", "name", "full_name"}

        return list(required_fields)

    def _generate_navigation_js(
        self, group_config: "GroupConfigWeb", output_dir: Path
    ) -> None:
        """
        Generate JavaScript file with navigation data for a specific group.
        Only generates once per group to avoid duplication.

        Args:
            group_config: The group configuration containing hierarchy information
            output_dir: The output directory for the export
        """
        group_by_key = group_config.group_by

        # Check if already generated for this group
        if group_by_key in self._navigation_js_generated:
            return

        # Get reference table name based on group
        reference_table = f"{group_by_key}_ref"

        # Extract required fields from hierarchical navigation widgets
        required_fields = self._extract_navigation_fields(group_config)

        # Load navigation data with only required fields
        navigation_data = self._load_and_cache_navigation_data(
            reference_table, required_fields
        )
        if not navigation_data:
            logger.warning(f"No navigation data to generate JS for {group_by_key}")
            return

        try:
            # Create JS directory if it doesn't exist
            js_dir = output_dir / "assets/js"
            js_dir.mkdir(parents=True, exist_ok=True)

            # Generic filename and variable name based on group
            js_filename = f"{group_by_key}_navigation.js"
            var_name = f"{group_by_key}NavigationData"

            # Simply dump all data as-is - let the widget handle the structure
            # This preserves all original field names and data
            js_content = f"const {var_name} = {json.dumps(navigation_data, separators=(',', ':'))};"

            # Write JS file
            js_path = js_dir / js_filename
            js_path.write_text(js_content, encoding="utf-8")

            # Mark as generated
            self._navigation_js_generated.add(group_by_key)

            logger.info(
                f"Generated navigation JS file: {js_path} with variable {var_name}"
            )

        except Exception as e:
            logger.error(
                f"Failed to generate navigation JS for {group_by_key}: {e}",
                exc_info=True,
            )

    def _get_group_index_data(
        self, repository: Database, table_name: str, id_column: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetches data needed for an index page (e.g., ID and a name column). Returns None on DB error."""
        logger.debug(
            f"Fetching index data for group '{table_name}' using ID column '{id_column}'"
        )

        try:
            table_columns = repository.get_table_columns(table_name)
            if not table_columns:
                logger.error(
                    f"Could not get columns for table '{table_name}'. Cannot fetch index data."
                )
                return None
            if id_column not in table_columns:
                logger.error(
                    f"ID column '{id_column}' not found in table '{table_name}'. Cannot fetch index data."
                )
                return None

            # Dynamically find the best "name" column
            name_column = None
            if "name" in table_columns:
                name_column = "name"
                logger.debug(
                    f"Found 'name' column for index display in table '{table_name}'."
                )
            else:
                # Look for the first column ending in '_name'
                possible_name_cols = [
                    col for col in table_columns if col.endswith("_name")
                ]
                if possible_name_cols:
                    name_column = possible_name_cols[0]  # Take the first one found
                    logger.debug(
                        f"Using '{name_column}' column for index display in table '{table_name}'."
                    )
                else:
                    """
                    logger.warning(
                        f"No 'name' or '*_name' column found in table '{table_name}'. Index pages might lack descriptive names."
                    ) """
                    # name_column remains None

            # Determine columns to select and order by
            columns_to_select = [id_column]
            if name_column:
                columns_to_select.append(name_column)
                order_by_col = name_column
            else:
                order_by_col = id_column  # Fallback to ordering by ID if no name column

            select_cols_str = ", ".join(
                f'"{col}"' for col in columns_to_select
            )  # Quote column names

            # Construct and execute the query
            query = f'SELECT {select_cols_str} FROM "{table_name}" ORDER BY "{order_by_col}"'  # Quote table/col names
            logger.debug(f"Executing index query: {query}")

            results = repository.fetch_all(query)
            return results if results else []

        except Exception as e:
            logger.error(
                f"Database error fetching index data from '{table_name}': {e}",
                exc_info=True,
            )
            return None  # Return None on any error during the process

    def _get_item_detail_data(
        self, repository: Database, table_name: str, id_column: str, item_id: Any
    ) -> Optional[Dict[str, Any]]:
        """Fetches the full data row for a single item detail page. Returns None on DB error or not found."""
        query = f'SELECT * FROM "{table_name}" WHERE "{id_column}" = :item_id'
        params = {"item_id": item_id}
        logger.debug(f"Executing detail query: {query} with params {params}")
        try:
            result = repository.fetch_one(query, params)
            if not result:
                logger.warning(
                    f"Data not found for {id_column} {item_id} in table '{table_name}'. Skipping detail page."
                )
                return None

            # Convert RowMapping to a mutable dictionary
            item_data = dict(result)

            # Return the fetched data directly as a dictionary
            # The widget processing logic will handle accessing specific keys (data_sources)
            return item_data
        except Exception as e:
            logger.error(
                f"Database error fetching detail data for {id_column} {item_id} from '{table_name}': {e}",
                exc_info=True,
            )
            return None

    def _generate_traditional_index(
        self,
        group_config,
        group_by_key: str,
        repository: Database,
        table_name: str,
        id_column: str,
        jinja_env,
        html_params,
        output_dir: Path,
        group_output_dir: Path,
    ) -> None:
        """
        Generate index page using the traditional method (for backward compatibility).

        Args:
            group_config: Group configuration
            group_by_key: Group type key
            repository: Database instance
            table_name: Name of the data table
            id_column: Name of the ID column
            jinja_env: Jinja2 environment
            html_params: HTML exporter parameters
            output_dir: Base output directory
            group_output_dir: Group-specific output directory
        """
        try:
            # Fetch index data
            index_data = self._get_group_index_data(repository, table_name, id_column)
            if not index_data:
                logger.error(
                    f"No index data found for group '{group_by_key}'. Skipping index generation."
                )
                return

            # Use traditional template
            index_template_name = group_config.index_template or "group_index.html"

            index_template = jinja_env.get_template(index_template_name)
            logger.debug(f"Rendering traditional index template: {index_template_name}")

            index_context = {
                "site": html_params.site,
                "navigation": html_params.navigation,
                "group_by": group_by_key,
                "items": index_data,
                "group_config": group_config,
                "id_column": id_column,
            }

            # Output index file to the specific group directory
            index_output_file = Path(
                group_config.index_output_pattern.format(group_by=group_by_key)
            )

            # Check if index_output_pattern already includes the group name to avoid duplication
            if (
                f"{group_by_key}/" in group_config.index_output_pattern
                or "{group_by}/" in group_config.index_output_pattern
            ):
                # Remove the group prefix from output path to avoid duplication
                index_output_path = output_dir / index_output_file
            else:
                # Keep current behavior for backward compatibility
                index_output_path = group_output_dir / index_output_file

            index_output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(index_output_path, "w", encoding="utf-8") as f:
                f.write(index_template.render(index_context))
            logger.debug(
                f"Rendered traditional index page for '{group_by_key}': {index_output_path}"
            )

        except Exception as e:
            logger.error(
                f"Error generating traditional index for group '{group_by_key}': {e}",
                exc_info=True,
            )
            raise
