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
import re
import shutil
import json
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Set, Optional, Tuple
import importlib.resources

from jinja2 import Environment, FileSystemLoader, select_autoescape, ChoiceLoader
from pydantic import ValidationError
from markdown_it import MarkdownIt
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from niamoto.common.database import Database
from niamoto.common.exceptions import ConfigurationError, ProcessError
from niamoto.common.config import Config
from niamoto.common.utils.emoji import emoji
from niamoto.common.i18n import I18nResolver
from niamoto.common.table_resolver import resolve_entity_table, resolve_reference_table
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

    # Define the parameter schema for this exporter
    param_schema = HtmlExporterParams

    def __init__(self, db: Database, registry=None):
        """Initialize the exporter with database connection."""
        super().__init__(db, registry)
        self._navigation_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._navigation_js_generated: Set[str] = set()

        # Initialize statistics tracking
        self.stats: Dict[str, Any] = {
            "start_time": None,
            "end_time": None,
            "groups_processed": {},
            "total_files_generated": 0,
            "errors_count": 0,
            "output_path": None,
        }

        # I18n resolver (initialized during export)
        self._i18n_resolver: Optional[I18nResolver] = None
        self._current_lang: Optional[str] = None

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

    def _resolve_registry_entity(
        self, entity_name: str
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Resolve an entity through registry metadata when available."""
        if not self.registry:
            return None, {}

        try:
            entity_meta = self.registry.get(entity_name)
            table_name = getattr(entity_meta, "table_name", None)
            if table_name and self.db.has_table(table_name):
                config = getattr(entity_meta, "config", {}) or {}
                if isinstance(config, dict):
                    return table_name, config
                return table_name, {}
        except Exception:
            pass

        return None, {}

    def _resolve_group_table_and_id(
        self, group_by_key: str, navigation_entity: Optional[str] = None
    ) -> Tuple[str, str]:
        """Resolve group table and identifier column from registry/config/conventions."""
        table_name, entity_config = self._resolve_registry_entity(group_by_key)
        if not table_name and navigation_entity and navigation_entity != group_by_key:
            table_name, entity_config = self._resolve_registry_entity(navigation_entity)

        if not table_name:
            table_name = resolve_entity_table(
                self.db,
                group_by_key,
                registry=self.registry,
                kind="reference",
            )
            if (
                not table_name
                and navigation_entity
                and navigation_entity != group_by_key
            ):
                table_name = resolve_entity_table(
                    self.db,
                    navigation_entity,
                    registry=self.registry,
                    kind="reference",
                )
            if not table_name:
                table_name = group_by_key

        id_column = f"{group_by_key}_id"
        try:
            table_columns = self.db.get_table_columns(table_name) or []
        except Exception:
            return table_name, id_column

        if not table_columns:
            return table_name, id_column

        schema_cfg = (
            entity_config.get("schema", {}) if isinstance(entity_config, dict) else {}
        )
        schema_id = schema_cfg.get("id_field") if isinstance(schema_cfg, dict) else None

        id_candidates: List[str] = []
        if schema_id:
            id_candidates.append(schema_id)
        id_candidates.extend([f"{group_by_key}_id", f"id_{group_by_key}", "id"])
        id_candidates.extend([c for c in table_columns if c.endswith("_id")])

        resolved_id = next((c for c in id_candidates if c in table_columns), None)
        if resolved_id:
            return table_name, resolved_id
        return table_name, id_column

    def _resolve_reference_table_name(self, entity_name: str) -> str:
        """Resolve reference table with registry-first strategy and safe fallback."""
        table_name, _ = self._resolve_registry_entity(entity_name)
        if table_name:
            return table_name

        return resolve_reference_table(self.db, entity_name) or f"entity_{entity_name}"

    def _resolve_localized(self, value: Any, lang: Optional[str] = None) -> Any:
        """
        Resolve a potentially localized value for the current language.

        Args:
            value: Value that may be a localized dict or simple value
            lang: Target language (uses current lang if not specified)

        Returns:
            Resolved value for the target language
        """
        if self._i18n_resolver is None:
            return (
                value
                if not isinstance(value, dict)
                else next(iter(value.values()), value)
            )

        target_lang = lang or self._current_lang
        return self._i18n_resolver.resolve(value, target_lang)

    def _resolve_navigation(
        self, navigation: List[Any], lang: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Resolve localized strings in navigation items.

        Args:
            navigation: List of NavigationItem objects or dicts
            lang: Target language

        Returns:
            List of navigation dicts with resolved strings
        """
        resolved = []
        for item in navigation:
            if hasattr(item, "model_dump"):
                item_dict = item.model_dump()
            else:
                item_dict = (
                    dict(item) if isinstance(item, dict) else {"text": str(item)}
                )

            # Resolve text
            if "text" in item_dict:
                item_dict["text"] = self._resolve_localized(item_dict["text"], lang)

            # Recursively resolve children
            if "children" in item_dict and item_dict["children"]:
                item_dict["children"] = self._resolve_navigation(
                    item_dict["children"], lang
                )

            resolved.append(item_dict)
        return resolved

    def _resolve_footer_sections(
        self, sections: List[Any], lang: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Resolve localized strings in footer sections."""
        resolved = []
        for section in sections:
            if hasattr(section, "model_dump"):
                s = section.model_dump()
            else:
                s = dict(section) if isinstance(section, dict) else {}

            if "title" in s:
                s["title"] = self._resolve_localized(s["title"], lang)

            if "links" in s and s["links"]:
                for link in s["links"]:
                    if "text" in link:
                        link["text"] = self._resolve_localized(link["text"], lang)

            resolved.append(s)
        return resolved

    def _get_site_context(
        self, html_params: HtmlExporterParams, lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build site context with resolved localized strings.

        Args:
            html_params: HTML exporter parameters
            lang: Target language

        Returns:
            Site context dict with resolved strings
        """
        site_dict = html_params.site.model_dump() if html_params.site else {}

        # Resolve localized title
        if "title" in site_dict:
            site_dict["title"] = self._resolve_localized(site_dict["title"], lang)

        # Add current language info
        site_dict["current_lang"] = lang or site_dict.get("lang", "en")

        return site_dict

    def _generate_language_redirect(
        self, output_dir: Path, default_lang: str, languages: List[str]
    ) -> None:
        """
        Generate a redirect page at the root that redirects to the default language.

        Args:
            output_dir: Base output directory
            default_lang: Default language to redirect to
            languages: List of available languages
        """
        redirect_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=/{default_lang}/">
    <script>
        // Detect browser language and redirect
        (function() {{
            var supportedLangs = {json.dumps(languages)};
            var browserLang = navigator.language || navigator.userLanguage;
            var shortLang = browserLang.split('-')[0].toLowerCase();

            if (supportedLangs.indexOf(shortLang) !== -1) {{
                window.location.href = '/' + shortLang + '/';
            }} else {{
                window.location.href = '/{default_lang}/';
            }}
        }})();
    </script>
    <title>Redirecting...</title>
</head>
<body>
    <p>Redirecting to <a href="/{default_lang}/">default language</a>...</p>
</body>
</html>"""

        redirect_path = output_dir / "index.html"
        redirect_path.write_text(redirect_html, encoding="utf-8")
        self.stats["total_files_generated"] += 1
        logger.info(f"Generated language redirect page: {redirect_path}")

    def export(
        self,
        target_config: TargetConfig,
        repository: Database,
        group_filter: Optional[str] = None,
    ) -> None:
        """
        Executes the HTML export process.

        Supports multi-language generation when site.languages is configured with
        multiple languages. In that case, generates separate directories for each
        language (e.g., /fr/, /en/) and a redirect page at the root.

        Args:
            target_config: The validated configuration for this HTML export target.
            repository: The Database instance to fetch data from.
            group_filter: Optional filter to apply to the groups.
        """
        logger.info(f"Starting HTML page export for target: '{target_config.name}'")

        # Initialize stats timing
        from datetime import datetime

        self.stats["start_time"] = datetime.now()

        try:
            # 1. Validate and parse specific HTML exporter parameters
            try:
                html_params = HtmlExporterParams.model_validate(target_config.params)
            except AttributeError:
                html_params = HtmlExporterParams.parse_obj(target_config.params)

            output_dir = Path(html_params.output_dir)
            user_template_dir = Path(html_params.template_dir)

            # Store output path for summary display
            self.stats["output_path"] = str(output_dir.resolve())

            # Initialize I18n resolver
            default_lang = html_params.site.lang if html_params.site else "en"
            languages = (
                html_params.site.languages
                if html_params.site and html_params.site.languages
                else [default_lang]
            )
            self._i18n_resolver = I18nResolver(
                default_lang=default_lang, available_languages=languages
            )

            # Determine if multi-language generation is enabled
            # Multi-lang is enabled if there's more than one language
            multi_lang_enabled = len(languages) > 1
            language_switcher = (
                html_params.site.language_switcher if html_params.site else False
            )

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

            # 4. Copy static assets (default and user-specified) - once at root level
            self._copy_static_assets(html_params, output_dir)

            # 5. Generate content for each language
            if multi_lang_enabled:
                logger.info(f"Multi-language export enabled for languages: {languages}")

                # Generate content for each language in its subdirectory
                for lang in languages:
                    self._current_lang = lang
                    lang_output_dir = output_dir / lang

                    # Create language directory
                    lang_output_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Generating content for language: {lang}")

                    # Reset navigation cache for each language
                    self._navigation_js_generated = set()

                    # Process static pages for this language
                    self._process_static_pages(
                        target_config.static_pages,
                        jinja_env,
                        html_params,
                        lang_output_dir,
                        md,
                        lang=lang,
                        languages=languages,
                        language_switcher=language_switcher,
                    )

                    # Process data groups for this language
                    self._process_groups(
                        target_config.groups,
                        jinja_env,
                        html_params,
                        lang_output_dir,
                        repository,
                        group_filter,
                        lang=lang,
                        languages=languages,
                        language_switcher=language_switcher,
                    )

                # Generate root redirect page
                self._generate_language_redirect(output_dir, default_lang, languages)

            else:
                # Single language mode (backward compatible)
                self._current_lang = default_lang

                # Process static pages
                logger.info(
                    f"Processing {len(target_config.static_pages)} static page configurations..."
                )
                self._process_static_pages(
                    target_config.static_pages, jinja_env, html_params, output_dir, md
                )

                # Process data groups
                self._process_groups(
                    target_config.groups,
                    jinja_env,
                    html_params,
                    output_dir,
                    repository,
                    group_filter,
                )

            # Mark completion time
            self.stats["end_time"] = datetime.now()

            logger.info(
                f"HTML export finished successfully for target: '{target_config.name}'"
            )

        except ValidationError as val_err:
            self.stats["errors_count"] += 1
            self.stats["end_time"] = datetime.now()
            logger.error(
                f"Configuration error in HTML exporter params for target '{target_config.name}': {val_err}"
            )
            raise ConfigurationError(
                config_key="params", message=f"Invalid params for {target_config.name}"
            ) from val_err
        except ProcessError as proc_err:
            self.stats["errors_count"] += 1
            self.stats["end_time"] = datetime.now()
            logger.error(
                f"Processing error during HTML export for '{target_config.name}': {proc_err}"
            )
            raise  # Re-raise process errors
        except Exception as e:
            self.stats["errors_count"] += 1
            self.stats["end_time"] = datetime.now()
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

    @staticmethod
    def _references_to_bibtex(references: List[Dict[str, Any]]) -> str:
        """Convert a list of reference dicts to BibTeX format."""
        type_mapping = {
            "article": "article",
            "book": "book",
            "chapter": "incollection",
            "thesis": "phdthesis",
            "report": "techreport",
            "conference": "inproceedings",
            "other": "misc",
        }

        lines = []
        for ref in references:
            bib_type = type_mapping.get(ref.get("type", "other"), "misc")
            authors = ref.get("authors", "unknown")
            first_author = authors.split(",")[0].strip().split()[-1].lower()
            year = ref.get("year", "0000")
            title_word = ref.get("title", "untitled").split()[0].lower()
            key = f"{first_author}{year}{title_word}"

            lines.append(f"@{bib_type}{{{key},")
            if ref.get("authors"):
                bib_authors = ref["authors"].replace(", ", " and ")
                lines.append(f"  author    = {{{bib_authors}}},")
            if ref.get("title"):
                lines.append(f"  title     = {{{ref['title']}}},")
            if ref.get("year"):
                lines.append(f"  year      = {{{ref['year']}}},")
            if ref.get("journal"):
                if bib_type in ("inproceedings", "incollection"):
                    lines.append(f"  booktitle = {{{ref['journal']}}},")
                elif bib_type == "phdthesis":
                    lines.append(f"  school    = {{{ref['journal']}}},")
                else:
                    lines.append(f"  journal   = {{{ref['journal']}}},")
            if ref.get("volume"):
                lines.append(f"  volume    = {{{ref['volume']}}},")
            if ref.get("pages"):
                lines.append(f"  pages     = {{{ref['pages'].replace('-', '--')}}},")
            if ref.get("doi"):
                lines.append(f"  doi       = {{{ref['doi']}}},")
            if ref.get("url"):
                lines.append(f"  url       = {{{ref['url']}}},")
            lines.append("}")
            lines.append("")

        return "\n".join(lines)

    def _load_bibtex_references(self, bibtex_source: str) -> List[Dict[str, Any]]:
        """
        Load and parse a BibTeX file into a list of reference dicts.

        Args:
            bibtex_source: Path to the .bib file (relative or absolute)

        Returns:
            List of reference dicts with keys: type, title, authors, year,
            journal, volume, pages, doi, url
        """
        import re

        bib_path = Path(bibtex_source)
        if not bib_path.is_file():
            logger.warning(f"BibTeX file not found: {bib_path}")
            return []

        try:
            text = bib_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading BibTeX file '{bib_path}': {e}")
            return []

        # Type mapping
        type_mapping = {
            "article": "article",
            "book": "book",
            "inbook": "chapter",
            "incollection": "chapter",
            "phdthesis": "thesis",
            "mastersthesis": "thesis",
            "techreport": "report",
            "inproceedings": "conference",
            "conference": "conference",
            "misc": "other",
            "unpublished": "other",
        }

        field_pattern = re.compile(
            r"(\w+)\s*=\s*(?:\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
            r"|\"([^\"]*)\"|(\d+))",
            re.IGNORECASE,
        )

        references = []
        entry_starts = [m.start() for m in re.finditer(r"@\w+\s*\{", text)]

        for start in entry_starts:
            # Find matching closing brace
            brace_count = 0
            end = start
            in_entry = False
            for j, char in enumerate(text[start:], start):
                if char == "{":
                    brace_count += 1
                    in_entry = True
                elif char == "}":
                    brace_count -= 1
                    if in_entry and brace_count == 0:
                        end = j + 1
                        break

            entry_text = text[start:end]

            # Extract entry type
            entry_match = re.match(
                r"@(\w+)\s*\{\s*([^,]+)\s*,", entry_text, re.IGNORECASE
            )
            if not entry_match:
                continue

            entry_type = entry_match.group(1).lower()
            ref_type = type_mapping.get(entry_type, "other")

            # Extract fields
            fields = {}
            for match in field_pattern.finditer(entry_text):
                field_name = match.group(1).lower()
                field_value = match.group(2) or match.group(3) or match.group(4) or ""
                fields[field_name] = re.sub(r"\s+", " ", field_value.strip())

            title = fields.get("title", "")
            if not title:
                continue

            ref = {
                "type": ref_type,
                "title": title,
                "authors": fields.get("author", "").replace(" and ", ", "),
                "year": fields.get("year", ""),
            }

            # Journal / venue
            for venue_field in (
                "journal",
                "booktitle",
                "school",
                "institution",
                "publisher",
            ):
                if venue_field in fields:
                    ref["journal"] = fields[venue_field]
                    break

            if "volume" in fields:
                vol = fields["volume"]
                if "number" in fields:
                    vol += f"({fields['number']})"
                ref["volume"] = vol

            if "pages" in fields:
                ref["pages"] = fields["pages"].replace("--", "-")
            if "doi" in fields:
                ref["doi"] = fields["doi"]
            if "url" in fields:
                ref["url"] = fields["url"]

            # Append note for extra context
            if "note" in fields:
                if "journal" in ref:
                    ref["journal"] += f" — {fields['note']}"
                else:
                    ref["journal"] = fields["note"]

            references.append(ref)

        # Sort by year descending, then by authors
        references.sort(
            key=lambda r: (-int(r.get("year") or "0"), r.get("authors", ""))
        )
        return references

    @staticmethod
    def _postprocess_markdown_html(html: str) -> str:
        """Post-process markdown-rendered HTML to handle image metadata in alt text.

        Transforms ![alt|300|center](src) rendered as <img alt="alt|300|center">
        into properly styled <img> with width and alignment.
        """

        def _replace_img(match: re.Match) -> str:
            full = match.group(0)
            alt_match = re.search(r'alt="([^"]*)"', full)
            if not alt_match:
                return full
            alt_raw = alt_match.group(1)
            parts = alt_raw.split("|")
            if len(parts) < 2:
                return full
            clean_alt = parts[0]
            img_styles: list[str] = []
            alignment = None
            for part in parts[1:]:
                p = part.strip()
                if re.match(r"^\d+$", p):
                    img_styles.append(f"max-width:{p}px")
                elif p == "center":
                    alignment = "center"
                elif p == "right":
                    alignment = "right"
            result = full.replace(f'alt="{alt_raw}"', f'alt="{clean_alt}"')
            if img_styles:
                style_str = ";".join(img_styles)
                if 'style="' in result:
                    result = result.replace('style="', f'style="{style_str};')
                else:
                    result = result.replace("<img ", f'<img style="{style_str}" ')
            # Wrap in flex div for alignment (works with Tailwind's display:block on img)
            if alignment == "center":
                return f'<div style="display:flex;justify-content:center;margin:1rem 0">{result}</div>'
            elif alignment == "right":
                return f'<div style="display:flex;justify-content:flex-end;margin:1rem 0">{result}</div>'
            return result

        return re.sub(r"<img\s[^>]+>", _replace_img, html)

    def _resolve_content_source(
        self, content_source: str, lang: Optional[str], md: MarkdownIt
    ) -> Optional[str]:
        """
        Resolve a content source path, supporting language-specific files.

        For a content_source like "pages/about", tries in order:
        1. pages/about.{lang}.md (e.g., pages/about.fr.md)
        2. pages/about.md (fallback)
        3. The literal path if it's a direct file reference

        Args:
            content_source: Base path or file path
            lang: Target language code
            md: Markdown parser

        Returns:
            Rendered HTML content or None if not found
        """
        content_path = Path(content_source)

        # If it's already a file with extension, try it directly
        if content_path.suffix:
            paths_to_try = [content_path]
        else:
            # Try language-specific file first, then generic
            paths_to_try = []
            if lang:
                paths_to_try.append(Path(f"{content_source}.{lang}.md"))
            paths_to_try.append(Path(f"{content_source}.md"))

        for path in paths_to_try:
            if path.is_file():
                try:
                    content_raw = path.read_text(encoding="utf-8")
                    if path.suffix.lower() in [".md", ".markdown"]:
                        return self._postprocess_markdown_html(md.render(content_raw))
                    return content_raw
                except Exception as read_err:
                    logger.error(f"Error reading content file '{path}': {read_err}")
                    return f"<p><em>Error loading content from {path}.</em></p>"

        logger.warning(
            f"Content source file not found for any tried paths: {paths_to_try}"
        )
        return f"<p><em>Content file not found: {content_source}</em></p>"

    def _process_static_pages(
        self,
        static_pages: List[StaticPageConfig],
        jinja_env: Environment,
        html_params: HtmlExporterParams,
        output_dir: Path,
        md: MarkdownIt,
        lang: Optional[str] = None,
        languages: Optional[List[str]] = None,
        language_switcher: bool = False,
    ) -> None:
        """
        Processes each static page configuration.

        Args:
            static_pages: List of static page configurations
            jinja_env: Jinja2 environment
            html_params: HTML export parameters
            output_dir: Output directory
            md: Markdown parser
            lang: Current language code (for multi-language mode)
            languages: List of all supported languages
            language_switcher: Whether to enable language switcher
        """
        logger.info(f"Processing {len(static_pages)} static pages...")
        if not static_pages:
            return

        for page_config in static_pages:
            logger.debug(
                f"Processing static page: '{page_config.name}' -> {page_config.output_file}"
            )
            try:
                template_name = page_config.template or "page.html"
                template = jinja_env.get_template(template_name)

                # Build site context with resolved localized strings
                site_context = self._get_site_context(html_params, lang)

                # Add i18n info to site context
                if lang:
                    site_context["current_lang"] = lang
                if languages:
                    site_context["languages"] = languages
                site_context["language_switcher"] = language_switcher

                # Resolve navigation with localized strings
                navigation = self._resolve_navigation(
                    html_params.navigation if html_params.navigation else [], lang
                )
                footer_navigation = self._resolve_footer_sections(
                    html_params.footer_navigation
                    if html_params.footer_navigation
                    else [],
                    lang,
                )

                # Build page context with resolved localized strings
                page_context = (
                    page_config.context.model_dump() if page_config.context else {}
                )
                if "title" in page_context:
                    page_context["title"] = self._resolve_localized(
                        page_context["title"], lang
                    )

                # Prepare full context
                context = {
                    "site": site_context,
                    "navigation": navigation,
                    "footer_navigation": footer_navigation,
                    "page": page_context,
                    "output_file": page_config.output_file,
                    "current_lang": lang,
                    "languages": languages or [],
                    "language_switcher": language_switcher,
                }

                # Handle content source (external markdown file) or inline markdown
                page_content_html = None
                if page_config.context:
                    content_source = page_config.context.content_source

                    if content_source:
                        # Load content from file with language support
                        page_content_html = self._resolve_content_source(
                            content_source, lang, md
                        )
                    elif hasattr(page_config.context, "content_markdown"):
                        # Handle inline markdown content
                        content_markdown = getattr(
                            page_config.context, "content_markdown", None
                        )
                        if content_markdown:
                            page_content_html = self._postprocess_markdown_html(
                                md.render(content_markdown)
                            )

                context["page_content_html"] = page_content_html

                # Handle bibtex_source: load and parse .bib file into references
                if page_context.get("bibtex_source"):
                    bibtex_refs = self._load_bibtex_references(
                        page_context["bibtex_source"]
                    )
                    if bibtex_refs:
                        context["references"] = bibtex_refs
                        # Also make available in page context
                        page_context["references"] = bibtex_refs
                        logger.debug(
                            f"Loaded {len(bibtex_refs)} references from BibTeX"
                        )

                # Resolve *_source JSON files (team_source, references_source, etc.)
                for key in list(page_context.keys()):
                    if (
                        key.endswith("_source")
                        and key != "content_source"
                        and key != "bibtex_source"
                    ):
                        target_key = key[:-7]  # "team_source" → "team"
                        json_path = Path(page_context[key])
                        if json_path.is_file():
                            import json as json_mod

                            data = json_mod.loads(json_path.read_text(encoding="utf-8"))
                            page_context[target_key] = data
                            context[target_key] = data
                            logger.debug(
                                f"Loaded {len(data)} items from {json_path} into '{target_key}'"
                            )

                # Pass top-level context keys for bibliography/team templates
                for key in (
                    "title",
                    "introduction",
                    "references",
                    "categories",
                    "team",
                    "partners",
                    "funders",
                    "resources",
                ):
                    if key in page_context and key not in context:
                        context[key] = page_context[key]

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

                # Generate .bib file alongside bibliography pages
                if context.get("references") and page_config.template in (
                    "bibliography.html",
                ):
                    bib_path = output_file_path.parent / "references.bib"
                    bib_content = self._references_to_bibtex(context["references"])
                    bib_path.write_text(bib_content, encoding="utf-8")
                    self.stats["total_files_generated"] += 1
                    logger.debug(
                        f"Generated BibTeX: {bib_path} ({len(context['references'])} refs)"
                    )
                self.stats["total_files_generated"] += 1
                logger.debug(f"Rendered static page: {output_file_path}")

            except Exception as e:
                logger.error(
                    f"Failed to process static page '{page_config.name}' ({page_config.template} -> {page_config.output_file}): {e}",
                    exc_info=True,
                )
                # Decide whether to raise or continue

        logger.info("Static pages processed.")

    def _process_groups(
        self,
        groups: List[GroupConfigWeb],
        jinja_env: Environment,
        html_params: HtmlExporterParams,
        output_dir: Path,
        repository: Database,
        group_filter: Optional[str] = None,
        lang: Optional[str] = None,
        languages: Optional[List[str]] = None,
        language_switcher: bool = False,
    ) -> None:
        """
        Processes each data group to generate index and detail pages.

        Args:
            groups: List of group configurations
            jinja_env: Jinja2 environment
            html_params: HTML export parameters
            output_dir: Output directory
            repository: Database instance
            group_filter: Optional filter to select specific groups
            lang: Current language code (for multi-language mode)
            languages: List of all supported languages
            language_switcher: Whether to enable language switcher
        """
        logger.info(f"Processing {len(groups)} data groups...")
        if not groups:
            return

        plugin_registry = PluginRegistry()

        for group_config in groups:
            # Skip group if filter is set and doesn't match
            if group_filter and group_config.group_by != group_filter:
                logger.debug(
                    f"Skipping group '{group_config.group_by}' due to filter '{group_filter}'."
                )
                continue

            group_by_key = group_config.group_by
            logger.info(f"Processing group: '{group_by_key}'")
            table_name, id_column = self._resolve_group_table_and_id(
                group_by_key, group_config.navigation_entity
            )

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
                    if group_output_dir.exists() and any(group_output_dir.iterdir()):
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
                        index_config_dict = group_config.index_generator.model_dump()
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
                        lang=lang,
                        languages=languages,
                        language_switcher=language_switcher,
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
                    lang=lang,
                    languages=languages,
                    language_switcher=language_switcher,
                )

            # --- End Render Index Page ---

            # --- Render Detail Pages ---
            # Resolve the transform output table for detail data (widget columns).
            # The transform stores its output in a table named after the group (e.g., "taxons"),
            # while the entity table (e.g., "entity_taxons") only has raw entity fields.
            detail_table_name = table_name
            detail_id_column = id_column
            transform_table = group_by_key
            transform_id_col = f"{group_by_key}_id"
            if repository.has_table(transform_table) and transform_table != table_name:
                transform_cols = repository.get_table_columns(transform_table) or []
                if transform_id_col in transform_cols:
                    detail_table_name = transform_table
                    detail_id_column = transform_id_col
                    logger.info(
                        f"Using transform output table '{transform_table}' for detail data "
                        f"(entity table: '{table_name}')"
                    )

            # Get index data: try entity table first, fallback to transform table
            index_data = self._get_group_index_data(repository, table_name, id_column)
            if not index_data and detail_table_name != table_name:
                logger.info(
                    f"No index data from entity table '{table_name}', "
                    f"trying transform table '{detail_table_name}'"
                )
                index_data = self._get_group_index_data(
                    repository, detail_table_name, detail_id_column
                )
            if not index_data:
                logger.info(
                    f"No items found for group '{group_by_key}', skipping detail pages."
                )
                continue

            detail_template_name = group_config.page_template or "_group_detail.html"

            # Outer try for the entire detail page generation process for this group
            try:
                # Pre-load detail template once per group
                detail_template = jinja_env.get_template(detail_template_name)
                logger.info(
                    f"Generating detail pages for {len(index_data)} items in group '{group_by_key}' using template '{detail_template_name}'..."
                )

                # Create a new progress bar for this group with the harmonized format
                import time

                start_time = time.time()

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                ) as group_progress:
                    detail_task = group_progress.add_task(
                        f"[green]Generating {group_by_key} detail pages[/green]",
                        total=len(index_data),
                    )

                    # Cache widget plugin classes to avoid repeated lookups
                    widget_cache = {}

                    for item_summary in index_data:
                        item_id = item_summary.get(id_column)
                        if item_id is None:
                            logger.warning(
                                f"Skipping item with missing ID in group '{group_by_key}' based on id_column '{id_column}'. Item data: {item_summary}"
                            )
                            group_progress.update(detail_task, advance=1)
                            continue

                        # Inner try for processing a single item
                        try:
                            # Get item data from transform output table (has widget columns)
                            item_data = self._get_item_detail_data(
                                repository, detail_table_name, detail_id_column, item_id
                            )
                            if not item_data:
                                # Warning already logged in _get_item_detail_data
                                group_progress.update(detail_task, advance=1)
                                continue

                            rendered_widgets: Dict[str, str] = {}
                            widget_dependencies: Set[str] = set()

                            # Sort widgets by layout.order before processing
                            sorted_widgets = sorted(
                                enumerate(group_config.widgets),
                                key=lambda x: (
                                    x[1].layout.order if x[1].layout else x[0]
                                ),
                            )

                            # Process widgets for this item
                            for i, widget_config in sorted_widgets:
                                # Create a unique key combining plugin type, data source, and index
                                widget_key = f"{widget_config.plugin}_{widget_config.data_source}_{i}"  # Unique key per widget instance

                                try:
                                    # Check if this is the hierarchical navigation widget
                                    is_hierarchical_nav = (
                                        widget_config.plugin
                                        == "hierarchical_nav_widget"
                                    )

                                    # Use cached widget class if available
                                    if widget_config.plugin not in widget_cache:
                                        widget_plugin_class = (
                                            plugin_registry.get_plugin(
                                                widget_config.plugin, PluginType.WIDGET
                                            )
                                        )
                                        if not widget_plugin_class:
                                            raise ConfigurationError(
                                                config_key="widgets.plugin",
                                                message=f"Widget plugin '{widget_config.plugin}' not found.",
                                            )
                                        widget_cache[widget_config.plugin] = (
                                            widget_plugin_class
                                        )
                                    else:
                                        widget_plugin_class = widget_cache[
                                            widget_config.plugin
                                        ]

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

                                        params_dict["current_item_id"] = (
                                            str(item_id)
                                            if item_id is not None
                                            else None
                                        )

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
                                            # Debug level instead of warning - missing data is often expected
                                            logger.debug(
                                                f"Data source '{data_source_key}' not found for widget '{widget_config.plugin}' "
                                                f"in {group_by_key} ID {item_id}. Skipping widget."
                                            )
                                            rendered_widgets[widget_key] = (
                                                f"<!-- Widget skipped: Data source '{data_source_key}' not found -->"
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

                            # Build site context with resolved localized strings
                            site_context = self._get_site_context(html_params, lang)
                            if lang:
                                site_context["current_lang"] = lang
                            if languages:
                                site_context["languages"] = languages
                            site_context["language_switcher"] = language_switcher

                            # Resolve navigation with localized strings
                            navigation = self._resolve_navigation(
                                html_params.navigation
                                if html_params.navigation
                                else [],
                                lang,
                            )
                            footer_navigation = self._resolve_footer_sections(
                                html_params.footer_navigation
                                if html_params.footer_navigation
                                else [],
                                lang,
                            )

                            detail_context = {
                                "site": site_context,
                                "navigation": navigation,
                                "footer_navigation": footer_navigation,
                                "id_column": id_column,
                                "group_config": group_config,
                                "group_by": group_by_key,
                                "item": item_data,
                                "widgets": rendered_widgets,
                                "dependencies": list(widget_dependencies),
                                "depth": depth,  # Add depth for relative URLs
                                "current_lang": lang,
                                "languages": languages or [],
                                "language_switcher": language_switcher,
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
                            self.stats["total_files_generated"] += 1
                            # logger.debug(f"Rendered detail page: {detail_output_path}")

                        except Exception as item_render_err:  # Catch errors specific to rendering this single item
                            logger.error(
                                f"Failed rendering detail page for item {item_id} in group '{group_by_key}': {item_render_err}",
                                exc_info=True,
                            )
                            # Continue to the next item even if one fails

                        # Update progress after each item (success or failure)
                        current_duration = time.time() - start_time
                        group_progress.update(
                            detail_task,
                            advance=1,
                            description=f"[green]Generating {group_by_key} detail pages • {current_duration:.1f}s[/green]",
                        )

                    # Update task description to show completion after all items processed
                    duration = time.time() - start_time
                    group_progress.update(
                        detail_task,
                        description=f"[green][{emoji('✓', '[OK]')}] {group_by_key} detail pages completed • {duration:.1f}s[/green]",
                    )

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
        self,
        referential_data_source: str,
        required_fields: Optional[List[str]] = None,
        preferred_order_fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load and cache navigation reference data.

        Args:
            referential_data_source: Name of the reference table (e.g., 'taxons')
            required_fields: List of specific fields to select. If None, selects all fields.
            preferred_order_fields: Optional list defining desired ORDER BY precedence.

        Returns:
            List of all items from the reference table
        """
        # Check cache first
        order_key = ",".join(preferred_order_fields) if preferred_order_fields else ""
        cache_key = (
            f"{referential_data_source}:"
            f"{','.join(required_fields) if required_fields else '*'}:"
            f"{order_key}"
        )
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
                # Determine deterministic ORDER BY clause prioritising nested-set structure
                order_candidates: List[str] = []
                if preferred_order_fields:
                    for field in preferred_order_fields:
                        if field in required_fields and field not in order_candidates:
                            order_candidates.append(field)
                if not order_candidates:
                    if required_fields:
                        order_candidates.append(required_fields[0])
                    else:
                        order_candidates.append("id")
                order_clause = ", ".join(f'"{field}"' for field in order_candidates)
                query = (
                    f'SELECT {fields_str} FROM "{referential_data_source}" '
                    f"ORDER BY {order_clause}"
                )
            else:
                query = f'SELECT * FROM "{referential_data_source}" ORDER BY "id"'
            results = self.db.fetch_all(query)

            if results:
                # Convert to list of dicts and cache
                data_list = [dict(row) for row in results]
                # FIX: Use consistent cache_key for both storage and retrieval
                self._navigation_cache[cache_key] = data_list
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
                # Add any custom fields that might be needed
                if "shape_type_field" in params:
                    required_fields.add(params["shape_type_field"])

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

        # Use navigation_entity if specified, otherwise fall back to group_by
        entity_name = group_config.navigation_entity or group_by_key

        reference_table = self._resolve_reference_table_name(entity_name)

        # Extract required fields from hierarchical navigation widgets
        required_fields = self._extract_navigation_fields(group_config)

        # Check which fields actually exist in the table
        try:
            table_columns = self.db.get_table_columns(reference_table)
            # Filter to only include fields that exist in the table
            existing_fields = [f for f in required_fields if f in table_columns]

            if not existing_fields:
                logger.warning(
                    f"None of the required fields {required_fields} exist in table {reference_table}"
                )
                id_candidates = [
                    col for col in table_columns if col == "id" or col.endswith("_id")
                ]
                if id_candidates:
                    existing_fields = [id_candidates[0]]
                    logger.debug(
                        "Using fallback identifier column '%s' for %s",
                        existing_fields[0],
                        reference_table,
                    )
                else:
                    logger.error(
                        "No suitable identifier column found in table %s; skipping navigation generation",
                        reference_table,
                    )
                    return

            logger.debug(f"Using fields {existing_fields} from table {reference_table}")
        except Exception as e:
            logger.error("Could not get columns for table %s: %s", reference_table, e)
            logger.error("Cannot load navigation data without valid column information")
            return

        # Build ordering preference (nested set first, then adjacency fallbacks)
        preferred_order_fields: List[str] = []
        if "lft" in existing_fields:
            preferred_order_fields.append("lft")
            if "rght" in existing_fields:
                preferred_order_fields.append("rght")
            if "level" in existing_fields:
                preferred_order_fields.append("level")
        else:
            if "level" in existing_fields:
                preferred_order_fields.append("level")
            if "parent_id" in existing_fields:
                preferred_order_fields.append("parent_id")

        if "id" in existing_fields:
            preferred_order_fields.append("id")

        # Load navigation data with only existing fields
        navigation_data = self._load_and_cache_navigation_data(
            reference_table,
            existing_fields,
            preferred_order_fields,
        )
        if not navigation_data:
            logger.warning(f"No navigation data to generate JS for {group_by_key}")
            return

        # Ensure identifier columns are serialised as strings to avoid float rounding in JS
        id_like_fields = [
            field
            for field in existing_fields
            if field == "id" or field.endswith("_id") or field == "parent_id"
        ]
        if id_like_fields:
            for item in navigation_data:
                for field in id_like_fields:
                    value = item.get(field)
                    if value is not None:
                        try:
                            item[field] = str(int(value))
                        except (TypeError, ValueError):
                            item[field] = str(value)

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
            self.stats["total_files_generated"] += 1

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
        lang: Optional[str] = None,
        languages: Optional[List[str]] = None,
        language_switcher: bool = False,
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
            lang: Current language code (for multi-language mode)
            languages: List of all supported languages
            language_switcher: Whether to enable language switcher
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
            index_template_name = group_config.index_template or "_group_index.html"

            index_template = jinja_env.get_template(index_template_name)
            logger.debug(f"Rendering traditional index template: {index_template_name}")

            # Build site context with resolved localized strings
            site_context = self._get_site_context(html_params, lang)
            if lang:
                site_context["current_lang"] = lang
            if languages:
                site_context["languages"] = languages
            site_context["language_switcher"] = language_switcher

            # Resolve navigation with localized strings
            navigation = self._resolve_navigation(
                html_params.navigation if html_params.navigation else [], lang
            )
            footer_navigation = self._resolve_footer_sections(
                html_params.footer_navigation if html_params.footer_navigation else [],
                lang,
            )

            # Convert DB rows to plain dicts (RowMapping is not JSON-serializable).
            normalized_items = [
                dict(item) if not isinstance(item, dict) else item
                for item in index_data
            ]

            # Build resilient defaults for legacy/traditional index rendering.
            first_item = normalized_items[0] if normalized_items else {}
            preferred_name_fields = ["name", "full_name", "label", "title"]
            name_field = next(
                (f for f in preferred_name_fields if f in first_item), None
            )
            if not name_field and first_item:
                name_field = next(
                    (k for k in first_item.keys() if k != id_column), None
                )
            if not name_field:
                name_field = id_column

            default_page_config = {
                "title": group_by_key.replace("_", " ").title(),
                "description": "",
                "items_per_page": 24,
            }

            index_generator_cfg = {}
            if (
                hasattr(group_config, "index_generator")
                and group_config.index_generator
            ):
                if hasattr(group_config.index_generator, "model_dump"):
                    index_generator_cfg = group_config.index_generator.model_dump()
                elif isinstance(group_config.index_generator, dict):
                    index_generator_cfg = group_config.index_generator

            page_config = index_generator_cfg.get("page_config", default_page_config)
            display_fields = index_generator_cfg.get(
                "display_fields",
                [
                    {
                        "name": name_field,
                        "source": name_field,
                        "type": "text",
                        "label": str(name_field).replace("_", " ").title(),
                        "searchable": True,
                    }
                ],
            )
            views = index_generator_cfg.get(
                "views",
                [
                    {"type": "grid", "default": True},
                    {"type": "list", "default": False},
                ],
            )
            filters = index_generator_cfg.get("filters", [])

            index_context = {
                "site": site_context,
                "navigation": navigation,
                "footer_navigation": footer_navigation,
                "group_by": group_by_key,
                "items": normalized_items,
                "group_config": group_config,
                "id_column": id_column,
                "current_lang": lang,
                "languages": languages or [],
                "language_switcher": language_switcher,
                # Backward-compatible variables expected by _group_index.html
                "page_config": page_config,
                "index_config": {
                    "group_by": group_by_key,
                    "page_config": page_config,
                    "display_fields": display_fields,
                    "filters": filters,
                    "views": views,
                },
                "items_data": normalized_items,
                "depth": group_config.output_pattern.count("/")
                if group_config.output_pattern
                else 0,
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
            self.stats["total_files_generated"] += 1
            logger.debug(
                f"Rendered traditional index page for '{group_by_key}': {index_output_path}"
            )

        except Exception as e:
            logger.error(
                f"Error generating traditional index for group '{group_by_key}': {e}",
                exc_info=True,
            )
            raise
