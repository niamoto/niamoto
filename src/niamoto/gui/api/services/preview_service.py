"""
Shared preview service for widget previews.

This service centralizes the common logic for generating widget previews
across different endpoints (recipes, templates, layout).
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd
import yaml

from niamoto.common.database import Database
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType

logger = logging.getLogger(__name__)


class PreviewService:
    """Service for generating widget previews."""

    # ==========================================================================
    # HTML WRAPPER
    # ==========================================================================

    @staticmethod
    def wrap_html_response(content: str, title: str = "Preview") -> str:
        """Wrap widget HTML in a complete HTML document for iframe display.

        Args:
            content: The widget HTML content
            title: Page title

        Returns:
            Complete HTML document string
        """
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: system-ui, -apple-system, sans-serif;
            background: transparent;
        }}
        .plotly-graph-div {{
            width: 100% !important;
            height: 100% !important;
        }}
        .error {{
            color: #ef4444;
            padding: 1rem;
            text-align: center;
        }}
        .info {{
            color: #6b7280;
            padding: 1rem;
            text-align: center;
        }}
    </style>
    <script src="/api/site/assets/js/vendor/plotly/3.0.1_plotly.min.js"></script>
</head>
<body>
{content}
</body>
</html>"""

    # ==========================================================================
    # TRANSFORMER EXECUTION
    # ==========================================================================

    @staticmethod
    def execute_transformer(
        db: Optional[Database],
        plugin_name: str,
        params: Dict[str, Any],
        data: Union[pd.DataFrame, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a transformer plugin on data.

        Args:
            db: Database instance (can be None for some transformers)
            plugin_name: Name of the transformer plugin
            params: Transformer parameters
            data: Input data (DataFrame or dict for class_object transformers)

        Returns:
            Transformed data dictionary

        Raises:
            ValueError: If transformer execution fails
        """
        try:
            plugin_class = PluginRegistry.get_plugin(
                plugin_name, PluginType.TRANSFORMER
            )
            plugin_instance = plugin_class(db=db)

            # Build config in expected format
            transform_config = {
                "plugin": plugin_name,
                "params": params,
            }

            return plugin_instance.transform(data, transform_config)
        except Exception as e:
            logger.exception(f"Error executing transformer '{plugin_name}': {e}")
            raise ValueError(f"Transformer error: {str(e)}")

    # ==========================================================================
    # WIDGET RENDERING
    # ==========================================================================

    @staticmethod
    def render_widget(
        db: Optional[Database],
        plugin_name: str,
        data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        title: str = "Widget",
    ) -> str:
        """Render a widget with the given data.

        Args:
            db: Database instance (can be None)
            plugin_name: Name of the widget plugin
            data: Data to render
            params: Widget parameters
            title: Widget title

        Returns:
            HTML string of rendered widget
        """
        try:
            plugin_class = PluginRegistry.get_plugin(plugin_name, PluginType.WIDGET)
            plugin_instance = plugin_class(db=db)

            # Build widget params
            widget_params: Dict[str, Any] = {"title": title}
            if params:
                widget_params.update(params)

            # Validate params if the plugin has a param_schema
            if (
                hasattr(plugin_instance, "param_schema")
                and plugin_instance.param_schema
            ):
                validated_params = plugin_instance.param_schema.model_validate(
                    widget_params
                )
            else:
                validated_params = widget_params

            return plugin_instance.render(data, validated_params)
        except Exception as e:
            logger.exception(f"Error rendering widget '{plugin_name}': {e}")
            return f"<p class='error'>Widget render error: {str(e)}</p>"

    # ==========================================================================
    # DATA LOADING
    # ==========================================================================

    @staticmethod
    def load_import_config(work_dir: Path) -> Dict[str, Any]:
        """Load import.yml configuration.

        Args:
            work_dir: Working directory path

        Returns:
            Import configuration dictionary
        """
        import_path = work_dir / "config" / "import.yml"
        if not import_path.exists():
            return {}
        with open(import_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def get_hierarchy_info(
        import_config: Dict[str, Any], group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract hierarchy info from import config.

        Args:
            import_config: Import configuration dictionary
            group_by: Reference name to look for

        Returns:
            Dictionary with reference_name, table_name, id_field, parent_field, fk_column
        """
        entities = import_config.get("entities", {})
        references = entities.get("references", {})

        # Find reference that matches group_by
        if group_by and group_by in references:
            ref = references[group_by]
            # Get FK column from connector.extraction.id_column
            extraction = ref.get("connector", {}).get("extraction", {})
            fk_column = extraction.get("id_column", "id_taxonref")
            return {
                "reference_name": group_by,
                "table_name": f"entity_{group_by}",
                "id_field": ref.get("identifier", "id"),
                "parent_field": ref.get("hierarchy", {}).get(
                    "parent_field", "id_parent"
                ),
                "fk_column": fk_column,
            }

        # Fallback to first hierarchical reference
        for ref_name, ref in references.items():
            if ref.get("hierarchy"):
                extraction = ref.get("connector", {}).get("extraction", {})
                fk_column = extraction.get("id_column", "id_taxonref")
                return {
                    "reference_name": ref_name,
                    "table_name": f"entity_{ref_name}",
                    "id_field": ref.get("identifier", "id"),
                    "parent_field": ref.get("hierarchy", {}).get(
                        "parent_field", "id_parent"
                    ),
                    "fk_column": fk_column,
                }

        return {
            "reference_name": "taxon",
            "table_name": "entity_taxon",
            "id_field": "id",
            "parent_field": "id_parent",
            "fk_column": "id_taxonref",
        }

    @staticmethod
    def load_sample_occurrences(
        db: Database, hierarchy_info: Dict[str, Any], limit: int = 500
    ) -> pd.DataFrame:
        """Load sample occurrence data for preview.

        For preview purposes, we load a representative sample of occurrences.
        We try to get occurrences for a single entity first (for realistic data),
        but fall back to random sample if that fails.

        Args:
            db: Database instance
            hierarchy_info: Hierarchy info from get_hierarchy_info
            limit: Maximum number of rows to load

        Returns:
            DataFrame with occurrence data
        """
        # Get the foreign key column
        fk_column = hierarchy_info.get("fk_column", "id_taxonref")

        try:
            # First, check which occurrence table exists
            tables = db.execute_sql("SHOW TABLES", fetch_all=True)
            table_names = [t[0] for t in tables] if tables else []

            occ_table = (
                "dataset_occurrences"
                if "dataset_occurrences" in table_names
                else "occurrences"
            )

            # For preview, load occurrences grouped by a single FK value
            # This gives us a realistic sample for a single taxon/entity
            query = f"""
                SELECT * FROM {occ_table}
                WHERE {fk_column} = (
                    SELECT {fk_column} FROM {occ_table}
                    WHERE {fk_column} IS NOT NULL
                    GROUP BY {fk_column}
                    HAVING COUNT(*) >= 10
                    LIMIT 1
                )
                LIMIT {limit}
            """
            df = pd.read_sql(query, db.engine)

            if df.empty:
                # Fallback: just get some occurrences
                simple_query = f"SELECT * FROM {occ_table} LIMIT {limit}"
                df = pd.read_sql(simple_query, db.engine)

            return df

        except Exception as e:
            logger.warning(f"Error loading sample occurrences: {e}")
            return pd.DataFrame()

    @staticmethod
    def load_csv_data(
        csv_path: Path, class_object_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Load data from a CSV file, optionally filtering by class_object column.

        Args:
            csv_path: Path to the CSV file
            class_object_name: Optional class_object value to filter by

        Returns:
            Dictionary with CSV data
        """
        import json

        try:
            # Detect delimiter
            with open(csv_path, "r", encoding="utf-8") as f:
                first_line = f.readline()
                delimiter = (
                    ";" if first_line.count(";") > first_line.count(",") else ","
                )

            df = pd.read_csv(csv_path, delimiter=delimiter)

            # If class_object specified, try to find matching row
            if class_object_name and "class_object" in df.columns:
                matching = df[df["class_object"] == class_object_name]
                if not matching.empty:
                    row = matching.iloc[0]
                    # Parse JSON columns if present
                    result = {}
                    for col in df.columns:
                        val = row[col]
                        if isinstance(val, str) and (
                            val.startswith("{") or val.startswith("[")
                        ):
                            try:
                                result[col] = json.loads(val)
                            except (json.JSONDecodeError, ValueError):
                                result[col] = val
                        else:
                            result[col] = val
                    return result

            # Return first row as sample
            if not df.empty:
                row = df.iloc[0]
                result = {}
                for col in df.columns:
                    val = row[col]
                    if isinstance(val, str) and (
                        val.startswith("{") or val.startswith("[")
                    ):
                        try:
                            result[col] = json.loads(val)
                        except (json.JSONDecodeError, ValueError):
                            result[col] = val
                    else:
                        result[col] = val
                return result

            return {}
        except Exception as e:
            logger.warning(f"Error loading CSV {csv_path}: {e}")
            return {}

    # ==========================================================================
    # HIGH-LEVEL PREVIEW GENERATION
    # ==========================================================================

    @classmethod
    def generate_preview(
        cls,
        db: Optional[Database],
        work_dir: Path,
        group_by: str,
        transformer_plugin: str,
        transformer_params: Dict[str, Any],
        widget_plugin: str,
        widget_params: Optional[Dict[str, Any]] = None,
        widget_title: str = "Preview",
    ) -> str:
        """Generate a complete widget preview.

        This is the main entry point for generating previews. It handles:
        - Class object transformers (CSV-based)
        - Occurrence-based transformers (database-based)

        Args:
            db: Database instance
            work_dir: Working directory path
            group_by: Reference name for grouping
            transformer_plugin: Transformer plugin name
            transformer_params: Transformer parameters
            widget_plugin: Widget plugin name
            widget_params: Widget parameters
            widget_title: Title for the widget

        Returns:
            Complete HTML string for the preview
        """
        # Check if this is a class_object-based transformer (CSV data)
        if transformer_plugin.startswith("class_object_"):
            return cls._generate_class_object_preview(
                db,
                work_dir,
                group_by,
                transformer_plugin,
                transformer_params,
                widget_plugin,
                widget_params,
                widget_title,
            )
        else:
            return cls._generate_occurrence_preview(
                db,
                work_dir,
                group_by,
                transformer_plugin,
                transformer_params,
                widget_plugin,
                widget_params,
                widget_title,
            )

    @classmethod
    def _generate_class_object_preview(
        cls,
        db: Optional[Database],
        work_dir: Path,
        group_by: str,
        transformer_plugin: str,
        transformer_params: Dict[str, Any],
        widget_plugin: str,
        widget_params: Optional[Dict[str, Any]],
        widget_title: str,
    ) -> str:
        """Generate preview for class_object-based transformers."""
        # Get source name from params
        source_name = transformer_params.get("source", "")
        class_object_name = transformer_params.get("class_object")

        # Find CSV file for this source
        csv_path = cls._get_csv_path_for_source(work_dir, group_by, source_name)

        if not csv_path or not csv_path.exists():
            return cls.wrap_html_response(
                f"<p class='info'>Source CSV '{source_name}' not found</p>"
            )

        # Load data from CSV
        csv_data = cls.load_csv_data(csv_path, class_object_name)

        if not csv_data:
            return cls.wrap_html_response(
                "<p class='info'>No data found in CSV source</p>"
            )

        # Execute transformer
        try:
            result = cls.execute_transformer(
                db, transformer_plugin, transformer_params, csv_data
            )
        except ValueError as e:
            return cls.wrap_html_response(f"<p class='error'>{str(e)}</p>")

        if not result:
            return cls.wrap_html_response(
                "<p class='info'>Transformer returned no data</p>"
            )

        # Render widget
        widget_html = cls.render_widget(
            db, widget_plugin, result, widget_params, widget_title
        )

        return cls.wrap_html_response(widget_html, title=widget_title)

    @classmethod
    def _generate_occurrence_preview(
        cls,
        db: Optional[Database],
        work_dir: Path,
        group_by: str,
        transformer_plugin: str,
        transformer_params: Dict[str, Any],
        widget_plugin: str,
        widget_params: Optional[Dict[str, Any]],
        widget_title: str,
    ) -> str:
        """Generate preview for occurrence-based transformers."""
        if not db:
            return cls.wrap_html_response("<p class='error'>Database not found</p>")

        # Load import config for hierarchy info
        import_config = cls.load_import_config(work_dir)
        hierarchy_info = cls.get_hierarchy_info(import_config, group_by)

        # Load sample data
        sample_data = cls.load_sample_occurrences(db, hierarchy_info)

        if sample_data.empty:
            return cls.wrap_html_response(
                "<p class='info'>No occurrence data available for preview</p>"
            )

        # Execute transformer
        try:
            result = cls.execute_transformer(
                db, transformer_plugin, transformer_params, sample_data
            )
        except ValueError as e:
            return cls.wrap_html_response(f"<p class='error'>{str(e)}</p>")

        if not result:
            return cls.wrap_html_response(
                "<p class='info'>Transformer returned no data</p>"
            )

        # Render widget
        widget_html = cls.render_widget(
            db, widget_plugin, result, widget_params, widget_title
        )

        return cls.wrap_html_response(widget_html, title=widget_title)

    @staticmethod
    def _get_csv_path_for_source(
        work_dir: Path, group_by: str, source_name: str
    ) -> Optional[Path]:
        """Get CSV path for a source name from transform.yml."""
        transform_path = work_dir / "config" / "transform.yml"
        if not transform_path.exists():
            return None

        try:
            with open(transform_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or []

            for group in config if isinstance(config, list) else []:
                if group.get("group_by") != group_by:
                    continue
                for source in group.get("sources", []):
                    if source.get("name") == source_name:
                        data_path = source.get("data", "")
                        if data_path.endswith(".csv"):
                            return work_dir / data_path
            return None
        except Exception:
            return None
