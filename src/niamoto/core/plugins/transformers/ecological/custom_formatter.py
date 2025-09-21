"""
Plugin for custom formatting of data for visualization.
Facilitates the adaptation of transformer outputs to widget requirements.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import Field, ConfigDict
import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class CustomFormatterParams(BasePluginParams):
    """Typed parameters for custom formatter plugin.

    This plugin formats data according to predefined templates
    for various widget types and visualization requirements.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Format data for specific widget templates",
            "examples": [
                {"template": "gauge", "value": 75.5, "max": 100, "units": "%"},
                {
                    "template": "simple_bar",
                    "labels": ["A", "B", "C"],
                    "values": [10, 20, 15],
                },
            ],
        }
    )

    template: Literal[
        "forest_cover",
        "gauge",
        "stacked_area",
        "forest_types",
        "fragmentation_distribution",
        "holdridge",
        "elevation_distribution",
        "land_use",
        "simple_bar",
        "simple_line",
        "pie_chart",
        "table",
    ] = Field(
        ...,
        description="Template name for data formatting",
        json_schema_extra={"ui:widget": "select"},
    )

    # Template-specific parameters (all optional since they depend on template)
    value: Optional[float] = Field(
        default=None,
        description="Value for gauge template",
        json_schema_extra={
            "ui:widget": "number",
            "ui:condition": "template === 'gauge'",
        },
    )

    max: Optional[float] = Field(
        default=100,
        description="Maximum value for gauge",
        json_schema_extra={
            "ui:widget": "number",
            "ui:condition": "template === 'gauge'",
        },
    )

    units: Optional[str] = Field(
        default="",
        description="Units for gauge display",
        json_schema_extra={"ui:widget": "text", "ui:condition": "template === 'gauge'"},
    )

    labels: Optional[List[str]] = Field(
        default=None,
        description="Labels for bar/line/pie charts",
        json_schema_extra={
            "ui:widget": "tags",
            "ui:condition": "template === 'simple_bar' || template === 'simple_line' || template === 'pie_chart'",
        },
    )

    values: Optional[List[float]] = Field(
        default=None,
        description="Values for bar/line/pie charts",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "template === 'simple_bar' || template === 'simple_line' || template === 'pie_chart'",
        },
    )

    categories: Optional[List[str]] = Field(
        default=None,
        description="Categories for forest types and land use",
        json_schema_extra={
            "ui:widget": "tags",
            "ui:condition": "template === 'forest_types' || template === 'land_use'",
        },
    )

    headers: Optional[List[str]] = Field(
        default=None,
        description="Column headers for table template",
        json_schema_extra={"ui:widget": "tags", "ui:condition": "template === 'table'"},
    )

    rows: Optional[List[List[Any]]] = Field(
        default=None,
        description="Table rows data",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "template === 'table'",
        },
    )


class CustomFormatterConfig(PluginConfig):
    """Configuration for custom formatter plugin"""

    plugin: Literal["custom_formatter"] = "custom_formatter"
    params: CustomFormatterParams


@register("custom_formatter", PluginType.TRANSFORMER)
class CustomFormatter(TransformerPlugin):
    """
    Plugin that formats data according to a specified template.

    Supports several predefined templates for common widget formats
    and can be extended with custom templates.
    """

    config_model = CustomFormatterConfig

    def validate_config(self, config: Dict[str, Any]) -> CustomFormatterConfig:
        """Validate configuration and return typed config."""
        try:
            return self.config_model(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def get_supported_templates(self) -> List[str]:
        """Returns the list of supported templates."""
        return [
            "forest_cover",  # Forest cover (ring chart)
            "gauge",  # Simple gauge
            "stacked_area",  # Stacked area chart
            "forest_types",  # Forest types (ring chart)
            "fragmentation_distribution",  # Fragmentation distribution
            "holdridge",  # Holdridge life zones
            "elevation_distribution",  # Elevation distribution
            "land_use",  # Land use
            "simple_bar",  # Simple bar chart
            "simple_line",  # Simple line chart
            "pie_chart",  # Pie chart
            "table",  # Simple table
        ]

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data according to the specified template.

        Args:
            data: Input DataFrame (ignored if data is provided in params)
            config: Configuration with:
                - template: Name of the template to use
                - ... template-specific parameters

        Returns:
            Formatted dictionary for the target widget
        """
        try:
            # Validate the configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get the template
            template = params.template

            # Convert params to dict for template methods (temporary)
            data_params = params.model_dump(exclude={"template"}, exclude_none=True)

            # Apply the appropriate template
            if template == "forest_cover":
                return self._format_forest_cover(data_params)

            elif template == "gauge":
                return self._format_gauge(data_params)

            elif template == "stacked_area":
                return self._format_stacked_area(data_params)

            elif template == "forest_types":
                return self._format_forest_types(data_params)

            elif template == "fragmentation_distribution":
                return self._format_fragmentation_distribution(data_params)

            elif template == "holdridge":
                return self._format_holdridge(data_params)

            elif template == "elevation_distribution":
                return self._format_elevation_distribution(data_params)

            elif template == "land_use":
                return self._format_land_use(data_params)

            elif template == "simple_bar":
                return self._format_simple_bar(data_params)

            elif template == "simple_line":
                return self._format_simple_line(data_params)

            elif template == "pie_chart":
                return self._format_pie_chart(data_params)

            elif template == "table":
                return self._format_table(data_params)

            else:
                raise DataTransformError(
                    f"Unsupported template: {template}", details={"template": template}
                )

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during formatting: {str(e)}", details={"config": config}
            )

    def _format_forest_cover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for a forest cover widget.

        Expected format:
        {
            "emprise": {"forest": float, "non_forest": float},
            "um": {"forest": float, "non_forest": float},
            "num": {"forest": float, "non_forest": float}
        }
        """
        required_keys = ["emprise", "um", "num"]
        for key in required_keys:
            if key not in params:
                raise DataTransformError(
                    f"Missing parameter: {key}",
                    details={"params": params, "required": required_keys},
                )

            if "forest" not in params[key] or "non_forest" not in params[key]:
                raise DataTransformError(
                    f"Missing keys 'forest' and 'non_forest' for '{key}'",
                    details={"params": params[key]},
                )

        # Validation des valeurs (les convertir en float)
        for key in required_keys:
            params[key]["forest"] = float(params[key]["forest"])
            params[key]["non_forest"] = float(params[key]["non_forest"])

        return params

    def _format_gauge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for a gauge widget.

        Expected format:
        {
            "value": float,
            "max": float,
            "units": str
        }
        """
        required_keys = ["value"]
        for key in required_keys:
            if key not in params:
                raise DataTransformError(
                    f"Missing parameter: {key}",
                    details={"params": params, "required": required_keys},
                )

        # Valeurs par defaut
        if "max" not in params:
            params["max"] = 100

        if "units" not in params:
            params["units"] = ""

        # Conversion des valeurs
        params["value"] = float(params["value"])
        params["max"] = float(params["max"])

        return params

    def _format_stacked_area(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for a stacked area chart.

        Expected format:
        {
            "altitudes": [float, ...],
            "secondaire": [float, ...],
            "mature": [float, ...],
            "coeur": [float, ...]
        }
        """
        required_keys = ["altitudes"]
        for key in required_keys:
            if key not in params:
                raise DataTransformError(
                    f"Missing parameter: {key}",
                    details={"params": params, "required": required_keys},
                )

        # Vérifier que tous les tableaux ont la même longueur
        length = len(params["altitudes"])
        for key, value in params.items():
            if key != "altitudes" and isinstance(value, list):
                if len(value) != length:
                    raise DataTransformError(
                        f"Incompatible length for '{key}': {len(value)} (expected: {length})",
                        details={"params": params},
                    )

        return params

    def _format_forest_types(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for a forest types widget.

        Expected format:
        {
            "categories": [str, ...],
            "values": [float, ...]
        }
        """
        required_keys = ["categories", "values"]
        for key in required_keys:
            if key not in params:
                raise DataTransformError(
                    f"Missing parameter: {key}",
                    details={"params": params, "required": required_keys},
                )

        # Check that all arrays have the same length
        if len(params["categories"]) != len(params["values"]):
            raise DataTransformError(
                f"Incompatible length: categories {len(params['categories'])}, values {len(params['values'])}",
                details={"params": params},
            )

        # Convert values to float
        params["values"] = [float(v) for v in params["values"]]

        return params

    def _format_fragmentation_distribution(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Formats the data for the forest fragmentation distribution.

        Expected format:
        {
            "sizes": [float, ...],
            "values": [float, ...]
        }
        """
        required_keys = ["sizes"]
        for key in required_keys:
            if key not in params:
                raise DataTransformError(
                    f"Missing parameter: {key}",
                    details={"params": params, "required": required_keys},
                )

        # Convert sizes to float
        params["sizes"] = [float(s) for s in params["sizes"]]

        # Calculate cumulative values if requested
        if params.get("cumulative", False):
            sizes = params["sizes"]
            total = sum(sizes)

            cumulative = 0
            values = []

            for size in sizes:
                cumulative += size
                values.append(cumulative / total * 100 if total > 0 else 0)

            params["values"] = values
        elif "values" not in params:
            params["values"] = params["sizes"]

        return params

    def _format_holdridge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for the Holdridge life zones widget.

        Expected format:
        {
            "forest": {
                "sec": float,
                "humide": float,
                "tres_humide": float
            },
            "non_forest": {
                "sec": float,
                "humide": float,
                "tres_humide": float
            }
        }
        """
        required_keys = ["forest", "non_forest"]
        for key in required_keys:
            if key not in params:
                raise DataTransformError(
                    f"Missing parameter: {key}",
                    details={"params": params, "required": required_keys},
                )

        # Check sub-keys
        sub_keys = ["sec", "humide", "tres_humide"]
        for main_key in required_keys:
            for sub_key in sub_keys:
                if sub_key not in params[main_key]:
                    raise DataTransformError(
                        f"Missing parameter: {main_key}.{sub_key}",
                        details={"params": params[main_key], "required": sub_keys},
                    )

        # Convert values to float
        for main_key in required_keys:
            for sub_key in sub_keys:
                params[main_key][sub_key] = float(params[main_key][sub_key])

        return params

    def _format_elevation_distribution(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for the elevation distribution.

        Expected format:
        {
            "elevation": {
                "classes": [str, ...],
                "subset": [float, ...],
                "complement": [float, ...]
            }
        }
        """
        if "elevation" not in params:
            raise DataTransformError(
                "Missing parameter: elevation", details={"params": params}
            )

        # Check sub-keys
        sub_keys = ["classes", "subset", "complement"]
        for sub_key in sub_keys:
            if sub_key not in params["elevation"]:
                raise DataTransformError(
                    f"Missing parameter: elevation.{sub_key}",
                    details={"params": params["elevation"], "required": sub_keys},
                )

        # Check that all arrays have the same length
        length = len(params["elevation"]["classes"])
        if (
            len(params["elevation"]["subset"]) != length
            or len(params["elevation"]["complement"]) != length
        ):
            raise DataTransformError(
                "Incompatible lengths in elevation",
                details={
                    "classes": len(params["elevation"]["classes"]),
                    "subset": len(params["elevation"]["subset"]),
                    "complement": len(params["elevation"]["complement"]),
                },
            )

        # Convert values to float
        params["elevation"]["subset"] = [
            float(v) for v in params["elevation"]["subset"]
        ]
        params["elevation"]["complement"] = [
            float(v) for v in params["elevation"]["complement"]
        ]

        return params

    def _format_land_use(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for the land use widget.

        Expected format:
        {
            "categories": [str, ...],
            "values": [float, ...]
        }
        """
        required_keys = ["categories", "values"]
        for key in required_keys:
            if key not in params:
                raise DataTransformError(
                    f"Missing parameter: {key}",
                    details={"params": params, "required": required_keys},
                )

        # Check that all arrays have the same length
        if len(params["categories"]) != len(params["values"]):
            raise DataTransformError(
                f"Incompatible length: categories {len(params['categories'])}, values {len(params['values'])}",
                details={"params": params},
            )

        # Convert values to float
        params["values"] = [float(v) for v in params["values"]]

        return params

    def _format_simple_bar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for a simple bar chart.

        Expected format:
        {
            "labels": [str, ...],
            "values": [float, ...],
            "colors": [str, ...]  # optional
        }
        """
        required_keys = ["labels", "values"]
        for key in required_keys:
            if key not in params:
                raise DataTransformError(
                    f"Missing parameter: {key}",
                    details={"params": params, "required": required_keys},
                )

        # Check that all arrays have the same length
        if len(params["labels"]) != len(params["values"]):
            raise DataTransformError(
                f"Incompatible length: labels {len(params['labels'])}, values {len(params['values'])}",
                details={"params": params},
            )

        # Convert values to float
        params["values"] = [float(v) for v in params["values"]]

        return params

    def _format_simple_line(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for a simple line chart.

        Expected format:
        {
            "labels": [str, ...],
            "values": [float, ...],
            "color": str  # optional
        }
        """
        return self._format_simple_bar(params)  # Same format

    def _format_pie_chart(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for a pie chart.

        Expected format:
        {
            "labels": [str, ...],
            "values": [float, ...],
            "colors": [str, ...]  # optional
        }
        """
        return self._format_simple_bar(params)  # Same format

    def _format_table(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the data for a table.

        Expected format:
        {
            "headers": [str, ...],
            "rows": [[value, ...], ...]
        }
        """
        required_keys = ["headers", "rows"]
        for key in required_keys:
            if key not in params:
                raise DataTransformError(
                    f"Missing parameter: {key}",
                    details={"params": params, "required": required_keys},
                )

        # Check that all rows have the same number of columns as the headers
        header_length = len(params["headers"])
        for i, row in enumerate(params["rows"]):
            if len(row) != header_length:
                raise DataTransformError(
                    f"Incompatible length for row {i}: {len(row)} (expected: {header_length})",
                    details={"row": row, "headers": params["headers"]},
                )

        return params
