"""
Plugin for aggregating fields from different sources.
"""

from typing import Dict, Any
from pydantic import BaseModel, field_validator, Field
import os

import pandas as pd
import geopandas as gpd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DatabaseError
from niamoto.common.config import Config


class FieldConfig(BaseModel):
    """Field configuration."""

    source: str
    field: str
    target: str
    transformation: str = "direct"
    units: str = ""
    labels: Dict[str, str] = {}

    @field_validator("transformation")
    def validate_transformation(cls, v):
        """Validate transformation."""
        if v not in ["direct", "count", "sum"]:
            raise ValueError(f"Invalid transformation: {v}")
        return v

    @field_validator("labels")
    def validate_labels(cls, v):
        """Convert list of labels to dictionary if needed."""
        if isinstance(v, list):
            return {str(label): str(label) for label in v}
        return v


class FieldAggregatorConfig(PluginConfig):
    """Field aggregator configuration."""

    plugin: str = "field_aggregator"
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        if "fields" not in v:
            raise ValueError("Missing required field: fields")

        if not isinstance(v["fields"], list):
            raise ValueError("fields must be a list")

        return v


@register("field_aggregator", PluginType.TRANSFORMER)
class FieldAggregator(TransformerPlugin):
    """Field aggregator transformer."""

    config_model = FieldAggregatorConfig

    def __init__(self, db):
        super().__init__(db)
        self.config = Config()
        self.imports_config = self.config.get_imports_config

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            # Validate config using pydantic model
            validated_config = self.config_model(**config)

            # Validate each field config
            for field_config in validated_config.params["fields"]:
                FieldConfig.model_validate(field_config)
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

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        self.validate_config(config)
        validated_config = self.config_model(**config)
        result = {}

        for field_config in validated_config.params["fields"]:
            # Validate field config using pydantic
            field = FieldConfig.model_validate(field_config)

            if field.transformation == "count":
                value = len(data)
            elif field.transformation == "sum":
                value = data[field.field].sum()
            else:  # direct
                try:
                    if field.source == "occurrences":
                        # Handle dot notation for DataFrame columns if needed in the future?
                        # For now, assume direct field access.
                        # Potential future enhancement: use json_normalize or similar if column contains dicts.
                        if not data.empty:
                            value = data[field.field].iloc[0]
                        else:
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

            # Add units if any
            if field.units:
                result[field.target] = {
                    "value": value,
                    "units": field.units,
                }
            else:
                result[field.target] = {"value": value}

        return result
