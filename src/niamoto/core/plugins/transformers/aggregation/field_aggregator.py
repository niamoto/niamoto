"""
Plugin for aggregating fields from different sources.
"""

from typing import Dict, Any, Union, List, Optional, Literal
from pydantic import BaseModel, field_validator, Field, ConfigDict
import os

import pandas as pd
import geopandas as gpd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DatabaseError
from niamoto.common.config import Config


class FieldConfig(BaseModel):
    """Configuration for a single field mapping.

    This model defines how to extract and transform a field from a source.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source": "taxon_ref",
                "field": "full_name",
                "target": "name",
                "transformation": "direct",
                "units": "",
                "format": "text",
            }
        }
    )

    source: str = Field(
        ...,
        description="Source table or data source name",
        json_schema_extra={"ui:widget": "select"},
    )
    field: str = Field(
        ..., description="Field name to extract (supports dot notation for JSON fields)"
    )
    target: str = Field(..., description="Target field name in output")
    transformation: Literal["direct", "count", "sum"] = Field(
        default="direct", description="Type of transformation to apply"
    )
    units: str = Field(
        default="", description="Units for the field value (e.g., 'ha', 'm', 'km²')"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict, description="Value mappings for field labels"
    )
    format: Optional[Literal["boolean", "url", "text", "number"]] = Field(
        None, description="Output format type for UI rendering"
    )

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v):
        """Convert list of labels to dictionary if needed."""
        if isinstance(v, list):
            return {str(label): str(label) for label in v}
        return v


class FieldAggregatorParams(BaseModel):
    """Parameters for field aggregator plugin.

    This model validates the complete parameter set for the field aggregator.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Aggregate multiple fields from different sources into a unified output"
        }
    )

    fields: List[FieldConfig] = Field(
        ..., min_length=1, description="List of field configurations to process"
    )


class FieldAggregatorConfig(PluginConfig):
    """Complete configuration for field aggregator plugin."""

    plugin: Literal["field_aggregator"] = "field_aggregator"
    params: FieldAggregatorParams


@register("field_aggregator", PluginType.TRANSFORMER)
class FieldAggregator(TransformerPlugin):
    """Field aggregator transformer."""

    config_model = FieldAggregatorConfig
    param_schema = FieldAggregatorParams

    def __init__(self, db):
        super().__init__(db)
        self.config = Config()
        self.imports_config = self.config.get_imports_config

    def validate_config(self, config: Dict[str, Any]) -> FieldAggregatorConfig:
        """Validate configuration and return validated config."""
        try:
            # Validate config using pydantic model
            return self.config_model(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def _get_field_from_table(self, table: str, field: str, id_value: int) -> Any:
        """Get a field value from any table.

        Support for JSON fields using dot notation: field.json_key
        For example: extra_data.taxon_type will extract the taxon_type from the extra_data JSON field
        """
        try:
            # Check if we're trying to access a JSON field (using dot notation)
            if "." in field:
                json_field, json_key = field.split(".", 1)
                query = f"""
                    SELECT {json_field} FROM {table} WHERE id = {id_value}
                """
                result = self.db.execute_select(query).fetchone()

                if result and result[0] is not None:
                    # Parse the JSON and extract the requested key
                    import json

                    try:
                        json_data = (
                            json.loads(result[0])
                            if isinstance(result[0], str)
                            else result[0]
                        )
                        # Return the value from the JSON if it exists, otherwise None
                        return (
                            str(json_data.get(json_key))
                            if json_key in json_data
                            else None
                        )
                    except (json.JSONDecodeError, AttributeError):
                        # If JSON parsing fails or the result is not a valid JSON
                        return None
                return None
            else:
                # Regular field access
                query = f"""
                    SELECT {field} FROM {table} WHERE id = {id_value}
                """
                result = self.db.execute_select(query).fetchone()
                return str(result[0]) if result and result[0] is not None else None
        except Exception as e:
            raise DatabaseError(f"Error getting field {field} from {table}") from e

    def _get_field_value(self, source: str, field: str, id_value: int) -> Any:
        """Get a field value from a source (table or import)."""
        try:
            # D'abord vérifier si la source est dans import.yml
            if source in self.imports_config:
                import_config = self.imports_config[source]

                # Construire le chemin complet du fichier
                file_path = os.path.join(
                    os.path.dirname(self.config.config_dir), import_config["path"]
                )

                # Charger les données selon le type
                if import_config["type"] == "csv":
                    df = pd.read_csv(file_path)
                elif import_config["type"] == "vector":
                    df = gpd.read_file(file_path)
                else:
                    raise ValueError(
                        f"Unsupported import type: {import_config['type']}"
                    )

                # Récupérer la valeur en utilisant l'identifiant spécifié
                identifier = import_config["identifier"]

                row = df[df[identifier] == id_value]
                if not row.empty:
                    value = str(row[field].iloc[0])
                    return value
                else:
                    return None

            return self._get_field_from_table(source, field, id_value)

        except Exception as e:
            raise ValueError(f"Error getting field {field} from {source}") from e

    def transform(
        self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform data according to configuration."""
        validated_config = self.validate_config(config)
        result = {}

        for field in validated_config.params.fields:
            # Determine if we should use DataFrame or DB/import source
            source_data = None

            # Check if data is a dict of sources
            if isinstance(data, dict):
                # Multiple sources available
                if field.source in data:
                    source_data = data[field.source]
                elif field.source == "occurrences" and "main" in data:
                    # For backward compatibility, 'occurrences' may refer to main source
                    source_data = data["main"]
                # If not found in data dict, source_data remains None (will use DB/import)
            elif isinstance(data, pd.DataFrame):
                # Single DataFrame passed - only use it if source is "occurrences" or empty
                if field.source == "occurrences" or not field.source:
                    source_data = data
                # Otherwise source_data remains None (will use DB/import)

            if field.transformation == "count":
                if source_data is not None:
                    value = len(source_data)
                else:
                    value = 0
            elif field.transformation == "sum":
                if source_data is not None:
                    value = source_data[field.field].sum()
                else:
                    value = 0
            else:  # direct
                try:
                    if source_data is not None:
                        # We have DataFrame source data
                        if not source_data.empty:
                            # Check if it's a JSON field access (contains dot notation)
                            if "." in field.field:
                                # Extract JSON field from DataFrame
                                json_field, json_key = field.field.split(".", 1)
                                if json_field in source_data.columns:
                                    json_data = source_data[json_field].iloc[0]
                                    if json_data:
                                        import json as json_module

                                        try:
                                            parsed = (
                                                json_module.loads(json_data)
                                                if isinstance(json_data, str)
                                                else json_data
                                            )
                                            if isinstance(parsed, dict):
                                                value = parsed.get(json_key)
                                            else:
                                                value = None
                                        except (
                                            json_module.JSONDecodeError,
                                            AttributeError,
                                        ):
                                            value = None
                                    else:
                                        value = None
                                else:
                                    value = None
                            else:
                                # Regular field access
                                value = source_data[field.field].iloc[0]
                        else:
                            # Empty DataFrame - return None
                            value = None
                    else:  # DB, import, etc.
                        # Check if it's a JSON field access (contains dot notation)
                        if "." in field.field:
                            # Use _get_field_from_table for JSON field extraction
                            value = self._get_field_from_table(
                                field.source, field.field, config.get("group_id")
                            )
                        else:
                            # Use _get_field_value for regular fields
                            value = self._get_field_value(
                                field.source, field.field, config.get("group_id")
                            )
                except (KeyError, IndexError, TypeError):
                    # Handle potential errors during DataFrame access or dict navigation
                    value = None  # Default to None on error

            # Apply labels if any
            if field.labels and str(value) in field.labels:
                value = field.labels[str(value)]

            # Convert boolean to JSON-serializable format
            if isinstance(value, bool):
                value = value  # Keep as boolean, but ensure it's properly handled by JSON encoder
            elif value is not None and str(value).lower() in ["true", "false"]:
                # Convert string representations of booleans
                value = str(value).lower() == "true"

            # Add units if any
            if field.units:
                result[field.target] = {
                    "value": value,
                    "units": field.units,
                }
            else:
                result[field.target] = {"value": value}

        return result
