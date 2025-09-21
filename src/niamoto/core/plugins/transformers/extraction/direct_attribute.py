"""
Plugin for getting a direct attribute from a source.
"""

from typing import Dict, Any, Union, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import os
import pandas as pd
import geopandas as gpd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DatabaseError
from niamoto.common.config import Config


class DirectAttributeParams(BaseModel):
    """Parameters for direct attribute extraction.

    This plugin extracts a single field value directly from a data source.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Extract a single attribute value from a data source",
            "examples": [
                {"source": "plots", "field": "shannon", "units": "", "max_value": 5},
                {
                    "source": "plots",
                    "field": "basal_area",
                    "units": "m²/ha",
                    "max_value": 100,
                    "format": "number",
                    "precision": 2,
                },
            ],
        }
    )

    source: str = Field(
        ...,
        description="Data source name (table or import)",
        json_schema_extra={"ui:widget": "select"},
    )
    field: str = Field(
        ...,
        description="Field name to extract from the source",
        json_schema_extra={"ui:widget": "field-select", "ui:depends": "source"},
    )
    units: str = Field(
        default="", description="Units for the value (e.g., 'm', 'ha', 'g/cm³')"
    )
    max_value: Optional[float] = Field(
        None, description="Maximum value to cap the result (for gauge widgets)"
    )
    format: Optional[Literal["number", "percentage", "text"]] = Field(
        None, description="Output format type"
    )
    precision: Optional[int] = Field(
        None, ge=0, le=10, description="Number of decimal places for numeric values"
    )

    @field_validator("max_value")
    @classmethod
    def validate_max_value(cls, v):
        """Ensure max_value is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("max_value must be positive")
        return v


class DirectAttributeConfig(PluginConfig):
    """Complete configuration for direct attribute plugin."""

    plugin: Literal["direct_attribute"] = "direct_attribute"
    params: DirectAttributeParams


@register("direct_attribute", PluginType.TRANSFORMER)
class DirectAttribute(TransformerPlugin):
    """Plugin for getting a direct attribute"""

    config_model = DirectAttributeConfig

    def __init__(self, db):
        super().__init__(db)
        try:
            self.config = Config()
            self.imports_config = self.config.get_imports_config()
        except Exception:
            # In test environment, config might not be available
            self.config = None
            self.imports_config = {}

    def validate_config(self, config: Dict[str, Any]) -> DirectAttributeConfig:
        """Validate configuration and return typed config."""
        try:
            return self.config_model(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def _get_field_from_table(self, source: str, field: str, id_value: int) -> Any:
        """Get a field value from any table."""
        try:
            query = f"""
                SELECT {field} FROM {source} WHERE id = {id_value}
            """
            result = self.db.execute_select(query).fetchone()
            # Return raw value without string conversion to preserve format
            return result[0] if result and result[0] is not None else None
        except Exception as e:
            raise DatabaseError(f"Error getting field {field} from {source}") from e

    def _get_field_value(self, source: str, field: str, id_value: int) -> Any:
        """Get a field value from a source (table or import)."""
        try:
            # D'abord vérifier si la source est dans import.yml
            if source in self.imports_config:
                import_config = self.imports_config[source]

                # Construire le chemin complet du fichier
                if self.config and hasattr(self.config, "config_dir"):
                    file_path = os.path.join(
                        os.path.dirname(self.config.config_dir), import_config["path"]
                    )
                else:
                    # Fallback for tests
                    file_path = import_config["path"]

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
                    # Return the raw value instead of converting to string
                    return row[field].iloc[0]
                else:
                    return None

            return self._get_field_from_table(source, field, id_value)

        except Exception as e:
            raise ValueError(f"Error getting field {field} from {source}") from e

    def transform(
        self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Préserver group_id avant validation
            group_id = config.get("group_id")
            validated_config = self.validate_config(config)
            params = validated_config.params

            if group_id is None:
                return {"value": None}

            # Get field value
            source = params.source
            field = params.field

            # Check if data is already the source we need (TransformerService smart selection)
            value = None
            if isinstance(data, pd.DataFrame):
                # Data is already a DataFrame - TransformerService passed the requested source directly
                if not data.empty:
                    if field in data.columns:
                        value = data[field].iloc[0]
                    else:
                        value = None
                else:
                    value = None
            elif isinstance(data, dict) and source in data:
                # Use DataFrame from the sources dict
                source_df = data[source]
                if isinstance(source_df, pd.DataFrame) and not source_df.empty:
                    # Get value from first row
                    if field in source_df.columns:
                        value = source_df[field].iloc[0]
                    else:
                        # Field not found in DataFrame columns
                        value = None
            else:
                # Fall back to loading from DB or import
                value = self._get_field_value(source, field, group_id)

            # Handle numeric values while preserving format
            original_format = value
            max_value = params.max_value

            if value is not None:
                try:
                    # Check if we need to apply max value restriction
                    float_value = float(value)
                    if max_value is not None and float_value > float(max_value):
                        value = float(max_value)
                    else:
                        # Preserve original format by converting back to string
                        # only if we didn't apply max_value
                        value = original_format
                except ValueError:
                    # If value can't be converted to float, keep it as is
                    pass

                # Ensure consistent string representation
                if isinstance(value, (float, int)):
                    # Apply precision if specified
                    if params.precision is not None:
                        value = f"{value:.{params.precision}f}"
                    elif isinstance(original_format, str) and "." in original_format:
                        # Try to maintain decimal precision from original
                        decimal_places = len(original_format.split(".")[-1])
                        value = f"{value:.{decimal_places}f}"
                    else:
                        # Convert to string while removing .0 for integers
                        value = (
                            str(value).rstrip("0").rstrip(".")
                            if "." in str(value)
                            else str(value)
                        )

            result = {
                "value": value,
                "units": params.units,
            }

            # Add optional fields if they exist
            if params.max_value is not None:
                result["max_value"] = params.max_value
            if params.format is not None:
                result["format"] = params.format

            return result

        except Exception as e:
            raise ValueError(f"Error transforming data: {str(e)}")
