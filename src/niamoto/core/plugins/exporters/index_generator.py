# src/niamoto/core/plugins/exporters/index_generator.py

"""
Index Generator Plugin

This plugin generates index pages for groups (taxon, plot, shape) with configurable
filtering, display fields, and interactive features like search, pagination, and multiple views.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from niamoto.common.database import Database
from niamoto.common.exceptions import ProcessError
from niamoto.common.hierarchy_context import (
    build_hierarchy_contexts,
    detect_hierarchy_metadata,
)
from niamoto.common.i18n import I18nResolver
from niamoto.common.table_resolver import resolve_entity_table
from niamoto.core.plugins.base import ExporterPlugin, PluginType, register
from niamoto.core.plugins.models import IndexGeneratorConfig, IndexGeneratorDisplayField

logger = logging.getLogger(__name__)


@register("index_generator", PluginType.EXPORTER)
class IndexGeneratorPlugin(ExporterPlugin):
    """Plugin for generating configurable index pages for groups."""

    def __init__(self, db: Database, registry=None):
        """Initialize the plugin with database connection."""
        super().__init__(db, registry)

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

        Args:
            data: Dictionary to search in
            path: Dot-separated path like "general_info.name.value"

        Returns:
            Value at the path or None if not found
        """
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _parse_json_field(self, field_value: Any) -> Optional[Any]:
        """
        Parse JSON field value, handling both strings and dict objects.

        Args:
            field_value: Value that might be JSON string or dict

        Returns:
            Parsed dictionary or None if parsing fails
        """
        if field_value is None:
            return None

        if isinstance(field_value, dict):
            return field_value

        if isinstance(field_value, str):
            try:
                return json.loads(field_value)
            except (json.JSONDecodeError, ValueError):
                logger.debug(f"Failed to parse JSON field: {field_value}")
                return None

        return None

    def _resolve_template_name(self, template_name: str) -> str:
        """Normalize legacy index template names to the canonical filename."""
        if template_name == "group_index.html":
            return "_group_index.html"
        return template_name

    def _normalize_filter_value(self, value: Any) -> Any:
        """Normalize values so config filters match JSON/native DB values."""
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
            if lowered in {"null", "none"}:
                return None

            try:
                if "." in lowered:
                    return float(lowered)
                return int(lowered)
            except ValueError:
                return value

        return value

    def _extract_field_value(
        self, item: Dict[str, Any], field: IndexGeneratorDisplayField
    ) -> Any:
        """
        Extract field value from item using configured source path.

        Args:
            item: Data item
            field: Field configuration

        Returns:
            Extracted value or None
        """
        # Try main source path
        value = self._get_nested_value(item, field.source)

        # If value is None and we have a fallback, try that
        if value is None and field.fallback:
            value = item.get(field.fallback)

        # Handle special JSON array types
        if field.type == "json_array" and isinstance(value, str):
            try:
                # Handle string representations of arrays
                value = json.loads(value.replace("'", '"'))
            except (json.JSONDecodeError, ValueError):
                logger.debug(
                    f"Failed to parse JSON array for field {field.name}: {value}"
                )
                value = None

        return value

    def _resolve_entity_join_column(
        self,
        entity_table: str,
        entity_columns: set[str],
        item_ids: set[Any],
        id_column: str,
    ) -> Optional[str]:
        """Pick the entity-side join column that matches the transformed IDs best."""
        best_column: Optional[str] = None
        best_overlap = 0

        for candidate in [id_column, "id"]:
            if candidate not in entity_columns:
                continue

            query = (
                f'SELECT "{candidate}" FROM "{entity_table}" '
                f'WHERE "{candidate}" IS NOT NULL'
            )
            rows = self.db.fetch_all(query)
            overlap = sum(1 for row in rows if row[candidate] in item_ids)

            if overlap > best_overlap:
                best_column = candidate
                best_overlap = overlap

        return best_column

    def _get_entity_rows_by_group_id(
        self,
        group_by: str,
        id_column: str,
        config: IndexGeneratorConfig,
        item_ids: set[Any],
    ) -> Dict[Any, Dict[str, Any]]:
        """Load entity-side fields such as extra_data for the current reference."""
        entity_table = resolve_entity_table(self.db, group_by, kind="reference")
        if (
            not entity_table
            or entity_table == group_by
            or not self.db.has_table(entity_table)
        ):
            return {}

        try:
            entity_columns = set(self.db.get_table_columns(entity_table))
        except TypeError:
            logger.debug(
                "Skipping entity merge for '%s': columns for '%s' are not iterable",
                group_by,
                entity_table,
            )
            return {}

        if not entity_columns:
            return {}

        join_column = self._resolve_entity_join_column(
            entity_table, entity_columns, item_ids, id_column
        )
        if not join_column:
            logger.debug(
                "Skipping entity merge for '%s': no join column matches transformed IDs in '%s'",
                group_by,
                entity_table,
            )
            return {}

        selected_columns = {join_column}
        hierarchy_metadata = detect_hierarchy_metadata(
            entity_columns, join_field=join_column
        )
        if hierarchy_metadata is not None:
            selected_columns.add(hierarchy_metadata.id_field)
            selected_columns.add(hierarchy_metadata.rank_field)
            selected_columns.add(hierarchy_metadata.name_field)
            if hierarchy_metadata.parent_field:
                selected_columns.add(hierarchy_metadata.parent_field)
            if hierarchy_metadata.left_field:
                selected_columns.add(hierarchy_metadata.left_field)
            if hierarchy_metadata.right_field:
                selected_columns.add(hierarchy_metadata.right_field)

        for field in config.display_fields:
            field_root = field.source.split(".", 1)[0]
            if field_root in entity_columns:
                selected_columns.add(field_root)

            if field.fallback and field.fallback in entity_columns:
                selected_columns.add(field.fallback)

        for filter_config in config.filters or []:
            field_root = filter_config.field.split(".", 1)[0]
            if field_root in entity_columns:
                selected_columns.add(field_root)

        if len(selected_columns) == 1:
            return {}

        quoted_columns = ", ".join(f'"{column}"' for column in sorted(selected_columns))
        query = (
            f'SELECT {quoted_columns} FROM "{entity_table}" ORDER BY "{join_column}"'
        )

        rows = self.db.fetch_all(query)
        entity_rows = {
            row[join_column]: dict(row)
            for row in rows
            if row.get(join_column) is not None
        }

        if hierarchy_metadata is None or not entity_rows:
            return entity_rows

        hierarchy_contexts = build_hierarchy_contexts(
            entity_rows.values(), hierarchy_metadata
        )
        for join_value, context in hierarchy_contexts.items():
            if join_value in entity_rows:
                entity_rows[join_value]["hierarchy_context"] = context

        return entity_rows

    def _get_group_data(
        self, group_by: str, config: IndexGeneratorConfig
    ) -> List[Dict[str, Any]]:
        """
        Fetch and process data for the group index.

        Args:
            group_by: Group type (taxon, plot, shape)
            config: Index generator configuration

        Returns:
            List of processed items for the index
        """
        try:
            # Get table info
            table_name = group_by
            id_column = f"{group_by}_id"

            # Verify table exists
            if not self.db.has_table(table_name):
                logger.error(f"Table '{table_name}' does not exist")
                return []

            # Base query - get all items
            query = f'SELECT * FROM "{table_name}" ORDER BY {id_column}'
            logger.debug(f"Executing query: {query}")

            results = self.db.fetch_all(query)
            if not results:
                logger.warning(f"No data found in table '{table_name}'")
                return []

            # Convert to list of dicts
            items = [dict(row) for row in results]
            logger.info(f"Found {len(items)} items in table '{table_name}'")
            item_ids = {
                item[id_column] for item in items if item.get(id_column) is not None
            }
            entity_rows = self._get_entity_rows_by_group_id(
                group_by, id_column, config, item_ids
            )

            # Process each item
            processed_items = []
            for item in items:
                entity_row = entity_rows.get(item.get(id_column))
                if entity_row:
                    for key, value in entity_row.items():
                        if key not in item or item[key] is None:
                            item[key] = value

                # Parse all JSON fields (not just general_info)
                for key, value in item.items():
                    # Try to parse any field that looks like JSON
                    if isinstance(value, str) and value.strip().startswith("{"):
                        parsed_value = self._parse_json_field(value)
                        if parsed_value:
                            item[key] = parsed_value
                    elif isinstance(value, dict):
                        # Already a dict, no need to parse
                        item[key] = value

                # Apply filters if configured
                if config.filters:
                    include_item = True
                    for filter_config in config.filters:
                        filter_value = self._normalize_filter_value(
                            self._get_nested_value(item, filter_config.field)
                        )
                        normalized_values = [
                            self._normalize_filter_value(v)
                            for v in filter_config.values
                        ]
                        if filter_config.operator == "in":
                            if filter_value not in normalized_values:
                                include_item = False
                                break
                        elif filter_config.operator == "equals":
                            expected = (
                                normalized_values[0] if normalized_values else None
                            )
                            if filter_value != expected:
                                include_item = False
                                break

                    if not include_item:
                        continue

                # Extract display fields
                # Convert ID to string to preserve precision in JSON/JavaScript
                item_id = item[id_column]
                processed_item = {
                    id_column: str(item_id) if item_id is not None else None
                }

                for field in config.display_fields:
                    field_value = self._extract_field_value(item, field)
                    processed_item[field.name] = field_value

                processed_items.append(processed_item)

            logger.info(f"Processed {len(processed_items)} items after filtering")
            return processed_items

        except Exception as e:
            logger.error(
                f"Error fetching group data for '{group_by}': {e}", exc_info=True
            )
            raise ProcessError(f"Failed to fetch data for group '{group_by}'") from e

    def generate_index(
        self,
        group_by: str,
        config: IndexGeneratorConfig,
        output_dir: Path,
        jinja_env: Any,
        html_params: Any,
        lang: Optional[str] = None,
        languages: Optional[List[str]] = None,
        language_switcher: bool = False,
        site_context: Optional[Dict[str, Any]] = None,
        navigation: Optional[List[Dict[str, Any]]] = None,
        footer_navigation: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Generate the index page for a group.

        Args:
            group_by: Group type (taxon, plot, shape)
            config: Index generator configuration
            output_dir: Base output directory
            jinja_env: Jinja2 environment
            html_params: HTML exporter parameters
        """
        try:
            logger.info(f"Generating index for group '{group_by}'")

            # Get data
            items_data = self._get_group_data(group_by, config)

            if not items_data:
                logger.warning(f"No data to generate index for group '{group_by}'")
                return

            output_file = output_dir / f"{group_by}" / "index.html"
            nav_depth = max(len(output_file.relative_to(output_dir).parts) - 1, 0)
            is_multilang = bool(lang and languages and len(languages) > 1)
            depth = nav_depth + (1 if is_multilang else 0)
            site_context_data = (
                site_context
                if site_context is not None
                else html_params.site.model_dump()
                if html_params.site
                else {}
            )
            default_lang = (
                lang
                or site_context_data.get("lang")
                or site_context_data.get("current_lang")
                or "fr"
            )
            available_languages = (
                list(languages or [])
                or list(site_context_data.get("languages") or [])
                or [default_lang]
            )
            i18n_resolver = I18nResolver(
                default_lang=default_lang,
                available_languages=available_languages,
            )
            resolved_site_context = i18n_resolver.resolve_recursive(site_context_data)
            resolved_page_config = i18n_resolver.resolve_recursive(
                config.page_config.model_dump()
            )
            resolved_display_fields = [
                i18n_resolver.resolve_recursive(field.model_dump())
                for field in config.display_fields
            ]

            # Prepare template context
            index_config = {
                "group_by": group_by,
                "id_column": f"{group_by}_id",
                "output_pattern": config.output_pattern.format(
                    group_by=group_by, id="{id}"
                ),
                "page_config": resolved_page_config,
                "display_fields": resolved_display_fields,
                "views": [view.model_dump() for view in config.views]
                if config.views
                else [],
            }

            context = {
                "site": resolved_site_context,
                "navigation": navigation
                if navigation is not None
                else html_params.navigation
                if html_params.navigation
                else [],
                "footer_navigation": footer_navigation
                if footer_navigation is not None
                else [s.model_dump() for s in html_params.footer_navigation]
                if html_params.footer_navigation
                else [],
                "group_by": group_by,
                "index_config": index_config,
                "items_data": items_data,
                "page_config": resolved_page_config,
                "nav_depth": nav_depth,
                "depth": depth,
                "current_lang": lang,
                "languages": languages or [],
                "language_switcher": language_switcher,
            }

            # Load and render template
            template_name = self._resolve_template_name(config.template)
            try:
                template = jinja_env.get_template(template_name)
            except Exception as template_error:
                logger.error(
                    f"Failed to load template '{template_name}' for group '{group_by}'. "
                    f"Available templates: {jinja_env.list_templates()}"
                )
                raise ProcessError(
                    f"Template '{template_name}' not found for group '{group_by}'"
                ) from template_error

            rendered_html = template.render(context)

            # Write output
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(rendered_html)

            logger.info(f"Generated index page: {output_file}")

        except Exception as e:
            logger.error(
                f"Error generating index for group '{group_by}': {e}", exc_info=True
            )
            raise ProcessError(
                f"Failed to generate index for group '{group_by}'"
            ) from e

    def export(
        self,
        target_config: Any,
        repository: Database,
        group_filter: Optional[str] = None,
    ) -> None:
        """
        Main export method - not used for this plugin.
        This plugin is called directly by the HTML page exporter.
        """
        raise NotImplementedError(
            "IndexGeneratorPlugin should be called directly, not through export()"
        )
