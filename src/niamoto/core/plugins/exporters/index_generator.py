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
from niamoto.core.plugins.base import ExporterPlugin, PluginType, register
from niamoto.core.plugins.models import IndexGeneratorConfig, IndexGeneratorDisplayField

logger = logging.getLogger(__name__)


@register("index_generator", PluginType.EXPORTER)
class IndexGeneratorPlugin(ExporterPlugin):
    """Plugin for generating configurable index pages for groups."""

    def __init__(self, db: Database):
        """Initialize the plugin with database connection."""
        super().__init__(db)

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

            # Process each item
            processed_items = []
            for item in items:
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
                        filter_value = self._get_nested_value(item, filter_config.field)
                        if filter_config.operator == "in":
                            if filter_value not in filter_config.values:
                                include_item = False
                                break
                        elif filter_config.operator == "equals":
                            if filter_value != filter_config.values[0]:
                                include_item = False
                                break

                    if not include_item:
                        continue

                # Extract display fields
                processed_item = {id_column: item[id_column]}

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

            # Prepare template context
            index_config = {
                "group_by": group_by,
                "id_column": f"{group_by}_id",
                "output_pattern": config.output_pattern.format(
                    group_by=group_by, id="{id}"
                ),
                "page_config": config.page_config.model_dump(),
                "display_fields": [
                    field.model_dump() for field in config.display_fields
                ],
                "views": [view.model_dump() for view in config.views]
                if config.views
                else [],
            }

            # Calculate depth based on output file path
            # For example: output_dir/taxon/index.html has depth 1
            depth = 1  # Index pages are always one level deep (group_by/index.html)

            context = {
                "site": html_params.site.model_dump() if html_params.site else {},
                "navigation": html_params.navigation if html_params.navigation else [],
                "group_by": group_by,
                "index_config": index_config,
                "items_data": items_data,
                "page_config": config.page_config.model_dump(),
                "depth": depth,
            }

            # Load and render template
            try:
                template = jinja_env.get_template(config.template)
            except Exception as template_error:
                logger.error(
                    f"Failed to load template '{config.template}' for group '{group_by}'. "
                    f"Available templates: {jinja_env.list_templates()}"
                )
                raise ProcessError(
                    f"Template '{config.template}' not found for group '{group_by}'"
                ) from template_error

            rendered_html = template.render(context)

            # Write output
            output_file = output_dir / f"{group_by}" / "index.html"
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
